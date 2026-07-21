import { TrendingUp, Zap, Shield, Target } from 'lucide-react';

const STATS = [
  { icon: Target, value: '73%', label: 'Win rate', color: 'text-emerald-400' },
  { icon: TrendingUp, value: '6/6', label: 'Conditions', color: 'text-cyan-400' },
  { icon: Zap, value: '<50ms', label: 'Speed', color: 'text-amber-400' },
  { icon: Shield, value: '0%', label: 'Martingale', color: 'text-rose-400' },
];

export function StatsStrip() {
  return (
    <div className="rounded-2xl border border-white/10 bg-[#111318] p-4">
      <div className="grid grid-cols-2 gap-3">
        {STATS.map((s) => (
          <div key={s.label} className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0">
              <s.icon className={`w-4 h-4 ${s.color}`} />
            </div>
            <div className="min-w-0">
              <div className={`text-base font-black font-mono leading-none ${s.color}`}>{s.value}</div>
              <div className="text-[9px] text-slate-500 leading-tight mt-0.5">{s.label}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
