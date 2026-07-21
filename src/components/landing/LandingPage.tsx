import { Sun, Moon, TrendingUp, Activity, Shield, Lock, ArrowRight, BarChart3, Zap, Target } from 'lucide-react';
import { useTheme } from './theme';
import { MarketData } from '../MarketData';
import { StatsStrip } from './StatsStrip';
import type { TickData } from '../../hooks/useDerivTicks';
import type { RegimeState } from '../../hooks/useRegimeDetection';

interface LandingPageProps {
  tickData: TickData;
  onSwitchSymbol: (symbol: string) => void;
  onReconnect: () => void;
  regimeState?: RegimeState;
  isStrategyAllowed?: (strategyType: string) => { allowed: boolean; reason: string };
  onTrade: () => void;
  onConnect: () => void;
}

export function LandingPage({
  tickData, onSwitchSymbol, onReconnect, onTrade, onConnect,
}: LandingPageProps) {
  const { theme, toggle } = useTheme();

  return (
    <div className="min-h-screen bg-[#0a0c11] text-slate-200 overflow-x-hidden">
      {/* Navbar */}
      <header className="nav-dark fixed top-0 inset-x-0 z-50 border-b border-white/10 bg-[#0a0c11]/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center shadow-lg shadow-red-500/30">
              <TrendingUp className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-black tracking-widest text-white uppercase">SmartPip</span>
            <span className="hidden sm:inline text-sm font-black tracking-widest text-slate-500 uppercase">Sniper</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={toggle}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <button
              onClick={onConnect}
              className="px-3 py-1.5 text-xs font-semibold text-white bg-gradient-to-r from-red-600 to-orange-500 rounded-lg shadow-lg shadow-red-500/25 hover:from-red-500 hover:to-orange-400 transition-all flex items-center gap-1.5"
            >
              <Lock className="w-3 h-3" />
              Connect
            </button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="pt-20 sm:pt-24 pb-6 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-emerald-500/30 bg-emerald-500/5 mb-4">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] sm:text-xs text-emerald-400 font-medium tracking-wide">Live market data — no login required</span>
          </div>
          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-black tracking-tight">
            <span className="text-white">Watch the market.</span><br />
            <span className="bg-gradient-to-r from-red-500 to-orange-400 bg-clip-text text-transparent">Trade when ready.</span>
          </h1>
          <p className="mt-3 sm:mt-4 text-sm sm:text-base text-slate-400 max-w-xl mx-auto">
            Real-time ticks, digit analysis, and regime detection from Deriv — free to explore.
            Login only when you want to place a trade.
          </p>
        </div>
      </section>

      {/* Live market — fully interactive, no login */}
      <section className="px-4 sm:px-6 pb-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
            {/* Market data — 2 cols on desktop */}
            <div className="lg:col-span-2">
              <MarketData tickData={tickData} onSwitchSymbol={onSwitchSymbol} onReconnect={onReconnect} />
            </div>

            {/* Side panel: stats + CTA */}
            <div className="space-y-4">
              <StatsStrip />

              {/* Trade CTA card */}
              <div className="rounded-2xl border border-white/10 bg-[#111318] p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Lock className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-bold text-amber-400 uppercase tracking-wider">Trading requires login</span>
                </div>
                <p className="text-xs text-slate-400 mb-4 leading-relaxed">
                  You've seen the market. Now place a trade. Login to execute — your capital is protected by flat stakes and an automatic kill switch.
                </p>
                <button
                  onClick={onTrade}
                  className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-bold bg-gradient-to-r from-red-600 to-orange-500 hover:from-red-500 hover:to-orange-400 text-white shadow-lg shadow-red-500/20 transition-all"
                >
                  Login to Trade
                  <ArrowRight className="w-4 h-4" />
                </button>
                <button
                  onClick={onConnect}
                  className="w-full mt-2 flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-semibold border border-white/10 text-slate-300 hover:bg-white/5 transition-colors"
                >
                  Create free account
                </button>
              </div>

              {/* Trust badges */}
              <div className="grid grid-cols-3 gap-2">
                {[
                  { icon: Shield, label: 'Capital protected', color: 'text-emerald-400' },
                  { icon: Zap, label: '<50ms execution', color: 'text-amber-400' },
                  { icon: Target, label: '6/6 conditions', color: 'text-cyan-400' },
                ].map((b) => (
                  <div key={b.label} className="rounded-xl border border-white/10 bg-[#111318] p-3 text-center">
                    <b.icon className={`w-4 h-4 mx-auto mb-1 ${b.color}`} />
                    <div className="text-[9px] text-slate-500 leading-tight">{b.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features strip — minimal */}
      <section className="px-4 sm:px-6 pb-12">
        <div className="max-w-7xl mx-auto grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { icon: Activity, title: 'Live ticks', desc: 'Real-time Deriv feed' },
            { icon: BarChart3, title: 'Digit analysis', desc: 'Even/odd, over/under, match' },
            { icon: TrendingUp, title: 'Regime detection', desc: 'Adapts to market state' },
            { icon: Shield, title: 'Risk controls', desc: 'Flat stakes, kill switch' },
          ].map((f) => (
            <div key={f.title} className="rounded-xl border border-white/10 bg-[#111318] p-4">
              <f.icon className="w-5 h-5 text-red-400 mb-2" />
              <div className="text-sm font-bold text-white">{f.title}</div>
              <div className="text-[10px] text-slate-500 mt-0.5">{f.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 bg-[#0a0c11]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-2 text-[10px] text-slate-600">
          <span>SmartPip Sniper · www.smartpip.site</span>
          <span>Market data via Deriv API · Not affiliated with Deriv Ltd</span>
        </div>
      </footer>
    </div>
  );
}
