import { useState } from 'react';
import {
  Eye, CheckCircle, XCircle, TrendingUp, TrendingDown, Clock,
  ChevronDown, ChevronUp, ShieldCheck, ShieldAlert, Activity,
  DollarSign, Target, Zap, Ban, Calendar, BarChart3, ArrowUpRight, ArrowDownRight
} from 'lucide-react';
import type { ShadowSignal, ShadowMetrics, ShadowDailyMetric } from '../hooks/useShadowMode';

interface ShadowModePanelProps {
  signals: ShadowSignal[];
  metrics: ShadowMetrics;
  dailyMetrics?: ShadowDailyMetric[];
}

function SignalCard({ signal }: { signal: ShadowSignal }) {
  const [expanded, setExpanded] = useState(false);

  const outcomeColor = signal.actualOutcome === 'win' ? 'text-emerald-400' :
    signal.actualOutcome === 'loss' ? 'text-red-400' :
    signal.actualOutcome === 'missed' ? 'text-amber-400' : 'text-slate-400';

  const executedColor = signal.executed ? 'text-emerald-400' : 'text-amber-400';

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-slate-750 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${
            signal.actualOutcome === 'win' ? 'bg-emerald-500' :
            signal.actualOutcome === 'loss' ? 'bg-red-500' :
            signal.actualOutcome === 'missed' ? 'bg-amber-500' :
            'bg-slate-500'
          }`} />
          <span className="text-xs text-slate-300">{signal.contractType}</span>
          <span className="text-[10px] text-slate-500 font-mono">{signal.symbol}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] ${outcomeColor}`}>{signal.actualOutcome}</span>
          {expanded ? <ChevronUp className="w-3 h-3 text-slate-400" /> : <ChevronDown className="w-3 h-3 text-slate-400" />}
        </div>
      </button>
      {expanded && (
        <div className="px-3 pb-2 border-t border-slate-700/50 space-y-1 pt-2">
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Predicted</span>
            <span className="text-slate-300">{signal.expectedOutcome} ({signal.confidence}%)</span>
          </div>
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Actual</span>
            <span className={outcomeColor}>{signal.actualOutcome}</span>
          </div>
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Expected P&L</span>
            <span className="text-slate-300">${signal.expectedPnl.toFixed(2)}</span>
          </div>
          {signal.actualPnl !== null && (
            <div className="flex justify-between text-[10px]">
              <span className="text-slate-500">Actual P&L</span>
              <span className={signal.actualPnl > 0 ? 'text-emerald-400' : 'text-red-400'}>
                ${signal.actualPnl.toFixed(2)}
              </span>
            </div>
          )}
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Latency</span>
            <span className="text-slate-300">{signal.latencyMs}ms</span>
          </div>
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Executed</span>
            <span className={executedColor}>{signal.executed ? 'Yes' : 'No'}</span>
          </div>
          {signal.missedReason && (
            <div className="text-[10px] text-amber-400">{signal.missedReason}</div>
          )}
        </div>
      )}
    </div>
  );
}

function DailyMetricRow({ metric }: { metric: ShadowDailyMetric }) {
  return (
    <div className="grid grid-cols-7 gap-1 text-[10px] py-1.5 border-b border-slate-700/30 items-center">
      <span className="text-slate-400">{metric.date}</span>
      <span className="text-slate-300 text-center">{metric.totalSignals}</span>
      <span className={`text-center ${metric.signalAccuracy >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>{metric.signalAccuracy.toFixed(0)}%</span>
      <span className={`text-center ${metric.paperPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>${metric.paperPnl.toFixed(2)}</span>
      <span className={`text-center ${metric.realPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>${metric.realPnl.toFixed(2)}</span>
      <span className="text-slate-300 text-center">{metric.avgLatencyMs.toFixed(0)}ms</span>
      <span className={`text-center ${metric.modelDrift < 10 ? 'text-emerald-400' : metric.modelDrift < 20 ? 'text-amber-400' : 'text-red-400'}`}>{metric.modelDrift.toFixed(1)}%</span>
    </div>
  );
}

function EquityChart({ data }: { data: ShadowDailyMetric[] }) {
  if (data.length < 2) return null;
  const reversed = [...data].reverse();
  const values = reversed.map(d => d.paperPnl);
  const cumulative: number[] = [];
  let sum = 0;
  for (const v of values) { sum += v; cumulative.push(sum); }

  const maxVal = Math.max(...cumulative, 0);
  const minVal = Math.min(...cumulative, 0);
  const range = maxVal - minVal || 1;

  return (
    <div className="h-24 relative">
      <svg viewBox={`0 0 100 ${range > 0 ? 40 : 1}`} preserveAspectRatio="none" className="w-full h-full">
        <polyline
          points={cumulative.map((v, i) => {
            const x = (i / (cumulative.length - 1)) * 100;
            const y = range > 0 ? ((v - minVal) / range) * 40 : 20;
            return `${x},${y}`;
          }).join(' ')}
          fill="none"
          stroke="#10b981"
          strokeWidth="0.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

export function ShadowModePanel({ signals, metrics, dailyMetrics = [] }: ShadowModePanelProps) {
  const [filter, setFilter] = useState<'all' | 'executed' | 'missed' | 'pending'>('all');
  const [activeView, setActiveView] = useState<'signals' | 'daily'>('signals');

  const filtered = signals.filter(s => {
    if (filter === 'executed') return s.executed;
    if (filter === 'missed') return !s.executed && s.actualOutcome === 'missed';
    if (filter === 'pending') return s.actualOutcome === 'pending';
    return true;
  });

  const daysRemaining = Math.max(0, 30 - metrics.daysInShadow);
  const progressPct = Math.min(100, (metrics.daysInShadow / 30) * 100);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
        <div className="flex items-center gap-2 mb-4">
          <Eye className="w-5 h-5 text-cyan-400" />
          <h3 className="text-sm font-semibold text-slate-200">Shadow Mode</h3>
          <span className="text-[10px] text-slate-500 bg-slate-900 px-1.5 py-0.5 rounded">Paper Trading</span>
        </div>

        {/* Qualification Banner */}
        <div className={`p-3 rounded-lg border mb-4 ${
          metrics.isQualified
            ? 'bg-emerald-500/10 border-emerald-500/20'
            : 'bg-amber-500/10 border-amber-500/20'
        }`}>
          <div className="flex items-center gap-2">
            {metrics.isQualified ? (
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
            ) : (
              <ShieldAlert className="w-5 h-5 text-amber-400" />
            )}
            <div className="flex-1">
              <div className={`text-sm font-medium ${metrics.isQualified ? 'text-emerald-400' : 'text-amber-400'}`}>
                {metrics.isQualified ? 'LIVE TRADING QUALIFIED' : 'SHADOW MODE ONLY'}
              </div>
              <div className="text-xs text-slate-400">
                {metrics.daysInShadow} days / 30 required • {metrics.profitableDays} profitable days
                {metrics.isQualified ? ' • Qualified!' : ` • ${daysRemaining} days remaining`}
              </div>
              {!metrics.isQualified && (
                <div className="mt-2 w-full bg-slate-900 rounded-full h-2">
                  <div
                    className="bg-amber-500 h-2 rounded-full transition-all"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Primary Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Total Signals</div>
            <div className="text-lg font-bold text-white">{metrics.totalSignals}</div>
          </div>
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Signal Accuracy</div>
            <div className={`text-lg font-bold ${metrics.signalAccuracy >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
              {metrics.signalAccuracy.toFixed(1)}%
            </div>
          </div>
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Paper P&L</div>
            <div className={`text-lg font-bold ${metrics.paperPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              ${metrics.paperPnl.toFixed(2)}
            </div>
          </div>
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Real P&L</div>
            <div className={`text-lg font-bold ${metrics.realPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              ${metrics.realPnl.toFixed(2)}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">P&L Delta</div>
            <div className={`text-sm font-bold ${metrics.pnlDelta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              ${metrics.pnlDelta.toFixed(2)}
            </div>
          </div>
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Avg Latency</div>
            <div className="text-sm font-bold text-slate-200">{metrics.avgLatencyMs.toFixed(0)}ms</div>
          </div>
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Model Drift</div>
            <div className={`text-sm font-bold ${metrics.modelDrift < 10 ? 'text-emerald-400' : metrics.modelDrift < 20 ? 'text-amber-400' : 'text-red-400'}`}>
              {metrics.modelDrift.toFixed(1)}%
            </div>
          </div>
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Missed</div>
            <div className="text-sm font-bold text-amber-400">{metrics.missedSignals}</div>
          </div>
        </div>

        {/* Equity Chart */}
        {dailyMetrics.length > 0 && (
          <div className="mt-4 bg-slate-900 rounded-lg border border-slate-700/50 p-3">
            <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-2">Cumulative Paper P&L</div>
            <EquityChart data={dailyMetrics} />
          </div>
        )}
      </div>

      {/* View Toggle */}
      <div className="flex items-center gap-1 bg-slate-900 rounded-lg p-1 w-fit border border-slate-700">
        <button
          onClick={() => setActiveView('signals')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
            activeView === 'signals' ? 'bg-cyan-500/20 text-cyan-400' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Target className="w-3.5 h-3.5" />
          Signals ({signals.length})
        </button>
        <button
          onClick={() => setActiveView('daily')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
            activeView === 'daily' ? 'bg-cyan-500/20 text-cyan-400' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Calendar className="w-3.5 h-3.5" />
          Daily ({dailyMetrics.length})
        </button>
      </div>

      {/* Signals View */}
      {activeView === 'signals' && (
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
          <div className="flex items-center justify-between flex-wrap gap-3 mb-3">
            <h4 className="text-xs font-semibold text-slate-300">Signal Log</h4>
            <div className="flex items-center gap-2">
              {(['all', 'executed', 'missed', 'pending'] as const).map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-2 py-1 rounded text-[10px] font-medium transition-colors ${
                    filter === f ? 'bg-cyan-500/20 text-cyan-400' : 'bg-slate-900 text-slate-500 hover:text-slate-300'
                  }`}
                >
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-1 max-h-80 overflow-y-auto">
            {filtered.map(signal => (
              <SignalCard key={signal.id} signal={signal} />
            ))}
          </div>
          {filtered.length === 0 && (
            <div className="text-center py-4 text-xs text-slate-500">No signals yet</div>
          )}
        </div>
      )}

      {/* Daily Metrics View */}
      {activeView === 'daily' && (
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
          <h4 className="text-xs font-semibold text-slate-300 mb-3">Daily Performance</h4>
          <div className="overflow-x-auto">
            <div className="grid grid-cols-7 gap-1 text-[9px] text-slate-500 uppercase tracking-wider mb-1">
              <span>Date</span>
              <span className="text-center">Signals</span>
              <span className="text-center">Accuracy</span>
              <span className="text-center">Paper</span>
              <span className="text-center">Real</span>
              <span className="text-center">Latency</span>
              <span className="text-center">Drift</span>
            </div>
            {dailyMetrics.map((m, i) => (
              <DailyMetricRow key={i} metric={m} />
            ))}
          </div>
          {dailyMetrics.length === 0 && (
            <div className="text-center py-4 text-xs text-slate-500">No daily data yet</div>
          )}
        </div>
      )}
    </div>
  );
}
