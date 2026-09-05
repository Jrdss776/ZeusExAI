import { beforeEach, describe, expect, it, vi } from 'vitest';
import { consumeChatDraft, saveChatDraft } from './chatDraft';

const values = new Map<string, string>();
const storage = {
  getItem: vi.fn((key: string) => values.get(key) ?? null),
  setItem: vi.fn((key: string, value: string) => values.set(key, value)),
  removeItem: vi.fn((key: string) => values.delete(key)),
};

Object.defineProperty(globalThis, 'sessionStorage', { value: storage, configurable: true });

describe('rascunho de atalhos para o chat', () => {
  beforeEach(() => {
    values.clear();
    vi.clearAllMocks();
  });

  it('salva texto limpo e o entrega apenas uma vez', () => {
    saveChatDraft('  Mostre minha agenda.  ');

    expect(consumeChatDraft()).toBe('Mostre minha agenda.');
    expect(consumeChatDraft()).toBe('');
  });

  it('ignora um rascunho vazio', () => {
    saveChatDraft('   ');

    expect(storage.setItem).not.toHaveBeenCalled();
  });
});
