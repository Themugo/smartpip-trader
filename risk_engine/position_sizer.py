"""
Position Sizer

Calculates position sizes based on risk parameters.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PositionSizeResult:
    """Result of position size calculation"""
    stake: float
    units: float
    risk_amount: float
    risk_percentage: float
    method: str


class PositionSizer:
    """
    Calculates position sizes for trading.
    
    Methods:
    - Fixed stake
    - Fixed risk percentage
    - Kelly criterion
    - Volatility-based
    """
    
    def __init__(
        self,
        default_method: str = "fixed_risk",
        max_stake_pct: float = 0.02,
    ):
        self._default_method = default_method
        self._max_stake_pct = max_stake_pct
    
    def calculate(
        self,
        method: str,
        balance: float,
        entry_price: float,
        stop_loss: float,
        risk_pct: float = 1.0,
    ) -> PositionSizeResult:
        """Calculate position size"""
        
        if method == "fixed_stake":
            return self._fixed_stake(balance, risk_pct)
        elif method == "fixed_risk":
            return self._fixed_risk(balance, entry_price, stop_loss, risk_pct)
        elif method == "volatility":
            return self._volatility_based(balance, entry_price, stop_loss)
        else:
            return self._fixed_stake(balance, risk_pct)
    
    def _fixed_stake(
        self,
        balance: float,
        stake_pct: float,
    ) -> PositionSizeResult:
        """Fixed stake as percentage of balance"""
        stake = balance * (stake_pct / 100)
        return PositionSizeResult(
            stake=stake,
            units=stake,
            risk_amount=stake,
            risk_percentage=stake_pct,
            method="fixed_stake",
        )
    
    def _fixed_risk(
        self,
        balance: float,
        entry_price: float,
        stop_loss: float,
        risk_pct: float,
    ) -> PositionSizeResult:
        """Fixed risk as percentage of balance"""
        risk_amount = balance * (risk_pct / 100)
        
        # Calculate position size based on stop loss distance
        price_diff = abs(entry_price - stop_loss)
        if price_diff > 0:
            units = risk_amount / price_diff
        else:
            units = 0
        
        stake = units * entry_price
        
        return PositionSizeResult(
            stake=stake,
            units=units,
            risk_amount=risk_amount,
            risk_percentage=risk_pct,
            method="fixed_risk",
        )
    
    def _volatility_based(
        self,
        balance: float,
        entry_price: float,
        stop_loss: float,
        atr: float = 0.0,
    ) -> PositionSizeResult:
        """Volatility-based position sizing"""
        if atr <= 0:
            return self._fixed_stake(balance, 1.0)
        
        # Use 1 ATR as stop loss distance
        stop_distance = atr
        risk_amount = balance * (self._max_stake_pct)
        
        units = risk_amount / stop_distance
        stake = units * entry_price
        
        return PositionSizeResult(
            stake=stake,
            units=units,
            risk_amount=risk_amount,
            risk_percentage=self._max_stake_pct * 100,
            method="volatility",
        )
