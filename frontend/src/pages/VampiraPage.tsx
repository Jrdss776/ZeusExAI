import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  FileText,
  Inbox,
  Loader2,
  Mail,
  Paperclip,
  RefreshCw,
  Search,
  Save,
  Send,
  Settings2,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';
import { useNavigate } from 'react-router';
import { toast } from 'sonner';
import {
  approveAction,
  denyAction,
  fetchPendingApprovals,
  fetchProductivityOverview,
  fetchVampiraResponseTemplates,
  queueEmailDraft,
  updateVampiraResponseTemplate,
  type PendingApproval,
  type ProductivityEmail,
  type ProductivityOverview,
  type VampiraResponseTemplate,
} from '../lib/api';

function formatDate(value: string, withTime = true) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || '—';
  return new Intl.DateTimeFormat('pt-BR', withTime
    ? { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }
    : { day: '2-digit', month: 'short' }).format(date);
}

function senderAddress(sender: string) {
  const bracketed = sender.match(/<([^>]+)>/);
  if (bracketed) return bracketed[1].trim();
  const plain = sender.match(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/);
  return plain?.[0] || sender.trim();
}

function senderName(sender: string) {
  const beforeBracket = sender.split('<')[0].trim().replace(/^"|"$/g, '');
  if (beforeBracket && !beforeBracket.includes('@')) return beforeBracket.split(' ')[0];
  const address = senderAddress(sender);
  return address.split('@')[0].split(/[._-]/)[0] || 'Senhor(a)';
}

function createDraft(email: ProductivityEmail) {
  const name = senderName(email.sender);
  const fallback = `Prezado(a) [Nome],\n\nAcusamos o recebimento de sua mensagem referente ao [Assunto].\n\nA mensagem será analisada com a devida atenção. O retorno formal será enviado até o dia [Data].\n\nAtenciosamente,\nJair da Silva Souza\njairdss44@gmail.com`;
  const body = (email.situation.response_template || fallback)
    .split('[Nome]').join(name)
    .split('[Assunto]').join(email.subject);
  return {
    recipients: senderAddress(email.sender),
    subject: email.subject.toLowerCase().startsWith('re:') ? email.subject : `Re: ${email.subject}`,
    body,
  };
}

type EmailFilter = 'important' | 'unread' | 'reply' | 'recent';

export function VampiraPage() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<ProductivityOverview | null>(null);
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [emailFilter, setEmailFilter] = useState<EmailFilter>('recent');
  const [searchQuery, setSearchQuery] = useState('');
  const [draft, setDraft] = useState<ReturnType<typeof createDraft> | null>(null);
  const [queueing, setQueueing] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [selectedApproval, setSelectedApproval] = useState<PendingApproval | null>(null);
  const [actingApproval, setActingApproval] = useState<'approve' | 'deny' | null>(null);
  const [noReplyNeeded, setNoReplyNeeded] = useState<Record<string, boolean>>({});

  const load = useCallback(async (notifyError = true) => {
    setLoading(true);
    try {
      const [nextOverview, nextApprovals] = await Promise.all([
        fetchProductivityOverview(),
        fetchPendingApprovals().catch(() => []),
      ]);
      setOverview(nextOverview);
      setApprovals(nextApprovals);
      setSelectedId((current) => current || nextOverview.emails[0]?.id || '');
      setLoadFailed(false);
    } catch (error) {
      setLoadFailed(true);
      if (notifyError) toast.error(error instanceof Error ? error.message : 'Não foi possível carregar a central da Vampira.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(false); }, [load]);
  useEffect(() => {
    if (!loadFailed) return;
    const retry = window.setTimeout(() => void load(false), 4000);
    return () => window.clearTimeout(retry);
  }, [load, loadFailed]);

  const visibleEmails = useMemo(() => {
    const emails = overview?.emails || [];
    const query = searchQuery.trim().toLowerCase();
    return emails.filter((email) => {
      const matchesFilter = emailFilter === 'important' ? email.important
        : emailFilter === 'unread' ? email.unread
          : emailFilter === 'reply' ? email.situation.reply_recommended && !noReplyNeeded[email.id]
            : true;
      const matchesSearch = !query || `${email.sender} ${email.subject} ${email.preview}`.toLowerCase().includes(query);
      return matchesFilter && matchesSearch;
    });
  }, [emailFilter, noReplyNeeded, overview, searchQuery]);
  const selectedEmail = visibleEmails.find((email) => email.id === selectedId) || visibleEmails[0];

  const chooseFilter = (nextFilter: EmailFilter) => {
    setEmailFilter(nextFilter);
    setSelectedId('');
    setDraft(null);
  };

  const prepareReply = () => {
    if (!selectedEmail) return;
    setNoReplyNeeded((current) => ({ ...current, [selectedEmail.id]: false }));
    setDraft(createDraft(selectedEmail));
  };

  const skipReply = () => {
    if (!selectedEmail) return;
    setDraft(null);
    setNoReplyNeeded((current) => ({ ...current, [selectedEmail.id]: true }));
    toast.success('Decisão registrada: este e-mail não precisa de resposta.');
  };

  const submitDraft = async () => {
    if (!draft) return;
    setQueueing(true);
    try {
      await queueEmailDraft({
        recipients: draft.recipients.split(',').map((value) => value.trim()).filter(Boolean),
        subject: draft.subject,
        body: draft.body,
      });
      setDraft(null);
      setApprovals(await fetchPendingApprovals().catch(() => approvals));
      toast.success('Resposta enviada para aprovação. Revise no sino da HUD.');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Não foi possível preparar a aprovação.');
    } finally {
      setQueueing(false);
    }
  };

  const decideApproval = async (decision: 'approve' | 'deny') => {
    if (!selectedApproval) return;
    setActingApproval(decision);
    try {
      if (decision === 'approve') {
        await approveAction(selectedApproval.id);
        toast.success('Ação aprovada e executada com sucesso.');
      } else {
        await denyAction(selectedApproval.id);
        toast.success('Ação recusada. Nada foi enviado.');
      }
      setApprovals((current) => current.filter((item) => item.id !== selectedApproval.id));
      setSelectedApproval(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Não foi possível concluir a decisão.');
      setApprovals(await fetchPendingApprovals().catch(() => approvals));
    } finally {
      setActingApproval(null);
    }
  };

  const counts = overview?.counts || {
    important_emails: 0,
    unread_emails: 0,
    agenda_today: 0,
    pending_tasks: 0,
  };
  const urgentCount = overview?.emails.filter((email) => email.situation.priority === 'high').length || 0;
  const replyCount = overview?.emails.filter((email) => email.situation.reply_recommended && !noReplyNeeded[email.id]).length || 0;

  return (
    <main className="flex-1 overflow-y-auto bg-[#06080d] text-white">
      <div className="mx-auto min-h-full max-w-[1600px] px-4 py-5 sm:px-6 lg:px-8">
        <header className="vampira-hero">
          <div className="vampira-hero__grid" aria-hidden="true" />
          <div className="vampira-hero__layout">
            <div className="vampira-hero__intro">
              <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[.24em] text-fuchsia-300"><Sparkles size={14} /> Inteligência de e-mail</div>
              <h1 className="font-[var(--font-display)] text-3xl font-semibold tracking-[.08em] sm:text-4xl">VAMPIRA</h1>
              <p className="mt-2 max-w-2xl text-sm text-slate-400">Triagem, leitura, análise e respostas de e-mail em um único fluxo.</p>
              <button onClick={() => setShowTemplates(true)} className="mt-4 inline-flex items-center gap-2 rounded-xl border border-fuchsia-300/20 bg-fuchsia-300/[.08] px-3.5 py-2 text-xs font-semibold text-fuchsia-200 transition hover:bg-fuchsia-300/[.14]"><Settings2 size={14} /> Modelos de resposta</button>
            </div>

            <div className="vampira-hero__console" aria-label="Atalhos da Vampira">
              <div className="vampira-hero__orbit" aria-hidden="true" />
              <div className="vampira-hero__portrait">
                <img src="/identity/vampira.jpg" alt="Vampira, assistente de produtividade" />
                <span><i /> ONLINE</span>
              </div>
              <a className="vampira-hero__shortcut vampira-hero__shortcut--mail" href="#vampira-inbox" title="Ir para e-mails"><Mail size={15} /><span>Email</span></a>
              <a className="vampira-hero__shortcut vampira-hero__shortcut--agenda" href="#vampira-analysis" title="Ir para análise"><Sparkles size={15} /><span>Análise</span></a>
              <a className="vampira-hero__shortcut vampira-hero__shortcut--tasks" href="#vampira-reply" title="Ir para respostas"><Send size={15} /><span>Responder</span></a>
              <a className="vampira-hero__shortcut vampira-hero__shortcut--approvals" href="#vampira-approvals" title="Ir para aprovações"><ShieldCheck size={15} /><span>Decisões</span></a>
            </div>

            <div className="vampira-hero__metrics">
              <Metric icon={<Mail size={15} />} label="Importantes" value={counts.important_emails} tone="purple" />
              <Metric icon={<AlertCircle size={15} />} label="Urgentes" value={urgentCount} tone="orange" />
              <Metric icon={<Send size={15} />} label="Responder" value={replyCount} tone="green" />
              <Metric icon={<ShieldCheck size={15} />} label="Aprovações" value={approvals.length} tone="cyan" />
            </div>
          </div>
        </header>

        <div className="mt-4 grid min-h-[680px] gap-4 xl:grid-cols-[330px_minmax(0,1fr)_340px]">
          <section id="vampira-inbox" className="scroll-mt-4 overflow-hidden rounded-[24px] border border-white/[.08] bg-[#0c1019]">
            <div className="flex items-center justify-between border-b border-white/[.07] p-4">
              <div><h2 className="font-semibold text-slate-100">Caixa de entrada</h2><p className="text-xs text-slate-500">{counts.unread_emails} não lidos</p></div>
              <button onClick={() => void load()} disabled={loading} className="rounded-lg p-2 text-slate-500 transition hover:bg-white/[.05] hover:text-fuchsia-300" title="Atualizar e-mails"><RefreshCw size={15} className={loading ? 'animate-spin' : ''} /></button>
            </div>
            <div className="border-b border-white/[.07] p-3">
              <label className="mb-3 flex items-center gap-2 rounded-xl border border-white/[.08] bg-black/20 px-3 py-2"><Search size={14} className="text-slate-600" /><input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Buscar remetente ou assunto..." className="min-w-0 flex-1 bg-transparent text-xs text-slate-200 outline-none placeholder:text-slate-600" /></label>
              <div className="flex flex-wrap gap-1.5">
                <Filter active={emailFilter === 'important'} onClick={() => chooseFilter('important')}>Importantes</Filter>
                <Filter active={emailFilter === 'unread'} onClick={() => chooseFilter('unread')}>Não lidos</Filter>
                <Filter active={emailFilter === 'reply'} onClick={() => chooseFilter('reply')}>Responder</Filter>
                <Filter active={emailFilter === 'recent'} onClick={() => chooseFilter('recent')}>Recentes</Filter>
              </div>
            </div>
            <div className="max-h-[620px] overflow-y-auto p-2">
              {loading && !overview && <LoadingState />}
              {!loading && visibleEmails.length === 0 && <Empty icon={<Inbox size={24} />} text="Nenhum e-mail encontrado neste filtro." />}
              {visibleEmails.map((email) => (
                <button key={email.id} onClick={() => { setSelectedId(email.id); setDraft(null); }} className={`mb-2 w-full rounded-2xl border p-3 text-left transition ${selectedEmail?.id === email.id ? 'border-fuchsia-400/30 bg-fuchsia-400/[.08]' : 'border-white/[.05] bg-white/[.02] hover:border-white/10'}`}>
                  <div className="mb-1 flex items-center gap-2">
                    {email.important && <AlertCircle size={13} className="text-amber-300" />}
                    <span className={`min-w-0 flex-1 truncate text-xs ${email.unread ? 'font-semibold text-slate-200' : 'text-slate-400'}`}>{email.sender}</span>
                    <span className="text-[10px] text-slate-600">{formatDate(email.timestamp, false)}</span>
                  </div>
                  <strong className="block truncate text-sm text-slate-100">{email.subject}</strong>
                  <span className="mt-1.5 inline-flex rounded-md bg-white/[.05] px-2 py-0.5 text-[10px] font-medium text-slate-400">{email.situation.label}</span>
                  <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">{email.preview}</p>
                </button>
              ))}
            </div>
          </section>

          <section className="relative overflow-hidden rounded-[24px] border border-white/[.08] bg-[#0c1019]">
            {!selectedEmail ? <Empty icon={<Mail size={28} />} text="Selecione um e-mail para ler." /> : (
              <div className="flex h-full flex-col">
                <div className="border-b border-white/[.07] p-5 sm:p-6">
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    {selectedEmail.important && <span className="rounded-full bg-amber-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-amber-300">Importante</span>}
                    {selectedEmail.unread && <span className="rounded-full bg-cyan-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-cyan-300">Não lido</span>}
                    <SituationBadge situation={selectedEmail.situation} />
                    <span className="ml-auto text-xs text-slate-600">{formatDate(selectedEmail.timestamp)}</span>
                  </div>
                  <h2 className="font-[var(--font-display)] text-xl font-semibold text-slate-100 sm:text-2xl">{selectedEmail.subject}</h2>
                  <p className="mt-2 text-sm text-slate-400">De: <span className="text-slate-200">{selectedEmail.sender}</span></p>
                  <div className="mt-3 rounded-xl border border-white/[.06] bg-white/[.025] px-3 py-2.5 text-xs leading-5 text-slate-400">
                    <span className="font-semibold text-slate-300">Ação sugerida:</span> {selectedEmail.situation.recommended_action}
                    <span className="ml-2 text-slate-600">Tom: {selectedEmail.situation.suggested_tone}</span>
                  </div>
                  {selectedEmail.attachments.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{selectedEmail.attachments.map((attachment) => <span key={attachment.filename} className="flex items-center gap-1.5 rounded-lg border border-white/[.08] bg-white/[.03] px-2.5 py-1.5 text-xs text-slate-400"><Paperclip size={12} />{attachment.filename}</span>)}</div>}
                </div>
                <div className="flex-1 overflow-y-auto p-5 sm:p-6">
                  <div className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-300">{selectedEmail.content || selectedEmail.preview}</div>
                </div>
                <div id="vampira-reply" className="scroll-mt-4 border-t border-white/[.07] p-4 sm:p-5">
                  {noReplyNeeded[selectedEmail.id] ? (
                    <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/[.06] p-4">
                      <p className="flex items-center gap-2 text-sm font-medium text-emerald-100"><CheckCircle2 size={16} /> Você indicou que este e-mail não precisa de resposta.</p>
                      <button onClick={() => setNoReplyNeeded((current) => ({ ...current, [selectedEmail.id]: false }))} className="mt-3 rounded-xl border border-emerald-300/15 px-3.5 py-2 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-300/[.08]">Reavaliar decisão</button>
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-fuchsia-400/20 bg-fuchsia-400/[.06] p-4">
                      <p className="text-sm font-medium text-slate-100">{selectedEmail.situation.response_question}</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {selectedEmail.situation.reply_recommended && <button onClick={prepareReply} className="flex items-center gap-2 rounded-xl bg-fuchsia-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-fuchsia-300"><FileText size={15} /> Sim, preparar resposta</button>}
                        {selectedEmail.situation.reply_recommended && <button onClick={skipReply} className="rounded-xl border border-white/10 px-4 py-2 text-sm text-slate-300 transition hover:bg-white/[.05]">Não precisa responder</button>}
                        {selectedEmail.url && <a href={selectedEmail.url} target="_blank" rel="noreferrer" className="flex items-center gap-2 rounded-xl border border-white/10 px-4 py-2 text-sm text-slate-300 transition hover:bg-white/[.05]"><ExternalLink size={15} /> Abrir no Gmail</a>}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {draft && <div className="absolute inset-0 z-10 flex flex-col bg-[#0a0d15]">
              <div className="flex items-center justify-between border-b border-white/[.08] px-5 py-4"><div><h3 className="font-semibold text-slate-100">Prévia da resposta</h3><p className="text-xs text-slate-500">Revise antes de enviar para aprovação.</p></div><button onClick={() => setDraft(null)} className="rounded-lg p-2 text-slate-500 hover:bg-white/[.05] hover:text-white"><X size={17} /></button></div>
              <div className="flex-1 space-y-3 overflow-y-auto p-5">
                <Field label="Destinatário"><input value={draft.recipients} onChange={(event) => setDraft({ ...draft, recipients: event.target.value })} className="vampira-input" /></Field>
                <Field label="Assunto"><input value={draft.subject} onChange={(event) => setDraft({ ...draft, subject: event.target.value })} className="vampira-input" /></Field>
                <Field label="Mensagem"><textarea value={draft.body} onChange={(event) => setDraft({ ...draft, body: event.target.value })} rows={17} className="vampira-input resize-none leading-6" /></Field>
                {draft.body.includes('[Data]') && <p className="flex items-center gap-2 text-xs text-amber-300"><AlertCircle size={13} /> Substitua [Data] antes de enviar para aprovação.</p>}
              </div>
              <div className="border-t border-white/[.08] p-4"><button onClick={() => void submitDraft()} disabled={queueing || draft.body.includes('[Data]')} className="flex w-full items-center justify-center gap-2 rounded-xl bg-fuchsia-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-fuchsia-300 disabled:cursor-not-allowed disabled:opacity-40">{queueing ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />} Enviar para aprovação</button></div>
            </div>}
          </section>

          <aside className="grid content-start gap-4">
            {overview && Object.keys(overview.errors).length > 0 && <div className="rounded-2xl border border-amber-400/15 bg-amber-400/[.05] px-4 py-3 text-xs leading-5 text-amber-200/80">Algumas fontes estão temporariamente indisponíveis. As demais informações continuam atualizadas.</div>}
            <div id="vampira-analysis" className="scroll-mt-4"><VampiraAnalysis email={selectedEmail} noReplyNeeded={Boolean(selectedEmail && noReplyNeeded[selectedEmail.id])} onPrepare={prepareReply} onSkip={skipReply} onOpenCommitments={() => navigate('/commitments')} /></div>
            <div id="vampira-approvals" className="scroll-mt-4"><SidePanel title="Aguardando decisão" icon={<ShieldCheck size={17} />} tone="cyan">
              {approvals.length ? approvals.slice(0, 4).map((approval) => <div key={approval.id} className="rounded-xl border border-cyan-400/10 bg-cyan-400/[.04] p-3"><span className="text-[10px] font-semibold uppercase tracking-wider text-cyan-300">{approval.action_type === 'email_send' ? 'Resposta de e-mail' : approval.action_type}</span><p className="mt-1 text-xs leading-5 text-slate-400">{approval.description}</p><button onClick={() => setSelectedApproval(approval)} className="mt-2 rounded-lg border border-cyan-300/15 bg-cyan-300/[.07] px-3 py-1.5 text-xs font-semibold text-cyan-200 hover:bg-cyan-300/[.12]">Revisar decisão</button></div>) : <Empty icon={<ShieldCheck size={18} />} text="Nenhuma decisão pendente." />}
            </SidePanel></div>
          </aside>
        </div>
      </div>
      {showTemplates && <ResponseTemplatesModal
        onClose={() => setShowTemplates(false)}
        onSaved={(kind, template) => setOverview((current) => current ? {
          ...current,
          emails: current.emails.map((email) => email.situation.kind === kind ? {
            ...email,
            situation: { ...email.situation, suggested_tone: template.tone, response_template: template.body },
          } : email),
        } : current)}
      />}
      {selectedApproval && <ApprovalReviewModal
        approval={selectedApproval}
        acting={actingApproval}
        onClose={() => !actingApproval && setSelectedApproval(null)}
        onApprove={() => void decideApproval('approve')}
        onDeny={() => void decideApproval('deny')}
      />}
    </main>
  );
}

function ApprovalReviewModal({ approval, acting, onClose, onApprove, onDeny }: {
  approval: PendingApproval;
  acting: 'approve' | 'deny' | null;
  onClose: () => void;
  onApprove: () => void;
  onDeny: () => void;
}) {
  const recipients = Array.isArray(approval.payload.recipients)
    ? approval.payload.recipients.map(String).join(', ')
    : String(approval.payload.recipients || '—');
  const subject = String(approval.payload.subject || '—');
  const body = String(approval.payload.body || '');
  const isEmail = approval.action_type === 'email_send';

  return <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 p-3 backdrop-blur-sm sm:p-6">
    <div className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-[26px] border border-cyan-300/20 bg-[#0b0e16] shadow-[0_30px_100px_rgba(0,0,0,.7)]">
      <div className="flex items-center justify-between border-b border-white/[.08] px-5 py-4 sm:px-6">
        <div><div className="mb-1 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.18em] text-cyan-300"><ShieldCheck size={13} /> Aprovação final</div><h2 className="font-[var(--font-display)] text-xl font-semibold text-slate-100">{isEmail ? 'Revisar resposta de e-mail' : 'Revisar ação'}</h2></div>
        <button onClick={onClose} disabled={Boolean(acting)} className="rounded-lg p-2 text-slate-500 hover:bg-white/[.05] hover:text-white disabled:opacity-40"><X size={18} /></button>
      </div>
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5 sm:p-6">
        {isEmail ? <>
          <ReviewField label="Destinatário" value={recipients} />
          <ReviewField label="Assunto" value={subject} />
          <div><span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">Mensagem completa</span><div className="whitespace-pre-wrap break-words rounded-2xl border border-white/[.07] bg-black/20 p-4 text-sm leading-7 text-slate-300">{body}</div></div>
        </> : <div className="rounded-2xl border border-white/[.07] bg-black/20 p-4 text-sm leading-6 text-slate-300">{approval.description}</div>}
        <div className="rounded-xl border border-amber-400/15 bg-amber-400/[.05] p-3 text-xs leading-5 text-amber-200/80">Ao clicar em <strong>Aprovar e enviar</strong>, esta ação será executada. Recusar encerra a solicitação sem envio.</div>
      </div>
      <div className="grid gap-2 border-t border-white/[.08] p-4 sm:grid-cols-2 sm:px-6">
        <button onClick={onDeny} disabled={Boolean(acting)} className="inline-flex items-center justify-center gap-2 rounded-xl border border-rose-400/20 bg-rose-400/[.06] px-4 py-3 text-sm font-semibold text-rose-300 hover:bg-rose-400/[.1] disabled:opacity-40">{acting === 'deny' ? <Loader2 size={16} className="animate-spin" /> : <X size={16} />} Recusar</button>
        <button onClick={onApprove} disabled={Boolean(acting)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-sm font-semibold text-emerald-950 hover:bg-emerald-300 disabled:opacity-40">{acting === 'approve' ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />} Aprovar e enviar</button>
      </div>
    </div>
  </div>;
}

function ReviewField({ label, value }: { label: string; value: string }) {
  return <div><span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</span><div className="rounded-xl border border-white/[.07] bg-white/[.025] px-3.5 py-3 text-sm text-slate-200">{value}</div></div>;
}

function VampiraAnalysis({ email, noReplyNeeded, onPrepare, onSkip, onOpenCommitments }: {
  email: ProductivityEmail | undefined;
  noReplyNeeded: boolean;
  onPrepare: () => void;
  onSkip: () => void;
  onOpenCommitments: () => void;
}) {
  if (!email) {
    return <SidePanel title="Análise da Vampira" icon={<Sparkles size={17} />} tone="green"><Empty icon={<Sparkles size={20} />} text="Selecione um e-mail para receber a análise." /></SidePanel>;
  }
  const priorityLabel = email.situation.priority === 'high' ? 'Alta — atenção imediata'
    : email.situation.priority === 'medium' ? 'Média — revisar hoje'
      : email.situation.priority === 'low' ? 'Baixa' : 'Normal';
  return <SidePanel title="Análise da Vampira" icon={<Sparkles size={17} />} tone="green">
    <div className="rounded-xl border border-emerald-400/10 bg-emerald-400/[.04] p-3">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-300">Resumo rápido</span>
      <p className="mt-1.5 line-clamp-4 text-xs leading-5 text-slate-400">{email.preview || email.content}</p>
    </div>
    <AnalysisRow label="Situação" value={email.situation.label} />
    <AnalysisRow label="Urgência" value={priorityLabel} />
    <AnalysisRow label="Ação sugerida" value={email.situation.recommended_action} />
    <AnalysisRow label="Tom da resposta" value={email.situation.suggested_tone || 'Profissional'} />
    <AnalysisRow label="Anexos" value={email.attachments.length ? `${email.attachments.length} arquivo(s)` : 'Nenhum'} />
    {noReplyNeeded ? <div className="flex items-center gap-2 rounded-xl border border-emerald-400/15 bg-emerald-400/[.05] p-3 text-xs text-emerald-200"><CheckCircle2 size={15} /> Marcado como sem resposta necessária.</div> : email.situation.reply_recommended && <button onClick={onPrepare} className="flex w-full items-center justify-center gap-2 rounded-xl bg-fuchsia-400 px-3 py-2.5 text-xs font-semibold text-slate-950 hover:bg-fuchsia-300"><FileText size={14} /> Preparar resposta</button>}
    {!noReplyNeeded && email.situation.reply_recommended && <button onClick={onSkip} className="w-full rounded-xl border border-white/10 px-3 py-2 text-xs text-slate-400 hover:bg-white/[.04]">Não precisa responder</button>}
    <button onClick={onOpenCommitments} className="flex w-full items-center justify-center gap-2 rounded-xl border border-emerald-300/15 bg-emerald-300/[.05] px-3 py-2.5 text-xs font-semibold text-emerald-200 hover:bg-emerald-300/[.1]"><CheckCircle2 size={14} /> Ver compromissos relacionados</button>
  </SidePanel>;
}

function AnalysisRow({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-white/[.06] bg-white/[.02] p-3"><span className="block text-[9px] uppercase tracking-[.12em] text-slate-600">{label}</span><strong className="mt-1 block text-xs font-medium leading-5 text-slate-300">{value}</strong></div>;
}

const TEMPLATE_LABELS: Record<string, string> = {
  legal: 'Jurídico / prazo',
  financial: 'Financeiro',
  document: 'Documento',
  meeting: 'Reunião',
  important: 'Importante geral',
  general: 'Mensagem geral',
};

function ResponseTemplatesModal({ onClose, onSaved }: {
  onClose: () => void;
  onSaved: (kind: string, template: VampiraResponseTemplate) => void;
}) {
  const [templates, setTemplates] = useState<Record<string, VampiraResponseTemplate>>({});
  const [selected, setSelected] = useState('document');
  const [editing, setEditing] = useState<VampiraResponseTemplate>({ tone: '', body: '' });
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void fetchVampiraResponseTemplates()
      .then((result) => {
        setTemplates(result);
        setEditing(result.document || Object.values(result)[0] || { tone: '', body: '' });
      })
      .catch((error) => toast.error(error instanceof Error ? error.message : 'Não foi possível carregar os modelos.'))
      .finally(() => setLoadingTemplates(false));
  }, []);

  const choose = (kind: string) => {
    setSelected(kind);
    setEditing(templates[kind] || { tone: '', body: '' });
  };

  const save = async () => {
    setSaving(true);
    try {
      const saved = await updateVampiraResponseTemplate(selected, editing);
      setTemplates((current) => ({ ...current, [selected]: saved }));
      setEditing(saved);
      onSaved(selected, saved);
      toast.success('Modelo salvo para HUD e WhatsApp.');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Não foi possível salvar o modelo.');
    } finally {
      setSaving(false);
    }
  };

  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-3 backdrop-blur-sm sm:p-6">
    <div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-[26px] border border-fuchsia-300/20 bg-[#0b0e16] shadow-[0_30px_100px_rgba(0,0,0,.65)]">
      <div className="flex items-center justify-between border-b border-white/[.08] px-5 py-4 sm:px-6">
        <div><h2 className="font-[var(--font-display)] text-xl font-semibold text-slate-100">Modelos de resposta</h2><p className="mt-1 text-xs text-slate-500">Os mesmos textos são usados na HUD e no WhatsApp.</p></div>
        <button onClick={onClose} className="rounded-lg p-2 text-slate-500 hover:bg-white/[.05] hover:text-white"><X size={18} /></button>
      </div>
      {loadingTemplates ? <LoadingState /> : <div className="grid min-h-0 flex-1 md:grid-cols-[220px_minmax(0,1fr)]">
        <nav className="border-b border-white/[.07] p-3 md:border-b-0 md:border-r">
          {Object.keys(TEMPLATE_LABELS).map((kind) => <button key={kind} onClick={() => choose(kind)} className={`mb-1 w-full rounded-xl px-3 py-2.5 text-left text-sm transition ${selected === kind ? 'bg-fuchsia-400/12 font-semibold text-fuchsia-200' : 'text-slate-500 hover:bg-white/[.04] hover:text-slate-300'}`}>{TEMPLATE_LABELS[kind]}</button>)}
        </nav>
        <div className="min-h-0 space-y-4 overflow-y-auto p-5 sm:p-6">
          <Field label="Tom"><input value={editing.tone} onChange={(event) => setEditing({ ...editing, tone: event.target.value })} className="vampira-input" /></Field>
          <Field label="Texto do modelo"><textarea value={editing.body} onChange={(event) => setEditing({ ...editing, body: event.target.value })} rows={17} className="vampira-input resize-none leading-6" /></Field>
          <div className="rounded-xl border border-amber-400/15 bg-amber-400/[.05] p-3 text-xs leading-5 text-amber-200/80">Mantenha os campos <strong>[Nome]</strong>, <strong>[Assunto]</strong> e <strong>[Data]</strong>. A data será obrigatoriamente confirmada antes da aprovação.</div>
        </div>
      </div>}
      <div className="flex justify-end gap-2 border-t border-white/[.08] px-5 py-4 sm:px-6"><button onClick={onClose} className="rounded-xl border border-white/10 px-4 py-2 text-sm text-slate-400 hover:bg-white/[.04]">Fechar</button><button onClick={() => void save()} disabled={saving || loadingTemplates} className="inline-flex items-center gap-2 rounded-xl bg-fuchsia-400 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-fuchsia-300 disabled:opacity-40">{saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} Salvar modelo</button></div>
    </div>
  </div>;
}

function Metric({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: number; tone: 'purple' | 'orange' | 'green' | 'cyan' }) {
  const colors = { purple: 'text-fuchsia-300 bg-fuchsia-400/10', orange: 'text-orange-300 bg-orange-400/10', green: 'text-emerald-300 bg-emerald-400/10', cyan: 'text-cyan-300 bg-cyan-400/10' };
  return <div className="min-w-[112px] rounded-2xl border border-white/10 bg-black/20 px-3 py-2.5"><div className={`mb-1 flex items-center gap-1.5 ${colors[tone]}`}>{icon}<strong className="text-lg">{value}</strong></div><span className="text-[10px] uppercase tracking-[.12em] text-slate-500">{label}</span></div>;
}

function Filter({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return <button onClick={onClick} className={`rounded-lg px-3 py-1.5 text-xs transition ${active ? 'bg-fuchsia-400/15 text-fuchsia-300' : 'text-slate-500 hover:bg-white/[.04] hover:text-slate-300'}`}>{children}</button>;
}

function SituationBadge({ situation }: { situation: ProductivityEmail['situation'] }) {
  const colors = {
    high: 'border-rose-400/20 bg-rose-400/10 text-rose-300',
    medium: 'border-amber-400/20 bg-amber-400/10 text-amber-300',
    normal: 'border-cyan-400/20 bg-cyan-400/10 text-cyan-300',
    low: 'border-slate-400/15 bg-slate-400/[.06] text-slate-400',
  };
  return <span className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider ${colors[situation.priority]}`}>{situation.label}</span>;
}

function SidePanel({ title, icon, tone, children }: { title: string; icon: React.ReactNode; tone: 'orange' | 'green' | 'cyan'; children: React.ReactNode }) {
  const colors = { orange: 'text-orange-300', green: 'text-emerald-300', cyan: 'text-cyan-300' };
  return <section className="rounded-[24px] border border-white/[.08] bg-[#0c1019] p-4"><h2 className={`mb-3 flex items-center gap-2 font-[var(--font-display)] text-sm font-semibold uppercase tracking-[.12em] ${colors[tone]}`}>{icon}{title}</h2><div className="space-y-2">{children}</div></section>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-slate-500">{label}</span>{children}</label>;
}

function Empty({ icon, text }: { icon: React.ReactNode; text: string }) {
  return <div className="flex min-h-[82px] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-white/10 p-4 text-center text-xs text-slate-600">{icon}{text}</div>;
}

function LoadingState() {
  return <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-500"><Loader2 size={17} className="animate-spin" /> Carregando...</div>;
}
