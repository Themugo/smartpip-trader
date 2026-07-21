import { TrendingUp, TrendingDown, BarChart3 } from 'lucide-react';
import { useMemo } from 'react';
import type { Trade } from '../lib/supabase';

interface PnLChartProps {
  trades: Trade[];
}

export function PnLChart({ trades }: PnLChartProps) {
  const data = useMemo(() => {
    if (!trades.length) return [];
    let cumulative = 0;
    return trades.map((t) => {
      cumulative += t.profit ?? 0;
      return cumulative;
    });
  }, [trades]);

  if (!trades.length) {
    return (
      <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 p-8 text-center">
        <div className="w-14 h-14 rounded-xl bg-slate-800/50 border border-slate-700/50 flex items-center justify-center mx-auto mb-3">
          <BarChart3 className="w-7 h-7 text-slate-500" />
        </div>
        <p className="text-slate-400 text-sm font-medium">No P&L data yet</p>
        <p className="text-slate-500 text-xs mt-1">Chart will populate with trades</p>
      </div>
    );
  }

  const maxVal = Math.max(...data, 0);
  const minVal = Math.min(...data, 0);
  const range = maxVal - minVal || 1;

  const getPoints = () => {
    if (data.length === 0) return '';
    const width = 100;
    const height = 100;
    const points = data.map((val, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((val - minVal) / range) * height;
      return `${x},${y}`;
    });
    return points.join(' ');
  };

  const current = data[data.length - 1] || 0;
  const isPositive = current >= 0;

  return (
    <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 overflow-hidden">
      {/* Header */}
      <div className="px-4 sm:px-5 py-4 border-b border-slate-800/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-lg ${
            isPositive
              ? 'bg-gradient-to-br from-emerald-500 to-teal-500 shadow-emerald-500/20'
              : 'bg-gradient-to-br from-red-500 to-rose-500 shadow-red-500/20'
          }`}>
            {isPositive ? <TrendingUp className="w-5 h-5 text-white" /> : <TrendingDown className="w-5 h-5 text-white" />}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Cumulative P&L</h3>
            <p className="text-[10px] text-slate-500">{trades.length} trades</p>
          </div>
        </div>
        <div className="text-right">
          <div className={`text-xl font-bold font-mono ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
            {isPositive ? '+' : ''}${current.toFixed(2)}
          </div>
          <div className="text-[10px] text-slate-500">
            Peak: +${Math.max(...data).toFixed(2)}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="p-4 sm:p-5">
        <div className="h-40 sm:h-48 relative bg-slate-800/30 rounded-xl overflow-hidden">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
            <defs>
              <linearGradient id="pnlGradientUp" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="rgba(16, 185, 129, 0.4)" />
                <stop offset="100%" stopColor="rgba(16, 185, 129, 0)" />
              </linearGradient>
              <linearGradient id="pnlGradientDown" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="rgba(239, 68, 68, 0.4)" />
                <stop offset="100%" stopColor="rgba(239, 68, 68, 0)" />
              </linearGradient>
            </defs>
            <polygon
              points={`0,100 ${getPoints()} 100,100`}
              fill={isPositive ? 'url(#pnlGradientUp)' : 'url(#pnlGradientDown)'}
            />
            <polyline
              points={getPoints()}
              fill="none"
              stroke={isPositive ? '#10b981' : '#ef4444'}
              strokeWidth="0.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>

          {/* Zero line */}
          {minVal < 0 && maxVal > 0 && (
            <div
              className="absolute left-0 right-0 border-t border-slate-700/50 border-dashed"
              style={{ top: `${((maxVal) / range) * 100}%` }}
            />
          )}
        </div>

        {/* Stats */}
        <div className="flex justify-between mt-3 text-xs">
          <div className="text-slate-500">
            <span className="text-emerald-400 font-medium">Best:</span> +${Math.max(...data).toFixed(2)}
          </div>
          <div className="text-slate-500">
            <span className="text-red-400 font-medium">Worst:</span> ${Math.min(...data).toFixed(2)}
          </div>
        </div>
      </div>
    </div>
  );
}
