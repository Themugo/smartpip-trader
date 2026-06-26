import { useState } from 'react';
import {
  FileText, CheckCircle, XCircle, AlertTriangle, ChevronDown, ChevronUp,
  Activity, Brain, ShieldCheck, Hash, TrendingUp, Ban, Scale
} from 'lucide-react';
import type { TradeEvidence } from '../hooks/useTradeEvidence';

interface TradeEvidencePanelProps {
  evidenceLog: TradeEvidence[];
}

function EvidenceCard({ evidence }: { evidence: TradeEvidence }) {
  const [expanded, setExpanded] = useState(false);

  const statusColor = evidence.blocked ? 'text-red-400' : 'text-emerald-400';
  const statusBg = evidence.blocked ? 'bg-red-500/10' : 'bg-emerald-500/10';
  const statusIcon = evidence.blocked ? XCircle : CheckCircle;
  const StatusIcon = statusIcon;

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-750 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg ${statusBg} flex items-center justify-center`}>
            <StatusIcon className={`w-4 h-4 ${statusColor}`} />
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white">{evidence.contractType}</span>
              <span className="text-[10px] text-slate-500 font-mono">{evidence.symbol}</span>
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-slate-400">
                {new Date(evidence.timestamp).toLocaleTimeString()}
              </span>
              <span className={`text-[10px] font-medium ${statusColor}`}>
                {evidence.blocked ? 'BLOCKED' : 'APPROVED'}
              </span>
            </div>
          </div>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-700/50 space-y-3 pt-3">
          {/* Indicators */}
          <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Activity className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">Indicators</span>
            </div>
            <div className="space-y-1">
              {evidence.indicators.map((ind, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-slate-300">{ind.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">{ind.value}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      ind.signal === 'bullish' ? 'bg-emerald-500/10 text-emerald-400' :
                      ind.signal === 'bearish' ? 'bg-red-500/10 text-red-400' :
                      'bg-slate-700 text-slate-400'
                    }`}>{ind.signal}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Analyzers */}
          <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Brain className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">Analyzer Outputs</span>
            </div>
            <div className="space-y-1.5">
              {evidence.analyzers.map((a, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-slate-300">{a.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">{a.prediction}</span>
                    <span className="text-blue-400">{a.confidence}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Risk Checks */}
          <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">Risk Checks</span>
            </div>
            <div className="space-y-1">
              {evidence.riskChecks.map((r, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-slate-300">{r.name}</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      r.passed ? 'bg-emerald-500/10 text-emerald-400' :
                      r.severity === 'critical' ? 'bg-red-500/10 text-red-400' :
                      'bg-amber-500/10 text-amber-400'
                    }`}>{r.passed ? 'PASS' : 'FAIL'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Regime & Sizing */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <TrendingUp className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-[10px] text-slate-400">Regime</span>
              </div>
              <div className="text-xs text-slate-300 capitalize">{evidence.regime.replace('_', ' ')}</div>
            </div>
            <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <Scale className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-[10px] text-slate-400">Amount</span>
              </div>
              <div className="text-xs text-slate-300">${evidence.amount.toFixed(2)}</div>
            </div>
          </div>

          {/* Explanation */}
          <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <FileText className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">Explanation</span>
            </div>
            <pre className="text-[10px] text-slate-400 whitespace-pre-wrap font-mono leading-relaxed">
              {evidence.explanation}
            </pre>
          </div>

          {evidence.blocked && evidence.blockReason && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
              <Ban className="w-4 h-4 text-red-400 shrink-0" />
              <span className="text-xs text-red-400">{evidence.blockReason}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function TradeEvidencePanel({ evidenceLog }: TradeEvidencePanelProps) {
  const [filter, setFilter] = useState<'all' | 'approved' | 'blocked'>('all');

  const filtered = evidenceLog.filter(e => {
    if (filter === 'approved') return !e.blocked;
    if (filter === 'blocked') return e.blocked;
    return true;
  });

  const approvedCount = evidenceLog.filter(e => !e.blocked).length;
  const blockedCount = evidenceLog.filter(e => e.blocked).length;

  return (
    <div className="space-y-4">
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-200">Trade Evidence Log</h3>
          </div>
          <div className="flex items-center gap-2">
            {(['all', 'approved', 'blocked'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2.5 py-1 rounded text-[10px] font-medium transition-colors ${
                  filter === f ? 'bg-blue-500/20 text-blue-400' : 'bg-slate-900 text-slate-500 hover:text-slate-300'
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
                {f === 'approved' && ` (${approvedCount})`}
                {f === 'blocked' && ` (${blockedCount})`}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Total</div>
            <div className="text-lg font-bold text-white">{evidenceLog.length}</div>
          </div>
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Approved</div>
            <div className="text-lg font-bold text-emerald-400">{approvedCount}</div>
          </div>
          <div className="bg-slate-900 rounded-lg p-2.5 text-center">
            <div className="text-[10px] text-slate-400">Blocked</div>
            <div className="text-lg font-bold text-red-400">{blockedCount}</div>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {filtered.map(evidence => (
          <EvidenceCard key={evidence.id} evidence={evidence} />
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-8 text-center">
          <FileText className="w-10 h-10 text-slate-500 mx-auto mb-3" />
          <p className="text-xs text-slate-500">No evidence records yet. Execute trades to generate evidence packages.</p>
        </div>
      )}
    </div>
  );
}
