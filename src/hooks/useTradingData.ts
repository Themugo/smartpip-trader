import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../lib/api';
import { supabase, supabaseConfigured } from '../lib/supabase';
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
      if (supabaseConfigured) {
        const { data: { user } } = await supabase.auth.getUser();
        if (!user) {
          if (mountedRef.current) {
            setTrades([]);
            setStats(null);
            setSettings(null);
            setAuditLogs([]);
            setLoading(false);
          }
          return;
        }

        const [journalRes, settingsRes] = await Promise.all([
          supabase.from('trade_journal').select('*').eq('user_id', user.id).order('timestamp', { ascending: false }).limit(100),
          supabase.from('user_trading_settings').select('*').eq('user_id', user.id).maybeSingle(),
        ]);
        if (!mountedRef.current) return;

        if (journalRes.error) throw journalRes.error;
        if (settingsRes.error) throw settingsRes.error;

        const journalRows = journalRes.data ?? [];
        const mappedTrades: Trade[] = journalRows.map((row) => ({
          id: row.id,
          market: row.symbol,
          type: row.contract_type,
          direction: String(row.entry_conditions?.[0] ?? '').includes('PUT') ? 'PUT' : String(row.notes ?? '').includes('PUT') ? 'PUT' : 'CALL',
          amount: Number(row.amount ?? 0),
          confidence: Number(row.confidence ?? 0),
          reason: row.notes ?? null,
          entry_price: Number(row.entry_price ?? 0),
          entry_time: row.timestamp ?? row.created_at,
          exit_time: row.exit_price == null ? null : row.timestamp ?? row.created_at,
          profit: row.profit == null ? null : Number(row.profit),
          contract_id: row.contract_id ?? null,
          created_at: row.created_at ?? row.timestamp,
        }));
        setTrades(mappedTrades);

        const closed = mappedTrades.filter((trade) => trade.profit != null);
        const profits = closed.map((trade) => Number(trade.profit ?? 0));
        const wins = profits.filter((profit) => profit > 0);
        const losses = profits.filter((profit) => profit < 0);
        const totalProfit = profits.reduce((sum, profit) => sum + profit, 0);
        setStats({
          id: 1,
          total_trades: closed.length,
          wins: wins.length,
          losses: losses.length,
          win_rate: closed.length ? (wins.length / closed.length) * 100 : 0,
          total_profit: totalProfit,
          session_pnl: totalProfit,
          best_trade: profits.length ? Math.max(...profits) : 0,
          worst_trade: profits.length ? Math.min(...profits) : 0,
          avg_win: wins.length ? wins.reduce((sum, value) => sum + value, 0) / wins.length : 0,
          avg_loss: losses.length ? losses.reduce((sum, value) => sum + value, 0) / losses.length : 0,
          updated_at: new Date().toISOString(),
        });

        let settingsRow = settingsRes.data;
        if (!settingsRow) {
          const { data: provisioned, error: provisionError } = await supabase
            .from('user_trading_settings')
            .upsert({ user_id: user.id }, { onConflict: 'user_id' })
            .select('*')
            .single();
          if (provisionError) throw provisionError;
          settingsRow = provisioned;
        }
        if (settingsRow) {
          setSettings({
            id: 1,
            base_amount: Number(settingsRow.max_stake ?? 1),
            auto_trading: Boolean(settingsRow.auto_trading_enabled),
            max_trades_per_hour: Number(settingsRow.max_trades_per_hour ?? 5),
            min_confidence: Number(settingsRow.min_confidence ?? 70),
            stop_loss: Number(settingsRow.daily_loss_limit ?? 10),
            take_profit: 0,
            max_consecutive_losses: 3,
            enable_even_odd: false,
            enable_rise_fall: true,
            enable_over_under: false,
            enable_match_diff: false,
            enable_digit_analysis: true,
            updated_at: settingsRow.updated_at ?? new Date().toISOString(),
          });
        } else {
          setSettings(null);
        }
        // Audit logs are intentionally not exposed through the end-user shell.
        setAuditLogs([]);
        setError(null);
        setLoading(false);
        return;
      }

      // Legacy/local development fallback. Production end users stay on the
      // user-scoped Supabase path above.
      const [tradesRes, statsRes, settingsRes, auditRes] = await Promise.all([
        api.getTrades(), api.getStatistics(), api.getSettings(), api.getAuditLog(),
      ]);
      if (!mountedRef.current) return;
      if (tradesRes.data) setTrades(tradesRes.data as Trade[]);
      if (statsRes.data) setStats(statsRes.data as TradeStatistics);
      if (settingsRes.data) setSettings(settingsRes.data as SystemSettings);
      if (auditRes.data) setAuditLogs(auditRes.data as AuditLogEntry[]);
      setError(tradesRes.error || statsRes.error || settingsRes.error || auditRes.error || null);
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
      if (supabaseConfigured) {
        const { data: { user } } = await supabase.auth.getUser();
        if (!user) throw new Error('Authentication required');
        const mapped: Record<string, unknown> = {
          user_id: user.id,
          ...(updates.auto_trading !== undefined ? { auto_trading_enabled: updates.auto_trading } : {}),
          ...(updates.min_confidence !== undefined ? { min_confidence: updates.min_confidence } : {}),
          ...(updates.base_amount !== undefined ? { max_stake: updates.base_amount } : {}),
          ...(updates.max_trades_per_hour !== undefined ? { max_trades_per_hour: updates.max_trades_per_hour } : {}),
          ...(updates.stop_loss !== undefined ? { daily_loss_limit: updates.stop_loss } : {}),
          updated_at: new Date().toISOString(),
        };
        const { error: updateError } = await supabase.from('user_trading_settings').upsert(mapped);
        if (updateError) throw updateError;
        setSettings((prev) => prev ? { ...prev, ...updates, updated_at: new Date().toISOString() } : prev);
        return;
      }
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
