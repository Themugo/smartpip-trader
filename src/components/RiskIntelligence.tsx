import { useState } from 'react';
import {
  Shield,
  AlertTriangle,
  TrendingUp,

  Activity,
  BarChart3,
  PieChart,


  DollarSign,

  RefreshCw,
  Download,
  Bell,
  CheckCircle2,
  XCircle,
  Maximize2,
  ChevronDown,
  Flame
} from 'lucide-react';

export function RiskIntelligence() {
  const [showMonteCarlo, setShowMonteCarlo] = useState(false);

  // Risk Metrics
  const riskMetrics = {
    dailyLossUsed: 127,
    dailyLossLimit: 500,
    consecutiveLosses: 2,
    maxConsecutiveLosses: 5,
    portfolioExposure: 35,
    maxExposure: 50,
    accountHealth: 92,
    var95: 245,
    expectedShortfall: 380,
  };

  // Correlation Matrix (mock data)
  const correlationMatrix = [
    { symbols: ['V-75', 'V-50', 'V-25', 'R-10'], correlations: [
      [1.00, 0.85, 0.72, 0.45],
      [0.85, 1.00, 0.88, 0.38],
      [0.72, 0.88, 1.00, 0.32],
      [0.45, 0.38, 0.32, 1.00],
    ]}
  ];

  // Monte Carlo Results (mock)
  const monteCarloResults = {
    simulations: 1000,
    finalEquity: { mean: 11500, median: 11450, p5: 9200, p95: 14200 },
    maxDrawdown: { mean: 8.5, median: 7.2, p5: 3.2, p95: 15.8 },
    survivalRate: 94.2,
    expectedReturn: 12.5,
    volatility: 18.3,
  };

  // Stress Test Scenarios
  const stressScenarios = [
    { name: 'Black Monday', impact: -25, probability: 2, exposure: 'High' },
    { name: 'Flash Crash', impact: -15, probability: 5, exposure: 'Medium' },
    { name: 'Volatility Spike', impact: -10, probability: 15, exposure: 'Low' },
    { name: 'Trend Reversal', impact: -8, probability: 20, exposure: 'Medium' },
  ];

  const getRiskColor = (value: number, max: number) => {
    const percent = (value / max) * 100;
    if (percent < 40) return 'text-emerald-400';
    if (percent < 70) return 'text-amber-400';
    return 'text-red-400';
  };

  const getRiskBgColor = (value: number, max: number) => {
    const percent = (value / max) * 100;
    if (percent < 40) return 'bg-emerald-500';
    if (percent < 70) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className="min-h-screen bg-slate-950 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Risk Intelligence</h1>
            <p className="text-slate-400">Monitor and manage your trading risk in real-time</p>
          </div>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors">
              <Bell className="w-4 h-4" />
              Configure Alerts
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors">
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* Risk Status Banner */}
        <div className={`p-6 rounded-xl border ${
          riskMetrics.accountHealth >= 80 
            ? 'bg-emerald-500/10 border-emerald-500/30' 
            : riskMetrics.accountHealth >= 50
            ? 'bg-amber-500/10 border-amber-500/30'
            : 'bg-red-500/10 border-red-500/30'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {riskMetrics.accountHealth >= 80 ? (
                <CheckCircle2 className="w-12 h-12 text-emerald-400" />
              ) : riskMetrics.accountHealth >= 50 ? (
                <AlertTriangle className="w-12 h-12 text-amber-400" />
              ) : (
                <XCircle className="w-12 h-12 text-red-400" />
              )}
              <div>
                <h2 className={`text-xl font-bold ${
                  riskMetrics.accountHealth >= 80 
                    ? 'text-emerald-400' 
                    : riskMetrics.accountHealth >= 50
                    ? 'text-amber-400'
                    : 'text-red-400'
                }`}>
                  Risk Status: {riskMetrics.accountHealth >= 80 ? 'SAFE' : riskMetrics.accountHealth >= 50 ? 'CAUTION' : 'CRITICAL'}
                </h2>
                <p className="text-slate-300">
                  All risk metrics within acceptable thresholds. Trading can continue.
                </p>
              </div>
            </div>
            <div className="text-center">
              <p className="text-4xl font-bold text-white">{riskMetrics.accountHealth}%</p>
              <p className="text-sm text-slate-400">Account Health</p>
            </div>
          </div>
        </div>

        {/* Main Risk Metrics */}
        <div className="grid grid-cols-4 gap-4">
          {/* Daily Loss */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-slate-500" />
                <span className="text-slate-400 text-sm">Daily Loss</span>
              </div>
              <span className={`text-sm font-medium ${getRiskColor(riskMetrics.dailyLossUsed, riskMetrics.dailyLossLimit)}`}>
                {((riskMetrics.dailyLossUsed / riskMetrics.dailyLossLimit) * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-2xl font-bold text-white mb-1">
              ${riskMetrics.dailyLossUsed} <span className="text-slate-500 text-lg">/ ${riskMetrics.dailyLossLimit}</span>
            </p>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden mt-3">
              <div 
                className={`h-full ${getRiskBgColor(riskMetrics.dailyLossUsed, riskMetrics.dailyLossLimit)} transition-all`}
                style={{ width: `${(riskMetrics.dailyLossUsed / riskMetrics.dailyLossLimit) * 100}%` }}
              />
            </div>
          </div>

          {/* Consecutive Losses */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Flame className="w-5 h-5 text-slate-500" />
                <span className="text-slate-400 text-sm">Consecutive Losses</span>
              </div>
            </div>
            <p className="text-2xl font-bold text-white mb-1">
              {riskMetrics.consecutiveLosses} <span className="text-slate-500 text-lg">/ {riskMetrics.maxConsecutiveLosses}</span>
            </p>
            <div className="flex gap-1 mt-3">
              {Array.from({ length: riskMetrics.maxConsecutiveLosses }).map((_, i) => (
                <div
                  key={i}
                  className={`w-6 h-6 rounded ${
                    i < riskMetrics.consecutiveLosses ? 'bg-red-500' : 'bg-slate-800'
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Portfolio Exposure */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <PieChart className="w-5 h-5 text-slate-500" />
                <span className="text-slate-400 text-sm">Portfolio Exposure</span>
              </div>
            </div>
            <p className="text-2xl font-bold text-white mb-1">
              {riskMetrics.portfolioExposure}% <span className="text-slate-500 text-lg">/ {riskMetrics.maxExposure}%</span>
            </p>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden mt-3">
              <div 
                className={`h-full ${getRiskBgColor(riskMetrics.portfolioExposure, riskMetrics.maxExposure)} transition-all`}
                style={{ width: `${(riskMetrics.portfolioExposure / riskMetrics.maxExposure) * 100}%` }}
              />
            </div>
          </div>

          {/* VaR */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-slate-500" />
                <span className="text-slate-400 text-sm">VaR (95%)</span>
              </div>
            </div>
            <p className="text-2xl font-bold text-white mb-1">
              ${riskMetrics.var95}
            </p>
            <p className="text-sm text-slate-500">Value at Risk for 1 day</p>
          </div>
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-2 gap-6">
          {/* Correlation Matrix */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <h3 className="text-lg font-semibold text-white mb-4">Correlation Matrix</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    <th className="text-left p-2 text-slate-500 font-medium"></th>
                    {correlationMatrix[0].symbols.map(sym => (
                      <th key={sym} className="text-center p-2 text-slate-400 font-medium">{sym}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {correlationMatrix[0].symbols.map((rowSym, i) => (
                    <tr key={rowSym}>
                      <td className="p-2 text-slate-400 font-medium">{rowSym}</td>
                      {correlationMatrix[0].correlations[i].map((val, j) => (
                        <td key={j} className="p-2 text-center">
                          <span className={`px-2 py-1 rounded ${
                            val >= 0.8 ? 'bg-red-500/20 text-red-400' :
                            val >= 0.6 ? 'bg-amber-500/20 text-amber-400' :
                            val >= 0.4 ? 'bg-slate-700 text-slate-300' :
                            'bg-emerald-500/20 text-emerald-400'
                          }`}>
                            {val.toFixed(2)}
                          </span>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Expected Shortfall */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <h3 className="text-lg font-semibold text-white mb-4">Expected Shortfall (CVaR)</h3>
            <div className="space-y-4">
              <div className="p-4 bg-slate-800/50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-slate-400">Expected Shortfall (95%)</span>
                  <span className="text-xl font-bold text-amber-400">${riskMetrics.expectedShortfall}</span>
                </div>
                <p className="text-xs text-slate-500">
                  Average loss when VaR is exceeded
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-slate-800/50 rounded-lg text-center">
                  <p className="text-2xl font-bold text-white">${riskMetrics.var95}</p>
                  <p className="text-xs text-slate-500">Value at Risk</p>
                </div>
                <div className="p-3 bg-slate-800/50 rounded-lg text-center">
                  <p className="text-2xl font-bold text-amber-400">${riskMetrics.expectedShortfall}</p>
                  <p className="text-xs text-slate-500">Expected Shortfall</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Monte Carlo Simulation */}
        <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
          <div 
            className="flex items-center justify-between p-5 cursor-pointer hover:bg-slate-800/50 transition-colors"
            onClick={() => setShowMonteCarlo(!showMonteCarlo)}
          >
            <div className="flex items-center gap-3">
              <Activity className="w-6 h-6 text-purple-400" />
              <div>
                <h3 className="text-lg font-semibold text-white">Monte Carlo Simulation</h3>
                <p className="text-sm text-slate-400">{monteCarloResults.simulations} simulations based on historical performance</p>
              </div>
            </div>
            <ChevronDown className={`w-5 h-5 text-slate-400 transition-transform ${showMonteCarlo ? 'rotate-180' : ''}`} />
          </div>

          {showMonteCarlo && (
            <div className="px-5 pb-5 space-y-4">
              {/* Distribution Chart Placeholder */}
              <div className="h-48 bg-slate-800/50 rounded-lg flex items-center justify-center">
                <div className="text-center text-slate-500">
                  <BarChart3 className="w-12 h-12 mx-auto mb-2" />
                  <p>Monte Carlo Distribution Chart</p>
                </div>
              </div>

              {/* Results Grid */}
              <div className="grid grid-cols-4 gap-4">
                <div className="p-4 bg-slate-800/50 rounded-lg">
                  <p className="text-xs text-slate-500 mb-1">Survival Rate</p>
                  <p className="text-2xl font-bold text-emerald-400">{monteCarloResults.survivalRate}%</p>
                </div>
                <div className="p-4 bg-slate-800/50 rounded-lg">
                  <p className="text-xs text-slate-500 mb-1">Expected Return</p>
                  <p className="text-2xl font-bold text-white">{monteCarloResults.expectedReturn}%</p>
                </div>
                <div className="p-4 bg-slate-800/50 rounded-lg">
                  <p className="text-xs text-slate-500 mb-1">Volatility</p>
                  <p className="text-2xl font-bold text-white">{monteCarloResults.volatility}%</p>
                </div>
                <div className="p-4 bg-slate-800/50 rounded-lg">
                  <p className="text-xs text-slate-500 mb-1">Final Equity (Mean)</p>
                  <p className="text-2xl font-bold text-white">${monteCarloResults.finalEquity.mean.toLocaleString()}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-slate-800/50 rounded-lg">
                  <p className="text-xs text-slate-500 mb-2">Final Equity Distribution</p>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-red-400">5th percentile: ${monteCarloResults.finalEquity.p5.toLocaleString()}</span>
                    <span className="text-emerald-400">95th percentile: ${monteCarloResults.finalEquity.p95.toLocaleString()}</span>
                  </div>
                </div>
                <div className="p-4 bg-slate-800/50 rounded-lg">
                  <p className="text-xs text-slate-500 mb-2">Max Drawdown Distribution</p>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-emerald-400">5th percentile: {monteCarloResults.maxDrawdown.p5}%</span>
                    <span className="text-red-400">95th percentile: {monteCarloResults.maxDrawdown.p95}%</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Stress Testing */}
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-white">Stress Testing</h3>
              <p className="text-sm text-slate-400">Scenario analysis for extreme market conditions</p>
            </div>
            <button className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm transition-colors">
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>

          <div className="grid grid-cols-4 gap-4">
            {stressScenarios.map((scenario, i) => (
              <div key={i} className="p-4 bg-slate-800/50 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-medium text-white">{scenario.name}</span>
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    scenario.exposure === 'High' ? 'bg-red-500/20 text-red-400' :
                    scenario.exposure === 'Medium' ? 'bg-amber-500/20 text-amber-400' :
                    'bg-emerald-500/20 text-emerald-400'
                  }`}>
                    {scenario.exposure}
                  </span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Impact</span>
                    <span className={`font-medium ${
                      scenario.impact <= -20 ? 'text-red-400' :
                      scenario.impact <= -10 ? 'text-amber-400' :
                      'text-emerald-400'
                    }`}>
                      {scenario.impact}%
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Probability</span>
                    <span className="text-white">{scenario.probability}%</span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${
                        scenario.impact <= -20 ? 'bg-red-500' :
                        scenario.impact <= -10 ? 'bg-amber-500' :
                        'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.abs(scenario.impact)}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Risk Recommendations */}
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
          <h3 className="text-lg font-semibold text-white mb-4">Risk Reduction Recommendations</h3>
          <div className="space-y-3">
            {[
              { priority: 'low', text: 'Consider reducing position size by 10% to improve Sharpe ratio', icon: TrendingUp },
              { priority: 'medium', text: 'High correlation detected between V-75 and V-50. Diversify to reduce exposure.', icon: AlertTriangle },
              { priority: 'high', text: 'Approaching daily loss limit. Pause trading to reassess strategy.', icon: Shield },
            ].map((rec, i) => (
              <div key={i} className="flex items-center gap-4 p-4 bg-slate-800/50 rounded-lg">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  rec.priority === 'high' ? 'bg-red-500/20 text-red-400' :
                  rec.priority === 'medium' ? 'bg-amber-500/20 text-amber-400' :
                  'bg-emerald-500/20 text-emerald-400'
                }`}>
                  <rec.icon className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <p className="text-white">{rec.text}</p>
                </div>
                <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm transition-colors">
                  Apply
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
