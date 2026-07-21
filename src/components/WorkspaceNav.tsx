/**
 * Workspace Navigation Component
 * 
 * Professional workspace navigation for the trading platform with:
 * - Tab-based navigation
 * - Favorites support
 * - Quick access shortcuts
 */

import React, { useState, useEffect } from 'react';
import { api } from '../lib/api_v2';

interface Workspace {
  id: string;
  type: string;
  name: string;
  description: string;
  icon: string;
  route: string;
  order: number;
  is_default: boolean;
}

interface WorkspaceNavProps {
  currentWorkspace?: string;
  onWorkspaceChange: (workspaceId: string) => void;
  collapsed?: boolean;
}

const WORKSPACE_ICONS: Record<string, React.ReactNode> = {
  dashboard: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  ),
  live_trading: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
  paper_trading: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  backtesting: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  ),
  strategy_builder: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    </svg>
  ),
  analytics: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  ),
  risk_center: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  notifications: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
    </svg>
  ),
  ai_command_center: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  ),
  developer_console: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
    </svg>
  ),
  settings: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    </svg>
  ),
};

const DEFAULT_WORKSPACES: Workspace[] = [
  { id: 'dashboard', type: 'dashboard', name: 'Dashboard', description: 'Overview', icon: 'dashboard', route: '/dashboard', order: 1, is_default: true },
  { id: 'live_trading', type: 'live_trading', name: 'Live Trading', description: 'Real-time trading', icon: 'live_trading', route: '/live-trading', order: 2, is_default: false },
  { id: 'paper_trading', type: 'paper_trading', name: 'Paper Trading', description: 'Practice mode', icon: 'paper_trading', route: '/paper-trading', order: 3, is_default: false },
  { id: 'backtesting', type: 'backtesting', name: 'Backtesting', description: 'Strategy testing', icon: 'backtesting', route: '/backtesting', order: 4, is_default: false },
  { id: 'strategy_builder', type: 'strategy_builder', name: 'Strategy Builder', description: 'Build strategies', icon: 'strategy_builder', route: '/strategy-builder', order: 5, is_default: false },
  { id: 'analytics', type: 'analytics', name: 'Analytics', description: 'Performance analysis', icon: 'analytics', route: '/analytics', order: 6, is_default: false },
  { id: 'risk_center', type: 'risk_center', name: 'Risk Center', description: 'Risk management', icon: 'risk_center', route: '/risk-center', order: 7, is_default: false },
  { id: 'notifications', type: 'notifications', name: 'Notifications', description: 'Alerts & history', icon: 'notifications', route: '/notifications', order: 8, is_default: false },
  { id: 'ai_command_center', type: 'ai_command_center', name: 'AI Command Center', description: 'AI control', icon: 'ai_command_center', route: '/ai-command-center', order: 9, is_default: false },
  { id: 'developer_console', type: 'developer_console', name: 'Developer Console', description: 'Dev tools', icon: 'developer_console', route: '/developer-console', order: 10, is_default: false },
  { id: 'settings', type: 'settings', name: 'Settings', description: 'Configuration', icon: 'settings', route: '/settings', order: 11, is_default: false },
];

export const WorkspaceNav: React.FC<WorkspaceNavProps> = ({
  currentWorkspace = 'dashboard',
  onWorkspaceChange,
  collapsed = false,
}) => {
  const [workspaces, setWorkspaces] = useState<Workspace[]>(DEFAULT_WORKSPACES);
  const [favorites, setFavorites] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWorkspaces();
  }, []);

  const loadWorkspaces = async () => {
    try {
      const response = await api.workspaces.list();
      if ((response.data as any)?.workspaces) {
        setWorkspaces((response.data as any).workspaces);
      }
      if ((response.data as any)?.favorites) {
        setFavorites((response.data as any).favorites);
      }
    } catch (error) {
      console.error('Failed to load workspaces:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleWorkspaceClick = (workspaceId: string) => {
    onWorkspaceChange(workspaceId);
  };

  const toggleFavorite = async (workspaceId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    
    try {
      if (favorites.includes(workspaceId)) {
        await api.workspaces.removeFavorite(workspaceId);
        setFavorites(favorites.filter(id => id !== workspaceId));
      } else {
        await api.workspaces.addFavorite(workspaceId);
        setFavorites([...favorites, workspaceId]);
      }
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
    }
  };

  const sortedWorkspaces = [...workspaces].sort((a, b) => a.order - b.order);
  const favoriteWorkspaces = sortedWorkspaces.filter(w => favorites.includes(w.id));

  if (loading) {
    return (
      <div className="flex items-center justify-center p-4">
        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className={`bg-slate-900 border-r border-slate-800 ${collapsed ? 'w-16' : 'w-64'} transition-all duration-200`}>
      {/* Favorites Section */}
      {favoriteWorkspaces.length > 0 && !collapsed && (
        <div className="p-3 border-b border-slate-800">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Favorites
          </h3>
          <div className="space-y-1">
            {favoriteWorkspaces.map(workspace => (
              <WorkspaceItem
                key={workspace.id}
                workspace={workspace}
                isActive={currentWorkspace === workspace.id}
                onClick={() => handleWorkspaceClick(workspace.id)}
                onToggleFavorite={(e) => toggleFavorite(workspace.id, e)}
                isFavorite={true}
                collapsed={collapsed}
              />
            ))}
          </div>
        </div>
      )}

      {/* All Workspaces */}
      <div className="p-3">
        {!collapsed && (
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Workspaces
          </h3>
        )}
        <div className="space-y-1">
          {sortedWorkspaces.map(workspace => (
            <WorkspaceItem
              key={workspace.id}
              workspace={workspace}
              isActive={currentWorkspace === workspace.id}
              onClick={() => handleWorkspaceClick(workspace.id)}
              onToggleFavorite={(e) => toggleFavorite(workspace.id, e)}
              isFavorite={favorites.includes(workspace.id)}
              collapsed={collapsed}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

interface WorkspaceItemProps {
  workspace: Workspace;
  isActive: boolean;
  onClick: () => void;
  onToggleFavorite: (e: React.MouseEvent) => void;
  isFavorite: boolean;
  collapsed: boolean;
}

const WorkspaceItem: React.FC<WorkspaceItemProps> = ({
  workspace,
  isActive,
  onClick,
  onToggleFavorite,
  isFavorite,
  collapsed,
}) => {
  const icon = WORKSPACE_ICONS[workspace.icon] || WORKSPACE_ICONS.dashboard;

  return (
    <div
      onClick={onClick}
      className={`
        group flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-all
        ${isActive 
          ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' 
          : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-transparent'
        }
      `}
    >
      <span className="flex-shrink-0">{icon}</span>
      
      {!collapsed && (
        <>
          <span className="flex-1 truncate text-sm font-medium">
            {workspace.name}
          </span>
          
          <button
            onClick={onToggleFavorite}
            className={`
              opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded
              ${isFavorite ? 'text-yellow-500' : 'text-slate-600 hover:text-slate-400'}
            `}
          >
            <svg className="w-4 h-4" fill={isFavorite ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
            </svg>
          </button>
        </>
      )}
    </div>
  );
};

export default WorkspaceNav;
