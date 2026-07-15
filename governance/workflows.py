"""
Approval Workflows
=================

Configurable approval workflows for strategy promotion.
"""

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval request status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalType(Enum):
    """Type of approval request"""
    STRATEGY_PROMOTION = "strategy_promotion"
    PARAMETER_CHANGE = "parameter_change"
    RISK_LIMIT_CHANGE = "risk_limit_change"
    MODEL_DEPLOYMENT = "model_deployment"
    CONFIG_CHANGE = "config_change"


class ApprovalLevel(Enum):
    """Required approval level"""
    AUTO = "auto"  # No approval needed
    SINGLE = "single"  # One approver
    DOUBLE = "double"  # Two approvers
    COMPLIANCE = "compliance"  # Compliance team required
    EXECUTIVE = "executive"  # Executive approval required


@dataclass
class ApprovalRequirement:
    """Requirements for approval"""
    min_performance: float = 0.0  # Minimum Sharpe ratio
    max_drawdown: float = 0.20  # Maximum allowed drawdown
    min_backtest_days: int = 30  # Minimum backtest period
    required_tests: List[str] = field(default_factory=list)
    risk_review_required: bool = False


@dataclass
class ApprovalDecision:
    """An approval decision"""
    decision_id: str
    timestamp: datetime
    approver: str
    decision: ApprovalStatus
    comments: str
    conditions: List[str] = field(default_factory=list)  # Conditions for approval


@dataclass
class ApprovalRequest:
    """
    An approval request.
    
    Tracks the full approval workflow for promoting changes.
    """
    request_id: str
    timestamp: datetime
    approval_type: ApprovalType
    title: str
    description: str
    
    # Requester info
    requested_by: str
    account_id: str
    
    # Item being approved
    target_id: str  # Strategy ID, model ID, etc.
    target_version: str
    changes_summary: List[str]
    
    # Approval requirements
    required_level: ApprovalLevel
    requirements: ApprovalRequirement
    
    # Current status
    status: ApprovalStatus
    
    # Approval chain
    approvals: List[ApprovalDecision] = field(default_factory=list)
    
    # Metadata
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Context data
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    risk_metrics: Dict[str, float] = field(default_factory=dict)
    test_results: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "approval_type": self.approval_type.value,
            "title": self.title,
            "description": self.description,
            "requested_by": self.requested_by,
            "account_id": self.account_id,
            "target_id": self.target_id,
            "target_version": self.target_version,
            "changes_summary": self.changes_summary,
            "required_level": self.required_level.value,
            "requirements": asdict(self.requirements),
            "status": self.status.value,
            "approvals": [
                {
                    "decision_id": a.decision_id,
                    "timestamp": a.timestamp.isoformat(),
                    "approver": a.approver,
                    "decision": a.decision.value,
                    "comments": a.comments,
                    "conditions": a.conditions
                }
                for a in self.approvals
            ],
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
            "performance_metrics": self.performance_metrics,
            "risk_metrics": self.risk_metrics,
            "test_results": self.test_results
        }


class ApprovalWorkflow:
    """
    Manages approval workflows for promotions.
    """
    
    def __init__(
        self,
        db_path: str = "data/governance/approvals.db",
        default_expiry_hours: int = 72
    ):
        self.db_path = db_path
        self.default_expiry_hours = default_expiry_hours
        self.requests: Dict[str, ApprovalRequest] = {}
        
        # Define approval requirements by type
        self.approval_requirements = {
            ApprovalType.STRATEGY_PROMOTION: ApprovalRequirement(
                min_performance=0.5,
                max_drawdown=0.15,
                min_backtest_days=30,
                required_tests=["backtest", "stress_test", "risk_assessment"],
                risk_review_required=True
            ),
            ApprovalType.PARAMETER_CHANGE: ApprovalRequirement(
                min_performance=0.3,
                max_drawdown=0.10,
                min_backtest_days=14,
                required_tests=["backtest"],
                risk_review_required=False
            ),
            ApprovalType.RISK_LIMIT_CHANGE: ApprovalRequirement(
                min_performance=0.0,
                max_drawdown=0.05,
                min_backtest_days=7,
                required_tests=["risk_assessment"],
                risk_review_required=True
            ),
            ApprovalType.MODEL_DEPLOYMENT: ApprovalRequirement(
                min_performance=0.4,
                max_drawdown=0.12,
                min_backtest_days=21,
                required_tests=["validation", "backtest"],
                risk_review_required=True
            ),
            ApprovalType.CONFIG_CHANGE: ApprovalRequirement(
                min_performance=0.0,
                max_drawdown=0.20,
                min_backtest_days=0,
                required_tests=[],
                risk_review_required=False
            )
        }
        
        self._ensure_database()
    
    def _ensure_database(self) -> None:
        """Initialize database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS approval_requests (
                request_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                approval_type TEXT NOT NULL,
                title TEXT,
                description TEXT,
                requested_by TEXT,
                account_id TEXT,
                target_id TEXT,
                target_version TEXT,
                changes_summary TEXT,
                required_level TEXT,
                requirements TEXT,
                status TEXT,
                expires_at TEXT,
                metadata TEXT,
                performance_metrics TEXT,
                risk_metrics TEXT,
                test_results TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS approval_decisions (
                decision_id TEXT PRIMARY KEY,
                request_id TEXT,
                timestamp TEXT NOT NULL,
                approver TEXT,
                decision TEXT,
                comments TEXT,
                conditions TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON approval_requests(status)
        """)
        
        conn.commit()
        conn.close()
    
    def create_request(
        self,
        approval_type: ApprovalType,
        title: str,
        description: str,
        requested_by: str,
        account_id: str,
        target_id: str,
        target_version: str,
        changes_summary: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ApprovalRequest:
        """
        Create a new approval request.
        
        Automatically determines required approval level based on type and risk.
        """
        # Get requirements
        requirements = self.approval_requirements.get(
            approval_type,
            ApprovalRequirement()
        )
        
        # Determine required level
        required_level = self._determine_level(
            approval_type,
            requirements,
            metadata or {}
        )
        
        # Check if auto-approval is possible
        if required_level == ApprovalLevel.AUTO:
            status = ApprovalStatus.APPROVED
        else:
            status = ApprovalStatus.PENDING
        
        request = ApprovalRequest(
            request_id=str(uuid4()),
            timestamp=datetime.now(),
            approval_type=approval_type,
            title=title,
            description=description,
            requested_by=requested_by,
            account_id=account_id,
            target_id=target_id,
            target_version=target_version,
            changes_summary=changes_summary,
            required_level=required_level,
            requirements=requirements,
            status=status,
            expires_at=datetime.now() + timedelta(hours=self.default_expiry_hours),
            metadata=metadata or {}
        )
        
        self.requests[request.request_id] = request
        self._store_request(request)
        
        logger.info(f"Created approval request: {request.request_id}")
        
        return request
    
    def _determine_level(
        self,
        approval_type: ApprovalType,
        requirements: ApprovalRequirement,
        metadata: Dict[str, Any]
    ) -> ApprovalLevel:
        """Determine required approval level"""
        # Auto-approve low-risk changes
        if approval_type == ApprovalType.CONFIG_CHANGE:
            return ApprovalLevel.AUTO
        
        # Check if requirements are met
        if requirements.risk_review_required:
            return ApprovalLevel.DOUBLE
        
        # Check risk metrics if available
        risk_metrics = metadata.get("risk_metrics", {})
        if risk_metrics.get("max_drawdown", 0) > requirements.max_drawdown:
            return ApprovalLevel.COMPLIANCE
        
        # Check performance
        perf = metadata.get("performance_metrics", {})
        if perf.get("sharpe_ratio", 0) < requirements.min_performance:
            return ApprovalLevel.SINGLE
        
        return ApprovalLevel.SINGLE
    
    def approve(
        self,
        request_id: str,
        approver: str,
        comments: str = "",
        conditions: Optional[List[str]] = None
    ) -> bool:
        """Approve a request"""
        request = self.requests.get(request_id)
        if not request:
            return False
        
        if request.status != ApprovalStatus.PENDING:
            return False
        
        decision = ApprovalDecision(
            decision_id=str(uuid4()),
            timestamp=datetime.now(),
            approver=approver,
            decision=ApprovalStatus.APPROVED,
            comments=comments,
            conditions=conditions or []
        )
        
        request.approvals.append(decision)
        
        # Check if approval is complete
        if self._is_approval_complete(request):
            request.status = ApprovalStatus.APPROVED
            logger.info(f"Approval request {request_id} fully approved")
        
        self._store_request(request)
        self._store_decision(request_id, decision)
        
        return True
    
    def reject(
        self,
        request_id: str,
        approver: str,
        comments: str
    ) -> bool:
        """Reject a request"""
        request = self.requests.get(request_id)
        if not request:
            return False
        
        if request.status != ApprovalStatus.PENDING:
            return False
        
        decision = ApprovalDecision(
            decision_id=str(uuid4()),
            timestamp=datetime.now(),
            approver=approver,
            decision=ApprovalStatus.REJECTED,
            comments=comments
        )
        
        request.approvals.append(decision)
        request.status = ApprovalStatus.REJECTED
        
        self._store_request(request)
        self._store_decision(request_id, decision)
        
        logger.info(f"Approval request {request_id} rejected")
        
        return True
    
    def cancel(self, request_id: str, cancelled_by: str) -> bool:
        """Cancel a request"""
        request = self.requests.get(request_id)
        if not request:
            return False
        
        if request.status != ApprovalStatus.PENDING:
            return False
        
        request.status = ApprovalStatus.CANCELLED
        self._store_request(request)
        
        logger.info(f"Approval request {request_id} cancelled by {cancelled_by}")
        
        return True
    
    def _is_approval_complete(self, request: ApprovalRequest) -> bool:
        """Check if required approvals have been received"""
        level = request.required_level
        
        if level == ApprovalLevel.AUTO:
            return True
        elif level == ApprovalLevel.SINGLE:
            return len(request.approvals) >= 1
        elif level == ApprovalLevel.DOUBLE:
            # Need 2 different approvers
            approvers = set(a.approver for a in request.approvals)
            return len(approvers) >= 2
        else:
            # Compliance/Executive require manual review
            return False
    
    def get_pending_requests(self) -> List[ApprovalRequest]:
        """Get all pending requests"""
        return [
            r for r in self.requests.values()
            if r.status == ApprovalStatus.PENDING
        ]
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get request by ID"""
        return self.requests.get(request_id)
    
    def check_expiry(self) -> List[str]:
        """Check and expire old requests"""
        expired = []
        now = datetime.now()
        
        for request in self.requests.values():
            if request.status == ApprovalStatus.PENDING:
                if request.expires_at and request.expires_at < now:
                    request.status = ApprovalStatus.EXPIRED
                    expired.append(request.request_id)
                    self._store_request(request)
        
        if expired:
            logger.info(f"Expired {len(expired)} approval requests")
        
        return expired
    
    def _store_request(self, request: ApprovalRequest) -> None:
        """Store request in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO approval_requests (
                request_id, timestamp, approval_type, title, description,
                requested_by, account_id, target_id, target_version,
                changes_summary, required_level, requirements, status,
                expires_at, metadata, performance_metrics, risk_metrics, test_results
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.request_id,
            request.timestamp.isoformat(),
            request.approval_type.value,
            request.title,
            request.description,
            request.requested_by,
            request.account_id,
            request.target_id,
            request.target_version,
            json.dumps(request.changes_summary),
            request.required_level.value,
            json.dumps(asdict(request.requirements)),
            request.status.value,
            request.expires_at.isoformat() if request.expires_at else None,
            json.dumps(request.metadata),
            json.dumps(request.performance_metrics),
            json.dumps(request.risk_metrics),
            json.dumps(request.test_results)
        ))
        
        conn.commit()
        conn.close()
    
    def _store_decision(self, request_id: str, decision: ApprovalDecision) -> None:
        """Store decision in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO approval_decisions (
                decision_id, request_id, timestamp, approver, decision, comments, conditions
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            decision.decision_id,
            request_id,
            decision.timestamp.isoformat(),
            decision.approver,
            decision.decision.value,
            decision.comments,
            json.dumps(decision.conditions)
        ))
        
        conn.commit()
        conn.close()
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get overall workflow status"""
        pending = sum(1 for r in self.requests.values() if r.status == ApprovalStatus.PENDING)
        approved = sum(1 for r in self.requests.values() if r.status == ApprovalStatus.APPROVED)
        rejected = sum(1 for r in self.requests.values() if r.status == ApprovalStatus.REJECTED)
        
        return {
            "total_requests": len(self.requests),
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "by_type": self._count_by_type(),
            "by_level": self._count_by_level()
        }
    
    def _count_by_type(self) -> Dict[str, int]:
        """Count requests by type"""
        counts = {}
        for r in self.requests.values():
            t = r.approval_type.value
            counts[t] = counts.get(t, 0) + 1
        return counts
    
    def _count_by_level(self) -> Dict[str, int]:
        """Count requests by required level"""
        counts = {}
        for r in self.requests.values():
            l = r.required_level.value
            counts[l] = counts.get(l, 0) + 1
        return counts


# Helper for dataclass
from dataclasses import asdict
