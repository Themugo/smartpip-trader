"""
Anomaly Detector
================

Statistical anomaly detection for metrics.
"""

import time
import threading
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import deque
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """Result of anomaly detection"""
    metric_name: str
    timestamp: float
    value: float
    expected_value: float
    deviation: float
    deviation_std: float  # Standard deviations from mean
    is_anomaly: bool
    anomaly_type: str  # spike, drop, drift, threshold


class AnomalyDetector:
    """
    Statistical anomaly detector.
    
    Methods:
    - Z-score: Values beyond N standard deviations
    - Percentile: Values outside percentile range
    - Moving average: Deviation from rolling mean
    - Change detection: Sudden shifts in values
    """
    
    def __init__(self):
        self._metrics: Dict[str, deque] = {}
        self._windows: Dict[str, int] = {}
        self._thresholds: Dict[str, float] = {}
        self._callbacks: List[Callable[[AnomalyResult], None]] = []
        self._lock = threading.Lock()
        
        # Default settings
        self._default_window = 100
        self._default_threshold = 3.0  # Standard deviations
    
    def register_metric(
        self,
        name: str,
        window_size: int = 100,
        threshold_std: float = 3.0
    ) -> None:
        """Register a metric for anomaly detection"""
        with self._lock:
            self._metrics[name] = deque(maxlen=window_size)
            self._windows[name] = window_size
            self._thresholds[name] = threshold_std
    
    def detect(
        self,
        metric_name: str,
        value: float,
        timestamp: Optional[float] = None
    ) -> Optional[AnomalyResult]:
        """Detect anomaly in a metric value"""
        timestamp = timestamp or time.time()
        
        with self._lock:
            # Auto-register if not seen
            if metric_name not in self._metrics:
                self._metrics[metric_name] = deque(maxlen=self._default_window)
                self._windows[metric_name] = self._default_window
                self._thresholds[metric_name] = self._default_threshold
            
            metric_data = self._metrics[metric_name]
            threshold = self._thresholds[metric_name]
            
            # Add current value
            metric_data.append(value)
            
            if len(metric_data) < 10:
                # Not enough data
                return None
            
            # Calculate statistics
            values = list(metric_data)
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            std = math.sqrt(variance) if variance > 0 else 0.001
            
            # Calculate deviation
            deviation = value - mean
            deviation_std = deviation / std if std > 0 else 0
            
            # Determine anomaly type
            is_anomaly = abs(deviation_std) > threshold
            anomaly_type = "normal"
            
            if is_anomaly:
                if deviation > 0:
                    if deviation_std > 5:
                        anomaly_type = "spike"
                    else:
                        anomaly_type = "drift"
                else:
                    if deviation_std < -5:
                        anomaly_type = "drop"
                    else:
                        anomaly_type = "drift"
            
            result = AnomalyResult(
                metric_name=metric_name,
                timestamp=timestamp,
                value=value,
                expected_value=mean,
                deviation=deviation,
                deviation_std=deviation_std,
                is_anomaly=is_anomaly,
                anomaly_type=anomaly_type if is_anomaly else "normal"
            )
            
            # Notify callbacks
            if is_anomaly:
                for callback in self._callbacks:
                    try:
                        callback(result)
                    except Exception as e:
                        logger.error(f"Anomaly callback error: {e}")
            
            return result
    
    def detect_zscore(
        self,
        metric_name: str,
        value: float,
        threshold: float = 3.0
    ) -> Optional[AnomalyResult]:
        """Detect using z-score method"""
        return self.detect(metric_name, value)
    
    def detect_percentile(
        self,
        metric_name: str,
        value: float,
        low_percentile: float = 5,
        high_percentile: float = 95
    ) -> bool:
        """Detect using percentile method"""
        with self._lock:
            if metric_name not in self._metrics or len(self._metrics[metric_name]) < 10:
                return False
            
            values = sorted(self._metrics[metric_name])
            n = len(values)
            
            low_idx = int(n * low_percentile / 100)
            high_idx = int(n * high_percentile / 100)
            
            low_threshold = values[low_idx]
            high_threshold = values[high_idx]
            
            return value < low_threshold or value > high_threshold
    
    def detect_change(
        self,
        metric_name: str,
        value: float,
        change_threshold: float = 0.5
    ) -> bool:
        """Detect sudden changes"""
        with self._lock:
            if metric_name not in self._metrics or len(self._metrics[metric_name]) < 2:
                return False
            
            values = list(self._metrics[metric_name])
            last_value = values[-1]
            
            if last_value == 0:
                return False
            
            change_ratio = abs(value - last_value) / abs(last_value)
            return change_ratio > change_threshold
    
    def subscribe(self, callback: Callable[[AnomalyResult], None]) -> None:
        """Subscribe to anomaly notifications"""
        self._callbacks.append(callback)
    
    def get_statistics(self, metric_name: str) -> Dict[str, float]:
        """Get current statistics for a metric"""
        with self._lock:
            if metric_name not in self._metrics or len(self._metrics[metric_name]) < 2:
                return {}
            
            values = list(self._metrics[metric_name])
            n = len(values)
            
            mean = sum(values) / n
            variance = sum((x - mean) ** 2 for x in values) / n
            std = math.sqrt(variance)
            
            sorted_values = sorted(values)
            
            return {
                "count": n,
                "mean": mean,
                "std": std,
                "min": min(values),
                "max": max(values),
                "p5": sorted_values[int(n * 0.05)],
                "p25": sorted_values[int(n * 0.25)],
                "p50": sorted_values[int(n * 0.50)],
                "p75": sorted_values[int(n * 0.75)],
                "p95": sorted_values[int(n * 0.95)],
            }


# Global anomaly detector instance
anomaly_detector = AnomalyDetector()
