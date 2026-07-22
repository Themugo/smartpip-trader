import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../lib/api';
import type { Trade, TradeStatistics, SystemSettings, AuditLogEntry } from '../lib/supabase';

export interface TradingDataState {
  trades: Trade[];
  stats: TradeStatistics | null;
  settings: SystemSettings | null;
  auditLogs: AuditLogEntry[];
  error: string | null;
  loading: boolean;
}

export interface TradingDataActions {
  fetchData: () => Promise<void>;
  updateSettings: (updates: Partial<SystemSettings>) => Promise<void>;
  setError: (error: string | null) => void;
  retry: () => Promise<void>;
}

export function useTradingData(isAuthenticated: boolean): TradingDataState & TradingDataActions {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [stats, setStats] = useState<TradeStatistics | null>(null);
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  const fetchData = useCallback(async () => {
    try {
      const [tradesRes, statsRes, settingsRes, auditRes] = await Promise.allSettled([
        api.getTrades(),
        api.getStatistics(),
        api.getSettings(),
        api.getAuditLog(),
      ]);

      if (!mountedRef.current) return;

      const errors: string[] = [];

      if (tradesRes.status === 'fulfilled' && tradesRes.value.data) {
        setTrades((tradesRes.value.data as Trade[]) ?? []);
      } else if (tradesRes.status === 'rejected') {
        errors.push('trades');
      }

      if (statsRes.status === 'fulfilled' && statsRes.value.data) {
        setStats((statsRes.value.data as TradeStatistics) ?? null);
      } else if (statsRes.status === 'rejected') {
        errors.push('statistics');
      }

      if (settingsRes.status === 'fulfilled' && settingsRes.value.data) {
        setSettings((settingsRes.value.data as SystemSettings) ?? null);
      } else if (settingsRes.status === 'rejected') {
        errors.push('settings');
      }

      if (auditRes.status === 'fulfilled' && auditRes.value.data) {
        setAuditLogs((auditRes.value.data as AuditLogEntry[]) ?? []);
      } else if (auditRes.status === 'rejected') {
        errors.push('audit logs');
      }

      setError(errors.length > 0 ? `Failed to load: ${errors.join(', ')}` : null);
    } catch (e: unknown) {
      if (!mountedRef.current) return;
      setError(e instanceof Error ? e.message : 'Failed to fetch account data');
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  // Poll data when authenticated
  useEffect(() => {
    mountedRef.current = true;
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    fetchData();
    intervalRef.current = setInterval(fetchData, 3000);
    return () => {
      mountedRef.current = false;
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchData, isAuthenticated]);

  const updateSettings = useCallback(async (updates: Partial<SystemSettings>) => {
    try {
      await api.updateSettings(updates);
      setSettings((prev) => (prev ? { ...prev, ...updates } : null));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to update settings');
      throw e;
    }
  }, []);

  const retry = useCallback(async () => {
    setLoading(true);
    setError(null);
    await fetchData();
  }, [fetchData]);

  return { trades, stats, settings, auditLogs, error, loading, fetchData, updateSettings, setError, retry };
}
