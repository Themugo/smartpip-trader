/**
 * Demo Data Badge Component
 * 
 * Visual indicator for demo/mock data throughout the platform.
 */

import { cn } from '../ui/utils';

export interface DemoDataBadgeProps {
  variant?: 'default' | 'subtle' | 'prominent';
  size?: 'sm' | 'md';
  showTooltip?: boolean;
  className?: string;
}

export function DemoDataBadge({
  variant = 'subtle',
  size = 'sm',
  showTooltip = true,
  className,
}: DemoDataBadgeProps) {
  const variantStyles = {
    default: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    subtle: 'bg-slate-800 text-slate-400 border-slate-700',
    prominent: 'bg-amber-500 text-black border-amber-400',
  };

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md border font-medium',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      title={showTooltip ? 'This data is for demonstration purposes only' : undefined}
    >
      <svg
        className="w-3 h-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      Demo
    </span>
  );
}

// Demo Data Container - wraps content that contains demo data
export interface DemoDataContainerProps {
  children: ReactNode;
  label?: string;
  showBadge?: boolean;
  className?: string;
}

import { type ReactNode } from 'react';

export function DemoDataContainer({
  children,
  label = 'Demo Data',
  showBadge = true,
  className,
}: DemoDataContainerProps) {
  return (
    <div className={cn('relative', className)}>
      {children}
      {showBadge && (
        <div className="absolute top-2 right-2">
          <DemoDataBadge />
        </div>
      )}
    </div>
  );
}

// Demo Data Warning Banner
export function DemoDataBanner() {
  return (
    <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4 mb-6">
      <div className="flex items-start gap-3">
        <svg
          className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <div>
          <h4 className="font-medium text-amber-400">Demo Mode Active</h4>
          <p className="text-sm text-slate-300 mt-1">
            This page contains demonstration data. Connect your broker account to see real trading data.
          </p>
        </div>
      </div>
    </div>
  );
}

// Demo Data Table Row - for marking specific rows
export function DemoDataRow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <tr className={cn('opacity-60', className)} title="Demo data row">
      {children}
    </tr>
  );
}

// Demo Data Placeholder
export function DemoPlaceholder({ 
  text = 'Loading...', 
  className 
}: { 
  text?: string; 
  className?: string 
}) {
  return (
    <span className={cn('text-slate-500 italic', className)}>
      {text}
    </span>
  );
}

// Demo Data Statistics - for showing demo metrics
export function DemoStatistics({ 
  label, 
  value, 
  demo = true 
}: { 
  label: string; 
  value: string | number; 
  demo?: boolean 
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-slate-400">{label}:</span>
      <span className="text-lg font-semibold text-white">{value}</span>
      {demo && <DemoDataBadge size="sm" />}
    </div>
  );
}

// Mock Data Indicator Hook
export function useMockData<T>(data: T, isMock: boolean = true): T | null {
  if (isMock) {
    console.warn('⚠️ Mock data is being used. Replace with real API data.');
    return data;
  }
  return data;
}

// Mock Data Generator Utilities
export const mockDataGenerators = {
  // Generate random trades
  generateTrades: (count: number = 10) => {
    const types = ['DIGITOVER', 'DIGITUNDER', 'DIGITMATCH', 'DIGITDIFF', 'RISEFALL', 'EVENODD'];
    const directions = ['up', 'down'];
    
    return Array.from({ length: count }, (_, i) => ({
      id: `mock-trade-${i}`,
      market: 'R_100',
      type: types[Math.floor(Math.random() * types.length)],
      direction: directions[Math.floor(Math.random() * directions.length)],
      amount: Math.floor(Math.random() * 100) + 10,
      confidence: Math.floor(Math.random() * 40) + 60,
      profit: (Math.random() - 0.4) * 50, // Slight positive bias
      entry_time: new Date(Date.now() - Math.random() * 86400000 * 7).toISOString(),
      exit_time: new Date(Date.now() - Math.random() * 86400000 * 7).toISOString(),
      isMock: true,
    }));
  },

  // Generate statistics
  generateStatistics: () => ({
    total_trades: 127,
    wins: 76,
    losses: 51,
    win_rate: 59.8,
    total_profit: 1245.67,
    session_pnl: 45.23,
    best_trade: 35.50,
    worst_trade: -28.00,
    avg_win: 16.39,
    avg_loss: -11.18,
    isMock: true,
  }),

  // Generate portfolio
  generatePortfolio: () => ({
    total_balance: 10245.67,
    equity: 10145.67,
    open_positions: 2,
    closed_positions: 125,
    win_rate: 59.8,
    profit_factor: 1.47,
    max_drawdown: 8.2,
    sharpe_ratio: 1.23,
    isMock: true,
  }),

  // Generate AI insights
  generateAIInsights: () => [
    {
      id: 'mock-insight-1',
      type: 'pattern',
      title: 'Bullish Divergence Detected',
      description: 'Price is showing bullish divergence on the 5-minute chart.',
      confidence: 78,
      timestamp: Date.now(),
      isMock: true,
    },
    {
      id: 'mock-insight-2',
      type: 'risk',
      title: 'Increased Volatility',
      description: 'Volatility has increased by 35% in the last hour.',
      confidence: 92,
      timestamp: Date.now(),
      isMock: true,
    },
  ],

  // Generate market data
  generateMarketData: (points: number = 50) => {
    let price = 100;
    return Array.from({ length: points }, (_, i) => {
      price += (Math.random() - 0.5) * 2;
      return {
        time: Date.now() - (points - i) * 60000,
        price: parseFloat(price.toFixed(2)),
        digit: Math.floor(Math.random() * 10),
      };
    });
  },
};

export default DemoDataBadge;
