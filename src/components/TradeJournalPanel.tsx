import { useState } from 'react';
import {
  BookOpen, Target,
  ChevronDown, ChevronUp, Lightbulb, RefreshCw, Sparkles
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
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/30 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2.5 flex items-center justify-between hover:bg-slate-700/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isWin ? 'bg-emerald-500' : 'bg-red-500'}`} />
          <span className="text-xs text-white font-medium">{entry.contractType}</span>
          <span className="text-[10px] text-slate-500 font-mono">{entry.symbol}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold font-mono ${isWin ? 'text-emerald-400' : 'text-red-400'}`}>
            {isWin ? '+' : ''}${(entry.profit || 0).toFixed(2)}
          </span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5 text-slate-400" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
        </div>
      </button>
      {expanded && (
        <div className="px-3 pb-3 border-t border-slate-700/30 space-y-1.5 pt-2">
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Entry</span>
            <span className="text-slate-300 font-mono">${entry.entryPrice.toFixed(4)} / digit {entry.entryDigit}</span>
          </div>
          {entry.exitPrice !== null && (
            <div className="flex justify-between text-[10px]">
              <span className="text-slate-500">Exit</span>
              <span className="text-slate-300 font-mono">${entry.exitPrice.toFixed(4)} / digit {entry.exitDigit}</span>
            </div>
          )}
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Amount</span>
            <span className="text-slate-300 font-mono">${entry.amount.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Confidence</span>
            <span className="text-slate-300">{entry.confidence}%</span>
          </div>
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-500">Regime</span>
            <span className="text-slate-300 capitalize">{entry.regime.replace('_', ' ')}</span>
          </div>
          {entry.notes && (
            <div className="text-[10px] text-slate-400 mt-2 italic">{entry.notes}</div>
          )}
        </div>
      )}
    </div>
  );
}

function InsightCard({ insight }: { insight: WeeklyInsight }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/30 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-700/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
            <Lightbulb className="w-4 h-4 text-white" />
          </div>
          <div className="text-left">
            <span className="text-sm font-semibold text-white">Week of {new Date(insight.weekStart).toLocaleDateString()}</span>
            <p className="text-[10px] text-slate-500">{insight.totalTrades} trades</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold font-mono ${insight.profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400'}`}>
            PF {insight.profitFactor.toFixed(2)}
          </span>
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-700/30 space-y-3 pt-3">
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-slate-900/50 rounded-lg p-2.5 text-center">
              <div className="text-[10px] text-slate-500 uppercase">Trades</div>
              <div className="text-lg font-bold text-white">{insight.totalTrades}</div>
            </div>
            <div className="bg-slate-900/50 rounded-lg p-2.5 text-center">
              <div className="text-[10px] text-slate-500 uppercase">Win Rate</div>
              <div className={`text-lg font-bold ${insight.winRate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>{insight.winRate.toFixed(1)}%</div>
            </div>
            <div className="bg-slate-900/50 rounded-lg p-2.5 text-center">
              <div className="text-[10px] text-slate-500 uppercase">Profit Factor</div>
              <div className={`text-lg font-bold ${insight.profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400'}`}>{insight.profitFactor.toFixed(2)}</div>
            </div>
          </div>

          {insight.bestSetup && (
            <div className="bg-gradient-to-r from-emerald-500/10 to-teal-500/10 rounded-xl p-3 border border-emerald-500/20">
              <div className="text-[10px] text-emerald-400 uppercase tracking-wider mb-1 font-medium">Best Setup</div>
              <div className="text-sm text-white font-semibold">{insight.bestSetup.setup}</div>
              <div className="text-xs text-emerald-300">+${insight.bestSetup.pnl.toFixed(2)} ({insight.bestSetup.trades} trades)</div>
            </div>
          )}

          {insight.worstSetup && (
            <div className="bg-gradient-to-r from-red-500/10 to-rose-500/10 rounded-xl p-3 border border-red-500/20">
              <div className="text-[10px] text-red-400 uppercase tracking-wider mb-1 font-medium">Worst Setup</div>
              <div className="text-sm text-white font-semibold">{insight.worstSetup.setup}</div>
              <div className="text-xs text-red-300">${insight.worstSetup.pnl.toFixed(2)} ({insight.worstSetup.trades} trades)</div>
            </div>
          )}

          {insight.recommendations.length > 0 && (
            <div className="bg-amber-500/10 rounded-xl border border-amber-500/20 p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-[10px] text-amber-400 uppercase tracking-wider font-medium">Recommendations</span>
              </div>
              <ul className="space-y-1">
                {insight.recommendations.map((rec, i) => (
                  <li key={i} className="text-xs text-amber-300 flex items-start gap-2">
                    <span className="text-amber-500 mt-1">•</span>
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
      {/* Header */}
      <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 overflow-hidden">
        <div className="px-4 sm:px-5 py-4 border-b border-slate-800/50 flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-500/20">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Trade Journal</h3>
              <p className="text-[10px] text-slate-500">Performance analysis & insights</p>
            </div>
          </div>

          {onGenerateInsights && (
            <button
              onClick={onGenerateInsights}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 text-amber-400 text-xs font-medium hover:from-amber-500/30 hover:to-orange-500/30 transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Generate Insights
            </button>
          )}
        </div>

        {/* View Toggle */}
        <div className="px-4 sm:px-5 py-3 flex items-center gap-2">
          <button
            onClick={() => setActiveView('insights')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition-all ${
              activeView === 'insights' ? 'bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-400 border border-amber-500/30' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Lightbulb className="w-3.5 h-3.5" />
            Insights
          </button>
          <button
            onClick={() => setActiveView('entries')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition-all ${
              activeView === 'entries' ? 'bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-400 border border-amber-500/30' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Target className="w-3.5 h-3.5" />
            Entries ({resolvedEntries.length})
          </button>
        </div>

        {/* Content */}
        <div className="p-4 sm:p-5 pt-0">
          {activeView === 'insights' ? (
            <div className="space-y-3">
              {insights.length > 0 ? (
                insights.map((insight, i) => <InsightCard key={i} insight={insight} />)
              ) : (
                <div className="text-center py-12">
                  <Lightbulb className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                  <p className="text-sm text-slate-400">No weekly insights yet</p>
                  <p className="text-xs text-slate-500 mt-1">Need at least one week of closed trades</p>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {resolvedEntries.length > 0 ? (
                resolvedEntries.map(entry => <EntryCard key={entry.id} entry={entry} />)
              ) : (
                <div className="text-center py-12">
                  <Target className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                  <p className="text-sm text-slate-400">No closed trades yet</p>
                  <p className="text-xs text-slate-500 mt-1">Journal entries appear after trades complete</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
