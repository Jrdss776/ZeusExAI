import { afterEach, describe, expect, it, vi } from 'vitest';
import { isLocalModel, preloadModel, unloadModel } from './api';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('Ollama model lifecycle', () => {
  it('preserves the exact Qwen 9B tag while loading and unloading', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal('fetch', fetchMock);

    await preloadModel('qwen3.5:9b');
    await unloadModel('qwen3.5:9b');

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      model: 'qwen3.5:9b',
      prompt: '',
      keep_alive: '5m',
    });
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
      model: 'qwen3.5:9b',
      prompt: '',
      keep_alive: 0,
    });
  });

  it('does not send cloud models to the local Ollama lifecycle', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    expect(isLocalModel('qwen3.5:9b')).toBe(true);
    expect(isLocalModel('gpt-5')).toBe(false);
    await preloadModel('gpt-5');
    await unloadModel('claude-sonnet');

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
