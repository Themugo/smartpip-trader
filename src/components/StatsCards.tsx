import { TrendingUp, TrendingDown, Target, Zap, Wallet, Percent } from 'lucide-react';
import type { TradeStatistics } from '../lib/supabase';

interface StatsCardsProps {
  stats: TradeStatistics | null;
}

export function StatsCards({ stats }: StatsCardsProps) {
  if (!stats) return null;

  const cards = [
    {
      label: 'Total Trades',
      value: stats.total_trades,
      icon: Target,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
    },
    {
      label: 'Win Rate',
      value: `${stats.win_rate.toFixed(1)}%`,
      icon: Percent,
      color: stats.win_rate >= 50 ? 'text-emerald-400' : 'text-amber-400',
      bg: stats.win_rate >= 50 ? 'bg-emerald-500/10' : 'bg-amber-500/10',
    },
    {
      label: 'Session P&L',
      value: `$${stats.session_pnl.toFixed(2)}`,
      icon: stats.session_pnl >= 0 ? TrendingUp : TrendingDown,
      color: stats.session_pnl >= 0 ? 'text-emerald-400' : 'text-red-400',
      bg: stats.session_pnl >= 0 ? 'bg-emerald-500/10' : 'bg-red-500/10',
    },
    {
      label: 'Total Profit',
      value: `$${stats.total_profit.toFixed(2)}`,
      icon: Wallet,
      color: stats.total_profit >= 0 ? 'text-emerald-400' : 'text-red-400',
      bg: stats.total_profit >= 0 ? 'bg-emerald-500/10' : 'bg-red-500/10',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      {cards.map((card) => (
        <div key={card.label} className="bg-slate-800 rounded-xl border border-slate-700 p-3 sm:p-4">
          <div className="flex items-center justify-between mb-1.5 sm:mb-2">
            <span className="text-xs sm:text-sm text-slate-400">{card.label}</span>
            <div className={`w-7 h-7 sm:w-8 sm:h-8 rounded-lg ${card.bg} flex items-center justify-center`}>
              <card.icon className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${card.color}`} />
            </div>
          </div>
          <div className={`text-lg sm:text-2xl font-bold ${card.color}`}>{card.value}</div>
        </div>
      ))}
    </div>
  );
}
