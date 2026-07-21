import { ShieldCheck, ChevronDown, ChevronUp, Activity, User, Settings } from 'lucide-react';
import { useState } from 'react';
import type { AuditLogEntry } from '../lib/supabase';

interface AuditLogProps {
  logs: AuditLogEntry[];
}

const ACTION_ICONS: Record<string, React.ElementType> = {
  START_BOT: Activity,
  STOP_BOT: Activity,
  RESET_SESSION: Activity,
  UPDATE_SETTINGS: Settings,
  default: ShieldCheck,
};

const ACTION_COLORS: Record<string, string> = {
  START_BOT: 'text-emerald-400 bg-emerald-500/10',
  STOP_BOT: 'text-red-400 bg-red-500/10',
  RESET_SESSION: 'text-amber-400 bg-amber-500/10',
  UPDATE_SETTINGS: 'text-blue-400 bg-blue-500/10',
  default: 'text-slate-400 bg-slate-500/10',
};

export function AuditLog({ logs }: AuditLogProps) {
  const [expanded, setExpanded] = useState(false);

  const displayLogs = expanded ? logs : logs.slice(0, 5);

  if (!logs.length) {
    return (
      <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 p-6 text-center">
        <div className="w-12 h-12 rounded-xl bg-slate-800/50 border border-slate-700/50 flex items-center justify-center mx-auto mb-3">
          <ShieldCheck className="w-6 h-6 text-slate-500" />
        </div>
        <p className="text-slate-400 text-xs font-medium">No audit logs</p>
        <p className="text-slate-500 text-[10px] mt-1">Actions will be logged here</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800/50 flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center">
          <ShieldCheck className="w-4 h-4 text-white" />
        </div>
        <span className="text-sm font-semibold text-white">Audit Log</span>
        <span className="ml-auto text-[10px] text-slate-500 bg-slate-800/50 px-2 py-0.5 rounded-full">{logs.length}</span>
      </div>

      {/* Log Entries */}
      <div className="divide-y divide-slate-800/50">
        {displayLogs.map((log) => {
          const Icon = ACTION_ICONS[log.action] || ACTION_ICONS.default;
          const colorClass = ACTION_COLORS[log.action] || ACTION_COLORS.default;

          return (
            <div key={log.id} className="px-4 py-3 flex items-start gap-3 hover:bg-slate-800/30 transition-colors">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${colorClass}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-white font-medium">{log.action.replace(/_/g, ' ')}</span>
                  <span className="text-[10px] text-slate-500 shrink-0">
                    {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <User className="w-3 h-3 text-slate-600" />
                  <span className="text-[10px] text-slate-500">{log.actor}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Show More */}
      {logs.length > 5 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-center gap-2 py-3 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800/30 transition-colors border-t border-slate-800/50"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-4 h-4" />
              Show Less
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              Show {logs.length - 5} More
            </>
          )}
        </button>
      )}
    </div>
  );
}
