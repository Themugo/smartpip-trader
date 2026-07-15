"""
Market DNA Engine — deep market fingerprinting via clustering, regime transitions,
and anomaly detection.

Each market is assigned a unique "DNA fingerprint" based on its statistical
signature. The engine maintains a library of known fingerprints and can detect
when a market's behaviour deviates from its expected DNA (anomaly), predict
regime transitions via a learned Markov model, and cluster similar market
conditions for cross-market intelligence.
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
_MIN_SAMPLES_FOR_CLUSTERING = 20
_MAX_CLUSTERS = 12
_ANOMALY_Z_THRESHOLD = 2.5
_TRANSITION_SMOOTHING = 0.01
_DNA_BUFFER_SIZE = 1000
_FINGERPRINT_FEATURES = [
    "volatility", "autocorrelation", "hurst", "entropy",
    "skewness", "kurtosis", "mean_return", "return_range",
    "trend_strength", "mean_reversion_speed",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DNAFingerprint:
    """Statistical fingerprint of a market's current state."""
    market: str
    features: Dict[str, float]
    cluster_id: int = -1
    anomaly_score: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market": self.market,
            "features": {k: round(v, 6) for k, v in self.features.items()},
            "cluster_id": self.cluster_id,
            "anomaly_score": round(self.anomaly_score, 4),
            "timestamp": self.timestamp,
        }


@dataclass
class TransitionPrediction:
    """Predicted next regime given current regime and DNA cluster."""
    current_regime: str
    predicted_regime: str
    probability: float
    transition_matrix: Dict[str, Dict[str, float]]
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_regime": self.current_regime,
            "predicted_regime": self.predicted_regime,
            "probability": round(self.probability, 4),
            "confidence": round(self.confidence, 4),
            "timestamp": self.timestamp,
        }


@dataclass
class AnomalyReport:
    """Result of an anomaly detection check."""
    is_anomaly: bool
    anomaly_score: float
    z_scores: Dict[str, float]
    contributing_features: List[str]
    description: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_anomaly": self.is_anomaly,
            "anomaly_score": round(self.anomaly_score, 4),
            "z_scores": {k: round(v, 4) for k, v in self.z_scores.items()},
            "contributing_features": self.contributing_features,
            "description": self.description,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Online K-Means Clustering (numpy only)
# ---------------------------------------------------------------------------

class _OnlineKMeans:
    """Lightweight online K-Means using mini-batch centroid updates."""

    def __init__(self, n_clusters: int = 6, n_features: int = 10, learning_rate: float = 0.05):
        self.n_clusters = n_clusters
        self.n_features = n_features
        self.lr = learning_rate
        self.centroids: Optional[np.ndarray] = None
        self.counts: np.ndarray = np.zeros(n_clusters, dtype=np.int64)
        self._initialised = False

    def _init_centroids(self, x: np.ndarray) -> None:
        """Random initialisation from first batch."""
        n = min(len(x), self.n_clusters)
        indices = np.random.choice(len(x), size=n, replace=False)
        self.centroids = np.zeros((self.n_clusters, self.n_features), dtype=np.float64)
        for i in range(n):
            self.centroids[i] = x[indices[i]]
        for i in range(n, self.n_clusters):
            self.centroids[i] = x[indices[i % n]] + np.random.randn(self.n_features) * 0.01
        self._initialised = True

    def predict(self, x: np.ndarray) -> int:
        """Return the nearest cluster index for a single sample."""
        if not self._initialised or self.centroids is None:
            return 0
        dists = np.sqrt(np.sum((self.centroids - x) ** 2, axis=1))
        return int(np.argmin(dists))

    def update(self, x: np.ndarray) -> int:
        """Update centroids with a single sample and return assigned cluster."""
        if not self._initialised:
            self._init_centroids(x.reshape(1, -1))
            self.counts[0] = 1
            return 0

        cluster = self.predict(x)
        n = self.counts[cluster]
        alpha = self.lr / (1.0 + n * 0.001)
        self.centroids[cluster] = (1.0 - alpha) * self.centroids[cluster] + alpha * x
        self.counts[cluster] += 1
        return cluster

    def get_distances_to_centroids(self, x: np.ndarray) -> np.ndarray:
        """Return Euclidean distances from x to all centroids."""
        if not self._initialised or self.centroids is None:
            return np.full(self.n_clusters, np.inf)
        return np.sqrt(np.sum((self.centroids - x) ** 2, axis=1))


# ---------------------------------------------------------------------------
# MarketDNA
# ---------------------------------------------------------------------------

class MarketDNA:
    """Deep market fingerprinting engine.

    Maintains per-market DNA fingerprints, a clustering model, a Markov
    regime-transition model, and per-feature anomaly baselines.

    Usage::

        dna = MarketDNA()
        fp = dna.compute_fingerprint("volatility_75", prices, digits)
        anomaly = dna.detect_anomaly("volatility_75", fp)
        transition = dna.predict_transition("volatility_75", "TRENDING_UP")
    """

    def __init__(self, n_clusters: int = 6):
        self.n_clusters = n_clusters
        self._clusterer = _OnlineKMeans(
            n_clusters=n_clusters,
            n_features=len(_FINGERPRINT_FEATURES),
        )
        # Per-market fingerprint buffers
        self._fingerprints: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=_DNA_BUFFER_SIZE)
        )
        # Per-cluster feature accumulators (mean, std) for anomaly detection
        self._cluster_stats: Dict[int, Dict[str, Tuple[float, float]]] = {}
        # Per-market regime history for Markov model
        self._regime_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        # Transition counts
        self._transition_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._regime_totals: Dict[str, int] = defaultdict(int)

        logger.info("MarketDNA initialised (n_clusters=%d)", n_clusters)

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_features(
        price_history: List[float],
        digit_history: List[int],
    ) -> Dict[str, float]:
        """Extract the 10-dimensional DNA feature vector."""
        prices = np.array(price_history, dtype=np.float64) if price_history else np.array([0.0])
        if len(prices) < 2:
            returns = np.array([0.0])
        else:
            returns = np.diff(np.log(np.maximum(prices, 1e-12)))

        volatility = float(np.std(returns)) if len(returns) > 1 else 0.0

        # Autocorrelation lag-1
        if len(returns) > 2:
            x, y = returns[:-1], returns[1:]
            if np.std(x) > 1e-12 and np.std(y) > 1e-12:
                autocorr = float(np.corrcoef(x, y)[0, 1])
            else:
                autocorr = 0.0
        else:
            autocorr = 0.0

        # Hurst exponent (simplified R/S)
        hurst = 0.5
        if len(prices) >= 20:
            try:
                max_k = min(len(returns) // 2, 50)
                rs_list, ns_list = [], []
                for k in range(10, max_k + 1, max(1, (max_k - 10) // 5)):
                    sub = returns[:k]
                    mean = np.mean(sub)
                    deviate = np.cumsum(sub - mean)
                    r = float(np.max(deviate) - np.min(deviate))
                    s = float(np.std(sub, ddof=1))
                    if s > 1e-12:
                        rs_list.append(r / s)
                        ns_list.append(k)
                if len(rs_list) >= 2:
                    slope = float(np.polyfit(np.log(ns_list), np.log(rs_list), 1)[0])
                    hurst = float(np.clip(slope, 0.0, 1.0))
            except Exception:
                pass

        # Shannon entropy
        entropy = 0.0
        if digit_history:
            counts = np.zeros(10, dtype=np.float64)
            for d in digit_history:
                if 0 <= d <= 9:
                    counts[d] += 1
            total = counts.sum()
            if total > 0:
                probs = counts / total
                probs = probs[probs > 0]
                entropy = float(-np.sum(probs * np.log2(probs)))

        # Skewness & kurtosis
        skewness = float(np.mean(((returns - np.mean(returns)) / (np.std(returns) + 1e-12)) ** 3)) if len(returns) > 2 else 0.0
        kurtosis = float(np.mean(((returns - np.mean(returns)) / (np.std(returns) + 1e-12)) ** 4) - 3.0) if len(returns) > 3 else 0.0

        mean_return = float(np.mean(returns)) if len(returns) > 0 else 0.0
        return_range = float(np.ptp(returns)) if len(returns) > 0 else 0.0

        # Trend strength: |slope of linear fit| / std
        trend_strength = 0.0
        if len(prices) >= 10:
            x_idx = np.arange(len(prices), dtype=np.float64)
            slope_val = float(np.polyfit(x_idx, prices, 1)[0])
            trend_strength = abs(slope_val) / (float(np.std(prices)) + 1e-12)

        # Mean reversion speed: -autocorrelation of price levels (negative = mean-reverting)
        mr_speed = 0.0
        if len(prices) > 5:
            deviations = prices - np.mean(prices)
            if np.std(deviations) > 1e-12:
                mr_speed = -autocorr

        return {
            "volatility": volatility,
            "autocorrelation": autocorr,
            "hurst": hurst,
            "entropy": entropy,
            "skewness": skewness,
            "kurtosis": kurtosis,
            "mean_return": mean_return,
            "return_range": return_range,
            "trend_strength": trend_strength,
            "mean_reversion_speed": mr_speed,
        }

    def _features_to_vector(self, features: Dict[str, float]) -> np.ndarray:
        """Convert named features to ordered numpy vector."""
        return np.array([features.get(k, 0.0) for k in _FINGERPRINT_FEATURES], dtype=np.float64)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_fingerprint(
        self,
        market: str,
        price_history: List[float],
        digit_history: List[int],
    ) -> DNAFingerprint:
        """Compute and store a DNA fingerprint for a market."""
        features = self._extract_features(price_history, digit_history)
        vec = self._features_to_vector(features)

        cluster_id = self._clusterer.update(vec)

        # Compute anomaly score against cluster stats
        anomaly_score = self._compute_anomaly_score(cluster_id, features)

        fp = DNAFingerprint(
            market=market,
            features=features,
            cluster_id=cluster_id,
            anomaly_score=anomaly_score,
        )
        self._fingerprints[market].append(fp)

        # Update cluster stats
        self._update_cluster_stats(cluster_id, features)

        return fp

    def detect_anomaly(
        self,
        market: str,
        fingerprint: DNAFingerprint,
    ) -> AnomalyReport:
        """Check if a fingerprint is anomalous relative to historical norms."""
        z_scores: Dict[str, float] = {}
        contributing: List[str] = []

        for feat_name in _FINGERPRINT_FEATURES:
            val = fingerprint.features.get(feat_name, 0.0)
            # Gather historical values for this market
            hist = [fp.features.get(feat_name, 0.0) for fp in self._fingerprints.get(market, [])]
            if len(hist) < 5:
                z_scores[feat_name] = 0.0
                continue
            arr = np.array(hist, dtype=np.float64)
            mu, sigma = float(np.mean(arr)), float(np.std(arr))
            if sigma < 1e-12:
                z_scores[feat_name] = 0.0
            else:
                z = (val - mu) / sigma
                z_scores[feat_name] = float(z)
                if abs(z) > _ANOMALY_Z_THRESHOLD:
                    contributing.append(feat_name)

        # Overall anomaly score: max absolute z-score
        abs_z = [abs(v) for v in z_scores.values()]
        overall = max(abs_z) if abs_z else 0.0
        is_anomaly = overall > _ANOMALY_Z_THRESHOLD

        if is_anomaly:
            desc = f"Anomaly detected: {', '.join(contributing)} deviate significantly from history"
        else:
            desc = "Market behaviour consistent with historical DNA"

        return AnomalyReport(
            is_anomaly=is_anomaly,
            anomaly_score=round(overall, 4),
            z_scores=z_scores,
            contributing_features=contributing,
            description=desc,
        )

    def predict_transition(
        self,
        market: str,
        current_regime: str,
    ) -> TransitionPrediction:
        """Predict the most likely next regime via learned Markov model."""
        # Record the transition
        history = self._regime_history.get(market, deque())
        if history and len(history) > 0:
            prev = history[-1]
            self._transition_counts[market][f"{prev}->{current_regime}"] += 1
            self._regime_totals[market] += 1

        self._regime_history[market].append(current_regime)

        # Build transition probabilities
        total = self._regime_totals.get(market, 0)
        if total < 5:
            # Not enough data — return uniform
            regimes = ["TRENDING_UP", "TRENDING_DOWN", "MEAN_REVERTING", "RANDOM", "HIGH_VOLATILITY", "LOW_VOLATILITY"]
            uniform = {r: 1.0 / len(regimes) for r in regimes}
            return TransitionPrediction(
                current_regime=current_regime,
                predicted_regime=current_regime,
                probability=1.0 / len(regimes),
                transition_matrix={current_regime: uniform},
            )

        transitions: Dict[str, float] = {}
        for key, count in self._transition_counts.get(market, {}).items():
            if key.startswith(f"{current_regime}->"):
                next_regime = key.split("->")[1]
                transitions[next_regime] = count / total + _TRANSITION_SMOOTHING

        if not transitions:
            regimes = ["TRENDING_UP", "TRENDING_DOWN", "MEAN_REVERTING", "RANDOM", "HIGH_VOLATILITY", "LOW_VOLATILITY"]
            transitions = {r: 1.0 / len(regimes) for r in regimes}

        # Normalise
        total_prob = sum(transitions.values())
        transitions = {k: v / total_prob for k, v in transitions.items()}

        best = max(transitions, key=transitions.get)
        return TransitionPrediction(
            current_regime=current_regime,
            predicted_regime=best,
            probability=transitions[best],
            transition_matrix={current_regime: transitions},
        )

    def get_market_profile(self, market: str) -> Dict[str, Any]:
        """Return a comprehensive DNA profile for a market."""
        fps = list(self._fingerprints.get(market, []))
        if not fps:
            return {"market": market, "fingerprints": 0, "avg_features": {}, "clusters": []}

        # Average features
        avg_features: Dict[str, float] = {}
        for feat in _FINGERPRINT_FEATURES:
            vals = [fp.features.get(feat, 0.0) for fp in fps]
            avg_features[feat] = round(float(np.mean(vals)), 6)

        clusters = list(set(fp.cluster_id for fp in fps))

        return {
            "market": market,
            "fingerprints": len(fps),
            "avg_features": avg_features,
            "clusters": clusters,
            "latest_cluster": fps[-1].cluster_id if fps else -1,
            "latest_anomaly_score": fps[-1].anomaly_score if fps else 0.0,
        }

    def get_global_stats(self) -> Dict[str, Any]:
        """Return aggregate engine statistics."""
        total_fps = sum(len(fps) for fps in self._fingerprints.values())
        markets = list(self._fingerprints.keys())
        return {
            "total_fingerprints": total_fps,
            "markets_tracked": len(markets),
            "n_clusters": self.n_clusters,
            "cluster_sizes": self._clusterer.counts.tolist() if self._clusterer._initialised else [],
            "cluster_trained": self._clusterer._initialised,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Serialise engine state to disk."""
        state = {
            "n_clusters": self.n_clusters,
            "clusterer_centroids": self._clusterer.centroids.tolist() if self._clusterer.centroids is not None else None,
            "clusterer_counts": self._clusterer.counts.tolist(),
            "cluster_stats": {str(k): v for k, v in self._cluster_stats.items()},
            "regime_totals": dict(self._regime_totals),
        }
        joblib.dump(state, path)
        logger.info("MarketDNA saved to %s", path)

    def load(self, path: str) -> bool:
        """Restore engine state from disk."""
        try:
            state = joblib.load(path)
            self.n_clusters = state["n_clusters"]
            self._clusterer = _OnlineKMeans(n_clusters=self.n_clusters, n_features=len(_FINGERPRINT_FEATURES))
            if state["clusterer_centroids"] is not None:
                self._clusterer.centroids = np.array(state["clusterer_centroids"], dtype=np.float64)
            self._clusterer.counts = np.array(state["clusterer_counts"], dtype=np.int64)
            self._clusterer._initialised = self._clusterer.centroids is not None
            self._cluster_stats = state.get("cluster_stats", {})
            self._regime_totals = defaultdict(int, state.get("regime_totals", {}))
            logger.info("MarketDNA loaded from %s", path)
            return True
        except Exception as exc:
            logger.error("Failed to load MarketDNA: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_anomaly_score(self, cluster_id: int, features: Dict[str, float]) -> float:
        """Z-score based anomaly score against cluster centroid."""
        stats = self._cluster_stats.get(cluster_id)
        if stats is None:
            return 0.0
        z_scores = []
        for feat in _FINGERPRINT_FEATURES:
            mu, sigma = stats.get(feat, (0.0, 1.0))
            val = features.get(feat, 0.0)
            if sigma > 1e-12:
                z_scores.append(abs((val - mu) / sigma))
        return max(z_scores) if z_scores else 0.0

    def _update_cluster_stats(self, cluster_id: int, features: Dict[str, float]) -> None:
        """Incrementally update running mean and variance for the cluster."""
        if cluster_id not in self._cluster_stats:
            self._cluster_stats[cluster_id] = {f: (features.get(f, 0.0), 1.0) for f in _FINGERPRINT_FEATURES}
            return

        stats = self._cluster_stats[cluster_id]
        for feat in _FINGERPRINT_FEATURES:
            val = features.get(feat, 0.0)
            mu, var = stats.get(feat, (0.0, 1.0))
            # Welford's online update
            new_mu = mu + (val - mu) * 0.01
            new_var = var + ((val - mu) * (val - new_mu) - var) * 0.01
            stats[feat] = (new_mu, max(new_var, 1e-12))
