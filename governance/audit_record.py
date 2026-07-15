"""
Audit Record System
===================

Comprehensive audit records for all automated decisions.
"""

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of decisions requiring audit"""
    TRADE_ENTRY = "trade_entry"
    TRADE_EXIT = "trade_exit"
    POSITION_ADJUSTMENT = "position_adjustment"
    STRATEGY_ACTIVATION = "strategy_activation"
    STRATEGY_DEACTIVATION = "strategy_deactivation"
    MODEL_SWITCH = "model_switch"
    PARAMETER_UPDATE = "parameter_update"
    RISK_LIMIT_CHANGE = "risk_limit_change"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_DECISION = "approval_decision"


class RiskCheckResult(Enum):
    """Result of risk checks"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class MarketState:
    """Market state at decision time"""
    regime: str
    volatility: float
    trend_direction: str
    liquidity: str
    spread: float
    volume_24h: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ModelVersion:
    """Model version information"""
    model_id: str
    version: str
    training_date: datetime
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class FeatureSnapshot:
    """Snapshot of feature values"""
    features: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AlternativeAction:
    """Alternative action considered"""
    action_type: str
    expected_value: float
    confidence: float
    reason_rejected: str
    risk_score: float


@dataclass
class RiskCheck:
    """Risk check performed"""
    check_name: str
    result: RiskCheckResult
    details: str
    threshold: Optional[float] = None
    actual_value: Optional[float] = None


@dataclass
class HistoricalAnalogue:
    """Historical situation similar to current"""
    timestamp: datetime
    situation_id: str
    similarity_score: float
    outcome: str
    lesson: str


@dataclass
class AuditRecord:
    """
    Complete audit record for an automated decision.
    
    Every automated decision produces this record with full context.
    """
    # Core identification
    record_id: str
    timestamp: datetime
    decision_type: DecisionType
    account_id: str
    
    # Market context
    market_state: MarketState
    
    # Model information
    model_versions: List[ModelVersion]
    
    # Decision details
    feature_values: FeatureSnapshot
    confidence: float
    uncertainty: float
    uncertainty_type: str  # aleatoric, epistemic, total
    
    # Historical context
    historical_analogues: List[HistoricalAnalogue]
    
    # Alternative actions
    alternative_actions: List[AlternativeAction]
    
    # Risk checks
    risk_checks: List[RiskCheck]
    overall_risk_result: RiskCheckResult
    
    # Decision outcome
    action_taken: str
    execution_result: str
    execution_latency_ms: float
    
    # Additional metadata
    session_id: str
    correlation_id: str
    parent_record_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        def make_serializable(obj):
            """Convert datetime and enum objects to strings"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, Enum):
                return obj.value
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(i) for i in obj]
            return obj
        
        base_dict = asdict(self)
        return make_serializable(base_dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditRecord":
        """Create from dictionary"""
        market_state = MarketState(**data["market_state"])
        
        model_versions = [
            ModelVersion(
                model_id=m["model_id"],
                version=m["version"],
                training_date=datetime.fromisoformat(m["training_date"]),
                metrics=m["metrics"]
            )
            for m in data["model_versions"]
        ]
        
        feature_values = FeatureSnapshot(
            features=data["feature_values"]["features"],
            timestamp=datetime.fromisoformat(data["feature_values"]["timestamp"])
        )
        
        historical_analogues = [
            HistoricalAnalogue(
                timestamp=datetime.fromisoformat(h["timestamp"]),
                situation_id=h["situation_id"],
                similarity_score=h["similarity_score"],
                outcome=h["outcome"],
                lesson=h["lesson"]
            )
            for h in data["historical_analogues"]
        ]
        
        alternative_actions = [
            AlternativeAction(**a)
            for a in data["alternative_actions"]
        ]
        
        risk_checks = [
            RiskCheck(
                check_name=r["check_name"],
                result=RiskCheckResult(r["result"]),
                details=r["details"],
                threshold=r["threshold"],
                actual_value=r["actual_value"]
            )
            for r in data["risk_checks"]
        ]
        
        return cls(
            record_id=data["record_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            decision_type=DecisionType(data["decision_type"]),
            account_id=data["account_id"],
            market_state=market_state,
            model_versions=model_versions,
            feature_values=feature_values,
            confidence=data["confidence"],
            uncertainty=data["uncertainty"],
            uncertainty_type=data["uncertainty_type"],
            historical_analogues=historical_analogues,
            alternative_actions=alternative_actions,
            risk_checks=risk_checks,
            overall_risk_result=RiskCheckResult(data["overall_risk_result"]),
            action_taken=data["action_taken"],
            execution_result=data["execution_result"],
            execution_latency_ms=data["execution_latency_ms"],
            session_id=data["session_id"],
            correlation_id=data["correlation_id"],
            parent_record_id=data.get("parent_record_id"),
            metadata=data.get("metadata", {})
        )


class AuditLogger:
    """
    Logs audit records for all automated decisions.
    """
    
    def __init__(self, db_path: str = "data/governance/audit.db"):
        self.db_path = db_path
        self._ensure_database()
    
    def _ensure_database(self) -> None:
        """Initialize database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_records (
                record_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                account_id TEXT,
                record_json TEXT NOT NULL,
                hash TEXT NOT NULL,
                previous_hash TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_records(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_decision_type ON audit_records(decision_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_account ON audit_records(account_id)
        """)
        
        conn.commit()
        conn.close()
    
    def log(self, record: AuditRecord, previous_hash: Optional[str] = None) -> str:
        """
        Log an audit record.
        
        Args:
            record: AuditRecord to log
            previous_hash: Hash of previous record (for chaining)
            
        Returns:
            Hash of the recorded entry
        """
        import hashlib
        
        # Serialize record
        record_json = json.dumps(record.to_dict(), sort_keys=True)
        
        # Calculate hash (includes previous hash for chaining)
        hash_input = f"{record_json}{previous_hash or ''}"
        record_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        # Store
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO audit_records (
                record_id, timestamp, decision_type, account_id,
                record_json, hash, previous_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            record.record_id,
            record.timestamp.isoformat(),
            record.decision_type.value,
            record.account_id,
            record_json,
            record_hash,
            previous_hash
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Logged audit record: {record.record_id}")
        
        return record_hash
    
    def get_record(self, record_id: str) -> Optional[AuditRecord]:
        """Get audit record by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT record_json FROM audit_records WHERE record_id = ?",
            (record_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return AuditRecord.from_dict(json.loads(row[0]))
        return None
    
    def get_records(
        self,
        decision_type: Optional[DecisionType] = None,
        account_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditRecord]:
        """Get audit records with filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT record_json FROM audit_records WHERE 1=1"
        params = []
        
        if decision_type:
            query += " AND decision_type = ?"
            params.append(decision_type.value)
        
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)
        
        if since:
            query += " AND timestamp > ?"
            params.append(since.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [AuditRecord.from_dict(json.loads(row[0])) for row in rows]
    
    def search(
        self,
        query: str,
        limit: int = 100
    ) -> List[AuditRecord]:
        """Full-text search in audit records"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT record_json FROM audit_records
            WHERE record_json LIKE ?
            ORDER BY timestamp DESC LIMIT ?
        """, (f"%{query}%", limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [AuditRecord.from_dict(json.loads(row[0])) for row in rows]
    
    def get_chain_integrity(self) -> Dict[str, Any]:
        """Verify chain integrity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT record_id, hash, previous_hash FROM audit_records ORDER BY timestamp"
        )
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {"valid": True, "records": 0}
        
        import hashlib
        
        valid = True
        for i, (record_id, current_hash, previous_hash) in enumerate(rows):
            if i > 0:
                expected_prev = rows[i-1][1]
                if previous_hash != expected_prev:
                    valid = False
                    break
        
        return {
            "valid": valid,
            "records": len(rows),
            "first_hash": rows[0][1] if rows else None,
            "last_hash": rows[-1][1] if rows else None
        }
