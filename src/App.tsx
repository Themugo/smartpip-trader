import { useState, useCallback, useEffect } from 'react';
import { AppShell } from './components/AppShell';
import { TabContent } from './components/TabContent';
import { OnboardingWizard } from './components/OnboardingWizard';
import { AuthModal } from './components/AuthModal';
import { useAuth } from './hooks/useAuth';
import { useTradingData } from './hooks/useTradingData';
import { useDerivTicks } from './hooks/useDerivTicks';
import { useDerivToken } from './hooks/useDerivToken';
import { useRegimeDetection } from './hooks/useRegimeDetection';
import { useTradeEvidence } from './hooks/useTradeEvidence';
import { useMLAudit } from './hooks/useMLAudit';
import { useShadowMode } from './hooks/useShadowMode';
import { useTradeJournal } from './hooks/useTradeJournal';
import type { Tab, Workspace, BotStatus } from './types';
import type { RegimeType } from './hooks/useRegimeDetection';
import { api } from './lib/api';
import { supabase, supabaseConfigured } from './lib/supabase';

export default function App() {
  // ── Auth ────────────────────────────────────────────────────
  const {
    user,
    loading: authLoading,
    hasCompletedOnboarding,
    signIn,
    signUp,
    signOut,
    completeOnboarding,
    showLoginModal,
  } = useAuth();

  const isAuthenticated = Boolean(user);

  // ── UI state ────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace>('dashboard');
  const [botStatus, setBotStatus] = useState<BotStatus>('STOPPED');
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [authTimedOut, setAuthTimedOut] = useState(false);

  // Safety net: force loading=false after 8s so the app is never stuck
  useEffect(() => {
    if (authLoading) {
      const timer = setTimeout(() => setAuthTimedOut(true), 8000);
      return () => clearTimeout(timer);
    }
  }, [authLoading]);

  // ── Trading data ────────────────────────────────────────────
  const {
    trades, stats, settings, auditLogs, error: dataError, loading: dataLoading,
    fetchData, updateSettings, setError: setDataError, retry: retryData,
  } = useTradingData(isAuthenticated);

  // ── Market data & hooks ─────────────────────────────────────
  const { tickData, switchSymbol, reconnect } = useDerivTicks('R_100');
  const { tradingToken, userToken, setUserToken, hasTradingToken } = useDerivToken(isAuthenticated);
  const { regimeState, isStrategyAllowed } = useRegimeDetection(tickData.digitHistory, tickData.price);
  const { evidenceLog, buildEvidence } = useTradeEvidence();
  const { state: mlAuditState, error: mlAuditError, runAudit } = useMLAudit();
  const { signals: shadowSignals, metrics: shadowMetrics, dailyMetrics: shadowDailyMetrics, loading: shadowLoading, error: shadowError, generateSignal, refresh: refreshShadow } = useShadowMode();
  const { entries: journalEntries, insights: journalInsights, loading: journalLoading, error: journalError, addEntry, generateWeeklyInsights } = useTradeJournal();

  // ── Journal entry wrapper ───────────────────────────────────
  const handleAddJournalEntry = useCallback((entry: {
    timestamp: number; symbol: string; contractType: string;
    entryPrice: number; entryDigit: number; amount: number;
    confidence: number; regime: string; entryConditions: string[];
    exitConditions: string[]; notes: string;
    profit?: number | null; exitPrice?: number | null;
    exitDigit?: number | null; pnl?: number | null;
  }) => {
    addEntry({
      ...entry,
      regime: entry.regime as RegimeType,
      profit: entry.profit ?? null,
      exitPrice: entry.exitPrice ?? null,
      exitDigit: entry.exitDigit ?? null,
      pnl: entry.pnl ?? null,
    });
  }, [addEntry]);

  // ── Audit logging ───────────────────────────────────────────
  const logAction = useCallback(async (action: string, details?: Record<string, unknown>) => {
    try {
      await api.logAudit({ action, actor: user?.email || 'anonymous', details });
    } catch { /* silent */ }
  }, [user]);

  // ── Bot controls ────────────────────────────────────────────
  const handleStart = useCallback(async () => {
    if (!isAuthenticated) { setShowAuthModal(true); return; }
    if (!hasTradingToken) { setDataError('Add your Deriv API token in the sidebar before starting the bot.'); return; }
    setBotStatus('RUNNING');
    await logAction('START_BOT');
    if (settings) { await api.updateSettings({ auto_trading: true }); updateSettings({ auto_trading: true }); }
  }, [isAuthenticated, hasTradingToken, logAction, settings, updateSettings, setDataError]);

  const handleStop = useCallback(async () => {
    setBotStatus('STOPPED');
    await logAction('STOP_BOT');
    if (settings) { await api.updateSettings({ auto_trading: false }); updateSettings({ auto_trading: false }); }
  }, [logAction, settings, updateSettings]);

  const handleReset = useCallback(async () => {
    await logAction('RESET_SESSION');
    fetchData();
  }, [logAction, fetchData]);

  const handleUpdateSettings = useCallback(async (updates: Record<string, unknown>) => {
    await api.updateSettings(updates);
    await logAction('UPDATE_SETTINGS', updates);
    updateSettings(updates as Partial<import('./lib/supabase').SystemSettings>);
  }, [logAction, updateSettings]);

  // ── ML audit on trades change ───────────────────────────────
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

  // ── Loading screen (max 8s, never permanent) ────────────────
  if (authLoading && !authTimedOut) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-slate-400 text-sm">Loading SmartPip...</p>
          <p className="text-slate-600 text-xs">Connecting to authentication</p>
        </div>
      </div>
    );
  }

  // ── Onboarding gate ─────────────────────────────────────────
  if (user && !hasCompletedOnboarding && !showOnboarding) {
    return (
      <OnboardingWizard
        onComplete={() => { completeOnboarding(); setShowOnboarding(true); }}
        onSkip={completeOnboarding}
      />
    );
  }

  // ── Main render ─────────────────────────────────────────────
  return (
    <>
      {/* Offline / auth-failed banner */}
      {(authTimedOut || (!supabaseConfigured && !isAuthenticated)) && (
        <div className="fixed top-0 left-0 right-0 z-[100] bg-amber-900/90 text-amber-100 text-xs text-center py-1.5 px-4 backdrop-blur-sm">
          Running in offline demo mode — trades are simulated.{' '}
          {authTimedOut && (
            <button
              onClick={() => window.location.reload()}
              className="underline hover:text-white ml-2"
            >
              Retry connection
            </button>
          )}
        </div>
      )}

      {showAuthModal && (
        <AuthModal
          onSignIn={signIn}
          onSignUp={signUp}
          onClose={() => setShowAuthModal(false)}
        />
      )}

      <AppShell
        activeTab={activeTab}
        activeWorkspace={activeWorkspace}
        botStatus={botStatus}
        isConnected={tickData.connected}
        user={user}
        isAuthenticated={isAuthenticated}
        showAuthBanner={!isAuthenticated}
        error={dataError}
        onTabChange={setActiveTab}
        onWorkspaceChange={setActiveWorkspace}
        onOpenAuth={() => setShowAuthModal(true)}
        onSignOut={signOut}
        onDismissError={() => setDataError(null)}
      >
        <TabContent
          activeTab={activeTab}
          trades={trades}
          stats={stats}
          settings={settings}
          auditLogs={auditLogs}
          tickData={tickData}
          regimeState={regimeState}
          isStrategyAllowed={isStrategyAllowed}
          botStatus={botStatus}
          tradingToken={tradingToken ?? ''}
          userToken={userToken}
          isAuthenticated={isAuthenticated}
          showAuthBanner={!isAuthenticated}
          evidenceLog={evidenceLog}
          mlAuditState={mlAuditState}
          mlAuditError={mlAuditError}
          shadowSignals={shadowSignals}
          shadowMetrics={shadowMetrics}
          shadowDailyMetrics={shadowDailyMetrics}
          shadowLoading={shadowLoading}
          shadowError={shadowError}
          journalEntries={journalEntries}
          journalInsights={journalInsights}
          journalLoading={journalLoading}
          journalError={journalError}
          dataLoading={dataLoading}
          onStart={handleStart}
          onStop={handleStop}
          onReset={handleReset}
          onOpenAuth={() => setShowAuthModal(true)}
          onSwitchSymbol={switchSymbol}
          onReconnect={reconnect}
          onSaveToken={setUserToken}
          onUpdateSettings={handleUpdateSettings}
          onBuildEvidence={buildEvidence}
          onGenerateShadowSignal={generateSignal}
          onAddJournalEntry={handleAddJournalEntry}
          onRunAudit={() => {
            const th = trades.map(t => ({ profit: t.profit || 0, timestamp: new Date(t.entry_time).getTime() }));
            const sh = trades.map(t => ({ name: t.type || 'digit', trades: 1, wins: (t.profit || 0) > 0 ? 1 : 0, losses: (t.profit || 0) <= 0 ? 1 : 0, pnl: t.profit || 0 }));
            runAudit(th, sh);
          }}
          onGenerateWeeklyInsights={generateWeeklyInsights}
        />
      </AppShell>
    </>
  );
}
