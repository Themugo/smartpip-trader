import { useState } from 'react';
import {
  Brain, CheckCircle, XCircle, AlertTriangle, ShieldCheck, ShieldAlert,
  ChevronDown, ChevronUp, BarChart3, TrendingUp, TrendingDown, Activity,
  Lock, Unlock, Target, Clock
} from 'lucide-react';
import type { MLAuditState, BiasCheck, CVFold, RollingWindow } from '../hooks/useMLAudit';

interface MLAuditPanelProps {
  auditState: MLAuditState;
  onRunAudit: () => void;
}

function ScoreRing({ score, size = 64 }: { score: number; size?: number }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 70 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444';

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="#1e293b" strokeWidth="4" fill="none" />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          stroke={color} strokeWidth="4" fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-sm font-bold" style={{ color }}>{score}</span>
      </div>
    </div>
  );
}

function BiasCheckCard({ check }: { check: BiasCheck }) {
  const [expanded, setExpanded] = useState(false);

  const severityColor = check.severity === 'critical' ? 'text-red-400' :
    check.severity === 'warning' ? 'text-amber-400' : 'text-blue-400';
  const severityBg = check.severity === 'critical' ? 'bg-red-500/10' :
    check.severity === 'warning' ? 'bg-amber-500/10' : 'bg-blue-500/10';

  return (
    <div className={`rounded-lg border overflow-hidden ${
      check.passed ? 'border-emerald-500/10 bg-emerald-500/5' : 'border-slate-700 bg-slate-900'
    }`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2.5 flex items-center justify-between hover:bg-slate-800/50 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          {check.passed ? (
            <CheckCircle className="w-4 h-4 text-emerald-400" />
          ) : check.severity === 'critical' ? (
            <XCircle className="w-4 h-4 text-red-400" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          )}
          <div className="text-left">
            <span className="text-xs text-slate-300 font-medium">{check.name}</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className={`text-[9px] px-1 py-0.5 rounded ${severityBg} ${severityColor}`}>{check.severity}</span>
              <span className="text-[10px] text-slate-500">Score: {check.score}/100</span>
            </div>
          </div>
        </div>
        <ScoreRing score={check.score} size={40} />
      </button>
      {expanded && (
        <div className="px-3 pb-3 border-t border-slate-700/30 space-y-2 pt-2">
          <p className="text-[10px] text-slate-400">{check.description}</p>
          <div className="bg-slate-950 rounded p-2">
            <div className="text-[9px] text-slate-500 uppercase tracking-wider mb-1">Test Method</div>
            <p className="text-[10px] text-slate-400 font-mono">{check.testMethod}</p>
          </div>
          <div className="bg-slate-950 rounded p-2">
            <div className="text-[9px] text-slate-500 uppercase tracking-wider mb-1">Details</div>
            <p className="text-[10px] text-slate-400">{check.details}</p>
          </div>
          {!check.passed && (
            <div className="bg-amber-500/5 rounded p-2 border border-amber-500/10">
              <div className="text-[9px] text-amber-400 uppercase tracking-wider mb-1">Recommendation</div>
              <p className="text-[10px] text-amber-300">{check.recommendation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CVFoldCard({ fold }: { fold: CVFold }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700/50 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-slate-800 transition-colors"
      >
        <div className="flex items-center gap-2">
          <BarChart3 className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-xs text-slate-300">Fold {fold.fold}</span>
          <span className="text-[10px] text-slate-500">Train [{fold.trainStart}-{fold.trainEnd}] → Test [{fold.testStart}-{fold.testEnd}]</span>
          {fold.embargoSize > 0 && (
            <span className="text-[9px] text-amber-400 bg-amber-500/10 px-1 py-0.5 rounded">Embargo: {fold.embargoSize}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium ${fold.profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400'}`}>
            PF {fold.profitFactor.toFixed(2)}
          </span>
          {expanded ? <ChevronUp className="w-3 h-3 text-slate-400" /> : <ChevronDown className="w-3 h-3 text-slate-400" />}
        </div>
      </button>
      {expanded && (
        <div className="px-3 pb-3 grid grid-cols-3 sm:grid-cols-6 gap-2">
          <div className="text-center p-2 bg-slate-800 rounded">
            <div className="text-[10px] text-slate-400">Trades</div>
            <div className="text-sm font-bold text-slate-200">{fold.trades}</div>
          </div>
          <div className="text-center p-2 bg-slate-800 rounded">
            <div className="text-[10px] text-slate-400">Win Rate</div>
            <div className={`text-sm font-bold ${fold.winRate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>{fold.winRate.toFixed(1)}%</div>
          </div>
          <div className="text-center p-2 bg-slate-800 rounded">
            <div className="text-[10px] text-slate-400">PF</div>
            <div className={`text-sm font-bold ${fold.profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400'}`}>{fold.profitFactor.toFixed(2)}</div>
          </div>
          <div className="text-center p-2 bg-slate-800 rounded">
            <div className="text-[10px] text-slate-400">Sharpe</div>
            <div className="text-sm font-bold text-slate-200">{fold.sharpe.toFixed(2)}</div>
          </div>
          <div className="text-center p-2 bg-slate-800 rounded">
            <div className="text-[10px] text-slate-400">Max DD</div>
            <div className="text-sm font-bold text-red-400">${fold.maxDrawdown.toFixed(2)}</div>
          </div>
          <div className="text-center p-2 bg-slate-800 rounded">
            <div className="text-[10px] text-slate-400">Skew</div>
            <div className="text-sm font-bold text-slate-200">{fold.skewness.toFixed(2)}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function RollingWindowCard({ window }: { window: RollingWindow }) {
  const degraded = window.degradation > 30;

  return (
    <div className={`bg-slate-900 rounded-lg border p-2.5 ${
      degraded ? 'border-red-500/30' : 'border-slate-700/50'
    }`}>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-slate-300">Window {window.windowIndex}</span>
        <span className={`text-[10px] font-medium ${degraded ? 'text-red-400' : 'text-emerald-400'}`}>
          {window.degradation.toFixed(1)}% degradation
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-[10px]">
        <div>
          <span className="text-slate-500">IS PF:</span>{' '}
          <span className="text-slate-300">{window.inSamplePF.toFixed(2)}</span>
        </div>
        <div>
          <span className="text-slate-500">OOS PF:</span>{' '}
          <span className={window.outOfSamplePF >= 1 ? 'text-emerald-400' : 'text-red-400'}>{window.outOfSamplePF.toFixed(2)}</span>
        </div>
        <div>
          <span className="text-slate-500">IS WR:</span>{' '}
          <span className="text-slate-300">{window.inSampleWR.toFixed(1)}%</span>
        </div>
        <div>
          <span className="text-slate-500">OOS WR:</span>{' '}
          <span className={window.outOfSampleWR >= 50 ? 'text-emerald-400' : 'text-red-400'}>{window.outOfSampleWR.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}

export function MLAuditPanel({ auditState, onRunAudit }: MLAuditPanelProps) {
  const [activeSection, setActiveSection] = useState<'bias' | 'cv' | 'holdout' | 'rolling'>('bias');

  const { checks, cvFolds, holdoutResult, rollingWindows, isAuditing, lastAuditTime, deployable, degradationDetected, overallScore } = auditState;

  const hasRun = checks.length > 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-violet-400" />
            <h3 className="text-sm font-semibold text-slate-200">ML Overfitting Audit</h3>
            <span className="text-[10px] text-slate-500 bg-slate-900 px-1.5 py-0.5 rounded">v2.0</span>
          </div>
          <button
            onClick={onRunAudit}
            disabled={isAuditing}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-violet-500 hover:bg-violet-600 text-white text-xs font-medium disabled:bg-slate-700 disabled:text-slate-500"
          >
            {isAuditing ? (
              <>
                <Activity className="w-3.5 h-3.5 animate-spin" />
                Auditing...
              </>
            ) : (
              <>
                <Target className="w-3.5 h-3.5" />
                Run Full Audit
              </>
            )}
          </button>
        </div>

        {lastAuditTime && (
          <div className="text-[10px] text-slate-500 mb-3">
            Last audit: {new Date(lastAuditTime).toLocaleString()}
          </div>
        )}

        {hasRun && (
          <div className="flex items-center gap-4 mb-4">
            <ScoreRing score={overallScore} size={72} />
            <div className="flex-1">
              <div className="text-xs text-slate-400 mb-1">Overall Audit Score</div>
              <div className={`text-lg font-bold ${overallScore >= 70 ? 'text-emerald-400' : overallScore >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                {overallScore}/100
              </div>
              <div className="text-[10px] text-slate-500">
                {checks.filter(c => c.passed).length}/{checks.length} checks passed
              </div>
            </div>
          </div>
        )}

        {/* Deployment Gate */}
        {hasRun && (
          <div className={`p-3 rounded-lg border ${
            deployable
              ? 'bg-emerald-500/10 border-emerald-500/20'
              : 'bg-red-500/10 border-red-500/20'
          }`}>
            <div className="flex items-center gap-2">
              {deployable ? (
                <Unlock className="w-5 h-5 text-emerald-400" />
              ) : (
                <Lock className="w-5 h-5 text-red-400" />
              )}
              <div>
                <div className={`text-sm font-medium ${deployable ? 'text-emerald-400' : 'text-red-400'}`}>
                  {deployable ? 'DEPLOYMENT ALLOWED' : 'DEPLOYMENT BLOCKED'}
                </div>
                <div className="text-xs text-slate-400">
                  {deployable
                    ? 'All critical checks passed. Holdout positive. No degradation. Rolling windows stable.'
                    : degradationDetected
                    ? 'Model degradation detected in rolling windows or holdout. Retrain required.'
                    : 'Critical bias checks failed. Review audit results.'}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {hasRun && (
        <>
          {/* Section Tabs */}
          <div className="flex items-center gap-1 bg-slate-900 rounded-lg p-1 w-fit border border-slate-700">
            {([
              { key: 'bias', label: 'Bias Checks', icon: Target },
              { key: 'cv', label: 'Cross-Validation', icon: BarChart3 },
              { key: 'holdout', label: 'Holdout', icon: ShieldCheck },
              { key: 'rolling', label: 'Rolling Windows', icon: Clock },
            ] as const).map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveSection(key)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  activeSection === key
                    ? 'bg-violet-500/20 text-violet-400'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
              </button>
            ))}
          </div>

          {/* Bias Checks */}
          {activeSection === 'bias' && (
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5 space-y-2">
              <h4 className="text-xs font-semibold text-slate-300 mb-2">Overfitting Risk Assessment</h4>
              {checks.map((check, i) => (
                <BiasCheckCard key={i} check={check} />
              ))}
            </div>
          )}

          {/* Cross-Validation */}
          {activeSection === 'cv' && (
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5 space-y-2">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-xs font-semibold text-slate-300">Purged Time-Series Cross-Validation</h4>
                <span className="text-[10px] text-slate-500">{cvFolds.length} folds with embargo</span>
              </div>
              {cvFolds.map(fold => (
                <CVFoldCard key={fold.fold} fold={fold} />
              ))}
              {cvFolds.length === 0 && (
                <div className="text-center py-4 text-xs text-slate-500">Insufficient data for CV (need 60+ trades)</div>
              )}
            </div>
          )}

          {/* Holdout */}
          {activeSection === 'holdout' && holdoutResult && (
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-semibold text-slate-300">Holdout Validation</h4>
                <span className="text-[10px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">
                  Embargo: {holdoutResult.embargoPeriod}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-3">
                <div className="bg-slate-900 rounded-lg p-2.5 text-center">
                  <div className="text-[10px] text-slate-400">Trades</div>
                  <div className="text-sm font-bold text-white">{holdoutResult.trades}</div>
                </div>
                <div className="bg-slate-900 rounded-lg p-2.5 text-center">
                  <div className="text-[10px] text-slate-400">Win Rate</div>
                  <div className={`text-sm font-bold ${holdoutResult.winRate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>{holdoutResult.winRate.toFixed(1)}%</div>
                </div>
                <div className="bg-slate-900 rounded-lg p-2.5 text-center">
                  <div className="text-[10px] text-slate-400">Profit Factor</div>
                  <div className={`text-sm font-bold ${holdoutResult.profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400'}`}>{holdoutResult.profitFactor.toFixed(2)}</div>
                </div>
                <div className="bg-slate-900 rounded-lg p-2.5 text-center">
                  <div className="text-[10px] text-slate-400">Sharpe</div>
                  <div className="text-sm font-bold text-slate-200">{holdoutResult.sharpe.toFixed(2)}</div>
                </div>
                <div className="bg-slate-900 rounded-lg p-2.5 text-center">
                  <div className="text-[10px] text-slate-400">Max DD</div>
                  <div className="text-sm font-bold text-red-400">${holdoutResult.maxDrawdown.toFixed(2)}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="bg-slate-900 rounded-lg p-2.5 text-center">
                  <div className="text-[10px] text-slate-400">Avg Return</div>
                  <div className={`text-sm font-bold ${holdoutResult.avgReturn >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>${holdoutResult.avgReturn.toFixed(4)}</div>
                </div>
                <div className="bg-slate-900 rounded-lg p-2.5 text-center">
                  <div className="text-[10px] text-slate-400">Std Dev</div>
                  <div className="text-sm font-bold text-slate-200">${holdoutResult.stdReturn.toFixed(4)}</div>
                </div>
                <div className="bg-slate-900 rounded-lg p-2.5 text-center">
                  <div className="text-[10px] text-slate-400">VaR 95%</div>
                  <div className="text-sm font-bold text-red-400">${holdoutResult.var95.toFixed(4)}</div>
                </div>
                <div className="bg-slate-900 rounded-lg p-2.5 text-center">
                  <div className="text-[10px] text-slate-400">CVaR 95%</div>
                  <div className="text-sm font-bold text-red-400">${holdoutResult.cvar95.toFixed(4)}</div>
                </div>
              </div>
            </div>
          )}

          {/* Rolling Windows */}
          {activeSection === 'rolling' && (
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-semibold text-slate-300">Rolling Retraining Windows</h4>
                <span className="text-[10px] text-slate-500">{rollingWindows.length} windows</span>
              </div>
              {rollingWindows.length > 0 ? (
                <div className="space-y-2">
                  {rollingWindows.map(w => (
                    <RollingWindowCard key={w.windowIndex} window={w} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-xs text-slate-500">Insufficient data for rolling windows (need 100+ trades)</div>
              )}
            </div>
          )}
        </>
      )}

      {!hasRun && (
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-8 text-center">
          <Brain className="w-10 h-10 text-slate-500 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-slate-300 mb-1">No Audit Data</h3>
          <p className="text-xs text-slate-500">Run the audit to analyze overfitting risks across 7 bias checks, purged CV, holdout validation, and rolling windows.</p>
        </div>
      )}
    </div>
  );
}
