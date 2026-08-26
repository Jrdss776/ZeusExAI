import { isLocalModel, preloadModel, unloadModel } from './api';

export const SMART_PERFORMANCE_IDLE_MS = 5 * 60 * 1000;

type Timer = ReturnType<typeof setTimeout>;
type LogLevel = 'info' | 'error';

interface SmartPerformanceDependencies {
  load?: (model: string) => Promise<void>;
  unload?: (model: string) => Promise<void>;
  idleMs?: number;
  onLoadingChange?: (loading: boolean) => void;
  onLog?: (level: LogLevel, message: string) => void;
}

export class SmartPerformanceManager {
  private readonly load: (model: string) => Promise<void>;
  private readonly unload: (model: string) => Promise<void>;
  private readonly idleMs: number;
  private onLoadingChange: (loading: boolean) => void;
  private onLog: (level: LogLevel, message: string) => void;
  private readonly readyModels = new Set<string>();
  private readonly loads = new Map<string, Promise<void>>();
  private readonly unloads = new Map<string, Promise<void>>();
  private readonly timers = new Map<string, Timer>();
  private readonly activeUses = new Map<string, number>();

  constructor(dependencies: SmartPerformanceDependencies = {}) {
    this.load = dependencies.load ?? preloadModel;
    this.unload = dependencies.unload ?? unloadModel;
    this.idleMs = dependencies.idleMs ?? SMART_PERFORMANCE_IDLE_MS;
    this.onLoadingChange = dependencies.onLoadingChange ?? (() => {});
    this.onLog = dependencies.onLog ?? (() => {});
  }

  setCallbacks(callbacks: Pick<SmartPerformanceDependencies, 'onLoadingChange' | 'onLog'>) {
    if (callbacks.onLoadingChange) this.onLoadingChange = callbacks.onLoadingChange;
    if (callbacks.onLog) this.onLog = callbacks.onLog;
  }

  async warm(model: string): Promise<void> {
    if (!isLocalModel(model)) return;

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
      try {
        await this.load(model);
        this.readyModels.add(model);
        this.onLog('info', `${model} pronto`);
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

  activity(model: string): void {
    if (!isLocalModel(model)) return;
    if (this.readyModels.has(model)) {
      this.scheduleIdleUnload(model);
      return;
    }
    void this.warm(model).catch(() => {});
  }

  async beginUse(model: string): Promise<void> {
    if (!isLocalModel(model)) return;
    this.activeUses.set(model, (this.activeUses.get(model) ?? 0) + 1);
    this.clearIdleTimer(model);
    await this.warm(model);
  }

  endUse(model: string): void {
    if (!isLocalModel(model)) return;
    const remaining = Math.max(0, (this.activeUses.get(model) ?? 1) - 1);
    if (remaining === 0) this.activeUses.delete(model);
    else this.activeUses.set(model, remaining);
    if (this.readyModels.has(model)) this.scheduleIdleUnload(model);
  }

  stop(): void {
    for (const timer of this.timers.values()) clearTimeout(timer);
    this.timers.clear();
  }

  private syncLoadingState(): void {
    this.onLoadingChange(this.loads.size > 0);
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
      void this.unloadAfterIdle(model);
    }, this.idleMs);
    this.timers.set(model, timer);
  }

  private async unloadAfterIdle(model: string): Promise<void> {
    if ((this.activeUses.get(model) ?? 0) > 0 || !this.readyModels.has(model)) {
      return;
    }

    // Mark it unavailable before the request so a returning user waits for the
    // unload to finish, then performs one clean reload instead of racing both.
    this.readyModels.delete(model);
    const operation = (async () => {
      try {
        await this.unload(model);
        this.onLog('info', `${model} descarregado após inatividade`);
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

const manager = new SmartPerformanceManager();

export function configureSmartPerformance(
  callbacks: Pick<SmartPerformanceDependencies, 'onLoadingChange' | 'onLog'>,
): void {
  manager.setCallbacks(callbacks);
}

export const warmModel = (model: string) => manager.warm(model);
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
