"""
Case-Based Reasoning — retrieves the most similar historical market situations
before every decision, enabling the system to learn from analogous past trades.

Uses weighted cosine similarity across discretised feature dimensions:
entropy, volatility, digit_pattern, analyzer_agreement, and regime.
"""
import time
import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

_SIMILARITY_WEIGHTS = {
    "entropy": 0.25,
    "volatility": 0.25,
    "digit_pattern": 0.15,
    "analyzer_agreement": 0.20,
    "regime": 0.15,
}

_REGIME_ENCODE = {
    "trending": np.array([1, 0, 0, 0], dtype=np.float64),
    "ranging": np.array([0, 1, 0, 0], dtype=np.float64),
    "volatile": np.array([0, 0, 1, 0], dtype=np.float64),
    "quiet": np.array([0, 0, 0, 1], dtype=np.float64),
}


@dataclass
class SimilarCase:
    """A single historical case returned by similarity retrieval."""

    case_id: str
    similarity_score: float
    trade_record: Any
    outcome: str
    profit: float
    key_factors: List[str]
    timestamp: float


def _safe_cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity that returns 0 for degenerate vectors."""
    dot = float(np.dot(a, b))
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def _encode_regime(regime: str) -> np.ndarray:
    key = regime.lower() if regime else "ranging"
    return _REGIME_ENCODE.get(key, np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64))


def _build_feature_vector(features: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """Convert a raw feature dict into per-dimension numpy vectors."""
    entropy_val = float(features.get("entropy", 0.0))
    volatility_val = float(features.get("volatility", 0.0))
    digit_pattern_val = float(features.get("digit_pattern", 0.0))
    agreement_val = float(features.get("analyzer_agreement", 0.5))
    regime_str = features.get("regime", "ranging")

    return {
        "entropy": np.array([entropy_val], dtype=np.float64),
        "volatility": np.array([volatility_val], dtype=np.float64),
        "digit_pattern": np.array([digit_pattern_val], dtype=np.float64),
        "analyzer_agreement": np.array([agreement_val], dtype=np.float64),
        "regime": _encode_regime(regime_str),
    }


def _compute_similarity(
    current_vecs: Dict[str, np.ndarray],
    case_vecs: Dict[str, np.ndarray],
) -> float:
    """Weighted cosine similarity between two feature representations."""
    total = 0.0
    for dim, weight in _SIMILARITY_WEIGHTS.items():
        cos = _safe_cosine(current_vecs[dim], case_vecs[dim])
        total += weight * cos
    return round(total, 6)


def _extract_key_factors(
    current: Dict[str, Any],
    case_features: Dict[str, Any],
) -> List[str]:
    """Return human-readable labels for the dimensions that contributed most."""
    contributions: List[tuple] = []
    for dim, weight in _SIMILARITY_WEIGHTS.items():
        cur_val = current.get(dim, 0)
        cas_val = case_features.get(dim, 0)
        if dim == "regime":
            diff = 0.0 if str(cur_val).lower() == str(cas_val).lower() else 1.0
        else:
            diff = abs(float(cur_val) - float(cas_val))
        contributions.append((dim, weight * (1.0 - min(diff, 1.0))))
    contributions.sort(key=lambda x: x[1], reverse=True)
    return [dim for dim, _ in contributions[:3]]


class CaseBasedReasoner:
    """Historical-similarity retrieval and evaluation engine.

    Maintains an in-memory case base built from completed trades stored in
    the ``TradeMemory`` feature store.  Before each new decision the caller
    supplies a feature snapshot; the reasoner returns the *N* most similar
    historical cases together with aggregate statistics.
    """

    def __init__(self, trade_memory: Any) -> None:
        """Initialise the reasoner.

        Parameters
        ----------
        trade_memory:
            An instance of ``intelligence.trade_memory.TradeMemory`` (or any
            object exposing ``get_completed_trades()`` → list of
            ``TradeRecord`` instances).
        """
        self._memory = trade_memory
        self._case_index: List[Dict[str, Any]] = []
        self._vector_cache: List[Dict[str, np.ndarray]] = []
        self._retrieval_count = 0
        self._hit_count = 0
        self._total_similarity_score = 0.0
        self._prediction_correct = 0
        self._prediction_total = 0
        logger.info("CaseBasedReasoner initialised with trade_memory=%s", type(trade_memory).__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        current_features: Dict[str, Any],
        market: str,
        regime: str,
        n: int = 5,
    ) -> List[SimilarCase]:
        """Return the *n* most similar historical cases.

        Parameters
        ----------
        current_features : dict
            Feature snapshot for the current market state.  Expected keys:
            ``entropy``, ``volatility``, ``digit_pattern``,
            ``analyzer_agreement``, ``regime``.
        market : str
            Market identifier (e.g. ``"Volatility 75"``).  Used to filter
            the case base to the same market when possible.
        regime : str
            Current regime label.
        n : int
            Number of similar cases to return.

        Returns
        -------
        list[SimilarCase]
            Sorted by descending similarity score.
        """
        self._ensure_indexed()
        self._retrieval_count += 1

        if not self._case_index:
            logger.debug("Case base empty — returning no similar cases")
            return []

        current_vecs = _build_feature_vector(current_features)

        scored: List[SimilarCase] = []
        for idx, case in enumerate(self._case_index):
            case_features = case.get("features", {})
            case_vecs = self._vector_cache[idx]
            score = _compute_similarity(current_vecs, case_vecs)

            trade_record = case.get("trade_record")
            profit = float(getattr(trade_record, "profit", 0) or 0)
            outcome = "win" if profit > 0 else "loss"
            factors = _extract_key_factors(current_features, case_features)

            scored.append(
                SimilarCase(
                    case_id=str(case.get("case_id", idx)),
                    similarity_score=score,
                    trade_record=trade_record,
                    outcome=outcome,
                    profit=profit,
                    key_factors=factors,
                    timestamp=float(case.get("timestamp", 0.0)),
                )
            )

        scored.sort(key=lambda c: c.similarity_score, reverse=True)
        top = scored[:n]

        if top:
            self._hit_count += 1
            self._total_similarity_score += top[0].similarity_score

        logger.debug(
            "Retrieved %d similar cases (best=%.4f) for market=%s regime=%s",
            len(top),
            top[0].similarity_score if top else 0.0,
            market,
            regime,
        )
        return top

    def evaluate(self, current_features: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate the current situation against the case base.

        Returns a dict with aggregate statistics from the similar cases
        and a confidence modifier / recommendation.
        """
        self._ensure_indexed()
        default = {
            "win_rate_in_similar": 0.0,
            "avg_profit_in_similar": 0.0,
            "confidence_modifier": 0.0,
            "recommendation": "INSUFFICIENT_DATA",
        }

        similar = self.retrieve(current_features, market="", regime="", n=5)
        if not similar:
            return default

        wins = sum(1 for c in similar if c.outcome == "win")
        win_rate = wins / len(similar)
        avg_profit = sum(c.profit for c in similar) / len(similar)

        high_similarity = similar[0].similarity_score > 0.80
        if high_similarity and win_rate >= 0.70:
            modifier = 0.05
            recommendation = "STRONG_TRADE"
        elif high_similarity and win_rate >= 0.50:
            modifier = 0.02
            recommendation = "MODERATE_TRADE"
        elif high_similarity and win_rate < 0.40:
            modifier = -0.05
            recommendation = "ABSTAIN"
        else:
            modifier = 0.0
            recommendation = "NEUTRAL"

        return {
            "win_rate_in_similar": round(win_rate, 4),
            "avg_profit_in_similar": round(avg_profit, 4),
            "confidence_modifier": round(modifier, 4),
            "recommendation": recommendation,
        }

    def index_new_case(self, trade_record: Any) -> None:
        """Add a completed trade to the case base.

        Parameters
        ----------
        trade_record : TradeRecord
            A completed trade with feature metadata attached.
        """
        features = getattr(trade_record, "features", None) or {}
        if not features:
            logger.debug("Trade record has no features — skipping indexing")
            return

        entry = {
            "case_id": getattr(trade_record, "trade_id", str(len(self._case_index))),
            "features": features,
            "trade_record": trade_record,
            "timestamp": float(getattr(trade_record, "timestamp", time.time())),
        }
        self._case_index.append(entry)
        self._vector_cache.append(_build_feature_vector(features))
        logger.debug("Indexed new case id=%s (total=%d)", entry["case_id"], len(self._case_index))

    def prune_old_cases(self, max_cases: int = 10000) -> int:
        """Remove oldest cases when the case base exceeds *max_cases*.

        Returns the number of cases removed.
        """
        if len(self._case_index) <= max_cases:
            return 0

        excess = len(self._case_index) - max_cases
        self._case_index = self._case_index[excess:]
        self._vector_cache = self._vector_cache[excess:]
        logger.info("Pruned %d old cases from case base", excess)
        return excess

    def get_case_stats(self) -> Dict[str, Any]:
        """Return retrieval statistics and accuracy information."""
        avg_sim = (
            self._total_similarity_score / self._hit_count
            if self._hit_count > 0
            else 0.0
        )
        hit_rate = (
            self._hit_count / self._retrieval_count
            if self._retrieval_count > 0
            else 0.0
        )
        prediction_accuracy = (
            self._prediction_correct / self._prediction_total
            if self._prediction_total > 0
            else 0.0
        )
        return {
            "case_base_size": len(self._case_index),
            "total_retrievals": self._retrieval_count,
            "hit_rate": round(hit_rate, 4),
            "avg_top_similarity": round(avg_sim, 6),
            "prediction_accuracy": round(prediction_accuracy, 4),
            "predictions_made": self._prediction_total,
            "predictions_correct": self._prediction_correct,
        }

    def record_prediction(self, predicted_outcome: str, actual_outcome: str) -> None:
        """Track whether a similarity-based prediction was correct."""
        self._prediction_total += 1
        if predicted_outcome == actual_outcome:
            self._prediction_correct += 1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_indexed(self) -> None:
        """Lazily populate the case index from TradeMemory."""
        if self._case_index:
            return
        try:
            completed = self._memory.get_completed_trades()
        except AttributeError:
            logger.warning("trade_memory object lacks get_completed_trades()")
            return
        except Exception as exc:
            logger.error("Failed to load completed trades: %s", exc)
            return

        for record in completed:
            self.index_new_case(record)
        if self._case_index:
            logger.info("Loaded %d historical cases into CBR index", len(self._case_index))
