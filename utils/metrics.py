import time
import logging
from typing import Dict, Any, Optional
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Track and report performance metrics"""
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize performance metrics tracker
        
        Args:
            max_history: Maximum number of metric entries to keep
        """
        self.metrics: Dict[str, deque] = {}
        self.max_history = max_history
        self.counters: Dict[str, int] = {}
        self.timers: Dict[str, float] = {}
    
    def record_timing(self, name: str, duration: float):
        """
        Record a timing metric
        
        Args:
            name: Metric name
            duration: Duration in seconds
        """
        if name not in self.metrics:
            self.metrics[name] = deque(maxlen=self.max_history)
        
        self.metrics[name].append({
            "value": duration,
            "timestamp": datetime.now().isoformat()
        })
    
    def increment_counter(self, name: str, value: int = 1):
        """
        Increment a counter metric
        
        Args:
            name: Counter name
            value: Value to add (default: 1)
        """
        if name not in self.counters:
            self.counters[name] = 0
        self.counters[name] += value
    
    def start_timer(self, name: str):
        """Start a timer for a named operation"""
        self.timers[name] = time.time()
    
    def stop_timer(self, name: str) -> Optional[float]:
        """
        Stop a timer and record the duration
        
        Args:
            name: Timer name
            
        Returns:
            Duration in seconds, or None if timer not found
        """
        if name not in self.timers:
            logger.warning(f"Timer {name} not found")
            return None
        
        duration = time.time() - self.timers[name]
        del self.timers[name]
        self.record_timing(name, duration)
        return duration
    
    def get_average(self, name: str) -> Optional[float]:
        """
        Get average value for a metric
        
        Args:
            name: Metric name
            
        Returns:
            Average value, or None if metric not found
        """
        if name not in self.metrics or not self.metrics[name]:
            return None
        
        values = [m["value"] for m in self.metrics[name]]
        return sum(values) / len(values)
    
    def get_percentile(self, name: str, percentile: float) -> Optional[float]:
        """
        Get percentile value for a metric
        
        Args:
            name: Metric name
            percentile: Percentile (0-100)
            
        Returns:
            Percentile value, or None if metric not found
        """
        if name not in self.metrics or not self.metrics[name]:
            return None
        
        values = sorted([m["value"] for m in self.metrics[name]])
        index = int(len(values) * percentile / 100)
        return values[min(index, len(values) - 1)]
    
    def get_counter(self, name: str) -> int:
        """
        Get counter value
        
        Args:
            name: Counter name
            
        Returns:
            Counter value (0 if not found)
        """
        return self.counters.get(name, 0)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        summary = {
            "counters": self.counters.copy(),
            "timings": {}
        }
        
        for name in self.metrics:
            values = [m["value"] for m in self.metrics[name]]
            if values:
                summary["timings"][name] = {
                    "count": len(values),
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "p50": self.get_percentile(name, 50),
                    "p95": self.get_percentile(name, 95),
                    "p99": self.get_percentile(name, 99)
                }
        
        return summary
    
    def reset(self):
        """Reset all metrics"""
        self.metrics.clear()
        self.counters.clear()
        self.timers.clear()
