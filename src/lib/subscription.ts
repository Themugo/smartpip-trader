// Subscription Plans Configuration
export type Plan = 'free' | 'starter' | 'professional' | 'enterprise';

export interface PlanFeatures {
  // Accounts
  maxDemoAccounts: number;
  maxLiveAccounts: number;
  
  // Trading
  autoTrading: boolean;
  paperTrading: boolean;
  liveTrading: boolean;
  
  // AI & Analytics
  basicPredictions: boolean;
  advancedPredictions: boolean;
  premiumAI: boolean;
  
  // Features
  shadowMode: boolean;
  backtesting: boolean;
  monteCarlo: boolean;
  walkForward: boolean;
  
  // Analytics
  basicAnalytics: boolean;
  fullAnalytics: boolean;
  
  // Support
  communitySupport: boolean;
  prioritySupport: boolean;
  dedicatedSupport: boolean;
  
  // Additional
  apiAccess: boolean;
  customStrategies: boolean;
  whiteLabel: boolean;
  customIntegrations: boolean;
  multiWorkspace: boolean;
}

export interface PlanConfig {
  name: string;
  price: number;
  priceId: string; // Stripe price ID
  features: PlanFeatures;
  limits: {
    maxTradesPerDay: number;
    maxStrategies: number;
    dataRetentionDays: number;
  };
}

export const PLANS: Record<Plan, PlanConfig> = {
  free: {
    name: 'Free',
    price: 0,
    priceId: 'price_free',
    features: {
      maxDemoAccounts: 1,
      maxLiveAccounts: 0,
      autoTrading: false,
      paperTrading: true,
      liveTrading: false,
      basicPredictions: true,
      advancedPredictions: false,
      premiumAI: false,
      shadowMode: false,
      backtesting: false,
      monteCarlo: false,
      walkForward: false,
      basicAnalytics: true,
      fullAnalytics: false,
      communitySupport: true,
      prioritySupport: false,
      dedicatedSupport: false,
      apiAccess: false,
      customStrategies: false,
      whiteLabel: false,
      customIntegrations: false,
      multiWorkspace: false,
    },
    limits: {
      maxTradesPerDay: 50,
      maxStrategies: 1,
      dataRetentionDays: 7,
    },
  },
  starter: {
    name: 'Starter',
    price: 19,
    priceId: 'price_starter',
    features: {
      maxDemoAccounts: 2,
      maxLiveAccounts: 1,
      autoTrading: true,
      paperTrading: true,
      liveTrading: true,
      basicPredictions: true,
      advancedPredictions: true,
      premiumAI: false,
      shadowMode: true,
      backtesting: true,
      monteCarlo: false,
      walkForward: false,
      basicAnalytics: true,
      fullAnalytics: true,
      communitySupport: true,
      prioritySupport: false,
      dedicatedSupport: false,
      apiAccess: false,
      customStrategies: false,
      whiteLabel: false,
      customIntegrations: false,
      multiWorkspace: false,
    },
    limits: {
      maxTradesPerDay: 200,
      maxStrategies: 3,
      dataRetentionDays: 30,
    },
  },
  professional: {
    name: 'Professional',
    price: 49,
    priceId: 'price_professional',
    features: {
      maxDemoAccounts: 3,
      maxLiveAccounts: 3,
      autoTrading: true,
      paperTrading: true,
      liveTrading: true,
      basicPredictions: true,
      advancedPredictions: true,
      premiumAI: true,
      shadowMode: true,
      backtesting: true,
      monteCarlo: true,
      walkForward: true,
      basicAnalytics: true,
      fullAnalytics: true,
      communitySupport: true,
      prioritySupport: true,
      dedicatedSupport: false,
      apiAccess: false,
      customStrategies: false,
      whiteLabel: false,
      customIntegrations: false,
      multiWorkspace: true,
    },
    limits: {
      maxTradesPerDay: 1000,
      maxStrategies: 10,
      dataRetentionDays: 90,
    },
  },
  enterprise: {
    name: 'Enterprise',
    price: 199,
    priceId: 'price_enterprise',
    features: {
      maxDemoAccounts: -1, // unlimited
      maxLiveAccounts: -1,
      autoTrading: true,
      paperTrading: true,
      liveTrading: true,
      basicPredictions: true,
      advancedPredictions: true,
      premiumAI: true,
      shadowMode: true,
      backtesting: true,
      monteCarlo: true,
      walkForward: true,
      basicAnalytics: true,
      fullAnalytics: true,
      communitySupport: true,
      prioritySupport: true,
      dedicatedSupport: true,
      apiAccess: true,
      customStrategies: true,
      whiteLabel: true,
      customIntegrations: true,
      multiWorkspace: true,
    },
    limits: {
      maxTradesPerDay: -1,
      maxStrategies: -1,
      dataRetentionDays: 365,
    },
  },
};

// Subscription state interface
export interface SubscriptionState {
  plan: Plan;
  status: 'active' | 'trialing' | 'past_due' | 'canceled' | 'none';
  currentPeriodEnd: string | null;
  trialEnd: string | null;
  features: PlanFeatures;
}

// Feature check hook helper
export function hasFeature(subscription: SubscriptionState | null, feature: keyof PlanFeatures): boolean {
  if (!subscription) return PLANS.free.features[feature];
  return subscription.features[feature];
}

// Check if feature is available for plan
export function isFeatureAvailable(plan: Plan, feature: keyof PlanFeatures): boolean {
  return PLANS[plan].features[feature];
}

// Get plan display name
export function getPlanDisplayName(plan: Plan): string {
  return PLANS[plan].name;
}

// Get plan price
export function getPlanPrice(plan: Plan): number {
  return PLANS[plan].price;
}
