"""
AI Explainability Storage - Permanent Storage for Explanations

Provides permanent, searchable storage for all AI decision explanations.
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator

logger = logging.getLogger(__name__)


class ExplanationStorage:
    """
    Permanent storage for AI decision explanations.
    
    Stores explanations with full evidence chains for:
    - Regulatory compliance
    - Audit trail reconstruction
    - Historical analysis
    - Model improvement
    """
    
    def __init__(self, db_path: str = "ai_explanations.db"):
        """
        Initialize explanation storage.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._initialize_database()
        logger.info(f"ExplanationStorage initialized at {db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _initialize_database(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Main explanations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS explanations (
                    explanation_id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    generation_time_ms REAL,
                    
                    -- Summary fields (for quick queries)
                    action TEXT,
                    symbol TEXT,
                    confidence REAL,
                    risk_level TEXT,
                    expected_value REAL,
                    
                    -- Opportunity details
                    opportunity_type TEXT,
                    amount REAL,
                    
                    -- Market context
                    market_regime TEXT,
                    volatility REAL,
                    
                    -- Raw JSON storage (for full data)
                    beginner_json TEXT,
                    advanced_json TEXT,
                    developer_json TEXT,
                    researcher_json TEXT,
                    executive_summary_json TEXT,
                    evidence_chain_json TEXT,
                    raw_data_json TEXT,
                    
                    -- Metadata
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    version TEXT DEFAULT '1.0.0'
                )
            """)
            
            # Evidence chain table (normalized)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evidence_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    explanation_id TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    weight REAL,
                    data_json TEXT,
                    FOREIGN KEY (explanation_id) REFERENCES explanations(explanation_id)
                )
            """)
            
            # Analyzer signals table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analyzer_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    explanation_id TEXT NOT NULL,
                    analyzer_name TEXT NOT NULL,
                    prediction TEXT,
                    confidence REAL,
                    weight REAL,
                    reason TEXT,
                    data_json TEXT,
                    FOREIGN KEY (explanation_id) REFERENCES explanations(explanation_id)
                )
            """)
            
            # Alternative actions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alternative_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    explanation_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    expected_value REAL,
                    risk_score REAL,
                    rejection_reason TEXT,
                    similarity_to_chosen REAL,
                    FOREIGN KEY (explanation_id) REFERENCES explanations(explanation_id)
                )
            """)
            
            # Historical analogues table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historical_analogues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    explanation_id TEXT NOT NULL,
                    past_decision_id TEXT NOT NULL,
                    timestamp TEXT,
                    action TEXT,
                    confidence REAL,
                    outcome REAL,
                    similarity_score REAL,
                    market_conditions_json TEXT
                )
            """)
            
            # Feature importance table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feature_importance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    explanation_id TEXT NOT NULL,
                    feature_name TEXT NOT NULL,
                    importance REAL,
                    rank INTEGER,
                    FOREIGN KEY (explanation_id) REFERENCES explanations(explanation_id)
                )
            """)
            
            # Decision tree table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS decision_tree_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    explanation_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    step_description TEXT,
                    step_type TEXT,
                    FOREIGN KEY (explanation_id) REFERENCES explanations(explanation_id)
                )
            """)
            
            # Create indexes for efficient queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_timestamp ON explanations(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_decision_id ON explanations(decision_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_action ON explanations(action)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_symbol ON explanations(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_confidence ON explanations(confidence)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_exp_id ON evidence_items(explanation_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_exp_id ON analyzer_signals(explanation_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_features_exp_id ON feature_importance(explanation_id)")
    
    def _serialize_for_json(self, obj):
        """Helper to serialize objects for JSON"""
        # Handle enums
        if hasattr(obj, 'value'):
            return obj.value
        # Handle datetime
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def save_explanation(self, explanation) -> bool:
        """
        Save an explanation to permanent storage.
        
        Args:
            explanation: ExplanationResponse object to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Serialize timestamps
                timestamp_str = explanation.timestamp
                if hasattr(timestamp_str, 'isoformat'):
                    timestamp_str = timestamp_str.isoformat()
                
                # Insert main explanation record
                cursor.execute("""
                    INSERT OR REPLACE INTO explanations (
                        explanation_id, decision_id, timestamp, generation_time_ms,
                        action, symbol, confidence, risk_level, expected_value,
                        opportunity_type, amount, market_regime, volatility,
                        beginner_json, advanced_json, developer_json, researcher_json,
                        executive_summary_json, evidence_chain_json, raw_data_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    explanation.explanation_id,
                    explanation.decision_id,
                    timestamp_str,
                    explanation.generation_time_ms,
                    
                    # Summary fields
                    explanation.executive_summary.get("action", ""),
                    explanation.executive_summary.get("symbol", ""),
                    explanation.executive_summary.get("confidence", 0),
                    explanation.executive_summary.get("risk_level", ""),
                    explanation.executive_summary.get("expected_value", 0),
                    
                    # Opportunity details
                    "",  # opportunity_type
                    0,   # amount
                    "",  # market_regime
                    0,   # volatility
                    
                    # JSON storage (with datetime handling)
                    json.dumps(explanation.beginner, default=self._serialize_for_json),
                    json.dumps(explanation.advanced, default=self._serialize_for_json),
                    json.dumps(explanation.developer, default=self._serialize_for_json),
                    json.dumps(explanation.researcher, default=self._serialize_for_json),
                    json.dumps(explanation.executive_summary, default=self._serialize_for_json),
                    json.dumps(explanation.evidence_chain, default=self._serialize_for_json),
                    json.dumps(explanation.raw_data, default=self._serialize_for_json),
                ))
                
                # Insert evidence items
                for evidence in explanation.evidence_chain:
                    evidence_timestamp = evidence.get("timestamp", "")
                    if hasattr(evidence_timestamp, 'isoformat'):
                        evidence_timestamp = evidence_timestamp.isoformat()
                    
                    cursor.execute("""
                        INSERT INTO evidence_items (
                            explanation_id, evidence_type, timestamp, weight, data_json
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        explanation.explanation_id,
                        evidence.get("type", ""),
                        evidence_timestamp,
                        evidence.get("weight", 0),
                        json.dumps(evidence.get("data", {}), default=self._serialize_for_json),
                    ))
                
                logger.info(f"Saved explanation {explanation.explanation_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save explanation: {e}")
            return False
    
    def save_explanation_from_request(
        self, 
        explanation_id: str,
        decision_id: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> bool:
        """
        Save an explanation from request/response data.
        
        Args:
            explanation_id: Unique explanation ID
            decision_id: Related decision ID
            request_data: Request data dictionary
            response_data: Response data dictionary
            
        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                exec_summary = response_data.get("executive_summary", {})
                
                cursor.execute("""
                    INSERT OR REPLACE INTO explanations (
                        explanation_id, decision_id, timestamp, generation_time_ms,
                        action, symbol, confidence, risk_level, expected_value,
                        opportunity_type, amount, market_regime, volatility,
                        beginner_json, advanced_json, developer_json, researcher_json,
                        executive_summary_json, evidence_chain_json, raw_data_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    explanation_id,
                    decision_id,
                    response_data.get("timestamp", datetime.utcnow().isoformat()),
                    response_data.get("generation_time_ms", 0),
                    
                    exec_summary.get("action", ""),
                    exec_summary.get("symbol", ""),
                    exec_summary.get("confidence", 0),
                    exec_summary.get("risk_level", ""),
                    exec_summary.get("expected_value", 0),
                    
                    request_data.get("opportunity_type", ""),
                    request_data.get("amount", 0),
                    request_data.get("market_regime", ""),
                    request_data.get("volatility", 0),
                    
                    json.dumps(response_data.get("beginner", {})),
                    json.dumps(response_data.get("advanced", {})),
                    json.dumps(response_data.get("developer", {})),
                    json.dumps(response_data.get("researcher", {})),
                    json.dumps(exec_summary),
                    json.dumps(response_data.get("evidence_chain", [])),
                    json.dumps(response_data.get("raw_data", {})),
                ))
                
                # Save evidence items
                for i, evidence in enumerate(response_data.get("evidence_chain", [])):
                    cursor.execute("""
                        INSERT INTO evidence_items (
                            explanation_id, evidence_type, timestamp, weight, data_json
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        explanation_id,
                        evidence.get("type", f"type_{i}"),
                        evidence.get("timestamp", ""),
                        evidence.get("weight", 0),
                        json.dumps(evidence.get("data", {})),
                    ))
                
                # Save analyzer signals
                for name, signal in request_data.get("analyzer_signals", {}).items():
                    cursor.execute("""
                        INSERT INTO analyzer_signals (
                            explanation_id, analyzer_name, prediction, confidence,
                            weight, reason, data_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        explanation_id,
                        name,
                        signal.get("prediction", ""),
                        signal.get("confidence", 0),
                        signal.get("weight", 0),
                        signal.get("reason", ""),
                        json.dumps(signal.get("data", {})),
                    ))
                
                # Save alternatives
                for alt in request_data.get("alternatives_considered", []):
                    cursor.execute("""
                        INSERT INTO alternative_actions (
                            explanation_id, action, expected_value, risk_score,
                            rejection_reason, similarity_to_chosen
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        explanation_id,
                        alt.get("action", ""),
                        alt.get("expected_value", 0),
                        alt.get("risk_score", 0),
                        alt.get("rejection_reason", ""),
                        alt.get("similarity_score", 0),
                    ))
                
                # Save historical analogues
                for analogue in request_data.get("similar_past_decisions", []):
                    cursor.execute("""
                        INSERT INTO historical_analogues (
                            explanation_id, past_decision_id, timestamp, action,
                            confidence, outcome, similarity_score, market_conditions_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        explanation_id,
                        analogue.get("decision_id", ""),
                        analogue.get("timestamp", ""),
                        analogue.get("action", ""),
                        analogue.get("confidence", 0),
                        analogue.get("outcome"),
                        analogue.get("similarity_score", 0),
                        json.dumps(analogue.get("market_conditions", {})),
                    ))
                
                # Save feature importance
                for i, (feature, importance) in enumerate(
                    request_data.get("feature_importance", {}).items()
                ):
                    cursor.execute("""
                        INSERT INTO feature_importance (
                            explanation_id, feature_name, importance, rank
                        ) VALUES (?, ?, ?, ?)
                    """, (explanation_id, feature, importance, i + 1))
                
                # Save decision tree
                for i, step in enumerate(request_data.get("decision_tree", [])):
                    cursor.execute("""
                        INSERT INTO decision_tree_steps (
                            explanation_id, step_index, step_description, step_type
                        ) VALUES (?, ?, ?, ?)
                    """, (
                        explanation_id,
                        i,
                        step,
                        self._classify_step_type(step),
                    ))
                
                logger.info(f"Saved explanation {explanation_id} with full details")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save explanation: {e}")
            return False
    
    def _classify_step_type(self, step: str) -> str:
        """Classify decision tree step type"""
        step_lower = step.lower()
        if "validator" in step_lower:
            return "validation"
        elif "analyzer" in step_lower or "signal" in step_lower:
            return "analysis"
        elif "risk" in step_lower or "exposure" in step_lower:
            return "risk_assessment"
        elif "confidence" in step_lower:
            return "confidence_check"
        return "decision"
    
    def get_explanation(self, explanation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single explanation by ID.
        
        Args:
            explanation_id: Explanation ID
            
        Returns:
            Explanation data or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM explanations WHERE explanation_id = ?
            """, (explanation_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return self._row_to_explanation(row)
    
    def get_explanation_by_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """
        Get explanation for a specific decision.
        
        Args:
            decision_id: Decision ID
            
        Returns:
            Explanation data or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM explanations WHERE decision_id = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (decision_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return self._row_to_explanation(row)
    
    def _row_to_explanation(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert database row to explanation dictionary"""
        result = dict(row)
        
        # Parse JSON fields
        for json_field in [
            "beginner_json", "advanced_json", "developer_json", "researcher_json",
            "executive_summary_json", "evidence_chain_json", "raw_data_json"
        ]:
            if result.get(json_field):
                field_name = json_field.replace("_json", "")
                result[field_name] = json.loads(result[json_field])
                del result[json_field]
        
        return result
    
    def get_explanation_with_evidence(self, explanation_id: str) -> Optional[Dict[str, Any]]:
        """Get explanation with full evidence chain"""
        explanation = self.get_explanation(explanation_id)
        if not explanation:
            return None
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get evidence items
            cursor.execute("""
                SELECT * FROM evidence_items 
                WHERE explanation_id = ?
                ORDER BY id
            """, (explanation_id,))
            
            explanation["evidence_items"] = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("data_json"):
                    item["data"] = json.loads(item["data_json"])
                    del item["data_json"]
                explanation["evidence_items"].append(item)
            
            # Get analyzer signals
            cursor.execute("""
                SELECT * FROM analyzer_signals 
                WHERE explanation_id = ?
                ORDER BY confidence DESC
            """, (explanation_id,))
            
            explanation["analyzer_signals"] = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("data_json"):
                    item["data"] = json.loads(item["data_json"])
                    del item["data_json"]
                explanation["analyzer_signals"].append(item)
            
            # Get feature importance
            cursor.execute("""
                SELECT * FROM feature_importance 
                WHERE explanation_id = ?
                ORDER BY rank
            """, (explanation_id,))
            
            explanation["features"] = [dict(row) for row in cursor.fetchall()]
            
            # Get decision tree
            cursor.execute("""
                SELECT * FROM decision_tree_steps 
                WHERE explanation_id = ?
                ORDER BY step_index
            """, (explanation_id,))
            
            explanation["decision_tree"] = [dict(row) for row in cursor.fetchall()]
            
            # Get alternatives
            cursor.execute("""
                SELECT * FROM alternative_actions 
                WHERE explanation_id = ?
            """, (explanation_id,))
            
            explanation["alternatives"] = [dict(row) for row in cursor.fetchall()]
            
            # Get historical analogues
            cursor.execute("""
                SELECT * FROM historical_analogues 
                WHERE explanation_id = ?
            """, (explanation_id,))
            
            explanation["historical_analogues"] = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("market_conditions_json"):
                    item["market_conditions"] = json.loads(item["market_conditions_json"])
                    del item["market_conditions_json"]
                explanation["historical_analogues"].append(item)
        
        return explanation
    
    def get_recent_explanations(
        self, 
        limit: int = 20,
        action_filter: Optional[str] = None,
        symbol_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent explanations with optional filters.
        
        Args:
            limit: Maximum number of explanations to return
            action_filter: Filter by action (BUY, SELL, etc.)
            symbol_filter: Filter by symbol
            
        Returns:
            List of explanation summaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM explanations WHERE 1=1"
            params = []
            
            if action_filter:
                query += " AND action = ?"
                params.append(action_filter)
            
            if symbol_filter:
                query += " AND symbol = ?"
                params.append(symbol_filter)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            return [self._row_to_explanation(row) for row in cursor.fetchall()]
    
    def get_explanation_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored explanations"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total count
            cursor.execute("SELECT COUNT(*) as count FROM explanations")
            total = cursor.fetchone()["count"]
            
            # By action
            cursor.execute("""
                SELECT action, COUNT(*) as count 
                FROM explanations 
                GROUP BY action
            """)
            by_action = {row["action"]: row["count"] for row in cursor.fetchall()}
            
            # Average confidence
            cursor.execute("SELECT AVG(confidence) as avg FROM explanations")
            avg_confidence = cursor.fetchone()["avg"] or 0
            
            # Date range
            cursor.execute("SELECT MIN(timestamp) as min_date, MAX(timestamp) as max_date FROM explanations")
            date_range = cursor.fetchone()
            
            # By symbol
            cursor.execute("""
                SELECT symbol, COUNT(*) as count 
                FROM explanations 
                GROUP BY symbol 
                ORDER BY count DESC 
                LIMIT 10
            """)
            by_symbol = {row["symbol"]: row["count"] for row in cursor.fetchall()}
            
            return {
                "total_explanations": total,
                "by_action": by_action,
                "average_confidence": round(avg_confidence, 1),
                "date_range": {
                    "earliest": date_range["min_date"],
                    "latest": date_range["max_date"],
                },
                "top_symbols": by_symbol,
            }
    
    def iterate_explanations(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        batch_size: int = 100
    ) -> Iterator[Dict[str, Any]]:
        """
        Iterate through explanations in batches (memory efficient).
        
        Args:
            since: Only get explanations after this time
            until: Only get explanations before this time
            batch_size: Number of records per batch
            
        Yields:
            Explanation dictionaries
        """
        offset = 0
        
        while True:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM explanations WHERE 1=1"
                params = []
                
                if since:
                    query += " AND timestamp >= ?"
                    params.append(since.isoformat())
                
                if until:
                    query += " AND timestamp <= ?"
                    params.append(until.isoformat())
                
                query += " ORDER BY timestamp LIMIT ? OFFSET ?"
                params.extend([batch_size, offset])
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                if not rows:
                    break
                
                for row in rows:
                    yield self._row_to_explanation(row)
                
                offset += batch_size
    
    def delete_explanation(self, explanation_id: str) -> bool:
        """Delete an explanation and all related data"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete in order (respecting foreign keys)
                cursor.execute("DELETE FROM decision_tree_steps WHERE explanation_id = ?", (explanation_id,))
                cursor.execute("DELETE FROM feature_importance WHERE explanation_id = ?", (explanation_id,))
                cursor.execute("DELETE FROM historical_analogues WHERE explanation_id = ?", (explanation_id,))
                cursor.execute("DELETE FROM alternative_actions WHERE explanation_id = ?", (explanation_id,))
                cursor.execute("DELETE FROM analyzer_signals WHERE explanation_id = ?", (explanation_id,))
                cursor.execute("DELETE FROM evidence_items WHERE explanation_id = ?", (explanation_id,))
                cursor.execute("DELETE FROM explanations WHERE explanation_id = ?", (explanation_id,))
                
                logger.info(f"Deleted explanation {explanation_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete explanation: {e}")
            return False
    
    def cleanup_old_explanations(self, days: int = 90) -> int:
        """
        Clean up explanations older than specified days.
        
        Args:
            days: Keep explanations from last N days
            
        Returns:
            Number of explanations deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM decision_tree_steps 
                WHERE explanation_id IN (
                    SELECT explanation_id FROM explanations WHERE timestamp < ?
                )
            """, (cutoff.isoformat(),))
            
            cursor.execute("""
                DELETE FROM feature_importance 
                WHERE explanation_id IN (
                    SELECT explanation_id FROM explanations WHERE timestamp < ?
                )
            """, (cutoff.isoformat(),))
            
            cursor.execute("""
                DELETE FROM historical_analogues 
                WHERE explanation_id IN (
                    SELECT explanation_id FROM explanations WHERE timestamp < ?
                )
            """, (cutoff.isoformat(),))
            
            cursor.execute("""
                DELETE FROM alternative_actions 
                WHERE explanation_id IN (
                    SELECT explanation_id FROM explanations WHERE timestamp < ?
                )
            """, (cutoff.isoformat(),))
            
            cursor.execute("""
                DELETE FROM analyzer_signals 
                WHERE explanation_id IN (
                    SELECT explanation_id FROM explanations WHERE timestamp < ?
                )
            """, (cutoff.isoformat(),))
            
            cursor.execute("""
                DELETE FROM evidence_items 
                WHERE explanation_id IN (
                    SELECT explanation_id FROM explanations WHERE timestamp < ?
                )
            """, (cutoff.isoformat(),))
            
            cursor.execute("DELETE FROM explanations WHERE timestamp < ?", (cutoff.isoformat(),))
            
            deleted = cursor.rowcount
            logger.info(f"Cleaned up {deleted} old explanations")
            return deleted
