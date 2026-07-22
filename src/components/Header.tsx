import { Activity, Shield, TrendingUp, BarChart3, LogOut, User, Menu, X } from 'lucide-react';
import { useState } from 'react';

interface HeaderProps {
  botStatus: 'RUNNING' | 'STOPPED' | 'PAUSED';
  connected: boolean;
  userEmail?: string;
  isGuest?: boolean;
  onSignIn?: () => void;
  onSignOut?: () => void;
}

export function Header({ botStatus, connected, userEmail, isGuest = false, onSignIn, onSignOut }: HeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const statusColor = botStatus === 'RUNNING' ? 'bg-emerald-500' : botStatus === 'PAUSED' ? 'bg-amber-500' : 'bg-red-500';
  const connColor = connected ? 'bg-emerald-500' : 'bg-red-500';

  return (
    <header className="bg-slate-900 border-b border-slate-700 px-3 sm:px-6 py-3 sm:py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center shrink-0">
            <TrendingUp className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
          </div>
          <div className="min-w-0">
            <h1 className="text-base sm:text-xl font-bold text-white tracking-tight truncate">SmartPip Trader</h1>
            <p className="text-[10px] sm:text-xs text-slate-400 hidden sm:block">AI-Powered Volatility Index Trading</p>
          </div>
        </div>

        {/* Desktop status badges */}
        <div className="hidden md:flex items-center gap-3 lg:gap-4">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-300">Secure Mode</span>
          </div>
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-slate-400" />
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-300">Deriv</span>
              <span className={`w-2 h-2 rounded-full ${connColor} animate-pulse`} />
            </div>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800 border border-slate-700">
            <BarChart3 className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-300">Bot</span>
            <span className={`w-2 h-2 rounded-full ${statusColor}`} />
            <span className={`text-sm font-medium ${botStatus === 'RUNNING' ? 'text-emerald-400' : 'text-red-400'}`}>
              {botStatus}
            </span>
          </div>
          {isGuest ? (
            <button
              onClick={onSignIn}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
            >
              <User className="w-4 h-4" />
              Sign In to Trade
            </button>
          ) : userEmail ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800 border border-slate-700">
                <User className="w-4 h-4 text-slate-400" />
                <span className="text-sm text-slate-300">{userEmail}</span>
              </div>
              {onSignOut && (
                <button
                  onClick={onSignOut}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-sm transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Sign Out
                </button>
              )}
            </div>
          ) : null}
        </div>

        {/* Mobile menu button */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden p-2 rounded-lg bg-slate-800 text-slate-300"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden mt-3 pt-3 border-t border-slate-800 space-y-2">
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-slate-400" />
              <span className="text-xs text-slate-300">API</span>
              <span className={`w-2 h-2 rounded-full ${connColor}`} />
            </div>
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-slate-400" />
              <span className="text-xs text-slate-300">Bot</span>
              <span className={`w-2 h-2 rounded-full ${statusColor}`} />
              <span className={`text-xs font-medium ${botStatus === 'RUNNING' ? 'text-emerald-400' : 'text-red-400'}`}>
                {botStatus}
              </span>
            </div>
          </div>
          {isGuest ? (
            <button
              onClick={onSignIn}
              className="flex items-center gap-1 px-2 py-1 rounded bg-blue-600 text-white text-xs"
            >
              Sign In
            </button>
          ) : userEmail ? (
            <div className="flex items-center justify-between px-2">
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-slate-400" />
                <span className="text-xs text-slate-300 truncate max-w-[150px]">{userEmail}</span>
              </div>
              {onSignOut && (
                <button
                  onClick={onSignOut}
                  className="flex items-center gap-1 px-2 py-1 rounded bg-slate-800 text-slate-300 text-xs"
                >
                  <LogOut className="w-3 h-3" />
                  Sign Out
                </button>
              )}
            </div>
          ) : null}
        </div>
      )}
    </header>
  );
}
