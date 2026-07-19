"""
Data Pipeline - Market Data Management

Market data collection, processing, and distribution pipeline.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Data source types"""
    DERIV_API = "deriv_api"
    WEB_SOCKET = "web_socket"
    REST_API = "rest_api"
    FILE = "file"
    DATABASE = "database"


class DataType(Enum):
    """Types of market data"""
    TICK = "tick"
    CANDLE = "candle"
    ORDERBOOK = "orderbook"
    TRADE = "trade"
    NEWS = "news"
    FUNDAMENTAL = "fundamental"


@dataclass
class DataFeed:
    """A market data feed"""
    id: str
    name: str
    source: DataSource
    symbols: List[str]
    data_type: DataType
    
    # Status
    is_active: bool = False
    last_update: Optional[datetime] = None
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Statistics
    messages_received: int = 0
    errors: int = 0


@dataclass
class DataTransformer:
    """Data transformation function"""
    name: str
    transform_func: Callable
    input_type: DataType
    output_type: DataType


class DataPipeline:
    """
    Data Pipeline for market data management.
    
    Features:
    - Multi-source data collection
    - Real-time streaming
    - Historical data retrieval
    - Data transformation
    - Data validation
    - Caching
    - Distribution to subscribers
    """
    
    def __init__(self):
        self._feeds: Dict[str, DataFeed] = {}
        self._transformers: Dict[str, DataTransformer] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._data_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._cache_max_size = 10000
    
    def add_feed(
        self,
        name: str,
        source: DataSource,
        symbols: List[str],
        data_type: DataType,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a data feed"""
        feed = DataFeed(
            id=str(uuid.uuid4()),
            name=name,
            source=source,
            symbols=symbols,
            data_type=data_type,
            config=config or {},
        )
        
        self._feeds[feed.id] = feed
        return feed.id
    
    def remove_feed(self, feed_id: str) -> bool:
        """Remove a data feed"""
        if feed_id in self._feeds:
            del self._feeds[feed_id]
            return True
        return False
    
    def start_feed(self, feed_id: str) -> bool:
        """Start a data feed"""
        feed = self._feeds.get(feed_id)
        if not feed:
            return False
        
        feed.is_active = True
        feed.last_update = datetime.now(timezone.utc)
        logger.info(f"Started feed: {feed.name}")
        return True
    
    def stop_feed(self, feed_id: str) -> bool:
        """Stop a data feed"""
        feed = self._feeds.get(feed_id)
        if not feed:
            return False
        
        feed.is_active = False
        logger.info(f"Stopped feed: {feed.name}")
        return True
    
    def add_transformer(
        self,
        name: str,
        transform_func: Callable,
        input_type: DataType,
        output_type: DataType,
    ) -> str:
        """Add a data transformer"""
        transformer = DataTransformer(
            name=name,
            transform_func=transform_func,
            input_type=input_type,
            output_type=output_type,
        )
        
        self._transformers[name] = transformer
        return name
    
    def subscribe(
        self,
        feed_id: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> str:
        """Subscribe to data from a feed"""
        sub_id = str(uuid.uuid4())
        
        if feed_id not in self._subscribers:
            self._subscribers[feed_id] = []
        
        self._subscribers[feed_id].append(callback)
        return sub_id
    
    def unsubscribe(self, feed_id: str, callback: Callable) -> bool:
        """Unsubscribe from a feed"""
        if feed_id in self._subscribers:
            try:
                self._subscribers[feed_id].remove(callback)
                return True
            except ValueError:
                pass
        return False
    
    def receive_data(
        self,
        feed_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Receive data from a feed"""
        feed = self._feeds.get(feed_id)
        if not feed:
            return
        
        feed.messages_received += 1
        feed.last_update = datetime.now(timezone.utc)
        
        # Apply transformers
        transformed_data = self._apply_transformers(feed.data_type, data)
        
        # Cache data
        self._cache_data(feed.symbols[0] if feed.symbols else "unknown", transformed_data)
        
        # Notify subscribers
        self._notify_subscribers(feed_id, transformed_data)
    
    def _apply_transformers(
        self,
        data_type: DataType,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply data transformers"""
        result = data
        
        for transformer in self._transformers.values():
            if transformer.input_type == data_type:
                result = transformer.transform_func(result)
        
        return result
    
    def _cache_data(self, symbol: str, data: Dict[str, Any]) -> None:
        """Cache data for later retrieval"""
        if symbol not in self._data_cache:
            self._data_cache[symbol] = []
        
        self._data_cache[symbol].append({
            **data,
            "cached_at": datetime.now(timezone.utc),
        })
        
        # Enforce cache size limit
        if len(self._data_cache[symbol]) > self._cache_max_size:
            self._data_cache[symbol] = self._data_cache[symbol][-self._cache_max_size:]
    
    def _notify_subscribers(
        self,
        feed_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Notify subscribers of new data"""
        if feed_id in self._subscribers:
            for callback in self._subscribers[feed_id]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Subscriber callback error: {e}")
    
    def get_cached_data(
        self,
        symbol: str,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get cached data for a symbol"""
        data = self._data_cache.get(symbol, [])
        
        if since:
            data = [d for d in data if d.get("timestamp", datetime.min) >= since]
        
        return data[-limit:]
    
    def get_feed_status(self, feed_id: str) -> Optional[Dict[str, Any]]:
        """Get feed status"""
        feed = self._feeds.get(feed_id)
        if not feed:
            return None
        
        return {
            "id": feed.id,
            "name": feed.name,
            "is_active": feed.is_active,
            "last_update": feed.last_update.isoformat() if feed.last_update else None,
            "messages_received": feed.messages_received,
            "errors": feed.errors,
            "symbols": feed.symbols,
        }
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get overall pipeline status"""
        active_feeds = sum(1 for f in self._feeds.values() if f.is_active)
        total_messages = sum(f.messages_received for f in self._feeds.values())
        
        return {
            "total_feeds": len(self._feeds),
            "active_feeds": active_feeds,
            "total_messages": total_messages,
            "cache_size": sum(len(d) for d in self._data_cache.values()),
            "feeds": [
                self.get_feed_status(fid)
                for fid in self._feeds
            ],
        }
