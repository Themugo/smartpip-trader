import { useState, type ReactNode } from 'react';
import {
  Activity,
  BarChart3,
  BookOpen,
  BrainCircuit,
  ChevronDown,
  LogOut,
  Menu,
  Settings,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Wallet,
  X,
  Zap,
} from 'lucide-react';
import type { User } from '../lib/supabase';

export type EndUserView = 'trade' | 'ai' | 'auto' | 'performance' | 'journal' | 'settings';

interface EndUserShellProps {
  user: User;
  view: EndUserView;
  onViewChange: (view: EndUserView) => void;
  onSignOut: () => void;
  connected: boolean;
  children: ReactNode;
}

const nav: Array<{ id: EndUserView; label: string; icon: typeof Activity }> = [
  { id: 'trade', label: 'Trade', icon: Activity },
  { id: 'ai', label: 'AI Analysis', icon: BrainCircuit },
  { id: 'auto', label: 'Auto Execution', icon: Zap },
  { id: 'performance', label: 'Performance', icon: BarChart3 },
  { id: 'journal', label: 'Trade Journal', icon: BookOpen },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function EndUserShell({ user, view, onViewChange, onSignOut, connected, children }: EndUserShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const initials = (user.user_metadata?.full_name || user.email || 'SP')
    .split(/\s+/)
    .map((part: string) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  const handleView = (next: EndUserView) => {
    onViewChange(next);
    setMobileOpen(false);
  };

  return (
    <div className="min-h-screen bg-[#050914] text-white overflow-x-hidden">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_70%_10%,rgba(0,208,190,0.08),transparent_28%),radial-gradient(circle_at_10%_90%,rgba(230,45,55,0.07),transparent_25%)]" />

      <header className="fixed inset-x-0 top-0 z-50 h-[72px] border-b border-white/[0.07] bg-[#07101d]/90 backdrop-blur-xl">
        <div className="h-full flex items-center px-4 lg:px-6 gap-4">
          <button className="lg:hidden rounded-xl border border-white/10 p-2 text-slate-300" onClick={() => setMobileOpen(true)} aria-label="Open menu">
            <Menu className="h-5 w-5" />
          </button>
          <button className="flex items-center gap-2.5 min-w-[190px]" onClick={() => handleView('trade')} aria-label="SmartPip home">
            <div className="relative h-9 w-9 rounded-xl bg-gradient-to-br from-red-500 to-red-700 flex items-center justify-center shadow-[0_0_24px_rgba(239,68,68,0.25)]">
              <TrendingUp className="h-5 w-5" />
            </div>
            <div className="text-left leading-none">
              <div className="text-lg font-black tracking-tight">SmartPip<span className="text-red-500">Trader</span></div>
              <div className="mt-1 text-[9px] uppercase tracking-[0.28em] text-slate-500">Trade smarter. Grow further.</div>
            </div>
          </button>

          <div className="hidden xl:flex flex-1 max-w-xl mx-auto h-10 rounded-xl border border-white/10 bg-white/[0.03] items-center px-3 text-sm text-slate-500">
            <Sparkles className="h-4 w-4 mr-2 text-teal-400" />
            AI market intelligence is monitoring live conditions
          </div>

          <div className="ml-auto flex items-center gap-2.5">
            <div className="hidden sm:flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-xs">
              <span className={`h-2 w-2 rounded-full ${connected ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,.7)]' : 'bg-amber-400'}`} />
              <span className="text-slate-300">{connected ? 'Market live' : 'Connecting'}</span>
            </div>
            <button className="hidden sm:flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 hover:bg-white/[0.06]" title="Account">
              <span className="h-7 w-7 rounded-full bg-slate-800 flex items-center justify-center text-[11px] font-bold text-slate-200">{initials}</span>
              <span className="max-w-[130px] truncate text-xs text-slate-300">{user.email}</span>
              <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
            </button>
            <button onClick={onSignOut} className="rounded-xl border border-white/10 p-2 text-slate-400 hover:text-white hover:bg-white/[0.05]" title="Sign out" aria-label="Sign out">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      <aside className="fixed left-0 top-[72px] bottom-0 z-40 hidden lg:flex w-[228px] flex-col border-r border-white/[0.07] bg-[#060c16]/90 backdrop-blur-xl">
        <nav className="p-3 space-y-1">
          {nav.map(({ id, label, icon: Icon }) => {
            const active = view === id;
            return (
              <button key={id} onClick={() => handleView(id)} className={`group w-full flex items-center gap-3 rounded-xl px-3.5 py-3 text-sm transition-all ${active ? 'bg-gradient-to-r from-red-600/25 to-red-500/5 text-white border border-red-500/20 shadow-[inset_3px_0_0_#ef4444]' : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'}`}>
                <Icon className={`h-[18px] w-[18px] ${active ? 'text-red-400' : 'text-slate-500 group-hover:text-slate-300'}`} />
                <span>{label}</span>
                {id === 'ai' && <span className="ml-auto rounded-full bg-teal-500/10 px-1.5 py-0.5 text-[9px] font-bold text-teal-300">LIVE</span>}
              </button>
            );
          })}
        </nav>

        <div className="mt-auto p-3 space-y-3">
          <div className="rounded-2xl border border-teal-400/10 bg-gradient-to-br from-teal-500/[0.08] to-transparent p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-200"><ShieldCheck className="h-4 w-4 text-teal-400" /> Capital discipline</div>
            <p className="mt-2 text-[11px] leading-5 text-slate-500">SmartPip can skip weak setups. No trade is better than an unqualified trade.</p>
          </div>
          <div className="flex items-center gap-2 px-2 text-[10px] text-slate-600"><Wallet className="h-3.5 w-3.5" /> Your funds remain with Deriv.</div>
        </div>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-[60] lg:hidden">
          <button className="absolute inset-0 bg-black/70" onClick={() => setMobileOpen(false)} aria-label="Close menu overlay" />
          <div className="absolute left-0 top-0 bottom-0 w-[290px] bg-[#07101d] border-r border-white/10 p-4 shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <div className="font-black text-lg">SmartPip<span className="text-red-500">Trader</span></div>
              <button onClick={() => setMobileOpen(false)} aria-label="Close menu"><X className="h-5 w-5 text-slate-400" /></button>
            </div>
            <nav className="space-y-1">
              {nav.map(({ id, label, icon: Icon }) => (
                <button key={id} onClick={() => handleView(id)} className={`w-full flex items-center gap-3 rounded-xl px-3 py-3 text-sm ${view === id ? 'bg-red-500/15 text-white' : 'text-slate-400'}`}>
                  <Icon className="h-5 w-5" /> {label}
                </button>
              ))}
            </nav>
          </div>
        </div>
      )}

      <main className="relative pt-[72px] lg:pl-[228px] min-h-screen">
        <div className="mx-auto max-w-[1500px] p-4 sm:p-6 lg:p-7">{children}</div>
      </main>
    </div>
  );
}

