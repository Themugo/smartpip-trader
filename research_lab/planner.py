"""
Experiment Planner
=================

Creates experiment plans from hypotheses.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    """Experiment status"""
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExperimentPlan:
    """An experiment plan"""
    id: str
    name: str
    hypothesis: Any  # Hypothesis object
    parameters: Dict[str, Any]
    datasets: List[str]
    metrics: List[str]
    status: ExperimentStatus
    estimated_duration_minutes: int = 30
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "hypothesis": self.hypothesis.to_dict() if hasattr(self.hypothesis, 'to_dict') else str(self.hypothesis),
            "parameters": self.parameters,
            "datasets": self.datasets,
            "metrics": self.metrics,
            "status": self.status.value,
            "estimated_duration": self.estimated_duration_minutes
        }


class ExperimentPlanner:
    """
    Creates experiment plans from hypotheses.
    """
    
    def __init__(
        self,
        default_lookback_days: int = 90,
        default_test_days: int = 30
    ):
        self.default_lookback_days = default_lookback_days
        self.default_test_days = default_test_days
        self.plans: Dict[str, ExperimentPlan] = {}
    
    def create_plan(
        self,
        hypothesis: Any,
        idea_id: str,
        custom_parameters: Optional[Dict[str, Any]] = None
    ) -> ExperimentPlan:
        """
        Create an experiment plan for a hypothesis.
        
        Args:
            hypothesis: The hypothesis to test
            idea_id: Associated research idea ID
            custom_parameters: Optional custom parameters
            
        Returns:
            ExperimentPlan
        """
        # Determine hypothesis type
        htype = hypothesis.type.value if hasattr(hypothesis.type, 'value') else str(hypothesis.type)
        
        # Get base parameters for this type
        base_params = self._get_parameters_for_type(htype, hypothesis)
        
        # Merge with custom parameters
        if custom_parameters:
            base_params.update(custom_parameters)
        
        # Determine datasets
        datasets = self._select_datasets(hypothesis, base_params)
        
        # Determine metrics
        metrics = self._select_metrics(hypothesis, base_params)
        
        # Create plan
        plan = ExperimentPlan(
            id=str(uuid4()),
            name=f"Experiment_{hypothesis.id[:8]}_{htype}",
            hypothesis=hypothesis,
            parameters=base_params,
            datasets=datasets,
            metrics=metrics,
            status=ExperimentStatus.PLANNED,
            estimated_duration_minutes=self._estimate_duration(base_params)
        )
        
        self.plans[plan.id] = plan
        logger.info(f"Created experiment plan: {plan.name}")
        
        return plan
    
    def _get_parameters_for_type(
        self,
        htype: str,
        hypothesis: Any
    ) -> Dict[str, Any]:
        """Get parameters for hypothesis type"""
        base_params = {
            "lookback_days": self.default_lookback_days,
            "test_days": self.default_test_days,
            "confidence_level": 0.95,
            "min_trades": 30,
            "train_test_split": 0.7
        }
        
        # Type-specific parameters
        if htype == "mean_reversion":
            base_params.update({
                "indicator_period": 20,
                "entry_threshold": 2.0,  # standard deviations
                "exit_threshold": 0.5,
                "stop_loss_pct": 0.02
            })
        elif htype == "momentum":
            base_params.update({
                "momentum_period": 14,
                "entry_threshold": 0.01,  # minimum momentum
                "holding_period": 5,
                "trailing_stop": True
            })
        elif htype == "volatility":
            base_params.update({
                "volatility_period": 20,
                "high_vol_threshold": 1.5,  # times average
                "low_vol_threshold": 0.5,
                "contracts": ["DIGITOVER", "DIGITUNDER"]
            })
        elif htype == "pattern":
            base_params.update({
                "pattern_type": "any",
                "min_pattern_confidence": 0.6,
                "confirmation_bars": 2
            })
        elif htype == "regime":
            base_params.update({
                "regime_indicator": "volatility",
                "regime_period": 50,
                "adapt_parameters": True
            })
        elif htype == "seasonal":
            base_params.update({
                "seasonal_period": "daily",  # daily, weekly, monthly
                "lookback_periods": 252
            })
        else:
            base_params.update({
                "strategy_type": "generic",
                "entry_method": "threshold",
                "exit_method": "time_based"
            })
        
        # Add parameters from hypothesis variables
        if hasattr(hypothesis, 'variables'):
            for var in hypothesis.variables:
                if var.name not in base_params:
                    base_params[f"var_{var.name}"] = var.name
        
        return base_params
    
    def _select_datasets(
        self,
        hypothesis: Any,
        parameters: Dict[str, Any]
    ) -> List[str]:
        """Select appropriate datasets for experiment"""
        datasets = ["default_market_data"]
        
        # Add specific datasets based on hypothesis
        htype = hypothesis.type.value if hasattr(hypothesis.type, 'value') else ""
        
        if "correlation" in htype:
            datasets.append("market_index_data")
        elif "cross_asset" in htype:
            datasets.extend(["asset_a_data", "asset_b_data"])
        
        # Add volatility data for volatility hypotheses
        if "volatility" in htype:
            datasets.append("volatility_indices")
        
        return datasets
    
    def _select_metrics(
        self,
        hypothesis: Any,
        parameters: Dict[str, Any]
    ) -> List[str]:
        """Select metrics to evaluate"""
        metrics = [
            "total_return",
            "sharpe_ratio",
            "max_drawdown",
            "win_rate",
            "profit_factor",
            "avg_trade_pnl",
            "trade_count",
            "calmar_ratio"
        ]
        
        # Add type-specific metrics
        htype = hypothesis.type.value if hasattr(hypothesis.type, 'value') else ""
        
        if "mean_reversion" in htype:
            metrics.extend(["mean_reversion_rate", "reversion_magnitude"])
        elif "momentum" in htype:
            metrics.extend(["momentum_persistence", "trend_strength"])
        elif "volatility" in htype:
            metrics.extend(["volatility_clustering", "volatility_reversion"])
        
        # Always include statistical metrics
        metrics.extend([
            "p_value",
            "confidence_interval",
            "statistical_power",
            "effect_size"
        ])
        
        return metrics
    
    def _estimate_duration(self, parameters: Dict[str, Any]) -> int:
        """Estimate experiment duration in minutes"""
        base = 10
        
        # Add time based on lookback
        lookback = parameters.get("lookback_days", 90)
        base += lookback // 30 * 5
        
        # Add time for complex strategies
        if parameters.get("adapt_parameters", False):
            base += 15
        
        # Add time for multiple datasets
        datasets = parameters.get("datasets", [])
        base += len(datasets) * 5
        
        return min(base, 120)  # Cap at 2 hours
    
    def get_plan(self, plan_id: str) -> Optional[ExperimentPlan]:
        """Get plan by ID"""
        return self.plans.get(plan_id)
    
    def get_all_plans(self) -> List[ExperimentPlan]:
        """Get all experiment plans"""
        return list(self.plans.values())
    
    def update_plan(
        self,
        plan_id: str,
        updates: Dict[str, Any]
    ) -> Optional[ExperimentPlan]:
        """Update experiment plan"""
        plan = self.plans.get(plan_id)
        if not plan:
            return None
        
        if "parameters" in updates:
            plan.parameters.update(updates["parameters"])
        if "metrics" in updates:
            plan.metrics.extend(updates["metrics"])
        if "status" in updates:
            plan.status = ExperimentStatus(updates["status"])
        
        return plan
    
    def delete_plan(self, plan_id: str) -> bool:
        """Delete experiment plan"""
        if plan_id in self.plans:
            del self.plans[plan_id]
            return True
        return False
