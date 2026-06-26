import { useState, useCallback, useRef, useEffect } from 'react';

export interface SizingConfig {
  baseAmount: number;
  maxRiskPerTrade: number;      // % of balance
  maxDailyExposure: number;     // % of balance
  kellyFraction: number;        // 0-1, typically 0.25
  volatilityLookback: number;   // ticks
  confidenceWeight: number;     // 0-1, how much confidence affects size
  drawdownReductionStart: number; // % drawdown where reduction begins
  drawdownMax: number;          // % drawdown where size = 0
  lossStreakReduction: boolean;
  winStreakBoost: boolean;
  minTradeSize: number;
  maxTradeSize: number;
}

export interface SizingResult {
  size: number;
  rawSize: number;
  adjustments: SizingAdjustment[];
  blocked: boolean;
  blockReason: string | null;
  dailyExposureUsed: number;
  dailyExposureRemaining: number;
  kellyEstimate: number | null;
}

export interface SizingAdjustment {
  name: string;
  factor: number;
  description: string;
}

export interface TradeRecord {
  profit: number;
  timestamp: number;
  strategy: string;
}

const DEFAULT_CONFIG: SizingConfig = {
  baseAmount: 1.0,
  maxRiskPerTrade: 0.02,
  maxDailyExposure: 0.2,
  kellyFraction: 0.25,
  volatilityLookback: 50,
  confidenceWeight: 0.5,
  drawdownReductionStart: 5,
  drawdownMax: 20,
  lossStreakReduction: true,
  winStreakBoost: false,
  minTradeSize: 0.35,
  maxTradeSize: 500,
};

function calculateStd(data: number[]): number {
  const mean = data.reduce((a, b) => a + b, 0) / data.length;
  return Math.sqrt(data.reduce((sq, n) => sq + Math.pow(n - mean, 2), 0) / data.length);
}

function calculateMean(data: number[]): number {
  return data.reduce((a, b) => a + b, 0) / data.length;
}

export function useAdaptivePositionSizing(
  config: Partial<SizingConfig> = {}
) {
  const cfg = { ...DEFAULT_CONFIG, ...config };

  const [balance, setBalance] = useState(1000);
  const [peakBalance, setPeakBalance] = useState(1000);
  const [tradeHistory, setTradeHistory] = useState<TradeRecord[]>([]);
  const [dailyTrades, setDailyTrades] = useState<TradeRecord[]>([]);
  const [currentDrawdown, setCurrentDrawdown] = useState(0);

  const historyRef = useRef<TradeRecord[]>([]);
  const dailyRef = useRef<TradeRecord[]>([]);
  const balanceRef = useRef(1000);
  const peakRef = useRef(1000);

  // Reset daily exposure at midnight
  useEffect(() => {
    const checkDay = () => {
      const now = new Date();
      if (now.getHours() === 0 && now.getMinutes() < 5) {
        dailyRef.current = [];
        setDailyTrades([]);
      }
    };
    const interval = setInterval(checkDay, 60000);
    return () => clearInterval(interval);
  }, []);

  const calculateKelly = useCallback((trades: TradeRecord[]): number | null => {
    if (trades.length < 20) return null;

    const wins = trades.filter((t) => t.profit > 0);
    const losses = trades.filter((t) => t.profit < 0);

    if (wins.length === 0 || losses.length === 0) return null;

    const winRate = wins.length / trades.length;
    const avgWin = calculateMean(wins.map((t) => t.profit));
    const avgLoss = Math.abs(calculateMean(losses.map((t) => t.profit)));

    if (avgLoss === 0) return null;

    const winLossRatio = avgWin / avgLoss;
    const kelly = (winRate * winLossRatio - (1 - winRate)) / winLossRatio;

    return Math.max(0, Math.min(kelly, 0.5));
  }, []);

  const calculateVolatilityAdjustment = useCallback((returns: number[]): number => {
    if (returns.length < 10) return 1;

    const currentVol = calculateStd(returns.slice(-10));
    const historicalVol = calculateStd(returns);

    if (historicalVol === 0) return 1;

    const volRatio = currentVol / historicalVol;

    // Higher vol = smaller size
    if (volRatio > 2) return 0.5;
    if (volRatio > 1.5) return 0.7;
    if (volRatio > 1.2) return 0.85;
    if (volRatio < 0.5) return 1.3;
    if (volRatio < 0.8) return 1.15;
    return 1;
  }, []);

  const calculateDrawdownAdjustment = useCallback((drawdownPct: number): number => {
    if (drawdownPct <= 0) return 1;
    if (drawdownPct >= cfg.drawdownMax) return 0;

    // Linear reduction from start to max
    const reductionRange = cfg.drawdownMax - cfg.drawdownReductionStart;
    if (reductionRange <= 0) return 1;

    const progress = (drawdownPct - cfg.drawdownReductionStart) / reductionRange;
    if (progress <= 0) return 1;

    return Math.max(0.1, 1 - progress * 0.9);
  }, [cfg.drawdownMax, cfg.drawdownReductionStart]);

  const calculateStreakAdjustment = useCallback((trades: TradeRecord[]): number => {
    if (trades.length < 2) return 1;

    // Count consecutive from most recent
    let streak = 0;
    const isWin = trades[trades.length - 1].profit > 0;

    for (let i = trades.length - 1; i >= 0; i--) {
      const won = trades[i].profit > 0;
      if (won === isWin) {
        streak++;
      } else {
        break;
      }
    }

    if (isWin) {
      // Win streak — conservative boost (requires statistical significance)
      if (!cfg.winStreakBoost) return 1;
      // Only boost after 5+ wins with positive expectancy
      const recent = trades.slice(-streak);
      const expectancy = calculateMean(recent.map((t) => t.profit));
      if (streak >= 5 && expectancy > 0) {
        return Math.min(1.2, 1 + streak * 0.03);
      }
      return 1;
    } else {
      // Loss streak — always reduce
      if (!cfg.lossStreakReduction) return 1;
      if (streak >= 5) return 0.3;
      if (streak >= 3) return 0.5;
      if (streak >= 2) return 0.7;
      return 1;
    }
  }, [cfg.winStreakBoost, cfg.lossStreakReduction]);

  const calculateSize = useCallback((
    confidence: number,
    strategy: string,
    volatilityData?: number[]
  ): SizingResult => {
    const adjustments: SizingAdjustment[] = [];
    const currentBalance = balanceRef.current;
    const currentPeak = peakRef.current;
    const allTrades = historyRef.current;
    const todayTrades = dailyRef.current;

    // Calculate current drawdown
    const drawdownPct = currentPeak > 0
      ? ((currentPeak - currentBalance) / currentPeak) * 100
      : 0;

    // Check daily exposure limit
    const dailyExposure = todayTrades.reduce((s, t) => s + Math.abs(t.profit), 0);
    const dailyExposurePct = currentBalance > 0 ? (dailyExposure / currentBalance) * 100 : 0;

    if (dailyExposurePct >= cfg.maxDailyExposure * 100) {
      return {
        size: 0,
        rawSize: 0,
        adjustments,
        blocked: true,
        blockReason: `Daily exposure limit reached: ${dailyExposurePct.toFixed(1)}% / ${(cfg.maxDailyExposure * 100).toFixed(0)}%`,
        dailyExposureUsed: dailyExposurePct,
        dailyExposureRemaining: 0,
        kellyEstimate: null,
      };
    }

    // 1. Base size
    let size = cfg.baseAmount;
    adjustments.push({ name: 'Base', factor: 1, description: `Base amount $${cfg.baseAmount}` });

    // 2. Kelly Criterion (if sufficient data)
    const strategyTrades = allTrades.filter((t) => t.strategy === strategy);
    const kelly = calculateKelly(strategyTrades.length >= 20 ? strategyTrades : allTrades);
    let kellySize = size;

    if (kelly !== null) {
      kellySize = currentBalance * kelly * cfg.kellyFraction;
      // Only use Kelly if it's statistically significant (20+ trades)
      if (strategyTrades.length >= 20 || allTrades.length >= 20) {
        size = Math.min(size, kellySize); // Kelly is a ceiling
        adjustments.push({
          name: 'Kelly',
          factor: kellySize / cfg.baseAmount,
          description: `Kelly ${(kelly * 100).toFixed(2)}% × ${(cfg.kellyFraction * 100).toFixed(0)}% = $${kellySize.toFixed(2)}`,
        });
      }
    }

    // 3. Confidence weighting
    if (cfg.confidenceWeight > 0) {
      const confFactor = 0.5 + (confidence / 100) * cfg.confidenceWeight;
      size *= confFactor;
      adjustments.push({
        name: 'Confidence',
        factor: confFactor,
        description: `${(confidence).toFixed(0)}% confidence × ${cfg.confidenceWeight}`,
      });
    }

    // 4. Volatility adjustment
    if (volatilityData && volatilityData.length >= 10) {
      const returns: number[] = [];
      for (let i = 1; i < volatilityData.length; i++) {
        returns.push(Math.log(volatilityData[i] / volatilityData[i - 1]));
      }
      const volFactor = calculateVolatilityAdjustment(returns);
      size *= volFactor;
      adjustments.push({
        name: 'Volatility',
        factor: volFactor,
        description: volFactor < 1 ? 'High vol: reduce size' : 'Low vol: increase size',
      });
    }

    // 5. Drawdown reduction
    const ddFactor = calculateDrawdownAdjustment(drawdownPct);
    if (ddFactor < 1) {
      size *= ddFactor;
      adjustments.push({
        name: 'Drawdown',
        factor: ddFactor,
        description: `${drawdownPct.toFixed(1)}% DD: reduce to ${(ddFactor * 100).toFixed(0)}%`,
      });
    }

    // 6. Streak adjustment
    const streakFactor = calculateStreakAdjustment(allTrades);
    if (streakFactor !== 1) {
      size *= streakFactor;
      adjustments.push({
        name: 'Streak',
        factor: streakFactor,
        description: streakFactor < 1 ? 'Loss streak: reduce risk' : 'Win streak: cautious boost',
      });
    }

    const rawSize = size;

    // 7. Max risk per trade cap
    const maxRiskAmount = currentBalance * cfg.maxRiskPerTrade;
    if (size > maxRiskAmount) {
      size = maxRiskAmount;
      adjustments.push({
        name: 'Risk Cap',
        factor: maxRiskAmount / rawSize,
        description: `Capped at ${(cfg.maxRiskPerTrade * 100).toFixed(1)}% of balance`,
      });
    }

    // 8. Min/max bounds
    if (size < cfg.minTradeSize) {
      size = cfg.minTradeSize;
      adjustments.push({ name: 'Min Size', factor: cfg.minTradeSize / rawSize, description: `Minimum $${cfg.minTradeSize}` });
    }
    if (size > cfg.maxTradeSize) {
      size = cfg.maxTradeSize;
      adjustments.push({ name: 'Max Size', factor: cfg.maxTradeSize / rawSize, description: `Maximum $${cfg.maxTradeSize}` });
    }

    // Final block check
    if (size <= 0) {
      return {
        size: 0,
        rawSize,
        adjustments,
        blocked: true,
        blockReason: 'Calculated size is zero after risk adjustments',
        dailyExposureUsed: dailyExposurePct,
        dailyExposureRemaining: Math.max(0, cfg.maxDailyExposure * 100 - dailyExposurePct),
        kellyEstimate: kelly,
      };
    }

    return {
      size: Math.round(size * 100) / 100,
      rawSize: Math.round(rawSize * 100) / 100,
      adjustments,
      blocked: false,
      blockReason: null,
      dailyExposureUsed: dailyExposurePct,
      dailyExposureRemaining: Math.max(0, cfg.maxDailyExposure * 100 - dailyExposurePct),
      kellyEstimate: kelly,
    };
  }, [cfg, calculateKelly, calculateVolatilityAdjustment, calculateDrawdownAdjustment, calculateStreakAdjustment]);

  const recordTrade = useCallback((profit: number, strategy: string) => {
    const record: TradeRecord = {
      profit,
      timestamp: Date.now(),
      strategy,
    };

    historyRef.current = [...historyRef.current.slice(-499), record];
    dailyRef.current = [...dailyRef.current.slice(-99), record];

    const newBalance = balanceRef.current + profit;
    balanceRef.current = newBalance;

    if (newBalance > peakRef.current) {
      peakRef.current = newBalance;
    }

    const dd = peakRef.current > 0
      ? ((peakRef.current - newBalance) / peakRef.current) * 100
      : 0;

    setBalance(newBalance);
    setPeakBalance(peakRef.current);
    setTradeHistory([...historyRef.current]);
    setDailyTrades([...dailyRef.current]);
    setCurrentDrawdown(dd);
  }, []);

  const reset = useCallback(() => {
    historyRef.current = [];
    dailyRef.current = [];
    balanceRef.current = 1000;
    peakRef.current = 1000;
    setBalance(1000);
    setPeakBalance(1000);
    setTradeHistory([]);
    setDailyTrades([]);
    setCurrentDrawdown(0);
  }, []);

  const getPerformanceStats = useCallback(() => {
    const trades = historyRef.current;
    if (trades.length === 0) {
      return {
        totalTrades: 0,
        winRate: 0,
        profitFactor: 0,
        expectancy: 0,
        avgWin: 0,
        avgLoss: 0,
        currentDrawdown,
        maxDrawdown: 0,
        balance,
        peakBalance,
      };
    }

    const wins = trades.filter((t) => t.profit > 0);
    const losses = trades.filter((t) => t.profit < 0);

    const grossProfit = wins.reduce((s, t) => s + t.profit, 0);
    const grossLoss = Math.abs(losses.reduce((s, t) => s + t.profit, 0)) || 1e-10;

    // Calculate max drawdown from trade sequence
    let peak = 1000;
    let maxDD = 0;
    let running = 1000;
    for (const t of trades) {
      running += t.profit;
      if (running > peak) peak = running;
      const dd = peak > 0 ? ((peak - running) / peak) * 100 : 0;
      if (dd > maxDD) maxDD = dd;
    }

    return {
      totalTrades: trades.length,
      winRate: trades.length > 0 ? (wins.length / trades.length) * 100 : 0,
      profitFactor: grossProfit / grossLoss,
      expectancy: trades.length > 0 ? trades.reduce((s, t) => s + t.profit, 0) / trades.length : 0,
      avgWin: wins.length > 0 ? grossProfit / wins.length : 0,
      avgLoss: losses.length > 0 ? grossLoss / losses.length : 0,
      currentDrawdown,
      maxDrawdown: maxDD,
      balance,
      peakBalance,
    };
  }, [balance, peakBalance, currentDrawdown]);

  return {
    calculateSize,
    recordTrade,
    reset,
    getPerformanceStats,
    balance,
    peakBalance,
    currentDrawdown,
    tradeHistory,
    dailyTrades,
    config: cfg,
  };
}
