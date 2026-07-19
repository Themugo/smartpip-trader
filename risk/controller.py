"""
Risk Controller

Orchestrates risk management across the trading system.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from collections import deque

from risk.validator import RiskValidator, RiskLimits, RiskCheck, CheckResult, ValidationResult, TradeRequest, AccountSnapshot

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level indicators"""
    LOW = "low"       # Green - All clear
    MEDIUM = "medium" # Yellow - Caution
    HIGH = "high"     # Orange - Warning
    CRITICAL = "critical"  # Red - Block trades
    EMERGENCY = "emergency"  # Full stop


@dataclass
class RiskMetrics:
    """Current risk metrics"""
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    active_positions: int = 0
    total_exposure: float = 0.0
    daily_pnl: float = 0.0
    drawdown: float = 0.0
    consecutive_losses: int = 0
    trades_today: int = 0
    warnings: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "active_positions": self.active_positions,
            "total_exposure": self.total_exposure,
            "daily_pnl": self.daily_pnl,
            "drawdown": self.drawdown,
            "consecutive_losses": self.consecutive_losses,
            "trades_today": self.trades_today,
            "warnings": self.warnings,
            "violations": self.violations,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class RiskEvent:
    """Risk-related event"""
    event_type: str
    severity: RiskLevel
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class RiskController:
    """
    Centralized risk controller managing all risk operations.
    
    Features:
    - Real-time risk monitoring
    - Multi-level alerts
    - Automated position sizing
    - Emergency procedures
    - Risk reporting
    """
    
    def __init__(
        self,
        validator: Optional[RiskValidator] = None,
        limits: Optional[RiskLimits] = None,
    ):
        self._validator = validator or RiskValidator(limits)
        self._metrics = RiskMetrics()
        self._events: deque = deque(maxlen=500)
        self._callbacks: Dict[RiskLevel, List[Callable[[RiskEvent], None]]] = {
            RiskLevel.LOW: [],
            RiskLevel.MEDIUM: [],
            RiskLevel.HIGH: [],
            RiskLevel.CRITICAL: [],
            RiskLevel.EMERGENCY: [],
        }
        self._monitoring_enabled = False
        self._last_account_update: Optional[datetime] = None
        self._current_account: Optional[AccountSnapshot] = None
    
    @property
    def validator(self) -> RiskValidator:
        return self._validator
    
    @property
    def metrics(self) -> RiskMetrics:
        return self._metrics
    
    @property
    def is_trading_allowed(self) -> bool:
        """Check if trading is currently allowed"""
        return self._metrics.risk_level not in (RiskLevel.CRITICAL, RiskLevel.EMERGENCY)
    
    def update_limits(self, limits: Dict[str, Any]) -> None:
        """Update risk limits"""
        self._validator.update_limits(limits)
        logger.info("Risk limits updated")
    
    def update_account(self, account: AccountSnapshot) -> None:
        """Update account state for risk calculations"""
        self._current_account = account
        self._last_account_update = datetime.now(timezone.utc)
        
        # Update metrics
        self._metrics.daily_pnl = account.daily_pnl
        self._metrics.drawdown = account.max_drawdown
        self._metrics.consecutive_losses = account.consecutive_losses
        self._metrics.active_positions = account.open_positions
        self._metrics.total_exposure = account.total_exposure
        self._metrics.last_updated = datetime.now(timezone.utc)
        
        # Check for kill switch conditions
        if self._validator.check_kill_switch_conditions(account):
            self._set_risk_level(RiskLevel.EMERGENCY, "Kill switch triggered")
    
    def register_callback(
        self,
        level: RiskLevel,
        callback: Callable[[RiskEvent], None],
    ) -> None:
        """Register a callback for risk level changes"""
        self._callbacks[level].append(callback)
    
    async def validate_and_execute(
        self,
        request: TradeRequest,
        account: Optional[AccountSnapshot] = None,
    ) -> ValidationResult:
        """
        Validate a trade and update risk metrics.
        
        Args:
            request: Trade request to validate
            account: Current account state (uses cached if not provided)
            
        Returns:
            ValidationResult with decision
        """
        # Use provided or cached account
        if account is None:
            account = self._current_account
            if account is None:
                return ValidationResult(
                    is_valid=False,
                    approved_amount=0,
                    risk_score=100,
                    checks={},
                    errors=["No account information available"],
                    recommendation="BLOCK",
                )
        
        # Validate trade
        result = await self._validator.validate_trade(
            request,
            account,
        )
        
        # Update metrics based on result
        if result.is_valid:
            self._record_successful_validation(request)
        else:
            self._record_failed_validation(request, result)
        
        # Update risk score
        self._update_risk_score(result)
        
        # Fire callbacks
        self._fire_callbacks(result)
        
        return result
    
    def _record_successful_validation(self, request: TradeRequest) -> None:
        """Record a successful validation"""
        self._metrics.trades_today += 1
        self._validator.record_trade(request.amount)
    
    def _record_failed_validation(
        self,
        request: TradeRequest,
        result: ValidationResult,
    ) -> None:
        """Record a failed validation"""
        self._log_risk_event(
            event_type="validation_failed",
            severity=RiskLevel.MEDIUM,
            message=f"Trade validation failed: {request.plugin_id}",
            details={
                "request": request.to_dict(),
                "errors": result.errors,
                "risk_score": result.risk_score,
            },
        )
    
    def _update_risk_score(self, result: ValidationResult) -> None:
        """Update the overall risk score"""
        self._metrics.risk_score = result.risk_score
        
        # Update warnings and violations
        self._metrics.warnings = result.warnings
        self._metrics.violations = result.errors
        
        # Determine risk level
        if result.risk_score >= 90:
            new_level = RiskLevel.EMERGENCY
        elif result.risk_score >= 75:
            new_level = RiskLevel.CRITICAL
        elif result.risk_score >= 50:
            new_level = RiskLevel.HIGH
        elif result.risk_score >= 25:
            new_level = RiskLevel.MEDIUM
        else:
            new_level = RiskLevel.LOW
        
        if new_level != self._metrics.risk_level:
            self._set_risk_level(new_level, f"Risk score: {result.risk_score:.1f}")
    
    def _set_risk_level(self, level: RiskLevel, reason: str) -> None:
        """Set the current risk level"""
        old_level = self._metrics.risk_level
        self._metrics.risk_level = level
        
        self._log_risk_event(
            event_type="risk_level_change",
            severity=level,
            message=f"Risk level changed from {old_level.value} to {level.value}: {reason}",
            details={"old_level": old_level.value, "new_level": level.value},
        )
        
        if level in (RiskLevel.CRITICAL, RiskLevel.EMERGENCY):
            self._log_risk_event(
                event_type="trading_blocked",
                severity=level,
                message="Trading blocked due to high risk level",
            )
    
    def _fire_callbacks(self, result: ValidationResult) -> None:
        """Fire registered callbacks for risk events"""
        for level in RiskLevel:
            if self._metrics.risk_score >= self._get_level_threshold(level):
                for callback in self._callbacks.get(level, []):
                    try:
                        event = RiskEvent(
                            event_type="risk_alert",
                            severity=level,
                            message=f"Risk level: {level.value}",
                            details=result.to_dict(),
                        )
                        callback(event)
                    except Exception as e:
                        logger.error(f"Risk callback error: {e}")
    
    @staticmethod
    def _get_level_threshold(level: RiskLevel) -> float:
        """Get the risk score threshold for a level"""
        thresholds = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 25,
            RiskLevel.HIGH: 50,
            RiskLevel.CRITICAL: 75,
            RiskLevel.EMERGENCY: 90,
        }
        return thresholds.get(level, 0)
    
    def _log_risk_event(
        self,
        event_type: str,
        severity: RiskLevel,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a risk event"""
        event = RiskEvent(
            event_type=event_type,
            severity=severity,
            message=message,
            details=details or {},
        )
        
        self._events.append(event)
        
        # Log to standard logger
        log_func = {
            RiskLevel.LOW: logger.debug,
            RiskLevel.MEDIUM: logger.info,
            RiskLevel.HIGH: logger.warning,
            RiskLevel.CRITICAL: logger.error,
            RiskLevel.EMERGENCY: logger.critical,
        }.get(severity, logger.info)
        
        log_func(f"[{event_type}] {message}")
    
    def get_events(
        self,
        since: Optional[datetime] = None,
        level: Optional[RiskLevel] = None,
        limit: int = 100,
    ) -> List[RiskEvent]:
        """Get recent risk events"""
        events = list(self._events)
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        if level:
            events = [e for e in events if e.severity == level]
        
        return events[-limit:]
    
    def get_risk_report(self) -> Dict[str, Any]:
        """Generate a comprehensive risk report"""
        return {
            "summary": self._metrics.to_dict(),
            "limits": self._validator.limits.to_dict(),
            "kill_switch": self._validator.get_kill_switch_status(),
            "recent_events": [e.to_dict() for e in list(self._events)[-20:]],
            "trading_allowed": self.is_trading_allowed,
            "last_update": self._metrics.last_updated.isoformat(),
        }
    
    def calculate_safe_position_size(
        self,
        account: AccountSnapshot,
        desired_amount: float,
    ) -> float:
        """Calculate the safest position size based on current risk"""
        # Start with desired amount
        amount = desired_amount
        
        # Apply account risk limit
        max_by_risk = account.balance * self._validator.limits.max_account_risk
        amount = min(amount, max_by_risk)
        
        # Apply position size limit
        amount = min(amount, self._validator.limits.max_position_size)
        
        # Ensure minimum
        amount = max(amount, self._validator.limits.min_position_size)
        
        return amount
    
    def emergency_stop(self, reason: str) -> None:
        """Execute emergency stop procedures"""
        logger.critical(f"EMERGENCY STOP: {reason}")
        
        self._log_risk_event(
            event_type="emergency_stop",
            severity=RiskLevel.EMERGENCY,
            message=reason,
        )
        
        # Trigger kill switch
        self._validator.trigger_kill_switch(reason)
        
        # Set emergency level
        self._set_risk_level(RiskLevel.EMERGENCY, reason)
    
    def reset(self) -> None:
        """Reset risk controller state"""
        self._validator.reset_kill_switch()
        self._metrics = RiskMetrics()
        self._events.clear()
        logger.info("Risk controller reset")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state for persistence"""
        return {
            "metrics": self._metrics.to_dict(),
            "limits": self._validator.limits.to_dict(),
            "kill_switch": self._validator.get_kill_switch_status(),
            "is_trading_allowed": self.is_trading_allowed,
            "recent_events_count": len(self._events),
        }


def create_risk_controller(
    limits: Optional[Dict[str, Any]] = None,
) -> RiskController:
    """Factory function to create a risk controller"""
    risk_limits = RiskLimits.from_dict(limits) if limits else None
    validator = RiskValidator(risk_limits)
    return RiskController(validator=validator)
