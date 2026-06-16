from typing import Dict, Any, Optional, List
from collections import defaultdict, deque
import numpy as np


class AdaptiveStrategyManager:
    """Adaptive strategy weight management based on real performance data"""
    
    def __init__(self):
        # Base strategy weights
        self.base_weights = {
            "even_odd": 0.15,
            "rise_fall": 0.20,
            "over_under": 0.20,
            "match_diff": 0.15,
            "technical": 0.20,
            "ml": 0.10
        }
        
        # Current adaptive weights
        self.current_weights = self.base_weights.copy()
        
        # Performance tracking
        self.strategy_performance = defaultdict(lambda: {
            "wins": 0,
            "losses": 0,
            "total": 0,
            "recent_results": deque(maxlen=20),
            "win_rate": 0.0,
            "profit_factor": 0.0
        })
        
        # Market-specific strategy performance
        self.market_strategy_performance = defaultdict(lambda: defaultdict(dict))
        
        # Time-specific strategy performance
        self.time_strategy_performance = defaultdict(lambda: defaultdict(dict))
        
        # Regime-specific strategy performance
        self.regime_strategy_performance = defaultdict(lambda: defaultdict(dict))
        
        # Weight adjustment parameters
        self.min_weight = 0.05
        self.max_weight = 0.35
        self.adjustment_rate = 0.1
        self.min_trades_for_adjustment = 10
        
        # Adaptation history
        self.adaptation_history = deque(maxlen=50)
    
    def update_strategy_performance(self, strategy: str, profit: float, 
                                   market: str, regime: Dict[str, str], 
                                   timestamp: str):
        """Update strategy performance with real trade data"""
        # Update overall strategy performance
        perf = self.strategy_performance[strategy]
        perf["total"] += 1
        perf["recent_results"].append(profit)
        
        if profit > 0:
            perf["wins"] += 1
        else:
            perf["losses"] += 1
        
        # Calculate win rate
        perf["win_rate"] = perf["wins"] / perf["total"] if perf["total"] > 0 else 0
        
        # Calculate profit factor
        recent_results = list(perf["recent_results"])
        wins = [r for r in recent_results if r > 0]
        losses = [r for r in recent_results if r < 0]
        
        if wins and losses:
            avg_win = np.mean(wins)
            avg_loss = abs(np.mean(losses))
            perf["profit_factor"] = avg_win / avg_loss
        elif wins:
            perf["profit_factor"] = 2.0  # Default if no losses yet
        else:
            perf["profit_factor"] = 0.0
        
        # Update market-specific performance
        market_perf = self.market_strategy_performance[market][strategy]
        market_perf["total"] = market_perf.get("total", 0) + 1
        market_perf["wins"] = market_perf.get("wins", 0) + (1 if profit > 0 else 0)
        market_perf["win_rate"] = market_perf["wins"] / market_perf["total"]
        
        # Update time-specific performance
        hour = int(timestamp.split("T")[1].split(":")[0])
        time_perf = self.time_strategy_performance[hour][strategy]
        time_perf["total"] = time_perf.get("total", 0) + 1
        time_perf["wins"] = time_perf.get("wins", 0) + (1 if profit > 0 else 0)
        time_perf["win_rate"] = time_perf["wins"] / time_perf["total"]
        
        # Update regime-specific performance
        regime_key = f"{regime.get('volatility', 'normal')}_{regime.get('trend', 'neutral')}"
        regime_perf = self.regime_strategy_performance[regime_key][strategy]
        regime_perf["total"] = regime_perf.get("total", 0) + 1
        regime_perf["wins"] = regime_perf.get("wins", 0) + (1 if profit > 0 else 0)
        regime_perf["win_rate"] = regime_perf["wins"] / regime_perf["total"]
        
        # Adjust weights if enough data
        if perf["total"] >= self.min_trades_for_adjustment:
            self._adjust_weights()
    
    def _adjust_weights(self):
        """Adjust strategy weights based on performance"""
        # Calculate performance scores for each strategy
        performance_scores = {}
        
        for strategy, perf in self.strategy_performance.items():
            if perf["total"] < self.min_trades_for_adjustment:
                performance_scores[strategy] = 0.5  # Neutral score for insufficient data
                continue
            
            # Score based on win rate and profit factor
            win_rate_score = perf["win_rate"]
            profit_factor_score = min(perf["profit_factor"] / 2.0, 1.0)  # Normalize to 0-1
            
            # Combined score (weighted)
            performance_scores[strategy] = (win_rate_score * 0.6 + profit_factor_score * 0.4)
        
        # Adjust weights based on performance
        for strategy, score in performance_scores.items():
            if strategy not in self.current_weights:
                continue
            
            current_weight = self.current_weights[strategy]
            
            # Calculate adjustment
            if score > 0.7:
                # High performance - increase weight
                adjustment = self.adjustment_rate * (score - 0.5)
                new_weight = current_weight * (1 + adjustment)
            elif score < 0.4:
                # Low performance - decrease weight
                adjustment = self.adjustment_rate * (0.5 - score)
                new_weight = current_weight * (1 - adjustment)
            else:
                # Average performance - maintain weight
                new_weight = current_weight
            
            # Clamp to allowed range
            new_weight = max(self.min_weight, min(self.max_weight, new_weight))
            
            self.current_weights[strategy] = new_weight
        
        # Normalize weights to sum to 1
        total_weight = sum(self.current_weights.values())
        if total_weight > 0:
            for strategy in self.current_weights:
                self.current_weights[strategy] /= total_weight
        
        # Record adaptation
        self.adaptation_history.append({
            "weights": self.current_weights.copy(),
            "performance_scores": performance_scores.copy(),
            "timestamp": str(datetime.now())
        })
    
    def get_adaptive_weights(self, market: str = None, regime: Dict[str, str] = None) -> Dict[str, float]:
        """Get adaptive weights, optionally adjusted for market or regime"""
        weights = self.current_weights.copy()
        
        # Adjust for market-specific performance
        if market and market in self.market_strategy_performance:
            market_weights = self._calculate_market_specific_weights(market)
            if market_weights:
                # Blend global and market-specific weights (70% global, 30% market)
                for strategy in weights:
                    if strategy in market_weights:
                        weights[strategy] = (weights[strategy] * 0.7 + 
                                            market_weights[strategy] * 0.3)
        
        # Adjust for regime-specific performance
        if regime:
            regime_key = f"{regime.get('volatility', 'normal')}_{regime.get('trend', 'neutral')}"
            if regime_key in self.regime_strategy_performance:
                regime_weights = self._calculate_regime_specific_weights(regime_key)
                if regime_weights:
                    # Blend global and regime-specific weights (80% global, 20% regime)
                    for strategy in weights:
                        if strategy in regime_weights:
                            weights[strategy] = (weights[strategy] * 0.8 + 
                                              regime_weights[strategy] * 0.2)
        
        # Normalize
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        
        return weights
    
    def _calculate_market_specific_weights(self, market: str) -> Optional[Dict[str, float]]:
        """Calculate market-specific strategy weights"""
        market_data = self.market_strategy_performance[market]
        
        if not market_data:
            return None
        
        weights = {}
        total_performance = 0
        
        for strategy, perf in market_data.items():
            if perf["total"] >= 5:
                weights[strategy] = perf["win_rate"]
                total_performance += weights[strategy]
        
        if total_performance > 0:
            weights = {k: v / total_performance for k, v in weights.items()}
            return weights
        
        return None
    
    def _calculate_regime_specific_weights(self, regime_key: str) -> Optional[Dict[str, float]]:
        """Calculate regime-specific strategy weights"""
        regime_data = self.regime_strategy_performance[regime_key]
        
        if not regime_data:
            return None
        
        weights = {}
        total_performance = 0
        
        for strategy, perf in regime_data.items():
            if perf["total"] >= 5:
                weights[strategy] = perf["win_rate"]
                total_performance += weights[strategy]
        
        if total_performance > 0:
            weights = {k: v / total_performance for k, v in weights.items()}
            return weights
        
        return None
    
    def get_strategy_performance_summary(self) -> Dict[str, Any]:
        """Get summary of all strategy performance"""
        summary = {}
        
        for strategy, perf in self.strategy_performance.items():
            summary[strategy] = {
                "total_trades": perf["total"],
                "wins": perf["wins"],
                "losses": perf["losses"],
                "win_rate": perf["win_rate"],
                "profit_factor": perf["profit_factor"],
                "current_weight": self.current_weights.get(strategy, 0),
                "base_weight": self.base_weights.get(strategy, 0),
                "weight_change": self.current_weights.get(strategy, 0) - self.base_weights.get(strategy, 0)
            }
        
        return summary
    
    def get_best_strategies(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Get best performing strategies"""
        strategies = []
        
        for strategy, perf in self.strategy_performance.items():
            if perf["total"] >= self.min_trades_for_adjustment:
                strategies.append({
                    "strategy": strategy,
                    "win_rate": perf["win_rate"],
                    "profit_factor": perf["profit_factor"],
                    "total_trades": perf["total"],
                    "current_weight": self.current_weights.get(strategy, 0)
                })
        
        # Sort by combined score (win_rate * 0.6 + profit_factor_score * 0.4)
        strategies.sort(key=lambda x: (x["win_rate"] * 0.6 + min(x["profit_factor"] / 2.0, 1.0) * 0.4), reverse=True)
        
        return strategies[:limit]
    
    def get_worst_strategies(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Get worst performing strategies"""
        strategies = []
        
        for strategy, perf in self.strategy_performance.items():
            if perf["total"] >= self.min_trades_for_adjustment:
                strategies.append({
                    "strategy": strategy,
                    "win_rate": perf["win_rate"],
                    "profit_factor": perf["profit_factor"],
                    "total_trades": perf["total"],
                    "current_weight": self.current_weights.get(strategy, 0)
                })
        
        # Sort by combined score (win_rate * 0.6 + profit_factor_score * 0.4)
        strategies.sort(key=lambda x: (x["win_rate"] * 0.6 + min(x["profit_factor"] / 2.0, 1.0) * 0.4))
        
        return strategies[:limit]
    
    def reset_weights(self):
        """Reset weights to base values"""
        self.current_weights = self.base_weights.copy()
        self.adaptation_history.append({
            "action": "reset",
            "weights": self.current_weights.copy(),
            "timestamp": str(datetime.now())
        })
    
    def get_adaptation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent adaptation history"""
        return list(self.adaptation_history)[-limit:]
    
    def should_disable_strategy(self, strategy: str) -> bool:
        """Determine if a strategy should be disabled due to poor performance"""
        perf = self.strategy_performance[strategy]
        
        # Disable if:
        # 1. Less than 30% win rate with at least 20 trades
        # 2. Profit factor less than 0.5 with at least 20 trades
        # 3. Weight has dropped to minimum
        
        if perf["total"] >= 20:
            if perf["win_rate"] < 0.3:
                return True
            if perf["profit_factor"] < 0.5:
                return True
        
        if self.current_weights.get(strategy, 0) <= self.min_weight * 1.1:
            return True
        
        return False
    
    def get_enabled_strategies(self) -> List[str]:
        """Get list of strategies that should be enabled"""
        enabled = []
        
        for strategy in self.base_weights.keys():
            if not self.should_disable_strategy(strategy):
                enabled.append(strategy)
        
        return enabled
