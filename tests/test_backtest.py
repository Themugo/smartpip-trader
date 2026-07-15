"""
Tests for Professional Backtest Framework
====================================
"""

import pytest
from datetime import datetime, timedelta
import numpy as np

from backtest import (
    # Data Management
    HistoricalDataManager,
    TickDatasetManager,
    DatasetVersion,
    DatasetType,
    Tick,
    # Validation
    WalkForwardValidator,
    RollingWindowValidator,
    OutOfSampleValidator,
    MonteCarloSimulator,
    BootstrapAnalyzer,
    # Simulations
    ExecutionSimulator,
    SlippageSimulator,
    TransactionCostSimulator,
    SimulationConfig,
    # Analysis
    ParameterStabilityAnalyzer,
    SensitivityAnalyzer,
    ConfidenceCalibrator,
    ExpectedValueAnalyzer,
    ProbabilityCalibrator,
    StabilityStatus,
    # Reporting
    BacktestReport,
    ReportGenerator,
    ReportFormat,
    EquityCurve,
    DrawdownAnalysis,
    TradeDistribution,
    CalibrationAnalysis,
    # Benchmark
    BenchmarkComparator,
    DeploymentGate,
    ComparisonResult,
    BenchmarkMetrics
)


class TestTickDatasetManager:
    """Tests for tick dataset manager"""
    
    def test_initialization(self, tmp_path):
        """Test manager initialization"""
        manager = TickDatasetManager(db_path=str(tmp_path / "ticks.db"))
        assert manager.cache_size == 10000
    
    def test_store_and_load_ticks(self, tmp_path):
        """Test storing and loading ticks"""
        manager = TickDatasetManager(db_path=str(tmp_path / "ticks.db"))
        
        ticks = [
            Tick(
                timestamp=datetime(2024, 1, 1, 12, 0, i),
                bid=1.2345,
                ask=1.2350,
                bid_size=1000,
                ask_size=1000,
                volume=50000
            )
            for i in range(10)
        ]
        
        version_id = manager.store_ticks("R_50", ticks)
        
        loaded = manager.load_ticks(
            "R_50",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2)
        )
        
        assert len(loaded) == 10
        assert loaded[0].bid == 1.2345


class TestWalkForwardValidator:
    """Tests for walk-forward validation"""
    
    def test_validation(self):
        """Test walk-forward validation"""
        validator = WalkForwardValidator(
            in_sample_days=10,
            out_sample_days=5,
            step_days=3
        )
        
        # Create mock data
        data = list(range(100))
        
        def get_metrics(subset):
            return {"sharpe_ratio": np.mean(subset) / 10, "total_return": np.mean(subset) / 100}
        
        def strategy_func(subset):
            return get_metrics(subset)
        
        result = validator.validate(strategy_func, data, get_metrics)
        
        assert result.consistency_ratio >= 0
        assert result.avg_sharpe >= 0


class TestMonteCarloSimulator:
    """Tests for Monte Carlo simulation"""
    
    def test_simulate_returns(self):
        """Test return simulation"""
        simulator = MonteCarloSimulator(n_simulations=100)
        
        returns = [0.01, -0.005, 0.02, 0.015, -0.01]
        
        result = simulator.simulate_returns(returns, n_periods=20)
        
        assert result["n_simulations"] == 100
        assert "final_returns" in result
        assert "probability_of_profit" in result


class TestBootstrapAnalyzer:
    """Tests for bootstrap analysis"""
    
    def test_analyze(self):
        """Test bootstrap analysis"""
        analyzer = BootstrapAnalyzer(n_iterations=100)
        
        returns = list(np.random.normal(0.001, 0.01, 50))
        
        result = analyzer.analyze(returns)
        
        assert "observed" in result
        assert "confidence_interval" in result
        assert "p_value" in result


class TestExecutionSimulator:
    """Tests for execution simulation"""
    
    def test_simulate_execution(self):
        """Test execution simulation"""
        config = SimulationConfig(base_latency_ms=50)
        simulator = ExecutionSimulator(config)
        
        result = simulator.simulate_execution(
            signal_price=1.2345,
            direction="buy",
            timestamp=datetime.now(),
            volatility=0.01
        )
        
        assert "execution_price" in result
        assert "latency_ms" in result
        assert result["latency_ms"] > 0


class TestSlippageSimulator:
    """Tests for slippage simulation"""
    
    def test_calculate_slippage(self):
        """Test slippage calculation"""
        simulator = SlippageSimulator()
        
        result = simulator.calculate_slippage(
            base_price=1.2345,
            order_size=100000,
            market_volatility=0.01
        )
        
        assert "expected_slippage" in result
        assert result["expected_slippage"] > 0


class TestTransactionCostSimulator:
    """Tests for transaction cost simulation"""
    
    def test_calculate_round_trip_cost(self):
        """Test round-trip cost calculation"""
        simulator = TransactionCostSimulator()
        
        result = simulator.calculate_round_trip_cost(
            entry_price=1.2345,
            exit_price=1.2355,
            position_size=100000,
            n_lots=1.0,
            holding_days=1,
            direction="long"
        )
        
        assert "total_cost" in result
        assert result["total_cost"] > 0


class TestParameterStabilityAnalyzer:
    """Tests for parameter stability analyzer"""
    
    def test_analyze_parameter(self):
        """Test parameter analysis"""
        analyzer = ParameterStabilityAnalyzer()
        
        param_values = [1, 2, 3, 4, 5]
        perf_values = [0.5, 0.8, 1.0, 0.9, 0.7]  # Parabolic
        
        result = analyzer.analyze_parameter("test_param", param_values, perf_values)
        
        assert result.parameter_name == "test_param"
        assert result.stability_score >= 0
        assert result.critical_value in param_values


class TestSensitivityAnalyzer:
    """Tests for sensitivity analyzer"""
    
    def test_analyze(self):
        """Test sensitivity analysis"""
        analyzer = SensitivityAnalyzer()
        
        def strategy_func(params):
            # Simple quadratic function
            x = params.get("x", 1)
            return 1.0 - 0.1 * (x - 3) ** 2
        
        base_params = {"x": 1.0}
        param_ranges = {"x": (0.0, 5.0)}
        
        result = analyzer.analyze(strategy_func, base_params, param_ranges, n_steps=5)
        
        assert "parameter_analysis" in result
        assert "most_sensitive" in result


class TestConfidenceCalibrator:
    """Tests for confidence calibrator"""
    
    def test_add_and_calibrate(self):
        """Test adding observations and calibration"""
        calibrator = ConfidenceCalibrator()
        
        # Add observations
        for i in range(50):
            conf = (i % 10) / 10
            outcome = 1.0 if conf > 0.5 else 0.0
            calibrator.add_observation(conf, outcome)
        
        result = calibrator.calibrate()
        
        assert "calibration_curve" in result
        assert "expected_calibration_error" in result


class TestExpectedValueAnalyzer:
    """Tests for expected value analyzer"""
    
    def test_add_and_analyze(self):
        """Test adding trades and analysis"""
        analyzer = ExpectedValueAnalyzer()
        
        # Add trades
        for i in range(20):
            conf = 0.6 + np.random.uniform(-0.2, 0.2)
            pnl = np.random.normal(10, 5) if conf > 0.5 else np.random.normal(-5, 3)
            analyzer.add_trade(
                confidence=conf,
                actual_pnl=pnl,
                predicted_direction="buy",
                actual_direction="buy" if pnl > 0 else "sell"
            )
        
        result = analyzer.analyze()
        
        assert "n_trades" in result
        assert "overall_ev" in result


class TestReportGenerator:
    """Tests for report generator"""
    
    def test_generate_report(self, tmp_path):
        """Test report generation"""
        generator = ReportGenerator(output_dir=str(tmp_path))
        
        # Create mock data
        timestamps = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(100)]
        equity = [100000 + i * 100 + np.random.normal(0, 50) for i in range(100)]
        
        trades = [
            {
                "pnl": np.random.normal(100, 50),
                "confidence": np.random.uniform(0.4, 0.8),
                "correct": np.random.random() > 0.4
            }
            for _ in range(50)
        ]
        
        report = generator.generate_report(trades, equity, timestamps, "TestStrategy")
        
        assert report.total_trades == 50
        assert report.sharpe_ratio > 0
        assert report.total_return > -1
    
    def test_export_report(self, tmp_path):
        """Test report export"""
        generator = ReportGenerator(output_dir=str(tmp_path))
        
        timestamps = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(10)]
        equity = [100000 + i * 100 for i in range(10)]
        trades = [
            {"pnl": 100, "confidence": 0.7, "correct": True},
            {"pnl": 50, "confidence": 0.6, "correct": True},
            {"pnl": -30, "confidence": 0.5, "correct": False}
        ]
        
        report = generator.generate_report(trades, equity, timestamps, "Test")
        
        path = generator.export_report(report, ReportFormat.MARKDOWN)
        
        assert path.endswith(".md")


class TestBenchmarkComparator:
    """Tests for benchmark comparator"""
    
    def test_compare_better_strategy(self):
        """Test comparing better strategy"""
        comparator = BenchmarkComparator()
        
        new_metrics = {
            "total_return": 0.25,
            "annualized_return": 0.20,
            "sharpe_ratio": 1.5,
            "sortino_ratio": 2.0,
            "max_drawdown": 0.10,
            "win_rate": 0.60,
            "profit_factor": 1.8,
            "expectancy": 50,
            "trade_count": 100,
            "n_days": 252
        }
        
        baseline_metrics = {
            "total_return": 0.15,
            "annualized_return": 0.12,
            "sharpe_ratio": 1.0,
            "sortino_ratio": 1.3,
            "max_drawdown": 0.15,
            "win_rate": 0.55,
            "profit_factor": 1.4,
            "expectancy": 30,
            "trade_count": 100,
            "n_days": 252
        }
        
        result = comparator.compare(
            "NewStrategy",
            new_metrics,
            "Baseline",
            baseline_metrics
        )
        
        assert result.new_strategy.sharpe_ratio > result.baseline_strategy.sharpe_ratio


class TestDeploymentGate:
    """Tests for deployment gate"""
    
    def test_can_deploy_passing(self):
        """Test deployment gate with passing metrics"""
        gate = DeploymentGate(
            minimum_sharpe=0.5,
            maximum_drawdown=0.20,
            minimum_win_rate=0.45
        )
        
        metrics = {
            "sharpe_ratio": 1.2,
            "max_drawdown": 0.10,
            "win_rate": 0.60,
            "trade_count": 50
        }
        
        result = gate.can_deploy("TestStrategy", metrics)
        
        assert result["can_deploy"] is True
    
    def test_can_deploy_blocked(self):
        """Test deployment gate with failing metrics"""
        gate = DeploymentGate(
            minimum_sharpe=0.5,
            maximum_drawdown=0.20,
            minimum_win_rate=0.45
        )
        
        metrics = {
            "sharpe_ratio": 0.3,  # Too low
            "max_drawdown": 0.30,  # Too high
            "win_rate": 0.40,  # Too low
            "trade_count": 50
        }
        
        result = gate.can_deploy("TestStrategy", metrics)
        
        assert result["can_deploy"] is False
        assert len(result["blockers"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
