/**
 * Alert Component
 * 
 * Standardized alert component for displaying messages and notifications.
 */

import { type ReactNode } from 'react';
import { cn } from './utils';

export type AlertVariant = 'info' | 'success' | 'warning' | 'error';

export interface AlertProps {
  /** Alert content */
  children: ReactNode;
  /** Alert title */
  title?: string;
  /** Visual style variant */
  variant?: AlertVariant;
  /** Show dismiss button */
  dismissible?: boolean;
  /** Dismiss handler */
  onDismiss?: () => void;
  /** Additional actions */
  actions?: ReactNode;
  /** Custom class name */
  className?: string;
}

const variantStyles: Record<AlertVariant, { bg: string; border: string; icon: string; iconColor: string }> = {
  info: {
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    icon: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
    iconColor: 'text-blue-400',
  },
  success: {
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
    iconColor: 'text-emerald-400',
  },
  warning: {
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
    iconColor: 'text-amber-400',
  },
  error: {
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    icon: 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z',
    iconColor: 'text-red-400',
  },
};

export function Alert({
  children,
  title,
  variant = 'info',
  dismissible = false,
  onDismiss,
  actions,
  className,
}: AlertProps) {
  const { bg, border, icon, iconColor } = variantStyles[variant];

  return (
    <div
      role="alert"
      className={cn(
        'p-4 rounded-lg border',
        bg,
        border,
        className
      )}
    >
      <div className="flex gap-3">
        <svg
          className={cn('w-5 h-5 flex-shrink-0 mt-0.5', iconColor)}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={icon} />
        </svg>
        
        <div className="flex-1">
          {title && (
            <h4 className="font-medium text-white mb-1">{title}</h4>
          )}
          <div className="text-sm text-slate-300">{children}</div>
          
          {actions && (
            <div className="flex gap-2 mt-3">
              {actions}
            </div>
          )}
        </div>
        
        {dismissible && onDismiss && (
          <button
            onClick={onDismiss}
            className="text-slate-400 hover:text-white transition-colors"
            aria-label="Dismiss"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}

// Preset alert components
export function InfoAlert({ title, children, ...props }: Omit<AlertProps, 'variant'>) {
  return <Alert variant="info" title={title} {...props}>{children}</Alert>;
}

export function SuccessAlert({ title, children, ...props }: Omit<AlertProps, 'variant'>) {
  return <Alert variant="success" title={title} {...props}>{children}</Alert>;
}

export function WarningAlert({ title, children, ...props }: Omit<AlertProps, 'variant'>) {
  return <Alert variant="warning" title={title} {...props}>{children}</Alert>;
}

export function ErrorAlert({ title, children, ...props }: Omit<AlertProps, 'variant'>) {
  return <Alert variant="error" title={title} {...props}>{children}</Alert>;
}

export default Alert;
