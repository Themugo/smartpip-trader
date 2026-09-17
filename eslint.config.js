import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      '@typescript-eslint/no-explicit-any': 'warn',
      // The codebase's convention for intentionally-unused parameters/vars
      // (e.g. unused callback args required by an interface, placeholder
      // destructures) is a leading underscore. Recognize that convention
      // instead of flagging every deliberate placeholder as a warning.
      '@typescript-eslint/no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
      'no-constant-condition': 'warn',
      'no-case-declarations': 'warn',
    },
  },
  {
    // The app entry point mounts React but doesn't (and shouldn't) export
    // a component — this rule doesn't apply to it. This is the standard
    // exception Vite's own React template configs carry for main.tsx.
    files: ['src/main.tsx'],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
  {
    // These files are established Context+Provider+consumer-hook modules
    // (e.g. AppProvider/useApp, ToastProvider/useToast) or general-purpose
    // shared hook/utility libraries (Accessibility, performanceOptimizations,
    // Navigation) — the co-located hook/utility exports are the intended,
    // idiomatic architecture here, not an oversight. Splitting each into
    // hook-only files would mean updating import paths in dozens of
    // consumers across the codebase for no behavioral benefit, so this is
    // a deliberate, scoped exception rather than a blanket disable.
    files: [
      'src/components/Accessibility.tsx',
      'src/components/AlertsCenter.tsx',
      'src/components/DemoDataBadge.tsx',
      'src/components/ErrorBoundary.tsx',
      'src/components/Navigation.tsx',
      'src/components/SubscriptionProvider.tsx',
      'src/components/UserWorkspaces.tsx',
      'src/contexts/AppContext.tsx',
      'src/lib/collaboration.tsx',
      'src/lib/performanceOptimizations.tsx',
      'src/ui/ErrorBoundary.tsx',
      'src/ui/Toast.tsx',
    ],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  }
);
