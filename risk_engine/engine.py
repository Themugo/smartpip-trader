"""
Professional Risk Engine - Portfolio Risk Management

Comprehensive risk management with limits, circuit breakers, and recovery modes.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Trading blocked
    HALF_OPEN = "half_open"  # Testing if recovery possible


@dataclass
class RiskLimits:
    """Risk limits configuration"""
    # Position limits
    max_position_size: float = 1000
    max_total_exposure: float = 10000
    max_single_trade: float = 500
    
    # Loss limits
    max_daily_loss: float = 500
    max_weekly_loss: float = 2000
    max_monthly_loss: float = 5000
    max_drawdown_percent: float = 20
    
    # Exposure limits
    max_correlation: float = 0.7
    max_concentration: float = 0.3  # Max % in single asset
    max_leverage: float = 1.0
    
    # Time limits
    min_trade_interval_seconds: float = 1.0
    max_trades_per_minute: int = 10
    max_trades_per_day: int = 100
    
    # Confidence thresholds
    min_confidence: float = 50
    min_signal_strength: float = 0.3


@dataclass
class Position:
    """A trading position"""
    id: str
    symbol: str
    side: str
    size: float
    entry_price: float
    current_price: float = 0
    pnl: float = 0
    opened_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PortfolioRisk:
    """Current portfolio risk metrics"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Exposure
    total_exposure: float = 0
    net_exposure: float = 0
    gross_exposure: float = 0
    
    # PnL
    daily_pnl: float = 0
    weekly_pnl: float = 0
    monthly_pnl: float = 0
    total_pnl: float = 0
    
    # Drawdown
    current_drawdown: float = 0
    max_drawdown: float = 0
    peak_equity: float = 0
    
    # Risk metrics
    var_95: float = 0  # Value at Risk (95%)
    sharpe_ratio: float = 0
    volatility: float = 0
    
    # Counts
    trades_today: int = 0
    trades_this_week: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_exposure": self.total_exposure,
            "net_exposure": self.net_exposure,
            "daily_pnl": self.daily_pnl,
            "weekly_pnl": self.weekly_pnl,
            "monthly_pnl": self.monthly_pnl,
            "current_drawdown": self.current_drawdown,
            "max_drawdown": self.max_drawdown,
            "trades_today": self.trades_today,
            "win_rate": self.winning_trades / (self.winning_trades + self.losing_trades) if (self.winning_trades + self.losing_trades) > 0 else 0,
        }


@dataclass
class CircuitBreaker:
    """Circuit breaker configuration"""
    name: str
    threshold: float
    period_seconds: int = 60
    triggered_count: int = 0
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    last_triggered: Optional[datetime] = None
    consecutive_breaks: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "threshold": self.threshold,
            "triggered_count": self.triggered_count,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
        }


class RiskEngine:
    """
    Professional Risk Engine for portfolio risk management.
    
    Features:
    - Multi-level risk limits
    - Circuit breakers
    - Recovery mode
    - Adaptive cooldown
    - Correlation monitoring
    - Exposure management
    """
    
    def __init__(
        self,
        limits: Optional[RiskLimits] = None,
    ):
        self._limits = limits or RiskLimits()
        
        # Positions
        self._positions: Dict[str, Position] = {}
        self._position_history: deque = deque(maxlen=10000)
        
        # Equity tracking
        self._equity_history: deque = deque(maxlen=1000)
        self._peak_equity = 0
        self._current_equity = 0
        
        # PnL tracking
        self._daily_pnl = 0
        self._weekly_pnl = 0
        self._monthly_pnl = 0
        self._daily_trades = deque(maxlen=1000)
        
        # Circuit breakers
        self._circuit_breakers: Dict[str, CircuitBreaker] = {
            "daily_loss": CircuitBreaker("daily_loss", self._limits.max_daily_loss, period_seconds=86400),
            "drawdown": CircuitBreaker("drawdown", self._limits.max_drawdown_percent, period_seconds=3600),
            "trade_frequency": CircuitBreaker("trade_frequency", self._limits.max_trades_per_minute, period_seconds=60),
            "exposure": CircuitBreaker("exposure", self._limits.max_total_exposure, period_seconds=300),
        }
        
        # State
        self._risk_level = RiskLevel.LOW
        self._recovery_mode = False
        self._cooldown_until: Optional[datetime] = None
        self._kill_switch_active = False
        
        # Callbacks
        self._risk_callbacks: List[Callable] = []
        
        self._logger = logging.getLogger(f"{__name__}.Risk")
    
    def set_limits(self, limits: RiskLimits) -> None:
        """Update risk limits"""
        self._limits = limits
    
    def add_position(self, position: Position) -> None:
        """Add a position"""
        self._positions[position.id] = position
        self._position_history.append(position)
    
    def remove_position(self, position_id: str) -> Optional[Position]:
        """Remove a position"""
        if position_id in self._positions:
            position = self._positions.pop(position_id)
            return position
        return None
    
    def update_position_prices(self, prices: Dict[str, float]) -> None:
        """Update position current prices"""
        for position in self._positions.values():
            if position.symbol in prices:
                position.current_price = prices[position.symbol]
                position.pnl = (position.current_price - position.entry_price) * position.size
    
    def validate_trade(
        self,
        symbol: str,
        side: str,
        amount: float,
        confidence: float,
        signal_strength: float,
    ) -> tuple[bool, str, RiskLevel]:
        """
        Validate a trade against risk limits.
        
        Returns:
            (approved, reason, risk_level)
        """
        # Check kill switch
        if self._kill_switch_active:
            return False, "Kill switch active", RiskLevel.CRITICAL
        
        # Check cooldown
        if self._cooldown_until and datetime.utcnow() < self._cooldown_until:
            remaining = (self._cooldown_until - datetime.utcnow()).total_seconds()
            return False, f"In cooldown ({remaining:.0f}s remaining)", self._risk_level
        
        # Check circuit breakers
        for name, breaker in self._circuit_breakers.items():
            if breaker.state == CircuitBreakerState.OPEN:
                return False, f"Circuit breaker open: {name}", RiskLevel.CRITICAL
        
        # Check position size
        if amount > self._limits.max_single_trade:
            return False, f"Trade size {amount} exceeds limit {self._limits.max_single_trade}", RiskLevel.HIGH
        
        # Check total exposure
        current_exposure = self.get_total_exposure()
        new_exposure = current_exposure + amount
        
        if new_exposure > self._limits.max_total_exposure:
            return False, f"Total exposure would exceed limit", RiskLevel.HIGH
        
        # Check daily loss limit
        if self._daily_pnl <= -self._limits.max_daily_loss:
            self._trigger_circuit_breaker("daily_loss")
            return False, "Daily loss limit reached", RiskLevel.CRITICAL
        
        # Check drawdown
        if self._current_equity > 0:
            current_drawdown = (self._peak_equity - self._current_equity) / self._peak_equity * 100
            
            if current_drawdown > self._limits.max_drawdown_percent:
                self._trigger_circuit_breaker("drawdown")
                return False, "Maximum drawdown exceeded", RiskLevel.CRITICAL
        
        # Check confidence threshold
        if confidence < self._limits.min_confidence:
            return False, f"Confidence {confidence:.1f} below threshold {self._limits.min_confidence}", RiskLevel.MEDIUM
        
        # Check signal strength
        if abs(signal_strength) < self._limits.min_signal_strength:
            return False, f"Signal strength {signal_strength:.2f} below threshold", RiskLevel.MEDIUM
        
        # Calculate risk level
        risk_level = self._calculate_risk_level(symbol, amount)
        
        # Add cooldown if risk is high
        if risk_level == RiskLevel.HIGH:
            self._cooldown_until = datetime.utcnow() + timedelta(seconds=5)
        
        return True, "Trade approved", risk_level
    
    def _calculate_risk_level(self, symbol: str, amount: float) -> RiskLevel:
        """Calculate current risk level"""
        # Check exposure
        exposure_ratio = self.get_total_exposure() / self._limits.max_total_exposure
        
        if exposure_ratio > 0.9:
            return RiskLevel.CRITICAL
        elif exposure_ratio > 0.7:
            return RiskLevel.HIGH
        elif exposure_ratio > 0.5:
            return RiskLevel.MEDIUM
        
        return RiskLevel.LOW
    
    def _trigger_circuit_breaker(self, name: str) -> None:
        """Trigger a circuit breaker"""
        if name not in self._circuit_breakers:
            return
        
        breaker = self._circuit_breakers[name]
        breaker.state = CircuitBreakerState.OPEN
        breaker.triggered_count += 1
        breaker.last_triggered = datetime.utcnow()
        breaker.consecutive_breaks += 1
        
        self._logger.warning(f"Circuit breaker triggered: {name}")
        
        # If too many consecutive breaks, activate kill switch
        if breaker.consecutive_breaks >= 3:
            self.activate_kill_switch(f"Multiple {name} circuit breaker trips")
    
    def reset_circuit_breaker(self, name: str) -> None:
        """Reset a circuit breaker to closed state"""
        if name in self._circuit_breakers:
            breaker = self._circuit_breakers[name]
            breaker.state = CircuitBreakerState.CLOSED
            breaker.consecutive_breaks = 0
            self._logger.info(f"Circuit breaker reset: {name}")
    
    def activate_kill_switch(self, reason: str) -> None:
        """Activate the kill switch"""
        self._kill_switch_active = True
        self._risk_level = RiskLevel.CRITICAL
        
        self._logger.critical(f"KILL SWITCH ACTIVATED: {reason}")
        
        # Fire callbacks
        for callback in self._risk_callbacks:
            try:
                callback({"type": "kill_switch", "reason": reason})
            except Exception as e:
                self._logger.error(f"Risk callback error: {e}")
    
    def deactivate_kill_switch(self) -> None:
        """Deactivate the kill switch"""
        self._kill_switch_active = False
        self._logger.info("Kill switch deactivated")
        
        # Reset all circuit breakers
        for breaker in self._circuit_breakers.values():
            breaker.state = CircuitBreakerState.CLOSED
    
    def enter_recovery_mode(self, duration_seconds: int = 300) -> None:
        """Enter recovery mode with reduced risk"""
        self._recovery_mode = True
        self._cooldown_until = datetime.utcnow() + timedelta(seconds=duration_seconds)
        
        self._logger.warning(f"Entered recovery mode for {duration_seconds}s")
    
    def exit_recovery_mode(self) -> None:
        """Exit recovery mode"""
        self._recovery_mode = False
        self._logger.info("Exited recovery mode")
    
    def record_trade_result(self, pnl: float, is_win: bool) -> None:
        """Record a trade result for tracking"""
        self._daily_pnl += pnl
        self._weekly_pnl += pnl
        self._monthly_pnl += pnl
        
        trade_record = {
            "timestamp": datetime.utcnow(),
            "pnl": pnl,
            "is_win": is_win,
        }
        self._daily_trades.append(trade_record)
    
    def update_equity(self, equity: float) -> None:
        """Update current equity"""
        self._current_equity = equity
        
        if equity > self._peak_equity:
            self._peak_equity = equity
        
        self._equity_history.append({
            "timestamp": datetime.utcnow(),
            "equity": equity,
        })
        
        # Update drawdown
        if self._peak_equity > 0:
            current_drawdown = (self._peak_equity - equity) / self._peak_equity * 100
            if current_drawdown > self.get_portfolio_risk().max_drawdown:
                self.get_portfolio_risk().max_drawdown = current_drawdown
    
    def get_total_exposure(self) -> float:
        """Get total position exposure"""
        return sum(p.size * p.current_price for p in self._positions.values())
    
    def get_portfolio_risk(self) -> PortfolioRisk:
        """Get current portfolio risk metrics"""
        risk = PortfolioRisk(timestamp=datetime.utcnow())
        
        risk.total_exposure = self.get_total_exposure()
        risk.daily_pnl = self._daily_pnl
        risk.weekly_pnl = self._weekly_pnl
        risk.monthly_pnl = self._monthly_pnl
        
        risk.peak_equity = self._peak_equity
        risk.current_drawdown = (
            (self._peak_equity - self._current_equity) / self._peak_equity * 100
            if self._peak_equity > 0 else 0
        )
        risk.max_drawdown = risk.current_drawdown
        
        # Trade counts
        today = datetime.utcnow().date()
        risk.trades_today = sum(
            1 for t in self._daily_trades
            if t["timestamp"].date() == today
        )
        
        wins = sum(1 for t in self._daily_trades if t["is_win"])
        losses = sum(1 for t in self._daily_trades if not t["is_win"])
        risk.winning_trades = wins
        risk.losing_trades = losses
        
        return risk
    
    def get_positions(self) -> List[Position]:
        """Get all open positions"""
        return list(self._positions.values())
    
    def get_circuit_breakers(self) -> Dict[str, CircuitBreaker]:
        """Get circuit breaker status"""
        return self._circuit_breakers
    
    def on_risk_event(self, callback: Callable) -> None:
        """Register a risk event callback"""
        self._risk_callbacks.append(callback)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current risk engine state"""
        return {
            "risk_level": self._risk_level.value,
            "kill_switch_active": self._kill_switch_active,
            "recovery_mode": self._recovery_mode,
            "cooldown_until": self._cooldown_until.isoformat() if self._cooldown_until else None,
            "daily_pnl": self._daily_pnl,
            "total_exposure": self.get_total_exposure(),
            "current_drawdown": self.get_portfolio_risk().current_drawdown,
            "circuit_breakers": {
                name: cb.to_dict()
                for name, cb in self._circuit_breakers.items()
            },
        }
