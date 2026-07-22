import { type ReactNode } from 'react';
import { Header } from './Header';
import { WorkspaceNav } from './WorkspaceNav';
import type { Tab, Workspace, BotStatus } from '../types';
import type { User } from '../lib/supabase';

interface AppShellProps {
  activeTab: Tab;
  activeWorkspace: Workspace;
  botStatus: BotStatus;
  isConnected: boolean;
  user: User | null;
  isAuthenticated: boolean;
  showAuthBanner: boolean;
  error: string | null;
  onTabChange: (tab: Tab) => void;
  onWorkspaceChange: (workspace: Workspace) => void;
  onOpenAuth: () => void;
  onSignOut: () => void;
  onDismissError: () => void;
  children: ReactNode;
}

const TABS: { id: Tab; label: string; activeClass: string }[] = [
  { id: 'dashboard', label: 'Dashboard', activeClass: 'bg-blue-500/20 text-blue-400' },
  { id: 'regimes', label: 'Regimes', activeClass: 'bg-blue-500/20 text-blue-400' },
  { id: 'sizing', label: 'Sizing', activeClass: 'bg-blue-500/20 text-blue-400' },
  { id: 'evidence', label: 'Evidence', activeClass: 'bg-blue-500/20 text-blue-400' },
  { id: 'mlaudit', label: 'ML Audit', activeClass: 'bg-blue-500/20 text-blue-400' },
  { id: 'shadow', label: 'Shadow', activeClass: 'bg-blue-500/20 text-blue-400' },
  { id: 'journal', label: 'Journal', activeClass: 'bg-blue-500/20 text-blue-400' },
  { id: 'validation', label: 'Validation', activeClass: 'bg-blue-500/20 text-blue-400' },
  { id: 'review', label: 'Review', activeClass: 'bg-violet-500/20 text-violet-400' },
];

export function AppShell({
  activeTab,
  activeWorkspace,
  botStatus,
  isConnected,
  user,
  isAuthenticated,
  showAuthBanner,
  error,
  onTabChange,
  onWorkspaceChange,
  onOpenAuth,
  onSignOut,
  onDismissError,
  children,
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-slate-950 flex">
      {showAuthBanner && (
        <div className="fixed top-0 left-0 right-0 z-40 bg-emerald-600/90 text-white text-center text-xs sm:text-sm py-2 px-4">
          Public mode — live Deriv market data is free. Sign in only when you want to place live trades.
        </div>
      )}

      <WorkspaceNav
        currentWorkspace={activeWorkspace}
        onWorkspaceChange={(id) => onWorkspaceChange(id as Workspace)}
      />

      <div className={`flex-1 flex flex-col ${showAuthBanner ? 'pt-9' : ''}`}>
        <Header
          botStatus={botStatus}
          connected={isConnected}
          userEmail={user?.email}
          isGuest={!isAuthenticated}
          onSignIn={onOpenAuth}
          onSignOut={onSignOut}
        />

        {/* Tab Navigation */}
        <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-6 pt-4">
          <div className="flex items-center gap-1 bg-slate-900 rounded-lg p-1 w-fit border border-slate-700 flex-wrap">
            {TABS.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? tab.activeClass
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>

        <main className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-6 py-4 sm:py-6 space-y-4 sm:space-y-6 w-full">
          {error && (
            <div className="flex items-center justify-between p-3 sm:p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs sm:text-sm">
              <span>{error}</span>
              <button
                onClick={onDismissError}
                className="ml-3 text-red-400/60 hover:text-red-400 text-xs shrink-0"
              >
                Dismiss
              </button>
            </div>
          )}
          {children}
        </main>

        <footer className="border-t border-slate-800 mt-8 sm:mt-12 py-4 sm:py-6 px-3 sm:px-6">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500">
            <span>SmartPip Trader v4.0 — Public market data via Deriv</span>
            <span>{isConnected ? 'Live feed connected' : 'Connecting to Deriv...'}</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
