import { Activity, Shield, TrendingUp, BarChart3, LogOut, User, Menu, X, Zap, AlertCircle } from 'lucide-react';
import { useState } from 'react';

interface HeaderProps {
  botStatus: 'RUNNING' | 'STOPPED' | 'PAUSED';
  connected: boolean;
  userEmail?: string;
  onSignOut?: () => void;
}

export function Header({ botStatus, connected, userEmail, onSignOut }: HeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const statusConfig = {
    RUNNING: { bg: 'bg-emerald-500', text: 'text-emerald-400', label: 'Active' },
    PAUSED: { bg: 'bg-amber-500', text: 'text-amber-400', label: 'Paused' },
    STOPPED: { bg: 'bg-slate-500', text: 'text-slate-400', label: 'Stopped' },
  };

  const status = statusConfig[botStatus];

  return (
    <header className="sticky top-0 z-50 bg-slate-900/80 backdrop-blur-xl border-b border-slate-800/50">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 py-3">
        <div className="flex items-center justify-between gap-3">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 via-cyan-500 to-teal-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                <TrendingUp className="w-5 h-5 text-white" />
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-slate-900 border-2 border-emerald-500 flex items-center justify-center">
                <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-emerald-500' : 'bg-slate-500'} animate-pulse`} />
              </div>
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-300 tracking-tight">
                SmartPip
              </h1>
              <p className="text-[10px] text-slate-500 font-medium tracking-wide">TRADING SYSTEM</p>
            </div>
          </div>

          {/* Desktop Status */}
          <div className="hidden md:flex items-center gap-4">
            {/* Connection Badge */}
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${connected ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-slate-800/50 border border-slate-700/50'}`}>
              <Activity className={`w-3.5 h-3.5 ${connected ? 'text-emerald-400' : 'text-slate-500'}`} />
              <span className={`text-xs font-medium ${connected ? 'text-emerald-400' : 'text-slate-400'}`}>
                {connected ? 'Connected' : 'Offline'}
              </span>
            </div>

            {/* Bot Status */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 border border-slate-700/50">
              <BarChart3 className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-xs text-slate-400">Bot</span>
              <AlertCircle className={`w-3.5 h-3.5 ${status.text}`} />
              <span className={`text-xs font-semibold ${status.text}`}>{status.label}</span>
            </div>

            {/* Security Badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 border border-slate-700/50">
              <Shield className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-xs text-cyan-400">Secure</span>
            </div>

            {/* User & Actions */}
            {userEmail && (
              <div className="flex items-center gap-2 ml-2 pl-4 border-l border-slate-800">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 border border-slate-700/50">
                  <User className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-xs text-slate-300 max-w-[120px] truncate">{userEmail}</span>
                </div>
                {onSignOut && (
                  <button
                    onClick={onSignOut}
                    className="p-2 rounded-lg bg-slate-800/50 hover:bg-red-500/10 border border-slate-700/50 hover:border-red-500/30 text-slate-400 hover:text-red-400 transition-all"
                    title="Sign Out"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-slate-300"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden mt-4 pt-4 border-t border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className={`w-4 h-4 ${connected ? 'text-emerald-400' : 'text-slate-500'}`} />
                <span className="text-sm text-slate-300">API Status</span>
              </div>
              <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full ${connected ? 'bg-emerald-500/10' : 'bg-slate-800'}`}>
                <div className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-slate-500'}`} />
                <span className={`text-xs font-medium ${connected ? 'text-emerald-400' : 'text-slate-400'}`}>
                  {connected ? 'Live' : 'Offline'}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Zap className={`w-4 h-4 ${status.text}`} />
                <span className="text-sm text-slate-300">Bot Status</span>
              </div>
              <span className={`text-sm font-semibold ${status.text}`}>{botStatus}</span>
            </div>

            {userEmail && (
              <div className="flex items-center justify-between pt-3 border-t border-slate-800">
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4 text-slate-400" />
                  <span className="text-sm text-slate-300 truncate max-w-[180px]">{userEmail}</span>
                </div>
                {onSignOut && (
                  <button
                    onClick={onSignOut}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 text-sm"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign Out
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
