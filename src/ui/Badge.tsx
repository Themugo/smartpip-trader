/**
 * Badge Component
 * 
 * Standardized badge component for labels, tags, and status indicators.
 */

import { type ReactNode } from 'react';
import { cn } from './utils';

export type BadgeVariant = 
  | 'default' 
  | 'primary' 
  | 'secondary' 
  | 'success' 
  | 'warning' 
  | 'error' 
  | 'info'
  | 'outline';

export type BadgeSize = 'sm' | 'md' | 'lg';

export interface BadgeProps {
  /** Badge content */
  children: ReactNode;
  /** Visual style variant */
  variant?: BadgeVariant;
  /** Size variant */
  size?: BadgeSize;
  /** Rounded pill style */
  pill?: boolean;
  /** With dot indicator */
  dot?: boolean;
  /** With icon */
  icon?: ReactNode;
  /** Custom class name */
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-slate-700 text-slate-300',
  primary: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  secondary: 'bg-violet-500/20 text-violet-400 border border-violet-500/30',
  success: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  warning: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  error: 'bg-red-500/20 text-red-400 border border-red-500/30',
  info: 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30',
  outline: 'bg-transparent border border-slate-600 text-slate-300',
};

const sizeStyles: Record<BadgeSize, string> = {
  sm: 'px-1.5 py-0.5 text-xs gap-1',
  md: 'px-2 py-0.5 text-xs gap-1.5',
  lg: 'px-2.5 py-1 text-sm gap-2',
};

export function Badge({
  children,
  variant = 'default',
  size = 'md',
  pill = false,
  dot = false,
  icon,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center font-medium',
        variantStyles[variant],
        sizeStyles[size],
        pill ? 'rounded-full' : 'rounded-md',
        className
      )}
    >
      {dot && (
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full',
            variant === 'default' && 'bg-slate-400',
            variant === 'primary' && 'bg-blue-400',
            variant === 'secondary' && 'bg-violet-400',
            variant === 'success' && 'bg-emerald-400',
            variant === 'warning' && 'bg-amber-400',
            variant === 'error' && 'bg-red-400',
            variant === 'info' && 'bg-cyan-400',
            variant === 'outline' && 'bg-slate-400'
          )}
        />
      )}
      {icon && <span className="flex-shrink-0">{icon}</span>}
      {children}
    </span>
  );
}

// Status-specific badges
export function StatusBadge({ status }: { status: 'connected' | 'disconnected' | 'connecting' | 'error' }) {
  const config = {
    connected: { variant: 'success' as const, label: 'Connected', dot: true },
    disconnected: { variant: 'error' as const, label: 'Disconnected', dot: true },
    connecting: { variant: 'warning' as const, label: 'Connecting', dot: true },
    error: { variant: 'error' as const, label: 'Error', dot: true },
  };
  
  const { variant, label, dot } = config[status];
  
  return (
    <Badge variant={variant} dot={dot}>
      {label}
    </Badge>
  );
}

// Trade type badges
export function TradeTypeBadge({ type }: { type: 'CALL' | 'PUT' | 'DIGITEVEN' | 'DIGITODD' | 'DIGITMATCH' | 'DIGITDIFF' }) {
  const config: Record<string, { variant: BadgeVariant; label: string }> = {
    CALL: { variant: 'success', label: 'CALL' },
    PUT: { variant: 'error', label: 'PUT' },
    DIGITEVEN: { variant: 'info', label: 'Even' },
    DIGITODD: { variant: 'info', label: 'Odd' },
    DIGITMATCH: { variant: 'primary', label: 'Match' },
    DIGITDIFF: { variant: 'secondary', label: 'Diff' },
  };
  
  const { variant, label } = config[type] || { variant: 'default', label: type };
  
  return <Badge variant={variant}>{label}</Badge>;
}

// Win/Loss badges
export function WinLossBadge({ profit }: { profit: number }) {
  const isWin = profit > 0;
  const isBreakEven = profit === 0;
  
  return (
    <Badge variant={isWin ? 'success' : isBreakEven ? 'warning' : 'error'}>
      {isWin ? '+' : ''}{profit.toFixed(2)}
    </Badge>
  );
}

// Confidence badge
export function ConfidenceBadge({ confidence }: { confidence: number }) {
  const getVariant = (): BadgeVariant => {
    if (confidence >= 80) return 'success';
    if (confidence >= 60) return 'warning';
    return 'error';
  };
  
  return (
    <Badge variant={getVariant()} size="sm">
      {confidence}%
    </Badge>
  );
}

export default Badge;
