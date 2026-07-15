"""
Sensitivity Analysis
====================

Analyzes how changes in inputs affect portfolio outputs.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SensitivityResult:
    """Result of sensitivity analysis"""
    parameter: str
    base_value: float
    perturbed_value: float
    change_pct: float
    portfolio_impact: float
    impact_per_unit: float  # Delta per unit of parameter change
    elasticity: float  # Percentage change in output per percentage change in input


class SensitivityAnalyzer:
    """
    Analyzes portfolio sensitivity to various parameters.
    """
    
    def __init__(self):
        self.analysis_history: List[Dict[str, Any]] = []
    
    def analyze(
        self,
        symbol: str,
        positions: List[Any],
        portfolio_value: float
    ) -> Dict[str, Any]:
        """Run sensitivity analysis for a symbol"""
        relevant_positions = [p for p in positions if p.symbol == symbol]
        
        if not relevant_positions:
            return {"symbol": symbol, "sensitivities": {}, "message": "No positions found"}
        
        sensitivities = {}
        
        # Price sensitivity
        sensitivities["price"] = self._analyze_price_sensitivity(
            positions=relevant_positions,
            portfolio_value=portfolio_value
        )
        
        # Volatility sensitivity (Vega)
        sensitivities["volatility"] = self._analyze_volatility_sensitivity(
            positions=relevant_positions,
            portfolio_value=portfolio_value
        )
        
        # Time sensitivity (Theta)
        sensitivities["time"] = self._analyze_time_sensitivity(
            positions=relevant_positions,
            portfolio_value=portfolio_value
        )
        
        # Correlation sensitivity
        sensitivities["correlation"] = self._analyze_correlation_sensitivity(
            positions=positions,
            portfolio_value=portfolio_value
        )
        
        # Interest rate sensitivity (Rho)
        sensitivities["interest_rate"] = self._analyze_interest_rate_sensitivity(
            positions=relevant_positions,
            portfolio_value=portfolio_value
        )
        
        return {
            "symbol": symbol,
            "sensitivities": sensitivities,
            "total_exposure": self._calculate_total_exposure(relevant_positions, portfolio_value),
            "key_risks": self._identify_key_risks(sensitivities)
        }
    
    def _analyze_price_sensitivity(
        self,
        positions: List[Any],
        portfolio_value: float
    ) -> Dict[str, Any]:
        """Analyze price sensitivity (Delta)"""
        total_delta = 0.0
        total_gamma = 0.0
        
        for pos in positions:
            # Delta: change in position value per unit price change
            if pos.direction == "LONG":
                delta = pos.size
                gamma = 0  # Linear approximation
            else:
                delta = -pos.size
                gamma = 0
            
            total_delta += delta
            total_gamma += gamma
        
        # Calculate sensitivities
        position_value = sum(p.size * p.current_price for p in positions)
        
        return {
            "delta": total_delta,
            "delta_percentage": total_delta / portfolio_value if portfolio_value > 0 else 0,
            "gamma": total_gamma,
            "dollar_delta": total_delta,  # Per unit price
            "impact_per_1pct_move": position_value * 0.01 * (total_delta / position_value) if position_value > 0 else 0
        }
    
    def _analyze_volatility_sensitivity(
        self,
        positions: List[Any],
        portfolio_value: float
    ) -> Dict[str, Any]:
        """Analyze volatility sensitivity (Vega)"""
        # Simplified vega calculation
        avg_time_to_expiry = 0.25  # Assume 3 months average
        vega = 0  # Would use Black-Scholes in production
        
        return {
            "vega": vega,
            "vega_per_vol_point": vega / 100 if vega != 0 else 0,
            "vol_impact_per_1pct": vega * 0.01 if vega != 0 else 0
        }
    
    def _analyze_time_sensitivity(
        self,
        positions: List[Any],
        portfolio_value: float
    ) -> Dict[str, Any]:
        """Analyze time decay sensitivity (Theta)"""
        # Simplified theta calculation
        theta = 0  # Would use Black-Scholes in production
        
        return {
            "theta": theta,
            "theta_per_day": theta / 365 if theta != 0 else 0,
            "time_impact": theta / 365 if theta != 0 else 0
        }
    
    def _analyze_correlation_sensitivity(
        self,
        positions: List[Any],
        portfolio_value: float
    ) -> Dict[str, Any]:
        """Analyze correlation sensitivity"""
        symbols = list(set(p.symbol for p in positions))
        
        if len(symbols) < 2:
            return {"correlation_risk": 0, "diversification_benefit": 0}
        
        # Simplified - assume some base correlation
        base_correlation = 0.3
        
        return {
            "average_correlation": base_correlation,
            "correlation_risk": base_correlation ** 2,
            "correlation_impact_per_10pct": base_correlation * 0.1
        }
    
    def _analyze_interest_rate_sensitivity(
        self,
        positions: List[Any],
        portfolio_value: float
    ) -> Dict[str, Any]:
        """Analyze interest rate sensitivity (Rho)"""
        rho = 0  # Simplified
        
        return {
            "rho": rho,
            "rho_per_rate_point": rho / 100 if rho != 0 else 0
        }
    
    def _calculate_total_exposure(
        self,
        positions: List[Any],
        portfolio_value: float
    ) -> Dict[str, float]:
        """Calculate total exposure metrics"""
        exposure = sum(abs(p.size * p.current_price) for p in positions)
        gross_exposure = sum(p.size * p.current_price for p in positions)
        
        return {
            "net_exposure": gross_exposure,
            "net_exposure_pct": gross_exposure / portfolio_value if portfolio_value > 0 else 0,
            "gross_exposure": exposure,
            "gross_exposure_pct": exposure / portfolio_value if portfolio_value > 0 else 0
        }
    
    def _identify_key_risks(
        self,
        sensitivities: Dict[str, Any]
    ) -> List[str]:
        """Identify key risk factors"""
        risks = []
        
        if sensitivities.get("price", {}).get("delta_percentage", 0) > 0.5:
            risks.append("HIGH_PRICE_SENSITIVITY")
        
        if sensitivities.get("volatility", {}).get("vol_impact_per_1pct", 0) < -0.01:
            risks.append("VOLATILITY_RISK")
        
        if sensitivities.get("correlation", {}).get("correlation_risk", 0) > 0.5:
            risks.append("CONCENTRATION_RISK")
        
        return risks if risks else ["NO_MATERIAL_RISKS"]
