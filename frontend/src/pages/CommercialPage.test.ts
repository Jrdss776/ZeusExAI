import { describe, expect, it } from 'vitest';

import { buildCommercialCommand } from './CommercialPage';

describe('Central Comercial ZeusExAI', () => {
  it('gera um comando em português com o modo Achadinhos do JR', () => {
    const command = buildCommercialCommand(
      'Faça uma Análise 360 completa deste produto',
      'Areia biodegradável de mandioca',
    );

    expect(command).toContain('Análise 360');
    expect(command).toContain('Areia biodegradável de mandioca');
    expect(command).toContain('Achadinhos do JR');
    expect(command).toContain('Não invente vendas');
  });

  it('mantém um marcador explícito quando o produto não foi informado', () => {
    const command = buildCommercialCommand('Crie um anúncio completo', '   ');

    expect(command).toContain('[adicione as informações do produto]');
    expect(command).toContain('português do Brasil');
  });
});
