"""
Approval System
=============

Enterprise approval workflow with policies and signoffs.
"""

import time
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Status of an approval request"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalType(Enum):
    """Types of approvals"""
    STRATEGY_DEPLOYMENT = "strategy_deployment"
    PARAMETER_CHANGE = "parameter_change"
    RISK_LIMIT_CHANGE = "risk_limit_change"
    MODEL_UPDATE = "model_update"
    STRATEGY_RETIREMENT = "strategy_retirement"
    EMERGENCY_ROLLBACK = "emergency_rollback"


class ApprovalLevel(Enum):
    """Approval levels"""
    AUTOMATIC = "automatic"  # No approval needed
    LEVEL_1 = "level_1"    # Single approver
    LEVEL_2 = "level_2"    # Two approvers
    LEVEL_3 = "level_3"     # Committee approval
    EXECUTIVE = "executive" # C-level approval


@dataclass
class ApprovalPolicy:
    """Policy for approval requirements"""
    policy_id: str
    name: str
    approval_type: ApprovalType
    required_level: ApprovalLevel
    
    # Conditions
    min_capital_threshold: float = 0  # Capital threshold for elevated approval
    min_risk_threshold: float = 0    # Risk threshold for elevated approval
    requires_testing: bool = True
    requires_documentation: bool = True
    
    # Override conditions
    can_override: bool = False
    override_level: Optional[ApprovalLevel] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "approval_type": self.approval_type.value,
            "required_level": self.required_level.value,
            "conditions": {
                "min_capital_threshold": self.min_capital_threshold,
                "min_risk_threshold": self.min_risk_threshold,
                "requires_testing": self.requires_testing,
                "requires_documentation": self.requires_documentation,
            }
        }


@dataclass
class Signoff:
    """Individual signoff on an approval"""
    signoff_id: str
    approver: str
    approver_role: str
    timestamp: float
    decision: str  # "approved", "rejected", "abstained"
    comments: str
    signature: str  # Cryptographic signature
    conditions: List[str] = field(default_factory=list)
    
    def calculate_signature(self, private_key: str) -> str:
        """Calculate cryptographic signature"""
        content = f"{self.approver}:{self.timestamp}:{self.decision}"
        return hashlib.sha256((content + private_key).encode()).hexdigest()
    
    def verify_signature(self, public_key: str) -> bool:
        """Verify signature (simplified)"""
        return len(self.signature) == 64  # SHA256 hex length


@dataclass
class ApprovalRequest:
    """Approval request"""
    request_id: str
    approval_type: ApprovalType
    title: str
    description: str
    
    # Requester info
    requested_by: str
    requested_at: float
    account_id: str
    
    # Target info
    target_id: str
    target_name: str
    target_version: str
    target_type: str  # "strategy", "model", "config"
    
    # Changes
    changes_summary: List[str]
    impact_assessment: str = ""
    risk_assessment: str = ""
    
    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    required_level: ApprovalLevel = ApprovalLevel.LEVEL_1
    
    # Signoffs
    signoffs: List[Signoff] = field(default_factory=list)
    
    # Expiration
    expires_at: Optional[float] = None
    
    # Metadata
    evidence: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def can_approve(self) -> bool:
        """Check if request can be approved"""
        if self.status != ApprovalStatus.PENDING:
            return False
        
        if self.expires_at and time.time() > self.expires_at:
            return False
        
        return True
    
    def get_required_signoffs(self) -> int:
        """Get number of required signoffs"""
        if self.required_level == ApprovalLevel.AUTOMATIC:
            return 0
        elif self.required_level == ApprovalLevel.LEVEL_1:
            return 1
        elif self.required_level == ApprovalLevel.LEVEL_2:
            return 2
        elif self.required_level in [ApprovalLevel.LEVEL_3, ApprovalLevel.EXECUTIVE]:
            return 3
        return 1
    
    def get_current_signoffs(self) -> int:
        """Get current number of approved signoffs"""
        return sum(1 for s in self.signoffs if s.decision == "approved")
    
    def is_fully_approved(self) -> bool:
        """Check if fully approved"""
        return self.get_current_signoffs() >= self.get_required_signoffs()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "approval_type": self.approval_type.value,
            "title": self.title,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at,
            "target_id": self.target_id,
            "target_version": self.target_version,
            "status": self.status.value,
            "required_level": self.required_level.value,
            "signoffs_count": len(self.signoffs),
            "approved_count": self.get_current_signoffs(),
        }


class ApprovalManager:
    """
    Manages approval workflows and policies.
    """
    
    def __init__(self):
        self._requests: Dict[str, ApprovalRequest] = {}
        self._policies: Dict[ApprovalType, ApprovalPolicy] = {}
        self._approvers: Dict[str, List[str]] = {}  # role -> list of approvers
        
        # Initialize default policies
        self._initialize_policies()
    
    def _initialize_policies(self) -> None:
        """Initialize default approval policies"""
        
        self._policies[ApprovalType.STRATEGY_DEPLOYMENT] = ApprovalPolicy(
            policy_id="policy_deployment",
            name="Strategy Deployment Approval",
            approval_type=ApprovalType.STRATEGY_DEPLOYMENT,
            required_level=ApprovalLevel.LEVEL_2,
            requires_testing=True,
            requires_documentation=True,
        )
        
        self._policies[ApprovalType.PARAMETER_CHANGE] = ApprovalPolicy(
            policy_id="policy_param",
            name="Parameter Change Approval",
            approval_type=ApprovalType.PARAMETER_CHANGE,
            required_level=ApprovalLevel.LEVEL_1,
            requires_testing=True,
            requires_documentation=True,
        )
        
        self._policies[ApprovalType.RISK_LIMIT_CHANGE] = ApprovalPolicy(
            policy_id="policy_risk",
            name="Risk Limit Change Approval",
            approval_type=ApprovalType.RISK_LIMIT_CHANGE,
            required_level=ApprovalLevel.LEVEL_3,
            min_risk_threshold=0.1,
            requires_testing=True,
            requires_documentation=True,
        )
        
        self._policies[ApprovalType.MODEL_UPDATE] = ApprovalPolicy(
            policy_id="policy_model",
            name="Model Update Approval",
            approval_type=ApprovalType.MODEL_UPDATE,
            required_level=ApprovalLevel.LEVEL_2,
            requires_testing=True,
            requires_documentation=True,
        )
        
        self._policies[ApprovalType.STRATEGY_RETIREMENT] = ApprovalPolicy(
            policy_id="policy_retirement",
            name="Strategy Retirement Approval",
            approval_type=ApprovalType.STRATEGY_RETIREMENT,
            required_level=ApprovalLevel.LEVEL_2,
            requires_documentation=True,
        )
        
        self._policies[ApprovalType.EMERGENCY_ROLLBACK] = ApprovalPolicy(
            policy_id="policy_rollback",
            name="Emergency Rollback Approval",
            approval_type=ApprovalType.EMERGENCY_ROLLBACK,
            required_level=ApprovalLevel.LEVEL_1,
            can_override=True,
            requires_documentation=True,
        )
    
    def create_request(
        self,
        approval_type: ApprovalType,
        title: str,
        description: str,
        requested_by: str,
        account_id: str,
        target_id: str,
        target_name: str,
        target_version: str,
        target_type: str,
        changes_summary: List[str],
        impact_assessment: str = "",
        risk_assessment: str = "",
        evidence: Optional[Dict[str, Any]] = None,
        expiration_hours: float = 72
    ) -> ApprovalRequest:
        """Create a new approval request"""
        # Get policy
        policy = self._policies.get(approval_type)
        required_level = policy.required_level if policy else ApprovalLevel.LEVEL_1
        
        request = ApprovalRequest(
            request_id=self._generate_id(),
            approval_type=approval_type,
            title=title,
            description=description,
            requested_by=requested_by,
            requested_at=time.time(),
            account_id=account_id,
            target_id=target_id,
            target_name=target_name,
            target_version=target_version,
            target_type=target_type,
            changes_summary=changes_summary,
            impact_assessment=impact_assessment,
            risk_assessment=risk_assessment,
            required_level=required_level,
            expires_at=time.time() + (expiration_hours * 3600),
            evidence=evidence or {},
        )
        
        self._requests[request.request_id] = request
        logger.info(f"Created approval request: {request.request_id}")
        
        return request
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request"""
        return self._requests.get(request_id)
    
    def get_pending_requests(self) -> List[ApprovalRequest]:
        """Get all pending requests"""
        return [
            r for r in self._requests.values()
            if r.status == ApprovalStatus.PENDING and r.can_approve()
        ]
    
    def get_requests_by_approver(self, approver: str) -> List[ApprovalRequest]:
        """Get requests that an approver can act on"""
        pending = self.get_pending_requests()
        # In production, would check approver permissions
        return pending
    
    def signoff(
        self,
        request_id: str,
        approver: str,
        approver_role: str,
        decision: str,
        comments: str = "",
        conditions: Optional[List[str]] = None,
        signature: Optional[str] = None
    ) -> bool:
        """
        Sign off on an approval request.
        
        Args:
            decision: "approved", "rejected", "abstained"
        """
        request = self._requests.get(request_id)
        if not request or not request.can_approve():
            return False
        
        # Check if approver already signed
        for existing in request.signoffs:
            if existing.approver == approver:
                logger.warning(f"Approver {approver} already signed off on {request_id}")
                return False
        
        # Create signoff
        signoff = Signoff(
            signoff_id=self._generate_id(),
            approver=approver,
            approver_role=approver_role,
            timestamp=time.time(),
            decision=decision,
            comments=comments,
            signature=signature or self._generate_signature(approver),
            conditions=conditions or [],
        )
        
        request.signoffs.append(signoff)
        
        # Check if request is now fully approved or rejected
        if decision == "rejected":
            request.status = ApprovalStatus.REJECTED
            logger.info(f"Approval request rejected: {request_id}")
        elif request.is_fully_approved():
            request.status = ApprovalStatus.APPROVED
            logger.info(f"Approval request approved: {request_id}")
        
        return True
    
    def cancel_request(self, request_id: str, cancelled_by: str, reason: str) -> bool:
        """Cancel an approval request"""
        request = self._requests.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False
        
        request.status = ApprovalStatus.CANCELLED
        logger.info(f"Approval request cancelled: {request_id} by {cancelled_by}")
        return True
    
    def expire_requests(self) -> int:
        """Expire old pending requests"""
        count = 0
        for request in self._requests.values():
            if (request.status == ApprovalStatus.PENDING and
                request.expires_at and
                time.time() > request.expires_at):
                request.status = ApprovalStatus.EXPIRED
                count += 1
        
        return count
    
    def get_policy(self, approval_type: ApprovalType) -> Optional[ApprovalPolicy]:
        """Get policy for approval type"""
        return self._policies.get(approval_type)
    
    def update_policy(self, policy: ApprovalPolicy) -> None:
        """Update an approval policy"""
        self._policies[policy.approval_type] = policy
    
    def register_approver(self, approver: str, role: str) -> None:
        """Register an approver"""
        if role not in self._approvers:
            self._approvers[role] = []
        if approver not in self._approvers[role]:
            self._approvers[role].append(approver)
    
    def get_approvers_by_role(self, role: str) -> List[str]:
        """Get approvers by role"""
        return self._approvers.get(role, [])
    
    def generate_approval_report(self, since: Optional[float] = None) -> Dict[str, Any]:
        """Generate approval report"""
        requests = list(self._requests.values())
        
        if since:
            requests = [r for r in requests if r.requested_at >= since]
        
        approved = sum(1 for r in requests if r.status == ApprovalStatus.APPROVED)
        rejected = sum(1 for r in requests if r.status == ApprovalStatus.REJECTED)
        pending = sum(1 for r in requests if r.status == ApprovalStatus.PENDING)
        expired = sum(1 for r in requests if r.status == ApprovalStatus.EXPIRED)
        
        # Average time to approval
        completed = [r for r in requests if r.status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]]
        if completed:
            avg_time = sum(
                r.signoffs[-1].timestamp - r.requested_at
                for r in completed
                if r.signoffs
            ) / len(completed)
        else:
            avg_time = 0
        
        return {
            "period_start": since,
            "total_requests": len(requests),
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "expired": expired,
            "approval_rate": approved / len(requests) if requests else 0,
            "avg_approval_time_hours": avg_time / 3600 if avg_time else 0,
            "by_type": {
                at.value: {
                    "total": sum(1 for r in requests if r.approval_type == at),
                    "approved": sum(1 for r in requests if r.approval_type == at and r.status == ApprovalStatus.APPROVED),
                }
                for at in ApprovalType
            }
        }
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _generate_signature(self, approver: str) -> str:
        """Generate signature (simplified)"""
        content = f"{approver}:{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()
