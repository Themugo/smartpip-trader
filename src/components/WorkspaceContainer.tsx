import { useState, useEffect, ReactNode } from 'react';
import { 
  Loader2, 
  AlertCircle, 
  RefreshCw, 
  Keyboard,
  Smartphone,
  Monitor
} from 'lucide-react';

// Base workspace component with required states
interface WorkspaceComponentProps {
  workspaceId: string;
}

interface WorkspaceState {
  loading: boolean;
  error: string | null;
  data: any;
}

// Loading State Component
function LoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-96 gap-4">
      <Loader2 className="w-12 h-12 text-blue-500 animate-spin" />
      <p className="text-slate-400 text-sm">{message}</p>
    </div>
  );
}

// Error State Component
function ErrorState({ 
  message, 
  onRetry 
}: { 
  message: string; 
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-96 gap-4">
      <AlertCircle className="w-12 h-12 text-red-500" />
      <p className="text-slate-400 text-sm">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Retry
        </button>
      )}
    </div>
  );
}

// Empty State Component
function EmptyState({ 
  title, 
  description, 
  action,
  icon
}: { 
  title: string; 
  description: string; 
  action?: { label: string; onClick: () => void };
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-96 gap-4">
      {icon && <div className="text-slate-600">{icon}</div>}
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <p className="text-slate-400 text-sm text-center max-w-md">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

// Success State Wrapper
function WorkspaceWrapper({ 
  children, 
  loading, 
  error, 
  onRetry,
  title,
  actions
}: { 
  children: ReactNode;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  title?: string;
  actions?: ReactNode;
}) {
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  
  return (
    <div className="space-y-6">
      {title && (
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white">{title}</h2>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

// Placeholder workspace for development
function PlaceholderWorkspace({ 
  name, 
  description 
}: { 
  name: string; 
  description: string;
}) {
  return (
    <div className="p-8">
      <div className="bg-slate-900/50 rounded-xl border border-slate-800 p-8 text-center">
        <h2 className="text-2xl font-bold text-white mb-4">{name}</h2>
        <p className="text-slate-400 mb-6">{description}</p>
        <div className="flex items-center justify-center gap-4 text-sm text-slate-500">
          <div className="flex items-center gap-2">
            <Monitor className="w-4 h-4" />
            Desktop Ready
          </div>
          <div className="flex items-center gap-2">
            <Smartphone className="w-4 h-4" />
            Mobile Ready
          </div>
          <div className="flex items-center gap-2">
            <Keyboard className="w-4 h-4" />
            Keyboard Navigation
          </div>
        </div>
      </div>
    </div>
  );
}

// Dashboard Workspace
export function DashboardWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Dashboard" 
        description="Your trading command center with real-time analytics and portfolio overview."
      />
    </WorkspaceWrapper>
  );
}

// Live Trading Workspace
export function LiveTradingWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Live Trading" 
        description="Execute trades in real-time with AI-powered decision support and risk management."
      />
    </WorkspaceWrapper>
  );
}

// Paper Trading Workspace
export function PaperTradingWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Paper Trading" 
        description="Practice trading strategies with simulated market conditions without financial risk."
      />
    </WorkspaceWrapper>
  );
}

// Backtesting Workspace
export function BacktestingWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Backtesting" 
        description="Test your strategies against historical market data with comprehensive performance analysis."
      />
    </WorkspaceWrapper>
  );
}

// Strategy Builder Workspace
export function StrategyBuilderWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Strategy Builder" 
        description="Create and customize trading strategies with our visual strategy builder."
      />
    </WorkspaceWrapper>
  );
}

// Replay Engine Workspace
export function ReplayEngineWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Replay Engine" 
        description="Review and analyze past trades with AI commentary and market annotations."
      />
    </WorkspaceWrapper>
  );
}

// Research Lab Workspace
export function ResearchLabWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Research Lab" 
        description="Conduct market research, analyze patterns, and develop new trading ideas."
      />
    </WorkspaceWrapper>
  );
}

// Analytics Workspace
export function AnalyticsWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Analytics" 
        description="Deep dive into your trading performance with comprehensive analytics and charts."
      />
    </WorkspaceWrapper>
  );
}

// Risk Center Workspace
export function RiskCenterWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Risk Center" 
        description="Monitor and manage your trading risk with real-time alerts and exposure tracking."
      />
    </WorkspaceWrapper>
  );
}

// Portfolio Workspace
export function PortfolioWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Portfolio" 
        description="Manage your trading portfolio across multiple accounts and brokers."
      />
    </WorkspaceWrapper>
  );
}

// Journal Workspace
export function JournalWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Trade Journal" 
        description="Document your trading decisions, lessons learned, and track your trading journal."
      />
    </WorkspaceWrapper>
  );
}

// Marketplace Workspace
export function MarketplaceWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Strategy Marketplace" 
        description="Browse, import, and share trading strategies with the community."
      />
    </WorkspaceWrapper>
  );
}

// AI Command Center Workspace
export function AICommandCenterWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="AI Command Center" 
        description="Unified AI interface for market analysis, trade explanations, and strategic insights."
      />
    </WorkspaceWrapper>
  );
}

// Notifications Workspace
export function NotificationsWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Notifications" 
        description="View all your trading alerts, system notifications, and activity history."
      />
    </WorkspaceWrapper>
  );
}

// Admin Workspace
export function AdminWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Administration" 
        description="Manage users, subscriptions, system settings, and view operational metrics."
      />
    </WorkspaceWrapper>
  );
}

// Settings Workspace
export function SettingsWorkspace({ workspaceId }: WorkspaceComponentProps) {
  return (
    <WorkspaceWrapper loading={false} error={null}>
      <PlaceholderWorkspace 
        name="Settings" 
        description="Configure your account, broker connections, preferences, and security settings."
      />
    </WorkspaceWrapper>
  );
}

// Workspace router
export function WorkspaceContainer({ workspaceId }: { workspaceId: string }) {
  const [state, setState] = useState<WorkspaceState>({
    loading: false,
    error: null,
    data: null,
  });

  useEffect(() => {
    // Reset state when workspace changes
    setState({ loading: false, error: null, data: null });
  }, [workspaceId]);

  const renderWorkspace = () => {
    switch (workspaceId) {
      case 'dashboard':
        return <DashboardWorkspace workspaceId={workspaceId} />;
      case 'live_trading':
        return <LiveTradingWorkspace workspaceId={workspaceId} />;
      case 'paper_trading':
        return <PaperTradingWorkspace workspaceId={workspaceId} />;
      case 'backtesting':
        return <BacktestingWorkspace workspaceId={workspaceId} />;
      case 'strategy_builder':
        return <StrategyBuilderWorkspace workspaceId={workspaceId} />;
      case 'replay':
        return <ReplayEngineWorkspace workspaceId={workspaceId} />;
      case 'research':
        return <ResearchLabWorkspace workspaceId={workspaceId} />;
      case 'analytics':
        return <AnalyticsWorkspace workspaceId={workspaceId} />;
      case 'risk_center':
        return <RiskCenterWorkspace workspaceId={workspaceId} />;
      case 'portfolio':
        return <PortfolioWorkspace workspaceId={workspaceId} />;
      case 'journal':
        return <JournalWorkspace workspaceId={workspaceId} />;
      case 'marketplace':
        return <MarketplaceWorkspace workspaceId={workspaceId} />;
      case 'ai_command_center':
        return <AICommandCenterWorkspace workspaceId={workspaceId} />;
      case 'notifications':
        return <NotificationsWorkspace workspaceId={workspaceId} />;
      case 'admin':
        return <AdminWorkspace workspaceId={workspaceId} />;
      case 'settings':
        return <SettingsWorkspace workspaceId={workspaceId} />;
      default:
        return <PlaceholderWorkspace name="Workspace" description="Select a workspace from the navigation." />;
    }
  };

  return (
    <div className="workspace-container" role="tabpanel" aria-label={`${workspaceId} workspace`}>
      {renderWorkspace()}
    </div>
  );
}
