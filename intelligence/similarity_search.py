"""
Similarity Search — high-performance historical pattern matching.

Upgrades the basic case-based reasoning with:
  - LSH (Locality-Sensitive Hashing) inspired indexing for O(1) approximate
    nearest-neighbour lookups on millions of stored vectors.
  - Multi-dimensional similarity across price patterns, regime context,
    timing, and sentiment.
  - Temporal decay weighting so recent patterns are prioritised.
  - Cross-market similarity for transferring insights between instruments.
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
_MAX_INDEX_SIZE = 500_000
_DEFAULT_TOP_K = 10
_TEMPORAL_DECAY_LAMBDA = 0.001  # exponential decay per hour
_FEATURE_DIMS = 12
_BUCKET_COUNT = 64
_HASH_FUNCTIONS = 8
_MIN_SIMILARITY = 0.3


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SearchResult:
    """Single result from similarity search."""
    record_id: str
    market: str
    similarity: float
    features: Dict[str, float]
    outcome: str
    profit: float
    regime: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "market": self.market,
            "similarity": round(self.similarity, 4),
            "outcome": self.outcome,
            "profit": round(self.profit, 4),
            "regime": self.regime,
            "timestamp": self.timestamp,
        }


@dataclass
class PatternCluster:
    """A cluster of similar historical patterns."""
    cluster_id: int
    centroid: np.ndarray
    count: int
    avg_profit: float = 0.0
    win_rate: float = 0.0
    representative_regime: str = "UNKNOWN"
    markets: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "count": self.count,
            "avg_profit": round(self.avg_profit, 4),
            "win_rate": round(self.win_rate, 4),
            "representative_regime": self.representative_regime,
            "markets": self.markets,
        }


# ---------------------------------------------------------------------------
# SimHash (LSH) for approximate similarity
# ---------------------------------------------------------------------------

class _SimHashIndex:
    """Locality-sensitive hashing index using random hyperplane projections."""

    def __init__(self, dim: int = _FEATURE_DIMS, n_hash: int = _HASH_FUNCTIONS, n_buckets: int = _BUCKET_COUNT):
        self.dim = dim
        self.n_hash = n_hash
        self.n_buckets = n_buckets
        self._projections: np.ndarray = np.random.randn(n_hash, dim)
        self._buckets: Dict[int, List[int]] = defaultdict(list)
        self._hash_to_id: Dict[int, str] = {}
        self._vectors: Dict[int, np.ndarray] = {}

    def _hash(self, vec: np.ndarray) -> int:
        """Compute bucket hash via random hyperplane projections."""
        projections = self._projections @ vec
        bits = (projections > 0).astype(np.int64)
        # Convert bit array to integer key
        key = 0
        for b in bits:
            key = (key << 1) | int(b)
        return key % self.n_buckets

    def add(self, vec: np.ndarray, record_id: str) -> None:
        """Add a vector to the LSH index."""
        idx = len(self._vectors)
        self._vectors[idx] = vec
        self._hash_to_id[idx] = record_id
        bucket = self._hash(vec)
        self._buckets[bucket].append(idx)

    def query(self, vec: np.ndarray, top_k: int = _DEFAULT_TOP_K) -> List[Tuple[int, float]]:
        """Approximate nearest-neighbour query.

        Returns list of (record_id_hash, cosine_similarity) tuples.
        """
        bucket = self._hash(vec)
        candidates = self._buckets.get(bucket, [])

        # Also check adjacent buckets for better recall
        candidates_set = set(candidates)
        for offset in range(1, 3):
            for b in [bucket - offset, bucket + offset]:
                b = b % self.n_buckets
                candidates_set.update(self._buckets.get(b, []))

        if not candidates_set:
            return []

        vec_norm = np.linalg.norm(vec)
        if vec_norm < 1e-12:
            return []

        scored = []
        for idx in candidates_set:
            stored = self._vectors.get(idx)
            if stored is None:
                continue
            stored_norm = np.linalg.norm(stored)
            if stored_norm < 1e-12:
                continue
            cos_sim = float(np.dot(vec, stored) / (vec_norm * stored_norm))
            scored.append((idx, cos_sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def size(self) -> int:
        return len(self._vectors)

    def clear(self) -> None:
        self._buckets.clear()
        self._hash_to_id.clear()
        self._vectors.clear()


# ---------------------------------------------------------------------------
# SimilaritySearch
# ---------------------------------------------------------------------------

class SimilaritySearch:
    """High-performance historical similarity search engine.

    Maintains a vector index of historical market patterns with multi-
    dimensional features, temporal decay weighting, and cross-market
    pattern transfer.

    Usage::

        engine = SimilaritySearch()
        engine.index_pattern("vol_75", features, outcome="WIN", profit=0.5)
        results = engine.search(query_features, top_k=10)
    """

    def __init__(self):
        self._index = _SimHashIndex(dim=_FEATURE_DIMS)
        self._records: Dict[int, Dict[str, Any]] = {}
        self._feature_matrix: List[np.ndarray] = []
        self._pattern_clusters: List[PatternCluster] = []
        self._total_queries: int = 0
        self._total_indexed: int = 0
        logger.info("SimilaritySearch initialised")

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_features(
        price_history: List[float],
        digit_history: List[int],
        regime: str = "UNKNOWN",
        hour: int = 12,
        confidence: float = 50.0,
        direction: str = "CALL",
    ) -> Dict[str, float]:
        """Extract the canonical feature vector for similarity search."""
        prices = np.array(price_history, dtype=np.float64) if price_history else np.array([0.0])
        if len(prices) < 2:
            returns = np.array([0.0])
        else:
            returns = np.diff(np.log(np.maximum(prices, 1e-12)))

        volatility = float(np.std(returns)) if len(returns) > 1 else 0.0

        # Momentum: recent trend direction and strength
        momentum = 0.0
        if len(prices) >= 5:
            momentum = float((prices[-1] - prices[-5]) / (np.mean(prices[-5:]) + 1e-12))

        # Pattern complexity
        complexity = 0.0
        if len(returns) > 3:
            complexity = float(np.std(np.abs(np.diff(returns))))

        # Regime encoding (one-hot → 6 dims)
        regime_map = {
            "TRENDING_UP": 0, "TRENDING_DOWN": 1, "MEAN_REVERTING": 2,
            "RANDOM": 3, "HIGH_VOLATILITY": 4, "LOW_VOLATILITY": 5,
        }
        regime_idx = regime_map.get(regime.upper(), 3)
        regime_oh = [0.0] * 6
        regime_oh[regime_idx] = 1.0

        direction_sign = 1.0 if direction.upper() in ("CALL", "RISE", "EVEN", "OVER") else -1.0

        # Time encoding
        hour_sin = math.sin(2 * math.pi * hour / 24)
        hour_cos = math.cos(2 * math.pi * hour / 24)

        # Entropy
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

        return {
            "volatility": volatility,
            "momentum": momentum,
            "complexity": complexity,
            "confidence": confidence / 100.0,
            "direction": direction_sign,
            "hour_sin": hour_sin,
            "hour_cos": hour_cos,
            "entropy": entropy,
            "regime_0": regime_oh[0],
            "regime_1": regime_oh[1],
            "regime_2": regime_oh[2],
            "regime_3": regime_oh[3],
        }

    @staticmethod
    def _features_to_vector(features: Dict[str, float]) -> np.ndarray:
        """Convert named features to ordered numpy vector."""
        keys = sorted(features.keys())[:_FEATURE_DIMS]
        vec = np.zeros(_FEATURE_DIMS, dtype=np.float64)
        for i, k in enumerate(keys):
            vec[i] = features.get(k, 0.0)
        return vec

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index_pattern(
        self,
        record_id: str,
        features: Dict[str, float],
        outcome: str = "OPEN",
        profit: float = 0.0,
        regime: str = "UNKNOWN",
        market: str = "unknown",
        timestamp: float = 0.0,
    ) -> None:
        """Index a historical pattern for future similarity search."""
        vec = self._features_to_vector(features)

        if self._index.size() >= _MAX_INDEX_SIZE:
            # Evict oldest 10%
            evict_count = _MAX_INDEX_SIZE // 10
            self._index.clear()
            self._feature_matrix = self._feature_matrix[evict_count:]
            self._records = {k: v for k, v in self._records.items() if k >= evict_count}
            for idx, (rid, rec) in enumerate(self._records.items()):
                self._index.add(self._feature_matrix[idx], rid)

        idx = len(self._feature_matrix)
        self._feature_matrix.append(vec)
        self._records[idx] = {
            "record_id": record_id,
            "features": features,
            "outcome": outcome,
            "profit": profit,
            "regime": regime,
            "market": market,
            "timestamp": timestamp or time.time(),
        }
        self._index.add(vec, record_id)
        self._total_indexed += 1

    def search(
        self,
        query_features: Dict[str, float],
        top_k: int = _DEFAULT_TOP_K,
        min_similarity: float = _MIN_SIMILARITY,
        regime_filter: Optional[str] = None,
        market_filter: Optional[str] = None,
    ) -> List[SearchResult]:
        """Find the top_k most similar historical patterns."""
        self._total_queries += 1
        query_vec = self._features_to_vector(query_features)

        candidates = self._index.query(query_vec, top_k=top_k * 3)

        results: List[SearchResult] = []
        for idx, cos_sim in candidates:
            if idx not in self._records:
                continue
            rec = self._records[idx]

            # Apply filters
            if regime_filter and rec["regime"].upper() != regime_filter.upper():
                continue
            if market_filter and rec["market"] != market_filter:
                continue

            # Temporal decay
            age_hours = (time.time() - rec["timestamp"]) / 3600.0
            decay = math.exp(-_TEMPORAL_DECAY_LAMBDA * age_hours)
            adjusted_sim = cos_sim * decay

            if adjusted_sim < min_similarity:
                continue

            results.append(SearchResult(
                record_id=rec["record_id"],
                market=rec["market"],
                similarity=adjusted_sim,
                features=rec["features"],
                outcome=rec["outcome"],
                profit=rec["profit"],
                regime=rec["regime"],
                timestamp=rec["timestamp"],
            ))

        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:top_k]

    def search_cross_market(
        self,
        query_features: Dict[str, float],
        source_market: str,
        top_k: int = _DEFAULT_TOP_K,
    ) -> List[SearchResult]:
        """Search for patterns in OTHER markets that match the query.

        Useful for transferring insights from one instrument to another.
        """
        self._total_queries += 1
        query_vec = self._features_to_vector(query_features)
        candidates = self._index.query(query_vec, top_k=top_k * 5)

        results: List[SearchResult] = []
        for idx, cos_sim in candidates:
            if idx not in self._records:
                continue
            rec = self._records[idx]
            if rec["market"] == source_market:
                continue  # skip same market

            if cos_sim < _MIN_SIMILARITY:
                continue

            results.append(SearchResult(
                record_id=rec["record_id"],
                market=rec["market"],
                similarity=cos_sim,
                features=rec["features"],
                outcome=rec["outcome"],
                profit=rec["profit"],
                regime=rec["regime"],
                timestamp=rec["timestamp"],
            ))

        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:top_k]

    def get_outcome_statistics(self, results: List[SearchResult]) -> Dict[str, Any]:
        """Compute aggregate statistics from search results."""
        if not results:
            return {
                "count": 0, "win_rate": 0.0, "avg_profit": 0.0,
                "avg_similarity": 0.0, "regime_distribution": {},
            }

        wins = sum(1 for r in results if r.outcome == "WIN")
        profits = [r.profit for r in results]
        sims = [r.similarity for r in results]

        regime_dist: Dict[str, int] = defaultdict(int)
        for r in results:
            regime_dist[r.regime] += 1

        return {
            "count": len(results),
            "win_rate": round(wins / len(results), 4),
            "avg_profit": round(float(np.mean(profits)), 4),
            "avg_similarity": round(float(np.mean(sims)), 4),
            "profit_std": round(float(np.std(profits)), 4) if len(profits) > 1 else 0.0,
            "regime_distribution": dict(regime_dist),
        }

    def get_search_stats(self) -> Dict[str, Any]:
        """Engine-level statistics."""
        return {
            "total_indexed": self._total_indexed,
            "index_size": self._index.size(),
            "total_queries": self._total_queries,
            "n_clusters": len(self._pattern_clusters),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Serialise the search index to disk."""
        state = {
            "feature_matrix": [v.tolist() for v in self._feature_matrix],
            "records": self._records,
            "total_indexed": self._total_indexed,
            "total_queries": self._total_queries,
        }
        joblib.dump(state, path)
        logger.info("SimilaritySearch saved to %s (%d records)", path, self._index.size())

    def load(self, path: str) -> bool:
        """Restore the search index from disk."""
        try:
            state = joblib.load(path)
            self._feature_matrix = [np.array(v, dtype=np.float64) for v in state["feature_matrix"]]
            self._records = state["records"]
            self._total_indexed = state["total_indexed"]
            self._total_queries = state.get("total_queries", 0)
            # Rebuild LSH index
            self._index = _SimHashIndex(dim=_FEATURE_DIMS)
            for idx, vec in enumerate(self._feature_matrix):
                rid = self._records.get(idx, {}).get("record_id", str(idx))
                self._index.add(vec, rid)
            logger.info("SimilaritySearch loaded from %s (%d records)", path, self._index.size())
            return True
        except Exception as exc:
            logger.error("Failed to load SimilaritySearch: %s", exc)
            return False
