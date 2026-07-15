"""
Acceptance Criteria
=================

Defines and evaluates acceptance criteria for strategy promotion.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


class CriterionType(Enum):
    """Types of acceptance criteria"""
    PERFORMANCE = "performance"
    RISK = "risk"
    STATISTICAL = "statistical"
    CONSISTENCY = "consistency"
    QUALITY = "quality"


class ComparisonOperator(Enum):
    """Comparison operators for thresholds"""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUAL = "=="


@dataclass
class Criterion:
    """A single acceptance criterion"""
    name: str
    criterion_type: CriterionType
    metric: str  # e.g., "sharpe_ratio", "max_drawdown"
    operator: ComparisonOperator
    threshold: float
    weight: float = 1.0
    description: str = ""
    
    def evaluate(self, value: float) -> bool:
        """Evaluate if value meets criterion"""
        if self.operator == ComparisonOperator.GREATER_THAN:
            return value > self.threshold
        elif self.operator == ComparisonOperator.LESS_THAN:
            return value < self.threshold
        elif self.operator == ComparisonOperator.GREATER_EQUAL:
            return value >= self.threshold
        elif self.operator == ComparisonOperator.LESS_EQUAL:
            return value <= self.threshold
        elif self.operator == ComparisonOperator.EQUAL:
            return abs(value - self.threshold) < 0.0001
        return False


@dataclass
class AcceptanceResult:
    """Result of evaluating acceptance criteria"""
    criteria: List[Criterion]
    results: Dict[str, bool]  # criterion_name -> passed
    scores: Dict[str, float]  # criterion_name -> score
    weighted_score: float
    overall_passed: bool
    failed_criteria: List[str]
    evaluated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "criteria": [
                {"name": c.name, "type": c.criterion_type.value, "threshold": c.threshold}
                for c in self.criteria
            ],
            "results": self.results,
            "scores": self.scores,
            "weighted_score": self.weighted_score,
            "overall_passed": self.overall_passed,
            "failed_criteria": self.failed_criteria,
            "evaluated_at": self.evaluated_at.isoformat()
        }


class AcceptanceCriteria:
    """
    Defines and evaluates acceptance criteria for strategy promotion.
    
    Only strategies meeting all criteria can be promoted to production.
    """
    
    def __init__(self):
        self.criteria: List[Criterion] = []
        self._setup_default_criteria()
    
    def _setup_default_criteria(self) -> None:
        """Set up default acceptance criteria"""
        # Performance criteria
        self.add_criterion(Criterion(
            name="sharpe_ratio",
            criterion_type=CriterionType.PERFORMANCE,
            metric="sharpe_ratio",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=0.5,
            weight=2.0,
            description="Sharpe ratio must be > 0.5"
        ))
        
        self.add_criterion(Criterion(
            name="total_return",
            criterion_type=CriterionType.PERFORMANCE,
            metric="total_return",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=0.0,
            weight=1.5,
            description="Total return must be positive"
        ))
        
        # Risk criteria
        self.add_criterion(Criterion(
            name="max_drawdown",
            criterion_type=CriterionType.RISK,
            metric="max_drawdown",
            operator=ComparisonOperator.LESS_THAN,
            threshold=0.20,
            weight=2.0,
            description="Max drawdown must be < 20%"
        ))
        
        self.add_criterion(Criterion(
            name="daily_var_95",
            criterion_type=CriterionType.RISK,
            metric="var_95",
            operator=ComparisonOperator.LESS_THAN,
            threshold=0.03,
            weight=1.5,
            description="95% VaR must be < 3%"
        ))
        
        # Statistical criteria
        self.add_criterion(Criterion(
            name="win_rate",
            criterion_type=CriterionType.STATISTICAL,
            metric="win_rate",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=0.50,
            weight=1.0,
            description="Win rate must be > 50%"
        ))
        
        self.add_criterion(Criterion(
            name="statistical_significance",
            criterion_type=CriterionType.STATISTICAL,
            metric="p_value",
            operator=ComparisonOperator.LESS_THAN,
            threshold=0.05,
            weight=1.5,
            description="Results must be statistically significant (p < 0.05)"
        ))
        
        # Consistency criteria
        self.add_criterion(Criterion(
            name="walk_forward_consistency",
            criterion_type=CriterionType.CONSISTENCY,
            metric="consistency_ratio",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=0.6,
            weight=1.5,
            description="Walk-forward consistency must be > 60%"
        ))
        
        self.add_criterion(Criterion(
            name="calibration_accuracy",
            criterion_type=CriterionType.QUALITY,
            metric="calibration_error",
            operator=ComparisonOperator.LESS_THAN,
            threshold=0.10,
            weight=1.0,
            description="Calibration error must be < 10%"
        ))
    
    def add_criterion(self, criterion: Criterion) -> None:
        """Add a criterion"""
        self.criteria.append(criterion)
        logger.info(f"Added criterion: {criterion.name}")
    
    def remove_criterion(self, name: str) -> bool:
        """Remove a criterion by name"""
        for i, c in enumerate(self.criteria):
            if c.name == name:
                self.criteria.pop(i)
                logger.info(f"Removed criterion: {name}")
                return True
        return False
    
    def evaluate(self, metrics: Dict[str, float]) -> AcceptanceResult:
        """
        Evaluate metrics against acceptance criteria.
        
        Args:
            metrics: Dict of metric_name -> value
            
        Returns:
            AcceptanceResult with pass/fail for each criterion
        """
        results = {}
        scores = {}
        failed = []
        total_weight = 0.0
        weighted_sum = 0.0
        
        for criterion in self.criteria:
            metric_value = metrics.get(criterion.metric)
            
            if metric_value is None:
                results[criterion.name] = False
                scores[criterion.name] = 0.0
                failed.append(criterion.name)
                logger.warning(f"Criterion {criterion.name}: metric {criterion.metric} not found")
                continue
            
            passed = criterion.evaluate(metric_value)
            results[criterion.name] = passed
            
            # Calculate score (0-1)
            if passed:
                # Full score for passed criteria
                score = 1.0
            else:
                # Partial score based on how close to threshold
                if criterion.operator in [ComparisonOperator.GREATER_THAN, ComparisonOperator.GREATER_EQUAL]:
                    score = min(1.0, metric_value / criterion.threshold)
                else:
                    score = min(1.0, criterion.threshold / max(metric_value, 0.0001))
            
            scores[criterion.name] = score
            
            if not passed:
                failed.append(criterion.name)
            
            weighted_sum += score * criterion.weight
            total_weight += criterion.weight
        
        # Calculate weighted score
        weighted_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Overall pass requires all criteria to pass
        overall_passed = len(failed) == 0
        
        result = AcceptanceResult(
            criteria=self.criteria.copy(),
            results=results,
            scores=scores,
            weighted_score=weighted_score,
            overall_passed=overall_passed,
            failed_criteria=failed
        )
        
        logger.info(
            f"Acceptance evaluation: {'PASSED' if overall_passed else 'FAILED'} "
            f"(weighted_score={weighted_score:.2f})"
        )
        
        return result
    
    def get_criteria_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all criteria"""
        return [
            {
                "name": c.name,
                "type": c.criterion_type.value,
                "metric": c.metric,
                "operator": c.operator.value,
                "threshold": c.threshold,
                "weight": c.weight,
                "description": c.description
            }
            for c in self.criteria
        ]


class AcceptancePolicy:
    """
    Policy-based acceptance evaluation.
    
    Different environments (staging, production) may have different requirements.
    """
    
    def __init__(self):
        self.policies: Dict[str, AcceptanceCriteria] = {}
        self._setup_default_policies()
    
    def _setup_default_policies(self) -> None:
        """Set up default policies"""
        # Staging - less strict
        staging = AcceptanceCriteria()
        for c in staging.criteria:
            if c.name == "sharpe_ratio":
                c.threshold = 0.3
            elif c.name == "max_drawdown":
                c.threshold = 0.30
        self.policies["staging"] = staging
        
        # Production - strict
        self.policies["production"] = AcceptanceCriteria()
        
        # Paper trading - moderate
        paper = AcceptanceCriteria()
        for c in paper.criteria:
            if c.name == "sharpe_ratio":
                c.threshold = 0.4
            elif c.name == "max_drawdown":
                c.threshold = 0.25
        self.policies["paper_trading"] = paper
    
    def get_policy(self, name: str) -> Optional[AcceptanceCriteria]:
        """Get a policy by name"""
        return self.policies.get(name)
    
    def add_policy(self, name: str, criteria: AcceptanceCriteria) -> None:
        """Add a new policy"""
        self.policies[name] = criteria
        logger.info(f"Added policy: {name}")
    
    def evaluate(
        self,
        metrics: Dict[str, float],
        environment: str = "production"
    ) -> AcceptanceResult:
        """Evaluate metrics against policy for environment"""
        criteria = self.policies.get(environment)
        
        if criteria is None:
            logger.warning(f"Policy '{environment}' not found, using production")
            criteria = self.policies.get("production")
        
        if criteria is None:
            raise ValueError("No acceptance policies defined")
        
        return criteria.evaluate(metrics)
