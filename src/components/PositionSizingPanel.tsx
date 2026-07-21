import { useState } from 'react';
import {
  Scale, TrendingUp, TrendingDown, Activity, DollarSign,
  ShieldCheck, AlertTriangle, BarChart3, Play, RotateCcw,
  ChevronDown, ChevronUp, Target
} from 'lucide-react';
import { useAdaptivePositionSizing, type SizingConfig } from '../hooks/useAdaptivePositionSizing';
import { useSizingSimulation, type SimulationResult } from '../hooks/useSizingSimulation';

function StatCard({ label, value, suffix = '', color = 'text-slate-300', icon: Icon }: {
  label: string; value: string | number; suffix?: string; color?: string; icon?: React.ElementType;
}) {
  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/30 p-3 text-center group hover:border-slate-600/50 transition-all">
      {Icon && <Icon className={`w-3.5 h-3.5 ${color} mx-auto mb-1`} />}
      <div className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</div>
      <div className={`text-lg font-bold ${color} font-mono`}>{value}{suffix}</div>
    </div>
  );
}

function EquityChart({ curves }: { curves: number[][] }) {
  if (!curves.length || !curves[0].length) return null;

  const maxVal = Math.max(...curves.flat());
  const minVal = Math.min(...curves.flat());
  const range = maxVal - minVal || 1;

  const colors = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'];

  return (
    <div className="h-32 relative bg-slate-900/50 rounded-lg overflow-hidden">
      <svg viewBox={`0 0 100 ${range > 0 ? 50 : 1}`} preserveAspectRatio="none" className="w-full h-full">
        {curves.map((curve, ci) => {
          const points = curve.map((v, i) => {
            const x = (i / (curve.length - 1)) * 100;
            const y = range > 0 ? ((v - minVal) / range) * 50 : 25;
            return `${x},${y}`;
          }).join(' ');

          return (
            <polyline
              key={ci}
              points={points}
              fill="none"
              stroke={colors[ci % colors.length]}
              strokeWidth="0.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          );
        })}
      </svg>
    </div>
  );
}

export function PositionSizingPanel() {
  const [config, setConfig] = useState<SizingConfig>({
    baseAmount: 1.0,
    maxRiskPerTrade: 0.02,
    maxDailyExposure: 0.2,
    kellyFraction: 0.25,
    volatilityLookback: 50,
    confidenceWeight: 0.5,
    drawdownReductionStart: 5,
    drawdownMax: 20,
    lossStreakReduction: true,
    winStreakBoost: false,
    minTradeSize: 0.35,
    maxTradeSize: 50,
  });

  const [simResults, setSimResults] = useState<{ adaptive: SimulationResult | null; fixed: SimulationResult | null }>({
    adaptive: null,
    fixed: null,
  });

  const [showSim, setShowSim] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [simParams, setSimParams] = useState({
    numTrades: 1000,
    winRate: 0.52,
    avgWin: 0.94,
    avgLoss: 1.0,
    startingBalance: 1000,
    volatility: 0.05,
  });

  const sizing = useAdaptivePositionSizing(config);
  const simulation = useSizingSimulation();

  const handleRunSimulation = async () => {
    const adaptiveResult = await simulation.runSimulation(
      { ...simParams, strategy: 'even_odd' },
      (confidence: number, strategy: string, volatilityData?: number[]) => sizing.calculateSize(confidence, strategy, volatilityData || [])
    );

    const fixedResult = await simulation.runFixedSimulation(
      { ...simParams, strategy: 'even_odd' },
      config.baseAmount
    );

    setSimResults({ adaptive: adaptiveResult, fixed: fixedResult });
  };

  const stats = sizing.getPerformanceStats();

  return (
    <div className="space-y-4">
      {/* Current Sizing Status */}
      <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 overflow-hidden">
        <div className="px-4 sm:px-5 py-4 border-b border-slate-800/50 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Scale className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Adaptive Position Sizing</h3>
            <p className="text-[10px] text-slate-500">Kelly Criterion + Risk Management</p>
          </div>
        </div>

        <div className="p-4 sm:p-5 space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard label="Balance" value={`$${sizing.balance.toFixed(2)}`} color="text-white" icon={DollarSign} />
            <StatCard label="Peak" value={`$${sizing.peakBalance.toFixed(2)}`} color="text-emerald-400" icon={TrendingUp} />
            <StatCard label="Drawdown" value={sizing.currentDrawdown.toFixed(1)} suffix="%" color={sizing.currentDrawdown > 5 ? 'text-red-400' : 'text-emerald-400'} icon={TrendingDown} />
            <StatCard label="Trades" value={stats.totalTrades} color="text-blue-400" icon={Activity} />
          </div>

          {stats.totalTrades > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatCard label="Win Rate" value={stats.winRate.toFixed(1)} suffix="%" color={stats.winRate >= 50 ? 'text-emerald-400' : 'text-red-400'} />
              <StatCard label="Profit Factor" value={stats.profitFactor.toFixed(2)} color={stats.profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400'} />
              <StatCard label="Expectancy" value={`$${stats.expectancy.toFixed(4)}`} color={stats.expectancy >= 0 ? 'text-emerald-400' : 'text-red-400'} />
              <StatCard label="Max DD" value={stats.maxDrawdown.toFixed(1)} suffix="%" color="text-red-400" />
            </div>
          )}
        </div>
      </div>

      {/* Configuration */}
      <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 overflow-hidden">
        <button
          onClick={() => setShowConfig(!showConfig)}
          className="w-full px-4 sm:px-5 py-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center">
              <Target className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-semibold text-white">Configuration</span>
          </div>
          {showConfig ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {showConfig && (
          <div className="px-4 sm:px-5 pb-5 border-t border-slate-800/50 pt-4 space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {[
                { key: 'baseAmount', label: 'Base Amount', suffix: '$', min: 0.35, max: 10000, step: 0.01 },
                { key: 'maxRiskPerTrade', label: 'Max Risk/Trade', suffix: '%', min: 0.1, max: 10, step: 0.1, isPercent: true },
                { key: 'maxDailyExposure', label: 'Max Daily Exposure', suffix: '%', min: 5, max: 100, step: 5, isPercent: true },
                { key: 'kellyFraction', label: 'Kelly Fraction', suffix: '', min: 0.05, max: 1, step: 0.05 },
                { key: 'drawdownReductionStart', label: 'DD Reduction Start', suffix: '%', min: 1, max: 50, step: 1 },
                { key: 'drawdownMax', label: 'Max Drawdown', suffix: '%', min: 5, max: 50, step: 1 },
              ].map((field) => (
                <div key={field.key}>
                  <label className="block text-[10px] text-slate-500 uppercase tracking-wider mb-1.5">{field.label}</label>
                  <div className="relative">
                    <input
                      type="number"
                      min={field.min}
                      max={field.max}
                      step={field.step}
                      value={field.isPercent ? (config[field.key as keyof SizingConfig] as number) * 100 : config[field.key as keyof SizingConfig] as number}
                      onChange={(e) => setConfig((c) => ({ ...c, [field.key]: field.isPercent ? parseFloat(e.target.value) / 100 : parseFloat(e.target.value) }))}
                      className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-xs text-white font-mono focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                    />
                    {field.suffix && (
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 text-xs">{field.suffix}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap gap-4 pt-2">
              {[
                { key: 'lossStreakReduction', label: 'Loss Streak Reduction' },
                { key: 'winStreakBoost', label: 'Win Streak Boost (conservative)' },
              ].map((toggle) => (
                <label key={toggle.key} className="flex items-center gap-2 cursor-pointer">
                  <div className={`w-8 h-4 rounded-full p-0.5 transition-all ${(config[toggle.key as keyof SizingConfig] as boolean) ? 'bg-cyan-500' : 'bg-slate-600'}`}>
                    <div className={`w-3 h-3 rounded-full bg-white transition-all ${(config[toggle.key as keyof SizingConfig] as boolean) ? 'translate-x-4' : 'translate-x-0'}`} />
                  </div>
                  <span className="text-xs text-slate-300">{toggle.label}</span>
                </label>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Simulation */}
      <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 overflow-hidden">
        <button
          onClick={() => setShowSim(!showSim)}
          className="w-full px-4 sm:px-5 py-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
              <BarChart3 className="w-4 h-4 text-white" />
            </div>
            <div className="text-left">
              <span className="text-sm font-semibold text-white">Monte Carlo Simulation</span>
              <p className="text-[10px] text-slate-500">Compare adaptive vs fixed sizing</p>
            </div>
          </div>
          {showSim ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {showSim && (
          <div className="px-4 sm:px-5 pb-5 border-t border-slate-800/50 pt-4 space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {[
                { key: 'numTrades', label: 'Trades' },
                { key: 'winRate', label: 'Win Rate', isPercent: true },
                { key: 'avgWin', label: 'Avg Win ($)' },
                { key: 'avgLoss', label: 'Avg Loss ($)' },
                { key: 'startingBalance', label: 'Start Balance ($)' },
                { key: 'volatility', label: 'Volatility', isPercent: true },
              ].map((field) => (
                <div key={field.key}>
                  <label className="block text-[10px] text-slate-500 uppercase tracking-wider mb-1.5">{field.label}</label>
                  <input
                    type="number"
                    min={field.isPercent ? 0 : undefined}
                    max={field.isPercent ? 1 : undefined}
                    step={field.isPercent ? 0.01 : 1}
                    value={field.isPercent ? simParams[field.key as keyof typeof simParams] : simParams[field.key as keyof typeof simParams]}
                    onChange={(e) => setSimParams((p) => ({ ...p, [field.key]: parseFloat(e.target.value) }))}
                    className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-xs text-white font-mono focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                  />
                </div>
              ))}
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleRunSimulation}
                disabled={simulation.isRunning}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white text-xs font-bold disabled:from-slate-600 disabled:to-slate-700 disabled:cursor-not-allowed transition-all shadow-lg shadow-emerald-500/20"
              >
                <Play className="w-4 h-4" />
                {simulation.isRunning ? `Running... ${simulation.progress}%` : 'Run Simulation'}
              </button>
              <button
                onClick={() => { sizing.reset(); setSimResults({ adaptive: null, fixed: null }); }}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-slate-600/50 text-slate-300 text-xs font-medium transition-all"
              >
                <RotateCcw className="w-4 h-4" />
                Reset
              </button>
            </div>

            {/* Results */}
            {(simResults.adaptive || simResults.fixed) && (
              <div className="space-y-4 pt-2">
                <div className="bg-slate-800/30 rounded-xl border border-slate-700/30 p-3">
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Equity Curves</div>
                  <EquityChart
                    curves={[simResults.adaptive?.equityCurve || [], simResults.fixed?.equityCurve || []]}
                  />
                  <div className="flex gap-4 mt-2">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                      <span className="text-[10px] text-slate-400">Adaptive</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-blue-500" />
                      <span className="text-[10px] text-slate-400">Fixed</span>
                    </div>
                  </div>
                </div>

                <div className="bg-slate-800/30 rounded-xl border border-slate-700/30 overflow-hidden">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-left text-slate-500 border-b border-slate-700/50">
                        <th className="px-3 py-2 font-medium">Metric</th>
                        <th className="px-3 py-2 text-emerald-400 font-medium">Adaptive</th>
                        <th className="px-3 py-2 text-blue-400 font-medium">Fixed</th>
                        <th className="px-3 py-2 font-medium">Delta</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/30">
                      {[
                        { label: 'Final Balance', key: 'finalBalance', fmt: (v: number) => `$${v.toFixed(2)}`, better: 'higher' },
                        { label: 'Total Return', key: 'totalReturn', fmt: (v: number) => `${v.toFixed(2)}%`, better: 'higher' },
                        { label: 'Max Drawdown', key: 'maxDrawdownPct', fmt: (v: number) => `${v.toFixed(2)}%`, better: 'lower' },
                        { label: 'Sharpe Ratio', key: 'sharpeRatio', fmt: (v: number) => v.toFixed(3), better: 'higher' },
                        { label: 'Profit Factor', key: 'profitFactor', fmt: (v: number) => v.toFixed(2), better: 'higher' },
                        { label: 'Win Rate', key: 'winRate', fmt: (v: number) => `${v.toFixed(1)}%`, better: 'higher' },
                      ].map((row) => {
                        const aVal = (simResults.adaptive as any)?.[row.key] ?? 0;
                        const fVal = (simResults.fixed as any)?.[row.key] ?? 0;
                        const delta = aVal - fVal;
                        const isBetter = row.better === 'higher' ? delta > 0 : delta < 0;

                        return (
                          <tr key={row.key}>
                            <td className="px-3 py-2 text-slate-300">{row.label}</td>
                            <td className="px-3 py-2 text-emerald-400 font-bold font-mono">{row.fmt(aVal)}</td>
                            <td className="px-3 py-2 text-blue-400 font-bold font-mono">{row.fmt(fVal)}</td>
                            <td className={`px-3 py-2 font-bold font-mono ${isBetter ? 'text-emerald-400' : 'text-red-400'}`}>
                              {delta > 0 ? '+' : ''}{row.fmt(delta)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {simResults.adaptive && simResults.fixed && (
                  <div className={`p-3 rounded-xl border flex items-center gap-3 ${
                    simResults.adaptive.finalBalance > simResults.fixed.finalBalance
                      ? 'bg-emerald-500/10 border-emerald-500/20'
                      : 'bg-red-500/10 border-red-500/20'
                  }`}>
                    {simResults.adaptive.finalBalance > simResults.fixed.finalBalance ? (
                      <>
                        <ShieldCheck className="w-5 h-5 text-emerald-400" />
                        <span className="text-xs text-emerald-400 font-medium">
                          Adaptive sizing outperformed fixed by ${(simResults.adaptive.finalBalance - simResults.fixed.finalBalance).toFixed(2)}
                        </span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="w-5 h-5 text-red-400" />
                        <span className="text-xs text-red-400 font-medium">
                          Fixed sizing outperformed adaptive by ${(simResults.fixed.finalBalance - simResults.adaptive.finalBalance).toFixed(2)}
                        </span>
                      </>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
