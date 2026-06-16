from typing import Dict, Any, Optional, List
from models import Prediction
from backtesting.strategy import BacktestStrategy
from indicators import RSI, SMA, EMA
import numpy as np
import time


class HFTStrategy(BacktestStrategy):
    """High-Frequency Trading strategy for ultra-fast execution"""
    
    def __init__(self, min_confidence: float = 75, max_latency_ms: float = 50):
        super().__init__("hft")
        self.min_confidence = min_confidence
        self.max_latency_ms = max_latency_ms
        self.last_execution_time = 0
        self.execution_latency = []
        self.tick_buffer = []
        self.tick_anomalies = []
    
    def generate_signal(self, data: Dict[str, Any]) -> Optional[Prediction]:
        """Generate ultra-fast signal with minimal latency"""
        start_time = time.time()
        
        price_history = data.get("price_history", [])
        if len(price_history) < 20:
            return None
        
        current_price = price_history[-1]
        
        # Detect tick anomalies (price jumps)
        if len(price_history) >= 2:
            price_change = abs(price_history[-1] - price_history[-2]) / price_history[-2]
            if price_change > 0.005:  # 0.5% jump
                self.tick_anomalies.append(price_change)
                if len(self.tick_anomalies) > 100:
                    self.tick_anomalies = self.tick_anomalies[-100:]
        
        # Fast momentum calculation
        if len(price_history) >= 5:
            momentum = (price_history[-1] - price_history[-5]) / price_history[-5]
            
            # Ultra-fast RSI for quick signals
            rsi = self._fast_rsi(price_history, 7)  # Shorter period for speed
            
            # Quick EMA crossover
            ema_5 = self._fast_ema(price_history, 5)
            ema_10 = self._fast_ema(price_history, 10)
            
            # Combine signals for ultra-fast decision
            signal_score = 0
            direction = None
            
            if momentum > 0.003:
                signal_score += 2
                direction = "CALL"
            elif momentum < -0.003:
                signal_score += 2
                direction = "PUT"
            
            if ema_5 and ema_10:
                if ema_5 > ema_10:
                    signal_score += 1.5
                    direction = "CALL"
                else:
                    signal_score += 1.5
                    direction = "PUT"
            
            if rsi:
                if rsi < 35:
                    signal_score += 2
                    direction = "CALL"
                elif rsi > 65:
                    signal_score += 2
                    direction = "PUT"
            
            # Only trade if signal is strong
            if signal_score >= 4 and direction:
                confidence = min(70 + signal_score * 5, 95)
                
                # Check execution latency
                execution_time = (time.time() - start_time) * 1000
                self.execution_latency.append(execution_time)
                if len(self.execution_latency) > 100:
                    self.execution_latency = self.execution_latency[-100:]
                
                # Only execute if latency is acceptable
                if execution_time <= self.max_latency_ms:
                    return Prediction(
                        type="HFT",
                        direction=direction,
                        confidence=confidence,
                        reason=f"HFT signal - Score: {signal_score}, Latency: {execution_time:.2f}ms"
                    )
        
        return None
    
    def _fast_rsi(self, prices: List[float], period: int) -> Optional[float]:
        """Fast RSI calculation optimized for speed"""
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _fast_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Fast EMA calculation optimized for speed"""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def get_average_latency(self) -> float:
        """Get average execution latency in milliseconds"""
        if not self.execution_latency:
            return 0
        return sum(self.execution_latency) / len(self.execution_latency)
    
    def get_anomaly_rate(self) -> float:
        """Get rate of price anomalies"""
        if not self.tick_anomalies:
            return 0
        return len(self.tick_anomalies) / 100  # Rate per 100 ticks
