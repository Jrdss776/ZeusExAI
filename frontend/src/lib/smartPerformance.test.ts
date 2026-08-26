import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SmartPerformanceManager } from './smartPerformance';

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
    const manager = new SmartPerformanceManager({ load, unload, idleMs: 1_000 });

    await manager.warm('qwen3.5:9b');
    expect(load).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1_000);
    expect(unload).toHaveBeenCalledWith('qwen3.5:9b');

    manager.activity('qwen3.5:9b');
    await vi.waitFor(() => expect(load).toHaveBeenCalledTimes(2));
    manager.stop();
  });

  it('does not unload while a chat request is using the model', async () => {
    const unload = vi.fn(async () => {});
    const manager = new SmartPerformanceManager({
      load: async () => {},
      unload,
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
      onLoadingChange: (loading) => loadingChanges.push(loading),
    });

    const first = manager.warm('qwen3.5:9b');
    const second = manager.warm('qwen3.5:9b');
    expect(load).toHaveBeenCalledTimes(1);

    finishLoad?.();
    await Promise.all([first, second]);
    expect(loadingChanges).toEqual([true, false]);
    manager.stop();
  });

  it('never manages cloud models through Ollama', async () => {
    const load = vi.fn(async () => {});
    const unload = vi.fn(async () => {});
    const manager = new SmartPerformanceManager({ load, unload, idleMs: 1 });

    await manager.warm('gpt-5');
    await manager.beginUse('claude-sonnet');
    manager.activity('gemini-2.5-pro');
    manager.endUse('claude-sonnet');
    await vi.runAllTimersAsync();

    expect(load).not.toHaveBeenCalled();
    expect(unload).not.toHaveBeenCalled();
  });
});
