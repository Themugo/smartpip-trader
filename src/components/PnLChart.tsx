import { TrendingUp } from 'lucide-react';
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
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 sm:p-8 text-center">
        <TrendingUp className="w-8 h-8 text-slate-500 mx-auto mb-3" />
        <p className="text-slate-400 text-sm">No P&L data yet</p>
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

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
      <div className="flex items-center justify-between mb-3 sm:mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-400" />
          <h3 className="text-sm font-semibold text-slate-200">P&L Chart</h3>
        </div>
        <span className={`text-sm sm:text-base font-bold ${current >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {current >= 0 ? '+' : ''}${current.toFixed(2)}
        </span>
      </div>

      <div className="h-32 sm:h-40 relative">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
          <defs>
            <linearGradient id="pnlGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(16, 185, 129, 0.3)" />
              <stop offset="100%" stopColor="rgba(16, 185, 129, 0)" />
            </linearGradient>
          </defs>
          <polygon
            points={`0,100 ${getPoints()} 100,100`}
            fill="url(#pnlGradient)"
          />
          <polyline
            points={getPoints()}
            fill="none"
            stroke={current >= 0 ? '#10b981' : '#ef4444'}
            strokeWidth="0.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      <div className="flex justify-between mt-2 text-[10px] sm:text-xs text-slate-500 min-w-0">
        <span className="shrink-0">{trades.length} trades</span>
        <span className="truncate ml-2">
          Best: +${Math.max(...data).toFixed(2)} | Worst: {Math.min(...data).toFixed(2)}
        </span>
      </div>
    </div>
  );
}
