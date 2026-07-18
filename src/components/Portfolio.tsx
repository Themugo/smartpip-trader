/**
 * Portfolio Page
 * 
 * Institutional-grade portfolio overview with comprehensive analytics,
 * equity curve, performance metrics, and risk management.
 */

import { useState, useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Skeleton } from '../ui/Skeleton';
import { EmptyState } from '../ui/EmptyState';
import { Tabs } from '../ui/Tabs';
import type { Trade, TradeStatistics } from '../lib/supabase';

interface PortfolioProps {
  trades: Trade[];
  statistics: TradeStatistics | null;
  isLoading?: boolean;
}

interface PortfolioMetrics {
  totalEquity: number;
  openPnl: number;
  closedPnl: number;
  totalDrawdown: number;
  maxDrawdown: number;
  winRate: number;
  profitFactor: number;
  sharpeRatio: number;
  totalTrades: number;
  avgWin: number;
  avgLoss: number;
  expectancy: number;
  bestTrade: number;
  worstTrade: number;
  consecutiveWins: number;
  consecutiveLosses: number;
}

interface PerformanceData {
  date: string;
  equity: number;
  drawdown: number;
  trades: number;
}

interface TradeDistribution {
  range: string;
  count: number;
  percentage: number;
}

export function Portfolio({ trades, statistics, isLoading = false }: PortfolioProps) {
  const [timeRange, setTimeRange] = useState<'day' | 'week' | 'month' | 'all'>('all');

  // Calculate comprehensive metrics
  const metrics = useMemo((): PortfolioMetrics | null => {
    if (!trades.length || !statistics) return null;

    const wins = trades.filter(t => (t.profit || 0) > 0);
    const losses = trades.filter(t => (t.profit || 0) <= 0);
    const profits = wins.map(t => t.profit || 0);
    const lossesValues = losses.map(t => Math.abs(t.profit || 0));

    // Calculate equity curve and drawdown
    let equity = 1000; // Starting balance
    let peak = equity;
    let maxDrawdown = 0;
    const equityCurve: number[] = [];

    trades.forEach(trade => {
      equity += (trade.profit || 0);
      equityCurve.push(equity);
      if (equity > peak) peak = equity;
      const drawdown = peak > 0 ? ((peak - equity) / peak) * 100 : 0;
      if (drawdown > maxDrawdown) maxDrawdown = drawdown;
    });

    // Calculate Sharpe ratio (simplified)
    const returns = equityCurve.slice(1).map((e, i) => e - equityCurve[i]);
    const avgReturn = returns.length > 0 ? returns.reduce((a, b) => a + b, 0) / returns.length : 0;
    const variance = returns.length > 0 
      ? returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length 
      : 0;
    const stdDev = Math.sqrt(variance);
    const sharpeRatio = stdDev !== 0 ? (avgReturn / stdDev) * Math.sqrt(252) : 0;

    // Calculate consecutive wins/losses
    let maxConsecutiveWins = 0;
    let maxConsecutiveLosses = 0;
    let currentWins = 0;
    let currentLosses = 0;

    trades.forEach(trade => {
      if ((trade.profit || 0) > 0) {
        currentWins++;
        currentLosses = 0;
        maxConsecutiveWins = Math.max(maxConsecutiveWins, currentWins);
      } else {
        currentLosses++;
        currentWins = 0;
        maxConsecutiveLosses = Math.max(maxConsecutiveLosses, currentLosses);
      }
    });

    const totalLosses = lossesValues.reduce((a, b) => a + b, 0);

    return {
      totalEquity: equity,
      openPnl: 0, // Would need open positions data
      closedPnl: equity - 1000,
      totalDrawdown: maxDrawdown,
      maxDrawdown: maxDrawdown,
      winRate: trades.length > 0 ? (wins.length / trades.length) * 100 : 0,
      profitFactor: totalLosses > 0
        ? (profits.reduce((a, b) => a + b, 0) || 0) / totalLosses
        : profits.length > 0 ? 999 : 0,
      sharpeRatio,
      totalTrades: trades.length,
      avgWin: wins.length > 0 ? (profits.reduce((a, b) => a + b, 0) || 0) / wins.length : 0,
      avgLoss: losses.length > 0 ? totalLosses / losses.length : 0,
      expectancy: trades.length > 0
        ? (trades.reduce((sum, t) => sum + (t.profit || 0), 0) || 0) / trades.length
        : 0,
      bestTrade: profits.length > 0 ? Math.max(...profits) : 0,
      worstTrade: losses.length > 0 ? -Math.min(...lossesValues) : 0,
      consecutiveWins: maxConsecutiveWins,
      consecutiveLosses: maxConsecutiveLosses,
    };
  }, [trades, statistics]);

  // Generate equity curve data
  const equityCurveData = useMemo((): PerformanceData[] => {
    if (!trades.length) return [];

    const data: PerformanceData[] = [];
    let equity = 1000;
    let peak = equity;

    trades.forEach((trade, index) => {
      equity += (trade.profit || 0);
      if (equity > peak) peak = equity;
      const drawdown = peak > 0 ? ((peak - equity) / peak) * 100 : 0;

      data.push({
        date: trade.entry_time?.split('T')[0] || `Trade ${index + 1}`,
        equity,
        drawdown,
        trades: index + 1,
      });
    });

    return data;
  }, [trades]);

  // Generate trade distribution
  const tradeDistribution = useMemo((): TradeDistribution[] => {
    if (!trades.length) return [];

    const profits = trades.map(t => t.profit || 0);
    const ranges = [
      { min: -Infinity, max: -50, label: '< -$50' },
      { min: -50, max: -25, label: '-$50 to -$25' },
      { min: -25, max: -10, label: '-$25 to -$10' },
      { min: -10, max: -5, label: '-$10 to -$5' },
      { min: -5, max: 0, label: '-$5 to $0' },
      { min: 0, max: 5, label: '$0 to $5' },
      { min: 5, max: 10, label: '$5 to $10' },
      { min: 10, max: 25, label: '$10 to $25' },
      { min: 25, max: 50, label: '$25 to $50' },
      { min: 50, max: Infinity, label: '> $50' },
    ];

    return ranges.map(range => {
      const count = profits.filter(p => p >= range.min && p < range.max).length;
      return {
        range: range.label,
        count,
        percentage: trades.length > 0 ? (count / trades.length) * 100 : 0,
      };
    }).filter(d => d.count > 0);
  }, [trades]);

  // Calculate performance calendar (simplified)
  const performanceCalendar = useMemo(() => {
    const days: { date: string; pnl: number }[] = [];
    const pnlByDay: Record<string, number> = {};

    trades.forEach(trade => {
      const date = trade.entry_time?.split('T')[0] || '';
      if (date) {
        pnlByDay[date] = (pnlByDay[date] || 0) + (trade.profit || 0);
      }
    });

    Object.entries(pnlByDay).forEach(([date, pnl]) => {
      days.push({ date, pnl });
    });

    return days.sort((a, b) => a.date.localeCompare(b.date));
  }, [trades]);

  if (isLoading) {
    return <PortfolioSkeleton />;
  }

  if (!trades.length) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">Portfolio</h1>
        </div>
        <Card>
          <EmptyState
            title="No trades yet"
            description="Execute some trades to see your portfolio analytics and performance metrics."
            action={{
              label: 'Execute First Trade',
              onClick: () => {},
            }}
          />
        </Card>
      </div>
    );
  }

  const tabs = [
    {
      id: 'overview',
      label: 'Overview',
      content: (
        <div className="space-y-6">
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <MetricCard
              label="Total Equity"
              value={metrics ? `$${metrics.totalEquity.toFixed(2)}` : '-'}
              change={metrics?.closedPnl}
              isPositive={metrics ? metrics.closedPnl >= 0 : undefined}
            />
            <MetricCard
              label="Win Rate"
              value={metrics ? `${metrics.winRate.toFixed(1)}%` : '-'}
              status={metrics ? (metrics.winRate >= 55 ? 'success' : metrics.winRate >= 45 ? 'warning' : 'error') : undefined}
            />
            <MetricCard
              label="Profit Factor"
              value={metrics ? metrics.profitFactor.toFixed(2) : '-'}
              status={metrics ? (metrics.profitFactor >= 1.5 ? 'success' : metrics.profitFactor >= 1 ? 'warning' : 'error') : undefined}
            />
            <MetricCard
              label="Sharpe Ratio"
              value={metrics ? metrics.sharpeRatio.toFixed(2) : '-'}
              status={metrics ? (metrics.sharpeRatio >= 1 ? 'success' : metrics.sharpeRatio >= 0 ? 'warning' : 'error') : undefined}
            />
            <MetricCard
              label="Max Drawdown"
              value={metrics ? `${metrics.maxDrawdown.toFixed(1)}%` : '-'}
              status={metrics ? (metrics.maxDrawdown <= 10 ? 'success' : metrics.maxDrawdown <= 20 ? 'warning' : 'error') : undefined}
            />
            <MetricCard
              label="Total Trades"
              value={metrics ? metrics.totalTrades.toString() : '-'}
            />
          </div>

          {/* Equity Curve */}
          <Card>
            <CardHeader title="Equity Curve" subtitle="Portfolio value over time" />
            <CardContent>
              <EquityCurveChart data={equityCurveData} />
            </CardContent>
          </Card>

          {/* Drawdown Chart */}
          <Card>
            <CardHeader title="Drawdown" subtitle="Portfolio drawdown percentage" />
            <CardContent>
              <DrawdownChart data={equityCurveData} />
            </CardContent>
          </Card>
        </div>
      ),
    },
    {
      id: 'performance',
      label: 'Performance',
      content: (
        <div className="space-y-6">
          {/* Performance Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard label="Avg Win" value={metrics ? `$${metrics.avgWin.toFixed(2)}` : '-'} status="success" />
            <MetricCard label="Avg Loss" value={metrics ? `$${metrics.avgLoss.toFixed(2)}` : '-'} status="error" />
            <MetricCard label="Expectancy" value={metrics ? `$${metrics.expectancy.toFixed(2)}` : '-'} status={metrics ? (metrics.expectancy >= 0 ? 'success' : 'error') : undefined} />
            <MetricCard label="Best Trade" value={metrics ? `$${metrics.bestTrade.toFixed(2)}` : '-'} status="success" />
            <MetricCard label="Worst Trade" value={metrics ? `$${metrics.worstTrade.toFixed(2)}` : '-'} status="error" />
            <MetricCard label="Consecutive Wins" value={metrics ? metrics.consecutiveWins.toString() : '-'} />
            <MetricCard label="Consecutive Losses" value={metrics ? metrics.consecutiveLosses.toString() : '-'} />
            <MetricCard label="Closed P/L" value={metrics ? `$${metrics.closedPnl.toFixed(2)}` : '-'} status={metrics ? (metrics.closedPnl >= 0 ? 'success' : 'error') : undefined} />
          </div>

          {/* Trade Distribution */}
          <Card>
            <CardHeader title="Trade Distribution" subtitle="Distribution of trade outcomes" />
            <CardContent>
              <TradeDistributionChart data={tradeDistribution} />
            </CardContent>
          </Card>

          {/* Performance Calendar */}
          <Card>
            <CardHeader title="Daily Performance" subtitle="P/L by trading day" />
            <CardContent>
              <PerformanceCalendar data={performanceCalendar} />
            </CardContent>
          </Card>
        </div>
      ),
    },
    {
      id: 'risk',
      label: 'Risk',
      content: (
        <div className="space-y-6">
          <RiskAnalysis metrics={metrics} />
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Portfolio</h1>
        <div className="flex gap-2">
          {(['day', 'week', 'month', 'all'] as const).map(range => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                timeRange === range
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              {range.charAt(0).toUpperCase() + range.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <Tabs tabs={tabs} variant="pills" />
    </div>
  );
}

// Metric Card Component
function MetricCard({
  label,
  value,
  change,
  isPositive,
  status,
}: {
  label: string;
  value: string | number | undefined | null;
  change?: number;
  isPositive?: boolean;
  status?: 'success' | 'warning' | 'error';
}) {
  const statusColors = {
    success: 'text-emerald-400',
    warning: 'text-amber-400',
    error: 'text-red-400',
  };
  
  const displayValue = value !== undefined && value !== null ? String(value) : '-';

  return (
    <Card padding="sm">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className={`text-xl font-semibold ${status ? statusColors[status] : 'text-white'}`}>
        {displayValue}
      </p>
      {change !== undefined && (
        <p className={`text-xs ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
          {isPositive ? '+' : ''}{change.toFixed(2)}
        </p>
      )}
    </Card>
  );
}

// Equity Curve Chart Component
function EquityCurveChart({ data }: { data: PerformanceData[] }) {
  if (!data.length) return <Skeleton height={200} />;

  const maxEquity = Math.max(...data.map(d => d.equity));
  const minEquity = Math.min(...data.map(d => d.equity));
  const range = maxEquity - minEquity || 1;

  return (
    <div className="h-64 flex items-end gap-1">
      {data.map((point, i) => {
        const height = ((point.equity - minEquity) / range) * 100;
        const isUp = i === 0 || point.equity >= data[i - 1].equity;
        return (
          <div
            key={i}
            className="flex-1 group relative"
            style={{ height: `${Math.max(height, 5)}%` }}
          >
            <div
              className={`absolute inset-x-0 bottom-0 rounded-t transition-colors ${
                isUp ? 'bg-emerald-500/60 hover:bg-emerald-500' : 'bg-red-500/60 hover:bg-red-500'
              }`}
            />
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-800 rounded text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
              <p className="font-medium">${point.equity.toFixed(2)}</p>
              <p className="text-slate-400">{point.date}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Drawdown Chart Component
function DrawdownChart({ data }: { data: PerformanceData[] }) {
  if (!data.length) return <Skeleton height={200} />;

  return (
    <div className="h-48 flex items-end gap-1">
      {data.map((point, i) => {
        const height = Math.min(point.drawdown * 2, 100); // Scale for visibility
        return (
          <div
            key={i}
            className="flex-1 group relative"
            style={{ height: `${Math.max(height, 2)}%` }}
          >
            <div className="absolute inset-x-0 bottom-0 bg-red-500/40 hover:bg-red-500/60 transition-colors rounded-t" />
          </div>
        );
      })}
    </div>
  );
}

// Trade Distribution Chart
function TradeDistributionChart({ data }: { data: TradeDistribution[] }) {
  if (!data.length) return <Skeleton height={200} />;

  const maxCount = Math.max(...data.map(d => d.count));

  return (
    <div className="space-y-2">
      {data.map((item, i) => (
        <div key={i} className="flex items-center gap-4">
          <span className="w-24 text-xs text-slate-400">{item.range}</span>
          <div className="flex-1 h-6 bg-slate-800 rounded overflow-hidden">
            <div
              className="h-full bg-blue-500/60 rounded transition-all"
              style={{ width: `${(item.count / maxCount) * 100}%` }}
            />
          </div>
          <span className="w-16 text-xs text-slate-400 text-right">{item.count}</span>
          <span className="w-16 text-xs text-slate-500 text-right">{item.percentage.toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
}

// Performance Calendar
function PerformanceCalendar({ data }: { data: { date: string; pnl: number }[] }) {
  if (!data.length) return <Skeleton height={200} />;

  const maxPnl = Math.max(...data.map(d => Math.abs(d.pnl)));

  return (
    <div className="grid grid-cols-7 gap-1">
      {data.map((day, i) => {
        const intensity = maxPnl > 0 ? Math.abs(day.pnl) / maxPnl : 0;
        const isPositive = day.pnl >= 0;
        return (
          <div
            key={i}
            className={`aspect-square rounded flex items-center justify-center text-xs ${
              isPositive ? 'bg-emerald-500/20 hover:bg-emerald-500/40' : 'bg-red-500/20 hover:bg-red-500/40'
            }`}
            style={{ opacity: 0.3 + intensity * 0.7 }}
            title={`${day.date}: $${day.pnl.toFixed(2)}`}
          >
            {new Date(day.date).getDate()}
          </div>
        );
      })}
    </div>
  );
}

// Risk Analysis Component
function RiskAnalysis({ metrics }: { metrics: PortfolioMetrics | null }) {
  const riskScore = useMemo(() => {
    if (!metrics) return 0;
    let score = 0;
    
    // Drawdown contribution
    if (metrics.maxDrawdown > 30) score += 30;
    else if (metrics.maxDrawdown > 20) score += 20;
    else if (metrics.maxDrawdown > 10) score += 10;
    else score += 5;

    // Win rate contribution
    if (metrics.winRate < 40) score += 25;
    else if (metrics.winRate < 50) score += 15;
    else if (metrics.winRate >= 55) score += 5;

    // Profit factor
    if (metrics.profitFactor < 0.8) score += 20;
    else if (metrics.profitFactor < 1) score += 10;
    else if (metrics.profitFactor >= 1.5) score += 5;

    return Math.min(score, 100);
  }, [metrics]);

  const riskLevel = riskScore <= 30 ? 'LOW' : riskScore <= 60 ? 'MEDIUM' : 'HIGH';
  const riskColors = {
    LOW: 'text-emerald-400',
    MEDIUM: 'text-amber-400',
    HIGH: 'text-red-400',
  };

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Risk Score */}
        <Card>
          <CardHeader title="Risk Score" subtitle="Overall portfolio risk assessment" />
          <CardContent>
            <div className="flex items-center justify-center py-8">
              <div className="relative w-32 h-32">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="8"
                    className="text-slate-700"
                  />
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="8"
                    strokeDasharray={`${(riskScore / 100) * 352} 352`}
                    strokeLinecap="round"
                    className={riskColors[riskLevel as keyof typeof riskColors]}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className={`text-3xl font-bold ${riskColors[riskLevel as keyof typeof riskColors]}`}>
                    {riskScore}
                  </span>
                  <span className="text-xs text-slate-400">Risk</span>
                </div>
              </div>
            </div>
            <Badge variant={riskScore <= 30 ? 'success' : riskScore <= 60 ? 'warning' : 'error'} className="w-full justify-center">
              {riskLevel} RISK
            </Badge>
          </CardContent>
        </Card>

        {/* Risk Factors */}
        <Card>
          <CardHeader title="Risk Factors" subtitle="Key risk indicators" />
          <CardContent>
            <div className="space-y-4">
              <RiskFactor
                label="Drawdown Risk"
                value={metrics?.maxDrawdown || 0}
                threshold={20}
                unit="%"
              />
              <RiskFactor
                label="Win Rate"
                value={metrics?.winRate || 0}
                threshold={50}
                unit="%"
                invert
              />
              <RiskFactor
                label="Profit Factor"
                value={metrics?.profitFactor || 0}
                threshold={1.2}
              />
              <RiskFactor
                label="Consecutive Losses"
                value={metrics?.consecutiveLosses || 0}
                threshold={5}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recommendations */}
      <Card>
        <CardHeader title="Risk Recommendations" subtitle="Suggested risk management actions" />
        <CardContent>
          <div className="space-y-2">
            {riskScore > 60 && (
              <div className="flex items-start gap-3 p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                <svg className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div>
                  <p className="text-sm font-medium text-red-400">High Risk Alert</p>
                  <p className="text-xs text-slate-400">Consider reducing position sizes and taking a break from trading.</p>
                </div>
              </div>
            )}
            {metrics?.maxDrawdown && metrics.maxDrawdown > 15 && (
              <div className="flex items-start gap-3 p-3 bg-amber-500/10 rounded-lg border border-amber-500/20">
                <svg className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="text-sm font-medium text-amber-400">Drawdown Warning</p>
                  <p className="text-xs text-slate-400">Your drawdown exceeds 15%. Consider tightening stop losses.</p>
                </div>
              </div>
            )}
            {metrics && metrics.winRate >= 55 && metrics.profitFactor >= 1.5 && (
              <div className="flex items-start gap-3 p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                <svg className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="text-sm font-medium text-emerald-400">Good Risk Management</p>
                  <p className="text-xs text-slate-400">Your metrics indicate solid risk management practices.</p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

// Risk Factor Component
function RiskFactor({
  label,
  value,
  threshold,
  unit = '',
  invert = false,
}: {
  label: string;
  value: number;
  threshold: number;
  unit?: string;
  invert?: boolean;
}) {
  const isGood = invert ? value >= threshold : value <= threshold;
  const percentage = invert 
    ? Math.min((value / threshold) * 100, 100)
    : Math.min((value / threshold) * 100, 100);

  return (
    <div className="flex items-center gap-4">
      <span className="w-32 text-sm text-slate-400">{label}</span>
      <div className="flex-1 h-2 bg-slate-800 rounded overflow-hidden">
        <div
          className={`h-full rounded transition-all ${
            isGood ? 'bg-emerald-500' : 'bg-red-500'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className={`w-20 text-sm text-right ${isGood ? 'text-emerald-400' : 'text-red-400'}`}>
        {value.toFixed(1)}{unit}
      </span>
    </div>
  );
}

// Loading Skeleton
function PortfolioSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Skeleton width={150} height={32} />
        <div className="flex gap-2">
          <Skeleton width={60} height={32} />
          <Skeleton width={60} height={32} />
          <Skeleton width={60} height={32} />
        </div>
      </div>
      <div className="grid grid-cols-6 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} height={80} />
        ))}
      </div>
      <Skeleton height={300} />
    </div>
  );
}

export default Portfolio;
