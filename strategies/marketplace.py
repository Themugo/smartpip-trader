"""
Strategy Marketplace — discovery, metadata, and hot-swap for strategies.

Wraps the existing strategy classes with rich metadata, auto-discovers
all strategies in the ``strategies`` package, and exposes a single
API for the frontend / trading_system to query and switch strategies.
"""

from __future__ import annotations

import copy
import importlib
import logging
import pkgutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from backtesting.strategy import BacktestStrategy

logger = logging.getLogger(__name__)


class StrategyRisk(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StrategyCategory(Enum):
    TREND = "trend"
    MEAN_REVERSION = "mean_reversion"
    GRID = "grid"
    MOMENTUM = "momentum"
    COMPOSITE = "composite"
    OTHER = "other"


@dataclass
class StrategyMeta:
    name: str
    class_name: str
    description: str
    category: StrategyCategory
    risk: StrategyRisk
    expected_win_rate: float  # 0-100%
    min_data_points: int
    uses_ml: bool
    uses_indicators: bool
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = "SmartPip"
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "class_name": self.class_name,
            "description": self.description,
            "category": self.category.value,
            "risk": self.risk.value,
            "expected_win_rate": self.expected_win_rate,
            "min_data_points": self.min_data_points,
            "uses_ml": self.uses_ml,
            "uses_indicators": self.uses_indicators,
            "tags": self.tags,
            "version": self.version,
            "author": self.author,
            "enabled": self.enabled,
        }


# ── Built-in strategy metadata ────────────────────────────────────────────

_BUILTIN_META: Dict[str, StrategyMeta] = {
    "grid": StrategyMeta(
        name="grid",
        class_name="GridStrategy",
        description="Places trades at regular price intervals. Profits from oscillating markets.",
        category=StrategyCategory.GRID,
        risk=StrategyRisk.LOW,
        expected_win_rate=55.0,
        min_data_points=1,
        uses_ml=False,
        uses_indicators=False,
        tags=["grid", "range", "oscillation"],
    ),
    "martingale": StrategyMeta(
        name="martingale",
        class_name="MartingaleStrategy",
        description="Doubles position size after a loss to recover. High risk, high reward.",
        category=StrategyCategory.MOMENTUM,
        risk=StrategyRisk.HIGH,
        expected_win_rate=50.0,
        min_data_points=30,
        uses_ml=False,
        uses_indicators=False,
        tags=["martingale", "recovery", "aggressive"],
    ),
    "anti_martingale": StrategyMeta(
        name="anti_martingale",
        class_name="AntiMartingaleStrategy",
        description="Increases position size after wins to ride streaks. Safer than martingale.",
        category=StrategyCategory.MOMENTUM,
        risk=StrategyRisk.MEDIUM,
        expected_win_rate=55.0,
        min_data_points=30,
        uses_ml=False,
        uses_indicators=False,
        tags=["anti-martingale", "streak", "momentum"],
    ),
    "sniper": StrategyMeta(
        name="sniper",
        class_name="SniperStrategy",
        description="High-precision entries requiring multi-indicator confluence. Selective but accurate.",
        category=StrategyCategory.COMPOSITE,
        risk=StrategyRisk.LOW,
        expected_win_rate=65.0,
        min_data_points=50,
        uses_ml=False,
        uses_indicators=True,
        tags=["precision", "confluence", "selective"],
    ),
    "hft": StrategyMeta(
        name="hft",
        class_name="HFTStrategy",
        description="Ultra-fast execution capturing micro price movements. Latency-sensitive.",
        category=StrategyCategory.MOMENTUM,
        risk=StrategyRisk.MEDIUM,
        expected_win_rate=58.0,
        min_data_points=20,
        uses_ml=False,
        uses_indicators=True,
        tags=["hft", "latency", "fast", "tick-level"],
    ),
    "unified": StrategyMeta(
        name="unified",
        class_name="UnifiedStrategy",
        description="Ensemble of all analyzers with adaptive weights and entropy gating.",
        category=StrategyCategory.COMPOSITE,
        risk=StrategyRisk.LOW,
        expected_win_rate=62.0,
        min_data_points=20,
        uses_ml=True,
        uses_indicators=True,
        tags=["ensemble", "adaptive", "entropy", "composite"],
    ),
}


class StrategyMarketplace:
    """
    Central discovery and metadata layer for trading strategies.

    Features:
    - Auto-discovers all ``BacktestStrategy`` subclasses in ``strategies/``
    - Provides rich metadata for each strategy
    - Supports hot-swap (switch the active strategy at runtime)
    - Integrates with ``StrategyRegistry`` for instance management
    - Exposes a clean API for the frontend dashboard
    """

    def __init__(self):
        self._meta: Dict[str, StrategyMeta] = copy.deepcopy(_BUILTIN_META)
        self._registry: Optional[Any] = None  # StrategyRegistry, set lazily
        self._discover()

    # ── Registry binding ───────────────────────────────────────────────────

    def set_registry(self, registry: Any) -> None:
        self._registry = registry

    # ── Discovery ──────────────────────────────────────────────────────────

    def _discover(self) -> None:
        """Auto-import the ``strategies`` package to ensure all subclasses
        are registered with Python's MRO."""
        try:
            import strategies as _pkg  # noqa: F401
        except ImportError as exc:
            logger.warning("Could not import strategies package: %s", exc)
            return

        # Walk submodules and import any we haven't covered in _BUILTIN_META
        for _importer, modname, _ispkg in pkgutil.iter_modules(_pkg.__path__):
            if modname.startswith("_") or modname in ("adaptive_strategy_manager", "registry", "marketplace"):
                continue
            try:
                importlib.import_module(f"strategies.{modname}")
            except Exception as exc:
                logger.debug("Skipped strategies.%s: %s", modname, exc)

        # Scan for BacktestStrategy subclasses not yet in _BUILTIN_META
        from backtesting.strategy import BacktestStrategy as _BS
        for cls in _BS.__subclasses__():
            key = getattr(cls, "name", None)
            if key and isinstance(key, str):
                key = key.lower()
            if key and key not in self._meta:
                self._meta[key] = StrategyMeta(
                    name=key,
                    class_name=cls.__name__,
                    description=f"Auto-discovered strategy: {cls.__name__}",
                    category=StrategyCategory.OTHER,
                    risk=StrategyRisk.MEDIUM,
                    expected_win_rate=50.0,
                    min_data_points=20,
                    uses_ml=False,
                    uses_indicators=False,
                    tags=["auto-discovered"],
                )

    # ── Query ──────────────────────────────────────────────────────────────

    def get_meta(self, name: str) -> Optional[StrategyMeta]:
        return self._meta.get(name)

    def list_all(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._meta.values()]

    def list_enabled(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._meta.values() if m.enabled]

    def list_by_category(self, category: StrategyCategory) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._meta.values() if m.category == category]

    def list_by_risk(self, risk: StrategyRisk) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._meta.values() if m.risk == risk]

    def search(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        return [
            m.to_dict()
            for m in self._meta.values()
            if q in m.name.lower()
            or q in m.class_name.lower()
            or q in m.description.lower()
            or any(q in tag for tag in m.tags)
        ]

    # ── Enable / Disable ───────────────────────────────────────────────────

    def enable_strategy(self, name: str) -> bool:
        meta = self._meta.get(name)
        if meta is None:
            return False
        meta.enabled = True
        if self._registry:
            self._registry.enable(name)
        return True

    def disable_strategy(self, name: str) -> bool:
        meta = self._meta.get(name)
        if meta is None:
            return False
        meta.enabled = False
        if self._registry:
            self._registry.disable(name)
        return True

    # ── Hot-swap ───────────────────────────────────────────────────────────

    def activate(self, name: str) -> bool:
        """Switch the active strategy at runtime."""
        meta = self._meta.get(name)
        if meta is None:
            logger.warning("Unknown strategy: %s", name)
            return False
        if not meta.enabled:
            logger.warning("Cannot activate disabled strategy: %s", name)
            return False
        if self._registry:
            return self._registry.set_active(name)
        return False

    # ── Create instance ────────────────────────────────────────────────────

    def create_strategy(self, name: str, **kwargs: Any) -> Optional[BacktestStrategy]:
        """Instantiate a strategy by name with optional constructor kwargs."""
        meta = self._meta.get(name)
        if meta is None:
            logger.warning("Unknown strategy: %s", name)
            return None

        try:
            import strategies as _pkg
            cls = getattr(_pkg, meta.class_name, None)
            if cls is None:
                # Try importing directly
                mod = importlib.import_module(f"strategies.{name}_strategy" if name != "unified" else "strategies.unified_strategy")
                cls = getattr(mod, meta.class_name)
            return cls(**kwargs) if kwargs else cls()
        except Exception as exc:
            logger.error("Failed to create strategy %s: %s", name, exc)
            return None

    # ── State ──────────────────────────────────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        return {
            "strategies": self.list_all(),
            "enabled_count": len(self.list_enabled()),
            "total_count": len(self._meta),
            "categories": [c.value for c in StrategyCategory],
            "risk_levels": [r.value for r in StrategyRisk],
        }
