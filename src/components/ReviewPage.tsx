import { useState, useEffect, useCallback } from 'react';
import {
  Activity, Server, Code2, Cpu, Zap, Globe,
  CheckCircle2, XCircle, RefreshCw, TrendingUp,
  Database, BarChart3, Shield, BookOpen, AlertTriangle,
  ChevronDown, ChevronUp, ExternalLink, Hash,
} from 'lucide-react';

// ── API shape ─────────────────────────────────────────────────────────────────

interface ModuleInfo {
  group: string;
  path: string;
  exists: boolean;
  lines: number;
  size_kb: number;
}

interface ComponentInfo {
  path: string;
  lines: number;
  size_kb: number;
}

interface Endpoint {
  method: string;
  path: string;
  tag: string;
}

interface ReviewData {
  generated_at: string;
  uptime_seconds: number;
  python_version: string;
  system: {
    status: string;
    market: string;
    tick_count: number;
    last_price: number | null;
    last_digit: number | null;
    digit_freq: Record<string, number>;
    latency_ms: number;
  };
  account: {
    balance: number;
    currency: string;
    active_account: string;
  };
  performance: {
    total_trades: number;
    wins: number;
    losses: number;
    win_rate: number;
    total_pnl: number;
    profit_factor: number;
    max_drawdown: number;
  };
  ai: {
    signals_count: number;
    consensus: Record<string, unknown>;
    market_entropy: number | null;
    top_signals: unknown[];
  };
  modules: {
    backend_total: number;
    backend_present: number;
    backend_missing: number;
    total_lines: number;
    inventory: ModuleInfo[];
  };
  frontend: {
    component_count: number;
    total_lines: number;
    components: ComponentInfo[];
  };
  api_endpoints: Endpoint[];
}

interface DerivAccount {
  balance?: number;
  currency?: string;
  loginid?: string;
  account_type?: string;
  status_flags?: string[];
  risk_classification?: string;
  error?: string;
}

interface ProfitEntry {
  contract_id: string | null;
  contract_type: string | null;
  pnl: number | null;
  buy_price: number | null;
  sell_price: number | null;
  duration: string;
  purchase_time: number | null;
  sell_time: number | null;
}

interface ProfitTable {
  count: number;
  wins: number;
  losses: number;
  total_pnl: number;
  win_rate: number;
  trades: ProfitEntry[];
  error?: string;
}

// ── Small helpers ─────────────────────────────────────────────────────────────

function Pill({
  label, color = 'slate',
}: { label: string; color?: 'green' | 'red' | 'amber' | 'violet' | 'slate' | 'blue' }) {
  const map: Record<string, string> = {
    green:  'bg-emerald-900/40 text-emerald-300 border-emerald-700/40',
    red:    'bg-red-900/40 text-red-300 border-red-700/40',
    amber:  'bg-amber-900/30 text-amber-300 border-amber-700/40',
    violet: 'bg-violet-900/40 text-violet-300 border-violet-700/40',
    blue:   'bg-blue-900/30 text-blue-300 border-blue-700/40',
    slate:  'bg-slate-700 text-slate-300 border-slate-600',
  };
  return (
    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${map[color]}`}>
      {label}
    </span>
  );
}

function Stat({
  icon, label, value, sub, ok,
}: {
  icon: React.ReactNode; label: string; value: string; sub?: string; ok?: boolean;
}) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/40 rounded-xl p-4 flex gap-3">
      <div className={`mt-0.5 ${ok === false ? 'text-red-400' : ok === true ? 'text-emerald-400' : 'text-violet-400'}`}>
        {icon}
      </div>
      <div>
        <div className="text-[10px] text-slate-500">{label}</div>
        <div className="text-sm font-bold text-slate-100 font-mono">{value}</div>
        {sub && <div className="text-[10px] text-slate-500 mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

function SectionHeader({ icon, title, badge }: { icon: React.ReactNode; title: string; badge?: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="text-violet-400">{icon}</div>
      <span className="text-sm font-semibold text-slate-200">{title}</span>
      {badge && <Pill label={badge} color="violet" />}
    </div>
  );
}

function MethodBadge({ method }: { method: string }) {
  const map: Record<string, string> = {
    GET:  'text-emerald-300 bg-emerald-900/30',
    POST: 'text-amber-300 bg-amber-900/30',
    WS:   'text-violet-300 bg-violet-900/30',
    PUT:  'text-blue-300 bg-blue-900/30',
  };
  return (
    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${map[method] ?? 'text-slate-300 bg-slate-700'}`}>
      {method}
    </span>
  );
}

function DigitBar({ freq }: { freq: Record<string, number> }) {
  const total = Object.values(freq).reduce((s, v) => s + v, 0) || 1;
  const max   = Math.max(...Object.values(freq), 1);
  return (
    <div className="flex gap-1 items-end h-12">
      {Array.from({ length: 10 }, (_, d) => {
        const n = freq[String(d)] ?? 0;
        const pct = (n / total) * 100;
        const h   = Math.round((n / max) * 44);
        const expected = 10;
        const color = pct > expected + 3 ? 'bg-emerald-500' : pct < expected - 3 ? 'bg-red-500' : 'bg-slate-500';
        return (
          <div key={d} className="flex flex-col items-center flex-1 gap-0.5">
            <div className="text-[8px] text-slate-500">{pct.toFixed(0)}%</div>
            <div
              className={`w-full rounded-t ${color} transition-all duration-700`}
              style={{ height: `${h}px` }}
            />
            <div className="text-[9px] text-slate-400">{d}</div>
          </div>
        );
      })}
    </div>
  );
}

function CollapsibleSection({
  title, icon, count, children,
}: { title: string; icon: React.ReactNode; count?: number; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-slate-800/40 border border-slate-700/40 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-700/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className="text-violet-400">{icon}</div>
          <span className="text-sm font-semibold text-slate-200">{title}</span>
          {count !== undefined && (
            <span className="text-[10px] text-slate-400 bg-slate-700 px-1.5 py-0.5 rounded">
              {count}
            </span>
          )}
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}

function uptime(s: number) {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m ${s % 60}s`;
}

// ── Main component ────────────────────────────────────────────────────────────

export function ReviewPage() {
  const [data, setData]           = useState<ReviewData | null>(null);
  const [loading, setLoading]     = useState(true);
  const [lastRefresh, setLast]    = useState('');
  const [derivAcc, setDerivAcc]   = useState<DerivAccount | null>(null);
  const [profitTbl, setProfitTbl] = useState<ProfitTable | null>(null);
  const [apiToken, setApiToken]   = useState('');
  const [loadingDeriv, setLoadingDeriv] = useState(false);
  const [activeSection, setSection]     = useState<string>('overview');
  const [showEpEndpoints, setEpOpen]    = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/review');
      if (res.ok) {
        const d = await res.json() as ReviewData;
        setData(d);
        setLast(new Date().toLocaleTimeString());
      }
    } catch (_) { /* silently retry */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 5000);
    return () => clearInterval(id);
  }, [load]);

  const loadDerivAccount = async () => {
    if (!apiToken.trim()) return;
    setLoadingDeriv(true);
    try {
      const [accRes, ptRes] = await Promise.all([
        fetch(`/api/review/deriv-account?api_token=${encodeURIComponent(apiToken)}`),
        fetch(`/api/review/profit-table?api_token=${encodeURIComponent(apiToken)}&limit=50`),
      ]);
      if (accRes.ok)  setDerivAcc(await accRes.json() as DerivAccount);
      if (ptRes.ok)   setProfitTbl(await ptRes.json() as ProfitTable);
    } catch (_) { /* */ }
    finally { setLoadingDeriv(false); }
  };

  const sections = [
    { id: 'overview',   label: 'Overview',   icon: <Activity className="w-3.5 h-3.5" /> },
    { id: 'deriv',      label: 'Deriv Live', icon: <Globe className="w-3.5 h-3.5" /> },
    { id: 'modules',    label: 'Modules',    icon: <Code2 className="w-3.5 h-3.5" /> },
    { id: 'endpoints',  label: 'API',        icon: <Server className="w-3.5 h-3.5" /> },
    { id: 'frontend',   label: 'Frontend',   icon: <Cpu className="w-3.5 h-3.5" /> },
  ];

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm animate-pulse">
        Loading system review…
      </div>
    );
  }

  const p = data?.performance;
  const sys = data?.system;
  const acc = data?.account;
  const ai  = data?.ai;
  const mods = data?.modules;
  const fe   = data?.frontend;
  const groups = mods
    ? Object.entries(
        mods.inventory.reduce<Record<string, ModuleInfo[]>>((acc2, m) => {
          (acc2[m.group] ??= []).push(m);
          return acc2;
        }, {}),
      )
    : [];

  const tagColors: Record<string, 'green' | 'blue' | 'amber' | 'violet' | 'slate'> = {
    System:   'blue',
    Trading:  'green',
    AI:       'violet',
    Journal:  'amber',
    Review:   'violet',
    Streaming:'amber',
    Config:   'slate',
    Market:   'blue',
  };

  return (
    <div className="space-y-4">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Shield className="w-5 h-5 text-violet-400" />
            Project Review
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Live system inspection — refreshes every 5 s
            {lastRefresh && <span className="ml-2 text-slate-600">last: {lastRefresh}</span>}
          </p>
        </div>
        <button
          onClick={() => void load()}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600/20 hover:bg-violet-600/30 border border-violet-700/40 text-violet-300 text-xs rounded-lg transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          Refresh
        </button>
      </div>

      {/* ── Sub-nav ─────────────────────────────────────────────────────── */}
      <div className="flex gap-1 flex-wrap">
        {sections.map((s) => (
          <button
            key={s.id}
            onClick={() => setSection(s.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeSection === s.id
                ? 'bg-violet-600/20 text-violet-300 border border-violet-700/40'
                : 'bg-slate-800/50 text-slate-400 border border-slate-700/30 hover:text-slate-200'
            }`}
          >
            {s.icon}{s.label}
          </button>
        ))}
      </div>

      {/* ═══ OVERVIEW ═══════════════════════════════════════════════════ */}
      {activeSection === 'overview' && data && (
        <div className="space-y-4">

          {/* KPI row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Stat
              icon={<Activity className="w-4 h-4" />}
              label="Bot Status"
              value={sys?.status?.toUpperCase() ?? '—'}
              ok={sys?.status === 'running'}
            />
            <Stat
              icon={<Server className="w-4 h-4" />}
              label="Uptime"
              value={uptime(data.uptime_seconds)}
              sub={`Python ${data.python_version}`}
            />
            <Stat
              icon={<Hash className="w-4 h-4" />}
              label="Ticks Seen"
              value={sys?.tick_count?.toLocaleString() ?? '0'}
              sub={`Latency: ${sys?.latency_ms ?? 0} ms`}
            />
            <Stat
              icon={<TrendingUp className="w-4 h-4" />}
              label="Session P&L"
              value={`${(p?.total_pnl ?? 0) >= 0 ? '+' : ''}$${(p?.total_pnl ?? 0).toFixed(2)}`}
              ok={(p?.total_pnl ?? 0) >= 0}
              sub={`${p?.win_rate ?? 0}% win rate`}
            />
          </div>

          {/* Market + Account */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="bg-slate-800/50 border border-slate-700/40 rounded-xl p-4 space-y-3">
              <SectionHeader icon={<Globe className="w-4 h-4" />} title="Market" />
              <div className="grid grid-cols-2 gap-2">
                {[
                  ['Symbol',      sys?.market ?? '—'],
                  ['Last Price',  sys?.last_price != null ? sys.last_price.toFixed(4) : '—'],
                  ['Last Digit',  sys?.last_digit != null ? String(sys.last_digit) : '—'],
                  ['Trades',      String(p?.total_trades ?? 0)],
                  ['Wins',        String(p?.wins ?? 0)],
                  ['Losses',      String(p?.losses ?? 0)],
                ].map(([l, v]) => (
                  <div key={l} className="text-[11px]">
                    <div className="text-slate-500">{l}</div>
                    <div className="text-slate-200 font-mono">{v}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-slate-800/50 border border-slate-700/40 rounded-xl p-4 space-y-3">
              <SectionHeader icon={<Database className="w-4 h-4" />} title="Account" />
              <div className="grid grid-cols-2 gap-2">
                {[
                  ['Balance',   `$${(acc?.balance ?? 0).toFixed(2)}`],
                  ['Currency',  acc?.currency ?? '—'],
                  ['Type',      acc?.active_account ?? '—'],
                  ['PF',        (p?.profit_factor ?? 0).toFixed(2)],
                  ['Max DD',    `${(p?.max_drawdown ?? 0).toFixed(2)}%`],
                  ['Entropy',   ai?.market_entropy != null ? ai.market_entropy.toFixed(4) : '—'],
                ].map(([l, v]) => (
                  <div key={l} className="text-[11px]">
                    <div className="text-slate-500">{l}</div>
                    <div className="text-slate-200 font-mono">{v}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Digit frequency heatmap */}
          {sys?.digit_freq && (
            <div className="bg-slate-800/50 border border-slate-700/40 rounded-xl p-4">
              <SectionHeader icon={<BarChart3 className="w-4 h-4" />} title="Live Digit Frequency (last 200 ticks)" />
              <DigitBar freq={sys.digit_freq} />
              <div className="flex justify-between text-[9px] text-slate-600 mt-1">
                <span>■ Overrepresented</span>
                <span>■ Expected ≈ 10%</span>
                <span>■ Underrepresented</span>
              </div>
            </div>
          )}

          {/* AI signals */}
          {ai && ai.signals_count > 0 && (
            <div className="bg-slate-800/50 border border-slate-700/40 rounded-xl p-4">
              <SectionHeader
                icon={<Zap className="w-4 h-4" />}
                title="AI Signals"
                badge={`${ai.signals_count} active`}
              />
              {ai.consensus && Object.keys(ai.consensus).length > 0 && (
                <div className="text-xs text-slate-300 bg-slate-700/40 rounded p-2 mb-2 font-mono">
                  Consensus: {JSON.stringify(ai.consensus, null, 0)}
                </div>
              )}
              <div className="grid grid-cols-2 gap-2">
                {(ai.top_signals as Array<Record<string, unknown>>).map((s, i) => (
                  <div key={i} className="bg-slate-700/30 rounded p-2">
                    <div className="text-[9px] text-violet-400 font-medium">
                      {String(s.analyzer ?? s.name ?? `Signal ${i + 1}`)}
                    </div>
                    <div className="text-[10px] text-slate-300 font-mono">
                      {String(s.prediction ?? '—')} · {Number(s.confidence ?? 0).toFixed(1)}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Code health summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Backend Modules',  value: `${mods?.backend_present}/${mods?.backend_total}`, ok: (mods?.backend_missing ?? 0) === 0 },
              { label: 'Backend Lines',    value: (mods?.total_lines ?? 0).toLocaleString() },
              { label: 'Frontend Components', value: String(fe?.component_count ?? 0) },
              { label: 'Frontend Lines',   value: (fe?.total_lines ?? 0).toLocaleString() },
            ].map(({ label, value, ok }) => (
              <div key={label} className="bg-slate-800/60 border border-slate-700/40 rounded-xl p-3">
                <div className="text-[10px] text-slate-500 mb-1">{label}</div>
                <div className={`text-sm font-bold font-mono ${ok === false ? 'text-red-400' : 'text-slate-100'}`}>
                  {value}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ═══ DERIV LIVE ═════════════════════════════════════════════════ */}
      {activeSection === 'deriv' && (
        <div className="space-y-4">
          {/* Token input */}
          <div className="bg-slate-800/60 border border-slate-700/40 rounded-xl p-4">
            <SectionHeader icon={<Globe className="w-4 h-4" />} title="Connect to Real Deriv Account" />
            <p className="text-xs text-slate-400 mb-3">
              Enter your Deriv API token to pull live account data and real closed-contract history.
              Token is used once per request — never stored server-side.
            </p>
            <div className="flex gap-2">
              <input
                type="password"
                value={apiToken}
                onChange={(e) => setApiToken(e.target.value)}
                placeholder="Deriv API token (read permission)"
                className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-violet-500"
              />
              <button
                onClick={() => void loadDerivAccount()}
                disabled={!apiToken.trim() || loadingDeriv}
                className="px-4 py-2 bg-violet-600/20 hover:bg-violet-600/40 border border-violet-700/50 text-violet-300 text-xs rounded-lg disabled:opacity-40 transition-colors"
              >
                {loadingDeriv ? 'Loading…' : 'Fetch'}
              </button>
            </div>
            {derivAcc?.error && (
              <div className="mt-2 text-xs text-red-400 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                {derivAcc.error}
              </div>
            )}
          </div>

          {/* Account info */}
          {derivAcc && !derivAcc.error && (
            <div className="bg-slate-800/50 border border-emerald-700/30 rounded-xl p-4">
              <SectionHeader icon={<Database className="w-4 h-4" />} title="Real Account" />
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {[
                  ['Login ID',    derivAcc.loginid ?? '—'],
                  ['Balance',     `$${(derivAcc.balance ?? 0).toFixed(2)}`],
                  ['Currency',    derivAcc.currency ?? '—'],
                  ['Type',        derivAcc.account_type ?? '—'],
                  ['Risk Class',  derivAcc.risk_classification ?? '—'],
                  ['Status',      (derivAcc.status_flags ?? []).join(', ') || 'Active'],
                ].map(([l, v]) => (
                  <div key={l} className="text-[11px]">
                    <div className="text-slate-500">{l}</div>
                    <div className="text-slate-200 font-mono truncate">{v}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Profit table */}
          {profitTbl && !profitTbl.error && (
            <div className="bg-slate-800/50 border border-slate-700/40 rounded-xl p-4">
              <SectionHeader
                icon={<BookOpen className="w-4 h-4" />}
                title="Real Closed Contracts"
                badge={`${profitTbl.count} trades`}
              />
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                {[
                  { label: 'Total',    value: String(profitTbl.count) },
                  { label: 'Wins',     value: String(profitTbl.wins) },
                  { label: 'Win Rate', value: `${profitTbl.win_rate.toFixed(1)}%` },
                  { label: 'Net P&L',  value: `$${profitTbl.total_pnl.toFixed(2)}` },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-slate-700/30 rounded-lg p-2">
                    <div className="text-[9px] text-slate-500">{label}</div>
                    <div className="text-sm font-bold font-mono text-slate-100">{value}</div>
                  </div>
                ))}
              </div>

              <div className="space-y-1 max-h-64 overflow-y-auto">
                {profitTbl.trades.map((t, i) => {
                  const win = (t.pnl ?? 0) > 0;
                  return (
                    <div
                      key={i}
                      className={`flex items-center justify-between px-2 py-1.5 rounded text-[10px] ${
                        win ? 'bg-emerald-900/10 border border-emerald-700/20' : 'bg-red-900/10 border border-red-700/20'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {win
                          ? <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                          : <XCircle className="w-3 h-3 text-red-400" />}
                        <span className="text-slate-300">{t.contract_type ?? '—'}</span>
                        <span className="text-slate-500">{t.duration}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-slate-500">
                          buy ${(t.buy_price ?? 0).toFixed(2)}
                        </span>
                        <span className={`font-mono font-bold ${win ? 'text-emerald-400' : 'text-red-400'}`}>
                          {win ? '+' : ''}${(t.pnl ?? 0).toFixed(4)}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {!derivAcc && (
            <div className="text-center py-12 text-slate-500 text-sm">
              Enter your Deriv API token above to unlock real account data.
            </div>
          )}
        </div>
      )}

      {/* ═══ MODULES ════════════════════════════════════════════════════ */}
      {activeSection === 'modules' && mods && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-2">
            {[
              { label: 'Present', value: String(mods.backend_present), ok: true },
              { label: 'Missing', value: String(mods.backend_missing), ok: mods.backend_missing === 0 },
              { label: 'Total Lines', value: mods.total_lines.toLocaleString() },
              { label: 'Coverage', value: `${Math.round(mods.backend_present / mods.backend_total * 100)}%` },
            ].map(({ label, value, ok }) => (
              <div key={label} className="bg-slate-800/60 border border-slate-700/40 rounded-xl p-3">
                <div className="text-[10px] text-slate-500 mb-1">{label}</div>
                <div className={`text-sm font-bold font-mono ${ok === false ? 'text-red-400' : 'text-slate-100'}`}>
                  {value}
                </div>
              </div>
            ))}
          </div>

          {groups.map(([group, items]) => (
            <CollapsibleSection
              key={group}
              title={group}
              icon={<Code2 className="w-3.5 h-3.5" />}
              count={items.length}
            >
              <div className="space-y-1 mt-2">
                {items.map((m) => (
                  <div
                    key={m.path}
                    className={`flex items-center justify-between px-2 py-1.5 rounded text-[10px] ${
                      m.exists
                        ? 'bg-slate-700/20 border border-slate-600/20'
                        : 'bg-red-900/10 border border-red-700/20'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {m.exists
                        ? <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
                        : <XCircle className="w-3 h-3 text-red-400 shrink-0" />}
                      <span className="font-mono text-slate-300">{m.path}</span>
                    </div>
                    <div className="flex gap-3 text-slate-500">
                      <span>{m.lines.toLocaleString()} lines</span>
                      <span>{m.size_kb} KB</span>
                    </div>
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          ))}
        </div>
      )}

      {/* ═══ API ENDPOINTS ══════════════════════════════════════════════ */}
      {activeSection === 'endpoints' && data && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-2">
            {(['GET', 'POST', 'WS', 'Total'] as const).map((m) => {
              const count = m === 'Total'
                ? data.api_endpoints.length
                : data.api_endpoints.filter((e) => e.method === m).length;
              return (
                <div key={m} className="bg-slate-800/60 border border-slate-700/40 rounded-xl p-3">
                  <div className="text-[10px] text-slate-500 mb-1">{m}</div>
                  <div className="text-sm font-bold font-mono text-slate-100">{count}</div>
                </div>
              );
            })}
          </div>

          {(['System', 'Trading', 'AI', 'Journal', 'Review', 'Streaming', 'Config', 'Market'] as const).map((tag) => {
            const eps = data.api_endpoints.filter((e) => e.tag === tag);
            if (eps.length === 0) return null;
            return (
              <div key={tag} className="bg-slate-800/40 border border-slate-700/30 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Pill label={tag} color={tagColors[tag] ?? 'slate'} />
                  <span className="text-[10px] text-slate-500">{eps.length} endpoint{eps.length > 1 ? 's' : ''}</span>
                </div>
                <div className="space-y-1">
                  {eps.map((e) => (
                    <div
                      key={e.path}
                      className="flex items-center gap-2 px-2 py-1 bg-slate-700/20 rounded text-[10px]"
                    >
                      <MethodBadge method={e.method} />
                      <span className="font-mono text-slate-300">{e.path}</span>
                      <ExternalLink className="w-2.5 h-2.5 text-slate-600 ml-auto" />
                    </div>
                  ))}
                </div>
              </div>
            );
          })}

          {/* Toggle to reveal all */}
          <button
            onClick={() => setEpOpen(!showEpEndpoints)}
            className="text-xs text-slate-500 hover:text-slate-300 underline"
          >
            {showEpEndpoints ? 'Hide raw list' : 'Show raw JSON list'}
          </button>
          {showEpEndpoints && (
            <pre className="text-[9px] text-slate-400 bg-slate-900 rounded-lg p-3 overflow-auto max-h-48">
              {JSON.stringify(data.api_endpoints, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* ═══ FRONTEND ═══════════════════════════════════════════════════ */}
      {activeSection === 'frontend' && fe && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 mb-2">
            <div className="bg-slate-800/60 border border-slate-700/40 rounded-xl p-3">
              <div className="text-[10px] text-slate-500 mb-1">Components</div>
              <div className="text-sm font-bold font-mono text-slate-100">{fe.component_count}</div>
            </div>
            <div className="bg-slate-800/60 border border-slate-700/40 rounded-xl p-3">
              <div className="text-[10px] text-slate-500 mb-1">Total Lines</div>
              <div className="text-sm font-bold font-mono text-slate-100">{fe.total_lines.toLocaleString()}</div>
            </div>
          </div>

          <div className="bg-slate-800/40 border border-slate-700/30 rounded-xl overflow-hidden">
            <div className="grid grid-cols-3 text-[9px] text-slate-500 px-3 py-2 border-b border-slate-700/30 uppercase">
              <span>File</span>
              <span className="text-right">Lines</span>
              <span className="text-right">Size</span>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {fe.components
                .sort((a, b) => b.lines - a.lines)
                .map((c) => (
                  <div
                    key={c.path}
                    className="grid grid-cols-3 px-3 py-1.5 border-b border-slate-800/50 hover:bg-slate-700/10 transition-colors"
                  >
                    <span className="font-mono text-[10px] text-slate-300 truncate pr-2">
                      {c.path.replace('src/', '')}
                    </span>
                    <span className="text-[10px] text-slate-400 text-right font-mono">
                      {c.lines.toLocaleString()}
                    </span>
                    <span className="text-[10px] text-slate-500 text-right font-mono">
                      {c.size_kb} KB
                    </span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
