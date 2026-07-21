import { Play, Square, RotateCcw, Power, AlertTriangle } from 'lucide-react';

interface ControlPanelProps {
  botStatus: 'RUNNING' | 'STOPPED' | 'PAUSED';
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
}

export function ControlPanel({ botStatus, onStart, onStop, onReset }: ControlPanelProps) {
  return (
    <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 overflow-hidden">
      {/* Header */}
      <div className="px-4 sm:px-5 py-4 border-b border-slate-800/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-lg transition-all ${
            botStatus === 'RUNNING'
              ? 'bg-gradient-to-br from-emerald-500 to-teal-500 shadow-emerald-500/20'
              : 'bg-gradient-to-br from-slate-600 to-slate-700 shadow-slate-500/10'
          }`}>
            <Power className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Bot Control</h3>
            <p className="text-[10px] text-slate-500">Automated trading management</p>
          </div>
        </div>

        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
          botStatus === 'RUNNING'
            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
            : botStatus === 'PAUSED'
            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
            : 'bg-slate-700/50 text-slate-400 border border-slate-600/50'
        }`}>
          <div className={`w-2 h-2 rounded-full ${
            botStatus === 'RUNNING' ? 'bg-emerald-500 animate-pulse' : 'bg-slate-500'
          }`} />
          {botStatus}
        </div>
      </div>

      {/* Controls */}
      <div className="p-4 sm:p-5">
        <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-4">
          {/* Start */}
          <button
            onClick={onStart}
            disabled={botStatus === 'RUNNING'}
            className={`group relative flex flex-col items-center gap-2 p-3 sm:p-4 rounded-xl border transition-all ${
              botStatus === 'RUNNING'
                ? 'bg-emerald-500/10 border-emerald-500/20 cursor-default'
                : 'bg-slate-800/50 border-slate-700/50 hover:border-emerald-500/30 hover:bg-emerald-500/5'
            }`}
          >
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
              botStatus === 'RUNNING'
                ? 'bg-emerald-500 text-white'
                : 'bg-slate-700 group-hover:bg-emerald-500 text-slate-300 group-hover:text-white'
            }`}>
              <Play className="w-5 h-5" />
            </div>
            <span className={`text-xs font-medium ${
              botStatus === 'RUNNING' ? 'text-emerald-400' : 'text-slate-300 group-hover:text-emerald-400'
            }`}>
              Start
            </span>
          </button>

          {/* Stop */}
          <button
            onClick={onStop}
            disabled={botStatus === 'STOPPED'}
            className={`group relative flex flex-col items-center gap-2 p-3 sm:p-4 rounded-xl border transition-all ${
              botStatus === 'STOPPED'
                ? 'bg-slate-800/30 border-slate-700/30 cursor-default'
                : 'bg-slate-800/50 border-slate-700/50 hover:border-red-500/30 hover:bg-red-500/5'
            }`}
          >
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
              botStatus === 'STOPPED'
                ? 'bg-slate-700 text-slate-500'
                : 'bg-slate-700 group-hover:bg-red-500 text-slate-300 group-hover:text-white'
            }`}>
              <Square className="w-5 h-5" />
            </div>
            <span className={`text-xs font-medium ${
              botStatus === 'STOPPED' ? 'text-slate-500' : 'text-slate-300 group-hover:text-red-400'
            }`}>
              Stop
            </span>
          </button>

          {/* Reset */}
          <button
            onClick={onReset}
            className="group flex flex-col items-center gap-2 p-3 sm:p-4 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-slate-600/50 transition-all"
          >
            <div className="w-10 h-10 rounded-xl bg-slate-700 group-hover:bg-slate-600 flex items-center justify-center text-slate-300 transition-all">
              <RotateCcw className="w-5 h-5" />
            </div>
            <span className="text-xs font-medium text-slate-300">Reset</span>
          </button>
        </div>

        {/* Warning */}
        <div className="flex items-start gap-3 p-3 rounded-xl bg-amber-500/5 border border-amber-500/20">
          <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
          <p className="text-xs text-amber-200/70 leading-relaxed">
            <span className="text-amber-400 font-medium">Warning:</span> Starting the bot will begin automated trading based on current settings.
            Ensure your risk parameters are configured correctly before proceeding.
          </p>
        </div>
      </div>
    </div>
  );
}
