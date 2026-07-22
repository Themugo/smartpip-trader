import { Play, Square, RotateCcw, ShieldCheck } from 'lucide-react';

interface ControlPanelProps {
  botStatus: 'RUNNING' | 'STOPPED' | 'PAUSED';
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
  locked?: boolean;
  onLockedClick?: () => void;
}

export function ControlPanel({ botStatus, onStart, onStop, onReset, locked = false, onLockedClick }: ControlPanelProps) {
  const handleStart = () => {
    if (locked) {
      onLockedClick?.();
      return;
    }
    onStart();
  };

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
      {locked && (
        <div className="mb-3 p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300">
          Sign in and connect your Deriv token to enable automated trading.
        </div>
      )}
      <div className="flex items-center gap-2 mb-3 sm:mb-4">
        <ShieldCheck className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-400" />
        <h3 className="text-sm font-semibold text-slate-200">Bot Control</h3>
      </div>

      <div className="flex flex-wrap gap-2 sm:gap-3">
        <button
          onClick={handleStart}
          disabled={botStatus === 'RUNNING'}
          className={`flex items-center gap-1.5 sm:gap-2 px-4 sm:px-5 py-2 sm:py-2.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
            botStatus === 'RUNNING'
              ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
              : 'bg-emerald-500 hover:bg-emerald-600 text-white shadow-lg shadow-emerald-500/20'
          }`}
        >
          <Play className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          Start Bot
        </button>

        <button
          onClick={onStop}
          disabled={botStatus === 'STOPPED'}
          className={`flex items-center gap-1.5 sm:gap-2 px-4 sm:px-5 py-2 sm:py-2.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
            botStatus === 'STOPPED'
              ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
              : 'bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/20'
          }`}
        >
          <Square className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          Stop Bot
        </button>

        <button
          onClick={onReset}
          className="flex items-center gap-1.5 sm:gap-2 px-4 sm:px-5 py-2 sm:py-2.5 rounded-lg text-xs sm:text-sm font-medium bg-slate-700 hover:bg-slate-600 text-slate-200 transition-all"
        >
          <RotateCcw className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          Reset Session
        </button>
      </div>

      <div className="mt-3 sm:mt-4 p-2.5 sm:p-3 rounded-lg bg-slate-900/50 border border-slate-700/50">
        <p className="text-[10px] sm:text-xs text-slate-400">
          <span className="text-amber-400 font-medium">Warning:</span> Starting the bot will begin automated trading based on current settings.
          Ensure your risk parameters are configured correctly before proceeding.
        </p>
      </div>
    </div>
  );
}
