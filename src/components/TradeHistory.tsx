import { ArrowUpRight, ArrowDownRight, Clock, ChevronDown, ChevronUp, TrendingUp } from 'lucide-react';
import { useState } from 'react';
import type { Trade } from '../lib/supabase';

interface TradeHistoryProps {
  trades: Trade[];
}

type FilterType = 'all' | 'win' | 'loss' | 'open';

export function TradeHistory({ trades }: TradeHistoryProps) {
  const [filter, setFilter] = useState<FilterType>('all');
  const [expanded, setExpanded] = useState(false);

  const filtered = trades.filter((t) => {
    if (filter === 'win') return t.profit !== null && t.profit > 0;
    if (filter === 'loss') return t.profit !== null && t.profit < 0;
    if (filter === 'open') return t.profit === null;
    return true;
  });

  const displayTrades = expanded ? filtered : filtered.slice(0, 5);

  const stats = {
    wins: trades.filter(t => t.profit !== null && t.profit > 0).length,
    losses: trades.filter(t => t.profit !== null && t.profit < 0).length,
    open: trades.filter(t => t.profit === null).length,
  };

  if (!trades.length) {
    return (
      <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 p-8 text-center">
        <div className="w-16 h-16 rounded-2xl bg-slate-800/50 border border-slate-700/50 flex items-center justify-center mx-auto mb-4">
          <Clock className="w-7 h-7 text-slate-500" />
        </div>
        <p className="text-slate-400 text-sm font-medium">No trades recorded yet</p>
        <p className="text-slate-500 text-xs mt-1">Trades will appear here once executed</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 overflow-hidden">
      {/* Header */}
      <div className="px-4 sm:px-5 py-4 border-b border-slate-800/50">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center shadow-lg shadow-violet-500/20">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Recent Trades</h3>
              <p className="text-[10px] text-slate-500">{trades.length} total trades</p>
            </div>
          </div>

          {/* Mini Stats */}
          <div className="flex items-center gap-3">
            {stats.wins > 0 && (
              <div className="text-center">
                <p className="text-sm font-bold text-emerald-400">{stats.wins}</p>
                <p className="text-[8px] text-slate-500 uppercase">Wins</p>
              </div>
            )}
            {stats.losses > 0 && (
              <div className="text-center">
                <p className="text-sm font-bold text-red-400">{stats.losses}</p>
                <p className="text-[8px] text-slate-500 uppercase">Losses</p>
              </div>
            )}
            {stats.open > 0 && (
              <div className="text-center">
                <p className="text-sm font-bold text-blue-400">{stats.open}</p>
                <p className="text-[8px] text-slate-500 uppercase">Open</p>
              </div>
            )}
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-1">
          {(['all', 'win', 'loss', 'open'] as FilterType[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                filter === f
                  ? 'bg-violet-500/20 text-violet-400 border border-violet-500/30'
                  : 'bg-slate-800/50 text-slate-500 border border-transparent hover:text-slate-300'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
              <span className="ml-1.5 opacity-60">
                {f === 'all' ? trades.length : f === 'win' ? stats.wins : f === 'loss' ? stats.losses : stats.open}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Desktop Table */}
      <div className="hidden sm:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[10px] text-slate-500 uppercase tracking-wider border-b border-slate-800/50">
              <th className="px-4 py-3 font-medium">Market</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Direction</th>
              <th className="px-4 py-3 font-medium text-right">Amount</th>
              <th className="px-4 py-3 font-medium text-right">Conf.</th>
              <th className="px-4 py-3 font-medium text-right">Entry</th>
              <th className="px-4 py-3 font-medium text-right">P/L</th>
              <th className="px-4 py-3 font-medium">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {displayTrades.map((trade) => (
              <tr key={trade.id} className="hover:bg-slate-800/30 transition-colors group">
                <td className="px-4 py-3">
                  <span className="font-mono text-xs text-slate-300 font-medium">{trade.market}</span>
                </td>
                <td className="px-4 py-3 text-xs text-slate-400">{trade.type}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-lg ${
                    trade.direction === 'CALL'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-red-500/10 text-red-400 border border-red-500/20'
                  }`}>
                    {trade.direction === 'CALL' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                    {trade.direction}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-mono text-xs text-slate-300">${trade.amount.toFixed(2)}</td>
                <td className="px-4 py-3 text-right">
                  <span className={`text-xs font-medium ${
                    trade.confidence >= 70 ? 'text-emerald-400' : trade.confidence >= 50 ? 'text-amber-400' : 'text-slate-400'
                  }`}>
                    {trade.confidence.toFixed(0)}%
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-mono text-xs text-slate-400">{trade.entry_price.toFixed(4)}</td>
                <td className="px-4 py-3 text-right">
                  {trade.profit !== null && trade.profit !== undefined ? (
                    <span className={`font-bold ${trade.profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {trade.profit >= 0 ? '+' : ''}${trade.profit.toFixed(2)}
                    </span>
                  ) : (
                    <span className="text-xs text-blue-400 font-medium">Open</span>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-500 text-xs">
                  {new Date(trade.entry_time).toLocaleTimeString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Cards */}
      <div className="sm:hidden divide-y divide-slate-800/50">
        {displayTrades.map((trade) => (
          <div key={trade.id} className="px-4 py-4 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-white font-medium">{trade.market}</span>
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-lg ${
                  trade.direction === 'CALL'
                    ? 'bg-emerald-500/10 text-emerald-400'
                    : 'bg-red-500/10 text-red-400'
                }`}>
                  {trade.direction}
                </span>
              </div>
              <span className="text-[10px] text-slate-500">
                {new Date(trade.entry_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">
                ${trade.amount.toFixed(2)} @ {trade.entry_price.toFixed(4)}
              </span>
              {trade.profit !== null ? (
                <span className={`text-sm font-bold ${trade.profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {trade.profit >= 0 ? '+' : ''}${trade.profit.toFixed(2)}
                </span>
              ) : (
                <span className="text-xs text-blue-400 font-medium">Open</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Show More/Less */}
      {filtered.length > 5 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-center gap-2 py-3 text-xs text-slate-400 hover:text-slate-300 hover:bg-slate-800/30 transition-colors border-t border-slate-800/50"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-4 h-4" />
              Show Less
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              Show {filtered.length - 5} More
            </>
          )}
        </button>
      )}
    </div>
  );
}
