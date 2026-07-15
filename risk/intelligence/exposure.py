"""
Adaptive Exposure Manager
=========================

Dynamically adjusts exposure based on market conditions.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


class ExposureState(Enum):
    """Exposure adjustment states"""
    FULL = "full"
    REDUCED = "reduced"
    MINIMAL = "minimal"
    ZERO = "zero"


@dataclass
class ExposureLimits:
    """Exposure limits"""
    max_daily_loss: float = 0.02
    max_drawdown: float = 0.10
    max_position_size: float = 0.20
    circuit_breaker_threshold: float = 0.05
    kill_switch_threshold: float = 0.15


class AdaptiveExposureManager:
    """
    Manages adaptive exposure limits based on conditions.
    """
    
    def __init__(self, limits: Optional[ExposureLimits] = None):
        self.limits = limits or ExposureLimits()
        
        # State
        self.current_exposure = 1.0  # 100%
        self.target_exposure = 1.0
        self.min_exposure = 0.0
        self.max_exposure = 1.0
        
        # Adjustment parameters
        self.volatility_scalar = 1.0
        self.drawdown_scalar = 1.0
        self.correlation_scalar = 1.0
        self.state_scalar = 1.0
        
        # History
        self.exposure_history = []
    
    def get_exposure_limit(
        self,
        current_drawdown: float,
        volatility: float,
        system_state: Any
    ) -> float:
        """
        Calculate adaptive exposure limit.
        
        Args:
            current_drawdown: Current drawdown as fraction
            volatility: Current volatility (annualized)
            system_state: Current system state enum
            
        Returns:
            Exposure limit (0 to 1)
        """
        # Base exposure
        exposure = 1.0
        
        # Drawdown adjustment
        if current_drawdown > self.limits.max_drawdown * 0.8:
            exposure *= 0.25
        elif current_drawdown > self.limits.max_drawdown * 0.5:
            exposure *= 0.50
        elif current_drawdown > self.limits.max_drawdown * 0.2:
            exposure *= 0.75
        
        self.drawdown_scalar = exposure
        
        # Volatility adjustment
        target_vol = 0.15  # 15% target
        if volatility > target_vol * 1.5:
            exposure *= 0.50
        elif volatility > target_vol * 1.2:
            exposure *= 0.75
        elif volatility < target_vol * 0.8:
            exposure *= 1.10  # Boost in calm markets
        
        self.volatility_scalar = exposure / self.drawdown_scalar if self.drawdown_scalar > 0 else 1.0
        
        # System state adjustment
        state_exposure = self._get_state_exposure(system_state)
        exposure *= state_exposure
        self.state_scalar = state_exposure
        
        # Apply limits
        exposure = max(self.min_exposure, min(self.max_exposure, exposure))
        
        # Update state
        self.target_exposure = exposure
        self.exposure_history.append({
            "timestamp": str.__class__,
            "exposure": exposure,
            "drawdown": current_drawdown,
            "volatility": volatility,
            "system_state": str(system_state.value) if hasattr(system_state, 'value') else str(system_state)
        })
        
        return exposure
    
    def _get_state_exposure(self, system_state: Any) -> float:
        """Get exposure multiplier based on system state"""
        state_map = {
            "NORMAL": 1.0,
            "CAUTION": 0.80,
            "ELEVATED": 0.50,
            "CRITICAL": 0.25,
            "RECOVERY": 0.30,
            "KILLED": 0.0
        }
        
        state_str = system_state.value if hasattr(system_state, 'value') else str(system_state)
        return state_map.get(state_str, 1.0)
    
    def get_position_size_limit(
        self,
        base_limit: float,
        confidence: float,
        volatility: float
    ) -> float:
        """
        Get position size limit adjusted for confidence and volatility.
        
        Args:
            base_limit: Base position size limit
            confidence: Confidence in the trade (0-1)
            volatility: Current volatility
            
        Returns:
            Adjusted position size limit
        """
        # Confidence adjustment
        confidence_factor = min(1.0, confidence ** 0.5)  # Square root scaling
        
        # Volatility adjustment (reduce size in high vol)
        target_vol = 0.15
        vol_factor = 1.0 if volatility < target_vol else target_vol / volatility
        
        # Combined factor
        factor = confidence_factor * vol_factor
        
        return base_limit * factor
    
    def calculate_stake_reduction(
        self,
        base_stake: float,
        current_drawdown: float,
        consecutive_losses: int = 0
    ) -> float:
        """
        Calculate stake reduction based on drawdown and losses.
        
        Args:
            base_stake: Base stake amount
            current_drawdown: Current drawdown
            consecutive_losses: Number of consecutive losses
            
        Returns:
            Reduced stake amount
        """
        reduction = 1.0
        
        # Drawdown reduction
        if current_drawdown > 0.05:
            reduction *= 0.75
        if current_drawdown > 0.10:
            reduction *= 0.50
        if current_drawdown > 0.15:
            reduction *= 0.25
        
        # Consecutive loss reduction
        if consecutive_losses >= 3:
            reduction *= 0.75
        if consecutive_losses >= 5:
            reduction *= 0.50
        if consecutive_losses >= 7:
            reduction *= 0.25
        
        return base_stake * reduction
    
    def get_exposure_state(self) -> ExposureState:
        """Get current exposure state"""
        if self.target_exposure >= 0.9:
            return ExposureState.FULL
        elif self.target_exposure >= 0.5:
            return ExposureState.REDUCED
        elif self.target_exposure >= 0.1:
            return ExposureState.MINIMAL
        else:
            return ExposureState.ZERO
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get exposure metrics"""
        return {
            "current_exposure": self.current_exposure,
            "target_exposure": self.target_exposure,
            "min_exposure": self.min_exposure,
            "max_exposure": self.max_exposure,
            "state": self.get_exposure_state().value,
            "drawdown_scalar": self.drawdown_scalar,
            "volatility_scalar": self.volatility_scalar,
            "state_scalar": self.state_scalar
        }
    
    def reset(self) -> None:
        """Reset to full exposure"""
        self.current_exposure = 1.0
        self.target_exposure = 1.0
        self.volatility_scalar = 1.0
        self.drawdown_scalar = 1.0
        self.correlation_scalar = 1.0
        self.state_scalar = 1.0
        self.exposure_history.clear()
