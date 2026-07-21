import { TrendingUp, TrendingDown, Target, Wallet, Percent, ArrowUpRight, ArrowDownRight } from 'lucide-react';
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
      sub: 'Session trades',
      icon: Target,
      color: 'from-blue-500 to-cyan-500',
      textColor: 'text-blue-400',
      bgGlow: 'shadow-blue-500/10',
    },
    {
      label: 'Win Rate',
      value: `${stats.win_rate.toFixed(1)}%`,
      sub: stats.win_rate >= 50 ? 'Above target' : 'Below target',
      icon: Percent,
      color: stats.win_rate >= 50 ? 'from-emerald-500 to-teal-500' : 'from-amber-500 to-orange-500',
      textColor: stats.win_rate >= 50 ? 'text-emerald-400' : 'text-amber-400',
      bgGlow: stats.win_rate >= 50 ? 'shadow-emerald-500/10' : 'shadow-amber-500/10',
    },
    {
      label: 'Session P&L',
      value: `$${stats.session_pnl.toFixed(2)}`,
      sub: stats.session_pnl >= 0 ? 'In profit' : 'In loss',
      icon: stats.session_pnl >= 0 ? TrendingUp : TrendingDown,
      color: stats.session_pnl >= 0 ? 'from-emerald-500 to-teal-500' : 'from-red-500 to-rose-500',
      textColor: stats.session_pnl >= 0 ? 'text-emerald-400' : 'text-red-400',
      bgGlow: stats.session_pnl >= 0 ? 'shadow-emerald-500/10' : 'shadow-red-500/10',
    },
    {
      label: 'Total Profit',
      value: `$${stats.total_profit.toFixed(2)}`,
      sub: 'Cumulative',
      icon: Wallet,
      color: stats.total_profit >= 0 ? 'from-violet-500 to-purple-500' : 'from-red-500 to-rose-500',
      textColor: stats.total_profit >= 0 ? 'text-violet-400' : 'text-red-400',
      bgGlow: stats.total_profit >= 0 ? 'shadow-violet-500/10' : 'shadow-red-500/10',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="group relative bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 p-4 sm:p-5 overflow-hidden transition-all duration-300 hover:border-slate-700/50 hover:bg-slate-900/70"
        >
          {/* Glow effect */}
          <div className={`absolute inset-0 bg-gradient-to-br ${card.color} opacity-0 group-hover:opacity-5 transition-opacity duration-300`} />

          {/* Icon */}
          <div className={`absolute -top-4 -right-4 w-20 h-20 bg-gradient-to-br ${card.color} opacity-10 rounded-full blur-xl group-hover:opacity-20 transition-opacity`} />
          <div className={`absolute top-3 right-3 w-10 h-10 rounded-xl bg-gradient-to-br ${card.color} bg-opacity-10 flex items-center justify-center opacity-50 group-hover:opacity-70 transition-opacity`}>
            <card.icon className="w-5 h-5 text-white" />
          </div>

          {/* Content */}
          <div className="relative">
            <p className="text-xs text-slate-500 font-medium mb-1">{card.label}</p>
            <p className={`text-2xl sm:text-3xl font-bold ${card.textColor} tracking-tight mb-0.5`}>
              {card.value}
              {card.label === 'Session P&L' && (
                <span className="ml-1.5">
                  {stats.session_pnl >= 0 ? (
                    <ArrowUpRight className="w-4 h-4 inline text-emerald-400" />
                  ) : (
                    <ArrowDownRight className="w-4 h-4 inline text-red-400" />
                  )}
                </span>
              )}
            </p>
            <p className="text-[10px] text-slate-600">{card.sub}</p>
          </div>

          {/* Bottom accent line */}
          <div className={`absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r ${card.color} opacity-50`} />
        </div>
      ))}
    </div>
  );
}
