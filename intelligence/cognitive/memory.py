"""
Layer 3 — Memory
=================

Retrieves similar historical situations, ranks them by similarity and relevance,
and summarizes historical outcomes.
"""

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .perception import PerceptionResult
from .situation import SituationResult, MarketRegime, TrendDirection

logger = logging.getLogger(__name__)


@dataclass
class HistoricalSituation:
    """A historical market situation"""
    id: str
    timestamp: datetime
    symbol: str
    regime: str
    trend: str
    volatility: float
    uncertainty: float
    price_at_time: float
    features: Dict[str, float]  # Vector of features for similarity
    outcome: str  # SUCCESS, PARTIAL, FAILURE, NO_TRADE
    pnl: float
    confidence: float
    lessons: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "regime": self.regime,
            "trend": self.trend,
            "volatility": self.volatility,
            "uncertainty": self.uncertainty,
            "price_at_time": self.price_at_time,
            "outcome": self.outcome,
            "pnl": self.pnl,
            "confidence": self.confidence,
            "lessons": self.lessons
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoricalSituation":
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            symbol=data["symbol"],
            regime=data["regime"],
            trend=data["trend"],
            volatility=data["volatility"],
            uncertainty=data["uncertainty"],
            price_at_time=data["price_at_time"],
            features=data["features"],
            outcome=data["outcome"],
            pnl=data["pnl"],
            confidence=data["confidence"],
            lessons=data.get("lessons", [])
        )


@dataclass
class MemoryResult:
    """Result from memory retrieval layer"""
    session_id: str
    timestamp: datetime
    query_situation: Dict[str, Any]  # The situation we queried for
    retrieved_situations: List[HistoricalSituation]
    ranked_situations: List[Tuple[HistoricalSituation, float]]  # (situation, similarity_score)
    similar_situations_summary: str
    outcome_distribution: Dict[str, int]  # Count of each outcome type
    expected_outcome: float  # Expected PnL based on history
    outcome_confidence: float  # Confidence in expected outcome
    applicable_lessons: List[str]
    is_sufficient_context: bool  # Whether we have enough historical context
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "query_situation": self.query_situation,
            "retrieved_count": len(self.retrieved_situations),
            "top_similar": [
                {"id": s.id, "similarity": sim, "outcome": s.outcome, "pnl": s.pnl}
                for s, sim in self.ranked_situations[:5]
            ],
            "summary": self.similar_situations_summary,
            "outcome_distribution": self.outcome_distribution,
            "expected_outcome": self.expected_outcome,
            "outcome_confidence": self.outcome_confidence,
            "lessons": self.applicable_lessons,
            "sufficient_context": self.is_sufficient_context,
            "confidence": self.confidence
        }


class MemoryLayer:
    """
    Layer 3: Memory
    
    Responsible for:
    - Retrieving similar historical situations
    - Ranking by similarity and relevance
    - Summarizing historical outcomes
    """
    
    def __init__(
        self,
        db_path: str = "data/cognitive_memory.db",
        max_retrieved: int = 50,
        min_similarity: float = 0.5,
        relevance_weights: Optional[Dict[str, float]] = None
    ):
        self.db_path = db_path
        self.max_retrieved = max_retrieved
        self.min_similarity = min_similarity
        self.relevance_weights = relevance_weights or {
            "regime": 0.3,
            "volatility": 0.2,
            "uncertainty": 0.15,
            "trend": 0.2,
            "recency": 0.15
        }
        
        self._ensure_database()
        self._in_memory_cache: Dict[str, List[HistoricalSituation]] = {}
        
    def _ensure_database(self) -> None:
        """Ensure database exists and is initialized"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS situations (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                regime TEXT NOT NULL,
                trend TEXT NOT NULL,
                volatility REAL NOT NULL,
                uncertainty REAL NOT NULL,
                price_at_time REAL NOT NULL,
                features TEXT NOT NULL,
                outcome TEXT NOT NULL,
                pnl REAL NOT NULL,
                confidence REAL NOT NULL,
                lessons TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON situations(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_regime ON situations(symbol, regime)
        """)
        
        conn.commit()
        conn.close()
        
    def process(
        self,
        situation_result: SituationResult,
        perception_result: PerceptionResult,
        symbol: str
    ) -> MemoryResult:
        """
        Retrieve similar historical situations.
        
        Args:
            situation_result: Result from situation assessment
            perception_result: Result from perception layer
            symbol: Trading symbol
            
        Returns:
            MemoryResult with retrieved situations and analysis
        """
        # Build query features
        query_features = self._build_query_features(situation_result, perception_result)
        
        # Retrieve similar situations
        retrieved = self._retrieve_similar(query_features, symbol)
        
        # Rank by similarity
        ranked = self._rank_by_similarity(query_features, retrieved)
        
        # Calculate outcome distribution
        outcome_dist = self._calculate_outcome_distribution(ranked)
        
        # Calculate expected outcome
        expected_outcome, outcome_confidence = self._calculate_expected_outcome(ranked)
        
        # Get applicable lessons
        lessons = self._extract_applicable_lessons(ranked)
        
        # Generate summary
        summary = self._generate_summary(ranked, outcome_dist, expected_outcome)
        
        # Check if we have sufficient context
        sufficient_context = len(ranked) >= 5 and outcome_confidence > 0.5
        
        # Calculate overall confidence
        confidence = min(1.0, len(ranked) / 10) * outcome_confidence
        
        result = MemoryResult(
            session_id=situation_result.session_id,
            timestamp=datetime.now(),
            query_situation=query_features,
            retrieved_situations=[s for s, _ in ranked],
            ranked_situations=ranked,
            similar_situations_summary=summary,
            outcome_distribution=outcome_dist,
            expected_outcome=expected_outcome,
            outcome_confidence=outcome_confidence,
            applicable_lessons=lessons,
            is_sufficient_context=sufficient_context,
            confidence=confidence,
            metadata={
                "retrieval_method": "feature_similarity",
                "min_similarity_threshold": self.min_similarity
            }
        )
        
        logger.debug(f"Memory: retrieved {len(ranked)} situations, expected_outcome={expected_outcome:.4f}")
        return result
    
    def _build_query_features(
        self,
        situation: SituationResult,
        perception: PerceptionResult
    ) -> Dict[str, Any]:
        """Build feature vector for similarity search"""
        current_tick = perception.current_tick
        
        return {
            "regime": situation.regime.value,
            "trend": situation.trend.value,
            "volatility": situation.volatility,
            "uncertainty": situation.uncertainty,
            "regime_confidence": situation.regime_confidence,
            "trend_confidence": situation.trend_confidence,
            "price": current_tick.mid_price if current_tick else 0,
            "spread": current_tick.spread if current_tick else 0,
            "timestamp": datetime.now().isoformat(),
            "symbol": perception.current_tick.symbol if perception.current_tick else "UNKNOWN"
        }
    
    def _retrieve_similar(
        self,
        query_features: Dict[str, Any],
        symbol: str
    ) -> List[HistoricalSituation]:
        """Retrieve similar situations from database"""
        # Check cache first
        cache_key = f"{symbol}_{query_features['regime']}"
        if cache_key in self._in_memory_cache:
            return self._in_memory_cache[cache_key]
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Simple query - get recent situations for this symbol and regime
        cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
        
        cursor.execute("""
            SELECT * FROM situations
            WHERE symbol = ? AND regime = ? AND timestamp > ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (symbol, query_features["regime"], cutoff_date, self.max_retrieved))
        
        rows = cursor.fetchall()
        conn.close()
        
        situations = []
        for row in rows:
            try:
                features = json.loads(row["features"])
                situations.append(HistoricalSituation(
                    id=row["id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    symbol=row["symbol"],
                    regime=row["regime"],
                    trend=row["trend"],
                    volatility=row["volatility"],
                    uncertainty=row["uncertainty"],
                    price_at_time=row["price_at_time"],
                    features=features,
                    outcome=row["outcome"],
                    pnl=row["pnl"],
                    confidence=row["confidence"],
                    lessons=json.loads(row["lessons"])
                ))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse situation {row['id']}: {e}")
        
        # Cache results
        self._in_memory_cache[cache_key] = situations
        
        return situations
    
    def _rank_by_similarity(
        self,
        query_features: Dict[str, Any],
        situations: List[HistoricalSituation]
    ) -> List[Tuple[HistoricalSituation, float]]:
        """Rank situations by similarity to current query"""
        scored = []
        
        for situation in situations:
            similarity = self._calculate_similarity(query_features, situation)
            if similarity >= self.min_similarity:
                scored.append((situation, similarity))
        
        # Sort by similarity (descending)
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored
    
    def _calculate_similarity(
        self,
        query: Dict[str, Any],
        situation: HistoricalSituation
    ) -> float:
        """Calculate similarity between query and historical situation"""
        weights = self.relevance_weights
        scores = []
        
        # Regime match (exact match)
        regime_score = 1.0 if query["regime"] == situation.regime else 0.0
        scores.append(("regime", regime_score, weights["regime"]))
        
        # Volatility similarity
        vol_diff = abs(query["volatility"] - situation.volatility)
        vol_score = 1.0 - min(1.0, vol_diff)
        scores.append(("volatility", vol_score, weights["volatility"]))
        
        # Uncertainty similarity
        unc_diff = abs(query["uncertainty"] - situation.uncertainty)
        unc_score = 1.0 - min(1.0, unc_diff)
        scores.append(("uncertainty", unc_score, weights["uncertainty"]))
        
        # Trend match
        trend_score = 1.0 if query["trend"] == situation.trend else 0.0
        scores.append(("trend", trend_score, weights["trend"]))
        
        # Recency (more recent = higher score)
        days_old = (datetime.now() - situation.timestamp).days
        recency_score = max(0, 1.0 - (days_old / 30))
        scores.append(("recency", recency_score, weights["recency"]))
        
        # Weighted average
        total_score = sum(score * weight for _, score, weight in scores)
        total_weight = sum(weight for _, _, weight in scores)
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _calculate_outcome_distribution(
        self,
        ranked: List[Tuple[HistoricalSituation, float]]
    ) -> Dict[str, int]:
        """Calculate distribution of outcomes in similar situations"""
        distribution = {"SUCCESS": 0, "PARTIAL": 0, "FAILURE": 0, "NO_TRADE": 0}
        
        for situation, similarity in ranked[:10]:  # Top 10 most similar
            if situation.outcome in distribution:
                distribution[situation.outcome] += 1
        
        return distribution
    
    def _calculate_expected_outcome(
        self,
        ranked: List[Tuple[HistoricalSituation, float]]
    ) -> Tuple[float, float]:
        """Calculate expected PnL and confidence"""
        if not ranked:
            return 0.0, 0.0
        
        # Weight by similarity
        weighted_pnl = 0.0
        total_weight = 0.0
        
        for situation, similarity in ranked[:10]:
            weight = similarity
            weighted_pnl += situation.pnl * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0, 0.0
        
        expected = weighted_pnl / total_weight
        
        # Calculate confidence based on consistency of outcomes
        pnls = [s.pnl for s, _ in ranked[:10]]
        if len(pnls) > 1:
            std = np.std(pnls)
            mean = np.mean(pnls)
            # Lower std = higher confidence
            confidence = 1.0 - min(1.0, std / (abs(mean) + 0.01) if mean != 0 else 1.0)
        else:
            confidence = 0.5
        
        return expected, max(0.0, min(1.0, confidence))
    
    def _extract_applicable_lessons(
        self,
        ranked: List[Tuple[HistoricalSituation, float]]
    ) -> List[str]:
        """Extract lessons from similar situations"""
        lessons = []
        
        for situation, similarity in ranked[:5]:
            for lesson in situation.lessons:
                if lesson not in lessons:
                    lessons.append(lesson)
        
        return lessons[:10]  # Limit to top 10 lessons
    
    def _generate_summary(
        self,
        ranked: List[Tuple[HistoricalSituation, float]],
        outcome_dist: Dict[str, int],
        expected_outcome: float
    ) -> str:
        """Generate natural language summary"""
        if not ranked:
            return "No similar historical situations found."
        
        total = sum(outcome_dist.values())
        if total == 0:
            return "Insufficient data for outcome analysis."
        
        success_rate = outcome_dist["SUCCESS"] / total
        failure_rate = outcome_dist["FAILURE"] / total
        
        summary_parts = []
        
        if len(ranked) >= 5:
            summary_parts.append(f"Found {len(ranked)} similar situations in recent history.")
        else:
            summary_parts.append(f"Limited historical context with only {len(ranked)} similar situations.")
        
        if success_rate > 0.6:
            summary_parts.append("Historically favorable conditions with >60% success rate.")
        elif failure_rate > 0.5:
            summary_parts.append("Historically challenging conditions with elevated failure risk.")
        else:
            summary_parts.append("Mixed historical outcomes with uncertain conditions.")
        
        if expected_outcome > 0:
            summary_parts.append(f"Expected outcome is positive (${expected_outcome:.2f} per unit).")
        elif expected_outcome < 0:
            summary_parts.append(f"Expected outcome is negative (${expected_outcome:.2f} per unit).")
        
        return " ".join(summary_parts)
    
    def store_situation(
        self,
        situation: SituationResult,
        perception: PerceptionResult,
        outcome: str,
        pnl: float,
        confidence: float,
        lessons: List[str]
    ) -> str:
        """
        Store a completed situation for future reference.
        
        Args:
            situation: The situation that was assessed
            perception: The perception result
            outcome: Outcome (SUCCESS, PARTIAL, FAILURE, NO_TRADE)
            pnl: Profit/loss from the trade
            confidence: Confidence level of the decision
            lessons: List of learned lessons
            
        Returns:
            ID of the stored situation
        """
        situation_id = str(uuid4())
        current_tick = perception.current_tick
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        features = {
            "regime": situation.regime.value,
            "trend": situation.trend.value,
            "volatility": situation.volatility,
            "uncertainty": situation.uncertainty,
            "price": current_tick.mid_price if current_tick else 0,
            "transition_detected": situation.regime_transition_detected
        }
        
        cursor.execute("""
            INSERT INTO situations (
                id, timestamp, symbol, regime, trend, volatility, uncertainty,
                price_at_time, features, outcome, pnl, confidence, lessons
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            situation_id,
            datetime.now().isoformat(),
            current_tick.symbol if current_tick else "UNKNOWN",
            situation.regime.value,
            situation.trend.value,
            situation.volatility,
            situation.uncertainty,
            current_tick.mid_price if current_tick else 0,
            json.dumps(features),
            outcome,
            pnl,
            confidence,
            json.dumps(lessons)
        ))
        
        conn.commit()
        conn.close()
        
        # Clear relevant cache
        cache_key = f"{current_tick.symbol}_{situation.regime.value}"
        if cache_key in self._in_memory_cache:
            del self._in_memory_cache[cache_key]
        
        logger.info(f"Stored situation {situation_id} with outcome {outcome}")
        return situation_id
    
    def reset(self) -> None:
        """Reset memory layer state"""
        self._in_memory_cache.clear()
        logger.info("Memory layer reset")


