import { useState } from 'react';
import {
  Scale, TrendingUp, TrendingDown, Activity, DollarSign,
  ShieldCheck, AlertTriangle, BarChart3, Play, RotateCcw,
  ChevronDown, ChevronUp, Hash, Zap, Target
} from 'lucide-react';
import { useAdaptivePositionSizing, type SizingConfig } from '../hooks/useAdaptivePositionSizing';
import { useSizingSimulation, type SimulationResult } from '../hooks/useSizingSimulation';

interface PositionSizingPanelProps {
  currentBalance?: number;
}

function StatCard({ label, value, suffix = '', color = 'text-slate-300' }: {
  label: string; value: string | number; suffix?: string; color?: string;
}) {
  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-2.5 text-center">
      <div className="text-[10px] text-slate-400">{label}</div>
      <div className={`text-sm font-bold ${color}`}>{value}{suffix}</div>
    </div>
  );
}

function EquityChart({ curves, labels }: { curves: number[][]; labels: string[] }) {
  if (!curves.length || !curves[0].length) return null;

  const maxVal = Math.max(...curves.flat());
  const minVal = Math.min(...curves.flat());
  const range = maxVal - minVal || 1;

  const colors = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'];

  return (
    <div className="h-32 relative">
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

export function PositionSizingPanel({ currentBalance }: PositionSizingPanelProps) {
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
    // Run adaptive
    const adaptiveResult = await simulation.runSimulation(
      {
        numTrades: simParams.numTrades,
        winRate: simParams.winRate,
        avgWin: simParams.avgWin,
        avgLoss: simParams.avgLoss,
        startingBalance: simParams.startingBalance,
        volatility: simParams.volatility,
        strategy: 'even_odd',
      },
      config,
      (confidence, strategy, volData) => sizing.calculateSize(confidence, strategy, volData)
    );

    // Run fixed
    const fixedResult = await simulation.runFixedSimulation(
      {
        numTrades: simParams.numTrades,
        winRate: simParams.winRate,
        avgWin: simParams.avgWin,
        avgLoss: simParams.avgLoss,
        startingBalance: simParams.startingBalance,
        volatility: simParams.volatility,
        strategy: 'even_odd',
      },
      config.baseAmount
    );

    setSimResults({ adaptive: adaptiveResult, fixed: fixedResult });
  };

  const stats = sizing.getPerformanceStats();

  return (
    <div className="space-y-4">
      {/* Current Sizing Status */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
        <div className="flex items-center gap-2 mb-4">
          <Scale className="w-5 h-5 text-cyan-400" />
          <h3 className="text-sm font-semibold text-slate-200">Adaptive Position Sizing</h3>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
          <StatCard label="Balance" value={`$${sizing.balance.toFixed(2)}`} color="text-white" />
          <StatCard label="Peak" value={`$${sizing.peakBalance.toFixed(2)}`} color="text-emerald-400" />
          <StatCard label="Drawdown" value={`${sizing.currentDrawdown.toFixed(1)}`} suffix="%" color={sizing.currentDrawdown > 5 ? 'text-red-400' : 'text-emerald-400'} />
          <StatCard label="Trades" value={stats.totalTrades} color="text-blue-400" />
        </div>

        {stats.totalTrades > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <StatCard label="Win Rate" value={stats.winRate.toFixed(1)} suffix="%" color={stats.winRate >= 50 ? 'text-emerald-400' : 'text-red-400'} />
            <StatCard label="Profit Factor" value={stats.profitFactor.toFixed(2)} color={stats.profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400'} />
            <StatCard label="Expectancy" value={`$${stats.expectancy.toFixed(4)}`} color={stats.expectancy >= 0 ? 'text-emerald-400' : 'text-red-400'} />
            <StatCard label="Max DD" value={`${stats.maxDrawdown.toFixed(1)}`} suffix="%" color="text-red-400" />
          </div>
        )}
      </div>

      {/* Configuration */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
        <div className="flex items-center gap-2 mb-4">
          <Target className="w-5 h-5 text-blue-400" />
          <h3 className="text-sm font-semibold text-slate-200">Sizing Configuration</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-[10px] text-slate-400 mb-1">Base Amount ($)</label>
            <input
              type="number"
              min={0.35}
              step={0.01}
              value={config.baseAmount}
              onChange={(e) => setConfig((c) => ({ ...c, baseAmount: parseFloat(e.target.value) }))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="block text-[10px] text-slate-400 mb-1">Max Risk/Trade (%)</label>
            <input
              type="number"
              min={0.001}
              max={0.1}
              step={0.001}
              value={config.maxRiskPerTrade}
              onChange={(e) => setConfig((c) => ({ ...c, maxRiskPerTrade: parseFloat(e.target.value) }))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="block text-[10px] text-slate-400 mb-1">Max Daily Exposure (%)</label>
            <input
              type="number"
              min={0.05}
              max={1}
              step={0.05}
              value={config.maxDailyExposure}
              onChange={(e) => setConfig((c) => ({ ...c, maxDailyExposure: parseFloat(e.target.value) }))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="block text-[10px] text-slate-400 mb-1">Kelly Fraction</label>
            <input
              type="number"
              min={0.05}
              max={1}
              step={0.05}
              value={config.kellyFraction}
              onChange={(e) => setConfig((c) => ({ ...c, kellyFraction: parseFloat(e.target.value) }))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="block text-[10px] text-slate-400 mb-1">DD Reduction Start (%)</label>
            <input
              type="number"
              min={1}
              max={50}
              value={config.drawdownReductionStart}
              onChange={(e) => setConfig((c) => ({ ...c, drawdownReductionStart: parseFloat(e.target.value) }))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="block text-[10px] text-slate-400 mb-1">DD Max (%)</label>
            <input
              type="number"
              min={5}
              max={50}
              value={config.drawdownMax}
              onChange={(e) => setConfig((c) => ({ ...c, drawdownMax: parseFloat(e.target.value) }))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="block text-[10px] text-slate-400 mb-1">Confidence Weight</label>
            <input
              type="number"
              min={0}
              max={1}
              step={0.1}
              value={config.confidenceWeight}
              onChange={(e) => setConfig((c) => ({ ...c, confidenceWeight: parseFloat(e.target.value) }))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="block text-[10px] text-slate-400 mb-1">Min Trade Size ($)</label>
            <input
              type="number"
              min={0.35}
              step={0.01}
              value={config.minTradeSize}
              onChange={(e) => setConfig((c) => ({ ...c, minTradeSize: parseFloat(e.target.value) }))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-3 mt-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={config.lossStreakReduction}
              onChange={(e) => setConfig((c) => ({ ...c, lossStreakReduction: e.target.checked }))}
              className="w-4 h-4 rounded border-slate-600 bg-slate-900 text-blue-500"
            />
            <span className="text-xs text-slate-300">Loss Streak Reduction</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={config.winStreakBoost}
              onChange={(e) => setConfig((c) => ({ ...c, winStreakBoost: e.target.checked }))}
              className="w-4 h-4 rounded border-slate-600 bg-slate-900 text-blue-500"
            />
            <span className="text-xs text-slate-300">Win Streak Boost (conservative)</span>
          </label>
        </div>
      </div>

      {/* Simulation */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
        <button
          onClick={() => setShowSim(!showSim)}
          className="w-full flex items-center justify-between"
        >
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-emerald-400" />
            <h3 className="text-sm font-semibold text-slate-200">Monte Carlo Simulation</h3>
          </div>
          {showSim ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {showSim && (
          <div className="mt-4 space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">Trades</label>
                <input
                  type="number"
                  value={simParams.numTrades}
                  onChange={(e) => setSimParams((p) => ({ ...p, numTrades: parseInt(e.target.value) }))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">Win Rate</label>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.01}
                  value={simParams.winRate}
                  onChange={(e) => setSimParams((p) => ({ ...p, winRate: parseFloat(e.target.value) }))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">Avg Win ($)</label>
                <input
                  type="number"
                  step={0.01}
                  value={simParams.avgWin}
                  onChange={(e) => setSimParams((p) => ({ ...p, avgWin: parseFloat(e.target.value) }))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">Avg Loss ($)</label>
                <input
                  type="number"
                  step={0.01}
                  value={simParams.avgLoss}
                  onChange={(e) => setSimParams((p) => ({ ...p, avgLoss: parseFloat(e.target.value) }))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">Start Balance</label>
                <input
                  type="number"
                  value={simParams.startingBalance}
                  onChange={(e) => setSimParams((p) => ({ ...p, startingBalance: parseInt(e.target.value) }))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">Volatility</label>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.01}
                  value={simParams.volatility}
                  onChange={(e) => setSimParams((p) => ({ ...p, volatility: parseFloat(e.target.value) }))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                />
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleRunSimulation}
                disabled={simulation.isRunning}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium disabled:bg-slate-700 disabled:text-slate-500"
              >
                <Play className="w-4 h-4" />
                {simulation.isRunning ? `Running... ${simulation.progress}%` : 'Run Simulation'}
              </button>
              <button
                onClick={() => {
                  sizing.reset();
                  setSimResults({ adaptive: null, fixed: null });
                }}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm font-medium"
              >
                <RotateCcw className="w-4 h-4" />
                Reset
              </button>
            </div>

            {/* Results */}
            {(simResults.adaptive || simResults.fixed) && (
              <div className="space-y-4 pt-2">
                {/* Equity Curves */}
                <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-2">Equity Curves</div>
                  <EquityChart
                    curves={[
                      simResults.adaptive?.equityCurve || [],
                      simResults.fixed?.equityCurve || [],
                    ]}
                    labels={['Adaptive', 'Fixed']}
                  />
                  <div className="flex gap-4 mt-2">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full bg-emerald-500" />
                      <span className="text-[10px] text-slate-400">Adaptive</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full bg-blue-500" />
                      <span className="text-[10px] text-slate-400">Fixed</span>
                    </div>
                  </div>
                </div>

                {/* Comparison Table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-left text-slate-400 border-b border-slate-700">
                        <th className="px-2 py-2">Metric</th>
                        <th className="px-2 py-2 text-emerald-400">Adaptive</th>
                        <th className="px-2 py-2 text-blue-400">Fixed</th>
                        <th className="px-2 py-2">Delta</th>
                      </tr>
                    </thead>
                    <tbody>
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
                          <tr key={row.key} className="border-b border-slate-700/30">
                            <td className="px-2 py-2 text-slate-300">{row.label}</td>
                            <td className="px-2 py-2 text-emerald-400 font-medium">{row.fmt(aVal)}</td>
                            <td className="px-2 py-2 text-blue-400 font-medium">{row.fmt(fVal)}</td>
                            <td className={`px-2 py-2 font-medium ${isBetter ? 'text-emerald-400' : 'text-red-400'}`}>
                              {delta > 0 ? '+' : ''}{row.fmt(delta)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Winner Banner */}
                {simResults.adaptive && simResults.fixed && (
                  <div className={`p-3 rounded-lg border ${
                    simResults.adaptive.finalBalance > simResults.fixed.finalBalance
                      ? 'bg-emerald-500/10 border-emerald-500/20'
                      : 'bg-red-500/10 border-red-500/20'
                  }`}>
                    <div className="flex items-center gap-2">
                      {simResults.adaptive.finalBalance > simResults.fixed.finalBalance ? (
                        <>
                          <ShieldCheck className="w-4 h-4 text-emerald-400" />
                          <span className="text-xs text-emerald-400 font-medium">
                            Adaptive sizing outperformed fixed by ${(simResults.adaptive.finalBalance - simResults.fixed.finalBalance).toFixed(2)}
                          </span>
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="w-4 h-4 text-red-400" />
                          <span className="text-xs text-red-400 font-medium">
                            Fixed sizing outperformed adaptive by ${(simResults.fixed.finalBalance - simResults.adaptive.finalBalance).toFixed(2)}
                          </span>
                        </>
                      )}
                    </div>
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
