"""
Walk-Forward Evaluation - Rolling Window Validation

Automated rolling-window validation with comprehensive reporting.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardWindow:
    """A single walk-forward window"""
    window_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    
    # Results
    train_metrics: Dict[str, float] = field(default_factory=dict)
    test_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Comparison
    degradation: Dict[str, float] = field(default_factory=dict)  # test - train
    
    status: str = "pending"  # pending, running, completed, failed
    
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
            "status": self.status,
        }


@dataclass
class WalkForwardReport:
    """Complete walk-forward analysis report"""
    strategy_id: str
    strategy_name: str
    
    # Configuration
    total_start: datetime
    total_end: datetime
    train_period_days: int
    test_period_days: int
    step_days: int
    
    # Windows
    windows: List[WalkForwardWindow] = field(default_factory=list)
    
    # Aggregate results
    avg_train_metrics: Dict[str, float] = field(default_factory=dict)
    avg_test_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Overall degradation
    overall_degradation: Dict[str, float] = field(default_factory=dict)
    
    # Robustness assessment
    robustness_score: float = 0  # 0-100
    is_robust: bool = False
    
    # Generated at
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "total_start": self.total_start.isoformat(),
            "total_end": self.total_end.isoformat(),
            "train_period_days": self.train_period_days,
            "test_period_days": self.test_period_days,
            "step_days": self.step_days,
            "windows": [w.to_dict() for w in self.windows],
            "avg_train_metrics": self.avg_train_metrics,
            "avg_test_metrics": self.avg_test_metrics,
            "overall_degradation": self.overall_degradation,
            "robustness_score": self.robustness_score,
            "is_robust": self.is_robust,
            "generated_at": self.generated_at.isoformat(),
        }


class WalkForwardEvaluator:
    """
    Walk-Forward Evaluator for rolling window validation.
    
    Features:
    - Configurable window sizes
    - Rolling train/test windows
    - Degradation analysis
    - Robustness scoring
    - Comprehensive reporting
    """
    
    def __init__(self):
        self._reports: Dict[str, WalkForwardReport] = {}
    
    def evaluate(
        self,
        strategy_id: str,
        strategy_name: str,
        total_start: datetime,
        total_end: datetime,
        backtest_func: Callable,
        train_period_days: int = 90,
        test_period_days: int = 30,
        step_days: int = 7,
    ) -> WalkForwardReport:
        """
        Run walk-forward evaluation.
        
        Args:
            strategy_id: Strategy ID
            strategy_name: Strategy name
            total_start: Start of evaluation period
            total_end: End of evaluation period
            train_period_days: Training window length
            test_period_days: Testing window length
            step_days: Step between windows
            backtest_func: Function to run backtest
            
        Returns:
            WalkForwardReport with results
        """
        report = WalkForwardReport(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            total_start=total_start,
            total_end=total_end,
            train_period_days=train_period_days,
            test_period_days=test_period_days,
            step_days=step_days,
        )
        
        # Generate windows
        current_train_end = total_start + timedelta(days=train_period_days)
        window_id = 0
        
        while current_train_end <= total_end - timedelta(days=test_period_days):
            train_start = current_train_end - timedelta(days=train_period_days)
            test_start = current_train_end
            test_end = min(
                test_start + timedelta(days=test_period_days),
                total_end
            )
            
            window = WalkForwardWindow(
                window_id=window_id,
                train_start=train_start,
                train_end=current_train_end,
                test_start=test_start,
                test_end=test_end,
            )
            
            report.windows.append(window)
            
            # Step forward
            current_train_end += timedelta(days=step_days)
            window_id += 1
        
        # Run evaluation for each window
        for window in report.windows:
            window.status = "running"
            
            try:
                # Train on training period
                train_result = backtest_func(
                    strategy_id=strategy_id,
                    start_date=window.train_start,
                    end_date=window.train_end,
                    optimize=True,
                )
                window.train_metrics = train_result.get("metrics", {})
                
                # Test on test period
                test_result = backtest_func(
                    strategy_id=strategy_id,
                    start_date=window.test_start,
                    end_date=window.test_end,
                    optimize=False,
                )
                window.test_metrics = test_result.get("metrics", {})
                
                # Calculate degradation
                for metric in window.train_metrics:
                    if metric in window.test_metrics:
                        train_val = window.train_metrics[metric]
                        test_val = window.test_metrics[metric]
                        
                        if train_val != 0:
                            degradation = ((test_val - train_val) / abs(train_val)) * 100
                            window.degradation[metric] = degradation
                
                window.status = "completed"
                
            except Exception as e:
                logger.error(f"Window {window.window_id} failed: {e}")
                window.status = "failed"
        
        # Calculate aggregate metrics
        report.avg_train_metrics = self._calculate_averages(
            [w.train_metrics for w in report.windows if w.train_metrics]
        )
        report.avg_test_metrics = self._calculate_averages(
            [w.test_metrics for w in report.windows if w.test_metrics]
        )
        
        # Calculate overall degradation
        for metric in report.avg_train_metrics:
            if metric in report.avg_test_metrics:
                train_val = report.avg_train_metrics[metric]
                test_val = report.avg_test_metrics[metric]
                
                if train_val != 0:
                    degradation = ((test_val - train_val) / abs(train_val)) * 100
                    report.overall_degradation[metric] = degradation
        
        # Calculate robustness score
        report.robustness_score = self._calculate_robustness_score(report)
        report.is_robust = report.robustness_score >= 70
        
        self._reports[strategy_id] = report
        
        logger.info(
            f"Walk-forward evaluation complete for {strategy_name}: "
            f"Score={report.robustness_score:.1f}, "
            f"Robust={report.is_robust}"
        )
        
        return report
    
    def _calculate_averages(
        self,
        metrics_list: List[Dict[str, float]],
    ) -> Dict[str, float]:
        """Calculate average metrics across windows"""
        if not metrics_list:
            return {}
        
        averages = {}
        all_keys = set()
        for metrics in metrics_list:
            all_keys.update(metrics.keys())
        
        for key in all_keys:
            values = [m.get(key, 0) for m in metrics_list]
            averages[key] = sum(values) / len(values)
        
        return averages
    
    def _calculate_robustness_score(self, report: WalkForwardReport) -> float:
        """Calculate overall robustness score (0-100)"""
        score = 100
        
        # Penalize for high degradation
        for metric, degradation in report.overall_degradation.items():
            # For return metrics, negative degradation is bad
            if metric in ["total_return", "sharpe_ratio", "win_rate"]:
                if degradation < -20:  # More than 20% worse
                    score -= 15
                elif degradation < -10:
                    score -= 8
                elif degradation < 0:
                    score -= 3
            # For drawdown, positive degradation (more drawdown) is bad
            elif metric == "max_drawdown":
                if degradation > 50:  # More than 50% worse drawdown
                    score -= 20
                elif degradation > 25:
                    score -= 10
        
        # Penalize for failed windows
        failed_count = sum(1 for w in report.windows if w.status == "failed")
        if report.windows:
            failure_rate = failed_count / len(report.windows)
            score -= failure_rate * 30
        
        # Penalize for high variance in test metrics
        for metric, avg_value in report.avg_test_metrics.items():
            values = [w.test_metrics.get(metric, 0) for w in report.windows]
            if values and avg_value != 0:
                variance = sum((v - avg_value) ** 2 for v in values) / len(values)
                cv = (variance ** 0.5) / abs(avg_value) if avg_value else 0
                
                if cv > 0.5:  # High variance
                    score -= 10
        
        return max(0, min(100, score))
    
    def get_report(self, strategy_id: str) -> Optional[WalkForwardReport]:
        """Get the latest report for a strategy"""
        return self._reports.get(strategy_id)
