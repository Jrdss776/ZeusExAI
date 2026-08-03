import { useRef, useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { MessageBubble } from './MessageBubble';
import { InputArea } from './InputArea';
import { StreamingDots } from './StreamingDots';
import { JamesVoiceControl } from './JamesVoiceControl';
import { useAppStore } from '../../lib/store';
import { Brain, PanelRightOpen, PanelRightClose, Database, MessageSquare, X } from 'lucide-react';
import { listConnectors } from '../../lib/connectors-api';

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Bom dia, senhor';
  if (hour < 18) return 'Boa tarde, senhor';
  return 'Boa noite, senhor';
}

const COMMERCIAL_CHAT_STARTERS = [
  {
    label: 'Analisar produto',
    prompt: 'Faça uma Análise 360 deste produto. Vou enviar o link ou os dados a seguir: ',
  },
  {
    label: 'Criar anúncio',
    prompt: 'Crie um anúncio otimizado para Shopee e Mercado Livre deste produto: ',
  },
  {
    label: 'Estratégia de vendas',
    prompt: 'Monte uma estratégia de vendas completa para este produto: ',
  },
  {
    label: 'Roteiro de vídeo',
    prompt: 'Crie um roteiro de venda para este produto, usando apenas os dados fornecidos: ',
  },
] as const;

export function ChatArea() {
  const messages = useAppStore((s) => s.messages);
  const streamState = useAppStore((s) => s.streamState);
  const systemPanelOpen = useAppStore((s) => s.systemPanelOpen);
  const toggleSystemPanel = useAppStore((s) => s.toggleSystemPanel);
  const navigate = useNavigate();
  const listRef = useRef<HTMLDivElement>(null);
  const shouldAutoScroll = useRef(true);
  const lastSpokenRef = useRef(messages.at(-1)?.id ?? '');

  // Check if any data sources are connected
  const [hasConnectedSources, setHasConnectedSources] = useState<boolean | null>(null);
  const [bannerDismissed, setBannerDismissed] = useState(false);

  useEffect(() => {
    listConnectors()
      .then((list) => setHasConnectedSources(list.some((c) => c.connected)))
      .catch(() => setHasConnectedSources(null));
  }, []);

  useEffect(() => {
    if (shouldAutoScroll.current && listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, streamState.content]);

  useEffect(() => {
    if (streamState.isStreaming) return;
    const last = messages.at(-1);
    if (!last || last.role !== 'assistant' || !last.content || last.id === lastSpokenRef.current) return;
    lastSpokenRef.current = last.id;
    window.dispatchEvent(new CustomEvent('zeusex-speak', { detail: last.content }));
  }, [messages, streamState.isStreaming]);

  const handleScroll = () => {
    if (!listRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = listRef.current;
    shouldAutoScroll.current = scrollHeight - scrollTop - clientHeight < 100;
  };

  const isEmpty = messages.length === 0 && !streamState.isStreaming;

  const PanelIcon = systemPanelOpen ? PanelRightClose : PanelRightOpen;

  return (
    <div className="flex flex-col h-full">
      {/* Toggle bar */}
      <div className="flex items-center justify-end gap-1 px-3 py-1.5 shrink-0">
        <JamesVoiceControl paused={streamState.isStreaming} />
        <button
          type="button"
          onClick={() => window.dispatchEvent(new CustomEvent('zeusex-toggle-brain'))}
          className="inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs transition-colors cursor-pointer"
          style={{ color: 'var(--color-accent)', border: '1px solid var(--color-border)' }}
          title="Abrir Second Brain"
        >
          <Brain size={15} />
          Second Brain
        </button>
        <button
          onClick={toggleSystemPanel}
          className="p-1.5 rounded-md transition-colors cursor-pointer"
          style={{ color: 'var(--color-text-tertiary)' }}
          title={`${systemPanelOpen ? 'Hide' : 'Show'} system panel (${navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'}+I)`}
        >
          <PanelIcon size={16} />
        </button>
      </div>

      {/* Data sources banner */}
      {hasConnectedSources === false && !bannerDismissed && (
        <div
          className="mx-4 mb-2 flex items-center gap-3 px-4 py-3 rounded-lg text-sm shrink-0"
          style={{
            background: 'var(--color-accent-subtle)',
            border: '1px solid var(--color-border)',
          }}
        >
          <Database size={16} style={{ color: 'var(--color-accent)', flexShrink: 0 }} />
          <span style={{ color: 'var(--color-text-secondary)', flex: 1 }}>
            Conecte suas fontes de dados para receber respostas ainda mais personalizadas.
          </span>
          <button
            onClick={() => navigate('/data-sources')}
            className="px-3 py-1 rounded text-xs font-medium cursor-pointer"
            style={{ background: 'var(--color-accent)', color: 'var(--color-on-accent)', border: 'none' }}
          >
            Connect
          </button>
          <button
            onClick={() => setBannerDismissed(true)}
            className="p-1 rounded cursor-pointer"
            style={{ color: 'var(--color-text-tertiary)', background: 'transparent', border: 'none' }}
          >
            <X size={14} />
          </button>
        </div>
      )}
      <div
        ref={listRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto"
      >
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full px-4">
            <div className="james-orb mb-5" aria-label="James online">
              <span className="james-orb-core" />
              <span className="james-orb-ring" />
            </div>
            <p className="hud-label mb-2 tracking-[0.28em]" style={{ color: 'var(--color-accent)' }}>
              JAMES // ONLINE
            </p>
            <h2 className="text-xl font-semibold mb-2" style={{ color: 'var(--color-text)' }}>
              {getGreeting()}
            </h2>
            <p className="text-sm text-center max-w-sm mb-6" style={{ color: 'var(--color-text-secondary)' }}>
              Converse comigo sobre sua vida, seus projetos ou vendas. Análises, anúncios e estratégias agora começam diretamente no chat.
            </p>

            <div className="mb-6 flex max-w-2xl flex-wrap justify-center gap-2">
              {COMMERCIAL_CHAT_STARTERS.map((starter) => (
                <button
                  key={starter.label}
                  type="button"
                  onClick={() =>
                    window.dispatchEvent(
                      new CustomEvent('zeusex-fill-chat', { detail: starter.prompt }),
                    )
                  }
                  className="rounded-full px-3 py-2 text-xs transition-colors cursor-pointer"
                  style={{
                    background: 'var(--color-accent-subtle)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-text-secondary)',
                  }}
                  onMouseEnter={(event) => {
                    event.currentTarget.style.borderColor = 'var(--color-accent)';
                  }}
                  onMouseLeave={(event) => {
                    event.currentTarget.style.borderColor = 'var(--color-border)';
                  }}
                >
                  {starter.label}
                </button>
              ))}
            </div>

            {/* Quick action hints */}
            <div className="flex gap-3">
              <button
                onClick={() => navigate('/data-sources')}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs cursor-pointer transition-colors"
                style={{
                  background: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text-secondary)',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--color-accent)')}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--color-border)')}
              >
                <Database size={14} style={{ color: 'var(--color-accent)' }} />
                Conectar fontes de dados
              </button>
              <button
                onClick={() => { navigate('/data-sources'); setTimeout(() => window.dispatchEvent(new CustomEvent('switch-tab', { detail: 'messaging' })), 100); }}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs cursor-pointer transition-colors"
                style={{
                  background: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text-secondary)',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--color-accent)')}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--color-border)')}
              >
                <MessageSquare size={14} style={{ color: 'var(--color-accent)' }} />
                Configurar mensagens
              </button>
            </div>
          </div>
        ) : (
          <div className="max-w-[var(--chat-max-width)] mx-auto px-4 py-6">
            {messages.map((msg, i) => {
              const isLastAssistant =
                i === messages.length - 1 && msg.role === 'assistant';
              return (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  isLive={isLastAssistant && streamState.isStreaming}
                />
              );
            })}
            {(() => {
              if (!streamState.isStreaming || streamState.content !== '') return null;
              // For research messages the ResearchTimeline handles its own
              // pre-content loading state — suppress the generic dots.
              const last = messages[messages.length - 1];
              if (last?.role === 'assistant' && last.isResearch) return null;
              return (
                <div className="flex justify-start mb-4">
                  <StreamingDots phase={streamState.phase} />
                </div>
              );
            })()}
          </div>
        )}
      </div>
      <InputArea />
    </div>
  );
}
