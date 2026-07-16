"""
System Events
=============

Events related to system operations and health.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .core import Event, EventType, EventMetadata


@dataclass
class ConfigurationChangeEvent(Event):
    """Configuration change event"""
    
    def __init__(
        self,
        config_key: str,
        old_value: Any,
        new_value: Any,
        changed_by: str,
        reason: str,
        timestamp: float,
        config_version: str = "",
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "config_key": config_key,
            "old_value": str(old_value),
            "new_value": str(new_value),
            "changed_by": changed_by,
            "reason": reason,
            "config_version": config_version,
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
            metadata.configuration_version = config_version
        
        super().__init__(
            event_type=EventType.CONFIGURATION_CHANGE,
            metadata=metadata,
            payload=payload,
        )


@dataclass
class PluginEvent(Event):
    """Plugin lifecycle event"""
    
    def __init__(
        self,
        plugin_name: str,
        plugin_version: str,
        event_action: str,  # loaded, unloaded, error, updated
        timestamp: float,
        details: str = "",
        error: str = "",
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "plugin_name": plugin_name,
            "plugin_version": plugin_version,
            "event_action": event_action,
            "details": details,
            "error": error,
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
        
        super().__init__(
            event_type=EventType.PLUGIN_EVENT,
            metadata=metadata,
            payload=payload,
        )


@dataclass
class SystemAlertEvent(Event):
    """System alert event"""
    
    def __init__(
        self,
        alert_type: str,  # warning, error, critical
        source: str,
        message: str,
        timestamp: float,
        alert_code: str = "",
        affected_components: List[str] = None,
        resolved: bool = False,
        resolution: str = "",
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "alert_type": alert_type,
            "source": source,
            "message": message,
            "alert_code": alert_code,
            "affected_components": affected_components or [],
            "resolved": resolved,
            "resolution": resolution,
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
        
        super().__init__(
            event_type=EventType.SYSTEM_ALERT,
            metadata=metadata,
            payload=payload,
        )


@dataclass
class HealthEvent(Event):
    """Health check event"""
    
    def __init__(
        self,
        component: str,
        status: str,  # healthy, degraded, unhealthy
        checks: Dict[str, Any],
        timestamp: float,
        response_time_ms: float = 0,
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "component": component,
            "status": status,
            "checks": checks,
            "response_time_ms": response_time_ms,
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
        
        super().__init__(
            event_type=EventType.HEALTH_EVENT,
            metadata=metadata,
            payload=payload,
        )
