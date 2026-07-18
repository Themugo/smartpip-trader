import { useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  BarChart3,

  Activity,
  Download,



  Target,
  DollarSign,
  Clock,
  ArrowUpRight,
  ArrowDownRight,

} from 'lucide-react';

export function AnalyticsPlatform() {
  const [selectedPeriod, setSelectedPeriod] = useState('7d');
  const [selectedView, setSelectedView] = useState<'equity' | 'trades' | 'strategy' | 'comparison'>('equity');

  // Performance Metrics
  const metrics = {
    equity: { value: 10450, change: 4.5, trend: 'up' },
    winRate: { value: 86, change: 2.1, trend: 'up' },
    profitFactor: { value: 2.4, change: 0.3, trend: 'up' },
    sharpeRatio: { value: 2.1, change: -0.1, trend: 'down' },
    maxDrawdown: { value: 3.2, change: -0.5, trend: 'up' },
    expectancy: { value: 0.72, change: 0.05, trend: 'up' },
    avgHoldingTime: { value: '4m 32s', change: 12, trend: 'up' },
    calmarRatio: { value: 1.4, change: 0.2, trend: 'up' },
  };

  // Strategy Comparison
  const strategyComparison = [
    { name: 'Digit Master', trades: 156, winRate: 87, profit: 2450, sharpe: 2.4 },
    { name: 'Trend Rider', trades: 89, winRate: 78, profit: 1820, sharpe: 1.9 },
    { name: 'Grid Pro', trades: 234, winRate: 72, profit: 1680, sharpe: 1.6 },
  ];

  // Symbol Performance
  const symbolPerformance = [
    { symbol: 'V-75', trades: 145, winRate: 88, pnl: 1890 },
    { symbol: 'V-50', trades: 98, winRate: 82, pnl: 1120 },
    { symbol: 'V-25', trades: 67, winRate: 85, pnl: 780 },
    { symbol: 'R-10', trades: 45, winRate: 79, pnl: 520 },
  ];

  // Session Performance
  const sessionPerformance = [
    { day: 'Mon', trades: 12, pnl: 245 },
    { day: 'Tue', trades: 18, pnl: 380 },
    { day: 'Wed', trades: 15, pnl: -120 },
    { day: 'Thu', trades: 22, pnl: 520 },
    { day: 'Fri', trades: 19, pnl: 345 },
  ];

  return (
    <div className="min-h-screen bg-slate-950 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Analytics Platform</h1>
            <p className="text-slate-400">Comprehensive trading performance analysis</p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              className="px-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="90d">Last 90 Days</option>
              <option value="all">All Time</option>
            </select>
            <button className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors">
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>

        {/* Period Selector */}
        <div className="flex gap-2">
          {[
            { id: 'equity', label: 'Equity Curve' },
            { id: 'trades', label: 'Trade Analysis' },
            { id: 'strategy', label: 'Strategy' },
            { id: 'comparison', label: 'Comparison' },
          ].map(view => (
            <button
              key={view.id}
              onClick={() => setSelectedView(view.id as any)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedView === view.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              {view.label}
            </button>
          ))}
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-slate-500 text-sm">Total Equity</span>
              <ArrowUpRight className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-2xl font-bold text-white mb-1">${metrics.equity.value.toLocaleString()}</p>
            <p className={`text-sm ${metrics.equity.trend === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
              {metrics.equity.change >= 0 ? '+' : ''}{metrics.equity.change}%
            </p>
          </div>

          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-slate-500 text-sm">Win Rate</span>
              <Target className="w-4 h-4 text-slate-500" />
            </div>
            <p className="text-2xl font-bold text-white mb-1">{metrics.winRate.value}%</p>
            <p className={`text-sm ${metrics.winRate.trend === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
              {metrics.winRate.change >= 0 ? '+' : ''}{metrics.winRate.change}%
            </p>
          </div>

          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-slate-500 text-sm">Profit Factor</span>
              <BarChart3 className="w-4 h-4 text-slate-500" />
            </div>
            <p className="text-2xl font-bold text-white mb-1">{metrics.profitFactor.value}</p>
            <p className={`text-sm ${metrics.profitFactor.trend === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
              {metrics.profitFactor.change >= 0 ? '+' : ''}{metrics.profitFactor.change}
            </p>
          </div>

          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-slate-500 text-sm">Sharpe Ratio</span>
              <TrendingUp className="w-4 h-4 text-slate-500" />
            </div>
            <p className="text-2xl font-bold text-white mb-1">{metrics.sharpeRatio.value}</p>
            <p className={`text-sm ${metrics.sharpeRatio.trend === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
              {metrics.sharpeRatio.change >= 0 ? '+' : ''}{metrics.sharpeRatio.change}
            </p>
          </div>
        </div>

        {/* Secondary Metrics */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-slate-500 text-sm">Max Drawdown</span>
              <TrendingDown className="w-4 h-4 text-red-500" />
            </div>
            <p className="text-2xl font-bold text-amber-400">-{metrics.maxDrawdown.value}%</p>
          </div>

          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-slate-500 text-sm">Expectancy</span>
              <Activity className="w-4 h-4 text-slate-500" />
            </div>
            <p className="text-2xl font-bold text-white">${metrics.expectancy.value}</p>
          </div>

          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-slate-500 text-sm">Avg Holding Time</span>
              <Clock className="w-4 h-4 text-slate-500" />
            </div>
            <p className="text-2xl font-bold text-white">{metrics.avgHoldingTime.value}</p>
          </div>

          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-slate-500 text-sm">Calmar Ratio</span>
              <TrendingUp className="w-4 h-4 text-slate-500" />
            </div>
            <p className="text-2xl font-bold text-white">{metrics.calmarRatio.value}</p>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-2 gap-6">
          {/* Equity Curve */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Equity Curve</h3>
              <div className="flex items-center gap-2 text-sm">
                <span className="w-3 h-3 bg-blue-500 rounded-full"></span>
                <span className="text-slate-400">Equity</span>
                <span className="w-3 h-3 bg-slate-600 rounded-full ml-2"></span>
                <span className="text-slate-400">Drawdown</span>
              </div>
            </div>
            <div className="h-64 flex items-center justify-center bg-slate-800/50 rounded-lg">
              <div className="text-center text-slate-500">
                <TrendingUp className="w-12 h-12 mx-auto mb-2" />
                <p>Equity Curve Chart</p>
                <p className="text-xs">Powered by Recharts</p>
              </div>
            </div>
          </div>

          {/* Session Performance */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Session Performance</h3>
            </div>
            <div className="space-y-3">
              {sessionPerformance.map((session, i) => (
                <div key={i} className="flex items-center gap-4">
                  <span className="w-12 text-sm text-slate-500">{session.day}</span>
                  <div className="flex-1 h-6 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${session.pnl >= 0 ? 'bg-emerald-500' : 'bg-red-500'} rounded-full`}
                      style={{ width: `${Math.min(100, Math.abs(session.pnl) / 6)}%` }}
                    />
                  </div>
                  <span className={`w-20 text-right text-sm font-medium ${
                    session.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'
                  }`}>
                    {session.pnl >= 0 ? '+' : ''}${session.pnl}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Strategy & Symbol Comparison */}
        <div className="grid grid-cols-2 gap-6">
          {/* Strategy Comparison */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Strategy Comparison</h3>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 text-left">
                  <th className="pb-3 font-medium">Strategy</th>
                  <th className="pb-3 font-medium text-right">Trades</th>
                  <th className="pb-3 font-medium text-right">Win Rate</th>
                  <th className="pb-3 font-medium text-right">P&L</th>
                  <th className="pb-3 font-medium text-right">Sharpe</th>
                </tr>
              </thead>
              <tbody>
                {strategyComparison.map((strategy, i) => (
                  <tr key={i} className="border-t border-slate-800">
                    <td className="py-3 text-white font-medium">{strategy.name}</td>
                    <td className="py-3 text-right text-slate-400">{strategy.trades}</td>
                    <td className="py-3 text-right">
                      <span className={`${strategy.winRate >= 80 ? 'text-emerald-400' : strategy.winRate >= 70 ? 'text-amber-400' : 'text-red-400'}`}>
                        {strategy.winRate}%
                      </span>
                    </td>
                    <td className={`py-3 text-right ${strategy.profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      ${strategy.profit}
                    </td>
                    <td className="py-3 text-right text-white">{strategy.sharpe}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Symbol Performance */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Symbol Performance</h3>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 text-left">
                  <th className="pb-3 font-medium">Symbol</th>
                  <th className="pb-3 font-medium text-right">Trades</th>
                  <th className="pb-3 font-medium text-right">Win Rate</th>
                  <th className="pb-3 font-medium text-right">P&L</th>
                </tr>
              </thead>
              <tbody>
                {symbolPerformance.map((symbol, i) => (
                  <tr key={i} className="border-t border-slate-800">
                    <td className="py-3 text-white font-medium">{symbol.symbol}</td>
                    <td className="py-3 text-right text-slate-400">{symbol.trades}</td>
                    <td className={`py-3 text-right ${
                      symbol.winRate >= 85 ? 'text-emerald-400' :
                      symbol.winRate >= 75 ? 'text-amber-400' : 'text-red-400'
                    }`}>
                      {symbol.winRate}%
                    </td>
                    <td className={`py-3 text-right ${symbol.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      +${symbol.pnl}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Trade Distribution */}
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Trade Distribution</h3>
          </div>
          <div className="grid grid-cols-3 gap-6">
            {/* Win/Loss Pie */}
            <div className="flex items-center justify-center">
              <div className="relative w-40 h-40">
                <svg className="w-full h-full transform -rotate-90">
                  <circle cx="80" cy="80" r="70" fill="none" stroke="#1e293b" strokeWidth="20" />
                  <circle
                    cx="80"
                    cy="80"
                    r="70"
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="20"
                    strokeDasharray={`${0.86 * 440} 440`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-bold text-white">86%</span>
                  <span className="text-xs text-slate-500">Win Rate</span>
                </div>
              </div>
            </div>

            {/* Win/Loss Stats */}
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-emerald-500/10 rounded-lg">
                <div className="flex items-center gap-2">
                  <ArrowUpRight className="w-4 h-4 text-emerald-400" />
                  <span className="text-emerald-400">Wins</span>
                </div>
                <span className="text-xl font-bold text-white">134</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-red-500/10 rounded-lg">
                <div className="flex items-center gap-2">
                  <ArrowDownRight className="w-4 h-4 text-red-400" />
                  <span className="text-red-400">Losses</span>
                </div>
                <span className="text-xl font-bold text-white">22</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                <div className="flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-slate-400" />
                  <span className="text-slate-400">Breakeven</span>
                </div>
                <span className="text-xl font-bold text-white">0</span>
              </div>
            </div>

            {/* Average Win/Loss */}
            <div className="space-y-4">
              <div className="p-3 bg-slate-800/50 rounded-lg">
                <p className="text-xs text-slate-500 mb-1">Avg Win</p>
                <p className="text-2xl font-bold text-emerald-400">+$85.50</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-lg">
                <p className="text-xs text-slate-500 mb-1">Avg Loss</p>
                <p className="text-2xl font-bold text-red-400">-$42.30</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-lg">
                <p className="text-xs text-slate-500 mb-1">Best Trade</p>
                <p className="text-2xl font-bold text-white">+$245</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
