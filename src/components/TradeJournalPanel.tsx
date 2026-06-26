import { useState, useEffect, useCallback } from 'react';
import {
  BookOpen, TrendingUp, TrendingDown, Clock, Target, Zap,
  ChevronDown, ChevronUp, Lightbulb, BarChart3, Hash, Activity,
  Calendar, ArrowUpRight, ArrowDownRight, RefreshCw, AlertTriangle,
  CheckCircle, XCircle, Award, Flame, Shield
} from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────

interface JournalEntry {
  id: string;
  timestamp: string;
  symbol: string;
  contractType: string;
  entryPrice: number;
  entryDigit?: number;
  exitPrice?: number;
  exitDigit?: number;
  amount: number;
  confidence: number;
  regime: string;
  entryConditions: string[];
  exitConditions: string[];
  pnl?: number;
  runningBalance: number;
  peakBalance: number;
  drawdownImpact: number;
  entropy?: number;
  streak?: number;
  chi2?: number;
  rsi?: number;
  score?: number;
  status: 'open' | 'closed';
  notes?: string;
}

interface WeeklyInsight {
  weekStart: string;
  weekEnd: string;
  summary: {
    totalTrades: number;
    winRate: number;
    profitFactor: number;
    totalPnl: number;
    sharpeRatio: number;
    maxDrawdownPct: number;
    expectedValuePerTrade: number;
    kellyFraction: number;
  };
  bestSetups: Setup[];
  worstSetups: Setup[];
  bestHours: HourStat[];
  worstHours: HourStat[];
  regimePerformance: Record<string, RegimeStat>;
  bestRegime?: string;
  worstRegime?: string;
  optimalConfidenceThreshold: { band: string; threshold: number; note: string };
  streaks: { bestWinStreak: number; worstLossStreak: number };
  significance: SignificanceFlag[];
  dailyBreakdown: Record<string, DayStat>;
  conditionWinRates: Record<string, ConditionStat>;
}

interface Setup { setup: string; trades: number; winRate: number; totalPnl: number; expectedValue: number; avgConfidence: number; score: number; }
interface HourStat { hour: string; trades: number; winRate: number; totalPnl: number; avgPnl: number; }
interface RegimeStat { trades: number; winRate: number; totalPnl: number; avgPnl: number; }
interface SignificanceFlag { finding: string; zScore: number; pValue: number; direction: 'positive' | 'negative'; }
interface DayStat { trades: number; winRate: number; totalPnl: number; avgPnl: number; }
interface ConditionStat { trades: number; winRate: number; expectedValue: number; totalPnl: number; }
interface Recommendation {
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  category: string;
  title: string;
  action: string;
  evidence: string;
  metric?: Record<string, unknown>;
}

// ── Mini components ────────────────────────────────────────────────────────────

const KPI = ({ label, value, sub, color = 'text-slate-100' }: { label: string; value: string; sub?: string; color?: string }) => (
  <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-3">
    <div className="text-[10px] text-slate-400 mb-1">{label}</div>
    <div className={`text-lg font-bold font-mono ${color}`}>{value}</div>
    {sub && <div className="text-[10px] text-slate-500 mt-0.5">{sub}</div>}
  </div>
);

const PriorityBadge = ({ p }: { p: 'HIGH' | 'MEDIUM' | 'LOW' }) => {
  const map = {
    HIGH: 'bg-red-900/50 text-red-300 border-red-700/50',
    MEDIUM: 'bg-amber-900/50 text-amber-300 border-amber-700/50',
    LOW: 'bg-emerald-900/30 text-emerald-400 border-emerald-700/40',
  };
  return <span className={`text-[9px] font-bold px-2 py-0.5 rounded border ${map[p]}`}>{p}</span>;
};

const WinRateBar = ({ value, label }: { value: number; label: string }) => {
  const col = value >= 60 ? 'bg-emerald-500' : value >= 50 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="text-[10px] text-slate-400 w-20 truncate">{label}</div>
      <div className="flex-1 h-2 bg-slate-700 rounded overflow-hidden">
        <div className={`h-full rounded ${col} transition-all duration-500`} style={{ width: `${Math.min(100, value)}%` }} />
      </div>
      <div className="text-[10px] font-mono text-slate-300 w-10 text-right">{value.toFixed(1)}%</div>
    </div>
  );
};

const HeatCell = ({ wr, trades }: { wr: number; trades: number }) => {
  if (trades === 0) return <div className="h-5 rounded bg-slate-800/40 text-[8px] text-slate-700 flex items-center justify-center">—</div>;
  const bg = wr >= 65 ? '#064e3b' : wr >= 55 ? '#1e3a1e' : wr >= 45 ? '#1c1c1c' : wr >= 35 ? '#3b1c1c' : '#4c0519';
  return (
    <div className="h-5 rounded text-[8px] font-mono flex items-center justify-center text-slate-300" style={{ background: bg }}>
      {wr.toFixed(0)}%
    </div>
  );
};

function EntryCard({ entry }: { entry: JournalEntry }) {
  const [expanded, setExpanded] = useState(false);
  const isWin = (entry.pnl || 0) > 0;
  const pending = entry.status === 'open';

  return (
    <div className={`rounded-lg border overflow-hidden ${pending ? 'border-amber-700/40 bg-amber-900/10' : isWin ? 'border-emerald-700/30 bg-emerald-900/5' : 'border-red-700/30 bg-red-900/5'}`}>
      <button onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-slate-800/40 transition-colors">
        <div className="flex items-center gap-2">
          {pending
            ? <Zap className="w-3 h-3 text-amber-400" />
            : isWin
              ? <CheckCircle className="w-3 h-3 text-emerald-400" />
              : <XCircle className="w-3 h-3 text-red-400" />
          }
          <span className="text-xs text-slate-300 font-medium">{entry.contractType}</span>
          <span className="text-[10px] text-slate-500 font-mono">{entry.symbol}</span>
          <span className="text-[9px] bg-slate-700 px-1.5 py-0.5 rounded text-slate-400">{entry.regime}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-slate-500">{entry.confidence}%</span>
          {pending
            ? <span className="text-xs text-amber-400 font-medium">PENDING</span>
            : <span className={`text-xs font-medium font-mono ${isWin ? 'text-emerald-400' : 'text-red-400'}`}>
                {isWin ? '+' : ''}${(entry.pnl || 0).toFixed(2)}
              </span>
          }
          {expanded ? <ChevronUp className="w-3 h-3 text-slate-500" /> : <ChevronDown className="w-3 h-3 text-slate-500" />}
        </div>
      </button>
      {expanded && (
        <div className="px-3 pb-3 border-t border-slate-700/30 pt-2 space-y-2">
          <div className="grid grid-cols-3 gap-2">
            {[
              ['Entry', `$${entry.entryPrice.toFixed(4)} · d${entry.entryDigit ?? '—'}`],
              ['Exit', entry.exitPrice ? `$${entry.exitPrice.toFixed(4)} · d${entry.exitDigit ?? '—'}` : '—'],
              ['Amount', `$${entry.amount.toFixed(2)}`],
              ['Confidence', `${entry.confidence}%`],
              ['Score', `${entry.score ?? '—'}/100`],
              ['Balance', `$${entry.runningBalance.toFixed(2)}`],
              ['DD Impact', `${entry.drawdownImpact.toFixed(2)}%`],
              ['Entropy', entry.entropy ? entry.entropy.toFixed(3) : '—'],
              ['Streak', entry.streak != null ? `${entry.streak}×` : '—'],
            ].map(([l, v]) => (
              <div key={l} className="text-[10px]">
                <div className="text-slate-500">{l}</div>
                <div className="text-slate-300 font-mono">{v}</div>
              </div>
            ))}
          </div>
          {entry.entryConditions.length > 0 && (
            <div>
              <div className="text-[9px] text-slate-500 uppercase mb-1">Entry conditions</div>
              <div className="flex flex-wrap gap-1">
                {entry.entryConditions.map((c, i) => (
                  <span key={i} className="text-[9px] bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded">{c}</span>
                ))}
              </div>
            </div>
          )}
          {entry.notes && (
            <div className="text-[10px] text-slate-400 bg-slate-800/50 rounded p-2">{entry.notes}</div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main panel ─────────────────────────────────────────────────────────────────

type Tab = 'trades' | 'weekly' | 'regimes' | 'heatmap' | 'recommendations';

export default function TradeJournalPanel() {
  const [tab, setTab] = useState<Tab>('trades');
  const [trades, setTrades] = useState<JournalEntry[]>([]);
  const [insight, setInsight] = useState<WeeklyInsight | null>(null);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [heatmap, setHeatmap] = useState<Record<string, { winRate: number; trades: number; avgPnl: number }>>({});
  const [regimePerfAll, setRegimePerfAll] = useState<Record<string, RegimeStat>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [weekOffset, setWeekOffset] = useState(0);

  const API = '/api/journal';

  const loadTrades = useCallback(async () => {
    try {
      const res = await fetch(`${API}/trades?limit=50`);
      if (!res.ok) return;
      const data = await res.json();
      setTrades((data.trades || []).map(camelizeEntry));
    } catch (_) {}
  }, []);

  const loadInsights = useCallback(async (offset = 0) => {
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API}/insights/weekly?week_offset=${offset}`);
      const data = await res.json();
      if (data.error) { setError(data.error); setInsight(null); }
      else setInsight(camelizeInsight(data));
    } catch (e) {
      setError('Failed to load insights');
    } finally { setLoading(false); }
  }, []);

  const loadRecs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/recommendations?lookback_days=30`);
      const data = await res.json();
      setRecs(data.recommendations || []);
    } catch (_) {} finally { setLoading(false); }
  }, []);

  const loadHeatmap = useCallback(async () => {
    try {
      const res = await fetch(`${API}/heatmap?lookback_days=30`);
      const data = await res.json();
      const tod: Record<string, { winRate: number; trades: number; avgPnl: number }> = {};
      Object.entries(data.time_of_day || {}).forEach(([hr, s]: [string, any]) => {
        tod[hr] = { winRate: s.win_rate, trades: s.trades, avgPnl: s.avg_pnl };
      });
      setHeatmap(tod);
      setRegimePerfAll(data.regime_performance || {});
    } catch (_) {}
  }, []);

  useEffect(() => { loadTrades(); }, [loadTrades]);
  useEffect(() => {
    if (tab === 'weekly') loadInsights(weekOffset);
    if (tab === 'recommendations') loadRecs();
    if (tab === 'heatmap') loadHeatmap();
    if (tab === 'regimes') loadHeatmap();
  }, [tab, weekOffset]);

  const tabs: { id: Tab; label: string; icon: JSX.Element }[] = [
    { id: 'trades',          label: 'Trades',     icon: <BookOpen className="w-3 h-3" /> },
    { id: 'weekly',          label: 'Weekly',     icon: <Calendar className="w-3 h-3" /> },
    { id: 'regimes',         label: 'Regimes',    icon: <Activity className="w-3 h-3" /> },
    { id: 'heatmap',         label: 'Heatmap',    icon: <BarChart3 className="w-3 h-3" /> },
    { id: 'recommendations', label: 'Advice',     icon: <Lightbulb className="w-3 h-3" /> },
  ];

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-700/50 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-violet-400" />
          <span className="text-sm font-semibold text-slate-100">Trade Journal</span>
        </div>
        <button onClick={() => { loadTrades(); if (tab === 'weekly') loadInsights(weekOffset); }}
          className="text-slate-400 hover:text-slate-200 transition-colors">
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-700/50 overflow-x-auto">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-2 text-[10px] font-medium whitespace-nowrap transition-colors ${
              tab === t.id
                ? 'text-violet-400 border-b-2 border-violet-400 bg-violet-900/10'
                : 'text-slate-500 hover:text-slate-300'
            }`}>
            {t.icon}{t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">

        {/* ── TRADES TAB ──────────────────────────────────────────────── */}
        {tab === 'trades' && (
          <>
            <div className="space-y-2">
              {trades.length === 0
                ? <div className="text-center py-8 text-slate-500 text-xs">No trades logged yet. Fire a shot to begin tracking.</div>
                : trades.map(t => <EntryCard key={t.id} entry={t} />)
              }
            </div>
          </>
        )}

        {/* ── WEEKLY TAB ──────────────────────────────────────────────── */}
        {tab === 'weekly' && (
          <>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button onClick={() => setWeekOffset(w => w + 1)}
                  className="text-slate-400 hover:text-slate-200 text-[10px] px-2 py-1 border border-slate-700 rounded">← Prev</button>
                <span className="text-[10px] text-slate-400">
                  {weekOffset === 0 ? 'This week' : `${weekOffset} week${weekOffset > 1 ? 's' : ''} ago`}
                </span>
                <button onClick={() => setWeekOffset(w => Math.max(0, w - 1))} disabled={weekOffset === 0}
                  className="text-slate-400 hover:text-slate-200 text-[10px] px-2 py-1 border border-slate-700 rounded disabled:opacity-30">Next →</button>
              </div>
              <button onClick={() => loadInsights(weekOffset)}
                className="text-[9px] text-violet-400 hover:text-violet-300">Regenerate</button>
            </div>

            {loading && <div className="text-center py-4 text-slate-500 text-xs animate-pulse">Generating insights...</div>}
            {error && <div className="text-center py-4 text-amber-400 text-xs">{error}</div>}

            {insight && !loading && (
              <>
                {/* KPIs */}
                <div className="grid grid-cols-2 gap-2">
                  <KPI label="Win Rate" value={`${insight.summary.winRate.toFixed(1)}%`}
                    color={insight.summary.winRate >= 55 ? 'text-emerald-400' : insight.summary.winRate >= 50 ? 'text-amber-400' : 'text-red-400'} />
                  <KPI label="Profit Factor" value={insight.summary.profitFactor.toFixed(2)}
                    sub={insight.summary.profitFactor >= 1.5 ? 'Excellent' : insight.summary.profitFactor >= 1.2 ? 'Good' : 'Needs improvement'}
                    color={insight.summary.profitFactor >= 1.5 ? 'text-emerald-400' : 'text-amber-400'} />
                  <KPI label="Net P&L" value={`${insight.summary.totalPnl >= 0 ? '+' : ''}$${insight.summary.totalPnl.toFixed(2)}`}
                    color={insight.summary.totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400'} />
                  <KPI label="Sharpe Ratio" value={insight.summary.sharpeRatio.toFixed(2)}
                    sub={insight.summary.sharpeRatio >= 1 ? 'Strong' : insight.summary.sharpeRatio >= 0.5 ? 'Acceptable' : 'Low'}
                    color={insight.summary.sharpeRatio >= 1 ? 'text-emerald-400' : 'text-amber-400'} />
                  <KPI label="Max Drawdown" value={`${insight.summary.maxDrawdownPct.toFixed(1)}%`}
                    color={insight.summary.maxDrawdownPct <= 5 ? 'text-emerald-400' : insight.summary.maxDrawdownPct <= 10 ? 'text-amber-400' : 'text-red-400'} />
                  <KPI label="¼ Kelly Stake" value={`${(insight.summary.kellyFraction * 25).toFixed(1)}% BR`}
                    sub={`EV $${insight.summary.expectedValuePerTrade.toFixed(4)}/trade`} />
                </div>

                {/* Best setups */}
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <Award className="w-3 h-3 text-emerald-400" />
                    <span className="text-[10px] font-semibold text-slate-300">Best Setups</span>
                  </div>
                  <div className="space-y-1.5">
                    {insight.bestSetups.slice(0, 3).map((s, i) => (
                      <div key={i} className="bg-emerald-900/10 border border-emerald-700/20 rounded p-2">
                        <div className="flex justify-between text-[10px]">
                          <span className="text-emerald-300 font-medium">{s.setup}</span>
                          <span className="text-emerald-400 font-mono">{s.winRate.toFixed(1)}% WR</span>
                        </div>
                        <div className="text-[9px] text-slate-500 mt-0.5">
                          {s.trades} trades · EV ${s.expectedValue.toFixed(4)} · conf {s.avgConfidence.toFixed(0)}%
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Worst setups */}
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <TrendingDown className="w-3 h-3 text-red-400" />
                    <span className="text-[10px] font-semibold text-slate-300">Worst Setups</span>
                  </div>
                  <div className="space-y-1.5">
                    {insight.worstSetups.slice(0, 3).map((s, i) => (
                      <div key={i} className="bg-red-900/10 border border-red-700/20 rounded p-2">
                        <div className="flex justify-between text-[10px]">
                          <span className="text-red-300 font-medium">{s.setup}</span>
                          <span className="text-red-400 font-mono">{s.winRate.toFixed(1)}% WR</span>
                        </div>
                        <div className="text-[9px] text-slate-500 mt-0.5">
                          {s.trades} trades · EV ${s.expectedValue.toFixed(4)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Significance flags */}
                {insight.significance.length > 0 && (
                  <div>
                    <div className="flex items-center gap-1.5 mb-2">
                      <Hash className="w-3 h-3 text-violet-400" />
                      <span className="text-[10px] font-semibold text-slate-300">Statistical Findings</span>
                    </div>
                    <div className="space-y-1">
                      {insight.significance.map((f, i) => (
                        <div key={i} className={`text-[10px] px-2 py-1.5 rounded border ${
                          f.direction === 'positive' ? 'border-emerald-700/30 text-emerald-300' : 'border-red-700/30 text-red-300'
                        }`}>
                          {f.finding}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Day breakdown */}
                <div>
                  <div className="text-[10px] font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
                    <Calendar className="w-3 h-3 text-violet-400" /> Day-of-Week Performance
                  </div>
                  <div className="space-y-1.5">
                    {Object.entries(insight.dailyBreakdown).map(([day, s]) => (
                      <WinRateBar key={day} label={day} value={s.winRate} />
                    ))}
                  </div>
                </div>
              </>
            )}
          </>
        )}

        {/* ── REGIMES TAB ─────────────────────────────────────────────── */}
        {tab === 'regimes' && (
          <>
            <div className="text-[10px] text-slate-400 mb-2">Win rate & P&L per market regime (last 30 days)</div>
            {Object.keys(regimePerfAll).length === 0
              ? <div className="text-center py-8 text-slate-500 text-xs">No regime data yet</div>
              : Object.entries(regimePerfAll).map(([regime, s]) => (
                <div key={regime} className="bg-slate-800/50 border border-slate-700/40 rounded p-3">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[11px] font-medium text-slate-200 capitalize">{regime.replace('_', ' ')}</span>
                    <span className={`text-[11px] font-bold ${s.winRate >= 55 ? 'text-emerald-400' : s.winRate >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                      {s.winRate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded overflow-hidden mb-1.5">
                    <div className={`h-full rounded transition-all ${s.winRate >= 55 ? 'bg-emerald-500' : s.winRate >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                      style={{ width: `${Math.min(100, s.winRate)}%` }} />
                  </div>
                  <div className="flex justify-between text-[9px] text-slate-500">
                    <span>{s.trades} trades</span>
                    <span>Avg P&L ${s.avgPnl.toFixed(4)}</span>
                    <span className={s.totalPnl >= 0 ? 'text-emerald-500' : 'text-red-500'}>
                      Net ${s.totalPnl.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))
            }
          </>
        )}

        {/* ── HEATMAP TAB ─────────────────────────────────────────────── */}
        {tab === 'heatmap' && (
          <>
            <div className="text-[10px] text-slate-400 mb-2">Hourly win rate heatmap UTC (last 30 days). Darker green = better performance.</div>
            <div className="grid grid-cols-6 gap-1">
              {Array.from({ length: 24 }, (_, h) => {
                const key = `${String(h).padStart(2, '0')}:00`;
                const s = heatmap[key] || { winRate: 0, trades: 0, avgPnl: 0 };
                return (
                  <div key={h}>
                    <div className="text-[8px] text-slate-600 text-center mb-0.5">{String(h).padStart(2,'0')}h</div>
                    <HeatCell wr={s.winRate} trades={s.trades} />
                    {s.trades > 0 && <div className="text-[7px] text-slate-600 text-center">{s.trades}t</div>}
                  </div>
                );
              })}
            </div>
            <div className="flex justify-between text-[9px] text-slate-600 mt-1">
              <span>■ &lt;35%</span><span>■ 35-45%</span><span>■ 45-55%</span><span>■ 55-65%</span><span>■ &gt;65%</span>
            </div>

            {/* Best/worst hours */}
            {Object.keys(heatmap).length > 0 && (
              <>
                <div className="text-[10px] font-semibold text-slate-300 mt-3">Best trading windows</div>
                <div className="space-y-1">
                  {Object.entries(heatmap)
                    .filter(([, s]) => s.trades >= 3)
                    .sort(([, a], [, b]) => b.winRate - a.winRate)
                    .slice(0, 4)
                    .map(([hr, s]) => <WinRateBar key={hr} label={hr} value={s.winRate} />)
                  }
                </div>
              </>
            )}
          </>
        )}

        {/* ── RECOMMENDATIONS TAB ─────────────────────────────────────── */}
        {tab === 'recommendations' && (
          <>
            {loading && <div className="text-center py-4 text-slate-500 text-xs animate-pulse">Analyzing 30-day history...</div>}
            {recs.length === 0 && !loading && (
              <div className="text-center py-8 text-slate-500 text-xs">
                No recommendations yet. Log at least 5 closed trades first.
              </div>
            )}
            {recs.map((rec, i) => (
              <div key={i} className={`rounded-lg border p-3 space-y-1.5 ${
                rec.priority === 'HIGH'
                  ? 'border-red-700/40 bg-red-900/10'
                  : rec.priority === 'MEDIUM'
                    ? 'border-amber-700/30 bg-amber-900/5'
                    : 'border-slate-700/40 bg-slate-800/30'
              }`}>
                <div className="flex items-start justify-between gap-2">
                  <span className="text-[11px] font-semibold text-slate-200 leading-tight">{rec.title}</span>
                  <PriorityBadge p={rec.priority} />
                </div>
                <div className="text-[10px] text-slate-300 leading-relaxed">{rec.action}</div>
                <div className="text-[9px] text-slate-500 bg-slate-800/50 rounded px-2 py-1">
                  Evidence: {rec.evidence}
                </div>
                <div className="text-[9px] text-violet-400 capitalize">Category: {rec.category}</div>
              </div>
            ))}
          </>
        )}

      </div>
    </div>
  );
}

// ── Data transformation helpers ───────────────────────────────────────────────

function camelizeEntry(t: any): JournalEntry {
  return {
    id: t.id,
    timestamp: t.timestamp || t.created_at,
    symbol: t.symbol,
    contractType: t.contract_type,
    entryPrice: t.entry_price,
    entryDigit: t.entry_digit,
    exitPrice: t.exit_price,
    exitDigit: t.exit_digit,
    amount: t.amount,
    confidence: t.confidence,
    regime: t.regime,
    entryConditions: t.entry_conditions || [],
    exitConditions: t.exit_conditions || [],
    pnl: t.pnl,
    runningBalance: t.running_balance,
    peakBalance: t.peak_balance,
    drawdownImpact: t.drawdown_impact,
    entropy: t.entropy,
    streak: t.streak,
    chi2: t.chi2,
    rsi: t.rsi,
    score: t.score,
    status: t.status,
    notes: t.notes,
  };
}

function camelizeInsight(d: any): WeeklyInsight {
  return {
    weekStart: d.week_start,
    weekEnd: d.week_end,
    summary: {
      totalTrades: d.summary?.total_trades ?? 0,
      winRate: d.summary?.win_rate ?? 0,
      profitFactor: d.summary?.profit_factor ?? 0,
      totalPnl: d.summary?.total_pnl ?? 0,
      sharpeRatio: d.summary?.sharpe_ratio ?? 0,
      maxDrawdownPct: d.summary?.max_drawdown_pct ?? 0,
      expectedValuePerTrade: d.summary?.expected_value_per_trade ?? 0,
      kellyFraction: d.summary?.kelly_fraction ?? 0,
    },
    bestSetups: (d.best_setups || []).map((s: any) => ({
      setup: s.setup, trades: s.trades, winRate: s.win_rate, totalPnl: s.total_pnl,
      expectedValue: s.expected_value, avgConfidence: s.avg_confidence, score: s.score,
    })),
    worstSetups: (d.worst_setups || []).map((s: any) => ({
      setup: s.setup, trades: s.trades, winRate: s.win_rate, totalPnl: s.total_pnl,
      expectedValue: s.expected_value, avgConfidence: s.avg_confidence, score: s.score,
    })),
    bestHours: d.best_hours || [],
    worstHours: d.worst_hours || [],
    regimePerformance: d.regime_performance || {},
    bestRegime: d.best_regime,
    worstRegime: d.worst_regime,
    optimalConfidenceThreshold: d.optimal_confidence_threshold || { band: '70-80%', threshold: 70, note: '' },
    streaks: { bestWinStreak: d.streaks?.best_win_streak ?? 0, worstLossStreak: d.streaks?.worst_loss_streak ?? 0 },
    significance: (d.significance || []).map((f: any) => ({
      finding: f.finding, zScore: f.z_score, pValue: f.p_value, direction: f.direction,
    })),
    dailyBreakdown: d.daily_breakdown || {},
    conditionWinRates: d.condition_win_rates || {},
  };
}
