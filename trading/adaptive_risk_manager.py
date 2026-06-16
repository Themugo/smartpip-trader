from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import deque
import numpy as np


class AdaptiveRiskManager:
    """Advanced adaptive risk management using real Deriv market data and digits"""
    
    def __init__(self, max_daily_loss: float = 0.05, max_consecutive_losses: int = 3):
        self.max_daily_loss = max_daily_loss
        self.max_consecutive_losses = max_consecutive_losses
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.trade_history = deque(maxlen=100)
        self.kill_switch = False
        
        # Adaptive parameters
        self.confidence_threshold = 85.0
        self.position_size_multiplier = 0.5
        self.max_risk_per_trade = 0.02
        
        # Market regime detection
        self.volatility_regime = "normal"
        self.trend_regime = "neutral"
        self.volatility_history = deque(maxlen=50)
        self.trend_history = deque(maxlen=50)
        
        # Real Deriv data tracking
        self.digit_history = deque(maxlen=100)
        self.price_history = deque(maxlen=100)
        self.market_flow = deque(maxlen=50)
        
        # Performance tracking
        self.strategy_performance = {}
        self.market_performance = {}
        self.time_performance = {}
        
        # Correlation tracking
        self.market_correlations = {}
        
        # Drawdown tracking
        self.peak_balance = 0.0
        self.current_balance = 0.0
        self.drawdown_percentage = 0.0
        
    def update_with_deriv_data(self, price: float, digits: List[int], market: str):
        """Update risk manager with real Deriv market data"""
        # Store price history
        self.price_history.append({
            "price": price,
            "market": market,
            "timestamp": datetime.now().isoformat()
        })
        
        # Store digit history
        self.digit_history.append({
            "digits": digits,
            "market": market,
            "timestamp": datetime.now().isoformat()
        })
        
        # Calculate market flow (price changes)
        if len(self.price_history) > 1:
            prev_price = self.price_history[-2]["price"]
            price_change = (price - prev_price) / prev_price
            self.market_flow.append({
                "change": price_change,
                "market": market,
                "timestamp": datetime.now().isoformat()
            })
        
        # Update volatility regime
        self._update_volatility_regime()
        
        # Update trend regime
        self._update_trend_regime()
        
        # Adjust risk parameters based on regime
        self._adjust_risk_parameters()
    
    def _update_volatility_regime(self):
        """Detect current volatility regime from real market data"""
        if len(self.market_flow) < 10:
            return
        
        recent_changes = [m["change"] for m in list(self.market_flow)[-10:]]
        volatility = np.std(recent_changes)
        mean_vol = np.mean([abs(m["change"]) for m in self.market_flow])
        
        # Classify volatility regime
        if volatility > mean_vol * 2:
            self.volatility_regime = "extreme"
        elif volatility > mean_vol * 1.5:
            self.volatility_regime = "high"
        elif volatility < mean_vol * 0.5:
            self.volatility_regime = "low"
        else:
            self.volatility_regime = "normal"
    
    def _update_trend_regime(self):
        """Detect current trend regime from real market data"""
        if len(self.price_history) < 20:
            return
        
        recent_prices = [p["price"] for p in list(self.price_history)[-20:]]
        sma_10 = sum(recent_prices[-10:]) / 10
        sma_20 = sum(recent_prices) / 20
        
        trend_strength = (sma_10 - sma_20) / sma_20 if sma_20 != 0 else 0
        
        # Classify trend regime
        if trend_strength > 0.01:
            self.trend_regime = "strong_uptrend"
        elif trend_strength > 0.005:
            self.trend_regime = "uptrend"
        elif trend_strength < -0.01:
            self.trend_regime = "strong_downtrend"
        elif trend_strength < -0.005:
            self.trend_regime = "downtrend"
        else:
            self.trend_regime = "neutral"
    
    def _adjust_risk_parameters(self):
        """Adjust risk parameters based on market regimes and performance"""
        # Adjust confidence threshold based on volatility regime
        if self.volatility_regime == "extreme":
            self.confidence_threshold = min(95, self.confidence_threshold + 5)
        elif self.volatility_regime == "high":
            self.confidence_threshold = min(92, self.confidence_threshold + 2)
        elif self.volatility_regime == "low":
            self.confidence_threshold = max(75, self.confidence_threshold - 5)
        else:
            self.confidence_threshold = max(80, min(90, self.confidence_threshold))
        
        # Adjust position size based on drawdown
        if self.drawdown_percentage > 10:
            self.position_size_multiplier *= 0.7
        elif self.drawdown_percentage > 5:
            self.position_size_multiplier *= 0.85
        elif self.drawdown_percentage < 2:
            self.position_size_multiplier *= 1.1
        
        # Adjust position size based on trend regime
        if self.trend_regime in ["strong_uptrend", "strong_downtrend"]:
            self.position_size_multiplier *= 1.15
        elif self.trend_regime == "neutral":
            self.position_size_multiplier *= 0.9
        
        # Ensure position size multiplier stays within bounds
        self.position_size_multiplier = max(0.2, min(1.0, self.position_size_multiplier))
    
    def should_trade(self, prediction: Dict[str, Any], market: str) -> tuple[bool, str]:
        """
        Determine if trade should be executed based on adaptive risk criteria
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
        
        # Check confidence threshold (adaptive)
        confidence = prediction.get("confidence", 0)
        if confidence < self.confidence_threshold:
            return False, f"Confidence too low: {confidence}% < {self.confidence_threshold}%"
        
        # Check market conditions based on real data
        if not self._check_market_conditions_real(market):
            return False, "Unfavorable market conditions"
        
        # Check volatility regime
        if self.volatility_regime == "extreme" and confidence < 90:
            return False, "Extreme volatility requires higher confidence"
        
        return True, "Trade approved"
    
    def _check_market_conditions_real(self, market: str) -> bool:
        """Check market conditions using real Deriv data"""
        # Get market-specific data
        market_data = [d for d in self.market_flow if d["market"] == market]
        
        if len(market_data) < 5:
            return True  # Allow trade if insufficient data
        
        recent_changes = [m["change"] for m in market_data[-5:]]
        volatility = np.std(recent_changes)
        
        # Check volatility range
        if volatility > 0.05:  # Too volatile
            return False
        if volatility < 0.005:  # Not volatile enough
            return False
        
        # Check trend strength
        if len(self.price_history) >= 20:
            market_prices = [p["price"] for p in self.price_history if p["market"] == market]
            if len(market_prices) >= 10:
                recent_avg = sum(market_prices[-5:]) / 5
                older_avg = sum(market_prices[-10:-5]) / 5
                trend_strength = abs(recent_avg - older_avg) / older_avg if older_avg != 0 else 0
                
                if trend_strength < 0.005:  # No clear trend
                    return False
        
        return True
    
    def calculate_position_size(self, base_amount: float, confidence: float, 
                               market: str) -> float:
        """Calculate position size using adaptive approach with real market data"""
        # Start with base amount
        position = base_amount * self.position_size_multiplier
        
        # Adjust based on confidence
        confidence_multiplier = confidence / 100
        position *= confidence_multiplier
        
        # Adjust based on volatility regime
        if self.volatility_regime == "low":
            position *= 1.2
        elif self.volatility_regime == "high":
            position *= 0.8
        elif self.volatility_regime == "extreme":
            position *= 0.5
        
        # Adjust based on trend regime
        if self.trend_regime in ["strong_uptrend", "strong_downtrend"]:
            position *= 1.1
        elif self.trend_regime == "neutral":
            position *= 0.9
        
        # Adjust based on market performance
        if market in self.market_performance:
            market_perf = self.market_performance[market]
            if market_perf["win_rate"] > 0.8:
                position *= 1.15
            elif market_perf["win_rate"] < 0.5:
                position *= 0.7
        
        # Reduce size after losses
        if self.consecutive_losses > 0:
            position *= (1 - self.consecutive_losses * 0.15)
        
        # Risk limit
        if self.current_balance > 0:
            max_position = self.current_balance * self.max_risk_per_trade
            position = min(position, max_position)
        
        # Minimum position
        position = max(position, base_amount * 0.1)
        
        return position
    
    def record_trade_result(self, profit: float, market: str, analysis_type: str, 
                           confidence: float):
        """Record trade result and update adaptive parameters"""
        self.daily_pnl += profit
        self.current_balance += profit
        
        # Update peak balance for drawdown calculation
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        # Calculate drawdown
        if self.peak_balance > 0:
            self.drawdown_percentage = ((self.peak_balance - self.current_balance) / self.peak_balance) * 100
        
        self.trade_history.append({
            "profit": profit,
            "market": market,
            "analysis_type": analysis_type,
            "confidence": confidence,
            "volatility_regime": self.volatility_regime,
            "trend_regime": self.trend_regime,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update strategy performance
        if analysis_type not in self.strategy_performance:
            self.strategy_performance[analysis_type] = {"wins": 0, "losses": 0, "total": 0}
        
        if profit > 0:
            self.strategy_performance[analysis_type]["wins"] += 1
            self.consecutive_losses = 0
        else:
            self.strategy_performance[analysis_type]["losses"] += 1
            self.consecutive_losses += 1
        
        self.strategy_performance[analysis_type]["total"] += 1
        
        # Update market performance
        if market not in self.market_performance:
            self.market_performance[market] = {"wins": 0, "losses": 0, "total": 0}
        
        if profit > 0:
            self.market_performance[market]["wins"] += 1
        else:
            self.market_performance[market]["losses"] += 1
        
        self.market_performance[market]["total"] += 1
        
        # Update time performance
        hour = datetime.now().hour
        if hour not in self.time_performance:
            self.time_performance[hour] = {"wins": 0, "losses": 0, "total": 0}
        
        if profit > 0:
            self.time_performance[hour]["wins"] += 1
        else:
            self.time_performance[hour]["losses"] += 1
        
        self.time_performance[hour]["total"] += 1
        
        # Adjust risk parameters based on performance
        self._adjust_parameters_based_on_performance()
    
    def _adjust_parameters_based_on_performance(self):
        """Adjust risk parameters based on recent performance"""
        if len(self.trade_history) < 10:
            return
        
        recent_trades = list(self.trade_history)[-10:]
        win_rate = sum(1 for t in recent_trades if t["profit"] > 0) / len(recent_trades)
        
        if win_rate > 0.8:
            # Increase confidence threshold for better quality trades
            self.confidence_threshold = min(95, self.confidence_threshold + 1)
            self.position_size_multiplier = min(1.0, self.position_size_multiplier + 0.05)
        elif win_rate < 0.5:
            # Decrease confidence threshold to allow more trades
            self.confidence_threshold = max(70, self.confidence_threshold - 1)
            self.position_size_multiplier = max(0.2, self.position_size_multiplier - 0.05)
    
    def get_strategy_weights(self) -> Dict[str, float]:
        """Get adaptive strategy weights based on performance"""
        weights = {}
        
        for strategy, perf in self.strategy_performance.items():
            if perf["total"] >= 5:
                win_rate = perf["wins"] / perf["total"]
                # Higher win rate = higher weight
                weights[strategy] = win_rate
            else:
                weights[strategy] = 0.5  # Default weight for insufficient data
        
        # Normalize weights
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        
        return weights
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics with real market data"""
        recent_trades = list(self.trade_history)[-20:]
        win_rate = sum(1 for t in recent_trades if t["profit"] > 0) / len(recent_trades) if recent_trades else 0
        
        return {
            "daily_pnl": self.daily_pnl,
            "consecutive_losses": self.consecutive_losses,
            "kill_switch": self.kill_switch,
            "win_rate": win_rate,
            "confidence_threshold": self.confidence_threshold,
            "position_multiplier": self.position_size_multiplier,
            "volatility_regime": self.volatility_regime,
            "trend_regime": self.trend_regime,
            "drawdown_percentage": self.drawdown_percentage,
            "current_balance": self.current_balance,
            "strategy_performance": self.strategy_performance,
            "market_performance": self.market_performance,
            "strategy_weights": self.get_strategy_weights()
        }
    
    def reset_daily(self):
        """Reset daily metrics"""
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.kill_switch = False
