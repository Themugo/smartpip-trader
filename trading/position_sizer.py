from typing import Dict, Any, List
import numpy as np


class PositionSizer:
    """Optimized position sizing for maximum profitability"""
    
    def __init__(self, base_amount: float = 1.0, max_risk_per_trade: float = 0.02):
        self.base_amount = base_amount
        self.max_risk_per_trade = max_risk_per_trade
        self.balance = 10000.0
        self.recent_trades = []
        self.win_streak = 0
        self.loss_streak = 0
    
    def calculate_position_size(self, confidence: float, market_conditions: Dict[str, Any]) -> float:
        """Calculate optimal position size based on multiple factors"""
        # Base position
        position = self.base_amount
        
        # Confidence multiplier (higher confidence = larger position)
        confidence_multiplier = confidence / 100
        position *= confidence_multiplier
        
        # Market volatility adjustment (lower volatility = larger position)
        volatility = market_conditions.get("volatility", 0.01)
        volatility_adjustment = 1.0 / (1.0 + volatility * 50)
        position *= volatility_adjustment
        
        # Trend strength adjustment (stronger trend = larger position)
        trend_strength = market_conditions.get("trend_strength", 0)
        if trend_strength > 0.01:
            position *= 1.2
        elif trend_strength < -0.01:
            position *= 1.2
        
        # Win streak bonus (increase size on winning streak)
        if self.win_streak >= 3:
            position *= 1.3
        elif self.win_streak >= 2:
            position *= 1.15
        
        # Loss streak protection (reduce size on losing streak)
        if self.loss_streak >= 3:
            position *= 0.5
        elif self.loss_streak >= 2:
            position *= 0.7
        
        # Risk limit
        max_position = self.balance * self.max_risk_per_trade
        position = min(position, max_position)
        
        # Minimum position
        position = max(position, self.base_amount * 0.5)
        
        return position
    
    def update_trade_result(self, profit: float):
        """Update trade statistics"""
        self.recent_trades.append({"profit": profit})
        
        if len(self.recent_trades) > 20:
            self.recent_trades = self.recent_trades[-20:]
        
        if profit > 0:
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.loss_streak += 1
            self.win_streak = 0
        
        self.balance += profit
    
    def get_kelly_criterion_size(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calculate position size using Kelly Criterion"""
        if avg_loss == 0:
            return self.base_amount
        
        win_loss_ratio = avg_win / avg_loss
        kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
        
        # Limit Kelly to 25% to avoid over-betting
        kelly = max(0, min(kelly, 0.25))
        
        return self.balance * kelly
    
    def get_optimal_size(self, confidence: float, market_conditions: Dict[str, Any], 
                        use_kelly: bool = False) -> float:
        """Get optimal position size using best method"""
        if use_kelly and len(self.recent_trades) >= 10:
            wins = [t["profit"] for t in self.recent_trades if t["profit"] > 0]
            losses = [t["profit"] for t in self.recent_trades if t["profit"] < 0]
            
            if wins and losses:
                win_rate = len(wins) / len(self.recent_trades)
                avg_win = np.mean(wins)
                avg_loss = abs(np.mean(losses))
                
                kelly_size = self.get_kelly_criterion_size(win_rate, avg_win, avg_loss)
                adaptive_size = self.calculate_position_size(confidence, market_conditions)
                
                # Use the more conservative of the two
                return min(kelly_size, adaptive_size)
        
        return self.calculate_position_size(confidence, market_conditions)
