import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe('governance API', () => {
  it('uses only the four read-only governance endpoints', async () => {
    const fetchMock = vi.fn(async (input: string, _init?: RequestInit) => {
      const leaf = input.endsWith('/status') ? { mode: 'read_only' } :
        input.includes('/history?') ? { history: { read_only: true } } :
          { overview: { read_only: true } };
      return { ok: true, json: async () => ({ ok: true, ...leaf }) } as Response;
    });
    vi.stubGlobal('fetch', fetchMock);
    const api = await import('./api');

    await Promise.all([
      api.fetchGovernanceStatus(), api.fetchGovernanceOverview(25),
      api.fetchGovernanceHistoryStatus(), api.fetchGovernanceHistory(7, 100),
    ]);

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      '/v1/agent/governance/status',
      '/v1/agent/governance/overview?limit=25',
      '/v1/agent/governance/history/status',
      '/v1/agent/governance/history?days=7&limit=100',
    ]);
    expect(fetchMock.mock.calls.every(([, init]) => !init?.method || init.method === 'GET')).toBe(true);
  });

  it('surfaces the service error message', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 503, json: async () => ({ error: 'Painel não configurado.' }) })));
    const { fetchGovernanceStatus } = await import('./api');
    await expect(fetchGovernanceStatus()).rejects.toThrow('Painel não configurado.');
  });
});
