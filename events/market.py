"""
Market Events
=============

Events related to market data and feature calculations.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .core import Event, EventType, EventMetadata


@dataclass
class MarketTickEvent(Event):
    """Market tick event - single price update"""
    
    def __init__(
        self,
        symbol: str,
        price: float,
        volume: float,
        bid: float,
        ask: float,
        timestamp: float,
        exchange: str = "",
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "symbol": symbol,
            "price": price,
            "volume": volume,
            "bid": bid,
            "ask": ask,
            "spread": ask - bid if bid and ask else 0,
            "exchange": exchange,
            "tick_time": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
        metadata.event_type = EventType.MARKET_TICK
        
        super().__init__(
            event_type=EventType.MARKET_TICK,
            metadata=metadata,
            payload=payload,
        )


@dataclass
class MarketSnapshotEvent(Event):
    """Market snapshot event - complete market state"""
    
    def __init__(
        self,
        symbol: str,
        best_bid: float,
        best_ask: float,
        last_price: float,
        volume: float,
        timestamp: float,
        high: float = 0,
        low: float = 0,
        open_price: float = 0,
        close_price: float = 0,
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "symbol": symbol,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "last_price": last_price,
            "volume": volume,
            "high": high,
            "low": low,
            "open": open_price,
            "close": close_price,
            "snapshot_time": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
        
        super().__init__(
            event_type=EventType.MARKET_SNAPSHOT,
            metadata=metadata,
            payload=payload,
        )


@dataclass  
class FeatureCalculationEvent(Event):
    """Feature calculation event - computed features"""
    
    def __init__(
        self,
        symbol: str,
        features: Dict[str, float],
        feature_version: str,
        timestamp: float,
        calculation_time_ms: float = 0,
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "symbol": symbol,
            "features": features,
            "feature_version": feature_version,
            "calculation_time_ms": calculation_time_ms,
            "feature_count": len(features),
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
            metadata.feature_version = feature_version
        
        super().__init__(
            event_type=EventType.FEATURE_CALCULATION,
            metadata=metadata,
            payload=payload,
        )
