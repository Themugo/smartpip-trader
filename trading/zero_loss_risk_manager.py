from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import deque
import numpy as np


class ZeroLossRiskManager:
    """Advanced risk management system designed to minimize losses"""
    
    def __init__(self, max_daily_loss: float = 0.05, max_consecutive_losses: int = 3):
        self.max_daily_loss = max_daily_loss
        self.max_consecutive_losses = max_consecutive_losses
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.trade_history = deque(maxlen=100)
        self.kill_switch = False
        self.confidence_threshold = 85  # Only trade with 85%+ confidence
        self.position_size_multiplier = 0.5  # Start with 50% of normal size
        self.market_blacklist = set()
        self.analysis_blacklist = set()
    
    def should_trade(self, prediction: Dict[str, Any], market: str) -> tuple[bool, str]:
        """
        Determine if trade should be executed based on zero-loss criteria
        
        Returns:
            (should_trade, reason)
        """
        # Check kill switch
        if self.kill_switch:
            return False, "Kill switch activated"
        
        # Check daily loss limit
        if self.daily_pnl < -self.max_daily_loss:
            self.kill_switch = True
            return False, f"Daily loss limit exceeded: {self.daily_pnl:.2%}"
        
        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"Consecutive losses limit: {self.consecutive_losses}"
        
        # Check market blacklist
        if market in self.market_blacklist:
            return False, f"Market {market} is blacklisted"
        
        # Check confidence threshold
        confidence = prediction.get("confidence", 0)
        if confidence < self.confidence_threshold:
            return False, f"Confidence too low: {confidence}% < {self.confidence_threshold}%"
        
        # Check analysis type blacklist
        analysis_type = prediction.get("type", "")
        if analysis_type in self.analysis_blacklist:
            return False, f"Analysis type {analysis_type} is blacklisted"
        
        # Check market conditions
        if not self._check_market_conditions(prediction):
            return False, "Unfavorable market conditions"
        
        return True, "Trade approved"
    
    def _check_market_conditions(self, prediction: Dict[str, Any]) -> bool:
        """Check if market conditions are favorable"""
        # Check volatility
        volatility = prediction.get("volatility", 0)
        if volatility > 0.05:  # Too volatile
            return False
        if volatility < 0.005:  # Not volatile enough
            return False
        
        # Check trend strength
        trend_strength = prediction.get("trend_strength", 0)
        if abs(trend_strength) < 0.005:  # No clear trend
            return False
        
        # Check signal agreement
        signal_agreement = prediction.get("signal_agreement", 0)
        if signal_agreement < 0.7:  # Less than 70% agreement
            return False
        
        return True
    
    def calculate_position_size(self, base_amount: float, confidence: float, 
                               market: str) -> float:
        """Calculate position size with zero-loss approach"""
        # Start with base amount
        position = base_amount * self.position_size_multiplier
        
        # Adjust based on confidence
        confidence_multiplier = confidence / 100
        position *= confidence_multiplier
        
        # Reduce size after losses
        if self.consecutive_losses > 0:
            position *= (1 - self.consecutive_losses * 0.2)
        
        # Ensure minimum position
        position = max(position, base_amount * 0.1)
        
        return position
    
    def record_trade_result(self, profit: float, market: str, analysis_type: str):
        """Record trade result and update risk parameters"""
        self.daily_pnl += profit
        self.trade_history.append({
            "profit": profit,
            "market": market,
            "analysis_type": analysis_type,
            "timestamp": datetime.now().isoformat()
        })
        
        if profit < 0:
            self.consecutive_losses += 1
            
            # Blacklist market if it causes losses
            if self._should_blacklist_market(market):
                self.market_blacklist.add(market)
            
            # Blacklist analysis type if it causes losses
            if self._should_blacklist_analysis(analysis_type):
                self.analysis_blacklist.add(analysis_type)
        else:
            self.consecutive_losses = 0
            
            # Remove from blacklist if profitable
            if market in self.market_blacklist:
                self.market_blacklist.remove(market)
            if analysis_type in self.analysis_blacklist:
                self.analysis_blacklist.remove(analysis_type)
    
    def _should_blacklist_market(self, market: str) -> bool:
        """Determine if market should be blacklisted"""
        recent_trades = [t for t in self.trade_history if t["market"] == market]
        if len(recent_trades) < 5:
            return False
        
        losses = sum(1 for t in recent_trades if t["profit"] < 0)
        loss_rate = losses / len(recent_trades)
        
        return loss_rate > 0.6  # Blacklist if >60% loss rate
    
    def _should_blacklist_analysis(self, analysis_type: str) -> bool:
        """Determine if analysis type should be blacklisted"""
        recent_trades = [t for t in self.trade_history if t["analysis_type"] == analysis_type]
        if len(recent_trades) < 5:
            return False
        
        losses = sum(1 for t in recent_trades if t["profit"] < 0)
        loss_rate = losses / len(recent_trades)
        
        return loss_rate > 0.6  # Blacklist if >60% loss rate
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics"""
        recent_trades = list(self.trade_history)[-20:]
        win_rate = sum(1 for t in recent_trades if t["profit"] > 0) / len(recent_trades) if recent_trades else 0
        
        return {
            "daily_pnl": self.daily_pnl,
            "consecutive_losses": self.consecutive_losses,
            "kill_switch": self.kill_switch,
            "win_rate": win_rate,
            "blacklisted_markets": list(self.market_blacklist),
            "blacklisted_analyses": list(self.analysis_blacklist),
            "confidence_threshold": self.confidence_threshold,
            "position_multiplier": self.position_size_multiplier
        }
    
    def reset_daily(self):
        """Reset daily metrics"""
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.kill_switch = False
    
    def adjust_parameters(self, performance: Dict[str, Any]):
        """Adjust risk parameters based on performance"""
        win_rate = performance.get("win_rate", 0.5)
        
        if win_rate > 0.8:
            # Increase confidence threshold for better quality
            self.confidence_threshold = min(95, self.confidence_threshold + 2)
            self.position_size_multiplier = min(1.0, self.position_size_multiplier + 0.1)
        elif win_rate < 0.5:
            # Decrease confidence threshold to allow more trades
            self.confidence_threshold = max(70, self.confidence_threshold - 2)
            self.position_size_multiplier = max(0.2, self.position_size_multiplier - 0.1)
