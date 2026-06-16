from typing import Dict, Any, Optional
from models import Prediction
from backtesting.strategy import BacktestStrategy


class AntiMartingaleStrategy(BacktestStrategy):
    """Anti-Martingale strategy - increases position size after wins"""
    
    def __init__(self, base_amount: float = 1.0, max_multiplier: int = 4):
        super().__init__("anti_martingale")
        self.base_amount = base_amount
        self.max_multiplier = max_multiplier
        self.current_multiplier = 1
        self.consecutive_wins = 0
    
    def generate_signal(self, data: Dict[str, Any]) -> Optional[Prediction]:
        """Generate signal based on analysis with anti-martingale position sizing"""
        price_history = data.get("price_history", [])
        if len(price_history) < 30:
            return None
        
        # Simple trend following
        sma_10 = sum(list(price_history)[-10:]) / 10
        sma_20 = sum(list(price_history)[-20:]) / 20
        
        if sma_10 > sma_20:
            direction = "CALL"
        elif sma_10 < sma_20:
            direction = "PUT"
        else:
            return None
        
        return Prediction(
            type="ANTI_MARTINGALE",
            direction=direction,
            confidence=65,
            reason=f"Trend following with {self.current_multiplier}x position"
        )
    
    def execute_trade(self, prediction: Prediction, price: float, amount: float = 1.0) -> Dict[str, Any]:
        """Execute trade with anti-martingale position sizing"""
        adjusted_amount = self.base_amount * self.current_multiplier
        return super().execute_trade(prediction, price, adjusted_amount)
    
    def close_trade(self, trade: Dict[str, Any], exit_price: float) -> Dict[str, Any]:
        """Close trade and update anti-martingale state"""
        result = super().close_trade(trade, exit_price)
        
        if result["profit"] > 0:
            self.consecutive_wins += 1
            self.current_multiplier = min(self.current_multiplier + 1, self.max_multiplier)
        else:
            self.consecutive_wins = 0
            self.current_multiplier = 1
        
        return result
    
    def reset(self):
        """Reset strategy state"""
        super().reset()
        self.current_multiplier = 1
        self.consecutive_wins = 0
