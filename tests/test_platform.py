"""
Comprehensive tests for the Strategy Platform modules.

Tests:
- StrategyRegistry: register, lifecycle, tracking, state
- StrategyMarketplace: discovery, metadata, search, hot-swap
- Integration: registry + marketplace + trading_system compatibility
"""
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Prediction
from backtesting.strategy import BacktestStrategy
from strategies.registry import StrategyRegistry, StrategyState, StrategyInstance
from strategies.marketplace import StrategyMarketplace, StrategyMeta, StrategyCategory, StrategyRisk


# ── Helpers ────────────────────────────────────────────────────────────────

class DummyStrategy(BacktestStrategy):
    """Minimal concrete strategy for testing."""

    def __init__(self, name: str = "dummy"):
        super().__init__(name)
        self._fail_next = False

    def generate_signal(self, data: Dict[str, Any]) -> Optional[Prediction]:
        if self._fail_next:
            raise RuntimeError("boom")
        price = data.get("current_price", 0)
        if price <= 0:
            return None
        return Prediction(
            type="DUMMY",
            direction="CALL" if price > 100 else "PUT",
            confidence=80.0,
            reason="test",
        )


class FailingStrategy(BacktestStrategy):
    def __init__(self):
        super().__init__("failing")

    def generate_signal(self, data: Dict[str, Any]) -> Optional[Prediction]:
        raise RuntimeError("always fails")


# =====================================================================
# StrategyRegistry Tests
# =====================================================================
class TestStrategyRegistryRegister(unittest.TestCase):

    def setUp(self):
        self.registry = StrategyRegistry()

    def test_register_returns_instance(self):
        s = DummyStrategy("a")
        inst = self.registry.register("a", s)
        self.assertIsInstance(inst, StrategyInstance)
        self.assertEqual(inst.name, "a")
        self.assertIs(inst.strategy, s)

    def test_register_stores_instance(self):
        s = DummyStrategy("x")
        self.registry.register("x", s)
        self.assertTrue(self.registry.has("x"))
        self.assertIs(self.registry.get_strategy("x"), s)

    def test_register_duplicate_replaces(self):
        s1 = DummyStrategy("d")
        s2 = DummyStrategy("d")
        self.registry.register("d", s1)
        self.registry.register("d", s2)
        self.assertIs(self.registry.get_strategy("d"), s2)

    def test_unregister(self):
        self.registry.register("r", DummyStrategy("r"))
        self.assertTrue(self.registry.unregister("r"))
        self.assertFalse(self.registry.has("r"))

    def test_unregister_unknown_returns_false(self):
        self.assertFalse(self.registry.unregister("nope"))


class TestStrategyRegistryLifecycle(unittest.TestCase):

    def setUp(self):
        self.registry = StrategyRegistry()
        self.registry.register("a", DummyStrategy("a"))
        self.registry.register("b", DummyStrategy("b"))

    def test_set_active(self):
        self.assertTrue(self.registry.set_active("a"))
        self.assertEqual(self.registry.active_name, "a")
        self.assertIs(self.registry.active_strategy, self.registry.get_strategy("a"))

    def test_set_active_unknown_returns_false(self):
        self.assertFalse(self.registry.set_active("nope"))
        self.assertIsNone(self.registry.active_name)

    def test_set_active_disabled_returns_false(self):
        self.registry.disable("a")
        self.assertFalse(self.registry.set_active("a"))

    def test_enable_disable(self):
        self.assertTrue(self.registry.disable("a"))
        inst = self.registry.get("a")
        self.assertFalse(inst.enabled)
        self.assertEqual(inst.state, StrategyState.DISABLED)

        self.assertTrue(self.registry.enable("a"))
        self.assertTrue(inst.enabled)
        self.assertEqual(inst.state, StrategyState.REGISTERED)

    def test_disable_active_clears_active(self):
        self.registry.set_active("a")
        self.registry.disable("a")
        self.assertIsNone(self.registry.active_name)

    def test_list_enabled(self):
        self.registry.disable("b")
        enabled = self.registry.list_enabled()
        self.assertEqual(len(enabled), 1)
        self.assertEqual(enabled[0].name, "a")


class TestStrategyRegistryTracking(unittest.TestCase):

    def setUp(self):
        self.registry = StrategyRegistry()
        self.registry.register("t", DummyStrategy("t"))

    def test_record_signal(self):
        self.registry.record_signal("t")
        inst = self.registry.get("t")
        self.assertEqual(inst.total_signals, 1)
        self.assertIsNotNone(inst.last_signal_at)

    def test_record_trade(self):
        self.registry.record_trade("t")
        self.assertEqual(self.registry.get("t").total_trades, 1)

    def test_record_error_increments(self):
        self.registry.record_error("t", "e1")
        self.registry.record_error("t", "e2")
        inst = self.registry.get("t")
        self.assertEqual(inst.error_count, 2)
        self.assertEqual(inst.last_error, "e2")

    def test_record_error_triggers_error_state(self):
        for i in range(5):
            self.registry.record_error("t", f"err{i}")
        self.assertEqual(self.registry.get("t").state, StrategyState.ERROR)


class TestStrategyRegistryFactory(unittest.TestCase):

    def test_create_from_factory(self):
        reg = StrategyRegistry()
        reg.register_factory("f", lambda: DummyStrategy("f"))
        inst = reg.create_from_factory("f")
        self.assertIsNotNone(inst)
        self.assertTrue(reg.has("f"))

    def test_create_from_factory_unknown_returns_none(self):
        reg = StrategyRegistry()
        self.assertIsNone(reg.create_from_factory("nope"))

    def test_create_from_factory_exception(self):
        reg = StrategyRegistry()
        def bad_factory():
            raise Exception("x")
        reg.register_factory("bad", bad_factory)
        inst = reg.create_from_factory("bad")
        self.assertIsNone(inst)


class TestStrategyRegistryState(unittest.TestCase):

    def test_get_state(self):
        reg = StrategyRegistry()
        reg.register("s1", DummyStrategy("s1"))
        reg.register("s2", DummyStrategy("s2"))
        reg.disable("s2")
        state = reg.get_state()
        self.assertEqual(state["total_count"], 2)
        self.assertEqual(state["enabled_count"], 1)
        self.assertIsNone(state["active_strategy"])

    def test_reset(self):
        reg = StrategyRegistry()
        reg.register("x", DummyStrategy("x"))
        reg.set_active("x")
        reg.reset()
        self.assertEqual(len(reg.list_all()), 0)
        self.assertIsNone(reg.active_name)


# =====================================================================
# StrategyMarketplace Tests
# =====================================================================
class TestMarketplaceDiscovery(unittest.TestCase):

    def setUp(self):
        self.marketplace = StrategyMarketplace()

    def test_builtin_strategies_present(self):
        names = [m["name"] for m in self.marketplace.list_all()]
        for expected in ["grid", "martingale", "anti_martingale", "sniper", "hft", "unified"]:
            self.assertIn(expected, names)

    def test_total_count_at_least_6(self):
        self.assertGreaterEqual(len(self.marketplace.list_all()), 6)


class TestMarketplaceMeta(unittest.TestCase):

    def setUp(self):
        self.marketplace = StrategyMarketplace()

    def test_get_meta_grid(self):
        meta = self.marketplace.get_meta("grid")
        self.assertIsNotNone(meta)
        self.assertEqual(meta.class_name, "GridStrategy")
        self.assertEqual(meta.category, StrategyCategory.GRID)
        self.assertEqual(meta.risk, StrategyRisk.LOW)

    def test_get_meta_sniper(self):
        meta = self.marketplace.get_meta("sniper")
        self.assertIsNotNone(meta)
        self.assertTrue(meta.uses_indicators)
        self.assertFalse(meta.uses_ml)

    def test_get_meta_unified(self):
        meta = self.marketplace.get_meta("unified")
        self.assertTrue(meta.uses_ml)
        self.assertTrue(meta.uses_indicators)

    def test_get_meta_unknown_returns_none(self):
        self.assertIsNone(self.marketplace.get_meta("nonexistent"))


class TestMarketplaceSearch(unittest.TestCase):

    def setUp(self):
        self.marketplace = StrategyMarketplace()

    def test_search_by_name(self):
        results = self.marketplace.search("grid")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["name"], "grid")

    def test_search_by_tag(self):
        results = self.marketplace.search("precision")
        names = [r["name"] for r in results]
        self.assertIn("sniper", names)

    def test_search_by_description(self):
        results = self.marketplace.search("ensemble")
        names = [r["name"] for r in results]
        self.assertIn("unified", names)

    def test_search_no_match(self):
        results = self.marketplace.search("zzzzzzzzz")
        self.assertEqual(len(results), 0)


class TestMarketplaceFilter(unittest.TestCase):

    def setUp(self):
        self.marketplace = StrategyMarketplace()

    def test_list_by_category(self):
        grids = self.marketplace.list_by_category(StrategyCategory.GRID)
        self.assertEqual(len(grids), 1)
        self.assertEqual(grids[0]["name"], "grid")

    def test_list_by_risk(self):
        highs = self.marketplace.list_by_risk(StrategyRisk.HIGH)
        self.assertEqual(len(highs), 1)
        self.assertEqual(highs[0]["name"], "martingale")

    def test_list_enabled(self):
        self.marketplace.disable_strategy("grid")
        enabled = self.marketplace.list_enabled()
        names = [m["name"] for m in enabled]
        self.assertNotIn("grid", names)


class TestMarketplaceEnableDisable(unittest.TestCase):

    def setUp(self):
        self.marketplace = StrategyMarketplace()

    def test_disable_strategy(self):
        self.assertTrue(self.marketplace.disable_strategy("grid"))
        meta = self.marketplace.get_meta("grid")
        self.assertFalse(meta.enabled)

    def test_enable_strategy(self):
        self.marketplace.disable_strategy("grid")
        self.assertTrue(self.marketplace.enable_strategy("grid"))
        self.assertTrue(self.marketplace.get_meta("grid").enabled)

    def test_disable_unknown_returns_false(self):
        self.assertFalse(self.marketplace.disable_strategy("nope"))

    def test_enable_unknown_returns_false(self):
        self.assertFalse(self.marketplace.enable_strategy("nope"))


class TestMarketplaceRegistryBinding(unittest.TestCase):

    def test_activate_delegates_to_registry(self):
        mp = StrategyMarketplace()
        reg = StrategyRegistry()
        reg.register("grid", DummyStrategy("grid"))
        mp.set_registry(reg)

        self.assertTrue(mp.activate("grid"))
        self.assertEqual(reg.active_name, "grid")

    def test_activate_disabled_strategy_fails(self):
        mp = StrategyMarketplace()
        reg = StrategyRegistry()
        reg.register("grid", DummyStrategy("grid"))
        mp.set_registry(reg)
        mp.disable_strategy("grid")

        self.assertFalse(mp.activate("grid"))

    def test_disable_via_marketplace_updates_registry(self):
        mp = StrategyMarketplace()
        reg = StrategyRegistry()
        reg.register("grid", DummyStrategy("grid"))
        mp.set_registry(reg)
        mp.disable_strategy("grid")

        inst = reg.get("grid")
        self.assertFalse(inst.enabled)


class TestMarketplaceCreateStrategy(unittest.TestCase):

    def setUp(self):
        self.marketplace = StrategyMarketplace()

    def test_create_grid(self):
        s = self.marketplace.create_strategy("grid")
        self.assertIsNotNone(s)
        self.assertEqual(s.name, "grid")

    def test_create_unified(self):
        s = self.marketplace.create_strategy("unified")
        self.assertIsNotNone(s)
        self.assertEqual(s.name, "unified")

    def test_create_unknown_returns_none(self):
        self.assertIsNone(self.marketplace.create_strategy("nonexistent"))

    def test_create_with_kwargs(self):
        s = self.marketplace.create_strategy("grid", grid_size=0.005)
        self.assertIsNotNone(s)
        self.assertEqual(s.grid_size, 0.005)


class TestMarketplaceState(unittest.TestCase):

    def test_get_state(self):
        mp = StrategyMarketplace()
        state = mp.get_state()
        self.assertIn("strategies", state)
        self.assertIn("total_count", state)
        self.assertGreaterEqual(state["total_count"], 6)
        self.assertIn("categories", state)
        self.assertIn("risk_levels", state)


# =====================================================================
# Integration: Registry + Marketplace + TradingSystem Compatibility
# =====================================================================
class TestRegistryMarketplaceIntegration(unittest.TestCase):

    def test_full_workflow(self):
        mp = StrategyMarketplace()
        reg = StrategyRegistry()

        # Register all strategies that can be created
        created = 0
        for meta_info in mp.list_all():
            s = mp.create_strategy(meta_info["name"])
            if s:
                reg.register(meta_info["name"], s)
                created += 1

        self.assertGreater(created, 0)

        # Bind registry BEFORE any activate/disable/enable
        mp.set_registry(reg)

        # Activate grid (always works, no external deps)
        self.assertTrue(mp.activate("grid"))
        self.assertEqual(reg.active_name, "grid")

        # Disable it via marketplace — propagates to registry
        mp.disable_strategy("grid")
        self.assertIsNone(reg.active_name)

        # Re-enable and activate a different strategy
        mp.enable_strategy("grid")
        if reg.has("sniper"):
            self.assertTrue(mp.activate("sniper"))
            self.assertEqual(reg.active_name, "sniper")
        elif reg.has("hft"):
            self.assertTrue(mp.activate("hft"))
            self.assertEqual(reg.active_name, "hft")

        # Check state
        state = reg.get_state()
        self.assertIn(state["active_strategy"], ["sniper", "hft", "grid"])
        self.assertEqual(state["total_count"], created)


class TestTradingSystemCompatibility(unittest.TestCase):
    """Verify the registry/marketplace work with trading_system's expectations."""

    def test_registry_api_matches_trading_system_usage(self):
        """TradingSystem accesses strategies via registry.get_strategy(name).generate_signal(data)."""
        reg = StrategyRegistry()
        s = DummyStrategy("compat")
        reg.register("compat", s)
        reg.set_active("compat")

        strategy = reg.active_strategy
        self.assertIsNotNone(strategy)
        signal = strategy.generate_signal({"current_price": 150.0})
        self.assertIsNotNone(signal)
        self.assertEqual(signal.direction, "CALL")
        self.assertEqual(signal.type, "DUMMY")

    def test_strategy_generate_signal_returns_none_for_no_data(self):
        s = DummyStrategy("nodata")
        signal = s.generate_signal({"current_price": 0})
        self.assertIsNone(signal)

    def test_strategy_generate_signal_call_for_high_price(self):
        s = DummyStrategy("high")
        signal = s.generate_signal({"current_price": 150.0})
        self.assertIsNotNone(signal)
        self.assertEqual(signal.direction, "CALL")

    def test_strategy_generate_signal_put_for_low_price(self):
        s = DummyStrategy("low")
        signal = s.generate_signal({"current_price": 50.0})
        self.assertIsNotNone(signal)
        self.assertEqual(signal.direction, "PUT")

    def test_error_recording_doesnt_crash(self):
        reg = StrategyRegistry()
        reg.register("err", DummyStrategy("err"))
        reg.record_error("err", "test error")
        inst = reg.get("err")
        self.assertEqual(inst.error_count, 1)
        self.assertEqual(inst.last_error, "test error")


# =====================================================================
# core_platform Registry Tests (sanity)
# =====================================================================
class TestCorePlatformRegistry(unittest.TestCase):

    def test_singleton_behavior(self):
        from core_platform.registry import ServiceRegistry
        r1 = ServiceRegistry()
        r2 = ServiceRegistry()
        self.assertIs(r1, r2)

    def test_register_and_get(self):
        from core_platform.registry import ServiceRegistry
        r = ServiceRegistry()
        svc_cls = type("SVC", (), {"hello": lambda self: 42})
        r.register("test_svc", service_class=svc_cls)
        self.assertTrue(r.has("test_svc"))

    def test_validate_dependencies(self):
        from core_platform.registry import ServiceRegistry
        r = ServiceRegistry()
        r.register("a", dependencies=[])
        r.register("b", dependencies=["a"])
        missing = r.validate_dependencies()
        self.assertEqual(len(missing), 0)

    def test_validate_dependencies_missing(self):
        from core_platform.registry import ServiceRegistry
        r = ServiceRegistry()
        r.register("x", dependencies=["nonexistent"])
        missing = r.validate_dependencies()
        self.assertIn("x", missing)


# =====================================================================
# core_platform EventBus Tests (sanity)
# =====================================================================
class TestCorePlatformEventBus(unittest.TestCase):

    def test_subscribe_and_publish(self):
        from core_platform.event_bus import EventBus
        EventBus._instance = None  # reset singleton
        bus = EventBus()
        received = []
        bus.subscribe("test.event", lambda event: received.append(event.data))
        bus.publish("test.event", {"msg": "hi"})
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["msg"], "hi")

    def test_unsubscribe(self):
        from core_platform.event_bus import EventBus
        EventBus._instance = None  # reset singleton
        bus = EventBus()
        received = []
        def handler(event): received.append(event.data)
        sub_id = bus.subscribe("test.event", handler)
        bus.unsubscribe(sub_id)
        bus.publish("test.event", {"msg": "gone"})
        self.assertEqual(len(received), 0)


# =====================================================================
# core_platform Lifecycle Tests (sanity)
# =====================================================================
class TestCorePlatformLifecycle(unittest.TestCase):

    def test_initial_phase(self):
        from core_platform.lifecycle import LifecycleManager, LifecyclePhase
        lm = LifecycleManager()
        self.assertEqual(lm.phase, LifecyclePhase.INITIALIZING)
        self.assertFalse(lm.is_running)

    def test_add_hook(self):
        from core_platform.lifecycle import LifecycleManager, LifecyclePhase
        lm = LifecycleManager()
        hook = lm.add_hook(LifecyclePhase.STARTING, "test_hook", lambda: None)
        self.assertEqual(hook.name, "test_hook")
        status = lm.get_status()
        self.assertEqual(status["hooks_summary"]["starting"], 1)


# =====================================================================
# core_platform Config Tests (sanity)
# =====================================================================
class TestCorePlatformConfig(unittest.TestCase):

    def test_config_set_get(self):
        from core_platform.config import ConfigManager
        cm = ConfigManager()
        cm.add_source("test", {"test_key": "test_value"})
        self.assertEqual(cm.get("test_key"), "test_value")

    def test_config_default(self):
        from core_platform.config import ConfigManager
        cm = ConfigManager()
        self.assertEqual(cm.get("nonexistent", "fallback"), "fallback")

    def test_config_has(self):
        from core_platform.config import ConfigManager
        cm = ConfigManager()
        cm.add_source("test", {"exists": 1})
        self.assertIsNotNone(cm.get("exists"))
        self.assertIsNone(cm.get("nope"))


# =====================================================================
# core_platform Scheduler Tests (sanity)
# =====================================================================
class TestCorePlatformScheduler(unittest.TestCase):

    def test_scheduler_add_task(self):
        from core_platform.scheduler import TaskScheduler
        ts = TaskScheduler()
        task = ts.schedule_interval(
            task_id="test_task",
            name="test_task",
            func=lambda: None,
            interval_seconds=60,
        )
        self.assertIsNotNone(task)
        self.assertEqual(task.name, "test_task")

    def test_scheduler_list_tasks(self):
        from core_platform.scheduler import TaskScheduler
        ts = TaskScheduler()
        ts.schedule_interval(task_id="a", name="a", func=lambda: None, interval_seconds=30)
        ts.schedule_interval(task_id="b", name="b", func=lambda: None, interval_seconds=60)
        tasks = ts.list_tasks()
        self.assertEqual(len(tasks), 2)


# =====================================================================
# core_platform Secrets Tests (sanity)
# =====================================================================
class TestCorePlatformSecrets(unittest.TestCase):

    def test_set_get_secret(self):
        from core_platform.secrets import SecretsManager
        sm = SecretsManager()
        sm.set("api_key", "secret123")
        self.assertEqual(sm.get("api_key"), "secret123")

    def test_get_missing_returns_none(self):
        from core_platform.secrets import SecretsManager
        sm = SecretsManager()
        self.assertIsNone(sm.get("nope"))

    def test_has_secret(self):
        from core_platform.secrets import SecretsManager
        sm = SecretsManager()
        sm.set("k", "v")
        self.assertIn("k", sm.get_all_keys())
        self.assertNotIn("missing", sm.get_all_keys())


# =====================================================================
# core_platform Discovery Tests (sanity)
# =====================================================================
class TestCorePlatformDiscovery(unittest.TestCase):

    def test_discover_modules(self):
        from core_platform.discovery import ModuleDiscovery
        md = ModuleDiscovery()
        modules = md.discover()
        self.assertIsInstance(modules, (list, dict))


if __name__ == "__main__":
    unittest.main()
