"""
Playback Controller
=================

Transport controls and playback speed management.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class PlaybackSpeed(Enum):
    """Predefined playback speeds"""
    QUARTER = 0.25
    HALF = 0.5
    NORMAL = 1.0
    DOUBLE = 2.0
    QUADRUPLE = 4.0
    TEN_X = 10.0
    HUNDRED_X = 100.0
    THOUSAND_X = 1000.0
    MAX = 5000.0


class TransportState(Enum):
    """Transport state"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"


@dataclass
class Bookmark:
    """Event bookmark"""
    bookmark_id: str
    timestamp: datetime
    position: int
    description: str
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bookmark_id": self.bookmark_id,
            "timestamp": self.timestamp.isoformat(),
            "position": self.position,
            "description": self.description,
            "category": self.category,
            "tags": self.tags
        }


@dataclass
class TimelineAnnotation:
    """Timeline annotation"""
    annotation_id: str
    timestamp: datetime
    position: int
    text: str
    author: str = "system"
    category: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "annotation_id": self.annotation_id,
            "timestamp": self.timestamp.isoformat(),
            "position": self.position,
            "text": self.text,
            "author": self.author,
            "category": self.category,
            "metadata": self.metadata
        }


class PlaybackController:
    """
    Controls replay playback with transport-like interface.
    
    Features:
    - Play/pause/stop
    - Speed control (0.25x to 5000x)
    - Frame-by-frame stepping
    - Jump to bookmark
    - Timeline scrubbing
    """
    
    def __init__(
        self,
        engine: Any,
        on_state_change: Optional[Callable] = None,
        on_position_change: Optional[Callable] = None
    ):
        self.engine = engine
        self.on_state_change = on_state_change
        self.on_position_change = on_position_change
        
        # State
        self.state = TransportState.STOPPED
        self.current_speed = 1.0
        self.is_looping = False
        self.loop_start: Optional[datetime] = None
        self.loop_end: Optional[datetime] = None
        
        # Bookmarks
        self.bookmarks: Dict[str, Bookmark] = {}
        
        # Annotations
        self.annotations: Dict[str, TimelineAnnotation] = {}
        
        # Thread
        self._play_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Callbacks
        self._position_callbacks: List[Callable] = []
        self._event_callbacks: Dict[str, List[Callable]] = {}
    
    def play(self) -> None:
        """Start or resume playback"""
        if self.state == TransportState.PLAYING:
            return
        
        self.state = TransportState.PLAYING
        self.engine.play()
        
        # Start playback thread
        self._stop_event.clear()
        self._play_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._play_thread.start()
        
        self._notify_state_change()
        logger.info(f"Playback started at speed {self.current_speed}x")
    
    def pause(self) -> None:
        """Pause playback"""
        if self.state != TransportState.PLAYING:
            return
        
        self.state = TransportState.PAUSED
        self.engine.pause()
        
        if self._play_thread:
            self._stop_event.set()
            self._play_thread = None
        
        self._notify_state_change()
        logger.info("Playback paused")
    
    def stop(self) -> None:
        """Stop playback and reset to beginning"""
        self.pause()
        self.engine.stop()
        self.state = TransportState.STOPPED
        self._notify_state_change()
        logger.info("Playback stopped")
    
    def _playback_loop(self) -> None:
        """Main playback loop"""
        while not self._stop_event.is_set():
            # Calculate delay based on speed
            if self.engine.current_time:
                # Determine how fast to advance
                delay = 0.001 / self.current_speed  # Base tick
            else:
                delay = 0.01
            
            # Step through events
            event = self.engine.step_forward()
            
            if event:
                self._notify_position_change()
                self._dispatch_event(event)
            else:
                # End of session
                if not self.is_looping:
                    self.stop()
                    break
                else:
                    # Loop
                    if self.loop_start:
                        self.engine.jump_to(self.loop_start)
                    else:
                        self.engine.jump_to_start()
            
            self._stop_event.wait(delay)
    
    def step_forward(self, frames: int = 1) -> None:
        """Step forward by frames"""
        for _ in range(frames):
            event = self.engine.step_forward()
            if event:
                self._dispatch_event(event)
        self._notify_position_change()
    
    def step_backward(self, frames: int = 1) -> None:
        """Step backward by frames"""
        for _ in range(frames):
            self.engine.step_backward()
        self._notify_position_change()
    
    def set_speed(self, speed: float) -> None:
        """Set playback speed"""
        self.current_speed = max(0.25, min(speed, 5000.0))
        self.engine.set_speed(self.current_speed)
        logger.info(f"Playback speed set to {self.current_speed}x")
    
    def set_speed_preset(self, preset: PlaybackSpeed) -> None:
        """Set predefined speed"""
        self.set_speed(preset.value)
    
    def jump_to(self, timestamp: datetime) -> None:
        """Jump to timestamp"""
        self.engine.jump_to(timestamp)
        self._notify_position_change()
    
    def jump_to_bookmark(self, bookmark_id: str) -> None:
        """Jump to bookmark"""
        bookmark = self.bookmarks.get(bookmark_id)
        if bookmark:
            self.engine.position = bookmark.position
            self.engine.current_time = bookmark.timestamp
            self._notify_position_change()
            logger.info(f"Jumped to bookmark: {bookmark.description}")
    
    def jump_to_start(self) -> None:
        """Jump to session start"""
        self.engine.jump_to_start()
        self._notify_position_change()
    
    def jump_to_end(self) -> None:
        """Jump to session end"""
        self.engine.jump_to_end()
        self._notify_position_change()
    
    def set_loop(self, start: datetime = None, end: datetime = None) -> None:
        """Set loop region"""
        self.loop_start = start
        self.loop_end = end
        self.is_looping = start is not None
        logger.info(f"Loop set: {start} to {end}")
    
    def clear_loop(self) -> None:
        """Clear loop"""
        self.loop_start = None
        self.loop_end = None
        self.is_looping = False
    
    def add_bookmark(
        self,
        timestamp: datetime,
        description: str,
        category: str = "general",
        tags: List[str] = None
    ) -> Bookmark:
        """Add bookmark at timestamp"""
        bookmark = Bookmark(
            bookmark_id=str(uuid4()),
            timestamp=timestamp,
            position=self.engine.position,
            description=description,
            category=category,
            tags=tags or []
        )
        
        self.bookmarks[bookmark.bookmark_id] = bookmark
        logger.info(f"Added bookmark: {description}")
        
        return bookmark
    
    def remove_bookmark(self, bookmark_id: str) -> bool:
        """Remove bookmark"""
        if bookmark_id in self.bookmarks:
            del self.bookmarks[bookmark_id]
            return True
        return False
    
    def get_bookmarks(self, category: str = None) -> List[Bookmark]:
        """Get bookmarks, optionally filtered by category"""
        if category:
            return [b for b in self.bookmarks.values() if b.category == category]
        return list(self.bookmarks.values())
    
    def add_annotation(
        self,
        timestamp: datetime,
        text: str,
        author: str = "system",
        category: str = "general",
        metadata: Dict[str, Any] = None
    ) -> TimelineAnnotation:
        """Add annotation at timestamp"""
        annotation = TimelineAnnotation(
            annotation_id=str(uuid4()),
            timestamp=timestamp,
            position=self.engine.position,
            text=text,
            author=author,
            category=category,
            metadata=metadata or {}
        )
        
        self.annotations[annotation.annotation_id] = annotation
        logger.info(f"Added annotation: {text[:50]}...")
        
        return annotation
    
    def remove_annotation(self, annotation_id: str) -> bool:
        """Remove annotation"""
        if annotation_id in self.annotations:
            del self.annotations[annotation_id]
            return True
        return False
    
    def get_annotations(
        self,
        start: datetime = None,
        end: datetime = None,
        category: str = None
    ) -> List[TimelineAnnotation]:
        """Get annotations, optionally filtered"""
        annotations = list(self.annotations.values())
        
        if start:
            annotations = [a for a in annotations if a.timestamp >= start]
        if end:
            annotations = [a for a in annotations if a.timestamp <= end]
        if category:
            annotations = [a for a in annotations if a.category == category]
        
        return sorted(annotations, key=lambda a: a.timestamp)
    
    def register_position_callback(self, callback: Callable) -> None:
        """Register position change callback"""
        self._position_callbacks.append(callback)
    
    def register_event_callback(
        self,
        event_type: str,
        callback: Callable
    ) -> None:
        """Register event callback"""
        if event_type not in self._event_callbacks:
            self._event_callbacks[event_type] = []
        self._event_callbacks[event_type].append(callback)
    
    def _notify_state_change(self) -> None:
        """Notify state change"""
        if self.on_state_change:
            self.on_state_change(self.state)
        
        for callback in self._position_callbacks:
            try:
                callback(self._get_state())
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def _notify_position_change(self) -> None:
        """Notify position change"""
        state = self._get_state()
        
        for callback in self._position_callbacks:
            try:
                callback(state)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def _dispatch_event(self, event) -> None:
        """Dispatch event to registered callbacks"""
        event_type = event.event_type.value
        
        for callback in self._event_callbacks.get(event_type, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")
        
        # Also dispatch to wildcard callbacks
        for callback in self._event_callbacks.get("*", []):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")
    
    def _get_state(self) -> Dict[str, Any]:
        """Get current state"""
        engine_state = self.engine.get_state()
        
        return {
            "transport_state": self.state.value,
            "speed": self.current_speed,
            "position": engine_state.get("position", 0),
            "total_events": engine_state.get("total_events", 0),
            "progress": engine_state.get("progress", 0.0),
            "current_time": engine_state.get("current_time"),
            "is_looping": self.is_looping,
            "loop_start": self.loop_start.isoformat() if self.loop_start else None,
            "loop_end": self.loop_end.isoformat() if self.loop_end else None,
            "bookmark_count": len(self.bookmarks),
            "annotation_count": len(self.annotations)
        }
    
    def get_state(self) -> Dict[str, Any]:
        """Get complete state"""
        return self._get_state()
