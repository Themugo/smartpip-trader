import { useState, useMemo } from 'react';
import {
  BarChart3, TrendingUp, TrendingDown, Activity, Zap,
  Waves, Ban, ChevronDown, ChevronUp, Filter, Percent,
 Target, ShieldCheck, ShieldAlert
} from 'lucide-react';
import type { RegimeType } from '../hooks/useRegimeDetection';

interface RegimeTradeData {
  regime: RegimeType;
  strategy: string;
  symbol: string;
  trades: number;
  wins: number;
  losses: number;
  profit: number;
  maxDrawdown: number;
  avgWin: number;
  avgLoss: number;
  timestamp: string;
}

interface RegimeDashboardProps {
  tradeData?: RegimeTradeData[];
}

const REGIME_META: Record<RegimeType, { label: string; color: string; icon: React.ElementType }> = {
  trending: { label: 'Trending', color: 'text-emerald-400', icon: TrendingUp },
  mean_reverting: { label: 'Mean Reverting', color: 'text-blue-400', icon: Waves },
  high_volatility: { label: 'High Volatility', color: 'text-amber-400', icon: Zap },
  low_volatility: { label: 'Low Volatility', color: 'text-cyan-400', icon: Activity },
  random: { label: 'Random', color: 'text-slate-400', icon: Target },
  no_edge: { label: 'No Edge', color: 'text-red-400', icon: Ban },
};

function aggregateByRegime(data: RegimeTradeData[]) {
  const agg: Record<RegimeType, RegimeTradeData[]> = {
    trending: [], mean_reverting: [], high_volatility: [], low_volatility: [], random: [], no_edge: [],
  };
  for (const d of data) {
    if (agg[d.regime]) agg[d.regime].push(d);
  }
  return agg;
}

function calcRegimeStats(items: RegimeTradeData[]) {
  const totalTrades = items.reduce((s, i) => s + i.trades, 0);
  const totalWins = items.reduce((s, i) => s + i.wins, 0);
  const totalProfit = items.reduce((s, i) => s + i.profit, 0);
  const grossProfit = items.reduce((s, i) => s + i.wins * i.avgWin, 0);
  const grossLoss = Math.abs(items.reduce((s, i) => s + i.losses * i.avgLoss, 0)) || 1e-10;
  const maxDD = Math.max(...items.map((i) => i.maxDrawdown), 0);

  return {
    totalTrades,
    winRate: totalTrades > 0 ? (totalWins / totalTrades) * 100 : 0,
    profitFactor: grossProfit / grossLoss,
    totalProfit,
    maxDrawdown: maxDD,
    avgWin: totalWins > 0 ? grossProfit / totalWins : 0,
    avgLoss: totalTrades - totalWins > 0 ? Math.abs(grossLoss) / (totalTrades - totalWins) : 0,
  };
}

function RegimeCard({ regime, items }: { regime: RegimeType; items: RegimeTradeData[] }) {
  const [expanded, setExpanded] = useState(false);
  const meta = REGIME_META[regime];
  const Icon = meta.icon;
  const stats = calcRegimeStats(items);

  if (items.length === 0) return null;

  const isProfitable = stats.totalProfit > 0;
  const hasEdge = stats.profitFactor > 1 && stats.winRate > 50;

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-750 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg bg-slate-900 border border-slate-700 flex items-center justify-center`}>
            <Icon className={`w-4 h-4 ${meta.color}`} />
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white">{meta.label}</span>
              <span className="text-[10px] text-slate-500">{stats.totalTrades} trades</span>
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`text-xs font-medium ${isProfitable ? 'text-emerald-400' : 'text-red-400'}`}>
                {isProfitable ? '+' : ''}${stats.totalProfit.toFixed(2)}
              </span>
              <span className={`text-xs ${hasEdge ? 'text-emerald-400' : 'text-amber-400'}`}>
                PF: {stats.profitFactor.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {hasEdge ? (
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          ) : (
            <ShieldAlert className="w-4 h-4 text-amber-400" />
          )}
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-700/50 space-y-3 pt-3">
          {/* Key Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div className="bg-slate-900 rounded-lg p-2.5 text-center">
              <div className="text-[10px] text-slate-400">Win Rate</div>
              <div className={`text-sm font-bold ${stats.winRate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
                {stats.winRate.toFixed(1)}%
              </div>
            </div>
            <div className="bg-slate-900 rounded-lg p-2.5 text-center">
              <div className="text-[10px] text-slate-400">Profit Factor</div>
              <div className={`text-sm font-bold ${stats.profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400'}`}>
                {stats.profitFactor.toFixed(2)}
              </div>
            </div>
            <div className="bg-slate-900 rounded-lg p-2.5 text-center">
              <div className="text-[10px] text-slate-400">Max Drawdown</div>
              <div className="text-sm font-bold text-red-400">${stats.maxDrawdown.toFixed(2)}</div>
            </div>
            <div className="bg-slate-900 rounded-lg p-2.5 text-center">
              <div className="text-[10px] text-slate-400">Expectancy</div>
              <div className={`text-sm font-bold ${stats.totalProfit / (stats.totalTrades || 1) > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                ${(stats.totalProfit / (stats.totalTrades || 1)).toFixed(4)}
              </div>
            </div>
          </div>

          {/* Avg Win/Loss */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-emerald-500/10 rounded-lg p-2.5 border border-emerald-500/20">
              <div className="text-[10px] text-emerald-400">Avg Win</div>
              <div className="text-sm font-bold text-emerald-400">+${stats.avgWin.toFixed(2)}</div>
            </div>
            <div className="bg-red-500/10 rounded-lg p-2.5 border border-red-500/20">
              <div className="text-[10px] text-red-400">Avg Loss</div>
              <div className="text-sm font-bold text-red-400">-${stats.avgLoss.toFixed(2)}</div>
            </div>
          </div>

          {/* Per-Strategy Breakdown */}
          <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
            <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-2">By Strategy</div>
            <div className="space-y-1.5">
              {Object.entries(
                items.reduce((acc: Record<string, RegimeTradeData[]>, item) => {
                  acc[item.strategy] = acc[item.strategy] || [];
                  acc[item.strategy].push(item);
                  return acc;
                }, {})
              ).map(([strategy, strategyItems]) => {
                const s = calcRegimeStats(strategyItems);
                return (
                  <div key={strategy} className="flex items-center justify-between py-1 border-b border-slate-700/30 last:border-0 min-w-0">
                    <span className="text-xs text-slate-300 capitalize truncate">{strategy.replace('_', ' ')}</span>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-[10px] text-slate-500">{s.totalTrades} trades</span>
                      <span className={`text-xs font-medium ${s.winRate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {s.winRate.toFixed(1)}%
                      </span>
                      <span className={`text-xs font-medium ${s.profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400'}`}>
                        PF {s.profitFactor.toFixed(2)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Per-Symbol Breakdown */}
          <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
            <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-2">By Symbol</div>
            <div className="space-y-1.5">
              {Object.entries(
                items.reduce((acc: Record<string, RegimeTradeData[]>, item) => {
                  acc[item.symbol] = acc[item.symbol] || [];
                  acc[item.symbol].push(item);
                  return acc;
                }, {})
              ).map(([symbol, symbolItems]) => {
                const s = calcRegimeStats(symbolItems);
                return (
                  <div key={symbol} className="flex items-center justify-between py-1 border-b border-slate-700/30 last:border-0 min-w-0">
                    <span className="text-xs text-slate-300 font-mono truncate">{symbol}</span>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-[10px] text-slate-500">{s.totalTrades} trades</span>
                      <span className={`text-xs font-medium ${s.totalProfit > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {s.totalProfit > 0 ? '+' : ''}${s.totalProfit.toFixed(2)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function RegimeDashboard({ tradeData = [] }: RegimeDashboardProps) {
  const [filterStrategy, setFilterStrategy] = useState<string>('all');

  const strategies = useMemo(() => {
    const set = new Set(tradeData.map((d) => d.strategy));
    return ['all', ...Array.from(set)];
  }, [tradeData]);

  const filtered = useMemo(() => {
    if (filterStrategy === 'all') return tradeData;
    return tradeData.filter((d) => d.strategy === filterStrategy);
  }, [tradeData, filterStrategy]);

  const byRegime = aggregateByRegime(filtered);

  const overallStats = useMemo(() => {
    const all = calcRegimeStats(filtered);
    return all;
  }, [filtered]);

  if (tradeData.length === 0) {
    return (
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-8 text-center">
        <BarChart3 className="w-10 h-10 text-slate-500 mx-auto mb-3" />
        <h3 className="text-sm font-semibold text-slate-300 mb-1">No Regime Data</h3>
        <p className="text-xs text-slate-500">Trade data with regime labels will appear here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-200">Regime Performance Dashboard</h3>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={filterStrategy}
              onChange={(e) => setFilterStrategy(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-xs text-white max-w-[160px] truncate"
            >
              {strategies.map((s) => (
                <option key={s} value={s}>
                  {s === 'all' ? 'All Strategies' : s.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Overall Summary */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Total Trades</div>
            <div className="text-lg font-bold text-white">{overallStats.totalTrades}</div>
          </div>
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Win Rate</div>
            <div className={`text-lg font-bold ${overallStats.winRate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
              {overallStats.winRate.toFixed(1)}%
            </div>
          </div>
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Profit Factor</div>
            <div className={`text-lg font-bold ${overallStats.profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400'}`}>
              {overallStats.profitFactor.toFixed(2)}
            </div>
          </div>
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Max Drawdown</div>
            <div className="text-lg font-bold text-red-400">${overallStats.maxDrawdown.toFixed(2)}</div>
          </div>
        </div>
      </div>

      {/* Regime Cards */}
      <div className="space-y-2">
        {(['trending', 'mean_reverting', 'high_volatility', 'low_volatility', 'random', 'no_edge'] as RegimeType[]).map(
          (regime) => (
            <RegimeCard key={regime} regime={regime} items={byRegime[regime] || []} />
          )
        )}
      </div>
    </div>
  );
}
