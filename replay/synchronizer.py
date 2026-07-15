"""
Event Synchronizer
================

Synchronizes different event types during replay.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class SyncChannel:
    """A synchronization channel for a specific event type"""
    name: str
    event_type: str
    events: List[Any] = field(default_factory=list)
    position: int = 0
    callbacks: List[Callable] = field(default_factory=list)
    
    def add_event(self, event: Any) -> None:
        """Add event to channel"""
        self.events.append(event)
    
    def seek(self, position: int) -> None:
        """Seek to position"""
        self.position = max(0, min(position, len(self.events) - 1))
    
    def get_current(self) -> Optional[Any]:
        """Get current event"""
        if 0 <= self.position < len(self.events):
            return self.events[self.position]
        return None
    
    def step_forward(self) -> Optional[Any]:
        """Step to next event"""
        if self.position < len(self.events) - 1:
            self.position += 1
            return self.events[self.position]
        return None
    
    def step_backward(self) -> Optional[Any]:
        """Step to previous event"""
        if self.position > 0:
            self.position -= 1
            return self.events[self.position]
        return None


@dataclass
class SyncPoint:
    """A synchronized point across all channels"""
    timestamp: datetime
    frame: int
    events: Dict[str, Any]  # channel_name -> event


class EventSynchronizer:
    """
    Synchronizes different event types during replay.
    
    Allows replaying:
    - Market data
    - Strategy decisions
    - AI confidence
    - Risk checks
    - Trade execution
    - Dashboard updates
    - Plugin events
    """
    
    def __init__(self):
        self.channels: Dict[str, SyncChannel] = {}
        self._current_frame = 0
        self._total_frames = 0
        self._is_synchronized = False
        
        # Timeline
        self.timeline: List[SyncPoint] = []
        self._timeline_index = 0
        
        # Callbacks
        self._sync_callbacks: List[Callable] = []
    
    def add_channel(self, name: str, event_type: str) -> SyncChannel:
        """Add a synchronization channel"""
        channel = SyncChannel(name=name, event_type=event_type)
        self.channels[name] = channel
        logger.info(f"Added sync channel: {name}")
        return channel
    
    def add_event_to_channel(
        self,
        channel_name: str,
        event: Any,
        timestamp: datetime = None
    ) -> None:
        """Add event to channel"""
        if channel_name not in self.channels:
            self.add_channel(channel_name, event.event_type.value)
        
        self.channels[channel_name].add_event(event)
        
        # Update timeline
        if timestamp:
            self._update_timeline(channel_name, event, timestamp)
    
    def _update_timeline(
        self,
        channel_name: str,
        event: Any,
        timestamp: datetime
    ) -> None:
        """Update synchronized timeline"""
        # Find or create sync point for timestamp
        sync_point = None
        for sp in self.timeline:
            if abs((sp.timestamp - timestamp).total_seconds()) < 0.001:
                sync_point = sp
                break
        
        if sync_point is None:
            sync_point = SyncPoint(
                timestamp=timestamp,
                frame=len(self.timeline),
                events={}
            )
            self.timeline.append(sync_point)
        
        sync_point.events[channel_name] = event
        self._total_frames = len(self.timeline)
    
    def build_timeline(self, events: List[Any]) -> None:
        """
        Build synchronized timeline from events.
        
        Groups events by timestamp for synchronized playback.
        """
        # Group events by timestamp
        timestamp_groups: Dict[datetime, Dict[str, Any]] = {}
        
        for event in events:
            ts = event.timestamp
            if ts not in timestamp_groups:
                timestamp_groups[ts] = {}
            
            channel = self._get_channel_for_event_type(event.event_type.value)
            timestamp_groups[ts][channel] = event
        
        # Build timeline
        self.timeline = []
        for ts in sorted(timestamp_groups.keys()):
            sync_point = SyncPoint(
                timestamp=ts,
                frame=len(self.timeline),
                events=timestamp_groups[ts]
            )
            self.timeline.append(sync_point)
        
        self._total_frames = len(self.timeline)
        self._is_synchronized = True
        
        logger.info(f"Built timeline with {self._total_frames} frames")
    
    def _get_channel_for_event_type(self, event_type: str) -> str:
        """Get channel name for event type"""
        channel_map = {
            "tick": "market_data",
            "ohlcv": "market_data",
            "orderbook": "market_data",
            "strategy_decision": "strategy",
            "signal_generated": "strategy",
            "parameter_update": "strategy",
            "ai_confidence": "ai",
            "ai_reasoning": "ai",
            "ai_recommendation": "ai",
            "risk_check": "risk",
            "risk_limit_hit": "risk",
            "trade_entry": "execution",
            "trade_exit": "execution",
            "order_placed": "execution",
            "order_filled": "execution",
            "order_cancelled": "execution",
            "dashboard_update": "dashboard",
            "metric_recorded": "dashboard",
            "plugin_event": "plugins"
        }
        return channel_map.get(event_type, "other")
    
    def get_current_frame(self) -> Optional[SyncPoint]:
        """Get current frame"""
        if 0 <= self._timeline_index < len(self.timeline):
            return self.timeline[self._timeline_index]
        return None
    
    def step_forward(self) -> Optional[SyncPoint]:
        """Step to next synchronized frame"""
        if self._timeline_index < len(self.timeline) - 1:
            self._timeline_index += 1
            frame = self.timeline[self._timeline_index]
            self._notify_sync(frame)
            return frame
        return None
    
    def step_backward(self) -> Optional[SyncPoint]:
        """Step to previous synchronized frame"""
        if self._timeline_index > 0:
            self._timeline_index -= 1
            frame = self.timeline[self._timeline_index]
            self._notify_sync(frame)
            return frame
        return None
    
    def seek_to_frame(self, frame: int) -> Optional[SyncPoint]:
        """Seek to specific frame"""
        if 0 <= frame < len(self.timeline):
            self._timeline_index = frame
            frame = self.timeline[self._timeline_index]
            self._notify_sync(frame)
            return frame
        return None
    
    def seek_to_timestamp(self, timestamp: datetime) -> Optional[SyncPoint]:
        """Seek to timestamp"""
        # Binary search
        left, right = 0, len(self.timeline) - 1
        result = None
        
        while left <= right:
            mid = (left + right) // 2
            ts = self.timeline[mid].timestamp
            
            if ts <= timestamp:
                result = mid
                left = mid + 1
            else:
                right = mid - 1
        
        if result is not None:
            return self.seek_to_frame(result)
        return None
    
    def seek_to_event(self, channel: str, event_id: str) -> Optional[SyncPoint]:
        """Seek to specific event"""
        for i, frame in enumerate(self.timeline):
            if channel in frame.events:
                event = frame.events[channel]
                if hasattr(event, 'event_id') and event.event_id == event_id:
                    return self.seek_to_frame(i)
        return None
    
    def get_frame_range(
        self,
        start: datetime,
        end: datetime
    ) -> List[SyncPoint]:
        """Get frames in time range"""
        frames = []
        for frame in self.timeline:
            if start <= frame.timestamp <= end:
                frames.append(frame)
        return frames
    
    def get_events_by_channel(
        self,
        channel: str,
        start: datetime = None,
        end: datetime = None
    ) -> List[Any]:
        """Get events for specific channel"""
        events = []
        for frame in self.timeline:
            if start and frame.timestamp < start:
                continue
            if end and frame.timestamp > end:
                break
            if channel in frame.events:
                events.append(frame.events[channel])
        return events
    
    def register_sync_callback(self, callback: Callable) -> None:
        """Register callback for synchronized playback"""
        self._sync_callbacks.append(callback)
    
    def _notify_sync(self, frame: SyncPoint) -> None:
        """Notify sync callbacks"""
        for callback in self._sync_callbacks:
            try:
                callback(frame)
            except Exception as e:
                logger.error(f"Sync callback error: {e}")
    
    def get_progress(self) -> float:
        """Get playback progress"""
        if self._total_frames == 0:
            return 0.0
        return self._timeline_index / self._total_frames
    
    def get_state(self) -> Dict[str, Any]:
        """Get synchronizer state"""
        current = self.get_current_frame()
        
        return {
            "current_frame": self._timeline_index,
            "total_frames": self._total_frames,
            "progress": self.get_progress(),
            "current_timestamp": current.timestamp.isoformat() if current else None,
            "channels": list(self.channels.keys()),
            "is_synchronized": self._is_synchronized,
            "events_per_channel": {
                name: len(ch.events)
                for name, ch in self.channels.items()
            }
        }
    
    def reset(self) -> None:
        """Reset to beginning"""
        self._timeline_index = 0
        for channel in self.channels.values():
            channel.position = 0
    
    def clear(self) -> None:
        """Clear all data"""
        self.channels.clear()
        self.timeline.clear()
        self._current_frame = 0
        self._total_frames = 0
        self._is_synchronized = False


@dataclass
class DisplayMetrics:
    """Metrics to display during replay"""
    current_regime: str = "unknown"
    confidence: float = 0.0
    opportunity_score: float = 0.0
    analyzer_votes: Dict[str, bool] = field(default_factory=dict)
    risk_status: str = "OK"
    execution_delay_ms: float = 0.0
    expected_value: float = 0.0
    historical_similarity: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.current_regime,
            "confidence": self.confidence,
            "opportunity_score": self.opportunity_score,
            "analyzer_votes": self.analyzer_votes,
            "risk_status": self.risk_status,
            "execution_delay_ms": self.execution_delay_ms,
            "expected_value": self.expected_value,
            "historical_similarity": self.historical_similarity,
            "timestamp": self.timestamp.isoformat()
        }


class DisplaySynchronizer:
    """
    Synchronizes display metrics with replay.
    """
    
    def __init__(self, synchronizer: EventSynchronizer):
        self.synchronizer = synchronizer
        self.current_metrics = DisplayMetrics()
        
        # History
        self.metrics_history: List[DisplayMetrics] = []
        
        # Register for sync updates
        self.synchronizer.register_sync_callback(self._on_sync)
    
    def _on_sync(self, frame) -> None:
        """Handle sync frame update"""
        self.current_metrics = DisplayMetrics()
        self.current_metrics.timestamp = frame.timestamp
        
        # Extract metrics from frame events
        for channel, event in frame.events.items():
            self._extract_metrics(channel, event)
        
        self.metrics_history.append(self.current_metrics)
    
    def _extract_metrics(self, channel: str, event) -> None:
        """Extract display metrics from event"""
        if not hasattr(event, 'data'):
            return
        
        data = event.data
        
        if channel == "market_data":
            if "regime" in data:
                self.current_metrics.current_regime = data["regime"]
        
        elif channel == "ai":
            if "confidence" in data:
                self.current_metrics.confidence = data["confidence"]
            if "opportunity_score" in data:
                self.current_metrics.opportunity_score = data["opportunity_score"]
        
        elif channel == "risk":
            if "status" in data:
                self.current_metrics.risk_status = data["status"]
        
        elif channel == "execution":
            if "delay_ms" in data:
                self.current_metrics.execution_delay_ms = data["delay_ms"]
        
        elif channel == "dashboard":
            if "metrics" in data:
                m = data["metrics"]
                if "expected_value" in m:
                    self.current_metrics.expected_value = m["expected_value"]
                if "historical_similarity" in m:
                    self.current_metrics.historical_similarity = m["historical_similarity"]
    
    def get_current_metrics(self) -> DisplayMetrics:
        """Get current display metrics"""
        return self.current_metrics
    
    def get_metrics_history(
        self,
        start: datetime = None,
        end: datetime = None
    ) -> List[DisplayMetrics]:
        """Get metrics history"""
        history = self.metrics_history
        
        if start:
            history = [m for m in history if m.timestamp >= start]
        if end:
            history = [m for m in history if m.timestamp <= end]
        
        return history
    
    def get_state(self) -> Dict[str, Any]:
        """Get display synchronizer state"""
        return {
            "current_metrics": self.current_metrics.to_dict(),
            "history_length": len(self.metrics_history)
        }
