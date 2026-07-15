"""
AI Explainability Search - Search Historical Explanations

Provides full-text and structured search for historical AI decision explanations.
"""

import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Iterator
from enum import Enum

logger = logging.getLogger(__name__)


class SortField(Enum):
    """Fields to sort by"""
    TIMESTAMP = "timestamp"
    CONFIDENCE = "confidence"
    EXPECTED_VALUE = "expected_value"
    RISK_SCORE = "risk_score"


class SortOrder(Enum):
    """Sort order"""
    ASC = "asc"
    DESC = "desc"


@dataclass
class SearchQuery:
    """Structured search query for explanations"""
    # Text search
    text_query: str = ""  # Full-text search across all fields
    
    # Filters
    action: Optional[str] = None  # BUY, SELL, HOLD, SKIP
    symbol: Optional[str] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
    min_expected_value: Optional[float] = None
    max_expected_value: Optional[float] = None
    risk_level: Optional[str] = None  # LOW, MEDIUM, HIGH, CRITICAL
    
    # Date range
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    
    # Analyzer filters
    analyzers: List[str] = field(default_factory=list)  # Must include these analyzers
    analyzer_signal: Optional[str] = None  # Specific signal from any analyzer
    
    # Market regime
    market_regime: Optional[str] = None
    
    # Decision outcome (if available)
    profitable_only: bool = False
    
    # Pagination
    limit: int = 50
    offset: int = 0
    
    # Sorting
    sort_by: SortField = SortField.TIMESTAMP
    sort_order: SortOrder = SortOrder.DESC


@dataclass
class SearchResult:
    """Search result with relevance scoring"""
    explanation_id: str
    decision_id: str
    timestamp: str
    action: str
    symbol: str
    confidence: float
    risk_level: str
    expected_value: float
    relevance_score: float
    match_highlights: List[str]  # Text snippets showing matches
    
    # Brief summary for quick viewing
    summary: str


class ExplanationSearch:
    """
    Search engine for AI decision explanations.
    
    Supports:
    - Full-text search across all explanation content
    - Structured filtering by any field
    - Date range queries
    - Analyzer-specific searches
    - Relevance-ranked results
    """
    
    def __init__(self, storage):
        """
        Initialize search engine.
        
        Args:
            storage: ExplanationStorage instance
        """
        self.storage = storage
        self.logger = logging.getLogger(f"{__name__}.Search")
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Execute search query and return results.
        
        Args:
            query: SearchQuery with filters and options
            
        Returns:
            List of SearchResult objects sorted by relevance
        """
        results = []
        
        # Get all matching explanations (using storage's iteration)
        for explanation in self._iterate_matching(query):
            score, highlights = self._calculate_relevance(explanation, query)
            
            if score > 0:
                result = SearchResult(
                    explanation_id=explanation.get("explanation_id", ""),
                    decision_id=explanation.get("decision_id", ""),
                    timestamp=explanation.get("timestamp", ""),
                    action=explanation.get("action", ""),
                    symbol=explanation.get("symbol", ""),
                    confidence=explanation.get("confidence", 0),
                    risk_level=explanation.get("risk_level", ""),
                    expected_value=explanation.get("expected_value", 0),
                    relevance_score=score,
                    match_highlights=highlights,
                    summary=explanation.get("executive_summary", {}).get("summary", ""),
                )
                results.append(result)
        
        # Sort results
        results = self._sort_results(results, query.sort_by, query.sort_order)
        
        # Apply pagination
        return results[query.offset:query.offset + query.limit]
    
    def _iterate_matching(self, query: SearchQuery) -> Iterator[Dict[str, Any]]:
        """Iterate through explanations matching the query filters"""
        
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build SQL query
            sql_parts = ["SELECT * FROM explanations WHERE 1=1"]
            params = []
            
            # Action filter
            if query.action:
                sql_parts.append("AND action = ?")
                params.append(query.action)
            
            # Symbol filter
            if query.symbol:
                sql_parts.append("AND symbol = ?")
                params.append(query.symbol)
            
            # Confidence range
            if query.min_confidence is not None:
                sql_parts.append("AND confidence >= ?")
                params.append(query.min_confidence)
            
            if query.max_confidence is not None:
                sql_parts.append("AND confidence <= ?")
                params.append(query.max_confidence)
            
            # Expected value range
            if query.min_expected_value is not None:
                sql_parts.append("AND expected_value >= ?")
                params.append(query.min_expected_value)
            
            if query.max_expected_value is not None:
                sql_parts.append("AND expected_value <= ?")
                params.append(query.max_expected_value)
            
            # Risk level
            if query.risk_level:
                sql_parts.append("AND risk_level = ?")
                params.append(query.risk_level)
            
            # Date range
            if query.since:
                sql_parts.append("AND timestamp >= ?")
                params.append(query.since.isoformat())
            
            if query.until:
                sql_parts.append("AND timestamp <= ?")
                params.append(query.until.isoformat())
            
            # Market regime
            if query.market_regime:
                sql_parts.append("AND market_regime = ?")
                params.append(query.market_regime)
            
            # Order by timestamp desc (most recent first)
            sql_parts.append("ORDER BY timestamp DESC")
            
            sql = " ".join(sql_parts)
            cursor.execute(sql, params)
            
            for row in cursor.fetchall():
                explanation = dict(row)
                
                # Parse JSON fields
                for json_field in [
                    "beginner_json", "advanced_json", "developer_json", 
                    "researcher_json", "executive_summary_json",
                    "evidence_chain_json", "raw_data_json"
                ]:
                    if explanation.get(json_field):
                        field_name = json_field.replace("_json", "")
                        try:
                            explanation[field_name] = json.loads(explanation[json_field])
                        except json.JSONDecodeError:
                            pass
                
                # Filter by text query if present
                if query.text_query:
                    if not self._matches_text_query(explanation, query.text_query):
                        continue
                
                # Filter by analyzers if specified
                if query.analyzers:
                    signals = explanation.get("analyzer_signals", {})
                    if not all(a in signals for a in query.analyzers):
                        continue
                
                # Filter by analyzer signal if specified
                if query.analyzer_signal:
                    signals = explanation.get("analyzer_signals", {})
                    if not any(
                        query.analyzer_signal.lower() in str(s.get("prediction", "")).lower()
                        for s in signals.values()
                    ):
                        continue
                
                yield explanation
    
    def _matches_text_query(self, explanation: Dict[str, Any], text_query: str) -> bool:
        """Check if explanation matches text query"""
        text_query = text_query.lower()
        
        # Search in all text fields
        searchable_text = []
        
        # Executive summary
        exec_summary = explanation.get("executive_summary", {})
        searchable_text.append(str(exec_summary.get("summary", "")))
        searchable_text.append(str(exec_summary.get("why_opportunity_exists", "")))
        searchable_text.append(str(exec_summary.get("why_confidence_level", "")))
        
        # Beginner explanation
        beginner = explanation.get("beginner", {})
        searchable_text.append(str(beginner.get("what_happened", "")))
        searchable_text.append(str(beginner.get("why", "")))
        searchable_text.append(str(beginner.get("how_confident", "")))
        searchable_text.append(str(beginner.get("recommendation", "")))
        
        # Advanced explanation
        advanced = explanation.get("advanced", {})
        searchable_text.append(str(advanced.get("regime_interpretation", "")))
        
        # Developer explanation
        developer = explanation.get("developer", {})
        searchable_text.append(str(developer.get("decision_id", "")))
        
        # Action and symbol
        searchable_text.append(str(explanation.get("action", "")))
        searchable_text.append(str(explanation.get("symbol", "")))
        
        # Full text search
        full_text = " ".join(searchable_text).lower()
        return text_query in full_text
    
    def _calculate_relevance(
        self, 
        explanation: Dict[str, Any], 
        query: SearchQuery
    ) -> tuple[float, List[str]]:
        """
        Calculate relevance score for an explanation.
        
        Returns:
            Tuple of (relevance_score, match_highlights)
        """
        score = 0.0
        highlights = []
        
        # Text query matching
        if query.text_query:
            text_query = query.text_query.lower()
            
            # Check executive summary
            exec_summary = explanation.get("executive_summary", {})
            summary_text = str(exec_summary.get("summary", "")).lower()
            if text_query in summary_text:
                score += 5.0
                highlights.append(f"Summary: {exec_summary.get('summary', '')[:100]}...")
            
            # Check why explanations
            why_opportunity = str(exec_summary.get("why_opportunity_exists", "")).lower()
            if text_query in why_opportunity:
                score += 3.0
                highlights.append(f"Why: {why_opportunity[:100]}...")
            
            # Check beginner explanation
            beginner = explanation.get("beginner", {})
            for field in ["what_happened", "why", "how_confident"]:
                field_text = str(beginner.get(field, "")).lower()
                if text_query in field_text:
                    score += 2.0
                    highlights.append(f"{field}: {field_text[:80]}...")
        
        # Exact match bonuses
        if query.action and explanation.get("action") == query.action:
            score += 2.0
        
        if query.symbol and explanation.get("symbol") == query.symbol:
            score += 2.0
        
        # Confidence scoring
        if query.min_confidence and explanation.get("confidence", 0) >= query.min_confidence:
            score += 1.0
        
        # Relevance based on recency
        timestamp_str = explanation.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            days_ago = (datetime.utcnow() - timestamp).days
            if days_ago <= 1:
                score += 2.0
            elif days_ago <= 7:
                score += 1.0
        except (ValueError, TypeError):
            pass
        
        # Limit highlights
        highlights = highlights[:5]
        
        return score, highlights
    
    def _sort_results(
        self, 
        results: List[SearchResult], 
        sort_by: SortField, 
        sort_order: SortOrder
    ) -> List[SearchResult]:
        """Sort search results"""
        reverse = sort_order == SortOrder.DESC
        
        if sort_by == SortField.TIMESTAMP:
            return sorted(
                results, 
                key=lambda r: r.timestamp or "", 
                reverse=reverse
            )
        elif sort_by == SortField.CONFIDENCE:
            return sorted(
                results, 
                key=lambda r: r.confidence or 0, 
                reverse=reverse
            )
        elif sort_by == SortField.EXPECTED_VALUE:
            return sorted(
                results, 
                key=lambda r: r.expected_value or 0, 
                reverse=reverse
            )
        elif sort_by == SortField.RISK_SCORE:
            return sorted(
                results, 
                key=lambda r: self._risk_to_score(r.risk_level), 
                reverse=reverse
            )
        
        return results
    
    def _risk_to_score(self, risk_level: str) -> float:
        """Convert risk level to numeric score"""
        scores = {
            "LOW": 0.25,
            "MEDIUM": 0.5,
            "HIGH": 0.75,
            "CRITICAL": 1.0,
        }
        return scores.get(risk_level.upper(), 0.5)
    
    def search_by_text(self, text: str, limit: int = 20) -> List[SearchResult]:
        """
        Quick text-only search.
        
        Args:
            text: Search text
            limit: Maximum results
            
        Returns:
            List of SearchResult
        """
        query = SearchQuery(text_query=text, limit=limit)
        return self.search(query)
    
    def search_by_decision_outcome(
        self, 
        profitable_only: bool = True, 
        limit: int = 50
    ) -> List[SearchResult]:
        """
        Search by decision outcome.
        
        Note: This requires outcome data to be stored with explanations.
        """
        query = SearchQuery(profitable_only=profitable_only, limit=limit)
        return self.search(query)
    
    def get_explanations_by_analyzer(
        self, 
        analyzer_name: str, 
        signal: Optional[str] = None,
        limit: int = 50
    ) -> List[SearchResult]:
        """
        Get all explanations where a specific analyzer was involved.
        
        Args:
            analyzer_name: Name of the analyzer
            signal: Optional specific signal (e.g., "CALL", "PUT")
            limit: Maximum results
            
        Returns:
            List of SearchResult
        """
        query = SearchQuery(
            analyzers=[analyzer_name],
            analyzer_signal=signal,
            limit=limit
        )
        return self.search(query)
    
    def get_recent_decisions(
        self, 
        hours: int = 24, 
        action: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Get recent decisions within a time window.
        
        Args:
            hours: Number of hours to look back
            action: Optional filter by action
            
        Returns:
            List of SearchResult
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        query = SearchQuery(
            since=since,
            action=action,
            limit=100,
            sort_by=SortField.TIMESTAMP,
            sort_order=SortOrder.DESC
        )
        return self.search(query)
    
    def get_confidence_distribution(
        self, 
        bins: int = 10
    ) -> Dict[str, Any]:
        """
        Get distribution of confidence scores.
        
        Args:
            bins: Number of histogram bins
            
        Returns:
            Distribution data
        """
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT confidence FROM explanations 
                WHERE confidence IS NOT NULL
                ORDER BY confidence
            """)
            
            confidences = [row["confidence"] for row in cursor.fetchall()]
            
            if not confidences:
                return {"bins": [], "counts": [], "total": 0}
            
            # Create histogram
            min_val = min(confidences)
            max_val = max(confidences)
            bin_width = (max_val - min_val) / bins if bins > 0 else 1
            
            histogram = [0] * bins
            for c in confidences:
                bin_idx = min(int((c - min_val) / bin_width), bins - 1) if bin_width > 0 else 0
                histogram[bin_idx] += 1
            
            bin_edges = [min_val + i * bin_width for i in range(bins + 1)]
            
            return {
                "bins": bin_edges,
                "counts": histogram,
                "total": len(confidences),
                "mean": sum(confidences) / len(confidences),
                "min": min_val,
                "max": max_val,
            }
    
    def get_action_breakdown(
        self, 
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get breakdown of actions over time.
        
        Args:
            since: Only include decisions after this time
            
        Returns:
            Action statistics
        """
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT action, COUNT(*) as count, AVG(confidence) as avg_conf FROM explanations WHERE 1=1"
            params = []
            
            if since:
                query += " AND timestamp >= ?"
                params.append(since.isoformat())
            
            query += " GROUP BY action"
            
            cursor.execute(query, params)
            
            breakdown = {}
            for row in cursor.fetchall():
                breakdown[row["action"] or "UNKNOWN"] = {
                    "count": row["count"],
                    "avg_confidence": round(row["avg_conf"] or 0, 1),
                }
            
            return breakdown
