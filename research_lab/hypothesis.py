"""
Hypothesis Generator
===================

Generates research hypotheses from data patterns and market analysis.
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


class HypothesisType(Enum):
    """Types of research hypotheses"""
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    CORRELATION = "correlation"
    PATTERN = "pattern"
    REGIME = "regime"
    SEASONAL = "seasonal"
    CROSS_ASSET = "cross_asset"


@dataclass
class Variable:
    """A variable in a hypothesis"""
    name: str
    type: str  # price, volume, volatility, indicator, time
    description: str


@dataclass
class Hypothesis:
    """A research hypothesis"""
    id: str
    type: HypothesisType
    description: str
    variables: List[Variable]
    expected_direction: str  # positive, negative, mixed
    confidence: float  # 0-1 initial confidence
    rationale: str
    supporting_evidence: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "variables": [v.__dict__ for v in self.variables],
            "expected_direction": self.expected_direction,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "supporting_evidence": self.supporting_evidence
        }


class HypothesisGenerator:
    """
    Generates research hypotheses for algorithmic trading.
    """
    
    def __init__(
        self,
        min_confidence: float = 0.4,
        max_hypotheses: int = 20
    ):
        self.min_confidence = min_confidence
        self.max_hypotheses = max_hypotheses
        self.generated_hypotheses: List[Hypothesis] = []
        self.hypothesis_templates = self._get_templates()
    
    def generate_hypotheses(
        self,
        count: int = 5,
        existing_hypotheses: Optional[List[Hypothesis]] = None,
        market_data: Optional[Dict[str, Any]] = None
    ) -> List[Hypothesis]:
        """
        Generate new research hypotheses.
        
        Args:
            count: Number of hypotheses to generate
            existing_hypotheses: Hypotheses to avoid duplicating
            market_data: Optional market context
            
        Returns:
            List of generated hypotheses
        """
        existing = existing_hypotheses or []
        existing_ids = {h.id for h in existing}
        
        hypotheses = []
        types_to_generate = [
            HypothesisType.MEAN_REVERSION,
            HypothesisType.MOMENTUM,
            HypothesisType.VOLATILITY,
            HypothesisType.CORRELATION,
            HypothesisType.PATTERN,
            HypothesisType.REGIME
        ]
        
        for _ in range(count):
            htype = random.choice(types_to_generate)
            hypothesis = self._generate_single(htype, market_data)
            
            # Check for duplicates
            if hypothesis.id not in existing_ids:
                hypotheses.append(hypothesis)
                self.generated_hypotheses.append(hypothesis)
                existing_ids.add(hypothesis.id)
        
        logger.info(f"Generated {len(hypotheses)} new hypotheses")
        return hypotheses
    
    def _generate_single(
        self,
        htype: HypothesisType,
        market_data: Optional[Dict[str, Any]] = None
    ) -> Hypothesis:
        """Generate a single hypothesis of given type"""
        templates = self.hypothesis_templates.get(htype, [])
        
        if not templates:
            # Generate generic hypothesis
            return self._generate_generic(htype)
        
        template = random.choice(templates)
        hypothesis = self._apply_template(template, htype)
        
        return hypothesis
    
    def _generate_generic(self, htype: HypothesisType) -> Hypothesis:
        """Generate a generic hypothesis"""
        description = f"Exploring {htype.value.replace('_', ' ')} patterns in market data"
        
        return Hypothesis(
            id=str(uuid4()),
            type=htype,
            description=description,
            variables=[Variable("price", "price", "Historical price data")],
            expected_direction="mixed",
            confidence=random.uniform(0.5, 0.8),
            rationale="Initial exploratory analysis"
        )
    
    def _apply_template(
        self,
        template: Dict[str, Any],
        htype: HypothesisType
    ) -> Hypothesis:
        """Apply a template to generate hypothesis"""
        description = template["description"].format(
            asset=random.choice(["R_50", "R_75", "VOL"]),
            timeframe=random.choice(["1min", "5min", "15min", "1h"]),
            indicator=random.choice(["SMA", "EMA", "RSI", "MACD", "BB"])
        )
        
        variables = [
            Variable(v["name"], v["type"], v["desc"])
            for v in template.get("variables", [])
        ]
        
        return Hypothesis(
            id=str(uuid4()),
            type=htype,
            description=description,
            variables=variables,
            expected_direction=template.get("expected", "mixed"),
            confidence=template.get("base_confidence", 0.6),
            rationale=template.get("rationale", "Pattern analysis"),
            supporting_evidence=template.get("evidence", [])
        )
    
    def _assess_novelty(self, hypothesis: Hypothesis) -> float:
        """Assess novelty of hypothesis"""
        # Check against generated hypotheses
        for existing in self.generated_hypotheses[-20:]:
            if hypothesis.type == existing.type:
                # Same type - check description similarity
                similarity = self._calculate_similarity(
                    hypothesis.description,
                    existing.description
                )
                if similarity > 0.7:
                    return 0.3  # Low novelty
        
        return 0.7  # High novelty
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _get_templates(self) -> Dict[HypothesisType, List[Dict[str, Any]]]:
        """Get hypothesis templates by type"""
        return {
            HypothesisType.MEAN_REVERSION: [
                {
                    "description": "Prices of {asset} will revert to {indicator} mean within {timeframe}",
                    "variables": [
                        {"name": "price", "type": "price", "desc": "Asset price"},
                        {"name": "indicator", "type": "indicator", "desc": "Moving average"}
                    ],
                    "expected": "positive",
                    "base_confidence": 0.65,
                    "rationale": "Mean reversion is common in bounded markets",
                    "evidence": ["Historical price clustering", "Central bank interventions"]
                },
                {
                    "description": "High volatility in {asset} indicates mean reversion opportunity",
                    "variables": [
                        {"name": "volatility", "type": "volatility", "desc": "Price volatility"},
                        {"name": "returns", "type": "indicator", "desc": "Historical returns"}
                    ],
                    "expected": "positive",
                    "base_confidence": 0.60,
                    "rationale": "Extreme moves often correct",
                    "evidence": ["Volatility clustering", "Historical patterns"]
                }
            ],
            HypothesisType.MOMENTUM: [
                {
                    "description": "{asset} exhibits {timeframe} momentum continuation",
                    "variables": [
                        {"name": "returns", "type": "indicator", "desc": "Historical returns"},
                        {"name": "volume", "type": "volume", "desc": "Trading volume"}
                    ],
                    "expected": "positive",
                    "base_confidence": 0.55,
                    "rationale": "Trending markets persist",
                    "evidence": ["Trend persistence", "Volume confirmation"]
                },
                {
                    "description": "{indicator} crossover signals momentum shift in {asset}",
                    "variables": [
                        {"name": "indicator1", "type": "indicator", "desc": "Fast indicator"},
                        {"name": "indicator2", "type": "indicator", "desc": "Slow indicator"}
                    ],
                    "expected": "mixed",
                    "base_confidence": 0.50,
                    "rationale": "Crossovers indicate trend changes",
                    "evidence": ["Moving average crossovers", "Historical signals"]
                }
            ],
            HypothesisType.VOLATILITY: [
                {
                    "description": "{asset} volatility predicts near-term returns",
                    "variables": [
                        {"name": "volatility", "type": "volatility", "desc": "Realized volatility"},
                        {"name": "returns", "type": "price", "desc": "Future returns"}
                    ],
                    "expected": "negative",
                    "base_confidence": 0.60,
                    "rationale": "High vol often precedes low returns",
                    "evidence": ["Volatility risk premium", "Empirical studies"]
                },
                {
                    "description": "Volatility regime changes in {asset} indicate market shifts",
                    "variables": [
                        {"name": "volatility", "type": "volatility", "desc": "Volatility level"},
                        {"name": "regime", "type": "indicator", "desc": "Market regime"}
                    ],
                    "expected": "mixed",
                    "base_confidence": 0.55,
                    "rationale": "Regime changes affect strategies",
                    "evidence": ["Volatility clustering", "Regime persistence"]
                }
            ],
            HypothesisType.CORRELATION: [
                {
                    "description": "{asset} correlation with market index predicts direction",
                    "variables": [
                        {"name": "correlation", "type": "indicator", "desc": "Rolling correlation"},
                        {"name": "returns", "type": "price", "desc": "Asset returns"}
                    ],
                    "expected": "positive",
                    "base_confidence": 0.50,
                    "rationale": "Correlation indicates market exposure",
                    "evidence": ["Beta relationships", "Market correlation"]
                }
            ],
            HypothesisType.PATTERN: [
                {
                    "description": "Technical patterns in {asset} predict {timeframe} movements",
                    "variables": [
                        {"name": "pattern", "type": "indicator", "desc": "Pattern identifier"},
                        {"name": "price", "type": "price", "desc": "Price series"}
                    ],
                    "expected": "mixed",
                    "base_confidence": 0.45,
                    "rationale": "Historical patterns repeat",
                    "evidence": ["Technical analysis", "Chart patterns"]
                },
                {
                    "description": "Candlestick patterns in {asset} signal reversals",
                    "variables": [
                        {"name": "candles", "type": "price", "desc": "OHLC data"},
                        {"name": "volume", "type": "volume", "desc": "Volume confirmation"}
                    ],
                    "expected": "mixed",
                    "base_confidence": 0.40,
                    "rationale": "Candlestick patterns indicate sentiment",
                    "evidence": ["Price action", "Volume confirmation"]
                }
            ],
            HypothesisType.REGIME: [
                {
                    "description": "{asset} regime changes affect optimal strategy parameters",
                    "variables": [
                        {"name": "regime", "type": "indicator", "desc": "Market regime"},
                        {"name": "strategy_params", "type": "indicator", "desc": "Strategy parameters"}
                    ],
                    "expected": "positive",
                    "base_confidence": 0.65,
                    "rationale": "Regime-specific strategies perform better",
                    "evidence": ["Regime detection", "Adaptive strategies"]
                },
                {
                    "description": "Low volatility regime in {asset} favors mean reversion",
                    "variables": [
                        {"name": "volatility", "type": "volatility", "desc": "Volatility level"},
                        {"name": "strategy", "type": "indicator", "desc": "Strategy type"}
                    ],
                    "expected": "positive",
                    "base_confidence": 0.60,
                    "rationale": "Strategy-regime alignment improves results",
                    "evidence": ["Volatility regimes", "Strategy performance"]
                }
            ]
        }
    
    def get_hypothesis_by_id(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Get hypothesis by ID"""
        for h in self.generated_hypotheses:
            if h.id == hypothesis_id:
                return h
        return None
    
    def get_hypotheses_by_type(
        self,
        htype: HypothesisType
    ) -> List[Hypothesis]:
        """Get all hypotheses of a given type"""
        return [h for h in self.generated_hypotheses if h.type == htype]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about generated hypotheses"""
        by_type = {}
        for h in self.generated_hypotheses:
            type_name = h.type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        return {
            "total": len(self.generated_hypotheses),
            "by_type": by_type,
            "avg_confidence": np.mean([h.confidence for h in self.generated_hypotheses]) if self.generated_hypotheses else 0
        }
