"""
Regime Detector — statistical market regime classification.

Classifies market states into discrete regimes using statistical features
extracted from price and digit history.  Uses an online nearest-centroid
classifier that improves with labelled examples over time.

Regimes
-------
TRENDING_UP / TRENDING_DOWN / MEAN_REVERTING / RANDOM /
HIGH_VOLATILITY / LOW_VOLATILITY
"""

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats as sp_stats
import joblib

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

VALID_REGIMES = (
    "TRENDING_UP",
    "TRENDING_DOWN",
    "MEAN_REVERTING",
    "RANDOM",
    "HIGH_VOLATILITY",
    "LOW_VOLATILITY",
)

MIN_HISTORY = 15
FEATURE_BUFFER_SIZE = 500
LEARNING_RATE = 0.05
CENTROID_DECAY = 0.98


# ── Dataclass ────────────────────────────────────────────────────────────

@dataclass
class MarketRegime:
    """Immutable snapshot of a detected market regime.

    Attributes:
        regime: One of the ``VALID_REGIMES`` strings.
        confidence: Classification confidence in ``[0, 1]``.
        features: Dictionary of the statistical features that led to the
            classification.  Useful for downstream explainability.
        timestamp: Unix epoch time when the regime was detected.
    """
    regime: str
    confidence: float
    features: Dict[str, float]
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary."""
        return {
            "regime": self.regime,
            "confidence": round(self.confidence, 4),
            "features": {k: round(v, 6) for k, v in self.features.items()},
            "timestamp": self.timestamp,
        }


# ── Feature extraction helpers ───────────────────────────────────────────

def _compute_returns(prices: np.ndarray) -> np.ndarray:
    """Log-returns from a price array.  Returns empty array when len < 2."""
    if len(prices) < 2:
        return np.array([], dtype=np.float64)
    return np.diff(np.log(np.maximum(prices, 1e-12)))


def _compute_volatility(returns: np.ndarray) -> float:
    """Annualised volatility from log-returns."""
    if len(returns) < 2:
        return 0.0
    return float(np.std(returns, ddof=1) * math.sqrt(252))


def _autocorrelation(returns: np.ndarray, lag: int = 1) -> float:
    """Lag-1 autocorrelation of returns."""
    if len(returns) < lag + 2:
        return 0.0
    n = len(returns)
    x = returns[: n - lag]
    y = returns[lag:]
    if np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def _hurst_exponent_approx(prices: np.ndarray) -> float:
    """Simplified Hurst exponent via rescaled-range (R/S).

    H > 0.5  → trending (persistent)
    H < 0.5  → mean-reverting (anti-persistent)
    H ≈ 0.5  → random walk

    Returns a value in ``[0, 1]``.
    """
    if len(prices) < 20:
        return 0.5
    try:
        returns = _compute_returns(prices)
        n = len(returns)
        if n < 10:
            return 0.5

        max_k = min(n // 2, 50)
        rs_list: List[float] = []
        ns_list: List[int] = []

        for k in range(10, max_k + 1, max(1, (max_k - 10) // 5)):
            sub = returns[:k]
            mean = np.mean(sub)
            deviate = np.cumsum(sub - mean)
            r = float(np.max(deviate) - np.min(deviate))
            s = float(np.std(sub, ddof=1))
            if s > 1e-12:
                rs_list.append(r / s)
                ns_list.append(k)

        if len(rs_list) < 2:
            return 0.5

        log_n = np.log(ns_list)
        log_rs = np.log(np.array(rs_list))
        slope, _, _, _, _ = sp_stats.linregress(log_n, log_rs)
        return float(np.clip(slope, 0.0, 1.0))
    except Exception:
        return 0.5


def _runs_test_statistic(digit_history: List[int]) -> float:
    """Wald–Wolfowitz runs test statistic on binary split (digit ≥ 5).

    Large |Z| → non-random clustering.
    Returns the absolute Z-statistic.
    """
    if len(digit_history) < 10:
        return 0.0
    try:
        binary = np.array([1 if d >= 5 else 0 for d in digit_history], dtype=np.float64)
        n = len(binary)
        n1 = int(np.sum(binary))
        n0 = n - n1
        if n1 == 0 or n0 == 0:
            return 0.0

        runs = 1
        for i in range(1, n):
            if binary[i] != binary[i - 1]:
                runs += 1

        expected = (2.0 * n1 * n0) / n + 1.0
        variance = (2.0 * n1 * n0 * (2.0 * n1 * n0 - n)) / (n * n * (n - 1))
        if variance <= 0:
            return 0.0
        z = (runs - expected) / math.sqrt(variance)
        return float(abs(z))
    except Exception:
        return 0.0


def _shannon_entropy(digit_history: List[int]) -> float:
    """Shannon entropy of the digit distribution (bits).

    Low entropy → strong bias.
    Maximum ≈ 3.32 bits for uniform 0-9.
    """
    if not digit_history:
        return 0.0
    try:
        counts = np.zeros(10, dtype=np.float64)
        for d in digit_history:
            if 0 <= d <= 9:
                counts[d] += 1
        total = counts.sum()
        if total == 0:
            return 0.0
        probs = counts / total
        probs = probs[probs > 0]
        return float(-np.sum(probs * np.log2(probs)))
    except Exception:
        return 0.0


def _compute_skewness(returns: np.ndarray) -> float:
    """Return skewness of log-returns."""
    if len(returns) < 3:
        return 0.0
    return float(sp_stats.skew(returns, bias=False))


def _compute_kurtosis(returns: np.ndarray) -> float:
    """Excess kurtosis of log-returns."""
    if len(returns) < 4:
        return 0.0
    return float(sp_stats.kurtosis(returns, bias=False))


def extract_regime_features(
    price_history: List[float],
    digit_history: List[int],
) -> Dict[str, float]:
    """Extract the full statistical feature vector used for regime classification.

    Returns a dict of named float features.  Safe to call with short histories;
    insufficient-data features default to neutral values.
    """
    prices = np.array(price_history, dtype=np.float64)
    returns = _compute_returns(prices)

    features: Dict[str, float] = {
        "volatility": _compute_volatility(returns),
        "autocorrelation_lag1": _autocorrelation(returns, lag=1),
        "autocorrelation_lag3": _autocorrelation(returns, lag=3),
        "hurst_exponent": _hurst_exponent_approx(prices),
        "runs_test": _runs_test_statistic(digit_history),
        "shannon_entropy": _shannon_entropy(digit_history),
        "skewness": _compute_skewness(returns),
        "kurtosis": _compute_kurtosis(returns),
        "mean_return": float(np.mean(returns)) if len(returns) > 0 else 0.0,
        "return_range": float(np.ptp(returns)) if len(returns) > 0 else 0.0,
    }
    return features


# ── Nearest-Centroid Classifier ──────────────────────────────────────────

class _NearestCentroidClassifier:
    """Lightweight online nearest-centroid classifier (numpy only).

    Each class is represented by a centroid in feature space.
    Centroids are updated incrementally via exponential moving average when
    new labelled examples arrive.
    """

    def __init__(self, n_features: int, learning_rate: float = LEARNING_RATE):
        self.n_features = n_features
        self.learning_rate = learning_rate
        self.centroids: Dict[str, np.ndarray] = {}
        self.counts: Dict[str, int] = {}

    @property
    def is_trained(self) -> bool:
        return len(self.centroids) >= 2 and all(c >= 3 for c in self.counts.values())

    def predict(self, x: np.ndarray) -> tuple:
        """Return ``(label, confidence)`` for a feature vector."""
        if not self.centroids:
            return "RANDOM", 0.0

        labels = list(self.centroids.keys())
        dists = {}
        for label in labels:
            diff = x - self.centroids[label]
            dists[label] = float(np.sqrt(np.sum(diff * diff)))

        sorted_labels = sorted(dists, key=lambda k: dists[k])
        best = sorted_labels[0]
        second = sorted_labels[1] if len(sorted_labels) > 1 else best

        d_best = dists[best]
        d_second = dists[second]

        # Confidence: inverse-distance weighting with softmax-like normalisation
        all_dists = np.array([dists[l] for l in labels])
        min_d = all_dists.min()
        max_d = all_dists.max()
        if max_d - min_d < 1e-12:
            confidence = 1.0 / len(labels)
        else:
            inv = np.exp(-(all_dists - min_d) / (max_d - min_d + 1e-12))
            probs = inv / inv.sum()
            confidence = float(probs[labels.index(best)])

        # Distance ratio boost
        if d_second > 1e-12:
            ratio = d_best / d_second
            confidence = confidence * (1.0 + max(0.0, 1.0 - ratio))

        return best, float(np.clip(confidence, 0.0, 1.0))

    def update(self, x: np.ndarray, label: str):
        """Incrementally update the centroid for *label*."""
        if label not in self.centroids:
            self.centroids[label] = x.copy()
            self.counts[label] = 1
        else:
            n = self.counts[label]
            alpha = self.learning_rate / (1.0 + n * 0.01)
            self.centroids[label] = (1.0 - alpha) * self.centroids[label] + alpha * x
            self.counts[label] = n + 1


# ── Public API ───────────────────────────────────────────────────────────

class RegimeDetector:
    """Market regime detection using statistical learning.

    Maintains a rolling buffer of extracted features, an online
    nearest-centroid classifier, and a history of recent classifications
    for stability assessment.

    Usage::

        detector = RegimeDetector()
        regime = detector.detect(prices, digits)
        # … later, after knowing the actual regime:
        detector.update(prices, digits, actual_regime="TRENDING_UP")
    """

    def __init__(self) -> None:
        self._feature_buffer: deque = deque(maxlen=FEATURE_BUFFER_SIZE)
        self._regime_history: deque = deque(maxlen=200)
        self._classifier = _NearestCentroidClassifier(n_features=10)
        self._detection_count: int = 0

        # Regime distribution counter (for stats)
        self._regime_counts: Dict[str, int] = {r: 0 for r in VALID_REGIMES}

        # Bootstrap with some neutral centroids so the classifier always
        # produces a prediction even before any labelled examples arrive.
        self._init_bootstrap_centroids()

    # ── Bootstrap ─────────────────────────────────────────────────────────

    def _init_bootstrap_centroids(self) -> None:
        """Initialise centroids with heuristic defaults per regime."""
        boot: Dict[str, Dict[str, float]] = {
            "TRENDING_UP": {
                "volatility": 0.15, "autocorrelation_lag1": 0.4,
                "autocorrelation_lag3": 0.2, "hurst_exponent": 0.65,
                "runs_test": 0.8, "shannon_entropy": 3.1,
                "skewness": 0.3, "kurtosis": 0.5,
                "mean_return": 0.001, "return_range": 0.05,
            },
            "TRENDING_DOWN": {
                "volatility": 0.18, "autocorrelation_lag1": 0.35,
                "autocorrelation_lag3": 0.15, "hurst_exponent": 0.62,
                "runs_test": 0.9, "shannon_entropy": 3.0,
                "skewness": -0.3, "kurtosis": 0.5,
                "mean_return": -0.001, "return_range": 0.06,
            },
            "MEAN_REVERTING": {
                "volatility": 0.12, "autocorrelation_lag1": -0.3,
                "autocorrelation_lag3": -0.15, "hurst_exponent": 0.35,
                "runs_test": 1.2, "shannon_entropy": 3.2,
                "skewness": 0.0, "kurtosis": 1.0,
                "mean_return": 0.0, "return_range": 0.04,
            },
            "RANDOM": {
                "volatility": 0.14, "autocorrelation_lag1": 0.02,
                "autocorrelation_lag3": 0.01, "hurst_exponent": 0.5,
                "runs_test": 0.4, "shannon_entropy": 3.3,
                "skewness": 0.0, "kurtosis": 0.0,
                "mean_return": 0.0, "return_range": 0.05,
            },
            "HIGH_VOLATILITY": {
                "volatility": 0.35, "autocorrelation_lag1": 0.1,
                "autocorrelation_lag3": 0.05, "hurst_exponent": 0.5,
                "runs_test": 0.6, "shannon_entropy": 2.8,
                "skewness": 0.5, "kurtosis": 3.0,
                "mean_return": 0.0, "return_range": 0.15,
            },
            "LOW_VOLATILITY": {
                "volatility": 0.04, "autocorrelation_lag1": 0.05,
                "autocorrelation_lag3": 0.03, "hurst_exponent": 0.45,
                "runs_test": 0.5, "shannon_entropy": 3.3,
                "skewness": 0.0, "kurtosis": -0.3,
                "mean_return": 0.0, "return_range": 0.01,
            },
        }
        feature_names = sorted(boot["RANDOM"].keys())
        for regime, vals in boot.items():
            vec = np.array([vals[k] for k in feature_names], dtype=np.float64)
            self._classifier.centroids[regime] = vec
            self._classifier.counts[regime] = 3  # pretend 3 samples

    # ── Public interface ──────────────────────────────────────────────────

    def detect(
        self,
        price_history: List[float],
        digit_history: List[int],
    ) -> MarketRegime:
        """Classify the current market regime.

        Parameters:
            price_history: Recent price values (oldest → newest).
            digit_history: Recent last-digit values.

        Returns:
            A ``MarketRegime`` with the detected regime, confidence, and
            the feature vector that was used for classification.

        When data is insufficient (< ``MIN_HISTORY`` data-points) the method
        returns a conservative ``RANDOM`` regime with low confidence.
        """
        try:
            features = extract_regime_features(price_history, digit_history)
            self._feature_buffer.append(features)

            if len(price_history) < MIN_HISTORY:
                return MarketRegime(
                    regime="RANDOM",
                    confidence=0.3,
                    features=features,
                    timestamp=time.time(),
                )

            # Build feature vector (sorted keys for deterministic ordering)
            sorted_keys = sorted(features.keys())
            x = np.array([features[k] for k in sorted_keys], dtype=np.float64)

            # Ensure classifier matches this feature order
            if self._classifier.n_features != len(sorted_keys):
                self._classifier = _NearestCentroidClassifier(
                    n_features=len(sorted_keys),
                )
                self._init_bootstrap_centroids()

            label, confidence = self._classifier.predict(x)

            # Stability bonus: if recent predictions agree, boost confidence
            recent = list(self._regime_history)[-5:]
            if recent and len(recent) >= 3:
                agree = sum(1 for r in recent if r.regime == label) / len(recent)
                confidence = confidence * (0.7 + 0.3 * agree)

            regime = MarketRegime(
                regime=label,
                confidence=float(np.clip(confidence, 0.0, 1.0)),
                features=features,
                timestamp=time.time(),
            )

            self._regime_history.append(regime)
            self._regime_counts[label] = self._regime_counts.get(label, 0) + 1
            self._detection_count += 1

            logger.debug(
                "Regime detected: %s (%.2f) — vol=%.4f ac=%.3f hurst=%.3f",
                label, confidence, features["volatility"],
                features["autocorrelation_lag1"], features["hurst_exponent"],
            )
            return regime

        except Exception as exc:
            logger.error("Regime detection failed: %s", exc, exc_info=True)
            return MarketRegime(
                regime="RANDOM",
                confidence=0.0,
                features={},
                timestamp=time.time(),
            )

    def update(
        self,
        price_history: List[float],
        digit_history: List[int],
        actual_regime: str,
    ) -> None:
        """Provide a labelled example for online learning.

        Call this after you know the true regime (e.g. from manual review or
        a delayed label) to improve future classifications.

        Parameters:
            price_history: The full price history at the time of the event.
            digit_history: The full digit history at the time of the event.
            actual_regime: The ground-truth regime label.
        """
        if actual_regime not in VALID_REGIMES:
            logger.warning("Invalid regime label '%s' — ignoring update.", actual_regime)
            return

        try:
            features = extract_regime_features(price_history, digit_history)
            sorted_keys = sorted(features.keys())
            x = np.array([features[k] for k in sorted_keys], dtype=np.float64)

            if self._classifier.n_features != len(sorted_keys):
                logger.warning("Feature dimension mismatch — skipping update.")
                return

            self._classifier.update(x, actual_regime)
            logger.info(
                "Regime classifier updated with label '%s' (centroid count=%d).",
                actual_regime, self._classifier.counts.get(actual_regime, 0),
            )
        except Exception as exc:
            logger.error("Regime update failed: %s", exc, exc_info=True)

    def get_regime_stats(self) -> Dict[str, Any]:
        """Return a summary of regime detection statistics.

        Includes the distribution of detected regimes, total detection count,
        and classifier state.
        """
        total = sum(self._regime_counts.values())
        distribution = {
            r: {
                "count": self._regime_counts.get(r, 0),
                "pct": round(
                    self._regime_counts.get(r, 0) / total * 100, 1
                ) if total > 0 else 0.0,
            }
            for r in VALID_REGIMES
        }
        return {
            "total_detections": self._detection_count,
            "distribution": distribution,
            "classifier_trained": self._classifier.is_trained,
            "centroid_labels": list(self._classifier.centroids.keys()),
            "centroid_sizes": dict(self._classifier.counts),
            "recent_regimes": [
                r.to_dict() for r in list(self._regime_history)[-10:]
            ],
        }

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        """Serialise the detector state to *path* via joblib."""
        try:
            state = {
                "classifier_centroids": dict(self._classifier.centroids),
                "classifier_counts": dict(self._classifier.counts),
                "classifier_n_features": self._classifier.n_features,
                "regime_counts": dict(self._regime_counts),
                "detection_count": self._detection_count,
            }
            joblib.dump(state, path)
            logger.info("RegimeDetector saved to %s", path)
        except Exception as exc:
            logger.error("Failed to save RegimeDetector: %s", exc, exc_info=True)

    def load(self, path: str) -> bool:
        """Restore detector state from *path*.  Returns ``True`` on success."""
        try:
            state = joblib.load(path)
            centroids = state["classifier_centroids"]
            counts = state["classifier_counts"]
            n_feat = state["classifier_n_features"]

            self._classifier = _NearestCentroidClassifier(
                n_features=n_feat,
            )
            self._classifier.centroids = {
                k: np.asarray(v, dtype=np.float64) for k, v in centroids.items()
            }
            self._classifier.counts = dict(counts)
            self._regime_counts = dict(state.get("regime_counts", {r: 0 for r in VALID_REGIMES}))
            self._detection_count = state.get("detection_count", 0)

            logger.info("RegimeDetector loaded from %s", path)
            return True
        except Exception as exc:
            logger.error("Failed to load RegimeDetector: %s", exc, exc_info=True)
            return False
