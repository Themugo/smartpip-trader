"""
Synthetic market simulator for generating realistic price data.
Models volatility indices with proper statistical properties.
"""
import numpy as np
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class MarketRegime(Enum):
    """Market regime types"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


@dataclass
class SimulationConfig:
    """Configuration for market simulation"""
    symbol: str = "R_100"
    initial_price: float = 5000.0
    volatility: float = 0.02  # 2% per tick
    drift: float = 0.0
    num_ticks: int = 10000
    regime_changes: bool = True
    mean_reversion_strength: float = 0.1
    # Transaction costs
    spread: float = 0.0001  # 0.01%
    commission_per_trade: float = 0.0
    # Latency and slippage
    latency_ticks: int = 1  # 1 tick latency
    slippage_std: float = 0.0005  # 0.05% std slippage
    # Digit properties
    digit_bias: Optional[Dict[int, float]] = None


class MarketSimulator:
    """
    Simulates synthetic index price movements with realistic properties.
    
    Key features:
    - Geometric Brownian Motion with optional mean reversion
    - Regime switching (trending, ranging, high/low volatility)
    - Realistic digit distribution with configurable bias
    - Transaction costs, latency, and slippage modeling
    """
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.rng = np.random.RandomState(seed=42)
        self.current_regime = MarketRegime.RANGING
        self.regime_duration = 0
        self.price = config.initial_price
        self.ticks: List[Dict[str, Any]] = []
        self.current_tick = 0
    
    def _switch_regime(self) -> None:
        """Randomly switch market regime"""
        if not self.config.regime_changes:
            return
        
        regimes = list(MarketRegime)
        weights = [0.15, 0.15, 0.3, 0.2, 0.2]  # probabilities
        self.current_regime = self.rng.choice(regimes, p=weights)
        self.regime_duration = self.rng.randint(500, 2000)
        
        # Adjust parameters based on regime
        if self.current_regime == MarketRegime.TRENDING_UP:
            self.config.drift = 0.0005
            self.config.volatility = 0.015
        elif self.current_regime == MarketRegime.TRENDING_DOWN:
            self.config.drift = -0.0005
            self.config.volatility = 0.015
        elif self.current_regime == MarketRegime.RANGING:
            self.config.drift = 0.0
            self.config.volatility = 0.01
        elif self.current_regime == MarketRegime.HIGH_VOLATILITY:
            self.config.drift = 0.0
            self.config.volatility = 0.04
        elif self.current_regime == MarketRegime.LOW_VOLATILITY:
            self.config.drift = 0.0
            self.config.volatility = 0.005
    
    def _generate_next_price(self) -> float:
        """Generate next price using GBM with mean reversion"""
        if self.config.regime_changes:
            self.regime_duration -= 1
            if self.regime_duration <= 0:
                self._switch_regime()
        
        # Mean reversion toward initial price
        mean_reversion = self.config.mean_reversion_strength * (
            np.log(self.config.initial_price) - np.log(self.price)
        )
        
        # GBM step
        dt = 1.0
        drift_term = (self.config.drift + mean_reversion) * dt
        vol_term = self.config.volatility * np.sqrt(dt) * self.rng.standard_normal()
        
        self.price *= np.exp(drift_term + vol_term)
        
        # Ensure price stays positive and reasonable
        self.price = max(self.price, 100.0)
        
        return self.price
    
    def _extract_digit(self, price: float) -> int:
        """Extract last digit from price with optional bias"""
        price_str = f"{price:.4f}"
        digit = int(price_str[-1])
        
        if self.config.digit_bias:
            # Apply bias by potentially re-rolling
            if self.rng.random() < self.config.digit_bias.get(digit, 0):
                digit = self.rng.randint(0, 9)
        
        return digit
    
    def _apply_slippage(self, price: float) -> float:
        """Apply random slippage to execution price"""
        slippage = self.rng.normal(0, self.config.slippage_std)
        return price * (1 + slippage)
    
    def generate_ticks(self, num_ticks: Optional[int] = None) -> List[Dict[str, Any]]:
        """Generate a sequence of ticks"""
        n = num_ticks or self.config.num_ticks
        self.ticks = []
        
        for i in range(n):
            price = self._generate_next_price()
            digit = self._extract_digit(price)
            
            tick = {
                "tick": i,
                "price": price,
                "digit": digit,
                "timestamp": i,
                "symbol": self.config.symbol,
                "regime": self.current_regime.value,
                "spread": price * self.config.spread,
                "slippage": self._apply_slippage(price) - price,
            }
            self.ticks.append(tick)
            self.current_tick = i
        
        return self.ticks
    
    def get_price_at_tick(self, tick_index: int) -> float:
        """Get price at specific tick with latency adjustment"""
        adjusted_index = min(tick_index + self.config.latency_ticks, len(self.ticks) - 1)
        if adjusted_index < len(self.ticks):
            return self.ticks[adjusted_index]["price"]
        return self.ticks[-1]["price"] if self.ticks else self.config.initial_price


class MultiMarketSimulator:
    """Simulate multiple synthetic indices simultaneously"""
    
    SYMBOLS = ["R_10", "R_25", "R_50", "R_75", "R_100"]
    
    @classmethod
    def create_simulators(cls, num_ticks: int = 10000) -> Dict[str, MarketSimulator]:
        """Create simulators for all synthetic indices"""
        simulators = {}
        
        configs = {
            "R_10": SimulationConfig(symbol="R_10", volatility=0.01, initial_price=1000.0, num_ticks=num_ticks),
            "R_25": SimulationConfig(symbol="R_25", volatility=0.015, initial_price=2500.0, num_ticks=num_ticks),
            "R_50": SimulationConfig(symbol="R_50", volatility=0.02, initial_price=5000.0, num_ticks=num_ticks),
            "R_75": SimulationConfig(symbol="R_75", volatility=0.025, initial_price=7500.0, num_ticks=num_ticks),
            "R_100": SimulationConfig(symbol="R_100", volatility=0.03, initial_price=10000.0, num_ticks=num_ticks),
        }
        
        for symbol, config in configs.items():
            simulators[symbol] = MarketSimulator(config)
        
        return simulators
