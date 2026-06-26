import { useState, useEffect, useRef, useCallback, useMemo } from 'react';

export type RegimeType = 'trending' | 'mean_reverting' | 'high_volatility' | 'low_volatility' | 'random' | 'no_edge';

export interface RegimeState {
  currentRegime: RegimeType;
  confidence: number;
  duration: number;
  history: { regime: RegimeType; tick: number; confidence: number }[];
  metrics: RegimeMetrics;
  lastUpdate: number;
  isTradeable: boolean;
  blockReason: string | null;
}

export interface RegimeMetrics {
  adfStatistic: number;      // Augmented Dickey-Fuller for mean reversion
  hurstExponent: number;     // Hurst: <0.5 = MR, >0.5 = trending, ~0.5 = random
  volatility: number;        // Realized volatility
  volatilityPercentile: number;
  trendStrength: number;     // R-squared of linear regression
  autoCorrelation: number;   // Lag-1 autocorrelation
  varianceRatio: number;     // Variance ratio test
}

// Supported regimes per strategy type
export const STRATEGY_REGIMES: Record<string, RegimeType[]> = {
  even_odd: ['mean_reverting', 'low_volatility'],
  over_under: ['mean_reverting', 'low_volatility'],
  match_diff: ['mean_reverting', 'low_volatility'],
  rise_fall: ['trending', 'high_volatility'],
  digit_match: ['random', 'low_volatility'],
  composite: ['trending', 'mean_reverting', 'low_volatility'],
};

const HISTORY_SIZE = 200;
const MIN_HISTORY = 50;

function calculateMean(data: number[]): number {
  return data.reduce((a, b) => a + b, 0) / data.length;
}

function calculateStd(data: number[]): number {
  const mean = calculateMean(data);
  return Math.sqrt(data.reduce((sq, n) => sq + Math.pow(n - mean, 2), 0) / data.length);
}

function linearRegression(x: number[], y: number[]): { slope: number; intercept: number; r2: number } {
  const n = x.length;
  const sumX = x.reduce((a, b) => a + b, 0);
  const sumY = y.reduce((a, b) => a + b, 0);
  const sumXY = x.reduce((s, xi, i) => s + xi * y[i], 0);
  const sumX2 = x.reduce((s, xi) => s + xi * xi, 0);
  const sumY2 = y.reduce((s, yi) => s + yi * yi, 0);

  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;

  const ssTot = sumY2 - sumY * sumY / n;
  const ssRes = sumY2 - 2 * slope * sumXY - 2 * intercept * sumY + slope * slope * sumX2 + 2 * slope * intercept * sumX + n * intercept * intercept;
  const r2 = ssTot > 0 ? 1 - ssRes / ssTot : 0;

  return { slope, intercept, r2 };
}

function hurstExponent(prices: number[]): number {
  // Simplified Hurst using R/S analysis
  const n = prices.length;
  if (n < 30) return 0.5;

  const returns: number[] = [];
  for (let i = 1; i < n; i++) {
    returns.push(Math.log(prices[i] / prices[i - 1]));
  }

  const meanReturn = calculateMean(returns);
  const deviations = returns.map((r) => r - meanReturn);

  let maxR = 0;
  let cumDev = 0;
  for (const dev of deviations) {
    cumDev += dev;
    maxR = Math.max(maxR, Math.abs(cumDev));
  }

  const s = calculateStd(returns);
  if (s === 0) return 0.5;

  const rs = maxR / s;
  // Approximate Hurst from R/S
  return Math.min(Math.max(Math.log(rs) / Math.log(n) + 0.5, 0), 1);
}

function varianceRatio(prices: number[], q: number = 2): number {
  const n = prices.length;
  if (n < q * 2) return 1;

  const returns: number[] = [];
  for (let i = 1; i < n; i++) {
    returns.push(Math.log(prices[i] / prices[i - 1]));
  }

  const var1 = calculateStd(returns) ** 2;

  const multiReturns: number[] = [];
  for (let i = 0; i < returns.length - q + 1; i++) {
    let sum = 0;
    for (let j = 0; j < q; j++) {
      sum += returns[i + j];
    }
    multiReturns.push(sum);
  }

  const varQ = calculateStd(multiReturns) ** 2 / q;

  return varQ / (var1 || 1e-10);
}

function adfStatistic(prices: number[]): number {
  // Simplified ADF: test if price differences are stationary
  const n = prices.length;
  if (n < 30) return 0;

  const diffs: number[] = [];
  for (let i = 1; i < n; i++) {
    diffs.push(prices[i] - prices[i - 1]);
  }

  const y = diffs.slice(1);
  const x = diffs.slice(0, -1);

  const reg = linearRegression(x, y);
  // t-statistic for mean reversion
  return -reg.slope / (calculateStd(y) || 1);
}

function detectRegime(metrics: RegimeMetrics): { regime: RegimeType; confidence: number } {
  const { hurstExponent: h, volatilityPercentile, trendStrength, varianceRatio: vr, autoCorrelation } = metrics;

  // Score each regime
  const scores: Record<RegimeType, number> = {
    trending: 0,
    mean_reverting: 0,
    high_volatility: 0,
    low_volatility: 0,
    random: 0,
    no_edge: 0,
  };

  // Trending: high Hurst, strong trend
  scores.trending = (h > 0.55 ? (h - 0.55) * 200 : 0) + (trendStrength > 0.3 ? trendStrength * 100 : 0);

  // Mean reverting: low Hurst, negative autocorr
  scores.mean_reverting = (h < 0.45 ? (0.45 - h) * 200 : 0) + (autoCorrelation < -0.1 ? -autoCorrelation * 200 : 0);

  // High volatility
  scores.high_volatility = volatilityPercentile > 70 ? (volatilityPercentile - 70) * 3.33 : 0;

  // Low volatility
  scores.low_volatility = volatilityPercentile < 30 ? (30 - volatilityPercentile) * 3.33 : 0;

  // Random: Hurst ~0.5, VR ~1, weak autocorr
  scores.random = (Math.abs(h - 0.5) < 0.1 ? 50 : 0) + (Math.abs(vr - 1) < 0.2 ? 50 : 0);

  // No edge: everything weak
  scores.no_edge = 30 - Math.max(...Object.values(scores));

  const best = Object.entries(scores).sort((a, b) => b[1] - a[1])[0];
  const totalScore = Object.values(scores).reduce((a, b) => a + b, 0);
  const confidence = totalScore > 0 ? Math.min(best[1] / totalScore * 100 * 2, 95) : 50;

  return { regime: best[0] as RegimeType, confidence };
}

export function useRegimeDetection(digitHistory: number[], price: number) {
  const [regimeState, setRegimeState] = useState<RegimeState>({
    currentRegime: 'random',
    confidence: 0,
    duration: 0,
    history: [],
    metrics: {
      adfStatistic: 0,
      hurstExponent: 0.5,
      volatility: 0,
      volatilityPercentile: 50,
      trendStrength: 0,
      autoCorrelation: 0,
      varianceRatio: 1,
    },
    lastUpdate: 0,
    isTradeable: false,
    blockReason: 'Collecting initial data...',
  });

  const priceHistoryRef = useRef<number[]>([]);
  const digitHistoryRef = useRef<number[]>([]);
  const volHistoryRef = useRef<number[]>([]);
  const tickCountRef = useRef(0);
  const currentRegimeRef = useRef<RegimeType>('random');
  const durationRef = useRef(0);

  const updateRegime = useCallback(() => {
    const prices = priceHistoryRef.current;
    const digits = digitHistoryRef.current;
    tickCountRef.current += 1;

    if (prices.length < MIN_HISTORY || digits.length < MIN_HISTORY) {
      setRegimeState((prev) => ({
        ...prev,
        blockReason: `Collecting data... ${prices.length}/${MIN_HISTORY} ticks`,
        isTradeable: false,
      }));
      return;
    }

    // Calculate returns for volatility
    const returns: number[] = [];
    for (let i = 1; i < prices.length; i++) {
      returns.push(Math.log(prices[i] / prices[i - 1]));
    }

    const volatility = calculateStd(returns) * Math.sqrt(252); // Annualized
    volHistoryRef.current.push(volatility);
    if (volHistoryRef.current.length > HISTORY_SIZE) volHistoryRef.current.shift();

    const volHist = volHistoryRef.current;
    const volatilityPercentile = volHist.length > 0
      ? (volHist.filter((v) => v < volatility).length / volHist.length) * 100
      : 50;

    // Trend strength via linear regression on last 50 prices
    const recentPrices = prices.slice(-50);
    const x = recentPrices.map((_, i) => i);
    const reg = linearRegression(x, recentPrices);

    // Autocorrelation of returns
    const lag1Returns = returns.slice(0, -1);
    const lag0Returns = returns.slice(1);
    const meanLag0 = calculateMean(lag0Returns);
    const meanLag1 = calculateMean(lag1Returns);
    const num = lag0Returns.reduce((s, r0, i) => s + (r0 - meanLag0) * (lag1Returns[i] - meanLag1), 0);
    const den0 = lag0Returns.reduce((s, r) => s + Math.pow(r - meanLag0, 2), 0);
    const den1 = lag1Returns.reduce((s, r) => s + Math.pow(r - meanLag1, 2), 0);
    const autoCorrelation = den0 > 0 && den1 > 0 ? num / Math.sqrt(den0 * den1) : 0;

    const metrics: RegimeMetrics = {
      adfStatistic: adfStatistic(recentPrices),
      hurstExponent: hurstExponent(recentPrices),
      volatility,
      volatilityPercentile,
      trendStrength: reg.r2,
      autoCorrelation,
      varianceRatio: varianceRatio(recentPrices, 2),
    };

    const { regime, confidence } = detectRegime(metrics);

    // Track regime duration
    if (regime === currentRegimeRef.current) {
      durationRef.current += 1;
    } else {
      currentRegimeRef.current = regime;
      durationRef.current = 1;
    }

    // Determine if tradeable
    let isTradeable = true;
    let blockReason: string | null = null;

    if (regime === 'no_edge') {
      isTradeable = false;
      blockReason = `No-edge regime detected (${confidence.toFixed(0)}% confidence). Trades blocked.`;
    } else if (regime === 'high_volatility' && confidence > 70) {
      isTradeable = false;
      blockReason = `High volatility regime (${confidence.toFixed(0)}% conf). Risk elevated. Trades blocked.`;
    } else if (confidence < 40) {
      isTradeable = false;
      blockReason = `Low regime confidence (${confidence.toFixed(0)}%). Waiting for clearer signal.`;
    }

    const newEntry = { regime, tick: tickCountRef.current, confidence };

    setRegimeState((prev) => ({
      currentRegime: regime,
      confidence,
      duration: durationRef.current,
      history: [...prev.history.slice(-99), newEntry],
      metrics,
      lastUpdate: tickCountRef.current,
      isTradeable,
      blockReason,
    }));
  }, []);

  // Update price/digit history when props change
  useEffect(() => {
    if (price > 0) {
      priceHistoryRef.current.push(price);
      if (priceHistoryRef.current.length > HISTORY_SIZE) priceHistoryRef.current.shift();
    }
    if (digitHistory.length > 0) {
      digitHistoryRef.current = [...digitHistory];
    }
  }, [price, digitHistory]);

  // Run regime detection periodically
  useEffect(() => {
    if (priceHistoryRef.current.length < MIN_HISTORY) return;

    updateRegime();
    const interval = setInterval(updateRegime, 5000); // Check every 5 seconds
    return () => clearInterval(interval);
  }, [updateRegime]);

  // Check if a strategy is compatible with current regime
  const isStrategyAllowed = useCallback((strategyType: string): { allowed: boolean; reason: string } => {
    const supported = STRATEGY_REGIMES[strategyType] || [];
    if (supported.includes(regimeState.currentRegime)) {
      return { allowed: true, reason: '' };
    }
    return {
      allowed: false,
      reason: `Strategy '${strategyType}' does not support '${regimeState.currentRegime}' regime. Supported: ${supported.join(', ')}`,
    };
  }, [regimeState.currentRegime]);

  return { regimeState, isStrategyAllowed };
}
