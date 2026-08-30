import type { ChatMessage, Conversation } from '../types';

export type JamesSkill = {
  id: string;
  name: string;
  description: string;
  triggers: string[];
  instructions: string[];
  requiresConfirmation?: boolean;
};

export type MemoryCandidate = {
  id: string;
  area: 'meta' | 'metas' | 'trabalho' | 'projetos' | 'financas' | 'aprendizado' | 'saude' | 'relacoes';
  title: string;
  body: string;
  sourceMessageId: string;
  createdAt: number;
};

export type CompactConversation = {
  messages: Array<{ role: ChatMessage['role']; content: string }>;
  summary: string;
  compacted: boolean;
};

export const JAMES_SKILLS: JamesSkill[] = [
  {
    id: 'memory-recall',
    name: 'Memória e continuidade',
    description: 'Recupera decisões, preferências e conversas anteriores sem inventar lembranças.',
    triggers: ['lembra', 'lembrar', 'memoria', 'conversamos', 'falamos', 'decidimos', 'antes', 'historico'],
    instructions: [
      'Use apenas as memórias e o histórico fornecidos no contexto.',
      'Se a lembrança não estiver disponível, diga isso claramente e peça uma pista curta.',
      'Diferencie uma memória confirmada de uma inferência feita agora.',
    ],
  },
  {
    id: 'safe-action',
    name: 'Ação segura',
    description: 'Cria prévias e exige confirmação antes de ações externas ou destrutivas.',
    triggers: [
      'enviar', 'envie', 'publicar', 'publique', 'apagar', 'apague', 'excluir', 'exclua',
      'comprar', 'compre', 'instalar', 'instale', 'executar', 'execute', 'agendar', 'agende',
      'cancelar', 'cancele', 'alterar', 'altere',
    ],
    requiresConfirmation: true,
    instructions: [
      'Antes de uma ação externa, destrutiva, financeira ou irreversível, apresente uma prévia objetiva.',
      'Não afirme que executou a ação enquanto não houver confirmação explícita e recibo de execução.',
      'Uma confirmação vale somente para a ação e os parâmetros mostrados na prévia.',
    ],
  },
  {
    id: 'technical-diagnosis',
    name: 'Diagnóstico técnico',
    description: 'Investiga causa, evidência e validação antes de propor mudanças.',
    triggers: ['erro', 'bug', 'falha', 'travando', 'nao funciona', 'codigo', 'programacao', 'github', 'zeusexai', 'james'],
    instructions: [
      'Separe sintoma, causa provável, evidência e correção recomendada.',
      'Não trate hipótese como diagnóstico confirmado.',
      'Ao sugerir mudança de código, inclua como validar e como desfazer com segurança.',
    ],
  },
  {
    id: 'planning',
    name: 'Planejamento prático',
    description: 'Transforma objetivos amplos em próximos passos verificáveis.',
    triggers: ['plano', 'planejar', 'projeto', 'objetivo', 'meta', 'passos', 'melhorias', 'implementar', 'fazer'],
    instructions: [
      'Converta o objetivo em etapas pequenas, ordenadas e verificáveis.',
      'Indique dependências, riscos e o próximo passo concreto.',
      'Mantenha o plano proporcional ao pedido; não crie burocracia desnecessária.',
    ],
  },
  {
    id: 'marketplace',
    name: 'Marketplace e vendas',
    description: 'Analisa Shopee, Mercado Livre, preço, custo e margem sem inventar números.',
    triggers: ['shopee', 'mercado livre', 'venda', 'anuncio', 'produto', 'preco', 'margem', 'frete'],
    instructions: [
      'Separe preço, taxas, frete, impostos, custo do produto e margem.',
      'Sinalize todo valor estimado e peça os dados ausentes antes de concluir rentabilidade.',
      'Não invente vendas, avaliações, concorrentes ou preços atuais.',
    ],
  },
];

export function normalizeJamesText(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function selectJamesSkills(input: string, maxSkills = 3): JamesSkill[] {
  const normalized = normalizeJamesText(input);
  if (!normalized) return [];

  return JAMES_SKILLS
    .map((skill) => ({
      skill,
      score: skill.triggers.reduce(
        (total, trigger) => total + (normalized.includes(normalizeJamesText(trigger)) ? 1 : 0),
        0,
      ),
    }))
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score || a.skill.name.localeCompare(b.skill.name))
    .slice(0, Math.max(0, maxSkills))
    .map(({ skill }) => skill);
}

export function formatJamesSkills(skills: JamesSkill[]): string {
  if (skills.length === 0) return '';
  return skills
    .map((skill) => [
      `HABILIDADE ATIVA — ${skill.name}:`,
      ...skill.instructions.map((instruction) => `- ${instruction}`),
    ].join('\n'))
    .join('\n\n');
}

function clip(value: string, maxChars: number): string {
  const clean = value.replace(/\s+/g, ' ').trim();
  return clean.length <= maxChars ? clean : `${clean.slice(0, Math.max(0, maxChars - 1)).trimEnd()}…`;
}

export function compactJamesConversation(
  input: ChatMessage[],
  options: { maxMessages?: number; maxChars?: number; maxSummaryChars?: number } = {},
): CompactConversation {
  const maxMessages = Math.max(4, options.maxMessages ?? 18);
  const maxChars = Math.max(2_000, options.maxChars ?? 14_000);
  const maxSummaryChars = Math.max(500, options.maxSummaryChars ?? 3_000);
  const totalChars = input.reduce((total, message) => total + message.content.length, 0);

  if (input.length <= maxMessages && totalChars <= maxChars) {
    return {
      messages: input.map(({ role, content }) => ({ role, content })),
      summary: '',
      compacted: false,
    };
  }

  const recent = input.slice(-maxMessages);
  const older = input.slice(0, -maxMessages);
  const latest = recent[recent.length - 1];
  const previous = recent.slice(0, -1);
  const previousBudget = Math.max(0, maxChars - (latest?.content.length ?? 0));
  const perMessageBudget = Math.max(500, Math.floor(previousBudget / Math.max(1, previous.length)));
  const messages = [
    ...previous.map(({ role, content }) => ({
      role,
      content: clip(content, perMessageBudget),
    })),
    ...(latest ? [{ role: latest.role, content: latest.content }] : []),
  ];

  const summaryLines = older
    .slice(-12)
    .map((message) => `${message.role === 'user' ? 'Senhor' : 'James'}: ${clip(message.content, 240)}`);
  const omitted = Math.max(0, older.length - summaryLines.length);
  const prefix = omitted > 0 ? `[${omitted} mensagens anteriores omitidas]\n` : '';

  return {
    messages,
    summary: clip(`${prefix}${summaryLines.join('\n')}`, maxSummaryChars),
    compacted: true,
  };
}

export function rankConversations(conversations: Conversation[], query: string): Array<{
  conversation: Conversation;
  snippet: string;
}> {
  const normalizedQuery = normalizeJamesText(query);
  if (!normalizedQuery) {
    return conversations.map((conversation) => ({ conversation, snippet: '' }));
  }
  const terms = normalizedQuery.split(' ').filter(Boolean);

  return conversations
    .map((conversation) => {
      const normalizedTitle = normalizeJamesText(conversation.title);
      const messageText = conversation.messages.map((message) => message.content).join(' ');
      const normalizedMessages = normalizeJamesText(messageText);
      if (!terms.every((term) => normalizedTitle.includes(term) || normalizedMessages.includes(term))) {
        return null;
      }

      let score = normalizedTitle.includes(normalizedQuery) ? 12 : 0;
      if (normalizedMessages.includes(normalizedQuery)) score += 6;
      for (const term of terms) {
        if (normalizedTitle.includes(term)) score += 3;
        if (normalizedMessages.includes(term)) score += 1;
      }

      const matchingMessage = conversation.messages.find((message) => {
        const normalized = normalizeJamesText(message.content);
        return terms.some((term) => normalized.includes(term));
      });
      return {
        conversation,
        snippet: matchingMessage ? clip(matchingMessage.content, 96) : '',
        score,
      };
    })
    .filter((item): item is { conversation: Conversation; snippet: string; score: number } => item !== null)
    .sort((a, b) => b.score - a.score || b.conversation.updatedAt - a.conversation.updatedAt)
    .map(({ conversation, snippet }) => ({ conversation, snippet }));
}

export function proposeJamesMemory(content: string, sourceMessageId: string): MemoryCandidate | null {
  const clean = content.replace(/\s+/g, ' ').trim();
  if (clean.length < 8 || clean.length > 500) return null;
  const normalized = normalizeJamesText(clean);

  const explicit = clean.match(
    /^(?:james[, ]+)?(?:lembre|guarde|anote)(?:-se)?(?: de)?(?: que)?\s+(.+)$/iu,
  );
  const durableSignals = [
    'eu prefiro ', 'prefiro ', 'meu objetivo ', 'minha meta ', 'eu moro ', 'moro em ',
    'meu trabalho ', 'meu projeto ', 'estou estudando ', 'minha esposa ', 'meu marido ',
    'meu filho ', 'minha filha ', 'tenho alergia ', 'nao posso ', 'não posso ',
  ];
  if (!explicit && !durableSignals.some((signal) => normalized.includes(normalizeJamesText(signal)))) {
    return null;
  }

  let body = explicit?.[1]?.trim() || clean;
  body = body.charAt(0).toUpperCase() + body.slice(1);
  const area: MemoryCandidate['area'] =
    /esposa|marido|filh|familia|família/.test(normalized) ? 'relacoes'
    : /meta|objetivo/.test(normalized) ? 'metas'
    : /trabalho|emprego|carreira/.test(normalized) ? 'trabalho'
    : /projeto|app|aplicativo/.test(normalized) ? 'projetos'
    : /renda|dinheiro|finance|salario|salário/.test(normalized) ? 'financas'
    : /estud|aprend|curso/.test(normalized) ? 'aprendizado'
    : /saude|saúde|alerg|exercicio|exercício/.test(normalized) ? 'saude'
    : 'meta';

  return {
    id: `memory-${Date.now().toString(36)}-${sourceMessageId.slice(-6)}`,
    area,
    title: clip(body, 44),
    body: clip(body, 320),
    sourceMessageId,
    createdAt: Date.now(),
  };
}
