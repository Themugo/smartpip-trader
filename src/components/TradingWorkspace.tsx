import { useState } from 'react';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  PieChart,
  Shield,
  BarChart3,
  Bell,
  History,
  Settings,


  Minimize2,





  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle
} from 'lucide-react';

interface Panel {
  id: string;
  title: string;
  icon: React.ReactNode;
  visible: boolean;
  minimized: boolean;
  order: number;
}

interface Trade {
  id: string;
  symbol: string;
  direction: 'up' | 'down';
  amount: number;
  profit: number;
  time: string;
  status: 'open' | 'closed' | 'pending';
}

export function TradingWorkspace() {
  const [panels, setPanels] = useState<Panel[]>([
    { id: 'market-watch', title: 'Market Watch', icon: <Activity className="w-4 h-4" />, visible: true, minimized: false, order: 1 },
    { id: 'chart', title: 'Chart Area', icon: <BarChart3 className="w-4 h-4" />, visible: true, minimized: false, order: 2 },
    { id: 'ai-decision', title: 'AI Decision Panel', icon: <Activity className="w-4 h-4" />, visible: true, minimized: false, order: 3 },
    { id: 'positions', title: 'Open Positions', icon: <TrendingUp className="w-4 h-4" />, visible: true, minimized: false, order: 4 },
    { id: 'orders', title: 'Pending Orders', icon: <Clock className="w-4 h-4" />, visible: true, minimized: false, order: 5 },
    { id: 'portfolio', title: 'Portfolio Summary', icon: <PieChart className="w-4 h-4" />, visible: true, minimized: false, order: 6 },
    { id: 'risk', title: 'Risk Gauge', icon: <Shield className="w-4 h-4" />, visible: true, minimized: false, order: 7 },
    { id: 'broker', title: 'Broker Status', icon: <Activity className="w-4 h-4" />, visible: true, minimized: false, order: 8 },
    { id: 'journal', title: 'Trade Journal', icon: <History className="w-4 h-4" />, visible: true, minimized: false, order: 9 },
    { id: 'news', title: 'News Panel', icon: <Bell className="w-4 h-4" />, visible: true, minimized: false, order: 10 },
    { id: 'execution', title: 'Execution Log', icon: <CheckCircle2 className="w-4 h-4" />, visible: true, minimized: false, order: 11 },
    { id: 'session', title: 'Session Statistics', icon: <BarChart3 className="w-4 h-4" />, visible: true, minimized: false, order: 12 },
  ]);

  const [symbols] = useState([
    { symbol: 'V-75', name: 'Volatility 75', price: '1845.32', change: '+1.24%', up: true },
    { symbol: 'V-50', name: 'Volatility 50', price: '923.18', change: '-0.45%', up: false },
    { symbol: 'V-25', name: 'Volatility 25', price: '461.55', change: '+0.12%', up: true },
    { symbol: 'R-10', name: 'Rise/Fall 10', price: '184.62', change: '+0.32%', up: true },
  ]);

  const [openPositions] = useState<Trade[]>([
    { id: '1', symbol: 'V-75', direction: 'up', amount: 100, profit: 85.50, time: '2 min ago', status: 'open' },
    { id: '2', symbol: 'V-50', direction: 'down', amount: 50, profit: -12.30, time: '5 min ago', status: 'open' },
  ]);

  const [brokerStatus] = useState({
    connected: true,
    latency: 45,
    lastSync: 'Just now',
    balance: 10250.00,
    currency: 'USD',
  });

  const togglePanel = (id: string) => {
    setPanels(prev => prev.map(p => p.id === id ? { ...p, visible: !p.visible } : p));
  };

  const minimizePanel = (id: string) => {
    setPanels(prev => prev.map(p => p.id === id ? { ...p, minimized: !p.minimized } : p));
  };

  const renderPanelContent = (panelId: string) => {
    switch (panelId) {
      case 'market-watch':
        return (
          <div className="space-y-2">
            {symbols.map((s) => (
              <div key={s.symbol} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 cursor-pointer transition-colors">
                <div>
                  <span className="font-medium text-white">{s.symbol}</span>
                  <span className="text-xs text-slate-500 ml-2">{s.name}</span>
                </div>
                <div className="text-right">
                  <div className="text-white font-medium">${s.price}</div>
                  <div className={`text-xs ${s.up ? 'text-emerald-400' : 'text-red-400'}`}>
                    {s.change}
                  </div>
                </div>
              </div>
            ))}
          </div>
        );

      case 'chart':
        return (
          <div className="h-64 bg-slate-800/50 rounded-lg flex items-center justify-center">
            <div className="text-center text-slate-500">
              <BarChart3 className="w-12 h-12 mx-auto mb-2" />
              <p>Interactive Chart Placeholder</p>
              <p className="text-xs">Powered by TradingView</p>
            </div>
          </div>
        );

      case 'ai-decision':
        return (
          <div className="space-y-3">
            <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-5 h-5 text-emerald-400" />
                <span className="font-medium text-white">Buy Signal</span>
                <span className="ml-auto px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full">94%</span>
              </div>
              <p className="text-sm text-slate-400">Digit pattern match detected. High confidence entry point.</p>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center p-2 bg-slate-800/50 rounded-lg">
                <p className="text-xs text-slate-500">Confidence</p>
                <p className="text-lg font-bold text-emerald-400">94%</p>
              </div>
              <div className="text-center p-2 bg-slate-800/50 rounded-lg">
                <p className="text-xs text-slate-500">Risk</p>
                <p className="text-lg font-bold text-amber-400">Low</p>
              </div>
              <div className="text-center p-2 bg-slate-800/50 rounded-lg">
                <p className="text-xs text-slate-500">Size</p>
                <p className="text-lg font-bold text-white">5%</p>
              </div>
            </div>
          </div>
        );

      case 'positions':
        return (
          <div className="space-y-2">
            {openPositions.map((pos) => (
              <div key={pos.id} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                <div className="flex items-center gap-3">
                  {pos.direction === 'up' ? (
                    <TrendingUp className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <TrendingDown className="w-5 h-5 text-red-400" />
                  )}
                  <div>
                    <p className="font-medium text-white">{pos.symbol}</p>
                    <p className="text-xs text-slate-500">${pos.amount} • {pos.time}</p>
                  </div>
                </div>
                <div className={`font-medium ${pos.profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {pos.profit >= 0 ? '+' : ''}${pos.profit.toFixed(2)}
                </div>
              </div>
            ))}
            {openPositions.length === 0 && (
              <p className="text-center text-slate-500 py-4">No open positions</p>
            )}
          </div>
        );

      case 'orders':
        return (
          <div className="space-y-2">
            <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-amber-400" />
                <div>
                  <p className="font-medium text-white">V-75 UP</p>
                  <p className="text-xs text-slate-500">Pending execution</p>
                </div>
              </div>
              <span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 text-xs rounded-full">Pending</span>
            </div>
          </div>
        );

      case 'portfolio':
        return (
          <div className="space-y-4">
            <div className="text-center p-4 bg-slate-800/50 rounded-lg">
              <p className="text-xs text-slate-500 mb-1">Total Equity</p>
              <p className="text-2xl font-bold text-white">${brokerStatus.balance.toLocaleString()}</p>
              <p className="text-sm text-emerald-400">+$450.00 (+4.6%)</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-slate-800/50 rounded-lg text-center">
                <p className="text-xs text-slate-500">Open</p>
                <p className="text-lg font-bold text-white">{openPositions.length}</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-lg text-center">
                <p className="text-xs text-slate-500">Today</p>
                <p className="text-lg font-bold text-emerald-400">+4.6%</p>
              </div>
            </div>
          </div>
        );

      case 'risk':
        return (
          <div className="space-y-3">
            <div className="p-4 bg-slate-800/50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-400">Daily Loss</span>
                <span className="text-white font-medium">$127 / $500</span>
              </div>
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: '25%' }} />
              </div>
            </div>
            <div className="p-4 bg-slate-800/50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-400">Consecutive Losses</span>
                <span className="text-white font-medium">2 / 5</span>
              </div>
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <div className="h-full bg-amber-500 rounded-full" style={{ width: '40%' }} />
              </div>
            </div>
            <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-center">
              <Shield className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
              <p className="text-emerald-400 font-medium">Risk Status: SAFE</p>
              <p className="text-xs text-slate-400 mt-1">All metrics within limits</p>
            </div>
          </div>
        );

      case 'broker':
        return (
          <div className="space-y-3">
            <div className="flex items-center gap-3 p-4 bg-slate-800/50 rounded-lg">
              {brokerStatus.connected ? (
                <CheckCircle2 className="w-8 h-8 text-emerald-400" />
              ) : (
                <XCircle className="w-8 h-8 text-red-400" />
              )}
              <div>
                <p className="font-medium text-white">Deriv</p>
                <p className="text-sm text-slate-400">
                  {brokerStatus.connected ? 'Connected' : 'Disconnected'}
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-slate-800/50 rounded-lg text-center">
                <p className="text-xs text-slate-500">Latency</p>
                <p className="text-lg font-bold text-white">{brokerStatus.latency}ms</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-lg text-center">
                <p className="text-xs text-slate-500">Last Sync</p>
                <p className="text-lg font-bold text-slate-400">{brokerStatus.lastSync}</p>
              </div>
            </div>
          </div>
        );

      case 'journal':
        return (
          <div className="space-y-2">
            <div className="p-3 bg-slate-800/50 rounded-lg">
              <div className="flex items-center gap-2 mb-1">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-sm text-white">V-75 UP +$85.50</span>
              </div>
              <p className="text-xs text-slate-500">AI signal: 94% confidence. Pattern match confirmed.</p>
            </div>
            <div className="p-3 bg-slate-800/50 rounded-lg">
              <div className="flex items-center gap-2 mb-1">
                <XCircle className="w-4 h-4 text-red-400" />
                <span className="text-sm text-white">V-50 DOWN -$12.30</span>
              </div>
              <p className="text-xs text-slate-500">AI signal: 72% confidence. Regime shift detected.</p>
            </div>
          </div>
        );

      case 'news':
        return (
          <div className="space-y-2">
            <div className="p-3 bg-slate-800/50 rounded-lg">
              <p className="text-sm text-white mb-1">Market Update</p>
              <p className="text-xs text-slate-500">Volatility indices showing moderate activity. Expected range-bound trading.</p>
            </div>
            <div className="p-3 bg-slate-800/50 rounded-lg">
              <p className="text-sm text-white mb-1">System Alert</p>
              <p className="text-xs text-slate-500">All systems operational. AI models updated.</p>
            </div>
          </div>
        );

      case 'execution':
        return (
          <div className="space-y-2 text-xs font-mono">
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="w-3 h-3" />
              <span>2026-07-17 14:32:15 EXECUTE BUY V-75 $100</span>
            </div>
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="w-3 h-3" />
              <span>2026-07-17 14:32:18 FILLED @ 1845.32</span>
            </div>
            <div className="flex items-center gap-2 text-amber-400">
              <AlertCircle className="w-3 h-3" />
              <span>2026-07-17 14:30:45 SIGNAL HIGH CONFIDENCE (94%)</span>
            </div>
          </div>
        );

      case 'session':
        return (
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-slate-800/50 rounded-lg text-center">
              <p className="text-xs text-slate-500">Trades</p>
              <p className="text-lg font-bold text-white">12</p>
            </div>
            <div className="p-3 bg-slate-800/50 rounded-lg text-center">
              <p className="text-xs text-slate-500">Win Rate</p>
              <p className="text-lg font-bold text-emerald-400">83%</p>
            </div>
            <div className="p-3 bg-slate-800/50 rounded-lg text-center">
              <p className="text-xs text-slate-500">P&L</p>
              <p className="text-lg font-bold text-emerald-400">+$450</p>
            </div>
            <div className="p-3 bg-slate-800/50 rounded-lg text-center">
              <p className="text-xs text-slate-500">Duration</p>
              <p className="text-lg font-bold text-white">2h 15m</p>
            </div>
          </div>
        );

      default:
        return <p className="text-slate-500">Panel content</p>;
    }
  };

  const visiblePanels = panels.filter(p => p.visible).sort((a, b) => a.order - b.order);

  return (
    <div className="h-full flex flex-col bg-slate-950">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold text-white">Trading Workspace</h2>
          <div className="flex items-center gap-2">
            {brokerStatus.connected ? (
              <span className="flex items-center gap-1 px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs rounded-full">
                <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                Connected
              </span>
            ) : (
              <span className="flex items-center gap-1 px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded-full">
                <span className="w-2 h-2 bg-red-400 rounded-full" />
                Disconnected
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors">
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Panel Grid */}
      <div className="flex-1 p-4 overflow-auto">
        <div className="grid grid-cols-12 gap-4">
          {/* Main Column - Chart and AI */}
          <div className="col-span-8 space-y-4">
            {/* Market Watch + Chart Row */}
            <div className="grid grid-cols-3 gap-4">
              {/* Market Watch */}
              <div className="col-span-1 bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    {panels.find(p => p.id === 'market-watch')?.icon}
                    <span className="font-medium text-white text-sm">Market Watch</span>
                  </div>
                  <button onClick={() => minimizePanel('market-watch')} className="text-slate-500 hover:text-white">
                    <Minimize2 className="w-4 h-4" />
                  </button>
                </div>
                {!panels.find(p => p.id === 'market-watch')?.minimized && (
                  <div className="p-4">
                    {renderPanelContent('market-watch')}
                  </div>
                )}
              </div>

              {/* AI Decision */}
              <div className="col-span-2 bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    {panels.find(p => p.id === 'ai-decision')?.icon}
                    <span className="font-medium text-white text-sm">AI Decision</span>
                  </div>
                  <button onClick={() => minimizePanel('ai-decision')} className="text-slate-500 hover:text-white">
                    <Minimize2 className="w-4 h-4" />
                  </button>
                </div>
                {!panels.find(p => p.id === 'ai-decision')?.minimized && (
                  <div className="p-4">
                    {renderPanelContent('ai-decision')}
                  </div>
                )}
              </div>
            </div>

            {/* Chart Area */}
            <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  {panels.find(p => p.id === 'chart')?.icon}
                  <span className="font-medium text-white text-sm">Chart - V-75</span>
                </div>
                <button onClick={() => minimizePanel('chart')} className="text-slate-500 hover:text-white">
                  <Minimize2 className="w-4 h-4" />
                </button>
              </div>
              {!panels.find(p => p.id === 'chart')?.minimized && (
                <div className="p-4">
                  {renderPanelContent('chart')}
                </div>
              )}
            </div>

            {/* Positions + Orders */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    {panels.find(p => p.id === 'positions')?.icon}
                    <span className="font-medium text-white text-sm">Open Positions</span>
                  </div>
                  <button onClick={() => minimizePanel('positions')} className="text-slate-500 hover:text-white">
                    <Minimize2 className="w-4 h-4" />
                  </button>
                </div>
                {!panels.find(p => p.id === 'positions')?.minimized && (
                  <div className="p-4">
                    {renderPanelContent('positions')}
                  </div>
                )}
              </div>
              <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    {panels.find(p => p.id === 'orders')?.icon}
                    <span className="font-medium text-white text-sm">Pending Orders</span>
                  </div>
                  <button onClick={() => minimizePanel('orders')} className="text-slate-500 hover:text-white">
                    <Minimize2 className="w-4 h-4" />
                  </button>
                </div>
                {!panels.find(p => p.id === 'orders')?.minimized && (
                  <div className="p-4">
                    {renderPanelContent('orders')}
                  </div>
                )}
              </div>
            </div>

            {/* Session + Execution */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    {panels.find(p => p.id === 'session')?.icon}
                    <span className="font-medium text-white text-sm">Session Stats</span>
                  </div>
                  <button onClick={() => minimizePanel('session')} className="text-slate-500 hover:text-white">
                    <Minimize2 className="w-4 h-4" />
                  </button>
                </div>
                {!panels.find(p => p.id === 'session')?.minimized && (
                  <div className="p-4">
                    {renderPanelContent('session')}
                  </div>
                )}
              </div>
              <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    {panels.find(p => p.id === 'execution')?.icon}
                    <span className="font-medium text-white text-sm">Execution Log</span>
                  </div>
                  <button onClick={() => minimizePanel('execution')} className="text-slate-500 hover:text-white">
                    <Minimize2 className="w-4 h-4" />
                  </button>
                </div>
                {!panels.find(p => p.id === 'execution')?.minimized && (
                  <div className="p-4">
                    {renderPanelContent('execution')}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar Column */}
          <div className="col-span-4 space-y-4">
            {/* Portfolio */}
            <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  {panels.find(p => p.id === 'portfolio')?.icon}
                  <span className="font-medium text-white text-sm">Portfolio</span>
                </div>
                <button onClick={() => minimizePanel('portfolio')} className="text-slate-500 hover:text-white">
                  <Minimize2 className="w-4 h-4" />
                </button>
              </div>
              {!panels.find(p => p.id === 'portfolio')?.minimized && (
                <div className="p-4">
                  {renderPanelContent('portfolio')}
                </div>
              )}
            </div>

            {/* Risk */}
            <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  {panels.find(p => p.id === 'risk')?.icon}
                  <span className="font-medium text-white text-sm">Risk Gauge</span>
                </div>
                <button onClick={() => minimizePanel('risk')} className="text-slate-500 hover:text-white">
                  <Minimize2 className="w-4 h-4" />
                </button>
              </div>
              {!panels.find(p => p.id === 'risk')?.minimized && (
                <div className="p-4">
                  {renderPanelContent('risk')}
                </div>
              )}
            </div>

            {/* Broker */}
            <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  {panels.find(p => p.id === 'broker')?.icon}
                  <span className="font-medium text-white text-sm">Broker</span>
                </div>
                <button onClick={() => minimizePanel('broker')} className="text-slate-500 hover:text-white">
                  <Minimize2 className="w-4 h-4" />
                </button>
              </div>
              {!panels.find(p => p.id === 'broker')?.minimized && (
                <div className="p-4">
                  {renderPanelContent('broker')}
                </div>
              )}
            </div>

            {/* Journal */}
            <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  {panels.find(p => p.id === 'journal')?.icon}
                  <span className="font-medium text-white text-sm">Journal</span>
                </div>
                <button onClick={() => minimizePanel('journal')} className="text-slate-500 hover:text-white">
                  <Minimize2 className="w-4 h-4" />
                </button>
              </div>
              {!panels.find(p => p.id === 'journal')?.minimized && (
                <div className="p-4">
                  {renderPanelContent('journal')}
                </div>
              )}
            </div>

            {/* News */}
            <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  {panels.find(p => p.id === 'news')?.icon}
                  <span className="font-medium text-white text-sm">News</span>
                </div>
                <button onClick={() => minimizePanel('news')} className="text-slate-500 hover:text-white">
                  <Minimize2 className="w-4 h-4" />
                </button>
              </div>
              {!panels.find(p => p.id === 'news')?.minimized && (
                <div className="p-4">
                  {renderPanelContent('news')}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
