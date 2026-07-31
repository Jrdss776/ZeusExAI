import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

class MemoryStorage {
  private store = new Map<string, string>();
  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }
  setItem(key: string, value: string): void {
    this.store.set(key, value);
  }
}

const dossier = {
  subject: 'https://example.com/produto',
  sources: [{ url: 'https://example.com/produto', title: 'Produto', retrieved_at: '' }],
  claims: [{ field: 'product.name', value: 'Produto', source_urls: ['https://example.com/produto'] }],
  missing_fields: ['product.sales'],
  warnings: [],
  collector_model: 'modelo-coletor',
};

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'test-anon-key');
  (globalThis as unknown as { localStorage: MemoryStorage }).localStorage = new MemoryStorage();
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe('fluxo comercial em duas etapas', () => {
  it('coleta a ficha sem executar os especialistas', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => dossier });
    vi.stubGlobal('fetch', fetchMock);
    const { collectCommercialEvidence } = await import('./api');

    const result = await collectCommercialEvidence(dossier.subject);

    expect(result).toEqual(dossier);
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0][0]).toBe('/v1/commercial/collect');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ subject: dossier.subject });
  });

  it('envia aos especialistas exatamente a ficha aprovada', async () => {
    const response = { action: 'analysis', status: 'completed', dossier, outputs: [], errors: [], blocked_reason: '' };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => response });
    vi.stubGlobal('fetch', fetchMock);
    const { runCommercialPipeline } = await import('./api');

    await runCommercialPipeline('analysis', dossier);

    expect(fetchMock.mock.calls[0][0]).toBe('/v1/commercial/orchestrate');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      action: 'analysis',
      dossier,
    });
  });
});
