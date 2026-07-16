"""
Tests for SDK Ecosystem
=======================

Tests for all SDK modules.
"""

import pytest
import time


class TestBaseSDK:
    """Tests for SDK base module"""
    
    def test_smartpip_sdk_initialization(self):
        """Test SDK initialization"""
        from sdk.base import SmartPipSDK, SDKConfig
        
        config = SDKConfig(api_url="http://test.local")
        sdk = SmartPipSDK(config)
        sdk.initialize()
        
        assert sdk.config.api_url == "http://test.local"
        assert sdk.health_check() is True
    
    def test_sdk_context_manager(self):
        """Test SDK context manager"""
        from sdk.base import SmartPipSDK
        
        with SmartPipSDK() as sdk:
            assert sdk.is_initialized
    
    def test_sdk_config_from_env(self):
        """Test SDK config from environment"""
        from sdk.base import SDKConfig
        
        config = SDKConfig.from_env()
        assert config is not None


class TestPluginSDK:
    """Tests for Plugin SDK"""
    
    def test_plugin_creation(self):
        """Test plugin creation"""
        from sdk.plugin import Plugin, PluginMetadata, PluginHook, create_plugin
        
        @create_plugin(
            name="test_plugin",
            version="1.0.0",
            hooks=[PluginHook.ON_INIT],
            description="A test plugin"
        )
        class TestPlugin(Plugin):
            pass
        
        assert TestPlugin.metadata.name == "test_plugin"
        assert TestPlugin.metadata.version == "1.0.0"
    
    def test_plugin_enable_disable(self):
        """Test plugin enable/disable"""
        from sdk.plugin import Plugin, PluginMetadata
        
        class MyPlugin(Plugin):
            metadata = PluginMetadata(
                plugin_id="test",
                name="Test",
                version="1.0.0"
            )
        
        plugin = MyPlugin()
        assert not plugin.is_enabled
        
        plugin.enable()
        assert plugin.is_enabled
        
        plugin.disable()
        assert not plugin.is_enabled
    
    def test_plugin_configure(self):
        """Test plugin configuration"""
        from sdk.plugin import Plugin, PluginMetadata
        
        class MyPlugin(Plugin):
            metadata = PluginMetadata(
                plugin_id="test",
                name="Test",
                version="1.0.0"
            )
        
        plugin = MyPlugin()
        plugin.configure({"param1": "value1"})
        
        assert plugin.get_config("param1") == "value1"
    
    def test_plugin_state(self):
        """Test plugin state management"""
        from sdk.plugin import Plugin, PluginMetadata
        
        class MyPlugin(Plugin):
            metadata = PluginMetadata(
                plugin_id="test",
                name="Test",
                version="1.0.0"
            )
        
        plugin = MyPlugin()
        plugin.set_state("key1", "value1")
        
        assert plugin.get_state("key1") == "value1"
        assert plugin.get_state("nonexistent", "default") == "default"


class TestStrategySDK:
    """Tests for Strategy SDK"""
    
    def test_strategy_creation(self):
        """Test strategy creation"""
        from sdk.strategy import Strategy, strategy
        
        @strategy(strategy_id="test_strategy", name="Test Strategy")
        class TestStrategy(Strategy):
            def on_init(self):
                pass
        
        assert TestStrategy.strategy_id == "test_strategy"
        assert TestStrategy.strategy_name == "Test Strategy"
    
    def test_signal_creation(self):
        """Test signal creation"""
        from sdk.strategy import Signal, OrderSide
        
        signal = Signal(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            strength=0.8,
            confidence=0.9
        )
        
        assert signal.symbol == "BTC/USD"
        assert signal.side == OrderSide.BUY
        assert signal.strength == 0.8
    
    def test_strategy_configure(self):
        """Test strategy configuration"""
        from sdk.strategy import Strategy
        
        class MyStrategy(Strategy):
            strategy_id = "test"
            strategy_name = "Test"
        
        strategy = MyStrategy()
        strategy.configure({"lookback": 20, "threshold": 0.5})
        
        assert strategy.get_config("lookback") == 20
        assert strategy.get_config("threshold") == 0.5
    
    def test_strategy_state(self):
        """Test strategy state management"""
        from sdk.strategy import Strategy
        
        class MyStrategy(Strategy):
            strategy_id = "test"
            strategy_name = "Test"
        
        strategy = MyStrategy()
        strategy.set_state("counter", 0)
        strategy.set_state("counter", strategy.get_state("counter") + 1)
        
        assert strategy.get_state("counter") == 1


class TestAISDK:
    """Tests for AI SDK"""
    
    def test_model_config(self):
        """Test model configuration"""
        from sdk.ai import ModelConfig
        
        config = ModelConfig(
            model_id="test_model",
            model_type="classification",
            version="1.0.0",
            input_features=["f1", "f2"],
            output_type="class"
        )
        
        assert config.model_id == "test_model"
        assert config.model_type == "classification"
    
    def test_prediction_result(self):
        """Test prediction result"""
        from sdk.ai import PredictionResult
        
        result = PredictionResult(
            prediction="buy",
            confidence=0.85,
            model_version="1.0.0",
            inference_time_ms=10.5
        )
        
        assert result.prediction == "buy"
        assert result.confidence == 0.85
    
    def test_feature_engineering_normalize(self):
        """Test feature normalization"""
        from sdk.ai import FeatureEngineering
        
        values = [1, 2, 3, 4, 5]
        normalized = FeatureEngineering.normalize(values)
        
        assert min(normalized) >= 0
        assert max(normalized) <= 1
    
    def test_feature_engineering_standardize(self):
        """Test feature standardization"""
        from sdk.ai import FeatureEngineering
        
        values = [1, 2, 3, 4, 5]
        standardized = FeatureEngineering.standardize(values)
        
        mean = sum(standardized) / len(standardized)
        assert abs(mean) < 0.001  # Close to 0


class TestFeatureSDK:
    """Tests for Feature SDK"""
    
    def test_feature_context(self):
        """Test feature context"""
        from sdk.feature import FeatureContext
        
        context = FeatureContext(
            user_id="user123",
            session_id="session456",
            environment="production"
        )
        
        assert context.user_id == "user123"
        assert context.environment == "production"
    
    def test_feature_client(self):
        """Test feature client"""
        from sdk.feature import FeatureClient
        
        client = FeatureClient()
        client.initialize()
        assert client.health_check() is True


class TestRiskSDK:
    """Tests for Risk SDK"""
    
    def test_risk_limits(self):
        """Test risk limits"""
        from sdk.risk import RiskLimits
        
        limits = RiskLimits(
            max_position_size=100000,
            max_daily_loss=0.05
        )
        
        assert limits.max_position_size == 100000
        assert limits.max_daily_loss == 0.05
    
    def test_risk_check(self):
        """Test risk checks"""
        from sdk.risk import RiskManager, RiskLimits
        
        manager = RiskManager()
        manager.set_limits(RiskLimits(max_position_size=100000))
        
        # This should fail - position exceeds limit
        check = manager.check_position_size("BTC/USD", 1000, 50000)
        assert check.passed is False  # 1000 * 50000 = 50M > 100K
        
        # This should pass
        check = manager.check_position_size("BTC/USD", 1, 50000)
        assert check.passed is True  # 1 * 50000 = 50K < 100K


class TestNotificationSDK:
    """Tests for Notification SDK"""
    
    def test_notification(self):
        """Test notification creation"""
        from sdk.notification import Notification, NotificationChannel, NotificationPriority
        
        notification = Notification(
            title="Test Alert",
            message="Test message",
            channel=NotificationChannel.EMAIL,
            priority=NotificationPriority.HIGH
        )
        
        assert notification.title == "Test Alert"
        assert notification.channel == NotificationChannel.EMAIL
    
    def test_notification_client(self):
        """Test notification client"""
        from sdk.notification import NotificationClient
        
        client = NotificationClient()
        client.initialize()
        assert client.health_check() is True


class TestReplaySDK:
    """Tests for Replay SDK"""
    
    def test_replay_config(self):
        """Test replay configuration"""
        from sdk.replay import ReplayConfig
        
        config = ReplayConfig(
            start_time=1000,
            end_time=2000,
            speed=2.0
        )
        
        assert config.start_time == 1000
        assert config.speed == 2.0
    
    def test_replay_engine(self):
        """Test replay engine"""
        from sdk.replay import ReplayEngine, MarketEvent
        
        engine = ReplayEngine()
        
        events = [
            MarketEvent(timestamp=1000, event_type="tick", symbol="BTC/USD", data={}),
            MarketEvent(timestamp=2000, event_type="tick", symbol="BTC/USD", data={}),
        ]
        
        engine.load_data(events)
        
        event = engine.next()
        assert event is not None
        assert event.timestamp == 1000


class TestTestingSDK:
    """Tests for Testing SDK"""
    
    def test_test_case(self):
        """Test test case creation"""
        from sdk.testing import TestCase
        
        test_case = TestCase(
            test_id="test_1",
            name="Test Case 1",
            description="A test case"
        )
        
        assert test_case.test_id == "test_1"
        assert len(test_case.assertions) == 0
    
    def test_backtest_runner(self):
        """Test backtest runner"""
        from sdk.testing import BacktestRunner, TestCase
        
        runner = BacktestRunner()
        
        test_case = TestCase(
            test_id="test_1",
            name="Test Case 1"
        )
        
        runner.register_test_suite("test_suite", [test_case])
        
        result = runner.run_test_suite("test_suite")
        
        assert result.suite_name == "test_suite"
        assert result.total_tests == 1


class TestGenerators:
    """Tests for code generators"""
    
    def test_project_generator(self):
        """Test project generator"""
        from sdk.generators import ProjectGenerator
        
        structure = ProjectGenerator.generate("my_project")
        
        assert "project.json" in structure
        assert "strategies/__init__.py" in structure
    
    def test_strategy_template_generator(self):
        """Test strategy template generator"""
        from sdk.generators import StrategyTemplateGenerator
        
        code = StrategyTemplateGenerator.generate("momentum_strategy", "momentum")
        
        assert "MomentumStrategy" in code
        assert "on_tick" in code
    
    def test_config_generator(self):
        """Test config generator"""
        from sdk.generators import ConfigGenerator
        
        config = ConfigGenerator.generate_strategy_profile(
            "conservative_strategy",
            risk_level="conservative"
        )
        
        assert config["name"] == "conservative_strategy"
        assert config["risk_level"] == "conservative"


class TestValidators:
    """Tests for validators"""
    
    def test_plugin_validator(self):
        """Test plugin validator"""
        from sdk.validators import PluginValidator
        
        validator = PluginValidator()
        assert validator is not None
    
    def test_dependency_checker(self):
        """Test dependency checker"""
        from sdk.validators import DependencyChecker
        
        checker = DependencyChecker()
        result = checker.check()
        
        # Should pass for required packages
        assert "requests" in checker.required


class TestTools:
    """Tests for SDK tools"""
    
    def test_performance_profiler(self):
        """Test performance profiler"""
        from sdk.tools import PerformanceProfiler
        
        profiler = PerformanceProfiler()
        
        profiler.start()
        result = profiler.profile_function(sum, [1, 2, 3, 4, 5])
        profiler.stop()
        
        assert result["function"] == "sum"
        assert result["result"] == 15
    
    def test_static_analyzer(self):
        """Test static analyzer"""
        from sdk.tools import StaticAnalyzer
        
        results = StaticAnalyzer.analyze_file(__file__)
        
        assert "file" in results
        assert "lines" in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
