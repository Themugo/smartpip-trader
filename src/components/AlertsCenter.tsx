/**
 * Smart Alerts Center
 * 
 * Intelligent alert system with preferences and categorization.
 */

import { useState, useEffect, createContext, useContext, type ReactNode } from 'react';
import { cn } from '../ui/utils';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';

// Types
export type AlertType = 
  | 'broker'
  | 'drawdown'
  | 'risk'
  | 'subscription'
  | 'system'
  | 'ai'
  | 'replay'
  | 'validation'
  | 'milestone';

export type AlertSeverity = 'info' | 'warning' | 'error' | 'success';

export interface Alert {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  title: string;
  message: string;
  timestamp: number;
  read: boolean;
  dismissed: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
  metadata?: Record<string, unknown>;
}

export interface AlertPreferences {
  brokerIssues: boolean;
  largeDrawdowns: boolean;
  riskLimitBreaches: boolean;
  paperTradingMilestones: boolean;
  subscriptionReminders: boolean;
  systemMaintenance: boolean;
  aiConfidenceWarnings: boolean;
  replayCompletion: boolean;
  strategyValidationResults: boolean;
  emailNotifications: boolean;
  pushNotifications: boolean;
}

const defaultPreferences: AlertPreferences = {
  brokerIssues: true,
  largeDrawdowns: true,
  riskLimitBreaches: true,
  paperTradingMilestones: true,
  subscriptionReminders: true,
  systemMaintenance: true,
  aiConfidenceWarnings: true,
  replayCompletion: true,
  strategyValidationResults: true,
  emailNotifications: false,
  pushNotifications: false,
};

// Icons
const BellIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
  </svg>
);

const XIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const CheckIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

const SettingsIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

const AlertTypeIcon: Record<AlertType, ReactNode> = {
  broker: <span className="text-amber-400">⚡</span>,
  drawdown: <span className="text-red-400">📉</span>,
  risk: <span className="text-red-400">⚠️</span>,
  subscription: <span className="text-blue-400">💳</span>,
  system: <span className="text-slate-400">🔧</span>,
  ai: <span className="text-purple-400">🤖</span>,
  replay: <span className="text-cyan-400">📹</span>,
  validation: <span className="text-emerald-400">✓</span>,
  milestone: <span className="text-emerald-400">🏆</span>,
};

// Context
interface AlertsContextValue {
  alerts: Alert[];
  unreadCount: number;
  addAlert: (alert: Omit<Alert, 'id' | 'timestamp' | 'read' | 'dismissed'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  dismissAlert: (id: string) => void;
  clearAllAlerts: () => void;
  preferences: AlertPreferences;
  updatePreferences: (prefs: Partial<AlertPreferences>) => void;
}

const AlertsContext = createContext<AlertsContextValue | null>(null);

export function useAlerts() {
  const context = useContext(AlertsContext);
  if (!context) {
    throw new Error('useAlerts must be used within AlertsProvider');
  }
  return context;
}

// Provider
export function AlertsProvider({ children }: { children: ReactNode }) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [preferences, setPreferences] = useState<AlertPreferences>(defaultPreferences);

  // Load from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('alert_preferences');
    if (saved) {
      try {
        setPreferences(JSON.parse(saved));
      } catch {
        // Ignore parse errors
      }
    }
  }, []);

  // Save to localStorage
  useEffect(() => {
    localStorage.setItem('alert_preferences', JSON.stringify(preferences));
  }, [preferences]);

  const addAlert = (alert: Omit<Alert, 'id' | 'timestamp' | 'read' | 'dismissed'>) => {
    const newAlert: Alert = {
      ...alert,
      id: `alert-${Date.now()}-${Math.random().toString(36).substring(7)}`,
      timestamp: Date.now(),
      read: false,
      dismissed: false,
    };
    setAlerts((prev) => [newAlert, ...prev]);
  };

  const markAsRead = (id: string) => {
    setAlerts((prev) =>
      prev.map((alert) =>
        alert.id === id ? { ...alert, read: true } : alert
      )
    );
  };

  const markAllAsRead = () => {
    setAlerts((prev) => prev.map((alert) => ({ ...alert, read: true })));
  };

  const dismissAlert = (id: string) => {
    setAlerts((prev) =>
      prev.map((alert) =>
        alert.id === id ? { ...alert, dismissed: true } : alert
      )
    );
  };

  const clearAllAlerts = () => {
    setAlerts([]);
  };

  const updatePreferences = (prefs: Partial<AlertPreferences>) => {
    setPreferences((prev) => ({ ...prev, ...prefs }));
  };

  const unreadCount = alerts.filter((a) => !a.read && !a.dismissed).length;

  return (
    <AlertsContext.Provider
      value={{
        alerts,
        unreadCount,
        addAlert,
        markAsRead,
        markAllAsRead,
        dismissAlert,
        clearAllAlerts,
        preferences,
        updatePreferences,
      }}
    >
      {children}
    </AlertsContext.Provider>
  );
}

// Alert Badge Component
export function AlertBadge({ count }: { count: number }) {
  if (count === 0) return null;
  
  return (
    <span className="absolute -top-1 -right-1 flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-red-500 rounded-full">
      {count > 9 ? '9+' : count}
    </span>
  );
}

// Alerts Center Component
interface AlertsCenterProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AlertsCenter({ isOpen, onClose }: AlertsCenterProps) {
  const { alerts, unreadCount, markAsRead, markAllAsRead, dismissAlert, clearAllAlerts } = useAlerts();
  
  const activeAlerts = alerts.filter((a) => !a.dismissed);
  const unreadAlerts = activeAlerts.filter((a) => !a.read);
  const readAlerts = activeAlerts.filter((a) => a.read);

  const formatTime = (timestamp: number) => {
    const now = Date.now();
    const diff = now - timestamp;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return new Date(timestamp).toLocaleDateString();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      
      <div className="absolute top-16 right-4 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden animate-scale-in">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <h2 className="font-semibold text-white">Notifications</h2>
              {unreadCount > 0 && (
                <Badge variant="primary" size="sm">{unreadCount} new</Badge>
              )}
            </div>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  className="text-xs text-slate-400 hover:text-white transition-colors"
                >
                  Mark all read
                </button>
              )}
              <button
                onClick={onClose}
                className="p-1 text-slate-400 hover:text-white transition-colors"
              >
                <XIcon />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="max-h-[60vh] overflow-y-auto">
            {activeAlerts.length === 0 ? (
              <div className="py-12 text-center text-slate-500">
                <BellIcon />
                <p className="mt-4">No notifications</p>
              </div>
            ) : (
              <>
                {/* Unread Alerts */}
                {unreadAlerts.length > 0 && (
                  <div>
                    <div className="px-4 py-2 text-xs font-medium text-slate-500 uppercase">
                      New
                    </div>
                    {unreadAlerts.map((alert) => (
                      <AlertItem
                        key={alert.id}
                        alert={alert}
                        onMarkRead={markAsRead}
                        onDismiss={dismissAlert}
                        formatTime={formatTime}
                      />
                    ))}
                  </div>
                )}

                {/* Read Alerts */}
                {readAlerts.length > 0 && (
                  <div>
                    {unreadAlerts.length > 0 && (
                      <div className="px-4 py-2 text-xs font-medium text-slate-500 uppercase">
                        Earlier
                      </div>
                    )}
                    {readAlerts.slice(0, 10).map((alert) => (
                      <AlertItem
                        key={alert.id}
                        alert={alert}
                        onMarkRead={markAsRead}
                        onDismiss={dismissAlert}
                        formatTime={formatTime}
                      />
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Footer */}
          {activeAlerts.length > 0 && (
            <div className="px-4 py-3 border-t border-slate-800">
              <button
                onClick={clearAllAlerts}
                className="w-full text-sm text-slate-400 hover:text-white transition-colors"
              >
                Clear all notifications
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Alert Item Component
function AlertItem({
  alert,
  onMarkRead,
  onDismiss,
  formatTime,
}: {
  alert: Alert;
  onMarkRead: (id: string) => void;
  onDismiss: (id: string) => void;
  formatTime: (timestamp: number) => string;
}) {
  const severityColors = {
    info: 'border-l-blue-500',
    warning: 'border-l-amber-500',
    error: 'border-l-red-500',
    success: 'border-l-emerald-500',
  };

  return (
    <div
      className={cn(
        'relative px-4 py-3 border-l-2 hover:bg-slate-800/50 transition-colors cursor-pointer',
        !alert.read && 'bg-slate-800/30',
        severityColors[alert.severity]
      )}
      onClick={() => {
        if (!alert.read) onMarkRead(alert.id);
        alert.action?.onClick();
      }}
    >
      <div className="flex gap-3">
        <div className="flex-shrink-0 mt-0.5">
          {AlertTypeIcon[alert.type]}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <p className={cn('text-sm', !alert.read ? 'font-medium text-white' : 'text-slate-300')}>
              {alert.title}
            </p>
            <span className="text-xs text-slate-500 whitespace-nowrap">
              {formatTime(alert.timestamp)}
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-0.5 line-clamp-2">
            {alert.message}
          </p>
          {alert.action && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                alert.action!.onClick();
              }}
              className="mt-2 text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              {alert.action.label}
            </button>
          )}
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDismiss(alert.id);
          }}
          className="flex-shrink-0 p-1 text-slate-500 hover:text-white transition-colors"
        >
          <XIcon />
        </button>
      </div>
      {!alert.read && (
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500 rounded-l" />
      )}
    </div>
  );
}

// Alerts Trigger Button
export function AlertsTrigger({ onClick }: { onClick: () => void }) {
  const { unreadCount } = useAlerts();

  return (
    <button
      onClick={onClick}
      className="relative p-2 text-slate-400 hover:text-white transition-colors"
      aria-label="Notifications"
    >
      <BellIcon />
      <AlertBadge count={unreadCount} />
    </button>
  );
}

export default AlertsProvider;
