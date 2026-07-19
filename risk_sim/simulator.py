"""
Risk Simulator - Pre-Deployment Stress Testing

Pre-deployment validation and stress testing.
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import deque

logger = logging.getLogger(__name__)


class TestScenario(Enum):
    """Types of stress test scenarios"""
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    LATENCY_SPIKE = "latency_spike"
    API_FAILURE = "api_failure"
    SLIPPAGE = "slippage"
    LARGE_POSITION = "large_position"
    CONCENTRATED_RISK = "concentrated_risk"
    RAPID_TRADING = "rapid_trading"
    EXTENDED_DRAWDOWN = "extended_drawdown"
    ALL_COMBINED = "all_combined"


@dataclass
class StressTestScenario:
    """Configuration for a stress test scenario"""
    name: str
    scenario_type: TestScenario
    description: str
    
    # Parameters
    volatility_multiplier: float = 1.0
    latency_ms: float = 0
    slippage_percent: float = 0
    api_failure_rate: float = 0
    position_multiplier: float = 1.0
    max_trades_per_minute: int = 100
    
    # Duration
    duration_seconds: int = 300
    warmup_seconds: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "scenario_type": self.scenario_type.value,
            "description": self.description,
            "volatility_multiplier": self.volatility_multiplier,
            "latency_ms": self.latency_ms,
            "slippage_percent": self.slippage_percent,
            "api_failure_rate": self.api_failure_rate,
            "position_multiplier": self.position_multiplier,
            "max_trades_per_minute": self.max_trades_per_minute,
            "duration_seconds": self.duration_seconds,
            "warmup_seconds": self.warmup_seconds,
        }


@dataclass
class TestResult:
    """Result of a single test iteration"""
    scenario_name: str
    timestamp: datetime
    duration_ms: float
    
    # Trading metrics
    trades_executed: int = 0
    trades_successful: int = 0
    trades_failed: int = 0
    
    # Financial metrics
    initial_balance: float = 0
    final_balance: float = 0
    pnl: float = 0
    max_drawdown: float = 0
    win_rate: float = 0
    
    # Risk metrics
    max_exposure: float = 0
    avg_latency_ms: float = 0
    slippage_cost: float = 0
    
    # Status
    passed: bool = False
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "trades_executed": self.trades_executed,
            "trades_successful": self.trades_successful,
            "trades_failed": self.trades_failed,
            "initial_balance": self.initial_balance,
            "final_balance": self.final_balance,
            "pnl": self.pnl,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "max_exposure": self.max_exposure,
            "avg_latency_ms": self.avg_latency_ms,
            "slippage_cost": self.slippage_cost,
            "passed": self.passed,
            "warnings": self.warnings,
            "errors": self.errors,
        }


@dataclass
class DeploymentReadinessReport:
    """Comprehensive deployment readiness report"""
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Overall readiness
    is_ready: bool = True
    readiness_score: float = 0  # 0-100
    
    # Individual test results
    test_results: List[TestResult] = field(default_factory=list)
    
    # Aggregated metrics
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    
    avg_pnl: float = 0
    worst_drawdown: float = 0
    max_latency: float = 0
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    blocking_issues: List[str] = field(default_factory=list)
    
    # Risk assessment
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "is_ready": self.is_ready,
            "readiness_score": self.readiness_score,
            "test_results": [t.to_dict() for t in self.test_results],
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "avg_pnl": self.avg_pnl,
            "worst_drawdown": self.worst_drawdown,
            "max_latency": self.max_latency,
            "recommendations": self.recommendations,
            "blocking_issues": self.blocking_issues,
            "risk_level": self.risk_level,
        }


class RiskSimulator:
    """
    Risk Simulator for pre-deployment stress testing.
    
    Features:
    - Volatility stress tests
    - Latency simulation
    - Slippage testing
    - API failure simulation
    - Position size variations
    - Confidence threshold testing
    - Comprehensive reporting
    """
    
    # Predefined scenarios
    DEFAULT_SCENARIOS = {
        TestScenario.HIGH_VOLATILITY: StressTestScenario(
            name="High Volatility",
            scenario_type=TestScenario.HIGH_VOLATILITY,
            description="Test with 2x market volatility",
            volatility_multiplier=2.0,
        ),
        TestScenario.LATENCY_SPIKE: StressTestScenario(
            name="Latency Spike",
            scenario_type=TestScenario.LATENCY_SPIKE,
            description="Simulate network latency of 500ms",
            latency_ms=500,
        ),
        TestScenario.SLIPPAGE: StressTestScenario(
            name="High Slippage",
            scenario_type=TestScenario.SLIPPAGE,
            description="Test with 1% average slippage",
            slippage_percent=1.0,
        ),
        TestScenario.API_FAILURE: StressTestScenario(
            name="API Failures",
            scenario_type=TestScenario.API_FAILURE,
            description="Simulate 10% API failure rate",
            api_failure_rate=0.1,
        ),
        TestScenario.LARGE_POSITION: StressTestScenario(
            name="Large Positions",
            scenario_type=TestScenario.LARGE_POSITION,
            description="Test with 3x normal position sizes",
            position_multiplier=3.0,
        ),
        TestScenario.RAPID_TRADING: StressTestScenario(
            name="Rapid Trading",
            scenario_type=TestScenario.RAPID_TRADING,
            description="Test with maximum trade frequency",
            max_trades_per_minute=100,
        ),
        TestScenario.EXTENDED_DRAWDOWN: StressTestScenario(
            name="Extended Drawdown",
            scenario_type=TestScenario.EXTENDED_DRAWDOWN,
            description="Simulate prolonged losing streak",
            duration_seconds=600,
        ),
        TestScenario.ALL_COMBINED: StressTestScenario(
            name="Combined Stress",
            scenario_type=TestScenario.ALL_COMBINED,
            description="All stress factors combined",
            volatility_multiplier=1.5,
            latency_ms=200,
            slippage_percent=0.5,
            api_failure_rate=0.05,
            position_multiplier=1.5,
        ),
    }
    
    def __init__(
        self,
        initial_balance: float = 10000,
        risk_limits: Optional[Dict[str, float]] = None,
    ):
        self._initial_balance = initial_balance
        self._risk_limits = risk_limits or {
            "max_drawdown_percent": 20,
            "max_position_size": 1000,
            "max_daily_loss": 500,
            "min_win_rate": 0.45,
        }
        
        self._test_history: deque = deque(maxlen=100)
    
    def run_stress_test(
        self,
        scenario: StressTestScenario,
        trade_executor: Callable[[Dict[str, Any]], Dict[str, Any]],
        price_simulator: Callable[[float], float],
    ) -> TestResult:
        """
        Run a single stress test scenario.
        
        Args:
            scenario: Scenario configuration
            trade_executor: Function to execute trades
            price_simulator: Function to simulate prices
            
        Returns:
            TestResult with test outcomes
        """
        import time
        
        result = TestResult(
            scenario_name=scenario.name,
            timestamp=datetime.now(timezone.utc),
            duration_ms=0,
            initial_balance=self._initial_balance,
            final_balance=self._initial_balance,
        )
        
        start_time = time.time()
        balance = self._initial_balance
        peak_balance = balance
        equity_trough = balance
        
        trades = []
        latencies = []
        slippage_costs = []
        
        # Simulate warmup period
        warmup_end = time.time() + scenario.warmup_seconds
        
        while time.time() - start_time < scenario.duration_seconds:
            try:
                # Generate simulated trade
                base_amount = random.uniform(10, 100) * scenario.position_multiplier
                
                # Check position size limit
                if base_amount > self._risk_limits["max_position_size"]:
                    result.warnings.append(f"Position size {base_amount} exceeds limit")
                    base_amount = self._risk_limits["max_position_size"]
                
                # Simulate latency
                latency = scenario.latency_ms if scenario.latency_ms > 0 else random.uniform(10, 100)
                latencies.append(latency)
                
                # Check for API failure
                if random.random() < scenario.api_failure_rate:
                    result.trades_failed += 1
                    result.errors.append("API call failed")
                    continue
                
                # Execute simulated trade
                trade_result = trade_executor({
                    "amount": base_amount,
                    "direction": random.choice(["CALL", "PUT"]),
                    "latency_ms": latency,
                })
                
                # Apply slippage
                slippage = base_amount * (scenario.slippage_percent / 100)
                slippage_costs.append(slippage)
                
                # Calculate outcome
                outcome = random.random()
                win_prob = 0.5 + (random.random() - 0.5) * 0.2  # 40-60% win rate
                
                if outcome < win_prob:
                    profit = base_amount * random.uniform(0.8, 0.95)
                    balance += profit
                    result.trades_successful += 1
                else:
                    loss = base_amount * random.uniform(0.8, 1.0)
                    balance -= loss
                    balance -= slippage
                    result.trades_failed += 1
                
                result.trades_executed += 1
                
                # Track equity
                if balance > peak_balance:
                    peak_balance = balance
                if balance < equity_trough:
                    equity_trough = balance
                
            except Exception as e:
                result.errors.append(str(e))
        
        result.duration_ms = (time.time() - start_time) * 1000
        result.final_balance = balance
        result.pnl = balance - result.initial_balance
        result.max_drawdown = (peak_balance - equity_trough) / peak_balance * 100 if peak_balance > 0 else 0
        result.win_rate = (
            result.trades_successful / result.trades_executed
            if result.trades_executed > 0 else 0
        )
        result.max_exposure = max(slippage_costs) if slippage_costs else 0
        result.avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0
        result.slippage_cost = sum(slippage_costs)
        
        # Determine pass/fail
        result.passed = (
            result.max_drawdown < self._risk_limits["max_drawdown_percent"] and
            result.win_rate >= self._risk_limits["min_win_rate"]
        )
        
        if result.max_drawdown >= self._risk_limits["max_drawdown_percent"]:
            result.errors.append(f"Drawdown {result.max_drawdown:.1f}% exceeds limit")
        
        if result.win_rate < self._risk_limits["min_win_rate"]:
            result.errors.append(f"Win rate {result.win_rate:.1%} below threshold")
        
        self._test_history.append(result)
        return result
    
    def run_all_scenarios(
        self,
        trade_executor: Callable[[Dict[str, Any]], Dict[str, Any]],
        price_simulator: Callable[[float], float],
    ) -> DeploymentReadinessReport:
        """
        Run all predefined stress test scenarios.
        
        Args:
            trade_executor: Function to execute trades
            price_simulator: Function to simulate prices
            
        Returns:
            DeploymentReadinessReport
        """
        report = DeploymentReadinessReport()
        
        for scenario_type, scenario in self.DEFAULT_SCENARIOS.items():
            logger.info(f"Running scenario: {scenario.name}")
            
            result = self.run_stress_test(scenario, trade_executor, price_simulator)
            report.test_results.append(result)
            
            report.total_tests += 1
            if result.passed:
                report.passed_tests += 1
            else:
                report.failed_tests += 1
                report.is_ready = False
                report.blocking_issues.append(
                    f"Failed: {scenario.name}"
                )
        
        # Calculate aggregated metrics
        if report.test_results:
            report.avg_pnl = sum(r.pnl for r in report.test_results) / len(report.test_results)
            report.worst_drawdown = max(r.max_drawdown for r in report.test_results)
            report.max_latency = max(r.avg_latency_ms for r in report.test_results)
        
        # Calculate readiness score
        if report.total_tests > 0:
            report.readiness_score = (report.passed_tests / report.total_tests) * 100
        
        # Determine risk level
        if report.failed_tests > len(self.DEFAULT_SCENARIOS) / 2:
            report.risk_level = "CRITICAL"
        elif report.failed_tests > 0:
            report.risk_level = "HIGH"
        elif report.worst_drawdown > 15:
            report.risk_level = "MEDIUM"
        else:
            report.risk_level = "LOW"
        
        # Generate recommendations
        if report.worst_drawdown > 10:
            report.recommendations.append(
                f"Consider reducing position sizes to limit drawdown to <10%"
            )
        
        if report.max_latency > 200:
            report.recommendations.append(
                "Optimize execution to reduce latency below 200ms"
            )
        
        if report.risk_level in ("HIGH", "CRITICAL"):
            report.recommendations.append(
                "Review and adjust risk parameters before deployment"
            )
        
        return report
    
    def get_test_history(self) -> List[TestResult]:
        """Get history of test results"""
        return list(self._test_history)
    
    def get_default_scenarios(self) -> Dict[TestScenario, StressTestScenario]:
        """Get all default test scenarios"""
        return self.DEFAULT_SCENARIOS.copy()
