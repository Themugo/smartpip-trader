import { useState } from 'react';
import {
  Activity, TrendingUp, TrendingDown, Waves, Zap, Ban,
  ChevronDown, ChevronUp, ShieldCheck, ShieldAlert, BarChart3,
  Clock, Target, Hash, Shuffle
} from 'lucide-react';
import type { RegimeState, RegimeType } from '../hooks/useRegimeDetection';

interface RegimePanelProps {
  regimeState: RegimeState;
}

const REGIME_CONFIG: Record<RegimeType, { label: string; icon: React.ElementType; color: string; bg: string; desc: string }> = {
  trending: {
    label: 'Trending',
    icon: TrendingUp,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    desc: 'Persistent directional movement detected',
  },
  mean_reverting: {
    label: 'Mean Reverting',
    icon: Waves,
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    desc: 'Price oscillates around a central level',
  },
  high_volatility: {
    label: 'High Volatility',
    icon: Zap,
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    desc: 'Large price swings, elevated risk',
  },
  low_volatility: {
    label: 'Low Volatility',
    icon: Activity,
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
    desc: 'Compressed ranges, potential breakout',
  },
  random: {
    label: 'Random Walk',
    icon: Shuffle,
    color: 'text-slate-400',
    bg: 'bg-slate-500/10',
    desc: 'No detectable statistical edge',
  },
  no_edge: {
    label: 'No Edge',
    icon: Ban,
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    desc: 'All strategies blocked — insufficient edge',
  },
};

function MetricBar({ label, value, min, max, color }: { label: string; value: number; min: number; max: number; color: string }) {
  const pct = max > min ? ((value - min) / (max - min)) * 100 : 50;
  const clamped = Math.max(0, Math.min(100, pct));

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px]">
        <span className="text-slate-400">{label}</span>
        <span className={`font-medium ${color}`}>{value.toFixed(3)}</span>
      </div>
      <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color.replace('text-', 'bg-')}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}

function RegimeHistoryChart({ history }: { history: { regime: RegimeType; tick: number; confidence: number }[] }) {
  if (history.length < 2) return null;

  const regimes = history.slice(-30);
  const colors: Record<RegimeType, string> = {
    trending: '#10b981',
    mean_reverting: '#3b82f6',
    high_volatility: '#f59e0b',
    low_volatility: '#06b6d4',
    random: '#94a3b8',
    no_edge: '#ef4444',
  };

  return (
    <div className="flex items-end gap-0.5 h-10 mt-2">
      {regimes.map((entry, i) => (
        <div
          key={i}
          className="flex-1 rounded-t-sm transition-all"
          style={{
            height: `${entry.confidence}%`,
            backgroundColor: colors[entry.regime],
            opacity: 0.7 + (entry.confidence / 500),
          }}
          title={`${entry.regime} @ tick ${entry.tick} (${entry.confidence.toFixed(0)}%)`}
        />
      ))}
    </div>
  );
}

export function RegimePanel({ regimeState }: RegimePanelProps) {
  const [expanded, setExpanded] = useState(false);
  const { currentRegime, confidence, duration, metrics, isTradeable, blockReason, history } = regimeState;

  const config = REGIME_CONFIG[currentRegime];
  const Icon = config.icon;

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-750 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg ${config.bg} flex items-center justify-center`}>
            <Icon className={`w-4 h-4 ${config.color}`} />
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white">{config.label}</span>
              <span className="text-[10px] text-slate-500">{confidence.toFixed(0)}% conf</span>
            </div>
            <div className="text-[10px] text-slate-400">{config.desc}</div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isTradeable ? (
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
              <ShieldCheck className="w-3 h-3 text-emerald-400" />
              <span className="text-[10px] font-medium text-emerald-400">Trading</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-red-500/10 border border-red-500/20">
              <ShieldAlert className="w-3 h-3 text-red-400" />
              <span className="text-[10px] font-medium text-red-400">Blocked</span>
            </div>
          )}
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {/* Status Banner */}
      {!isTradeable && blockReason && (
        <div className="px-4 py-2 bg-red-500/10 border-y border-red-500/20">
          <div className="flex items-center gap-2">
            <Ban className="w-3.5 h-3.5 text-red-400 shrink-0" />
            <span className="text-xs text-red-400">{blockReason}</span>
          </div>
        </div>
      )}

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-700/50 space-y-4 pt-3">
          {/* Regime Duration */}
          <div className="flex items-center gap-3">
            <Clock className="w-4 h-4 text-slate-400" />
            <div className="flex-1">
              <div className="text-[10px] text-slate-400">Regime Duration</div>
              <div className="text-sm font-medium text-slate-200">{duration} ticks</div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-slate-400">Confidence</div>
              <div className={`text-sm font-bold ${config.color}`}>{confidence.toFixed(1)}%</div>
            </div>
          </div>

          {/* Statistical Metrics */}
          <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3 space-y-2.5">
            <div className="flex items-center gap-1.5 mb-1">
              <BarChart3 className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">Statistical Metrics</span>
            </div>

            <MetricBar
              label="Hurst Exponent"
              value={metrics.hurstExponent}
              min={0}
              max={1}
              color={metrics.hurstExponent > 0.55 ? 'text-emerald-400' : metrics.hurstExponent < 0.45 ? 'text-blue-400' : 'text-slate-400'}
            />
            <MetricBar
              label="Trend Strength (R²)"
              value={metrics.trendStrength}
              min={0}
              max={1}
              color={metrics.trendStrength > 0.3 ? 'text-emerald-400' : 'text-slate-400'}
            />
            <MetricBar
              label="Autocorrelation"
              value={metrics.autoCorrelation}
              min={-1}
              max={1}
              color={metrics.autoCorrelation > 0.1 ? 'text-emerald-400' : metrics.autoCorrelation < -0.1 ? 'text-blue-400' : 'text-slate-400'}
            />
            <MetricBar
              label="Volatility Percentile"
              value={metrics.volatilityPercentile}
              min={0}
              max={100}
              color={metrics.volatilityPercentile > 70 ? 'text-amber-400' : metrics.volatilityPercentile < 30 ? 'text-cyan-400' : 'text-slate-400'}
            />
            <MetricBar
              label="Variance Ratio"
              value={metrics.varianceRatio}
              min={0}
              max={2}
              color={metrics.varianceRatio > 1.2 ? 'text-emerald-400' : metrics.varianceRatio < 0.8 ? 'text-blue-400' : 'text-slate-400'}
            />
            <MetricBar
              label="ADF Statistic"
              value={metrics.adfStatistic}
              min={-5}
              max={5}
              color={metrics.adfStatistic < -2 ? 'text-blue-400' : 'text-slate-400'}
            />
          </div>

          {/* Regime History */}
          {history.length > 0 && (
            <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <Target className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-[10px] text-slate-400 uppercase tracking-wider">Regime History (last 30)</span>
              </div>
              <RegimeHistoryChart history={history} />
              <div className="flex flex-wrap gap-2 mt-2">
                {Object.entries(REGIME_CONFIG).map(([key, cfg]) => (
                  <div key={key} className="flex items-center gap-1">
                    <div className={`w-2 h-2 rounded-full ${cfg.bg.replace('/10', '')}`} />
                    <span className="text-[10px] text-slate-500">{cfg.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Strategy Compatibility */}
          <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Hash className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">Strategy Compatibility</span>
            </div>
            <div className="space-y-1.5">
              {Object.entries({
                even_odd: 'Even/Odd',
                over_under: 'Over/Under',
                match_diff: 'Match/Diff',
                rise_fall: 'Rise/Fall',
                digit_match: 'Digit Match',
                composite: 'Composite',
              }).map(([key, label]) => {
                const supported = {
                  even_odd: ['mean_reverting', 'low_volatility'],
                  over_under: ['mean_reverting', 'low_volatility'],
                  match_diff: ['mean_reverting', 'low_volatility'],
                  rise_fall: ['trending', 'high_volatility'],
                  digit_match: ['random', 'low_volatility'],
                  composite: ['trending', 'mean_reverting', 'low_volatility'],
                }[key] || [];

                const isCompatible = supported.includes(currentRegime);

                return (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-xs text-slate-300">{label}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      isCompatible
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-red-500/10 text-red-400'
                    }`}>
                      {isCompatible ? 'Active' : 'Blocked'}
                    </span>
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
