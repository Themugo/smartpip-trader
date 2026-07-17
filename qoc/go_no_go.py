"""
Go/No-Go Board
==============

Deployment gate decision system.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DeploymentDecision(Enum):
    """Deployment decision"""
    GO = "go"
    NO_GO = "no_go"
    CONDITIONAL_GO = "conditional_go"
    PENDING = "pending"


class GateStatus(Enum):
    """Gate status"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"


@dataclass
class Gate:
    """A deployment gate"""
    name: str
    description: str
    category: str  # technical, validation, risk, operational
    
    # Status
    status: GateStatus
    passed: bool
    
    # Details
    score: float
    threshold: float
    message: str
    
    # Evidence
    evidence: Dict[str, Any] = field(default_factory=dict)
    checks: List[Dict] = field(default_factory=list)
    
    # Blocking
    mandatory: bool = True
    blocked_reason: str = ""


@dataclass
class DeploymentScore:
    """Overall deployment score"""
    technical_score: float
    validation_score: float
    risk_score: float
    operational_score: float
    
    # Composite
    overall_score: float = 0
    deployment_recommendation: DeploymentDecision = DeploymentDecision.PENDING
    
    # Details
    gates_passed: int = 0
    gates_failed: int = 0
    gates_skipped: int = 0
    mandatory_failed: List[str] = field(default_factory=list)
    
    timestamp: float = field(default_factory=time.time)


class GoNoGoBoard:
    """
    Deployment gate decision system.
    
    Evaluates:
    - Technical Score
    - Validation Score
    - Risk Score
    - Operational Score
    
    Generates:
    - Deployment Recommendation
    - Required Actions
    - Evidence Summary
    - Production Checklist
    """
    
    def __init__(self):
        # Gates
        self._gates: Dict[str, Gate] = {}
        
        # Gate validators
        self._validators: Dict[str, Callable] = {}
        
        # Initialize default gates
        self._init_default_gates()
    
    def _init_default_gates(self) -> None:
        """Initialize default deployment gates"""
        
        # Technical gates
        self._gates["build_success"] = Gate(
            name="Build Success",
            description="Build completes successfully",
            category="technical",
            status=GateStatus.PENDING,
            passed=False,
            score=0,
            threshold=1.0,
            message="",
            mandatory=True,
        )
        
        self._gates["unit_tests"] = Gate(
            name="Unit Tests",
            description="All unit tests pass",
            category="technical",
            status=GateStatus.PENDING,
            passed=False,
            score=0,
            threshold=0.95,
            message="",
            mandatory=True,
        )
        
        self._gates["integration_tests"] = Gate(
            name="Integration Tests",
            description="All integration tests pass",
            category="technical",
            status=GateStatus.PENDING,
            passed=False,
            score=0,
            threshold=1.0,
            message="",
            mandatory=True,
        )
        
        self._gates["replay_consistency"] = Gate(
            name="Replay Consistency",
            description="Event replay produces consistent results",
            category="technical",
            status=GateStatus.PENDING,
            passed=False,
            score=0,
            threshold=0.95,
            message="",
            mandatory=True,
        )
        
        # Validation gates
        self._gates["walk_forward"] = Gate(
            name="Walk-Forward Validation",
            description="Strategy passes walk-forward analysis",
            category="validation",
            status=GateStatus.PENDING,
            passed=False,
            score=0,
            threshold=0.7,
            message="",
            mandatory=True,
        )
        
        self._gates["out_of_sample"] = Gate(
            name="Out-of-Sample Validation",
            description="Strategy passes OOS testing",
            category="validation",
            status=GateStatus.PENDING,
            passed=False,
            score=0,
            threshold=0.7,
            message="",
            mandatory=True,
        )
        
        self._gates["monte_carlo"] = Gate(
            name="Monte Carlo Analysis",
            description="Strategy passes Monte Carlo simulation",
            category="validation",
            status=GateStatus.PENDING,
            passed=False,
            score=0,
            threshold=0.8,
            message="",
            mandatory=True,
        )
        
        self._gates["statistical_validation"] = Gate(
            name="Statistical Validation",
            description="All statistical thresholds met",
            category="validation",
            status=GateStatus.PENDING,
            passed=False,
            score=0,
            threshold=0.8,
            message="",
            mandatory=True,
        )
        
        # Risk gates
        self._gates["max_drawdown"] = Gate(
            name="Maximum Drawdown",
            description="Drawdown within risk limits",
            category="risk",
            status=GateStatus.PENDING,
            passed=False,
            score=0,
            threshold=0.15,
            message="",
            mandatory=True,
        )
        
        self._gates["risk_evaluation"] = Gate(
            name="Risk Evaluation",
            description="Risk metrics acceptable",
            category="risk",
            status=GateStatus.PENDING,
            passed=False,
            score=0,
            threshold=0.7,
            message="",
            mandatory=True,
        )
        
        self._gates["model_drift"] = Gate(
            name="Model Drift Check",
            description="No significant model drift detected",
            category="risk",
            status=GateStatus.PENDING,
            passed=False,
            score=1.0,
            threshold=0.9,
            message="",
            mandatory=True,
        )
        
        # Operational gates
        self._gates["data_quality"] = Gate(
            name="Data Quality",
            description="Data quality checks pass",
            category="operational",
            status=GateStatus.PENDING,
            passed=False,
            score=0,
            threshold=0.8,
            message="",
            mandatory=True,
        )
        
        self._gates["monitoring"] = Gate(
            name="Monitoring Status",
            description="Monitoring is operational",
            category="operational",
            status=GateStatus.PENDING,
            passed=False,
            score=0,
            threshold=1.0,
            message="",
            mandatory=True,
        )
        
        self._gates["health_score"] = Gate(
            name="System Health",
            description="System health score acceptable",
            category="operational",
            status=GateStatus.PENDING,
            passed=False,
            score=0,
            threshold=0.8,
            message="",
            mandatory=True,
        )
        
        self._gates["paper_trading"] = Gate(
            name="Paper Trading",
            description="Paper trading performance acceptable",
            category="operational",
            status=GateStatus.PENDING,
            passed=False,
            score=0,
            threshold=0.7,
            message="",
            mandatory=False,
        )
    
    def register_validator(
        self,
        gate_name: str,
        validator_fn: Callable[[], Dict[str, Any]]
    ) -> None:
        """Register a gate validator"""
        self._validators[gate_name] = validator_fn
    
    def evaluate_gate(self, gate_name: str) -> Gate:
        """Evaluate a single gate"""
        if gate_name not in self._gates:
            raise ValueError(f"Unknown gate: {gate_name}")
        
        gate = self._gates[gate_name]
        
        if gate_name in self._validators:
            result = self._validators[gate_name]()
            gate.score = result.get("score", 0)
            gate.passed = gate.score >= gate.threshold
            gate.status = GateStatus.PASSED if gate.passed else GateStatus.FAILED
            gate.message = result.get("message", "")
            gate.evidence = result.get("evidence", {})
            gate.checks = result.get("checks", [])
        else:
            gate.status = GateStatus.SKIPPED
            gate.message = "No validator registered"
        
        return gate
    
    def evaluate_all(self) -> DeploymentScore:
        """Evaluate all gates and generate deployment score"""
        
        # Evaluate all gates
        for gate_name in self._gates:
            self.evaluate_gate(gate_name)
        
        # Calculate scores by category
        categories = ["technical", "validation", "risk", "operational"]
        scores = {}
        
        for category in categories:
            category_gates = [
                g for g in self._gates.values()
                if g.category == category and g.status != GateStatus.SKIPPED
            ]
            
            if category_gates:
                scores[category] = sum(g.score for g in category_gates) / len(category_gates)
            else:
                scores[category] = 1.0
        
        # Count gates
        gates_passed = sum(1 for g in self._gates.values() if g.status == GateStatus.PASSED)
        gates_failed = sum(1 for g in self._gates.values() if g.status == GateStatus.FAILED)
        gates_skipped = sum(1 for g in self._gates.values() if g.status == GateStatus.SKIPPED)
        
        # Mandatory failures
        mandatory_failed = [
            g.name for g in self._gates.values()
            if g.status == GateStatus.FAILED and g.mandatory
        ]
        
        # Overall score (weighted average)
        weights = {
            "technical": 0.25,
            "validation": 0.35,
            "risk": 0.25,
            "operational": 0.15,
        }
        
        overall = sum(scores.get(c, 0) * weights[c] for c in categories)
        
        # Decision
        if mandatory_failed:
            recommendation = DeploymentDecision.NO_GO
        elif gates_failed > 0:
            recommendation = DeploymentDecision.CONDITIONAL_GO
        else:
            recommendation = DeploymentDecision.GO
        
        return DeploymentScore(
            technical_score=scores.get("technical", 0),
            validation_score=scores.get("validation", 0),
            risk_score=scores.get("risk", 0),
            operational_score=scores.get("operational", 0),
            overall_score=overall,
            deployment_recommendation=recommendation,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            gates_skipped=gates_skipped,
            mandatory_failed=mandatory_failed,
        )
    
    def get_gates_by_category(self, category: str) -> List[Gate]:
        """Get gates by category"""
        return [g for g in self._gates.values() if g.category == category]
    
    def get_gate(self, gate_name: str) -> Optional[Gate]:
        """Get a gate by name"""
        return self._gates.get(gate_name)
    
    def generate_deployment_report(self) -> Dict[str, Any]:
        """Generate comprehensive deployment report"""
        score = self.evaluate_all()
        
        report = {
            "timestamp": time.time(),
            
            # Recommendation
            "decision": score.deployment_recommendation.value,
            "decision_emoji": {
                DeploymentDecision.GO: "🟢",
                DeploymentDecision.NO_GO: "🔴",
                DeploymentDecision.CONDITIONAL_GO: "🟡",
                DeploymentDecision.PENDING: "⚪",
            }.get(score.deployment_recommendation, "⚪"),
            
            # Scores
            "scores": {
                "technical": score.technical_score,
                "validation": score.validation_score,
                "risk": score.risk_score,
                "operational": score.operational_score,
                "overall": score.overall_score,
            },
            
            # Gate summary
            "gates": {
                "total": len(self._gates),
                "passed": score.gates_passed,
                "failed": score.gates_failed,
                "skipped": score.gates_skipped,
            },
            
            # Failed mandatory gates
            "mandatory_failures": score.mandatory_failed,
            
            # Gates by category
            "by_category": {
                category: [
                    {
                        "name": g.name,
                        "status": g.status.value,
                        "passed": g.passed,
                        "score": g.score,
                        "threshold": g.threshold,
                        "message": g.message,
                        "mandatory": g.mandatory,
                    }
                    for g in self._gates.values()
                    if g.category == category
                ]
                for category in ["technical", "validation", "risk", "operational"]
            },
            
            # Evidence summary
            "evidence_summary": self._get_evidence_summary(),
            
            # Required actions
            "required_actions": self._get_required_actions(score),
            
            # Production checklist
            "production_checklist": self._get_production_checklist(score),
        }
        
        return report
    
    def _get_evidence_summary(self) -> List[str]:
        """Get evidence summary"""
        summary = []
        
        for gate in self._gates.values():
            if gate.evidence:
                summary.append(f"{gate.name}: {len(gate.evidence)} evidence items")
        
        return summary
    
    def _get_required_actions(self, score: DeploymentScore) -> List[str]:
        """Get required actions based on results"""
        actions = []
        
        if score.deployment_recommendation == DeploymentDecision.NO_GO:
            actions.append("BLOCKED: Fix all mandatory gate failures before deployment")
            for gate_name in score.mandatory_failed:
                actions.append(f"- Fix: {gate_name}")
        
        elif score.deployment_recommendation == DeploymentDecision.CONDITIONAL_GO:
            actions.append("Review failed gates and document acceptance")
        
        if score.validation_score < 0.8:
            actions.append("Consider additional validation before production")
        
        if score.risk_score < 0.8:
            actions.append("Review risk metrics - additional risk analysis recommended")
        
        return actions
    
    def _get_production_checklist(self, score: DeploymentScore) -> List[str]:
        """Get production deployment checklist"""
        checklist = [
            "□ Verify build artifacts",
            "□ Confirm database migrations",
            "□ Verify configuration changes",
            "□ Review rollback plan",
            "□ Confirm monitoring alerts",
            "□ Notify stakeholders",
            "□ Schedule deployment window",
        ]
        
        if score.deployment_recommendation == DeploymentDecision.GO:
            checklist.append("☑ All gates passed - ready for deployment")
        
        return checklist
