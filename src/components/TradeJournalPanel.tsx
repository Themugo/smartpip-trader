import { useState } from 'react';
import {
  BookOpen, TrendingUp, TrendingDown, Clock, Target, Zap,
  ChevronDown, ChevronUp, Lightbulb, BarChart3, Hash, Activity,
  Calendar, ArrowUpRight, ArrowDownRight, RefreshCw
} from 'lucide-react';
import type { JournalEntry, WeeklyInsight } from '../hooks/useTradeJournal';

interface TradeJournalPanelProps {
  entries: JournalEntry[];
  insights: WeeklyInsight[];
  onGenerateInsights?: () => void;
}

function EntryCard({ entry }: { entry: JournalEntry }) {
  const [expanded, setExpanded] = useState(false);
  const isWin = (entry.profit || 0) > 0;

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-slate-750 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isWin ? 'bg-emerald-500' : 'bg-red-500'}`} />
          <span className="text-xs text-slate-300">{entry.contractType}</span>
          <span className="text-[10px] text-slate-500 font-mono">{entry.symbol}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium ${isWin ? 'text-emerald-400' : 'text-red-400'}`}>
            {isWin ? '+' : ''}${(entry.profit || 0).toFixed(2)}
          </span>
          {expanded ? <ChevronUp className="w-3 h-3 text-slate-400" /> : <ChevronDown className="w-3 h-3 text-slate-400" />}
        </div>
      </button>
      {expanded && (
        <div className="px-3 pb-2 border-t border-slate-700/50 space-y-1 pt-2">
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Entry</span>
            <span className="text-slate-300">${entry.entryPrice.toFixed(4)} / digit {entry.entryDigit}</span>
          </div>
          {entry.exitPrice !== null && (
            <div className="flex justify-between text-[10px]">
              <span className="text-slate-500">Exit</span>
              <span className="text-slate-300">${entry.exitPrice.toFixed(4)} / digit {entry.exitDigit}</span>
            </div>
          )}
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Amount</span>
            <span className="text-slate-300">${entry.amount.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Confidence</span>
            <span className="text-slate-300">{entry.confidence}%</span>
          </div>
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Regime</span>
            <span className="text-slate-300 capitalize">{entry.regime.replace('_', ' ')}</span>
          </div>
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Balance</span>
            <span className="text-slate-300">${entry.runningBalance.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">DD Impact</span>
            <span className="text-red-400">{entry.drawdownImpact.toFixed(2)}%</span>
          </div>
          {entry.entryConditions.length > 0 && (
            <div className="mt-1">
              <span className="text-[9px] text-slate-500 uppercase">Entry Conditions</span>
              <ul className="mt-0.5 space-y-0.5">
                {entry.entryConditions.map((c, i) => (
                  <li key={i} className="text-[10px] text-slate-400 flex items-start gap-1">
                    <span className="text-slate-600 mt-0.5">•</span>{c}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {entry.notes && (
            <div className="text-[10px] text-slate-400 mt-1">{entry.notes}</div>
          )}
        </div>
      )}
    </div>
  );
}

function InsightCard({ insight }: { insight: WeeklyInsight }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-750 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-amber-400" />
          <span className="text-sm font-semibold text-white">
            Week of {new Date(insight.weekStart).toLocaleDateString()}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium ${insight.profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400'}`}>
            PF {insight.profitFactor.toFixed(2)}
          </span>
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-700/50 space-y-3 pt-3">
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-slate-900 rounded-lg p-2 text-center">
              <div className="text-[10px] text-slate-400">Trades</div>
              <div className="text-sm font-bold text-white">{insight.totalTrades}</div>
            </div>
            <div className="bg-slate-900 rounded-lg p-2 text-center">
              <div className="text-[10px] text-slate-400">Win Rate</div>
              <div className={`text-sm font-bold ${insight.winRate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>{insight.winRate.toFixed(1)}%</div>
            </div>
            <div className="bg-slate-900 rounded-lg p-2 text-center">
              <div className="text-[10px] text-slate-400">Profit Factor</div>
              <div className={`text-sm font-bold ${insight.profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400'}`}>{insight.profitFactor.toFixed(2)}</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {insight.bestSetup && (
              <div className="bg-emerald-500/10 rounded-lg p-2.5 border border-emerald-500/20">
                <div className="text-[10px] text-emerald-400 mb-1">Best Setup</div>
                <div className="text-xs text-white font-medium">{insight.bestSetup.setup}</div>
                <div className="text-[10px] text-emerald-300">+${insight.bestSetup.pnl.toFixed(2)} ({insight.bestSetup.trades} trades)</div>
              </div>
            )}
            {insight.worstSetup && (
              <div className="bg-red-500/10 rounded-lg p-2.5 border border-red-500/20">
                <div className="text-[10px] text-red-400 mb-1">Worst Setup</div>
                <div className="text-xs text-white font-medium">{insight.worstSetup.setup}</div>
                <div className="text-[10px] text-red-300">-${Math.abs(insight.worstSetup.pnl).toFixed(2)} ({insight.worstSetup.trades} trades)</div>
              </div>
            )}
          </div>

          {Object.keys(insight.timeOfDay).length > 0 && (
            <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
              <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-2">Time of Day</div>
              <div className="flex gap-1 flex-wrap">
                {Object.entries(insight.timeOfDay).sort((a, b) => parseInt(a[0]) - parseInt(b[0])).map(([hour, data]) => (
                  <div key={hour} className={`px-2 py-1 rounded text-[10px] ${
                    data.pnl > 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                  }`} title={`WR: ${data.winRate.toFixed(0)}%, PnL: $${data.pnl.toFixed(2)}`}>
                    {hour}:00
                  </div>
                ))}
              </div>
            </div>
          )}

          {Object.keys(insight.regimePerformance).length > 0 && (
            <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
              <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-2">Regime Performance</div>
              <div className="space-y-1">
                {Object.entries(insight.regimePerformance).map(([regime, data]) => (
                  <div key={regime} className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 capitalize">{regime.replace('_', ' ')}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500">{data.trades} trades</span>
                      <span className={`${data.pnl > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {data.pnl > 0 ? '+' : ''}${data.pnl.toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {insight.recommendations.length > 0 && (
            <div className="bg-amber-500/10 rounded-lg border border-amber-500/20 p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-[10px] text-amber-400 uppercase tracking-wider">Recommendations</span>
              </div>
              <ul className="space-y-1">
                {insight.recommendations.map((rec, i) => (
                  <li key={i} className="text-xs text-amber-300 flex items-start gap-1.5">
                    <span className="text-amber-500 mt-0.5">•</span>
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function TradeJournalPanel({ entries, insights, onGenerateInsights }: TradeJournalPanelProps) {
  const [activeView, setActiveView] = useState<'entries' | 'insights'>('insights');

  const resolvedEntries = entries.filter(e => e.profit !== null);

  return (
    <div className="space-y-4">
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-amber-400" />
            <h3 className="text-sm font-semibold text-slate-200">Trade Journal</h3>
          </div>
          <div className="flex items-center gap-2">
            {onGenerateInsights && (
              <button
                onClick={onGenerateInsights}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-amber-500/20 text-amber-400 text-xs font-medium hover:bg-amber-500/30 transition-colors"
              >
                <RefreshCw className="w-3 h-3" />
                Generate Insights
              </button>
            )}
            <div className="flex items-center gap-1 bg-slate-900 rounded-lg p-1">
              <button
                onClick={() => setActiveView('insights')}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  activeView === 'insights' ? 'bg-amber-500/20 text-amber-400' : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                Insights
              </button>
              <button
                onClick={() => setActiveView('entries')}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  activeView === 'entries' ? 'bg-amber-500/20 text-amber-400' : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                Entries ({resolvedEntries.length})
              </button>
            </div>
          </div>
        </div>

        {activeView === 'insights' ? (
          <div className="space-y-2">
            {insights.length > 0 ? (
              insights.map((insight, i) => (
                <InsightCard key={i} insight={insight} />
              ))
            ) : (
              <div className="text-center py-8 text-xs text-slate-500">
                Not enough closed trades for weekly insights. Need at least one week of data.
                {onGenerateInsights && (
                  <button
                    onClick={onGenerateInsights}
                    className="block mx-auto mt-3 px-3 py-1.5 rounded-lg bg-amber-500/20 text-amber-400 text-xs"
                  >
                    Generate Now
                  </button>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-1 max-h-96 overflow-y-auto">
            {resolvedEntries.map(entry => (
              <EntryCard key={entry.id} entry={entry} />
            ))}
            {resolvedEntries.length === 0 && (
              <div className="text-center py-8 text-xs text-slate-500">No closed trades yet</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
