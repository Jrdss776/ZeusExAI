import { describe, expect, it } from 'vitest';
import type { ChatMessage, Conversation } from '../types';
import {
  compactJamesConversation,
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
