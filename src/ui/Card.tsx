/**
 * Card Component
 * 
 * Standardized card component with multiple variants
 * for displaying content.
 */

import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import { cn } from './utils';

export type CardVariant = 'default' | 'elevated' | 'outline' | 'gradient';
export type CardPadding = 'none' | 'sm' | 'md' | 'lg' | 'xl';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Visual style variant */
  variant?: CardVariant;
  /** Padding size */
  padding?: CardPadding;
  /** Interactive card (clickable) */
  interactive?: boolean;
  /** Card header content */
  header?: ReactNode;
  /** Card footer content */
  footer?: ReactNode;
  /** Children content */
  children?: ReactNode;
}

const variantStyles: Record<CardVariant, string> = {
  default: 'bg-slate-900 border border-slate-800',
  elevated: 'bg-slate-900 border border-slate-700 shadow-lg',
  outline: 'bg-transparent border border-slate-700',
  gradient: 'bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700',
};

const paddingStyles: Record<CardPadding, string> = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
  xl: 'p-8',
};

export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      variant = 'default',
      padding = 'md',
      interactive = false,
      header,
      footer,
      children,
      className,
      ...props
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={cn(
          'rounded-xl',
          variantStyles[variant],
          paddingStyles[padding],
          interactive && 'cursor-pointer transition-all duration-200 hover:border-slate-600 hover:shadow-lg hover:scale-[1.01]',
          className
        )}
        {...props}
      >
        {header && (
          <div className="border-b border-slate-800 px-4 py-3">
            {header}
          </div>
        )}
        <div className={!header && padding !== 'none' ? paddingStyles[padding] : ''}>
          {children}
        </div>
        {footer && (
          <div className="border-t border-slate-800 px-4 py-3">
            {footer}
          </div>
        )}
      </div>
    );
  }
);

Card.displayName = 'Card';

// Card sub-components
export interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
}

export function CardHeader({
  title,
  subtitle,
  action,
  className,
  children,
  ...props
}: CardHeaderProps) {
  return (
    <div className={cn('flex items-center justify-between', className)} {...props}>
      <div>
        {title && <h3 className="text-lg font-semibold text-white">{title}</h3>}
        {subtitle && <p className="text-sm text-slate-400 mt-0.5">{subtitle}</p>}
        {children}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

export interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
}

export function CardTitle({ as: Component = 'h3', className, children, ...props }: CardTitleProps) {
  return (
    <Component className={cn('text-lg font-semibold text-white', className)} {...props}>
      {children}
    </Component>
  );
}

export interface CardDescriptionProps extends HTMLAttributes<HTMLParagraphElement> {}

export function CardDescription({ className, children, ...props }: CardDescriptionProps) {
  return (
    <p className={cn('text-sm text-slate-400', className)} {...props}>
      {children}
    </p>
  );
}

export interface CardContentProps extends HTMLAttributes<HTMLDivElement> {}

export function CardContent({ className, children, ...props }: CardContentProps) {
  return (
    <div className={cn('', className)} {...props}>
      {children}
    </div>
  );
}

export interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {}

export function CardFooter({ className, children, ...props }: CardFooterProps) {
  return (
    <div className={cn('flex items-center gap-3', className)} {...props}>
      {children}
    </div>
  );
}

export default Card;
