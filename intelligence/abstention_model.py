"""
Intelligent Abstention System — knows when NOT to trade.

The abstention model is the system's self-preservation mechanism.  Rather
than optimising for *when to trade*, it learns to identify conditions under
which any trade is likely to be harmful.  It evaluates eight independent
abstention signals, combines them via weighted scoring, and applies a
cost-benefit analysis before recommending whether to abstain.

Key design principles:
  1. The model is asymmetric — false negatives (failing to abstain when it
     should) are penalised more heavily than false positives.
  2. The abstention threshold adapts over time based on the quality of past
     abstention decisions (recorded via ``record_outcome``).
  3. Cost-benefit analysis weighs the expected cost of a bad trade against
     the opportunity cost of sitting out.
"""

import logging
import math
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

_SIGNAL_WEIGHTS: Dict[str, float] = {
    "high_volatility": 0.18,
    "low_regime_confidence": 0.14,
    "low_model_agreement": 0.16,
    "low_opportunity_score": 0.12,
    "recent_drawdown": 0.14,
    "unfavourable_hour": 0.06,
    "high_entropy": 0.12,
    "consecutive_loss_streak": 0.08,
}

_DEFAULT_BASE_THRESHOLD: float = 0.55
_THRESHOLD_ADAPT_RATE: float = 0.02
_THRESHOLD_MIN: float = 0.30
_THRESHOLD_MAX: float = 0.80
_HISTORY_SIZE: int = 1000
_OUTCOME_WINDOW: int = 200

# Approximate cost ratios — bad trades hurt more than missed opportunities
_DEFAULT_COST_BAD_TRADE: float = 1.0
_DEFAULT_COST_MISSED_OPPORTUNITY: float = 0.35


# ── Dataclasses ──────────────────────────────────────────────────────────

@dataclass
class AbstentionSignal:
    """A single abstention signal raised during evaluation.

    Attributes:
        trigger: Short identifier for the signal type
            (e.g. ``"high_volatility"``).
        strength: Signal strength in ``[0, 1]`` where 1 means maximum
            abstention pressure.
        description: Human-readable explanation of why this signal fired.
        timestamp: Unix epoch time when the signal was generated.
    """

    trigger: str
    strength: float
    description: str
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary."""
        return {
            "trigger": self.trigger,
            "strength": round(self.strength, 4),
            "description": self.description,
            "timestamp": self.timestamp,
        }


@dataclass
class AbstentionVerdict:
    """Complete abstention evaluation result.

    Attributes:
        should_abstain: Final binary decision — ``True`` means do NOT trade.
        abstention_probability: Continuous probability in ``[0, 1]`` that
            the system should abstain from trading.
        signals: List of ``AbstentionSignal`` objects that contributed to
            the verdict.
        cost_benefit_analysis: Dict containing the cost-of-bad-trade vs
            cost-of-missed-opportunity breakdown.
        recommendation: Human-readable one-line summary.
        confidence_in_abstention: Model's confidence that the abstention
            decision itself is correct (``[0, 1]``).
        timestamp: Unix epoch time of the evaluation.
    """

    should_abstain: bool
    abstention_probability: float
    signals: List[AbstentionSignal]
    cost_benefit_analysis: Dict[str, Any]
    recommendation: str
    confidence_in_abstention: float
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary."""
        return {
            "should_abstain": self.should_abstain,
            "abstention_probability": round(self.abstention_probability, 4),
            "signals": [s.to_dict() for s in self.signals],
            "cost_benefit_analysis": self.cost_benefit_analysis,
            "recommendation": self.recommendation,
            "confidence_in_abstention": round(self.confidence_in_abstention, 4),
            "timestamp": self.timestamp,
        }


# ── Signal scorers ───────────────────────────────────────────────────────

def _score_high_volatility(volatility: float) -> float:
    """Higher volatility → stronger abstention signal.

    Uses a sigmoid centred at 0.18 (annualised) to smoothly transition
    from no-pressure to full-pressure as volatility climbs.
    """
    if volatility <= 0:
        return 0.0
    x = (volatility - 0.18) * 12.0
    return float(np.clip(1.0 / (1.0 + math.exp(-x)), 0.0, 1.0))


def _score_low_regime_confidence(confidence: float) -> float:
    """Lower regime confidence → stronger abstention signal.

    ``confidence`` is expected in ``[0, 1]``.
    """
    inverted = 1.0 - float(np.clip(confidence, 0.0, 1.0))
    return float(np.clip(inverted, 0.0, 1.0))


def _score_low_model_agreement(agreement: float) -> float:
    """Lower model agreement → stronger abstention signal.

    ``agreement`` is expected in ``[0, 1]`` where 1 means perfect agreement.
    """
    inverted = 1.0 - float(np.clip(agreement, 0.0, 1.0))
    return float(np.clip(inverted, 0.0, 1.0))


def _score_low_opportunity(opportunity_score: float) -> float:
    """Lower opportunity score → stronger abstention signal.

    ``opportunity_score`` is in ``[0, 100]`` (OpportunityScorer scale).
    """
    normalised = float(np.clip(opportunity_score, 0.0, 100.0)) / 100.0
    inverted = 1.0 - normalised
    return float(np.clip(inverted, 0.0, 1.0))


def _score_recent_drawdown(drawdown: float) -> float:
    """Larger recent drawdown → stronger abstention signal.

    ``drawdown`` is expected as a positive fraction (e.g. 0.05 = 5% DD).
    """
    if drawdown <= 0:
        return 0.0
    x = (drawdown - 0.04) * 30.0
    return float(np.clip(1.0 / (1.0 + math.exp(-x)), 0.0, 1.0))


def _score_unfavourable_hour(hour: int) -> float:
    """Off-peak hours increase abstention pressure.

    Hours 22-5 are considered low-liquidity and therefore unfavourable.
    """
    unfavourable = {0, 1, 2, 3, 4, 5, 22, 23}
    if hour in unfavourable:
        return 0.65
    marginal = {6, 7, 18, 19, 20, 21}
    if hour in marginal:
        return 0.30
    return 0.0


def _score_high_entropy(entropy: float, max_entropy: float = 3.32) -> float:
    """Higher entropy (more randomness) → stronger abstention signal.

    ``entropy`` is Shannon entropy in bits.  ``max_entropy`` is ``log2(10)``
    for digit-based markets.
    """
    if max_entropy <= 0:
        return 0.5
    ratio = float(np.clip(entropy / max_entropy, 0.0, 1.0))
    return float(np.clip(ratio, 0.0, 1.0))


def _score_consecutive_losses(consecutive_losses: int) -> float:
    """More consecutive losses → stronger abstention signal.

    Uses a cumulative geometric ramp so each additional loss has
    diminishing but still increasing pressure.
    """
    if consecutive_losses <= 0:
        return 0.0
    pressure = 1.0 - math.exp(-0.35 * consecutive_losses)
    return float(np.clip(pressure, 0.0, 1.0))


# ── AbstentionModel ─────────────────────────────────────────────────────

class AbstentionModel:
    """Intelligent abstention system with adaptive thresholding.

    Evaluates eight independent signals, combines them via weighted
    scoring, and applies a cost-benefit analysis to determine whether
    the system should refrain from trading.

    Usage::

        model = AbstentionModel()
        verdict = model.evaluate(
            volatility=0.22,
            regime_confidence=0.40,
            model_agreement=0.55,
            opportunity_score=42.0,
            recent_drawdown=0.06,
            hour=3,
            entropy=2.9,
            consecutive_losses=4,
            daily_trades=12,
        )
        if verdict.should_abstain:
            print("Skipping trade:", verdict.recommendation)
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        base_threshold: float = _DEFAULT_BASE_THRESHOLD,
        cost_bad_trade: float = _DEFAULT_COST_BAD_TRADE,
        cost_missed_opportunity: float = _DEFAULT_COST_MISSED_OPPORTUNITY,
    ) -> None:
        self._weights: Dict[str, float] = dict(_SIGNAL_WEIGHTS)
        if weights:
            for k, v in weights.items():
                if k in self._weights:
                    self._weights[k] = v
            self._normalise_weights()

        self._threshold: float = base_threshold
        self._base_threshold: float = base_threshold
        self._cost_bad_trade: float = cost_bad_trade
        self._cost_missed_opportunity: float = cost_missed_opportunity

        # Adaptive threshold tracking
        self._abstention_history: deque = deque(maxlen=_HISTORY_SIZE)
        self._outcome_buffer: deque = deque(maxlen=_OUTCOME_WINDOW)
        self._abstention_quality: deque = deque(maxlen=_OUTCOME_WINDOW)

        # Lifetime stats
        self._total_evaluations: int = 0
        self._total_abstentions: int = 0
        self._total_correct_abstentions: int = 0
        self._total_incorrect_abstentions: int = 0
        self._creation_time: float = time.time()

        # Per-signal stats
        self._signal_fire_counts: Dict[str, int] = {k: 0 for k in self._weights}
        self._signal_strength_sums: Dict[str, float] = {k: 0.0 for k in self._weights}

        logger.info("AbstentionModel initialised (threshold=%.3f)", self._threshold)

    def _normalise_weights(self) -> None:
        """Ensure weights sum to 1.0."""
        total = sum(self._weights.values())
        if total > 0:
            for k in self._weights:
                self._weights[k] /= total

    # ── Public API ────────────────────────────────────────────────────────

    def evaluate(
        self,
        volatility: float,
        regime_confidence: float,
        model_agreement: float,
        opportunity_score: float,
        recent_drawdown: float,
        hour: int,
        entropy: float,
        consecutive_losses: int,
        daily_trades: int = 0,
    ) -> AbstentionVerdict:
        """Evaluate all abstention signals and produce a verdict.

        Parameters:
            volatility: Current annualised volatility.
            regime_confidence: Regime detector confidence in ``[0, 1]``.
            model_agreement: Agreement among ensemble models in ``[0, 1]``.
            opportunity_score: Composite opportunity score in ``[0, 100]``.
            recent_drawdown: Largest recent drawdown as positive fraction.
            hour: Current hour (0-23).
            entropy: Shannon entropy of digit distribution in bits.
            consecutive_losses: Number of consecutive recent losses.
            daily_trades: Number of trades executed today.

        Returns:
            ``AbstentionVerdict`` with the full evaluation.
        """
        try:
            signals: List[AbstentionSignal] = []
            now = time.time()

            # ── 1. High volatility signal ──────────────────────────────
            vol_strength = _score_high_volatility(volatility)
            if vol_strength > 0.05:
                sig = AbstentionSignal(
                    trigger="high_volatility",
                    strength=vol_strength,
                    description=(
                        f"Volatility {volatility:.4f} exceeds comfortable "
                        f"threshold (pressure: {vol_strength:.2f})"
                    ),
                    timestamp=now,
                )
                signals.append(sig)
                self._signal_fire_counts["high_volatility"] += 1
                self._signal_strength_sums["high_volatility"] += vol_strength

            # ── 2. Low regime confidence signal ─────────────────────────
            rc_strength = _score_low_regime_confidence(regime_confidence)
            if rc_strength > 0.05:
                sig = AbstentionSignal(
                    trigger="low_regime_confidence",
                    strength=rc_strength,
                    description=(
                        f"Regime confidence only {regime_confidence:.2f} — "
                        f"market classification is unreliable"
                    ),
                    timestamp=now,
                )
                signals.append(sig)
                self._signal_fire_counts["low_regime_confidence"] += 1
                self._signal_strength_sums["low_regime_confidence"] += rc_strength

            # ── 3. Low model agreement signal ───────────────────────────
            ma_strength = _score_low_model_agreement(model_agreement)
            if ma_strength > 0.05:
                sig = AbstentionSignal(
                    trigger="low_model_agreement",
                    strength=ma_strength,
                    description=(
                        f"Model agreement only {model_agreement:.2f} — "
                        f"ensemble is divided"
                    ),
                    timestamp=now,
                )
                signals.append(sig)
                self._signal_fire_counts["low_model_agreement"] += 1
                self._signal_strength_sums["low_model_agreement"] += ma_strength

            # ── 4. Low opportunity score signal ─────────────────────────
            opp_strength = _score_low_opportunity(opportunity_score)
            if opp_strength > 0.05:
                sig = AbstentionSignal(
                    trigger="low_opportunity_score",
                    strength=opp_strength,
                    description=(
                        f"Opportunity score only {opportunity_score:.1f}/100 — "
                        f"edge is insufficient"
                    ),
                    timestamp=now,
                )
                signals.append(sig)
                self._signal_fire_counts["low_opportunity_score"] += 1
                self._signal_strength_sums["low_opportunity_score"] += opp_strength

            # ── 5. Recent drawdown signal ───────────────────────────────
            dd_strength = _score_recent_drawdown(recent_drawdown)
            if dd_strength > 0.05:
                pct = recent_drawdown * 100.0
                sig = AbstentionSignal(
                    trigger="recent_drawdown",
                    strength=dd_strength,
                    description=(
                        f"Recent drawdown of {pct:.1f}% indicates elevated "
                        f"risk — recovery mode advised"
                    ),
                    timestamp=now,
                )
                signals.append(sig)
                self._signal_fire_counts["recent_drawdown"] += 1
                self._signal_strength_sums["recent_drawdown"] += dd_strength

            # ── 6. Unfavourable hour signal ─────────────────────────────
            hour_strength = _score_unfavourable_hour(hour)
            if hour_strength > 0.05:
                sig = AbstentionSignal(
                    trigger="unfavourable_hour",
                    strength=hour_strength,
                    description=(
                        f"Hour {hour:02d}:00 is off-peak — liquidity is "
                        f"reduced and spreads are wider"
                    ),
                    timestamp=now,
                )
                signals.append(sig)
                self._signal_fire_counts["unfavourable_hour"] += 1
                self._signal_strength_sums["unfavourable_hour"] += hour_strength

            # ── 7. High entropy signal ──────────────────────────────────
            ent_strength = _score_high_entropy(entropy)
            if ent_strength > 0.05:
                sig = AbstentionSignal(
                    trigger="high_entropy",
                    strength=ent_strength,
                    description=(
                        f"Entropy at {entropy:.2f} bits "
                        f"({ent_strength:.0%} of max) — market appears "
                        f"near-random"
                    ),
                    timestamp=now,
                )
                signals.append(sig)
                self._signal_fire_counts["high_entropy"] += 1
                self._signal_strength_sums["high_entropy"] += ent_strength

            # ── 8. Consecutive loss streak signal ───────────────────────
            cl_strength = _score_consecutive_losses(consecutive_losses)
            if cl_strength > 0.05:
                sig = AbstentionSignal(
                    trigger="consecutive_loss_streak",
                    strength=cl_strength,
                    description=(
                        f"{consecutive_losses} consecutive losses — "
                        f"drawdown protection engaged"
                    ),
                    timestamp=now,
                )
                signals.append(sig)
                self._signal_fire_counts["consecutive_loss_streak"] += 1
                self._signal_strength_sums["consecutive_loss_streak"] += cl_strength

            # ── Weighted probability computation ────────────────────────
            signal_strengths: Dict[str, float] = {}
            for sig in signals:
                signal_strengths[sig.trigger] = sig.strength

            weighted_sum = 0.0
            for name, weight in self._weights.items():
                strength = signal_strengths.get(name, 0.0)
                weighted_sum += strength * weight

            # ── Interaction amplifiers ──────────────────────────────────
            # Multiple concurrent high-strength signals amplify abstention
            high_signals = [s for s in signals if s.strength > 0.6]
            if len(high_signals) >= 3:
                amplifier = min(0.15, len(high_signals) * 0.04)
                weighted_sum = min(1.0, weighted_sum + amplifier)

            # Loss streak + drawdown is especially dangerous
            if ("consecutive_loss_streak" in signal_strengths
                    and "recent_drawdown" in signal_strengths):
                combined = (
                    signal_strengths["consecutive_loss_streak"]
                    + signal_strengths["recent_drawdown"]
                )
                if combined > 1.0:
                    penalty = min(0.10, (combined - 1.0) * 0.08)
                    weighted_sum = min(1.0, weighted_sum + penalty)

            # ── Daily trade count cooldown ───────────────────────────────
            if daily_trades > 15:
                fatigue = min(0.10, (daily_trades - 15) * 0.01)
                weighted_sum = min(1.0, weighted_sum + fatigue)

            abstention_probability = float(np.clip(weighted_sum, 0.0, 1.0))

            # ── Cost-benefit analysis ───────────────────────────────────
            cba = self._cost_benefit_analysis(
                abstention_probability,
                opportunity_score,
                recent_drawdown,
                consecutive_losses,
            )

            # ── Final decision ──────────────────────────────────────────
            effective_threshold = self._threshold
            should_abstain = abstention_probability >= effective_threshold

            # ── Confidence in abstention ────────────────────────────────
            confidence = self._compute_abstention_confidence(
                abstention_probability, signals, cba
            )

            # ── Recommendation text ─────────────────────────────────────
            recommendation = self._build_recommendation(
                should_abstain,
                abstention_probability,
                signals,
                cba,
                effective_threshold,
            )

            # ── Record and track ────────────────────────────────────────
            verdict = AbstentionVerdict(
                should_abstain=should_abstain,
                abstention_probability=abstention_probability,
                signals=signals,
                cost_benefit_analysis=cba,
                recommendation=recommendation,
                confidence_in_abstention=confidence,
                timestamp=now,
            )

            self._total_evaluations += 1
            if should_abstain:
                self._total_abstentions += 1
            self._abstention_history.append(verdict)

            logger.info(
                "Abstention eval: prob=%.3f threshold=%.3f "
                "abstain=%s signals=%d",
                abstention_probability,
                effective_threshold,
                should_abstain,
                len(signals),
            )
            return verdict

        except Exception as exc:
            logger.error("Abstention evaluation failed: %s", exc, exc_info=True)
            return AbstentionVerdict(
                should_abstain=True,
                abstention_probability=1.0,
                signals=[],
                cost_benefit_analysis={},
                recommendation=f"Abstention evaluation error — defaulting to abstain: {exc}",
                confidence_in_abstention=0.0,
                timestamp=time.time(),
            )

    # ── Cost-benefit analysis ─────────────────────────────────────────────

    def _cost_benefit_analysis(
        self,
        abstention_probability: float,
        opportunity_score: float,
        recent_drawdown: float,
        consecutive_losses: int,
    ) -> Dict[str, Any]:
        """Compute cost of a bad trade vs cost of a missed opportunity.

        Returns a dict with the full breakdown for audit and reporting.
        """
        # Expected cost of a bad trade scales with drawdown and loss streak
        dd_risk_multiplier = 1.0 + (recent_drawdown * 10.0)
        loss_risk_multiplier = 1.0 + (consecutive_losses * 0.25)
        expected_bad_trade_cost = (
            self._cost_bad_trade * dd_risk_multiplier * loss_risk_multiplier
        )

        # Expected cost of missing an opportunity scales with opportunity score
        opportunity_factor = max(0.0, opportunity_score / 100.0)
        expected_missed_cost = self._cost_missed_opportunity * opportunity_factor

        # Net benefit of abstaining = bad_trade_cost - missed_opp_cost
        net_abstention_benefit = expected_bad_trade_cost - expected_missed_cost

        # Verdict
        abstaining_is_cheaper = net_abstention_benefit > 0.0

        return {
            "expected_bad_trade_cost": round(expected_bad_trade_cost, 4),
            "expected_missed_opportunity_cost": round(expected_missed_cost, 4),
            "net_abstention_benefit": round(net_abstention_benefit, 4),
            "abstaining_is_cheaper": abstaining_is_cheaper,
            "dd_risk_multiplier": round(dd_risk_multiplier, 4),
            "loss_risk_multiplier": round(loss_risk_multiplier, 4),
            "opportunity_factor": round(opportunity_factor, 4),
        }

    # ── Confidence computation ────────────────────────────────────────────

    def _compute_abstention_confidence(
        self,
        probability: float,
        signals: List[AbstentionSignal],
        cba: Dict[str, Any],
    ) -> float:
        """Estimate confidence that the abstention decision is correct.

        Uses signal agreement, probability distance from threshold, and
        cost-benefit alignment to produce a confidence in ``[0, 1]``.
        """
        if not signals:
            return 0.1

        # Factor 1: distance from threshold (further = more confident)
        threshold_distance = abs(probability - self._threshold)
        distance_confidence = float(np.clip(threshold_distance * 2.0, 0.0, 1.0))

        # Factor 2: signal agreement (proportion of signals with strength > 0.4)
        strengths = np.array([s.strength for s in signals])
        agreement = float(np.mean(strengths > 0.4)) if len(strengths) > 0 else 0.0

        # Factor 3: cost-benefit alignment
        cba_aligned = 1.0 if cba.get("abstaining_is_cheaper", False) else 0.3

        # Weighted combination
        confidence = (
            0.40 * distance_confidence
            + 0.35 * agreement
            + 0.25 * cba_aligned
        )
        return float(np.clip(confidence, 0.0, 1.0))

    # ── Recommendation builder ────────────────────────────────────────────

    @staticmethod
    def _build_recommendation(
        should_abstain: bool,
        probability: float,
        signals: List[AbstentionSignal],
        cba: Dict[str, Any],
        threshold: float,
    ) -> str:
        """Build a human-readable recommendation string."""
        top_signals = sorted(signals, key=lambda s: s.strength, reverse=True)[:3]
        trigger_names = [s.trigger for s in top_signals]

        if should_abstain:
            reason_part = (
                f"top factors: {', '.join(trigger_names)}"
                if trigger_names
                else "multiple weak signals accumulated"
            )
            return (
                f"ABSTAIN (prob={probability:.2f}, threshold={threshold:.2f}) — "
                f"{reason_part}"
            )

        if probability > threshold * 0.7:
            return (
                f"PROCEED WITH CAUTION (prob={probability:.2f}, "
                f"threshold={threshold:.2f}) — marginal conditions"
            )

        return (
            f"TRADE ALLOWED (prob={probability:.2f}, "
            f"threshold={threshold:.2f}) — conditions are favourable"
        )

    # ── Learning from outcomes ────────────────────────────────────────────

    def record_outcome(
        self,
        abstained: bool,
        trade_outcome: Optional[str] = None,
        profit: float = 0.0,
    ) -> None:
        """Record the outcome of a decision to learn over time.

        Parameters:
            abstained: Whether the model recommended abstention.
            trade_outcome: ``"WIN"`` / ``"LOSS"`` / ``None`` if abstained.
            profit: Profit (or loss) from the trade, or 0 if abstained.
        """
        try:
            entry = {
                "abstained": abstained,
                "trade_outcome": trade_outcome,
                "profit": profit,
                "timestamp": time.time(),
            }
            self._outcome_buffer.append(entry)

            # Evaluate abstention quality
            if abstained:
                if trade_outcome is None:
                    # True abstention — we don't know if it was right
                    # Use opportunity_score proxy if available
                    quality = 0.5
                elif trade_outcome.upper() == "LOSS":
                    # Good abstention (would have lost money)
                    quality = 1.0
                    self._total_correct_abstentions += 1
                else:
                    # Bad abstention (missed a winning trade)
                    quality = 0.0
                    self._total_incorrect_abstentions += 1
            else:
                if trade_outcome == "WIN":
                    quality = 1.0
                elif trade_outcome == "LOSS":
                    quality = 0.0
                else:
                    quality = 0.5

            self._abstention_quality.append(quality)
            self._adapt_threshold()

            logger.debug(
                "Outcome recorded: abstained=%s outcome=%s profit=%.2f quality=%.2f",
                abstained, trade_outcome, profit, quality,
            )
        except Exception as exc:
            logger.error("Failed to record outcome: %s", exc, exc_info=True)

    def _adapt_threshold(self) -> None:
        """Adjust the abstention threshold based on recent quality.

        If recent abstentions have been high quality (correctly avoiding
        losses), the threshold is lowered slightly (abstain more easily).
        If abstentions have been poor (missing wins), the threshold is
        raised (abstain less readily).
        """
        if len(self._abstention_quality) < 20:
            return

        recent = np.array(list(self._abstention_quality))
        mean_quality = float(recent.mean())

        # If quality is high (above 0.6), lower threshold to abstain more
        # If quality is low (below 0.4), raise threshold to abstain less
        adjustment = (0.5 - mean_quality) * _THRESHOLD_ADAPT_RATE
        self._threshold = float(np.clip(
            self._threshold + adjustment,
            _THRESHOLD_MIN,
            _THRESHOLD_MAX,
        ))

    # ── Statistics ─────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive abstention model statistics.

        Returns a dict with evaluation counts, abstention rates, signal
        frequency, threshold info, and adaptive learning metrics.
        """
        uptime_hours = (time.time() - self._creation_time) / 3600.0

        abstention_rate = (
            self._total_abstentions / self._total_evaluations
            if self._total_evaluations > 0
            else 0.0
        )

        # Signal frequency analysis
        signal_frequency: Dict[str, Dict[str, Any]] = {}
        for name in self._weights:
            count = self._signal_fire_counts.get(name, 0)
            total_strength = self._signal_strength_sums.get(name, 0.0)
            avg_strength = total_strength / count if count > 0 else 0.0
            fire_rate = count / self._total_evaluations if self._total_evaluations > 0 else 0.0
            signal_frequency[name] = {
                "fire_count": count,
                "fire_rate": round(fire_rate, 4),
                "avg_strength": round(avg_strength, 4),
            }

        # Recent verdict distribution
        recent_verdicts = list(self._abstention_history)[-100:]
        recent_probs = [v.abstention_probability for v in recent_verdicts]

        stats: Dict[str, Any] = {
            "total_evaluations": self._total_evaluations,
            "total_abstentions": self._total_abstentions,
            "abstention_rate": round(abstention_rate, 4),
            "current_threshold": round(self._threshold, 4),
            "base_threshold": self._base_threshold,
            "weights": {k: round(v, 4) for k, v in self._weights.items()},
            "signal_frequency": signal_frequency,
            "uptime_hours": round(uptime_hours, 2),
        }

        if self._total_abstentions > 0:
            correct = self._total_correct_abstentions
            incorrect = self._total_incorrect_abstentions
            total_known = correct + incorrect
            stats["abstention_accuracy"] = (
                round(correct / total_known, 4) if total_known > 0 else 0.5
            )
            stats["correct_abstentions"] = correct
            stats["incorrect_abstentions"] = incorrect

        if recent_probs:
            arr = np.array(recent_probs)
            stats["recent_avg_probability"] = round(float(arr.mean()), 4)
            stats["recent_median_probability"] = round(float(np.median(arr)), 4)
            stats["recent_std_probability"] = round(float(arr.std()), 4)

        if self._abstention_quality:
            q_arr = np.array(list(self._abstention_quality))
            stats["abstention_quality_score"] = round(float(q_arr.mean()), 4)

        return stats

    def get_signal_importance(self) -> Dict[str, float]:
        """Return normalised signal importance based on historical fire
        rates and average strengths.

        Returns:
            Dict mapping signal name to importance in ``[0, 1]``.
        """
        if self._total_evaluations == 0:
            return dict(self._weights)

        importance: Dict[str, float] = {}
        for name in self._weights:
            fire_rate = (
                self._signal_fire_counts.get(name, 0) / self._total_evaluations
            )
            avg_str = (
                self._signal_strength_sums.get(name, 0.0)
                / max(self._signal_fire_counts.get(name, 1), 1)
            )
            importance[name] = fire_rate * avg_str

        total = sum(importance.values())
        if total > 0:
            importance = {k: v / total for k, v in importance.items()}

        return {k: round(v, 4) for k, v in importance.items()}

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        """Persist the abstention model state to disk via joblib.

        Parameters:
            path: File path for the serialised state.
        """
        state = {
            "_weights": dict(self._weights),
            "_threshold": self._threshold,
            "_base_threshold": self._base_threshold,
            "_cost_bad_trade": self._cost_bad_trade,
            "_cost_missed_opportunity": self._cost_missed_opportunity,
            "_abstention_history": list(self._abstention_history),
            "_outcome_buffer": list(self._outcome_buffer),
            "_abstention_quality": list(self._abstention_quality),
            "_total_evaluations": self._total_evaluations,
            "_total_abstentions": self._total_abstentions,
            "_total_correct_abstentions": self._total_correct_abstentions,
            "_total_incorrect_abstentions": self._total_incorrect_abstentions,
            "_creation_time": self._creation_time,
            "_signal_fire_counts": dict(self._signal_fire_counts),
            "_signal_strength_sums": dict(self._signal_strength_sums),
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        joblib.dump(state, path)
        logger.info("AbstentionModel saved to %s", path)

    def load(self, path: str) -> None:
        """Restore abstention model state from a previously saved file.

        Parameters:
            path: File path to load from.
        """
        state = joblib.load(path)
        self._weights = state["_weights"]
        self._threshold = state["_threshold"]
        self._base_threshold = state["_base_threshold"]
        self._cost_bad_trade = state["_cost_bad_trade"]
        self._cost_missed_opportunity = state["_cost_missed_opportunity"]
        self._abstention_history = deque(
            state["_abstention_history"], maxlen=_HISTORY_SIZE
        )
        self._outcome_buffer = deque(
            state["_outcome_buffer"], maxlen=_OUTCOME_WINDOW
        )
        self._abstention_quality = deque(
            state["_abstention_quality"], maxlen=_OUTCOME_WINDOW
        )
        self._total_evaluations = state["_total_evaluations"]
        self._total_abstentions = state["_total_abstentions"]
        self._total_correct_abstentions = state["_total_correct_abstentions"]
        self._total_incorrect_abstentions = state["_total_incorrect_abstentions"]
        self._creation_time = state["_creation_time"]
        self._signal_fire_counts = state["_signal_fire_counts"]
        self._signal_strength_sums = state["_signal_strength_sums"]
        logger.info("AbstentionModel loaded from %s", path)

    def reset(self) -> None:
        """Clear all tracking data and reset to initial state."""
        self._threshold = self._base_threshold
        self._abstention_history.clear()
        self._outcome_buffer.clear()
        self._abstention_quality.clear()
        self._total_evaluations = 0
        self._total_abstentions = 0
        self._total_correct_abstentions = 0
        self._total_incorrect_abstentions = 0
        self._creation_time = time.time()
        self._signal_fire_counts = {k: 0 for k in self._weights}
        self._signal_strength_sums = {k: 0.0 for k in self._weights}
        logger.info("AbstentionModel reset")
