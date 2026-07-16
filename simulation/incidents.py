"""
Incident Replay System
====================

Records and replays production incidents for testing.
"""

import time
import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Incident:
    """A recorded production incident"""
    incident_id: str
    name: str
    description: str
    start_time: float
    end_time: float
    severity: str  # low, medium, high, critical
    
    # What happened
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Environment context
    environment: Dict[str, Any] = field(default_factory=dict)
    
    # Resolution
    root_cause: str = ""
    resolution: str = ""
    resolved_at: Optional[float] = None
    
    def duration_seconds(self) -> float:
        """Get incident duration"""
        return self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "name": self.name,
            "description": self.description,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds(),
            "severity": self.severity,
            "events": self.events,
            "environment": self.environment,
            "root_cause": self.root_cause,
            "resolution": self.resolution,
            "resolved_at": self.resolved_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Incident":
        """Create incident from dict"""
        return cls(
            incident_id=data["incident_id"],
            name=data["name"],
            description=data["description"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            severity=data["severity"],
            events=data.get("events", []),
            environment=data.get("environment", {}),
            root_cause=data.get("root_cause", ""),
            resolution=data.get("resolution", ""),
            resolved_at=data.get("resolved_at"),
        )


class IncidentRecorder:
    """
    Records incidents from production for later replay.
    """
    
    def __init__(self, storage_path: str = "./incidents"):
        self.storage_path = storage_path
        self._current_incident: Optional[Incident] = None
        self._event_buffer: List[Dict[str, Any]] = []
        self._is_recording = False
        os.makedirs(storage_path, exist_ok=True)
    
    def start_recording(self, incident_id: str, name: str, description: str, severity: str = "medium") -> None:
        """Start recording a new incident"""
        if self._is_recording:
            self.stop_recording()  # Stop any existing recording
        
        self._current_incident = Incident(
            incident_id=incident_id,
            name=name,
            description=description,
            start_time=time.time(),
            end_time=0,  # Will be set when stopped
            severity=severity,
        )
        self._event_buffer = []
        self._is_recording = True
        logger.info(f"Started recording incident: {name}")
    
    def record_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Record an event during the incident"""
        if not self._is_recording:
            return
        
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "data": data,
        }
        self._event_buffer.append(event)
    
    def record_error(self, error_type: str, message: str, context: Dict[str, Any]) -> None:
        """Record an error event"""
        self.record_event("error", {
            "error_type": error_type,
            "message": message,
            "context": context,
        })
    
    def record_failure(self, component: str, reason: str, details: Dict[str, Any]) -> None:
        """Record a failure event"""
        self.record_event("failure", {
            "component": component,
            "reason": reason,
            "details": details,
        })
    
    def record_recovery(self, component: str, method: str) -> None:
        """Record a recovery event"""
        self.record_event("recovery", {
            "component": component,
            "method": method,
        })
    
    def capture_environment(self, env: Dict[str, Any]) -> None:
        """Capture environment context"""
        if self._current_incident:
            self._current_incident.environment = env
    
    def stop_recording(self, root_cause: str = "", resolution: str = "") -> Optional[Incident]:
        """Stop recording and save the incident"""
        if not self._is_recording or not self._current_incident:
            return None
        
        self._current_incident.end_time = time.time()
        self._current_incident.events = self._event_buffer.copy()
        self._current_incident.root_cause = root_cause
        self._current_incident.resolution = resolution
        self._current_incident.resolved_at = time.time()
        
        # Save to file
        self._save_incident(self._current_incident)
        
        logger.info(f"Stopped recording incident: {self._current_incident.name}")
        
        incident = self._current_incident
        self._current_incident = None
        self._is_recording = False
        
        return incident
    
    def cancel_recording(self) -> None:
        """Cancel the current recording"""
        self._current_incident = None
        self._event_buffer = []
        self._is_recording = False
    
    def _save_incident(self, incident: Incident) -> None:
        """Save incident to file"""
        filepath = os.path.join(self.storage_path, f"{incident.incident_id}.json")
        with open(filepath, "w") as f:
            json.dump(incident.to_dict(), f, indent=2)
    
    def load_incident(self, incident_id: str) -> Optional[Incident]:
        """Load an incident from file"""
        filepath = os.path.join(self.storage_path, f"{incident_id}.json")
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, "r") as f:
            data = json.load(f)
        
        return Incident.from_dict(data)
    
    def list_incidents(self) -> List[Dict[str, Any]]:
        """List all recorded incidents"""
        incidents = []
        for filename in os.listdir(self.storage_path):
            if filename.endswith(".json"):
                filepath = os.path.join(self.storage_path, filename)
                with open(filepath, "r") as f:
                    data = json.load(f)
                incidents.append({
                    "incident_id": data["incident_id"],
                    "name": data["name"],
                    "severity": data["severity"],
                    "start_time": data["start_time"],
                    "duration_seconds": data["end_time"] - data["start_time"],
                })
        
        return sorted(incidents, key=lambda x: x["start_time"], reverse=True)
    
    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self._is_recording


class IncidentReplayer:
    """
    Replays recorded incidents for testing.
    """
    
    def __init__(self, recorder: IncidentRecorder):
        self.recorder = recorder
        self._playback_speed = 1.0  # 1.0 = real-time
        self._is_playing = False
        self._event_callbacks: List[Callable] = []
        self._failure_injector = None  # Will be set if available
    
    def set_playback_speed(self, speed: float) -> None:
        """Set playback speed multiplier"""
        self._playback_speed = max(0.1, min(100.0, speed))
    
    def set_failure_injector(self, injector) -> None:
        """Set failure injector for incident replay"""
        self._failure_injector = injector
    
    def on_event(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register event callback"""
        self._event_callbacks.append(callback)
    
    def replay(
        self,
        incident: Incident,
        failure_injector: Optional[Any] = None,
        on_progress: Optional[Callable[[float], None]] = None
    ) -> Dict[str, Any]:
        """
        Replay an incident.
        
        Args:
            incident: Incident to replay
            failure_injector: Failure injector to use
            on_progress: Progress callback
            
        Returns:
            Replay results
        """
        injector = failure_injector or self._failure_injector
        self._is_playing = True
        
        results = {
            "incident_id": incident.incident_id,
            "events_replayed": 0,
            "failures_injected": 0,
            "duration_seconds": 0,
            "success": True,
        }
        
        start_time = time.time()
        last_timestamp = incident.start_time
        total_duration = incident.end_time - incident.start_time
        
        for i, event in enumerate(incident.events):
            if not self._is_playing:
                results["success"] = False
                break
            
            # Calculate delay until this event
            event_time = event["timestamp"]
            if i > 0:
                delay = (event_time - last_timestamp) / self._playback_speed
                if delay > 0:
                    time.sleep(delay)
            
            last_timestamp = event_time
            
            # Inject failures if appropriate
            if injector and event["type"] in ["error", "failure"]:
                self._inject_failure_from_event(injector, event)
                results["failures_injected"] += 1
            
            # Trigger callbacks
            for callback in self._event_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Event callback error: {e}")
            
            results["events_replayed"] += 1
            
            # Report progress
            if on_progress:
                progress = (time.time() - start_time) / total_duration
                on_progress(min(1.0, progress))
        
        results["duration_seconds"] = time.time() - start_time
        self._is_playing = False
        
        return results
    
    def _inject_failure_from_event(self, injector, event: Dict[str, Any]) -> None:
        """Inject failure based on event data"""
        from .failures import FailureType
        
        event_type = event.get("type", "")
        data = event.get("data", {})
        
        if event_type == "error":
            error_type = data.get("error_type", "NETWORK_ERROR")
            # Map error types to failure types
            failure_map = {
                "TIMEOUT": FailureType.NETWORK_TIMEOUT,
                "CONNECTION_ERROR": FailureType.NETWORK_ERROR,
                "API_ERROR": FailureType.API_ERROR,
                "RATE_LIMIT": FailureType.RATE_LIMIT,
            }
            failure_type = failure_map.get(error_type, FailureType.API_ERROR)
            injector.inject_failure(failure_type, duration_ms=1000)
        
        elif event_type == "failure":
            component = data.get("component", "")
            reason = data.get("reason", "")
            # Map to appropriate failure type
            if "network" in reason.lower():
                injector.inject_failure(FailureType.NETWORK_ERROR, duration_ms=2000)
            elif "websocket" in reason.lower():
                injector.inject_failure(FailureType.WEBSOCKET_DISCONNECT, duration_ms=3000)
            elif "order" in reason.lower():
                injector.inject_failure(FailureType.ORDER_REJECTED, duration_ms=500)
            elif "data" in reason.lower():
                injector.inject_failure(FailureType.DATA_CORRUPTION, duration_ms=1000)
    
    def stop(self) -> None:
        """Stop replay"""
        self._is_playing = False
    
    @property
    def is_playing(self) -> bool:
        """Check if replaying"""
        return self._is_playing


# Simulated incident templates for testing
class IncidentTemplates:
    """Templates for creating test incidents"""
    
    @staticmethod
    def high_latency() -> Incident:
        """High latency incident"""
        now = time.time()
        events = [
            {
                "type": "observation",
                "timestamp": now,
                "data": {"message": "Latency increasing"}
            },
            {
                "type": "failure",
                "timestamp": now + 5,
                "data": {"component": "execution", "reason": "timeout", "details": {}}
            },
            {
                "type": "error",
                "timestamp": now + 10,
                "data": {"error_type": "TIMEOUT", "message": "Order timeout"}
            },
            {
                "type": "recovery",
                "timestamp": now + 30,
                "data": {"component": "execution", "method": "retry"}
            },
        ]
        
        return Incident(
            incident_id="test_high_latency",
            name="High Latency Incident",
            description="Latency spikes causing order timeouts",
            start_time=now,
            end_time=now + 60,
            severity="high",
            events=events,
            root_cause="Network congestion",
            resolution="Increased timeout values"
        )
    
    @staticmethod
    def websocket_disconnect() -> Incident:
        """WebSocket disconnect incident"""
        now = time.time()
        events = [
            {
                "type": "failure",
                "timestamp": now,
                "data": {"component": "websocket", "reason": "connection_lost"}
            },
            {
                "type": "error",
                "timestamp": now + 1,
                "data": {"error_type": "CONNECTION_ERROR", "message": "WebSocket disconnected"}
            },
            {
                "type": "recovery",
                "timestamp": now + 5,
                "data": {"component": "websocket", "method": "auto_reconnect"}
            },
        ]
        
        return Incident(
            incident_id="test_websocket_disconnect",
            name="WebSocket Disconnect",
            description="WebSocket connection lost during trading",
            start_time=now,
            end_time=now + 30,
            severity="medium",
            events=events,
        )
    
    @staticmethod
    def order_rejections() -> Incident:
        """Order rejection spike"""
        now = time.time()
        events = [
            {
                "type": "failure",
                "timestamp": now + i * 2,
                "data": {"component": "order", "reason": "rejected", "details": {"reason": "RATE_LIMIT"}}
            }
            for i in range(10)
        ]
        
        return Incident(
            incident_id="test_order_rejections",
            name="Order Rejection Spike",
            description="High number of order rejections",
            start_time=now,
            end_time=now + 20,
            severity="high",
            events=events,
            root_cause="Exchange rate limiting",
            resolution="Implemented backoff strategy"
        )
