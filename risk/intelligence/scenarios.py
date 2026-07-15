"""
Scenario Analysis & Stress Testing
==================================

Simulates different market conditions to assess portfolio risk.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


class ScenarioType(Enum):
    """Types of stress scenarios"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    FLASH_CRASH = "flash_crash"
    VOLATILITY_SPIKE = "volatility_spike"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    SECTOR_ROTATION = "sector_rotation"
    BLACK_SWANS = "black_swans"


@dataclass
class ScenarioResult:
    """Result of scenario analysis"""
    scenario_type: ScenarioType
    price_change: float  # Percentage
    portfolio_impact: float
    positions_affected: int
    max_loss: float
    max_gain: float
    recovery_time: Optional[int]  # Estimated in trades
    probability: float
    severity: str  # LOW, MEDIUM, HIGH, EXTREME


class ScenarioAnalyzer:
    """
    Analyzes portfolio under various market scenarios.
    """
    
    def __init__(self):
        self.scenario_history: List[ScenarioResult] = []
    
    def analyze(
        self,
        symbol: str,
        positions: List[Any],
        portfolio_value: float
    ) -> Dict[str, Any]:
        """Run scenario analysis for a symbol"""
        results = {}
        
        for scenario_type in ScenarioType:
            result = self._run_single_scenario(
                symbol=symbol,
                scenario_type=scenario_type,
                positions=positions,
                portfolio_value=portfolio_value
            )
            results[scenario_type.value] = result
        
        return {
            "symbol": symbol,
            "scenarios": results,
            "worst_case": self._get_worst_case(results),
            "best_case": self._get_best_case(results),
            "expected_impact": self._get_expected_impact(results)
        }
    
    def _run_single_scenario(
        self,
        symbol: str,
        scenario_type: ScenarioType,
        positions: List[Any],
        portfolio_value: float
    ) -> ScenarioResult:
        """Run a single scenario"""
        # Define scenario parameters
        scenario_params = self._get_scenario_params(scenario_type)
        
        # Find relevant positions
        relevant_positions = [p for p in positions if p.symbol == symbol]
        
        # Calculate impact
        portfolio_impact = 0.0
        max_loss = 0.0
        max_gain = 0.0
        
        for pos in relevant_positions:
            if scenario_params["directional"]:
                if pos.direction == "LONG":
                    impact = pos.size * pos.current_price * scenario_params["price_change"]
                else:
                    impact = -pos.size * pos.current_price * scenario_params["price_change"]
            else:
                # For non-directional scenarios
                impact = -abs(pos.size * pos.current_price * scenario_params["volatility_change"])
            
            portfolio_impact += impact
            
            if impact < 0:
                max_loss = min(max_loss, impact)
            else:
                max_gain = max(max_gain, impact)
        
        return ScenarioResult(
            scenario_type=scenario_type,
            price_change=scenario_params["price_change"],
            portfolio_impact=portfolio_impact,
            positions_affected=len(relevant_positions),
            max_loss=max_loss,
            max_gain=max_gain,
            recovery_time=scenario_params["recovery_time"],
            probability=scenario_params["probability"],
            severity=scenario_params["severity"]
        )
    
    def _get_scenario_params(self, scenario_type: ScenarioType) -> Dict[str, Any]:
        """Get parameters for a scenario type"""
        params = {
            ScenarioType.BULL_MARKET: {
                "price_change": 0.05,
                "volatility_change": 0.02,
                "directional": True,
                "recovery_time": 10,
                "probability": 0.25,
                "severity": "LOW"
            },
            ScenarioType.BEAR_MARKET: {
                "price_change": -0.10,
                "volatility_change": 0.15,
                "directional": True,
                "recovery_time": 50,
                "probability": 0.15,
                "severity": "HIGH"
            },
            ScenarioType.FLASH_CRASH: {
                "price_change": -0.20,
                "volatility_change": 0.50,
                "directional": False,
                "recovery_time": 5,
                "probability": 0.05,
                "severity": "EXTREME"
            },
            ScenarioType.VOLATILITY_SPIKE: {
                "price_change": 0.0,
                "volatility_change": 0.30,
                "directional": False,
                "recovery_time": 20,
                "probability": 0.10,
                "severity": "MEDIUM"
            },
            ScenarioType.LIQUIDITY_CRISIS: {
                "price_change": -0.08,
                "volatility_change": 0.25,
                "directional": True,
                "recovery_time": 100,
                "probability": 0.08,
                "severity": "HIGH"
            },
            ScenarioType.CORRELATION_BREAKDOWN: {
                "price_change": 0.0,
                "volatility_change": 0.20,
                "directional": False,
                "recovery_time": 30,
                "probability": 0.12,
                "severity": "MEDIUM"
            },
            ScenarioType.SECTOR_ROTATION: {
                "price_change": -0.03,
                "volatility_change": 0.10,
                "directional": True,
                "recovery_time": 15,
                "probability": 0.18,
                "severity": "LOW"
            },
            ScenarioType.BLACK_SWANS: {
                "price_change": -0.30,
                "volatility_change": 1.0,
                "directional": False,
                "recovery_time": 200,
                "probability": 0.02,
                "severity": "EXTREME"
            }
        }
        return params.get(scenario_type, params[ScenarioType.BEAR_MARKET])
    
    def _get_worst_case(self, results: Dict[str, ScenarioResult]) -> Dict[str, Any]:
        """Get worst case scenario"""
        if not results:
            return {}
        
        worst = min(results.values(), key=lambda r: r.portfolio_impact)
        return {
            "scenario": worst.scenario_type.value,
            "impact": worst.portfolio_impact,
            "probability": worst.probability,
            "severity": worst.severity
        }
    
    def _get_best_case(self, results: Dict[str, ScenarioResult]) -> Dict[str, Any]:
        """Get best case scenario"""
        if not results:
            return {}
        
        best = max(results.values(), key=lambda r: r.portfolio_impact)
        return {
            "scenario": best.scenario_type.value,
            "impact": best.portfolio_impact,
            "probability": best.probability,
            "severity": best.severity
        }
    
    def _get_expected_impact(self, results: Dict[str, ScenarioResult]) -> float:
        """Get expected portfolio impact"""
        total = 0.0
        for result in results.values():
            total += result.portfolio_impact * result.probability
        return total


class StressTestRunner:
    """
    Runs comprehensive stress tests on the portfolio.
    """
    
    def __init__(self, num_simulations: int = 10000):
        self.num_simulations = num_simulations
    
    def run_full_stress_test(
        self,
        portfolio_value: float,
        positions: List[Any],
        initial_capital: float
    ) -> Dict[str, Any]:
        """Run comprehensive stress test"""
        # Historical stress scenarios
        historical_results = self._run_historical_scenarios(portfolio_value, positions)
        
        # Monte Carlo simulation
        mc_results = self._run_monte_carlo(portfolio_value, positions)
        
        # Extreme scenarios
        extreme_results = self._run_extreme_scenarios(portfolio_value, positions)
        
        # Calculate aggregate metrics
        var_99 = self._calculate_var(mc_results, 0.99)
        cvar_99 = self._calculate_cvar(mc_results, 0.99)
        max_drawdown_stress = min(mc_results)
        
        return {
            "historical_scenarios": historical_results,
            "monte_carlo": {
                "simulations": self.num_simulations,
                "mean": np.mean(mc_results),
                "std": np.std(mc_results),
                "var_95": self._calculate_var(mc_results, 0.95),
                "var_99": var_99,
                "cvar_99": cvar_99,
                "worst_5pct": np.percentile(mc_results, 5),
                "best_5pct": np.percentile(mc_results, 95)
            },
            "extreme_scenarios": extreme_results,
            "summary": {
                "max_potential_loss": min(mc_results),
                "max_drawdown_under_stress": max_drawdown_stress,
                "capital_at_risk_99": abs(cvar_99),
                "recommendation": self._get_recommendation(var_99, cvar_99)
            }
        }
    
    def _run_historical_scenarios(
        self,
        portfolio_value: float,
        positions: List[Any]
    ) -> List[Dict[str, Any]]:
        """Run scenarios based on historical events"""
        # Define historical-like scenarios
        scenarios = [
            ("2020_COVID_CRASH", -0.34, 0.8),
            ("2008_LEHMAN", -0.25, 0.6),
            ("2011_DEBT_CRISIS", -0.15, 0.4),
            ("2022_RATE_HIKE", -0.20, 0.5),
            ("DOTCOM_BUBBLE", -0.45, 0.3)
        ]
        
        results = []
        for name, shock, correlation in scenarios:
            # Calculate portfolio impact
            impact = portfolio_value * shock * self._calculate_beta(positions, correlation)
            
            results.append({
                "name": name,
                "market_shock": shock,
                "portfolio_impact": impact,
                "portfolio_impact_pct": shock * correlation,
                "correlation": correlation
            })
        
        return results
    
    def _run_monte_carlo(
        self,
        portfolio_value: float,
        positions: List[Any]
    ) -> List[float]:
        """Run Monte Carlo simulation"""
        # Assume daily returns follow normal distribution
        mean_return = -0.0002  # Slight negative drift
        std_return = 0.02  # 2% daily volatility
        
        # Generate random returns
        np.random.seed(42)
        returns = np.random.normal(mean_return, std_return, self.num_simulations)
        
        # Calculate portfolio outcomes
        outcomes = portfolio_value * returns
        
        return outcomes.tolist()
    
    def _run_extreme_scenarios(
        self,
        portfolio_value: float,
        positions: List[Any]
    ) -> List[Dict[str, Any]]:
        """Run extreme tail scenarios"""
        scenarios = [
            ("5_STD_MOVE", 5),
            ("10_STD_MOVE", 10),
            ("20_STD_MOVE", 20),
            ("TOTAL_LOSS", 100)
        ]
        
        results = []
        std_daily = 0.02
        
        for name, num_std in scenarios:
            if name == "TOTAL_LOSS":
                shock = -1.0
            else:
                shock = -num_std * std_daily
            
            impact = portfolio_value * shock
            
            results.append({
                "name": name,
                "shock": shock,
                "impact": impact,
                "probability": self._calculate_tail_probability(num_std)
            })
        
        return results
    
    def _calculate_var(self, returns: List[float], confidence: float) -> float:
        """Calculate Value at Risk"""
        return np.percentile(returns, (1 - confidence) * 100)
    
    def _calculate_cvar(self, returns: List[float], confidence: float) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)"""
        var = self._calculate_var(returns, confidence)
        tail_returns = [r for r in returns if r <= var]
        return np.mean(tail_returns) if tail_returns else var
    
    def _calculate_beta(
        self,
        positions: List[Any],
        market_correlation: float
    ) -> float:
        """Calculate portfolio beta"""
        # Simplified - assume positions have beta of 1
        return market_correlation
    
    def _calculate_tail_probability(self, num_std: float) -> float:
        """Calculate probability of N standard deviation move"""
        from scipy import stats
        return 2 * (1 - stats.norm.cdf(num_std))
    
    def _get_recommendation(self, var: float, cvar: float) -> str:
        """Get risk management recommendation"""
        if abs(var) > 0.15:
            return "REDUCE_EXPOSURE"
        elif abs(var) > 0.10:
            return "MAINTAIN_TIGHT_STOPS"
        elif abs(var) > 0.05:
            return "MONITOR_CLOSELY"
        else:
            return "NORMAL_OPERATIONS"
