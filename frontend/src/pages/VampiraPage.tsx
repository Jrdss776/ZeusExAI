import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { CalendarDays, CloudSun, Database, Mail, MessageSquare, MoonStar, RefreshCw } from 'lucide-react';
import { listConnectors } from '../lib/connectors-api';
import { saveChatDraft } from '../lib/chatDraft';
import type { ConnectorInfo } from '../types/connectors';

type ServiceId = 'weather' | 'gcalendar' | 'gmail';

const services: Array<{
  id: ServiceId;
  title: string;
  description: string;
  icon: typeof CloudSun;
  prompt: string;
  aliases: string[];
}> = [
  { id: 'weather', title: 'Previsão do tempo', description: 'Consulte as condições e a previsão para sua cidade.', icon: CloudSun, prompt: 'Qual é a previsão do tempo para hoje na minha cidade?', aliases: ['weather'] },
  { id: 'gcalendar', title: 'Agenda', description: 'Veja compromissos, horários e prioridades do dia.', icon: CalendarDays, prompt: 'Mostre os compromissos da minha agenda para hoje.', aliases: ['gcalendar', 'google_calendar'] },
  { id: 'gmail', title: 'E-mail', description: 'Resuma mensagens importantes e itens que precisam de resposta.', icon: Mail, prompt: 'Quais e-mails importantes precisam da minha atenção hoje?', aliases: ['gmail', 'gmail_imap', 'gmail_api'] },
];

export function VampiraPage() {
  const navigate = useNavigate();
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);

  const loadConnections = () => {
    setLoading(true);
    setLoadFailed(false);
    listConnectors()
      .then(setConnectors)
      .catch(() => setLoadFailed(true))
      .finally(() => setLoading(false));
  };

  useEffect(loadConnections, []);

  const connectedIds = useMemo(
    () => new Set(connectors.filter((item) => item.connected).map((item) => item.connector_id)),
    [connectors],
  );

  const openChat = (prompt?: string) => {
    if (prompt) saveChatDraft(prompt);
    navigate('/');
  };

  return (
    <div className="relative h-full overflow-y-auto">
      <div className="hud-backdrop" aria-hidden="true" />
      <main className="relative z-10 mx-auto flex w-full max-w-6xl flex-col gap-5 p-5 md:p-8">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div><p className="hud-label">ASSISTENTE DE PRODUTIVIDADE</p><h1 className="mt-1 text-3xl font-semibold tracking-tight">Vampira</h1></div>
          <button type="button" onClick={loadConnections} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-[var(--color-border)] px-3 py-2 text-xs text-[var(--color-text-secondary)] disabled:opacity-50">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Atualizar conexões
          </button>
        </header>

        <section className="hud-panel overflow-hidden p-6 md:p-8">
          <div className="grid items-center gap-7 lg:grid-cols-[1fr_0.8fr]">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full bg-[var(--color-accent-purple-subtle)] px-3 py-1.5 text-xs text-[var(--color-accent-purple)]"><MoonStar size={14} /> Sua rotina em um só lugar</span>
              <h2 className="mt-5 text-2xl font-semibold md:text-4xl">Bom dia. O que vamos organizar?</h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--color-text-secondary)] md:text-base">Clima, agenda, e-mails e conversa reunidos em uma tela simples. Os dados continuam sob as permissões das integrações já configuradas.</p>
              <button type="button" onClick={() => openChat()} className="mt-6 inline-flex items-center gap-2 rounded-xl bg-[var(--color-accent-purple)] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[var(--color-accent-purple-hover)]">
                <MessageSquare size={17} /> Conversar com Vampira
              </button>
            </div>
            <div className="flex min-h-52 items-center justify-center" aria-label="Representação visual da Vampira">
              <div className="vampira-avatar-stage"><VampiraCircuitIcon /></div>
            </div>
          </div>
        </section>

        {loadFailed && (
          <div className="rounded-xl border border-[var(--color-warning)] bg-[var(--color-accent-amber-subtle)] p-4 text-sm text-[var(--color-text-secondary)]">Não foi possível verificar as conexões agora. Você ainda pode abrir o chat ou tentar novamente.</div>
        )}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {services.map((service) => {
            const connected = service.aliases.some((id) => connectedIds.has(id));
            const Icon = service.icon;
            return (
              <article key={service.id} className="hud-panel flex min-h-56 flex-col p-5">
                <div className="flex items-start justify-between gap-3"><span className="rounded-xl bg-[var(--color-accent-subtle)] p-2.5 text-[var(--color-accent)]"><Icon size={21} /></span><ConnectionBadge loading={loading} failed={loadFailed} connected={connected} /></div>
                <h2 className="mt-5 font-semibold">{service.title}</h2>
                <p className="mt-2 flex-1 text-sm leading-6 text-[var(--color-text-secondary)]">{service.description}</p>
                <button type="button" onClick={() => connected ? openChat(service.prompt) : navigate('/data-sources')} className="mt-5 inline-flex items-center justify-center gap-2 rounded-lg border border-[var(--color-border)] px-3 py-2.5 text-sm font-medium transition hover:border-[var(--color-accent)]">
                  {connected ? <MessageSquare size={15} /> : <Database size={15} />}{connected ? 'Consultar no chat' : 'Conectar'}
                </button>
              </article>
            );
          })}

          <article className="hud-panel flex min-h-56 flex-col p-5">
            <span className="w-fit rounded-xl bg-[var(--color-accent-purple-subtle)] p-2.5 text-[var(--color-accent-purple)]"><MessageSquare size={21} /></span>
            <h2 className="mt-5 font-semibold">Chat</h2><p className="mt-2 flex-1 text-sm leading-6 text-[var(--color-text-secondary)]">Peça resumos, prepare seu dia ou converse livremente.</p>
            <button type="button" onClick={() => openChat()} className="mt-5 inline-flex items-center justify-center gap-2 rounded-lg bg-[var(--color-accent-purple)] px-3 py-2.5 text-sm font-semibold text-white hover:bg-[var(--color-accent-purple-hover)]"><MessageSquare size={15} /> Abrir chat</button>
          </article>
        </section>
      </main>
    </div>
  );
}

function VampiraCircuitIcon() {
  const rays = Array.from({ length: 16 }, (_, index) => {
    const angle = (index * 360) / 16;
    return (
      <g key={angle} transform={`rotate(${angle} 110 110)`}>
        <path d="M110 48 V30 H102 V18" />
        <circle cx="102" cy="14" r="3" />
      </g>
    );
  });

  return (
    <svg className="vampira-circuit-icon" viewBox="0 0 220 220" role="img" aria-label="Circuito digital da Vampira">
      <circle className="vampira-circuit-orbit" cx="110" cy="110" r="94" />
      <g className="vampira-circuit-rays">{rays}</g>
      <circle className="vampira-circuit-center" cx="110" cy="110" r="46" />
    </svg>
  );
}

function ConnectionBadge({ loading, failed, connected }: { loading: boolean; failed: boolean; connected: boolean }) {
  const label = loading ? 'Verificando' : failed ? 'Indisponível' : connected ? 'Conectado' : 'Não conectado';
  return <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-border)] px-2.5 py-1 text-[10px] text-[var(--color-text-tertiary)]"><span className={`h-1.5 w-1.5 rounded-full ${loading || failed ? 'bg-[var(--color-warning)]' : connected ? 'bg-[var(--color-success)]' : 'bg-[var(--color-text-tertiary)]'}`} />{label}</span>;
}
