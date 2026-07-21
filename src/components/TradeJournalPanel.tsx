import { useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import {
  BookOpen, Target,
  ChevronDown, ChevronUp, Lightbulb, RefreshCw, CheckCircle, XCircle, Award, Zap,
  Calendar, BarChart3, TrendingDown, Hash, Clock,
} from 'lucide-react';
import type { JournalEntry, WeeklyInsight } from '../hooks/useTradeJournal';

// ── Props matching what App.tsx passes ────────────────────────────────────────

interface TradeJournalPanelProps {
  entries: JournalEntry[];
  insights: WeeklyInsight[];
  onGenerateInsights?: () => void;
}

// ── Backend API types ─────────────────────────────────────────────────────────

interface ApiRecommendation {
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  category: string;
  title: string;
  action: string;
  evidence: string;
}

interface RegimeStat {
  trades: number;
  win_rate: number;
  total_pnl: number;
  avg_pnl: number;
}

interface HourStat {
  trades: number;
  win_rate: number;
  avg_pnl: number;
}

// ── Small display components ──────────────────────────────────────────────────

function KPI({
  label,
  value,
  sub,
  color = 'text-slate-100',
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-3">
      <div className="text-[10px] text-slate-400 mb-1">{label}</div>
      <div className={`text-lg font-bold font-mono ${color}`}>{value}</div>
      {sub && <div className="text-[10px] text-slate-500 mt-0.5">{sub}</div>}
    </div>
  );
}

function PriorityBadge({ p }: { p: 'HIGH' | 'MEDIUM' | 'LOW' }) {
  const map: Record<string, string> = {
    HIGH: 'bg-red-900/50 text-red-300 border-red-700/50',
    MEDIUM: 'bg-amber-900/50 text-amber-300 border-amber-700/50',
    LOW: 'bg-emerald-900/30 text-emerald-400 border-emerald-700/40',
  };
  return (
    <span className={`text-[9px] font-bold px-2 py-0.5 rounded border ${map[p]}`}>{p}</span>
  );
}

function WinRateBar({ value, label }: { value: number; label: string }) {
  const col =
    value >= 60 ? 'bg-emerald-500' : value >= 50 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="text-[10px] text-slate-400 w-20 truncate">{label}</div>
      <div className="flex-1 h-2 bg-slate-700 rounded overflow-hidden">
        <div
          className={`h-full rounded ${col} transition-all duration-500`}
          style={{ width: `${Math.min(100, value)}%` }}
        />
      </div>
      <div className="text-[10px] font-mono text-slate-300 w-10 text-right">
        {value.toFixed(1)}%
      </div>
    </div>
  );
}

function HeatCell({ wr, trades }: { wr: number; trades: number }) {
  if (trades === 0) {
    return (
      <div className="h-5 rounded bg-slate-800/40 text-[8px] text-slate-700 flex items-center justify-center">
        —
      </div>
    );
  }
  const bg =
    wr >= 65
      ? '#064e3b'
      : wr >= 55
      ? '#1e3a1e'
      : wr >= 45
      ? '#1c1c1c'
      : wr >= 35
      ? '#3b1c1c'
      : '#4c0519';
  return (
    <div
      className="h-5 rounded text-[8px] font-mono flex items-center justify-center text-slate-300"
      style={{ background: bg }}
    >
      {wr.toFixed(0)}%
    </div>
  );
}

function EntryCard({ entry }: { entry: JournalEntry }) {
  const [expanded, setExpanded] = useState(false);
  const isWin = (entry.profit ?? 0) > 0;
  const pending = entry.exitPrice === null;

  return (
    <div
      className={`rounded-lg border overflow-hidden ${
        pending
          ? 'border-amber-700/40 bg-amber-900/10'
          : isWin
          ? 'border-emerald-700/30 bg-emerald-900/5'
          : 'border-red-700/30 bg-red-900/5'
      }`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-slate-800/40 transition-colors"
      >
        <div className="flex items-center gap-2">
          {pending ? (
            <Zap className="w-3 h-3 text-amber-400" />
          ) : isWin ? (
            <CheckCircle className="w-3 h-3 text-emerald-400" />
          ) : (
            <XCircle className="w-3 h-3 text-red-400" />
          )}
          <span className="text-xs text-slate-300 font-medium">{entry.contractType}</span>
          <span className="text-[10px] text-slate-500 font-mono">{entry.symbol}</span>
          <span className="text-[9px] bg-slate-700 px-1.5 py-0.5 rounded text-slate-400">
            {entry.regime}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-slate-500">{entry.confidence}%</span>
          {pending ? (
            <span className="text-xs text-amber-400 font-medium">PENDING</span>
          ) : (
            <span
              className={`text-xs font-medium font-mono ${
                isWin ? 'text-emerald-400' : 'text-red-400'
              }`}
            >
              {isWin ? '+' : ''}${(entry.profit ?? 0).toFixed(2)}
            </span>
          )}
          {expanded ? (
            <ChevronUp className="w-3 h-3 text-slate-500" />
          ) : (
            <ChevronDown className="w-3 h-3 text-slate-500" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 border-t border-slate-700/30 pt-2 space-y-2">
          <div className="grid grid-cols-3 gap-2">
            {(
              [
                ['Entry Price', `$${entry.entryPrice.toFixed(4)}`],
                ['Entry Digit', `d${entry.entryDigit}`],
                ['Amount', `$${entry.amount.toFixed(2)}`],
                ['Confidence', `${entry.confidence}%`],
                ['DD Impact', `${entry.drawdownImpact.toFixed(2)}%`],
                ['Balance', `$${entry.runningBalance.toFixed(2)}`],
              ] as [string, string][]
            ).map(([l, v]) => (
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
                  <span
                    key={i}
                    className="text-[9px] bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded"
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {entry.notes && (
            <div className="text-[10px] text-slate-400 bg-slate-800/50 rounded p-2">
              {entry.notes}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────────────

type Tab = 'trades' | 'weekly' | 'regimes' | 'heatmap' | 'recommendations';

interface TabDef {
  id: Tab;
  label: string;
  icon: ReactNode;
}

// ── Main panel ────────────────────────────────────────────────────────────────

export function TradeJournalPanel({
  entries,
  insights,
  onGenerateInsights,
}: TradeJournalPanelProps) {
  const [tab, setTab] = useState<Tab>('trades');
  const [recs, setRecs] = useState<ApiRecommendation[]>([]);
  const [heatmap, setHeatmap] = useState<Record<string, HourStat>>({});
  const [regimePerf, setRegimePerf] = useState<Record<string, RegimeStat>>({});
  const [loadingApi, setLoadingApi] = useState(false);
  const [weekOffset, setWeekOffset] = useState(0);

  const API = '/api/journal';

  const loadRecs = useCallback(async () => {
    setLoadingApi(true);
    try {
      const res = await fetch(`${API}/recommendations?lookback_days=30`);
      if (!res.ok) return;
      const data = await res.json() as { recommendations?: ApiRecommendation[] };
      setRecs(data.recommendations ?? []);
    } catch (_) {
      // API unavailable — degrade gracefully
    } finally {
      setLoadingApi(false);
    }
  }, []);

  const loadHeatmap = useCallback(async () => {
    try {
      const res = await fetch(`${API}/heatmap?lookback_days=30`);
      if (!res.ok) return;
      const data = await res.json() as {
        time_of_day?: Record<string, HourStat>;
        regime_performance?: Record<string, RegimeStat>;
      };
      setHeatmap(data.time_of_day ?? {});
      setRegimePerf(data.regime_performance ?? {});
    } catch (_) {
      // API unavailable
    }
  }, []);

  useEffect(() => {
    if (tab === 'recommendations') void loadRecs();
    if (tab === 'heatmap' || tab === 'regimes') void loadHeatmap();
  }, [tab, loadRecs, loadHeatmap]);

  const tabs: TabDef[] = [
    { id: 'trades',          label: 'Trades',  icon: <BookOpen className="w-3 h-3" /> },
    { id: 'weekly',          label: 'Weekly',  icon: <Calendar className="w-3 h-3" /> },
    { id: 'regimes',         label: 'Regimes', icon: <Target className="w-3 h-3" /> },
    { id: 'heatmap',         label: 'Heatmap', icon: <BarChart3 className="w-3 h-3" /> },
    { id: 'recommendations', label: 'Advice',  icon: <Lightbulb className="w-3 h-3" /> },
  ];

  // ── Derived stats from hook entries ───────────────────────────────────────
  const closed = entries.filter((e) => e.profit !== null);
  const wins = closed.filter((e) => (e.profit ?? 0) > 0);
  const totalPnl = closed.reduce((s, e) => s + (e.profit ?? 0), 0);
  const grossProfit = wins.reduce((s, e) => s + (e.profit ?? 0), 0);
  const grossLoss = Math.abs(
    closed.filter((e) => (e.profit ?? 0) < 0).reduce((s, e) => s + (e.profit ?? 0), 0),
  );
  const pf = grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0;
  const wr = closed.length > 0 ? (wins.length / closed.length) * 100 : 0;

  // Regime breakdown computed from hook entries (used as fallback when API is down)
  const regimeLocal: Record<string, { trades: number; wins: number; pnl: number }> = {};
  for (const e of closed) {
    const r = String(e.regime);
    if (!regimeLocal[r]) regimeLocal[r] = { trades: 0, wins: 0, pnl: 0 };
    regimeLocal[r].trades++;
    regimeLocal[r].pnl += e.profit ?? 0;
    if ((e.profit ?? 0) > 0) regimeLocal[r].wins++;
  }

  const currentInsight = insights.length > 0 ? insights[weekOffset] ?? insights[0] : null;

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-700/50 flex flex-col h-full">

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-violet-400" />
          <span className="text-sm font-semibold text-slate-100">Trade Journal</span>
          {entries.length > 0 && (
            <span className="text-[10px] bg-violet-900/40 text-violet-300 px-1.5 py-0.5 rounded">
              {entries.length}
            </span>
          )}
        </div>
        <button
          onClick={onGenerateInsights}
          title="Refresh insights"
          className="text-slate-400 hover:text-slate-200 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-700/50 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-2 text-[10px] font-medium whitespace-nowrap transition-colors ${
              tab === t.id
                ? 'text-violet-400 border-b-2 border-violet-400 bg-violet-900/10'
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">

        {/* ── TRADES ──────────────────────────────────────────────────── */}
        {tab === 'trades' && (
          <div className="space-y-2">
            {entries.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-xs">
                No trades logged yet. Fire a shot to begin tracking.
              </div>
            ) : (
              entries.slice(0, 50).map((e) => <EntryCard key={e.id} entry={e} />)
            )}
          </div>
        )}

        {/* ── WEEKLY ──────────────────────────────────────────────────── */}
        {tab === 'weekly' && (
          <>
            {insights.length > 1 && (
              <div className="flex items-center justify-between">
                <button
                  disabled={weekOffset >= insights.length - 1}
                  onClick={() => setWeekOffset((w) => Math.min(insights.length - 1, w + 1))}
                  className="text-[10px] text-slate-400 hover:text-slate-200 px-2 py-1 border border-slate-700 rounded disabled:opacity-30"
                >
                  ← Prev
                </button>
                <span className="text-[10px] text-slate-400">
                  {weekOffset === 0 ? 'This week' : `${weekOffset}w ago`}
                </span>
                <button
                  disabled={weekOffset === 0}
                  onClick={() => setWeekOffset((w) => Math.max(0, w - 1))}
                  className="text-[10px] text-slate-400 hover:text-slate-200 px-2 py-1 border border-slate-700 rounded disabled:opacity-30"
                >
                  Next →
                </button>
              </div>
            )}

            {/* Live KPIs */}
            <div className="grid grid-cols-2 gap-2">
              <KPI
                label="Win Rate"
                value={`${wr.toFixed(1)}%`}
                color={wr >= 55 ? 'text-emerald-400' : wr >= 50 ? 'text-amber-400' : 'text-red-400'}
              />
              <KPI
                label="Profit Factor"
                value={isFinite(pf) ? pf.toFixed(2) : '∞'}
                sub={pf >= 1.5 ? 'Excellent' : pf >= 1.2 ? 'Good' : 'Needs work'}
                color={pf >= 1.5 ? 'text-emerald-400' : 'text-amber-400'}
              />
              <KPI
                label="Net P&L"
                value={`${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}`}
                color={totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}
              />
              <KPI
                label="Trades"
                value={String(closed.length)}
                sub={`${wins.length}W / ${closed.length - wins.length}L`}
              />
            </div>

            {/* Insight from hook */}
            {currentInsight ? (
              <div className="space-y-3">
                {currentInsight.bestSetup && (
                  <div>
                    <div className="flex items-center gap-1.5 mb-2">
                      <Award className="w-3 h-3 text-emerald-400" />
                      <span className="text-[10px] font-semibold text-slate-300">Best Setup</span>
                    </div>
                    <div className="bg-emerald-900/10 border border-emerald-700/20 rounded p-2">
                      <div className="flex justify-between text-[10px]">
                        <span className="text-emerald-300 font-medium">
                          {currentInsight.bestSetup.setup}
                        </span>
                        <span className="text-emerald-400 font-mono">
                          +${currentInsight.bestSetup.pnl.toFixed(2)}
                        </span>
                      </div>
                      <div className="text-[9px] text-slate-500 mt-0.5">
                        {currentInsight.bestSetup.trades} trades
                      </div>
                    </div>
                  </div>
                )}

                {currentInsight.worstSetup && (
                  <div>
                    <div className="flex items-center gap-1.5 mb-2">
                      <TrendingDown className="w-3 h-3 text-red-400" />
                      <span className="text-[10px] font-semibold text-slate-300">Worst Setup</span>
                    </div>
                    <div className="bg-red-900/10 border border-red-700/20 rounded p-2">
                      <div className="flex justify-between text-[10px]">
                        <span className="text-red-300 font-medium">
                          {currentInsight.worstSetup.setup}
                        </span>
                        <span className="text-red-400 font-mono">
                          ${currentInsight.worstSetup.pnl.toFixed(2)}
                        </span>
                      </div>
                      <div className="text-[9px] text-slate-500 mt-0.5">
                        {currentInsight.worstSetup.trades} trades
                      </div>
                    </div>
                  </div>
                )}

                {Object.keys(currentInsight.regimePerformance).length > 0 && (
                  <div>
                    <div className="flex items-center gap-1.5 mb-2">
                      <Hash className="w-3 h-3 text-violet-400" />
                      <span className="text-[10px] font-semibold text-slate-300">
                        Regime Performance
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      {Object.entries(currentInsight.regimePerformance).map(([r, s]) => (
                        <WinRateBar key={r} label={r} value={s.winRate} />
                      ))}
                    </div>
                  </div>
                )}

                {Object.keys(currentInsight.timeOfDay).length > 0 && (
                  <div>
                    <div className="flex items-center gap-1.5 mb-2">
                      <Clock className="w-3 h-3 text-amber-400" />
                      <span className="text-[10px] font-semibold text-slate-300">
                        Best Hours (UTC)
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      {Object.entries(currentInsight.timeOfDay)
                        .filter(([, s]) => s.trades >= 2)
                        .sort(([, a], [, b]) => b.winRate - a.winRate)
                        .slice(0, 5)
                        .map(([hr, s]) => (
                          <WinRateBar key={hr} label={`${hr}:00`} value={s.winRate} />
                        ))}
                    </div>
                  </div>
                )}

                {currentInsight.recommendations.length > 0 && (
                  <div>
                    <div className="text-[10px] font-semibold text-slate-300 mb-2">
                      Weekly Insights
                    </div>
                    <div className="space-y-1">
                      {currentInsight.recommendations.map((r, idx) => (
                        <div
                          key={idx}
                          className="text-[10px] text-slate-300 bg-slate-800/50 rounded px-2 py-1.5 border-l-2 border-violet-500/50"
                        >
                          {r}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              closed.length === 0 && (
                <div className="text-center py-6 text-slate-500 text-xs">
                  No closed trades yet.
                  {onGenerateInsights && (
                    <>
                      {' '}
                      <button
                        onClick={onGenerateInsights}
                        className="text-violet-400 underline"
                      >
                        Generate insights
                      </button>
                    </>
                  )}
                </div>
              )
            )}
          </>
        )}

        {/* ── REGIMES ─────────────────────────────────────────────────── */}
        {tab === 'regimes' && (
          <>
            <div className="text-[10px] text-slate-400 mb-2">
              Win rate &amp; P&amp;L per market regime
            </div>

            {Object.keys(regimePerf).length > 0 ? (
              Object.entries(regimePerf).map(([regime, s]) => (
                <div
                  key={regime}
                  className="bg-slate-800/50 border border-slate-700/40 rounded p-3 mb-2"
                >
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[11px] font-medium text-slate-200 capitalize">
                      {regime.replace('_', ' ')}
                    </span>
                    <span
                      className={`text-[11px] font-bold ${
                        s.win_rate >= 55
                          ? 'text-emerald-400'
                          : s.win_rate >= 50
                          ? 'text-amber-400'
                          : 'text-red-400'
                      }`}
                    >
                      {s.win_rate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded overflow-hidden mb-1.5">
                    <div
                      className={`h-full rounded ${
                        s.win_rate >= 55
                          ? 'bg-emerald-500'
                          : s.win_rate >= 50
                          ? 'bg-amber-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.min(100, s.win_rate)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[9px] text-slate-500">
                    <span>{s.trades} trades</span>
                    <span>Avg ${s.avg_pnl.toFixed(4)}</span>
                    <span className={s.total_pnl >= 0 ? 'text-emerald-500' : 'text-red-500'}>
                      Net ${s.total_pnl.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))
            ) : Object.keys(regimeLocal).length > 0 ? (
              Object.entries(regimeLocal).map(([regime, s]) => {
                const regWr = s.trades > 0 ? (s.wins / s.trades) * 100 : 0;
                return (
                  <div
                    key={regime}
                    className="bg-slate-800/50 border border-slate-700/40 rounded p-3 mb-2"
                  >
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-[11px] font-medium text-slate-200 capitalize">
                        {regime.replace('_', ' ')}
                      </span>
                      <span
                        className={`text-[11px] font-bold ${
                          regWr >= 55
                            ? 'text-emerald-400'
                            : regWr >= 50
                            ? 'text-amber-400'
                            : 'text-red-400'
                        }`}
                      >
                        {regWr.toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 bg-slate-700 rounded overflow-hidden mb-1.5">
                      <div
                        className={`h-full rounded ${
                          regWr >= 55
                            ? 'bg-emerald-500'
                            : regWr >= 50
                            ? 'bg-amber-500'
                            : 'bg-red-500'
                        }`}
                        style={{ width: `${Math.min(100, regWr)}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[9px] text-slate-500">
                      <span>{s.trades} trades</span>
                      <span className={s.pnl >= 0 ? 'text-emerald-500' : 'text-red-500'}>
                        Net ${s.pnl.toFixed(2)}
                      </span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-8 text-slate-500 text-xs">
                No regime data yet. Complete some trades first.
              </div>
            )}
          </>
        )}

        {/* ── HEATMAP ─────────────────────────────────────────────────── */}
        {tab === 'heatmap' && (
          <>
            <div className="text-[10px] text-slate-400 mb-2">
              Hourly win-rate heatmap (UTC, last 30 days). Green = profitable window.
            </div>

            {Object.keys(heatmap).length === 0 ? (
              <div className="text-center py-6 text-slate-500 text-xs">
                {loadingApi
                  ? 'Loading…'
                  : 'No heatmap data yet. Need 30+ days of history.'}
              </div>
            ) : (
              <>
                <div className="grid grid-cols-6 gap-1">
                  {Array.from({ length: 24 }, (_, h) => {
                    const key = `${String(h).padStart(2, '0')}:00`;
                    const s = heatmap[key] ?? { win_rate: 0, trades: 0, avg_pnl: 0 };
                    return (
                      <div key={h}>
                        <div className="text-[8px] text-slate-600 text-center mb-0.5">
                          {String(h).padStart(2, '0')}h
                        </div>
                        <HeatCell wr={s.win_rate} trades={s.trades} />
                        {s.trades > 0 && (
                          <div className="text-[7px] text-slate-600 text-center">
                            {s.trades}t
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="flex justify-between text-[9px] text-slate-600 mt-1">
                  <span>■ &lt;35%</span>
                  <span>■ 35–45%</span>
                  <span>■ 45–55%</span>
                  <span>■ 55–65%</span>
                  <span>■ &gt;65%</span>
                </div>

                <div className="text-[10px] font-semibold text-slate-300 mt-3 mb-1.5">
                  Best windows
                </div>
                <div className="space-y-1">
                  {Object.entries(heatmap)
                    .filter(([, s]) => s.trades >= 3)
                    .sort(([, a], [, b]) => b.win_rate - a.win_rate)
                    .slice(0, 5)
                    .map(([hr, s]) => (
                      <WinRateBar key={hr} label={hr} value={s.win_rate} />
                    ))}
                </div>
              </>
            )}
          </>
        )}

        {/* ── ADVICE ──────────────────────────────────────────────────── */}
        {tab === 'recommendations' && (
          <>
            {loadingApi && (
              <div className="text-center py-4 text-slate-500 text-xs animate-pulse">
                Analysing 30-day history…
              </div>
            )}

            {!loadingApi && recs.length === 0 && (
              <div className="text-center py-8 text-slate-500 text-xs">
                No recommendations yet.
                <br />
                Complete at least 5 live trades to unlock quant insights.
              </div>
            )}

            {recs.map((rec, i) => (
              <div
                key={i}
                className={`rounded-lg border p-3 space-y-1.5 ${
                  rec.priority === 'HIGH'
                    ? 'border-red-700/40 bg-red-900/10'
                    : rec.priority === 'MEDIUM'
                    ? 'border-amber-700/30 bg-amber-900/5'
                    : 'border-slate-700/40 bg-slate-800/30'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="text-[11px] font-semibold text-slate-200 leading-tight">
                    {rec.title}
                  </span>
                  <PriorityBadge p={rec.priority} />
                </div>
                <div className="text-[10px] text-slate-300 leading-relaxed">{rec.action}</div>
                <div className="text-[9px] text-slate-500 bg-slate-800/50 rounded px-2 py-1">
                  Evidence: {rec.evidence}
                </div>
                <div className="text-[9px] text-violet-400 capitalize">
                  Category: {rec.category}
                </div>
              </div>
            ))}
          </>
        )}

      </div>
    </div>
  );
}
