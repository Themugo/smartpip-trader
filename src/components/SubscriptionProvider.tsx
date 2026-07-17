import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { supabase } from '../lib/supabase';
import { 
  SubscriptionState, 
  Plan, 
  PlanFeatures, 
  PLANS 
} from '../lib/subscription';

interface SubscriptionContextType {
  subscription: SubscriptionState;
  plan: Plan;
  isLoading: boolean;
  canAccess: (feature: keyof PlanFeatures) => boolean;
  upgradePlan: (plan: Plan) => void;
  cancelSubscription: () => void;
}

const defaultSubscription: SubscriptionState = {
  plan: 'free',
  status: 'none',
  currentPeriodEnd: null,
  trialEnd: null,
  features: PLANS.free.features,
};

const SubscriptionContext = createContext<SubscriptionContextType>({
  subscription: defaultSubscription,
  plan: 'free',
  isLoading: true,
  canAccess: () => false,
  upgradePlan: () => {},
  cancelSubscription: () => {},
});

export function useSubscription() {
  const context = useContext(SubscriptionContext);
  if (!context) {
    throw new Error('useSubscription must be used within SubscriptionProvider');
  }
  return context;
}

interface SubscriptionProviderProps {
  children: ReactNode;
}

export function SubscriptionProvider({ children }: SubscriptionProviderProps) {
  const [subscription, setSubscription] = useState<SubscriptionState>(defaultSubscription);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchSubscription();
  }, []);

  const fetchSubscription = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        setSubscription(defaultSubscription);
        setIsLoading(false);
        return;
      }

      // In production, fetch from subscriptions table
      // For now, use localStorage for demo
      const storedPlan = localStorage.getItem('subscription_plan') as Plan | null;
      const plan = storedPlan || 'free';
      
      setSubscription({
        plan,
        status: plan === 'free' ? 'none' : 'active',
        currentPeriodEnd: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        trialEnd: null,
        features: PLANS[plan].features,
      });
    } catch (error) {
      console.error('Failed to fetch subscription:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const canAccess = (feature: keyof PlanFeatures): boolean => {
    const value = subscription.features[feature];
    return typeof value === 'boolean' ? value : (value as number) > 0;
  };

  const upgradePlan = (plan: Plan) => {
    // In production, redirect to Stripe checkout
    localStorage.setItem('subscription_plan', plan);
    setSubscription({
      plan,
      status: 'active',
      currentPeriodEnd: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      trialEnd: null,
      features: PLANS[plan].features,
    });
  };

  const cancelSubscription = () => {
    localStorage.setItem('subscription_plan', 'free');
    setSubscription(defaultSubscription);
  };

  return (
    <SubscriptionContext.Provider
      value={{
        subscription,
        plan: subscription.plan,
        isLoading,
        canAccess,
        upgradePlan,
        cancelSubscription,
      }}
    >
      {children}
    </SubscriptionContext.Provider>
  );
}

// Higher Order Component for feature gating
export function withFeatureGate<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  requiredFeature: keyof PlanFeatures
) {
  return function FeatureGatedComponent(props: P) {
    const { canAccess } = useSubscription();
    
    if (!canAccess(requiredFeature)) {
      return (
        <div className="p-6 bg-slate-900 rounded-xl border border-slate-700">
          <div className="text-center">
            <div className="w-12 h-12 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Feature Locked</h3>
            <p className="text-slate-400 text-sm mb-4">
              This feature requires a higher subscription plan.
            </p>
            <a
              href="/pricing"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium text-sm transition-colors"
            >
              Upgrade Plan
            </a>
          </div>
        </div>
      );
    }
    
    return <WrappedComponent {...props} />;
  };
}
