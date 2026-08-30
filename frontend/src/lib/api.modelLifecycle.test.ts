import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  getInferenceSource,
  getOllamaMemorySnapshot,
  isLocalModel,
  preloadModel,
  unloadModel,
} from './api';

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

  it('reads per-model RAM and VRAM from a configured Ollama host', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        models: [
          { name: 'qwen3.5:9b', size: 7_000, size_vram: 6_000 },
          { name: 'embedding:latest', size: 500, size_vram: 0 },
        ],
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const snapshot = await getOllamaMemorySnapshot(
      'qwen3.5:9b',
      'http://192.168.1.20:11434/v1/',
    );

    expect(fetchMock.mock.calls[0][0]).toBe('http://192.168.1.20:11434/api/ps');
    expect(snapshot).toEqual({
      modelBytes: 7_000,
      modelVramBytes: 6_000,
      totalBytes: 7_500,
      totalVramBytes: 6_000,
    });
  });

  it('does not classify a custom web inference server as Ollama', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ model: 'qwen2.5-7b-instruct', agent: null, engine: 'lmstudio' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(getInferenceSource()).resolves.toEqual({
      kind: 'custom',
      model: 'qwen2.5-7b-instruct',
      engine: 'lmstudio',
    });
  });
});
