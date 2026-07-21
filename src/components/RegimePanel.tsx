import { useState } from 'react';
import {
  Activity, TrendingUp, Waves, Zap, Ban,
  ChevronDown, ChevronUp, ShieldCheck, ShieldAlert, BarChart3,
  Clock, Target, Hash, Shuffle, AlertCircle
} from 'lucide-react';
import type { RegimeState, RegimeType } from '../hooks/useRegimeDetection';

interface RegimePanelProps {
  regimeState: RegimeState;
}

const REGIME_CONFIG: Record<RegimeType, { label: string; icon: React.ElementType; color: string; bg: string; gradient: string; desc: string }> = {
  trending: {
    label: 'Trending',
    icon: TrendingUp,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    gradient: 'from-emerald-500 to-teal-500',
    desc: 'Persistent directional movement detected',
  },
  mean_reverting: {
    label: 'Mean Reverting',
    icon: Waves,
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    gradient: 'from-blue-500 to-cyan-500',
    desc: 'Price oscillates around a central level',
  },
  high_volatility: {
    label: 'High Volatility',
    icon: Zap,
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    gradient: 'from-amber-500 to-orange-500',
    desc: 'Large price swings, elevated risk',
  },
  low_volatility: {
    label: 'Low Volatility',
    icon: Activity,
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
    gradient: 'from-cyan-500 to-blue-500',
    desc: 'Compressed ranges, potential breakout',
  },
  random: {
    label: 'Random Walk',
    icon: Shuffle,
    color: 'text-slate-400',
    bg: 'bg-slate-500/10',
    gradient: 'from-slate-500 to-slate-600',
    desc: 'No detectable statistical edge',
  },
  no_edge: {
    label: 'No Edge',
    icon: Ban,
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    gradient: 'from-red-500 to-rose-500',
    desc: 'All strategies blocked',
  },
};

function MetricBar({ label, value, min, max, color, format }: { label: string; value: number; min: number; max: number; color: string; format?: string }) {
  const pct = max > min ? ((value - min) / (max - min)) * 100 : 50;
  const clamped = Math.max(0, Math.min(100, pct));

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-[10px]">
        <span className="text-slate-500">{label}</span>
        <span className={`font-mono font-medium ${color}`}>
          {format === 'percent' ? `${value.toFixed(1)}%` : value.toFixed(3)}
        </span>
      </div>
      <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 bg-gradient-to-r ${color.replace('text-', 'from-').replace('-400', '-500')} to-${color.replace('text-', '').replace('-400', '-400')}`}
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
    random: '#64748b',
    no_edge: '#ef4444',
  };

  return (
    <div className="flex items-end gap-0.5 h-12 mt-2 rounded-lg overflow-hidden">
      {regimes.map((entry, i) => (
        <div
          key={i}
          className="flex-1 rounded-t-sm transition-all hover:opacity-100"
          style={{
            height: `${entry.confidence}%`,
            backgroundColor: colors[entry.regime],
            opacity: 0.6 + (entry.confidence / 300),
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
    <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 sm:px-5 py-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${config.gradient} flex items-center justify-center shadow-lg`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white">{config.label}</span>
              <span className="text-[10px] text-slate-500 bg-slate-800/50 px-1.5 py-0.5 rounded font-mono">
                {confidence.toFixed(0)}%
              </span>
            </div>
            <div className="text-[10px] text-slate-500">{config.desc}</div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isTradeable ? (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wide">Trading</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-red-500/10 border border-red-500/20">
              <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
              <span className="text-[10px] font-bold text-red-400 uppercase tracking-wide">Blocked</span>
            </div>
          )}
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {/* Status Banner */}
      {!isTradeable && blockReason && (
        <div className="px-4 sm:px-5 py-2.5 bg-red-500/5 border-y border-red-500/20 flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
          <span className="text-xs text-red-400">{blockReason}</span>
        </div>
      )}

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 sm:px-5 pb-5 space-y-4 border-t border-slate-800/50 pt-4">
          {/* Duration & Confidence */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-800/30 rounded-xl border border-slate-700/30 p-3">
              <div className="flex items-center gap-2 text-slate-500 mb-1">
                <Clock className="w-3.5 h-3.5" />
                <span className="text-[10px] uppercase tracking-wider">Duration</span>
              </div>
              <div className="text-lg font-bold text-white font-mono">{duration} <span className="text-xs text-slate-500">ticks</span></div>
            </div>
            <div className="bg-slate-800/30 rounded-xl border border-slate-700/30 p-3">
              <div className="flex items-center gap-2 text-slate-500 mb-1">
                <Target className="w-3.5 h-3.5" />
                <span className="text-[10px] uppercase tracking-wider">Confidence</span>
              </div>
              <div className={`text-lg font-bold ${config.color} font-mono`}>{confidence.toFixed(1)}%</div>
            </div>
          </div>

          {/* Statistical Metrics */}
          <div className="bg-slate-800/30 rounded-xl border border-slate-700/30 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Statistical Metrics</span>
            </div>

            <MetricBar label="Hurst Exponent" value={metrics.hurstExponent} min={0} max={1} color={metrics.hurstExponent > 0.55 ? 'text-emerald-400' : metrics.hurstExponent < 0.45 ? 'text-blue-400' : 'text-slate-400'} />
            <MetricBar label="Trend Strength (R)" value={metrics.trendStrength} min={0} max={1} color={metrics.trendStrength > 0.3 ? 'text-emerald-400' : 'text-slate-400'} />
            <MetricBar label="Autocorrelation" value={metrics.autoCorrelation} min={-1} max={1} color={metrics.autoCorrelation > 0.1 ? 'text-emerald-400' : metrics.autoCorrelation < -0.1 ? 'text-blue-400' : 'text-slate-400'} />
            <MetricBar label="Volatility Percentile" value={metrics.volatilityPercentile} min={0} max={100} color={metrics.volatilityPercentile > 70 ? 'text-amber-400' : metrics.volatilityPercentile < 30 ? 'text-cyan-400' : 'text-slate-400'} format="percent" />
            <MetricBar label="Variance Ratio" value={metrics.varianceRatio} min={0} max={2} color={metrics.varianceRatio > 1.2 ? 'text-emerald-400' : metrics.varianceRatio < 0.8 ? 'text-blue-400' : 'text-slate-400'} />
            <MetricBar label="ADF Statistic" value={metrics.adfStatistic} min={-5} max={5} color={metrics.adfStatistic < -2 ? 'text-blue-400' : 'text-slate-400'} />
          </div>

          {/* Regime History */}
          {history.length > 0 && (
            <div className="bg-slate-800/30 rounded-xl border border-slate-700/30 p-4">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Regime History (last 30)</span>
              </div>
              <RegimeHistoryChart history={history} />
              <div className="flex flex-wrap gap-2 mt-3">
                {Object.entries(REGIME_CONFIG).map(([key, cfg]) => (
                  <div key={key} className="flex items-center gap-1.5">
                    <div className={`w-2.5 h-2.5 rounded-full bg-gradient-to-br ${cfg.gradient}`} />
                    <span className="text-[10px] text-slate-500">{cfg.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Strategy Compatibility */}
          <div className="bg-slate-800/30 rounded-xl border border-slate-700/30 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Hash className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Strategy Compatibility</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries({
                even_odd: 'Even/Odd',
                over_under: 'Over/Under',
                match_diff: 'Match/Diff',
                rise_fall: 'Rise/Fall',
                digit_match: 'Digit Match',
                composite: 'Composite',
              }).map(([key, label]) => {
                const supported: Record<string, RegimeType[]> = {
                  even_odd: ['mean_reverting', 'low_volatility'],
                  over_under: ['mean_reverting', 'low_volatility'],
                  match_diff: ['mean_reverting', 'low_volatility'],
                  rise_fall: ['trending', 'high_volatility'],
                  digit_match: ['random', 'low_volatility'],
                  composite: ['trending', 'mean_reverting', 'low_volatility'],
                };

                const isCompatible = (supported[key] || []).includes(currentRegime);

                return (
                  <div key={key} className="flex items-center justify-between p-2 rounded-lg bg-slate-900/50">
                    <span className="text-xs text-slate-300">{label}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
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
