import { useState } from 'react';
import {
  Eye, ChevronDown, ChevronUp, Target, Calendar, Sparkles, Clock
} from 'lucide-react';
import type { ShadowSignal, ShadowMetrics, ShadowDailyMetric } from '../hooks/useShadowMode';

interface ShadowModePanelProps {
  signals: ShadowSignal[];
  metrics: ShadowMetrics;
  dailyMetrics?: ShadowDailyMetric[];
}

function SignalCard({ signal }: { signal: ShadowSignal }) {
  const [expanded, setExpanded] = useState(false);

  const outcomeConfig = {
    win: { color: 'text-emerald-400', bg: 'bg-emerald-500', label: 'WIN' },
    loss: { color: 'text-red-400', bg: 'bg-red-500', label: 'LOSS' },
    missed: { color: 'text-amber-400', bg: 'bg-amber-500', label: 'MISSED' },
    pending: { color: 'text-slate-400', bg: 'bg-slate-500', label: 'PENDING' },
  };

  const outcome = outcomeConfig[signal.actualOutcome || 'pending'];

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/30 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2.5 flex items-center justify-between hover:bg-slate-700/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${outcome.bg}`} />
          <span className="text-xs text-white font-medium">{signal.contractType}</span>
          <span className="text-[10px] text-slate-500 font-mono">{signal.symbol}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold ${outcome.color}`}>{outcome.label}</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5 text-slate-400" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 border-t border-slate-700/30 space-y-1.5 pt-2">
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Predicted</span>
            <span className="text-slate-300">{signal.expectedOutcome} ({signal.confidence}%)</span>
          </div>
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Expected P&L</span>
            <span className="text-slate-300 font-mono">${signal.expectedPnl.toFixed(2)}</span>
          </div>
          {signal.actualPnl !== null && (
            <div className="flex justify-between text-[10px]">
              <span className="text-slate-500">Actual P&L</span>
              <span className={`font-mono font-bold ${signal.actualPnl > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {signal.actualPnl > 0 ? '+' : ''}${signal.actualPnl.toFixed(2)}
              </span>
            </div>
          )}
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Latency</span>
            <span className="text-slate-300 font-mono">{signal.latencyMs}ms</span>
          </div>
        </div>
      )}
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
    <div className="h-24 relative bg-slate-900/50 rounded-lg overflow-hidden">
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
      {/* Qualification Status */}
      <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 overflow-hidden">
        <div className="px-4 sm:px-5 py-4 border-b border-slate-800/50 flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-lg ${
            metrics.isQualified
              ? 'bg-gradient-to-br from-emerald-500 to-teal-500 shadow-emerald-500/20'
              : 'bg-gradient-to-br from-amber-500 to-orange-500 shadow-amber-500/20'
          }`}>
            <Eye className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Shadow Mode</h3>
            <p className="text-[10px] text-slate-500">Paper trading qualification system</p>
          </div>
          <div className="ml-auto">
            {metrics.isQualified ? (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-xs text-emerald-400 font-bold">QUALIFIED</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20">
                <Clock className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-xs text-amber-400 font-bold">{daysRemaining} DAYS LEFT</span>
              </div>
            )}
          </div>
        </div>

        <div className="p-4 sm:p-5 space-y-4">
          {/* Progress Bar */}
          {!metrics.isQualified && (
            <div className="bg-slate-800/50 rounded-xl p-3">
              <div className="flex items-center justify-between text-xs mb-2">
                <span className="text-slate-400">Qualification Progress</span>
                <span className="text-slate-300 font-mono">{metrics.daysInShadow}/30 days</span>
              </div>
              <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full transition-all"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
          )}

          {/* Stats Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/30 p-3 text-center">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">Total Signals</div>
              <div className="text-xl font-bold text-white font-mono">{metrics.totalSignals}</div>
            </div>
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/30 p-3 text-center">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">Accuracy</div>
              <div className={`text-xl font-bold font-mono ${metrics.signalAccuracy >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
                {metrics.signalAccuracy.toFixed(1)}%
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/30 p-3 text-center">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">Paper P&L</div>
              <div className={`text-xl font-bold font-mono ${metrics.paperPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                ${metrics.paperPnl.toFixed(2)}
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/30 p-3 text-center">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">Real P&L</div>
              <div className={`text-xl font-bold font-mono ${metrics.realPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                ${metrics.realPnl.toFixed(2)}
              </div>
            </div>
          </div>

          {/* Equity Chart */}
          {dailyMetrics.length > 0 && (
            <div className="bg-slate-800/30 rounded-xl border border-slate-700/30 p-3">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Cumulative Paper P&L</div>
              <EquityChart data={dailyMetrics} />
            </div>
          )}
        </div>
      </div>

      {/* View Toggle */}
      <div className="flex items-center gap-1 bg-slate-900/50 rounded-xl p-1 w-fit border border-slate-800/50">
        <button
          onClick={() => setActiveView('signals')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
            activeView === 'signals' ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-400 border border-cyan-500/30' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Target className="w-3.5 h-3.5" />
          Signals ({signals.length})
        </button>
        <button
          onClick={() => setActiveView('daily')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
            activeView === 'daily' ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-400 border border-cyan-500/30' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Calendar className="w-3.5 h-3.5" />
          Daily ({dailyMetrics.length})
        </button>
      </div>

      {/* Signals View */}
      {activeView === 'signals' && (
        <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 p-4 sm:p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-white">Signal Log</span>
            <div className="flex items-center gap-1">
              {(['all', 'executed', 'missed', 'pending'] as const).map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all ${
                    filter === f ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' : 'bg-slate-800/50 text-slate-500 hover:text-slate-300 border border-transparent'
                  }`}
                >
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {filtered.length > 0 ? (
              filtered.map(signal => <SignalCard key={signal.id} signal={signal} />)
            ) : (
              <div className="text-center py-8 text-xs text-slate-500">No signals recorded yet</div>
            )}
          </div>
        </div>
      )}

      {/* Daily Metrics View */}
      {activeView === 'daily' && (
        <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 p-4 sm:p-5">
          <span className="text-xs font-semibold text-white">Daily Performance</span>
          <div className="mt-3 space-y-2">
            {dailyMetrics.length > 0 ? (
              dailyMetrics.map((m, i) => (
                <div key={i} className="grid grid-cols-4 sm:grid-cols-7 gap-2 p-2.5 rounded-lg bg-slate-800/30 text-[10px]">
                  <span className="text-slate-400 col-span-1">{m.date}</span>
                  <span className="text-slate-300 text-center">{m.totalSignals}</span>
                  <span className={`text-center font-bold ${m.signalAccuracy >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>{m.signalAccuracy.toFixed(0)}%</span>
                  <span className={`text-center font-bold font-mono ${m.paperPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>${m.paperPnl.toFixed(2)}</span>
                  <span className={`text-center font-bold font-mono ${m.realPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>${m.realPnl.toFixed(2)}</span>
                  <span className="text-slate-400 text-center font-mono hidden sm:block">{m.avgLatencyMs.toFixed(0)}ms</span>
                  <span className={`text-center font-bold hidden sm:block ${m.modelDrift < 10 ? 'text-emerald-400' : m.modelDrift < 20 ? 'text-amber-400' : 'text-red-400'}`}>{m.modelDrift.toFixed(1)}%</span>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-xs text-slate-500">No daily data yet</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
