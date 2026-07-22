import { Inbox, AlertTriangle, RefreshCw, ArrowRight } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

// ── Empty State ────────────────────────────────────────────────

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  actionLabel,
  onAction,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-12 px-4 text-center ${className}`}>
      <div className="w-12 h-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center mb-3">
        <Icon className="w-6 h-6 text-slate-500" />
      </div>
      <h3 className="text-sm font-semibold text-slate-300 mb-1">{title}</h3>
      {description && (
        <p className="text-xs text-slate-500 max-w-xs leading-relaxed">{description}</p>
      )}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-3 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/15 border border-blue-500/25 text-blue-400 text-xs font-medium hover:bg-blue-500/25 transition-colors"
        >
          {actionLabel}
          <ArrowRight className="w-3 h-3" />
        </button>
      )}
    </div>
  );
}

// ── Error State ────────────────────────────────────────────────

interface ErrorStateProps {
  title?: string;
  message: string;
  errorId?: string;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  errorId,
  onRetry,
  retryLabel = 'Try again',
  className = '',
}: ErrorStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-10 px-4 text-center ${className}`}>
      <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-3">
        <AlertTriangle className="w-6 h-6 text-red-400" />
      </div>
      <h3 className="text-sm font-semibold text-slate-300 mb-1">{title}</h3>
      <p className="text-xs text-slate-500 max-w-xs leading-relaxed mb-1">{message}</p>
      {errorId && (
        <p className="text-[10px] font-mono text-slate-600 mb-3">{errorId}</p>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/15 border border-red-500/25 text-red-400 text-xs font-medium hover:bg-red-500/25 transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          {retryLabel}
        </button>
      )}
    </div>
  );
}

// ── Banner Error (for inline error bars) ───────────────────────

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export function ErrorBanner({ message, onRetry, onDismiss, className = '' }: ErrorBannerProps) {
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-xs ${className}`}>
      <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0" />
      <span className="text-red-400 flex-1 min-w-0 truncate">{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="shrink-0 flex items-center gap-1 px-2 py-0.5 rounded bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-colors"
        >
          <RefreshCw className="w-2.5 h-2.5" />
          Retry
        </button>
      )}
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="shrink-0 text-red-500 hover:text-red-300 transition-colors"
        >
          Dismiss
        </button>
      )}
    </div>
  );
}
