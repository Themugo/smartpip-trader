from typing import Dict, Any, List
import numpy as np


class AdaptiveConfidence:
    """Adaptive confidence threshold based on market conditions"""
    
    def __init__(self, base_threshold: float = 70):
        self.base_threshold = base_threshold
        self.current_threshold = base_threshold
        self.market_volatility = 0.0
        self.trend_strength = 0.0
        self.recent_accuracy = 0.5
    
    def update_market_conditions(self, price_history: List[float], recent_trades: List[Dict[str, Any]]):
        """Update market condition metrics"""
        if len(price_history) >= 20:
            # Calculate volatility
            returns = np.diff(price_history[-20:])
            self.market_volatility = np.std(returns) / np.mean(returns) if np.mean(returns) != 0 else 0
            
            # Calculate trend strength
            sma_10 = sum(price_history[-10:]) / 10
            sma_20 = sum(price_history[-20:]) / 20
            self.trend_strength = abs(sma_10 - sma_20) / sma_20 if sma_20 != 0 else 0
        
        # Calculate recent accuracy
        if recent_trades:
            wins = sum(1 for t in recent_trades if t.get("profit", 0) > 0)
            self.recent_accuracy = wins / len(recent_trades)
    
    def get_adjusted_threshold(self) -> float:
        """Get confidence threshold adjusted for market conditions"""
        # Increase threshold in high volatility
        volatility_adjustment = self.market_volatility * 500
        
        # Decrease threshold in strong trends
        trend_adjustment = -self.trend_strength * 200
        
        # Adjust based on recent accuracy
        accuracy_adjustment = (self.recent_accuracy - 0.5) * -20
        
        adjusted = self.base_threshold + volatility_adjustment + trend_adjustment + accuracy_adjustment
        
        # Clamp between 50 and 95
        self.current_threshold = max(50, min(95, adjusted))
        
        return self.current_threshold
    
    def should_trade(self, confidence: float) -> bool:
        """Determine if trade should be executed based on confidence"""
        return confidence >= self.get_adjusted_threshold()
