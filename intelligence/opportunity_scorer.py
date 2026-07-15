"""
Opportunity Scorer — multi-signal composite execution score.

Combines eight independent signal components into a single 0-100 score
that determines whether to TRADE, WAIT, or ABSTAIN.

The scorer uses non-linear combinations, interaction terms, and regime
penalties to produce a calibrated decision signal.
"""

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

DEFAULT_WEIGHTS: Dict[str, float] = {
    "analyzer_consensus": 0.20,
    "entropy_score": 0.15,
    "volatility_score": 0.10,
    "historical_similarity": 0.15,
    "model_accuracy": 0.15,
    "regime_alignment": 0.10,
    "time_quality": 0.05,
    "streak_momentum": 0.10,
}

DEFAULT_MIN_SCORE_TO_TRADE = 75.0
DEFAULT_WAIT_THRESHOLD = 50.0
STATS_HISTORY_SIZE = 500


# ── Dataclass ────────────────────────────────────────────────────────────

@dataclass
class OpportunityScore:
    """Result of an opportunity scoring pass.

    Attributes:
        score: Composite score in ``[0, 100]``.
        components: Breakdown of each signal component's contribution.
        recommendation: ``"TRADE"`` / ``"WAIT"`` / ``"ABSTAIN"``.
        reasoning: Human-readable list of reasons for the recommendation.
        timestamp: Unix epoch time of the scoring pass.
    """
    score: float
    components: Dict[str, float]
    recommendation: str
    reasoning: List[str]
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary."""
        return {
            "score": round(self.score, 2),
            "components": {k: round(v, 2) for k, v in self.components.items()},
            "recommendation": self.recommendation,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
        }


# ── Sub-signal scorers ──────────────────────────────────────────────────

def _score_analyzer_consensus(analyzer_output: Dict[str, Any]) -> float:
    """Score 0-100 based on agreement among analyzers.

    Reads ``analyzer_output`` which is expected to be a dict mapping
    analyzer names to dicts with at least a ``"direction"`` and
    ``"confidence"`` key.
    """
    if not analyzer_output:
        return 30.0

    directions: List[str] = []
    confidences: List[float] = []

    for name, info in analyzer_output.items():
        if isinstance(info, dict):
            d = info.get("direction", info.get("prediction", ""))
            c = float(info.get("confidence", 50.0))
            if d:
                directions.append(d.upper())
                confidences.append(c)

    if not directions:
        return 30.0

    # Consensus ratio
    from collections import Counter
    counts = Counter(directions)
    most_common_count = counts.most_common(1)[0][1]
    consensus_ratio = most_common_count / len(directions)

    # Average confidence
    avg_conf = np.mean(confidences) / 100.0

    # Score: consensus ratio dominates, confidence adds lift
    score = (consensus_ratio ** 1.5) * 60.0 + avg_conf * 40.0
    return float(np.clip(score, 0.0, 100.0))


def _score_entropy(entropy: float, max_entropy: float = 3.32) -> float:
    """Lower entropy → more pattern → higher score.

    entropy is in bits (Shannon).  max_entropy ≈ log2(10) ≈ 3.32.
    """
    if max_entropy <= 0:
        return 50.0
    # Normalise to [0, 1] where 1 = most patterned
    pattern_strength = 1.0 - (entropy / max_entropy)
    return float(np.clip(pattern_strength * 100.0, 0.0, 100.0))


def _score_volatility(volatility: float) -> float:
    """Optimal volatility band scoring.

    Too low → nothing happening → low score.
    Too high → chaotic → low score.
    Sweet spot around 0.08-0.20 annualised.
    """
    if volatility <= 0:
        return 20.0

    # Gaussian membership around the optimal centre
    optimal_centre = 0.14
    optimal_width = 0.08
    raw = math.exp(-0.5 * ((volatility - optimal_centre) / optimal_width) ** 2)
    return float(np.clip(raw * 100.0, 0.0, 100.0))


def _score_historical_similarity(similarity: float) -> float:
    """Direct pass-through of similarity in [0, 1] scaled to [0, 100]."""
    return float(np.clip(similarity * 100.0, 0.0, 100.0))


def _score_model_accuracy(accuracy: float) -> float:
    """Model accuracy in [0, 1] → score [0, 100] with sigmoid boost."""
    # Sigmoid centred at 0.55 to reward models above random
    x = (accuracy - 0.55) * 10.0
    sig = 1.0 / (1.0 + math.exp(-x))
    return float(np.clip(sig * 100.0, 0.0, 100.0))


def _score_regime_alignment(regime: str) -> float:
    """Score how favourable the current regime is for trading.

    Trending and mean-reverting regimes score higher than RANDOM or
    extreme volatility.
    """
    regime_scores: Dict[str, float] = {
        "TRENDING_UP": 80.0,
        "TRENDING_DOWN": 80.0,
        "MEAN_REVERTING": 75.0,
        "LOW_VOLATILITY": 65.0,
        "RANDOM": 30.0,
        "HIGH_VOLATILITY": 35.0,
    }
    return regime_scores.get(regime.upper(), 40.0)


def _score_time_quality(hour: int) -> float:
    """Time-of-day quality factor.

    Peak liquidity hours score highest (London + NY overlap).
    """
    # Approximate hour quality for binary options / synthetic indices
    quality_map = {
        0: 40, 1: 35, 2: 30, 3: 30, 4: 35, 5: 45,
        6: 55, 7: 65, 8: 80, 9: 90, 10: 95, 11: 90,
        12: 85, 13: 80, 14: 90, 15: 85, 16: 80, 17: 70,
        18: 60, 19: 50, 20: 45, 21: 42, 22: 40, 23: 38,
    }
    return float(quality_map.get(hour, 50))


def _score_streak_momentum(digit_history: List[int]) -> float:
    """Detect streak-based reversal opportunities.

    After a long streak of similar digits, a reversal may be due.
    Score increases with streak length up to a cap.
    """
    if not digit_history or len(digit_history) < 3:
        return 50.0

    recent = digit_history[-20:]
    if not recent:
        return 50.0

    # Determine if we are on a streak of high/low digits
    high_streak = 0
    low_streak = 0
    for d in reversed(recent):
        if d >= 5:
            if low_streak > 0:
                break
            high_streak += 1
        else:
            if high_streak > 0:
                break
            low_streak += 1

    streak_len = max(high_streak, low_streak)

    if streak_len <= 2:
        return 50.0  # neutral
    elif streak_len <= 4:
        return 70.0  # mild opportunity
    elif streak_len <= 6:
        return 82.0  # good opportunity
    else:
        return 90.0  # strong reversal opportunity


# ── OpportunityScorer ───────────────────────────────────────────────────

class OpportunityScorer:
    """Multi-signal opportunity scorer with adaptive weight tuning.

    The scorer combines eight signal components using configurable weights,
    non-linear interaction terms, and regime-based penalties.

    Usage::

        scorer = OpportunityScorer()
        result = scorer.score(
            analyzer_output=...,
            entropy=1.8,
            volatility=0.12,
            historical_similarity=0.65,
            model_accuracy=0.72,
            regime="TRENDING_UP",
            digit_history=[3, 7, 2, 8, ...],
            hour=10,
        )
        if result.recommendation == "TRADE":
            execute()
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        min_score_to_trade: float = DEFAULT_MIN_SCORE_TO_TRADE,
        wait_threshold: float = DEFAULT_WAIT_THRESHOLD,
    ) -> None:
        self._weights = dict(DEFAULT_WEIGHTS)
        if weights:
            for k, v in weights.items():
                if k in self._weights:
                    self._weights[k] = v
            self._normalise_weights()

        self._min_score_to_trade = min_score_to_trade
        self._wait_threshold = wait_threshold

        # History for adaptive tuning
        self._score_history: deque = deque(maxlen=STATS_HISTORY_SIZE)
        self._outcome_buffer: deque = deque(maxlen=STATS_HISTORY_SIZE)

        # Performance tracking per weight
        self._component_correlations: Dict[str, deque] = {
            k: deque(maxlen=200) for k in DEFAULT_WEIGHTS
        }

    def _normalise_weights(self) -> None:
        """Ensure weights sum to 1.0."""
        total = sum(self._weights.values())
        if total > 0:
            for k in self._weights:
                self._weights[k] /= total

    # ── Public API ────────────────────────────────────────────────────────

    def score(
        self,
        analyzer_output: Dict[str, Any],
        entropy: float,
        volatility: float,
        historical_similarity: float,
        model_accuracy: float,
        regime: str,
        digit_history: List[int],
        hour: int,
    ) -> OpportunityScore:
        """Compute the composite opportunity score.

        Parameters:
            analyzer_output: Dict of analyzer name → prediction info.
            entropy: Shannon entropy of the current digit distribution (bits).
            volatility: Current annualised volatility.
            historical_similarity: Cosine similarity to best past trades [0, 1].
            model_accuracy: Live ML model accuracy [0, 1].
            regime: Current regime string from ``RegimeDetector``.
            digit_history: Recent digit values for streak analysis.
            hour: Current hour (0-23) for time quality.

        Returns:
            ``OpportunityScore`` with score, recommendation, and reasoning.
        """
        reasoning: List[str] = []
        components: Dict[str, float] = {}

        try:
            # ── Raw component scores ──────────────────────────────────
            raw: Dict[str, float] = {
                "analyzer_consensus": _score_analyzer_consensus(analyzer_output),
                "entropy_score": _score_entropy(entropy),
                "volatility_score": _score_volatility(volatility),
                "historical_similarity": _score_historical_similarity(historical_similarity),
                "model_accuracy": _score_model_accuracy(model_accuracy),
                "regime_alignment": _score_regime_alignment(regime),
                "time_quality": _score_time_quality(hour),
                "streak_momentum": _score_streak_momentum(digit_history),
            }

            # ── Apply weights ─────────────────────────────────────────
            weighted_sum = 0.0
            for name, raw_val in raw.items():
                w = self._weights.get(name, 0.0)
                contribution = raw_val * w
                weighted_sum += contribution
                components[name] = round(contribution, 2)

            base_score = weighted_sum

            # ── Interaction terms ─────────────────────────────────────
            # High consensus + low entropy = strong signal
            consensus_raw = raw["analyzer_consensus"]
            entropy_raw = raw["entropy_score"]
            interaction_boost = 0.0
            if consensus_raw > 65 and entropy_raw > 60:
                interaction_boost = min(8.0, (consensus_raw - 65) * 0.2 * (entropy_raw - 60) * 0.2)
                reasoning.append(
                    f"Consensus-entropy synergy +{interaction_boost:.1f}"
                )

            # Good model + similar past wins = confirmation
            model_raw = raw["model_accuracy"]
            sim_raw = raw["historical_similarity"]
            confirmation_boost = 0.0
            if model_raw > 55 and sim_raw > 55:
                confirmation_boost = min(5.0, (model_raw - 55) * 0.15 * (sim_raw - 55) * 0.15)
                reasoning.append(
                    f"Historical-model confirmation +{confirmation_boost:.1f}"
                )

            # ── Regime penalty ────────────────────────────────────────
            regime_penalty = 0.0
            if regime.upper() == "RANDOM":
                regime_penalty = 15.0
                reasoning.append("RANDOM regime penalty -15")
            elif regime.upper() == "HIGH_VOLATILITY":
                regime_penalty = 10.0
                reasoning.append("HIGH_VOLATILITY regime penalty -10")
            elif regime.upper() == "LOW_VOLATILITY":
                regime_penalty = 5.0
                reasoning.append("LOW_VOLATILITY regime penalty -5")

            # ── Streak bonus / penalty ────────────────────────────────
            streak_raw = raw["streak_momentum"]
            if streak_raw >= 82:
                bonus = (streak_raw - 70) * 0.3
                base_score += bonus
                reasoning.append(f"Streak reversal opportunity +{bonus:.1f}")

            # ── Final composite ───────────────────────────────────────
            final_score = base_score + interaction_boost + confirmation_boost - regime_penalty
            final_score = float(np.clip(final_score, 0.0, 100.0))

            # ── Recommendation ────────────────────────────────────────
            if final_score >= self._min_score_to_trade:
                recommendation = "TRADE"
            elif final_score >= self._wait_threshold:
                recommendation = "WAIT"
            else:
                recommendation = "ABSTAIN"

            # ── Build reasoning ───────────────────────────────────────
            top_components = sorted(raw.items(), key=lambda x: x[1], reverse=True)
            if top_components:
                reasoning.append(
                    f"Top signals: {top_components[0][0]}={top_components[0][1]:.0f}, "
                    f"{top_components[1][0]}={top_components[1][1]:.0f}"
                )

            if consensus_raw < 40:
                reasoning.append("Low analyzer consensus — mixed signals")
            if entropy_raw > 70:
                reasoning.append("Strong market pattern detected")
            if model_raw < 40:
                reasoning.append("ML model accuracy below threshold")

            reasoning.append(
                f"Score {final_score:.1f} → {recommendation}"
            )

            # ── Record for adaptive tuning ────────────────────────────
            result = OpportunityScore(
                score=final_score,
                components=components,
                recommendation=recommendation,
                reasoning=reasoning,
                timestamp=time.time(),
            )
            self._score_history.append(result)
            for name, raw_val in raw.items():
                self._component_correlations[name].append(raw_val)

            logger.debug(
                "Opportunity score: %.1f (%s) — consensus=%.0f entropy=%.0f "
                "regime=%s",
                final_score, recommendation, consensus_raw, entropy_raw, regime,
            )
            return result

        except Exception as exc:
            logger.error("Scoring failed: %s", exc, exc_info=True)
            return OpportunityScore(
                score=0.0,
                components={},
                recommendation="ABSTAIN",
                reasoning=[f"Scoring error: {exc}"],
                timestamp=time.time(),
            )

    def update_weights_from_performance(self, trade_records: List[Dict[str, Any]]) -> None:
        """Adjust component weights based on actual trade outcomes.

        Each trade record should contain ``"outcome"`` ("WIN" / "LOSS") and
        the original ``"components"`` dict from the ``OpportunityScore`` that
        triggered the trade.

        The algorithm increases weights for components that were high in
        winning trades and low in losing trades.
        """
        if not trade_records:
            return

        try:
            wins: Dict[str, List[float]] = {k: [] for k in self._weights}
            losses: Dict[str, List[float]] = {k: [] for k in self._weights}

            for rec in trade_records:
                outcome = rec.get("outcome", "").upper()
                comps = rec.get("components", {})
                for name in self._weights:
                    val = comps.get(name, 0.0)
                    if outcome == "WIN":
                        wins[name].append(val)
                    elif outcome == "LOSS":
                        losses[name].append(val)

            # Compute adjustment
            adjustments: Dict[str, float] = {}
            for name in self._weights:
                win_avg = np.mean(wins[name]) if wins[name] else 0.0
                loss_avg = np.mean(losses[name]) if losses[name] else 0.0
                # Positive diff → this component is predictive of wins
                diff = win_avg - loss_avg
                adjustments[name] = diff

            # Apply adjustments with small step size
            step = 0.02
            max_adj = 0.15
            for name in self._weights:
                raw_adj = adjustments[name] * step
                clamped = float(np.clip(raw_adj, -max_adj, max_adj))
                self._weights[name] += clamped

            self._normalise_weights()

            logger.info(
                "Weights updated from %d trades. New weights: %s",
                len(trade_records),
                {k: round(v, 4) for k, v in self._weights.items()},
            )
        except Exception as exc:
            logger.error("Weight update failed: %s", exc, exc_info=True)

    def get_scoring_stats(self) -> Dict[str, Any]:
        """Return statistics about recent scoring activity."""
        scores = [s.score for s in self._score_history]
        recommendations = [s.recommendation for s in self._score_history]

        from collections import Counter
        rec_counts = Counter(recommendations)

        stats: Dict[str, Any] = {
            "total_scores": len(scores),
            "current_weights": {k: round(v, 4) for k, v in self._weights.items()},
            "min_score_to_trade": self._min_score_to_trade,
            "wait_threshold": self._wait_threshold,
            "recommendation_distribution": dict(rec_counts),
        }

        if scores:
            arr = np.array(scores)
            stats["avg_score"] = round(float(arr.mean()), 2)
            stats["median_score"] = round(float(np.median(arr)), 2)
            stats["std_score"] = round(float(arr.std()), 2)
            stats["min_score"] = round(float(arr.min()), 2)
            stats["max_score"] = round(float(arr.max()), 2)

            trade_scores = [s for s, r in zip(scores, recommendations) if r == "TRADE"]
            if trade_scores:
                stats["avg_trade_score"] = round(float(np.mean(trade_scores)), 2)
                stats["trade_signal_rate"] = round(
                    len(trade_scores) / len(scores) * 100, 1
                )

        return stats
