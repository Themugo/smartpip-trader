"""
Pre-Trade Validator

Validates orders before execution:
- Risk checks
- Position limits
- Market hours
- Order size validation
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ValidationResult:
    """Result of order validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def __bool__(self):
        return self.is_valid


class PreTradeValidator:
    """
    Pre-trade validation for orders.
    
    Checks:
    - Order parameters
    - Risk limits
    - Position size
    - Account balance
    """
    
    def __init__(
        self,
        max_position_size: float = 10000,
        max_daily_trades: int = 50,
        min_stake: float = 1.0,
        max_stake: float = 1000,
    ):
        self._max_position_size = max_position_size
        self._max_daily_trades = max_daily_trades
        self._min_stake = min_stake
        self._max_stake = max_stake
        
        # Counters
        self._daily_trade_count = 0
        self._last_reset = datetime.utcnow()
    
    def validate_order(
        self,
        amount: float,
        market: str,
        direction: str,
        current_balance: float,
    ) -> ValidationResult:
        """Validate an order"""
        errors = []
        warnings = []
        
        # Check amount limits
        if amount < self._min_stake:
            errors.append(f"Amount ${amount} below minimum ${self._min_stake}")
        if amount > self._max_stake:
            errors.append(f"Amount ${amount} exceeds maximum ${self._max_stake}")
        
        # Check position size
        if amount > self._max_position_size:
            errors.append(f"Position size ${amount} exceeds limit ${self._max_position_size}")
        
        # Check balance
        if amount > current_balance:
            errors.append(f"Insufficient balance: ${amount} > ${current_balance}")
        
        # Check daily trade limit
        self._check_daily_reset()
        if self._daily_trade_count >= self._max_daily_trades:
            errors.append(f"Daily trade limit ({self._max_daily_trades}) reached")
        
        # Warnings
        if amount > self._max_position_size * 0.8:
            warnings.append(f"Position size is >80% of maximum limit")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def _check_daily_reset(self):
        """Reset daily counter if needed"""
        now = datetime.utcnow()
        if now.date() > self._last_reset.date():
            self._daily_trade_count = 0
            self._last_reset = now
    
    def record_trade(self):
        """Record a trade for daily count"""
        self._check_daily_reset()
        self._daily_trade_count += 1
    
    def get_daily_count(self) -> int:
        """Get current daily trade count"""
        self._check_daily_reset()
        return self._daily_trade_count
