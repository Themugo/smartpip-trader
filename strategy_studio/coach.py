"""
AI Strategy Coach - Automatic Strategy Analysis and Recommendations

Analyzes backtest results and provides actionable recommendations.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from strategy_studio.builder import StrategyGraph

logger = logging.getLogger(__name__)


class IssueSeverity(Enum):
    """Severity of identified issues"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class IssueCategory(Enum):
    """Categories of strategy issues"""
    OVERFITTING = "overfitting"
    PARAMETER_SENSITIVITY = "parameter_sensitivity"
    INSTABILITY = "instability"
    RISK = "risk"
    COMPLEXITY = "complexity"
    PERFORMANCE = "performance"
    CALIBRATION = "calibration"
    DATA_LEAKAGE = "data_leakage"


@dataclass
class StrategyIssue:
    """An identified issue with a strategy"""
    id: str
    category: IssueCategory
    severity: IssueSeverity
    title: str
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    # Context
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    backtest_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "recommendations": self.recommendations,
            "detected_at": self.detected_at.isoformat(),
            "backtest_id": self.backtest_id,
        }


@dataclass
class CoachAnalysis:
    """Complete analysis from the AI Coach"""
    strategy_id: str
    strategy_name: str
    backtest_id: str
    
    # Issues found
    issues: List[StrategyIssue] = field(default_factory=list)
    
    # Overall assessment
    overall_score: float = 0  # 0-100
    readiness_level: str = "unknown"  # not_ready, needs_work, ready, production_ready
    
    # Strengths
    strengths: List[str] = field(default_factory=list)
    
    # Weaknesses
    weaknesses: List[str] = field(default_factory=list)
    
    # Suggestions for improvement
    improvement_plan: List[str] = field(default_factory=list)
    
    # Comparison to benchmarks
    benchmarks: Dict[str, float] = field(default_factory=dict)
    
    # Analysis metadata
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    analysis_duration_seconds: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "backtest_id": self.backtest_id,
            "issues": [i.to_dict() for i in self.issues],
            "overall_score": self.overall_score,
            "readiness_level": self.readiness_level,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "improvement_plan": self.improvement_plan,
            "benchmarks": self.benchmarks,
            "analyzed_at": self.analyzed_at.isoformat(),
            "analysis_duration_seconds": self.analysis_duration_seconds,
        }


class AIStrategyCoach:
    """
    AI Strategy Coach for automatic strategy analysis.
    
    Features:
    - Overfitting detection
    - Parameter sensitivity analysis
    - Instability detection
    - Risk analysis
    - Complexity assessment
    - Performance benchmarking
    - Calibration analysis
    - Data leakage detection
    - Actionable recommendations
    """
    
    def __init__(self):
        self._analysis_history: Dict[str, List[CoachAnalysis]] = {}
        self._benchmarks = self._get_default_benchmarks()
    
    def _get_default_benchmarks(self) -> Dict[str, float]:
        """Get default benchmark values"""
        return {
            "min_sharpe_ratio": 1.0,
            "min_win_rate": 0.45,
            "max_drawdown": 15.0,
            "min_trade_count": 50,
            "max_trade_frequency": 20,  # trades per day
            "min_calibration_score": 70.0,
            "max_complexity_score": 50.0,
        }
    
    def analyze(
        self,
        strategy_id: str,
        strategy_name: str,
        backtest_results: Dict[str, Any],
        strategy_graph: Optional[StrategyGraph] = None,
    ) -> CoachAnalysis:
        """
        Analyze a strategy and provide recommendations.
        
        Args:
            strategy_id: Strategy ID
            strategy_name: Strategy name
            backtest_results: Backtest results dictionary
            strategy_graph: Optional strategy graph for complexity analysis
            
        Returns:
            CoachAnalysis with findings and recommendations
        """
        import time
        start_time = time.time()
        
        analysis = CoachAnalysis(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            backtest_id=backtest_results.get("id", str(uuid.uuid4())),
        )
        
        # Run all analyzers
        self._detect_overfitting(backtest_results, analysis)
        self._detect_parameter_sensitivity(backtest_results, analysis)
        self._detect_instability(backtest_results, analysis)
        self._analyze_risk(backtest_results, analysis)
        self._analyze_complexity(strategy_graph, analysis)
        self._analyze_calibration(backtest_results, analysis)
        self._detect_data_leakage(backtest_results, analysis)
        self._analyze_performance(backtest_results, analysis)
        
        # Calculate overall score
        analysis.overall_score = self._calculate_overall_score(analysis)
        
        # Determine readiness level
        analysis.readiness_level = self._determine_readiness(analysis)
        
        # Identify strengths
        self._identify_strengths(backtest_results, analysis)
        
        # Identify weaknesses
        self._identify_weaknesses(analysis)
        
        # Generate improvement plan
        self._generate_improvement_plan(analysis)
        
        # Set benchmarks
        analysis.benchmarks = self._benchmarks.copy()
        
        # Calculate analysis duration
        analysis.analysis_duration_seconds = time.time() - start_time
        
        # Store analysis
        if strategy_id not in self._analysis_history:
            self._analysis_history[strategy_id] = []
        self._analysis_history[strategy_id].append(analysis)
        
        logger.info(
            f"Strategy analysis complete: {strategy_name} "
            f"(Score: {analysis.overall_score:.1f}, "
            f"Issues: {len(analysis.issues)}, "
            f"Duration: {analysis.analysis_duration_seconds:.2f}s)"
        )
        
        return analysis
    
    def _detect_overfitting(
        self,
        results: Dict[str, Any],
        analysis: CoachAnalysis,
    ) -> None:
        """Detect potential overfitting"""
        metrics = results.get("metrics", {})
        
        # Check if win rate is suspiciously high
        win_rate = metrics.get("win_rate", 0)
        if win_rate > 0.70:
            issue = StrategyIssue(
                id=str(uuid.uuid4()),
                category=IssueCategory.OVERFITTING,
                severity=IssueSeverity.WARNING,
                title="Suspiciously High Win Rate",
                description=f"Win rate of {win_rate:.1%} may indicate overfitting or data leakage",
                evidence={"win_rate": win_rate, "threshold": 0.70},
                recommendations=[
                    "Verify training and testing data are properly separated",
                    "Check for look-ahead bias in indicators",
                    "Consider out-of-sample validation",
                    "Compare with random strategy baseline",
                ],
            )
            analysis.issues.append(issue)
        
        # Check profit factor
        profit_factor = metrics.get("profit_factor", 0)
        if profit_factor > 3.0:
            issue = StrategyIssue(
                id=str(uuid.uuid4()),
                category=IssueCategory.OVERFITTING,
                severity=IssueSeverity.INFO,
                title="High Profit Factor",
                description=f"Profit factor of {profit_factor:.2f} is unusually high",
                evidence={"profit_factor": profit_factor, "threshold": 3.0},
                recommendations=[
                    "Verify this performance is consistent across different periods",
                    "Check for survivorship bias",
                ],
            )
            analysis.issues.append(issue)
        
        # Check number of trades vs parameters
        trades = metrics.get("total_trades", 0)
        estimated_params = results.get("estimated_parameters", 5)
        
        if trades < estimated_params * 10:
            issue = StrategyIssue(
                id=str(uuid.uuid4()),
                category=IssueCategory.OVERFITTING,
                severity=IssueSeverity.CRITICAL,
                title="Insufficient Trade Count",
                description=f"Only {trades} trades for ~{estimated_params} parameters may lead to overfitting",
                evidence={
                    "trades": trades,
                    "estimated_parameters": estimated_params,
                    "ratio": trades / estimated_params if estimated_params > 0 else 0,
                },
                recommendations=[
                    "Increase data sample size",
                    "Reduce number of optimized parameters",
                    "Use walk-forward analysis",
                    "Consider simplifying the strategy",
                ],
            )
            analysis.issues.append(issue)
    
    def _detect_parameter_sensitivity(
        self,
        results: Dict[str, Any],
        analysis: CoachAnalysis,
    ) -> None:
        """Detect parameter sensitivity issues"""
        sensitivity = results.get("parameter_sensitivity", {})
        
        if not sensitivity:
            # Estimate based on Sharpe variability
            sharpe_variability = results.get("metrics", {}).get("sharpe_variability", 0)
            if sharpe_variability > 0.5:
                issue = StrategyIssue(
                    id=str(uuid.uuid4()),
                    category=IssueCategory.PARAMETER_SENSITIVITY,
                    severity=IssueSeverity.WARNING,
                    title="High Parameter Sensitivity",
                    description="Strategy may be sensitive to parameter changes",
                    evidence={"sharpe_variability": sharpe_variability},
                    recommendations=[
                        "Use wider parameter ranges",
                        "Implement parameter robustness checks",
                        "Consider averaging across parameter sets",
                    ],
                )
                analysis.issues.append(issue)
            return
        
        # Analyze individual parameter sensitivities
        for param_name, sensitivity_data in sensitivity.items():
            sensitivity_score = sensitivity_data.get("score", 0)
            
            if sensitivity_score > 0.7:
                issue = StrategyIssue(
                    id=str(uuid.uuid4()),
                    category=IssueCategory.PARAMETER_SENSITIVITY,
                    severity=IssueSeverity.WARNING,
                    title=f"Parameter '{param_name}' is Sensitive",
                    description=f"Small changes in '{param_name}' cause large performance changes",
                    evidence={"parameter": param_name, "sensitivity_score": sensitivity_score},
                    recommendations=[
                        f"Consider using a more robust value for '{param_name}'",
                        "Average across a range of values",
                        "Simplify the parameter dependencies",
                    ],
                )
                analysis.issues.append(issue)
    
    def _detect_instability(
        self,
        results: Dict[str, Any],
        analysis: CoachAnalysis,
    ) -> None:
        """Detect strategy instability"""
        metrics = results.get("metrics", {})
        
        # Check Sharpe ratio consistency
        sharpe = metrics.get("sharpe_ratio", 0)
        sharpe_std = metrics.get("sharpe_std", 0)
        
        if sharpe_std > 0.5 and sharpe < 1.5:
            issue = StrategyIssue(
                id=str(uuid.uuid4()),
                category=IssueCategory.INSTABILITY,
                severity=IssueSeverity.WARNING,
                title="Strategy Returns are Unstable",
                description="High variability in returns indicates potential instability",
                evidence={"sharpe_std": sharpe_std, "sharpe": sharpe},
                recommendations=[
                    "Add more stable signals",
                    "Reduce position sizes",
                    "Implement tighter risk controls",
                ],
            )
            analysis.issues.append(issue)
        
        # Check for large drawdown recovery
        max_dd = metrics.get("max_drawdown", 0)
        recovery_time = metrics.get("recovery_time", 0)
        
        if recovery_time > 30 and max_dd > 10:
            issue = StrategyIssue(
                id=str(uuid.uuid4()),
                category=IssueCategory.INSTABILITY,
                severity=IssueSeverity.INFO,
                title="Slow Drawdown Recovery",
                description=f"Strategy takes {recovery_time} days to recover from {max_dd:.1f}% drawdown",
                evidence={"max_drawdown": max_dd, "recovery_time": recovery_time},
                recommendations=[
                    "Implement tighter stop losses",
                    "Reduce exposure during drawdowns",
                    "Consider position sizing adjustments",
                ],
            )
            analysis.issues.append(issue)
    
    def _analyze_risk(
        self,
        results: Dict[str, Any],
        analysis: CoachAnalysis,
    ) -> None:
        """Analyze risk metrics"""
        metrics = results.get("metrics", {})
        
        # Check max drawdown
        max_dd = metrics.get("max_drawdown", 0)
        if max_dd > 20:
            issue = StrategyIssue(
                id=str(uuid.uuid4()),
                category=IssueCategory.RISK,
                severity=IssueSeverity.CRITICAL,
                title="Excessive Drawdown",
                description=f"Maximum drawdown of {max_dd:.1f}% exceeds safe limits",
                evidence={"max_drawdown": max_dd, "threshold": 20},
                recommendations=[
                    "Reduce position sizes",
                    "Implement stricter stop losses",
                    "Add correlation-based risk limits",
                    "Consider adding hedging instruments",
                ],
            )
            analysis.issues.append(issue)
        elif max_dd > 15:
            issue = StrategyIssue(
                id=str(uuid.uuid4()),
                category=IssueCategory.RISK,
                severity=IssueSeverity.WARNING,
                title="Elevated Drawdown",
                description=f"Maximum drawdown of {max_dd:.1f}% is elevated",
                evidence={"max_drawdown": max_dd, "threshold": 15},
                recommendations=[
                    "Review position sizing",
                    "Add drawdown-based position reduction",
                ],
            )
            analysis.issues.append(issue)
        
        # Check trade frequency risk
        trade_freq = metrics.get("trade_frequency", 0)
        if trade_freq > self._benchmarks["max_trade_frequency"]:
            issue = StrategyIssue(
                id=str(uuid.uuid4()),
                category=IssueCategory.RISK,
                severity=IssueSeverity.WARNING,
                title="High Trade Frequency",
                description=f"Average of {trade_freq:.1f} trades/day may increase costs and risk",
                evidence={"trade_frequency": trade_freq, "threshold": self._benchmarks["max_trade_frequency"]},
                recommendations=[
                    "Consider filtering signals more strictly",
                    "Implement minimum holding periods",
                    "Review transaction cost impact",
                ],
            )
            analysis.issues.append(issue)
    
    def _analyze_complexity(
        self,
        graph: Optional[StrategyGraph],
        analysis: CoachAnalysis,
    ) -> None:
        """Analyze strategy complexity"""
        if not graph:
            return
        
        # Count blocks
        num_blocks = len(graph.blocks)
        num_connections = len(graph.connections)
        
        # Calculate complexity score
        complexity_score = num_blocks + (num_connections * 0.5)
        
        if complexity_score > self._benchmarks["max_complexity_score"]:
            issue = StrategyIssue(
                id=str(uuid.uuid4()),
                category=IssueCategory.COMPLEXITY,
                severity=IssueSeverity.INFO,
                title="Strategy is Complex",
                description=f"Strategy has {num_blocks} blocks and {num_connections} connections",
                evidence={
                    "blocks": num_blocks,
                    "connections": num_connections,
                    "complexity_score": complexity_score,
                },
                recommendations=[
                    "Consider simplifying the strategy",
                    "Remove redundant blocks",
                    "Simplify connection flow",
                    "Higher complexity increases maintenance burden",
                ],
            )
            analysis.issues.append(issue)
    
    def _analyze_calibration(
        self,
        results: Dict[str, Any],
        analysis: CoachAnalysis,
    ) -> None:
        """Analyze confidence calibration"""
        calibration = results.get("calibration", {})
        
        if not calibration:
            return
        
        calibration_score = calibration.get("score", 0)
        
        if calibration_score < self._benchmarks["min_calibration_score"]:
            issue = StrategyIssue(
                id=str(uuid.uuid4()),
                category=IssueCategory.CALIBRATION,
                severity=IssueSeverity.WARNING,
                title="Poor Confidence Calibration",
                description=f"Confidence calibration score of {calibration_score:.1f}% indicates miscalibrated probabilities",
                evidence={"calibration_score": calibration_score},
                recommendations=[
                    "Review confidence threshold settings",
                    "Implement proper probability calibration",
                    "Use larger sample sizes for confidence estimation",
                ],
            )
            analysis.issues.append(issue)
    
    def _detect_data_leakage(
        self,
        results: Dict[str, Any],
        analysis: CoachAnalysis,
    ) -> None:
        """Detect potential data leakage"""
        leakage_indicators = results.get("leakage_indicators", {})
        
        # Check for look-ahead bias
        if leakage_indicators.get("look_ahead_detected"):
            issue = StrategyIssue(
                id=str(uuid.uuid4()),
                category=IssueCategory.DATA_LEAKAGE,
                severity=IssueSeverity.CRITICAL,
                title="Potential Look-Ahead Bias Detected",
                description="Strategy may be using future data",
                evidence=leakage_indicators,
                recommendations=[
                    "Review all indicator calculations",
                    "Ensure proper time alignment",
                    "Use only available data at each point",
                ],
            )
            analysis.issues.append(issue)
        
        # Check for survivorship bias
        if leakage_indicators.get("survivorship_bias_detected"):
            issue = StrategyIssue(
                id=str(uuid.uuid4()),
                category=IssueCategory.DATA_LEAKAGE,
                severity=IssueSeverity.WARNING,
                title="Potential Survivorship Bias",
                description="Backtest may include delisted or failed assets",
                evidence=leakage_indicators,
                recommendations=[
                    "Use point-in-time data",
                    "Include delisted assets in dataset",
                    "Verify data sources",
                ],
            )
            analysis.issues.append(issue)
    
    def _analyze_performance(
        self,
        results: Dict[str, Any],
        analysis: CoachAnalysis,
    ) -> None:
        """Analyze overall performance"""
        metrics = results.get("metrics", {})
        
        # Check Sharpe ratio
        sharpe = metrics.get("sharpe_ratio", 0)
        if sharpe < self._benchmarks["min_sharpe_ratio"]:
            issue = StrategyIssue(
                id=str(uuid.uuid4()),
                category=IssueCategory.PERFORMANCE,
                severity=IssueSeverity.INFO,
                title="Below-Target Sharpe Ratio",
                description=f"Sharpe ratio of {sharpe:.2f} is below target of {self._benchmarks['min_sharpe_ratio']}",
                evidence={"sharpe_ratio": sharpe, "target": self._benchmarks["min_sharpe_ratio"]},
                recommendations=[
                    "Optimize entry/exit conditions",
                    "Improve signal quality",
                    "Review risk-adjusted returns",
                ],
            )
            analysis.issues.append(issue)
    
    def _calculate_overall_score(self, analysis: CoachAnalysis) -> float:
        """Calculate overall strategy score (0-100)"""
        base_score = 100
        
        # Deduct for issues
        deductions = {
            IssueSeverity.CRITICAL: 20,
            IssueSeverity.WARNING: 10,
            IssueSeverity.INFO: 3,
        }
        
        for issue in analysis.issues:
            deduction = deductions.get(issue.severity, 5)
            analysis.overall_score -= deduction
        
        return max(0, min(100, base_score - analysis.overall_score))
    
    def _determine_readiness(self, analysis: CoachAnalysis) -> str:
        """Determine strategy readiness level"""
        critical_issues = sum(
            1 for i in analysis.issues
            if i.severity == IssueSeverity.CRITICAL
        )
        warning_issues = sum(
            1 for i in analysis.issues
            if i.severity == IssueSeverity.WARNING
        )
        
        if critical_issues > 0:
            return "not_ready"
        elif warning_issues > 2:
            return "needs_work"
        elif warning_issues > 0:
            return "ready"
        elif analysis.overall_score >= 90:
            return "production_ready"
        else:
            return "ready"
    
    def _identify_strengths(self, results: Dict[str, Any], analysis: CoachAnalysis) -> None:
        """Identify strategy strengths"""
        metrics = results.get("metrics", {})
        
        if metrics.get("sharpe_ratio", 0) >= 2.0:
            analysis.strengths.append("Excellent risk-adjusted returns (Sharpe ≥ 2.0)")
        
        if metrics.get("win_rate", 0) >= 0.55 and metrics.get("win_rate", 0) <= 0.65:
            analysis.strengths.append("Consistent win rate in realistic range")
        
        if metrics.get("max_drawdown", 100) <= 10:
            analysis.strengths.append("Well-controlled drawdowns")
        
        if metrics.get("profit_factor", 0) >= 1.5 and metrics.get("profit_factor", 0) <= 2.5:
            analysis.strengths.append("Good profit factor indicating positive expectancy")
    
    def _identify_weaknesses(self, analysis: CoachAnalysis) -> None:
        """Identify strategy weaknesses from issues"""
        categories = {}
        
        for issue in analysis.issues:
            if issue.category not in categories:
                categories[issue.category] = []
            categories[issue.category].append(issue.title)
        
        for category, issues in categories.items():
            if len(issues) >= 2:
                analysis.weaknesses.append(f"Multiple {category.value} issues detected")
    
    def _generate_improvement_plan(self, analysis: CoachAnalysis) -> None:
        """Generate prioritized improvement plan"""
        # Sort issues by severity
        sorted_issues = sorted(
            analysis.issues,
            key=lambda i: [IssueSeverity.CRITICAL, IssueSeverity.WARNING, IssueSeverity.INFO].index(i.severity)
        )
        
        # Add top recommendations
        for issue in sorted_issues[:5]:
            if issue.recommendations:
                analysis.improvement_plan.append(
                    f"Priority: Address '{issue.title}' - {issue.recommendations[0]}"
                )
    
    def get_analysis_history(self, strategy_id: str) -> List[CoachAnalysis]:
        """Get analysis history for a strategy"""
        return self._analysis_history.get(strategy_id, [])
    
    def get_latest_analysis(self, strategy_id: str) -> Optional[CoachAnalysis]:
        """Get latest analysis for a strategy"""
        history = self._analysis_history.get(strategy_id, [])
        return history[-1] if history else None
