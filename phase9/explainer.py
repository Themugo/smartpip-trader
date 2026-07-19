"""
Decision Explainer - Comprehensive Trade Explanation

Generate detailed explanations for every trade decision.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExplanationComponent:
    """A component of an explanation"""
    component_type: str  # "summary", "confidence", "analyzer", "history", "risk", "probability"
    title: str
    content: str
    importance: float = 1.0  # 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyzerVote:
    """Vote from a single analyzer"""
    analyzer_name: str
    analyzer_type: str
    signal: str  # "buy", "sell", "neutral"
    confidence: float
    reasoning: str
    weight: float = 1.0


@dataclass
class HistoricalAnalogue:
    """A historical situation similar to the current one"""
    trade_id: str
    timestamp: datetime
    similarity_score: float
    outcome: str
    outcome_value: float
    key_differences: List[str]


@dataclass
class TradeExplanation:
    """Complete explanation for a trade decision"""
    trade_id: str
    symbol: str
    action: str
    amount: float
    price: float
    
    # Executive summary
    summary: str = ""
    
    # Confidence explanation
    confidence: float = 0
    confidence_factors: List[str] = field(default_factory=list)
    
    # Analyzer votes
    analyzer_votes: List[AnalyzerVote] = field(default_factory=list)
    consensus_score: float = 0
    
    # Historical analogues
    analogues: List[HistoricalAnalogue] = field(default_factory=list)
    
    # Risk analysis
    risk_score: float = 0
    risk_factors: List[str] = field(default_factory=list)
    
    # Probability distribution
    probability_distribution: Dict[str, float] = field(default_factory=dict)
    
    # Reasoning chain
    reasoning_chain: List[ExplanationComponent] = field(default_factory=list)
    
    # Alternatives considered
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    
    # Expected value
    expected_value: float = 0
    expected_return: float = 0
    expected_loss: float = 0
    
    # Metadata
    regime: str = "unknown"
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "action": self.action,
            "amount": self.amount,
            "price": self.price,
            "summary": self.summary,
            "confidence": self.confidence,
            "consensus_score": self.consensus_score,
            "risk_score": self.risk_score,
            "expected_value": self.expected_value,
            "expected_return": self.expected_return,
            "expected_loss": self.expected_loss,
            "regime": self.regime,
            "timestamp": self.timestamp.isoformat(),
            "analyzer_votes": [
                {
                    "name": v.analyzer_name,
                    "signal": v.signal,
                    "confidence": v.confidence,
                    "reasoning": v.reasoning,
                }
                for v in self.analyzer_votes
            ],
            "reasoning_chain": [
                {
                    "type": c.component_type,
                    "title": c.title,
                    "content": c.content,
                }
                for c in self.reasoning_chain
            ],
        }
    
    def to_markdown(self) -> str:
        """Format explanation as markdown"""
        md = f"""# Trade Decision Explanation

## Overview
- **Symbol:** {self.symbol}
- **Action:** {self.action}
- **Amount:** {self.amount}
- **Price:** {self.price:.5f}
- **Confidence:** {self.confidence:.1f}%
- **Risk Score:** {self.risk_score:.1f}/100

## Executive Summary
{self.summary}

## Analyzer Votes
| Analyzer | Signal | Confidence | Reasoning |
|----------|--------|-------------|-----------|
"""
        for vote in self.analyzer_votes:
            md += f"| {vote.analyzer_name} | {vote.signal} | {vote.confidence:.1f}% | {vote.reasoning} |\n"
        
        md += f"""
## Expected Value
- **Expected Value:** ${self.expected_value:.2f}
- **Expected Return:** ${self.expected_return:.2f}
- **Expected Loss:** ${self.expected_loss:.2f}

## Risk Analysis
Risk Score: {self.risk_score:.1f}/100
"""
        for factor in self.risk_factors:
            md += f"- {factor}\n"
        
        md += """
## Reasoning Chain
"""
        for i, component in enumerate(self.reasoning_chain, 1):
            md += f"{i}. **{component.title}**: {component.content}\n"
        
        if self.alternatives:
            md += """
## Alternatives Considered
"""
            for alt in self.alternatives:
                md += f"- **{alt['action']}**: {alt['reason']}\n"
        
        if self.analogues:
            md += """
## Historical Analogues
"""
            for analogue in self.analogues[:3]:
                md += f"- Similar trade on {analogue.timestamp.strftime('%Y-%m-%d')} "
                md += f"(similarity: {analogue.similarity_score:.1f}%) - {analogue.outcome}\n"
        
        return md


class DecisionExplainer:
    """
    Decision Explainer - Generate comprehensive trade explanations.
    
    Features:
    - Executive summary generation
    - Confidence explanation
    - Analyzer vote aggregation
    - Historical analogue search
    - Expected value calculation
    - Risk analysis
    - Probability distribution
    - Reasoning chain
    - Alternative action analysis
    """
    
    def __init__(self):
        self._explanations: Dict[str, TradeExplanation] = {}
    
    def explain_trade(
        self,
        trade_id: str,
        trade_data: Dict[str, Any],
        signals: List[Dict[str, Any]],
        market_context: Dict[str, Any],
        historical_trades: List[Dict[str, Any]],
    ) -> TradeExplanation:
        """Generate a complete explanation for a trade"""
        
        explanation = TradeExplanation(
            trade_id=trade_id,
            symbol=trade_data.get("symbol", ""),
            action=trade_data.get("action", ""),
            amount=trade_data.get("amount", 0),
            price=trade_data.get("price", 0),
            regime=market_context.get("regime", "unknown"),
            market_conditions=market_context,
        )
        
        # Generate all components
        explanation.summary = self._generate_summary(explanation, signals)
        explanation.confidence, explanation.confidence_factors = self._explain_confidence(signals)
        explanation.analyzer_votes = self._aggregate_analyzer_votes(signals)
        explanation.consensus_score = self._calculate_consensus(explanation.analyzer_votes)
        explanation.analogues = self._find_analogues(trade_data, historical_trades)
        explanation.risk_score, explanation.risk_factors = self._analyze_risk(trade_data, market_context)
        explanation.expected_value, explanation.expected_return, explanation.expected_loss = self._calculate_expected_value(
            explanation, signals, market_context
        )
        explanation.reasoning_chain = self._build_reasoning_chain(explanation)
        explanation.alternatives = self._generate_alternatives(explanation, signals)
        
        self._explanations[trade_id] = explanation
        
        logger.info(f"Generated explanation for trade {trade_id}")
        return explanation
    
    def _generate_summary(
        self,
        explanation: TradeExplanation,
        signals: List[Dict[str, Any]],
    ) -> str:
        """Generate executive summary"""
        consensus = "strong" if explanation.consensus_score > 0.7 else "moderate" if explanation.consensus_score > 0.4 else "weak"
        
        # Count buy vs sell signals
        buy_signals = sum(1 for s in signals if s.get("signal") == "buy")
        sell_signals = sum(1 for s in signals if s.get("signal") == "sell")
        
        direction = "bullish" if buy_signals > sell_signals else "bearish" if sell_signals > buy_signals else "neutral"
        
        return (
            f"The decision to {explanation.action} {explanation.amount} {explanation.symbol} at "
            f"{explanation.price:.5f} is based on a {consensus} market consensus ({explanation.consensus_score:.0%}) "
            f"indicating {direction} momentum. The overall confidence level is {explanation.confidence:.0f}%, "
            f"supported by {len(explanation.analogues)} similar historical situations with positive outcomes."
        )
    
    def _explain_confidence(self, signals: List[Dict[str, Any]]) -> tuple[float, List[str]]:
        """Explain confidence level"""
        if not signals:
            return 0, ["No signals available"]
        
        # Calculate weighted confidence
        total_confidence = 0
        total_weight = 0
        factors = []
        
        for signal in signals:
            confidence = signal.get("confidence", 50)
            weight = signal.get("weight", 1.0)
            
            total_confidence += confidence * weight
            total_weight += weight
            
            if signal.get("reasoning"):
                factors.append(f"{signal.get('name', 'Unknown')}: {signal['reasoning']}")
        
        avg_confidence = total_confidence / total_weight if total_weight > 0 else 0
        
        # Add factors based on signals
        if avg_confidence > 80:
            factors.insert(0, "High agreement across multiple analyzers")
        elif avg_confidence > 60:
            factors.insert(0, "Moderate agreement across analyzers")
        else:
            factors.insert(0, "Low agreement - proceed with caution")
        
        return avg_confidence, factors
    
    def _aggregate_analyzer_votes(self, signals: List[Dict[str, Any]]) -> List[AnalyzerVote]:
        """Aggregate votes from all analyzers"""
        votes = []
        
        for signal in signals:
            vote = AnalyzerVote(
                analyzer_name=signal.get("name", "Unknown"),
                analyzer_type=signal.get("type", "generic"),
                signal=signal.get("signal", "neutral"),
                confidence=signal.get("confidence", 50),
                reasoning=signal.get("reasoning", "No reasoning provided"),
                weight=signal.get("weight", 1.0),
            )
            votes.append(vote)
        
        return votes
    
    def _calculate_consensus(self, votes: List[AnalyzerVote]) -> float:
        """Calculate consensus score"""
        if not votes:
            return 0
        
        # Count agreement
        signals = [v.signal for v in votes]
        
        if not signals:
            return 0
        
        most_common = max(set(signals), key=signals.count)
        agreement_count = sum(1 for s in signals if s == most_common)
        
        return agreement_count / len(signals)
    
    def _find_analogues(
        self,
        trade_data: Dict[str, Any],
        historical_trades: List[Dict[str, Any]],
    ) -> List[HistoricalAnalogue]:
        """Find similar historical trades"""
        analogues = []
        
        # Simple similarity matching
        for trade in historical_trades[:20]:  # Check last 20 trades
            similarity = self._calculate_similarity(trade_data, trade)
            
            if similarity > 0.6:  # Threshold for being considered similar
                analogue = HistoricalAnalogue(
                    trade_id=trade.get("id", ""),
                    timestamp=trade.get("timestamp", datetime.now(timezone.utc)),
                    similarity_score=similarity * 100,
                    outcome="Won" if trade.get("pnl", 0) > 0 else "Lost",
                    outcome_value=trade.get("pnl", 0),
                    key_differences=self._get_key_differences(trade_data, trade),
                )
                analogues.append(analogue)
        
        # Sort by similarity
        analogues.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return analogues[:5]  # Return top 5
    
    def _calculate_similarity(self, trade1: Dict, trade2: Dict) -> float:
        """Calculate similarity between two trades"""
        score = 0
        checks = 0
        
        # Same symbol
        if trade1.get("symbol") == trade2.get("symbol"):
            score += 0.3
        checks += 0.3
        
        # Same regime
        if trade1.get("regime") == trade2.get("regime"):
            score += 0.2
        checks += 0.2
        
        # Similar volatility
        vol1 = trade1.get("volatility", 0.5)
        vol2 = trade2.get("volatility", 0.5)
        if abs(vol1 - vol2) < 0.2:
            score += 0.2
        checks += 0.2
        
        # Same direction
        if trade1.get("action") == trade2.get("action"):
            score += 0.3
        checks += 0.3
        
        return score / checks if checks > 0 else 0
    
    def _get_key_differences(self, trade1: Dict, trade2: Dict) -> List[str]:
        """Get key differences between two trades"""
        differences = []
        
        if trade1.get("symbol") != trade2.get("symbol"):
            differences.append(f"Different symbol ({trade1.get('symbol')} vs {trade2.get('symbol')})")
        
        if trade1.get("regime") != trade2.get("regime"):
            differences.append(f"Different market regime")
        
        return differences
    
    def _analyze_risk(
        self,
        trade_data: Dict[str, Any],
        market_context: Dict[str, Any],
    ) -> tuple[float, List[str]]:
        """Analyze risk factors"""
        risk_score = 50  # Base score
        factors = []
        
        # Check exposure
        exposure = market_context.get("exposure", 0)
        if exposure > 0.8:
            risk_score += 20
            factors.append(f"High portfolio exposure ({exposure:.0%})")
        elif exposure > 0.5:
            risk_score += 10
            factors.append(f"Moderate portfolio exposure ({exposure:.0%})")
        
        # Check volatility
        volatility = market_context.get("volatility", 0.5)
        if volatility > 0.7:
            risk_score += 15
            factors.append(f"High market volatility ({volatility:.0%})")
        
        # Check drawdown
        drawdown = market_context.get("drawdown", 0)
        if drawdown > 10:
            risk_score += 15
            factors.append(f"Elevated drawdown ({drawdown:.1f}%)")
        
        # Check confidence
        confidence = trade_data.get("confidence", 50)
        if confidence < 60:
            risk_score += 10
            factors.append(f"Low confidence ({confidence:.0f}%)")
        
        return min(100, risk_score), factors
    
    def _calculate_expected_value(
        self,
        explanation: TradeExplanation,
        signals: List[Dict[str, Any]],
        market_context: Dict[str, Any],
    ) -> tuple[float, float, float]:
        """Calculate expected value"""
        # Simple EV calculation
        confidence = explanation.confidence / 100
        
        # Estimated price movement
        estimated_move = market_context.get("estimated_move", 0.005)
        
        # Position size
        position = explanation.amount * explanation.price
        
        # Expected return
        expected_return = position * estimated_move * confidence
        expected_loss = position * (estimated_move * 0.5) * (1 - confidence)
        
        # Expected value
        expected_value = expected_return - expected_loss
        
        return expected_value, expected_return, expected_loss
    
    def _build_reasoning_chain(
        self,
        explanation: TradeExplanation,
    ) -> List[ExplanationComponent]:
        """Build the reasoning chain"""
        chain = []
        
        # Market analysis
        chain.append(ExplanationComponent(
            component_type="market",
            title="Market Analysis",
            content=f"Current regime is {explanation.regime} with "
                   f"{len(explanation.analyzer_votes)} analyzer signals",
            importance=0.9,
        ))
        
        # Signal consensus
        chain.append(ExplanationComponent(
            component_type="consensus",
            title="Signal Consensus",
            content=f"{explanation.consensus_score:.0%} of analyzers agree on {explanation.action}",
            importance=0.85,
        ))
        
        # Confidence
        chain.append(ExplanationComponent(
            component_type="confidence",
            title="Confidence Level",
            content=f"Combined confidence is {explanation.confidence:.0f}%",
            importance=0.8,
        ))
        
        # Risk assessment
        chain.append(ExplanationComponent(
            component_type="risk",
            title="Risk Assessment",
            content=f"Risk score is {explanation.risk_score:.0f}/100",
            importance=0.75,
        ))
        
        # Historical precedent
        if explanation.analogues:
            avg_outcome = sum(a.outcome_value for a in explanation.analogues) / len(explanation.analogues)
            chain.append(ExplanationComponent(
                component_type="history",
                title="Historical Precedent",
                content=f"{len(explanation.analogues)} similar trades with avg P&L: ${avg_outcome:.2f}",
                importance=0.7,
            ))
        
        # Expected value
        chain.append(ExplanationComponent(
            component_type="value",
            title="Expected Value",
            content=f"Expected value: ${explanation.expected_value:.2f}",
            importance=0.65,
        ))
        
        return chain
    
    def _generate_alternatives(
        self,
        explanation: TradeExplanation,
        signals: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate alternative actions"""
        alternatives = []
        
        # No trade option
        alternatives.append({
            "action": "No Trade",
            "reason": "Avoid risk when confidence is low",
            "expected_value": 0,
        })
        
        # Smaller position
        alternatives.append({
            "action": f"Reduce Position to {explanation.amount * 0.5}",
            "reason": "Reduce risk exposure",
            "expected_value": explanation.expected_value * 0.4,
        })
        
        # Wait for confirmation
        alternatives.append({
            "action": "Wait for Confirmation",
            "reason": "Let price confirm the signal",
            "expected_value": explanation.expected_value * 0.8,
        })
        
        return alternatives
    
    def get_explanation(self, trade_id: str) -> Optional[TradeExplanation]:
        """Get an existing explanation"""
        return self._explanations.get(trade_id)
    
    def get_all_explanations(self) -> List[TradeExplanation]:
        """Get all explanations"""
        return list(self._explanations.values())
