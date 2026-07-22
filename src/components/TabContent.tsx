import { Suspense, lazy } from 'react';
import { TabErrorBoundary } from './TabErrorBoundary';
import type { Tab } from '../types';
import type { Trade, TradeStatistics, SystemSettings, AuditLogEntry } from '../lib/supabase';
import type { RegimeType } from '../hooks/useRegimeDetection';
import type { TickData } from '../hooks/useDerivTicks';

// ── Eagerly loaded (lightweight, shown on every tab switch) ────
import { StatsCards } from './StatsCards';
import { MarketData } from './MarketData';
import { RegimePanel } from './RegimePanel';
import { TradeExecutionPanel } from './TradeExecutionPanel';
import { ControlPanel } from './ControlPanel';
import { TradeHistory } from './TradeHistory';
import { BrokerConnectPanel } from './BrokerConnectPanel';
import { SettingsPanel } from './SettingsPanel';
import { AuditLog } from './AuditLog';

// ── Lazy loaded (heavy, only loaded when tab is active) ────────
const PnLChart = lazy(() => import('./PnLChart').then(m => ({ default: m.PnLChart })));
const RegimeDashboard = lazy(() => import('./RegimeDashboard').then(m => ({ default: m.RegimeDashboard })));
const PositionSizingPanel = lazy(() => import('./PositionSizingPanel').then(m => ({ default: m.PositionSizingPanel })));
const TradeEvidencePanel = lazy(() => import('./TradeEvidencePanel').then(m => ({ default: m.TradeEvidencePanel })));
const MLAuditPanel = lazy(() => import('./MLAuditPanel').then(m => ({ default: m.MLAuditPanel })));
const ShadowModePanel = lazy(() => import('./ShadowModePanel').then(m => ({ default: m.ShadowModePanel })));
const TradeJournalPanel = lazy(() => import('./TradeJournalPanel').then(m => ({ default: m.TradeJournalPanel })));
const ValidationDashboard = lazy(() => import('./ValidationDashboard').then(m => ({ default: m.ValidationDashboard })));
const ReviewPage = lazy(() => import('./ReviewPage').then(m => ({ default: m.ReviewPage })));

// ── Shared loading fallback ────────────────────────────────────
function TabLoader() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="flex flex-col items-center gap-3">
        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-500 text-xs">Loading...</p>
      </div>
    </div>
  );
}

// ── Props (only what tab content needs) ────────────────────────
interface TabContentProps {
  activeTab: Tab;

  // Trading data
  trades: Trade[];
  stats: TradeStatistics | null;
  settings: SystemSettings | null;
  auditLogs: AuditLogEntry[];

  // Market data
  tickData: TickData;
  regimeState: { regime: RegimeType; confidence: number; isTransitioning: boolean };
  isStrategyAllowed: boolean;

  // Trading controls
  botStatus: 'RUNNING' | 'STOPPED' | 'PAUSED';
  tradingToken: string;
  userToken: string;
  isAuthenticated: boolean;
  showAuthBanner: boolean;

  // Evidence / ML / Shadow / Journal
  evidenceLog: Array<{ timestamp: number; type: string; confidence: number; details: string }>;
  mlAuditState: { isRunning: boolean; lastAudit: unknown };
  shadowSignals: unknown[];
  shadowMetrics: unknown;
  shadowDailyMetrics: unknown[];
  journalEntries: unknown[];
  journalInsights: unknown;

  // Actions
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
  onOpenAuth: () => void;
  onSwitchSymbol: (symbol: string) => void;
  onReconnect: () => void;
  onSaveToken: (token: string) => void;
  onUpdateSettings: (updates: Partial<SystemSettings>) => void;
  onBuildEvidence: (data: unknown) => void;
  onGenerateShadowSignal: (data: unknown) => void;
  onAddJournalEntry: (entry: unknown) => void;
  onRunAudit: () => void;
  onGenerateWeeklyInsights: () => void;
}

export function TabContent({
  activeTab,
  trades,
  stats,
  settings,
  auditLogs,
  tickData,
  regimeState,
  isStrategyAllowed,
  botStatus,
  tradingToken,
  userToken,
  isAuthenticated,
  showAuthBanner,
  evidenceLog,
  mlAuditState,
  shadowSignals,
  shadowMetrics,
  shadowDailyMetrics,
  journalEntries,
  journalInsights,
  onStart,
  onStop,
  onReset,
  onOpenAuth,
  onSwitchSymbol,
  onReconnect,
  onSaveToken,
  onUpdateSettings,
  onBuildEvidence,
  onGenerateShadowSignal,
  onAddJournalEntry,
  onRunAudit,
  onGenerateWeeklyInsights,
}: TabContentProps) {
  return (
    <TabErrorBoundary tabName={activeTab}>
      {activeTab === 'dashboard' && (
        <DashboardTab
          trades={trades}
          stats={stats}
          settings={settings}
          auditLogs={auditLogs}
          tickData={tickData}
          regimeState={regimeState}
          isStrategyAllowed={isStrategyAllowed}
          botStatus={botStatus}
          tradingToken={tradingToken}
          userToken={userToken}
          isAuthenticated={isAuthenticated}
          showAuthBanner={showAuthBanner}
          onStart={onStart}
          onStop={onStop}
          onReset={onReset}
          onOpenAuth={onOpenAuth}
          onSwitchSymbol={onSwitchSymbol}
          onReconnect={onReconnect}
          onSaveToken={onSaveToken}
          onUpdateSettings={onUpdateSettings}
          onBuildEvidence={onBuildEvidence}
          onGenerateShadowSignal={onGenerateShadowSignal}
          onAddJournalEntry={onAddJournalEntry}
        />
      )}

      {activeTab === 'regimes' && (
        <Suspense fallback={<TabLoader />}>
          <RegimePanel regimeState={regimeState} />
          <RegimeDashboard />
        </Suspense>
      )}

      {activeTab === 'sizing' && (
        <Suspense fallback={<TabLoader />}>
          <PositionSizingPanel />
        </Suspense>
      )}

      {activeTab === 'evidence' && (
        <Suspense fallback={<TabLoader />}>
          <TradeEvidencePanel evidenceLog={evidenceLog} />
        </Suspense>
      )}

      {activeTab === 'mlaudit' && (
        <Suspense fallback={<TabLoader />}>
          <MLAuditPanel auditState={mlAuditState} onRunAudit={onRunAudit} />
        </Suspense>
      )}

      {activeTab === 'shadow' && (
        <Suspense fallback={<TabLoader />}>
          <ShadowModePanel signals={shadowSignals} metrics={shadowMetrics} dailyMetrics={shadowDailyMetrics} />
        </Suspense>
      )}

      {activeTab === 'journal' && (
        <Suspense fallback={<TabLoader />}>
          <TradeJournalPanel entries={journalEntries} insights={journalInsights} onGenerateInsights={onGenerateWeeklyInsights} />
        </Suspense>
      )}

      {activeTab === 'validation' && (
        <Suspense fallback={<TabLoader />}>
          <ValidationDashboard />
        </Suspense>
      )}

      {activeTab === 'review' && (
        <Suspense fallback={<TabLoader />}>
          <ReviewPage />
        </Suspense>
      )}
    </TabErrorBoundary>
  );
}

// ── Dashboard sub-component (eagerly loaded, largest section) ──

interface DashboardTabProps {
  trades: Trade[];
  stats: TradeStatistics | null;
  settings: SystemSettings | null;
  auditLogs: AuditLogEntry[];
  tickData: TickData;
  regimeState: { regime: RegimeType; confidence: number; isTransitioning: boolean };
  isStrategyAllowed: boolean;
  botStatus: 'RUNNING' | 'STOPPED' | 'PAUSED';
  tradingToken: string;
  userToken: string;
  isAuthenticated: boolean;
  showAuthBanner: boolean;
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
  onOpenAuth: () => void;
  onSwitchSymbol: (symbol: string) => void;
  onReconnect: () => void;
  onSaveToken: (token: string) => void;
  onUpdateSettings: (updates: Partial<SystemSettings>) => void;
  onBuildEvidence: (data: unknown) => void;
  onGenerateShadowSignal: (data: unknown) => void;
  onAddJournalEntry: (entry: unknown) => void;
}

function DashboardTab({
  trades,
  stats,
  settings,
  auditLogs,
  tickData,
  regimeState,
  isStrategyAllowed,
  botStatus,
  tradingToken,
  userToken,
  isAuthenticated,
  onOpenAuth,
  onSwitchSymbol,
  onReconnect,
  onSaveToken,
  onUpdateSettings,
  onStart,
  onStop,
  onReset,
  onBuildEvidence,
  onGenerateShadowSignal,
  onAddJournalEntry,
}: DashboardTabProps) {
  return (
    <>
      <StatsCards stats={stats} tickData={tickData} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        <div className="lg:col-span-2 space-y-4 sm:space-y-6">
          <MarketData
            tickData={tickData}
            onSwitchSymbol={onSwitchSymbol}
            onReconnect={onReconnect}
          />
          <RegimePanel regimeState={regimeState} />
          <TradeExecutionPanel
            tickData={tickData}
            apiToken={tradingToken}
            isAuthenticated={isAuthenticated}
            onSignInRequired={onOpenAuth}
            regimeState={regimeState}
            isStrategyAllowed={isStrategyAllowed}
            onBuildEvidence={onBuildEvidence}
            onGenerateShadowSignal={onGenerateShadowSignal}
            onAddJournalEntry={onAddJournalEntry}
          />
          <ControlPanel
            botStatus={botStatus}
            onStart={onStart}
            onStop={onStop}
            onReset={onReset}
            locked={!isAuthenticated}
            onLockedClick={onOpenAuth}
          />
          <Suspense fallback={<TabLoader />}>
            <PnLChart trades={trades} />
          </Suspense>
          <TradeHistory trades={trades} />
        </div>

        <div className="space-y-4 sm:space-y-6">
          <BrokerConnectPanel
            isAuthenticated={isAuthenticated}
            userToken={userToken}
            hasTradingToken={Boolean(tradingToken)}
            onSaveToken={onSaveToken}
            onSignIn={onOpenAuth}
          />
          {isAuthenticated && (
            <>
              <SettingsPanel settings={settings} onUpdate={onUpdateSettings} />
              <AuditLog logs={auditLogs} />
            </>
          )}
        </div>
      </div>
    </>
  );
}
