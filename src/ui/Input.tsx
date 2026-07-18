/**
 * Input Component
 * 
 * Standardized input component with label, error state,
 * and various sizes.
 */

import { forwardRef, type InputHTMLAttributes, type ReactNode } from 'react';
import { cn } from './utils';

export type InputSize = 'sm' | 'md' | 'lg';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  /** Input label */
  label?: string;
  /** Helper text below input */
  helperText?: string;
  /** Error message */
  error?: string;
  /** Success message */
  success?: string;
  /** Left icon */
  leftIcon?: ReactNode;
  /** Right icon */
  rightIcon?: ReactNode;
  /** Size variant */
  size?: InputSize;
  /** Full width */
  fullWidth?: boolean;
}

const sizeStyles: Record<InputSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2.5 text-sm',
  lg: 'px-4 py-3 text-base',
};

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      helperText,
      error,
      success,
      leftIcon,
      rightIcon,
      size = 'md',
      fullWidth = false,
      className,
      disabled,
      id,
      ...props
    },
    ref
  ) => {
    const inputId = id || `input-${Math.random().toString(36).substring(7)}`;
    const hasError = !!error;
    const hasSuccess = !!success;

    return (
      <div className={cn('flex flex-col gap-1.5', fullWidth && 'w-full')}>
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-medium text-slate-300"
          >
            {label}
          </label>
        )}
        
        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
              {leftIcon}
            </div>
          )}
          
          <input
            ref={ref}
            id={inputId}
            disabled={disabled}
            className={cn(
              // Base styles
              'w-full bg-slate-800 border rounded-lg text-white placeholder-slate-500',
              'transition-colors duration-200',
              'focus:outline-none focus:ring-2 focus:ring-offset-0',
              
              // Size
              sizeStyles[size],
              
              // Icon padding
              leftIcon ? 'pl-10' : '',
              rightIcon ? 'pr-10' : '',
              
              // States
              hasError ? 'border-red-500 focus:ring-red-500/50 focus:border-red-500' : '',
              hasSuccess ? 'border-emerald-500 focus:ring-emerald-500/50 focus:border-emerald-500' : '',
              !hasError && !hasSuccess ? 'border-slate-700 focus:ring-blue-500/50 focus:border-blue-500' : '',
              
              disabled ? 'opacity-50 cursor-not-allowed' : '',
              
              className
            )}
            aria-invalid={hasError}
            aria-describedby={
              error ? `${inputId}-error` : 
              helperText ? `${inputId}-helper` : 
              undefined
            }
            {...props}
          />
          
          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
              {rightIcon}
            </div>
          )}
        </div>
        
        {(error || helperText || success) && (
          <p
            id={error ? `${inputId}-error` : `${inputId}-helper`}
            className={cn(
              'text-xs',
              hasError && 'text-red-400',
              hasSuccess && 'text-emerald-400',
              !hasError && !hasSuccess && 'text-slate-400'
            )}
          >
            {error || helperText || success}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

// Textarea variant
export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  helperText?: string;
  error?: string;
  fullWidth?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, helperText, error, fullWidth = false, className, id, ...props }, ref) => {
    const textareaId = id || `textarea-${Math.random().toString(36).substring(7)}`;
    
    return (
      <div className={cn('flex flex-col gap-1.5', fullWidth && 'w-full')}>
        {label && (
          <label
            htmlFor={textareaId}
            className="text-sm font-medium text-slate-300"
          >
            {label}
          </label>
        )}
        
        <textarea
          ref={ref}
          id={textareaId}
          className={cn(
            'w-full px-4 py-2.5 bg-slate-800 border rounded-lg text-white placeholder-slate-500',
            'text-sm transition-colors duration-200',
            'focus:outline-none focus:ring-2 focus:ring-offset-0 focus:ring-blue-500/50',
            error 
              ? 'border-red-500 focus:border-red-500' 
              : 'border-slate-700 focus:border-blue-500',
            className
          )}
          aria-invalid={!!error}
          aria-describedby={error ? `${textareaId}-error` : helperText ? `${textareaId}-helper` : undefined}
          {...props}
        />
        
        {(error || helperText) && (
          <p
            id={error ? `${textareaId}-error` : `${textareaId}-helper`}
            className={cn('text-xs', error ? 'text-red-400' : 'text-slate-400')}
          >
            {error || helperText}
          </p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

// Select variant
export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  helperText?: string;
  error?: string;
  options: { value: string; label: string; disabled?: boolean }[];
  fullWidth?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, helperText, error, options, fullWidth = false, className, id, ...props }, ref) => {
    const selectId = id || `select-${Math.random().toString(36).substring(7)}`;
    
    return (
      <div className={cn('flex flex-col gap-1.5', fullWidth && 'w-full')}>
        {label && (
          <label
            htmlFor={selectId}
            className="text-sm font-medium text-slate-300"
          >
            {label}
          </label>
        )}
        
        <select
          ref={ref}
          id={selectId}
          className={cn(
            'w-full px-4 py-2.5 bg-slate-800 border rounded-lg text-white',
            'text-sm transition-colors duration-200 cursor-pointer',
            'focus:outline-none focus:ring-2 focus:ring-offset-0 focus:ring-blue-500/50',
            error 
              ? 'border-red-500 focus:border-red-500' 
              : 'border-slate-700 focus:border-blue-500',
            className
          )}
          aria-invalid={!!error}
          {...props}
        >
          {options.map((option) => (
            <option
              key={option.value}
              value={option.value}
              disabled={option.disabled}
            >
              {option.label}
            </option>
          ))}
        </select>
        
        {(error || helperText) && (
          <p
            className={cn('text-xs', error ? 'text-red-400' : 'text-slate-400')}
          >
            {error || helperText}
          </p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';

// Checkbox variant
export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string;
  description?: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, description, className, id, ...props }, ref) => {
    const checkboxId = id || `checkbox-${Math.random().toString(36).substring(7)}`;
    
    return (
      <div className="flex items-start gap-3">
        <input
          ref={ref}
          type="checkbox"
          id={checkboxId}
          className={cn(
            'mt-1 w-4 h-4 rounded border-slate-600 bg-slate-800',
            'text-blue-600 focus:ring-2 focus:ring-blue-500/50 focus:ring-offset-0',
            'cursor-pointer',
            className
          )}
          {...props}
        />
        <div className="flex flex-col">
          <label htmlFor={checkboxId} className="text-sm font-medium text-white cursor-pointer">
            {label}
          </label>
          {description && (
            <p className="text-xs text-slate-400">{description}</p>
          )}
        </div>
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';

// Switch variant
export interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string;
  description?: string;
}

export const Switch = forwardRef<HTMLInputElement, SwitchProps>(
  ({ label, description, className, id, ...props }, ref) => {
    const switchId = id || `switch-${Math.random().toString(36).substring(7)}`;
    
    return (
      <div className="flex items-start gap-3">
        <div className="relative">
          <input
            ref={ref}
            type="checkbox"
            role="switch"
            id={switchId}
            className={cn(
              'peer appearance-none w-11 h-6 rounded-full bg-slate-700',
              'checked:bg-blue-600 checked:bg-blue-500',
              'focus:outline-none focus:ring-2 focus:ring-blue-500/50',
              'cursor-pointer transition-colors duration-200',
              className
            )}
            {...props}
          />
          <div className="absolute left-0.5 top-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform duration-200 peer-checked:translate-x-5" />
        </div>
        <div className="flex flex-col">
          <label htmlFor={switchId} className="text-sm font-medium text-white cursor-pointer">
            {label}
          </label>
          {description && (
            <p className="text-xs text-slate-400">{description}</p>
          )}
        </div>
      </div>
    );
  }
);

Switch.displayName = 'Switch';

export default Input;
