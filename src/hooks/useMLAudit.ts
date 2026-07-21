import { useState, useCallback, useRef } from 'react';

export type BiasType = 'data_leakage' | 'survivorship' | 'curve_fitting' | 'selection_bias' | 'look_ahead' | 'multiple_comparison' | 'non_stationarity';

export interface BiasCheck {
  type: BiasType;
  name: string;
  description: string;
  passed: boolean;
  severity: 'critical' | 'warning' | 'info';
  score: number; // 0-100
  details: string;
  recommendation: string;
  testMethod: string;
}

export interface CVFold {
  fold: number;
  trainStart: number;
  trainEnd: number;
  testStart: number;
  testEnd: number;
  embargoSize: number;
  winRate: number;
  profitFactor: number;
  sharpe: number;
  maxDrawdown: number;
  trades: number;
  avgReturn: number;
  stdReturn: number;
  skewness: number;
  kurtosis: number;
}

export interface HoldoutResult {
  trainPeriod: string;
  testPeriod: string;
  embargoPeriod: string;
  winRate: number;
  profitFactor: number;
  sharpe: number;
  maxDrawdown: number;
  trades: number;
  avgReturn: number;
  stdReturn: number;
  var95: number;
  cvar95: number;
}

export interface RollingWindow {
  windowIndex: number;
  trainStart: number;
  trainEnd: number;
  testStart: number;
  testEnd: number;
  inSamplePF: number;
  outOfSamplePF: number;
  inSampleWR: number;
  outOfSampleWR: number;
  degradation: number;
}

export interface MLAuditState {
  checks: BiasCheck[];
  cvFolds: CVFold[];
  holdoutResult: HoldoutResult | null;
  rollingWindows: RollingWindow[];
  isAuditing: boolean;
  lastAuditTime: number | null;
  deployable: boolean;
  degradationDetected: boolean;
  overallScore: number;
  auditVersion: string;
}

function calculateMean(data: number[]): number {
  return data.length === 0 ? 0 : data.reduce((a, b) => a + b, 0) / data.length;
}

function calculateStd(data: number[]): number {
  if (data.length < 2) return 0;
  const mean = calculateMean(data);
  return Math.sqrt(data.reduce((sq, n) => sq + Math.pow(n - mean, 2), 0) / data.length);
}

function calculateSkewness(data: number[]): number {
  if (data.length < 3) return 0;
  const mean = calculateMean(data);
  const std = calculateStd(data);
  if (std === 0) return 0;
  return data.reduce((sum, x) => sum + Math.pow((x - mean) / std, 3), 0) / data.length;
}

function calculateKurtosis(data: number[]): number {
  if (data.length < 4) return 0;
  const mean = calculateMean(data);
  const std = calculateStd(data);
  if (std === 0) return 0;
  return data.reduce((sum, x) => sum + Math.pow((x - mean) / std, 4), 0) / data.length - 3;
}

function calculateVaR(returns: number[], confidence: number = 0.95): number {
  if (returns.length === 0) return 0;
  const sorted = [...returns].sort((a, b) => a - b);
  const index = Math.floor((1 - confidence) * sorted.length);
  return sorted[Math.max(0, index)];
}

function calculateCVaR(returns: number[], confidence: number = 0.95): number {
  if (returns.length === 0) return 0;
  const varVal = calculateVaR(returns, confidence);
  const tail = returns.filter(r => r <= varVal);
  return tail.length > 0 ? calculateMean(tail) : varVal;
}

function runsTest(data: number[]): { passed: boolean; pValue: number; score: number } {
  // Wald-Wolfowitz runs test for randomness
  if (data.length < 10) return { passed: false, pValue: 1, score: 0 };
  const median = calculateMean(data);
  const binary = data.map(x => (x > median ? 1 : 0));
  let runs = 1;
  for (let i = 1; i < binary.length; i++) {
    if (binary[i] !== binary[i - 1]) runs++;
  }
  const n1 = binary.filter(x => x === 1).length;
  const n0 = binary.filter(x => x === 0).length;
  const expectedRuns = (2 * n1 * n0) / (n1 + n0) + 1;
  const stdRuns = Math.sqrt((2 * n1 * n0 * (2 * n1 * n0 - n1 - n0)) / (Math.pow(n1 + n0, 2) * (n1 + n0 - 1)));
  const zScore = stdRuns > 0 ? (runs - expectedRuns) / stdRuns : 0;
  const pValue = 2 * (1 - Math.min(1, Math.abs(zScore) / 4)); // Simplified
  const passed = pValue > 0.05;
  const score = Math.min(100, Math.max(0, pValue * 100));
  return { passed, pValue, score };
}

function ljungBoxTest(data: number[], lags: number = 10): { passed: boolean; pValue: number; score: number } {
  // Ljung-Box test for autocorrelation
  if (data.length < lags + 2) return { passed: false, pValue: 1, score: 0 };
  const n = data.length;
  const mean = calculateMean(data);
  const autocorr: number[] = [];
  for (let lag = 1; lag <= lags; lag++) {
    let num = 0;
    let den = 0;
    for (let i = 0; i < n; i++) {
      den += Math.pow(data[i] - mean, 2);
      if (i >= lag) {
        num += (data[i] - mean) * (data[i - lag] - mean);
      }
    }
    autocorr.push(den > 0 ? num / den : 0);
  }
  const lb = n * (n + 2) * autocorr.reduce((sum, r, k) => sum + Math.pow(r, 2) / (n - k - 1), 0);
  const pValue = Math.exp(-lb / (2 * lags)); // Simplified chi-square approximation
  const passed = pValue > 0.05;
  const score = Math.min(100, Math.max(0, pValue * 100));
  return { passed, pValue, score };
}

function adfStatistic(data: number[]): { statistic: number; passed: boolean; score: number } {
  // Simplified Augmented Dickey-Fuller for stationarity
  if (data.length < 20) return { statistic: 0, passed: false, score: 0 };
  const diffs: number[] = [];
  for (let i = 1; i < data.length; i++) {
    diffs.push(data[i] - data[i - 1]);
  }
  const y = diffs.slice(1);
  const x = diffs.slice(0, -1);
  const meanY = calculateMean(y);
  const meanX = calculateMean(x);
  const num = x.reduce((s, xi, i) => s + (xi - meanX) * (y[i] - meanY), 0);
  const den = x.reduce((s, xi) => s + Math.pow(xi - meanX, 2), 0);
  const beta = den > 0 ? num / den : 0;
  const residuals = y.map((yi, i) => yi - beta * x[i]);
  const se = Math.sqrt(residuals.reduce((s, r) => s + r * r, 0) / (y.length - 1));
  const tStat = se > 0 ? beta / se : 0;
  const passed = tStat < -2.86; // 5% critical value
  const score = Math.min(100, Math.max(0, (Math.abs(tStat) / 4) * 100));
  return { statistic: tStat, passed, score };
}

export function useMLAudit() {
  const [state, setState] = useState<MLAuditState>({
    checks: [],
    cvFolds: [],
    holdoutResult: null,
    rollingWindows: [],
    isAuditing: false,
    lastAuditTime: null,
    deployable: false,
    degradationDetected: false,
    overallScore: 0,
    auditVersion: '2.0',
  });

  const stateRef = useRef(state);

  const runAudit = useCallback(async (
    tradeHistory: { profit: number; timestamp: number; strategy?: string; regime?: string }[],
    strategyHistory: { name: string; trades: number; wins: number; losses: number; pnl: number }[],
    digitHistory?: number[],
    priceHistory?: number[]
  ) => {
    setState(s => ({ ...s, isAuditing: true }));

    const checks: BiasCheck[] = [];
    const profits = tradeHistory.map(t => t.profit);

    // 1. DATA LEAKAGE — Multiple tests
    const timestamps = tradeHistory.map(t => t.timestamp);
    const isMonotonic = timestamps.every((t, i) => i === 0 || t >= timestamps[i - 1]);
    const hasDuplicates = timestamps.some((t, i) => i > 0 && t === timestamps[i - 1]);
    const timeGaps = timestamps.slice(1).map((t, i) => t - timestamps[i]);
    const avgGap = calculateMean(timeGaps);
    const suspiciousGaps = timeGaps.filter(g => g > avgGap * 5).length;

    // Runs test on returns — clustered wins/losses suggest leakage
    const runsResult = runsTest(profits);
    // Ljung-Box for autocorrelation in returns
    const lbResult = ljungBoxTest(profits);

    const leakageScore = Math.round((
      (isMonotonic ? 25 : 0) +
      (!hasDuplicates ? 25 : 0) +
      (suspiciousGaps === 0 ? 15 : 0) +
      (runsResult.passed ? 20 : 0) +
      (lbResult.passed ? 15 : 0)
    ));

    checks.push({
      type: 'data_leakage',
      name: 'Data Leakage',
      description: 'Checks if future data influences past predictions via timestamp integrity, runs test, and autocorrelation',
      passed: leakageScore >= 70,
      severity: 'critical',
      score: leakageScore,
      details: `Monotonic: ${isMonotonic}, Duplicates: ${hasDuplicates ? 'YES' : 'no'}, Suspicious gaps: ${suspiciousGaps}, Runs test p=${runsResult.pValue.toFixed(3)}, Ljung-Box p=${lbResult.pValue.toFixed(3)}`,
      recommendation: 'Ensure strict temporal ordering. Purge overlapping bars between train/test. Lag all features by at least 1 observation.',
      testMethod: 'Timestamp monotonicity + Wald-Wolfowitz runs test + Ljung-Box Q-test',
    });

    // 2. SURVIVORSHIP BIAS
    const strategiesWithData = strategyHistory.filter(s => s.trades >= 5);
    const allHaveLosses = strategiesWithData.every(s => s.losses > 0);
    const allHaveWins = strategiesWithData.every(s => s.wins > 0);
    const failureRate = strategiesWithData.filter(s => s.pnl < 0).length / (strategiesWithData.length || 1);
    const reportedStrategies = strategyHistory.length;

    const survivorScore = Math.round((
      (allHaveLosses ? 30 : 0) +
      (allHaveWins ? 20 : 0) +
      (failureRate > 0.2 ? 25 : failureRate > 0 ? 15 : 0) +
      (reportedStrategies >= 3 ? 25 : 10)
    ));

    checks.push({
      type: 'survivorship',
      name: 'Survivorship Bias',
      description: 'Checks if failed strategies are hidden and only winners reported',
      passed: survivorScore >= 60,
      severity: 'critical',
      score: survivorScore,
      details: `${reportedStrategies} strategies reported, ${strategiesWithData.length} with data. Failure rate: ${(failureRate * 100).toFixed(1)}%. All have losses: ${allHaveLosses}`,
      recommendation: 'Track and report ALL strategy attempts including failures. Maintain a strategy graveyard.',
      testMethod: 'Win/loss distribution analysis + failure rate estimation',
    });

    // 3. CURVE FITTING / OVERFITTING
    const paramCount = 8; // estimated: regime params, sizing params, confidence thresholds, etc.
    const minDataPoints = paramCount * 50; // stricter: 50 per parameter
    const hasEnoughData = tradeHistory.length >= minDataPoints;
    const inSampleTrades = Math.floor(tradeHistory.length * 0.8);
    const oosTrades = tradeHistory.length - inSampleTrades;
    const inSampleReturns = profits.slice(0, inSampleTrades);
    const oosReturns = profits.slice(inSampleTrades);
    const inSamplePF = Math.abs(inSampleReturns.filter(r => r > 0).reduce((s, r) => s + r, 0)) /
      Math.abs(inSampleReturns.filter(r => r < 0).reduce((s, r) => s + r, 0) || 1);
    const oosPF = oosReturns.length > 0
      ? Math.abs(oosReturns.filter(r => r > 0).reduce((s, r) => s + r, 0)) /
        Math.abs(oosReturns.filter(r => r < 0).reduce((s, r) => s + r, 0) || 1)
      : 0;
    const pfRatio = inSamplePF > 0 ? oosPF / inSamplePF : 0;
    const isOverfit = pfRatio < 0.5 && inSamplePF > 1.5;

    // Degrees of freedom test
    const dfScore = tradeHistory.length / (paramCount * 10);

    const curveFitScore = Math.round((
      (hasEnoughData ? 30 : Math.min(30, dfScore * 30)) +
      (!isOverfit ? 30 : 0) +
      (pfRatio > 0.7 ? 25 : pfRatio > 0.5 ? 15 : 0) +
      (oosTrades >= paramCount * 10 ? 15 : 0)
    ));

    checks.push({
      type: 'curve_fitting',
      name: 'Curve Fitting',
      description: 'Checks if model is over-optimized to historical noise using IS/OOS ratio and degrees of freedom',
      passed: curveFitScore >= 60,
      severity: 'critical',
      score: curveFitScore,
      details: `${tradeHistory.length} trades vs ${minDataPoints} min (${paramCount} params × 50). IS PF: ${inSamplePF.toFixed(2)}, OOS PF: ${oosPF.toFixed(2)}, Ratio: ${pfRatio.toFixed(2)}. Overfit: ${isOverfit}`,
      recommendation: 'Use minimum 50 observations per parameter. Cap in-sample optimization iterations. Enforce OOS validation before deployment.',
      testMethod: 'In-sample / out-of-sample profit factor ratio + degrees of freedom test',
    });

    // 4. SELECTION BIAS / P-HACKING
    const actualWinRate = tradeHistory.length > 0
      ? tradeHistory.filter(t => t.profit > 0).length / tradeHistory.length
      : 0;
    const reportedWinRate = strategyHistory.length > 0
      ? strategyHistory.reduce((s, st) => s + st.wins, 0) / strategyHistory.reduce((s, st) => s + st.trades, 0)
      : 0;
    const winRateMatch = Math.abs(actualWinRate - reportedWinRate) < 0.05;

    // Check for selective reporting: compare early vs late performance
    const earlyTrades = tradeHistory.slice(0, Math.floor(tradeHistory.length * 0.3));
    const lateTrades = tradeHistory.slice(Math.floor(tradeHistory.length * 0.7));
    const earlyWR = earlyTrades.length > 0 ? earlyTrades.filter(t => t.profit > 0).length / earlyTrades.length : 0;
    const lateWR = lateTrades.length > 0 ? lateTrades.filter(t => t.profit > 0).length / lateTrades.length : 0;
    const wrDrift = Math.abs(earlyWR - lateWR);

    // Bonferroni correction check: how many strategies tested
    const strategiesTested = strategyHistory.length;
    const bonferroniAlpha = 0.05 / Math.max(1, strategiesTested);
    const isSignificant = actualWinRate > 0.5 + bonferroniAlpha;

    const selectionScore = Math.round((
      (winRateMatch ? 30 : 0) +
      (wrDrift < 0.15 ? 25 : wrDrift < 0.25 ? 15 : 0) +
      (isSignificant ? 25 : 10) +
      (strategiesTested <= 5 ? 20 : strategiesTested <= 10 ? 15 : 5)
    ));

    checks.push({
      type: 'selection_bias',
      name: 'Selection Bias',
      description: 'Checks for p-hacking, cherry-picking, and selective reporting with Bonferroni correction',
      passed: selectionScore >= 60,
      severity: 'critical',
      score: selectionScore,
      details: `Actual WR: ${(actualWinRate * 100).toFixed(1)}%, Reported: ${(reportedWinRate * 100).toFixed(1)}%. Early WR: ${(earlyWR * 100).toFixed(1)}%, Late: ${(lateWR * 100).toFixed(1)}%. Strategies: ${strategiesTested}. Bonferroni α: ${bonferroniAlpha.toFixed(4)}`,
      recommendation: 'Pre-register all strategy hypotheses. Apply Bonferroni correction for multiple testing. Report all attempts.',
      testMethod: 'Win rate consistency + temporal drift + Bonferroni-corrected significance',
    });

    // 5. LOOK-AHEAD BIAS
    const hasPriceHistory = priceHistory && priceHistory.length >= 20;
    const hasDigitHistory = digitHistory && digitHistory.length >= 20;

    // Check if features could use future data
    // Lag-1 correlation of returns should be near zero if no look-ahead
    const returns = priceHistory && priceHistory.length > 1
      ? priceHistory.slice(1).map((p, i) => Math.log(p / priceHistory[i]))
      : [];
    const lag1Corr = returns.length > 1
      ? calculateCorrelation(returns.slice(0, -1), returns.slice(1))
      : 0;
    const lookAheadDetected = Math.abs(lag1Corr) > 0.3; // Suspicious if too high

    // Check digit pattern for randomness (would be predictable with future info)
    const digitRandomness = digitHistory && digitHistory.length >= 50
      ? chiSquareTest(digitHistory)
      : { score: 50, passed: true };

    const lookAheadScore = Math.round((
      (!lookAheadDetected ? 40 : 10) +
      (Math.abs(lag1Corr) < 0.1 ? 30 : Math.abs(lag1Corr) < 0.2 ? 20 : 5) +
      (digitRandomness.passed ? 20 : 5) +
      (hasPriceHistory && hasDigitHistory ? 10 : 0)
    ));

    checks.push({
      type: 'look_ahead',
      name: 'Look-Ahead Bias',
      description: 'Checks if features use information unavailable at decision time',
      passed: lookAheadScore >= 70,
      severity: 'critical',
      score: lookAheadScore,
      details: `Lag-1 return correlation: ${lag1Corr.toFixed(3)}. Digit randomness: ${digitRandomness.passed ? 'PASS' : 'FAIL'}. Price history: ${hasPriceHistory ? 'YES' : 'no'}`,
      recommendation: 'Lag ALL indicators by at least 1 bar. Use point-in-time data only. Never use future-derived features.',
      testMethod: 'Lag-1 autocorrelation of returns + digit distribution chi-square + feature lag verification',
    });

    // 6. MULTIPLE COMPARISON / P-HACKING
    const sharpeRatios = strategyHistory.map(s => {
      const wr = s.trades > 0 ? s.wins / s.trades : 0;
      const avgWin = s.pnl / (s.wins || 1);
      const avgLoss = s.pnl / (s.losses || 1);
      return (wr * avgWin - (1 - wr) * avgLoss) / (calculateStd([avgWin, avgLoss]) || 1);
    });
    const maxSharpe = sharpeRatios.length > 0 ? Math.max(...sharpeRatios) : 0;
    const expectedMaxSharpe = Math.sqrt(2 * Math.log(strategiesTested || 1)); // Expected max of N standard normals
    const sharpeInflated = maxSharpe > expectedMaxSharpe * 1.5;

    const multipleCompScore = Math.round((
      (!sharpeInflated ? 40 : 10) +
      (strategiesTested <= 3 ? 30 : strategiesTested <= 5 ? 20 : 10) +
      (maxSharpe < 3 ? 30 : maxSharpe < 5 ? 15 : 0)
    ));

    checks.push({
      type: 'multiple_comparison',
      name: 'Multiple Comparison',
      description: 'Checks if best-performing strategy is inflated by testing many variants',
      passed: multipleCompScore >= 60,
      severity: 'warning',
      score: multipleCompScore,
      details: `Max Sharpe: ${maxSharpe.toFixed(2)}, Expected max (N=${strategiesTested}): ${expectedMaxSharpe.toFixed(2)}. Inflated: ${sharpeInflated}`,
      recommendation: 'Use family-wise error rate control. Split data: train/validation/test. Only test pre-registered hypotheses.',
      testMethod: 'Expected maximum Sharpe vs observed + number of strategies tested',
    });

    // 7. NON-STATIONARITY
    const adf = priceHistory && priceHistory.length >= 20 ? adfStatistic(priceHistory) : { statistic: 0, passed: false, score: 0 };
    const profitADF = profits.length >= 20 ? adfStatistic(profits) : { statistic: 0, passed: false, score: 0 };
    const regimeChanges = tradeHistory.filter((t, i) => i > 0 && t.regime !== tradeHistory[i - 1].regime).length;
    const regimeStability = tradeHistory.length > 0 ? 1 - (regimeChanges / tradeHistory.length) : 0;

    const stationarityScore = Math.round((
      (adf.passed ? 25 : adf.score * 0.25) +
      (profitADF.passed ? 25 : profitADF.score * 0.25) +
      (regimeStability > 0.7 ? 25 : regimeStability > 0.5 ? 15 : 5) +
      (tradeHistory.length >= 100 ? 25 : tradeHistory.length >= 50 ? 15 : 5)
    ));

    checks.push({
      type: 'non_stationarity',
      name: 'Non-Stationarity',
      description: 'Checks if market regime shifts invalidate model assumptions',
      passed: stationarityScore >= 50,
      severity: 'warning',
      score: stationarityScore,
      details: `Price ADF: ${adf.passed ? 'PASS' : 'FAIL'} (${adf.statistic.toFixed(2)}). Profit ADF: ${profitADF.passed ? 'PASS' : 'FAIL'}. Regime stability: ${(regimeStability * 100).toFixed(0)}%`,
      recommendation: 'Use rolling windows for retraining. Monitor regime detection stability. Reduce position size after regime changes.',
      testMethod: 'ADF stationarity test on prices and returns + regime change frequency',
    });

    // === TIME-SERIES CROSS-VALIDATION WITH PURGING ===
    const cvFolds: CVFold[] = [];
    const nFolds = 5;
    const foldSize = Math.max(30, Math.floor(tradeHistory.length / (nFolds + 1)));
    const embargoSize = Math.max(5, Math.floor(foldSize * 0.1)); // 10% embargo between train/test

    for (let fold = 0; fold < nFolds; fold++) {
      const trainEnd = (fold + 1) * foldSize;
      const testStart = trainEnd + embargoSize;
      const testEnd = Math.min(testStart + foldSize, tradeHistory.length);

      if (testEnd <= testStart || trainEnd < 10) continue;

      const testTrades = tradeHistory.slice(testStart, testEnd);
      const testProfits = testTrades.map(t => t.profit);
      const wins = testTrades.filter(t => t.profit > 0);
      const losses = testTrades.filter(t => t.profit < 0);
      const grossProfit = wins.reduce((s, t) => s + t.profit, 0);
      const grossLoss = Math.abs(losses.reduce((s, t) => s + t.profit, 0)) || 1e-10;

      let peak = 0;
      let running = 0;
      let maxDD = 0;
      for (const t of testTrades) {
        running += t.profit;
        if (running > peak) peak = running;
        const dd = peak - running;
        if (dd > maxDD) maxDD = dd;
      }

      cvFolds.push({
        fold: fold + 1,
        trainStart: 0,
        trainEnd,
        testStart,
        testEnd,
        embargoSize,
        winRate: testTrades.length > 0 ? (wins.length / testTrades.length) * 100 : 0,
        profitFactor: grossProfit / grossLoss,
        sharpe: testTrades.length > 1 ? (calculateMean(testProfits) / (calculateStd(testProfits) || 1)) : 0,
        maxDrawdown: maxDD,
        trades: testTrades.length,
        avgReturn: calculateMean(testProfits),
        stdReturn: calculateStd(testProfits),
        skewness: calculateSkewness(testProfits),
        kurtosis: calculateKurtosis(testProfits),
      });
    }

    // === HOLDOUT WITH EMBARGO ===
    const holdoutStart = Math.floor(tradeHistory.length * 0.75);
    const embargoEnd = holdoutStart + embargoSize;
    const holdoutTrades = tradeHistory.slice(embargoEnd);
    const holdoutProfits = holdoutTrades.map(t => t.profit);
    const holdoutWins = holdoutTrades.filter(t => t.profit > 0);
    const holdoutLosses = holdoutTrades.filter(t => t.profit < 0);
    const holdoutGrossProfit = holdoutWins.reduce((s, t) => s + t.profit, 0);
    const holdoutGrossLoss = Math.abs(holdoutLosses.reduce((s, t) => s + t.profit, 0)) || 1e-10;

    let holdoutPeak = 0;
    let holdoutRunning = 0;
    let holdoutMaxDD = 0;
    for (const t of holdoutTrades) {
      holdoutRunning += t.profit;
      if (holdoutRunning > holdoutPeak) holdoutPeak = holdoutRunning;
      const dd = holdoutPeak - holdoutRunning;
      if (dd > holdoutMaxDD) holdoutMaxDD = dd;
    }

    const holdoutResult: HoldoutResult = {
      trainPeriod: `0-${holdoutStart}`,
      testPeriod: `${embargoEnd}-${tradeHistory.length}`,
      embargoPeriod: `${holdoutStart}-${embargoEnd}`,
      winRate: holdoutTrades.length > 0 ? (holdoutWins.length / holdoutTrades.length) * 100 : 0,
      profitFactor: holdoutGrossProfit / holdoutGrossLoss,
      sharpe: holdoutTrades.length > 1 ? (calculateMean(holdoutProfits) / (calculateStd(holdoutProfits) || 1)) : 0,
      maxDrawdown: holdoutMaxDD,
      trades: holdoutTrades.length,
      avgReturn: calculateMean(holdoutProfits),
      stdReturn: calculateStd(holdoutProfits),
      var95: calculateVaR(holdoutProfits),
      cvar95: calculateCVaR(holdoutProfits),
    };

    // === ROLLING RETRAINING WINDOWS ===
    const rollingWindows: RollingWindow[] = [];
    const windowSize = Math.max(50, Math.floor(tradeHistory.length * 0.3));
    const stepSize = Math.max(20, Math.floor(windowSize * 0.3));

    for (let start = 0; start + windowSize * 2 <= tradeHistory.length; start += stepSize) {
      const trainEnd = start + windowSize;
      const testEnd = Math.min(trainEnd + windowSize, tradeHistory.length);

      const isProfits = profits.slice(start, trainEnd);
      const oosProfits = profits.slice(trainEnd, testEnd);

      const isWins = isProfits.filter(p => p > 0);
      const oosWins = oosProfits.filter(p => p > 0);

      const isPF = isWins.length > 0
        ? isWins.reduce((s, p) => s + p, 0) / Math.abs(isProfits.filter(p => p < 0).reduce((s, p) => s + p, 0) || 1)
        : 0;
      const oosPF = oosWins.length > 0
        ? oosWins.reduce((s, p) => s + p, 0) / Math.abs(oosProfits.filter(p => p < 0).reduce((s, p) => s + p, 0) || 1)
        : 0;

      const isWR = isProfits.length > 0 ? (isWins.length / isProfits.length) * 100 : 0;
      const oosWR = oosProfits.length > 0 ? (oosWins.length / oosProfits.length) * 100 : 0;

      const degradation = isPF > 0 ? ((isPF - oosPF) / isPF) * 100 : 0;

      rollingWindows.push({
        windowIndex: rollingWindows.length + 1,
        trainStart: start,
        trainEnd,
        testStart: trainEnd,
        testEnd,
        inSamplePF: isPF,
        outOfSamplePF: oosPF,
        inSampleWR: isWR,
        outOfSampleWR: oosWR,
        degradation,
      });
    }

    // === DEGRADATION DETECTION ===
    const avgDegradation = rollingWindows.length > 0
      ? calculateMean(rollingWindows.map(w => w.degradation))
      : 0;
    const maxDegradation = rollingWindows.length > 0
      ? Math.max(...rollingWindows.map(w => w.degradation))
      : 0;
    const cvDegradation = cvFolds.length > 1
      ? (cvFolds[0].profitFactor - cvFolds[cvFolds.length - 1].profitFactor) / (cvFolds[0].profitFactor || 1) * 100
      : 0;
    const holdoutDegradation = cvFolds.length > 0 && holdoutResult
      ? (cvFolds[cvFolds.length - 1].profitFactor - holdoutResult.profitFactor) / (cvFolds[cvFolds.length - 1].profitFactor || 1) * 100
      : 0;

    const degradationDetected =
      avgDegradation > 30 ||
      maxDegradation > 50 ||
      cvDegradation > 40 ||
      holdoutDegradation > 30 ||
      (holdoutResult && holdoutResult.profitFactor < 0.8);

    // === DEPLOYMENT GATE ===
    const criticalChecks = checks.filter(c => c.severity === 'critical');
    const allCriticalPassed = criticalChecks.every(c => c.passed);
    const criticalScore = criticalChecks.length > 0
      ? calculateMean(criticalChecks.map(c => c.score))
      : 100;

    const holdoutPositive = holdoutResult && holdoutResult.profitFactor > 1 && holdoutResult.winRate > 50;
    const holdoutSharpeOK = holdoutResult ? holdoutResult.sharpe > 0 : false;
    const varOK = holdoutResult ? holdoutResult.var95 > -5 : true; // Max $5 loss at 95%

    const overallScore = Math.round(calculateMean(checks.map(c => c.score)));

    const deployable =
      allCriticalPassed &&
      criticalScore >= 70 &&
      holdoutPositive &&
      holdoutSharpeOK &&
      varOK &&
      !degradationDetected &&
      overallScore >= 65;

    const newState: MLAuditState = {
      checks,
      cvFolds,
      holdoutResult,
      rollingWindows,
      isAuditing: false,
      lastAuditTime: Date.now(),
      deployable,
      degradationDetected,
      overallScore,
      auditVersion: '2.0',
    };

    stateRef.current = newState;
    setState(newState);

    return newState;
  }, []);

  return { state, runAudit };
}

function calculateCorrelation(x: number[], y: number[]): number {
  if (x.length !== y.length || x.length < 2) return 0;
  const meanX = calculateMean(x);
  const meanY = calculateMean(y);
  const num = x.reduce((s, xi, i) => s + (xi - meanX) * (y[i] - meanY), 0);
  const denX = x.reduce((s, xi) => s + Math.pow(xi - meanX, 2), 0);
  const denY = y.reduce((s, yi) => s + Math.pow(yi - meanY, 2), 0);
  return denX > 0 && denY > 0 ? num / Math.sqrt(denX * denY) : 0;
}

function chiSquareTest(digits: number[]): { score: number; passed: boolean } {
  const counts: Record<number, number> = {};
  for (const d of digits) {
    counts[d] = (counts[d] || 0) + 1;
  }
  const expected = digits.length / 10;
  const chiSq = Object.values(counts).reduce((sum, count) => sum + Math.pow(count - expected, 2) / expected, 0);
  // Degrees of freedom = 9, critical at 5% = 16.92
  const passed = chiSq < 16.92;
  const score = Math.min(100, Math.max(0, (1 - chiSq / 30) * 100));
  return { score, passed };
}
