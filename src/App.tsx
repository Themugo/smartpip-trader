import { useState, useCallback, useEffect } from 'react';
import { AppShell } from './components/AppShell';
import { TabContent } from './components/TabContent';
import { OnboardingWizard } from './components/OnboardingWizard';
import { AuthModal } from './components/AuthModal';
import { AuthPage } from './components/AuthPage';
import { EndUserShell, type EndUserView } from './components/EndUserShell';
import { EndUserDashboard } from './components/EndUserDashboard';
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
import { supabaseConfigured } from './lib/supabase';

export default function App() {
  // ── Auth ────────────────────────────────────────────────────
  const {
    user,
    loading: authLoading,
    hasCompletedOnboarding,
    signIn,
    signUp,
    resetPassword,
    signOut,
    completeOnboarding,
    showLoginModal,
  } = useAuth();

  const isAuthenticated = Boolean(user);

  // ── UI state ────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [endUserView, setEndUserView] = useState<EndUserView>('trade');
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
    fetchData, updateSettings, setError: setDataError,
  } = useTradingData(isAuthenticated);

  // ── Market data & hooks ─────────────────────────────────────
  const { tickData, switchSymbol, reconnect } = useDerivTicks('R_100');
  const { tradingToken, userToken, setUserToken } = useDerivToken(isAuthenticated);
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
    if (!settings) { setDataError('Trading preferences are still loading. Please try again.'); return; }
    if (!tickData.connected) { setDataError('Market feed is offline. Reconnect before enabling automation.'); return; }
    try {
      await updateSettings({ auto_trading: true });
      setBotStatus('RUNNING');
      await logAction('START_BOT');
    } catch {
      setBotStatus('STOPPED');
      throw new Error('Unable to enable auto execution.');
    }
  }, [isAuthenticated, settings, tickData.connected, logAction, updateSettings, setDataError]);

  const handleStop = useCallback(async () => {
    try {
      await updateSettings({ auto_trading: false });
      setBotStatus('STOPPED');
      await logAction('STOP_BOT');
    } catch {
      throw new Error('Unable to pause auto execution.');
    }
  }, [logAction, updateSettings]);

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

  // ── Authentication gate ────────────────────────────────────
  // In a configured production environment the customer enters through
  // Supabase Auth. The legacy offline shell remains available only when
  // Supabase is intentionally not configured for local development.
  if (!isAuthenticated && supabaseConfigured) {
    return (
      <AuthPage
        onSignIn={async (email, password) => { await signIn(email, password); }}
        onSignUp={async (email, password) => { await signUp(email, password); }}
        onResetPassword={async (email) => { await resetPassword(email); }}
        initialLogin={showLoginModal}
      />
    );
  }

  // ── Onboarding gate ─────────────────────────────────────────
  if (user && !hasCompletedOnboarding && !showOnboarding) {
    return (
      <OnboardingWizard
        onComplete={async (profile) => { await completeOnboarding(profile); setShowOnboarding(true); }}
        onSkip={async () => { await completeOnboarding(); }}
      />
    );
  }

  // ── Authenticated end-user product shell ────────────────────
  if (user) {
    return (
      <EndUserShell
        user={user}
        view={endUserView}
        onViewChange={setEndUserView}
        onSignOut={signOut}
        connected={tickData.connected}
      >
        <EndUserDashboard
          view={endUserView}
          userEmail={user.email || ''}
          tickData={tickData}
          trades={trades}
          stats={stats}
          settings={settings}
          dataLoading={dataLoading}
          onSwitchSymbol={switchSymbol}
          onReconnect={reconnect}
          onStartAuto={handleStart}
          onStopAuto={handleStop}
          onRefresh={fetchData}
        />
      </EndUserShell>
    );
  }

  // ── Main render (offline development shell) ─────────────────
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
          onResetPassword={resetPassword}
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
