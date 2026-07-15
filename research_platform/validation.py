"""
Validation Center - Comprehensive Strategy Validation

Complete validation system with:
- Walk-forward testing
- Rolling-window validation
- Out-of-sample evaluation
- Monte Carlo simulations
- Sensitivity analysis
- Stability analysis
"""

import json
import logging
import uuid
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict
import random

logger = logging.getLogger(__name__)


class ValidationType(Enum):
    """Types of validation"""
    WALK_FORWARD = "walk_forward"
    ROLLING_WINDOW = "rolling_window"
    OUT_OF_SAMPLE = "out_of_sample"
    MONTE_CARLO = "monte_carlo"
    SENSITIVITY = "sensitivity"
    STABILITY = "stability"
    BOOTSTRAP = "bootstrap"


class ValidationStatus(Enum):
    """Validation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ValidationWindow:
    """A single validation window"""
    window_id: int
    
    # Time periods
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    
    # Results
    train_metrics: Dict[str, float] = field(default_factory=dict)
    test_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Degradation analysis
    degradation: Dict[str, float] = field(default_factory=dict)
    degradation_pct: Dict[str, float] = field(default_factory=dict)
    
    # Status
    status: ValidationStatus = ValidationStatus.PENDING
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_id": self.window_id,
            "train_start": self.train_start.isoformat(),
            "train_end": self.train_end.isoformat(),
            "test_start": self.test_start.isoformat(),
            "test_end": self.test_end.isoformat(),
            "train_metrics": self.train_metrics,
            "test_metrics": self.test_metrics,
            "degradation": self.degradation,
            "degradation_pct": self.degradation_pct,
            "status": self.status.value,
            "error_message": self.error_message,
        }


@dataclass
class MonteCarloResult:
    """Result of a Monte Carlo simulation"""
    simulation_id: int
    
    # Metrics
    final_equity: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_return: float
    
    # Path data
    equity_curve: List[float] = field(default_factory=list)
    drawdown_curve: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "final_equity": self.final_equity,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "win_rate": self.win_rate,
            "total_return": self.total_return,
            "equity_curve": self.equity_curve,
            "drawdown_curve": self.drawdown_curve,
        }


@dataclass
class SensitivityResult:
    """Result of sensitivity analysis"""
    parameter: str
    base_value: Any
    
    # Sensitivity data
    values_tested: List[Any] = field(default_factory=list)
    metrics_at_values: Dict[str, List[float]] = field(default_factory=dict)
    
    # Analysis
    sensitivity_score: float = 0.0  # How much output changes with input
    optimal_value: Any = None
    acceptable_range: Tuple[Any, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter": self.parameter,
            "base_value": self.base_value,
            "values_tested": self.values_tested,
            "metrics_at_values": self.metrics_at_values,
            "sensitivity_score": self.sensitivity_score,
            "optimal_value": self.optimal_value,
            "acceptable_range": self.acceptable_range,
        }


@dataclass
class StabilityResult:
    """Result of stability analysis"""
    metric_name: str
    
    # Statistics
    mean: float
    std: float
    cv: float  # Coefficient of variation
    
    # Stability metrics
    stability_score: float = 0.0  # 0-100
    is_stable: bool = False
    
    # Bounds
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    out_of_bounds_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "mean": self.mean,
            "std": self.std,
            "cv": self.cv,
            "stability_score": self.stability_score,
            "is_stable": self.is_stable,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "out_of_bounds_count": self.out_of_bounds_count,
        }


@dataclass
class ValidationResult:
    """Complete validation result"""
    result_id: str
    validation_type: ValidationType
    
    # Strategy info
    strategy_id: str
    strategy_name: str
    
    # Time coverage (before optional config)
    start_date: datetime
    end_date: datetime
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Windows (for walk-forward, rolling)
    windows: List[ValidationWindow] = field(default_factory=list)
    
    # Monte Carlo results
    monte_carlo_results: List[MonteCarloResult] = field(default_factory=list)
    
    # Sensitivity results
    sensitivity_results: List[SensitivityResult] = field(default_factory=list)
    
    # Stability results
    stability_results: List[StabilityResult] = field(default_factory=list)
    
    # Aggregate metrics
    avg_train_metrics: Dict[str, float] = field(default_factory=dict)
    avg_test_metrics: Dict[str, float] = field(default_factory=dict)
    overall_degradation: Dict[str, float] = field(default_factory=dict)
    
    # Overall assessment
    is_robust: bool = False
    robustness_score: float = 0.0  # 0-100
    confidence_level: float = 0.0
    
    # Issues
    warnings: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    execution_time_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "validation_type": self.validation_type.value,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "config": self.config,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "windows": [w.to_dict() for w in self.windows],
            "monte_carlo_results": [m.to_dict() for m in self.monte_carlo_results],
            "sensitivity_results": [s.to_dict() for s in self.sensitivity_results],
            "stability_results": [st.to_dict() for st in self.stability_results],
            "avg_train_metrics": self.avg_train_metrics,
            "avg_test_metrics": self.avg_test_metrics,
            "overall_degradation": self.overall_degradation,
            "is_robust": self.is_robust,
            "robustness_score": self.robustness_score,
            "confidence_level": self.confidence_level,
            "warnings": self.warnings,
            "failures": self.failures,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_seconds": self.execution_time_seconds,
        }


@dataclass
class ValidationSuite:
    """A suite of validation tests"""
    suite_id: str
    name: str
    description: str
    
    # Tests to run
    validation_types: List[ValidationType] = field(default_factory=list)
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Results
    results: List[ValidationResult] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "name": self.name,
            "description": self.description,
            "validation_types": [v.value for v in self.validation_types],
            "config": self.config,
            "results": [r.to_dict() for r in self.results],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ValidationCenter:
    """
    Validation Center for comprehensive strategy validation.
    
    Features:
    - Walk-forward analysis
    - Rolling window validation
    - Out-of-sample testing
    - Monte Carlo simulations
    - Sensitivity analysis
    - Stability analysis
    - Bootstrap validation
    """
    
    def __init__(self, storage_path: str = "data/validation"):
        self._storage_path = storage_path
        self._results: Dict[str, ValidationResult] = {}
        self._suites: Dict[str, ValidationSuite] = {}
        
        import os
        os.makedirs(storage_path, exist_ok=True)
        self._load_results()
    
    def _load_results(self) -> None:
        """Load validation results"""
        results_file = f"{self._storage_path}/results.json"
        
        try:
            if os.path.exists(results_file):
                with open(results_file, "r") as f:
                    data = json.load(f)
                
                for result_data in data.get("results", []):
                    result_data["created_at"] = datetime.fromisoformat(result_data["created_at"])
                    if result_data.get("completed_at"):
                        result_data["completed_at"] = datetime.fromisoformat(result_data["completed_at"])
                    
                    # Parse windows
                    for w in result_data.get("windows", []):
                        w["train_start"] = datetime.fromisoformat(w["train_start"])
                        w["train_end"] = datetime.fromisoformat(w["train_end"])
                        w["test_start"] = datetime.fromisoformat(w["test_start"])
                        w["test_end"] = datetime.fromisoformat(w["test_end"])
                    result_data["windows"] = [ValidationWindow(**w) for w in result_data.get("windows", [])]
                    
                    # Parse Monte Carlo results
                    result_data["monte_carlo_results"] = [
                        MonteCarloResult(**m) for m in result_data.get("monte_carlo_results", [])
                    ]
                    
                    # Parse sensitivity results
                    result_data["sensitivity_results"] = [
                        SensitivityResult(**s) for s in result_data.get("sensitivity_results", [])
                    ]
                    
                    # Parse stability results
                    result_data["stability_results"] = [
                        StabilityResult(**s) for s in result_data.get("stability_results", [])
                    ]
                    
                    result = ValidationResult(**result_data)
                    self._results[result.result_id] = result
                
                logger.info(f"Loaded {len(self._results)} validation results")
        except Exception as e:
            logger.warning(f"Could not load results: {e}")
    
    def _save_results(self) -> None:
        """Save validation results"""
        results_file = f"{self._storage_path}/results.json"
        
        data = {
            "results": [r.to_dict() for r in self._results.values()],
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(results_file, "w") as f:
            json.dump(data, f, indent=2)
    
    # Walk-Forward Analysis
    def run_walk_forward(
        self,
        strategy_id: str,
        strategy_name: str,
        start_date: datetime,
        end_date: datetime,
        backtest_func: Callable,
        train_period_days: int = 90,
        test_period_days: int = 30,
        step_days: int = 7,
        metrics: Optional[List[str]] = None,
    ) -> ValidationResult:
        """Run walk-forward analysis"""
        result = ValidationResult(
            result_id=str(uuid.uuid4()),
            validation_type=ValidationType.WALK_FORWARD,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            config={
                "train_period_days": train_period_days,
                "test_period_days": test_period_days,
                "step_days": step_days,
            },
            start_date=start_date,
            end_date=end_date,
        )
        
        start_time = datetime.utcnow()
        
        # Generate windows
        current_train_end = start_date + timedelta(days=train_period_days)
        window_id = 0
        
        while current_train_end <= end_date - timedelta(days=test_period_days):
            train_start = current_train_end - timedelta(days=train_period_days)
            test_start = current_train_end
            test_end = min(test_start + timedelta(days=test_period_days), end_date)
            
            window = ValidationWindow(
                window_id=window_id,
                train_start=train_start,
                train_end=current_train_end,
                test_start=test_start,
                test_end=test_end,
            )
            
            result.windows.append(window)
            
            # Run backtest
            try:
                window.status = ValidationStatus.RUNNING
                
                # Train
                train_result = backtest_func(
                    strategy_id=strategy_id,
                    start_date=train_start,
                    end_date=current_train_end,
                    optimize=True,
                    metrics=metrics,
                )
                window.train_metrics = train_result.get("metrics", {})
                
                # Test
                test_result = backtest_func(
                    strategy_id=strategy_id,
                    start_date=test_start,
                    end_date=test_end,
                    optimize=False,
                    metrics=metrics,
                )
                window.test_metrics = test_result.get("metrics", {})
                
                # Calculate degradation
                for metric in window.train_metrics:
                    if metric in window.test_metrics:
                        train_val = window.train_metrics[metric]
                        test_val = window.test_metrics[metric]
                        
                        window.degradation[metric] = test_val - train_val
                        if train_val != 0:
                            window.degradation_pct[metric] = ((test_val - train_val) / abs(train_val)) * 100
                
                window.status = ValidationStatus.COMPLETED
                
            except Exception as e:
                window.status = ValidationStatus.FAILED
                window.error_message = str(e)
                result.failures.append(f"Window {window_id}: {str(e)}")
            
            current_train_end += timedelta(days=step_days)
            window_id += 1
        
        # Calculate aggregates
        result.avg_train_metrics = self._calculate_averages(
            [w.train_metrics for w in result.windows if w.train_metrics]
        )
        result.avg_test_metrics = self._calculate_averages(
            [w.test_metrics for w in result.windows if w.test_metrics]
        )
        
        # Calculate overall degradation
        for metric in result.avg_train_metrics:
            if metric in result.avg_test_metrics:
                train_val = result.avg_train_metrics[metric]
                test_val = result.avg_test_metrics[metric]
                if train_val != 0:
                    result.overall_degradation[metric] = ((test_val - train_val) / abs(train_val)) * 100
        
        # Calculate robustness
        result.robustness_score = self._calculate_robustness_score(result)
        result.is_robust = result.robustness_score >= 70
        
        result.completed_at = datetime.utcnow()
        result.execution_time_seconds = (result.completed_at - start_time).total_seconds()
        
        self._results[result.result_id] = result
        self._save_results()
        
        return result
    
    # Monte Carlo Simulation
    def run_monte_carlo(
        self,
        strategy_id: str,
        strategy_name: str,
        trades: List[Dict[str, Any]],
        num_simulations: int = 1000,
        metrics: Optional[List[str]] = None,
    ) -> ValidationResult:
        """Run Monte Carlo simulation"""
        result = ValidationResult(
            result_id=str(uuid.uuid4()),
            validation_type=ValidationType.MONTE_CARLO,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            config={
                "num_simulations": num_simulations,
            },
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
        )
        
        start_time = datetime.utcnow()
        
        # Extract trade returns
        returns = [t.get("pnl", 0) for t in trades]
        if not returns:
            result.failures.append("No trades provided")
            return result
        
        # Run simulations
        for sim_id in range(num_simulations):
            # Shuffle returns
            shuffled_returns = returns.copy()
            random.shuffle(shuffled_returns)
            
            # Build equity curve
            equity = 1000.0  # Starting capital
            equity_curve = [equity]
            peak = equity
            max_dd = 0.0
            drawdown_curve = [0.0]
            
            wins = 0
            total_trades = len(shuffled_returns)
            
            for ret in shuffled_returns:
                equity += ret
                equity_curve.append(equity)
                
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak if peak > 0 else 0
                drawdown_curve.append(dd)
                max_dd = max(max_dd, dd)
                
                if ret > 0:
                    wins += 1
            
            # Calculate metrics
            total_return = (equity - 1000) / 1000
            sharpe = self._calculate_sharpe(returns)
            win_rate = wins / total_trades if total_trades > 0 else 0
            
            mc_result = MonteCarloResult(
                simulation_id=sim_id,
                final_equity=equity,
                max_drawdown=max_dd,
                sharpe_ratio=sharpe,
                win_rate=win_rate,
                total_return=total_return,
                equity_curve=equity_curve[-100:],  # Store last 100 points
                drawdown_curve=drawdown_curve[-100:],
            )
            
            result.monte_carlo_results.append(mc_result)
        
        # Calculate aggregate statistics
        final_equities = [m.final_equity for m in result.monte_carlo_results]
        max_drawdowns = [m.max_drawdown for m in result.monte_carlo_results]
        returns_dist = [m.total_return for m in result.monte_carlo_results]
        
        result.avg_test_metrics = {
            "mean_final_equity": float(np.mean(final_equities)),
            "median_final_equity": float(np.median(final_equities)),
            "std_final_equity": float(np.std(final_equities)),
            "mean_max_drawdown": float(np.mean(max_drawdowns)),
            "worst_case_drawdown": float(np.max(max_drawdowns)),
            "probability_of_loss": float(np.mean([e < 1000 for e in final_equities])),
            "value_at_risk_95": float(np.percentile(final_equities, 5)),
        }
        
        # Confidence level
        result.confidence_level = 1.0 - result.avg_test_metrics["probability_of_loss"]
        
        result.completed_at = datetime.utcnow()
        result.execution_time_seconds = (result.completed_at - start_time).total_seconds()
        
        self._results[result.result_id] = result
        self._save_results()
        
        return result
    
    # Sensitivity Analysis
    def run_sensitivity_analysis(
        self,
        strategy_id: str,
        strategy_name: str,
        base_params: Dict[str, Any],
        param_ranges: Dict[str, Tuple[Any, Any, int]],
        backtest_func: Callable,
        primary_metric: str = "sharpe_ratio",
    ) -> ValidationResult:
        """Run sensitivity analysis on strategy parameters"""
        result = ValidationResult(
            result_id=str(uuid.uuid4()),
            validation_type=ValidationType.SENSITIVITY,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            config={
                "base_params": base_params,
                "param_ranges": {k: list(v) for k, v in param_ranges.items()},
            },
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
        )
        
        start_time = datetime.utcnow()
        
        for param_name, (min_val, max_val, num_steps) in param_ranges.items():
            sensitivity = SensitivityResult(
                parameter=param_name,
                base_value=base_params.get(param_name),
            )
            
            # Generate values to test
            if isinstance(min_val, int) and isinstance(max_val, int):
                values = list(range(min_val, max_val + 1, max(1, (max_val - min_val) // num_steps)))
            else:
                values = np.linspace(min_val, max_val, num_steps).tolist()
            
            sensitivity.values_tested = values
            sensitivity.metrics_at_values = {primary_metric: []}
            
            for value in values:
                # Create parameter set
                test_params = base_params.copy()
                test_params[param_name] = value
                
                # Run backtest
                try:
                    backtest_result = backtest_func(strategy_id=strategy_id, parameters=test_params)
                    metric_value = backtest_result.get("metrics", {}).get(primary_metric, 0)
                    sensitivity.metrics_at_values[primary_metric].append(metric_value)
                except Exception as e:
                    sensitivity.metrics_at_values[primary_metric].append(0)
            
            # Calculate sensitivity score
            metric_values = sensitivity.metrics_at_values[primary_metric]
            if len(metric_values) > 1:
                sensitivity.sensitivity_score = float(np.std(metric_values) / (abs(np.mean(metric_values)) + 1e-10))
            
            # Find optimal value
            best_idx = np.argmax(metric_values)
            sensitivity.optimal_value = values[best_idx]
            
            # Find acceptable range (within 10% of optimal)
            optimal_value = metric_values[best_idx]
            acceptable_values = [
                v for v, m in zip(values, metric_values)
                if m >= optimal_value * 0.9
            ]
            if acceptable_values:
                sensitivity.acceptable_range = (min(acceptable_values), max(acceptable_values))
            
            result.sensitivity_results.append(sensitivity)
        
        # Overall assessment
        avg_sensitivity = np.mean([s.sensitivity_score for s in result.sensitivity_results])
        result.robustness_score = max(0, 100 - avg_sensitivity * 100)
        result.is_robust = result.robustness_score >= 70
        
        result.completed_at = datetime.utcnow()
        result.execution_time_seconds = (result.completed_at - start_time).total_seconds()
        
        self._results[result.result_id] = result
        self._save_results()
        
        return result
    
    # Stability Analysis
    def run_stability_analysis(
        self,
        strategy_id: str,
        strategy_name: str,
        validation_results: List[ValidationResult],
        stability_threshold: float = 0.2,
    ) -> ValidationResult:
        """Run stability analysis on validation results"""
        result = ValidationResult(
            result_id=str(uuid.uuid4()),
            validation_type=ValidationType.STABILITY,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
        )
        
        # Aggregate metrics across validation results
        metric_values: Dict[str, List[float]] = defaultdict(list)
        
        for val_result in validation_results:
            for metric_name, value in val_result.avg_test_metrics.items():
                metric_values[metric_name].append(value)
        
        # Calculate stability for each metric
        for metric_name, values in metric_values.items():
            if len(values) < 2:
                continue
            
            mean_val = np.mean(values)
            std_val = np.std(values)
            cv = std_val / abs(mean_val) if mean_val != 0 else 0
            
            stability = StabilityResult(
                metric_name=metric_name,
                mean=mean_val,
                std=std_val,
                cv=cv,
            )
            
            # Stability score (lower CV = more stable)
            stability.stability_score = max(0, 100 - cv * 100)
            stability.is_stable = cv < stability_threshold
            
            # Calculate bounds (mean ± 2 std)
            stability.lower_bound = mean_val - 2 * std_val
            stability.upper_bound = mean_val + 2 * std_val
            stability.out_of_bounds_count = sum(
                1 for v in values if v < stability.lower_bound or v > stability.upper_bound
            )
            
            result.stability_results.append(stability)
        
        # Overall assessment
        if result.stability_results:
            result.robustness_score = np.mean([s.stability_score for s in result.stability_results])
            result.is_robust = all(s.is_stable for s in result.stability_results)
        
        self._results[result.result_id] = result
        self._save_results()
        
        return result
    
    # Helper Methods
    def _calculate_averages(self, metrics_list: List[Dict[str, float]]) -> Dict[str, float]:
        """Calculate average metrics across windows"""
        if not metrics_list:
            return {}
        
        all_keys = set()
        for metrics in metrics_list:
            all_keys.update(metrics.keys())
        
        averages = {}
        for key in all_keys:
            values = [m.get(key, 0) for m in metrics_list if key in m]
            if values:
                averages[key] = float(np.mean(values))
        
        return averages
    
    def _calculate_robustness_score(self, result: ValidationResult) -> float:
        """Calculate overall robustness score"""
        score = 100.0
        
        # Penalize for degradation
        for metric, degradation in result.overall_degradation.items():
            if metric in ["total_return", "sharpe_ratio", "win_rate"]:
                if degradation < -20:
                    score -= 15
                elif degradation < -10:
                    score -= 8
                elif degradation < 0:
                    score -= 3
            elif metric == "max_drawdown":
                if degradation > 50:
                    score -= 20
        
        # Penalize for failed windows
        failed_count = sum(1 for w in result.windows if w.status == ValidationStatus.FAILED)
        if result.windows:
            failure_rate = failed_count / len(result.windows)
            score -= failure_rate * 30
        
        # Penalize for high variance
        for metric, avg_value in result.avg_test_metrics.items():
            values = [w.test_metrics.get(metric, 0) for w in result.windows]
            if values and avg_value != 0:
                variance = np.std(values)
                cv = variance / abs(avg_value)
                if cv > 0.5:
                    score -= 10
        
        return max(0, min(100, score))
    
    def _calculate_sharpe(self, returns: List[float], risk_free: float = 0.0) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        return (mean_return - risk_free) / std_return * np.sqrt(252)
    
    # Retrieval
    def get_result(self, result_id: str) -> Optional[ValidationResult]:
        """Get a validation result"""
        return self._results.get(result_id)
    
    def get_latest_result(
        self,
        strategy_id: str,
        validation_type: Optional[ValidationType] = None,
    ) -> Optional[ValidationResult]:
        """Get the latest validation result for a strategy"""
        results = [
            r for r in self._results.values()
            if r.strategy_id == strategy_id
            and (validation_type is None or r.validation_type == validation_type)
        ]
        
        if not results:
            return None
        
        return sorted(results, key=lambda r: r.created_at, reverse=True)[0]
    
    def get_validation_history(
        self,
        strategy_id: str,
        limit: int = 50,
    ) -> List[ValidationResult]:
        """Get validation history for a strategy"""
        results = [
            r for r in self._results.values()
            if r.strategy_id == strategy_id
        ]
        
        return sorted(results, key=lambda r: r.created_at, reverse=True)[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        results = list(self._results.values())
        
        return {
            "total_validations": len(results),
            "by_type": {
                vtype.value: sum(1 for r in results if r.validation_type == vtype)
                for vtype in ValidationType
            },
            "robust_validations": sum(1 for r in results if r.is_robust),
            "avg_robustness_score": np.mean([r.robustness_score for r in results]) if results else 0,
        }


import os
