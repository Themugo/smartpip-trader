import { useState, useCallback, useRef } from 'react';
import type { SizingConfig, TradeRecord } from './useAdaptivePositionSizing';

export interface SimulationParams {
  numTrades: number;
  winRate: number;
  avgWin: number;
  avgLoss: number;
  startingBalance: number;
  volatility: number; // std dev of returns
  strategy: string;
}

export interface SimulationResult {
  name: string;
  finalBalance: number;
  totalReturn: number;
  maxDrawdown: number;
  maxDrawdownPct: number;
  sharpeRatio: number;
  profitFactor: number;
  winRate: number;
  numTrades: number;
  equityCurve: number[];
  tradeSizes: number[];
  trades: TradeRecord[];
}

function generateTrade(params: SimulationParams, rng: () => number): number {
  const isWin = rng() < params.winRate;
  const base = isWin ? params.avgWin : -params.avgLoss;
  // Add noise
  const noise = (rng() - 0.5) * 2 * params.volatility;
  return base + noise;
}

function calculateStd(data: number[]): number {
  const mean = data.reduce((a, b) => a + b, 0) / data.length;
  return Math.sqrt(data.reduce((sq, n) => sq + Math.pow(n - mean, 2), 0) / data.length);
}

function calculateSharpe(returns: number[]): number {
  if (returns.length < 2) return 0;
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
  const std = calculateStd(returns);
  return std > 0 ? mean / std : 0;
}

export function useSizingSimulation() {
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const abortRef = useRef(false);

  const runSimulation = useCallback(async (
    params: SimulationParams,
    sizingConfig: SizingConfig,
    sizingFn: (confidence: number, strategy: string, volatilityData?: number[]) => {
      size: number;
      blocked: boolean;
      blockReason: string | null;
    }
  ): Promise<SimulationResult> => {
    abortRef.current = false;
    setIsRunning(true);
    setProgress(0);

    const trades: TradeRecord[] = [];
    const equityCurve: number[] = [params.startingBalance];
    const tradeSizes: number[] = [];
    let balance = params.startingBalance;
    let peak = balance;
    let maxDD = 0;
    const prices: number[] = [100]; // synthetic price series

    // Seeded RNG
    let seed = 42;
    const rng = () => {
      seed = (seed * 16807 + 0) % 2147483647;
      return seed / 2147483647;
    };

    for (let i = 0; i < params.numTrades; i++) {
      if (abortRef.current) break;

      // Generate price for volatility calc
      const priceChange = (rng() - 0.5) * params.volatility * 2;
      prices.push(prices[prices.length - 1] * (1 + priceChange));

      // Confidence varies with "market conditions"
      const confidence = 50 + Math.floor(rng() * 40); // 50-90

      // Get adaptive size
      const sizing = sizingFn(confidence, params.strategy, prices.slice(-20));

      let profit: number;
      let size: number;

      if (sizing.blocked) {
        // Skip trade but still "pass time"
        profit = 0;
        size = 0;
      } else {
        size = sizing.size;
        const rawProfit = generateTrade(params, rng);
        // Scale profit by size (assuming $1 base)
        profit = rawProfit * size;
      }

      tradeSizes.push(size);
      balance += profit;

      if (balance > peak) peak = balance;
      const dd = peak > 0 ? peak - balance : 0;
      if (dd > maxDD) maxDD = dd;

      trades.push({ profit, timestamp: Date.now() + i, strategy: params.strategy });
      equityCurve.push(balance);

      if (i % 100 === 0) {
        setProgress(Math.round((i / params.numTrades) * 100));
        await new Promise((r) => setTimeout(r, 0));
      }
    }

    const returns = trades.map((t) => t.profit);
    const wins = trades.filter((t) => t.profit > 0);
    const losses = trades.filter((t) => t.profit < 0);
    const grossProfit = wins.reduce((s, t) => s + t.profit, 0);
    const grossLoss = Math.abs(losses.reduce((s, t) => s + t.profit, 0)) || 1e-10;

    setIsRunning(false);
    setProgress(100);

    return {
      name: 'Adaptive',
      finalBalance: balance,
      totalReturn: ((balance - params.startingBalance) / params.startingBalance) * 100,
      maxDrawdown: maxDD,
      maxDrawdownPct: peak > 0 ? (maxDD / peak) * 100 : 0,
      sharpeRatio: calculateSharpe(returns),
      profitFactor: grossProfit / grossLoss,
      winRate: trades.length > 0 ? (wins.length / trades.length) * 100 : 0,
      numTrades: trades.length,
      equityCurve,
      tradeSizes,
      trades,
    };
  }, []);

  const runFixedSimulation = useCallback(async (
    params: SimulationParams,
    fixedSize: number
  ): Promise<SimulationResult> => {
    abortRef.current = false;
    setIsRunning(true);
    setProgress(0);

    const trades: TradeRecord[] = [];
    const equityCurve: number[] = [params.startingBalance];
    const tradeSizes: number[] = [];
    let balance = params.startingBalance;
    let peak = balance;
    let maxDD = 0;

    let seed = 123;
    const rng = () => {
      seed = (seed * 16807 + 0) % 2147483647;
      return seed / 2147483647;
    };

    for (let i = 0; i < params.numTrades; i++) {
      if (abortRef.current) break;

      const profit = generateTrade(params, rng) * fixedSize;
      tradeSizes.push(fixedSize);
      balance += profit;

      if (balance > peak) peak = balance;
      const dd = peak > 0 ? peak - balance : 0;
      if (dd > maxDD) maxDD = dd;

      trades.push({ profit, timestamp: Date.now() + i, strategy: params.strategy });
      equityCurve.push(balance);

      if (i % 100 === 0) {
        setProgress(Math.round((i / params.numTrades) * 100));
        await new Promise((r) => setTimeout(r, 0));
      }
    }

    const returns = trades.map((t) => t.profit);
    const wins = trades.filter((t) => t.profit > 0);
    const losses = trades.filter((t) => t.profit < 0);
    const grossProfit = wins.reduce((s, t) => s + t.profit, 0);
    const grossLoss = Math.abs(losses.reduce((s, t) => s + t.profit, 0)) || 1e-10;

    setIsRunning(false);
    setProgress(100);

    return {
      name: 'Fixed',
      finalBalance: balance,
      totalReturn: ((balance - params.startingBalance) / params.startingBalance) * 100,
      maxDrawdown: maxDD,
      maxDrawdownPct: peak > 0 ? (maxDD / peak) * 100 : 0,
      sharpeRatio: calculateSharpe(returns),
      profitFactor: grossProfit / grossLoss,
      winRate: trades.length > 0 ? (wins.length / trades.length) * 100 : 0,
      numTrades: trades.length,
      equityCurve,
      tradeSizes,
      trades,
    };
  }, []);

  const abort = useCallback(() => {
    abortRef.current = true;
  }, []);

  return {
    runSimulation,
    runFixedSimulation,
    isRunning,
    progress,
    abort,
  };
}
