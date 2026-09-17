import { describe, expect, it } from 'vitest';
import { toDisplayText } from './message-content';

describe('toDisplayText', () => {
  it('keeps plain text unchanged', () => {
    expect(toDisplayText('Olá, Jair')).toBe('Olá, Jair');
  });

  it('formats query result objects instead of passing them to React', () => {
    const text = toDisplayText({ query_results: [{ title: 'Novo e-mail', important: true }] });

    expect(text).toContain('Resultados da consulta');
    expect(text).toContain('Novo e-mail');
    expect(text).toContain('```json');
  });

  it('extracts common text fields from structured responses', () => {
    expect(toDisplayText({ answer: 'Compromisso confirmado' })).toBe('Compromisso confirmado');
  });

  it('handles arrays and empty values safely', () => {
    expect(toDisplayText(['um', 'dois'])).toBe('um\ndois');
    expect(toDisplayText(null)).toBe('');
  });
});
