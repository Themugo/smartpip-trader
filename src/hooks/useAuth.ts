import { useState, useEffect, useCallback } from 'react';
import { supabase, supabaseConfigured, AUTH_TIMEOUT_MS, type User } from '../lib/supabase';

export interface OnboardingProfile {
  name: string;
  tradingGoal: string;
  experience: 'beginner' | 'intermediate' | 'advanced';
  riskTolerance: 'conservative' | 'moderate' | 'aggressive';
  preferredMarkets: string[];
}

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

    const resolveOnboarding = async (user: User | null) => {
      if (!user) return true;
      try {
        const { data, error } = await supabase
          .from('profiles')
          .select('onboarding_completed')
          .eq('id', user.id)
          .maybeSingle();
        if (!error && data) return Boolean(data.onboarding_completed);
      } catch (err) {
        console.warn('[Auth] profile lookup failed; using local onboarding state:', err);
      }
      return localStorage.getItem(`onboarding_completed:${user.id}`) === 'true';
    };

    // getSession with timeout — never hang the app
    const sessionPromise = supabase.auth.getSession()
      .then(async ({ data: { session } }) => {
        const user = session?.user ?? null;
        const onboarding = await resolveOnboarding(user);
        setState({ user, loading: false, hasCompletedOnboarding: onboarding, authError: null, isOffline: false });
        if (showLogin && !user) {
          // URL state is consumed by the UI as initial login mode.
        }
      })
      .catch((err) => {
        console.warn('[Auth] getSession failed:', err);
        setState({ user: null, loading: false, hasCompletedOnboarding: true, authError: 'Could not reach authentication service', isOffline: true });
      });

    withTimeout(sessionPromise, AUTH_TIMEOUT_MS, undefined).catch(() => {});

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      const user = session?.user ?? null;
      // Keep auth state synchronous here; the profile check happens on the next
      // render through the dedicated effect below.
      const onboarding = user ? localStorage.getItem(`onboarding_completed:${user.id}`) === 'true' : true;
      setState({ user, loading: false, hasCompletedOnboarding: onboarding, authError: null, isOffline: false });
      if (user) {
        void resolveOnboarding(user).then((completed) => {
          setState((prev) => prev.user?.id === user.id ? { ...prev, hasCompletedOnboarding: completed } : prev);
        });
      }
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

  const resetPassword = useCallback(async (email: string, redirectTo?: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: redirectTo || `${window.location.origin}/`,
    });
    if (error) throw error;
  }, []);

  const signOut = useCallback(async () => {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
    } catch (err) {
      // Network error or unreachable — clear local state anyway
      console.warn('[Auth] signOut failed, clearing local session:', err);
      localStorage.removeItem('sb-auth-token');
    } finally {
      setState({ user: null, loading: false, hasCompletedOnboarding: true, authError: null, isOffline: true });
    }
  }, []);

  const retryAuth = useCallback(() => {
    setState((prev) => ({ ...prev, loading: true, authError: null }));
    // Re-trigger the effect by remounting — simplest reliable approach
    window.location.reload();
  }, []);

  const completeOnboarding = useCallback(async (profile?: OnboardingProfile) => {
    if (state.user && supabaseConfigured) {
      const payload = {
        id: state.user.id,
        full_name: profile?.name || state.user.user_metadata?.full_name || null,
        trading_goal: profile?.tradingGoal || null,
        experience: profile?.experience || 'beginner',
        risk_tolerance: profile?.riskTolerance || 'moderate',
        preferred_markets: profile?.preferredMarkets || [],
        onboarding_completed: true,
        updated_at: new Date().toISOString(),
      };
      const { error } = await supabase.from('profiles').upsert(payload);
      if (error) throw error;
    }
    if (state.user) localStorage.setItem(`onboarding_completed:${state.user.id}`, 'true');
    setState((prev) => ({ ...prev, hasCompletedOnboarding: true }));
  }, [state.user]);

  const showLoginModal = new URLSearchParams(window.location.search).get('login') === '1';

  return {
    ...state,
    signIn,
    signUp,
    resetPassword,
    signOut,
    retryAuth,
    completeOnboarding,
    showLoginModal,
  };
}
