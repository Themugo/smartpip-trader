"""Strategy Registry — maps strategy IDs to classes with auto-discovery."""
from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .base import StrategyBase

logger = logging.getLogger(__name__)


class StrategyEntry:
    """Lightweight wrapper pairing a strategy class with its metadata."""

    __slots__ = ("strategy_id", "cls", "metadata")

    def __init__(
        self,
        strategy_id: str,
        cls: Type[Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.strategy_id = strategy_id
        self.cls = cls
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        base: Dict[str, Any] = {
            "strategy_id": self.strategy_id,
            "class_name": self.cls.__name__,
        }
        if self.metadata is not None:
            base["metadata"] = self.metadata.to_dict()
        return base

    def __repr__(self) -> str:  # pragma: no cover
        return (f"StrategyEntry(id={self.strategy_id!r}, "
                f"cls={self.cls.__name__!r})")


class StrategyRegistry:
    """Central registry mapping ``strategy_id`` → ``strategy_class``.

    The registry is intentionally lightweight: it stores *classes*, not
    instances.  Lifetime management of instances lives in the marketplace.
    """

    def __init__(self) -> None:
        self._entries: Dict[str, StrategyEntry] = {}
        self.logger = logging.getLogger(f"{__name__}.StrategyRegistry")
        self.logger.debug("StrategyRegistry created")

    # ---- public API -------------------------------------------------------

    def register(
        self,
        strategy_id: str,
        strategy_class: Type[Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register *strategy_class* under *strategy_id*.

        If *metadata* is ``None`` a minimal default is created.
        """
        entry = StrategyEntry(strategy_id, strategy_class, metadata)
        self._entries[strategy_id] = entry
        self.logger.info("Registered strategy '%s' (%s)", strategy_id,
                         strategy_class.__name__)

    def unregister(self, strategy_id: str) -> bool:
        """Remove a strategy from the registry.  Returns *True* if present."""
        if strategy_id in self._entries:
            del self._entries[strategy_id]
            self.logger.info("Unregistered strategy '%s'", strategy_id)
            return True
        self.logger.warning("Cannot unregister unknown strategy '%s'",
                            strategy_id)
        return False

    def get(self, strategy_id: str) -> Optional[Type[Any]]:
        """Return the class for *strategy_id* or ``None``."""
        entry = self._entries.get(strategy_id)
        return entry.cls if entry is not None else None

    def get_entry(self, strategy_id: str) -> Optional[StrategyEntry]:
        """Return the full ``StrategyEntry`` for *strategy_id* or ``None``."""
        return self._entries.get(strategy_id)

    def get_metadata(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Return metadata for *strategy_id* or ``None``."""
        entry = self._entries.get(strategy_id)
        return entry.metadata if entry is not None else None

    def list_all(self) -> List[str]:
        """Return all registered strategy IDs."""
        return list(self._entries.keys())

    def has(self, strategy_id: str) -> bool:
        return strategy_id in self._entries

    def count(self) -> int:
        return len(self._entries)

    def get_all_entries(self) -> List[Dict[str, Any]]:
        """Snapshot of every registered entry as dicts."""
        return [e.to_dict() for e in self._entries.values()]

    # ---- auto-discovery ---------------------------------------------------

    def discover_strategies(self, package_path: str) -> int:
        """Scan *package_path* for modules containing ``StrategyBase``
        subclasses and register each one found.

        *package_path* may be a filesystem directory **or** a dotted Python
        package name.  Returns the number of newly registered strategies.
        """
        resolved = self._resolve_package(package_path)
        if resolved is None:
            self.logger.error("Cannot resolve package path '%s'",
                              package_path)
            return 0

        pkg_path: Path = resolved
        pkg_name = self._path_to_module(pkg_path)
        if pkg_name is None:
            self.logger.error("Cannot determine module name for '%s'",
                              pkg_path)
            return 0

        discovered = 0
        for _importer, modname, _ispkg in pkgutil.iter_modules(
            [str(pkg_path)]
        ):
            full_name = f"{pkg_name}.{modname}"
            try:
                module = importlib.import_module(full_name)
            except Exception:
                self.logger.exception("Failed to import '%s'", full_name)
                continue

            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, StrategyBase)
                    and obj is not StrategyBase
                ):
                    sid = getattr(obj, "STRATEGY_ID", None) or attr_name.lower()
                    if not self.has(sid):
                        self.register(sid, obj)
                        discovered += 1
                        self.logger.info("Discovered strategy '%s' from %s",
                                         sid, full_name)

        self.logger.info("Discovery complete: %d new strategies from '%s'",
                         discovered, package_path)
        return discovered

    # ---- query helpers ----------------------------------------------------

    def filter_by_category(self, category: str) -> List[str]:
        """Return strategy IDs whose class CATEGORY matches *category*."""
        results: List[str] = []
        for sid, entry in self._entries.items():
            cat = getattr(entry.cls, "CATEGORY", None)
            if cat == category:
                results.append(sid)
        return results

    def get_all_categories(self) -> List[str]:
        """Return de-duplicated list of all registered categories."""
        seen: set = set()
        cats: List[str] = []
        for entry in self._entries.values():
            cat = getattr(entry.cls, "CATEGORY", "general")
            if cat not in seen:
                seen.add(cat)
                cats.append(cat)
        return cats

    def reload_strategy(self, strategy_id: str) -> bool:
        """Re-import the module that provides *strategy_id* and re-register.

        Useful during development when a strategy class has been modified
        on disk.  Returns *True* on success.
        """
        entry = self._entries.get(strategy_id)
        if entry is None:
            self.logger.warning("Cannot reload unknown strategy '%s'",
                                strategy_id)
            return False
        module = inspect.getmodule(entry.cls)
        if module is None:
            self.logger.error("Cannot determine module for '%s'",
                              strategy_id)
            return False
        try:
            reloaded = importlib.reload(module)
        except Exception:
            self.logger.exception("Failed to reload module for '%s'",
                                  strategy_id)
            return False
        new_cls = getattr(reloaded, entry.cls.__name__, None)
        if new_cls is None:
            self.logger.error("Class %s not found after reload",
                              entry.cls.__name__)
            return False
        entry.cls = new_cls
        self.logger.info("Reloaded strategy '%s'", strategy_id)
        return True

    def validate(self) -> Dict[str, List[str]]:
        """Validate every registered entry.  Returns a dict of
        ``strategy_id → [issues]`` with empty lists for healthy entries."""
        issues: Dict[str, List[str]] = {}
        for sid, entry in self._entries.items():
            entry_issues: List[str] = []
            if not inspect.isclass(entry.cls):
                entry_issues.append("cls is not a class")
            if not getattr(entry.cls, "STRATEGY_ID", None):
                entry_issues.append("STRATEGY_ID class attr is empty")
            if not getattr(entry.cls, "__abstractmethods__", None) is not None:
                pass  # abstract methods only present on ABCs
            if hasattr(entry.cls, "generate_signal"):
                pass  # expected
            else:
                entry_issues.append("Missing generate_signal method")
            issues[sid] = entry_issues
        return issues

    # ---- internal helpers -------------------------------------------------

    @staticmethod
    def _resolve_package(path_str: str) -> Optional[Path]:
        """Return a ``Path`` that is a real directory."""
        candidate = Path(path_str)
        if candidate.is_dir():
            return candidate
        candidate = Path.cwd() / path_str
        if candidate.is_dir():
            return candidate
        return None

    @staticmethod
    def _path_to_module(path: Path) -> Optional[str]:
        """Best-effort conversion of a filesystem path to a dotted module
        name.  Returns ``None`` on failure."""
        parts: List[str] = []
        current: Optional[Path] = path.resolve()
        while current is not None:
            init = current / "__init__.py"
            if not init.exists():
                break
            parts.append(current.name)
            current = current.parent
        if not parts:
            return None
        return ".".join(reversed(parts))

    # ---- dunder helpers ---------------------------------------------------

    def __contains__(self, strategy_id: str) -> bool:
        return self.has(strategy_id)

    def __len__(self) -> int:
        return self.count()

    def __repr__(self) -> str:  # pragma: no cover
        return f"StrategyRegistry(entries={self.count()})"
