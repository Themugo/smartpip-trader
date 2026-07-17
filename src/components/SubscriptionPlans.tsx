import { useState } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  Sparkles, 
  Zap,
  Crown,
  ArrowRight,
  CreditCard,
  Clock,
  Gauge
} from 'lucide-react';
import { useSubscription } from './SubscriptionProvider';
import { Plan, PLANS } from '../lib/subscription';

const planIcons: Record<Plan, React.ReactNode> = {
  free: <Gauge className="w-6 h-6" />,
  starter: <Zap className="w-6 h-6" />,
  professional: <Sparkles className="w-6 h-6" />,
  enterprise: <Crown className="w-6 h-6" />,
};

const planColors: Record<Plan, string> = {
  free: 'border-slate-600',
  starter: 'border-blue-500',
  professional: 'border-purple-500',
  enterprise: 'border-amber-500',
};

export function SubscriptionPlans() {
  const { subscription, plan: currentPlan, upgradePlan } = useSubscription();
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');
  const [loading, setLoading] = useState<Plan | null>(null);

  const handleUpgrade = async (plan: Plan) => {
    if (plan === currentPlan) return;
    
    setLoading(plan);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    upgradePlan(plan);
    setLoading(null);
  };

  const getPrice = (plan: Plan) => {
    const basePrice = PLANS[plan].price;
    if (billingCycle === 'yearly') {
      return Math.round(basePrice * 0.8); // 20% discount
    }
    return basePrice;
  };

  const features = [
    { key: 'maxDemoAccounts', label: 'Demo Accounts', format: (v: number) => v === -1 ? 'Unlimited' : v },
    { key: 'maxLiveAccounts', label: 'Live Accounts', format: (v: number) => v === -1 ? 'Unlimited' : v },
    { key: 'autoTrading', label: 'Auto Trading' },
    { key: 'paperTrading', label: 'Paper Trading' },
    { key: 'liveTrading', label: 'Live Trading' },
    { key: 'basicPredictions', label: 'Basic AI Predictions' },
    { key: 'advancedPredictions', label: 'Advanced Predictions' },
    { key: 'premiumAI', label: 'Premium AI Models' },
    { key: 'shadowMode', label: 'Shadow Mode' },
    { key: 'backtesting', label: 'Backtesting' },
    { key: 'monteCarlo', label: 'Monte Carlo' },
    { key: 'walkForward', label: 'Walk-Forward Analysis' },
    { key: 'fullAnalytics', label: 'Full Analytics Suite' },
    { key: 'prioritySupport', label: 'Priority Support' },
    { key: 'apiAccess', label: 'API Access' },
    { key: 'multiWorkspace', label: 'Multi-Workspace' },
  ];

  return (
    <div className="min-h-screen bg-slate-950 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-white mb-4">
            Choose Your Plan
          </h1>
          <p className="text-slate-400 max-w-2xl mx-auto">
            Start free and upgrade as you grow. All plans include our core AI trading features.
          </p>
          
          {/* Billing Toggle */}
          <div className="flex items-center justify-center gap-4 mt-8">
            <span className={`text-sm font-medium ${billingCycle === 'monthly' ? 'text-white' : 'text-slate-500'}`}>
              Monthly
            </span>
            <button
              onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'yearly' : 'monthly')}
              className={`relative w-14 h-7 rounded-full transition-colors ${
                billingCycle === 'yearly' ? 'bg-blue-600' : 'bg-slate-700'
              }`}
            >
              <div
                className={`absolute top-1 w-5 h-5 rounded-full bg-white transition-transform ${
                  billingCycle === 'yearly' ? 'left-8' : 'left-1'
                }`}
              />
            </button>
            <span className={`text-sm font-medium ${billingCycle === 'yearly' ? 'text-white' : 'text-slate-500'}`}>
              Yearly
              <span className="ml-2 text-xs text-emerald-400 font-semibold">Save 20%</span>
            </span>
          </div>
        </div>

        {/* Plans Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {(Object.keys(PLANS) as Plan[]).map((plan) => {
            const config = PLANS[plan];
            const isCurrentPlan = plan === currentPlan;
            const price = getPrice(plan);
            const isPopular = plan === 'professional';
            
            return (
              <div
                key={plan}
                className={`relative bg-slate-900 rounded-2xl border-2 ${planColors[plan]} overflow-hidden ${
                  isPopular ? 'ring-2 ring-purple-500 ring-offset-2 ring-offset-slate-950' : ''
                }`}
              >
                {/* Popular Badge */}
                {isPopular && (
                  <div className="absolute top-0 left-0 right-0 bg-gradient-to-r from-purple-600 to-blue-600 text-center py-2 text-sm font-semibold text-white">
                    Most Popular
                  </div>
                )}

                <div className={`p-6 ${isPopular ? 'pt-12' : ''}`}>
                  {/* Plan Header */}
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      isPopular ? 'bg-purple-500/20 text-purple-400' :
                      plan === 'enterprise' ? 'bg-amber-500/20 text-amber-400' :
                      plan === 'starter' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-slate-700 text-slate-400'
                    }`}>
                      {planIcons[plan]}
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">{config.name}</h3>
                      <p className="text-sm text-slate-500">
                        {plan === 'free' ? 'Get started' : `$${price}/mo`}
                      </p>
                    </div>
                  </div>

                  {/* Price */}
                  {plan !== 'free' && (
                    <div className="mb-6">
                      <span className="text-4xl font-bold text-white">${price}</span>
                      <span className="text-slate-500">/month</span>
                      {billingCycle === 'yearly' && (
                        <p className="text-sm text-emerald-400 mt-1">
                          Billed ${price * 12}/year
                        </p>
                      )}
                    </div>
                  )}

                  {/* CTA Button */}
                  <button
                    onClick={() => handleUpgrade(plan)}
                    disabled={isCurrentPlan || loading !== null}
                    className={`w-full py-3 rounded-lg font-medium transition-all mb-6 flex items-center justify-center gap-2 ${
                      isCurrentPlan
                        ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                        : isPopular
                        ? 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white'
                        : 'bg-slate-800 hover:bg-slate-700 text-white'
                    }`}
                  >
                    {loading === plan ? (
                      <div className="w-5 h-5 border-2 border-t-transparent border-white rounded-full animate-spin" />
                    ) : isCurrentPlan ? (
                      'Current Plan'
                    ) : (
                      <>
                        {plan === 'free' ? 'Downgrade' : 'Upgrade'}
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>

                  {/* Features */}
                  <ul className="space-y-3">
                    {features.map((feature) => {
                      const value = config.features[feature.key];
                      const formattedValue = feature.format ? feature.format(value) : null;
                      
                      return (
                        <li key={feature.key} className="flex items-center gap-3">
                          {value ? (
                            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                          ) : (
                            <XCircle className="w-5 h-5 text-slate-600 flex-shrink-0" />
                          )}
                          <span className={`text-sm ${value ? 'text-slate-300' : 'text-slate-600'}`}>
                            {feature.label}
                            {formattedValue && (
                              <span className="text-slate-500 ml-1">({formattedValue})</span>
                            )}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              </div>
            );
          })}
        </div>

        {/* Current Plan Info */}
        {subscription.status !== 'none' && (
          <div className="mt-12 bg-slate-900 rounded-xl p-6 border border-slate-800">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center">
                  <CreditCard className="w-6 h-6 text-purple-400" />
                </div>
                <div>
                  <p className="text-sm text-slate-400">Current Plan</p>
                  <p className="text-xl font-semibold text-white">
                    {PLANS[currentPlan].name}
                    {subscription.status === 'trialing' && (
                      <span className="ml-2 text-sm text-amber-400">
                        (Trial)
                      </span>
                    )}
                  </p>
                </div>
              </div>
              <div className="text-right">
                {subscription.currentPeriodEnd && (
                  <p className="text-sm text-slate-400 flex items-center gap-1 justify-end">
                    <Clock className="w-4 h-4" />
                    Renews {new Date(subscription.currentPeriodEnd).toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* FAQ */}
        <div className="mt-16">
          <h2 className="text-2xl font-bold text-white text-center mb-8">
            Frequently Asked Questions
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {[
              {
                q: 'Can I change plans anytime?',
                a: 'Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately.',
              },
              {
                q: 'What payment methods do you accept?',
                a: 'We accept all major credit cards through our secure Stripe payment processing.',
              },
              {
                q: 'Is there a free trial?',
                a: 'Yes! The Professional plan includes a 14-day free trial. No credit card required.',
              },
              {
                q: 'Can I cancel anytime?',
                a: 'Absolutely. Cancel anytime and you will retain access until the end of your billing period.',
              },
            ].map((faq, i) => (
              <div key={i} className="bg-slate-900 rounded-xl p-6 border border-slate-800">
                <h3 className="font-semibold text-white mb-2">{faq.q}</h3>
                <p className="text-slate-400 text-sm">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
