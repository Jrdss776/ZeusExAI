import {
  DEFAULT_OLLAMA_URL,
  getOllamaMemorySnapshot,
  isLocalModel,
  preloadModel,
  unloadModel,
  type OllamaMemorySnapshot,
} from './api';

export const SMART_PERFORMANCE_IDLE_MS = 20 * 60 * 1000;

type Timer = ReturnType<typeof setTimeout>;
type LogLevel = 'info' | 'error';
type ModelOperation = (model: string, host: string, keepAliveMinutes?: number) => Promise<void>;
type MemoryProbe = (model: string, host: string) => Promise<OllamaMemorySnapshot>;

interface SmartPerformanceDependencies {
  load?: ModelOperation;
  unload?: ModelOperation;
  measure?: MemoryProbe;
  idleMs?: number;
  enabled?: boolean;
  host?: string;
  onLoadingChange?: (loading: boolean) => void;
  onLog?: (level: LogLevel, message: string) => void;
}

interface SmartPerformanceRuntime {
  enabled: boolean;
  idleMs?: number;
  host?: string;
  onLoadingChange?: (loading: boolean) => void;
  onLog?: (level: LogLevel, message: string) => void;
}

function formatBytes(bytes: number): string {
  if (bytes <= 0) return '0 MB';
  return `${(bytes / (1024 ** 3)).toFixed(2)} GB`;
}

export class SmartPerformanceManager {
  private readonly load: ModelOperation;
  private readonly unload: ModelOperation;
  private readonly measure: MemoryProbe;
  private idleMs: number;
  private enabled: boolean;
  private host: string;
  private onLoadingChange: (loading: boolean) => void;
  private onLog: (level: LogLevel, message: string) => void;
  private activeModel: string | null = null;
  private activationQueue: Promise<void> = Promise.resolve();
  private readonly readyModels = new Set<string>();
  private readonly loads = new Map<string, Promise<void>>();
  private readonly unloads = new Map<string, Promise<void>>();
  private readonly timers = new Map<string, Timer>();
  private readonly activeUses = new Map<string, number>();
  private readonly memoryByModel = new Map<string, OllamaMemorySnapshot>();
  private readonly lifecycleEpoch = new Map<string, number>();

  constructor(dependencies: SmartPerformanceDependencies = {}) {
    this.load = dependencies.load ?? preloadModel;
    this.unload = dependencies.unload ?? unloadModel;
    this.measure = dependencies.measure ?? getOllamaMemorySnapshot;
    this.idleMs = dependencies.idleMs ?? SMART_PERFORMANCE_IDLE_MS;
    this.enabled = dependencies.enabled ?? true;
    this.host = dependencies.host ?? DEFAULT_OLLAMA_URL;
    this.onLoadingChange = dependencies.onLoadingChange ?? (() => {});
    this.onLog = dependencies.onLog ?? (() => {});
  }

  configure(runtime: SmartPerformanceRuntime): void {
    const requestedIdleMs = runtime.idleMs ?? this.idleMs;
    const nextIdleMs = Number.isFinite(requestedIdleMs)
      ? Math.max(60_000, requestedIdleMs)
      : SMART_PERFORMANCE_IDLE_MS;
    const idleChanged = nextIdleMs !== this.idleMs;
    this.idleMs = nextIdleMs;
    this.enabled = runtime.enabled;
    this.host = runtime.host?.trim() || DEFAULT_OLLAMA_URL;
    if (runtime.onLoadingChange) this.onLoadingChange = runtime.onLoadingChange;
    if (runtime.onLog) this.onLog = runtime.onLog;
    if (!this.enabled) {
      for (const timer of this.timers.values()) clearTimeout(timer);
      this.timers.clear();
      this.readyModels.clear();
      this.memoryByModel.clear();
      this.lifecycleEpoch.clear();
      this.activeModel = null;
      this.onLoadingChange(false);
    } else if (idleChanged) {
      for (const model of this.readyModels) {
        if ((this.activeUses.get(model) ?? 0) === 0) this.scheduleIdleUnload(model);
      }
    }
  }

  async warm(model: string): Promise<void> {
    if (!this.manages(model)) return;

    const unloading = this.unloads.get(model);
    if (unloading) await unloading;

    if (this.readyModels.has(model)) {
      this.scheduleIdleUnload(model);
      return;
    }

    const existing = this.loads.get(model);
    if (existing) return existing;

    const operation = (async () => {
      this.onLog('info', `Carregando ${model} para uso...`);
      const startedAt = Date.now();
      try {
        await this.load(model, this.host, Math.ceil(this.idleMs / 60_000) + 1);
        this.readyModels.add(model);
        const epoch = this.bumpEpoch(model);
        this.onLog('info', `${model} pronto em ${((Date.now() - startedAt) / 1000).toFixed(1)}s`);
        void this.recordLoadedMemory(model, epoch);
        this.scheduleIdleUnload(model);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        this.onLog('error', `Falha ao carregar ${model}: ${message}`);
        throw error;
      }
    })();

    this.loads.set(model, operation);
    this.syncLoadingState();
    try {
      await operation;
    } finally {
      this.loads.delete(model);
      this.syncLoadingState();
    }
  }

  async activate(model: string): Promise<void> {
    if (!this.manages(model)) return;
    const transition = async () => {
      const previous = this.activeModel;
      await this.warm(model);
      this.activeModel = model;
      if (previous && previous !== model && (this.activeUses.get(previous) ?? 0) === 0) {
        await this.unloadReadyModel(previous, 'troca de modelo');
      }
    };
    const operation = this.activationQueue.then(transition, transition);
    this.activationQueue = operation.catch(() => {});
    return operation;
  }

  activity(model: string): void {
    if (!this.manages(model)) return;
    void this.activate(model).catch(() => {});
  }

  async beginUse(model: string): Promise<void> {
    if (!this.manages(model)) return;
    this.activeUses.set(model, (this.activeUses.get(model) ?? 0) + 1);
    this.clearIdleTimer(model);
    await this.activate(model);
  }

  endUse(model: string): void {
    if (!this.manages(model)) return;
    const remaining = Math.max(0, (this.activeUses.get(model) ?? 1) - 1);
    if (remaining === 0) this.activeUses.delete(model);
    else this.activeUses.set(model, remaining);
    if (this.readyModels.has(model)) this.scheduleIdleUnload(model);
  }

  stop(): void {
    for (const timer of this.timers.values()) clearTimeout(timer);
    this.timers.clear();
  }

  private manages(model: string): boolean {
    return this.enabled && isLocalModel(model);
  }

  private async readMemory(model: string): Promise<OllamaMemorySnapshot | null> {
    try {
      return await this.measure(model, this.host);
    } catch {
      return null;
    }
  }

  private bumpEpoch(model: string): number {
    const epoch = (this.lifecycleEpoch.get(model) ?? 0) + 1;
    this.lifecycleEpoch.set(model, epoch);
    return epoch;
  }

  private async recordLoadedMemory(model: string, epoch: number): Promise<void> {
    const snapshot = await this.readMemory(model);
    if (!snapshot || this.lifecycleEpoch.get(model) !== epoch || !this.readyModels.has(model)) return;
    this.memoryByModel.set(model, snapshot);
    if (snapshot.modelBytes > 0) {
      this.onLog(
        'info',
        `${model}: memória ${formatBytes(snapshot.modelBytes)}${snapshot.modelVramBytes ? `, VRAM ${formatBytes(snapshot.modelVramBytes)}` : ''}`,
      );
    }
  }

  private async recordReleasedMemory(
    model: string,
    before: OllamaMemorySnapshot | undefined,
    epoch: number,
  ): Promise<void> {
    const after = await this.readMemory(model);
    if (this.lifecycleEpoch.get(model) !== epoch || this.readyModels.has(model)) return;
    this.memoryByModel.delete(model);
    if (!before || !after) return;
    const released = Math.max(0, before.modelBytes - after.modelBytes);
    const releasedVram = Math.max(0, before.modelVramBytes - after.modelVramBytes);
    if (released > 0) {
      this.onLog(
        'info',
        `${model}: liberados ${formatBytes(released)}${releasedVram ? `, VRAM ${formatBytes(releasedVram)}` : ''}`,
      );
    }
  }

  private syncLoadingState(): void {
    this.onLoadingChange(this.enabled && this.loads.size > 0);
  }

  private clearIdleTimer(model: string): void {
    const timer = this.timers.get(model);
    if (timer) clearTimeout(timer);
    this.timers.delete(model);
  }

  private scheduleIdleUnload(model: string): void {
    this.clearIdleTimer(model);
    if ((this.activeUses.get(model) ?? 0) > 0) return;
    const timer = setTimeout(() => {
      this.timers.delete(model);
      void this.unloadReadyModel(model, 'inatividade');
    }, this.idleMs);
    this.timers.set(model, timer);
  }

  private async unloadReadyModel(model: string, reason: string): Promise<void> {
    if ((this.activeUses.get(model) ?? 0) > 0 || !this.readyModels.has(model)) return;

    this.clearIdleTimer(model);
    this.readyModels.delete(model);
    const epoch = this.bumpEpoch(model);
    const before = this.memoryByModel.get(model);
    const operation = (async () => {
      try {
        await this.unload(model, this.host);
        this.onLog('info', `${model} descarregado por ${reason}`);
        void this.recordReleasedMemory(model, before, epoch);
      } catch (error) {
        this.readyModels.add(model);
        const message = error instanceof Error ? error.message : String(error);
        this.onLog('error', `Falha ao descarregar ${model}: ${message}`);
        this.scheduleIdleUnload(model);
      }
    })();
    this.unloads.set(model, operation);
    try {
      await operation;
    } finally {
      this.unloads.delete(model);
    }
  }
}

const manager = new SmartPerformanceManager({ enabled: false });

export function configureSmartPerformance(runtime: SmartPerformanceRuntime): void {
  manager.configure(runtime);
}

export const warmModel = (model: string) => manager.activate(model);
export const noteModelActivity = (model: string) => manager.activity(model);
export const beginModelUse = (model: string) => manager.beginUse(model);
export const endModelUse = (model: string) => manager.endUse(model);

export function watchSmartPerformanceActivity(getModel: () => string): () => void {
  const wake = () => noteModelActivity(getModel());
  const onVisibility = () => {
    if (document.visibilityState === 'visible') wake();
  };

  window.addEventListener('keydown', wake);
  window.addEventListener('pointerdown', wake);
  window.addEventListener('focus', wake);
  document.addEventListener('visibilitychange', onVisibility);

  return () => {
    window.removeEventListener('keydown', wake);
    window.removeEventListener('pointerdown', wake);
    window.removeEventListener('focus', wake);
    document.removeEventListener('visibilitychange', onVisibility);
    manager.stop();
  };
}
