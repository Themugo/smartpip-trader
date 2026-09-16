import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  AlertTriangle,
  BarChart3,
  BookOpen,
  ArrowDownRight,
  ArrowUpRight,
  BrainCircuit,
  Check,
  ChevronRight,
  CircleDollarSign,
  Gauge,
  Loader2,
  PauseCircle,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Zap,
} from 'lucide-react';
import { api } from '../lib/api';
import type { Trade, TradeStatistics, SystemSettings } from '../lib/supabase';
import type { TickData } from '../hooks/useDerivTicks';
import type { EndUserView } from './EndUserShell';

interface Props {
  view: EndUserView;
  userEmail: string;
  tickData: TickData;
  trades: Trade[];
  stats: TradeStatistics | null;
  settings: SystemSettings | null;
  dataLoading: boolean;
  onSwitchSymbol: (symbol: string) => void;
  onReconnect: () => void;
  onStartAuto: () => Promise<void>;
  onStopAuto: () => Promise<void>;
  onRefresh: () => Promise<void>;
}

const markets = ['R_50', 'R_75', 'R_100', '1HZ50V', '1HZ75V', '1HZ100V'];

function fmtMoney(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return '—';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)} USD`;
}

function Sparkline({ values, positive = true }: { values: number[]; positive?: boolean }) {
  if (values.length < 2) return <div className="h-14" />;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values.map((v, i) => `${(i / (values.length - 1)) * 100},${54 - ((v - min) / range) * 48}`).join(' ');
  return <svg viewBox="0 0 100 60" preserveAspectRatio="none" className="h-14 w-full"><polyline fill="none" stroke={positive ? '#19d3ae' : '#ef4444'} strokeWidth="2" points={points} /></svg>;
}

function SectionTitle({ eyebrow, title, action }: { eyebrow?: string; title: string; action?: ReactNode }) {
  return <div className="flex items-end justify-between mb-4"><div>{eyebrow && <div className="text-[10px] uppercase tracking-[0.22em] text-slate-500 mb-1">{eyebrow}</div>}<h2 className="text-lg sm:text-xl font-bold text-white">{title}</h2></div>{action}</div>;
}

export function EndUserDashboard({ view, userEmail, tickData, trades, stats, settings, dataLoading, onSwitchSymbol, onReconnect, onStartAuto, onStopAuto, onRefresh }: Props) {
  const [ai, setAi] = useState<{ confidence?: number; direction?: string; consensus?: Record<string, unknown> | null; entropy_pct?: number; pattern_health?: Record<string, unknown> } | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [tradeAmount, setTradeAmount] = useState(1);
  const [duration, setDuration] = useState(1);
  const [tradeState, setTradeState] = useState<{ kind: 'idle' | 'working' | 'success' | 'error'; message?: string }>({ kind: 'idle' });

  const loadAi = useCallback(async () => {
    setAiLoading(true);
    setAiError(null);
    const response = await api.ai.getSignals();
    if (response.data) {
      const consensus = response.data.consensus;
      const confidence = typeof consensus?.confidence === 'number' ? consensus.confidence : undefined;
      const direction = typeof consensus?.prediction === 'string' ? consensus.prediction : typeof consensus?.direction === 'string' ? consensus.direction : undefined;
      setAi({ confidence, direction, consensus, entropy_pct: response.data.entropy_pct, pattern_health: response.data.pattern_health });
    } else {
      setAi(null);
      setAiError(response.error || 'AI analysis is temporarily unavailable.');
    }
    setAiLoading(false);
  }, []);

  useEffect(() => {
    if (!['trade', 'ai', 'auto'].includes(view)) return;
    void loadAi();
    const id = window.setInterval(() => void loadAi(), 5000);
    return () => window.clearInterval(id);
  }, [loadAi, view]);

  const confidence = ai?.confidence ?? 0;
  const direction = (ai?.direction || '').toUpperCase();
  const qualified = confidence >= (settings?.min_confidence ?? 70);
  const priceValues = tickData.priceHistory;
  const pnlValues = useMemo(() => {
    let running = 0;
    return trades.slice(-30).reverse().map((t) => { running += Number(t.profit || 0); return running; }).reverse();
  }, [trades]);

  const execute = async (side: 'CALL' | 'PUT') => {
    if (!tickData.connected) {
      setTradeState({ kind: 'error', message: 'Market feed is offline. Reconnect before submitting a trade.' });
      return;
    }
    if (!Number.isFinite(tradeAmount) || tradeAmount < 0.35) {
      setTradeState({ kind: 'error', message: 'Stake must be at least 0.35 USD.' });
      return;
    }
    if (!Number.isInteger(duration) || duration < 1) {
      setTradeState({ kind: 'error', message: 'Duration must be a positive whole number of ticks.' });
      return;
    }
    setTradeState({ kind: 'working' });
    const response = await api.executeTrade({
      contract_type: 'RISEFALL', symbol: tickData.symbol, amount: tradeAmount, duration, duration_unit: 't', prediction: side,
    });
    if (response.data?.success) {
      const contractId = response.data.contract_id || 'pending';
      if (contractId !== 'pending') {
        const journal = await api.userJournal.recordExecution({
          contractId,
          symbol: tickData.symbol,
          contractType: 'RISEFALL',
          direction: side,
          entryPrice: tickData.price,
          entryDigit: tickData.lastDigit,
          amount: tradeAmount,
          confidence,
        });
        if (journal.error) {
          setTradeState({ kind: 'success', message: `Trade accepted • ${contractId}. Journal sync is pending.` });
          return;
        }
      }
      setTradeState({ kind: 'success', message: `Trade accepted • ${contractId}` });
    } else setTradeState({ kind: 'error', message: response.error || 'Trade was blocked by the execution service.' });
  };

  if (view === 'ai') return <AIView ai={ai} loading={aiLoading} error={aiError} tickData={tickData} qualified={qualified} onRefresh={loadAi} />;
  if (view === 'auto') return <AutoView settings={settings} ai={ai} onStart={onStartAuto} onStop={onStopAuto} />;
  if (view === 'performance') return <PerformanceView stats={stats} trades={trades} pnlValues={pnlValues} />;
  if (view === 'journal') return <JournalView trades={trades} />;
  if (view === 'settings') return <SettingsView userEmail={userEmail} settings={settings} />;

  return (
    <div className="space-y-5">
      <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-4">
        <div>
          <div className="text-xs text-slate-500 mb-1">Welcome back</div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight">Trade with intelligence.</h1>
          <p className="text-sm text-slate-500 mt-1">SmartPip watches the market so you can focus on qualified opportunities.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onRefresh} className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-slate-300 hover:bg-white/[0.06]"><RefreshCw className="inline h-3.5 w-3.5 mr-1.5" />Refresh</button>
          <button onClick={() => void loadAi()} className="rounded-xl border border-teal-400/20 bg-teal-400/[0.06] px-3 py-2 text-xs text-teal-300"><Sparkles className="inline h-3.5 w-3.5 mr-1.5" />Refresh AI</button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2.5">
        {markets.map((market) => <button key={market} onClick={() => onSwitchSymbol(market)} className={`rounded-xl border p-3 text-left transition-all ${tickData.symbol === market ? 'border-red-500/40 bg-red-500/[0.08]' : 'border-white/[0.07] bg-white/[0.025] hover:bg-white/[0.05]'}`}><div className="text-xs font-bold text-slate-200">{market}</div><div className="mt-1 text-sm font-semibold">{tickData.symbol === market && tickData.price ? tickData.price.toFixed(2) : '—'}</div><div className="mt-1 text-[10px] text-slate-500">Synthetic market</div></button>)}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.8fr)_340px] gap-5">
        <section className="rounded-2xl border border-white/[0.08] bg-[#091321]/90 overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 border-b border-white/[0.06]">
            <div><div className="flex items-center gap-2"><h2 className="text-2xl font-black">{tickData.symbol}</h2><span className="rounded-full bg-emerald-400/10 px-2 py-1 text-[10px] font-semibold text-emerald-300">{tickData.connected ? 'LIVE' : 'OFFLINE'}</span></div><p className="text-xs text-slate-500 mt-1">Live market price • {tickData.tickCount.toLocaleString()} ticks</p></div>
            <div className="flex items-end gap-3"><div className="text-right"><div className="text-2xl font-bold tabular-nums">{tickData.price ? tickData.price.toFixed(2) : '—'}</div><div className="text-xs text-slate-500">Latency {tickData.latencyMs || '—'} ms</div></div>{!tickData.connected && <button onClick={onReconnect} className="rounded-lg border border-amber-400/20 px-2.5 py-2 text-[10px] text-amber-300 hover:bg-amber-400/10">Reconnect</button>}</div>
          </div>
          <div className="px-4 pt-4"><div className="flex items-center gap-1.5 mb-2">{['1M', '5M', '15M', '1H'].map((tf) => <button key={tf} className={`rounded-lg px-3 py-1.5 text-[11px] ${tf === '5M' ? 'bg-red-500 text-white' : 'bg-white/[0.04] text-slate-500'}`}>{tf}</button>)}</div><div className="h-[310px] rounded-xl bg-[#060d18] border border-white/[0.05] p-3"><Sparkline values={priceValues} positive={true} /><div className="h-px bg-white/[0.04]" /><div className="mt-4 grid grid-cols-6 gap-2 items-end h-20">{(tickData.digitHistory.slice(-24).length ? tickData.digitHistory.slice(-24) : Array.from({ length: 24 }, () => 0)).map((d, i) => <div key={`${d}-${i}`} className="rounded-sm bg-slate-700/60" style={{ height: `${Math.max(8, d * 9)}%` }} />)}</div></div></div>
          <div className="grid grid-cols-3 gap-3 p-4"><Metric label="AI confidence" value={`${confidence || 0}%`} accent={qualified ? 'text-teal-300' : 'text-amber-300'} /><Metric label="Market state" value={direction || 'WAIT'} /><Metric label="Entropy" value={`${ai?.entropy_pct?.toFixed(0) ?? '—'}%`} /></div>
        </section>

        <section className="rounded-2xl border border-white/[0.08] bg-[#091321]/90 p-4 flex flex-col">
          <SectionTitle eyebrow="SmartPip AI" title="Decision engine" action={<span className="text-[10px] text-teal-300">● LIVE</span>} />
          <div className={`rounded-2xl border p-5 ${qualified ? 'border-teal-400/20 bg-teal-400/[0.05]' : 'border-amber-400/15 bg-amber-400/[0.04]'}`}>
            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Current decision</div>
            <div className="mt-2 flex items-end justify-between"><div className={`text-4xl font-black ${qualified ? 'text-teal-300' : 'text-amber-300'}`}>{qualified ? direction || 'QUALIFIED' : 'WAIT'}</div><div className="text-2xl font-bold">{confidence || 0}%</div></div>
            <p className="mt-3 text-xs leading-5 text-slate-400">{qualified ? 'The backend AI signal currently meets the configured confidence threshold. Review risk and execution conditions before trading.' : 'Conditions are below the configured confidence threshold. SmartPip will keep monitoring rather than force an entry.'}</p>
          </div>
          <div className="mt-3 space-y-2 text-xs"><StatusRow label="Market feed" ok={tickData.connected} /><StatusRow label="AI analysis" ok={Boolean(ai)} /><StatusRow label="Confidence gate" ok={qualified} /><StatusRow label="Risk review" ok={false} warning /></div>
          <button onClick={() => void loadAi()} className="mt-auto pt-5 flex items-center justify-center gap-2 text-xs text-slate-300 hover:text-white">View full AI analysis <ChevronRight className="h-4 w-4" /></button>
        </section>
      </div>

      <section className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.4fr)_minmax(320px,.8fr)] gap-5">
        <div className="rounded-2xl border border-white/[0.08] bg-[#091321]/90 p-4">
          <SectionTitle eyebrow="Execution" title="Manual trade" />
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-3"><label className="block text-xs text-slate-500">Stake (USD)<input type="number" min="0.35" step="0.01" value={tradeAmount} onChange={(e) => setTradeAmount(Number(e.target.value))} className="mt-1.5 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-3 text-sm text-white outline-none focus:border-red-500/50" /></label><label className="block text-xs text-slate-500">Duration (ticks)<input type="number" min="1" step="1" value={duration} onChange={(e) => setDuration(Number(e.target.value))} className="mt-1.5 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-3 text-sm text-white outline-none focus:border-red-500/50" /></label></div>
            <div className="rounded-xl border border-white/[0.06] bg-black/20 p-3"><div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Execution rule</div><div className="mt-2 flex items-center gap-2 text-sm font-semibold"><ShieldCheck className="h-4 w-4 text-teal-400" /> Backend approval required</div><p className="mt-2 text-[11px] leading-5 text-slate-500">Your browser sends an order request only. The backend applies probability, calibration, risk and market-freshness gates.</p></div>
          </div>
          <div className="grid grid-cols-2 gap-3 mt-4"><button disabled={tradeState.kind === 'working' || !tickData.connected || !qualified || direction !== 'CALL'} onClick={() => void execute('CALL')} className="rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 py-3 font-bold text-sm flex items-center justify-center gap-2"><ArrowUpRight className="h-4 w-4" />CALL</button><button disabled={tradeState.kind === 'working' || !tickData.connected || !qualified || direction !== 'PUT'} onClick={() => void execute('PUT')} className="rounded-xl bg-red-500 hover:bg-red-400 disabled:opacity-50 py-3 font-bold text-sm flex items-center justify-center gap-2"><ArrowDownRight className="h-4 w-4" />PUT</button></div>
          {tradeState.kind !== 'idle' && <div className={`mt-3 rounded-xl border p-3 text-xs ${tradeState.kind === 'success' ? 'border-emerald-400/20 bg-emerald-400/[0.05] text-emerald-300' : tradeState.kind === 'error' ? 'border-red-400/20 bg-red-400/[0.05] text-red-300' : 'border-white/10 bg-white/[0.03] text-slate-400'}`}>{tradeState.kind === 'working' && <Loader2 className="inline h-4 w-4 mr-2 animate-spin" />}{tradeState.message || 'Submitting through the execution service…'}</div>}
        </div>
        <div className="rounded-2xl border border-red-500/15 bg-gradient-to-br from-red-500/[0.08] to-transparent p-4"><div className="flex items-center gap-2 text-sm font-bold"><Zap className="h-4 w-4 text-red-400" />Auto execution</div><p className="mt-2 text-xs leading-5 text-slate-400">Let the same AI and risk gates monitor qualified setups. Auto execution should remain disabled until your Deriv session and user risk controls are configured.</p><div className="mt-5 flex items-center justify-between"><div><div className="text-[10px] uppercase tracking-widest text-slate-500">Current state</div><div className="mt-1 text-lg font-bold">{settings?.auto_trading ? 'ACTIVE' : 'OFF'}</div></div><button onClick={() => window.dispatchEvent(new CustomEvent('smartpip:auto'))} className="rounded-xl border border-red-400/20 px-3 py-2 text-xs text-red-300 hover:bg-red-500/10">Configure</button></div></div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5"><PerformanceMini stats={stats} pnlValues={pnlValues} /><RecentTrades trades={trades} /></div>
      {dataLoading && <div className="text-center text-[11px] text-slate-600">Refreshing account data…</div>}
    </div>
  );
}

function AIView({ ai, loading, error, tickData, qualified, onRefresh }: { ai: EndUserDashboardPropsAI; loading: boolean; error: string | null; tickData: TickData; qualified: boolean; onRefresh: () => Promise<void> }) {
  const confidence = ai?.confidence ?? 0;
  return <div className="space-y-5"><PageHeader icon={<BrainCircuit />} title="AI Analysis" subtitle="A focused view of the evidence behind SmartPip's current market decision." onRefresh={onRefresh} loading={loading} /><div className="grid grid-cols-1 xl:grid-cols-[1.1fr_.9fr] gap-5"><div className="rounded-2xl border border-white/[0.08] bg-[#091321]/90 p-6"><div className="text-xs uppercase tracking-widest text-slate-500">{tickData.symbol} • current decision</div><div className="mt-5 flex flex-col sm:flex-row sm:items-center gap-6"><div className={`h-36 w-36 rounded-full border-[10px] ${qualified ? 'border-teal-400/60' : 'border-amber-400/40'} flex items-center justify-center`}><div className="text-center"><div className="text-3xl font-black">{confidence}%</div><div className="text-[10px] text-slate-500">confidence</div></div></div><div><div className={`text-4xl font-black ${qualified ? 'text-teal-300' : 'text-amber-300'}`}>{qualified ? (ai?.direction || 'QUALIFIED') : 'WAIT'}</div><p className="mt-2 max-w-lg text-sm leading-6 text-slate-400">{qualified ? 'The current backend consensus meets the configured threshold. This is a signal for review, not a guarantee of outcome.' : 'The current evidence does not meet the configured threshold. SmartPip is deliberately withholding an entry.'}</p></div></div></div><div className="rounded-2xl border border-white/[0.08] bg-[#091321]/90 p-6 space-y-3"><SectionTitle title="Evidence snapshot" /> {error && <div className="rounded-xl border border-red-400/20 bg-red-400/[0.05] p-3 text-xs text-red-300">{error}</div>} <StatusRow label="Market feed" ok={tickData.connected} /><StatusRow label="Backend consensus" ok={Boolean(ai)} /><StatusRow label="Confidence threshold" ok={qualified} /><StatusRow label="Randomness / entropy" ok={(ai?.entropy_pct ?? 100) < 80} warning /><div className="mt-5 rounded-xl bg-black/20 p-4 text-xs text-slate-500">AI confidence is informational until the backend risk and approval gates also pass.</div></div></div></div>;
}

type EndUserDashboardPropsAI = { confidence?: number; direction?: string; consensus?: Record<string, unknown> | null; entropy_pct?: number; pattern_health?: Record<string, unknown> } | null;

function AutoView({ settings, ai, onStart, onStop }: { settings: SystemSettings | null; ai: EndUserDashboardPropsAI; onStart: () => Promise<void>; onStop: () => Promise<void> }) {
  const active = Boolean(settings?.auto_trading);
  const [working, setWorking] = useState(false);
  const run = async (action: () => Promise<void>) => {
    setWorking(true);
    try { await action(); } finally { setWorking(false); }
  };
  return <div className="space-y-5"><PageHeader icon={<Zap />} title="Auto Execution" subtitle="Controlled automation: analyse first, pass risk gates, then execute." /><div className="grid grid-cols-1 lg:grid-cols-3 gap-5"><div className="lg:col-span-2 rounded-2xl border border-white/[0.08] bg-[#091321]/90 p-6"><div className="flex items-center justify-between"><div><div className="text-xs uppercase tracking-widest text-slate-500">Execution service</div><div className="mt-1 text-2xl font-black">{active ? 'Active' : 'Ready'}</div></div><div className={`rounded-full px-3 py-1.5 text-xs ${active ? 'bg-teal-400/10 text-teal-300' : 'bg-white/5 text-slate-400'}`}>● {active ? 'Running' : 'Standby'}</div></div><div className="grid sm:grid-cols-3 gap-3 mt-6"><Metric label="AI confidence" value={`${ai?.confidence ?? 0}%`} accent="text-teal-300" /><Metric label="Min confidence" value={`${settings?.min_confidence ?? 70}%`} /><Metric label="Max/hour" value={`${settings?.max_trades_per_hour ?? '—'}`} /></div><div className="mt-6 flex flex-wrap gap-3"><button onClick={() => void run(onStart)} disabled={active || working} className="rounded-xl bg-red-500 px-4 py-3 text-sm font-bold disabled:opacity-40"><Play className="inline h-4 w-4 mr-2" />Enable</button><button onClick={() => void run(onStop)} disabled={!active || working} className="rounded-xl border border-white/10 px-4 py-3 text-sm font-bold disabled:opacity-40"><PauseCircle className="inline h-4 w-4 mr-2" />Pause</button></div><div className="mt-5 rounded-xl border border-amber-400/15 bg-amber-400/[0.04] p-4 text-xs leading-5 text-amber-200/80"><AlertTriangle className="inline h-4 w-4 mr-2" />Automation only operates within the server-side controls currently configured for the trading service.</div></div><div className="rounded-2xl border border-teal-400/15 bg-teal-400/[0.04] p-6"><ShieldCheck className="h-7 w-7 text-teal-300" /><h3 className="mt-4 font-bold">Capital discipline</h3><p className="mt-2 text-xs leading-5 text-slate-400">The objective is not maximum activity. Weak conditions can be skipped, and backend approval remains authoritative.</p></div></div></div>;
}

function PerformanceView({ stats, trades, pnlValues }: { stats: TradeStatistics | null; trades: Trade[]; pnlValues: number[] }) { return <div className="space-y-5"><PageHeader icon={<BarChart3 />} title="Performance" subtitle="Measure outcomes and decision quality without hiding the losing trades." /><PerformanceMini stats={stats} pnlValues={pnlValues} /><RecentTrades trades={trades} /></div>; }
function JournalView({ trades }: { trades: Trade[] }) { return <div className="space-y-5"><PageHeader icon={<BookOpenIcon />} title="Trade Journal" subtitle="A chronological record of executed contracts and their outcomes." /><RecentTrades trades={trades} full /></div>; }
function SettingsView({ userEmail, settings }: { userEmail: string; settings: SystemSettings | null }) { return <div className="space-y-5"><PageHeader icon={<Gauge />} title="Settings" subtitle="Your account and current server-side trading controls." /><div className="grid md:grid-cols-2 gap-5"><div className="rounded-2xl border border-white/[0.08] bg-[#091321]/90 p-5"><div className="text-xs text-slate-500">Account</div><div className="mt-2 flex items-center gap-3"><div className="h-10 w-10 rounded-full bg-slate-800 flex items-center justify-center"><UserIcon /></div><div><div className="font-semibold">{userEmail}</div><div className="text-xs text-slate-500">Authenticated SmartPip user</div></div></div></div><div className="rounded-2xl border border-white/[0.08] bg-[#091321]/90 p-5"><div className="text-xs text-slate-500">Trading controls</div><div className="mt-4 grid grid-cols-2 gap-3"><Metric label="Min confidence" value={`${settings?.min_confidence ?? '—'}%`} /><Metric label="Stop loss" value={settings ? `$${settings.stop_loss}` : '—'} /><Metric label="Take profit" value={settings ? `$${settings.take_profit}` : '—'} /><Metric label="Auto trading" value={settings?.auto_trading ? 'ON' : 'OFF'} /></div></div></div></div>; }

function PerformanceMini({ stats, pnlValues }: { stats: TradeStatistics | null; pnlValues: number[] }) { return <div className="rounded-2xl border border-white/[0.08] bg-[#091321]/90 p-5"><SectionTitle eyebrow="Account intelligence" title="Performance" /><div className="grid grid-cols-2 lg:grid-cols-4 gap-3"><Metric label="Total P&L" value={fmtMoney(stats?.total_profit)} accent={(stats?.total_profit ?? 0) >= 0 ? 'text-teal-300' : 'text-red-300'} /><Metric label="Win rate" value={stats ? `${Number(stats.win_rate).toFixed(1)}%` : '—'} /><Metric label="Trades" value={stats ? String(stats.total_trades) : '—'} /><Metric label="Avg loss" value={fmtMoney(stats?.avg_loss)} /></div><div className="mt-4 rounded-xl border border-white/[0.05] bg-black/20 p-3"><Sparkline values={pnlValues} positive={(stats?.total_profit ?? 0) >= 0} /></div></div>; }
function RecentTrades({ trades, full = false }: { trades: Trade[]; full?: boolean }) { const list = full ? trades : trades.slice(0, 5); return <div className="rounded-2xl border border-white/[0.08] bg-[#091321]/90 p-5"><SectionTitle eyebrow="History" title="Recent trades" /><div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead className="text-slate-600"><tr><th className="py-2">Time</th><th>Market</th><th>Direction</th><th>Stake</th><th>Result</th></tr></thead><tbody>{list.map((t) => <tr key={t.id} className="border-t border-white/[0.05]"><td className="py-3 text-slate-500">{new Date(t.entry_time).toLocaleTimeString()}</td><td className="font-semibold">{t.market}</td><td className={t.direction === 'CALL' ? 'text-teal-300' : 'text-red-300'}>{t.direction}</td><td>${Number(t.amount).toFixed(2)}</td><td className={(t.profit ?? 0) >= 0 ? 'text-teal-300' : 'text-red-300'}>{fmtMoney(t.profit)}</td></tr>)}</tbody></table>{list.length === 0 && <div className="py-8 text-center text-xs text-slate-600">No completed trades yet.</div>}</div></div>; }
function PageHeader({ icon, title, subtitle, onRefresh, loading }: { icon: ReactNode; title: string; subtitle: string; onRefresh?: () => Promise<void>; loading?: boolean }) { return <div className="flex items-start justify-between gap-4"><div><div className="flex items-center gap-2 text-red-400">{icon}<span className="text-[10px] uppercase tracking-[0.2em]">SmartPip</span></div><h1 className="mt-2 text-3xl font-black">{title}</h1><p className="mt-1 text-sm text-slate-500">{subtitle}</p></div>{onRefresh && <button onClick={() => void onRefresh()} className="rounded-xl border border-white/10 p-2.5 text-slate-400 hover:text-white">{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}</button>}</div>; }
function Metric({ label, value, accent = 'text-white' }: { label: string; value: string; accent?: string }) { return <div className="rounded-xl border border-white/[0.06] bg-black/20 p-3"><div className="text-[10px] uppercase tracking-wider text-slate-600">{label}</div><div className={`mt-1 text-lg font-bold tabular-nums ${accent}`}>{value}</div></div>; }
function StatusRow({ label, ok, warning = false }: { label: string; ok: boolean; warning?: boolean }) { return <div className="flex items-center justify-between rounded-xl bg-black/20 px-3 py-2.5"><span className="text-xs text-slate-400">{label}</span><span className={`text-[10px] font-bold ${ok ? 'text-teal-300' : warning ? 'text-amber-300' : 'text-slate-600'}`}>{ok ? <><Check className="inline h-3.5 w-3.5 mr-1" />PASS</> : warning ? 'REVIEW' : 'WAIT'}</span></div>; }
function BookOpenIcon() { return <BookOpen className="h-5 w-5" />; }
function UserIcon() { return <CircleDollarSign className="h-5 w-5 text-slate-400" />; }
