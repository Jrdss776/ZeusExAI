import { useNavigate } from 'react-router';
import { Activity, Bot, BrainCircuit, Gauge, MessageSquare, Mic, Search, Send, ShieldCheck, Sparkles, Users, Zap } from 'lucide-react';
import { saveChatDraft } from '../lib/chatDraft';
import { useAppStore } from '../lib/store';

const capabilities = [
  { icon: BrainCircuit, label: 'Memória', detail: 'Contexto local e privado' },
  { icon: ShieldCheck, label: 'Governança', detail: 'Ações sob seu controle' },
  { icon: Gauge, label: 'Desempenho', detail: 'Modelo executado no dispositivo' },
];

const shortcuts = [
  { icon: Mic, label: 'Microfone', detail: 'Ditado e conversa por voz', action: 'voice' },
  { icon: BrainCircuit, label: 'Segundo Cérebro', detail: 'Memória e informações pessoais', action: 'memory' },
  { icon: Search, label: 'Pesquisa Profunda', detail: 'Investigue fontes conectadas', action: 'research' },
  { icon: Users, label: 'Agentes', detail: 'Automatizações especializadas', action: 'agents' },
] as const;

export function DashboardPage() {
  const navigate = useNavigate();
  const selectedModel = useAppStore((state) => state.selectedModel);
  const modelLoading = useAppStore((state) => state.modelLoading);
  const serverInfo = useAppStore((state) => state.serverInfo);
  const savings = useAppStore((state) => state.savings);
  const liveEnergy = useAppStore((state) => state.liveEnergy);
  const setDeepResearch = useAppStore((state) => state.setDeepResearch);

  const openTelegram = () => {
    navigate('/data-sources?tab=messaging');
  };

  const openShortcut = (action: typeof shortcuts[number]['action']) => {
    if (action === 'memory') return navigate('/data-sources?tab=memory');
    if (action === 'agents') return navigate('/agents');
    if (action === 'research') {
      setDeepResearch(true);
      saveChatDraft('Quero iniciar uma pesquisa profunda sobre: ');
    }
    navigate('/');
  };

  return (
    <div className="relative h-full overflow-y-auto">
      <div className="hud-backdrop" aria-hidden="true" />
      <main className="relative z-10 mx-auto flex w-full max-w-6xl flex-col gap-5 p-5 md:p-8">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div><p className="hud-label">ASSISTENTE DIGITAL</p><h1 className="mt-1 text-3xl font-semibold tracking-tight">Gambit</h1></div>
          <div className="flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)]">
            <span className={`h-2 w-2 rounded-full ${modelLoading || !serverInfo ? 'bg-[var(--color-warning)]' : 'bg-[var(--color-success)]'}`} />
            {modelLoading ? 'Carregando modelo' : serverInfo ? 'Sistema disponível' : 'Aguardando conexão'}
          </div>
        </header>

        <section className="hud-panel overflow-hidden p-5 md:p-8">
          <div className="grid items-center gap-7 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="order-2 lg:order-1">
              <span className="inline-flex items-center gap-2 rounded-full bg-[var(--color-accent-subtle)] px-3 py-1.5 text-xs text-[var(--color-accent)]"><Sparkles size={14} /> IA local e pessoal</span>
              <h2 className="mt-5 text-2xl font-semibold md:text-4xl">Como posso ajudar você hoje?</h2>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--color-text-secondary)] md:text-base">Converse, organize informações e acompanhe o funcionamento do seu assistente em um único lugar.</p>
            </div>

            <div className="order-1 flex min-h-48 items-center justify-center lg:order-2 lg:min-h-56" aria-label="Representação visual do Gambit">
              <div className="james-avatar-stage">
                <div className="james-avatar-ring james-avatar-ring-outer" /><div className="james-avatar-ring james-avatar-ring-inner" />
                <div className="james-avatar-core" aria-hidden="true"><div className="james-face"><span className="james-antenna" /><span className="james-eye" /><span className="james-eye" /></div></div><div className="james-avatar-base" />
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-3 md:grid-cols-[2fr_1fr]">
          <button type="button" onClick={() => navigate('/')} className="hud-panel group flex min-h-32 items-center gap-5 p-6 text-left hover:border-[var(--color-accent)]">
            <span className="rounded-2xl bg-[var(--color-accent)] p-4 text-[var(--color-on-accent)]"><MessageSquare size={28} /></span>
            <span className="min-w-0 flex-1"><span className="block text-xl font-semibold">Chat com Gambit</span><span className="mt-1 block text-sm text-[var(--color-text-secondary)]">Abra uma conversa maior para perguntar, planejar ou pesquisar.</span></span>
            <span className="text-[var(--color-accent)] transition group-hover:translate-x-1">→</span>
          </button>
          <button type="button" onClick={openTelegram} className="hud-panel group flex min-h-32 items-center gap-4 p-6 text-left hover:border-[#2aabee]">
            <span className="rounded-2xl bg-[#2aabee]/15 p-4 text-[#2aabee]"><Send size={26} /></span>
            <span><span className="block font-semibold">Telegram</span><span className="mt-1 block text-sm text-[var(--color-text-secondary)]">Conectar ou conversar pelo celular</span></span>
          </button>
        </section>

        <section>
          <div className="mb-3"><p className="hud-label">ATALHOS</p><h2 className="mt-1 text-lg font-semibold">Acesso rápido</h2></div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {shortcuts.map(({ icon: Icon, label, detail, action }) => (
              <button key={label} type="button" onClick={() => openShortcut(action)} className="hud-panel flex items-center gap-4 p-4 text-left hover:border-[var(--color-accent)]">
                <span className="rounded-xl bg-[var(--color-accent-subtle)] p-2.5 text-[var(--color-accent)]"><Icon size={20} /></span>
                <span><span className="block text-sm font-semibold">{label}</span><span className="mt-0.5 block text-xs text-[var(--color-text-secondary)]">{detail}</span></span>
              </button>
            ))}
          </div>
        </section>

        <section className="grid gap-3 md:grid-cols-3">
          {capabilities.map(({ icon: Icon, label, detail }) => (
            <article key={label} className="hud-panel p-5"><Icon size={20} className="text-[var(--color-accent)]" /><h3 className="mt-4 font-semibold">{label}</h3><p className="mt-1 text-sm text-[var(--color-text-secondary)]">{detail}</p></article>
          ))}
        </section>
        <section className="grid gap-3 sm:grid-cols-3">
          <StatusCard icon={BrainCircuit} label="Modelo ativo" value={selectedModel || 'Não selecionado'} />
          <StatusCard icon={Activity} label="Conversas processadas" value={String(savings?.total_calls ?? 0)} />
          <StatusCard icon={Zap} label="Consumo atual" value={`${(liveEnergy?.power_w ?? 0).toFixed(1)} W`} />
        </section>
      </main>
    </div>
  );
}

function StatusCard({ icon: Icon, label, value }: { icon: typeof Bot; label: string; value: string }) {
  return <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-4"><div className="flex items-center gap-2 text-xs text-[var(--color-text-tertiary)]"><Icon size={14} className="text-[var(--color-accent)]" /> {label}</div><p className="mt-2 truncate text-sm font-semibold" title={value}>{value}</p></div>;
}
