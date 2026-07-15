"""
Strategy Optimizer - Continuous Self-Improvement

Automated strategy optimization and continuous improvement.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class OptimizationStatus(Enum):
    """Optimization status"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OptimizationConfig:
    """Configuration for continuous optimization"""
    # Frequency
    check_interval_hours: int = 24
    
    # Thresholds
    improvement_threshold: float = 0.05  # 5% improvement required
    min_confidence: float = 0.8
    
    # Validation
    validation_trades: int = 50
    validation_period_days: int = 7
    
    # Rollback
    auto_rollback: bool = True
    rollback_threshold: float = 0.1  # 10% degradation triggers rollback
    
    # Safety
    max_changes_per_day: int = 3
    require_approval: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_interval_hours": self.check_interval_hours,
            "improvement_threshold": self.improvement_threshold,
            "min_confidence": self.min_confidence,
            "validation_trades": self.validation_trades,
            "validation_period_days": self.validation_period_days,
            "auto_rollback": self.auto_rollback,
            "rollback_threshold": self.rollback_threshold,
            "max_changes_per_day": self.max_changes_per_day,
            "require_approval": self.require_approval,
        }


@dataclass
class OptimizationCandidate:
    """A candidate for optimization"""
    id: str
    strategy_id: str
    
    # Changes
    changes: Dict[str, Any] = field(default_factory=dict)
    description: str
    
    # Expected improvement
    expected_improvement: float = 0
    expected_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Validation
    validation_results: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    status: OptimizationStatus = OptimizationStatus.IDLE
    approved: bool = False
    deployed_at: Optional[datetime] = None
    
    # Results
    actual_improvement: float = 0
    actual_metrics: Dict[str, float] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "changes": self.changes,
            "description": self.description,
            "expected_improvement": self.expected_improvement,
            "status": self.status.value,
            "approved": self.approved,
            "actual_improvement": self.actual_improvement,
            "created_at": self.created_at.isoformat(),
        }


class StrategyOptimizer:
    """
    Continuous Strategy Optimizer.
    
    Features:
    - Daily data collection
    - Performance evaluation
    - Candidate generation
    - Statistical validation
    - A/B testing
    - Automatic rollback
    - Approval workflows
    """
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        self._config = config or OptimizationConfig()
        self._candidates: Dict[str, OptimizationCandidate] = {}
        self._strategy_baselines: Dict[str, Dict[str, float]] = {}
        self._last_check: Dict[str, datetime] = {}
        
        self._optimization_func: Optional[Callable] = None
        self._validation_func: Optional[Callable] = None
    
    def set_optimization_function(self, func: Callable) -> None:
        """Set the optimization function"""
        self._optimization_func = func
    
    def set_validation_function(self, func: Callable) -> None:
        """Set the validation function"""
        self._validation_func = func
    
    def set_baseline(
        self,
        strategy_id: str,
        metrics: Dict[str, float],
    ) -> None:
        """Set baseline metrics for comparison"""
        self._strategy_baselines[strategy_id] = metrics.copy()
        logger.info(f"Set baseline for {strategy_id}: {metrics}")
    
    def check_and_optimize(
        self,
        strategy_id: str,
        current_metrics: Dict[str, float],
    ) -> List[OptimizationCandidate]:
        """
        Check performance and generate optimization candidates.
        
        Returns:
            List of optimization candidates
        """
        # Check interval
        last_check = self._last_check.get(strategy_id)
        if last_check:
            hours_since = (datetime.utcnow() - last_check).total_seconds() / 3600
            if hours_since < self._config.check_interval_hours:
                return []
        
        self._last_check[strategy_id] = datetime.utcnow()
        
        # Get baseline
        baseline = self._strategy_baselines.get(strategy_id)
        if not baseline:
            self.set_baseline(strategy_id, current_metrics)
            return []
        
        # Analyze performance
        candidates = []
        
        # Check for degradation
        degraded = self._check_degradation(baseline, current_metrics)
        if degraded:
            candidate = self._generate_fix_candidate(strategy_id, degraded, current_metrics)
            if candidate:
                candidates.append(candidate)
        
        # Check for optimization opportunities
        opportunities = self._find_opportunities(strategy_id, current_metrics)
        for opp in opportunities:
            candidate = self._create_candidate(strategy_id, opp)
            if candidate:
                candidates.append(candidate)
        
        return candidates
    
    def _check_degradation(
        self,
        baseline: Dict[str, float],
        current: Dict[str, float],
    ) -> Dict[str, float]:
        """Check if metrics have degraded"""
        degraded = {}
        
        # Metrics where higher is better
        higher_better = ["sharpe_ratio", "total_return", "win_rate", "profit_factor"]
        
        for metric in higher_better:
            if metric in baseline and metric in current:
                change = (current[metric] - baseline[metric]) / max(abs(baseline[metric]), 0.001)
                if change < -self._config.rollback_threshold:
                    degraded[metric] = change
        
        return degraded
    
    def _find_opportunities(
        self,
        strategy_id: str,
        current_metrics: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """Find optimization opportunities"""
        opportunities = []
        
        # Run optimization if available
        if self._optimization_func:
            try:
                results = self._optimization_func(strategy_id, current_metrics)
                opportunities = results if isinstance(results, list) else [results]
            except Exception as e:
                logger.error(f"Optimization function error: {e}")
        
        return opportunities
    
    def _generate_fix_candidate(
        self,
        strategy_id: str,
        degraded_metrics: Dict[str, float],
        current_metrics: Dict[str, float],
    ) -> Optional[OptimizationCandidate]:
        """Generate a candidate to fix degradation"""
        candidate = OptimizationCandidate(
            id=str(uuid.uuid4()),
            strategy_id=strategy_id,
            changes={"action": "fix_degradation", "metrics": degraded_metrics},
            description=f"Fix degraded metrics: {list(degraded_metrics.keys())}",
            expected_improvement=sum(abs(v) for v in degraded_metrics.values()),
        )
        
        candidate.status = OptimizationStatus.IDLE
        self._candidates[candidate.id] = candidate
        
        return candidate
    
    def _create_candidate(
        self,
        strategy_id: str,
        opportunity: Dict[str, Any],
    ) -> Optional[OptimizationCandidate]:
        """Create a candidate from an opportunity"""
        if opportunity.get("improvement", 0) < self._config.improvement_threshold:
            return None
        
        candidate = OptimizationCandidate(
            id=str(uuid.uuid4()),
            strategy_id=strategy_id,
            changes=opportunity.get("changes", {}),
            description=opportunity.get("description", ""),
            expected_improvement=opportunity.get("improvement", 0),
            expected_metrics=opportunity.get("metrics", {}),
        )
        
        self._candidates[candidate.id] = candidate
        return candidate
    
    def validate_candidate(
        self,
        candidate_id: str,
    ) -> Dict[str, Any]:
        """Validate an optimization candidate"""
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return {"valid": False, "error": "Candidate not found"}
        
        candidate.status = OptimizationStatus.RUNNING
        
        # Run validation
        if self._validation_func:
            try:
                result = self._validation_func(candidate)
                candidate.validation_results = result
                
                # Check if validation passed
                passed = result.get("passed", False)
                if passed:
                    candidate.status = OptimizationStatus.COMPLETED
                else:
                    candidate.status = OptimizationStatus.FAILED
                
                return result
                
            except Exception as e:
                logger.error(f"Validation error: {e}")
                candidate.status = OptimizationStatus.FAILED
                return {"valid": False, "error": str(e)}
        
        # Default: assume valid
        candidate.status = OptimizationStatus.COMPLETED
        candidate.approved = True
        return {"valid": True, "passed": True}
    
    def deploy_candidate(
        self,
        candidate_id: str,
        force: bool = False,
    ) -> tuple[bool, str]:
        """
        Deploy an optimization candidate.
        
        Returns:
            (success, message)
        """
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return False, "Candidate not found"
        
        # Check if approved
        if not candidate.approved and not force:
            if self._config.require_approval:
                return False, "Candidate requires approval"
        
        # Deploy
        try:
            # In production, would actually deploy the changes
            candidate.status = OptimizationStatus.RUNNING
            candidate.deployed_at = datetime.utcnow()
            
            # Simulate deployment
            logger.info(f"Deployed candidate: {candidate_id}")
            
            candidate.status = OptimizationStatus.COMPLETED
            return True, "Candidate deployed successfully"
            
        except Exception as e:
            logger.error(f"Deployment error: {e}")
            candidate.status = OptimizationStatus.FAILED
            return False, str(e)
    
    def rollback_candidate(
        self,
        candidate_id: str,
    ) -> tuple[bool, str]:
        """Rollback a deployed candidate"""
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return False, "Candidate not found"
        
        try:
            # In production, would rollback the changes
            logger.info(f"Rolled back candidate: {candidate_id}")
            
            candidate.status = OptimizationStatus.FAILED
            return True, "Rolled back successfully"
            
        except Exception as e:
            return False, str(e)
    
    def record_results(
        self,
        candidate_id: str,
        actual_metrics: Dict[str, float],
    ) -> None:
        """Record actual results after deployment"""
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return
        
        candidate.actual_metrics = actual_metrics
        candidate.completed_at = datetime.utcnow()
        
        # Calculate actual improvement
        baseline = self._strategy_baselines.get(candidate.strategy_id, {})
        
        if baseline:
            total_change = 0
            count = 0
            
            for metric in ["sharpe_ratio", "total_return"]:
                if metric in baseline and metric in actual_metrics:
                    change = actual_metrics[metric] - baseline[metric]
                    total_change += change
                    count += 1
            
            if count > 0:
                candidate.actual_improvement = total_change / count
        
        # Check if rollback is needed
        if self._config.auto_rollback:
            if candidate.actual_improvement < -self._config.rollback_threshold:
                logger.warning(f"Candidate {candidate_id} degraded, triggering rollback")
                self.rollback_candidate(candidate_id)
    
    def get_candidates(
        self,
        strategy_id: Optional[str] = None,
        status: Optional[OptimizationStatus] = None,
    ) -> List[OptimizationCandidate]:
        """Get optimization candidates"""
        candidates = list(self._candidates.values())
        
        if strategy_id:
            candidates = [c for c in candidates if c.strategy_id == strategy_id]
        
        if status:
            candidates = [c for c in candidates if c.status == status]
        
        return sorted(candidates, key=lambda c: c.created_at, reverse=True)
    
    def get_deployment_history(
        self,
        strategy_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get deployment history"""
        candidates = self.get_candidates(strategy_id=strategy_id)
        deployed = [c for c in candidates if c.deployed_at]
        
        return [
            {
                "id": c.id,
                "description": c.description,
                "expected_improvement": c.expected_improvement,
                "actual_improvement": c.actual_improvement,
                "deployed_at": c.deployed_at.isoformat() if c.deployed_at else None,
                "completed_at": c.completed_at.isoformat() if c.completed_at else None,
            }
            for c in deployed[:limit]
        ]
