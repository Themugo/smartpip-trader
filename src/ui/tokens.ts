/**
 * Design Tokens
 * 
 * Centralized design system tokens for consistent styling
 * across the entire application.
 */

export const tokens = {
  // ==========================================
  // COLORS
  // ==========================================
  colors: {
    // Primary palette
    primary: {
      50: '#eff6ff',
      100: '#dbeafe',
      200: '#bfdbfe',
      300: '#93c5fd',
      400: '#60a5fa',
      500: '#3b82f6',
      600: '#2563eb',
      700: '#1d4ed8',
      800: '#1e40af',
      900: '#1e3a8a',
    },
    // Accent (cyan)
    accent: {
      50: '#ecfeff',
      100: '#cffafe',
      200: '#a5f3fc',
      300: '#67e8f9',
      400: '#22d3ee',
      500: '#06b6d4',
      600: '#0891b2',
      700: '#0e7490',
      800: '#155e75',
      900: '#164e63',
    },
    // Success (emerald)
    success: {
      50: '#ecfdf5',
      100: '#d1fae5',
      200: '#a7f3d0',
      300: '#6ee7b7',
      400: '#34d399',
      500: '#10b981',
      600: '#059669',
      700: '#047857',
      800: '#065f46',
      900: '#064e3b',
    },
    // Warning (amber)
    warning: {
      50: '#fffbeb',
      100: '#fef3c7',
      200: '#fde68a',
      300: '#fcd34d',
      400: '#fbbf24',
      500: '#f59e0b',
      600: '#d97706',
      700: '#b45309',
      800: '#92400e',
      900: '#78350f',
    },
    // Error (red)
    error: {
      50: '#fef2f2',
      100: '#fee2e2',
      200: '#fecaca',
      300: '#fca5a5',
      400: '#f87171',
      500: '#ef4444',
      600: '#dc2626',
      700: '#b91c1c',
      800: '#991b1b',
      900: '#7f1d1d',
    },
    // Slate (neutral)
    slate: {
      50: '#f8fafc',
      100: '#f1f5f9',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#94a3b8',
      500: '#64748b',
      600: '#475569',
      700: '#334155',
      800: '#1e293b',
      900: '#0f172a',
      950: '#020617',
    },
    // Violet (secondary)
    violet: {
      50: '#f5f3ff',
      100: '#ede9fe',
      200: '#ddd6fe',
      300: '#c4b5fd',
      400: '#a78bfa',
      500: '#8b5cf6',
      600: '#7c3aed',
      700: '#6d28d9',
      800: '#5b21b6',
      900: '#4c1d95',
    },
  },

  // ==========================================
  // TYPOGRAPHY
  // ==========================================
  typography: {
    fontFamily: {
      display: "'Outfit', system-ui, sans-serif",
      mono: "'JetBrains Mono', 'Fira Code', monospace",
    },
    fontSize: {
      xs: '0.75rem',      // 12px
      sm: '0.875rem',     // 14px
      base: '1rem',       // 16px
      lg: '1.125rem',     // 18px
      xl: '1.25rem',      // 20px
      '2xl': '1.5rem',   // 24px
      '3xl': '1.875rem',  // 30px
      '4xl': '2.25rem',   // 36px
      '5xl': '3rem',      // 48px
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: 1.25,
      normal: 1.5,
      relaxed: 1.75,
    },
  },

  // ==========================================
  // SPACING
  // ==========================================
  spacing: {
    0: '0',
    px: '1px',
    0.5: '0.125rem',    // 2px
    1: '0.25rem',       // 4px
    1.5: '0.375rem',    // 6px
    2: '0.5rem',        // 8px
    2.5: '0.625rem',    // 10px
    3: '0.75rem',       // 12px
    3.5: '0.875rem',    // 14px
    4: '1rem',          // 16px
    5: '1.25rem',       // 20px
    6: '1.5rem',        // 24px
    7: '1.75rem',       // 28px
    8: '2rem',          // 32px
    9: '2.25rem',       // 36px
    10: '2.5rem',        // 40px
    12: '3rem',          // 48px
    14: '3.5rem',       // 56px
    16: '4rem',          // 64px
    20: '5rem',          // 80px
    24: '6rem',         // 96px
    32: '8rem',         // 128px
  },

  // ==========================================
  // BORDERS
  // ==========================================
  borderRadius: {
    none: '0',
    sm: '0.25rem',       // 4px
    DEFAULT: '0.375rem', // 6px
    md: '0.5rem',        // 8px
    lg: '0.75rem',       // 12px
    xl: '1rem',          // 16px
    '2xl': '1.5rem',     // 24px
    full: '9999px',
  },

  // ==========================================
  // SHADOWS
  // ==========================================
  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
    glow: '0 0 20px rgb(0 212 255 / 0.15)',
    'glow-lg': '0 0 40px rgb(0 212 255 / 0.2)',
  },

  // ==========================================
  // TRANSITIONS
  // ==========================================
  transitions: {
    duration: {
      fast: '150ms',
      DEFAULT: '200ms',
      slow: '300ms',
      slower: '500ms',
    },
    easing: {
      DEFAULT: 'cubic-bezier(0.4, 0, 0.2, 1)',
      in: 'cubic-bezier(0.4, 0, 1, 1)',
      out: 'cubic-bezier(0, 0, 0.2, 1)',
      'in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
    },
  },

  // ==========================================
  // Z-INDEX
  // ==========================================
  zIndex: {
    dropdown: 1000,
    sticky: 1020,
    fixed: 1030,
    'modal-backdrop': 1040,
    modal: 1050,
    popover: 1060,
    tooltip: 1070,
    toast: 1080,
  },
};

// Theme types
export type ThemeMode = 'light' | 'dark' | 'system';

export interface ThemeColors {
  background: string;
  surface: string;
  surfaceHover: string;
  border: string;
  borderHover: string;
  text: string;
  textSecondary: string;
  textMuted: string;
  primary: string;
  primaryHover: string;
  accent: string;
  success: string;
  warning: string;
  error: string;
}

export const lightTheme: ThemeColors = {
  background: tokens.colors.slate[50],
  surface: '#ffffff',
  surfaceHover: tokens.colors.slate[100],
  border: tokens.colors.slate[200],
  borderHover: tokens.colors.slate[300],
  text: tokens.colors.slate[900],
  textSecondary: tokens.colors.slate[700],
  textMuted: tokens.colors.slate[500],
  primary: tokens.colors.primary[600],
  primaryHover: tokens.colors.primary[700],
  accent: tokens.colors.accent[500],
  success: tokens.colors.success[600],
  warning: tokens.colors.warning[500],
  error: tokens.colors.error[500],
};

export const darkTheme: ThemeColors = {
  background: tokens.colors.slate[950],
  surface: tokens.colors.slate[900],
  surfaceHover: tokens.colors.slate[800],
  border: tokens.colors.slate[700],
  borderHover: tokens.colors.slate[600],
  text: tokens.colors.slate[100],
  textSecondary: tokens.colors.slate[300],
  textMuted: tokens.colors.slate[500],
  primary: tokens.colors.primary[400],
  primaryHover: tokens.colors.primary[300],
  accent: tokens.colors.accent[400],
  success: tokens.colors.success[400],
  warning: tokens.colors.warning[400],
  error: tokens.colors.error[400],
};

// Default dark theme for trading platform
export const defaultTheme = darkTheme;

export default tokens;
