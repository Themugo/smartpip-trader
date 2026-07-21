from typing import Dict, Any, Optional, List
from models import Prediction
from backtesting.strategy import BacktestStrategy
from analysis import AnalysisManager
from indicators import RSI, SMA, EMA, MACD, BollingerBands
import numpy as np


class UnifiedStrategy(BacktestStrategy):
    """Unified strategy that combines all analysis types for maximum win rate"""
    
    def __init__(self, min_confidence: float = 80):
        super().__init__("unified")
        self.min_confidence = min_confidence
        self.analysis_manager = AnalysisManager()
        self.analysis_weights = {
            "even_odd": 0.15,
            "rise_fall": 0.20,
            "over_under": 0.20,
            "match_diff": 0.15,
            "technical": 0.20,
            "ml": 0.10
        }
        self.last_predictions = {}
    
    def generate_signal(self, data: Dict[str, Any]) -> Optional[Prediction]:
        """Generate signal using unified analysis of all types"""
        price_history = data.get("price_history", [])
        if len(price_history) < 30:
            return None
        
        # Run all analysis types
        comprehensive_analysis = self.analysis_manager.get_comprehensive_analysis(data)
        
        # Collect predictions from all analyzers
        predictions = {}
        for analyzer_name, analyzer in self.analysis_manager.analyzers.items():
            if not analyzer.enabled:
                continue
            
            result = analyzer.analyze(data)
            if result.prediction:
                predictions[analyzer_name] = {
                    "direction": result.prediction,
                    "confidence": result.confidence,
                    "data": result.data
                }
        
        if not predictions:
            return None
        
        # Calculate weighted score
        weighted_score = self._calculate_weighted_score(predictions)
        
        # Determine consensus direction
        consensus_direction = self._get_consensus_direction(predictions)
        
        if not consensus_direction:
            return None
        
        # Calculate final confidence
        final_confidence = self._calculate_final_confidence(predictions, weighted_score)
        
        # Check if meets minimum confidence
        if final_confidence < self.min_confidence:
            return None
        
        # Generate reason
        reason = self._generate_reason(predictions, consensus_direction, weighted_score)
        
        return Prediction(
            type="UNIFIED",
            direction=consensus_direction,
            confidence=final_confidence,
            reason=reason
        )
    
    def _calculate_weighted_score(self, predictions: Dict[str, Dict]) -> float:
        """Calculate weighted score from all predictions"""
        total_score = 0.0
        total_weight = 0.0
        
        for analyzer_name, pred in predictions.items():
            weight = self.analysis_weights.get(analyzer_name, 0.1)
            confidence = pred["confidence"]
            total_score += confidence * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0
    
    def _get_consensus_direction(self, predictions: Dict[str, Dict]) -> Optional[str]:
        """Get consensus direction from all predictions"""
        call_count = sum(1 for p in predictions.values() if p["direction"] == "CALL")
        put_count = sum(1 for p in predictions.values() if p["direction"] == "PUT")
        
        # Require at least 60% agreement
        total = len(predictions)
        if call_count / total >= 0.6:
            return "CALL"
        elif put_count / total >= 0.6:
            return "PUT"
        
        return None
    
    def _calculate_final_confidence(self, predictions: Dict[str, Dict], 
                                   weighted_score: float) -> float:
        """Calculate final confidence with adjustments"""
        # Base confidence from weighted score
        confidence = weighted_score
        
        # Boost if high agreement
        call_count = sum(1 for p in predictions.values() if p["direction"] == "CALL")
        put_count = sum(1 for p in predictions.values() if p["direction"] == "PUT")
        max_count = max(call_count, put_count)
        agreement_ratio = max_count / len(predictions)
        
        if agreement_ratio >= 0.8:
            confidence += 10
        elif agreement_ratio >= 0.6:
            confidence += 5
        
        # Boost if technical and ML agree
        if "technical" in predictions and "ml" in predictions:
            if predictions["technical"]["direction"] == predictions["ml"]["direction"]:
                confidence += 8
        
        # Clamp to valid range
        return min(95, max(50, confidence))
    
    def _generate_reason(self, predictions: Dict[str, Dict], direction: str, 
                        weighted_score: float) -> str:
        """Generate reason for prediction"""
        agreeing_analyzers = [name for name, pred in predictions.items() 
                             if pred["direction"] == direction]
        
        return (
            f"Unified signal - {len(agreeing_analyzers)}/{len(predictions)} analyzers agree: "
            f"{', '.join(agreeing_analyzers)}. Weighted score: {weighted_score:.1f}"
        )
    
    def execute_trade(self, prediction: Prediction, price: float, amount: float = 1.0) -> Dict[str, Any]:
        """Execute trade with unified strategy"""
        # Use adjusted position size based on confidence
        adjusted_amount = amount * (prediction.confidence / 100)
        
        trade = super().execute_trade(prediction, price, adjusted_amount)
        trade["unified_analysis"] = self.last_predictions
        
        return trade
