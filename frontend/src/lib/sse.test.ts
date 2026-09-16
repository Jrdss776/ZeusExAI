import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('./api', () => ({
  getBase: () => 'http://127.0.0.1:8000',
  authHeaders: (headers: Record<string, string>) => headers,
}));

import { streamChat } from './sse';

describe('streamChat', () => {
  afterEach(() => vi.restoreAllMocks());

  it.each([false, true])('preserves event names across network chunks (CRLF: %s)', async (crlf) => {
    const newline = crlf ? '\r\n' : '\n';
    const payload = `event: tool_call_start${newline}data: {"tool":"search"}${newline}${newline}`
      + `event: tool_call_end${newline}data: {"tool":"search","success":true}${newline}${newline}`
      + `data: {"choices":[{"delta":{"content":"Olá"}}]}${newline}${newline}`
      + `data: [DONE]${newline}${newline}`;
    const bytes = new TextEncoder().encode(payload);
    const expected = [
      { event: 'tool_call_start', data: '{"tool":"search"}' },
      { event: 'tool_call_end', data: '{"tool":"search","success":true}' },
      { event: undefined, data: '{"choices":[{"delta":{"content":"Olá"}}]}' },
    ];
    const fetchMock = vi.spyOn(globalThis, 'fetch');
    // Exercise every possible two-chunk split, including inside UTF-8 text.
    for (let split = 1; split < bytes.length; split++) {
      fetchMock.mockResolvedValueOnce(new Response(new ReadableStream({
        start(controller) {
          controller.enqueue(bytes.slice(0, split));
          controller.enqueue(bytes.slice(split));
          controller.close();
        },
      })));
      const events = [];
      for await (const event of streamChat({ model: 'test', messages: [], stream: true })) {
        events.push(event);
      }
      expect(events, `split at byte ${split}`).toEqual(expected);
    }
  });

  it('requests true direct streaming for the desktop James prompt', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('data: [DONE]\n\n', {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    );

    for await (const _event of streamChat({
      model: 'qwen2.5:3b',
      messages: [{ role: 'user', content: 'Olá' }],
      stream: true,
    })) {
      // The DONE marker ends the stream without yielding a data event.
    }

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/v1/chat/completions',
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-OpenJarvis-Direct-Stream': '1',
        }),
      }),
    );
  });

  it('routes capability requests through the agent instead of direct streaming', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('data: [DONE]\n\n', {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    );

    for await (const _event of streamChat(
      {
        model: 'qwen2.5:3b',
        messages: [{ role: 'user', content: 'Organize a pasta Downloads' }],
        stream: true,
      },
      undefined,
      { directStream: false },
    )) {
      // DONE
    }

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/v1/chat/completions',
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-OpenJarvis-Direct-Stream': '0',
          'X-OpenJarvis-Chat-Mode': 'agent',
        }),
      }),
    );
  });
});
