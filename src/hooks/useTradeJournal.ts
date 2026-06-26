import { useState, useCallback, useRef, useMemo } from 'react';
import { supabase } from '../lib/supabase';
import type { RegimeType } from './useRegimeDetection';

export interface JournalEntry {
  id: string;
  timestamp: number;
  symbol: string;
  contractType: string;
  entryPrice: number;
  entryDigit: number;
  exitPrice: number | null;
  exitDigit: number | null;
  amount: number;
  confidence: number;
  regime: RegimeType;
  entryConditions: string[];
  exitConditions: string[];
  profit: number | null;
  pnl: number | null;
  drawdownImpact: number;
  runningBalance: number;
  peakBalance: number;
  notes: string;
}

export interface WeeklyInsight {
  weekStart: number;
  weekEnd: number;
  totalTrades: number;
  winRate: number;
  profitFactor: number;
  bestSetup: { setup: string; trades: number; pnl: number } | null;
  worstSetup: { setup: string; trades: number; pnl: number } | null;
  timeOfDay: Record<number, { trades: number; winRate: number; pnl: number }>;
  regimePerformance: Record<string, { trades: number; winRate: number; pnl: number }>;
  recommendations: string[];
}

export function useTradeJournal() {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [insights, setInsights] = useState<WeeklyInsight[]>([]);
  const [loading, setLoading] = useState(false);
  const entriesRef = useRef<JournalEntry[]>([]);

  // Load from Supabase on mount
  const loadFromSupabase = useCallback(async () => {
    setLoading(true);
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { setLoading(false); return; }

      const { data } = await supabase
        .from('trade_journal')
        .select('*')
        .eq('user_id', user.id)
        .order('timestamp', { ascending: false })
        .limit(500);

      if (data) {
        const loaded: JournalEntry[] = data.map((j: any) => ({
          id: j.id,
          timestamp: new Date(j.timestamp).getTime(),
          symbol: j.symbol,
          contractType: j.contract_type,
          entryPrice: j.entry_price,
          entryDigit: j.entry_digit || 0,
          exitPrice: j.exit_price,
          exitDigit: j.exit_digit,
          amount: j.amount,
          confidence: j.confidence,
          regime: j.regime as RegimeType,
          entryConditions: j.entry_conditions || [],
          exitConditions: j.exit_conditions || [],
          profit: j.profit,
          pnl: j.pnl,
          drawdownImpact: j.drawdown_impact,
          runningBalance: j.running_balance,
          peakBalance: j.peak_balance,
          notes: j.notes || '',
        }));
        entriesRef.current = loaded;
        setEntries([...loaded]);
      }

      // Load saved insights
      const { data: iData } = await supabase
        .from('weekly_insights')
        .select('*')
        .eq('user_id', user.id)
        .order('week_start', { ascending: false })
        .limit(52);

      if (iData) {
        setInsights(iData.map((w: any) => ({
          weekStart: new Date(w.week_start).getTime(),
          weekEnd: new Date(w.week_end).getTime(),
          totalTrades: w.total_trades,
          winRate: w.win_rate,
          profitFactor: w.profit_factor,
          bestSetup: w.best_setup,
          worstSetup: w.worst_setup,
          timeOfDay: w.time_of_day,
          regimePerformance: w.regime_performance,
          recommendations: w.recommendations || [],
        })));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const addEntry = useCallback(async (entry: Omit<JournalEntry, 'id' | 'drawdownImpact' | 'runningBalance' | 'peakBalance'>) => {
    const prevEntries = entriesRef.current;
    const lastEntry = prevEntries[0];
    const runningBalance = lastEntry ? lastEntry.runningBalance + (entry.profit || 0) : 1000 + (entry.profit || 0);
    const peakBalance = lastEntry
      ? Math.max(lastEntry.peakBalance, runningBalance)
      : Math.max(1000, runningBalance);
    const drawdownImpact = peakBalance > 0
      ? ((peakBalance - runningBalance) / peakBalance) * 100
      : 0;

    const fullEntry: JournalEntry = {
      ...entry,
      id: `journal-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      drawdownImpact,
      runningBalance,
      peakBalance,
    };

    entriesRef.current = [fullEntry, ...entriesRef.current].slice(0, 500);
    setEntries([...entriesRef.current]);

    // Persist to Supabase
    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      await supabase.from('trade_journal').insert({
        user_id: user.id,
        timestamp: new Date(fullEntry.timestamp).toISOString(),
        symbol: fullEntry.symbol,
        contract_type: fullEntry.contractType,
        entry_price: fullEntry.entryPrice,
        entry_digit: fullEntry.entryDigit,
        amount: fullEntry.amount,
        confidence: fullEntry.confidence,
        regime: fullEntry.regime,
        entry_conditions: fullEntry.entryConditions,
        exit_conditions: fullEntry.exitConditions,
        profit: fullEntry.profit,
        pnl: fullEntry.pnl,
        drawdown_impact: fullEntry.drawdownImpact,
        running_balance: fullEntry.runningBalance,
        peak_balance: fullEntry.peakBalance,
        notes: fullEntry.notes,
      });
    }

    return fullEntry;
  }, []);

  const updateExit = useCallback(async (entryId: string, exitPrice: number, exitDigit: number, profit: number, exitConditions: string[]) => {
    entriesRef.current = entriesRef.current.map(e => {
      if (e.id !== entryId) return e;
      const runningBalance = e.runningBalance + profit;
      const peakBalance = Math.max(e.peakBalance, runningBalance);
      const drawdownImpact = peakBalance > 0 ? ((peakBalance - runningBalance) / peakBalance) * 100 : 0;
      return {
        ...e,
        exitPrice,
        exitDigit,
        profit,
        pnl: profit,
        exitConditions,
        drawdownImpact,
        runningBalance,
        peakBalance,
      };
    });
    setEntries([...entriesRef.current]);

    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      const entry = entriesRef.current.find(e => e.id === entryId);
      if (entry) {
        await supabase.from('trade_journal')
          .update({
            exit_price: exitPrice,
            exit_digit: exitDigit,
            profit,
            pnl: profit,
            exit_conditions: exitConditions,
            drawdown_impact: entry.drawdownImpact,
            running_balance: entry.runningBalance,
            peak_balance: entry.peakBalance,
          })
          .eq('id', entryId)
          .eq('user_id', user.id);
      }
    }
  }, []);

  const generateWeeklyInsights = useCallback(async (): Promise<WeeklyInsight[]> => {
    const all = entriesRef.current.filter(e => e.profit !== null);
    if (all.length === 0) return [];

    const weekMap: Record<string, JournalEntry[]> = {};
    for (const entry of all) {
      const date = new Date(entry.timestamp);
      const weekStart = new Date(date.getFullYear(), date.getMonth(), date.getDate() - date.getDay());
      const key = weekStart.toISOString().split('T')[0];
      weekMap[key] = weekMap[key] || [];
      weekMap[key].push(entry);
    }

    const generated: WeeklyInsight[] = Object.entries(weekMap).map(([weekStart, trades]) => {
      const wins = trades.filter(t => (t.profit || 0) > 0);
      const losses = trades.filter(t => (t.profit || 0) <= 0);
      const grossProfit = wins.reduce((s, t) => s + (t.profit || 0), 0);
      const grossLoss = Math.abs(losses.reduce((s, t) => s + (t.profit || 0), 0)) || 1e-10;

      const bySetup: Record<string, { trades: number; pnl: number }> = {};
      for (const t of trades) {
        const key = t.contractType;
        bySetup[key] = bySetup[key] || { trades: 0, pnl: 0 };
        bySetup[key].trades++;
        bySetup[key].pnl += t.profit || 0;
      }
      const setups = Object.entries(bySetup);
      const best = setups.length > 0 ? setups.sort((a, b) => b[1].pnl - a[1].pnl)[0] : null;
      const worst = setups.length > 0 ? setups.sort((a, b) => a[1].pnl - b[1].pnl)[0] : null;

      const timeOfDay: Record<number, { trades: number; winRate: number; pnl: number }> = {};
      for (const t of trades) {
        const hour = new Date(t.timestamp).getHours();
        timeOfDay[hour] = timeOfDay[hour] || { trades: 0, winRate: 0, pnl: 0 };
        timeOfDay[hour].trades++;
        timeOfDay[hour].pnl += t.profit || 0;
      }
      for (const hour of Object.keys(timeOfDay)) {
        const h = parseInt(hour);
        const hourTrades = trades.filter(t => new Date(t.timestamp).getHours() === h);
        const hourWins = hourTrades.filter(t => (t.profit || 0) > 0);
        timeOfDay[h].winRate = hourTrades.length > 0 ? (hourWins.length / hourTrades.length) * 100 : 0;
      }

      const regimePerf: Record<string, { trades: number; winRate: number; pnl: number }> = {};
      for (const t of trades) {
        regimePerf[t.regime] = regimePerf[t.regime] || { trades: 0, winRate: 0, pnl: 0 };
        regimePerf[t.regime].trades++;
        regimePerf[t.regime].pnl += t.profit || 0;
      }
      for (const regime of Object.keys(regimePerf)) {
        const regimeTrades = trades.filter(t => t.regime === regime);
        const regimeWins = regimeTrades.filter(t => (t.profit || 0) > 0);
        regimePerf[regime].winRate = regimeTrades.length > 0 ? (regimeWins.length / regimeTrades.length) * 100 : 0;
      }

      const recommendations: string[] = [];
      if (best && best[1].pnl > 0) {
        recommendations.push(`Focus on ${best[0]} setups — generated $${best[1].pnl.toFixed(2)} this week`);
      }
      if (worst && worst[1].pnl < 0) {
        recommendations.push(`Avoid ${worst[0]} setups — lost $${Math.abs(worst[1].pnl).toFixed(2)} this week`);
      }
      const bestHour = Object.entries(timeOfDay).sort((a, b) => b[1].pnl - a[1].pnl)[0];
      if (bestHour && bestHour[1].pnl > 0) {
        recommendations.push(`Best trading hour: ${bestHour[0]}:00 (${bestHour[1].winRate.toFixed(0)}% WR)`);
      }
      const bestRegime = Object.entries(regimePerf).sort((a, b) => b[1].pnl - a[1].pnl)[0];
      if (bestRegime && bestRegime[1].pnl > 0) {
        recommendations.push(`Favor ${bestRegime[0]} regime — $${bestRegime[1].pnl.toFixed(2)} profit`);
      }
      if (grossProfit / grossLoss < 1) {
        recommendations.push('Profit factor below 1 — consider reducing trade frequency');
      }

      return {
        weekStart: new Date(weekStart).getTime(),
        weekEnd: new Date(weekStart).getTime() + 7 * 24 * 60 * 60 * 1000,
        totalTrades: trades.length,
        winRate: trades.length > 0 ? (wins.length / trades.length) * 100 : 0,
        profitFactor: grossProfit / grossLoss,
        bestSetup: best ? { setup: best[0], trades: best[1].trades, pnl: best[1].pnl } : null,
        worstSetup: worst ? { setup: worst[0], trades: worst[1].trades, pnl: worst[1].pnl } : null,
        timeOfDay,
        regimePerformance: regimePerf,
        recommendations,
      };
    }).sort((a, b) => b.weekStart - a.weekStart);

    // Persist insights to Supabase
    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      for (const insight of generated) {
        await supabase.from('weekly_insights').upsert({
          user_id: user.id,
          week_start: new Date(insight.weekStart).toISOString().split('T')[0],
          week_end: new Date(insight.weekEnd).toISOString().split('T')[0],
          total_trades: insight.totalTrades,
          win_rate: insight.winRate,
          profit_factor: insight.profitFactor,
          best_setup: insight.bestSetup,
          worst_setup: insight.worstSetup,
          time_of_day: insight.timeOfDay,
          regime_performance: insight.regimePerformance,
          recommendations: insight.recommendations,
        }, { onConflict: 'user_id,week_start' });
      }
    }

    return generated;
  }, []);

  const insightsMemo = useMemo(() => {
    generateWeeklyInsights();
    return insights;
  }, [entries, insights, generateWeeklyInsights]);

  const reset = useCallback(async () => {
    entriesRef.current = [];
    setEntries([]);
    setInsights([]);

    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      await supabase.from('trade_journal').delete().eq('user_id', user.id);
      await supabase.from('weekly_insights').delete().eq('user_id', user.id);
    }
  }, []);

  return {
    entries,
    insights: insightsMemo,
    loading,
    addEntry,
    updateExit,
    generateWeeklyInsights,
    reset,
    refresh: loadFromSupabase,
  };
}
