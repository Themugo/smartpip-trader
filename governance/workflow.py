"""
Workflow Management
=================

Strategy workflow management with stage transitions and validation.
"""

import time
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import logging

from .core import (
    StrategyLifecycle,
    StrategyVersion,
    WorkflowStage,
    StageStatus,
    StageTransition,
    Approval,
    ComplianceRecord,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationRequirement:
    """Requirement for stage completion"""
    requirement_id: str
    stage: WorkflowStage
    description: str
    required: bool = True
    validator: Optional[str] = None  # Function name to call
    
    # Evidence requirements
    requires_evidence: bool = True
    evidence_types: List[str] = field(default_factory=list)  # e.g., ["document", "test_result"]
    
    # Metrics thresholds
    min_test_coverage: float = 0.0
    min_win_rate: float = 0.0
    max_drawdown: float = 1.0
    min_sharpe_ratio: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "stage": self.stage.value,
            "description": self.description,
            "required": self.required,
            "requires_evidence": self.requires_evidence,
            "evidence_types": self.evidence_types,
            "thresholds": {
                "min_test_coverage": self.min_test_coverage,
                "min_win_rate": self.min_win_rate,
                "max_drawdown": self.max_drawdown,
                "min_sharpe_ratio": self.min_sharpe_ratio,
            }
        }


class WorkflowManager:
    """
    Manages strategy workflows through all stages.
    
    Handles:
    - Stage transitions with validation
    - Evidence collection
    - Approval tracking
    - Compliance verification
    """
    
    def __init__(self):
        self._strategies: Dict[str, StrategyLifecycle] = {}
        self._requirements: Dict[WorkflowStage, List[ValidationRequirement]] = {}
        self._validators: Dict[str, Callable] = {}
        self._transition_callbacks: List[Callable] = []
        
        # Initialize default requirements
        self._initialize_requirements()
    
    def _initialize_requirements(self) -> None:
        """Initialize default validation requirements for each stage"""
        
        # Idea stage
        self._requirements[WorkflowStage.IDEA] = [
            ValidationRequirement(
                requirement_id="idea_desc",
                stage=WorkflowStage.IDEA,
                description="Strategy idea documented",
                evidence_types=["document"]
            ),
            ValidationRequirement(
                requirement_id="market_analysis",
                stage=WorkflowStage.IDEA,
                description="Market opportunity identified",
                evidence_types=["document", "analysis"]
            ),
        ]
        
        # Research stage
        self._requirements[WorkflowStage.RESEARCH] = [
            ValidationRequirement(
                requirement_id="research_doc",
                stage=WorkflowStage.RESEARCH,
                description="Research documentation completed",
                evidence_types=["document"]
            ),
            ValidationRequirement(
                requirement_id="backtest_results",
                stage=WorkflowStage.RESEARCH,
                description="Initial backtest results",
                evidence_types=["test_result", "metrics"]
            ),
        ]
        
        # Draft stage
        self._requirements[WorkflowStage.DRAFT] = [
            ValidationRequirement(
                requirement_id="draft_code",
                stage=WorkflowStage.DRAFT,
                description="Strategy code drafted",
                evidence_types=["document"]
            ),
            ValidationRequirement(
                requirement_id="design_doc",
                stage=WorkflowStage.DRAFT,
                description="Architecture design documented",
                evidence_types=["document", "diagram"]
            ),
        ]
        
        # Development stage
        self._requirements[WorkflowStage.DEVELOPMENT] = [
            ValidationRequirement(
                requirement_id="code_complete",
                stage=WorkflowStage.DEVELOPMENT,
                description="Core implementation complete",
                evidence_types=["document"]
            ),
            ValidationRequirement(
                requirement_id="unit_tests",
                stage=WorkflowStage.DEVELOPMENT,
                description="Unit tests passing",
                min_test_coverage=0.8,
                evidence_types=["test_result"]
            ),
        ]
        
        # Testing stage
        self._requirements[WorkflowStage.TESTING] = [
            ValidationRequirement(
                requirement_id="integration_tests",
                stage=WorkflowStage.TESTING,
                description="Integration tests passing",
                evidence_types=["test_result"]
            ),
            ValidationRequirement(
                requirement_id="stress_tests",
                stage=WorkflowStage.TESTING,
                description="Stress tests completed",
                evidence_types=["test_result", "report"]
            ),
            ValidationRequirement(
                requirement_id="test_coverage",
                stage=WorkflowStage.TESTING,
                min_test_coverage=0.9,
                description="Test coverage meets threshold",
                evidence_types=["test_result"]
            ),
        ]
        
        # Paper trading stage
        self._requirements[WorkflowStage.PAPER_TRADING] = [
            ValidationRequirement(
                requirement_id="paper_trading_period",
                stage=WorkflowStage.PAPER_TRADING,
                description="Minimum paper trading period",
                evidence_types=["metrics"]
            ),
            ValidationRequirement(
                requirement_id="paper_trading_results",
                stage=WorkflowStage.PAPER_TRADING,
                min_win_rate=0.4,
                max_drawdown=0.15,
                description="Paper trading performance meets criteria",
                evidence_types=["test_result", "metrics"]
            ),
        ]
        
        # Validation stage
        self._requirements[WorkflowStage.VALIDATION] = [
            ValidationRequirement(
                requirement_id="validation_results",
                stage=WorkflowStage.VALIDATION,
                description="Formal validation completed",
                evidence_types=["document", "test_result"]
            ),
            ValidationRequirement(
                requirement_id="risk_assessment",
                stage=WorkflowStage.VALIDATION,
                description="Risk assessment approved",
                evidence_types=["document"]
            ),
            ValidationRequirement(
                requirement_id="compliance_review",
                stage=WorkflowStage.VALIDATION,
                description="Compliance review passed",
                evidence_types=["document", "signature"]
            ),
        ]
        
        # Approval stage
        self._requirements[WorkflowStage.APPROVAL] = [
            ValidationRequirement(
                requirement_id="approval_signoff",
                stage=WorkflowStage.APPROVAL,
                description="Required approvals obtained",
                evidence_types=["signature"]
            ),
            ValidationRequirement(
                requirement_id="change_management",
                stage=WorkflowStage.APPROVAL,
                description="Change management process completed",
                evidence_types=["document"]
            ),
        ]
        
        # Production stage
        self._requirements[WorkflowStage.PRODUCTION] = [
            ValidationRequirement(
                requirement_id="deployment_record",
                stage=WorkflowStage.PRODUCTION,
                description="Deployment documented",
                evidence_types=["document"]
            ),
        ]
    
    def create_strategy(
        self,
        strategy_id: str,
        name: str,
        description: str,
        created_by: str,
        owner: str = "",
        team: str = ""
    ) -> StrategyLifecycle:
        """Create a new strategy lifecycle"""
        lifecycle = StrategyLifecycle(
            strategy_id=strategy_id,
            name=name,
            description=description,
            created_at=time.time(),
            created_by=created_by,
            current_stage=WorkflowStage.IDEA,
            owner=owner,
            team=team,
        )
        
        # Record initial stage
        lifecycle.stage_history.append({
            "stage": WorkflowStage.IDEA.value,
            "status": StageStatus.IN_PROGRESS.value,
            "started_at": time.time(),
        })
        
        self._strategies[strategy_id] = lifecycle
        logger.info(f"Created strategy lifecycle: {strategy_id}")
        
        return lifecycle
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategyLifecycle]:
        """Get strategy lifecycle"""
        return self._strategies.get(strategy_id)
    
    def get_all_strategies(self) -> List[StrategyLifecycle]:
        """Get all strategies"""
        return list(self._strategies.values())
    
    def get_strategies_by_stage(self, stage: WorkflowStage) -> List[StrategyLifecycle]:
        """Get strategies in a specific stage"""
        return [
            s for s in self._strategies.values()
            if s.current_stage == stage
        ]
    
    def transition_to(
        self,
        strategy_id: str,
        target_stage: WorkflowStage,
        triggered_by: str,
        reason: str = "",
        evidence: Optional[Dict[str, Any]] = None,
        version_info: Optional[Dict[str, Any]] = None
    ) -> Optional[StageTransition]:
        """
        Transition strategy to a new stage.
        
        Validates requirements before allowing transition.
        """
        lifecycle = self._strategies.get(strategy_id)
        if not lifecycle:
            logger.error(f"Strategy not found: {strategy_id}")
            return None
        
        # Validate transition
        if not lifecycle.current_stage.can_transition_to(target_stage):
            logger.warning(f"Invalid transition: {lifecycle.current_stage} -> {target_stage}")
            return None
        
        # Check requirements for target stage
        validation = self.validate_requirements(strategy_id, target_stage)
        if not validation["can_transition"]:
            logger.warning(f"Requirements not met for {target_stage}: {validation['missing']}")
            return None
        
        # Create transition record
        transition = StageTransition(
            transition_id=self._generate_id(),
            strategy_id=strategy_id,
            from_stage=lifecycle.current_stage,
            to_stage=target_stage,
            timestamp=time.time(),
            triggered_by=triggered_by,
            reason=reason,
            evidence=evidence or {},
        )
        
        # Update lifecycle
        old_stage = lifecycle.current_stage
        
        # Complete old stage
        for entry in lifecycle.stage_history:
            if entry.get("stage") == old_stage.value and entry.get("status") == StageStatus.IN_PROGRESS.value:
                entry["status"] = StageStatus.COMPLETED.value
                entry["completed_at"] = time.time()
                break
        
        # Add new stage
        lifecycle.stage_history.append({
            "stage": target_stage.value,
            "status": StageStatus.IN_PROGRESS.value,
            "started_at": time.time(),
            "transition_id": transition.transition_id,
        })
        
        lifecycle.current_stage = target_stage
        
        # Add version if provided
        if version_info:
            lifecycle.versions.append(StrategyVersion(
                version=version_info.get("version", f"v{len(lifecycle.versions) + 1}"),
                created_at=time.time(),
                created_by=triggered_by,
                changes=version_info.get("changes", ""),
                evidence=version_info.get("evidence", {}),
            ))
        
        # Notify callbacks
        for callback in self._transition_callbacks:
            try:
                callback(transition, lifecycle)
            except Exception as e:
                logger.error(f"Transition callback error: {e}")
        
        logger.info(f"Strategy {strategy_id} transitioned: {old_stage} -> {target_stage}")
        return transition
    
    def validate_requirements(
        self,
        strategy_id: str,
        stage: WorkflowStage
    ) -> Dict[str, Any]:
        """
        Validate requirements for a stage.
        
        Returns dict with:
        - can_transition: bool
        - requirements: list of requirement status
        - missing: list of missing requirements
        """
        lifecycle = self._strategies.get(strategy_id)
        if not lifecycle:
            return {"can_transition": False, "requirements": [], "missing": ["Strategy not found"]}
        
        requirements = self._requirements.get(stage, [])
        results = []
        missing = []
        
        for req in requirements:
            # Check if evidence exists
            has_evidence = False
            if req.requires_evidence:
                # Check compliance records
                matching_records = [
                    r for r in lifecycle.compliance_records
                    if r.requirement == req.description
                ]
                has_evidence = any(r.verified for r in matching_records)
            else:
                has_evidence = True
            
            # Check metrics thresholds
            meets_thresholds = True
            if req.min_win_rate > 0 and lifecycle.win_rate < req.min_win_rate:
                meets_thresholds = False
            if lifecycle.max_drawdown > req.max_drawdown:
                meets_thresholds = False
            if req.min_sharpe_ratio > 0 and lifecycle.sharpe_ratio < req.min_sharpe_ratio:
                meets_thresholds = False
            
            result = {
                "requirement_id": req.requirement_id,
                "description": req.description,
                "has_evidence": has_evidence,
                "meets_thresholds": meets_thresholds,
                "passed": has_evidence and meets_thresholds,
            }
            results.append(result)
            
            if not result["passed"]:
                missing.append(req.description)
        
        return {
            "can_transition": len(missing) == 0 or not any(r.required for r in requirements if not any(m in missing for m in [r.description])),
            "requirements": results,
            "missing": missing,
        }
    
    def get_stage_requirements(self, stage: WorkflowStage) -> List[ValidationRequirement]:
        """Get requirements for a stage"""
        return self._requirements.get(stage, [])
    
    def add_compliance_record(
        self,
        strategy_id: str,
        requirement: str,
        evidence_type: str,
        evidence: Dict[str, Any],
        submitted_by: str
    ) -> Optional[ComplianceRecord]:
        """Add compliance evidence record"""
        lifecycle = self._strategies.get(strategy_id)
        if not lifecycle:
            return None
        
        record = ComplianceRecord(
            record_id=self._generate_id(),
            strategy_id=strategy_id,
            requirement=requirement,
            evidence_type=evidence_type,
            evidence=evidence,
            submitted_at=time.time(),
            submitted_by=submitted_by,
        )
        
        lifecycle.compliance_records.append(record)
        return record
    
    def verify_compliance_record(
        self,
        strategy_id: str,
        record_id: str,
        verified_by: str
    ) -> bool:
        """Verify a compliance record"""
        lifecycle = self._strategies.get(strategy_id)
        if not lifecycle:
            return False
        
        for record in lifecycle.compliance_records:
            if record.record_id == record_id:
                record.verified = True
                record.verified_by = verified_by
                record.verified_at = time.time()
                return True
        
        return False
    
    def add_approval(
        self,
        strategy_id: str,
        stage: WorkflowStage,
        approver: str,
        decision: str,
        comments: str = "",
        conditions: Optional[List[str]] = None,
        signature: Optional[str] = None
    ) -> Optional[Approval]:
        """Add approval record"""
        lifecycle = self._strategies.get(strategy_id)
        if not lifecycle:
            return None
        
        approval = Approval(
            approval_id=self._generate_id(),
            stage=stage,
            approver=approver,
            timestamp=time.time(),
            decision=decision,
            comments=comments,
            conditions=conditions or [],
            signature=signature,
        )
        
        lifecycle.approvals.append(approval)
        return approval
    
    def get_strategy_history(self, strategy_id: str) -> Dict[str, Any]:
        """Get complete history of a strategy"""
        lifecycle = self._strategies.get(strategy_id)
        if not lifecycle:
            return {}
        
        return {
            "strategy": lifecycle.to_dict(),
            "stage_history": lifecycle.stage_history,
            "versions": [
                {
                    "version": v.version,
                    "created_at": v.created_at,
                    "created_by": v.created_by,
                    "changes": v.changes,
                }
                for v in lifecycle.versions
            ],
            "approvals": [
                {
                    "approval_id": a.approval_id,
                    "stage": a.stage.value,
                    "approver": a.approver,
                    "decision": a.decision,
                    "timestamp": a.timestamp,
                }
                for a in lifecycle.approvals
            ],
            "compliance_records": [
                {
                    "record_id": r.record_id,
                    "requirement": r.requirement,
                    "evidence_type": r.evidence_type,
                    "verified": r.verified,
                    "submitted_at": r.submitted_at,
                }
                for r in lifecycle.compliance_records
            ],
            "rollback_history": [
                {
                    "rollback_id": r.rollback_id,
                    "from_version": r.from_version,
                    "to_version": r.to_version,
                    "timestamp": r.timestamp,
                    "reason": r.reason,
                }
                for r in lifecycle.rollback_history
            ],
        }
    
    def on_transition(self, callback: Callable) -> None:
        """Register transition callback"""
        self._transition_callbacks.append(callback)
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        import uuid
        return str(uuid.uuid4())
