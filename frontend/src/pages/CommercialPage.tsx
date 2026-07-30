import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import {
  BarChart3,
  Bot,
  Check,
  Clipboard,
  FileText,
  Gauge,
  Megaphone,
  Radar,
  Search,
  Send,
  ShoppingBag,
  Sparkles,
  Target,
  Video,
  Zap,
} from 'lucide-react';

type CommercialAction = {
  id: string;
  label: string;
  description: string;
  icon: typeof Search;
  prompt: string;
};

const actions: CommercialAction[] = [
  {
    id: 'analysis',
    label: 'Analisar um produto',
    description: 'Avaliação 360, concorrência, público e potencial de venda.',
    icon: Search,
    prompt: 'Faça uma Análise 360 completa deste produto',
  },
  {
    id: 'listing',
    label: 'Criar anúncio',
    description: 'Título, descrição, atributos, palavras-chave e CTA.',
    icon: Megaphone,
    prompt: 'Crie um anúncio completo e otimizado para Shopee e Mercado Livre',
  },
  {
    id: 'video',
    label: 'Roteiro de vídeo',
    description: 'Roteiros de 15, 30 e 60 segundos prontos para vender.',
    icon: Video,
    prompt: 'Crie roteiros de venda de 15, 30 e 60 segundos',
  },
  {
    id: 'strategy',
    label: 'Estratégia de vendas',
    description: 'Preço, posicionamento, canais, kits, upsell e calendário.',
    icon: Target,
    prompt: 'Monte uma estratégia comercial completa para este produto',
  },
];

const modules = [
  { icon: BarChart3, title: 'Análise 360', text: 'Nota de qualidade, oportunidades e melhorias prioritárias.' },
  { icon: Search, title: 'SEO Marketplace', text: 'Títulos, palavras-chave e atributos para melhor ranqueamento.' },
  { icon: FileText, title: 'Copy de alta conversão', text: 'Descrição, benefícios, FAQ, bullet points e CTA persuasivo.' },
  { icon: Video, title: 'Vídeos de venda', text: 'Cenas, narração e prompts para vídeos de 15, 30 e 60 segundos.' },
  { icon: Megaphone, title: 'Redes sociais', text: 'Legendas para Instagram, Facebook e mensagens para WhatsApp.' },
  { icon: Gauge, title: 'Inteligência competitiva', text: 'Posicionamento, diferenciais, preço e nível de concorrência.' },
];

export function buildCommercialCommand(prompt: string, product: string) {
  return [
    prompt + '.',
    product.trim()
      ? `Produto ou link: ${product.trim()}`
      : 'Produto ou link: [adicione as informações do produto]',
    'Use o modo Achadinhos do JR.',
    'Não invente vendas, avaliações, preços ou métricas ausentes.',
    'Entregue o resultado em português do Brasil, pronto para revisão.',
  ].join('\n');
}

const radarItems = [
  'Potencial de vendas',
  'Nível de concorrência',
  'Público-alvo',
  'Palavras-chave',
  'Melhor horário para postar',
];

export function CommercialPage() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState(actions[0].id);
  const [product, setProduct] = useState('');
  const [copied, setCopied] = useState(false);

  const current = actions.find((action) => action.id === selected) ?? actions[0];
  const command = useMemo(
    () => buildCommercialCommand(current.prompt, product),
    [current, product],
  );

  const copyCommand = async () => {
    await navigator.clipboard.writeText(command);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  const openChat = async () => {
    try {
      await navigator.clipboard.writeText(command);
    } catch {
      // The command remains visible in this page if clipboard access is unavailable.
    }
    sessionStorage.setItem('zeusex-commercial-command', command);
    navigate('/');
  };

  return (
    <div className="relative h-full overflow-y-auto">
      <div className="hud-backdrop" />
      <main className="relative z-10 mx-auto flex w-full max-w-7xl flex-col gap-6 p-5 md:p-8">
        <section className="hud-panel overflow-hidden p-6 md:p-8">
          <div className="pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full bg-[var(--color-accent)] opacity-10 blur-3xl" />
          <div className="relative grid gap-7 lg:grid-cols-[1.25fr_0.75fr] lg:items-center">
            <div>
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-accent-subtle)] px-3 py-1.5 text-xs text-[var(--color-accent)]">
                <Zap size={14} />
                IA comercial local e governada
              </div>
              <h1 className="max-w-3xl text-3xl font-semibold tracking-tight md:text-5xl">
                Olá! Eu sou o <span className="text-[var(--color-accent)]">ZeusEx</span> 🤖⚡
              </h1>
              <p className="mt-4 max-w-2xl text-base text-[var(--color-text-secondary)] md:text-lg">
                Inteligência estratégica para analisar produtos, criar anúncios e vender melhor
                na Shopee, Mercado Livre e redes sociais.
              </p>
            </div>

            <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-5">
              <div className="flex items-center gap-3">
                <span className="hud-reticle"><Bot size={16} className="text-[var(--color-accent)]" /></span>
                <div>
                  <p className="text-sm font-medium">MODO EXCLUSIVO</p>
                  <p className="text-lg font-semibold text-[var(--color-accent)]">Achadinhos do JR</p>
                </div>
              </div>
              <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
                Campanha completa com títulos, descrição, vídeos, redes sociais, kits,
                upsell, cross-sell e estratégia comercial.
              </p>
            </div>
          </div>
        </section>

        <section>
          <div className="mb-3 flex items-end justify-between gap-4">
            <div>
              <p className="hud-label">COMECE POR AQUI</p>
              <h2 className="mt-1 text-xl font-semibold">O que você quer fazer?</h2>
            </div>
            <span className="hidden text-xs text-[var(--color-text-tertiary)] md:block">
              Selecione uma ação e informe o produto
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {actions.map((action) => {
              const active = action.id === selected;
              const Icon = action.icon;
              return (
                <button
                  key={action.id}
                  type="button"
                  onClick={() => setSelected(action.id)}
                  className="hud-panel group p-4 text-left"
                  style={{
                    borderColor: active ? 'var(--color-accent)' : undefined,
                    boxShadow: active ? '0 0 24px -12px var(--color-accent)' : undefined,
                  }}
                >
                  <span className="mb-4 inline-flex rounded-xl bg-[var(--color-accent-subtle)] p-2.5 text-[var(--color-accent)]">
                    <Icon size={20} />
                  </span>
                  <span className="block font-medium">{action.label}</span>
                  <span className="mt-1 block text-xs leading-5 text-[var(--color-text-secondary)]">
                    {action.description}
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        <section className="hud-panel p-5 md:p-6">
          <div className="mb-4 flex items-center gap-3">
            <Sparkles size={20} className="text-[var(--color-accent)]" />
            <div>
              <h2 className="font-semibold">{current.label}</h2>
              <p className="text-xs text-[var(--color-text-tertiary)]">
                Envie um link ou descreva o produto
              </p>
            </div>
          </div>
          <textarea
            value={product}
            onChange={(event) => setProduct(event.target.value)}
            placeholder="Ex.: link da Shopee/Mercado Livre, nome do produto, custo, preço e diferenciais..."
            className="min-h-28 w-full resize-y rounded-xl border border-[var(--color-input-border)] bg-[var(--color-input-bg)] p-4 text-sm text-[var(--color-text)] outline-none transition focus:border-[var(--color-accent)]"
          />
          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={copyCommand}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-[var(--color-border)] px-4 py-2.5 text-sm text-[var(--color-text-secondary)] transition hover:bg-[var(--color-bg-tertiary)]"
            >
              {copied ? <Check size={16} /> : <Clipboard size={16} />}
              {copied ? 'Comando copiado' : 'Copiar comando'}
            </button>
            <button
              type="button"
              onClick={openChat}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--color-accent)] px-5 py-2.5 text-sm font-medium text-[var(--color-on-accent)] transition hover:bg-[var(--color-accent-hover)]"
            >
              Preparar no chat
              <Send size={16} />
            </button>
          </div>
        </section>

        <section>
          <p className="hud-label">RECURSOS COMERCIAIS</p>
          <h2 className="mb-4 mt-1 text-xl font-semibold">Tudo para transformar análise em venda</h2>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {modules.map((module) => {
              const Icon = module.icon;
              return (
                <article key={module.title} className="hud-panel p-5">
                  <Icon size={20} className="mb-4 text-[var(--color-accent)]" />
                  <h3 className="font-medium">{module.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-[var(--color-text-secondary)]">{module.text}</p>
                </article>
              );
            })}
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <article className="hud-panel p-6">
            <div className="flex items-center gap-3">
              <Radar size={22} className="text-[var(--color-accent)]" />
              <div>
                <p className="hud-label">RADAR DE PRODUTOS</p>
                <h2 className="font-semibold">Sinais para decidir melhor</h2>
              </div>
            </div>
            <ul className="mt-5 grid gap-3">
              {radarItems.map((item) => (
                <li key={item} className="flex items-center gap-3 text-sm text-[var(--color-text-secondary)]">
                  <Check size={15} className="text-[var(--color-success)]" />
                  {item}
                </li>
              ))}
            </ul>
          </article>

          <article className="hud-panel p-6">
            <div className="flex items-center gap-3">
              <ShoppingBag size={22} className="text-[var(--color-accent)]" />
              <div>
                <p className="hud-label">SAÍDAS PRONTAS</p>
                <h2 className="font-semibold">Uma campanha, vários canais</h2>
              </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              {[
                'Título Shopee',
                'Título Mercado Livre',
                'Descrição otimizada',
                'Bullet points',
                'Instagram e Facebook',
                'WhatsApp',
                'Roteiro 15/30/60s',
                'Prompt para imagem',
                'Hashtags',
                'Estratégia completa',
              ].map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)]"
                >
                  {item}
                </span>
              ))}
            </div>
          </article>
        </section>
      </main>
    </div>
  );
}
