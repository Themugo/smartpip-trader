import numpy as np
from typing import List, Dict, Any
from collections import deque


class FeatureEngineer:
    """Engineer features for machine learning prediction"""
    
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
    
    def extract_features(self, data: Dict[str, Any]) -> np.ndarray:
        """
        Extract features from market data
        
        Args:
            data: Dictionary containing market data
            
        Returns:
            Feature vector as numpy array
        """
        features = []
        
        # Price features
        price_history = data.get("price_history", [])
        if len(price_history) >= self.window_size:
            recent_prices = list(price_history)[-self.window_size:]
            
            # Returns
            returns = np.diff(recent_prices)
            features.extend([
                np.mean(returns),
                np.std(returns),
                np.min(returns),
                np.max(returns)
            ])
            
            # Momentum
            features.append(recent_prices[-1] - recent_prices[-5])
            features.append(recent_prices[-1] - recent_prices[-10])
            
            # Volatility
            features.append(np.std(recent_prices))
        else:
            features.extend([0.0] * 7)
        
        # Digit features
        last_20_digits = data.get("last_20_digits", [])
        if len(last_20_digits) >= 10:
            digits = last_20_digits[-10:]
            
            # Digit frequency
            digit_counts = [digits.count(i) for i in range(10)]
            features.extend(digit_counts)
            
            # Digit patterns
            features.append(sum(1 for i in range(len(digits)-1) if digits[i] % 2 == digits[i+1] % 2))
            features.append(sum(1 for i in range(len(digits)-1) if digits[i] == digits[i+1]))
        else:
            features.extend([0.0] * 12)
        
        # Technical indicator features
        if len(price_history) >= 30:
            from indicators import SMA, EMA, RSI
            
            sma_10 = SMA.calculate(price_history, 10)
            sma_20 = SMA.calculate(price_history, 20)
            ema_12 = EMA.calculate(price_history, 12)
            rsi = RSI.calculate(price_history, 14)
            
            features.extend([
                sma_10 if sma_10 else 0,
                sma_20 if sma_20 else 0,
                ema_12 if ema_12 else 0,
                rsi if rsi else 50
            ])
        else:
            features.extend([0.0] * 4)
        
        # Market features
        current_price = data.get("current_price", 0)
        features.append(current_price)
        
        return np.array(features)
    
    def get_feature_names(self) -> List[str]:
        """Get names of extracted features"""
        return [
            # Price features
            "return_mean",
            "return_std",
            "return_min",
            "return_max",
            "momentum_5",
            "momentum_10",
            "volatility",
            # Digit features
            "digit_0", "digit_1", "digit_2", "digit_3", "digit_4",
            "digit_5", "digit_6", "digit_7", "digit_8", "digit_9",
            "even_odd_pattern",
            "match_pattern",
            # Technical indicators
            "sma_10",
            "sma_20",
            "ema_12",
            "rsi_14",
            # Market features
            "current_price"
        ]
