import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../lib/api';
import type { Trade, TradeStatistics, SystemSettings, AuditLogEntry } from '../lib/supabase';

export interface TradingDataState {
  trades: Trade[];
  stats: TradeStatistics | null;
  settings: SystemSettings | null;
  auditLogs: AuditLogEntry[];
  error: string | null;
}

export interface TradingDataActions {
  fetchData: () => Promise<void>;
  updateSettings: (updates: Partial<SystemSettings>) => Promise<void>;
  setError: (error: string | null) => void;
}

export function useTradingData(isAuthenticated: boolean): TradingDataState & TradingDataActions {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [stats, setStats] = useState<TradeStatistics | null>(null);
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  // Poll data when authenticated
  useEffect(() => {
    if (!isAuthenticated) return;
    fetchData();
    intervalRef.current = setInterval(fetchData, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchData, isAuthenticated]);

  const updateSettings = useCallback(async (updates: Partial<SystemSettings>) => {
    await api.updateSettings(updates);
    setSettings((prev) => (prev ? { ...prev, ...updates } : null));
  }, []);

  return { trades, stats, settings, auditLogs, error, fetchData, updateSettings, setError };
}
