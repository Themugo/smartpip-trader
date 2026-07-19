"""
Replay Engine - Historical Session Playback

Provides session replay functionality:
- Adjustable playback speeds
- Pause/resume/seek
- Step-by-step analysis
- Equity curve visualization
"""

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Iterator

from timeline.manager import TimelineEvent, TimelineManager, EventType

logger = logging.getLogger(__name__)


class PlaybackState(Enum):
    """Playback state"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"


class PlaybackSpeed(Enum):
    """Playback speed options"""
    SLOW = 0.25
    NORMAL = 1.0
    FAST = 2.0
    VERY_FAST = 4.0
    ULTRA_FAST = 10.0


@dataclass
class ReplayState:
    """Current replay state"""
    session_id: str
    current_index: int = 0
    total_events: int = 0
    playback_state: PlaybackState = PlaybackState.STOPPED
    speed: PlaybackSpeed = PlaybackSpeed.NORMAL
    start_time: Optional[datetime] = None
    current_time: Optional[datetime] = None
    buffer_size: int = 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "current_index": self.current_index,
            "total_events": self.total_events,
            "playback_state": self.playback_state.value,
            "speed": self.speed.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "current_time": self.current_time.isoformat() if self.current_time else None,
            "progress": self.current_index / self.total_events if self.total_events > 0 else 0,
        }


class ReplayEngine:
    """
    Historical session replay engine.
    
    Features:
    - Variable speed playback
    - Pause/resume/seek
    - Event-by-event stepping
    - Playback callbacks
    """
    
    def __init__(
        self,
        timeline_manager: TimelineManager,
        storage_path: str = "data/replay",
    ):
        self._timeline = timeline_manager
        self._storage_path = storage_path
        self._current_state: Optional[ReplayState] = None
        self._events: List[TimelineEvent] = []
        self._playback_task: Optional[asyncio.Task] = None
        self._callbacks: Dict[str, List[Callable]] = {
            "on_event": [],
            "on_state_change": [],
            "on_progress": [],
            "on_complete": [],
        }
    
    def load_session(self, session_id: str) -> bool:
        """Load a session for replay"""
        events = self._timeline.get_session_events(session_id)
        
        if not events:
            logger.warning(f"No events found for session {session_id}")
            return False
        
        self._events = sorted(events, key=lambda e: e.timestamp)
        
        self._current_state = ReplayState(
            session_id=session_id,
            current_index=0,
            total_events=len(self._events),
            playback_state=PlaybackState.STOPPED,
        )
        
        logger.info(f"Loaded session {session_id} with {len(self._events)} events")
        return True
    
    def load_events(self, events: List[TimelineEvent]) -> bool:
        """Load a list of events for replay"""
        if not events:
            return False
        
        self._events = sorted(events, key=lambda e: e.timestamp)
        
        self._current_state = ReplayState(
            session_id="custom",
            current_index=0,
            total_events=len(self._events),
            playback_state=PlaybackState.STOPPED,
        )
        
        return True
    
    def get_state(self) -> Optional[ReplayState]:
        """Get current replay state"""
        return self._current_state
    
    def get_current_event(self) -> Optional[TimelineEvent]:
        """Get the current event being replayed"""
        if not self._current_state or not self._events:
            return None
        
        if self._current_state.current_index >= len(self._events):
            return None
        
        return self._events[self._current_state.current_index]
    
    def get_visible_events(self, window: int = 50) -> List[TimelineEvent]:
        """Get events around the current position"""
        if not self._current_state or not self._events:
            return []
        
        start = max(0, self._current_state.current_index - window // 2)
        end = min(len(self._events), start + window)
        
        return self._events[start:end]
    
    def play(self) -> bool:
        """Start/resume playback"""
        if not self._current_state:
            return False
        
        if self._current_state.playback_state == PlaybackState.PLAYING:
            return True
        
        self._current_state.playback_state = PlaybackState.PLAYING
        self._current_state.start_time = datetime.now(timezone.utc)
        
        # Start playback task
        self._playback_task = asyncio.create_task(self._playback_loop())
        
        self._fire_callback("on_state_change", self._current_state)
        return True
    
    def pause(self) -> bool:
        """Pause playback"""
        if not self._current_state:
            return False
        
        if self._current_state.playback_state != PlaybackState.PLAYING:
            return True
        
        self._current_state.playback_state = PlaybackState.PAUSED
        
        if self._playback_task:
            self._playback_task.cancel()
            self._playback_task = None
        
        self._fire_callback("on_state_change", self._current_state)
        return True
    
    def stop(self) -> bool:
        """Stop playback and reset"""
        if not self._current_state:
            return False
        
        if self._playback_task:
            self._playback_task.cancel()
            self._playback_task = None
        
        self._current_state.playback_state = PlaybackState.STOPPED
        self._current_state.current_index = 0
        
        self._fire_callback("on_state_change", self._current_state)
        return True
    
    def seek(self, index: int) -> bool:
        """Seek to a specific event index"""
        if not self._current_state:
            return False
        
        if index < 0 or index >= len(self._events):
            return False
        
        self._current_state.current_index = index
        self._current_state.current_time = self._events[index].timestamp
        
        self._fire_callback("on_progress", self._current_state)
        self._fire_callback("on_event", self._events[index])
        
        return True
    
    def seek_to_time(self, timestamp: datetime) -> bool:
        """Seek to a specific timestamp"""
        if not self._events:
            return False
        
        # Binary search for closest event
        left, right = 0, len(self._events) - 1
        
        while left <= right:
            mid = (left + right) // 2
            if self._events[mid].timestamp < timestamp:
                left = mid + 1
            else:
                right = mid - 1
        
        # Find the closest event
        if left < len(self._events):
            return self.seek(left)
        elif right >= 0:
            return self.seek(right)
        
        return False
    
    def step_forward(self, count: int = 1) -> bool:
        """Step forward by count events"""
        if not self._current_state:
            return False
        
        new_index = min(self._current_state.current_index + count, len(self._events) - 1)
        return self.seek(new_index)
    
    def step_backward(self, count: int = 1) -> bool:
        """Step backward by count events"""
        if not self._current_state:
            return False
        
        new_index = max(self._current_state.current_index - count, 0)
        return self.seek(new_index)
    
    def set_speed(self, speed: PlaybackSpeed) -> bool:
        """Set playback speed"""
        if not self._current_state:
            return False
        
        self._current_state.speed = speed
        self._fire_callback("on_state_change", self._current_state)
        return True
    
    def jump_to_event_type(self, event_type: EventType) -> bool:
        """Jump to the next event of a specific type"""
        if not self._current_state or not self._events:
            return False
        
        for i in range(self._current_state.current_index + 1, len(self._events)):
            if self._events[i].event_type == event_type:
                return self.seek(i)
        
        return False
    
    def get_event_summary(self, event: TimelineEvent) -> Dict[str, Any]:
        """Get a summary of an event for display"""
        summary = {
            "timestamp": event.timestamp.isoformat(),
            "type": event.event_type.value,
            "severity": event.severity.value,
            "message": event.message,
            "source": event.source,
        }
        
        # Add type-specific details
        if event.event_type == EventType.TRADE_EXECUTED:
            summary["details"] = {
                "direction": event.data.get("direction"),
                "amount": event.data.get("amount"),
                "price": event.data.get("price"),
            }
        elif event.event_type == EventType.SIGNAL_GENERATED:
            summary["details"] = {
                "direction": event.data.get("direction"),
                "confidence": event.data.get("confidence"),
                "reason": event.data.get("reason"),
            }
        elif event.event_type == EventType.RISK_REJECTED:
            summary["details"] = {
                "reason": event.data.get("reason"),
                "risk_score": event.data.get("risk_score"),
            }
        
        return summary
    
    def get_equity_snapshots(
        self,
        window: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get equity curve snapshots from trade events"""
        if not self._events:
            return []
        
        equity = 0.0
        snapshots = []
        
        for event in self._events:
            if event.event_type == EventType.TRADE_RESULT:
                profit = event.data.get("profit", 0)
                equity += profit
                
                snapshots.append({
                    "timestamp": event.timestamp.isoformat(),
                    "equity": equity,
                    "profit": profit,
                    "event_id": event.id,
                })
        
        return snapshots[-window:]
    
    def register_callback(
        self,
        event_type: str,
        callback: Callable,
    ) -> None:
        """Register a callback for replay events"""
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
    
    def _fire_callback(self, event_type: str, *args) -> None:
        """Fire registered callbacks"""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"Replay callback error: {e}")
    
    async def _playback_loop(self) -> None:
        """Main playback loop"""
        if not self._current_state:
            return
        
        base_delay = 0.1  # 100ms base delay
        last_update = datetime.now(timezone.utc)
        
        while (
            self._current_state.playback_state == PlaybackState.PLAYING and
            self._current_state.current_index < len(self._events)
        ):
            try:
                # Calculate delay based on speed and event timestamps
                current_event = self._events[self._current_state.current_index]
                
                if self._current_state.current_index + 1 < len(self._events):
                    next_event = self._events[self._current_state.current_index + 1]
                    time_diff = (next_event.timestamp - current_event.timestamp).total_seconds()
                    
                    # Adjust for playback speed
                    delay = min(time_diff / self._current_state.speed.value, 5.0)  # Max 5 seconds
                else:
                    delay = base_delay / self._current_state.speed.value
                
                await asyncio.sleep(delay)
                
                # Move to next event
                self._current_state.current_index += 1
                self._current_state.current_time = current_event.timestamp
                
                # Fire callbacks
                self._fire_callback("on_event", current_event)
                self._fire_callback("on_progress", self._current_state)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Playback error: {e}")
        
        # Check if playback completed
        if self._current_state and self._current_state.current_index >= len(self._events):
            self._current_state.playback_state = PlaybackState.STOPPED
            self._fire_callback("on_complete", self._current_state)
    
    def export_replay_data(self, filepath: str) -> bool:
        """Export replay data to file"""
        import json
        
        if not self._current_state or not self._events:
            return False
        
        data = {
            "session_id": self._current_state.session_id,
            "events": [e.to_dict() for e in self._events],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to export replay data: {e}")
            return False
