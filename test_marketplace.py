"""Quick smoke test for marketplace."""
import sys
sys.path.insert(0, ".")

from platform.strategies.base import StrategyBase
from platform.strategies.registry import StrategyRegistry
from platform.strategies.marketplace import StrategyMarketplace

r = StrategyRegistry()
m = StrategyMarketplace(registry=r)

# Test catalog
stats = m.get_marketplace_stats()
assert stats["total_known"] == 6, f"Expected 6, got {stats['total_known']}"
assert stats["installed"] == 0
assert stats["available"] == 6
print("PASS: catalog stats")

# Test search
results = m.search_strategies("grid")
assert len(results) == 1 and results[0]["strategy_id"] == "grid"
print("PASS: search by name")

# Test search by category
results = m.search_strategies("", category="progression")
assert len(results) == 2
print("PASS: search by category")

# Test compatibility
cc = m.check_compatibility("grid", "R_100", "demo")
assert cc.compatible
print("PASS: compatibility check (compatible)")

cc2 = m.check_compatibility("sniper", "R_50", "demo")
assert not cc2.compatible
print("PASS: compatibility check (incompatible)")

# Test performance recording
m.record_trade("grid", 1.5)
m.record_trade("grid", -0.5)
m.record_trade("grid", 2.0)
perf = m.get_performance("grid")
assert perf["count"] == 3
assert perf["sum"] == 3.0
print("PASS: performance recording")

# Test all strategies include performance
all_strats = m.get_all_strategies()
for s in all_strats:
    assert "performance" in s
    assert "count" in s["performance"]
print("PASS: all strategies have performance")

# Test enable/disable (requires install first)
from strategies.grid_strategy import GridStrategy
m.install_strategy(GridStrategy)
grid = [s for s in m.get_all_strategies() if s["strategy_id"] == "grid"][0]
assert grid["installed"] and grid["active"]
m.disable_strategy("grid")
grid2 = [s for s in m.get_all_strategies() if s["strategy_id"] == "grid"][0]
assert not grid2["active"]
m.enable_strategy("grid")
grid3 = [s for s in m.get_all_strategies() if s["strategy_id"] == "grid"][0]
assert grid3["active"]
print("PASS: install/enable/disable")

# Test update config
m.update_strategy("grid", {"grid_size": 0.002})
inst = m.get_strategy("grid")
assert inst is not None
print("PASS: update config / get strategy")

# Test uninstall
m.uninstall_strategy("grid")
assert len(m.get_installed_strategies()) == 0
print("PASS: uninstall")

# Test registry
assert "grid" in r
assert r.count() == 6
cats = r.get_all_categories()
assert len(cats) == 5  # grid, progression, momentum, hft, hybrid
print("PASS: registry")

# Test dunder
assert len(m) == 6
assert "grid" in m
print("PASS: dunder methods")

print("\nAll tests passed!")
