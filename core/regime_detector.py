from typing import Dict, Any, Optional, List, Tuple
from collections import deque
from datetime import datetime
import numpy as np


class RegimeDetector:
    """Market regime detection using real Deriv digits and market flow data"""
    
    def __init__(self):
        # Real Deriv data storage
        self.digit_history = deque(maxlen=200)
        self.price_history = deque(maxlen=200)
        self.market_flow = deque(maxlen=100)
        
        # Regime detection parameters
        self.volatility_regime = "normal"
        self.trend_regime = "neutral"
        self.digit_regime = "random"
        self.liquidity_regime = "normal"
        
        # Historical regime data
        self.regime_history = deque(maxlen=50)
        
        # Digit pattern analysis
        self.digit_patterns = {}
        self.digit_frequencies = {i: 0 for i in range(10)}
        self.digit_transitions = {}
        
        # Market flow analysis
        self.flow_patterns = {}
        self.volatility_windows = deque(maxlen=20)
        
    def update_with_deriv_data(self, price: float, digits: List[int], market: str):
        """Update detector with real Deriv market data"""
        timestamp = datetime.now().isoformat()
        
        # Store digit history
        self.digit_history.append({
            "digits": digits,
            "market": market,
            "timestamp": timestamp
        })
        
        # Update digit frequencies
        for digit in digits:
            self.digit_frequencies[digit] += 1
        
        # Update digit transitions
        if len(self.digit_history) > 1:
            prev_digits = self.digit_history[-2]["digits"]
            curr_digits = digits
            for i in range(min(len(prev_digits), len(curr_digits))):
                transition = (prev_digits[i], curr_digits[i])
                if transition not in self.digit_transitions:
                    self.digit_transitions[transition] = 0
                self.digit_transitions[transition] += 1
        
        # Store price history
        self.price_history.append({
            "price": price,
            "market": market,
            "timestamp": timestamp
        })
        
        # Calculate and store market flow
        if len(self.price_history) > 1:
            prev_price = self.price_history[-2]["price"]
            price_change = (price - prev_price) / prev_price
            volatility = abs(price_change)
            
            self.market_flow.append({
                "change": price_change,
                "volatility": volatility,
                "market": market,
                "timestamp": timestamp
            })
            
            self.volatility_windows.append(volatility)
        
        # Detect all regimes
        self._detect_volatility_regime()
        self._detect_trend_regime()
        self._detect_digit_regime()
        self._detect_liquidity_regime()
        
        # Record regime history
        self.regime_history.append({
            "volatility": self.volatility_regime,
            "trend": self.trend_regime,
            "digit": self.digit_regime,
            "liquidity": self.liquidity_regime,
            "timestamp": timestamp
        })
    
    def _detect_volatility_regime(self):
        """Detect volatility regime from real market data"""
        if len(self.volatility_windows) < 10:
            return
        
        recent_volatility = list(self.volatility_windows)[-10:]
        current_volatility = recent_volatility[-1]
        mean_volatility = np.mean(recent_volatility)
        std_volatility = np.std(recent_volatility)
        
        # Classify volatility regime
        if current_volatility > mean_volatility + 2 * std_volatility:
            self.volatility_regime = "extreme"
        elif current_volatility > mean_volatility + std_volatility:
            self.volatility_regime = "high"
        elif current_volatility < mean_volatility - std_volatility:
            self.volatility_regime = "low"
        else:
            self.volatility_regime = "normal"
    
    def _detect_trend_regime(self):
        """Detect trend regime from real price data"""
        if len(self.price_history) < 20:
            return
        
        recent_prices = [p["price"] for p in list(self.price_history)[-20:]]
        
        # Calculate moving averages
        sma_5 = sum(recent_prices[-5:]) / 5
        sma_10 = sum(recent_prices[-10:]) / 10
        sma_20 = sum(recent_prices) / 20
        
        # Calculate trend strength
        trend_5_10 = (sma_5 - sma_10) / sma_10 if sma_10 != 0 else 0
        trend_10_20 = (sma_10 - sma_20) / sma_20 if sma_20 != 0 else 0
        
        # Classify trend regime
        if trend_5_10 > 0.01 and trend_10_20 > 0.005:
            self.trend_regime = "strong_uptrend"
        elif trend_5_10 > 0.005:
            self.trend_regime = "uptrend"
        elif trend_5_10 < -0.01 and trend_10_20 < -0.005:
            self.trend_regime = "strong_downtrend"
        elif trend_5_10 < -0.005:
            self.trend_regime = "downtrend"
        else:
            self.trend_regime = "neutral"
    
    def _detect_digit_regime(self):
        """Detect digit pattern regime from real Deriv digits"""
        if len(self.digit_history) < 50:
            return
        
        recent_digits = []
        for entry in list(self.digit_history)[-50:]:
            recent_digits.extend(entry["digits"])
        
        # Calculate digit distribution
        digit_counts = {i: recent_digits.count(i) for i in range(10)}
        expected_count = len(recent_digits) / 10
        
        # Chi-square test for randomness
        chi_square = sum((count - expected_count) ** 2 / expected_count 
                       for count in digit_counts.values())
        
        # Classify digit regime
        if chi_square < 15:
            self.digit_regime = "random"
        elif chi_square < 30:
            self.digit_regime = "slightly_biased"
        else:
            self.digit_regime = "highly_biased"
        
        # Detect specific patterns
        self._detect_digit_patterns(recent_digits)
    
    def _detect_digit_patterns(self, digits: List[int]):
        """Detect specific digit patterns"""
        # Check for repeating patterns
        for pattern_length in [2, 3, 4]:
            patterns = {}
            for i in range(len(digits) - pattern_length):
                pattern = tuple(digits[i:i + pattern_length])
                if pattern not in patterns:
                    patterns[pattern] = 0
                patterns[pattern] += 1
            
            # Store patterns that appear frequently
            for pattern, count in patterns.items():
                if count >= 3:
                    pattern_key = f"pattern_{pattern_length}"
                    if pattern_key not in self.digit_patterns:
                        self.digit_patterns[pattern_key] = {}
                    self.digit_patterns[pattern_key][pattern] = count
    
    def _detect_liquidity_regime(self):
        """Detect liquidity regime from market flow data"""
        if len(self.market_flow) < 10:
            return
        
        recent_flow = list(self.market_flow)[-10:]
        avg_volatility = np.mean([f["volatility"] for f in recent_flow])
        
        # Classify liquidity regime based on volatility
        if avg_volatility < 0.002:
            self.liquidity_regime = "low"
        elif avg_volatility < 0.01:
            self.liquidity_regime = "normal"
        else:
            self.liquidity_regime = "high"
    
    def get_regime_summary(self) -> Dict[str, Any]:
        """Get current regime summary"""
        return {
            "volatility_regime": self.volatility_regime,
            "trend_regime": self.trend_regime,
            "digit_regime": self.digit_regime,
            "liquidity_regime": self.liquidity_regime,
            "regime_confidence": self._calculate_regime_confidence(),
            "recommended_actions": self._get_recommended_actions()
        }
    
    def _calculate_regime_confidence(self) -> float:
        """Calculate confidence in current regime detection"""
        if len(self.regime_history) < 10:
            return 0.5
        
        recent_regimes = list(self.regime_history)[-10:]
        
        # Check how stable the current regimes are
        volatility_stability = sum(1 for r in recent_regimes 
                                  if r["volatility"] == self.volatility_regime) / len(recent_regimes)
        trend_stability = sum(1 for r in recent_regimes 
                             if r["trend"] == self.trend_regime) / len(recent_regimes)
        
        return (volatility_stability + trend_stability) / 2
    
    def _get_recommended_actions(self) -> List[str]:
        """Get recommended trading actions based on regimes"""
        actions = []
        
        # Volatility-based actions
        if self.volatility_regime == "extreme":
            actions.append("Reduce position sizes significantly")
            actions.append("Increase confidence threshold")
            actions.append("Consider pausing trading")
        elif self.volatility_regime == "high":
            actions.append("Reduce position sizes moderately")
            actions.append("Increase confidence threshold slightly")
        elif self.volatility_regime == "low":
            actions.append("Can increase position sizes")
            actions.append("Lower confidence threshold acceptable")
        
        # Trend-based actions
        if self.trend_regime in ["strong_uptrend", "strong_downtrend"]:
            actions.append("Trend-following strategies preferred")
            actions.append("Consider directional trades")
        elif self.trend_regime == "neutral":
            actions.append("Mean-reversion strategies preferred")
            actions.append("Range-bound trading strategies")
        
        # Digit-based actions
        if self.digit_regime == "highly_biased":
            actions.append("Digit-based strategies may be effective")
            actions.append("Focus on biased digit patterns")
        elif self.digit_regime == "random":
            actions.append("Digit-based strategies less effective")
            actions.append("Focus on price-based strategies")
        
        # Liquidity-based actions
        if self.liquidity_regime == "low":
            actions.append("Reduce trade frequency")
            actions.append("Be cautious with execution")
        elif self.liquidity_regime == "high":
            actions.append("Can increase trade frequency")
            actions.append("Execution timing less critical")
        
        return actions
    
    def get_digit_analysis(self) -> Dict[str, Any]:
        """Get detailed digit analysis from real data"""
        if not self.digit_history:
            return {"status": "insufficient_data"}
        
        recent_digits = []
        for entry in list(self.digit_history)[-100:]:
            recent_digits.extend(entry["digits"])
        
        # Calculate digit statistics
        digit_counts = {i: recent_digits.count(i) for i in range(10)}
        total_digits = len(recent_digits)
        digit_percentages = {i: (count / total_digits) * 100 for i, count in digit_counts.items()}
        
        # Find most and least frequent digits
        most_frequent = max(digit_counts.items(), key=lambda x: x[1])
        least_frequent = min(digit_counts.items(), key=lambda x: x[1])
        
        return {
            "total_digits": total_digits,
            "digit_counts": digit_counts,
            "digit_percentages": digit_percentages,
            "most_frequent_digit": most_frequent,
            "least_frequent_digit": least_frequent,
            "digit_regime": self.digit_regime,
            "detected_patterns": self.digit_patterns
        }
    
    def get_market_flow_analysis(self) -> Dict[str, Any]:
        """Get market flow analysis from real data"""
        if not self.market_flow:
            return {"status": "insufficient_data"}
        
        recent_flow = list(self.market_flow)[-50:]
        
        changes = [f["change"] for f in recent_flow]
        volatilities = [f["volatility"] for f in recent_flow]
        
        return {
            "avg_change": np.mean(changes),
            "avg_volatility": np.mean(volatilities),
            "volatility_std": np.std(volatilities),
            "current_volatility": volatilities[-1],
            "volatility_regime": self.volatility_regime,
            "trend_regime": self.trend_regime,
            "liquidity_regime": self.liquidity_regime
        }
    
    def predict_regime_change(self) -> Optional[Dict[str, Any]]:
        """Predict potential regime change"""
        if len(self.regime_history) < 20:
            return None
        
        recent_regimes = list(self.regime_history)[-20:]
        
        # Check for regime transitions
        volatility_changes = []
        for i in range(1, len(recent_regimes)):
            if recent_regimes[i]["volatility"] != recent_regimes[i-1]["volatility"]:
                volatility_changes.append(i)
        
        # If volatility regime changes frequently, predict potential change
        if len(volatility_changes) > 3:
            return {
                "prediction": "high_volatility_change_risk",
                "confidence": 0.7,
                "recommendation": "Be cautious with position sizing"
            }
        
        return None
    
    def get_optimal_trading_parameters(self) -> Dict[str, Any]:
        """Get optimal trading parameters based on current regimes"""
        params = {
            "confidence_threshold": 85,
            "position_size_multiplier": 1.0,
            "max_trades_per_hour": 10,
            "preferred_strategies": []
        }
        
        # Adjust based on volatility regime
        if self.volatility_regime == "extreme":
            params["confidence_threshold"] = 92
            params["position_size_multiplier"] = 0.5
            params["max_trades_per_hour"] = 5
        elif self.volatility_regime == "high":
            params["confidence_threshold"] = 88
            params["position_size_multiplier"] = 0.7
            params["max_trades_per_hour"] = 7
        elif self.volatility_regime == "low":
            params["confidence_threshold"] = 80
            params["position_size_multiplier"] = 1.2
            params["max_trades_per_hour"] = 15
        
        # Adjust based on trend regime
        if self.trend_regime in ["strong_uptrend", "strong_downtrend"]:
            params["preferred_strategies"].extend(["trend_following", "momentum"])
            params["position_size_multiplier"] *= 1.1
        elif self.trend_regime == "neutral":
            params["preferred_strategies"].extend(["mean_reversion", "range_trading"])
        
        # Adjust based on digit regime
        if self.digit_regime == "highly_biased":
            params["preferred_strategies"].append("digit_based")
        
        return params
