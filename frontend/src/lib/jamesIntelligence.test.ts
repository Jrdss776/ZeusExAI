import { describe, expect, it } from 'vitest';
import type { ChatMessage, Conversation } from '../types';
import {
  compactJamesConversation,
  formatJamesSkills,
  proposeJamesMemory,
  rankConversations,
  selectJamesSkills,
} from './jamesIntelligence';

const message = (id: string, role: ChatMessage['role'], content: string): ChatMessage => ({
  id, role, content, timestamp: Number(id.replace(/\D/g, '')) || 1,
});

describe('James intelligence helpers', () => {
  it('loads only skills relevant to the current request', () => {
    const skills = selectJamesSkills('Apague o anúncio com erro no Mercado Livre');
    const ids = skills.map((skill) => skill.id);

    expect(ids).toContain('safe-action');
    expect(ids).toContain('marketplace');
    expect(ids).toContain('technical-diagnosis');
    expect(ids).not.toContain('memory-recall');
  });

  it('loads Excel knowledge only for spreadsheet requests', () => {
    const excelContext = formatJamesSkills(
      selectJamesSkills('Preciso corrigir um PROCV na minha planilha do Excel'),
    );
    const unrelatedContext = formatJamesSkills(
      selectJamesSkills('Ajude a planejar uma entrevista de emprego'),
    );

    expect(excelContext).toContain('HABILIDADE ATIVA — Excel e planilhas');
    expect(excelContext).toContain('Excel — referência operacional');
    expect(excelContext).toContain('Detecte idioma e localidade');
    expect(unrelatedContext).not.toContain('Excel — referência operacional');
  });

  it('compacts old turns while keeping the recent conversation intact', () => {
    const messages = Array.from({ length: 24 }, (_, index) =>
      message(String(index + 1), index % 2 ? 'assistant' : 'user', `mensagem ${index + 1} ${'x'.repeat(80)}`),
    );
    const result = compactJamesConversation(messages, { maxMessages: 8, maxChars: 4_000 });

    expect(result.compacted).toBe(true);
    expect(result.messages).toHaveLength(8);
    expect(result.messages[result.messages.length - 1]?.content).toContain('mensagem 24');
    expect(result.summary).toContain('mensagem 16');
  });

  it('never truncates the latest user message during compaction', () => {
    const latestContent = `pedido atual ${'z'.repeat(3_000)}`;
    const messages = [
      ...Array.from({ length: 20 }, (_, index) =>
        message(String(index + 1), index % 2 ? 'assistant' : 'user', `histórico ${index + 1} ${'x'.repeat(800)}`),
      ),
      message('21', 'user', latestContent),
    ];

    const result = compactJamesConversation(messages, { maxMessages: 8, maxChars: 4_000 });

    expect(result.compacted).toBe(true);
    expect(result.messages[result.messages.length - 1]?.role).toBe('user');
    expect(result.messages[result.messages.length - 1]?.content).toBe(latestContent);
  });

  it('searches message content as well as conversation titles', () => {
    const conversations: Conversation[] = [
      {
        id: 'one', title: 'Conversa geral', createdAt: 1, updatedAt: 2, model: 'qwen',
        messages: [message('1', 'user', 'Falamos sobre o projeto Piper')],
      },
      {
        id: 'two', title: 'Compras', createdAt: 1, updatedAt: 1, model: 'qwen',
        messages: [message('2', 'user', 'Lista do mercado')],
      },
    ];

    const matches = rankConversations(conversations, 'projeto piper');
    expect(matches.map((item) => item.conversation.id)).toEqual(['one']);
    expect(matches[0].snippet).toContain('Piper');
  });

  it('filters one-character searches instead of returning every conversation', () => {
    const conversations: Conversation[] = [
      {
        id: 'c', title: 'C', createdAt: 2, updatedAt: 2, model: 'qwen',
        messages: [message('1', 'user', 'Código nativo')],
      },
      {
        id: 'other', title: 'Relatório', createdAt: 1, updatedAt: 1, model: 'qwen',
        messages: [message('2', 'user', 'Resumo mensal')],
      },
    ];

    expect(rankConversations(conversations, 'c').map((item) => item.conversation.id)).toEqual(['c']);
  });

  it('creates a review candidate only for durable personal information', () => {
    expect(proposeJamesMemory('Minha meta é conseguir um emprego novo', 'msg-1')).toMatchObject({
      area: 'metas',
      sourceMessageId: 'msg-1',
    });
    expect(proposeJamesMemory('James, lembre que José é meu irmão', 'msg-3')?.body)
      .toBe('José é meu irmão');
    expect(proposeJamesMemory('Qual é a previsão do tempo?', 'msg-2')).toBeNull();
  });
});
