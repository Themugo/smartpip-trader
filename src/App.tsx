import { useState, useEffect, useCallback, useRef } from 'react';
import { Header } from './components/Header';
import { StatsCards } from './components/StatsCards';
import { ControlPanel } from './components/ControlPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { TradeHistory } from './components/TradeHistory';
import { AuditLog } from './components/AuditLog';
import { PnLChart } from './components/PnLChart';
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
import { ReviewPage } from './components/ReviewPage';
import { WorkspaceNav } from './components/WorkspaceNav';
import { OnboardingWizard } from './components/OnboardingWizard';
import { AuthModal } from './components/AuthModal';
import { BrokerConnectPanel } from './components/BrokerConnectPanel';
import { api } from './lib/api';
import { supabase } from './lib/supabase';
import { useDerivTicks } from './hooks/useDerivTicks';
import { useDerivToken } from './hooks/useDerivToken';
import { useRegimeDetection } from './hooks/useRegimeDetection';
import { useTradeEvidence } from './hooks/useTradeEvidence';
import { useMLAudit } from './hooks/useMLAudit';
import { useShadowMode } from './hooks/useShadowMode';
import { useTradeJournal } from './hooks/useTradeJournal';
import type { Trade, TradeStatistics, SystemSettings, AuditLogEntry, User } from './lib/supabase';
import type { RegimeType } from './hooks/useRegimeDetection';

type Tab = 'dashboard' | 'regimes' | 'sizing' | 'evidence' | 'mlaudit' | 'shadow' | 'journal' | 'validation' | 'review';
type Workspace = 'dashboard' | 'live_trading' | 'paper_trading' | 'backtesting' | 'strategy_builder' | 'analytics' | 'risk_center' | 'notifications' | 'ai_command_center' | 'developer_console' | 'settings';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [hasCompletedOnboarding, setHasCompletedOnboarding] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace>('dashboard');

  const [trades, setTrades] = useState<Trade[]>([]);
  const [stats, setStats] = useState<TradeStatistics | null>(null);
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [botStatus, setBotStatus] = useState<'RUNNING' | 'STOPPED' | 'PAUSED'>('STOPPED');
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isAuthenticated = Boolean(user);
  const { tickData, switchSymbol, reconnect } = useDerivTicks('R_100');
  const { tradingToken, userToken, setUserToken, hasTradingToken } = useDerivToken(isAuthenticated);
  const { regimeState, isStrategyAllowed } = useRegimeDetection(tickData.digitHistory, tickData.price);
  const { evidenceLog, buildEvidence } = useTradeEvidence();
  const { state: mlAuditState, runAudit } = useMLAudit();
  const { signals: shadowSignals, metrics: shadowMetrics, dailyMetrics: shadowDailyMetrics, generateSignal } = useShadowMode();
  const { entries: journalEntries, addEntry, insights: journalInsights, generateWeeklyInsights } = useTradeJournal();
  
  // Wrapper for addEntry to match expected type
  const handleAddJournalEntry = (entry: {
    timestamp: number;
    symbol: string;
    contractType: string;
    entryPrice: number;
    entryDigit: number;
    amount: number;
    confidence: number;
    regime: string;
    entryConditions: string[];
    exitConditions: string[];
    notes: string;
    profit?: number | null;
    exitPrice?: number | null;
    exitDigit?: number | null;
    pnl?: number | null;
  }) => {
    addEntry({
      timestamp: entry.timestamp,
      symbol: entry.symbol,
      contractType: entry.contractType,
      entryPrice: entry.entryPrice,
      entryDigit: entry.entryDigit,
      amount: entry.amount,
      confidence: entry.confidence,
      regime: entry.regime as RegimeType,
      entryConditions: entry.entryConditions,
      exitConditions: entry.exitConditions,
      notes: entry.notes,
      profit: entry.profit ?? null,
      exitPrice: entry.exitPrice ?? null,
      exitDigit: entry.exitDigit ?? null,
      pnl: entry.pnl ?? null,
    });
  };

  // Auth state (optional — market data is public)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('login') === '1') {
      setShowAuthModal(true);
    }

    const supabaseConfigured = Boolean(
      import.meta.env.VITE_SUPABASE_URL && import.meta.env.VITE_SUPABASE_ANON_KEY
    );

    if (!supabaseConfigured) {
      setAuthLoading(false);
      return;
    }

    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        // Check if user has completed onboarding
        const onboardingCompleted = localStorage.getItem('onboarding_completed');
        setHasCompletedOnboarding(!!onboardingCompleted);
      }
      setAuthLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        const onboardingCompleted = localStorage.getItem('onboarding_completed');
        setHasCompletedOnboarding(!!onboardingCompleted);
      }
      setAuthLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const [tradesRes, statsRes, settingsRes, auditRes] = await Promise.all([
        api.getTrades(),
        api.getStatistics(),
        api.getSettings(),
        api.getAuditLog(),
      ]);
      setTrades((tradesRes.data as Trade[]) ?? []);
      setStats((statsRes.data as TradeStatistics) ?? null);
      setSettings((settingsRes.data as SystemSettings) ?? null);
      setAuditLogs((auditRes.data as AuditLogEntry[]) ?? []);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to fetch account data');
    }
  }, []);

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
  };

  const logAction = useCallback(async (action: string, details?: Record<string, unknown>) => {
    try {
      await api.logAudit({
        action,
        actor: user?.email || 'anonymous',
        details,
      });
    } catch {
      // Silently fail audit logging
    }
  }, [user]);

  const openAuthModal = useCallback(() => setShowAuthModal(true), []);

  const handleStart = async () => {
    if (!isAuthenticated) {
      openAuthModal();
      return;
    }
    if (!hasTradingToken) {
      setError('Add your Deriv API token in the sidebar before starting the bot.');
      return;
    }
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
    await api.updateSettings(updates);
    await logAction('UPDATE_SETTINGS', updates);
    setSettings((prev) => (prev ? { ...prev, ...updates } : null));
  };

  // Run ML audit when trades change
  useEffect(() => {
    if (trades.length >= 20) {
      const tradeHistory = trades.map(t => ({
        profit: t.profit || 0,
        timestamp: new Date(t.entry_time).getTime(),
      }));
      const strategyHistory = trades.map(t => ({
        name: t.type || 'digit',
        trades: 1,
        wins: (t.profit || 0) > 0 ? 1 : 0,
        losses: (t.profit || 0) <= 0 ? 1 : 0,
        pnl: t.profit || 0,
      }));
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

  if (user && !hasCompletedOnboarding && !showOnboarding) {
    return (
      <OnboardingWizard
        onComplete={() => {
          localStorage.setItem('onboarding_completed', 'true');
          setHasCompletedOnboarding(true);
          setShowOnboarding(true);
        }}
        onSkip={() => {
          localStorage.setItem('onboarding_completed', 'true');
          setHasCompletedOnboarding(true);
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 flex">
      {showAuthModal && (
        <AuthModal
          onSignIn={handleSignIn}
          onSignUp={handleSignUp}
          onClose={() => setShowAuthModal(false)}
        />
      )}

      {!isAuthenticated && (
        <div className="fixed top-0 left-0 right-0 z-40 bg-emerald-600/90 text-white text-center text-xs sm:text-sm py-2 px-4">
          Public mode — live Deriv market data is free. Sign in only when you want to place live trades.
        </div>
      )}

      {/* Workspace Navigation Sidebar */}
      <WorkspaceNav
        currentWorkspace={activeWorkspace}
        onWorkspaceChange={(workspaceId) => setActiveWorkspace(workspaceId as Workspace)}
      />

      <div className={`flex-1 flex flex-col ${!isAuthenticated ? 'pt-9' : ''}`}>
        <Header
          botStatus={botStatus}
          connected={tickData.connected}
          userEmail={user?.email}
          isGuest={!isAuthenticated}
          onSignIn={openAuthModal}
          onSignOut={handleSignOut}
        />

        {/* Tab Navigation */}
        <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-6 pt-4">
          <div className="flex items-center gap-1 bg-slate-900 rounded-lg p-1 w-fit border border-slate-700 flex-wrap">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                activeTab === 'dashboard'
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setActiveTab('regimes')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                activeTab === 'regimes'
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Regimes
            </button>
            <button
              onClick={() => setActiveTab('sizing')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                activeTab === 'sizing'
                  ? 'bg-blue-500/20 text-blue-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Sizing
          </button>
          <button
            onClick={() => setActiveTab('evidence')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              activeTab === 'evidence'
                ? 'bg-blue-500/20 text-blue-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Evidence
          </button>
          <button
            onClick={() => setActiveTab('mlaudit')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              activeTab === 'mlaudit'
                ? 'bg-blue-500/20 text-blue-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            ML Audit
          </button>
          <button
            onClick={() => setActiveTab('shadow')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              activeTab === 'shadow'
                ? 'bg-blue-500/20 text-blue-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Shadow
          </button>
          <button
            onClick={() => setActiveTab('journal')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              activeTab === 'journal'
                ? 'bg-blue-500/20 text-blue-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Journal
          </button>
          <button
            onClick={() => setActiveTab('validation')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              activeTab === 'validation'
                ? 'bg-blue-500/20 text-blue-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Validation
          </button>
          <button
            onClick={() => setActiveTab('review')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              activeTab === 'review'
                ? 'bg-violet-500/20 text-violet-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Review
          </button>
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
            <StatsCards stats={stats} tickData={tickData} />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
              <div className="lg:col-span-2 space-y-4 sm:space-y-6">
                <MarketData
                  tickData={tickData}
                  onSwitchSymbol={switchSymbol}
                  onReconnect={reconnect}
                />
                <RegimePanel regimeState={regimeState} />
                <TradeExecutionPanel
                  tickData={tickData}
                  apiToken={tradingToken}
                  isAuthenticated={isAuthenticated}
                  onSignInRequired={openAuthModal}
                  regimeState={regimeState}
                  isStrategyAllowed={isStrategyAllowed}
                  onBuildEvidence={buildEvidence}
                  onGenerateShadowSignal={generateSignal}
                  onAddJournalEntry={handleAddJournalEntry}
                />
                <ControlPanel
                  botStatus={botStatus}
                  onStart={handleStart}
                  onStop={handleStop}
                  onReset={handleReset}
                  locked={!isAuthenticated}
                  onLockedClick={openAuthModal}
                />
                <PnLChart trades={trades} />
                <TradeHistory trades={trades} />
              </div>

              <div className="space-y-4 sm:space-y-6">
                <BrokerConnectPanel
                  isAuthenticated={isAuthenticated}
                  userToken={userToken}
                  hasTradingToken={hasTradingToken}
                  onSaveToken={setUserToken}
                  onSignIn={openAuthModal}
                />
                {isAuthenticated && (
                  <>
                    <SettingsPanel settings={settings} onUpdate={handleUpdateSettings} />
                    <AuditLog logs={auditLogs} />
                  </>
                )}
              </div>
            </div>
          </>
        )}

        {activeTab === 'regimes' && (
          <>
            <RegimePanel regimeState={regimeState} />
            <RegimeDashboard />
          </>
        )}

        {activeTab === 'sizing' && (
          <PositionSizingPanel />
        )}

        {activeTab === 'evidence' && (
          <TradeEvidencePanel evidenceLog={evidenceLog} />
        )}

        {activeTab === 'mlaudit' && (
          <MLAuditPanel auditState={mlAuditState} onRunAudit={() => {
            const tradeHistory = trades.map(t => ({
              profit: t.profit || 0,
              timestamp: new Date(t.entry_time).getTime(),
            }));
            const strategyHistory = trades.map(t => ({
              name: t.type || 'digit',
              trades: 1,
              wins: (t.profit || 0) > 0 ? 1 : 0,
              losses: (t.profit || 0) <= 0 ? 1 : 0,
              pnl: t.profit || 0,
            }));
            runAudit(tradeHistory, strategyHistory);
          }} />
        )}

        {activeTab === 'shadow' && (
          <ShadowModePanel signals={shadowSignals} metrics={shadowMetrics} dailyMetrics={shadowDailyMetrics} />
        )}

        {activeTab === 'journal' && (
          <TradeJournalPanel entries={journalEntries} insights={journalInsights} onGenerateInsights={generateWeeklyInsights} />
        )}

        {activeTab === 'validation' && (
          <ValidationDashboard />
        )}

        {activeTab === 'review' && (
          <ReviewPage />
        )}
      </main>

      <footer className="border-t border-slate-800 mt-8 sm:mt-12 py-4 sm:py-6 px-3 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500">
          <span>SmartPip Trader v4.0 — Public market data via Deriv</span>
          <span>{tickData.connected ? 'Live feed connected' : 'Connecting to Deriv...'}</span>
        </div>
      </footer>
      </div>
    </div>
  );
}
