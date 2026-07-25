import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  History,
  Loader2,
  RefreshCw,
  ShieldCheck,
  ShieldX,
} from 'lucide-react';
import {
  fetchGovernanceHistory,
  fetchGovernanceHistoryStatus,
  fetchGovernanceOverview,
  fetchGovernanceStatus,
  type GovernanceHistory as GovernanceHistoryData,
  type GovernanceOverview,
  type GovernanceStatus,
} from '../lib/api';

const number = (value: number | undefined) => (value ?? 0).toLocaleString();

function timeLabel(value?: string) {
  if (!value) return 'Not available';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <section className={`hud-panel p-5 ${className}`}>{children}</section>;
}

function Metric({ label, value, tone = 'accent' }: { label: string; value: number; tone?: 'accent' | 'warning' | 'error' | 'success' }) {
  const colors = {
    accent: 'var(--color-accent)',
    warning: 'var(--color-warning)',
    error: 'var(--color-error)',
    success: 'var(--color-success)',
  };
  return (
    <div className="rounded-xl p-4" style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}>
      <div className="hud-label">{label}</div>
      <div className="mt-2 text-2xl font-semibold tabular-nums" style={{ color: colors[tone] }}>{number(value)}</div>
    </div>
  );
}

export function GovernancePage() {
  const [days, setDays] = useState(30);
  const [status, setStatus] = useState<GovernanceStatus | null>(null);
  const [historyStatus, setHistoryStatus] = useState<GovernanceStatus | null>(null);
  const [overview, setOverview] = useState<GovernanceOverview | null>(null);
  const [history, setHistory] = useState<GovernanceHistoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [nextStatus, nextOverview, nextHistoryStatus, nextHistory] = await Promise.all([
        fetchGovernanceStatus(),
        fetchGovernanceOverview(),
        fetchGovernanceHistoryStatus(),
        fetchGovernanceHistory(days),
      ]);
      setStatus(nextStatus);
      setOverview(nextOverview);
      setHistoryStatus(nextHistoryStatus);
      setHistory(nextHistory);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Governance data could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { void refresh(); }, [refresh]);

  const safe = status?.mode === 'read_only' && historyStatus?.mode === 'read_only' &&
    status.can_execute === false && status.external_actions_enabled === false;
  const summary = overview?.summary ?? {};
  const totals = history?.totals ?? {};

  return (
    <div className="flex-1 overflow-y-auto px-4 py-8 sm:px-6 sm:py-10">
      <div className="mx-auto max-w-6xl">
        <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2 hud-label"><ShieldCheck size={14} /> Agent safety control</div>
            <h1 className="hud-title text-2xl font-semibold">Governance</h1>
            <p className="mt-2 max-w-2xl text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              Read-only visibility into plans, execution receipts, policies and audit events. This screen cannot approve or execute actions.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
              History
              <select value={days} onChange={(event) => setDays(Number(event.target.value))} className="ml-2 rounded-lg px-2 py-1.5" style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text)' }}>
                <option value={7}>7 days</option><option value={30}>30 days</option><option value={90}>90 days</option><option value={365}>365 days</option>
              </select>
            </label>
            <button onClick={() => void refresh()} disabled={loading} className="rounded-lg p-2 disabled:opacity-50" aria-label="Refresh governance data" style={{ border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}>
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </header>

        {error && (
          <div className="mb-5 flex items-start gap-3 rounded-xl p-4 text-sm" style={{ border: '1px solid color-mix(in srgb, var(--color-error) 35%, transparent)', background: 'color-mix(in srgb, var(--color-error) 8%, transparent)' }}>
            <ShieldX size={18} style={{ color: 'var(--color-error)' }} />
            <div><div className="font-medium">Governance service unavailable</div><div className="mt-1" style={{ color: 'var(--color-text-secondary)' }}>{error}</div></div>
          </div>
        )}

        {loading && !overview ? (
          <div className="flex min-h-64 items-center justify-center gap-3" style={{ color: 'var(--color-text-secondary)' }}><Loader2 className="animate-spin" size={20} /> Loading governance controls…</div>
        ) : (
          <>
            <Panel className="mb-4">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  {safe ? <CheckCircle2 size={24} style={{ color: 'var(--color-success)' }} /> : <AlertTriangle size={24} style={{ color: 'var(--color-warning)' }} />}
                  <div><h2 className="font-medium">{safe ? 'Read-only boundary active' : 'Safety status needs attention'}</h2><p className="mt-1 text-xs" style={{ color: 'var(--color-text-secondary)' }}>Approval, rejection, execution and external actions remain disabled.</p></div>
                </div>
                <span className="rounded-full px-3 py-1 text-xs font-medium" style={{ color: safe ? 'var(--color-success)' : 'var(--color-warning)', background: safe ? 'color-mix(in srgb, var(--color-success) 10%, transparent)' : 'var(--color-accent-amber-subtle)' }}>{safe ? 'SAFE · READ ONLY' : 'VERIFY CONFIGURATION'}</span>
              </div>
            </Panel>

            <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
              <Metric label="Pending review" value={summary.plans_pending} tone={summary.plans_pending ? 'warning' : 'success'} />
              <Metric label="Recent blocks" value={summary.audit_blocked} tone={summary.audit_blocked ? 'warning' : 'success'} />
              <Metric label="Recent failures" value={summary.audit_failed} tone={summary.audit_failed ? 'error' : 'success'} />
              <Metric label="Active alerts" value={summary.alerts_total} tone={summary.alerts_total ? 'warning' : 'success'} />
            </div>

            <div className="mb-4 grid gap-4 lg:grid-cols-5">
              <Panel className="lg:col-span-3">
                <div className="hud-panel-head mb-4 flex items-center gap-2"><AlertTriangle size={16} /> Current alerts</div>
                {overview?.alerts.length ? <div className="space-y-2">{overview.alerts.map((alert) => <div key={alert.code} className="flex gap-3 rounded-lg p-3 text-sm" style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}><span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ background: alert.level === 'high' ? 'var(--color-error)' : 'var(--color-warning)' }} /><div><div className="font-medium">{alert.code.replaceAll('_', ' ')}</div><div className="mt-1" style={{ color: 'var(--color-text-secondary)' }}>{alert.message}</div></div></div>)}</div> : <div className="flex min-h-28 items-center justify-center gap-2 text-sm" style={{ color: 'var(--color-text-secondary)' }}><CheckCircle2 size={17} style={{ color: 'var(--color-success)' }} /> No active governance alerts</div>}
              </Panel>
              <Panel className="lg:col-span-2">
                <div className="hud-panel-head mb-4 flex items-center gap-2"><Clock3 size={16} /> Current snapshot</div>
                <dl className="space-y-3 text-sm">
                  {[['Plans visible', summary.plans_visible], ['Receipts visible', summary.receipts_visible], ['Policies', summary.policies_total], ['Audit events', summary.audit_events_visible]].map(([label, value]) => <div key={String(label)} className="flex justify-between"><dt style={{ color: 'var(--color-text-secondary)' }}>{label}</dt><dd className="font-mono tabular-nums">{number(value as number)}</dd></div>)}
                </dl>
                <div className="mt-5 border-t pt-4 text-xs" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-tertiary)' }}>Generated {timeLabel(overview?.generated_at)}</div>
              </Panel>
            </div>

            <Panel>
              <div className="hud-panel-head mb-4 flex flex-wrap items-center justify-between gap-3"><span className="flex items-center gap-2"><History size={16} /> {days}-day history</span><span className="text-xs font-normal" style={{ color: 'var(--color-text-tertiary)' }}>Updated {timeLabel(history?.generated_at)}</span></div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <Metric label="Plans" value={totals.plans} /><Metric label="Executions" value={totals.executions} /><Metric label="Audit events" value={totals.audit_events} /><Metric label="Blocked" value={totals.blocked} tone={totals.blocked ? 'warning' : 'success'} /><Metric label="Failed" value={totals.failed} tone={totals.failed ? 'error' : 'success'} /><Metric label="Timeouts" value={totals.timeouts} tone={totals.timeouts ? 'error' : 'success'} />
              </div>
            </Panel>
          </>
        )}
      </div>
    </div>
  );
}
