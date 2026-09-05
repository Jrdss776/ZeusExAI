const CHAT_DRAFT_KEY = 'zeusex-chat-draft';

export function saveChatDraft(prompt: string): void {
  const value = prompt.trim();
  if (value) sessionStorage.setItem(CHAT_DRAFT_KEY, value);
}

export function consumeChatDraft(): string {
  const value = sessionStorage.getItem(CHAT_DRAFT_KEY) || '';
  sessionStorage.removeItem(CHAT_DRAFT_KEY);
  return value;
}
