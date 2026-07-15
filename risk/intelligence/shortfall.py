"""
Expected Shortfall (CVaR) Calculator
=====================================

Calculates Value at Risk and Conditional Value at Risk.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


class ExpectedShortfallCalculator:
    """
    Calculates Expected Shortfall (CVaR) and Value at Risk (VaR).
    """
    
    def __init__(
        self,
        lookback_periods: int = 252,
        confidence_levels: Optional[List[float]] = None
    ):
        self.lookback_periods = lookback_periods
        self.confidence_levels = confidence_levels or [0.90, 0.95, 0.99]
        
        self.recent_volatility = 0.0
        self.recent_returns: List[float] = []
        self.var_history: Dict[float, List[float]] = {c: [] for c in self.confidence_levels}
        self.cvar_history: Dict[float, List[float]] = {c: [] for c in self.confidence_levels}
    
    def calculate(
        self,
        positions: List[Any],
        portfolio_value: float,
        confidence: float = 0.95,
        method: str = "historical"
    ) -> tuple[float, float]:
        """
        Calculate VaR and CVaR.
        
        Args:
            positions: List of positions
            portfolio_value: Current portfolio value
            confidence: Confidence level (e.g., 0.95 for 95%)
            method: Calculation method ("historical", "parametric", "monte_carlo")
            
        Returns:
            Tuple of (VaR, CVaR) as absolute values
        """
        if not positions:
            return 0.0, 0.0
        
        # Get position values
        position_values = [p.size * p.current_price for p in positions]
        total_exposure = sum(abs(v) for v in position_values)
        
        if portfolio_value <= 0 or total_exposure == 0:
            return 0.0, 0.0
        
        if method == "historical":
            var, cvar = self._historical_method(portfolio_value, confidence)
        elif method == "parametric":
            var, cvar = self._parametric_method(portfolio_value, confidence)
        else:  # monte_carlo
            var, cvar = self._monte_carlo_method(portfolio_value, confidence)
        
        # Update history
        self.var_history[confidence].append(var)
        self.cvar_history[confidence].append(cvar)
        
        return var, cvar
    
    def _historical_method(
        self,
        portfolio_value: float,
        confidence: float
    ) -> tuple[float, float]:
        """Historical simulation method"""
        if len(self.recent_returns) < 30:
            # Use recent volatility estimate
            volatility = max(self.recent_volatility, 0.01)
            z_score = self._get_z_score(confidence)
            var = portfolio_value * volatility * z_score
            cvar = var * 1.3  # Approximate CVaR
        else:
            # Use actual historical returns
            returns = np.array(self.recent_returns[-self.lookback_periods:])
            var_pct = -np.percentile(returns, (1 - confidence) * 100)
            var = portfolio_value * var_pct
            
            # CVaR is the mean of losses beyond VaR
            tail_losses = returns[returns <= -var_pct]
            if len(tail_losses) > 0:
                cvar = portfolio_value * abs(np.mean(tail_losses))
            else:
                cvar = var * 1.2
        
        return var, cvar
    
    def _parametric_method(
        self,
        portfolio_value: float,
        confidence: float
    ) -> tuple[float, float]:
        """Parametric (variance-covariance) method"""
        volatility = max(self.recent_volatility, 0.01)
        z_score = self._get_z_score(confidence)
        
        var = portfolio_value * volatility * z_score
        
        # CVaR for normal distribution: VaR * (1 + f(z) / (1 - p)) / z
        # Simplified: CVaR ≈ VaR * 1.3 for 95%, 1.25 for 99%
        if confidence == 0.95:
            cvar_factor = 1.3
        elif confidence == 0.99:
            cvar_factor = 1.25
        else:
            cvar_factor = 1.35
        
        cvar = var * cvar_factor
        
        return var, cvar
    
    def _monte_carlo_method(
        self,
        portfolio_value: float,
        confidence: float
    ) -> tuple[float, float]:
        """Monte Carlo simulation method"""
        volatility = max(self.recent_volatility, 0.01)
        
        # Simulate many scenarios
        np.random.seed(42)
        n_simulations = 10000
        daily_returns = np.random.normal(0, volatility, n_simulations)
        
        # Calculate portfolio losses
        losses = portfolio_value * (-daily_returns)
        
        var_pct = np.percentile(daily_returns, (1 - confidence) * 100)
        var = portfolio_value * abs(var_pct)
        
        # CVaR is mean of losses beyond VaR
        tail_losses = losses[daily_returns <= var_pct]
        cvar = np.mean(tail_losses) if len(tail_losses) > 0 else var
        
        return var, cvar
    
    def _get_z_score(self, confidence: float) -> float:
        """Get z-score for confidence level"""
        z_scores = {
            0.90: 1.28,
            0.95: 1.65,
            0.99: 2.33,
            0.999: 3.09
        }
        return z_scores.get(confidence, 1.65)
    
    def update_volatility(self, returns: List[float]) -> None:
        """Update volatility estimate from recent returns"""
        if len(returns) < 2:
            return
        
        self.recent_returns = returns[-self.lookback_periods:]
        
        # Use EWMA for volatility (more responsive)
        if len(returns) >= 20:
            lambda_ = 0.94  # GARCH-like decay
            variance = 0
            for r in reversed(returns[-20:]):
                variance = lambda_ * variance + (1 - lambda_) * r ** 2
            self.recent_volatility = np.sqrt(variance * 252)  # Annualized
        else:
            self.recent_volatility = np.std(returns) * np.sqrt(252)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all VaR/CVaR metrics"""
        return {
            "recent_volatility": self.recent_volatility,
            "var_90": self._get_latest_var(0.90),
            "var_95": self._get_latest_var(0.95),
            "var_99": self._get_latest_var(0.99),
            "cvar_95": self._get_latest_cvar(0.95),
            "cvar_99": self._get_latest_cvar(0.99),
            "volatility_trend": self._get_volatility_trend()
        }
    
    def _get_latest_var(self, confidence: float) -> float:
        """Get latest VaR for confidence level"""
        history = self.var_history.get(confidence, [])
        return history[-1] if history else 0.0
    
    def _get_latest_cvar(self, confidence: float) -> float:
        """Get latest CVaR for confidence level"""
        history = self.cvar_history.get(confidence, [])
        return history[-1] if history else 0.0
    
    def _get_volatility_trend(self) -> str:
        """Get volatility trend"""
        if len(self.var_history[0.95]) < 5:
            return "INSUFFICIENT_DATA"
        
        recent = self.var_history[0.95][-5:]
        if all(recent[i] > recent[i+1] for i in range(len(recent)-1)):
            return "DECREASING"
        elif all(recent[i] < recent[i+1] for i in range(len(recent)-1)):
            return "INCREASING"
        else:
            return "STABLE"
    
    def calculate_greeks(self) -> Dict[str, float]:
        """Calculate risk greeks (simplified)"""
        return {
            "delta_var": self._calculate_delta_var(),
            "vega_var": self._calculate_vega_var(),
            "correlation_var": self._calculate_correlation_var()
        }
    
    def _calculate_delta_var(self) -> float:
        """Delta VaR - VaR change for unit price move"""
        if not self.var_history.get(0.95):
            return 0.0
        return self.var_history[0.95][-1] * 0.01 if self.var_history[0.95] else 0.0
    
    def _calculate_vega_var(self) -> float:
        """Vega VaR - VaR change for 1% vol change"""
        if self.recent_volatility > 0:
            return self.var_history.get(0.95, [0])[-1] * 0.01 / self.recent_volatility
        return 0.0
    
    def _calculate_correlation_var(self) -> float:
        """Correlation VaR - sensitivity to correlation changes"""
        return 0.0  # Simplified
