"""
Capital Allocation Models
=========================

Distributes capital across strategies and positions.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class AllocationMethod(Enum):
    """Capital allocation methods"""
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    EQUAL_RISK_CONTRIBUTION = "equal_risk_contribution"
    MEAN_VARIANCE = "mean_variance"
    MIN_VARIANCE = "min_variance"
    VOLATILITY_TARGETING = "volatility_targeting"
    INVERSE_VOLATILITY = "inverse_volatility"


class CapitalAllocator:
    """
    Allocates capital across positions and strategies.
    """
    
    def __init__(
        self,
        target_volatility: float = 0.15,  # 15% annualized
        max_leverage: float = 1.0
    ):
        self.target_volatility = target_volatility
        self.max_leverage = max_leverage
        
        self.allocation_history: List[Dict[str, Any]] = []
    
    def allocate(
        self,
        positions: List[Dict[str, Any]],
        total_capital: float,
        method: AllocationMethod = AllocationMethod.INVERSE_VOLATILITY
    ) -> Dict[str, float]:
        """
        Allocate capital across positions.
        
        Args:
            positions: List of position dicts with 'symbol', 'volatility', 'expected_return'
            total_capital: Total capital to allocate
            method: Allocation method
            
        Returns:
            Dict mapping symbol to allocated capital
        """
        if not positions:
            return {}
        
        # Ensure we have volatility for each position
        for pos in positions:
            if 'volatility' not in pos:
                pos['volatility'] = 0.20  # Default 20% vol
        
        if method == AllocationMethod.EQUAL_WEIGHT:
            allocation = self._equal_weight(positions, total_capital)
        elif method == AllocationMethod.RISK_PARITY:
            allocation = self._risk_parity(positions, total_capital)
        elif method == AllocationMethod.EQUAL_RISK_CONTRIBUTION:
            allocation = self._equal_risk_contribution(positions, total_capital)
        elif method == AllocationMethod.MEAN_VARIANCE:
            allocation = self._mean_variance(positions, total_capital)
        elif method == AllocationMethod.MIN_VARIANCE:
            allocation = self._min_variance(positions, total_capital)
        elif method == AllocationMethod.VOLATILITY_TARGETING:
            allocation = self._volatility_targeting(positions, total_capital)
        else:  # INVERSE_VOLATILITY
            allocation = self._inverse_volatility(positions, total_capital)
        
        self.allocation_history.append({
            "method": method.value,
            "total_capital": total_capital,
            "allocation": allocation,
            "leverage": sum(allocation.values()) / total_capital
        })
        
        return allocation
    
    def _equal_weight(
        self,
        positions: List[Dict[str, Any]],
        total_capital: float
    ) -> Dict[str, float]:
        """Equal weight allocation"""
        n = len(positions)
        weight = 1.0 / n
        
        return {
            pos['symbol']: total_capital * weight
            for pos in positions
        }
    
    def _inverse_volatility(
        self,
        positions: List[Dict[str, Any]],
        total_capital: float
    ) -> Dict[str, float]:
        """Inverse volatility weighting"""
        volatilities = np.array([p['volatility'] for p in positions])
        
        # Avoid division by zero
        volatilities = np.maximum(volatilities, 0.01)
        
        # Inverse volatility weights
        inv_vol = 1.0 / volatilities
        weights = inv_vol / inv_vol.sum()
        
        return {
            pos['symbol']: total_capital * weights[i]
            for i, pos in enumerate(positions)
        }
    
    def _risk_parity(
        self,
        positions: List[Dict[str, Any]],
        total_capital: float
    ) -> Dict[str, float]:
        """Risk parity - equal risk contribution"""
        volatilities = np.array([p['volatility'] for p in positions])
        
        # Risk parity weights (inverse vol, normalized)
        inv_vol = 1.0 / volatilities
        risk_weights = inv_vol / inv_vol.sum()
        
        # Apply leverage limit
        gross_exposure = risk_weights.sum()
        if gross_exposure > self.max_leverage:
            risk_weights = risk_weights * (self.max_leverage / gross_exposure)
        
        return {
            pos['symbol']: total_capital * risk_weights[i]
            for i, pos in enumerate(positions)
        }
    
    def _equal_risk_contribution(
        self,
        positions: List[Dict[str, Any]],
        total_capital: float
    ) -> Dict[str, float]:
        """Equal risk contribution (similar to risk parity)"""
        return self._risk_parity(positions, total_capital)
    
    def _mean_variance(
        self,
        positions: List[Dict[str, Any]],
        total_capital: float
    ) -> Dict[str, float]:
        """Mean-variance optimized allocation (simplified)"""
        volatilities = np.array([p['volatility'] for p in positions])
        returns = np.array([p.get('expected_return', 0.10) for p in positions])
        
        # Simplified: weight by return-to-volatility ratio
        ratios = returns / volatilities
        weights = ratios / ratios.sum()
        
        return {
            pos['symbol']: total_capital * weights[i]
            for i, pos in enumerate(positions)
        }
    
    def _min_variance(
        self,
        positions: List[Dict[str, Any]],
        total_capital: float
    ) -> Dict[str, float]:
        """Minimum variance portfolio"""
        volatilities = np.array([p['volatility'] for p in positions])
        
        # Min var weights are inversely proportional to variance
        variances = volatilities ** 2
        weights = (1.0 / variances)
        weights = weights / weights.sum()
        
        return {
            pos['symbol']: total_capital * weights[i]
            for i, pos in enumerate(positions)
        }
    
    def _volatility_targeting(
        self,
        positions: List[Dict[str, Any]],
        total_capital: float
    ) -> Dict[str, float]:
        """Volatility targeting allocation"""
        volatilities = np.array([p['volatility'] for p in positions])
        
        # Inverse volatility weights, scaled to hit target vol
        inv_vol = 1.0 / volatilities
        weights = inv_vol / inv_vol.sum()
        
        # Calculate current portfolio vol
        current_vol = np.sqrt(np.sum(weights ** 2 * volatilities ** 2))
        
        if current_vol > 0:
            # Scale to target volatility
            vol_scalar = self.target_volatility / current_vol
            weights = weights * vol_scalar
            
            # Apply leverage limit
            gross_exposure = weights.sum()
            if gross_exposure > self.max_leverage:
                weights = weights * (self.max_leverage / gross_exposure)
        
        return {
            pos['symbol']: total_capital * weights[i]
            for i, pos in enumerate(positions)
        }
    
    def rebalance(
        self,
        current_allocation: Dict[str, float],
        target_allocation: Dict[str, float],
        threshold: float = 0.05  # 5% drift threshold
    ) -> Dict[str, float]:
        """
        Determine if rebalancing is needed.
        
        Returns:
            Dict of adjustments needed
        """
        adjustments = {}
        
        all_symbols = set(current_allocation.keys()) | set(target_allocation.keys())
        
        for symbol in all_symbols:
            current = current_allocation.get(symbol, 0)
            target = target_allocation.get(symbol, 0)
            drift = abs(current - target) / (sum(current_allocation.values()) if sum(current_allocation.values()) > 0 else 1)
            
            if drift > threshold:
                adjustments[symbol] = target - current
        
        return adjustments
    
    def get_allocation_stats(self) -> Dict[str, Any]:
        """Get allocation statistics"""
        if not self.allocation_history:
            return {}
        
        latest = self.allocation_history[-1]
        
        return {
            "method": latest["method"],
            "leverage": latest["leverage"],
            "num_positions": len(latest["allocation"]),
            "allocation_history_length": len(self.allocation_history)
        }
