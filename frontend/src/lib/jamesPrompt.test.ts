import { describe, expect, it } from 'vitest';
import { buildJamesSystemPrompt } from './jamesPrompt';

describe('buildJamesSystemPrompt', () => {
  it('preserves James identity and injects the live context', () => {
    const prompt = buildJamesSystemPrompt('- Metas / Emprego: conseguir novo emprego');

    expect(prompt).toContain('assistente pessoal e profissional de Jair');
    expect(prompt).toContain('chame Jair de senhor');
    expect(prompt).toContain('Metas / Emprego: conseguir novo emprego');
  });

  it('guards against the interview-questionnaire misunderstanding', () => {
    const prompt = buildJamesSystemPrompt('');

    expect(prompt).toContain('objetivo real do pedido');
    expect(prompt).toContain('não significa criação de formulários de pesquisa');
    expect(prompt).toContain('faça uma única pergunta curta');
  });
});
