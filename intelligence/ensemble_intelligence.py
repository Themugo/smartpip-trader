"""
Ensemble Intelligence Layer — advanced multi-model aggregation with
dynamic weighting, disagreement detection, and model lifecycle tracking.

Goes beyond simple majority voting:
  - Dynamic per-regime weight adjustment.
  - Bayesian model combination via log-probability averaging.
  - Confidence-calibrated weighting (models that are well-calibrated get more weight).
  - Model freshness tracking (stale models get downweighted).
  - Disagreement detection (signals high uncertainty when models disagree).
"""

import logging
import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import joblib

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MIN_MODELS = 2
_FRESHNESS_HALF_LIFE_HOURS = 72  # models lose half weight every 72 hours
_MIN_CALIBRATION_SAMPLES = 5
_DEFAULT_WEIGHT_HISTORY = 200


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ModelVote:
    """A single model's vote on direction and confidence."""
    model_name: str
    direction: str  # "CALL" or "PUT"
    confidence: float  # 0-100
    raw_output: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "direction": self.direction,
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class EnsembleVerdict:
    """Aggregated ensemble decision."""
    direction: str  # "CALL" or "PUT" or "NEUTRAL"
    confidence: float  # 0-100
    agreement_ratio: float  # fraction of models agreeing
    model_weights: Dict[str, float]
    individual_votes: List[ModelVote]
    disagreement_detected: bool
    weighted_confidence: float
    bayesian_score: float  # log-probability averaged score
    freshness_score: float  # average model freshness [0,1]
    regime: str
    recommendation: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction,
            "confidence": round(self.confidence, 2),
            "agreement_ratio": round(self.agreement_ratio, 4),
            "disagreement_detected": self.disagreement_detected,
            "weighted_confidence": round(self.weighted_confidence, 2),
            "bayesian_score": round(self.bayesian_score, 4),
            "freshness_score": round(self.freshness_score, 4),
            "regime": self.regime,
            "recommendation": self.recommendation,
            "n_models": len(self.individual_votes),
            "timestamp": self.timestamp,
        }


@dataclass
class ModelPerformance:
    """Tracks a single model's historical performance."""
    model_name: str
    total_predictions: int = 0
    correct_predictions: int = 0
    win_rate: float = 0.5
    avg_confidence_when_correct: float = 50.0
    avg_confidence_when_wrong: float = 50.0
    calibration_error: float = 0.0  # |predicted_conf - actual_wr|
    last_prediction_time: float = 0.0
    regime_performance: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {"correct": 0, "total": 0}))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "total_predictions": self.total_predictions,
            "correct_predictions": self.correct_predictions,
            "win_rate": round(self.win_rate, 4),
            "calibration_error": round(self.calibration_error, 4),
            "last_prediction_time": self.last_prediction_time,
        }


# ---------------------------------------------------------------------------
# EnsembleIntelligence
# ---------------------------------------------------------------------------

class EnsembleIntelligence:
    """Advanced multi-model aggregation engine.

    Maintains per-model performance tracking, dynamic weighting by regime,
    and Bayesian combination of model probabilities.

    Usage::

        ensemble = EnsembleIntelligence()
        verdict = ensemble.aggregate(
            votes=[ModelVote("momentum", "CALL", 80), ModelVote("mr", "PUT", 65)],
            regime="TRENDING_UP",
        )
        # After trade completes:
        ensemble.update_performance("momentum", correct=True, confidence=80, regime="TRENDING_UP")
    """

    def __init__(self):
        self._model_performance: Dict[str, ModelPerformance] = {}
        self._regime_weights: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(lambda: 1.0)
        )
        self._weight_history: deque = deque(maxlen=_DEFAULT_WEIGHT_HISTORY)
        self._total_aggregations: int = 0
        logger.info("EnsembleIntelligence initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def aggregate(
        self,
        votes: List[ModelVote],
        regime: str = "UNKNOWN",
        min_agreement: float = 0.5,
    ) -> EnsembleVerdict:
        """Aggregate multiple model votes into a single ensemble verdict.

        Parameters
        ----------
        votes : list[ModelVote]
            Individual model predictions.
        regime : str
            Current market regime for dynamic weighting.
        min_agreement : float
            Minimum agreement ratio required for a confident call.

        Returns
        -------
        EnsembleVerdict
        """
        self._total_aggregations += 1

        if not votes:
            return self._empty_verdict(regime)

        # Ensure all models have performance records
        for v in votes:
            if v.model_name not in self._model_performance:
                self._model_performance[v.model_name] = ModelPerformance(model_name=v.model_name)

        # Compute dynamic weights
        weights = self._compute_weights(votes, regime)

        # Direction tally (weighted)
        call_weight = 0.0
        put_weight = 0.0
        for v in votes:
            w = weights.get(v.model_name, 1.0)
            if v.direction.upper() in ("CALL", "RISE", "EVEN", "OVER"):
                call_weight += w * (v.confidence / 100.0)
            else:
                put_weight += w * (v.confidence / 100.0)

        total_weight = call_weight + put_weight
        if total_weight < 1e-12:
            direction = "NEUTRAL"
            confidence = 0.0
        elif call_weight > put_weight:
            direction = "CALL"
            confidence = (call_weight / total_weight) * 100.0
        else:
            direction = "PUT"
            confidence = (put_weight / total_weight) * 100.0

        # Agreement ratio
        if direction == "NEUTRAL":
            agreement = 0.0
        else:
            agreeing = sum(
                1 for v in votes
                if v.direction.upper() in ("CALL", "RISE", "EVEN", "OVER") and direction == "CALL"
                or v.direction.upper() in ("PUT", "FALL", "ODD", "UNDER") and direction == "PUT"
            )
            agreement = agreeing / len(votes)

        # Disagreement detection
        disagreements = sum(
            1 for i, v1 in enumerate(votes)
            for v2 in votes[i+1:]
            if v1.direction != v2.direction
        )
        max_disagreements = len(votes) * (len(votes) - 1) / 2
        disagreement_detected = (disagreements / max_disagreements) > 0.5 if max_disagreements > 0 else False

        # Weighted confidence
        weighted_conf = 0.0
        total_w = 0.0
        for v in votes:
            w = weights.get(v.model_name, 1.0)
            weighted_conf += w * v.confidence
            total_w += w
        weighted_conf = weighted_conf / total_w if total_w > 0 else 0.0

        # Bayesian score (log-probability averaging)
        bayesian_score = self._bayesian_combine(votes, weights)

        # Freshness score
        freshness = self._compute_freshness(votes)

        # Recommendation
        if disagreement_detected:
            rec = "HIGH_DISAGREEMENT — consider abstaining"
        elif confidence < 50:
            rec = "LOW_CONFIDENCE — ensemble is uncertain"
        elif agreement < min_agreement:
            rec = f"LOW_AGREEMENT ({agreement:.0%}) — models are split"
        else:
            rec = f"ENSEMBLE_{direction}: confidence={confidence:.1f}%, agreement={agreement:.0%}"

        return EnsembleVerdict(
            direction=direction,
            confidence=confidence,
            agreement_ratio=agreement,
            model_weights=weights,
            individual_votes=votes,
            disagreement_detected=disagreement_detected,
            weighted_confidence=weighted_conf,
            bayesian_score=bayesian_score,
            freshness_score=freshness,
            regime=regime,
            recommendation=rec,
        )

    def update_performance(
        self,
        model_name: str,
        correct: bool,
        confidence: float,
        regime: str = "UNKNOWN",
    ) -> None:
        """Update a model's performance after trade outcome is known."""
        if model_name not in self._model_performance:
            self._model_performance[model_name] = ModelPerformance(model_name=model_name)

        perf = self._model_performance[model_name]
        perf.total_predictions += 1
        perf.last_prediction_time = time.time()

        if correct:
            perf.correct_predictions += 1
            perf.avg_confidence_when_correct = (
                perf.avg_confidence_when_correct * 0.9 + confidence * 0.1
            )
        else:
            perf.avg_confidence_when_wrong = (
                perf.avg_confidence_when_wrong * 0.9 + confidence * 0.1
            )

        perf.win_rate = perf.correct_predictions / max(perf.total_predictions, 1)

        # Regime-specific tracking
        perf.regime_performance[regime]["total"] += 1
        if correct:
            perf.regime_performance[regime]["correct"] += 1

        # Calibration error
        expected = confidence / 100.0
        actual = 1.0 if correct else 0.0
        perf.calibration_error = perf.calibration_error * 0.9 + abs(expected - actual) * 0.1

    def get_model_report(self) -> Dict[str, Any]:
        """Full report on all tracked models."""
        models = {}
        for name, perf in self._model_performance.items():
            models[name] = perf.to_dict()
        return {
            "total_models": len(models),
            "total_aggregations": self._total_aggregations,
            "models": models,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        state = {
            "model_performance": {k: {
                "model_name": v.model_name,
                "total_predictions": v.total_predictions,
                "correct_predictions": v.correct_predictions,
                "win_rate": v.win_rate,
                "calibration_error": v.calibration_error,
                "avg_confidence_when_correct": v.avg_confidence_when_correct,
                "avg_confidence_when_wrong": v.avg_confidence_when_wrong,
                "last_prediction_time": v.last_prediction_time,
                "regime_performance": dict(v.regime_performance),
            } for k, v in self._model_performance.items()},
            "total_aggregations": self._total_aggregations,
        }
        joblib.dump(state, path)
        logger.info("EnsembleIntelligence saved to %s", path)

    def load(self, path: str) -> bool:
        try:
            state = joblib.load(path)
            self._model_performance = {}
            for k, v in state["model_performance"].items():
                perf = ModelPerformance(model_name=v["model_name"])
                perf.total_predictions = v["total_predictions"]
                perf.correct_predictions = v["correct_predictions"]
                perf.win_rate = v["win_rate"]
                perf.calibration_error = v["calibration_error"]
                perf.avg_confidence_when_correct = v["avg_confidence_when_correct"]
                perf.avg_confidence_when_wrong = v["avg_confidence_when_wrong"]
                perf.last_prediction_time = v["last_prediction_time"]
                perf.regime_performance = defaultdict(lambda: {"correct": 0, "total": 0}, v.get("regime_performance", {}))
                self._model_performance[k] = perf
            self._total_aggregations = state.get("total_aggregations", 0)
            logger.info("EnsembleIntelligence loaded from %s", path)
            return True
        except Exception as exc:
            logger.error("Failed to load EnsembleIntelligence: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_weights(self, votes: List[ModelVote], regime: str) -> Dict[str, float]:
        """Compute dynamic weights for each model based on performance, calibration, and regime."""
        weights = {}
        for v in votes:
            perf = self._model_performance.get(v.model_name)
            if perf is None or perf.total_predictions < _MIN_CALIBRATION_SAMPLES:
                weights[v.model_name] = 1.0  # uninformative prior
                continue

            # Base weight from win rate
            base = perf.win_rate

            # Regime-specific adjustment
            regime_data = perf.regime_performance.get(regime, {"correct": 0, "total": 0})
            if regime_data["total"] >= 3:
                regime_wr = regime_data["correct"] / regime_data["total"]
                base = 0.7 * base + 0.3 * regime_wr

            # Penalise poor calibration
            calibration_penalty = 1.0 - perf.calibration_error
            weight = base * calibration_penalty

            weights[v.model_name] = max(0.01, weight)

        # Normalise so weights sum to number of models (keeps scale)
        total = sum(weights.values())
        n = len(weights)
        if total > 0:
            weights = {k: v / total * n for k, v in weights.items()}

        return weights

    def _bayesian_combine(self, votes: List[ModelVote], weights: Dict[str, float]) -> float:
        """Combine model confidences via log-probability averaging (Bayesian model combination)."""
        if not votes:
            return 0.5

        log_probs_call = []
        log_probs_put = []
        ws = []

        for v in votes:
            w = weights.get(v.model_name, 1.0)
            p = v.confidence / 100.0
            p = max(0.01, min(0.99, p))

            if v.direction.upper() in ("CALL", "RISE", "EVEN", "OVER"):
                log_probs_call.append(math.log(p))
                log_probs_put.append(math.log(1 - p))
            else:
                log_probs_call.append(math.log(1 - p))
                log_probs_put.append(math.log(p))
            ws.append(w)

        ws_arr = np.array(ws, dtype=np.float64)
        ws_arr = ws_arr / ws_arr.sum()

        avg_log_call = float(np.average(log_probs_call, weights=ws_arr))
        avg_log_put = float(np.average(log_probs_put, weights=ws_arr))

        # Convert back to probability
        max_log = max(avg_log_call, avg_log_put)
        call_prob = math.exp(avg_log_call - max_log)
        put_prob = math.exp(avg_log_put - max_log)
        total = call_prob + put_prob

        return call_prob / total if total > 0 else 0.5

    def _compute_freshness(self, votes: List[ModelVote]) -> float:
        """Average model freshness score [0, 1]."""
        if not votes:
            return 1.0
        now = time.time()
        freshness_scores = []
        for v in votes:
            age_hours = (now - v.timestamp) / 3600.0
            f = math.exp(-0.693 * age_hours / _FRESHNESS_HALF_LIFE_HOURS)
            freshness_scores.append(f)
        return float(np.mean(freshness_scores))

    def _empty_verdict(self, regime: str) -> EnsembleVerdict:
        return EnsembleVerdict(
            direction="NEUTRAL", confidence=0.0, agreement_ratio=0.0,
            model_weights={}, individual_votes=[], disagreement_detected=False,
            weighted_confidence=0.0, bayesian_score=0.5, freshness_score=0.0,
            regime=regime, recommendation="NO_VOTES — no model inputs provided",
        )
