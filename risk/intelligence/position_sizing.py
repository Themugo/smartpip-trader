"""
Confidence-Aware Position Sizing
=================================

Sizes positions based on confidence levels and risk parameters.
"""

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PositionSizeLimits:
    """Position sizing limits"""
    max_position_size: float = 0.20  # 20% max per position
    max_total_exposure: float = 1.0  # 100% max total
    min_confidence: float = 0.5


class ConfidenceAwareSizer:
    """
    Calculates position sizes based on confidence and risk parameters.
    """
    
    def __init__(self, limits: Optional[PositionSizeLimits] = None):
        self.limits = limits or PositionSizeLimits()
        
        # Kelly criterion parameters
        self.kelly_fraction = 0.25  # Use 1/4 Kelly by default
        
        # Historical win rate (for Kelly calculation)
        self.win_rate = 0.55
        self.avg_win = 1.0
        self.avg_loss = 1.0
    
    def calculate(
        self,
        portfolio_value: float,
        confidence: float,
        entry_price: float,
        stop_loss_pct: float,
        current_drawdown: float,
        system_state: Any
    ) -> float:
        """
        Calculate position size.
        
        Args:
            portfolio_value: Current portfolio value
            confidence: Trade confidence (0-1)
            entry_price: Entry price
            stop_loss_pct: Stop loss as percentage
            current_drawdown: Current drawdown
            system_state: System state
            
        Returns:
            Position size (in units)
        """
        # Base size using Kelly criterion
        kelly_size = self._calculate_kelly_size(portfolio_value, stop_loss_pct)
        
        # Adjust for confidence
        confidence_adjusted = kelly_size * (confidence ** 0.5)
        
        # Adjust for drawdown
        drawdown_adjusted = self._adjust_for_drawdown(
            confidence_adjusted,
            current_drawdown
        )
        
        # Adjust for system state
        state_adjusted = self._adjust_for_state(
            drawdown_adjusted,
            system_state
        )
        
        # Apply limits
        max_size = portfolio_value * self.limits.max_position_size / entry_price
        final_size = min(state_adjusted, max_size)
        
        # Ensure minimum size
        if final_size < 1:
            final_size = 0
        
        return final_size
    
    def _calculate_kelly_size(
        self,
        portfolio_value: float,
        stop_loss_pct: float
    ) -> float:
        """Calculate Kelly criterion position size"""
        if self.win_rate <= 0.5:
            return 0
        
        # Kelly formula: f = (bp - q) / b
        # where b = avg_win/avg_loss, p = win_rate, q = 1 - p
        b = self.avg_win / self.avg_loss if self.avg_loss > 0 else 1
        p = self.win_rate
        q = 1 - p
        
        kelly = (b * p - q) / b
        
        if kelly <= 0:
            return 0
        
        # Apply fractional Kelly
        fractional_kelly = kelly * self.kelly_fraction
        
        # Calculate dollar position size
        dollar_size = portfolio_value * fractional_kelly
        
        # Convert to units based on stop loss
        if stop_loss_pct > 0:
            risk_per_unit = stop_loss_pct
            size = dollar_size * self.kelly_fraction / risk_per_unit
        else:
            size = dollar_size / 100  # Simplified
        
        return size
    
    def _adjust_for_drawdown(
        self,
        size: float,
        drawdown: float
    ) -> float:
        """Adjust size based on current drawdown"""
        if drawdown < 0.02:
            return size
        elif drawdown < 0.05:
            return size * 0.75
        elif drawdown < 0.10:
            return size * 0.50
        elif drawdown < 0.15:
            return size * 0.25
        else:
            return size * 0.10
    
    def _adjust_for_state(
        self,
        size: float,
        system_state: Any
    ) -> float:
        """Adjust size based on system state"""
        state_multipliers = {
            "NORMAL": 1.0,
            "CAUTION": 0.75,
            "ELEVATED": 0.50,
            "CRITICAL": 0.25,
            "RECOVERY": 0.30,
            "KILLED": 0.0
        }
        
        state_str = system_state.value if hasattr(system_state, 'value') else str(system_state)
        multiplier = state_multipliers.get(state_str, 1.0)
        
        return size * multiplier
    
    def calculate_kelly_fraction(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """Calculate Kelly fraction"""
        if win_rate <= 0 or avg_loss <= 0:
            return 0
        
        b = avg_win / avg_loss
        q = 1 - win_rate
        
        kelly = (b * win_rate - q) / b
        
        if kelly <= 0:
            return 0
        
        return min(kelly, 0.25)  # Cap at 25% Kelly
    
    def update_win_rate(
        self,
        wins: int,
        losses: int
    ) -> None:
        """Update win rate estimate"""
        total = wins + losses
        if total > 0:
            self.win_rate = wins / total
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get sizing metrics"""
        kelly = self._calculate_kelly_fraction()
        
        return {
            "kelly_fraction": kelly,
            "effective_fraction": kelly * self.kelly_fraction,
            "win_rate": self.win_rate,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "max_position_pct": self.limits.max_position_size * 100
        }
    
    def _calculate_kelly_fraction(self) -> float:
        """Calculate Kelly fraction internally"""
        if self.win_rate <= 0.5 or self.avg_loss <= 0:
            return 0
        
        b = self.avg_win / self.avg_loss
        p = self.win_rate
        q = 1 - p
        
        kelly = (b * p - q) / b
        return max(0, kelly)
