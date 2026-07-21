import { useState, useEffect, useCallback, useRef } from 'react';
import { Header } from './components/Header';
import { StatsCards } from './components/StatsCards';
import { ControlPanel } from './components/ControlPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { TradeHistory } from './components/TradeHistory';
import { AuditLog } from './components/AuditLog';
import { PnLChart } from './components/PnLChart';
import { LandingPage } from './components/landing/LandingPage';
import { MarketData } from './components/MarketData';
import { TradeExecutionPanel } from './components/TradeExecutionPanel';
import { ValidationDashboard } from './components/ValidationDashboard';
import { RegimePanel } from './components/RegimePanel';
import { RegimeDashboard } from './components/RegimeDashboard';
import { PositionSizingPanel } from './components/PositionSizingPanel';
import { TradeEvidencePanel } from './components/TradeEvidencePanel';
import { MLAuditPanel } from './components/MLAuditPanel';
import { ShadowModePanel } from './components/ShadowModePanel';
import { TradeJournalPanel } from './components/TradeJournalPanel';
import { AuthModal } from './components/AuthModal';
import { api } from './lib/api';
import { supabase } from './lib/supabase';
import { useDerivTicks } from './hooks/useDerivTicks';
import { useRegimeDetection } from './hooks/useRegimeDetection';
import { useTradeEvidence } from './hooks/useTradeEvidence';
import { useMLAudit } from './hooks/useMLAudit';
import { useShadowMode } from './hooks/useShadowMode';
import { useTradeJournal } from './hooks/useTradeJournal';
import type { Trade, TradeStatistics, SystemSettings, AuditLogEntry, User } from './lib/supabase';

type Tab = 'dashboard' | 'regimes' | 'sizing' | 'evidence' | 'mlaudit' | 'shadow' | 'journal' | 'validation';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');

  const [trades, setTrades] = useState<Trade[]>([]);
  const [stats, setStats] = useState<TradeStatistics | null>(null);
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [botStatus, setBotStatus] = useState<'RUNNING' | 'STOPPED' | 'PAUSED'>('STOPPED');
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const apiToken = import.meta.env.VITE_DERIV_API_TOKEN || undefined;
  const { tickData, switchSymbol, reconnect } = useDerivTicks('R_100', apiToken);
  const { regimeState, isStrategyAllowed } = useRegimeDetection(tickData.digitHistory, tickData.price);
  const { evidenceLog, buildEvidence } = useTradeEvidence();
  const { state: mlAuditState, runAudit } = useMLAudit();
  const { signals: shadowSignals, metrics: shadowMetrics, dailyMetrics: shadowDailyMetrics, generateSignal } = useShadowMode();
  const { entries: journalEntries, addEntry, insights: journalInsights, generateWeeklyInsights } = useTradeJournal();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setAuthLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setAuthLoading(false);
      if (session?.user) setAuthOpen(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const fetchData = useCallback(async () => {
    if (!user) return;
    try {
      const [tradesData, statsData, settingsData, auditData] = await Promise.all([
        api.getTrades(),
        api.getStatistics(),
        api.getSettings(),
        api.getAuditLog(),
      ]);
      setTrades(tradesData || []);
      setStats(statsData || null);
      setSettings(settingsData || null);
      setAuditLogs(auditData || []);
      setConnected(true);
      setError(null);
    } catch (e: unknown) {
      setConnected(false);
      setError(e instanceof Error ? e.message : 'Failed to fetch data');
    }
  }, [user]);

  useEffect(() => {
    if (!user) return;
    fetchData();
    intervalRef.current = setInterval(fetchData, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchData, user]);

  const handleSignIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  };

  const handleSignUp = async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setActiveTab('dashboard');
  };

  const requireAuth = useCallback(() => {
    if (!user) {
      setAuthMode('login');
      setAuthOpen(true);
      return false;
    }
    return true;
  }, [user]);

  const logAction = useCallback(async (action: string, details?: Record<string, unknown>) => {
    try {
      await api.logAudit({ action, actor: user?.email || 'anonymous', details });
    } catch { /* ignore */ }
  }, [user]);

  const handleStart = async () => {
    if (!requireAuth()) return;
    setBotStatus('RUNNING');
    await logAction('START_BOT');
    if (settings) {
      await api.updateSettings({ auto_trading: true });
      setSettings({ ...settings, auto_trading: true });
    }
  };

  const handleStop = async () => {
    setBotStatus('STOPPED');
    await logAction('STOP_BOT');
    if (settings) {
      await api.updateSettings({ auto_trading: false });
      setSettings({ ...settings, auto_trading: false });
    }
  };

  const handleReset = async () => {
    await logAction('RESET_SESSION');
    fetchData();
  };

  const handleUpdateSettings = async (updates: Partial<SystemSettings>) => {
    if (!requireAuth()) return;
    await api.updateSettings(updates);
    await logAction('UPDATE_SETTINGS', updates);
    setSettings((prev) => (prev ? { ...prev, ...updates } : null));
  };

  useEffect(() => {
    if (trades.length >= 20) {
      const tradeHistory = trades.map(t => ({ profit: t.profit || 0, timestamp: new Date(t.entry_time).getTime() }));
      const strategyHistory = [{ 
        name: 'digit', 
        trades: trades.length, 
        wins: trades.filter(t => (t.profit || 0) > 0).length,
        losses: trades.filter(t => (t.profit || 0) < 0).length,
        pnl: trades.reduce((sum, t) => sum + (t.profit || 0), 0)
      }];
      runAudit(tradeHistory, strategyHistory);
    }
  }, [trades, runAudit]);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-slate-400 text-sm">Loading SmartPip...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <>
        <LandingPage
          tickData={tickData}
          onSwitchSymbol={switchSymbol}
          onReconnect={reconnect}
          regimeState={regimeState}
          isStrategyAllowed={isStrategyAllowed}
          onTrade={() => requireAuth()}
          onConnect={() => { setAuthMode('signup'); setAuthOpen(true); }}
        />
        <AuthModal
          open={authOpen}
          initialMode={authMode}
          onClose={() => setAuthOpen(false)}
          onSignIn={handleSignIn}
          onSignUp={handleSignUp}
        />
      </>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <Header botStatus={botStatus} connected={connected} userEmail={user.email} onSignOut={handleSignOut} />

      <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-6 pt-4">
        <div className="flex items-center gap-1 overflow-x-auto pb-2 scrollbar-hide">
          {[
            { id: 'dashboard', label: 'Dashboard' },
            { id: 'regimes', label: 'Regimes' },
            { id: 'sizing', label: 'Position Sizing' },
            { id: 'evidence', label: 'Evidence' },
            { id: 'mlaudit', label: 'ML Audit' },
            { id: 'shadow', label: 'Shadow Mode' },
            { id: 'journal', label: 'Journal' },
            { id: 'validation', label: 'Validation' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as Tab)}
              className={`px-3 sm:px-4 py-2 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-gradient-to-r from-blue-500/20 to-cyan-500/20 text-cyan-400 border border-cyan-500/30 shadow-lg shadow-cyan-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-6 py-4 sm:py-6 space-y-4 sm:space-y-6">
        {error && (
          <div className="p-3 sm:p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs sm:text-sm">
            {error}
          </div>
        )}

        {activeTab === 'dashboard' && (
          <>
            <StatsCards stats={stats} />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
              <div className="lg:col-span-2 space-y-4 sm:space-y-6">
                <MarketData tickData={tickData} onSwitchSymbol={switchSymbol} onReconnect={reconnect} />
                <RegimePanel regimeState={regimeState} />
                <TradeExecutionPanel
                  tickData={tickData}
                  apiToken={apiToken}
                  regimeState={regimeState}
                  isStrategyAllowed={isStrategyAllowed}
                  onBuildEvidence={buildEvidence}
                  onGenerateShadowSignal={generateSignal}
                  onAddJournalEntry={addEntry}
                />
                <ControlPanel botStatus={botStatus} onStart={handleStart} onStop={handleStop} onReset={handleReset} />
                <PnLChart trades={trades} />
                <TradeHistory trades={trades} />
              </div>
              <div className="space-y-4 sm:space-y-6">
                <SettingsPanel settings={settings} onUpdate={handleUpdateSettings} />
                <AuditLog logs={auditLogs} />
              </div>
            </div>
          </>
        )}

        {activeTab === 'regimes' && (<><RegimePanel regimeState={regimeState} /><RegimeDashboard /></>)}
        {activeTab === 'sizing' && (<PositionSizingPanel />)}
        {activeTab === 'evidence' && (<TradeEvidencePanel evidenceLog={evidenceLog} />)}
        {activeTab === 'mlaudit' && (
          <MLAuditPanel auditState={mlAuditState} onRunAudit={() => {
            const tradeHistory = trades.map(t => ({ profit: t.profit || 0, timestamp: new Date(t.entry_time).getTime() }));
            const strategyHistory = [{ 
        name: 'digit', 
        trades: trades.length, 
        wins: trades.filter(t => (t.profit || 0) > 0).length,
        losses: trades.filter(t => (t.profit || 0) < 0).length,
        pnl: trades.reduce((sum, t) => sum + (t.profit || 0), 0)
      }];
            runAudit(tradeHistory, strategyHistory);
          }} />
        )}
        {activeTab === 'shadow' && (<ShadowModePanel signals={shadowSignals} metrics={shadowMetrics} dailyMetrics={shadowDailyMetrics} />)}
        {activeTab === 'journal' && (<TradeJournalPanel entries={journalEntries} insights={journalInsights} onGenerateInsights={generateWeeklyInsights} />)}
        {activeTab === 'validation' && (<ValidationDashboard />)}
      </main>

      <footer className="border-t border-slate-800 mt-8 sm:mt-12 py-4 sm:py-6 px-3 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500">
          <span>SmartPip Trader v2.7.0</span>
          <span>Data persisted via Supabase</span>
        </div>
      </footer>
    </div>
  );
}
