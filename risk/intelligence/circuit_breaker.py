"""
Circuit Breakers & Kill Switches
================================

Automated trading pauses and emergency stop mechanisms.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class BreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Tripped, no trading
    HALF_OPEN = "half_open"  # Testing if conditions improved


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    daily_loss_threshold: float = 0.05  # 5% daily loss
    hourly_loss_threshold: float = 0.03  # 3% hourly loss
    consecutive_losses: int = 5  # Number of consecutive losses
    volatility_spike_threshold: float = 2.0  # Multiples of normal vol
    auto_reset_timeout: int = 300  # 5 minutes
    max_trips_per_hour: int = 3


@dataclass
class CircuitBreakerTrip:
    """Record of circuit breaker trip"""
    id: str
    timestamp: datetime
    trigger_type: str
    triggered_at: float  # Loss amount or value
    reset_at: Optional[datetime]
    auto_reset: bool
    reason: str


@dataclass
class KillSwitchConfig:
    """Kill switch configuration"""
    max_drawdown: float = 0.15  # 15% drawdown
    max_daily_loss: float = 0.10  # 10% daily loss
    max_consecutive_losses: int = 10
    require_manual_reset: bool = True
    notify_on_trigger: bool = True


class CircuitBreaker:
    """
    Circuit breaker that pauses trading when thresholds are exceeded.
    """
    
    def __init__(self, limits: Any):
        self.config = CircuitBreakerConfig()
        
        # State
        self.state = BreakerState.CLOSED
        self.trip_count_today = 0
        self.last_trip_time: Optional[datetime] = None
        self.trips: List[CircuitBreakerTrip] = []
        
        # Counters
        self.consecutive_losses = 0
        self.hourly_losses: List[float] = []
    
    def is_tripped(self) -> bool:
        """Check if circuit breaker is tripped"""
        if self.state == BreakerState.OPEN:
            # Check if should auto-reset
            if self._should_auto_reset():
                self._auto_reset()
            return True
        return False
    
    def trip(
        self,
        trigger_type: str,
        triggered_at: float,
        reason: str = ""
    ) -> None:
        """Trip the circuit breaker"""
        self.state = BreakerState.OPEN
        self.trip_count_today += 1
        self.last_trip_time = datetime.now()
        
        trip = CircuitBreakerTrip(
            id=str(uuid4()),
            timestamp=datetime.now(),
            trigger_type=trigger_type,
            triggered_at=triggered_at,
            reset_at=None,
            auto_reset=self.config.auto_reset_timeout > 0,
            reason=reason
        )
        self.trips.append(trip)
        
        logger.warning(f"Circuit breaker TRIPPED: {trigger_type} at {triggered_at}")
    
    def reset(self, manual: bool = True) -> None:
        """Reset the circuit breaker"""
        if self.trips:
            self.trips[-1].reset_at = datetime.now()
        
        self.state = BreakerState.CLOSED
        logger.info("Circuit breaker reset")
    
    def check(
        self,
        daily_loss: float,
        hourly_loss: float,
        volatility_ratio: float,
        consecutive_loss: bool
    ) -> tuple[bool, str]:
        """
        Check if circuit breaker should trip.
        
        Returns:
            Tuple of (should_trip, reason)
        """
        # Check daily loss
        if daily_loss <= -self.config.daily_loss_threshold:
            return True, f"Daily loss {abs(daily_loss):.1%} exceeds threshold"
        
        # Check hourly loss
        if hourly_loss <= -self.config.hourly_loss_threshold:
            return True, f"Hourly loss {abs(hourly_loss):.1%} exceeds threshold"
        
        # Check consecutive losses
        if consecutive_loss:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.config.consecutive_losses:
                return True, f"{self.consecutive_losses} consecutive losses"
        else:
            self.consecutive_losses = 0
        
        # Check volatility
        if volatility_ratio > self.config.volatility_spike_threshold:
            return True, f"Volatility spike {volatility_ratio:.1f}x normal"
        
        # Check trip count
        if self.trip_count_today >= self.config.max_trips_per_hour:
            return True, f"Too many trips ({self.trip_count_today}) in short period"
        
        return False, ""
    
    def _should_auto_reset(self) -> bool:
        """Check if should auto-reset"""
        if not self.trips:
            return False
        
        last_trip = self.trips[-1]
        if not last_trip.auto_reset:
            return False
        
        if self.last_trip_time:
            elapsed = (datetime.now() - self.last_trip_time).total_seconds()
            return elapsed >= self.config.auto_reset_timeout
        
        return False
    
    def _auto_reset(self) -> None:
        """Auto reset the breaker"""
        self.state = BreakerState.HALF_OPEN
        
        # Will fully reset on next successful check
        logger.info("Circuit breaker auto-reset to HALF_OPEN")
    
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state"""
        return {
            "state": self.state.value,
            "trip_count_today": self.trip_count_today,
            "consecutive_losses": self.consecutive_losses,
            "last_trip": self.trips[-1].__dict__ if self.trips else None,
            "should_auto_reset": self._should_auto_reset()
        }
    
    def reset_daily_counters(self) -> None:
        """Reset daily counters (call at start of trading day)"""
        self.trip_count_today = 0


class KillSwitch:
    """
    Kill switch for emergency trading stop.
    """
    
    def __init__(self, limits: Any):
        self.config = KillSwitchConfig()
        
        self.is_triggered = False
        self.trigger_time: Optional[datetime] = None
        self.trigger_reason: Optional[str] = None
        self.trigger_value: Optional[float] = None
    
    def trigger(
        self,
        reason: str,
        drawdown: float = 0.0,
        daily_loss: float = 0.0,
        consecutive_losses: int = 0
    ) -> None:
        """Trigger the kill switch"""
        self.is_triggered = True
        self.trigger_time = datetime.now()
        self.trigger_reason = reason
        self.trigger_value = drawdown if reason == "drawdown" else daily_loss
        
        logger.critical(f"KILL SWITCH TRIGGERED: {reason}")
        
        if self.config.notify_on_trigger:
            self._send_notification()
    
    def check(
        self,
        current_drawdown: float,
        daily_loss: float,
        consecutive_losses: int
    ) -> tuple[bool, str]:
        """
        Check if kill switch should trigger.
        
        Returns:
            Tuple of (should_trigger, reason)
        """
        if self.is_triggered:
            return False, "Already triggered"
        
        # Check drawdown
        if current_drawdown >= self.config.max_drawdown:
            return True, f"Drawdown {current_drawdown:.1%} exceeds limit"
        
        # Check daily loss
        if daily_loss <= -self.config.max_daily_loss:
            return True, f"Daily loss {abs(daily_loss):.1%} exceeds limit"
        
        # Check consecutive losses
        if consecutive_losses >= self.config.max_consecutive_losses:
            return True, f"{consecutive_losses} consecutive losses"
        
        return False, ""
    
    def reset(self) -> bool:
        """Reset kill switch (requires manual intervention)"""
        if self.config.require_manual_reset and self.is_triggered:
            logger.warning("Kill switch requires manual reset")
            return False
        
        self.is_triggered = False
        self.trigger_time = None
        self.trigger_reason = None
        self.trigger_value = None
        
        logger.info("Kill switch reset")
        return True
    
    def get_state(self) -> Dict[str, Any]:
        """Get kill switch state"""
        return {
            "is_triggered": self.is_triggered,
            "trigger_time": self.trigger_time.isoformat() if self.trigger_time else None,
            "trigger_reason": self.trigger_reason,
            "trigger_value": self.trigger_value,
            "require_manual_reset": self.config.require_manual_reset
        }
    
    def _send_notification(self) -> None:
        """Send kill switch notification"""
        # Would integrate with notification system
        logger.critical(f"KILL SWITCH ALERT: {self.trigger_reason} at {self.trigger_value}")
