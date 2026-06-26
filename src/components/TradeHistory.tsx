import { ArrowUpRight, ArrowDownRight, Clock, ChevronDown, ChevronUp, Filter } from 'lucide-react';
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

  if (!trades.length) {
    return (
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 sm:p-8 text-center">
        <Clock className="w-8 h-8 text-slate-500 mx-auto mb-3" />
        <p className="text-slate-400 text-sm">No trades recorded yet</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      <div className="px-3 sm:px-4 py-3 border-b border-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-200">Recent Trades</h3>
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <div className="flex gap-1">
            {(['all', 'win', 'loss', 'open'] as FilterType[]).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2 py-0.5 rounded text-[10px] sm:text-xs font-medium transition-colors ${
                  filter === f
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'bg-slate-900 text-slate-500 hover:text-slate-300'
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
          <span className="text-[10px] sm:text-xs text-slate-500 ml-1">{filtered.length}</span>
        </div>
      </div>

      {/* Desktop Table */}
      <div className="hidden sm:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 border-b border-slate-700">
              <th className="px-4 py-2">Market</th>
              <th className="px-4 py-2">Type</th>
              <th className="px-4 py-2">Direction</th>
              <th className="px-4 py-2">Amount</th>
              <th className="px-4 py-2">Confidence</th>
              <th className="px-4 py-2">Entry</th>
              <th className="px-4 py-2">Profit</th>
              <th className="px-4 py-2">Time</th>
            </tr>
          </thead>
          <tbody>
            {displayTrades.map((trade) => (
              <tr key={trade.id} className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                <td className="px-4 py-2.5 text-slate-300 font-mono text-xs">{trade.market}</td>
                <td className="px-4 py-2.5 text-slate-300 text-xs">{trade.type}</td>
                <td className="px-4 py-2.5">
                  <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
                    trade.direction === 'CALL' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                  }`}>
                    {trade.direction === 'CALL' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                    {trade.direction}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-slate-300">${trade.amount.toFixed(2)}</td>
                <td className="px-4 py-2.5 text-slate-300">{trade.confidence.toFixed(0)}%</td>
                <td className="px-4 py-2.5 text-slate-300 font-mono text-xs">{trade.entry_price.toFixed(4)}</td>
                <td className="px-4 py-2.5">
                  {trade.profit !== null && trade.profit !== undefined ? (
                    <span className={`font-medium ${trade.profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {trade.profit >= 0 ? '+' : ''}${trade.profit.toFixed(2)}
                    </span>
                  ) : (
                    <span className="text-slate-500">-</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-slate-500 text-xs">
                  {new Date(trade.entry_time).toLocaleTimeString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Cards */}
      <div className="sm:hidden divide-y divide-slate-700/50">
        {displayTrades.map((trade) => (
          <div key={trade.id} className="px-3 py-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-slate-300">{trade.market}</span>
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                  trade.direction === 'CALL' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                }`}>
                  {trade.direction}
                </span>
              </div>
              <span className="text-[10px] text-slate-500">
                {new Date(trade.entry_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">${trade.amount.toFixed(2)} @ {trade.entry_price.toFixed(4)}</span>
              {trade.profit !== null ? (
                <span className={`font-medium ${trade.profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {trade.profit >= 0 ? '+' : ''}${trade.profit.toFixed(2)}
                </span>
              ) : (
                <span className="text-slate-500">Open</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {filtered.length > 5 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-center gap-1 py-2.5 text-xs text-slate-400 hover:text-slate-300 hover:bg-slate-700/30 transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-3.5 h-3.5" />
              Show Less
            </>
          ) : (
            <>
              <ChevronDown className="w-3.5 h-3.5" />
              Show {filtered.length - 5} More
            </>
          )}
        </button>
      )}
    </div>
  );
}
