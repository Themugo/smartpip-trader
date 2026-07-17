"""Strategy Marketplace — lifecycle management for strategies."""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Type

from .base import StrategyBase
from .registry import StrategyRegistry

logger = logging.getLogger(__name__)
_PERF_BUF_SIZE: int = 200


@dataclass
class StrategyInfo:
    """Lightweight metadata dict returned by marketplace queries."""
    strategy_id: str
    name: str
    category: str
    description: str
    version: str
    author: str = ""
    tags: List[str] = field(default_factory=list)
    risk_level: str = "medium"
    supported_markets: List[str] = field(default_factory=lambda: ["R_100"])
    min_balance: float = 100.0
    installed: bool = False
    active: bool = False
    installed_at: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CompatibilityCheck:
    """Result of a compatibility check for a strategy on a given market."""
    strategy_id: str
    market: str
    account_type: str
    compatible: bool
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class _PerformanceBuffer:
    """Fixed-size ring buffer of per-trade profits using a plain list."""

    __slots__ = ("_buf", "_head", "_full", "_maxlen")

    def __init__(self, maxlen: int = _PERF_BUF_SIZE) -> None:
        self._maxlen = maxlen
        self._buf: List[float] = [0.0] * maxlen
        self._head: int = 0
        self._full: bool = False

    def append(self, value: float) -> None:
        self._buf[self._head] = value
        self._head = (self._head + 1) % self._maxlen
        if self._head == 0:
            self._full = True

    @property
    def length(self) -> int:
        return self._maxlen if self._full else self._head

    def snapshot(self) -> List[float]:
        if self._full:
            return list(self._buf)
        return list(self._buf[:self._head])

    def to_dict(self) -> Dict[str, Any]:
        n = self.length
        if n == 0:
            return {"count": 0, "mean": 0.0, "std": 0.0, "sum": 0.0}
        data = self.snapshot()
        mean = sum(data) / n
        variance = sum((x - mean) ** 2 for x in data) / n
        std = variance ** 0.5
        return {"count": n, "mean": round(mean, 6), "std": round(std, 6),
                "sum": round(sum(data), 6), "min": min(data), "max": max(data)}


# Built-in catalog: (id, class, category, description, tags, risk_level)
_CATALOG: List[tuple] = []


def _load_catalog() -> List[tuple]:
    """Lazy-load so the strategies package is not imported at module level."""
    global _CATALOG
    if _CATALOG:
        return _CATALOG
    from strategies.grid_strategy import GridStrategy
    from strategies.martingale_strategy import MartingaleStrategy
    from strategies.anti_martingale_strategy import AntiMartingaleStrategy
    from strategies.sniper_strategy import SniperStrategy
    from strategies.hft_strategy import HFTStrategy
    from strategies.unified_strategy import UnifiedStrategy
    _CATALOG = [
        ("grid",            GridStrategy,            "grid",
         "Grid trading with configurable spacing",
         ["grid", "range", "systematic"], "medium"),
        ("martingale",      MartingaleStrategy,      "progression",
         "Martingale progression with configurable max multiplier",
         ["martingale", "progression", "recovery"], "high"),
        ("anti_martingale", AntiMartingaleStrategy,  "progression",
         "Anti-martingale - increase size on winning streaks",
         ["anti-martingale", "progression", "momentum"], "medium"),
        ("sniper",          SniperStrategy,          "momentum",
         "High-precision selective entries via multi-indicator confluence",
         ["sniper", "precision", "confluence"], "low"),
        ("hft",             HFTStrategy,             "hft",
         "Ultra-fast high-frequency trading with latency gating",
         ["hft", "scalping", "latency"], "high"),
        ("unified",         UnifiedStrategy,         "hybrid",
         "Adaptive-weight hybrid combining all analyzers with entropy gating",
         ["unified", "adaptive", "hybrid", "entropy"], "medium"),
    ]
    return _CATALOG


class StrategyMarketplace:
    """Manages strategy lifecycle: install, enable, disable, update,
    remove, search, and persistence.  Includes a built-in catalog of
    six first-party strategies."""

    def __init__(self, registry: Optional[StrategyRegistry] = None) -> None:
        self._registry = registry if registry is not None else StrategyRegistry()
        self._instances: Dict[str, Any] = {}
        self._info: Dict[str, StrategyInfo] = {}
        self._perf: Dict[str, _PerformanceBuffer] = {}
        self._install_order: Deque[str] = deque()
        self.logger = logging.getLogger(f"{__name__}.StrategyMarketplace")
        self._populate_builtin_catalog()

    # ---- built-in catalog -------------------------------------------------

    def _populate_builtin_catalog(self) -> None:
        for sid, cls, cat, desc, tags, risk in _load_catalog():
            info = StrategyInfo(
                strategy_id=sid, name=cls.__name__, category=cat,
                description=desc, version=getattr(cls, "VERSION", "1.0.0"),
                author=getattr(cls, "AUTHOR", ""), tags=tags,
                risk_level=risk,
                supported_markets=list(
                    getattr(cls, "SUPPORTED_MARKETS", ["R_100"])),
                min_balance=float(getattr(cls, "MIN_BALANCE", 100.0)),
            )
            self._info[sid] = info
            self._registry.register(sid, cls)
            self._perf[sid] = _PerformanceBuffer()
        self.logger.info("Built-in catalog populated (%d strategies)",
                         len(self._info))

    # ---- install / uninstall ----------------------------------------------

    @staticmethod
    def _instantiate(cls: Type[Any], strategy_id: str,
                     config: Optional[Dict[str, Any]] = None) -> Any:
        """Try to create an instance of *cls* by probing its __init__ sig."""
        import inspect as _inspect
        sig = _inspect.signature(cls.__init__)
        params = list(sig.parameters.keys())
        # Skip 'self'
        params = [p for p in params if p != "self"]
        kwargs: Dict[str, Any] = {}
        if "strategy_id" in params:
            kwargs["strategy_id"] = strategy_id
        if "config" in params:
            kwargs["config"] = config or {}
        elif "name" in params:
            kwargs["name"] = strategy_id
        try:
            return cls(**kwargs)
        except TypeError:
            return cls()

    def install_strategy(self, strategy_class: Type[Any],
                         config: Optional[Dict[str, Any]] = None) -> StrategyInfo:
        # Try to find an existing catalog entry for this class
        sid = None
        for existing_sid, info in self._info.items():
            if info.name == strategy_class.__name__:
                sid = existing_sid
                break
        if sid is None:
            sid = getattr(strategy_class, "STRATEGY_ID", None) \
                  or strategy_class.__name__.lower()
        if sid in self._instances:
            self.logger.warning("Strategy '%s' already installed", sid)
            return self._info[sid]
        instance = self._instantiate(strategy_class, sid, config)
        if hasattr(instance, "initialize"):
            result = instance.initialize()
            if result is False:
                self.logger.error("Strategy '%s' init returned False", sid)
        self._instances[sid] = instance
        self._install_order.append(sid)
        if sid not in self._info:
            self._info[sid] = StrategyInfo(
                strategy_id=sid, name=strategy_class.__name__,
                category=getattr(strategy_class, "CATEGORY", "general"),
                description=getattr(strategy_class, "DESCRIPTION", ""),
                version=getattr(strategy_class, "VERSION", "1.0.0"),
                tags=list(getattr(strategy_class, "TAGS", [])),
                risk_level=getattr(strategy_class, "RISK_LEVEL", "medium"),
            )
        self._info[sid].installed = True
        self._info[sid].active = True
        self._info[sid].installed_at = datetime.utcnow().isoformat()
        self._perf.setdefault(sid, _PerformanceBuffer())
        self.logger.info("Installed strategy '%s'", sid)
        return self._info[sid]

    def uninstall_strategy(self, strategy_id: str) -> bool:
        if strategy_id not in self._instances:
            self.logger.warning("Cannot uninstall '%s' - not installed",
                                strategy_id)
            return False
        inst = self._instances.pop(strategy_id)
        if hasattr(inst, "cleanup"):
            inst.cleanup()
        self._install_order = deque(
            s for s in self._install_order if s != strategy_id)
        if strategy_id in self._info:
            self._info[strategy_id].installed = False
            self._info[strategy_id].active = False
        self.logger.info("Uninstalled strategy '%s'", strategy_id)
        return True

    # ---- enable / disable -------------------------------------------------

    def enable_strategy(self, strategy_id: str) -> bool:
        if strategy_id not in self._info:
            self.logger.warning("Unknown strategy '%s'", strategy_id)
            return False
        if not self._info[strategy_id].installed:
            self.logger.warning("Strategy '%s' not installed", strategy_id)
            return False
        self._info[strategy_id].active = True
        self.logger.info("Enabled strategy '%s'", strategy_id)
        return True

    def disable_strategy(self, strategy_id: str) -> bool:
        if strategy_id not in self._info:
            return False
        self._info[strategy_id].active = False
        self.logger.info("Disabled strategy '%s'", strategy_id)
        return True

    # ---- config hot-update ------------------------------------------------

    def update_strategy(self, strategy_id: str,
                        config: Dict[str, Any]) -> bool:
        if strategy_id not in self._instances:
            self.logger.warning("Strategy '%s' not installed", strategy_id)
            return False
        inst = self._instances[strategy_id]
        if hasattr(inst, "update_config"):
            inst.update_config(config)
        elif hasattr(inst, "_config"):
            inst._config.update(config)
        self._info[strategy_id].config = config
        self.logger.info("Updated config for '%s'", strategy_id)
        return True

    # ---- getters ----------------------------------------------------------

    def get_strategy(self, strategy_id: str) -> Optional[Any]:
        return self._instances.get(strategy_id)

    def get_all_strategies(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for sid, info in self._info.items():
            entry = info.to_dict()
            entry["performance"] = self._perf.get(
                sid, _PerformanceBuffer()).to_dict()
            results.append(entry)
        return results

    def get_installed_strategies(self) -> List[Dict[str, Any]]:
        return [s for s in self.get_all_strategies() if s.get("installed")]

    def get_available_strategies(self) -> List[Dict[str, Any]]:
        return [s for s in self.get_all_strategies() if not s.get("installed")]

    # ---- search -----------------------------------------------------------

    def search_strategies(self, query: str,
                          category: Optional[str] = None) -> List[Dict[str, Any]]:
        q = query.lower()
        results: List[Dict[str, Any]] = []
        for info in self._info.values():
            if category and info.category != category:
                continue
            haystack = (f"{info.name.lower()} {info.description.lower()} "
                        f"{' '.join(info.tags)}")
            if q in haystack:
                entry = info.to_dict()
                entry["performance"] = self._perf.get(
                    info.strategy_id, _PerformanceBuffer()).to_dict()
                results.append(entry)
        return results

    # ---- stats ------------------------------------------------------------

    def get_marketplace_stats(self) -> Dict[str, Any]:
        installed = sum(1 for m in self._info.values() if m.installed)
        active = sum(1 for m in self._info.values() if m.active)
        by_cat: Dict[str, int] = {}
        for m in self._info.values():
            by_cat[m.category] = by_cat.get(m.category, 0) + 1
        return {
            "total_known": len(self._info), "installed": installed,
            "active": active, "available": len(self._info) - installed,
            "by_category": by_cat,
        }

    # ---- compatibility ----------------------------------------------------

    def check_compatibility(self, strategy_id: str, market: str,
                            account_type: str) -> CompatibilityCheck:
        info = self._info.get(strategy_id)
        if info is None:
            return CompatibilityCheck(strategy_id, market, account_type,
                                      False, ["Strategy not found"])
        reasons: List[str] = []
        compatible = True
        if market not in info.supported_markets:
            compatible = False
            reasons.append(
                f"Market '{market}' not in {info.supported_markets}")
        risk_map = {"demo": "high", "real": "low", "cent": "medium"}
        max_risk = risk_map.get(account_type, "low")
        risk_order = {"low": 0, "medium": 1, "high": 2}
        if risk_order.get(info.risk_level, 2) > risk_order.get(max_risk, 0):
            compatible = False
            reasons.append(
                f"Risk '{info.risk_level}' exceeds '{max_risk}' "
                f"for {account_type}")
        if compatible:
            reasons.append("Strategy is compatible")
        return CompatibilityCheck(strategy_id, market, account_type,
                                  compatible, reasons)

    # ---- performance recording --------------------------------------------

    def record_trade(self, strategy_id: str, profit: float) -> None:
        buf = self._perf.setdefault(strategy_id, _PerformanceBuffer())
        buf.append(profit)
        inst = self._instances.get(strategy_id)
        if inst is not None and hasattr(inst, "on_trade_closed"):
            try:
                inst.on_trade_closed(profit)
            except Exception:
                pass  # best-effort; not all strategy types accept this

    def get_performance(self, strategy_id: str) -> Dict[str, Any]:
        buf = self._perf.get(strategy_id)
        return buf.to_dict() if buf is not None else {"count": 0}

    # ---- persistence ------------------------------------------------------

    def save(self, path: str) -> None:
        import joblib
        snapshot: Dict[str, Any] = {
            "info": {s: i.to_dict() for s, i in self._info.items()},
            "config": {s: getattr(inst, "_config", {})
                       for s, inst in self._instances.items()},
            "perf": {s: b.snapshot() for s, b in self._perf.items()},
            "install_order": list(self._install_order),
            "saved_at": datetime.utcnow().isoformat(),
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(snapshot, path)
        self.logger.info("Marketplace saved to '%s'", path)

    def load(self, path: str) -> None:
        import joblib
        snapshot: Dict[str, Any] = joblib.load(path)
        for sid, md in snapshot.get("info", {}).items():
            self._info[sid] = StrategyInfo(**md)
        for sid, cfg in snapshot.get("config", {}).items():
            cls = self._registry.get(sid)
            if cls is not None and sid not in self._instances:
                inst = cls(config=cfg)
                inst.initialize()
                self._instances[sid] = inst
                self._info[sid].active = True
        for sid, vals in snapshot.get("perf", {}).items():
            buf = _PerformanceBuffer()
            for v in vals:
                buf.append(v)
            self._perf[sid] = buf
        self._install_order = deque(snapshot.get("install_order", []))
        self.logger.info("Marketplace loaded from '%s'", path)

    # ---- dunder -----------------------------------------------------------

    def __len__(self) -> int:
        return len(self._info)

    def __contains__(self, strategy_id: str) -> bool:
        return strategy_id in self._info

    def __repr__(self) -> str:  # pragma: no cover
        s = self.get_marketplace_stats()
        return (f"StrategyMarketplace(installed={s['installed']}, "
                f"active={s['active']}, total={s['total_known']})")
