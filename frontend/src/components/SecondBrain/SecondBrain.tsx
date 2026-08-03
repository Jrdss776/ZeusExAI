import { useMemo, useState } from 'react';
import { Brain, Plus, Save, Trash2, X } from 'lucide-react';
import { storeMemory } from '../../lib/api';

export type BrainArea =
  | 'meta'
  | 'metas'
  | 'trabalho'
  | 'projetos'
  | 'financas'
  | 'aprendizado'
  | 'saude'
  | 'relacoes';

export type BrainNote = {
  id: string;
  area: BrainArea;
  title: string;
  body: string;
};

export const SECOND_BRAIN_KEY = 'zeusex-second-brain';

export const BRAIN_AREAS: Record<BrainArea, { label: string; color: string }> = {
  meta: { label: 'Você', color: '#8a90a6' },
  metas: { label: 'Metas', color: '#fbbf24' },
  trabalho: { label: 'Carreira', color: '#ff5547' },
  projetos: { label: 'Projetos', color: '#8b7cff' },
  financas: { label: 'Finanças', color: '#f7931a' },
  aprendizado: { label: 'Aprendizado', color: '#2dd4ff' },
  saude: { label: 'Saúde', color: '#10b981' },
  relacoes: { label: 'Relações', color: '#ec4899' },
};

export const DEFAULT_BRAIN_NOTES: BrainNote[] = [
  { id: 'jair', area: 'meta', title: 'Jair', body: 'Jair tem 50 anos e mora em São Paulo, Brasil.' },
  { id: 'novo-emprego', area: 'metas', title: 'Novo emprego', body: 'Conseguir um novo emprego nos próximos três meses.' },
  { id: 'viagem-familia', area: 'metas', title: 'Viagem familiar', body: 'Realizar uma viagem com a família dentro de um a três anos.' },
  { id: 'experiencia', area: 'trabalho', title: 'Experiência', body: 'Experiência como garçom, gerente de cozinha de restaurante e vendedor em pet shop.' },
  { id: 'situacao', area: 'trabalho', title: 'Situação atual', body: 'Está desempregado e procurando uma nova oportunidade.' },
  { id: 'vendas-online', area: 'projetos', title: 'Vendas online', body: 'Estudar e desenvolver vendas pela Shopee e pelo Mercado Livre.' },
  { id: 'meta-mensal', area: 'financas', title: 'Meta mensal', body: 'Alcançar inicialmente uma renda de R$ 5 mil por mês.' },
  { id: 'programacao', area: 'aprendizado', title: 'Programação', body: 'Estuda programação e quer ampliar seus conhecimentos.' },
  { id: 'inteligencia-artificial', area: 'aprendizado', title: 'Inteligência artificial', body: 'Estuda inteligência artificial e suas aplicações.' },
  { id: 'exercicios', area: 'saude', title: 'Exercícios', body: 'Pratica exercícios três vezes por semana.' },
  { id: 'paula', area: 'relacoes', title: 'Paula', body: 'Paula é sua esposa.' },
  { id: 'lucas', area: 'relacoes', title: 'Lucas', body: 'Lucas é seu filho.' },
];

export function loadBrainNotes(): BrainNote[] {
  try {
    const raw = localStorage.getItem(SECOND_BRAIN_KEY);
    if (!raw) return DEFAULT_BRAIN_NOTES;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) && parsed.length ? parsed : DEFAULT_BRAIN_NOTES;
  } catch {
    return DEFAULT_BRAIN_NOTES;
  }
}

function persist(notes: BrainNote[]) {
  localStorage.setItem(SECOND_BRAIN_KEY, JSON.stringify(notes));
  window.dispatchEvent(new CustomEvent('zeusex-brain-updated'));
}

type Props = {
  open: boolean;
  onClose: () => void;
};

export function SecondBrain({ open, onClose }: Props) {
  const [notes, setNotes] = useState<BrainNote[]>(loadBrainNotes);
  const [editing, setEditing] = useState<BrainNote | null>(null);
  const areas = useMemo(() => new Set(notes.map((note) => note.area)).size, [notes]);

  if (!open) return null;

  const saveNote = async () => {
    if (!editing?.title.trim() || !editing.body.trim()) return;
    const next = notes.some((note) => note.id === editing.id)
      ? notes.map((note) => (note.id === editing.id ? editing : note))
      : [...notes, editing];
    setNotes(next);
    persist(next);
    setEditing(null);
    try {
      await storeMemory(editing.body, {
        source: 'second_brain',
        area: editing.area,
        title: editing.title,
      });
    } catch {
      // The local Second Brain remains available if the memory service is offline.
    }
  };

  const removeNote = (id: string) => {
    const next = notes.filter((note) => note.id !== id);
    setNotes(next);
    persist(next);
    setEditing(null);
  };

  const positions = notes.map((note, index) => {
    const angle = -Math.PI / 2 + (index / Math.max(notes.length, 1)) * Math.PI * 2;
    return {
      note,
      x: 300 + Math.cos(angle) * 230,
      y: 205 + Math.sin(angle) * 145,
    };
  });

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/55 backdrop-blur-sm" onMouseDown={onClose}>
      <aside
        className="h-full w-full max-w-3xl overflow-y-auto border-l p-5 md:p-7"
        style={{ background: 'var(--color-bg)', borderColor: 'var(--color-border)' }}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="mb-5 flex items-center gap-3">
          <span className="james-brain-icon"><Brain size={19} /></span>
          <div>
            <p className="hud-label">JAMES // MEMÓRIA VIVA</p>
            <h2 className="text-xl font-semibold">Second Brain</h2>
          </div>
          <span className="ml-auto text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
            {notes.length} notas · {areas} áreas
          </span>
          <button
            type="button"
            onClick={() =>
              setEditing({
                id: `note-${Date.now().toString(36)}`,
                area: 'meta',
                title: '',
                body: '',
              })
            }
            className="rounded-lg p-2"
            style={{ color: 'var(--color-accent)', border: '1px solid var(--color-border)' }}
            title="Nova nota"
          >
            <Plus size={18} />
          </button>
          <button type="button" onClick={onClose} className="rounded-lg p-2" title="Fechar">
            <X size={19} />
          </button>
        </header>

        <section className="hud-panel mb-5 overflow-hidden p-3">
          <svg viewBox="0 0 600 410" className="h-auto w-full" role="img" aria-label="Grafo do Second Brain">
            <defs>
              <radialGradient id="james-core">
                <stop offset="0" stopColor="#dcfce7" />
                <stop offset=".35" stopColor="#4ade80" />
                <stop offset="1" stopColor="#14532d" />
              </radialGradient>
              <filter id="james-glow">
                <feGaussianBlur stdDeviation="5" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>
            {positions.map(({ note, x, y }) => (
              <line
                key={`line-${note.id}`}
                x1="300"
                y1="205"
                x2={x}
                y2={y}
                stroke={BRAIN_AREAS[note.area].color}
                strokeOpacity=".28"
                strokeDasharray="5 7"
                className="james-synapse"
              />
            ))}
            <circle cx="300" cy="205" r="43" fill="url(#james-core)" filter="url(#james-glow)" />
            <Brain x="286" y="191" width="28" height="28" color="#052e16" />
            {positions.map(({ note, x, y }) => (
              <g
                key={note.id}
                className="cursor-pointer"
                onClick={() => setEditing({ ...note })}
              >
                <circle
                  cx={x}
                  cy={y}
                  r="17"
                  fill="var(--color-bg-secondary)"
                  stroke={BRAIN_AREAS[note.area].color}
                  strokeWidth="3"
                  filter="url(#james-glow)"
                />
                <circle cx={x} cy={y} r="4" fill={BRAIN_AREAS[note.area].color} />
                <text
                  x={x}
                  y={y + 31}
                  textAnchor="middle"
                  fill="var(--color-text-secondary)"
                  fontSize="10"
                >
                  {note.title.length > 18 ? `${note.title.slice(0, 16)}…` : note.title}
                </text>
              </g>
            ))}
          </svg>
        </section>

        <div className="mb-5 flex flex-wrap gap-2">
          {Object.entries(BRAIN_AREAS).map(([key, area]) => (
            <span
              key={key}
              className="rounded-full px-2.5 py-1 text-xs"
              style={{ border: `1px solid ${area.color}55`, color: area.color }}
            >
              {area.label}
            </span>
          ))}
        </div>

        <section className="grid gap-2 sm:grid-cols-2">
          {notes.map((note) => (
            <button
              type="button"
              key={note.id}
              onClick={() => setEditing({ ...note })}
              className="rounded-xl p-3 text-left transition-colors"
              style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}
            >
              <span className="text-xs" style={{ color: BRAIN_AREAS[note.area].color }}>
                {BRAIN_AREAS[note.area].label}
              </span>
              <strong className="mt-1 block text-sm">{note.title}</strong>
              <span className="mt-1 block text-xs leading-5" style={{ color: 'var(--color-text-secondary)' }}>
                {note.body}
              </span>
            </button>
          ))}
        </section>

        {editing && (
          <div className="fixed inset-0 z-[60] grid place-items-center bg-black/65 p-4" onMouseDown={() => setEditing(null)}>
            <div
              className="w-full max-w-lg rounded-2xl p-5"
              style={{ background: 'var(--color-bg)', border: '1px solid var(--color-border)' }}
              onMouseDown={(event) => event.stopPropagation()}
            >
              <h3 className="mb-4 font-semibold">Nota do Second Brain</h3>
              <label className="mb-3 block text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                Área
                <select
                  value={editing.area}
                  onChange={(event) => setEditing({ ...editing, area: event.target.value as BrainArea })}
                  className="mt-1 w-full rounded-lg p-2.5"
                  style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}
                >
                  {Object.entries(BRAIN_AREAS).map(([key, area]) => (
                    <option key={key} value={key}>{area.label}</option>
                  ))}
                </select>
              </label>
              <label className="mb-3 block text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                Título
                <input
                  value={editing.title}
                  onChange={(event) => setEditing({ ...editing, title: event.target.value })}
                  className="mt-1 w-full rounded-lg p-2.5"
                  style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}
                />
              </label>
              <label className="block text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                Conteúdo
                <textarea
                  value={editing.body}
                  onChange={(event) => setEditing({ ...editing, body: event.target.value })}
                  rows={5}
                  className="mt-1 w-full resize-y rounded-lg p-2.5"
                  style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}
                />
              </label>
              <div className="mt-4 flex gap-2">
                {notes.some((note) => note.id === editing.id) && (
                  <button
                    type="button"
                    onClick={() => removeNote(editing.id)}
                    className="mr-auto inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm"
                    style={{ color: 'var(--color-error)', border: '1px solid var(--color-error)' }}
                  >
                    <Trash2 size={15} /> Excluir
                  </button>
                )}
                <button type="button" onClick={() => setEditing(null)} className="rounded-lg px-3 py-2 text-sm">
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={saveNote}
                  className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm"
                  style={{ background: 'var(--color-accent)', color: 'var(--color-on-accent)' }}
                >
                  <Save size={15} /> Salvar
                </button>
              </div>
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}
