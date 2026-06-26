import { ShieldCheck, Clock, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import type { AuditLogEntry } from '../lib/supabase';

interface AuditLogProps {
  logs: AuditLogEntry[];
}

export function AuditLog({ logs }: AuditLogProps) {
  const [expanded, setExpanded] = useState(false);

  const displayLogs = expanded ? logs : logs.slice(0, 5);

  if (!logs.length) {
    return (
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 sm:p-6 text-center">
        <ShieldCheck className="w-7 h-7 text-slate-500 mx-auto mb-2" />
        <p className="text-slate-400 text-xs sm:text-sm">No audit logs</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      <div className="px-3 sm:px-4 py-3 border-b border-slate-700">
        <h3 className="text-sm font-semibold text-slate-200">Audit Log</h3>
      </div>

      <div className="divide-y divide-slate-700/50">
        {displayLogs.map((log) => (
          <div key={log.id} className="px-3 sm:px-4 py-2.5 flex items-start gap-2.5 sm:gap-3">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs sm:text-sm text-slate-300 font-medium truncate">{log.action}</span>
                <span className="text-[10px] sm:text-xs text-slate-500 shrink-0">
                  {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <span className="text-[10px] sm:text-xs text-slate-500">{log.actor}</span>
              {log.details && Object.keys(log.details).length > 0 && (
                <div className="mt-1 text-[10px] text-slate-600 font-mono truncate">
                  {JSON.stringify(log.details)}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {logs.length > 5 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-center gap-1 py-2 text-xs text-slate-400 hover:text-slate-300 hover:bg-slate-700/30 transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-3.5 h-3.5" />
              Show Less
            </>
          ) : (
            <>
              <ChevronDown className="w-3.5 h-3.5" />
              Show {logs.length - 5} More
            </>
          )}
        </button>
      )}
    </div>
  );
}
