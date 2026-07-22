import { useState, useEffect, useCallback } from 'react';
import { supabase, supabaseConfigured, type User } from '../lib/supabase';

export interface AuthState {
  user: User | null;
  loading: boolean;
  hasCompletedOnboarding: boolean;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    hasCompletedOnboarding: false,
  });

  useEffect(() => {
    if (!supabaseConfigured) {
      setState({ user: null, loading: false, hasCompletedOnboarding: true });
      return;
    }

    // Check URL for login=1 param
    const params = new URLSearchParams(window.location.search);
    const showLogin = params.get('login') === '1';

    supabase.auth.getSession().then(({ data: { session } }) => {
      const user = session?.user ?? null;
      const onboarding = user
        ? !!localStorage.getItem('onboarding_completed')
        : true;
      setState({ user, loading: false, hasCompletedOnboarding: onboarding });

      if (showLogin && !user) {
        // Signal to parent that auth modal should open — handled via URL param
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      const user = session?.user ?? null;
      const onboarding = user
        ? !!localStorage.getItem('onboarding_completed')
        : true;
      setState({ user, loading: false, hasCompletedOnboarding: onboarding });
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
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
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
    completeOnboarding,
    showLoginModal,
  };
}
