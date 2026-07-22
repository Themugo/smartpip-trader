import { Suspense, lazy } from 'react';
import { TabErrorBoundary } from './TabErrorBoundary';
import type { Tab } from '../types';
import type { Trade, TradeStatistics, SystemSettings, AuditLogEntry } from '../lib/supabase';
import type { RegimeType, RegimeState } from '../hooks/useRegimeDetection';
import type { TickData } from '../hooks/useDerivTicks';
import type { TradeEvidence } from '../hooks/useTradeEvidence';
import type { MLAuditState } from '../hooks/useMLAudit';
import type { ShadowSignal, ShadowMetrics, ShadowDailyMetric } from '../hooks/useShadowMode';
import type { JournalEntry, WeeklyInsight } from '../hooks/useTradeJournal';

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
  regimeState: RegimeState;
  isStrategyAllowed: (strategyType: string) => { allowed: boolean; reason: string };

  // Trading controls
  botStatus: 'RUNNING' | 'STOPPED' | 'PAUSED';
  tradingToken: string;
  userToken: string;
  isAuthenticated: boolean;
  showAuthBanner: boolean;

  // Evidence / ML / Shadow / Journal
  evidenceLog: TradeEvidence[];
  mlAuditState: MLAuditState;
  mlAuditError: string | null;
  shadowSignals: ShadowSignal[];
  shadowMetrics: ShadowMetrics;
  shadowDailyMetrics: ShadowDailyMetric[];
  shadowLoading: boolean;
  shadowError: string | null;
  journalEntries: JournalEntry[];
  journalInsights: WeeklyInsight[];
  journalLoading: boolean;
  journalError: string | null;
  dataLoading: boolean;

  // Actions
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
  onOpenAuth: () => void;
  onSwitchSymbol: (symbol: string) => void;
  onReconnect: () => void;
  onSaveToken: (token: string) => void;
  onUpdateSettings: (updates: Partial<SystemSettings>) => void;
  onBuildEvidence: (
    symbol: string,
    contractType: string,
    amount: number,
    digitHistory: number[],
    price: number,
    regime: RegimeType,
    regimeConfidence: number,
    sizingAdjustments: { name: string; factor: number }[],
    isStrategyAllowed: boolean,
    strategyBlockReason: string,
    isGloballyBlocked: boolean,
    globalBlockReason: string | null,
  ) => TradeEvidence;
  onGenerateShadowSignal: (
    symbol: string,
    contractType: string,
    predictedDirection: string,
    confidence: number,
    expectedOutcome: 'win' | 'loss',
    expectedPnl: number,
    latencyMs: number,
    modelVersion?: string,
  ) => Promise<ShadowSignal>;
  onAddJournalEntry: (entry: {
    timestamp: number; symbol: string; contractType: string;
    entryPrice: number; entryDigit: number; amount: number;
    confidence: number; regime: string; entryConditions: string[];
    exitConditions: string[]; notes: string;
    profit?: number | null; exitPrice?: number | null;
    exitDigit?: number | null; pnl?: number | null;
  }) => void;
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
  mlAuditError,
  shadowSignals,
  shadowMetrics,
  shadowDailyMetrics,
  shadowLoading,
  shadowError,
  journalEntries,
  journalInsights,
  journalLoading,
  journalError,
  dataLoading,
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
          <MLAuditPanel auditState={mlAuditState} error={mlAuditError} onRunAudit={onRunAudit} />
        </Suspense>
      )}

      {activeTab === 'shadow' && (
        <Suspense fallback={<TabLoader />}>
          <ShadowModePanel signals={shadowSignals} metrics={shadowMetrics} dailyMetrics={shadowDailyMetrics} loading={shadowLoading} error={shadowError} />
        </Suspense>
      )}

      {activeTab === 'journal' && (
        <Suspense fallback={<TabLoader />}>
          <TradeJournalPanel entries={journalEntries} insights={journalInsights} loading={journalLoading} error={journalError} onGenerateInsights={onGenerateWeeklyInsights} />
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
  regimeState: RegimeState;
  isStrategyAllowed: (strategyType: string) => { allowed: boolean; reason: string };
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
  onBuildEvidence: TabContentProps['onBuildEvidence'];
  onGenerateShadowSignal: TabContentProps['onGenerateShadowSignal'];
  onAddJournalEntry: TabContentProps['onAddJournalEntry'];
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
