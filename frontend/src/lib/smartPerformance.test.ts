import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SmartPerformanceManager } from './smartPerformance';

const NO_MEMORY = {
  modelBytes: 0,
  modelVramBytes: 0,
  totalBytes: 0,
  totalVramBytes: 0,
};
const noMemory = async () => NO_MEMORY;

describe('SmartPerformanceManager', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('unloads a local model after inactivity and reloads it on return', async () => {
    const load = vi.fn(async () => {});
    const unload = vi.fn(async () => {});
    const manager = new SmartPerformanceManager({ load, unload, measure: noMemory, idleMs: 1_000 });

    await manager.warm('qwen3.5:9b');
    expect(load).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1_000);
    expect(unload).toHaveBeenCalledWith('qwen3.5:9b', 'http://127.0.0.1:11434');

    manager.activity('qwen3.5:9b');
    await vi.waitFor(() => expect(load).toHaveBeenCalledTimes(2));
    manager.stop();
  });

  it('does not unload while a chat request is using the model', async () => {
    const unload = vi.fn(async () => {});
    const manager = new SmartPerformanceManager({
      load: async () => {},
      unload,
      measure: noMemory,
      idleMs: 1_000,
    });

    await manager.beginUse('qwen3.5:9b');
    await vi.advanceTimersByTimeAsync(5_000);
    expect(unload).not.toHaveBeenCalled();

    manager.endUse('qwen3.5:9b');
    await vi.advanceTimersByTimeAsync(1_000);
    expect(unload).toHaveBeenCalledTimes(1);
    manager.stop();
  });

  it('deduplicates concurrent reload requests and clears loading state', async () => {
    let finishLoad: (() => void) | undefined;
    const load = vi.fn(() => new Promise<void>((resolve) => {
      finishLoad = resolve;
    }));
    const loadingChanges: boolean[] = [];
    const manager = new SmartPerformanceManager({
      load,
      unload: async () => {},
      measure: noMemory,
      onLoadingChange: (loading) => loadingChanges.push(loading),
    });

    const first = manager.warm('qwen3.5:9b');
    const second = manager.warm('qwen3.5:9b');
    await vi.waitFor(() => expect(load).toHaveBeenCalledTimes(1));

    finishLoad?.();
    await Promise.all([first, second]);
    expect(loadingChanges).toEqual([true, false]);
    manager.stop();
  });

  it('never manages cloud models through Ollama', async () => {
    const load = vi.fn(async () => {});
    const unload = vi.fn(async () => {});
    const manager = new SmartPerformanceManager({ load, unload, measure: noMemory, idleMs: 1 });

    await manager.warm('gpt-5');
    await manager.beginUse('claude-sonnet');
    manager.activity('gemini-2.5-pro');
    manager.endUse('claude-sonnet');
    await vi.runAllTimersAsync();

    expect(load).not.toHaveBeenCalled();
    expect(unload).not.toHaveBeenCalled();
  });

  it('never touches Ollama when a custom inference source is active', async () => {
    const load = vi.fn(async () => {});
    const unload = vi.fn(async () => {});
    const manager = new SmartPerformanceManager({
      load,
      unload,
      measure: noMemory,
      enabled: false,
    });

    await manager.warm('qwen2.5-7b-instruct');
    await manager.beginUse('qwen2.5-7b-instruct');
    manager.activity('qwen2.5-7b-instruct');
    await vi.runAllTimersAsync();

    expect(load).not.toHaveBeenCalled();
    expect(unload).not.toHaveBeenCalled();
  });

  it('loads the replacement before immediately unloading the previous model', async () => {
    const operations: string[] = [];
    const manager = new SmartPerformanceManager({
      load: async (model) => { operations.push(`load:${model}`); },
      unload: async (model) => { operations.push(`unload:${model}`); },
      measure: noMemory,
    });

    await manager.activate('qwen3.5:9b');
    await manager.activate('qwen3.5:4b');

    expect(operations).toEqual([
      'load:qwen3.5:9b',
      'load:qwen3.5:4b',
      'unload:qwen3.5:9b',
    ]);
    manager.stop();
  });

  it('logs measured memory loaded and released when Ollama exposes /api/ps', async () => {
    const gb = 1024 ** 3;
    const measure = vi.fn()
      .mockResolvedValueOnce({ ...NO_MEMORY, modelBytes: 7 * gb, modelVramBytes: 6 * gb })
      .mockResolvedValueOnce(NO_MEMORY);
    const logs: string[] = [];
    const manager = new SmartPerformanceManager({
      load: async () => {},
      unload: async () => {},
      measure,
      idleMs: 1_000,
      onLog: (_level, message) => logs.push(message),
    });

    await manager.warm('qwen3.5:9b');
    await vi.waitFor(() => {
      expect(logs.some((message) => message.includes('memória 7.00 GB, VRAM 6.00 GB'))).toBe(true);
    });
    await vi.advanceTimersByTimeAsync(1_000);
    await vi.waitFor(() => {
      expect(logs.some((message) => message.includes('liberados 7.00 GB, VRAM 6.00 GB'))).toBe(true);
    });
    manager.stop();
  });

  it('updates the idle timeout and keeps Ollama alive slightly longer', async () => {
    const load = vi.fn(async () => {});
    const unload = vi.fn(async () => {});
    const manager = new SmartPerformanceManager({
      load,
      unload,
      measure: noMemory,
      idleMs: 5 * 60_000,
    });

    manager.configure({ enabled: true, idleMs: 20 * 60_000 });
    await manager.warm('qwen3.5:9b');

    expect(load).toHaveBeenCalledWith('qwen3.5:9b', 'http://127.0.0.1:11434', 21);
    await vi.advanceTimersByTimeAsync(19 * 60_000);
    expect(unload).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(60_000);
    expect(unload).toHaveBeenCalledTimes(1);
    manager.stop();
  });
});
