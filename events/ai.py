"""
AI Events
=========

Events related to AI predictions and decisions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .core import Event, EventType, EventMetadata


@dataclass
class AIPredictionEvent(Event):
    """AI prediction event"""
    
    def __init__(
        self,
        symbol: str,
        prediction: str,  # "buy", "sell", "hold"
        confidence: float,
        model_version: str,
        timestamp: float,
        features: Optional[Dict[str, float]] = None,
        expected_value: float = 0,
        risk_score: float = 0,
        inference_time_ms: float = 0,
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "symbol": symbol,
            "prediction": prediction,
            "confidence": confidence,
            "model_version": model_version,
            "expected_value": expected_value,
            "risk_score": risk_score,
            "inference_time_ms": inference_time_ms,
            "features": features or {},
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
            metadata.model_version = model_version
        
        super().__init__(
            event_type=EventType.AI_PREDICTION,
            metadata=metadata,
            payload=payload,
        )


@dataclass
class RiskEvaluationEvent(Event):
    """Risk evaluation event"""
    
    def __init__(
        self,
        symbol: str,
        risk_score: float,
        risk_factors: Dict[str, float],
        max_position_size: float,
        recommended_stop_loss: float,
        recommended_take_profit: float,
        timestamp: float,
        risk_level: str = "medium",  # low, medium, high, extreme
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "symbol": symbol,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "risk_level": risk_level,
            "max_position_size": max_position_size,
            "recommended_stop_loss": recommended_stop_loss,
            "recommended_take_profit": recommended_take_profit,
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
        
        super().__init__(
            event_type=EventType.RISK_EVALUATION,
            metadata=metadata,
            payload=payload,
        )


@dataclass
class ConfidenceCalculationEvent(Event):
    """Confidence calculation event"""
    
    def __init__(
        self,
        prediction_id: str,
        confidence: float,
        uncertainty_total: float,
        uncertainty_epistemic: float,
        uncertainty_aleatoric: float,
        confidence_factors: Dict[str, float],
        timestamp: float,
        calibration_score: float = 0,
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "prediction_id": prediction_id,
            "confidence": confidence,
            "uncertainty_total": uncertainty_total,
            "uncertainty_epistemic": uncertainty_epistemic,
            "uncertainty_aleatoric": uncertainty_aleatoric,
            "confidence_factors": confidence_factors,
            "calibration_score": calibration_score,
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
        
        super().__init__(
            event_type=EventType.CONFIDENCE_CALCULATION,
            metadata=metadata,
            payload=payload,
        )


@dataclass
class StrategyDecisionEvent(Event):
    """Strategy decision event"""
    
    def __init__(
        self,
        symbol: str,
        action: str,  # buy, sell, hold, wait
        quantity: float,
        price: float,
        order_type: str,  # market, limit, stop
        reason: str,
        confidence: float,
        alternative_actions: List[Dict[str, Any]],
        timestamp: float,
        strategy_id: str = "",
        strategy_version: str = "",
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "strategy_id": strategy_id,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "order_type": order_type,
            "reason": reason,
            "confidence": confidence,
            "alternative_actions": alternative_actions,
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
            metadata.strategy_version = strategy_version
        
        super().__init__(
            event_type=EventType.STRATEGY_DECISION,
            metadata=metadata,
            payload=payload,
        )
