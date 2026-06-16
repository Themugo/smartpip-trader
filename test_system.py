#!/usr/bin/env python3
"""
Test script to verify the refactored system imports and basic functionality
"""

import sys
import traceback
import importlib

def test_imports():
    """Test that all modules can be imported safely without exec()"""
    print("Testing imports...")
    
    # Define imports as module paths and expected attributes
    tests = [
        ("config", "config", ["Settings"]),
        ("models", "models", ["MarketType", "Prediction", "AnalysisResult"]),
        ("core.connection", "core", ["DerivConnection"]),
        ("core.account", "core", ["AccountManager"]),
        ("core.market", "core", ["MarketManager"]),
        ("analysis.base_analyzer", "analysis", ["BaseAnalyzer"]),
        ("analysis.even_odd_analyzer", "analysis", ["EvenOddAnalyzer"]),
        ("analysis.rise_fall_analyzer", "analysis", ["RiseFallAnalyzer"]),
        ("analysis.over_under_analyzer", "analysis", ["OverUnderAnalyzer"]),
        ("analysis.match_diff_analyzer", "analysis", ["MatchDiffAnalyzer"]),
        ("analysis.digit_analyzer", "analysis", ["DigitAnalyzer"]),
        ("analysis.volatility_analyzer", "analysis", ["VolatilityAnalyzer"]),
        ("analysis.analysis_manager", "analysis", ["AnalysisManager"]),
        ("trading.executor", "trading", ["TradeExecutor"]),
        ("trading.monitor", "trading", ["TradeMonitor"]),
        ("trading.risk_manager", "trading", ["RiskManager"]),
        ("trading.stats_manager", "trading", ["StatsManager"]),
        ("database", "database", ["DatabaseManager"]),
        ("utils.cache", "utils", ["CacheManager"]),
        ("utils.metrics", "utils", ["PerformanceMetrics"]),
        ("utils.rate_limiter", "utils", ["RateLimiter"]),
        ("utils.logger", "utils", ["StructuredLogger"]),
        ("dashboard", "dashboard", ["get_dashboard_html"]),
        ("api", "api", ["setup_routes"]),
        ("trading_system", "trading_system", ["TradingSystem"]),
    ]
    
    passed = 0
    failed = 0
    
    for name, module_path, expected_attrs in tests:
        try:
            # Safe import using importlib
            module = importlib.import_module(module_path)
            
            # Verify expected attributes exist
            for attr in expected_attrs:
                if not hasattr(module, attr):
                    raise AttributeError(f"Module {module_path} missing attribute {attr}")
            
            print(f"✓ {name}")
            passed += 1
        except Exception as e:
            print(f"✗ {name}: {e}")
            failed += 1
    
    print(f"\nImport test results: {passed} passed, {failed} failed")
    return failed == 0

def test_basic_functionality():
    """Test basic functionality of key components"""
    print("\nTesting basic functionality...")
    
    tests = []
    
    # Test Settings
    try:
        from config import Settings
        settings = Settings()
        assert settings.base_amount == 1.0
        assert settings.auto_trading == False
        tests.append(("Settings initialization", True))
    except Exception as e:
        tests.append(("Settings initialization", False))
        print(f"✗ Settings: {e}")
    
    # Test CacheManager
    try:
        from utils import CacheManager
        cache = CacheManager(max_size=10, ttl=5)
        cache.set({"test": "data"}, "result")
        result = cache.get({"test": "data"})
        assert result == "result"
        tests.append(("CacheManager", True))
    except Exception as e:
        tests.append(("CacheManager", False))
        print(f"✗ CacheManager: {e}")
    
    # Test PerformanceMetrics
    try:
        from utils import PerformanceMetrics
        metrics = PerformanceMetrics()
        metrics.increment_counter("test")
        assert metrics.get_counter("test") == 1
        tests.append(("PerformanceMetrics", True))
    except Exception as e:
        tests.append(("PerformanceMetrics", False))
        print(f"✗ PerformanceMetrics: {e}")
    
    # Test RateLimiter
    try:
        from utils import RateLimiter
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        assert limiter.is_allowed("test_client") == True
        tests.append(("RateLimiter", True))
    except Exception as e:
        tests.append(("RateLimiter", False))
        print(f"✗ RateLimiter: {e}")
    
    # Test DatabaseManager
    try:
        from database import DatabaseManager
        db = DatabaseManager(":memory:")
        assert db is not None
        tests.append(("DatabaseManager", True))
    except Exception as e:
        tests.append(("DatabaseManager", False))
        print(f"✗ DatabaseManager: {e}")
    
    # Test TradingSystem initialization
    try:
        from trading_system import TradingSystem
        system = TradingSystem()
        assert system is not None
        assert system.settings is not None
        assert system.cache is not None
        assert system.metrics is not None
        assert system.database is not None
        tests.append(("TradingSystem initialization", True))
    except Exception as e:
        tests.append(("TradingSystem initialization", False))
        print(f"✗ TradingSystem: {e}")
    
    passed = sum(1 for _, result in tests if result)
    failed = len(tests) - passed
    
    for name, result in tests:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
    
    print(f"\nFunctionality test results: {passed} passed, {failed} failed")
    return failed == 0

def main():
    """Run all tests"""
    print("=" * 50)
    print("SmartPip Trading System - Refactored System Test")
    print("=" * 50)
    
    import_success = test_imports()
    functionality_success = test_basic_functionality()
    
    print("\n" + "=" * 50)
    if import_success and functionality_success:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
