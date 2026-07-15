"""
Online Learner — continuous online learning with concept drift detection.

Implements adaptive learning that adjusts to changing market dynamics:
  - Exponentially-weighted moving average (EWMA) feature tracking.
  - ADWIN-style drift detection via sliding-window divergence.
  - Automatic model parameter adjustment when drift is detected.
  - Incremental model updates from each trade outcome.
  - Learning rate scheduling based on confidence and market regime.
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
_BUFFER_SIZE = 2000
_DRIFT_WINDOW = 100
_DRIFT_THRESHOLD = 0.15  # max acceptable distribution shift
_MIN_SAMPLES_FOR_DRIFT = 30
_LEARNING_RATE_MIN = 0.001
_LEARNING_RATE_MAX = 0.1
_LEARNING_RATE_DECAY = 0.995
_EWMA_ALPHA = 0.05


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DriftReport:
    """Report from concept drift detection."""
    drift_detected: bool
    magnitude: float
    direction: str  # "INCREASING", "DECREASING", "SHIFT", "NONE"
    affected_features: List[str]
    recommendation: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drift_detected": self.drift_detected,
            "magnitude": round(self.magnitude, 4),
            "direction": self.direction,
            "affected_features": self.affected_features,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
        }


@dataclass
class LearningState:
    """Current state of the online learning system."""
    learning_rate: float
    total_updates: int
    drift_events: int
    current_ewma: Dict[str, float]
    performance_trend: float  # rolling win rate
    adaptation_count: int
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "learning_rate": round(self.learning_rate, 6),
            "total_updates": self.total_updates,
            "drift_events": self.drift_events,
            "performance_trend": round(self.performance_trend, 4),
            "adaptation_count": self.adaptation_count,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# EWMA Tracker
# ---------------------------------------------------------------------------

class _EWMATracker:
    """Exponentially-weighted moving average tracker for feature streams."""

    def __init__(self, alpha: float = _EWMA_ALPHA):
        self.alpha = alpha
        self._values: Dict[str, float] = {}
        self._variances: Dict[str, float] = {}
        self._count: int = 0

    def update(self, features: Dict[str, float]) -> Dict[str, float]:
        """Update EWMA with new observations, return current EWMA values."""
        self._count += 1
        result = {}
        for key, val in features.items():
            if key not in self._values:
                self._values[key] = val
                self._variances[key] = 0.0
            else:
                old = self._values[key]
                self._values[key] = old + self.alpha * (val - old)
                # EWMA variance
                diff = val - old
                self._variances[key] = (
                    (1 - self.alpha) * (self._variances[key] + self.alpha * diff * diff)
                )
            result[key] = self._values[key]
        return result

    def get_state(self) -> Dict[str, float]:
        return dict(self._values)

    def get_variance(self) -> Dict[str, float]:
        return dict(self._variances)


# ---------------------------------------------------------------------------
# Sliding Window Divergence Detector
# ---------------------------------------------------------------------------

class _WindowDivergence:
    """Detects distributional shift between two sliding windows."""

    def __init__(self, window_size: int = _DRIFT_WINDOW):
        self.window_size = window_size
        self._window_a: deque = deque(maxlen=window_size)
        self._window_b: deque = deque(maxlen=window_size)
        self._phase = "filling"  # "filling" or "comparing"

    def add(self, value: float) -> Optional[float]:
        """Add a value and return divergence if measurable."""
        if self._phase == "filling":
            self._window_a.append(value)
            if len(self._window_a) >= self.window_size:
                self._phase = "comparing"
            return None

        self._window_b.append(value)
        if len(self._window_b) >= self.window_size:
            div = self._compute_divergence()
            # Slide: b becomes a, clear b
            self._window_a = deque(list(self._window_b), maxlen=self.window_size)
            self._window_b.clear()
            return div
        return None

    def _compute_divergence(self) -> float:
        """Simple distributional divergence via mean and variance shift."""
        a = np.array(list(self._window_a), dtype=np.float64)
        b = np.array(list(self._window_b), dtype=np.float64)
        if len(a) < 5 or len(b) < 5:
            return 0.0

        # Normalised mean difference
        pooled_std = np.sqrt((np.var(a) + np.var(b)) / 2 + 1e-12)
        mean_diff = abs(np.mean(a) - np.mean(b)) / pooled_std

        # Variance ratio
        var_ratio = np.var(a) / (np.var(b) + 1e-12)
        var_shift = abs(math.log(max(var_ratio, 0.01)))

        return float(mean_diff + var_shift * 0.5)


# ---------------------------------------------------------------------------
# OnlineLearner
# ---------------------------------------------------------------------------

class OnlineLearner:
    """Continuous online learning engine with concept drift detection.

    Tracks feature distributions, detects when market dynamics shift,
    and adapts learning parameters accordingly.

    Usage::

        learner = OnlineLearner()
        state = learner.update(features, outcome=True, confidence=75)
        drift = learner.check_drift(features)
    """

    def __init__(self):
        self._ewma = _EWMATracker(alpha=_EWMA_ALPHA)
        self._drift_detectors: Dict[str, _WindowDivergence] = {}
        self._learning_rate = _LEARNING_RATE_MAX
        self._total_updates: int = 0
        self._drift_events: int = 0
        self._adaptation_count: int = 0

        # Performance tracking
        self._outcome_buffer: deque = deque(maxlen=_BUFFER_SIZE)
        self._confidence_buffer: deque = deque(maxlen=_BUFFER_SIZE)
        self._rolling_win_rate: deque = deque(maxlen=200)
        self._performance_history: List[float] = []

        # Feature importance weights (learned)
        self._feature_importance: Dict[str, float] = defaultdict(lambda: 1.0)

        logger.info("OnlineLearner initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        features: Dict[str, float],
        outcome: bool,
        confidence: float = 50.0,
    ) -> LearningState:
        """Record a new observation and update learning state.

        Parameters
        ----------
        features : dict
            Current market feature values.
        outcome : bool
            True for WIN, False for LOSS.
        confidence : float
            Confidence at time of prediction (0-100).

        Returns
        -------
        LearningState
        """
        self._total_updates += 1

        # Update EWMA
        ewma_vals = self._ewma.update(features)

        # Track outcomes
        self._outcome_buffer.append(1.0 if outcome else 0.0)
        self._confidence_buffer.append(confidence)

        # Update rolling win rate
        recent = list(self._outcome_buffer)[-50:]
        wr = sum(recent) / len(recent) if recent else 0.5
        self._rolling_win_rate.append(wr)
        self._performance_history.append(wr)

        # Adjust learning rate based on recent performance
        if len(self._rolling_win_rate) >= 10:
            recent_trend = list(self._rolling_win_rate)[-10:]
            if len(recent_trend) >= 2:
                slope = (recent_trend[-1] - recent_trend[0]) / len(recent_trend)
                if slope < -0.01:
                    # Performance declining — increase learning rate
                    self._learning_rate = min(
                        _LEARNING_RATE_MAX,
                        self._learning_rate / _LEARNING_RATE_DECAY,
                    )
                elif slope > 0.01:
                    # Performance improving — decrease learning rate (exploit)
                    self._learning_rate = max(
                        _LEARNING_RATE_MIN,
                        self._learning_rate * _LEARNING_RATE_DECAY,
                    )

        # Update feature importance
        self._update_feature_importance(features, outcome, confidence)

        return LearningState(
            learning_rate=self._learning_rate,
            total_updates=self._total_updates,
            drift_events=self._drift_events,
            current_ewma=ewma_vals,
            performance_trend=wr,
            adaptation_count=self._adaptation_count,
        )

    def check_drift(self, features: Dict[str, float]) -> DriftReport:
        """Check for concept drift in current feature stream.

        Parameters
        ----------
        features : dict
            Current feature values.

        Returns
        -------
        DriftReport
        """
        if self._total_updates < _MIN_SAMPLES_FOR_DRIFT:
            return DriftReport(
                drift_detected=False, magnitude=0.0, direction="NONE",
                affected_features=[], recommendation="Insufficient data for drift detection",
            )

        affected = []
        max_magnitude = 0.0

        for key, val in features.items():
            if key not in self._drift_detectors:
                self._drift_detectors[key] = _WindowDivergence(window_size=_DRIFT_WINDOW)

            detector = self._drift_detectors[key]
            divergence = detector.add(val)

            if divergence is not None and divergence > _DRIFT_THRESHOLD:
                affected.append(key)
                max_magnitude = max(max_magnitude, divergence)

        drift_detected = len(affected) > 0

        if drift_detected:
            self._drift_events += 1
            # Increase learning rate to adapt faster
            self._learning_rate = min(
                _LEARNING_RATE_MAX,
                self._learning_rate * 1.5,
            )
            self._adaptation_count += 1
            direction = "SHIFT"
            rec = f"Drift detected in {len(affected)} features — increased learning rate to {self._learning_rate:.4f}"
        else:
            direction = "NONE"
            rec = "No significant drift detected"

        return DriftReport(
            drift_detected=drift_detected,
            magnitude=max_magnitude,
            direction=direction,
            affected_features=affected,
            recommendation=rec,
        )

    def predict_with_uncertainty(
        self,
        features: Dict[str, float],
        base_prediction: float = 0.5,
    ) -> Tuple[float, float]:
        """Make a prediction with uncertainty estimation.

        Returns (prediction, uncertainty) where prediction is in [0, 1]
        and uncertainty is the estimated standard deviation.
        """
        ewma = self._ewma.get_state()
        variance = self._ewma.get_variance()

        # Weighted combination of EWMA prediction and base prediction
        total_importance = 0.0
        weighted_pred = 0.0
        for key in features:
            if key in ewma:
                imp = self._feature_importance.get(key, 1.0)
                # Use the feature's EWMA as a directional signal
                feat_pred = 0.5 + 0.1 * math.tanh(ewma[key])
                weighted_pred += imp * feat_pred
                total_importance += imp

        if total_importance > 0:
            ewma_pred = weighted_pred / total_importance
        else:
            ewma_pred = 0.5

        # Blend with base prediction
        alpha = min(0.8, self._total_updates / 200.0)
        prediction = alpha * ewma_pred + (1 - alpha) * base_prediction

        # Uncertainty from variance and drift
        avg_variance = float(np.mean(list(variance.values()))) if variance else 0.01
        uncertainty = math.sqrt(avg_variance + 0.01)

        return float(np.clip(prediction, 0.01, 0.99)), float(np.clip(uncertainty, 0.01, 0.5))

    def get_learning_state(self) -> Dict[str, Any]:
        """Full learning state report."""
        recent_wr = list(self._rolling_win_rate)[-50:] if self._rolling_win_rate else [0.5]
        return {
            "total_updates": self._total_updates,
            "learning_rate": round(self._learning_rate, 6),
            "drift_events": self._drift_events,
            "adaptation_count": self._adaptation_count,
            "current_win_rate": round(float(np.mean(recent_wr)), 4),
            "win_rate_trend": round(float(np.mean(recent_wr[-10:])) - float(np.mean(recent_wr[:10])), 4) if len(recent_wr) >= 20 else 0.0,
            "feature_importance": {k: round(v, 4) for k, v in sorted(self._feature_importance.items(), key=lambda x: -x[1])[:10]},
            "ewma_state": {k: round(v, 6) for k, v in self._ewma.get_state().items()},
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        state = {
            "learning_rate": self._learning_rate,
            "total_updates": self._total_updates,
            "drift_events": self._drift_events,
            "adaptation_count": self._adaptation_count,
            "feature_importance": dict(self._feature_importance),
            "ewma_values": self._ewma.get_state(),
            "ewma_variances": self._ewma.get_variance(),
            "outcome_buffer": list(self._outcome_buffer),
            "rolling_win_rate": list(self._rolling_win_rate),
        }
        joblib.dump(state, path)
        logger.info("OnlineLearner saved to %s", path)

    def load(self, path: str) -> bool:
        try:
            state = joblib.load(path)
            self._learning_rate = state["learning_rate"]
            self._total_updates = state["total_updates"]
            self._drift_events = state["drift_events"]
            self._adaptation_count = state["adaptation_count"]
            self._feature_importance = defaultdict(lambda: 1.0, state["feature_importance"])
            self._ewma._values = state.get("ewma_values", {})
            self._ewma._variances = state.get("ewma_variances", {})
            self._outcome_buffer = deque(state.get("outcome_buffer", []), maxlen=_BUFFER_SIZE)
            self._rolling_win_rate = deque(state.get("rolling_win_rate", []), maxlen=200)
            logger.info("OnlineLearner loaded from %s", path)
            return True
        except Exception as exc:
            logger.error("Failed to load OnlineLearner: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_feature_importance(
        self,
        features: Dict[str, float],
        outcome: bool,
        confidence: float,
    ) -> None:
        """Incrementally update feature importance weights."""
        for key, val in features.items():
            # Features that co-occur with correct high-confidence predictions get higher importance
            contribution = 1.0 if outcome else -0.5
            contribution *= (confidence / 100.0)
            self._feature_importance[key] += self._learning_rate * contribution
            # Keep in reasonable range
            self._feature_importance[key] = max(0.01, min(5.0, self._feature_importance[key]))
