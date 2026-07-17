import { useState } from 'react';
import { 
  Rocket, 
  User, 
  Settings2, 
  TrendingUp, 
  Shield, 
  CheckCircle2,
  ChevronRight,
  ChevronLeft,
  Sparkles,
  Target,
  Zap,
  BarChart3
} from 'lucide-react';

interface OnboardingWizardProps {
  onComplete: () => void;
  onSkip?: () => void;
}

type Step = 'welcome' | 'profile' | 'experience' | 'preferences' | 'recommendation' | 'tour';

interface ProfileData {
  name: string;
  tradingGoal: string;
  experience: 'beginner' | 'intermediate' | 'advanced';
  riskTolerance: 'conservative' | 'moderate' | 'aggressive';
  preferredMarkets: string[];
}

const steps: { id: Step; title: string; description: string }[] = [
  { id: 'welcome', title: 'Welcome', description: 'Get started' },
  { id: 'profile', title: 'Profile', description: 'Tell us about yourself' },
  { id: 'experience', title: 'Experience', description: 'Your trading background' },
  { id: 'preferences', title: 'Preferences', description: 'Risk and goals' },
  { id: 'recommendation', title: 'Recommendation', description: 'Your starting plan' },
  { id: 'tour', title: 'Tour', description: 'Quick dashboard tour' },
];

export function OnboardingWizard({ onComplete, onSkip }: OnboardingWizardProps) {
  const [currentStep, setCurrentStep] = useState<Step>('welcome');
  const [completedSteps, setCompletedSteps] = useState<Set<Step>>(new Set());
  const [data, setData] = useState<ProfileData>({
    name: '',
    tradingGoal: '',
    experience: 'beginner',
    riskTolerance: 'moderate',
    preferredMarkets: ['volatility_indices'],
  });

  const currentIndex = steps.findIndex(s => s.id === currentStep);
  const progress = ((currentIndex + 1) / steps.length) * 100;

  const goNext = () => {
    setCompletedSteps(prev => new Set([...prev, currentStep]));
    const nextIndex = currentIndex + 1;
    if (nextIndex < steps.length) {
      setCurrentStep(steps[nextIndex].id);
    } else {
      onComplete();
    }
  };

  const goBack = () => {
    const prevIndex = currentIndex - 1;
    if (prevIndex >= 0) {
      setCurrentStep(steps[prevIndex].id);
    }
  };

  const skip = () => {
    if (onSkip) onSkip();
    else onComplete();
  };

  const renderStep = () => {
    switch (currentStep) {
      case 'welcome':
        return (
          <div className="text-center py-8">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <Rocket className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-3">
              Welcome to SmartPip!
            </h2>
            <p className="text-slate-400 max-w-md mx-auto mb-8">
              Let's set up your trading workspace. This takes about 2 minutes and helps us optimize your experience.
            </p>
            <div className="grid grid-cols-3 gap-4 max-w-lg mx-auto mb-8">
              {[
                { icon: Sparkles, label: 'AI-Powered', desc: 'Smart predictions' },
                { icon: Shield, label: 'Risk-Safe', desc: 'Protected trading' },
                { icon: TrendingUp, label: 'Automated', desc: 'Set & forget' },
              ].map((item, i) => (
                <div key={i} className="bg-slate-800/50 rounded-xl p-4">
                  <item.icon className="w-6 h-6 text-blue-400 mx-auto mb-2" />
                  <p className="font-medium text-white text-sm">{item.label}</p>
                  <p className="text-xs text-slate-500">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        );

      case 'profile':
        return (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <User className="w-12 h-12 text-blue-400 mx-auto mb-3" />
              <h2 className="text-xl font-bold text-white">Tell us about yourself</h2>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                What should we call you?
              </label>
              <input
                type="text"
                value={data.name}
                onChange={(e) => setData({ ...data, name: e.target.value })}
                placeholder="Your name"
                className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                What's your main trading goal?
              </label>
              <div className="space-y-2">
                {[
                  { id: 'income', label: 'Generate additional income', icon: BarChart3 },
                  { id: 'growth', label: 'Grow my wealth over time', icon: TrendingUp },
                  { id: 'learning', label: 'Learn trading strategies', icon: Target },
                ].map((goal) => (
                  <button
                    key={goal.id}
                    onClick={() => setData({ ...data, tradingGoal: goal.id })}
                    className={`w-full flex items-center gap-3 p-4 rounded-lg border transition-all ${
                      data.tradingGoal === goal.id
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    <goal.icon className={`w-5 h-5 ${
                      data.tradingGoal === goal.id ? 'text-blue-400' : 'text-slate-400'
                    }`} />
                    <span className={data.tradingGoal === goal.id ? 'text-white' : 'text-slate-400'}>
                      {goal.label}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        );

      case 'experience':
        return (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <Zap className="w-12 h-12 text-purple-400 mx-auto mb-3" />
              <h2 className="text-xl font-bold text-white">Your trading experience</h2>
              <p className="text-slate-400 text-sm mt-1">This helps us customize your workspace</p>
            </div>

            <div className="space-y-3">
              {[
                { id: 'beginner', label: 'New to trading', desc: 'Just getting started with trading' },
                { id: 'intermediate', label: 'Some experience', desc: 'Know the basics, still learning' },
                { id: 'advanced', label: 'Experienced trader', desc: 'Familiar with strategies and tools' },
              ].map((exp) => (
                <button
                  key={exp.id}
                  onClick={() => setData({ ...data, experience: exp.id as any })}
                  className={`w-full text-left p-4 rounded-lg border transition-all ${
                    data.experience === exp.id
                      ? 'border-purple-500 bg-purple-500/10'
                      : 'border-slate-700 hover:border-slate-600'
                  }`}
                >
                  <p className={`font-medium ${
                    data.experience === exp.id ? 'text-white' : 'text-slate-300'
                  }`}>{exp.label}</p>
                  <p className="text-sm text-slate-500">{exp.desc}</p>
                </button>
              ))}
            </div>
          </div>
        );

      case 'preferences':
        return (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <Settings2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
              <h2 className="text-xl font-bold text-white">Risk preferences</h2>
              <p className="text-slate-400 text-sm mt-1">How do you feel about risk?</p>
            </div>

            <div className="space-y-3">
              {[
                { id: 'conservative', label: 'Conservative', desc: 'Small, safe trades. Minimize losses above all.', color: 'emerald' },
                { id: 'moderate', label: 'Moderate', desc: 'Balanced approach. Some risk for better returns.', color: 'blue' },
                { id: 'aggressive', label: 'Aggressive', desc: 'Higher risk, higher potential rewards.', color: 'orange' },
              ].map((pref) => (
                <button
                  key={pref.id}
                  onClick={() => setData({ ...data, riskTolerance: pref.id as any })}
                  className={`w-full text-left p-4 rounded-lg border transition-all ${
                    data.riskTolerance === pref.id
                      ? pref.color === 'emerald' ? 'border-emerald-500 bg-emerald-500/10' :
                        pref.color === 'blue' ? 'border-blue-500 bg-blue-500/10' :
                        'border-orange-500 bg-orange-500/10'
                      : 'border-slate-700 hover:border-slate-600'
                  }`}
                >
                  <p className={`font-medium ${
                    data.riskTolerance === pref.id ? 'text-white' : 'text-slate-300'
                  }`}>{pref.label}</p>
                  <p className="text-sm text-slate-500">{pref.desc}</p>
                </button>
              ))}
            </div>
          </div>
        );

      case 'recommendation':
        const recommendedPlan = data.experience === 'beginner' ? 'paper_first' : 'balanced';
        
        return (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <Sparkles className="w-12 h-12 text-amber-400 mx-auto mb-3" />
              <h2 className="text-xl font-bold text-white">Your personalized plan</h2>
              <p className="text-slate-400 text-sm mt-1">Based on your profile</p>
            </div>

            <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 border border-slate-700">
              {recommendedPlan === 'paper_first' ? (
                <>
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-amber-500/20 rounded-lg flex items-center justify-center">
                      <Target className="w-5 h-5 text-amber-400" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">Start with Paper Trading</h3>
                      <p className="text-sm text-slate-400">Practice with virtual money first</p>
                    </div>
                  </div>
                  <ul className="space-y-2 text-sm text-slate-300">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      Learn without financial risk
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      Test AI predictions
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      Build confidence
                    </li>
                  </ul>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                      <Zap className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">Balanced Approach</h3>
                      <p className="text-sm text-slate-400">Demo + Live with risk limits</p>
                    </div>
                  </div>
                  <ul className="space-y-2 text-sm text-slate-300">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      Start with small live trades
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      AI-guided entry points
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      Automatic risk protection
                    </li>
                  </ul>
                </>
              )}
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <p className="text-sm text-slate-400">
                <strong className="text-white">Pro tip:</strong> You can always change these settings later in your profile.
              </p>
            </div>
          </div>
        );

      case 'tour':
        return (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <BarChart3 className="w-12 h-12 text-cyan-400 mx-auto mb-3" />
              <h2 className="text-xl font-bold text-white">Quick dashboard tour</h2>
              <p className="text-slate-400 text-sm mt-1">Key areas to know</p>
            </div>

            <div className="space-y-3">
              {[
                { area: 'Dashboard', desc: 'Your main view - stats, charts, trades' },
                { area: 'Settings', desc: 'Connect brokers, adjust preferences' },
                { area: 'AI Panel', desc: 'View predictions and confidence scores' },
                { area: 'Risk Center', desc: 'Monitor and control your exposure' },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-4 p-4 bg-slate-800/50 rounded-lg">
                  <div className="w-8 h-8 bg-cyan-500/20 rounded-lg flex items-center justify-center text-cyan-400 font-bold">
                    {i + 1}
                  </div>
                  <div>
                    <p className="font-medium text-white">{item.area}</p>
                    <p className="text-sm text-slate-400">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
              <p className="text-sm text-blue-300">
                You can always take this tour again from the Help menu.
              </p>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex justify-between text-xs text-slate-500 mb-2">
            <span>Step {currentIndex + 1} of {steps.length}</span>
            <span>{Math.round(progress)}% complete</span>
          </div>
          <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Step content */}
        <div className="bg-slate-900 rounded-2xl border border-slate-800 p-6">
          {renderStep()}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between mt-6">
          <button
            onClick={currentIndex > 0 ? goBack : skip}
            className="flex items-center gap-2 px-4 py-2 text-slate-400 hover:text-white transition-colors"
          >
            {currentIndex > 0 && <ChevronLeft className="w-4 h-4" />}
            {currentIndex > 0 ? 'Back' : 'Skip'}
          </button>

          <button
            onClick={goNext}
            className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors"
          >
            {currentStep === 'tour' ? (
              <>
                Start Trading
                <Rocket className="w-4 h-4" />
              </>
            ) : (
              <>
                Continue
                <ChevronRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
