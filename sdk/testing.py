"""
Testing SDK
============

SDK for testing trading strategies.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .base import SmartPipSDK, SDKConfig, SDKLogger

logger = SDKLogger("testing")


@dataclass
class TestCase:
    """Test case definition"""
    test_id: str
    name: str
    description: str = ""
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None
    assertions: List[Callable] = field(default_factory=list)


@dataclass
class TestResult:
    """Test result"""
    test_id: str
    name: str
    passed: bool
    duration_ms: float
    error_message: Optional[str] = None
    assertions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TestSuiteResult:
    """Test suite result"""
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration_ms: float
    results: List[TestResult] = field(default_factory=list)


class AssertionError(Exception):
    """Custom assertion error for tests"""
    pass


class BacktestRunner(SmartPipSDK):
    """
    Strategy backtesting runner.
    """
    
    def __init__(self, config: Optional[SDKConfig] = None):
        super().__init__(config)
        self._test_suites: Dict[str, List[TestCase]] = {}
        self._results: List[TestResult] = []
    
    def register_test_suite(self, suite_name: str, tests: List[TestCase]) -> None:
        """Register a test suite"""
        self._test_suites[suite_name] = tests
        logger.info(f"Registered test suite: {suite_name} ({len(tests)} tests)")
    
    def run_test_suite(self, suite_name: str) -> TestSuiteResult:
        """Run a test suite"""
        if suite_name not in self._test_suites:
            raise ValueError(f"Test suite not found: {suite_name}")
        
        tests = self._test_suites[suite_name]
        start_time = time.time()
        results = []
        
        for test in tests:
            result = self._run_test(test)
            results.append(result)
        
        duration = (time.time() - start_time) * 1000
        
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        skipped = sum(1 for r in results if r.error_message == "skipped")
        
        return TestSuiteResult(
            suite_name=suite_name,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration_ms=duration,
            results=results
        )
    
    def _run_test(self, test: TestCase) -> TestResult:
        """Run a single test"""
        start_time = time.time()
        error_message = None
        
        try:
            # Setup
            if test.setup:
                test.setup()
            
            # Run assertions
            assertions_results = []
            for assertion in test.assertions:
                try:
                    assertion()
                    assertions_results.append({"passed": True, "message": "OK"})
                except AssertionError as e:
                    raise e
                except Exception as e:
                    raise AssertionError(str(e))
            
            # Teardown
            if test.teardown:
                test.teardown()
            
        except AssertionError as e:
            error_message = str(e)
        except Exception as e:
            error_message = f"Error: {str(e)}"
        
        duration = (time.time() - start_time) * 1000
        
        return TestResult(
            test_id=test.test_id,
            name=test.name,
            passed=error_message is None,
            duration_ms=duration,
            error_message=error_message,
            assertions=[]
        )
    
    def run_all(self) -> List[TestSuiteResult]:
        """Run all test suites"""
        results = []
        for suite_name in self._test_suites:
            result = self.run_test_suite(suite_name)
            results.append(result)
        return results


class StrategyTestBuilder:
    """Builder for strategy tests"""
    
    def __init__(self, test_id: str, name: str):
        self._test = TestCase(
            test_id=test_id,
            name=name,
            setup=None,
            teardown=None,
            assertions=[]
        )
    
    def description(self, desc: str) -> "StrategyTestBuilder":
        """Set test description"""
        self._test.description = desc
        return self
    
    def setup(self, func: Callable) -> "StrategyTestBuilder":
        """Set test setup function"""
        self._test.setup = func
        return self
    
    def teardown(self, func: Callable) -> "StrategyTestBuilder":
        """Set test teardown function"""
        self._test.teardown = func
        return self
    
    def assert_that(self, condition: bool, message: str = "") -> "StrategyTestBuilder":
        """Add an assertion"""
        def assertion():
            if not condition:
                raise AssertionError(message or "Assertion failed")
        self._test.assertions.append(assertion)
        return self
    
    def assert_equal(self, actual: Any, expected: Any, message: str = "") -> "StrategyTestBuilder":
        """Assert equality"""
        def assertion():
            if actual != expected:
                raise AssertionError(message or f"Expected {expected}, got {actual}")
        self._test.assertions.append(assertion)
        return self
    
    def assert_pnl(self, pnl: float, min_pnl: float, message: str = "") -> "StrategyTestBuilder":
        """Assert minimum P&L"""
        def assertion():
            if pnl < min_pnl:
                raise AssertionError(message or f"P&L {pnl} below minimum {min_pnl}")
        self._test.assertions.append(assertion)
        return self
    
    def assert_drawdown(self, drawdown: float, max_drawdown: float, message: str = "") -> "StrategyTestBuilder":
        """Assert maximum drawdown"""
        def assertion():
            if drawdown > max_drawdown:
                raise AssertionError(message or f"Drawdown {drawdown} exceeds max {max_drawdown}")
        self._test.assertions.append(assertion)
        return self
    
    def assert_win_rate(self, win_rate: float, min_win_rate: float, message: str = "") -> "StrategyTestBuilder":
        """Assert minimum win rate"""
        def assertion():
            if win_rate < min_win_rate:
                raise AssertionError(message or f"Win rate {win_rate} below minimum {min_win_rate}")
        self._test.assertions.append(assertion)
        return self
    
    def build(self) -> TestCase:
        """Build the test case"""
        return self._test


def test(test_id: str, name: str) -> StrategyTestBuilder:
    """Create a test builder"""
    return StrategyTestBuilder(test_id, name)
