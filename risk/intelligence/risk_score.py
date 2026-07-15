"""
Risk Score Calculator (0-100)
==============================

Calculates composite risk score from multiple factors.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RiskScoreWeights:
    """Weights for risk score components"""
    drawdown: float = 0.20
    volatility: float = 0.15
    concentration: float = 0.15
    var_95: float = 0.15
    state: float = 0.15
    circuit_breaker: float = 0.10
    positions: float = 0.10


class RiskScoreCalculator:
    """
    Calculates a composite risk score (0-100).
    
    0-20: Very Low Risk (Green)
    21-40: Low Risk (Light Green)
    41-60: Moderate Risk (Yellow)
    61-80: High Risk (Orange)
    81-100: Very High Risk (Red)
    """
    
    def __init__(self, limits: Any):
        self.weights = RiskScoreWeights()
        
        # Thresholds
        self.drawdown_thresholds = [0.02, 0.05, 0.10, 0.15]  # %, %, %, %
        self.volatility_thresholds = [0.10, 0.15, 0.20, 0.30]  # Annualized
        self.concentration_thresholds = [0.15, 0.25, 0.35, 0.50]
        self.var_thresholds = [0.01, 0.02, 0.03, 0.05]
        
        self.score_history: List[int] = []
    
    def calculate(
        self,
        drawdown: float,
        volatility: float,
        concentration: float,
        var_95: float,
        system_state: Any,
        circuit_breaker_tripped: bool,
        positions: List[Any]
    ) -> int:
        """
        Calculate composite risk score.
        
        Args:
            drawdown: Current drawdown (0-1)
            volatility: Current volatility (annualized)
            concentration: HHI concentration measure (0-1)
            var_95: 95% Value at Risk (0-1 of portfolio)
            system_state: Current system state
            circuit_breaker_tripped: Whether circuit breaker is active
            positions: List of current positions
            
        Returns:
            Risk score 0-100
        """
        # Calculate component scores
        drawdown_score = self._score_drawdown(drawdown)
        volatility_score = self._score_volatility(volatility)
        concentration_score = self._score_concentration(concentration)
        var_score = self._score_var(var_95)
        state_score = self._score_state(system_state)
        breaker_score = self._score_circuit_breaker(circuit_breaker_tripped)
        position_score = self._score_positions(positions)
        
        # Weighted average
        score = (
            self.weights.drawdown * drawdown_score +
            self.weights.volatility * volatility_score +
            self.weights.concentration * concentration_score +
            self.weights.var_95 * var_score +
            self.weights.state * state_score +
            self.weights.circuit_breaker * breaker_score +
            self.weights.positions * position_score
        )
        
        # Round to integer
        final_score = int(round(max(0, min(100, score))))
        
        self.score_history.append(final_score)
        
        return final_score
    
    def _score_drawdown(self, drawdown: float) -> float:
        """Score drawdown component (0-100)"""
        if drawdown <= self.drawdown_thresholds[0]:
            return drawdown / self.drawdown_thresholds[0] * 20
        elif drawdown <= self.drawdown_thresholds[1]:
            return 20 + (drawdown - self.drawdown_thresholds[0]) / (self.drawdown_thresholds[1] - self.drawdown_thresholds[0]) * 20
        elif drawdown <= self.drawdown_thresholds[2]:
            return 40 + (drawdown - self.drawdown_thresholds[1]) / (self.drawdown_thresholds[2] - self.drawdown_thresholds[1]) * 20
        elif drawdown <= self.drawdown_thresholds[3]:
            return 60 + (drawdown - self.drawdown_thresholds[2]) / (self.drawdown_thresholds[3] - self.drawdown_thresholds[2]) * 20
        else:
            return 80 + min(20, (drawdown - self.drawdown_thresholds[3]) / 0.05 * 20)
    
    def _score_volatility(self, volatility: float) -> float:
        """Score volatility component (0-100)"""
        if volatility <= self.volatility_thresholds[0]:
            return volatility / self.volatility_thresholds[0] * 20
        elif volatility <= self.volatility_thresholds[1]:
            return 20 + (volatility - self.volatility_thresholds[0]) / (self.volatility_thresholds[1] - self.volatility_thresholds[0]) * 20
        elif volatility <= self.volatility_thresholds[2]:
            return 40 + (volatility - self.volatility_thresholds[1]) / (self.volatility_thresholds[2] - self.volatility_thresholds[1]) * 20
        elif volatility <= self.volatility_thresholds[3]:
            return 60 + (volatility - self.volatility_thresholds[2]) / (self.volatility_thresholds[3] - self.volatility_thresholds[2]) * 20
        else:
            return 80 + min(20, (volatility - self.volatility_thresholds[3]) / 0.1 * 20)
    
    def _score_concentration(self, concentration: float) -> float:
        """Score concentration component (0-100)"""
        if concentration <= self.concentration_thresholds[0]:
            return concentration / self.concentration_thresholds[0] * 20
        elif concentration <= self.concentration_thresholds[1]:
            return 20 + (concentration - self.concentration_thresholds[0]) / (self.concentration_thresholds[1] - self.concentration_thresholds[0]) * 20
        elif concentration <= self.concentration_thresholds[2]:
            return 40 + (concentration - self.concentration_thresholds[1]) / (self.concentration_thresholds[2] - self.concentration_thresholds[1]) * 20
        elif concentration <= self.concentration_thresholds[3]:
            return 60 + (concentration - self.concentration_thresholds[2]) / (self.concentration_thresholds[3] - self.concentration_thresholds[2]) * 20
        else:
            return 80 + min(20, (concentration - self.concentration_thresholds[3]) / 0.25 * 20)
    
    def _score_var(self, var_95: float) -> float:
        """Score VaR component (0-100)"""
        if var_95 <= self.var_thresholds[0]:
            return var_95 / self.var_thresholds[0] * 20
        elif var_95 <= self.var_thresholds[1]:
            return 20 + (var_95 - self.var_thresholds[0]) / (self.var_thresholds[1] - self.var_thresholds[0]) * 20
        elif var_95 <= self.var_thresholds[2]:
            return 40 + (var_95 - self.var_thresholds[1]) / (self.var_thresholds[2] - self.var_thresholds[1]) * 20
        elif var_95 <= self.var_thresholds[3]:
            return 60 + (var_95 - self.var_thresholds[2]) / (self.var_thresholds[3] - self.var_thresholds[2]) * 20
        else:
            return 80 + min(20, (var_95 - self.var_thresholds[3]) / 0.02 * 20)
    
    def _score_state(self, system_state: Any) -> float:
        """Score system state component (0-100)"""
        state_scores = {
            "NORMAL": 10,
            "CAUTION": 35,
            "ELEVATED": 60,
            "CRITICAL": 85,
            "RECOVERY": 70,
            "KILLED": 100
        }
        
        state_str = system_state.value if hasattr(system_state, 'value') else str(system_state)
        return state_scores.get(state_str, 50)
    
    def _score_circuit_breaker(self, tripped: bool) -> float:
        """Score circuit breaker component (0-100)"""
        return 100 if tripped else 10
    
    def _score_positions(self, positions: List[Any]) -> float:
        """Score position count/complexity (0-100)"""
        n = len(positions)
        
        if n <= 3:
            return 10
        elif n <= 5:
            return 30
        elif n <= 8:
            return 50
        elif n <= 12:
            return 70
        else:
            return 90
    
    def get_risk_level(self, score: int) -> tuple[str, str]:
        """
        Get risk level and color from score.
        
        Returns:
            Tuple of (level, color)
        """
        if score <= 20:
            return "VERY_LOW", "#00FF00"  # Green
        elif score <= 40:
            return "LOW", "#90EE90"  # Light Green
        elif score <= 60:
            return "MODERATE", "#FFFF00"  # Yellow
        elif score <= 80:
            return "HIGH", "#FFA500"  # Orange
        else:
            return "VERY_HIGH", "#FF0000"  # Red
    
    def get_trend(self) -> str:
        """Get risk score trend"""
        if len(self.score_history) < 5:
            return "INSUFFICIENT_DATA"
        
        recent = self.score_history[-5:]
        if all(recent[i] > recent[i+1] for i in range(len(recent)-1)):
            return "IMPROVING"
        elif all(recent[i] < recent[i+1] for i in range(len(recent)-1)):
            return "WORSENING"
        else:
            return "STABLE"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get risk score metrics"""
        if not self.score_history:
            return {"current": 50, "level": "MODERATE", "trend": "INSUFFICIENT_DATA"}
        
        current = self.score_history[-1]
        level, color = self.get_risk_level(current)
        
        return {
            "current": current,
            "level": level,
            "color": color,
            "trend": self.get_trend(),
            "mean": np.mean(self.score_history) if self.score_history else 50,
            "max": max(self.score_history) if self.score_history else 50,
            "min": min(self.score_history) if self.score_history else 50
        }
