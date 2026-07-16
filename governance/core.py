"""
Governance Core
==============

Core classes for enterprise strategy governance.
"""

import time
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class WorkflowStage(Enum):
    """Strategy workflow stages"""
    IDEA = "idea"
    RESEARCH = "research"
    DRAFT = "draft"
    DEVELOPMENT = "development"
    TESTING = "testing"
    PAPER_TRADING = "paper_trading"
    VALIDATION = "validation"
    APPROVAL = "approval"
    PRODUCTION = "production"
    MONITORING = "monitoring"
    RETIREMENT = "retirement"
    
    def next(self) -> Optional["WorkflowStage"]:
        """Get next stage"""
        stages = list(WorkflowStage)
        idx = stages.index(self)
        if idx + 1 < len(stages):
            return stages[idx + 1]
        return None
    
    def previous(self) -> Optional["WorkflowStage"]:
        """Get previous stage"""
        stages = list(WorkflowStage)
        idx = stages.index(self)
        if idx > 0:
            return stages[idx - 1]
        return None
    
    def can_transition_to(self, target: "WorkflowStage") -> bool:
        """Check if transition is allowed"""
        stages = list(WorkflowStage)
        current_idx = stages.index(self)
        target_idx = stages.index(target)
        
        # Can only move forward or backward one step
        return abs(target_idx - current_idx) == 1


class StageStatus(Enum):
    """Status of a workflow stage"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class StrategyVersion:
    """Version information for a strategy"""
    version: str
    created_at: float
    created_by: str
    changes: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    status: StageStatus = StageStatus.NOT_STARTED


@dataclass
class StageTransition:
    """Record of a stage transition"""
    transition_id: str
    strategy_id: str
    from_stage: WorkflowStage
    to_stage: WorkflowStage
    timestamp: float
    triggered_by: str
    reason: str
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Approval:
    """Record of an approval"""
    approval_id: str
    stage: WorkflowStage
    approver: str
    timestamp: float
    decision: str  # "approved", "rejected", "conditions"
    comments: str
    conditions: List[str] = field(default_factory=list)
    signature: Optional[str] = None


@dataclass
class ComplianceRecord:
    """Compliance evidence record"""
    record_id: str
    strategy_id: str
    requirement: str
    evidence_type: str  # "document", "test_result", "metric", "signature"
    evidence: Dict[str, Any]
    submitted_at: float
    submitted_by: str
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[float] = None


@dataclass
class AuditEntry:
    """Audit log entry"""
    entry_id: str
    timestamp: float
    action: str
    actor: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    previous_hash: Optional[str] = None
    hash: str = ""
    
    def calculate_hash(self) -> str:
        """Calculate entry hash"""
        content = json.dumps({
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "action": self.action,
            "actor": self.actor,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class RollbackRecord:
    """Record of a rollback"""
    rollback_id: str
    strategy_id: str
    from_version: str
    to_version: str
    timestamp: float
    reason: str
    initiated_by: str
    approved_by: Optional[str] = None
    completed: bool = True


@dataclass
class StrategyLifecycle:
    """
    Complete lifecycle tracking for a strategy.
    """
    strategy_id: str
    name: str
    description: str
    created_at: float
    created_by: str
    current_stage: WorkflowStage = WorkflowStage.IDEA
    
    # Stage tracking
    stage_history: List[Dict[str, Any]] = field(default_factory=list)
    versions: List[StrategyVersion] = field(default_factory=list)
    approvals: List[Approval] = field(default_factory=list)
    compliance_records: List[ComplianceRecord] = field(default_factory=list)
    rollback_history: List[RollbackRecord] = field(default_factory=list)
    
    # Metadata
    owner: str = ""
    team: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Metrics
    total_trades: int = 0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    
    def get_current_version(self) -> Optional[StrategyVersion]:
        """Get the current version"""
        if self.versions:
            return self.versions[-1]
        return None
    
    def get_stage_duration(self, stage: WorkflowStage) -> float:
        """Get duration in current or last completion of a stage"""
        for entry in reversed(self.stage_history):
            if entry.get("stage") == stage.value:
                if entry.get("completed_at"):
                    start = entry.get("started_at", entry["completed_at"])
                    return entry["completed_at"] - start
                elif entry.get("started_at"):
                    return time.time() - entry["started_at"]
        return 0
    
    def is_production_ready(self) -> bool:
        """Check if strategy is ready for production"""
        required_stages = [
            WorkflowStage.IDEA,
            WorkflowStage.RESEARCH,
            WorkflowStage.DRAFT,
            WorkflowStage.DEVELOPMENT,
            WorkflowStage.TESTING,
            WorkflowStage.PAPER_TRADING,
            WorkflowStage.VALIDATION,
        ]
        
        for stage in required_stages:
            completed = any(
                h.get("stage") == stage.value and h.get("status") == StageStatus.COMPLETED.value
                for h in self.stage_history
            )
            if not completed:
                return False
        
        return True
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get compliance summary"""
        total = len(self.compliance_records)
        verified = sum(1 for r in self.compliance_records if r.verified)
        
        return {
            "total_records": total,
            "verified_records": verified,
            "verification_rate": verified / total if total > 0 else 0,
            "pending_verification": total - verified,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "current_stage": self.current_stage.value,
            "stage_history": self.stage_history,
            "versions": [
                {"version": v.version, "created_at": v.created_at}
                for v in self.versions
            ],
            "total_approvals": len(self.approvals),
            "compliance_summary": self.get_compliance_summary(),
            "production_ready": self.is_production_ready(),
            "metrics": {
                "total_trades": self.total_trades,
                "win_rate": self.win_rate,
                "sharpe_ratio": self.sharpe_ratio,
                "max_drawdown": self.max_drawdown,
            },
        }


# Type alias
from typing import Optional
