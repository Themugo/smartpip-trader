import asyncio
import time
from typing import Dict, Any, Optional, Callable
from collections import deque
import numpy as np


class ExecutionOptimizer:
    """Optimizes trade execution for minimal latency and maximum speed"""
    
    def __init__(self):
        self.latency_history = deque(maxlen=100)
        self.execution_times = deque(maxlen=100)
        self.price_predictions = deque(maxlen=50)
        self.optimal_timing_window = 0.1  # 100ms optimal window
        self.prediction_confidence = 0.0
    
    async def execute_optimized(self, trade_func: Callable, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trade with optimized timing"""
        start_time = time.time()
        
        # Predict optimal execution time
        optimal_delay = self._predict_optimal_delay()
        
        # Wait for optimal window
        if optimal_delay > 0:
            await asyncio.sleep(optimal_delay)
        
        # Execute trade
        result = await trade_func(prediction)
        
        # Record metrics
        execution_time = time.time() - start_time
        self.execution_times.append(execution_time)
        
        return result
    
    def _predict_optimal_delay(self) -> float:
        """Predict optimal delay for execution"""
        if len(self.execution_times) < 10:
            return 0.0
        
        # Analyze execution patterns
        recent_times = list(self.execution_times)[-10:]
        avg_time = sum(recent_times) / len(recent_times)
        
        # Calculate optimal delay based on historical performance
        # If execution is fast, delay slightly to catch optimal price
        if avg_time < 0.05:  # Very fast execution
            return 0.02  # 20ms delay
        elif avg_time < 0.1:  # Fast execution
            return 0.01  # 10ms delay
        else:
            return 0.0  # No delay for slow execution
    
    def record_latency(self, latency: float):
        """Record execution latency"""
        self.latency_history.append(latency)
    
    def get_average_latency(self) -> float:
        """Get average execution latency"""
        if not self.latency_history:
            return 0.0
        return sum(self.latency_history) / len(self.latency_history)
    
    def get_latency_percentile(self, percentile: float) -> float:
        """Get latency at specific percentile"""
        if not self.latency_history:
            return 0.0
        return np.percentile(list(self.latency_history), percentile)
    
    def predict_price_movement(self, price_history: list) -> Optional[float]:
        """Predict short-term price movement for timing"""
        if len(price_history) < 10:
            return None
        
        # Simple momentum prediction
        recent = price_history[-5:]
        older = price_history[-10:-5]
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        
        momentum = (recent_avg - older_avg) / older_avg if older_avg != 0 else 0
        
        # Predict next tick movement
        predicted_change = momentum * price_history[-1]
        
        self.price_predictions.append(predicted_change)
        if len(self.price_predictions) > 50:
            self.price_predictions = self.price_predictions[-50:]
        
        return predicted_change
    
    def get_optimal_execution_price(self, current_price: float, direction: str) -> float:
        """Get optimal execution price based on predictions"""
        if not self.price_predictions:
            return current_price
        
        avg_prediction = sum(self.price_predictions) / len(self.price_predictions)
        
        if direction == "CALL":
            # For CALL, want to buy at lower price
            return current_price - abs(avg_prediction) * 0.5
        else:
            # For PUT, want to buy at higher price
            return current_price + abs(avg_prediction) * 0.5
    
    def should_execute_now(self, current_price: float, target_price: float, tolerance: float = 0.001) -> bool:
        """Determine if should execute now based on price proximity"""
        price_diff = abs(current_price - target_price) / target_price
        return price_diff <= tolerance
