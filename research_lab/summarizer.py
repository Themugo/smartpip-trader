"""
Conclusion Summarizer
====================

Generates summaries and conclusions from research.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


class ConclusionType(Enum):
    """Types of conclusions"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    INCONCLUSIVE = "inconclusive"
    NEEDS_MORE_DATA = "needs_more_data"
    REQUIRES_VALIDATION = "requires_validation"


@dataclass
class Conclusion:
    """A single conclusion"""
    type: ConclusionType
    statement: str
    supporting_evidence: List[str]
    confidence: float
    caveats: List[str]


@dataclass
class ResearchSummary:
    """Summary of research"""
    id: str
    hypothesis: Dict[str, Any]
    experiment_summary: Dict[str, Any]
    statistical_summary: Dict[str, Any]
    benchmark_summary: Dict[str, Any]
    main_conclusion: Conclusion
    additional_conclusions: List[Conclusion]
    recommendations: List[str]
    key_findings: List[str]
    limitations: List[str]
    next_steps: List[str]
    generated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "hypothesis": self.hypothesis.get("description", ""),
            "main_conclusion": {
                "type": self.main_conclusion.type.value,
                "statement": self.main_conclusion.statement
            },
            "recommendations": self.recommendations,
            "key_findings": self.key_findings,
            "generated_at": self.generated_at.isoformat()
        }


class ConclusionSummarizer:
    """
    Generates summaries and conclusions from research results.
    """
    
    def __init__(self):
        self.summaries: Dict[str, ResearchSummary] = {}
    
    def summarize(
        self,
        hypothesis: Any,
        experiment_result: Any,
        statistical_result: Any,
        benchmark_result: Any
    ) -> ResearchSummary:
        """
        Generate comprehensive summary.
        
        Args:
            hypothesis: Hypothesis object
            experiment_result: ExperimentResult
            statistical_result: StatisticalResult
            benchmark_result: BenchmarkResult
            
        Returns:
            ResearchSummary
        """
        # Determine main conclusion
        main_conclusion = self._determine_conclusion(
            experiment_result,
            statistical_result,
            benchmark_result
        )
        
        # Generate additional conclusions
        additional = self._generate_additional_conclusions(
            hypothesis,
            experiment_result,
            statistical_result,
            benchmark_result
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            hypothesis,
            main_conclusion,
            statistical_result
        )
        
        # Extract key findings
        key_findings = self._extract_key_findings(
            experiment_result,
            statistical_result,
            benchmark_result
        )
        
        # Identify limitations
        limitations = self._identify_limitations(
            experiment_result,
            statistical_result
        )
        
        # Suggest next steps
        next_steps = self._suggest_next_steps(
            main_conclusion,
            statistical_result,
            hypothesis
        )
        
        summary = ResearchSummary(
            id=str(uuid4()),
            hypothesis=hypothesis.to_dict() if hasattr(hypothesis, 'to_dict') else {},
            experiment_summary=self._summarize_experiment(experiment_result),
            statistical_summary=self._summarize_statistics(statistical_result),
            benchmark_summary=self._summarize_benchmark(benchmark_result),
            main_conclusion=main_conclusion,
            additional_conclusions=additional,
            recommendations=recommendations,
            key_findings=key_findings,
            limitations=limitations,
            next_steps=next_steps
        )
        
        self.summaries[summary.id] = summary
        
        logger.info(f"Generated summary: {main_conclusion.type.value}")
        
        return summary
    
    def _determine_conclusion(
        self,
        experiment_result: Any,
        statistical_result: Any,
        benchmark_result: Any
    ) -> Conclusion:
        """Determine main conclusion"""
        # Check statistical significance
        is_significant = statistical_result.is_significant if statistical_result else False
        
        # Check outperformance
        is_outperforming = benchmark_result.is_outperforming if benchmark_result else False
        
        # Check return
        total_return = experiment_result.metrics.get("total_return", 0) if experiment_result else 0
        is_profitable = total_return > 0
        
        # Determine conclusion type
        if is_significant and is_outperforming and is_profitable:
            ctype = ConclusionType.POSITIVE
            statement = (
                f"The hypothesis is supported. The strategy shows statistically "
                f"significant outperformance (p={statistical_result.p_value:.4f}, "
                f"IR={benchmark_result.information_ratio:.3f}) with positive returns."
            )
            confidence = min(0.95, statistical_result.power + 0.1)
            caveats = []
            
        elif is_significant and not is_profitable:
            ctype = ConclusionType.NEGATIVE
            statement = (
                f"The hypothesis is rejected. While statistically significant, "
                f"the strategy produces negative returns."
            )
            confidence = statistical_result.power
            caveats = ["Results may not generalize to future periods"]
            
        elif not is_significant and is_profitable:
            ctype = ConclusionType.NEEDS_MORE_DATA
            statement = (
                f"Results are promising but not statistically significant. "
                f"More data is needed to validate the strategy."
            )
            confidence = 0.5
            caveats = ["Positive returns may be due to luck"]
            
        elif not is_significant:
            ctype = ConclusionType.INCONCLUSIVE
            statement = (
                f"The experiment is inconclusive. No statistically significant "
                f"evidence supports or refutes the hypothesis."
            )
            confidence = 0.4
            caveats = ["Sample size may be insufficient"]
            
        else:
            ctype = ConclusionType.REQUIRES_VALIDATION
            statement = (
                f"Results require further validation before drawing conclusions."
            )
            confidence = 0.3
            caveats = ["Results may be sensitive to parameter choices"]
        
        return Conclusion(
            type=ctype,
            statement=statement,
            supporting_evidence=self._get_supporting_evidence(
                experiment_result,
                statistical_result,
                benchmark_result
            ),
            confidence=confidence,
            caveats=caveats
        )
    
    def _get_supporting_evidence(
        self,
        experiment_result: Any,
        statistical_result: Any,
        benchmark_result: Any
    ) -> List[str]:
        """Get supporting evidence"""
        evidence = []
        
        if experiment_result:
            if experiment_result.metrics.get("sharpe_ratio", 0) > 1:
                evidence.append(f"Sharpe ratio of {experiment_result.metrics['sharpe_ratio']:.2f}")
            if experiment_result.metrics.get("win_rate", 0) > 0.5:
                evidence.append(f"Win rate of {experiment_result.metrics['win_rate']:.1%}")
        
        if statistical_result and statistical_result.is_significant:
            evidence.append(f"Statistically significant at {1-statistical_result.significance_level:.0%} confidence")
        
        if benchmark_result and benchmark_result.is_outperforming:
            evidence.append(f"Outperforms benchmark by {benchmark_result.excess_return:.2%}")
        
        return evidence
    
    def _generate_additional_conclusions(
        self,
        hypothesis: Any,
        experiment_result: Any,
        statistical_result: Any,
        benchmark_result: Any
    ) -> List[Conclusion]:
        """Generate additional conclusions"""
        conclusions = []
        
        # Risk-adjusted performance
        if experiment_result:
            sharpe = experiment_result.metrics.get("sharpe_ratio", 0)
            if sharpe > 1.5:
                conclusions.append(Conclusion(
                    type=ConclusionType.POSITIVE,
                    statement=f"Excellent risk-adjusted returns with Sharpe ratio of {sharpe:.2f}",
                    supporting_evidence=["High Sharpe ratio"],
                    confidence=0.8,
                    caveats=[]
                ))
            elif sharpe < 0.5:
                conclusions.append(Conclusion(
                    type=ConclusionType.NEGATIVE,
                    statement=f"Poor risk-adjusted returns with Sharpe ratio of {sharpe:.2f}",
                    supporting_evidence=["Low Sharpe ratio"],
                    confidence=0.8,
                    caveats=["Strategy may not be suitable for risk-averse portfolios"]
                ))
        
        # Drawdown analysis
        if experiment_result:
            max_dd = experiment_result.metrics.get("max_drawdown", 0)
            if max_dd > 0.15:
                conclusions.append(Conclusion(
                    type=ConclusionType.NEGATIVE,
                    statement=f"High maximum drawdown of {max_dd:.1%} raises risk concerns",
                    supporting_evidence=[f"Max drawdown: {max_dd:.1%}"],
                    confidence=0.7,
                    caveats=["Historical drawdown may not predict future drawdowns"]
                ))
        
        return conclusions
    
    def _generate_recommendations(
        self,
        hypothesis: Any,
        main_conclusion: Conclusion,
        statistical_result: Any
    ) -> List[str]:
        """Generate recommendations"""
        recommendations = []
        
        if main_conclusion.type == ConclusionType.POSITIVE:
            recommendations.append("Consider paper trading to validate live performance")
            recommendations.append("Explore parameter optimization to improve results")
            
        elif main_conclusion.type == ConclusionType.NEGATIVE:
            recommendations.append("Investigate failure modes and potential improvements")
            recommendations.append("Consider combining with other strategies")
            
        elif main_conclusion.type == ConclusionType.NEEDS_MORE_DATA:
            recommendations.append("Run extended backtest with more data")
            recommendations.append("Consider increasing trade frequency for more samples")
            
        elif main_conclusion.type == ConclusionType.INCONCLUSIVE:
            recommendations.append("Re-examine hypothesis and experiment design")
            recommendations.append("Consider alternative data sources")
        
        if statistical_result and not statistical_result.assumptions_valid:
            recommendations.append("Address statistical assumption violations")
        
        return recommendations
    
    def _extract_key_findings(
        self,
        experiment_result: Any,
        statistical_result: Any,
        benchmark_result: Any
    ) -> List[str]:
        """Extract key findings"""
        findings = []
        
        if experiment_result:
            findings.append(
                f"Total return: {experiment_result.metrics.get('total_return', 0):.2%}"
            )
            findings.append(
                f"Sharpe ratio: {experiment_result.metrics.get('sharpe_ratio', 0):.2f}"
            )
            findings.append(
                f"Max drawdown: {experiment_result.metrics.get('max_drawdown', 0):.2%}"
            )
            findings.append(
                f"Trade count: {experiment_result.metrics.get('trade_count', 0)}"
            )
        
        if statistical_result:
            findings.append(
                f"P-value: {statistical_result.p_value:.4f}"
            )
            findings.append(
                f"Effect size (Cohen's d): {statistical_result.effect_size:.3f}"
            )
        
        if benchmark_result:
            findings.append(
                f"Information ratio: {benchmark_result.information_ratio:.3f}"
            )
            findings.append(
                f"Excess return: {benchmark_result.excess_return:.2%}"
            )
        
        return findings
    
    def _identify_limitations(
        self,
        experiment_result: Any,
        statistical_result: Any
    ) -> List[str]:
        """Identify study limitations"""
        limitations = []
        
        if statistical_result and not statistical_result.assumptions_valid:
            if not statistical_result.assumptions_check.get("normality"):
                limitations.append("Return distribution may not be normal")
            if not statistical_result.assumptions_check.get("sample_size"):
                limitations.append("Sample size may be insufficient for robust inference")
        
        if experiment_result:
            if experiment_result.metrics.get("trade_count", 0) < 30:
                limitations.append("Low trade count limits statistical power")
        
        limitations.append("Backtest results may not predict future performance")
        limitations.append("Market conditions may change")
        
        return limitations
    
    def _suggest_next_steps(
        self,
        main_conclusion: Conclusion,
        statistical_result: Any,
        hypothesis: Any
    ) -> List[str]:
        """Suggest next research steps"""
        steps = []
        
        if main_conclusion.type in [ConclusionType.POSITIVE, ConclusionType.NEEDS_MORE_DATA]:
            steps.append("Extend backtest period to validate robustness")
            steps.append("Test on out-of-sample data")
            steps.append("Perform sensitivity analysis on parameters")
        
        elif main_conclusion.type == ConclusionType.NEGATIVE:
            steps.append("Analyze loss patterns to identify improvement opportunities")
            steps.append("Consider alternative entry/exit criteria")
            steps.append("Explore regime-specific approaches")
        
        else:
            steps.append("Refine hypothesis based on findings")
            steps.append("Gather additional market data")
            steps.append("Consider ensemble approaches")
        
        return steps
    
    def _summarize_experiment(self, result: Any) -> Dict[str, Any]:
        """Summarize experiment results"""
        if not result:
            return {}
        
        return {
            "total_return": result.metrics.get("total_return", 0),
            "sharpe_ratio": result.metrics.get("sharpe_ratio", 0),
            "max_drawdown": result.metrics.get("max_drawdown", 0),
            "win_rate": result.metrics.get("win_rate", 0),
            "trade_count": result.metrics.get("trade_count", 0)
        }
    
    def _summarize_statistics(self, result: Any) -> Dict[str, Any]:
        """Summarize statistical results"""
        if not result:
            return {}
        
        return {
            "p_value": result.p_value,
            "is_significant": result.is_significant,
            "effect_size": result.effect_size,
            "confidence_interval": list(result.confidence_interval),
            "power": result.power
        }
    
    def _summarize_benchmark(self, result: Any) -> Dict[str, Any]:
        """Summarize benchmark comparison"""
        if not result:
            return {}
        
        return {
            "benchmark_type": result.benchmark_type.value,
            "excess_return": result.excess_return,
            "information_ratio": result.information_ratio,
            "is_outperforming": result.is_outperforming
        }
