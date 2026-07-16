"""
Replay SDK
==========

SDK for historical data replay and backtesting.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional

from .base import SmartPipSDK, SDKConfig, SDKLogger

logger = SDKLogger("replay")


@dataclass
class ReplayConfig:
    """Replay configuration"""
    start_time: float
    end_time: float
    speed: float = 1.0  # 1.0 = real-time, 0 = as fast as possible
    symbols: List[str] = field(default_factory=list)
    data_source: str = "memory"  # memory, file, api


@dataclass
class MarketEvent:
    """Market data event"""
    timestamp: float
    event_type: str  # tick, bar, orderbook
    symbol: str
    data: Dict[str, Any]


@dataclass
class ReplayState:
    """Replay state"""
    current_time: float
    progress: float  # 0.0 - 1.0
    events_processed: int
    current_bar: Optional[Dict[str, Any]] = None


class ReplayEngine(SmartPipSDK):
    """
    Historical data replay engine.
    """
    
    def __init__(self, config: Optional[SDKConfig] = None):
        super().__init__(config)
        self._data: List[MarketEvent] = []
        self._replay_config: Optional[ReplayConfig] = None
        self._current_index = 0
        self._is_playing = False
        self._subscribers: List[Callable] = []
    
    def load_data(self, data: List[MarketEvent]) -> None:
        """Load market data for replay"""
        self._data = sorted(data, key=lambda x: x.timestamp)
        logger.info(f"Loaded {len(data)} events")
    
    def load_from_file(self, filepath: str) -> None:
        """Load data from file"""
        import json
        with open(filepath, "r") as f:
            data_dict = json.load(f)
        
        events = [MarketEvent(**e) for e in data_dict]
        self.load_data(events)
    
    def start(self, replay_config: ReplayConfig) -> None:
        """Start replay"""
        self._replay_config = replay_config
        self._current_index = 0
        self._is_playing = True
        logger.info(f"Replay started: {replay_config.start_time} - {replay_config.end_time}")
    
    def stop(self) -> None:
        """Stop replay"""
        self._is_playing = False
        logger.info("Replay stopped")
    
    def pause(self) -> None:
        """Pause replay"""
        self._is_playing = False
        logger.info("Replay paused")
    
    def resume(self) -> None:
        """Resume replay"""
        self._is_playing = True
        logger.info("Replay resumed")
    
    def seek(self, timestamp: float) -> None:
        """Seek to timestamp"""
        for i, event in enumerate(self._data):
            if event.timestamp >= timestamp:
                self._current_index = i
                break
    
    def next(self) -> Optional[MarketEvent]:
        """Get next event"""
        if self._current_index >= len(self._data):
            return None
        
        event = self._data[self._current_index]
        self._current_index += 1
        
        # Notify subscribers
        for subscriber in self._subscribers:
            try:
                subscriber(event)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")
        
        return event
    
    def iterate(self) -> Iterator[MarketEvent]:
        """Iterate through events"""
        while self._current_index < len(self._data):
            if not self._is_playing:
                break
            yield self.next()
    
    def get_state(self) -> ReplayState:
        """Get current replay state"""
        total = len(self._data)
        current = self._current_index
        
        progress = current / total if total > 0 else 0
        
        current_time = 0
        if self._current_index < len(self._data):
            current_time = self._data[self._current_index].timestamp
        
        return ReplayState(
            current_time=current_time,
            progress=progress,
            events_processed=current,
            current_bar=self._data[self._current_index - 1].data if self._current_index > 0 else None
        )
    
    def subscribe(self, callback: Callable[[MarketEvent], None]) -> None:
        """Subscribe to market events"""
        self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe from market events"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    @property
    def is_playing(self) -> bool:
        """Check if replay is playing"""
        return self._is_playing
    
    @property
    def current_time(self) -> float:
        """Get current replay time"""
        if self._current_index < len(self._data):
            return self._data[self._current_index].timestamp
        return 0
