/**
 * Button Component
 * 
 * Standardized button component with multiple variants,
 * sizes, and states.
 */

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { tokens } from './tokens';
import { cn } from './utils';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success';
export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual style variant */
  variant?: ButtonVariant;
  /** Size of the button */
  size?: ButtonSize;
  /** Full width button */
  fullWidth?: boolean;
  /** Loading state */
  loading?: boolean;
  /** Left icon */
  leftIcon?: ReactNode;
  /** Right icon */
  rightIcon?: ReactNode;
  /** Button content */
  children?: ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: `
    bg-blue-600 text-white hover:bg-blue-500 
    focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900
    disabled:bg-blue-800 disabled:cursor-not-allowed
  `,
  secondary: `
    bg-slate-700 text-white hover:bg-slate-600
    focus:ring-2 focus:ring-slate-500 focus:ring-offset-2 focus:ring-offset-slate-900
    disabled:bg-slate-800 disabled:cursor-not-allowed
  `,
  outline: `
    border border-slate-600 text-slate-300 hover:bg-slate-800 hover:border-slate-500
    focus:ring-2 focus:ring-slate-500 focus:ring-offset-2 focus:ring-offset-slate-900
    disabled:opacity-50 disabled:cursor-not-allowed
  `,
  ghost: `
    text-slate-300 hover:bg-slate-800 hover:text-white
    focus:ring-2 focus:ring-slate-500 focus:ring-offset-2 focus:ring-offset-slate-900
    disabled:opacity-50 disabled:cursor-not-allowed
  `,
  danger: `
    bg-red-600 text-white hover:bg-red-500
    focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-slate-900
    disabled:bg-red-800 disabled:cursor-not-allowed
  `,
  success: `
    bg-emerald-600 text-white hover:bg-emerald-500
    focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 focus:ring-offset-slate-900
    disabled:bg-emerald-800 disabled:cursor-not-allowed
  `,
};

const sizeStyles: Record<ButtonSize, string> = {
  xs: 'px-2 py-1 text-xs gap-1',
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-5 py-2.5 text-base gap-2',
  xl: 'px-6 py-3 text-lg gap-2.5',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      fullWidth = false,
      loading = false,
      leftIcon,
      rightIcon,
      children,
      className,
      disabled,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          // Base styles
          'inline-flex items-center justify-center font-medium rounded-lg',
          'transition-all duration-200 ease-out',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
          'disabled:cursor-not-allowed disabled:transform-none',
          
          // Variant
          variantStyles[variant],
          
          // Size
          sizeStyles[size],
          
          // Full width
          fullWidth && 'w-full',
          
          // Loading state
          loading && 'opacity-80 cursor-wait',
          
          // Custom class
          className
        )}
        {...props}
      >
        {loading ? (
          <>
            <svg
              className="animate-spin h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>Loading...</span>
          </>
        ) : (
          <>
            {leftIcon && <span className="flex-shrink-0">{leftIcon}</span>}
            {children && <span>{children}</span>}
            {rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
          </>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

// Icon-only button variant
export interface IconButtonProps extends ButtonProps {
  'aria-label': string;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ size = 'md', children, className, ...props }, ref) => {
    const iconSizes: Record<ButtonSize, string> = {
      xs: 'w-6 h-6',
      sm: 'w-8 h-8',
      md: 'w-10 h-10',
      lg: 'w-12 h-12',
      xl: 'w-14 h-14',
    };

    return (
      <Button
        ref={ref}
        size={size}
        className={cn('p-0 rounded-full', iconSizes[size], className)}
        {...props}
      >
        {children}
      </Button>
    );
  }
);

IconButton.displayName = 'IconButton';

export default Button;
