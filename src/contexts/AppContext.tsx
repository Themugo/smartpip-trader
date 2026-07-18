/**
 * App Context
 * 
 * Centralized application state management using React Context.
 * Consolidates auth, theme, settings, and global app state.
 */

import { createContext, useContext, useReducer, useEffect, type ReactNode } from 'react';
import type { User } from '@supabase/supabase-js';

// Types
export interface AppState {
  // Auth state
  user: User | null;
  authLoading: boolean;
  
  // Theme state
  theme: 'light' | 'dark' | 'system';
  resolvedTheme: 'light' | 'dark';
  
  // Onboarding state
  hasCompletedOnboarding: boolean;
  showOnboarding: boolean;
  
  // Connection state
  hasBrokerConnection: boolean;
  connected: boolean;
  
  // UI state
  sidebarOpen: boolean;
  activeWorkspace: string;
  activeTab: string;
  
  // Error state
  error: string | null;
}

type AppAction =
  | { type: 'SET_USER'; payload: User | null }
  | { type: 'SET_AUTH_LOADING'; payload: boolean }
  | { type: 'SET_THEME'; payload: 'light' | 'dark' | 'system' }
  | { type: 'SET_RESOLVED_THEME'; payload: 'light' | 'dark' }
  | { type: 'SET_ONBOARDING_COMPLETE'; payload: boolean }
  | { type: 'SET_SHOW_ONBOARDING'; payload: boolean }
  | { type: 'SET_BROKER_CONNECTION'; payload: boolean }
  | { type: 'SET_CONNECTED'; payload: boolean }
  | { type: 'SET_SIDEBAR_OPEN'; payload: boolean }
  | { type: 'SET_ACTIVE_WORKSPACE'; payload: string }
  | { type: 'SET_ACTIVE_TAB'; payload: string }
  | { type: 'SET_ERROR'; payload: string | null };

const initialState: AppState = {
  user: null,
  authLoading: true,
  theme: 'dark',
  resolvedTheme: 'dark',
  hasCompletedOnboarding: false,
  showOnboarding: false,
  hasBrokerConnection: false,
  connected: false,
  sidebarOpen: true,
  activeWorkspace: 'dashboard',
  activeTab: 'dashboard',
  error: null,
};

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_USER':
      return { ...state, user: action.payload };
    case 'SET_AUTH_LOADING':
      return { ...state, authLoading: action.payload };
    case 'SET_THEME':
      return { ...state, theme: action.payload };
    case 'SET_RESOLVED_THEME':
      return { ...state, resolvedTheme: action.payload };
    case 'SET_ONBOARDING_COMPLETE':
      return { ...state, hasCompletedOnboarding: action.payload };
    case 'SET_SHOW_ONBOARDING':
      return { ...state, showOnboarding: action.payload };
    case 'SET_BROKER_CONNECTION':
      return { ...state, hasBrokerConnection: action.payload };
    case 'SET_CONNECTED':
      return { ...state, connected: action.payload };
    case 'SET_SIDEBAR_OPEN':
      return { ...state, sidebarOpen: action.payload };
    case 'SET_ACTIVE_WORKSPACE':
      return { ...state, activeWorkspace: action.payload };
    case 'SET_ACTIVE_TAB':
      return { ...state, activeTab: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    default:
      return state;
  }
}

// Context
interface AppContextValue extends AppState {
  dispatch: React.Dispatch<AppAction>;
  setUser: (user: User | null) => void;
  setAuthLoading: (loading: boolean) => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  setOnboardingComplete: (complete: boolean) => void;
  setShowOnboarding: (show: boolean) => void;
  setBrokerConnection: (connected: boolean) => void;
  setConnected: (connected: boolean) => void;
  toggleSidebar: () => void;
  setActiveWorkspace: (workspace: string) => void;
  setActiveTab: (tab: string) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

// Provider
export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // Resolve theme on mount and when theme changes
  useEffect(() => {
    const resolveTheme = () => {
      if (state.theme === 'system') {
        const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        dispatch({ type: 'SET_RESOLVED_THEME', payload: isDark ? 'dark' : 'light' });
      } else {
        dispatch({ type: 'SET_RESOLVED_THEME', payload: state.theme });
      }
    };

    resolveTheme();

    // Listen for system theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      if (state.theme === 'system') {
        resolveTheme();
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [state.theme]);

  // Apply theme to document
  useEffect(() => {
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(state.resolvedTheme);
    document.documentElement.setAttribute('data-theme', state.resolvedTheme);
  }, [state.resolvedTheme]);

  // Helper functions
  const setUser = (user: User | null) => dispatch({ type: 'SET_USER', payload: user });
  const setAuthLoading = (loading: boolean) => dispatch({ type: 'SET_AUTH_LOADING', payload: loading });
  const setTheme = (theme: 'light' | 'dark' | 'system') => dispatch({ type: 'SET_THEME', payload: theme });
  const setOnboardingComplete = (complete: boolean) => dispatch({ type: 'SET_ONBOARDING_COMPLETE', payload: complete });
  const setShowOnboarding = (show: boolean) => dispatch({ type: 'SET_SHOW_ONBOARDING', payload: show });
  const setBrokerConnection = (connected: boolean) => dispatch({ type: 'SET_BROKER_CONNECTION', payload: connected });
  const setConnected = (connected: boolean) => dispatch({ type: 'SET_CONNECTED', payload: connected });
  const toggleSidebar = () => dispatch({ type: 'SET_SIDEBAR_OPEN', payload: !state.sidebarOpen });
  const setActiveWorkspace = (workspace: string) => dispatch({ type: 'SET_ACTIVE_WORKSPACE', payload: workspace });
  const setActiveTab = (tab: string) => dispatch({ type: 'SET_ACTIVE_TAB', payload: tab });
  const setError = (error: string | null) => dispatch({ type: 'SET_ERROR', payload: error });
  const clearError = () => dispatch({ type: 'SET_ERROR', payload: null });

  const value: AppContextValue = {
    ...state,
    dispatch,
    setUser,
    setAuthLoading,
    setTheme,
    setOnboardingComplete,
    setShowOnboarding,
    setBrokerConnection,
    setConnected,
    toggleSidebar,
    setActiveWorkspace,
    setActiveTab,
    setError,
    clearError,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

// Hook
export function useApp(): AppContextValue {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}

// Selective hooks for specific state slices
export function useAuth() {
  const { user, authLoading, setUser, setAuthLoading } = useApp();
  return { user, authLoading, setUser, setAuthLoading };
}

export function useTheme() {
  const { theme, resolvedTheme, setTheme } = useApp();
  return { theme, resolvedTheme, setTheme };
}

export function useNavigation() {
  const { sidebarOpen, activeWorkspace, activeTab, toggleSidebar, setActiveWorkspace, setActiveTab } = useApp();
  return { sidebarOpen, activeWorkspace, activeTab, toggleSidebar, setActiveWorkspace, setActiveTab };
}

export default AppProvider;
