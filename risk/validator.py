"""
Risk Validator

Comprehensive risk validation for all trading decisions.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import deque

logger = logging.getLogger(__name__)


class RiskCheck(Enum):
    """Types of risk checks"""
    POSITION_SIZE = "position_size"
    ACCOUNT_BALANCE = "account_balance"
    DRAWDOWN = "drawdown"
    EXPOSURE = "exposure"
    CORRELATION = "correlation"
    CONCENTRATION = "concentration"
    VOLATILITY = "volatility"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    DAILY_LOSS = "daily_loss"
    MARGIN = "margin"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class CheckResult(Enum):
    """Result of a risk check"""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    BLOCK = "block"


@dataclass
class RiskLimits:
    """Risk limit configuration"""
    # Position limits
    max_position_size: float = 1000.0
    min_position_size: float = 1.0
    max_positions_per_market: int = 3
    max_total_positions: int = 10
    
    # Account limits
    max_account_risk: float = 0.02  # 2% of account per trade
    max_daily_loss: float = 0.05  # 5% max daily loss
    max_drawdown: float = 0.15  # 15% max drawdown
    min_account_balance: float = 10.0
    
    # Exposure limits
    max_market_exposure: float = 0.20  # 20% per market
    max_correlated_exposure: float = 0.30  # 30% correlated pairs
    max_sector_exposure: float = 0.50  # 50% per sector
    
    # Time limits
    max_trades_per_minute: int = 3
    max_trades_per_hour: int = 30
    cooldown_period: float = 5.0  # seconds between trades
    
    # Streak limits
    max_consecutive_losses: int = 5
    max_consecutive_wins: int = 20
    
    # Kill switch
    kill_switch_enabled: bool = True
    kill_switch_loss_threshold: float = 0.10  # 10%
    kill_switch_loss_count: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_position_size": self.max_position_size,
            "min_position_size": self.min_position_size,
            "max_positions_per_market": self.max_positions_per_market,
            "max_total_positions": self.max_total_positions,
            "max_account_risk": self.max_account_risk,
            "max_daily_loss": self.max_daily_loss,
            "max_drawdown": self.max_drawdown,
            "min_account_balance": self.min_account_balance,
            "max_market_exposure": self.max_market_exposure,
            "max_correlated_exposure": self.max_correlated_exposure,
            "max_sector_exposure": self.max_sector_exposure,
            "max_trades_per_minute": self.max_trades_per_minute,
            "max_trades_per_hour": self.max_trades_per_hour,
            "cooldown_period": self.cooldown_period,
            "max_consecutive_losses": self.max_consecutive_losses,
            "max_consecutive_wins": self.max_consecutive_wins,
            "kill_switch_enabled": self.kill_switch_enabled,
            "kill_switch_loss_threshold": self.kill_switch_loss_threshold,
            "kill_switch_loss_count": self.kill_switch_loss_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskLimits":
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class ValidationResult:
    """Result of risk validation"""
    is_valid: bool
    approved_amount: float
    risk_score: float
    checks: Dict[RiskCheck, Tuple[CheckResult, str]]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    recommendation: str = "EXECUTE"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "approved_amount": self.approved_amount,
            "risk_score": self.risk_score,
            "checks": {
                check.value: {"result": result.value, "message": message}
                for check, (result, message) in self.checks.items()
            },
            "warnings": self.warnings,
            "errors": self.errors,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TradeRequest:
    """Trade request for validation"""
    plugin_id: str
    market: str
    direction: str  # CALL or PUT
    amount: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    contract_type: str = "DIGITAL"
    duration: int = 1
    duration_unit: str = "m"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "market": self.market,
            "direction": self.direction,
            "amount": self.amount,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "contract_type": self.contract_type,
            "duration": self.duration,
            "duration_unit": self.duration_unit,
        }


@dataclass
class AccountSnapshot:
    """Snapshot of account state for risk calculation"""
    balance: float
    equity: float
    currency: str
    open_positions: int = 0
    total_exposure: float = 0.0
    daily_pnl: float = 0.0
    daily_trades: int = 0
    consecutive_losses: int = 0
    consecutive_wins: int = 0
    max_drawdown: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "balance": self.balance,
            "equity": self.equity,
            "currency": self.currency,
            "open_positions": self.open_positions,
            "total_exposure": self.total_exposure,
            "daily_pnl": self.daily_pnl,
            "daily_trades": self.daily_trades,
            "consecutive_losses": self.consecutive_losses,
            "consecutive_wins": self.consecutive_wins,
            "max_drawdown": self.max_drawdown,
            "timestamp": self.timestamp.isoformat(),
        }


class RiskValidator:
    """
    Centralized risk validator for all trading decisions.
    
    Validates:
    - Position sizing against account limits
    - Account balance adequacy
    - Drawdown limits
    - Exposure limits
    - Correlation risk
    - Trading frequency
    - Kill switch conditions
    """
    
    def __init__(self, limits: Optional[RiskLimits] = None):
        self._limits = limits or RiskLimits()
        self._trade_timestamps: deque = deque(maxlen=1000)
        self._daily_trade_timestamps: deque = deque(maxlen=1000)
        self._recent_losses: deque = deque(maxlen=100)
        self._market_positions: Dict[str, int] = {}
        self._kill_switch_triggered = False
        self._kill_switch_reason: Optional[str] = None
    
    @property
    def limits(self) -> RiskLimits:
        return self._limits
    
    @limits.setter
    def limits(self, value: RiskLimits) -> None:
        self._limits = value
    
    def update_limits(self, updates: Dict[str, Any]) -> None:
        """Update risk limits"""
        for key, value in updates.items():
            if hasattr(self._limits, key):
                setattr(self._limits, key, value)
    
    def reset_kill_switch(self) -> None:
        """Reset the kill switch"""
        self._kill_switch_triggered = False
        self._kill_switch_reason = None
        logger.info("Kill switch reset")
    
    def get_kill_switch_status(self) -> Dict[str, Any]:
        """Get kill switch status"""
        return {
            "triggered": self._kill_switch_triggered,
            "reason": self._kill_switch_reason,
            "enabled": self._limits.kill_switch_enabled,
        }
    
    async def validate_trade(
        self,
        request: TradeRequest,
        account: AccountSnapshot,
        market_exposure: float = 0.0,
    ) -> ValidationResult:
        """
        Validate a trade request against all risk rules.
        
        Args:
            request: The trade request to validate
            account: Current account snapshot
            market_exposure: Current exposure to the market
            
        Returns:
            ValidationResult with validation details
        """
        checks: Dict[RiskCheck, Tuple[CheckResult, str]] = {}
        warnings: List[str] = []
        errors: List[str] = []
        approved_amount = request.amount
        risk_score = 0.0
        
        # Check 1: Kill Switch
        if self._limits.kill_switch_enabled and self._kill_switch_triggered:
            return ValidationResult(
                is_valid=False,
                approved_amount=0,
                risk_score=100,
                checks={},
                errors=[f"Kill switch active: {self._kill_switch_reason}"],
                recommendation="BLOCK",
            )
        
        # Check 2: Account Balance
        balance_check, balance_result = self._check_balance(account, request.amount)
        checks[RiskCheck.ACCOUNT_BALANCE] = (balance_check, balance_result)
        if balance_check == CheckResult.FAIL:
            errors.append(balance_result)
            risk_score += 30
        
        # Check 3: Position Size
        size_check, size_result, adjusted_size = self._check_position_size(request.amount)
        checks[RiskCheck.POSITION_SIZE] = (size_check, size_result)
        approved_amount = adjusted_size
        if size_check == CheckResult.WARNING:
            warnings.append(size_result)
            risk_score += 10
        
        # Check 4: Account Risk
        risk_check, risk_result = self._check_account_risk(account, request.amount)
        checks[RiskCheck.ACCOUNT_BALANCE] = (risk_check, risk_result)
        if risk_check == CheckResult.WARNING:
            warnings.append(risk_result)
            risk_score += 15
        elif risk_check == CheckResult.FAIL:
            errors.append(risk_result)
            risk_score += 25
        
        # Check 5: Drawdown
        dd_check, dd_result = self._check_drawdown(account)
        checks[RiskCheck.DRAWDOWN] = (dd_check, dd_result)
        if dd_check == CheckResult.WARNING:
            warnings.append(dd_result)
            risk_score += 20
        elif dd_check == CheckResult.FAIL:
            errors.append(dd_result)
            risk_score += 40
            approved_amount = 0
        
        # Check 6: Daily Loss
        daily_check, daily_result = self._check_daily_loss(account)
        checks[RiskCheck.DAILY_LOSS] = (daily_check, daily_result)
        if daily_check == CheckResult.WARNING:
            warnings.append(daily_result)
            risk_score += 15
        elif daily_check == CheckResult.FAIL:
            errors.append(daily_result)
            risk_score += 30
        
        # Check 7: Exposure
        exp_check, exp_result = self._check_exposure(account, market_exposure, request.amount)
        checks[RiskCheck.EXPOSURE] = (exp_check, exp_result)
        if exp_check == CheckResult.WARNING:
            warnings.append(exp_result)
            risk_score += 15
        elif exp_check == CheckResult.FAIL:
            errors.append(exp_result)
            risk_score += 25
        
        # Check 8: Trading Frequency
        freq_check, freq_result = self._check_frequency()
        checks[RiskCheck.POSITION_SIZE] = (freq_check, freq_result)
        if freq_check == CheckResult.WARNING:
            warnings.append(freq_result)
            risk_score += 10
        elif freq_check == CheckResult.FAIL:
            errors.append(freq_result)
            risk_score += 20
        
        # Check 9: Consecutive Losses
        streak_check, streak_result = self._check_consecutive_losses(account)
        checks[RiskCheck.CONSECUTIVE_LOSSES] = (streak_check, streak_result)
        if streak_check == CheckResult.WARNING:
            warnings.append(streak_result)
            risk_score += 20
        elif streak_check == CheckResult.FAIL:
            errors.append(streak_result)
            risk_score += 35
        
        # Check 10: Stop Loss / Take Profit
        sl_check, sl_result = self._check_stop_loss(request)
        checks[RiskCheck.STOP_LOSS] = (sl_check, sl_result)
        if sl_check == CheckResult.WARNING:
            warnings.append(sl_result)
            risk_score += 5
        
        # Determine final result
        is_valid = len(errors) == 0 and risk_score < 50
        recommendation = "EXECUTE" if is_valid else ("REVIEW" if risk_score < 75 else "BLOCK")
        
        if is_valid and warnings:
            recommendation = "EXECUTE_WITH_CAUTION"
        
        return ValidationResult(
            is_valid=is_valid,
            approved_amount=approved_amount,
            risk_score=min(risk_score, 100),
            checks=checks,
            warnings=warnings,
            errors=errors,
            recommendation=recommendation,
        )
    
    def _check_balance(
        self,
        account: AccountSnapshot,
        amount: float,
    ) -> Tuple[CheckResult, str]:
        """Check if account has sufficient balance"""
        if account.balance < self._limits.min_account_balance:
            return CheckResult.FAIL, f"Balance ${account.balance:.2f} below minimum ${self._limits.min_account_balance:.2f}"
        
        if account.balance < amount:
            return CheckResult.WARNING, f"Balance ${account.balance:.2f} insufficient for ${amount:.2f} trade"
        
        return CheckResult.PASS, "Balance adequate"
    
    def _check_position_size(
        self,
        amount: float,
    ) -> Tuple[CheckResult, str, float]:
        """Check position size against limits"""
        if amount < self._limits.min_position_size:
            return CheckResult.FAIL, f"Amount ${amount:.2f} below minimum ${self._limits.min_position_size:.2f}", self._limits.min_position_size
        
        if amount > self._limits.max_position_size:
            return CheckResult.WARNING, f"Amount ${amount:.2f} exceeds maximum ${self._limits.max_position_size:.2f}", self._limits.max_position_size
        
        return CheckResult.PASS, "Position size acceptable", amount
    
    def _check_account_risk(
        self,
        account: AccountSnapshot,
        amount: float,
    ) -> Tuple[CheckResult, str]:
        """Check if trade exceeds account risk percentage"""
        risk_amount = amount / account.balance if account.balance > 0 else 0
        
        if risk_amount > self._limits.max_account_risk:
            adjusted = account.balance * self._limits.max_account_risk
            return CheckResult.FAIL, f"Trade risk {risk_amount*100:.1f}% exceeds limit {self._limits.max_account_risk*100:.1f}%"
        
        if risk_amount > self._limits.max_account_risk * 0.8:
            return CheckResult.WARNING, f"Trade risk {risk_amount*100:.1f}% approaching limit"
        
        return CheckResult.PASS, "Account risk acceptable"
    
    def _check_drawdown(
        self,
        account: AccountSnapshot,
    ) -> Tuple[CheckResult, str]:
        """Check if current drawdown is within limits"""
        if account.max_drawdown > self._limits.max_drawdown:
            return CheckResult.FAIL, f"Drawdown {account.max_drawdown*100:.1f}% exceeds limit {self._limits.max_drawdown*100:.1f}%"
        
        if account.max_drawdown > self._limits.max_drawdown * 0.8:
            return CheckResult.WARNING, f"Drawdown {account.max_drawdown*100:.1f}% approaching limit"
        
        return CheckResult.PASS, "Drawdown acceptable"
    
    def _check_daily_loss(
        self,
        account: AccountSnapshot,
    ) -> Tuple[CheckResult, str]:
        """Check if daily loss exceeds limit"""
        daily_loss_pct = abs(account.daily_pnl) / account.balance if account.balance > 0 else 0
        
        if account.daily_pnl < 0 and daily_loss_pct > self._limits.max_daily_loss:
            return CheckResult.FAIL, f"Daily loss {daily_loss_pct*100:.1f}% exceeds limit {self._limits.max_daily_loss*100:.1f}%"
        
        if account.daily_pnl < 0 and daily_loss_pct > self._limits.max_daily_loss * 0.8:
            return CheckResult.WARNING, f"Daily loss {daily_loss_pct*100:.1f}% approaching limit"
        
        return CheckResult.PASS, "Daily loss acceptable"
    
    def _check_exposure(
        self,
        account: AccountSnapshot,
        current_exposure: float,
        new_amount: float,
    ) -> Tuple[CheckResult, str]:
        """Check market exposure limits"""
        new_exposure = current_exposure + (new_amount / account.balance if account.balance > 0 else 0)
        
        if new_exposure > self._limits.max_market_exposure:
            return CheckResult.FAIL, f"Market exposure {new_exposure*100:.1f}% exceeds limit"
        
        if new_exposure > self._limits.max_market_exposure * 0.8:
            return CheckResult.WARNING, f"Market exposure {new_exposure*100:.1f}% approaching limit"
        
        return CheckResult.PASS, "Exposure acceptable"
    
    def _check_frequency(self) -> Tuple[CheckResult, str]:
        """Check trading frequency limits"""
        now = datetime.now(timezone.utc)
        
        # Recent trades (last minute)
        recent = [t for t in self._trade_timestamps if (now - t).total_seconds() < 60]
        if len(recent) >= self._limits.max_trades_per_minute:
            return CheckResult.FAIL, f"Too many trades in last minute ({len(recent)}/{self._limits.max_trades_per_minute})"
        
        if len(recent) >= self._limits.max_trades_per_minute * 0.8:
            return CheckResult.WARNING, f"Approaching minute trade limit"
        
        # Hourly trades
        hourly = [t for t in self._trade_timestamps if (now - t).total_seconds() < 3600]
        if len(hourly) >= self._limits.max_trades_per_hour:
            return CheckResult.FAIL, f"Too many trades in last hour ({len(hourly)}/{self._limits.max_trades_per_hour})"
        
        if len(hourly) >= self._limits.max_trades_per_hour * 0.8:
            return CheckResult.WARNING, f"Approaching hourly trade limit"
        
        return CheckResult.PASS, "Trading frequency acceptable"
    
    def _check_consecutive_losses(
        self,
        account: AccountSnapshot,
    ) -> Tuple[CheckResult, str]:
        """Check consecutive loss limits"""
        if account.consecutive_losses >= self._limits.max_consecutive_losses:
            return CheckResult.FAIL, f"Consecutive losses ({account.consecutive_losses}) exceeds limit"
        
        if account.consecutive_losses >= self._limits.max_consecutive_losses - 1:
            return CheckResult.WARNING, f"Consecutive losses ({account.consecutive_losses}) approaching limit"
        
        return CheckResult.PASS, "Loss streak acceptable"
    
    def _check_stop_loss(
        self,
        request: TradeRequest,
    ) -> Tuple[CheckResult, str]:
        """Check stop loss configuration"""
        if request.contract_type == "DIGITAL":
            # Digital options have fixed durations, no stop loss
            return CheckResult.PASS, "Stop loss N/A for digital options"
        
        if request.stop_loss and request.stop_loss <= 0:
            return CheckResult.WARNING, "Stop loss should be positive"
        
        return CheckResult.PASS, "Stop loss acceptable"
    
    def record_trade(self, amount: float, profit: Optional[float] = None) -> None:
        """Record a trade for frequency tracking"""
        now = datetime.now(timezone.utc)
        self._trade_timestamps.append(now)
        
        if profit is not None and profit < 0:
            self._recent_losses.append(now)
    
    def trigger_kill_switch(self, reason: str) -> None:
        """Trigger the emergency kill switch"""
        self._kill_switch_triggered = True
        self._kill_switch_reason = reason
        logger.critical(f"KILL SWITCH TRIGGERED: {reason}")
    
    def check_kill_switch_conditions(self, account: AccountSnapshot) -> bool:
        """Check if kill switch should be triggered"""
        if not self._limits.kill_switch_enabled:
            return False
        
        # Check loss threshold
        if account.daily_pnl < -account.balance * self._limits.kill_switch_loss_threshold:
            self.trigger_kill_switch(
                f"Daily loss ${abs(account.daily_pnl):.2f} exceeds threshold"
            )
            return True
        
        # Check consecutive losses
        if account.consecutive_losses >= self._limits.kill_switch_loss_count:
            self.trigger_kill_switch(
                f"{account.consecutive_losses} consecutive losses exceeds threshold"
            )
            return True
        
        # Check drawdown
        if account.max_drawdown > self._limits.max_drawdown * 1.5:
            self.trigger_kill_switch(
                f"Drawdown {account.max_drawdown*100:.1f}% exceeds threshold"
            )
            return True
        
        return False
    
    def get_state(self) -> Dict[str, Any]:
        """Get current risk state"""
        now = datetime.now(timezone.utc)
        return {
            "limits": self._limits.to_dict(),
            "kill_switch": self.get_kill_switch_status(),
            "recent_trades": len([t for t in self._trade_timestamps if (now - t).total_seconds() < 60]),
            "hourly_trades": len([t for t in self._trade_timestamps if (now - t).total_seconds() < 3600]),
            "recent_losses": len(self._recent_losses),
        }
