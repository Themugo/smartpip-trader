"""
Events Package
==============

Event collection and distribution.
"""

from .event_bus import (
    EventBus,
    Event,
    EventType,
    event_bus,
    emit_opportunity_detected,
    emit_trade_executed,
    emit_risk_alert,
    emit_model_drift,
)

__all__ = [
    "EventBus",
    "Event",
    "EventType",
    "event_bus",
    "emit_opportunity_detected",
    "emit_trade_executed",
    "emit_risk_alert",
    "emit_model_drift",
]
