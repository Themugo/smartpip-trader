"""
Layer 1 — Perception
====================

Ingests and validates incoming market data, detects missing or delayed data,
and estimates data quality.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


class DataQuality(Enum):
    """Data quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNUSABLE = "unusable"


class DataAnomaly(Enum):
    """Types of data anomalies"""
    NONE = "none"
    MISSING_DATA = "missing_data"
    DELAYED_DATA = "delayed_data"
    STALE_PRICE = "stale_price"
    SPIKE_DETECTED = "spike_detected"
    GAPS_DETECTED = "gaps_detected"
    VOLATILITY_SPIKE = "volatility_spike"


@dataclass
class TickData:
    """Market tick data"""
    symbol: str
    timestamp: datetime
    bid: float
    ask: float
    volume: float = 0.0
    
    @property
    def mid_price(self) -> float:
        return (self.bid + self.ask) / 2
    
    @property
    def spread(self) -> float:
        return self.ask - self.bid


@dataclass
class PerceptionResult:
    """Result from perception layer"""
    session_id: str
    timestamp: datetime
    current_tick: Optional[TickData]
    recent_ticks: List[TickData]
    quality: DataQuality
    anomalies: List[DataAnomaly]
    quality_score: float  # 0-1
    latency_ms: float
    missing_ticks_count: int
    is_valid: bool
    confidence: float  # Confidence in the data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "current_tick": {
                "symbol": self.current_tick.symbol,
                "bid": self.current_tick.bid,
                "ask": self.current_tick.ask,
                "mid": self.current_tick.mid_price,
                "spread": self.current_tick.spread
            } if self.current_tick else None,
            "quality": self.quality.value,
            "anomalies": [a.value for a in self.anomalies],
            "quality_score": self.quality_score,
            "latency_ms": self.latency_ms,
            "missing_ticks": self.missing_ticks_count,
            "is_valid": self.is_valid,
            "confidence": self.confidence
        }


class PerceptionLayer:
    """
    Layer 1: Perception
    
    Responsible for:
    - Ingesting and validating market data
    - Detecting missing or delayed data
    - Estimating data quality
    """
    
    def __init__(
        self,
        expected_ticks_per_second: float = 1.0,
        max_latency_ms: float = 500.0,
        spike_threshold_std: float = 3.0,
        quality_thresholds: Optional[Dict[str, float]] = None
    ):
        self.expected_ticks_per_second = expected_ticks_per_second
        self.max_latency_ms = max_latency_ms
        self.spike_threshold_std = spike_threshold_std
        self.quality_thresholds = quality_thresholds or {
            "excellent": 0.95,
            "good": 0.85,
            "fair": 0.70,
            "poor": 0.50
        }
        
        self._tick_buffer: List[TickData] = []
        self._buffer_size = 100
        self._last_processed_time: Optional[datetime] = None
        self._session_id = str(uuid4())
        
    def process(self, raw_data: Dict[str, Any]) -> PerceptionResult:
        """
        Process incoming market data through perception layer.
        
        Args:
            raw_data: Raw market data from data source
            
        Returns:
            PerceptionResult with validated data and quality assessment
        """
        start_time = time.time()
        
        # Extract tick data
        tick = self._extract_tick(raw_data)
        
        # Update buffer
        self._update_buffer(tick)
        
        # Validate data
        anomalies = self._detect_anomalies()
        
        # Calculate quality
        quality, quality_score = self._assess_quality(tick, anomalies)
        
        # Calculate confidence
        confidence = self._calculate_confidence(quality_score, anomalies)
        
        # Determine if data is valid for trading
        is_valid = quality != DataQuality.UNUSABLE and len(anomalies) == 0
        
        # If there are anomalies but quality is still acceptable, data may still be valid
        if anomalies and all(a in [DataAnomaly.MISSING_DATA, DataAnomaly.DELAYED_DATA] for a in anomalies):
            is_valid = quality_score >= 0.7
        
        latency_ms = (time.time() - start_time) * 1000
        self._last_processed_time = datetime.now()
        
        result = PerceptionResult(
            session_id=self._session_id,
            timestamp=datetime.now(),
            current_tick=tick,
            recent_ticks=self._tick_buffer.copy(),
            quality=quality,
            anomalies=anomalies,
            quality_score=quality_score,
            latency_ms=latency_ms,
            missing_ticks_count=self._count_missing_ticks(),
            is_valid=is_valid,
            confidence=confidence,
            metadata={
                "buffer_size": len(self._tick_buffer),
                "expected_ticks": self.expected_ticks_per_second
            }
        )
        
        logger.debug(f"Perception: quality={quality.value}, confidence={confidence:.2f}")
        return result
    
    def _extract_tick(self, raw_data: Dict[str, Any]) -> Optional[TickData]:
        """Extract tick data from raw input"""
        try:
            symbol = raw_data.get("symbol", raw_data.get("symbol", "UNKNOWN"))
            timestamp_str = raw_data.get("timestamp")
            bid = float(raw_data.get("bid", raw_data.get("price", 0)))
            ask = float(raw_data.get("ask", raw_data.get("price", bid)))
            volume = float(raw_data.get("volume", 0))
            
            if timestamp_str:
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    timestamp = timestamp_str
            else:
                timestamp = datetime.now()
            
            return TickData(
                symbol=symbol,
                timestamp=timestamp,
                bid=bid,
                ask=ask,
                volume=volume
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to extract tick data: {e}")
            return None
    
    def _update_buffer(self, tick: Optional[TickData]) -> None:
        """Update tick buffer with new data"""
        if tick:
            self._tick_buffer.append(tick)
            if len(self._tick_buffer) > self._buffer_size:
                self._tick_buffer.pop(0)
    
    def _detect_anomalies(self) -> List[DataAnomaly]:
        """Detect anomalies in the current data stream"""
        anomalies = []
        
        if not self._tick_buffer:
            anomalies.append(DataAnomaly.MISSING_DATA)
            return anomalies
        
        # Check for missing data (gaps in time)
        if self._last_processed_time:
            time_diff = (datetime.now() - self._last_processed_time).total_seconds()
            expected_interval = 1.0 / self.expected_ticks_per_second
            if time_diff > expected_interval * 5:  # 5x expected interval
                anomalies.append(DataAnomaly.MISSING_DATA)
        
        # Check for delayed data
        if len(self._tick_buffer) >= 2:
            last_tick = self._tick_buffer[-1]
            if last_tick.timestamp:
                age_ms = (datetime.now() - last_tick.timestamp).total_seconds() * 1000
                if age_ms > self.max_latency_ms:
                    anomalies.append(DataAnomaly.DELAYED_DATA)
        
        # Check for stale price (no change for extended period)
        if len(self._tick_buffer) >= 10:
            recent_prices = [t.mid_price for t in self._tick_buffer[-10:]]
            if len(set(recent_prices)) == 1:
                anomalies.append(DataAnomaly.STALE_PRICE)
        
        # Check for price spikes
        if len(self._tick_buffer) >= 20:
            prices = np.array([t.mid_price for t in self._tick_buffer])
            mean = np.mean(prices)
            std = np.std(prices)
            if std > 0 and abs(prices[-1] - mean) / std > self.spike_threshold_std:
                anomalies.append(DataAnomaly.SPIKE_DETECTED)
        
        # Check for gaps in price (unusual jumps)
        if len(self._tick_buffer) >= 5:
            returns = []
            for i in range(1, min(5, len(self._tick_buffer))):
                prev = self._tick_buffer[-i-1].mid_price
                curr = self._tick_buffer[-i].mid_price
                if prev > 0:
                    returns.append(abs((curr - prev) / prev))
            
            if returns and max(returns) > 0.05:  # 5% jump
                anomalies.append(DataAnomaly.GAPS_DETECTED)
        
        return anomalies
    
    def _assess_quality(self, tick: Optional[TickData], anomalies: List[DataAnomaly]) -> Tuple[DataQuality, float]:
        """Assess data quality based on tick and anomalies"""
        base_score = 1.0
        
        if not tick:
            return DataQuality.UNUSABLE, 0.0
        
        # Penalize for anomalies
        anomaly_penalties = {
            DataAnomaly.NONE: 0.0,
            DataAnomaly.MISSING_DATA: 0.3,
            DataAnomaly.DELAYED_DATA: 0.2,
            DataAnomaly.STALE_PRICE: 0.25,
            DataAnomaly.SPIKE_DETECTED: 0.4,
            DataAnomaly.GAPS_DETECTED: 0.35,
            DataAnomaly.VOLATILITY_SPIKE: 0.3
        }
        
        total_penalty = sum(anomaly_penalties.get(a, 0.1) for a in anomalies)
        quality_score = max(0.0, base_score - total_penalty)
        
        # Check spread quality
        if tick.spread > 0:
            relative_spread = tick.spread / tick.mid_price
            if relative_spread > 0.01:  # >1% spread is poor
                quality_score *= 0.8
        
        # Map score to quality
        if quality_score >= self.quality_thresholds["excellent"]:
            quality = DataQuality.EXCELLENT
        elif quality_score >= self.quality_thresholds["good"]:
            quality = DataQuality.GOOD
        elif quality_score >= self.quality_thresholds["fair"]:
            quality = DataQuality.FAIR
        elif quality_score >= self.quality_thresholds["poor"]:
            quality = DataQuality.POOR
        else:
            quality = DataQuality.UNUSABLE
        
        return quality, quality_score
    
    def _calculate_confidence(self, quality_score: float, anomalies: List[DataAnomaly]) -> float:
        """Calculate confidence in the perceived data"""
        confidence = quality_score
        
        # Reduce confidence for each anomaly type
        for anomaly in anomalies:
            if anomaly == DataAnomaly.MISSING_DATA:
                confidence *= 0.7
            elif anomaly == DataAnomaly.DELAYED_DATA:
                confidence *= 0.85
            elif anomaly == DataAnomaly.STALE_PRICE:
                confidence *= 0.8
            elif anomaly == DataAnomaly.SPIKE_DETECTED:
                confidence *= 0.5
            elif anomaly == DataAnomaly.GAPS_DETECTED:
                confidence *= 0.6
        
        return max(0.0, min(1.0, confidence))
    
    def _count_missing_ticks(self) -> int:
        """Count potentially missing ticks in recent history"""
        if not self._tick_buffer or not self._last_processed_time:
            return 0
        
        expected_count = int((datetime.now() - self._last_processed_time).total_seconds() * self.expected_ticks_per_second)
        actual_count = len(self._tick_buffer)
        
        return max(0, expected_count - actual_count)
    
    def reset(self) -> None:
        """Reset perception state"""
        self._tick_buffer.clear()
        self._last_processed_time = None
        self._session_id = str(uuid4())
        logger.info("Perception layer reset")
