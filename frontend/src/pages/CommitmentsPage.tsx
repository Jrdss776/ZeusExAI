import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Clock3,
  ExternalLink,
  FileText,
  ListTodo,
  Loader2,
  MapPin,
  Plus,
  RefreshCw,
  Search,
  Users,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  fetchProductivityOverview,
  type ProductivityEvent,
  type ProductivityOverview,
  type ProductivityTask,
} from '../lib/api';

type CommitmentView = 'today' | 'week' | 'calendar' | 'pending';
type Commitment =
  | { key: string; kind: 'event'; date: Date; event: ProductivityEvent }
  | { key: string; kind: 'task'; date: Date | null; task: ProductivityTask };

const VIEW_LABELS: Array<{ id: CommitmentView; label: string }> = [
  { id: 'today', label: 'Hoje' },
  { id: 'week', label: 'Semana' },
  { id: 'calendar', label: 'Calendário' },
  { id: 'pending', label: 'Pendências' },
];

function validDate(value: string) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function sameDay(left: Date, right: Date) {
  return left.getFullYear() === right.getFullYear()
    && left.getMonth() === right.getMonth()
    && left.getDate() === right.getDate();
}

function formatDay(date: Date | null) {
  if (!date) return 'Sem prazo';
  return new Intl.DateTimeFormat('pt-BR', { weekday: 'short', day: '2-digit', month: 'short' }).format(date);
}

function formatTime(date: Date | null) {
  if (!date) return '—';
  return new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' }).format(date);
}

function isTaskDone(task: ProductivityTask) {
  return ['completed', 'done', 'concluída', 'concluido', 'concluído'].includes(task.status.toLowerCase());
}

export function CommitmentsPage() {
  const [overview, setOverview] = useState<ProductivityOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<CommitmentView>('today');
  const [query, setQuery] = useState('');
  const [selectedKey, setSelectedKey] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const next = await fetchProductivityOverview();
      setOverview(next);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Não foi possível carregar seus compromissos.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const allItems = useMemo<Commitment[]>(() => {
    if (!overview) return [];
    return [
      ...overview.agenda.map((event) => ({ key: `event-${event.id}`, kind: 'event' as const, date: validDate(event.start) || new Date(0), event })),
      ...overview.tasks.map((task) => ({ key: `task-${task.id}`, kind: 'task' as const, date: validDate(task.due), task })),
    ].sort((left, right) => (left.date?.getTime() ?? Number.MAX_SAFE_INTEGER) - (right.date?.getTime() ?? Number.MAX_SAFE_INTEGER));
  }, [overview]);

  const filteredItems = useMemo(() => {
    const now = new Date();
    const weekEnd = new Date(now);
    weekEnd.setDate(now.getDate() + 7);
    const normalizedQuery = query.trim().toLowerCase();
    return allItems.filter((item) => {
      const title = item.kind === 'event' ? item.event.title : item.task.title;
      if (normalizedQuery && !title.toLowerCase().includes(normalizedQuery)) return false;
      if (view === 'today') return Boolean(item.date && sameDay(item.date, now));
      if (view === 'week') return Boolean(item.date && item.date >= new Date(now.getFullYear(), now.getMonth(), now.getDate()) && item.date <= weekEnd);
      if (view === 'pending') return item.kind === 'task' && !isTaskDone(item.task);
      return true;
    });
  }, [allItems, query, view]);

  useEffect(() => {
    if (!filteredItems.some((item) => item.key === selectedKey)) {
      setSelectedKey(filteredItems[0]?.key || '');
    }
  }, [filteredItems, selectedKey]);

  const selected = filteredItems.find((item) => item.key === selectedKey) || filteredItems[0];
  const todayCount = allItems.filter((item) => item.date && sameDay(item.date, new Date())).length;
  const pendingCount = overview?.tasks.filter((task) => !isTaskDone(task)).length || 0;
  const nextEvent = allItems.find((item) => item.kind === 'event' && item.date.getTime() >= Date.now());

  return (
    <main className="flex-1 overflow-y-auto bg-[#050908] text-white">
      <div className="mx-auto min-h-full max-w-[1600px] px-4 py-5 sm:px-6 lg:px-8">
        <header className="overflow-hidden rounded-[28px] border border-emerald-400/20 bg-[radial-gradient(circle_at_15%_0%,rgba(52,211,153,.16),transparent_42%),linear-gradient(135deg,#0d1b17,#070a0a)] p-5 shadow-[0_22px_70px_rgba(0,0,0,.38)] sm:p-7">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[.24em] text-emerald-300"><CalendarDays size={14} /> Central do dia</div>
              <h1 className="font-[var(--font-display)] text-3xl font-semibold tracking-[.06em] sm:text-4xl">COMPROMISSOS</h1>
              <p className="mt-2 max-w-2xl text-sm text-slate-400">Agenda, tarefas, prazos e tudo o que precisa de preparação.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Summary label="Hoje" value={todayCount} icon={<Clock3 size={15} />} />
              <Summary label="Pendências" value={pendingCount} icon={<ListTodo size={15} />} />
              <Summary label="Próximo" value={nextEvent ? formatTime(nextEvent.date) : 'Livre'} icon={<CalendarDays size={15} />} />
              <a href="https://calendar.google.com/calendar/u/0/r/eventedit" target="_blank" rel="noreferrer" className="inline-flex min-h-[58px] items-center gap-2 rounded-2xl bg-emerald-400 px-4 text-sm font-semibold text-emerald-950 transition hover:bg-emerald-300"><Plus size={17} /> Novo compromisso</a>
            </div>
          </div>
        </header>

        <div className="mt-4 flex flex-col gap-3 rounded-[22px] border border-white/[.08] bg-[#0b1211] p-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex gap-1 overflow-x-auto">
            {VIEW_LABELS.map((option) => <button key={option.id} onClick={() => setView(option.id)} className={`shrink-0 rounded-xl px-4 py-2 text-sm font-medium transition ${view === option.id ? 'bg-emerald-400/15 text-emerald-200' : 'text-slate-500 hover:bg-white/[.04] hover:text-slate-300'}`}>{option.label}</button>)}
          </div>
          <div className="flex items-center gap-2">
            <label className="flex min-w-0 flex-1 items-center gap-2 rounded-xl border border-white/[.08] bg-black/20 px-3 py-2 sm:w-64"><Search size={14} className="text-slate-600" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar compromisso..." className="min-w-0 flex-1 bg-transparent text-sm text-slate-200 outline-none placeholder:text-slate-600" /></label>
            <button onClick={() => void load()} disabled={loading} title="Atualizar" className="rounded-xl border border-white/[.08] p-2.5 text-slate-500 hover:text-emerald-300"><RefreshCw size={15} className={loading ? 'animate-spin' : ''} /></button>
          </div>
        </div>

        <div className="mt-4 grid min-h-[620px] gap-4 xl:grid-cols-[360px_minmax(0,1fr)_330px]">
          <section className="overflow-hidden rounded-[24px] border border-white/[.08] bg-[#0b1111]">
            <div className="border-b border-white/[.07] p-4"><h2 className="font-semibold text-slate-100">{VIEW_LABELS.find((option) => option.id === view)?.label}</h2><p className="text-xs text-slate-500">{filteredItems.length} itens encontrados</p></div>
            <div className="max-h-[700px] overflow-y-auto p-2">
              {loading && !overview && <div className="flex justify-center py-14 text-slate-500"><Loader2 className="animate-spin" /></div>}
              {!loading && filteredItems.length === 0 && <EmptyState />}
              {filteredItems.map((item) => <CommitmentButton key={item.key} item={item} active={selected?.key === item.key} onClick={() => setSelectedKey(item.key)} />)}
            </div>
          </section>

          <section className="rounded-[24px] border border-white/[.08] bg-[#0b1111] p-5 sm:p-6">
            {!selected ? <EmptyState /> : selected.kind === 'event' ? <EventDetails event={selected.event} date={selected.date} /> : <TaskDetails task={selected.task} date={selected.date} />}
          </section>

          <aside className="space-y-4">
            <section className="rounded-[24px] border border-emerald-400/15 bg-emerald-400/[.04] p-5">
              <h2 className="flex items-center gap-2 font-[var(--font-display)] text-sm font-semibold uppercase tracking-[.12em] text-emerald-300"><FileText size={16} /> Preparação</h2>
              {!selected ? <p className="mt-4 text-sm leading-6 text-slate-500">Selecione um compromisso para ver o que precisa ser preparado.</p> : <Preparation item={selected} />}
            </section>
            {overview && Object.keys(overview.errors).length > 0 && <div className="rounded-2xl border border-amber-400/15 bg-amber-400/[.05] p-4 text-xs leading-5 text-amber-200/80"><AlertCircle size={15} className="mb-2" /> Algumas fontes estão indisponíveis. As informações acessíveis continuam sendo exibidas.</div>}
          </aside>
        </div>
      </div>
    </main>
  );
}

function Summary({ label, value, icon }: { label: string; value: number | string; icon: React.ReactNode }) {
  return <div className="min-w-[106px] rounded-2xl border border-white/10 bg-black/20 px-3 py-2.5"><div className="flex items-center gap-2 text-emerald-300">{icon}<strong className="text-lg text-slate-100">{value}</strong></div><span className="text-[10px] uppercase tracking-[.12em] text-slate-500">{label}</span></div>;
}

function CommitmentButton({ item, active, onClick }: { item: Commitment; active: boolean; onClick: () => void }) {
  const title = item.kind === 'event' ? item.event.title : item.task.title;
  return <button onClick={onClick} className={`mb-2 w-full rounded-2xl border p-3 text-left transition ${active ? 'border-emerald-400/30 bg-emerald-400/[.08]' : 'border-white/[.05] bg-white/[.02] hover:border-white/10'}`}><div className="flex gap-3"><div className={`mt-0.5 rounded-xl p-2 ${item.kind === 'event' ? 'bg-cyan-400/10 text-cyan-300' : 'bg-emerald-400/10 text-emerald-300'}`}>{item.kind === 'event' ? <CalendarDays size={16} /> : <CheckCircle2 size={16} />}</div><div className="min-w-0 flex-1"><span className="text-[10px] uppercase tracking-wider text-slate-600">{formatDay(item.date)} {item.kind === 'event' && `• ${formatTime(item.date)}`}</span><strong className="mt-1 block truncate text-sm text-slate-200">{title}</strong><small className="text-xs text-slate-500">{item.kind === 'event' ? 'Compromisso' : item.task.status || 'Tarefa pendente'}</small></div><ChevronRight size={15} className="mt-3 text-slate-700" /></div></button>;
}

function EventDetails({ event, date }: { event: ProductivityEvent; date: Date }) {
  return <div><span className="text-[10px] font-semibold uppercase tracking-[.18em] text-cyan-300">Compromisso</span><h2 className="mt-2 font-[var(--font-display)] text-2xl font-semibold text-slate-100">{event.title}</h2><div className="mt-5 grid gap-3 sm:grid-cols-2"><Detail icon={<CalendarDays size={16} />} label="Data" value={formatDay(date)} /><Detail icon={<Clock3 size={16} />} label="Horário" value={formatTime(date)} /><Detail icon={<MapPin size={16} />} label="Local" value={event.location || 'Não informado'} /><Detail icon={<Users size={16} />} label="Participantes" value={event.participants.length ? event.participants.join(', ') : 'Não informados'} /></div>{event.content && <div className="mt-5 rounded-2xl border border-white/[.07] bg-black/20 p-4 text-sm leading-7 text-slate-300 whitespace-pre-wrap">{event.content}</div>}{event.url && <a href={event.url} target="_blank" rel="noreferrer" className="mt-5 inline-flex items-center gap-2 rounded-xl border border-cyan-300/15 bg-cyan-300/[.06] px-4 py-2.5 text-sm font-semibold text-cyan-200"><ExternalLink size={15} /> Abrir no calendário</a>}</div>;
}

function TaskDetails({ task, date }: { task: ProductivityTask; date: Date | null }) {
  return <div><span className="text-[10px] font-semibold uppercase tracking-[.18em] text-emerald-300">Tarefa</span><h2 className="mt-2 font-[var(--font-display)] text-2xl font-semibold text-slate-100">{task.title}</h2><div className="mt-5 grid gap-3 sm:grid-cols-2"><Detail icon={<CalendarDays size={16} />} label="Prazo" value={formatDay(date)} /><Detail icon={<CheckCircle2 size={16} />} label="Status" value={task.status || 'Pendente'} /><Detail icon={<ListTodo size={16} />} label="Lista" value={task.task_list || 'Tarefas'} /></div>{task.notes && <div className="mt-5 rounded-2xl border border-white/[.07] bg-black/20 p-4 text-sm leading-7 text-slate-300 whitespace-pre-wrap">{task.notes}</div>}{task.url && <a href={task.url} target="_blank" rel="noreferrer" className="mt-5 inline-flex items-center gap-2 rounded-xl border border-emerald-300/15 bg-emerald-300/[.06] px-4 py-2.5 text-sm font-semibold text-emerald-200"><ExternalLink size={15} /> Abrir tarefa</a>}</div>;
}

function Detail({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="rounded-2xl border border-white/[.07] bg-white/[.025] p-3"><span className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-slate-600">{icon}{label}</span><strong className="mt-1.5 block text-sm font-medium text-slate-300">{value}</strong></div>;
}

function Preparation({ item }: { item: Commitment }) {
  const notes = item.kind === 'event' ? item.event.content : item.task.notes;
  const participants = item.kind === 'event' ? item.event.participants : [];
  return <div className="mt-4 space-y-3"><PrepRow done={Boolean(participants.length)} text={participants.length ? `${participants.length} participante(s) identificado(s)` : 'Confirmar participantes'} /><PrepRow done={Boolean(notes)} text={notes ? 'Informações de contexto disponíveis' : 'Adicionar informações de contexto'} /><PrepRow done={Boolean(item.date)} text={item.date ? `Horário ou prazo: ${formatDay(item.date)}` : 'Definir prazo'} /><p className="pt-2 text-xs leading-5 text-slate-500">A Vampira poderá relacionar e-mails e documentos a este compromisso em uma próxima integração.</p></div>;
}

function PrepRow({ done, text }: { done: boolean; text: string }) {
  return <div className="flex gap-2 rounded-xl border border-white/[.06] bg-black/15 p-3 text-xs text-slate-400">{done ? <CheckCircle2 size={15} className="shrink-0 text-emerald-300" /> : <Clock3 size={15} className="shrink-0 text-amber-300" />}{text}</div>;
}

function EmptyState() {
  return <div className="flex min-h-[180px] flex-col items-center justify-center gap-3 p-6 text-center text-sm text-slate-600"><CalendarDays size={28} /><span>Nenhum compromisso encontrado nesta visão.</span></div>;
}
