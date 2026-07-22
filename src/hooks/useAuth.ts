import { useState, useEffect, useCallback } from 'react';
import { supabase, supabaseConfigured, AUTH_TIMEOUT_MS, type User } from '../lib/supabase';

export interface AuthState {
  user: User | null;
  loading: boolean;
  hasCompletedOnboarding: boolean;
  authError: string | null;
  isOffline: boolean;
}

function withTimeout<T>(promise: Promise<T>, ms: number, fallback: T): Promise<T> {
  let timer: ReturnType<typeof setTimeout>;
  return Promise.race([
    promise,
    new Promise<T>((resolve) => {
      timer = setTimeout(() => resolve(fallback), ms);
    }),
  ]).finally(() => clearTimeout(timer));
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    hasCompletedOnboarding: false,
    authError: null,
    isOffline: false,
  });

  useEffect(() => {
    if (!supabaseConfigured) {
      setState({ user: null, loading: false, hasCompletedOnboarding: true, authError: null, isOffline: true });
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const showLogin = params.get('login') === '1';

    // getSession with timeout — never hang the app
    const sessionPromise = supabase.auth.getSession()
      .then(({ data: { session } }) => {
        const user = session?.user ?? null;
        const onboarding = user ? !!localStorage.getItem('onboarding_completed') : true;
        setState({ user, loading: false, hasCompletedOnboarding: onboarding, authError: null, isOffline: false });
        if (showLogin && !user) {
          // Signal to parent that auth modal should open — handled via URL param
        }
      })
      .catch((err) => {
        console.warn('[Auth] getSession failed:', err);
        setState({ user: null, loading: false, hasCompletedOnboarding: true, authError: 'Could not reach authentication service', isOffline: true });
      });

    withTimeout(sessionPromise, AUTH_TIMEOUT_MS, undefined).catch(() => {});

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      const user = session?.user ?? null;
      const onboarding = user ? !!localStorage.getItem('onboarding_completed') : true;
      setState({ user, loading: false, hasCompletedOnboarding: onboarding, authError: null, isOffline: false });
    });

    return () => subscription.unsubscribe();
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
    return data;
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
    return data;
  }, []);

  const signOut = useCallback(async () => {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
    } catch (err) {
      // Network error or unreachable — clear local state anyway
      console.warn('[Auth] signOut failed, clearing local session:', err);
      localStorage.removeItem('sb-auth-token');
      localStorage.removeItem('onboarding_completed');
    } finally {
      setState({ user: null, loading: false, hasCompletedOnboarding: true, authError: null, isOffline: true });
    }
  }, []);

  const retryAuth = useCallback(() => {
    setState((prev) => ({ ...prev, loading: true, authError: null }));
    // Re-trigger the effect by remounting — simplest reliable approach
    window.location.reload();
  }, []);

  const completeOnboarding = useCallback(() => {
    localStorage.setItem('onboarding_completed', 'true');
    setState((prev) => ({ ...prev, hasCompletedOnboarding: true }));
  }, []);

  const showLoginModal = new URLSearchParams(window.location.search).get('login') === '1';

  return {
    ...state,
    signIn,
    signUp,
    signOut,
    retryAuth,
    completeOnboarding,
    showLoginModal,
  };
}
