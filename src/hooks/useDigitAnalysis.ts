import { useMemo } from 'react';

export interface DigitAnalysis {
  evenOdd: {
    evenCount: number;
    oddCount: number;
    evenPercentage: number;
    oddPercentage: number;
    streak: { type: 'even' | 'odd'; count: number };
    prediction: 'even' | 'odd' | null;
    confidence: number;
  };
  overUnder: {
    overCount: number;
    underCount: number;
    overPercentage: number;
    underPercentage: number;
    streak: { type: 'over' | 'under'; count: number };
    prediction: 'over' | 'under' | null;
    confidence: number;
  };
  matchDiff: {
    matches: number;
    diffs: number;
    matchPercentage: number;
    diffPercentage: number;
    prediction: 'match' | 'diff' | null;
    confidence: number;
  };
  digitFrequency: Record<number, number>;
  hotDigits: number[];
  coldDigits: number[];
  last20: number[];
}

function calculateStreak(digits: number[], predicate: (d: number) => boolean): { type: string; count: number } {
  let currentStreak = 0;
  for (let i = digits.length - 1; i >= 0; i--) {
    if (predicate(digits[i])) {
      currentStreak++;
    } else {
      break;
    }
  }
  return { type: predicate(digits[digits.length - 1]) ? 'active' : 'inactive', count: currentStreak };
}

function getPrediction(percentage: number, threshold = 55): { prediction: string | null; confidence: number } {
  if (percentage >= threshold) {
    return { prediction: 'current', confidence: Math.min(percentage, 95) };
  } else if (percentage <= 100 - threshold) {
    return { prediction: 'opposite', confidence: Math.min(100 - percentage, 95) };
  }
  return { prediction: null, confidence: 0 };
}

export function useDigitAnalysis(digitHistory: number[]): DigitAnalysis {
  return useMemo(() => {
    const last20 = digitHistory.slice(-20);
    const last50 = digitHistory.slice(-50);

    if (last20.length === 0) {
      return {
        evenOdd: { evenCount: 0, oddCount: 0, evenPercentage: 0, oddPercentage: 0, streak: { type: 'even', count: 0 }, prediction: null, confidence: 0 },
        overUnder: { overCount: 0, underCount: 0, overPercentage: 0, underPercentage: 0, streak: { type: 'over', count: 0 }, prediction: null, confidence: 0 },
        matchDiff: { matches: 0, diffs: 0, matchPercentage: 0, diffPercentage: 0, prediction: null, confidence: 0 },
        digitFrequency: {},
        hotDigits: [],
        coldDigits: [],
        last20: [],
      };
    }

    // Even/Odd analysis
    const evenCount = last20.filter((d) => d % 2 === 0).length;
    const oddCount = last20.length - evenCount;
    const evenPercentage = (evenCount / last20.length) * 100;
    const oddPercentage = (oddCount / last20.length) * 100;
    const evenStreak = calculateStreak(last20, (d) => d % 2 === 0);
    const evenPred = getPrediction(evenPercentage);
    const oddPred = getPrediction(oddPercentage);
    const evenOddPrediction = evenPred.prediction === 'current' ? 'even' : oddPred.prediction === 'current' ? 'odd' : null;
    const evenOddConfidence = evenPred.prediction === 'current' ? evenPred.confidence : oddPred.confidence;

    // Over/Under analysis
    const overCount = last20.filter((d) => d >= 5).length;
    const underCount = last20.length - overCount;
    const overPercentage = (overCount / last20.length) * 100;
    const underPercentage = (underCount / last20.length) * 100;
    const overStreak = calculateStreak(last20, (d) => d >= 5);
    const overPred = getPrediction(overPercentage);
    const underPred = getPrediction(underPercentage);
    const overUnderPrediction = overPred.prediction === 'current' ? 'over' : underPred.prediction === 'current' ? 'under' : null;
    const overUnderConfidence = overPred.prediction === 'current' ? overPred.confidence : underPred.confidence;

    // Match/Diff analysis (comparing consecutive digits)
    let matches = 0;
    let diffs = 0;
    for (let i = 1; i < last20.length; i++) {
      if (last20[i] === last20[i - 1]) matches++;
      else diffs++;
    }
    const totalPairs = matches + diffs;
    const matchPercentage = totalPairs > 0 ? (matches / totalPairs) * 100 : 0;
    const diffPercentage = totalPairs > 0 ? (diffs / totalPairs) * 100 : 0;
    const matchPred = getPrediction(matchPercentage);
    const diffPred = getPrediction(diffPercentage);
    const matchDiffPrediction = matchPred.prediction === 'current' ? 'match' : diffPred.prediction === 'current' ? 'diff' : null;
    const matchDiffConfidence = matchPred.prediction === 'current' ? matchPred.confidence : diffPred.confidence;

    // Digit frequency
    const frequency: Record<number, number> = {};
    for (const d of last50.length > 0 ? last50 : last20) {
      frequency[d] = (frequency[d] || 0) + 1;
    }

    const sortedDigits = Object.entries(frequency)
      .map(([digit, count]) => ({ digit: parseInt(digit), count }))
      .sort((a, b) => b.count - a.count);

    const hotDigits = sortedDigits.slice(0, 3).map((d) => d.digit);
    const coldDigits = sortedDigits.slice(-3).map((d) => d.digit);

    return {
      evenOdd: {
        evenCount,
        oddCount,
        evenPercentage,
        oddPercentage,
        streak: { type: evenStreak.count > 0 && last20[last20.length - 1] % 2 === 0 ? 'even' : 'odd', count: evenStreak.count || last20.length - evenStreak.count },
        prediction: evenOddPrediction as 'even' | 'odd' | null,
        confidence: evenOddConfidence,
      },
      overUnder: {
        overCount,
        underCount,
        overPercentage,
        underPercentage,
        streak: { type: overStreak.count > 0 && last20[last20.length - 1] >= 5 ? 'over' : 'under', count: overStreak.count || last20.length - overStreak.count },
        prediction: overUnderPrediction as 'over' | 'under' | null,
        confidence: overUnderConfidence,
      },
      matchDiff: {
        matches,
        diffs,
        matchPercentage,
        diffPercentage,
        prediction: matchDiffPrediction as 'match' | 'diff' | null,
        confidence: matchDiffConfidence,
      },
      digitFrequency: frequency,
      hotDigits,
      coldDigits,
      last20,
    };
  }, [digitHistory]);
}
