import { describe, expect, it, vi } from 'vitest';

import {
  COMMERCIAL_COMMAND_KEY,
  consumeCommercialCommand,
} from './InputArea';

describe('handoff da Central Comercial para o chat', () => {
  it('consome uma única vez o comando preparado', () => {
    const storage = {
      getItem: vi.fn(() => '  Analise este produto  '),
      removeItem: vi.fn(),
    };

    expect(consumeCommercialCommand(storage)).toBe('Analise este produto');
    expect(storage.getItem).toHaveBeenCalledWith(COMMERCIAL_COMMAND_KEY);
    expect(storage.removeItem).toHaveBeenCalledWith(COMMERCIAL_COMMAND_KEY);
  });

  it('não remove nada quando não existe comando preparado', () => {
    const storage = {
      getItem: vi.fn(() => null),
      removeItem: vi.fn(),
    };

    expect(consumeCommercialCommand(storage)).toBe('');
    expect(storage.removeItem).not.toHaveBeenCalled();
  });
});
