const TEXT_FIELDS = ['content', 'text', 'message', 'answer', 'result', 'output'] as const;

function jsonBlock(value: unknown): string {
  try {
    const json = JSON.stringify(value, null, 2);
    return json === undefined ? String(value) : `\`\`\`json\n${json}\n\`\`\``;
  } catch {
    return String(value);
  }
}

/**
 * Converts API and persisted message payloads into text that React can render.
 * Some tools return structured objects (for example, { query_results: [...] })
 * even though the chat message contract expects a string.
 */
export function toDisplayText(value: unknown): string {
  if (typeof value === 'string') return value;
  if (value === null || value === undefined) return '';
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') {
    return String(value);
  }

  if (Array.isArray(value)) {
    if (value.every((item) => typeof item === 'string')) return value.join('\n');
    return jsonBlock(value);
  }

  if (typeof value === 'object') {
    const record = value as Record<string, unknown>;

    if ('query_results' in record) {
      const results = record.query_results;
      const formatted = typeof results === 'string' ? results : jsonBlock(results);
      return `Resultados da consulta:\n\n${formatted}`;
    }

    for (const field of TEXT_FIELDS) {
      if (field in record && record[field] !== value) {
        const text = toDisplayText(record[field]);
        if (text) return text;
      }
    }

    return jsonBlock(value);
  }

  return String(value);
}
