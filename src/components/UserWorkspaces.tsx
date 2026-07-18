/**
 * User Workspaces
 * 
 * Customizable workspace system with widget arrangement,
 * layout persistence, and multiple workspace support.
 */

import { useState, useEffect, useCallback, createContext, useContext, type ReactNode, useMemo } from 'react';
import { cn } from '../ui/utils';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';

// Types
export interface Widget {
  id: string;
  type: WidgetType;
  title: string;
  x: number;
  y: number;
  width: number;
  height: number;
  minWidth?: number;
  minHeight?: number;
  props?: Record<string, unknown>;
  collapsed?: boolean;
}

export type WidgetType =
  | 'stats'
  | 'chart'
  | 'orderbook'
  | 'trades'
  | 'journal'
  | 'ai-insights'
  | 'risk-monitor'
  | 'portfolio'
  | 'calendar'
  | 'notes'
  | 'alerts'
  | 'terminal';

export interface Workspace {
  id: string;
  name: string;
  widgets: Widget[];
  isDefault?: boolean;
  createdAt: number;
  updatedAt: number;
}

export interface WorkspacePreferences {
  snapToGrid: boolean;
  gridSize: number;
  showGuides: boolean;
  autoSave: boolean;
}

// Default widgets configuration
const DEFAULT_WIDGETS: Widget[] = [
  { id: 'stats-1', type: 'stats', title: 'Trading Stats', x: 0, y: 0, width: 3, height: 2 },
  { id: 'chart-1', type: 'chart', title: 'Market Chart', x: 3, y: 0, width: 6, height: 4 },
  { id: 'trades-1', type: 'trades', title: 'Recent Trades', x: 9, y: 0, width: 3, height: 3 },
  { id: 'journal-1', type: 'journal', title: 'Trade Journal', x: 0, y: 2, width: 3, height: 4 },
  { id: 'ai-1', type: 'ai-insights', title: 'AI Insights', x: 0, y: 6, width: 4, height: 2 },
  { id: 'risk-1', type: 'risk-monitor', title: 'Risk Monitor', x: 4, y: 4, width: 5, height: 2 },
];

// Default workspaces
const DEFAULT_WORKSPACES: Workspace[] = [
  {
    id: 'dashboard',
    name: 'Dashboard',
    widgets: DEFAULT_WIDGETS,
    isDefault: true,
    createdAt: Date.now(),
    updatedAt: Date.now(),
  },
  {
    id: 'trading',
    name: 'Trading',
    widgets: [
      { id: 'chart-trading', type: 'chart', title: 'Trading Chart', x: 0, y: 0, width: 8, height: 6 },
      { id: 'orderbook-1', type: 'orderbook', title: 'Order Book', x: 8, y: 0, width: 4, height: 4 },
      { id: 'terminal-1', type: 'terminal', title: 'Terminal', x: 8, y: 4, width: 4, height: 4 },
    ],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  },
  {
    id: 'analysis',
    name: 'Analysis',
    widgets: [
      { id: 'portfolio-1', type: 'portfolio', title: 'Portfolio', x: 0, y: 0, width: 6, height: 4 },
      { id: 'calendar-1', type: 'calendar', title: 'Performance Calendar', x: 6, y: 0, width: 6, height: 4 },
      { id: 'journal-analysis', type: 'journal', title: 'Trade Journal', x: 0, y: 4, width: 12, height: 4 },
    ],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  },
];

// Default preferences
const DEFAULT_PREFERENCES: WorkspacePreferences = {
  snapToGrid: true,
  gridSize: 12,
  showGuides: true,
  autoSave: true,
};

// Context
interface WorkspaceContextValue {
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  setActiveWorkspace: (id: string) => void;
  createWorkspace: (name: string) => string;
  deleteWorkspace: (id: string) => void;
  duplicateWorkspace: (id: string) => string;
  renameWorkspace: (id: string, name: string) => void;
  updateWidget: (widgetId: string, updates: Partial<Widget>) => void;
  addWidget: (widget: Omit<Widget, 'id'>) => void;
  removeWidget: (widgetId: string) => void;
  resetWorkspace: (id: string) => void;
  preferences: WorkspacePreferences;
  updatePreferences: (prefs: Partial<WorkspacePreferences>) => void;
  exportLayout: () => string;
  importLayout: (data: string) => boolean;
  isDragging: boolean;
  setIsDragging: (dragging: boolean) => void;
  isEditing: boolean;
  setIsEditing: (editing: boolean) => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function useWorkspaces() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspaces must be used within WorkspaceProvider');
  }
  return context;
}

// Provider
export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>(DEFAULT_WORKSPACES);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string>('dashboard');
  const [preferences, setPreferences] = useState<WorkspacePreferences>(DEFAULT_PREFERENCES);
  const [isDragging, setIsDragging] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // Load from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('workspace_workspaces');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setWorkspaces(parsed);
        }
      } catch {
        // Ignore parse errors
      }
    }

    const savedPrefs = localStorage.getItem('workspace_preferences');
    if (savedPrefs) {
      try {
        setPreferences(JSON.parse(savedPrefs));
      } catch {
        // Ignore parse errors
      }
    }
  }, []);

  // Save to localStorage
  useEffect(() => {
    if (preferences.autoSave) {
      localStorage.setItem('workspace_workspaces', JSON.stringify(workspaces));
    }
    localStorage.setItem('workspace_preferences', JSON.stringify(preferences));
  }, [workspaces, preferences]);

  const activeWorkspace = useMemo(
    () => workspaces.find((w) => w.id === activeWorkspaceId) || workspaces[0] || null,
    [workspaces, activeWorkspaceId]
  );

  const setActiveWorkspace = useCallback((id: string) => {
    setActiveWorkspaceId(id);
  }, []);

  const createWorkspace = useCallback((name: string): string => {
    const id = `workspace-${Date.now()}`;
    const newWorkspace: Workspace = {
      id,
      name,
      widgets: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setWorkspaces((prev) => [...prev, newWorkspace]);
    setActiveWorkspaceId(id);
    return id;
  }, []);

  const deleteWorkspace = useCallback((id: string) => {
    setWorkspaces((prev) => {
      const filtered = prev.filter((w) => w.id !== id);
      if (filtered.length === 0) {
        // Ensure at least one workspace exists
        return [DEFAULT_WORKSPACES[0]];
      }
      return filtered;
    });
    if (activeWorkspaceId === id) {
      setActiveWorkspaceId(workspaces[0]?.id || 'dashboard');
    }
  }, [activeWorkspaceId, workspaces]);

  const duplicateWorkspace = useCallback((id: string): string => {
    const workspace = workspaces.find((w) => w.id === id);
    if (!workspace) return '';
    
    const newId = `workspace-${Date.now()}`;
    const duplicated: Workspace = {
      ...workspace,
      id: newId,
      name: `${workspace.name} (Copy)`,
      isDefault: false,
      widgets: workspace.widgets.map((w) => ({ ...w, id: `${w.id}-copy-${Date.now()}` })),
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setWorkspaces((prev) => [...prev, duplicated]);
    return newId;
  }, [workspaces]);

  const renameWorkspace = useCallback((id: string, name: string) => {
    setWorkspaces((prev) =>
      prev.map((w) =>
        w.id === id ? { ...w, name, updatedAt: Date.now() } : w
      )
    );
  }, []);

  const updateWidget = useCallback((widgetId: string, updates: Partial<Widget>) => {
    setWorkspaces((prev) =>
      prev.map((workspace) =>
        workspace.id === activeWorkspaceId
          ? {
              ...workspace,
              widgets: workspace.widgets.map((w) =>
                w.id === widgetId ? { ...w, ...updates } : w
              ),
              updatedAt: Date.now(),
            }
          : workspace
      )
    );
  }, [activeWorkspaceId]);

  const addWidget = useCallback((widget: Omit<Widget, 'id'>) => {
    const newWidget: Widget = {
      ...widget,
      id: `widget-${Date.now()}-${Math.random().toString(36).substring(7)}`,
    };
    setWorkspaces((prev) =>
      prev.map((workspace) =>
        workspace.id === activeWorkspaceId
          ? {
              ...workspace,
              widgets: [...workspace.widgets, newWidget],
              updatedAt: Date.now(),
            }
          : workspace
      )
    );
  }, [activeWorkspaceId]);

  const removeWidget = useCallback((widgetId: string) => {
    setWorkspaces((prev) =>
      prev.map((workspace) =>
        workspace.id === activeWorkspaceId
          ? {
              ...workspace,
              widgets: workspace.widgets.filter((w) => w.id !== widgetId),
              updatedAt: Date.now(),
            }
          : workspace
      )
    );
  }, [activeWorkspaceId]);

  const resetWorkspace = useCallback((id: string) => {
    const defaultWorkspace = DEFAULT_WORKSPACES.find((w) => w.id === id);
    if (defaultWorkspace) {
      setWorkspaces((prev) =>
        prev.map((w) =>
          w.id === id
            ? {
                ...defaultWorkspace,
                id,
                name: w.name,
                createdAt: w.createdAt,
                updatedAt: Date.now(),
              }
            : w
        )
      );
    }
  }, []);

  const updatePreferences = useCallback((prefs: Partial<WorkspacePreferences>) => {
    setPreferences((prev) => ({ ...prev, ...prefs }));
  }, []);

  const exportLayout = useCallback((): string => {
    return JSON.stringify({
      workspace: activeWorkspace,
      exportedAt: Date.now(),
      version: '1.0',
    });
  }, [activeWorkspace]);

  const importLayout = useCallback((data: string): boolean => {
    try {
      const parsed = JSON.parse(data);
      if (parsed.workspace && parsed.workspace.widgets) {
        const newId = `workspace-${Date.now()}`;
        const imported: Workspace = {
          ...parsed.workspace,
          id: newId,
          name: `${parsed.workspace.name} (Imported)`,
          isDefault: false,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        setWorkspaces((prev) => [...prev, imported]);
        setActiveWorkspaceId(newId);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, []);

  return (
    <WorkspaceContext.Provider
      value={{
        workspaces,
        activeWorkspace,
        setActiveWorkspace,
        createWorkspace,
        deleteWorkspace,
        duplicateWorkspace,
        renameWorkspace,
        updateWidget,
        addWidget,
        removeWidget,
        resetWorkspace,
        preferences,
        updatePreferences,
        exportLayout,
        importLayout,
        isDragging,
        setIsDragging,
        isEditing,
        setIsEditing,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

// Widget Renderer
export function WidgetRenderer({ widget }: { widget: Widget }) {
  const { removeWidget, updateWidget } = useWorkspaces();
  const [isCollapsed, setIsCollapsed] = useState(widget.collapsed || false);

  const toggleCollapse = () => {
    updateWidget(widget.id, { collapsed: !isCollapsed });
    setIsCollapsed(!isCollapsed);
  };

  return (
    <div
      className={cn(
        'absolute rounded-lg border border-slate-700 bg-slate-900 overflow-hidden',
        'transition-shadow duration-200',
        'hover:border-slate-600'
      )}
      style={{
        left: `${(widget.x / 12) * 100}%`,
        top: `${(widget.y / 10) * 100}%`,
        width: `${(widget.width / 12) * 100}%`,
        height: isCollapsed ? 'auto' : `${(widget.height / 10) * 100}%`,
        minWidth: widget.minWidth ? `${(widget.minWidth / 12) * 100}%` : undefined,
        minHeight: widget.minHeight ? `${(widget.minHeight / 10) * 100}%` : undefined,
      }}
    >
      {/* Widget Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800 bg-slate-800/50">
        <span className="text-sm font-medium text-white">{widget.title}</span>
        <div className="flex items-center gap-1">
          <button
            onClick={toggleCollapse}
            className="p-1 text-slate-400 hover:text-white transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={isCollapsed ? 'M19 9l-7 7-7-7' : 'M5 15l7-7 7 7'} />
            </svg>
          </button>
          <button
            onClick={() => removeWidget(widget.id)}
            className="p-1 text-slate-400 hover:text-red-400 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Widget Content */}
      {!isCollapsed && (
        <div className="p-3 h-full overflow-auto">
          <WidgetContent type={widget.type} />
        </div>
      )}
    </div>
  );
}

// Widget Content Component
function WidgetContent({ type }: { type: WidgetType }) {
  const widgetContent: Record<WidgetType, ReactNode> = {
    stats: (
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2 bg-slate-800 rounded">
          <p className="text-xs text-slate-400">Win Rate</p>
          <p className="text-lg font-semibold text-emerald-400">62.5%</p>
        </div>
        <div className="p-2 bg-slate-800 rounded">
          <p className="text-xs text-slate-400">P/L</p>
          <p className="text-lg font-semibold text-white">+$1,245</p>
        </div>
        <div className="p-2 bg-slate-800 rounded">
          <p className="text-xs text-slate-400">Trades</p>
          <p className="text-lg font-semibold text-white">48</p>
        </div>
        <div className="p-2 bg-slate-800 rounded">
          <p className="text-xs text-slate-400">Streak</p>
          <p className="text-lg font-semibold text-blue-400">5W</p>
        </div>
      </div>
    ),
    chart: (
      <div className="h-full flex items-center justify-center bg-slate-800/50 rounded">
        <p className="text-slate-500">Chart Widget</p>
      </div>
    ),
    orderbook: (
      <div className="h-full flex items-center justify-center bg-slate-800/50 rounded">
        <p className="text-slate-500">Order Book Widget</p>
      </div>
    ),
    trades: (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center justify-between p-2 bg-slate-800 rounded">
            <div className="flex items-center gap-2">
              <Badge variant={i % 2 === 0 ? 'success' : 'error'} size="sm">
                {i % 2 === 0 ? 'WIN' : 'LOSS'}
              </Badge>
              <span className="text-sm text-slate-300">DIGITOVER</span>
            </div>
            <span className={i % 2 === 0 ? 'text-emerald-400' : 'text-red-400'}>
              +${(Math.random() * 10).toFixed(2)}
            </span>
          </div>
        ))}
      </div>
    ),
    journal: (
      <div className="h-full flex items-center justify-center bg-slate-800/50 rounded">
        <p className="text-slate-500">Journal Widget</p>
      </div>
    ),
    'ai-insights': (
      <div className="space-y-2">
        <div className="p-2 bg-blue-500/10 border border-blue-500/20 rounded">
          <p className="text-xs text-blue-400 font-medium">AI Insight</p>
          <p className="text-sm text-slate-300 mt-1">High volatility detected. Consider reducing position size.</p>
        </div>
        <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded">
          <p className="text-xs text-emerald-400 font-medium">Pattern Match</p>
          <p className="text-sm text-slate-300 mt-1">Similar pattern occurred 3 times this week.</p>
        </div>
      </div>
    ),
    'risk-monitor': (
      <div className="space-y-2">
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-400">Risk Score</span>
            <span className="text-amber-400">68/100</span>
          </div>
          <div className="h-2 bg-slate-800 rounded overflow-hidden">
            <div className="h-full bg-amber-500 rounded" style={{ width: '68%' }} />
          </div>
        </div>
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-400">Drawdown</span>
            <span className="text-emerald-400">8.2%</span>
          </div>
          <div className="h-2 bg-slate-800 rounded overflow-hidden">
            <div className="h-full bg-emerald-500 rounded" style={{ width: '8.2%' }} />
          </div>
        </div>
      </div>
    ),
    portfolio: (
      <div className="h-full flex items-center justify-center bg-slate-800/50 rounded">
        <p className="text-slate-500">Portfolio Widget</p>
      </div>
    ),
    calendar: (
      <div className="h-full flex items-center justify-center bg-slate-800/50 rounded">
        <p className="text-slate-500">Calendar Widget</p>
      </div>
    ),
    notes: (
      <textarea
        className="w-full h-full bg-transparent text-sm text-slate-300 resize-none outline-none"
        placeholder="Add notes..."
      />
    ),
    alerts: (
      <div className="space-y-2">
        <div className="flex items-center gap-2 p-2 bg-amber-500/10 rounded">
          <span className="text-amber-400">⚠️</span>
          <span className="text-sm text-slate-300">High volatility alert</span>
        </div>
        <div className="flex items-center gap-2 p-2 bg-blue-500/10 rounded">
          <span className="text-blue-400">ℹ️</span>
          <span className="text-sm text-slate-300">5 trades today</span>
        </div>
      </div>
    ),
    terminal: (
      <div className="h-full font-mono text-xs bg-slate-950 rounded p-2 overflow-auto">
        <p className="text-slate-500">$ smartpip --status</p>
        <p className="text-emerald-400">System: Online</p>
        <p className="text-slate-400">Connected: Deriv Demo</p>
        <p className="text-slate-400">Session: Active</p>
      </div>
    ),
  };

  return widgetContent[type] || <p className="text-slate-500">Unknown widget</p>;
}

// Workspace Switcher Component
export function WorkspaceSwitcher() {
  const { workspaces, activeWorkspace, setActiveWorkspace, createWorkspace } = useWorkspaces();
  const [isOpen, setIsOpen] = useState(false);
  const [showNewInput, setShowNewInput] = useState(false);
  const [newName, setNewName] = useState('');

  const handleCreate = () => {
    if (newName.trim()) {
      createWorkspace(newName.trim());
      setNewName('');
      setShowNewInput(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
      >
        <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
        <span className="text-sm font-medium text-white">{activeWorkspace?.name || 'Workspaces'}</span>
        <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full left-0 mt-2 w-64 bg-slate-900 border border-slate-700 rounded-lg shadow-xl z-50">
            <div className="p-2 max-h-80 overflow-y-auto">
              {workspaces.map((workspace) => (
                <button
                  key={workspace.id}
                  onClick={() => {
                    setActiveWorkspace(workspace.id);
                    setIsOpen(false);
                  }}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors',
                    workspace.id === activeWorkspace?.id
                      ? 'bg-blue-600/20 text-blue-400'
                      : 'text-slate-300 hover:bg-slate-800'
                  )}
                >
                  <span className="text-sm">{workspace.name}</span>
                  {workspace.isDefault && (
                    <Badge variant="primary" size="sm">Default</Badge>
                  )}
                </button>
              ))}
            </div>

            <div className="p-2 border-t border-slate-800">
              {showNewInput ? (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                    placeholder="Workspace name"
                    className="flex-1 px-2 py-1 bg-slate-800 border border-slate-700 rounded text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500"
                    autoFocus
                  />
                  <Button size="sm" onClick={handleCreate}>Add</Button>
                </div>
              ) : (
                <button
                  onClick={() => setShowNewInput(true)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  New Workspace
                </button>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// Widget Library Component
export function WidgetLibrary() {
  const { addWidget } = useWorkspaces();
  const [isOpen, setIsOpen] = useState(false);

  const availableWidgets: { type: WidgetType; title: string; description: string }[] = [
    { type: 'stats', title: 'Stats', description: 'Trading statistics overview' },
    { type: 'chart', title: 'Chart', description: 'Market price chart' },
    { type: 'trades', title: 'Recent Trades', description: 'Latest trade history' },
    { type: 'journal', title: 'Journal', description: 'Trade journal notes' },
    { type: 'ai-insights', title: 'AI Insights', description: 'AI-powered analysis' },
    { type: 'risk-monitor', title: 'Risk Monitor', description: 'Risk metrics display' },
    { type: 'portfolio', title: 'Portfolio', description: 'Portfolio overview' },
    { type: 'calendar', title: 'Calendar', description: 'Performance calendar' },
    { type: 'notes', title: 'Notes', description: 'Personal notes widget' },
    { type: 'alerts', title: 'Alerts', description: 'Recent alerts' },
    { type: 'terminal', title: 'Terminal', description: 'Command terminal' },
  ];

  const handleAddWidget = (type: WidgetType) => {
    addWidget({
      type,
      title: availableWidgets.find((w) => w.type === type)?.title || type,
      x: 0,
      y: 0,
      width: 4,
      height: 3,
    });
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <Button
        variant="secondary"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        Add Widget
      </Button>

      {isOpen && (
        <>
          <div className="fixed inset-0" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full right-0 mt-2 w-72 bg-slate-900 border border-slate-700 rounded-lg shadow-xl z-50">
            <div className="p-2">
              <p className="px-3 py-2 text-xs font-medium text-slate-500 uppercase">Available Widgets</p>
              {availableWidgets.map((widget) => (
                <button
                  key={widget.type}
                  onClick={() => handleAddWidget(widget.type)}
                  className="w-full flex items-start gap-3 px-3 py-2 rounded-lg text-left hover:bg-slate-800 transition-colors"
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white">{widget.title}</p>
                    <p className="text-xs text-slate-400">{widget.description}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// Workspace Toolbar Component
export function WorkspaceToolbar() {
  const { exportLayout, importLayout, resetWorkspace, activeWorkspace, isEditing, setIsEditing } = useWorkspaces();
  const [showImport, setShowImport] = useState(false);
  const [importData, setImportData] = useState('');

  const handleExport = () => {
    const data = exportLayout();
    navigator.clipboard.writeText(data);
    alert('Layout copied to clipboard!');
  };

  const handleImport = () => {
    if (importData.trim()) {
      const success = importLayout(importData.trim());
      if (success) {
        setImportData('');
        setShowImport(false);
        alert('Layout imported successfully!');
      } else {
        alert('Invalid layout data');
      }
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Button
        variant={isEditing ? 'primary' : 'outline'}
        size="sm"
        onClick={() => setIsEditing(!isEditing)}
      >
        {isEditing ? 'Done Editing' : 'Edit Layout'}
      </Button>

      {isEditing && (
        <>
          <WidgetLibrary />

          <Button variant="outline" size="sm" onClick={handleExport}>
            Export
          </Button>

          {showImport ? (
            <div className="flex gap-2">
              <input
                type="text"
                value={importData}
                onChange={(e) => setImportData(e.target.value)}
                placeholder="Paste layout data"
                className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500"
              />
              <Button size="sm" onClick={handleImport}>Import</Button>
              <Button variant="outline" size="sm" onClick={() => setShowImport(false)}>Cancel</Button>
            </div>
          ) : (
            <Button variant="outline" size="sm" onClick={() => setShowImport(true)}>
              Import
            </Button>
          )}

          {activeWorkspace && !activeWorkspace.isDefault && (
            <Button variant="outline" size="sm" onClick={() => resetWorkspace(activeWorkspace.id)}>
              Reset
            </Button>
          )}
        </>
      )}
    </div>
  );
}

// Workspace Canvas Component
export function WorkspaceCanvas() {
  const { activeWorkspace, isEditing } = useWorkspaces();

  if (!activeWorkspace) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-slate-500">No workspace selected</p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'relative h-full bg-slate-950 rounded-lg overflow-hidden',
        isEditing && 'border-2 border-dashed border-slate-700'
      )}
    >
      {isEditing && (
        <div className="absolute top-2 right-2 z-10">
          <Badge variant="warning" size="sm">Edit Mode</Badge>
        </div>
      )}
      <div className="relative h-full">
        {activeWorkspace.widgets.map((widget) => (
          <WidgetRenderer key={widget.id} widget={widget} />
        ))}
      </div>
    </div>
  );
}

export default WorkspaceProvider;
