"""
Strategy SDK
============

SDK for building and running trading strategies.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from datetime import datetime

from .base import SmartPipSDK, SDKConfig, SDKError, SDKLogger

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """Order side"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Signal:
    """Trading signal"""
    symbol: str
    side: OrderSide
    strength: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "strength": self.strength,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class Order:
    """Trading order"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0
    average_price: float = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """Trading position"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float = 0
    unrealized_pnl: float = 0
    realized_pnl: float = 0
    opened_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_long(self) -> bool:
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        return self.quantity < 0


@dataclass
class StrategyContext:
    """Strategy execution context"""
    strategy_id: str
    timestamp: float
    portfolio_value: float
    positions: Dict[str, Position] = field(default_factory=dict)
    cash: float = 0
    available_margin: float = 0
    market_data: Dict[str, Any] = field(default_factory=dict)
    signals: List[Signal] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Strategy:
    """
    Base Strategy class.
    
    All trading strategies must inherit from this class.
    """
    
    strategy_id: str = ""
    strategy_name: str = "Base Strategy"
    version: str = "1.0.0"
    
    def __init__(self):
        self._enabled = False
        self._config: Dict[str, Any] = {}
        self._state: Dict[str, Any] = {}
        self._logger = logging.getLogger(f"strategy.{self.strategy_name}")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the strategy"""
        self._config.update(config)
        self._on_configure()
    
    def _on_configure(self) -> None:
        """Override to handle configuration"""
        pass
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)
    
    def on_init(self) -> None:
        """Called when strategy is initialized"""
        self._logger.info(f"Initializing strategy: {self.strategy_name}")
    
    def on_tick(self, tick: Dict[str, Any], context: StrategyContext) -> List[Signal]:
        """
        Called on each market tick.
        
        Override this method to implement your trading logic.
        
        Args:
            tick: Current market tick data
            context: Strategy context with positions, portfolio info
            
        Returns:
            List of trading signals
        """
        return []
    
    def on_bar(self, bar: Dict[str, Any], context: StrategyContext) -> List[Signal]:
        """
        Called on each bar/candle.
        
        Override this method for bar-based strategies.
        """
        return []
    
    def on_signal(self, signal: Signal, context: StrategyContext) -> Optional[Order]:
        """
        Called when a signal should be converted to an order.
        
        Override to customize order placement.
        """
        return None
    
    def on_order_update(self, order: Order) -> None:
        """Called when an order is updated"""
        pass
    
    def on_position_update(self, position: Position) -> None:
        """Called when a position is updated"""
        pass
    
    def on_pnl_update(self, pnl: float) -> None:
        """Called when P&L is updated"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters"""
        return self._config.copy()
    
    def set_state(self, key: str, value: Any) -> None:
        """Set strategy state"""
        self._state[key] = value
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get strategy state"""
        return self._state.get(key, default)
    
    def reset_state(self) -> None:
        """Reset strategy state"""
        self._state.clear()


class StrategyRunner(SmartPipSDK):
    """
    Strategy runner for executing strategies.
    """
    
    def __init__(self, config: Optional[SDKConfig] = None):
        super().__init__(config)
        self._strategies: Dict[str, Strategy] = {}
        self._active_strategy: Optional[Strategy] = None
        self._running = False
        self._tick_callbacks: List[Callable] = []
    
    def _on_initialize(self) -> None:
        """Initialize strategy runner"""
        pass
    
    def register_strategy(self, strategy: Strategy) -> None:
        """Register a strategy"""
        if not strategy.strategy_id:
            raise SDKError("Strategy must have an ID")
        
        self._strategies[strategy.strategy_id] = strategy
        self._logger.info(f"Registered strategy: {strategy.strategy_name}")
    
    def unregister_strategy(self, strategy_id: str) -> bool:
        """Unregister a strategy"""
        if strategy_id in self._strategies:
            del self._strategies[strategy_id]
            return True
        return False
    
    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get a strategy by ID"""
        return self._strategies.get(strategy_id)
    
    def list_strategies(self) -> List[Dict[str, Any]]:
        """List all registered strategies"""
        return [
            {
                "strategy_id": s.strategy_id,
                "name": s.strategy_name,
                "version": s.version,
            }
            for s in self._strategies.values()
        ]
    
    def set_active_strategy(self, strategy_id: str) -> bool:
        """Set the active strategy"""
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False
        
        if self._active_strategy:
            self._active_strategy._enabled = False
        
        self._active_strategy = strategy
        strategy._enabled = True
        strategy.on_init()
        
        return True
    
    def get_active_strategy(self) -> Optional[Strategy]:
        """Get the active strategy"""
        return self._active_strategy
    
    def on_tick(self, tick: Dict[str, Any], context: StrategyContext) -> List[Signal]:
        """Process a tick with active strategy"""
        if not self._active_strategy or not self._active_strategy._enabled:
            return []
        
        signals = self._active_strategy.on_tick(tick, context)
        
        # Trigger callbacks
        for callback in self._tick_callbacks:
            try:
                callback(tick, signals)
            except Exception as e:
                self._logger.error(f"Tick callback error: {e}")
        
        return signals
    
    def on_bar(self, bar: Dict[str, Any], context: StrategyContext) -> List[Signal]:
        """Process a bar with active strategy"""
        if not self._active_strategy or not self._active_strategy._enabled:
            return []
        
        return self._active_strategy.on_bar(bar, context)
    
    def register_tick_callback(self, callback: Callable) -> None:
        """Register a tick callback"""
        self._tick_callbacks.append(callback)
    
    def start(self) -> None:
        """Start the strategy runner"""
        self._running = True
        self._logger.info("Strategy runner started")
    
    def stop(self) -> None:
        """Stop the strategy runner"""
        self._running = False
        if self._active_strategy:
            self._active_strategy._enabled = False
        self._logger.info("Strategy runner stopped")
    
    @property
    def is_running(self) -> bool:
        """Check if runner is running"""
        return self._running


def strategy(
    strategy_id: str,
    name: str,
    version: str = "1.0.0"
) -> Callable:
    """Decorator to create a strategy class"""
    
    def decorator(cls: type) -> type:
        cls.strategy_id = strategy_id
        cls.strategy_name = name
        cls.version = version
        return cls
    
    return decorator
