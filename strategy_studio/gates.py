"""
Quality Gates - Pre-Deployment Validation

Automated validation checks before strategy deployment.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class GateStatus(Enum):
    """Gate check status"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"


class GateCategory(Enum):
    """Categories of quality gates"""
    COMPILATION = "compilation"
    TESTING = "testing"
    PERFORMANCE = "performance"
    RISK = "risk"
    CALIBRATION = "calibration"
    REPRODUCIBILITY = "reproducibility"
    DOCUMENTATION = "documentation"


@dataclass
class GateCheck:
    """A single quality gate check"""
    id: str
    name: str
    category: GateCategory
    description: str
    
    # Requirements
    is_mandatory: bool = True
    threshold: Optional[float] = None
    comparator: str = ">="  # >=, <=, ==, !=, >, <
    
    # Result
    status: GateStatus = GateStatus.PENDING
    value: Optional[float] = None
    message: str = ""
    
    # Metadata
    checked_at: Optional[datetime] = None
    
    def evaluate(self, value: float) -> bool:
        """Evaluate if the value passes the gate"""
        if self.threshold is None:
            return True
        
        if self.comparator == ">=":
            return value >= self.threshold
        elif self.comparator == "<=":
            return value <= self.threshold
        elif self.comparator == "==":
            return value == self.threshold
        elif self.comparator == "!=":
            return value != self.threshold
        elif self.comparator == ">":
            return value > self.threshold
        elif self.comparator == "<":
            return value < self.threshold
        
        return True


@dataclass
class GateReport:
    """Report from quality gate validation"""
    strategy_id: str
    strategy_name: str
    
    # All gates
    gates: List[GateCheck] = field(default_factory=list)
    
    # Overall result
    is_ready: bool = False
    blocked_by: List[str] = field(default_factory=list)
    
    # Summary
    total_gates: int = 0
    passed_gates: int = 0
    failed_gates: int = 0
    warning_gates: int = 0
    skipped_gates: int = 0
    
    # Generated at
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "is_ready": self.is_ready,
            "blocked_by": self.blocked_by,
            "total_gates": self.total_gates,
            "passed_gates": self.passed_gates,
            "failed_gates": self.failed_gates,
            "warning_gates": self.warning_gates,
            "skipped_gates": self.skipped_gates,
            "gates": [
                {
                    "id": g.id,
                    "name": g.name,
                    "category": g.category.value,
                    "status": g.status.value,
                    "is_mandatory": g.is_mandatory,
                    "message": g.message,
                    "checked_at": g.checked_at.isoformat() if g.checked_at else None,
                }
                for g in self.gates
            ],
            "checked_at": self.checked_at.isoformat(),
        }


class QualityGates:
    """
    Quality Gates for pre-deployment validation.
    
    Gates:
    - Compilation: Strategy must compile without errors
    - Testing: All tests must pass
    - Performance: Metrics must meet thresholds
    - Risk: Drawdown and risk must be acceptable
    - Calibration: Confidence must be calibrated
    - Reproducibility: Results must be reproducible
    - Documentation: Required docs must be present
    """
    
    # Default gates for production deployment
    DEFAULT_GATES = [
        GateCheck(
            id="compilation_success",
            name="Successful Compilation",
            category=GateCategory.COMPILATION,
            description="Strategy must compile without errors",
            is_mandatory=True,
        ),
        GateCheck(
            id="test_coverage",
            name="Test Coverage",
            category=GateCategory.TESTING,
            description="At least 80% test coverage",
            is_mandatory=True,
            threshold=80,
            comparator=">=",
        ),
        GateCheck(
            id="min_trades",
            name="Minimum Trades",
            category=GateCategory.TESTING,
            description="At least 50 trades in backtest",
            is_mandatory=True,
            threshold=50,
            comparator=">=",
        ),
        GateCheck(
            id="sharpe_ratio",
            name="Sharpe Ratio",
            category=GateCategory.PERFORMANCE,
            description="Sharpe ratio must be at least 1.0",
            is_mandatory=True,
            threshold=1.0,
            comparator=">=",
        ),
        GateCheck(
            id="max_drawdown",
            name="Maximum Drawdown",
            category=GateCategory.RISK,
            description="Drawdown must be below 15%",
            is_mandatory=True,
            threshold=15,
            comparator="<=",
        ),
        GateCheck(
            id="win_rate",
            name="Win Rate",
            category=GateCategory.PERFORMANCE,
            description="Win rate must be above 40%",
            is_mandatory=False,
            threshold=40,
            comparator=">=",
        ),
        GateCheck(
            id="calibration_score",
            name="Calibration Score",
            category=GateCategory.CALIBRATION,
            description="Confidence calibration must be above 70%",
            is_mandatory=True,
            threshold=70,
            comparator=">=",
        ),
        GateCheck(
            id="profit_factor",
            name="Profit Factor",
            category=GateCategory.PERFORMANCE,
            description="Profit factor must be above 1.2",
            is_mandatory=False,
            threshold=1.2,
            comparator=">=",
        ),
        GateCheck(
            id="documentation_complete",
            name="Documentation Complete",
            category=GateCategory.DOCUMENTATION,
            description="Strategy must have complete documentation",
            is_mandatory=True,
        ),
        GateCheck(
            id="reproducibility",
            name="Reproducibility Check",
            category=GateCategory.REPRODUCIBILITY,
            description="Results must be reproducible",
            is_mandatory=True,
        ),
    ]
    
    def __init__(self):
        self._custom_gates: List[GateCheck] = []
    
    def run_gates(
        self,
        strategy_id: str,
        strategy_name: str,
        validation_data: Dict[str, Any],
        gates: Optional[List[GateCheck]] = None,
    ) -> GateReport:
        """
        Run all quality gates.
        
        Args:
            strategy_id: Strategy ID
            strategy_name: Strategy name
            validation_data: Data for validation
            gates: Optional custom gates (uses defaults if not provided)
            
        Returns:
            GateReport with results
        """
        gates = gates or self.DEFAULT_GATES + self._custom_gates
        
        report = GateReport(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            gates=[],
        )
        
        for gate in gates:
            # Create copy for this run
            gate_check = GateCheck(
                id=gate.id,
                name=gate.name,
                category=gate.category,
                description=gate.description,
                is_mandatory=gate.is_mandatory,
                threshold=gate.threshold,
                comparator=gate.comparator,
            )
            
            # Run the gate check
            result = self._run_gate(gate, validation_data)
            
            gate_check.status = result["status"]
            gate_check.value = result.get("value")
            gate_check.message = result.get("message", "")
            gate_check.checked_at = datetime.now(timezone.utc)
            
            report.gates.append(gate_check)
            
            # Update counters
            if gate_check.status == GateStatus.PASSED:
                report.passed_gates += 1
            elif gate_check.status == GateStatus.FAILED:
                report.failed_gates += 1
                if gate_check.is_mandatory:
                    report.blocked_by.append(gate_check.name)
            elif gate_check.status == GateStatus.WARNING:
                report.warning_gates += 1
            elif gate_check.status == GateStatus.SKIPPED:
                report.skipped_gates += 1
        
        report.total_gates = len(report.gates)
        report.is_ready = len(report.blocked_by) == 0
        
        logger.info(
            f"Quality gates for {strategy_name}: "
            f"{report.passed_gates}/{report.total_gates} passed, "
            f"Ready={report.is_ready}"
        )
        
        return report
    
    def _run_gate(
        self,
        gate: GateCheck,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run a single gate check"""
        # Map gate IDs to data sources
        data_map = {
            "compilation_success": ("compilation", "success", True),
            "test_coverage": ("metrics", "test_coverage", 0),
            "min_trades": ("metrics", "total_trades", 0),
            "sharpe_ratio": ("metrics", "sharpe_ratio", 0),
            "max_drawdown": ("metrics", "max_drawdown", 100),
            "win_rate": ("metrics", "win_rate", 0),
            "calibration_score": ("metrics", "calibration_score", 0),
            "profit_factor": ("metrics", "profit_factor", 0),
            "documentation_complete": ("documentation", "complete", False),
            "reproducibility": ("reproducibility", "verified", False),
        }
        
        if gate.id in data_map:
            section, key, default = data_map[gate.id]
            
            if section == "metrics":
                value = data.get("metrics", {}).get(key, default)
                
                passed = gate.evaluate(value) if gate.threshold else value == True
                
                return {
                    "status": GateStatus.PASSED if passed else GateStatus.FAILED,
                    "value": value,
                    "message": f"{gate.name}: {value}" + (
                        " ✓" if passed else f" (required: {gate.comparator} {gate.threshold})"
                    ),
                }
            
            elif section == "compilation":
                success = data.get("compilation", {}).get("success", False)
                return {
                    "status": GateStatus.PASSED if success else GateStatus.FAILED,
                    "value": 1 if success else 0,
                    "message": f"Compilation: {'Success' if success else 'Failed'}",
                }
            
            elif section == "documentation":
                complete = data.get("documentation", {}).get("complete", False)
                return {
                    "status": GateStatus.PASSED if complete else GateStatus.FAILED,
                    "value": 1 if complete else 0,
                    "message": f"Documentation: {'Complete' if complete else 'Incomplete'}",
                }
            
            elif section == "reproducibility":
                verified = data.get("reproducibility", {}).get("verified", False)
                return {
                    "status": GateStatus.PASSED if verified else GateStatus.FAILED,
                    "value": 1 if verified else 0,
                    "message": f"Reproducibility: {'Verified' if verified else 'Not Verified'}",
                }
        
        # Unknown gate - pass with warning
        return {
            "status": GateStatus.WARNING,
            "value": None,
            "message": f"Unknown gate: {gate.id}",
        }
    
    def add_custom_gate(self, gate: GateCheck) -> None:
        """Add a custom gate"""
        self._custom_gates.append(gate)
    
    def remove_custom_gate(self, gate_id: str) -> bool:
        """Remove a custom gate"""
        for i, gate in enumerate(self._custom_gates):
            if gate.id == gate_id:
                del self._custom_gates[i]
                return True
        return False
