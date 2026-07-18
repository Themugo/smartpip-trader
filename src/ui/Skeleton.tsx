/**
 * Skeleton Component
 * 
 * Loading skeleton component for displaying placeholder content while loading.
 */

import { cn } from './utils';

export type SkeletonVariant = 'text' | 'circular' | 'rectangular' | 'rounded';

export interface SkeletonProps {
  /** Skeleton variant */
  variant?: SkeletonVariant;
  /** Width of the skeleton */
  width?: string | number;
  /** Height of the skeleton */
  height?: string | number;
  /** Animation speed in seconds */
  speed?: number;
  /** Number of skeleton lines (for text variant) */
  lines?: number;
  /** Custom class name */
  className?: string;
}

export function Skeleton({
  variant = 'text',
  width,
  height,
  speed = 1.5,
  lines = 1,
  className,
}: SkeletonProps) {
  const baseStyles = 'bg-slate-700 animate-pulse';
  
  const variantStyles = {
    text: '',
    circular: 'rounded-full',
    rectangular: 'rounded-md',
    rounded: 'rounded-lg',
  };

  const style: React.CSSProperties = {
    width: width || (variant === 'circular' ? height || 40 : '100%'),
    height: height || (variant === 'text' ? 16 : 40),
    animationDuration: `${speed}s`,
  };

  if (variant === 'text' && lines > 1) {
    return (
      <div className={cn('space-y-2', className)}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={cn(
              baseStyles,
              'rounded',
              i === lines - 1 ? 'w-3/4' : 'w-full'
            )}
            style={{
              height: height || 16,
              animationDuration: `${speed}s`,
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={cn(baseStyles, variantStyles[variant], className)}
      style={style}
    />
  );
}

// Preset skeleton components
export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return <Skeleton variant="text" lines={lines} className={className} />;
}

export function SkeletonAvatar({ size = 40, className }: { size?: number; className?: string }) {
  return <Skeleton variant="circular" width={size} height={size} className={className} />;
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-4 p-4 bg-slate-900 rounded-xl border border-slate-800', className)}>
      <div className="flex items-center gap-4">
        <Skeleton variant="circular" width={48} height={48} />
        <div className="flex-1 space-y-2">
          <Skeleton variant="text" height={20} width="60%" />
          <Skeleton variant="text" height={14} width="40%" />
        </div>
      </div>
      <SkeletonText lines={3} />
      <div className="flex gap-2">
        <Skeleton width={80} height={32} />
        <Skeleton width={80} height={32} />
      </div>
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4, className }: { rows?: number; cols?: number; className?: string }) {
  return (
    <div className={cn('space-y-3', className)}>
      {/* Header */}
      <div className="flex gap-4 px-4 py-2">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} variant="text" height={14} className="flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-4 px-4 py-3 bg-slate-800/50 rounded-lg">
          {Array.from({ length: cols }).map((_, colIndex) => (
            <Skeleton
              key={colIndex}
              variant="text"
              height={14}
              className="flex-1"
              width={colIndex === 0 ? '80%' : '60%'}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonChart({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-4', className)}>
      {/* Chart header */}
      <div className="flex justify-between items-center">
        <Skeleton width={120} height={20} />
        <Skeleton width={80} height={32} />
      </div>
      {/* Chart area */}
      <div className="h-48 flex items-end gap-2 px-4">
        {Array.from({ length: 12 }).map((_, i) => (
          <Skeleton
            key={i}
            variant="rounded"
            className="flex-1"
            height={`${Math.random() * 60 + 20}%`}
          />
        ))}
      </div>
    </div>
  );
}

export default Skeleton;
