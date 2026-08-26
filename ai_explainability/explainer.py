"""
AI Explainer - Core Explanation Generation Engine

Generates comprehensive, multi-level explanations for every AI trading decision.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import numpy as np

logger = logging.getLogger(__name__)


class ExplanationLevel(Enum):
    """Levels of explanation detail"""
    BEGINNER = "beginner"           # Simple, non-technical explanations
    ADVANCED = "advanced"          # Detailed trading explanations
    DEVELOPER = "developer"         # Technical implementation details
    RESEARCHER = "researcher"      # Research-grade analysis


class OpportunityType(Enum):
    """Types of trading opportunities"""
    TRADE_ENTRY = "trade_entry"
    TRADE_EXIT = "trade_exit"
    POSITION_ADJUSTMENT = "position_adjustment"
    RISK_REDUCTION = "risk_reduction"
    STRATEGY_SWITCH = "strategy_switch"
    NO_TRADE = "no_trade"


@dataclass
class ExplanationRequest:
    """Request for an explanation"""
    decision_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Core decision data
    opportunity_type: OpportunityType = OpportunityType.TRADE_ENTRY
    action: str = ""                # BUY, SELL, HOLD, SKIP
    amount: float = 0
    confidence: float = 0
    
    # Market context
    symbol: str = ""
    price: float = 0
    market_regime: str = "unknown"
    volatility: float = 0
    
    # Analysis data
    analyzer_signals: Dict[str, Dict] = field(default_factory=dict)
    consensus: Dict[str, Any] = field(default_factory=dict)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    # Decision context
    decision_tree: List[str] = field(default_factory=list)
    alternatives_considered: List[Dict] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)
    
    # Risk and value
    expected_value: float = 0
    risk_score: float = 0
    uncertainty_estimate: float = 0
    probability_distribution: Dict[str, float] = field(default_factory=dict)
    
    # Calibration
    calibration_confidence: float = 0
    historical_accuracy: float = 0
    
    # Historical analogues
    similar_past_decisions: List[Dict] = field(default_factory=list)
    
    # Account state
    balance: float = 0
    equity: float = 0
    current_exposure: float = 0


@dataclass
class ExplanationResponse:
    """Complete explanation response with all formats"""
    explanation_id: str
    decision_id: str
    timestamp: datetime
    generation_time_ms: float
    
    # All audience explanations
    beginner: Dict[str, Any]
    advanced: Dict[str, Any]
    developer: Dict[str, Any]
    researcher: Dict[str, Any]
    
    # Shared components
    executive_summary: Dict[str, Any]
    evidence_chain: List[Dict]
    raw_data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result


class HistoricalAnalogue:
    """Represents a historical decision similar to the current one"""
    
    def __init__(self, data: Dict[str, Any]):
        self.decision_id = data.get("decision_id", "")
        self.timestamp = data.get("timestamp")
        self.action = data.get("action", "")
        self.confidence = data.get("confidence", 0)
        self.outcome = data.get("outcome")  # profit/loss if resolved
        self.similarity_score = data.get("similarity_score", 0)
        self.market_conditions = data.get("market_conditions", {})
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "timestamp": self.timestamp,
            "action": self.action,
            "confidence": self.confidence,
            "outcome": self.outcome,
            "similarity_score": self.similarity_score,
            "market_conditions": self.market_conditions,
        }


class AIExplainer:
    """
    Core AI Explainer - Generates comprehensive explanations for all decisions.
    
    This engine transforms raw AI decision data into human-readable explanations
    at multiple levels of technical detail.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.AIExplainer")
        self._calibration_cache: Dict[str, float] = {}
        self._historical_similarity_fn: Optional[Callable] = None
    
    def set_historical_similarity_fn(self, fn: Callable[[Dict, Dict], float]):
        """Set custom function to calculate historical decision similarity"""
        self._historical_similarity_fn = fn
    
    async def generate_explanation(
        self, 
        request: ExplanationRequest
    ) -> ExplanationResponse:
        """
        Generate comprehensive explanation for a decision.
        
        Args:
            request: Explanation request with all decision data
            
        Returns:
            ExplanationResponse with explanations for all audiences
        """
        start_time = datetime.utcnow()
        
        # Generate evidence chain
        evidence_chain = self._build_evidence_chain(request)
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(request, evidence_chain)
        
        # Generate explanations for each audience level
        beginner = self._generate_beginner_explanation(request, executive_summary)
        advanced = self._generate_advanced_explanation(request, evidence_chain)
        developer = self._generate_developer_explanation(request)
        researcher = self._generate_researcher_explanation(request, evidence_chain)
        
        # Calculate generation time
        generation_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        response = ExplanationResponse(
            explanation_id=str(uuid.uuid4()),
            decision_id=request.decision_id,
            timestamp=datetime.utcnow(),
            generation_time_ms=generation_time,
            beginner=beginner,
            advanced=advanced,
            developer=developer,
            researcher=researcher,
            executive_summary=executive_summary,
            evidence_chain=evidence_chain,
            raw_data=self._extract_raw_data(request),
        )
        
        self.logger.info(
            f"Generated explanation {response.explanation_id} for decision "
            f"{request.decision_id} in {generation_time:.2f}ms"
        )
        
        return response
    
    def _build_evidence_chain(self, request: ExplanationRequest) -> List[Dict]:
        """Build the chain of evidence supporting the decision"""
        evidence = []
        
        # Market regime evidence
        if request.market_regime:
            evidence.append({
                "type": "market_regime",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "regime": request.market_regime,
                    "volatility": request.volatility,
                    "interpretation": self._interpret_regime(request.market_regime),
                },
                "weight": 0.2,
            })
        
        # Analyzer signals evidence
        for analyzer_name, signal_data in request.analyzer_signals.items():
            if signal_data.get("prediction") and signal_data.get("confidence", 0) > 50:
                evidence.append({
                    "type": "analyzer_signal",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "analyzer": analyzer_name,
                        "prediction": signal_data.get("prediction"),
                        "confidence": signal_data.get("confidence", 0),
                        "reason": signal_data.get("reason", signal_data.get("data", {}).get("reason", "")),
                    },
                    "weight": signal_data.get("weight", 0.1),
                })
        
        # Consensus evidence
        if request.consensus:
            evidence.append({
                "type": "consensus",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "direction": request.consensus.get("direction"),
                    "confidence": request.consensus.get("confidence", 0),
                    "agreement": request.consensus.get("agreement", 0),
                    "active_analyzers": request.consensus.get("active_analyzers", 0),
                },
                "weight": 0.3,
            })
        
        # Feature importance evidence
        if request.feature_importance:
            top_features = sorted(
                request.feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            evidence.append({
                "type": "feature_importance",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "top_features": [{"feature": f, "importance": round(v, 4)} for f, v in top_features],
                    "total_features": len(request.feature_importance),
                },
                "weight": 0.15,
            })
        
        # Historical analogue evidence
        if request.similar_past_decisions:
            avg_outcome = np.mean([d.get("outcome", 0) for d in request.similar_past_decisions])
            evidence.append({
                "type": "historical_analogue",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "count": len(request.similar_past_decisions),
                    "avg_outcome": round(avg_outcome, 4) if avg_outcome else None,
                    "avg_similarity": round(
                        np.mean([d.get("similarity_score", 0) for d in request.similar_past_decisions]), 2
                    ),
                },
                "weight": 0.15,
            })
        
        return evidence
    
    def _interpret_regime(self, regime: str) -> str:
        """Convert regime code to human-readable interpretation"""
        interpretations = {
            "strong_uptrend": "Strong upward momentum detected",
            "uptrend": "Upward momentum detected",
            "neutral": "No clear trend direction",
            "downtrend": "Downward momentum detected",
            "strong_downtrend": "Strong downward momentum detected",
            "high_volatility": "High price volatility - caution advised",
            "low_volatility": "Low price volatility - trending opportunity",
            "random": "Market appears random - limited predictability",
            "highly_biased": "Significant market bias detected",
            "normal": "Normal market conditions",
        }
        return interpretations.get(regime, f"Regime: {regime}")
    
    def _generate_executive_summary(self, request: ExplanationRequest, evidence: List[Dict]) -> Dict[str, Any]:
        """Generate executive summary for stakeholders"""
        
        # Calculate overall confidence
        if request.consensus:
            base_confidence = request.consensus.get("confidence", request.confidence)
            agreement = request.consensus.get("agreement", 1.0)
            confidence = base_confidence * (0.7 + 0.3 * agreement)
        else:
            confidence = request.confidence
        
        # Determine why opportunity exists
        why_opportunity = self._explain_why_opportunity_exists(request)
        
        # Explain confidence level
        why_confidence = self._explain_confidence_level(request)
        
        # Generate brief summary
        action_verb = {
            "BUY": "Entering a LONG position",
            "SELL": "Entering a SHORT position", 
            "HOLD": "Maintaining current position",
            "SKIP": "Skipping this opportunity",
        }.get(request.action, f"Taking action: {request.action}")
        
        summary = f"{action_verb} on {request.symbol} with {confidence:.0f}% confidence"
        if request.amount > 0:
            summary += f", amount: ${request.amount:.2f}"
        
        return {
            "summary": summary,
            "opportunity_id": request.decision_id,
            "timestamp": datetime.utcnow().isoformat(),
            "action": request.action,
            "symbol": request.symbol,
            "confidence": round(confidence, 1),
            "expected_value": round(request.expected_value, 4),
            "risk_level": self._risk_to_level(request.risk_score),
            "why_opportunity_exists": why_opportunity,
            "why_confidence_level": why_confidence,
            "key_evidence": [
                {"type": e["type"], "summary": self._summarize_evidence(e)}
                for e in evidence[:3]
            ],
        }
    
    def _explain_why_opportunity_exists(self, request: ExplanationRequest) -> str:
        """Explain why this trading opportunity exists"""
        reasons = []
        
        # Market regime reason
        if request.market_regime and request.market_regime != "unknown":
            reasons.append(f"Market regime is {request.market_regime}")
        
        # Analyzer consensus reason
        if request.consensus:
            active = request.consensus.get("active_analyzers", 0)
            direction = request.consensus.get("direction", "")
            reasons.append(f"{active} analyzers agree on {direction} direction")
        
        # Feature signals
        if request.feature_importance:
            top = max(request.feature_importance.items(), key=lambda x: x[1], default=(None, 0))
            if top[0]:
                reasons.append(f"Strong signal from {top[0]}")
        
        # Historical pattern
        if request.similar_past_decisions:
            count = len(request.similar_past_decisions)
            reasons.append(f"Pattern matches {count} historical opportunities")
        
        return "; ".join(reasons) if reasons else "Multiple factors aligned"
    
    def _explain_confidence_level(self, request: ExplanationRequest) -> str:
        """Explain why confidence has its current value"""
        factors = []
        
        # Calibration factor
        if request.calibration_confidence > 0:
            factors.append(
                f"Model calibration: {request.calibration_confidence:.0f}% "
                f"(based on {request.historical_accuracy:.0f}% historical accuracy)"
            )
        
        # Agreement factor
        if request.consensus:
            agreement = request.consensus.get("agreement", 0) * 100
            factors.append(f"Analyzer agreement: {agreement:.0f}%")
        
        # Uncertainty factor
        if request.uncertainty_estimate > 0:
            factors.append(f"Uncertainty estimate: ±{request.uncertainty_estimate:.1f}%")
        
        # Feature clarity
        if request.feature_importance:
            clear_signals = sum(1 for v in request.feature_importance.values() if v > 0.1)
            factors.append(f"{clear_signals} strong feature signals detected")
        
        return "; ".join(factors) if factors else "Based on model output"
    
    def _summarize_evidence(self, evidence: Dict) -> str:
        """Create brief summary of evidence item"""
        data = evidence.get("data", {})
        etype = evidence.get("type")
        
        summaries = {
            "market_regime": f"Market: {data.get('regime', 'unknown')}",
            "analyzer_signal": f"{data.get('analyzer', '')}: {data.get('prediction', '')} ({data.get('confidence', 0):.0f}%)",
            "consensus": f"{data.get('active_analyzers', 0)} analyzers → {data.get('direction', '')}",
            "feature_importance": f"{len(data.get('top_features', []))} key features identified",
            "historical_analogue": f"{data.get('count', 0)} similar past decisions found",
        }
        
        return summaries.get(etype, str(data)[:50])
    
    def _risk_to_level(self, risk_score: float) -> str:
        """Convert numeric risk score to level"""
        if risk_score < 0.3:
            return "LOW"
        elif risk_score < 0.6:
            return "MEDIUM"
        elif risk_score < 0.8:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def _generate_beginner_explanation(self, request: ExplanationRequest, summary: Dict) -> Dict[str, Any]:
        """Generate simple, non-technical explanation for beginners"""
        
        # Simple action description
        action_descriptions = {
            "BUY": "The AI decided to buy. This means it expects the price to go up.",
            "SELL": "The AI decided to sell. This means it expects the price to go down.",
            "HOLD": "The AI decided to wait. This means it's not confident enough to act right now.",
            "SKIP": "The AI decided to skip this trade. The potential risks outweigh the potential gains.",
        }
        
        # Simple confidence explanation
        if request.confidence >= 80:
            confidence_explanation = "The AI is very confident about this decision."
        elif request.confidence >= 60:
            confidence_explanation = "The AI is fairly confident about this decision."
        elif request.confidence >= 40:
            confidence_explanation = "The AI has moderate confidence in this decision."
        else:
            confidence_explanation = "The AI is not very confident about this decision. It might be risky."
        
        # Simple risk explanation
        risk_explanations = {
            "LOW": "This trade has low risk. The potential reward seems worth it.",
            "MEDIUM": "This trade has medium risk. Make sure you can afford to lose this money.",
            "HIGH": "This trade has high risk. Only trade with money you can afford to lose.",
            "CRITICAL": "This trade has very high risk. Consider skipping it.",
        }
        risk_level = self._risk_to_level(request.risk_score)
        
        return {
            "title": f"Explanation: {request.action} on {request.symbol}",
            "summary": summary.get("summary", ""),
            
            # Simple explanations
            "what_happened": action_descriptions.get(request.action, request.action),
            "why": summary.get("why_opportunity_exists", "The AI analyzed market data."),
            "how_confident": confidence_explanation,
            "how_risky": risk_explanations.get(risk_level, f"Risk level: {risk_level}"),
            "what_to_expect": self._simple_outlook(request),
            
            # Simple key points
            "key_points": [
                f"Action: {request.action}",
                f"Confidence: {request.confidence:.0f}%",
                f"Risk: {risk_level}",
                f"Expected value: ${request.expected_value:.2f}" if request.expected_value else "Expected value: N/A",
            ],
            
            # Simple recommendation
            "recommendation": self._simple_recommendation(request),
            
            # Visual-friendly summary
            "visual_summary": {
                "confidence_bar": self._make_confidence_bar(request.confidence),
                "risk_indicator": risk_level,
                "action_icon": request.action,
            },
        }
    
    def _simple_outlook(self, request: ExplanationRequest) -> str:
        """Generate simple outlook statement"""
        if request.action == "BUY":
            return "If the AI is correct, the price will go up and you'll make a profit."
        elif request.action == "SELL":
            return "If the AI is correct, the price will go down and you'll make a profit."
        elif request.action == "HOLD":
            return "The AI thinks it's better to wait for a clearer signal."
        else:
            return "The AI thinks the risks outweigh potential rewards."
    
    def _simple_recommendation(self, request: ExplanationRequest) -> str:
        """Generate simple recommendation"""
        risk_level = self._risk_to_level(request.risk_score)
        
        if request.confidence >= 70 and risk_level in ["LOW", "MEDIUM"]:
            return "This looks like a reasonable trade to consider."
        elif request.confidence >= 50 and risk_level == "LOW":
            return "The low risk makes this trade worth considering."
        elif request.confidence < 50 or risk_level in ["HIGH", "CRITICAL"]:
            return "Consider waiting for a better opportunity."
        else:
            return "Make your own decision based on your risk tolerance."
    
    def _make_confidence_bar(self, confidence: float) -> Dict[str, Any]:
        """Create visual confidence bar data"""
        return {
            "value": confidence,
            "level": "high" if confidence >= 70 else "medium" if confidence >= 50 else "low",
            "fill_percent": confidence,
        }
    
    def _generate_advanced_explanation(self, request: ExplanationRequest, evidence: List[Dict]) -> Dict[str, Any]:
        """Generate detailed trading explanation for advanced traders"""
        
        # Detailed signal breakdown
        signal_breakdown = []
        for analyzer, data in request.analyzer_signals.items():
            signal_breakdown.append({
                "analyzer": analyzer,
                "signal": data.get("prediction", "NO_SIGNAL"),
                "confidence": data.get("confidence", 0),
                "weight": data.get("weight", 0),
                "reason": data.get("reason", data.get("data", {}).get("reason", "")),
            })
        
        # Sort by confidence
        signal_breakdown.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Decision factors
        decision_factors = self._analyze_decision_factors(request)
        
        # Market context
        market_context = {
            "regime": request.market_regime,
            "volatility": round(request.volatility, 4),
            "balance": request.balance,
            "equity": request.equity,
            "exposure": round(request.current_exposure * 100, 1),
        }
        
        return {
            "title": f"Trading Decision Analysis: {request.action} {request.symbol}",
            
            # Market analysis
            "market_context": market_context,
            "regime_interpretation": self._interpret_regime(request.market_regime),
            
            # Signal analysis
            "signal_breakdown": signal_breakdown,
            "consensus_details": request.consensus,
            "analyzer_agreement": self._calculate_agreement(request),
            
            # Decision analysis
            "decision_factors": decision_factors,
            "decision_tree": self._format_decision_tree(request.decision_tree),
            "alternatives": request.alternatives_considered,
            
            # Value and risk
            "expected_value": round(request.expected_value, 4),
            "risk_metrics": {
                "risk_score": request.risk_score,
                "risk_level": self._risk_to_level(request.risk_score),
                "uncertainty": round(request.uncertainty_estimate, 2),
                "calibration_confidence": request.calibration_confidence,
            },
            
            # Position sizing
            "position_sizing": {
                "suggested_amount": request.amount,
                "balance_percent": round(request.amount / request.balance * 100, 2) if request.balance > 0 else 0,
                "risk_percent": round(request.risk_score * request.amount, 2),
            },
            
            # Key technical points
            "technical_summary": self._generate_technical_summary(request),
            
            # Trade management
            "trade_management": {
                "entry_strategy": self._suggest_entry_strategy(request),
                "exit_strategy": self._suggest_exit_strategy(request),
                "stop_loss": self._suggest_stop_loss(request),
                "take_profit": self._suggest_take_profit(request),
            },
        }
    
    def _analyze_decision_factors(self, request: ExplanationRequest) -> List[Dict[str, Any]]:
        """Analyze the key factors influencing the decision"""
        factors = []
        
        # Analyzer consensus factor
        if request.consensus:
            factors.append({
                "name": "Analyzer Consensus",
                "impact": "positive" if request.consensus.get("agreement", 0) > 0.6 else "negative",
                "value": f"{request.consensus.get('agreement', 0) * 100:.0f}% agreement",
                "description": f"{request.consensus.get('active_analyzers', 0)} analyzers support {request.consensus.get('direction', 'UNKNOWN')}",
            })
        
        # Confidence factor
        factors.append({
            "name": "Confidence Level",
            "impact": "positive" if request.confidence > 60 else "neutral" if request.confidence > 40 else "negative",
            "value": f"{request.confidence:.0f}%",
            "description": "Overall confidence in the prediction",
        })
        
        # Risk factor
        factors.append({
            "name": "Risk Assessment",
            "impact": "negative" if request.risk_score > 0.6 else "neutral",
            "value": f"{request.risk_score:.0%}",
            "description": f"Risk level: {self._risk_to_level(request.risk_score)}",
        })
        
        # Market regime factor
        if request.market_regime:
            favorable = request.market_regime in ["strong_uptrend", "uptrend", "strong_downtrend", "downtrend"]
            factors.append({
                "name": "Market Regime",
                "impact": "positive" if favorable else "neutral",
                "value": request.market_regime,
                "description": self._interpret_regime(request.market_regime),
            })
        
        # Feature importance factor
        if request.feature_importance:
            top_feature = max(request.feature_importance.items(), key=lambda x: x[1], default=(None, 0))
            if top_feature[0]:
                factors.append({
                    "name": "Feature Signal",
                    "impact": "positive" if top_feature[1] > 0.15 else "neutral",
                    "value": f"{top_feature[0]}: {top_feature[1]:.2f}",
                    "description": "Most influential feature in the decision",
                })
        
        return factors
    
    def _calculate_agreement(self, request: ExplanationRequest) -> Dict[str, Any]:
        """Calculate analyzer agreement metrics"""
        if not request.consensus:
            return {"agreement": 0, "count": 0}
        
        active = request.consensus.get("active_analyzers", 0)
        agreement = request.consensus.get("agreement", 0)
        
        return {
            "agreement_percent": round(agreement * 100, 1),
            "unanimous": agreement >= 1.0,
            "strong_consensus": agreement >= 0.8,
            "majority": agreement >= 0.6,
            "contributing_count": request.consensus.get("contributing", 0),
            "total_analyzers": active,
        }
    
    def _format_decision_tree(self, tree: List[str]) -> List[Dict[str, Any]]:
        """Format decision tree for display"""
        return [{"step": i + 1, "description": step} for i, step in enumerate(tree)]
    
    def _generate_technical_summary(self, request: ExplanationRequest) -> Dict[str, str]:
        """Generate technical summary of the decision"""
        return {
            "primary_signal": request.consensus.get("direction", request.action) if request.consensus else request.action,
            "signal_strength": "strong" if request.confidence > 70 else "moderate" if request.confidence > 50 else "weak",
            "regime_compatibility": "favorable" if request.market_regime in ["uptrend", "downtrend", "strong_uptrend", "strong_downtrend"] else "neutral",
            "risk_adjusted": "yes" if request.risk_score < 0.5 else "caution",
        }
    
    def _suggest_entry_strategy(self, request: ExplanationRequest) -> Dict[str, Any]:
        """Suggest entry strategy"""
        if request.action in ["BUY", "SELL"]:
            return {
                "type": "immediate" if request.confidence > 75 else "gradual",
                "reason": "High confidence allows immediate entry" if request.confidence > 75 else "Lower confidence - consider scaling in",
                "sizing": "full position" if request.confidence > 80 else "50-75% initial, remainder on confirmation",
            }
        return {"type": "none", "reason": "No entry recommended"}
    
    def _suggest_exit_strategy(self, request: ExplanationRequest) -> Dict[str, Any]:
        """Suggest exit strategy"""
        return {
            "time_based": "2 minutes (contract duration)",
            "profit_target": "+80% of potential",
            "stop_loss": "Immediate exit on adverse move",
        }
    
    def _suggest_stop_loss(self, request: ExplanationRequest) -> Dict[str, Any]:
        """Suggest stop loss levels"""
        return {
            "recommended": False,
            "reason": "Binary options have fixed risk - stop loss not applicable",
            "max_loss": f"${request.amount:.2f} (full stake)",
        }
    
    def _suggest_take_profit(self, request: ExplanationRequest) -> Dict[str, Any]:
        """Suggest take profit levels"""
        return {
            "recommended": True,
            "target_percent": 80,
            "auto_close": True,
            "reason": "Lock in profits at 80% of max return",
        }
    
    def _generate_developer_explanation(self, request: ExplanationRequest) -> Dict[str, Any]:
        """Generate technical explanation for developers"""
        
        return {
            "title": f"Developer Analysis: Decision {request.decision_id}",
            
            # System integration
            "system_info": {
                "module": "ai_explainability",
                "component": "AIExplainer",
                "api_version": "1.0.0",
            },
            
            # Data structures
            "request_schema": {
                "decision_id": request.decision_id,
                "opportunity_type": request.opportunity_type.value,
                "action": request.action,
                "confidence": request.confidence,
                "timestamp": request.timestamp.isoformat(),
            },
            
            # Analyzer integration
            "analyzers_used": list(request.analyzer_signals.keys()),
            "analyzer_data": {
                name: {
                    "prediction": data.get("prediction"),
                    "confidence": data.get("confidence"),
                    "weight": data.get("weight"),
                    "data_keys": list(data.get("data", {}).keys()) if "data" in data else [],
                }
                for name, data in request.analyzer_signals.items()
            },
            
            # Consensus algorithm
            "consensus_algorithm": {
                "type": "weighted_vote",
                "parameters": {
                    "min_confidence": 55,
                    "entropy_filter": True,
                    "agreement_threshold": 0.6,
                },
                "result": request.consensus,
            },
            
            # Feature importance
            "feature_importance": request.feature_importance,
            "top_features": sorted(
                request.feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            
            # Decision tree
            "decision_tree": request.decision_tree,
            "tree_depth": len(request.decision_tree),
            
            # Alternatives considered
            "alternatives": request.alternatives_considered,
            "rejection_reasons": request.rejection_reasons,
            
            # Probability distribution
            "probability_distribution": request.probability_distribution,
            "uncertainty_estimate": request.uncertainty_estimate,
            
            # Calibration data
            "calibration": {
                "confidence": request.calibration_confidence,
                "historical_accuracy": request.historical_accuracy,
                "calibration_curve": self._get_calibration_curve(request),
            },
            
            # Implementation details
            "implementation": {
                "calculation_methods": {
                    "expected_value": "win_rate * avg_win - (1 - win_rate) * avg_loss",
                    "risk_score": "weighted combination of exposure, drawdown, confidence",
                    "uncertainty": "standard deviation of probability distribution",
                },
                "thresholds": {
                    "min_confidence": 55,
                    "max_risk": 0.85,
                    "high_agreement": 0.8,
                },
            },
            
            # Code references
            "code_references": [
                "ai_core/orchestrator.py:make_decision()",
                "analysis/analysis_manager.py:generate_best_prediction()",
                "ai_explainability/explainer.py:generate_explanation()",
            ],
        }
    
    def _get_calibration_curve(self, request: ExplanationRequest) -> List[Dict[str, float]]:
        """Generate calibration curve data points"""
        # Simple calibration curve based on confidence bins
        bins = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]
        curve = []
        
        for low, high in bins:
            if low <= request.confidence < high:
                # Ideal: actual matches confidence
                actual = request.historical_accuracy if request.historical_accuracy else 0.5
                predicted = (low + high) / 2 / 100
                curve.append({
                    "bin": f"{low}-{high}",
                    "predicted": predicted,
                    "actual": actual,
                    "count": 1,
                })
        
        return curve
    
    def _generate_researcher_explanation(self, request: ExplanationRequest, evidence: List[Dict]) -> Dict[str, Any]:
        """Generate research-grade explanation with full methodology"""
        
        return {
            "title": f"Research Analysis: Decision {request.decision_id}",
            
            # Methodology
            "methodology": {
                "approach": "ensemble_analysis_with_entropy_filtering",
                "analyzers": {
                    name: {
                        "type": data.get("type", "unknown"),
                        "base_weight": data.get("weight", 0.1),
                        "confidence": data.get("confidence", 0),
                    }
                    for name, data in request.analyzer_signals.items()
                },
                "consensus_method": "weighted_vote_with_entropy_penalty",
                "calibration_method": "histogram_binning",
            },
            
            # Statistical analysis
            "statistics": {
                "confidence": {
                    "value": request.confidence,
                    "calibration_confidence": request.calibration_confidence,
                    "uncertainty_estimate": request.uncertainty_estimate,
                    "standard_error": request.uncertainty_estimate / 2,
                },
                "agreement": {
                    "raw_agreement": request.consensus.get("agreement", 0) if request.consensus else 0,
                    "fleiss_kappa": self._calculate_fleiss_kappa(request),
                    "analyzer_count": request.consensus.get("active_analyzers", 0) if request.consensus else 0,
                },
                "risk": {
                    "score": request.risk_score,
                    "components": self._decompose_risk(request),
                },
            },
            
            # Probability analysis
            "probability_analysis": {
                "distribution": request.probability_distribution,
                "expected_value": request.expected_value,
                "variance": self._calculate_variance(request),
                "sharpe_ratio": self._calculate_sharpe(request),
            },
            
            # Evidence chain (full)
            "evidence_chain": evidence,
            "evidence_weights": {e["type"]: e["weight"] for e in evidence},
            
            # Feature importance (full)
            "feature_importance": {
                "all_features": request.feature_importance,
                "top_10": dict(sorted(request.feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]),
                "normalization": "sum_to_one",
            },
            
            # Decision tree (full)
            "decision_tree": {
                "steps": request.decision_tree,
                "branches": self._analyze_branches(request.decision_tree),
                "leaf_node": request.decision_tree[-1] if request.decision_tree else None,
            },
            
            # Historical analogues
            "historical_analogues": {
                "count": len(request.similar_past_decisions),
                "similarity_scores": [d.get("similarity_score", 0) for d in request.similar_past_decisions],
                "outcomes": [d.get("outcome") for d in request.similar_past_decisions],
                "avg_outcome": np.mean([d.get("outcome", 0) for d in request.similar_past_decisions]) if request.similar_past_decisions else None,
            },
            
            # Alternative analysis
            "alternative_analysis": {
                "alternatives_considered": request.alternatives_considered,
                "rejection_reasons": request.rejection_reasons,
                "opportunity_cost": self._calculate_opportunity_cost(request),
            },
            
            # Reproducibility
            "reproducibility": {
                "random_seed": hash(request.decision_id) % (2**32),
                "data_snapshot": {
                    "timestamp": request.timestamp.isoformat(),
                    "symbol": request.symbol,
                    "price": request.price,
                },
                "model_versions": self._get_model_versions(),
            },
        }
    
    def _calculate_fleiss_kappa(self, request: ExplanationRequest) -> float:
        """Calculate Fleiss' kappa for inter-rater agreement"""
        if not request.consensus:
            return 0
        
        n = request.consensus.get("active_analyzers", 1)
        if n < 2:
            return 1.0
        
        # Simplified calculation
        agreement = request.consensus.get("agreement", 0)
        
        # Expected agreement (assuming equal distribution)
        expected = 1 / 2  # Binary decision
        
        # Kappa formula
        kappa = (agreement - expected) / (1 - expected) if expected < 1 else 0
        return max(0, min(1, kappa))
    
    def _decompose_risk(self, request: ExplanationRequest) -> Dict[str, float]:
        """Decompose risk score into components"""
        return {
            "exposure_component": min(0.3, request.current_exposure * 0.3),
            "drawdown_component": min(0.2, request.current_exposure * 0.2),
            "confidence_component": max(0, (50 - request.confidence) / 500) if request.confidence < 50 else 0,
            "volatility_component": min(0.2, request.volatility * 100),
        }
    
    def _calculate_variance(self, request: ExplanationRequest) -> float:
        """Calculate variance of expected outcomes"""
        if not request.probability_distribution:
            return request.uncertainty_estimate ** 2
        return sum(
            (p - request.expected_value) ** 2 * prob
            for p, prob in request.probability_distribution.items()
        )
    
    def _calculate_sharpe(self, request: ExplanationRequest) -> float:
        """Calculate simplified Sharpe-like ratio"""
        if request.uncertainty_estimate == 0:
            return 0
        return request.expected_value / request.uncertainty_estimate
    
    def _analyze_branches(self, tree: List[str]) -> List[Dict[str, Any]]:
        """Analyze decision tree branches"""
        return [
            {
                "index": i,
                "description": step,
                "type": self._classify_branch(step),
            }
            for i, step in enumerate(tree)
        ]
    
    def _classify_branch(self, step: str) -> str:
        """Classify the type of decision branch"""
        step_lower = step.lower()
        if "validator" in step_lower:
            return "validation"
        elif "analyzer" in step_lower or "signal" in step_lower:
            return "analysis"
        elif "risk" in step_lower or "exposure" in step_lower:
            return "risk_assessment"
        elif "confidence" in step_lower:
            return "confidence_check"
        else:
            return "decision"
    
    def _calculate_opportunity_cost(self, request: ExplanationRequest) -> Dict[str, Any]:
        """Calculate opportunity cost of rejecting alternatives"""
        if not request.alternatives_considered:
            return {"cost": 0, "reason": "No alternatives considered"}
        
        best_alternative = max(
            request.alternatives_considered,
            key=lambda x: x.get("expected_value", 0),
            default={"expected_value": 0}
        )
        
        cost = best_alternative.get("expected_value", 0) - request.expected_value
        
        return {
            "cost": round(cost, 4),
            "best_alternative": best_alternative.get("action", "none"),
            "reason": f"Chose {request.action} over {best_alternative.get('action', 'none')}",
        }
    
    def _get_model_versions(self) -> Dict[str, str]:
        """Get versions of models used in decision"""
        return {
            "ai_core": "1.0.0",
            "analysis_manager": "3.0",
            "ml_analyzer": "1.0.0",
            "pattern_recognizer": "1.0.0",
        }
    
    def _extract_raw_data(self, request: ExplanationRequest) -> Dict[str, Any]:
        """Extract raw data for audit purposes"""
        return {
            "request": asdict(request),
            "timestamp": datetime.utcnow().isoformat(),
            "generator": "AIExplainer v1.0.0",
        }
