import { Sun, Moon } from 'lucide-react';
import { useTheme } from './theme';

interface NavbarProps {
  onLogin: () => void;
  onSignUp: () => void;
}

export function Navbar({ onLogin, onSignUp }: NavbarProps) {
  const { theme, toggle } = useTheme();

  return (
    <header className="nav-dark fixed top-0 inset-x-0 z-50 border-b border-white/10">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center shadow-lg shadow-red-500/30">
            <span className="text-sm font-black text-white">S</span>
          </div>
          <span className="text-sm font-bold tracking-widest text-white uppercase">SmartPip</span>
          <span className="text-sm font-bold tracking-widest text-slate-400 uppercase">Sniper</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={toggle}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <button
            onClick={onLogin}
            className="px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-white border border-white/10 rounded-lg hover:bg-white/5 transition-colors"
          >
            Login
          </button>
          <button
            onClick={onSignUp}
            className="px-3 py-1.5 text-xs font-semibold text-white bg-gradient-to-r from-red-500 to-orange-500 rounded-lg shadow-lg shadow-red-500/25 hover:from-red-400 hover:to-orange-400 transition-all"
          >
            Start Free
          </button>
        </div>
      </div>
    </header>
  );
}
