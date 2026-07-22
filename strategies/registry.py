"""
Strategy Registry — lifecycle management for trading strategies.

Handles creation, enable/disable, hot-swap, and state persistence
for all strategy instances.  The marketplace provides the metadata
and discovery layer; the registry provides the instance management.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from backtesting.strategy import BacktestStrategy

logger = logging.getLogger(__name__)


class StrategyState(Enum):
    REGISTERED = "registered"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class StrategyInstance:
    name: str
    strategy: BacktestStrategy
    state: StrategyState = StrategyState.REGISTERED
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    last_signal_at: Optional[float] = None
    total_signals: int = 0
    total_trades: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "class": type(self.strategy).__name__,
            "state": self.state.value,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "last_signal_at": self.last_signal_at,
            "total_signals": self.total_signals,
            "total_trades": self.total_trades,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }


class StrategyRegistry:
    """
    Manages strategy instances for the trading system.

    Responsibilities:
    - Register / unregister strategy instances
    - Enable / disable individual strategies
    - Hot-swap the active strategy
    - Track per-strategy signal/trade/error counts
    - Provide state snapshot for the dashboard
    """

    def __init__(self):
        self._instances: Dict[str, StrategyInstance] = {}
        self._active_name: Optional[str] = None
        self._factory: Dict[str, Callable[[], BacktestStrategy]] = {}

    # ── Registration ───────────────────────────────────────────────────────

    def register(
        self,
        name: str,
        strategy: BacktestStrategy,
        *,
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StrategyInstance:
        instance = StrategyInstance(
            name=name,
            strategy=strategy,
            enabled=enabled,
            metadata=metadata or {},
        )
        self._instances[name] = instance
        logger.info("Registered strategy: %s", name)
        return instance

    def register_factory(
        self,
        name: str,
        factory: Callable[[], BacktestStrategy],
    ) -> None:
        self._factory[name] = factory

    def unregister(self, name: str) -> bool:
        if name in self._instances:
            del self._instances[name]
            if self._active_name == name:
                self._active_name = None
            logger.info("Unregistered strategy: %s", name)
            return True
        return False

    # ── Query ──────────────────────────────────────────────────────────────

    def get(self, name: str) -> Optional[StrategyInstance]:
        return self._instances.get(name)

    def get_strategy(self, name: str) -> Optional[BacktestStrategy]:
        inst = self._instances.get(name)
        return inst.strategy if inst else None

    def has(self, name: str) -> bool:
        return name in self._instances

    def list_all(self) -> List[Dict[str, Any]]:
        return [inst.to_dict() for inst in self._instances.values()]

    def list_enabled(self) -> List[StrategyInstance]:
        return [inst for inst in self._instances.values() if inst.enabled]

    @property
    def active_name(self) -> Optional[str]:
        return self._active_name

    @property
    def active_strategy(self) -> Optional[BacktestStrategy]:
        if self._active_name and self._active_name in self._instances:
            return self._instances[self._active_name].strategy
        return None

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def set_active(self, name: str) -> bool:
        if name not in self._instances:
            logger.warning("Cannot activate unknown strategy: %s", name)
            return False
        inst = self._instances[name]
        if not inst.enabled:
            logger.warning("Cannot activate disabled strategy: %s", name)
            return False
        self._active_name = name
        inst.state = StrategyState.ACTIVE
        logger.info("Active strategy: %s", name)
        return True

    def enable(self, name: str) -> bool:
        inst = self._instances.get(name)
        if inst is None:
            return False
        was_disabled = inst.state == StrategyState.DISABLED
        inst.enabled = True
        if was_disabled:
            inst.state = StrategyState.REGISTERED
        logger.info("Enabled strategy: %s", name)
        return True

    def disable(self, name: str) -> bool:
        inst = self._instances.get(name)
        if inst is None:
            return False
        inst.enabled = False
        inst.state = StrategyState.DISABLED
        if self._active_name == name:
            self._active_name = None
        logger.info("Disabled strategy: %s", name)
        return True

    def create_from_factory(self, name: str) -> Optional[StrategyInstance]:
        factory = self._factory.get(name)
        if factory is None:
            logger.warning("No factory for strategy: %s", name)
            return None
        try:
            strategy = factory()
            return self.register(name, strategy)
        except Exception as e:
            logger.error("Failed to create strategy %s: %s", name, e)
            return None

    # ── Signal / Trade Tracking ────────────────────────────────────────────

    def record_signal(self, name: str) -> None:
        inst = self._instances.get(name)
        if inst:
            inst.total_signals += 1
            inst.last_signal_at = time.time()

    def record_trade(self, name: str) -> None:
        inst = self._instances.get(name)
        if inst:
            inst.total_trades += 1

    def record_error(self, name: str, error: str) -> None:
        inst = self._instances.get(name)
        if inst:
            inst.error_count += 1
            inst.last_error = error
            if inst.error_count >= 5:
                inst.state = StrategyState.ERROR
                logger.error("Strategy %s entered ERROR state after %d failures", name, inst.error_count)

    # ── State Snapshot ─────────────────────────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        return {
            "active_strategy": self._active_name,
            "strategies": self.list_all(),
            "enabled_count": len(self.list_enabled()),
            "total_count": len(self._instances),
        }

    def reset(self) -> None:
        self._instances.clear()
        self._active_name = None
        self._factory.clear()
