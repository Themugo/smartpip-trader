import { useState, useCallback, useRef } from 'react';
import type { RegimeType } from './useRegimeDetection';

export interface IndicatorSnapshot {
  name: string;
  value: number | string;
  threshold?: number;
  signal: 'bullish' | 'bearish' | 'neutral';
}

export interface AnalyzerOutput {
  name: string;
  prediction: string | null;
  confidence: number;
  reason: string;
  data: Record<string, unknown>;
}

export interface RiskCheck {
  name: string;
  passed: boolean;
  reason: string;
  severity: 'info' | 'warning' | 'critical';
}

export interface HistoricalSetup {
  similarTrades: number;
  winRate: number;
  avgProfit: number;
  avgLoss: number;
  profitFactor: number;
}

export interface TradeEvidence {
  id: string;
  timestamp: number;
  symbol: string;
  contractType: string;
  amount: number;
  indicators: IndicatorSnapshot[];
  analyzers: AnalyzerOutput[];
  confidence: number;
  regime: RegimeType;
  riskChecks: RiskCheck[];
  historicalSetup: HistoricalSetup | null;
  sizingAdjustments: { name: string; factor: number }[];
  explanation: string;
  blocked: boolean;
  blockReason: string | null;
}

let evidenceIdCounter = 0;

export function useTradeEvidence() {
  const [evidenceLog, setEvidenceLog] = useState<TradeEvidence[]>([]);
  const evidenceRef = useRef<TradeEvidence[]>([]);

  const buildEvidence = useCallback((
    symbol: string,
    contractType: string,
    amount: number,
    digitHistory: number[],
    price: number,
    regime: RegimeType,
    regimeConfidence: number,
    sizingAdjustments: { name: string; factor: number }[],
    isStrategyAllowed: boolean,
    strategyBlockReason: string,
    isGloballyBlocked: boolean,
    globalBlockReason: string | null,
  ): TradeEvidence => {
    const last20 = digitHistory.slice(-20);

    // Build indicator snapshots
    const indicators: IndicatorSnapshot[] = [
      {
        name: 'Even/Odd Bias',
        value: last20.length > 0 ? (last20.filter(d => d % 2 === 0).length / last20.length * 100).toFixed(1) + '%' : 'N/A',
        threshold: 55,
        signal: last20.filter(d => d % 2 === 0).length > last20.length * 0.55 ? 'bullish' : 'neutral',
      },
      {
        name: 'Over/Under Bias',
        value: last20.length > 0 ? (last20.filter(d => d >= 5).length / last20.length * 100).toFixed(1) + '%' : 'N/A',
        threshold: 55,
        signal: last20.filter(d => d >= 5).length > last20.length * 0.55 ? 'bullish' : 'neutral',
      },
      {
        name: 'Digit Variance',
        value: last20.length > 0 ? (Math.max(...last20) - Math.min(...last20)).toString() : 'N/A',
        signal: 'neutral',
      },
      {
        name: 'Last Digit',
        value: last20.length > 0 ? last20[last20.length - 1].toString() : 'N/A',
        signal: 'neutral',
      },
    ];

    // Build analyzer outputs
    const analyzers: AnalyzerOutput[] = [];

    if (contractType.includes('EVEN') || contractType.includes('ODD')) {
      const evens = last20.filter(d => d % 2 === 0).length;
      const odds = last20.length - evens;
      analyzers.push({
        name: 'EvenOddAnalyzer',
        prediction: evens > odds ? 'odd' : 'even',
        confidence: Math.min(50 + Math.abs(evens - odds) * 3, 95),
        reason: evens > odds + 2 ? 'Mean reversion: majority even, predict odd' : 'Streak detected',
        data: { evens, odds, streak: 1 },
      });
    }

    if (contractType.includes('OVER') || contractType.includes('UNDER')) {
      const overs = last20.filter(d => d >= 5).length;
      const unders = last20.length - overs;
      analyzers.push({
        name: 'OverUnderAnalyzer',
        prediction: overs > unders ? 'under' : 'over',
        confidence: Math.min(50 + Math.abs(overs - unders) * 3, 95),
        reason: overs > unders + 2 ? 'Mean reversion: majority over, predict under' : 'Streak detected',
        data: { overs, unders, barrier: 5 },
      });
    }

    if (contractType.includes('MATCH') || contractType.includes('DIFF')) {
      let matches = 0;
      for (let i = 1; i < last20.length; i++) {
        if (last20[i] === last20[i - 1]) matches++;
      }
      const diffs = last20.length - 1 - matches;
      analyzers.push({
        name: 'MatchDiffAnalyzer',
        prediction: matches > diffs ? 'diff' : 'match',
        confidence: Math.min(50 + Math.abs(matches - diffs) * 2, 95),
        reason: matches > diffs ? 'Mean reversion: majority match, predict diff' : 'Streak detected',
        data: { matches, diffs },
      });
    }

    // Risk checks
    const riskChecks: RiskCheck[] = [
      {
        name: 'Minimum Data',
        passed: digitHistory.length >= 20,
        reason: digitHistory.length >= 20 ? 'Sufficient digit history' : `Only ${digitHistory.length} digits, need 20`,
        severity: digitHistory.length >= 20 ? 'info' : 'critical',
      },
      {
        name: 'Regime Compatibility',
        passed: isStrategyAllowed,
        reason: isStrategyAllowed ? 'Strategy supports current regime' : strategyBlockReason,
        severity: isStrategyAllowed ? 'info' : 'warning',
      },
      {
        name: 'Global Trading Status',
        passed: !isGloballyBlocked,
        reason: !isGloballyBlocked ? 'Trading permitted' : (globalBlockReason || 'Trading blocked'),
        severity: !isGloballyBlocked ? 'info' : 'critical',
      },
      {
        name: 'Regime Confidence',
        passed: regimeConfidence >= 40,
        reason: `Regime confidence: ${regimeConfidence.toFixed(0)}%`,
        severity: regimeConfidence >= 40 ? 'info' : 'warning',
      },
      {
        name: 'Price Validity',
        passed: price > 0,
        reason: price > 0 ? 'Valid price data' : 'No price available',
        severity: price > 0 ? 'info' : 'critical',
      },
    ];

    const allPassed = riskChecks.every(r => r.passed);
    const blockReason = allPassed ? null : riskChecks.filter(r => !r.passed).map(r => r.reason).join('; ');

    // Historical setup (simulated from evidence log)
    const historicalSetup: HistoricalSetup | null = null; // Would query similar setups from DB

    // Generate explanation
    const explanationLines: string[] = [];
    explanationLines.push(`Trade Signal: ${contractType} on ${symbol}`);
    explanationLines.push(`Amount: $${amount.toFixed(2)}`);
    explanationLines.push(`Market Regime: ${regime} (${regimeConfidence.toFixed(0)}% confidence)`);
    explanationLines.push('');
    explanationLines.push('Indicators:');
    indicators.forEach(i => {
      explanationLines.push(`  ${i.name}: ${i.value} [${i.signal}]`);
    });
    explanationLines.push('');
    explanationLines.push('Analyzer Outputs:');
    analyzers.forEach(a => {
      explanationLines.push(`  ${a.name}: ${a.prediction} (${a.confidence}% confidence) — ${a.reason}`);
    });
    explanationLines.push('');
    explanationLines.push('Risk Checks:');
    riskChecks.forEach(r => {
      explanationLines.push(`  [${r.passed ? 'PASS' : 'FAIL'}] ${r.name}: ${r.reason}`);
    });
    if (sizingAdjustments.length > 0) {
      explanationLines.push('');
      explanationLines.push('Sizing Adjustments:');
      sizingAdjustments.forEach(s => {
        explanationLines.push(`  ${s.name}: ${s.factor < 1 ? '' : '+'}${((s.factor - 1) * 100).toFixed(0)}%`);
      });
    }

    const evidence: TradeEvidence = {
      id: `evidence-${++evidenceIdCounter}-${Date.now()}`,
      timestamp: Date.now(),
      symbol,
      contractType,
      amount,
      indicators,
      analyzers,
      confidence: analyzers.length > 0 ? Math.max(...analyzers.map(a => a.confidence)) : 0,
      regime,
      riskChecks,
      historicalSetup,
      sizingAdjustments,
      explanation: explanationLines.join('\n'),
      blocked: !allPassed,
      blockReason,
    };

    evidenceRef.current = [evidence, ...evidenceRef.current].slice(0, 100);
    setEvidenceLog([...evidenceRef.current]);

    return evidence;
  }, [evidenceLog]);

  const getEvidenceById = useCallback((id: string): TradeEvidence | undefined => {
    return evidenceRef.current.find(e => e.id === id);
  }, []);

  return { evidenceLog, buildEvidence, getEvidenceById };
}
