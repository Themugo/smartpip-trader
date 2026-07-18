/**
 * Accessibility Utilities
 * 
 * WCAG 2.1 AA compliance utilities including:
 * - Skip links
 * - ARIA helpers
 * - Focus management
 * - Screen reader announcements
 */

import { useEffect, useRef, useCallback, type ReactNode } from 'react';

// ============================================================================
// SKIP LINKS
// ============================================================================

export interface SkipLink {
  id: string;
  label: string;
  target: string;
}

export interface SkipLinksProps {
  links: SkipLink[];
  className?: string;
}

/**
 * Skip Links Component
 * Provides navigation shortcuts for keyboard users
 */
export function SkipLinks({ links, className = '' }: SkipLinksProps) {
  return (
    <div 
      className={`skip-links sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] ${className}`}
      role="navigation"
      aria-label="Skip navigation"
    >
      {links.map((link) => (
        <a
          key={link.id}
          href={link.target}
          className="block px-4 py-2 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2"
          onClick={(e) => {
            e.preventDefault();
            const target = document.querySelector(link.target);
            if (target) {
              target.scrollIntoView({ behavior: 'smooth' });
              (target as HTMLElement).focus();
            }
          }}
        >
          {link.label}
        </a>
      ))}
    </div>
  );
}

/**
 * Default skip links for SmartPip
 */
export const defaultSkipLinks: SkipLink[] = [
  { id: 'skip-main', label: 'Skip to main content', target: '#main-content' },
  { id: 'skip-nav', label: 'Skip to navigation', target: '#main-navigation' },
  { id: 'skip-trades', label: 'Skip to trades', target: '#trades-section' },
  { id: 'skip-footer', label: 'Skip to footer', target: '#main-footer' },
];

// ============================================================================
// LIVE REGIONS (Screen Reader Announcements)
// ============================================================================

export interface LiveRegionProps {
  politeness?: 'polite' | 'assertive' | 'off';
  children: ReactNode;
}

/**
 * Live Region for screen reader announcements
 * Uses aria-live to announce dynamic content changes
 */
export function LiveRegion({ politeness = 'polite', children }: LiveRegionProps) {
  return (
    <div
      role="status"
      aria-live={politeness}
      aria-atomic="true"
      className="sr-only"
    >
      {children}
    </div>
  );
}

// ============================================================================
// FOCUS MANAGEMENT
// ============================================================================

/**
 * Focus trap hook for modals and dialogs
 */
export function useFocusTrap(isActive: boolean) {
  const containerRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isActive) return;

    // Store previously focused element
    previousActiveElement.current = document.activeElement as HTMLElement;

    const container = containerRef.current;
    if (!container) return;

    // Get all focusable elements
    const focusableElements = container.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Focus first element
    firstElement?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    container.addEventListener('keydown', handleKeyDown);

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
      // Restore focus
      previousActiveElement.current?.focus();
    };
  }, [isActive]);

  return containerRef;
}

/**
 * Return focus to trigger when dialog closes
 */
export function useRestoreFocus(triggerRef: React.RefObject<HTMLElement | null>) {
  const previousActiveElement = useRef<HTMLElement | null>(null);

  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement;
    
    return () => {
      // Delay to ensure trigger is available
      setTimeout(() => {
        triggerRef.current?.focus();
      }, 0);
    };
  }, [triggerRef]);
}

// ============================================================================
// ARIA HELPERS
// ============================================================================

/**
 * Generate unique ID for ARIA attributes
 */
let idCounter = 0;
export function useUniqueId(prefix = 'aria'): string {
  const idRef = useRef<string>('');

  if (!idRef.current) {
    idRef.current = `${prefix}-${++idCounter}`;
  }

  return idRef.current;
}

/**
 * Get accessible label for form element
 */
export function getAccessibleLabel(
  label: string,
  id: string,
  describedBy?: string
): { 'aria-label'?: string; 'aria-labelledby'?: string; 'aria-describedby'?: string } {
  if (label) {
    return {
      'aria-labelledby': id,
      'aria-describedby': describedBy,
    };
  }
  return {
    'aria-label': label,
  };
}

/**
 * Get loading announcement text
 */
export function getLoadingAnnouncement(isLoading: boolean, itemType: string): string {
  if (isLoading) {
    return `Loading ${itemType}`;
  }
  return '';
}

/**
 * Get error announcement text
 */
export function getErrorAnnouncement(error: string | null): string {
  if (error) {
    return `Error: ${error}`;
  }
  return '';
}

// ============================================================================
// KEYBOARD NAVIGATION
// ============================================================================

export interface KeyboardShortcut {
  key: string;
  modifiers?: ('ctrl' | 'alt' | 'shift' | 'meta')[];
  description: string;
  action: () => void;
}

/**
 * Global keyboard shortcut handler
 */
export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const modifiersMatch = shortcut.modifiers?.every((mod) => {
          switch (mod) {
            case 'ctrl':
              return e.ctrlKey;
            case 'alt':
              return e.altKey;
            case 'shift':
              return e.shiftKey;
            case 'meta':
              return e.metaKey;
            default:
              return false;
          }
        }) ?? true;

        if (e.key.toLowerCase() === shortcut.key.toLowerCase() && modifiersMatch) {
          e.preventDefault();
          shortcut.action();
          break;
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}

/**
 * Roving tabindex for grid navigation
 */
export function useRovingTabIndex(
  items: unknown[],
  orientation: 'horizontal' | 'vertical' | 'both' = 'vertical'
) {
  const [focusedIndex, setFocusedIndex] = useState(0);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, currentIndex: number) => {
      let newIndex = currentIndex;

      switch (e.key) {
        case 'ArrowUp':
          if (orientation === 'vertical' || orientation === 'both') {
            e.preventDefault();
            newIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
          }
          break;
        case 'ArrowDown':
          if (orientation === 'vertical' || orientation === 'both') {
            e.preventDefault();
            newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
          }
          break;
        case 'ArrowLeft':
          if (orientation === 'horizontal' || orientation === 'both') {
            e.preventDefault();
            newIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
          }
          break;
        case 'ArrowRight':
          if (orientation === 'horizontal' || orientation === 'both') {
            e.preventDefault();
            newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
          }
          break;
        case 'Home':
          e.preventDefault();
          newIndex = 0;
          break;
        case 'End':
          e.preventDefault();
          newIndex = items.length - 1;
          break;
      }

      if (newIndex !== currentIndex) {
        setFocusedIndex(newIndex);
      }
    },
    [items.length, orientation]
  );

  return { focusedIndex, setFocusedIndex, handleKeyDown };
}

import { useState } from 'react';

// ============================================================================
// VISUALLY HIDDEN (Screen Reader Only)
// ============================================================================

export interface VisuallyHiddenProps {
  children: ReactNode;
  className?: string;
}

/**
 * Visually hidden but accessible to screen readers
 */
export function VisuallyHidden({ children, className = '' }: VisuallyHiddenProps) {
  return (
    <span
      className={`sr-only ${className}`}
      style={{
        position: 'absolute',
        width: '1px',
        height: '1px',
        padding: '0',
        margin: '-1px',
        overflow: 'hidden',
        clip: 'rect(0, 0, 0, 0)',
        whiteSpace: 'nowrap',
        border: '0',
      }}
    >
      {children}
    </span>
  );
}

// ============================================================================
// EXPORTS
// ============================================================================

export default {
  SkipLinks,
  defaultSkipLinks,
  LiveRegion,
  useFocusTrap,
  useRestoreFocus,
  useUniqueId,
  useKeyboardShortcuts,
  useRovingTabIndex,
  VisuallyHidden,
  getAccessibleLabel,
  getLoadingAnnouncement,
  getErrorAnnouncement,
};
