from typing import Dict, Any, Optional, List
from collections import deque
import numpy as np


class KellyPositionSizer:
    """Advanced position sizing using Kelly Criterion with real Deriv market flow data"""
    
    def __init__(self, base_amount: float = 1.0, max_risk_per_trade: float = 0.02):
        self.base_amount = base_amount
        self.max_risk_per_trade = max_risk_per_trade
        self.balance = 10000.0
        self.trade_history = deque(maxlen=100)
        self.win_streak = 0
        self.loss_streak = 0
        
        # Real market flow data
        self.market_flow_history = deque(maxlen=50)
        self.volatility_history = deque(maxlen=50)
        self.correlation_data = {}
        
        # Kelly parameters
        self.kelly_fraction = 0.25  # Fractional Kelly for safety
        self.min_kelly = 0.01
        self.max_kelly = 0.25
        
        # Performance tracking
        self.strategy_performance = {}
        self.market_performance = {}
        
    def update_with_market_flow(self, market_flow: Dict[str, Any]):
        """Update sizer with real Deriv market flow data"""
        self.market_flow_history.append({
            "change": market_flow.get("change", 0),
            "volatility": market_flow.get("volatility", 0),
            "market": market_flow.get("market", ""),
            "timestamp": market_flow.get("timestamp", "")
        })
        
        # Update volatility history
        volatility = market_flow.get("volatility", 0)
        self.volatility_history.append(volatility)
    
    def calculate_fractional_kelly(self, win_rate: float, avg_win: float, 
                                   avg_loss: float) -> float:
        """Calculate fractional Kelly Criterion position size"""
        if avg_loss == 0 or win_rate == 0:
            return self.min_kelly
        
        win_loss_ratio = avg_win / avg_loss
        kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
        
        # Apply fractional Kelly for safety
        kelly = kelly * self.kelly_fraction
        
        # Clamp to safe range
        kelly = max(self.min_kelly, min(kelly, self.max_kelly))
        
        return kelly
    
    def calculate_kelly_from_real_data(self, market: str) -> Optional[float]:
        """Calculate Kelly Criterion using real trade history data"""
        # Get market-specific trade history
        market_trades = [t for t in self.trade_history if t.get("market") == market]
        
        if len(market_trades) < 10:
            return None  # Need at least 10 trades
        
        wins = [t["profit"] for t in market_trades if t["profit"] > 0]
        losses = [t["profit"] for t in market_trades if t["profit"] < 0]
        
        if not wins or not losses:
            return None
        
        win_rate = len(wins) / len(market_trades)
        avg_win = np.mean(wins)
        avg_loss = abs(np.mean(losses))
        
        return self.calculate_fractional_kelly(win_rate, avg_win, avg_loss)
    
    def calculate_volatility_adjusted_size(self, base_size: float, 
                                         market: str) -> float:
        """Adjust position size based on real volatility data"""
        # Get market-specific volatility
        market_volatility = self._get_market_volatility(market)
        
        if market_volatility is None:
            return base_size
        
        # Calculate average volatility across all markets
        if len(self.volatility_history) > 0:
            avg_volatility = np.mean(self.volatility_history)
            
            # Adjust size based on volatility relative to average
            if market_volatility > avg_volatility * 1.5:
                # High volatility - reduce position
                base_size *= 0.7
            elif market_volatility > avg_volatility * 1.2:
                base_size *= 0.85
            elif market_volatility < avg_volatility * 0.8:
                # Low volatility - increase position
                base_size *= 1.15
            elif market_volatility < avg_volatility * 0.5:
                base_size *= 1.3
        
        return base_size
    
    def _get_market_volatility(self, market: str) -> Optional[float]:
        """Get volatility for specific market from real data"""
        market_data = [d for d in self.market_flow_history if d.get("market") == market]
        
        if len(market_data) < 5:
            return None
        
        volatilities = [d.get("volatility", 0) for d in market_data[-5:]]
        return np.mean(volatilities)
    
    def calculate_correlation_adjusted_size(self, base_size: float, market: str,
                                          active_positions: List[str]) -> float:
        """Adjust position size based on correlation with active positions"""
        if not active_positions:
            return base_size
        
        correlation_risk = 0.0
        
        for active_market in active_positions:
            correlation = self.correlation_data.get((market, active_market), 0.0)
            correlation_risk += abs(correlation)
        
        # Reduce size if high correlation with existing positions
        if correlation_risk > 0.7:
            base_size *= 0.6
        elif correlation_risk > 0.5:
            base_size *= 0.75
        elif correlation_risk > 0.3:
            base_size *= 0.9
        
        return base_size
    
    def calculate_optimal_size(self, confidence: float, market: str, 
                             market_conditions: Dict[str, Any],
                             active_positions: List[str] = None) -> float:
        """Calculate optimal position size using Kelly Criterion with real market data"""
        active_positions = active_positions or []
        
        # Start with base position
        position = self.base_amount
        
        # Apply Kelly Criterion if we have enough data
        kelly_size = self.calculate_kelly_from_real_data(market)
        if kelly_size is not None:
            position = self.balance * kelly_size
        else:
            # Fallback to confidence-based sizing
            position = self.base_amount * (confidence / 100)
        
        # Adjust for volatility using real data
        position = self.calculate_volatility_adjusted_size(position, market)
        
        # Adjust for correlation with active positions
        if active_positions:
            position = self.calculate_correlation_adjusted_size(position, market, active_positions)
        
        # Confidence multiplier
        confidence_multiplier = confidence / 100
        position *= confidence_multiplier
        
        # Win streak bonus
        if self.win_streak >= 3:
            position *= 1.3
        elif self.win_streak >= 2:
            position *= 1.15
        
        # Loss streak protection
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
    
    def update_trade_result(self, profit: float, market: str, strategy: str):
        """Update trade statistics with real data"""
        self.trade_history.append({
            "profit": profit,
            "market": market,
            "strategy": strategy,
            "timestamp": str(datetime.now())
        })
        
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]
        
        if profit > 0:
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.loss_streak += 1
            self.win_streak = 0
        
        self.balance += profit
        
        # Update strategy performance
        if strategy not in self.strategy_performance:
            self.strategy_performance[strategy] = {"wins": 0, "losses": 0, "total": 0}
        
        if profit > 0:
            self.strategy_performance[strategy]["wins"] += 1
        else:
            self.strategy_performance[strategy]["losses"] += 1
        
        self.strategy_performance[strategy]["total"] += 1
        
        # Update market performance
        if market not in self.market_performance:
            self.market_performance[market] = {"wins": 0, "losses": 0, "total": 0}
        
        if profit > 0:
            self.market_performance[market]["wins"] += 1
        else:
            self.market_performance[market]["losses"] += 1
        
        self.market_performance[market]["total"] += 1
    
    def update_correlation_matrix(self, correlation_data: Dict[str, float]):
        """Update correlation matrix from real market data"""
        self.correlation_data = correlation_data
    
    def get_kelly_metrics(self, market: str) -> Dict[str, Any]:
        """Get Kelly Criterion metrics for a market"""
        kelly = self.calculate_kelly_from_real_data(market)
        
        if kelly is None:
            return {
                "kelly": None,
                "status": "insufficient_data",
                "trades_needed": 10
            }
        
        return {
            "kelly": kelly,
            "fractional_kelly": kelly * self.kelly_fraction,
            "position_size": self.balance * kelly * self.kelly_fraction,
            "status": "calculated"
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from real trade data"""
        if not self.trade_history:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "profit_factor": 0
            }
        
        trades = list(self.trade_history)
        wins = [t["profit"] for t in trades if t["profit"] > 0]
        losses = [t["profit"] for t in trades if t["profit"] < 0]
        
        win_rate = len(wins) / len(trades) if trades else 0
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        profit_factor = (sum(wins) / abs(sum(losses))) if losses else 0
        
        return {
            "total_trades": len(trades),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "current_balance": self.balance,
            "win_streak": self.win_streak,
            "loss_streak": self.loss_streak
        }
