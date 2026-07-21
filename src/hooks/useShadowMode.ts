import { useState, useCallback, useRef, useEffect } from 'react';
import { supabase } from '../lib/supabase';

export interface ShadowSignal {
  id: string;
  timestamp: number;
  symbol: string;
  contractType: string;
  predictedDirection: string;
  confidence: number;
  expectedOutcome: 'win' | 'loss' | 'unknown';
  actualOutcome: 'win' | 'loss' | 'pending' | 'missed';
  expectedPnl: number;
  actualPnl: number | null;
  latencyMs: number;
  executed: boolean;
  missedReason: string | null;
  modelVersion: string;
}

export interface ShadowMetrics {
  totalSignals: number;
  executedSignals: number;
  missedSignals: number;
  signalAccuracy: number;
  paperPnl: number;
  realPnl: number;
  pnlDelta: number;
  avgLatencyMs: number;
  modelDrift: number;
  daysInShadow: number;
  profitableDays: number;
  isQualified: boolean;
}

export interface ShadowDailyMetric {
  date: string;
  totalSignals: number;
  executedSignals: number;
  missedSignals: number;
  signalAccuracy: number;
  paperPnl: number;
  realPnl: number;
  pnlDelta: number;
  avgLatencyMs: number;
  modelDrift: number;
  isProfitable: boolean;
}

export function useShadowMode() {
  const [signals, setSignals] = useState<ShadowSignal[]>([]);
  const [metrics, setMetrics] = useState<ShadowMetrics>({
    totalSignals: 0, executedSignals: 0, missedSignals: 0, signalAccuracy: 0,
    paperPnl: 0, realPnl: 0, pnlDelta: 0, avgLatencyMs: 0, modelDrift: 0,
    daysInShadow: 0, profitableDays: 0, isQualified: false,
  });
  const [dailyMetrics, setDailyMetrics] = useState<ShadowDailyMetric[]>([]);
  const [loading, setLoading] = useState(false);

  const signalsRef = useRef<ShadowSignal[]>([]);
  const startDateRef = useRef<number>(Date.now());

  // Load from Supabase on mount
  useEffect(() => {
    loadFromSupabase();
  }, []);

  const loadFromSupabase = async () => {
    setLoading(true);
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { setLoading(false); return; }

      // Load recent signals
      const { data: sigData } = await supabase
        .from('shadow_signals')
        .select('*')
        .eq('user_id', user.id)
        .order('timestamp', { ascending: false })
        .limit(200);

      if (sigData) {
        const loaded: ShadowSignal[] = sigData.map((s) => ({
          id: s.id,
          timestamp: new Date(s.timestamp).getTime(),
          symbol: s.symbol,
          contractType: s.contract_type,
          predictedDirection: s.predicted_direction,
          confidence: s.confidence,
          expectedOutcome: s.expected_outcome,
          actualOutcome: s.actual_outcome || 'pending',
          expectedPnl: s.expected_pnl,
          actualPnl: s.actual_pnl,
          latencyMs: s.latency_ms,
          executed: s.executed,
          missedReason: s.missed_reason,
          modelVersion: s.model_version,
        }));
        signalsRef.current = loaded;
        setSignals([...loaded]);
      }

      // Load daily metrics
      const { data: dmData } = await supabase
        .from('shadow_daily_metrics')
        .select('*')
        .eq('user_id', user.id)
        .order('date', { ascending: false })
        .limit(90);

      if (dmData) {
        setDailyMetrics(dmData.map((d) => ({
          date: d.date,
          totalSignals: d.total_signals,
          executedSignals: d.executed_signals,
          missedSignals: d.missed_signals,
          signalAccuracy: d.signal_accuracy,
          paperPnl: d.paper_pnl,
          realPnl: d.real_pnl,
          pnlDelta: d.pnl_delta,
          avgLatencyMs: d.avg_latency_ms,
          modelDrift: d.model_drift,
          isProfitable: d.is_profitable,
        })));
      }

      // Load qualification
      const { data: qData } = await supabase
        .from('shadow_qualification')
        .select('*')
        .eq('user_id', user.id)
        .single();

      if (qData) {
        startDateRef.current = new Date(qData.start_date).getTime();
      } else {
        // Initialize qualification record
        await supabase.from('shadow_qualification').insert({
          user_id: user.id,
          start_date: new Date().toISOString(),
          days_in_shadow: 0,
          profitable_days: 0,
          total_paper_pnl: 0,
          is_qualified: false,
        });
      }
    } finally {
      setLoading(false);
    }
  };

  // Recalculate metrics whenever signals change
  useEffect(() => {
    const all = signalsRef.current;
    if (all.length === 0) return;

    const executed = all.filter(s => s.executed);
    const missed = all.filter(s => !s.executed && s.actualOutcome === 'missed');
    const resolved = all.filter(s => s.actualOutcome === 'win' || s.actualOutcome === 'loss');
    const correct = resolved.filter(s =>
      (s.expectedOutcome === 'win' && s.actualOutcome === 'win') ||
      (s.expectedOutcome === 'loss' && s.actualOutcome === 'loss')
    );

    const paperPnl = all.reduce((s, sig) => s + (sig.actualPnl || 0), 0);
    const realPnl = executed.reduce((s, sig) => s + (sig.actualPnl || 0), 0);

    const latencies = all.map(s => s.latencyMs).filter(l => l > 0);
    const avgLatency = latencies.length > 0 ? latencies.reduce((a, b) => a + b, 0) / latencies.length : 0;

    const split = Math.floor(resolved.length * 0.8);
    const early = resolved.slice(0, split);
    const recent = resolved.slice(split);
    const earlyAcc = early.length > 0 ? early.filter(s =>
      (s.expectedOutcome === 'win' && s.actualOutcome === 'win') ||
      (s.expectedOutcome === 'loss' && s.actualOutcome === 'loss')
    ).length / early.length : 0;
    const recentAcc = recent.length > 0 ? recent.filter(s =>
      (s.expectedOutcome === 'win' && s.actualOutcome === 'win') ||
      (s.expectedOutcome === 'loss' && s.actualOutcome === 'loss')
    ).length / recent.length : 0;
    const drift = earlyAcc > 0 ? ((earlyAcc - recentAcc) / earlyAcc) * 100 : 0;

    const daysInShadow = Math.max(1, Math.floor((Date.now() - startDateRef.current) / (1000 * 60 * 60 * 24)));
    const profitableDays = dailyMetrics.filter(d => d.isProfitable).length;

    const newMetrics: ShadowMetrics = {
      totalSignals: all.length,
      executedSignals: executed.length,
      missedSignals: missed.length,
      signalAccuracy: resolved.length > 0 ? (correct.length / resolved.length) * 100 : 0,
      paperPnl,
      realPnl,
      pnlDelta: paperPnl - realPnl,
      avgLatencyMs: avgLatency,
      modelDrift: drift,
      daysInShadow,
      profitableDays,
      isQualified: daysInShadow >= 30 && paperPnl > 0 && drift < 20,
    };

    setMetrics(newMetrics);
    saveMetricsToSupabase(newMetrics);
  }, [signals, dailyMetrics]);

  const saveMetricsToSupabase = async (m: ShadowMetrics) => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return;

    const today = new Date().toISOString().split('T')[0];
    await supabase.from('shadow_daily_metrics').upsert({
      user_id: user.id,
      date: today,
      total_signals: m.totalSignals,
      executed_signals: m.executedSignals,
      missed_signals: m.missedSignals,
      signal_accuracy: m.signalAccuracy,
      paper_pnl: m.paperPnl,
      real_pnl: m.realPnl,
      pnl_delta: m.pnlDelta,
      avg_latency_ms: m.avgLatencyMs,
      model_drift: m.modelDrift,
      is_profitable: m.paperPnl > 0,
    }, { onConflict: 'user_id,date' });

    await supabase.from('shadow_qualification').upsert({
      user_id: user.id,
      days_in_shadow: m.daysInShadow,
      profitable_days: m.profitableDays,
      total_paper_pnl: m.paperPnl,
      is_qualified: m.isQualified,
      qualified_at: m.isQualified ? new Date().toISOString() : null,
      last_evaluated_at: new Date().toISOString(),
    }, { onConflict: 'user_id' });
  };

  const generateSignal = useCallback(async (
    symbol: string,
    contractType: string,
    predictedDirection: string,
    confidence: number,
    expectedOutcome: 'win' | 'loss',
    expectedPnl: number,
    latencyMs: number,
    modelVersion: string = 'v1.0'
  ): Promise<ShadowSignal> => {
    const { data: { user } } = await supabase.auth.getUser();

    const signal: ShadowSignal = {
      id: `shadow-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      timestamp: Date.now(),
      symbol,
      contractType,
      predictedDirection,
      confidence,
      expectedOutcome,
      actualOutcome: 'pending',
      expectedPnl,
      actualPnl: null,
      latencyMs,
      executed: false,
      missedReason: null,
      modelVersion,
    };

    signalsRef.current = [signal, ...signalsRef.current].slice(0, 500);
    setSignals([...signalsRef.current]);

    // Persist to Supabase
    if (user) {
      await supabase.from('shadow_signals').insert({
        user_id: user.id,
        symbol,
        contract_type: contractType,
        predicted_direction: predictedDirection,
        confidence,
        expected_outcome: expectedOutcome,
        actual_outcome: 'pending',
        expected_pnl: expectedPnl,
        latency_ms: latencyMs,
        executed: false,
        model_version: modelVersion,
      });
    }

    return signal;
  }, []);

  const markExecuted = useCallback(async (signalId: string, actualPnl: number) => {
    signalsRef.current = signalsRef.current.map(s =>
      s.id === signalId
        ? { ...s, executed: true, actualOutcome: actualPnl > 0 ? 'win' : 'loss', actualPnl }
        : s
    );
    setSignals([...signalsRef.current]);

    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      await supabase.from('shadow_signals')
        .update({ executed: true, actual_outcome: actualPnl > 0 ? 'win' : 'loss', actual_pnl: actualPnl })
        .eq('id', signalId)
        .eq('user_id', user.id);
    }
  }, []);

  const markMissed = useCallback(async (signalId: string, reason: string, actualOutcome?: 'win' | 'loss', actualPnl?: number) => {
    signalsRef.current = signalsRef.current.map(s =>
      s.id === signalId
        ? { ...s, executed: false, missedReason: reason, actualOutcome: actualOutcome || 'missed', actualPnl: actualPnl || null }
        : s
    );
    setSignals([...signalsRef.current]);

    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      await supabase.from('shadow_signals')
        .update({
          executed: false,
          missed_reason: reason,
          actual_outcome: actualOutcome || 'missed',
          actual_pnl: actualPnl || null,
        })
        .eq('id', signalId)
        .eq('user_id', user.id);
    }
  }, []);

  const resolveSignal = useCallback(async (signalId: string, actualOutcome: 'win' | 'loss', actualPnl: number) => {
    signalsRef.current = signalsRef.current.map(s =>
      s.id === signalId ? { ...s, actualOutcome, actualPnl } : s
    );
    setSignals([...signalsRef.current]);

    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      await supabase.from('shadow_signals')
        .update({ actual_outcome: actualOutcome, actual_pnl: actualPnl })
        .eq('id', signalId)
        .eq('user_id', user.id);
    }
  }, []);

  const reset = useCallback(async () => {
    signalsRef.current = [];
    startDateRef.current = Date.now();
    setSignals([]);
    setDailyMetrics([]);

    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      await supabase.from('shadow_signals').delete().eq('user_id', user.id);
      await supabase.from('shadow_daily_metrics').delete().eq('user_id', user.id);
      await supabase.from('shadow_qualification').delete().eq('user_id', user.id);
    }
  }, []);

  return {
    signals,
    metrics,
    dailyMetrics,
    loading,
    generateSignal,
    markExecuted,
    markMissed,
    resolveSignal,
    reset,
    refresh: loadFromSupabase,
  };
}
