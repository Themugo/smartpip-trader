import { useState, useEffect } from 'react';
import {
  ShieldCheck, ShieldAlert, TrendingUp, TrendingDown, Activity,
  BarChart3, Percent, DollarSign, Clock, AlertTriangle, CheckCircle,
  XCircle, ChevronDown, ChevronUp, Brain, Target, Zap, Hash
} from 'lucide-react';

interface ValidationResult {
  strategy_name: string;
  symbol: string;
  total_ticks: number;
  in_sample: Metrics;
  out_of_sample: Metrics;
  monte_carlo: MonteCarloResults;
  deployable: boolean;
  timestamp: string;
}

interface Metrics {
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  profit_factor: number;
  expectancy: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  recovery_factor: number;
  max_drawdown: number;
  max_drawdown_duration: number;
  net_profit: number;
  avg_trade: number;
  avg_win: number;
  avg_loss: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
  total_fees: number;
  fee_impact_pct: number;
  total_return_pct: number;
  volatility: number;
  regime_performance: Record<string, RegimePerf>;
  is_valid: boolean;
  validation_errors: string[];
}

interface RegimePerf {
  trades: number;
  win_rate: number;
  avg_profit: number;
  total_pnl: number;
}

interface MonteCarloResults {
  num_simulations: number;
  mean_final_pnl: number;
  std_final_pnl: number;
  median_final_pnl: number;
  prob_profit: number;
  confidence_95: [number, number];
  confidence_99: [number, number];
  max_dd_95: number;
  max_dd_mean: number;
  worst_case_pnl: number;
  best_case_pnl: number;
}

interface ValidationDashboardProps {
  results?: ValidationResult[];
}

function MetricCard({ label, value, icon: Icon, color, suffix = '' }: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color: string;
  suffix?: string;
}) {
  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon className={`w-3.5 h-3.5 ${color}`} />
        <span className="text-[10px] text-slate-400 uppercase tracking-wider">{label}</span>
      </div>
      <div className={`text-lg font-bold ${color}`}>
        {typeof value === 'number' ? value.toFixed(4) : value}{suffix}
      </div>
    </div>
  );
}

function StatusBadge({ deployable }: { deployable: boolean }) {
  return deployable ? (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
      <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
      <span className="text-xs font-medium text-emerald-400">DEPLOYABLE</span>
    </div>
  ) : (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-500/10 border border-red-500/20">
      <XCircle className="w-3.5 h-3.5 text-red-400" />
      <span className="text-xs font-medium text-red-400">BLOCKED</span>
    </div>
  );
}

function StrategyPanel({ result }: { result: ValidationResult }) {
  const [expanded, setExpanded] = useState(false);
  const oos = result.out_of_sample;
  const mc = result.monte_carlo;

  const isPositive = oos.expectancy > 0;
  const isProfitable = oos.net_profit > 0;

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-750 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`w-2 h-2 rounded-full ${result.deployable ? 'bg-emerald-500' : 'bg-red-500'}`} />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white">{result.strategy_name}</span>
              <span className="text-xs text-slate-500 font-mono">{result.symbol}</span>
            </div>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="text-[10px] text-slate-400">
                {oos.total_trades.toLocaleString()} trades
              </span>
              <span className={`text-[10px] font-medium ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                Expectancy: {oos.expectancy > 0 ? '+' : ''}{oos.expectancy.toFixed(4)}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge deployable={result.deployable} />
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-700/50 space-y-4">
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-3">
            <MetricCard label="Win Rate" value={oos.win_rate} icon={Percent} color="text-blue-400" suffix="%" />
            <MetricCard label="Profit Factor" value={oos.profit_factor} icon={TrendingUp} color={oos.profit_factor >= 1 ? 'text-emerald-400' : 'text-red-400'} />
            <MetricCard label="Sharpe" value={oos.sharpe_ratio} icon={Activity} color={oos.sharpe_ratio > 0 ? 'text-emerald-400' : 'text-red-400'} />
            <MetricCard label="Max DD" value={oos.max_drawdown} icon={TrendingDown} color="text-red-400" suffix="$" />
            <MetricCard label="Expectancy" value={oos.expectancy} icon={DollarSign} color={isPositive ? 'text-emerald-400' : 'text-red-400'} suffix="$" />
            <MetricCard label="Net Profit" value={oos.net_profit} icon={BarChart3} color={isProfitable ? 'text-emerald-400' : 'text-red-400'} suffix="$" />
            <MetricCard label="Recovery" value={oos.recovery_factor} icon={ShieldCheck} color={oos.recovery_factor > 1 ? 'text-emerald-400' : 'text-amber-400'} />
            <MetricCard label="Sortino" value={oos.sortino_ratio} icon={Target} color={oos.sortino_ratio > 0 ? 'text-emerald-400' : 'text-red-400'} />
          </div>

          {/* Trade Distribution */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
              <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-2">Win/Loss Distribution</div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full transition-all"
                    style={{ width: `${oos.win_rate}%` }}
                  />
                </div>
                <span className="text-xs text-emerald-400 font-medium">{oos.win_rate.toFixed(1)}%</span>
              </div>
              <div className="flex justify-between mt-2 text-[10px] text-slate-500">
                <span>Wins: {oos.wins}</span>
                <span>Losses: {oos.losses}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 mt-2">
                <div className="text-center p-2 rounded bg-emerald-500/10">
                  <div className="text-[10px] text-slate-400">Avg Win</div>
                  <div className="text-sm font-bold text-emerald-400">+${oos.avg_win.toFixed(2)}</div>
                </div>
                <div className="text-center p-2 rounded bg-red-500/10">
                  <div className="text-[10px] text-slate-400">Avg Loss</div>
                  <div className="text-sm font-bold text-red-400">${oos.avg_loss.toFixed(2)}</div>
                </div>
              </div>
            </div>

            {/* Monte Carlo */}
            <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
              <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-2">Monte Carlo (n={mc.num_simulations})</div>
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Prob. Profit</span>
                  <span className={`font-medium ${mc.prob_profit > 0.5 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {(mc.prob_profit * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Mean P&L</span>
                  <span className="text-slate-300">${mc.mean_final_pnl.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">95% CI</span>
                  <span className="text-slate-300">[{mc.confidence_95[0].toFixed(2)}, {mc.confidence_95[1].toFixed(2)}]</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Max DD (95%)</span>
                  <span className="text-red-400">${mc.max_dd_95.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Worst Case</span>
                  <span className="text-red-400">${mc.worst_case_pnl.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Regime Performance */}
          {Object.keys(oos.regime_performance).length > 0 && (
            <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
              <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-2">Regime Performance</div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {Object.entries(oos.regime_performance).map(([regime, perf]) => (
                  <div key={regime} className="p-2 rounded bg-slate-800">
                    <div className="text-[10px] text-slate-400 capitalize">{regime.replace('_', ' ')}</div>
                    <div className="text-xs font-medium text-slate-200">{perf.trades} trades</div>
                    <div className={`text-[10px] ${perf.win_rate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {perf.win_rate.toFixed(1)}% WR
                    </div>
                    <div className={`text-[10px] ${perf.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      ${perf.total_pnl.toFixed(2)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Validation Errors */}
          {oos.validation_errors.length > 0 && (
            <div className="space-y-1">
              {oos.validation_errors.map((err, i) => (
                <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                  <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                  <span className="text-xs text-red-400">{err}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ValidationDashboard({ results }: ValidationDashboardProps) {
  const [filter, setFilter] = useState<'all' | 'deployable' | 'blocked'>('all');

  if (!results || results.length === 0) {
    return (
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-8 text-center">
        <Brain className="w-10 h-10 text-slate-500 mx-auto mb-3" />
        <h3 className="text-sm font-semibold text-slate-300 mb-1">No Validation Results</h3>
        <p className="text-xs text-slate-500">Run the validation suite to see results here.</p>
      </div>
    );
  }

  const filtered = results.filter((r) => {
    if (filter === 'deployable') return r.deployable;
    if (filter === 'blocked') return !r.deployable;
    return true;
  });

  const deployableCount = results.filter((r) => r.deployable).length;
  const blockedCount = results.length - deployableCount;

  return (
    <div className="space-y-4">
      {/* Summary Header */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-200">Strategy Validation</h3>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Filter:</span>
            {(['all', 'deployable', 'blocked'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2.5 py-1 rounded text-[10px] font-medium transition-colors ${
                  filter === f
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'bg-slate-900 text-slate-500 hover:text-slate-300'
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
                {f === 'deployable' && ` (${deployableCount})`}
                {f === 'blocked' && ` (${blockedCount})`}
              </button>
            ))}
          </div>
        </div>

        {/* Deployment Gate Banner */}
        {deployableCount === 0 ? (
          <div className="flex items-center gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <ShieldAlert className="w-5 h-5 text-red-400 shrink-0" />
            <div>
              <div className="text-sm font-medium text-red-400">DEPLOYMENT BLOCKED</div>
              <div className="text-xs text-red-300/70">
                No strategies passed validation. All show negative expectancy. Review and refine strategies before deployment.
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
            <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
            <div>
              <div className="text-sm font-medium text-emerald-400">DEPLOYMENT ALLOWED</div>
              <div className="text-xs text-emerald-300/70">
                {deployableCount} strategy-market combinations passed validation with positive expectancy.
              </div>
            </div>
          </div>
        )}

        {/* Summary Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4">
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Total Tests</div>
            <div className="text-lg font-bold text-white">{results.length}</div>
          </div>
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Deployable</div>
            <div className="text-lg font-bold text-emerald-400">{deployableCount}</div>
          </div>
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Blocked</div>
            <div className="text-lg font-bold text-red-400">{blockedCount}</div>
          </div>
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Avg Expectancy</div>
            <div className={`text-lg font-bold ${
              results.reduce((s, r) => s + r.out_of_sample.expectancy, 0) / results.length > 0
                ? 'text-emerald-400' : 'text-red-400'
            }`}>
              {(results.reduce((s, r) => s + r.out_of_sample.expectancy, 0) / results.length).toFixed(4)}
            </div>
          </div>
        </div>
      </div>

      {/* Strategy Panels */}
      <div className="space-y-2">
        {filtered.map((result, i) => (
          <StrategyPanel key={`${result.strategy_name}-${result.symbol}-${i}`} result={result} />
        ))}
      </div>
    </div>
  );
}
