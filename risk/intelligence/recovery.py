"""
Recovery Mode Manager
=====================

Manages trading recovery after significant drawdowns.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class RecoveryPhase(Enum):
    """Recovery phases"""
    NOT_IN_RECOVERY = "not_in_recovery"
    PHASE_1_CONSERVATIVE = "phase_1_conservative"
    PHASE_2_MODERATE = "phase_2_moderate"
    PHASE_3_AGGRESSIVE = "phase_3_aggressive"
    FULL_RECOVERY = "full_recovery"


@dataclass
class RecoveryConfig:
    """Recovery configuration"""
    min_drawdown_to_start: float = 0.05  # 5% drawdown to enter recovery
    phase_1_duration: int = 10  # 10 trades
    phase_2_duration: int = 20  # 20 trades
    phase_1_max_stake: float = 0.25  # 25% of normal stake
    phase_2_max_stake: float = 0.50  # 50% of normal stake
    phase_3_max_stake: float = 0.75  # 75% of normal stake
    recovery_target: float = 0.0  # Break-even
    exit_on_loss: bool = True  # Exit recovery on any loss


class RecoveryManager:
    """
    Manages trading in recovery mode after drawdowns.
    """
    
    def __init__(self, config: Optional[RecoveryConfig] = None):
        self.config = config or RecoveryConfig()
        
        # State
        self.in_recovery = False
        self.phase = RecoveryPhase.NOT_IN_RECOVERY
        self.phase_start: Optional[datetime] = None
        self.trades_in_phase = 0
        self.total_recovery_trades = 0
        self.recovery_wins = 0
        self.recovery_losses = 0
        self.peak_during_recovery = 0.0
        
        # History
        self.recovery_history: List[Dict[str, Any]] = []
    
    def start_recovery(self, peak_value: float = 0.0) -> None:
        """Start recovery mode"""
        self.in_recovery = True
        self.phase = RecoveryPhase.PHASE_1_CONSERVATIVE
        self.phase_start = datetime.now()
        self.trades_in_phase = 0
        self.total_recovery_trades = 0
        self.recovery_wins = 0
        self.recovery_losses = 0
        self.peak_during_recovery = peak_value
        
        self._log_event("RECOVERY_STARTED", "Phase 1 Conservative")
        logger.info("Entering recovery mode - Phase 1 Conservative")
    
    def end_recovery(self, reason: str = "Manual") -> None:
        """End recovery mode"""
        if not self.in_recovery:
            return
        
        self._log_event("RECOVERY_ENDED", reason)
        
        # Record recovery session
        self.recovery_history.append({
            "start": self.phase_start,
            "end": datetime.now(),
            "duration_trades": self.total_recovery_trades,
            "wins": self.recovery_wins,
            "losses": self.recovery_losses,
            "exit_reason": reason
        })
        
        self.in_recovery = False
        self.phase = RecoveryPhase.NOT_IN_RECOVERY
        self.phase_start = None
        
        logger.info(f"Recovery ended: {reason}")
    
    def check_recovery_trade(
        self,
        trade_result: float,  # Positive for win, negative for loss
        current_value: float,
        peak_value: float
    ) -> tuple[bool, str]:
        """
        Process a trade result during recovery.
        
        Returns:
            Tuple of (should_continue_recovery, message)
        """
        if not self.in_recovery:
            return False, "Not in recovery"
        
        self.total_recovery_trades += 1
        self.trades_in_phase += 1
        
        if trade_result > 0:
            self.recovery_wins += 1
        else:
            self.recovery_losses += 1
            
            # Check if should exit recovery
            if self.config.exit_on_loss and self.phase == RecoveryPhase.PHASE_1_CONSERVATIVE:
                self.end_recovery("Loss in Phase 1 - resetting")
                return False, "Recovery reset due to loss"
        
        # Update peak
        if current_value > self.peak_during_recovery:
            self.peak_during_recovery = current_value
        
        # Check for phase transition
        self._check_phase_transition(current_value, peak_value)
        
        # Check for full recovery
        if current_value >= peak_value:
            self.end_recovery("Full recovery achieved")
            return False, "Full recovery achieved"
        
        return True, f"Continuing in {self.phase.value}"
    
    def _check_phase_transition(
        self,
        current_value: float,
        peak_value: float
    ) -> None:
        """Check and execute phase transitions"""
        if self.phase == RecoveryPhase.PHASE_1_CONSERVATIVE:
            # Check if should move to phase 2
            recovery_pct = (self.peak_during_recovery - current_value) / self.peak_during_recovery
            if self.trades_in_phase >= self.config.phase_1_duration and self.recovery_wins > self.recovery_losses:
                self._transition_to_phase(RecoveryPhase.PHASE_2_MODERATE)
        
        elif self.phase == RecoveryPhase.PHASE_2_MODERATE:
            # Check if should move to phase 3
            if self.trades_in_phase >= self.config.phase_2_duration and self.recovery_wins > self.recovery_losses * 1.5:
                self._transition_to_phase(RecoveryPhase.PHASE_3_AGGRESSIVE)
        
        elif self.phase == RecoveryPhase.PHASE_3_AGGRESSIVE:
            # Check for full recovery
            if current_value >= peak_value * 0.95:  # Within 5% of peak
                self.end_recovery("Near full recovery")
    
    def _transition_to_phase(self, new_phase: RecoveryPhase) -> None:
        """Transition to a new recovery phase"""
        old_phase = self.phase
        self.phase = new_phase
        self.trades_in_phase = 0
        self.phase_start = datetime.now()
        
        self._log_event("RECOVERY_PHASE_CHANGE", f"{old_phase.value} -> {new_phase.value}")
        logger.info(f"Recovery phase transition: {old_phase.value} -> {new_phase.value}")
    
    def get_stake_multiplier(self) -> float:
        """Get stake multiplier for current phase"""
        multipliers = {
            RecoveryPhase.PHASE_1_CONSERVATIVE: self.config.phase_1_max_stake,
            RecoveryPhase.PHASE_2_MODERATE: self.config.phase_2_max_stake,
            RecoveryPhase.PHASE_3_AGGRESSIVE: self.config.phase_3_max_stake,
            RecoveryPhase.FULL_RECOVERY: 1.0,
            RecoveryPhase.NOT_IN_RECOVERY: 1.0
        }
        return multipliers.get(self.phase, 1.0)
    
    def should_allow_trade(
        self,
        confidence: float,
        base_stake: float
    ) -> tuple[bool, float, str]:
        """
        Check if trade should be allowed in recovery mode.
        
        Returns:
            Tuple of (allowed, adjusted_stake, reason)
        """
        if not self.in_recovery:
            return True, base_stake, "Normal trading"
        
        # Minimum confidence increases with conservatism
        min_confidence = {
            RecoveryPhase.PHASE_1_CONSERVATIVE: 0.75,
            RecoveryPhase.PHASE_2_MODERATE: 0.65,
            RecoveryPhase.PHASE_3_AGGRESSIVE: 0.55
        }.get(self.phase, 0.5)
        
        if confidence < min_confidence:
            return False, 0, f"Confidence {confidence:.2f} below minimum {min_confidence}"
        
        # Calculate adjusted stake
        multiplier = self.get_stake_multiplier()
        adjusted_stake = base_stake * multiplier
        
        return True, adjusted_stake, f"Recovery phase: {self.phase.value}"
    
    def get_state(self) -> Dict[str, Any]:
        """Get recovery state"""
        return {
            "in_recovery": self.in_recovery,
            "phase": self.phase.value,
            "phase_start": self.phase_start.isoformat() if self.phase_start else None,
            "trades_in_phase": self.trades_in_phase,
            "total_recovery_trades": self.total_recovery_trades,
            "recovery_wins": self.recovery_wins,
            "recovery_losses": self.recovery_losses,
            "win_rate": self.recovery_wins / self.total_recovery_trades if self.total_recovery_trades > 0 else 0,
            "stake_multiplier": self.get_stake_multiplier()
        }
    
    def _log_event(self, event_type: str, description: str) -> None:
        """Log recovery event"""
        logger.info(f"RECOVERY: {event_type} - {description}")
    
    def reset(self) -> None:
        """Reset recovery state"""
        self.in_recovery = False
        self.phase = RecoveryPhase.NOT_IN_RECOVERY
        self.phase_start = None
        self.trades_in_phase = 0
        self.total_recovery_trades = 0
        self.recovery_wins = 0
        self.recovery_losses = 0
        self.peak_during_recovery = 0.0
