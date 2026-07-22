import { Loader2 } from 'lucide-react';

// ── Skeleton pulse animation ───────────────────────────────────
function Pulse({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  return <div className={`animate-pulse bg-slate-700/50 rounded ${className}`} style={style} />;
}

// ── Card skeleton ──────────────────────────────────────────────
export function CardSkeleton({ lines = 3, className = '' }: { lines?: number; className?: string }) {
  return (
    <div className={`bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5 space-y-3 ${className}`}>
      <div className="flex items-center gap-2">
        <Pulse className="w-5 h-5 rounded-lg" />
        <Pulse className="w-32 h-4" />
      </div>
      {Array.from({ length: lines }, (_, i) => (
        <Pulse key={i} className="h-3 w-full" style={{ width: `${85 - i * 15}%` }} />
      ))}
    </div>
  );
}

// ── Stats card skeleton ────────────────────────────────────────
export function StatsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="bg-slate-800 rounded-xl border border-slate-700 p-4 space-y-2">
          <Pulse className="w-16 h-3" />
          <Pulse className="w-20 h-6" />
        </div>
      ))}
    </div>
  );
}

// ── Table skeleton ─────────────────────────────────────────────
export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-700">
        <div className="flex gap-4">
          {Array.from({ length: cols }, (_, i) => (
            <Pulse key={i} className="h-3 flex-1" />
          ))}
        </div>
      </div>
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} className="px-4 py-3 border-b border-slate-700/30">
          <div className="flex gap-4">
            {Array.from({ length: cols }, (_, c) => (
              <Pulse key={c} className="h-3 flex-1" style={{ width: `${60 + Math.random() * 30}%` }} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Chart skeleton ─────────────────────────────────────────────
export function ChartSkeleton({ height = 'h-40' }: { height?: string }) {
  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
      <div className="flex items-center justify-between mb-4">
        <Pulse className="w-24 h-4" />
        <Pulse className="w-16 h-4" />
      </div>
      <div className={`${height} rounded-lg overflow-hidden`}>
        <svg viewBox="0 0 400 100" className="w-full h-full opacity-20">
          <polyline
            points="0,80 50,60 100,70 150,40 200,50 250,30 300,45 350,20 400,35"
            fill="none"
            stroke="#6366f1"
            strokeWidth="2"
          />
        </svg>
      </div>
    </div>
  );
}

// ── Panel skeleton (generic) ───────────────────────────────────
export function PanelSkeleton({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5 ${className}`}>
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Pulse className="w-5 h-5 rounded-lg" />
          <Pulse className="w-40 h-4" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {Array.from({ length: 4 }, (_, i) => (
            <Pulse key={i} className="h-16 rounded-lg" />
          ))}
        </div>
        <Pulse className="h-24 rounded-lg" />
      </div>
    </div>
  );
}

// ── Inline spinner ─────────────────────────────────────────────
export function Spinner({ size = 'sm', text }: { size?: 'sm' | 'md'; text?: string }) {
  const s = size === 'sm' ? 'w-4 h-4' : 'w-6 h-6';
  return (
    <div className="flex items-center justify-center gap-2 py-8">
      <Loader2 className={`${s} text-blue-400 animate-spin`} />
      {text && <span className="text-sm text-slate-400">{text}</span>}
    </div>
  );
}
