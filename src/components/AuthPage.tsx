import { useState, type FormEvent } from 'react';
import { BarChart3, Eye, EyeOff, Loader2, LogIn, ShieldCheck, Sparkles, TrendingUp, UserPlus } from 'lucide-react';

interface AuthPageProps {
  onSignIn: (email: string, password: string) => Promise<void>;
  onSignUp: (email: string, password: string) => Promise<void>;
  onResetPassword: (email: string) => Promise<void>;
  initialLogin?: boolean;
}

export function AuthPage({ onSignIn, onSignUp, onResetPassword, initialLogin = true }: AuthPageProps) {
  const [isLogin, setIsLogin] = useState(initialLogin);
  const [resetMode, setResetMode] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const clearFeedback = () => {
    setError(null);
    setMessage(null);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    clearFeedback();
    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail) {
      setError('Email is required.');
      return;
    }

    setLoading(true);
    try {
      if (resetMode) {
        await onResetPassword(normalizedEmail);
        setMessage('If an account exists for that email, reset instructions have been sent.');
        setResetMode(false);
        return;
      }

      if (password.length < 8) {
        setError('Use a password with at least 8 characters.');
        return;
      }

      if (isLogin) {
        await onSignIn(normalizedEmail, password);
      } else {
        if (password !== confirmPassword) {
          setError('Passwords do not match.');
          return;
        }
        await onSignUp(normalizedEmail, password);
        setMessage('Account created. Check your email if confirmation is required, then sign in.');
        setIsLogin(true);
        setPassword('');
        setConfirmPassword('');
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    clearFeedback();
    setResetMode(false);
    setIsLogin((value) => !value);
    setPassword('');
    setConfirmPassword('');
  };

  return (
    <div className="min-h-screen bg-[#050914] text-white relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_20%,rgba(239,68,68,.12),transparent_30%),radial-gradient(circle_at_86%_72%,rgba(20,184,166,.10),transparent_32%)]" />
      <div className="relative z-10 min-h-screen mx-auto max-w-6xl grid lg:grid-cols-2 items-center gap-10 px-5 py-10 lg:px-8">
        <section className="hidden lg:block">
          <div className="inline-flex items-center gap-2 rounded-full border border-teal-400/15 bg-teal-400/[0.06] px-3 py-1.5 text-[10px] uppercase tracking-[0.22em] text-teal-300">
            <Sparkles className="h-3.5 w-3.5" /> AI trading intelligence
          </div>
          <h1 className="mt-6 text-5xl xl:text-6xl font-black leading-[1.02] tracking-tight">
            Trade with intelligence.<br /><span className="text-red-500">Grow with discipline.</span>
          </h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-slate-400">
            A focused trading workspace for Deriv markets. SmartPip combines live market analysis, AI decision support, risk controls and execution in one place.
          </p>
          <div className="mt-9 grid grid-cols-3 gap-3">
            {[
              { icon: Sparkles, title: 'AI analysis', text: 'Evidence first' },
              { icon: ShieldCheck, title: 'Risk gates', text: 'Disciplined entries' },
              { icon: BarChart3, title: 'Performance', text: 'Learn from results' },
            ].map(({ icon: Icon, title, text }) => (
              <div key={title} className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4">
                <Icon className="h-5 w-5 text-teal-300" />
                <div className="mt-3 text-sm font-semibold">{title}</div>
                <div className="mt-1 text-[11px] text-slate-600">{text}</div>
              </div>
            ))}
          </div>
          <div className="mt-8 flex items-center gap-2 text-xs text-slate-500">
            <ShieldCheck className="h-4 w-4 text-teal-400" /> Your funds remain in your Deriv account.
          </div>
        </section>

        <section className="w-full max-w-md mx-auto">
          <div className="flex items-center gap-3 mb-6">
            <div className="h-11 w-11 rounded-xl bg-gradient-to-br from-red-500 to-red-700 flex items-center justify-center shadow-[0_0_28px_rgba(239,68,68,.22)]">
              <TrendingUp className="h-6 w-6" />
            </div>
            <div>
              <div className="text-2xl font-black tracking-tight">SmartPip<span className="text-red-500">Trader</span></div>
              <div className="text-[9px] uppercase tracking-[0.25em] text-slate-500">Trade smarter. Grow further.</div>
            </div>
          </div>

          <div className="rounded-3xl border border-white/[0.08] bg-[#091321]/95 p-6 sm:p-8 shadow-2xl backdrop-blur-xl">
            <div className="flex items-center gap-2 mb-2">
              <ShieldCheck className="h-4 w-4 text-teal-300" />
              <h2 className="text-xl font-bold">
                {resetMode ? 'Reset your password' : isLogin ? 'Welcome back' : 'Create your account'}
              </h2>
            </div>
            <p className="text-sm text-slate-500 mb-6">
              {resetMode
                ? 'Enter your email and we will send password reset instructions.'
                : isLogin
                  ? 'Sign in to your private SmartPip workspace.'
                  : 'Create a SmartPip workspace and complete your trading profile.'}
            </p>

            {error && <div role="alert" className="mb-4 rounded-xl border border-red-400/20 bg-red-400/[0.06] p-3 text-xs text-red-300">{error}</div>}
            {message && <div role="status" className="mb-4 rounded-xl border border-teal-400/20 bg-teal-400/[0.06] p-3 text-xs text-teal-300">{message}</div>}

            <form onSubmit={handleSubmit} className="space-y-4">
              <label className="block text-xs font-medium text-slate-400">
                Email
                <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" autoComplete="email" placeholder="you@example.com" required className="mt-1.5 w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white placeholder:text-slate-700 outline-none transition focus:border-red-500/50" />
              </label>

              {!resetMode && (
                <label className="block text-xs font-medium text-slate-400">
                  Password
                  <div className="relative mt-1.5">
                    <input value={password} onChange={(e) => setPassword(e.target.value)} type={showPassword ? 'text' : 'password'} autoComplete={isLogin ? 'current-password' : 'new-password'} placeholder="••••••••" required minLength={8} className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 pr-11 text-sm text-white placeholder:text-slate-700 outline-none focus:border-red-500/50" />
                    <button type="button" onClick={() => setShowPassword((value) => !value)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-300" aria-label={showPassword ? 'Hide password' : 'Show password'}>
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </label>
              )}

              {!resetMode && !isLogin && (
                <label className="block text-xs font-medium text-slate-400">
                  Confirm password
                  <input value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} type="password" autoComplete="new-password" placeholder="••••••••" required minLength={8} className="mt-1.5 w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white placeholder:text-slate-700 outline-none focus:border-red-500/50" />
                </label>
              )}

              <button type="submit" disabled={loading} className="w-full rounded-xl bg-red-500 hover:bg-red-400 disabled:opacity-50 py-3.5 font-bold text-sm transition flex items-center justify-center gap-2">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : resetMode ? 'Send reset link' : isLogin ? <><LogIn className="h-4 w-4" />Sign in</> : <><UserPlus className="h-4 w-4" />Create account</>}
              </button>
            </form>

            {isLogin && !resetMode && (
              <button type="button" onClick={() => { clearFeedback(); setResetMode(true); }} className="mt-4 w-full text-center text-xs text-slate-500 hover:text-white transition">Forgot your password?</button>
            )}
            <button type="button" onClick={switchMode} className="mt-3 w-full text-center text-xs text-slate-500 hover:text-white transition">
              {resetMode ? 'Back to sign in' : isLogin ? "Don't have an account? Create one" : 'Already have an account? Sign in'}
            </button>
          </div>
          <p className="mt-4 text-center text-[10px] leading-5 text-slate-700">Trading involves risk. SmartPip provides analysis and execution tools; it does not guarantee trading outcomes.</p>
        </section>
      </div>
    </div>
  );
}
