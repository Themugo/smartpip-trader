"""
Portfolio Concentration Analysis
================================

Analyzes and monitors portfolio concentration risk.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class ConcentrationLevel(Enum):
    """Concentration risk levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class ConcentrationLimits:
    """Concentration limits"""
    max_single_position: float = 0.20  # 20% max
    max_position_size: float = 0.20  # Alias for max_single_position
    max_sector: float = 0.40  # 40% max per sector
    max_correlated_group: float = 0.50  # 50% max correlated
    herfindahl_limit: float = 0.25  # HHI limit


class ConcentrationAnalyzer:
    """
    Analyzes portfolio concentration risk.
    """
    
    def __init__(self, limits: Optional[ConcentrationLimits] = None):
        self.limits = limits or ConcentrationLimits()
        
        self.herfindahl_history: List[float] = []
    
    def calculate(
        self,
        positions: List[Any],
        portfolio_value: float
    ) -> float:
        """
        Calculate overall concentration risk.
        
        Args:
            positions: List of positions
            portfolio_value: Total portfolio value
            
        Returns:
            Concentration risk score (0-1)
        """
        if not positions or portfolio_value <= 0:
            return 0.0
        
        # Calculate weights
        weights = np.array([
            abs(p.size * p.current_price) / portfolio_value
            for p in positions
        ])
        
        # Herfindahl-Hirschman Index (HHI)
        hhi = np.sum(weights ** 2)
        
        # Normalize HHI (1/n is perfectly diversified)
        n = len(positions)
        normalized_hhi = (hhi - 1/n) / (1 - 1/n) if n > 1 else 1.0
        
        self.herfindahl_history.append(normalized_hhi)
        
        return normalized_hhi
    
    def check_addition(
        self,
        symbol: str,
        position_value: float,
        existing_positions: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Check if adding a position would breach concentration limits.
        
        Returns:
            Tuple of (allowed, reason)
        """
        # If no existing positions, always allow
        if not existing_positions:
            return True, "OK"
        
        total_value = sum(
            p.size * p.current_price
            for p in existing_positions.values()
        ) + position_value
        
        # Check single position limit
        position_ratio = position_value / total_value if total_value > 0 else 0
        if position_ratio > self.limits.max_single_position:
            return False, f"Single position {position_ratio:.1%} exceeds limit {self.limits.max_single_position:.1%}"
        
        # Check HHI after addition
        weights = [
            p.size * p.current_price / total_value
            for p in existing_positions.values()
        ]
        weights.append(position_value / total_value)
        
        hhi = np.sum(np.array(weights) ** 2)
        
        if hhi > self.limits.herfindahl_limit:
            return False, f"HHI {hhi:.3f} would exceed limit {self.limits.herfindahl_limit:.3f}"
        
        return True, "OK"
    
    def get_concentration_by_symbol(
        self,
        positions: List[Any],
        portfolio_value: float
    ) -> Dict[str, float]:
        """Get concentration by symbol"""
        if portfolio_value <= 0:
            return {}
        
        return {
            p.symbol: abs(p.size * p.current_price) / portfolio_value
            for p in positions
        }
    
    def get_sector_concentration(
        self,
        positions: List[Any],
        portfolio_value: float,
        sector_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """Get concentration by sector"""
        if portfolio_value <= 0:
            return {}
        
        sector_mapping = sector_mapping or {}
        sector_values: Dict[str, float] = {}
        
        for p in positions:
            sector = sector_mapping.get(p.symbol, "UNKNOWN")
            sector_values[sector] = sector_values.get(sector, 0) + abs(p.size * p.current_price)
        
        return {
            sector: value / portfolio_value
            for sector, value in sector_values.items()
        }
    
    def get_level(self, concentration: float) -> ConcentrationLevel:
        """Get concentration level"""
        if concentration < 0.15:
            return ConcentrationLevel.LOW
        elif concentration < 0.25:
            return ConcentrationLevel.MEDIUM
        elif concentration < 0.40:
            return ConcentrationLevel.HIGH
        else:
            return ConcentrationLevel.VERY_HIGH
    
    def get_diversification_benefit(
        self,
        positions: List[Any],
        portfolio_value: float
    ) -> float:
        """
        Calculate diversification benefit.
        
        Returns:
            Percentage of risk reduction from diversification
        """
        if not positions or len(positions) < 2:
            return 0.0
        
        # Calculate weighted average volatility (assuming equal correlation)
        volatilities = np.array([p.risk_contribution for p in positions])
        
        if volatilities.sum() == 0:
            return 0.0
        
        weights = volatilities / volatilities.sum()
        
        # Diversified portfolio vol (assuming 0.3 average correlation)
        avg_vol = np.mean(volatilities)
        correlation = 0.3
        n = len(positions)
        
        diversified_vol = avg_vol * np.sqrt((1 + (n - 1) * correlation) / n)
        concentrated_vol = np.sum(weights * volatilities)
        
        if concentrated_vol == 0:
            return 0.0
        
        benefit = 1 - diversified_vol / concentrated_vol
        
        return max(0, min(1, benefit))
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get concentration metrics"""
        current_hhi = self.herfindahl_history[-1] if self.herfindahl_history else 0
        
        return {
            "current_hhi": current_hhi,
            "level": self.get_level(current_hhi).value,
            "hhi_trend": self._get_hhi_trend(),
            "limits": {
                "max_single_position": self.limits.max_single_position,
                "herfindahl_limit": self.limits.herfindahl_limit
            }
        }
    
    def _get_hhi_trend(self) -> str:
        """Get HHI trend"""
        if len(self.herfindahl_history) < 5:
            return "INSUFFICIENT_DATA"
        
        recent = self.herfindahl_history[-5:]
        if all(recent[i] > recent[i+1] for i in range(len(recent)-1)):
            return "DECREASING"
        elif all(recent[i] < recent[i+1] for i in range(len(recent)-1)):
            return "INCREASING"
        else:
            return "STABLE"
    
    def reset(self) -> None:
        """Reset analyzer"""
        self.herfindahl_history.clear()
