"""
Tests for Simulation Framework
============================
"""

import pytest
import time


class TestExecutionSimulator:
    """Tests for ExecutionSimulator"""
    
    def test_simulator_initialization(self):
        """Test simulator initialization"""
        from simulation import ExecutionSimulator, SimulationConfig
        
        config = SimulationConfig(
            min_latency_ms=10,
            max_latency_ms=100,
            order_rejection_rate=0.0,
        )
        sim = ExecutionSimulator(config)
        
        assert sim.config.min_latency_ms == 10
        assert sim.config.max_latency_ms == 100
    
    def test_submit_order(self):
        """Test order submission"""
        from simulation import ExecutionSimulator, SimulationConfig
        from simulation.simulator import OrderSide, OrderType
        
        sim = ExecutionSimulator(SimulationConfig(order_rejection_rate=0.0))
        sim.start()
        
        order = sim.submit_order(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
            market_price=50000,
        )
        
        assert order is not None
        assert order.symbol == "BTC/USD"
        
        sim.stop()
    
    def test_order_cancellation(self):
        """Test order cancellation"""
        from simulation import ExecutionSimulator, SimulationConfig
        from simulation.simulator import OrderSide, OrderType
        
        sim = ExecutionSimulator(SimulationConfig())
        sim.start()
        
        order = sim.submit_order(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
            market_price=50000,
        )
        
        cancelled = sim.cancel_order(order.order_id)
        # May or may not be cancelled depending on timing
        assert isinstance(cancelled, bool)
        
        sim.stop()
    
    def test_latency_simulation(self):
        """Test latency simulation"""
        from simulation import ExecutionSimulator, SimulationConfig
        from simulation.simulator import OrderSide, OrderType
        
        config = SimulationConfig(
            min_latency_ms=10,
            max_latency_ms=20,
            order_rejection_rate=0.0,
        )
        sim = ExecutionSimulator(config)
        sim.start()
        
        start = time.time()
        sim.submit_order(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
            market_price=50000,
        )
        duration_ms = (time.time() - start) * 1000
        
        assert duration_ms >= 10
        assert duration_ms <= 100  # Allow more buffer for CI environments
        
        sim.stop()
    
    def test_result_calculation(self):
        """Test simulation result calculation"""
        from simulation import ExecutionSimulator, SimulationConfig
        from simulation.simulator import OrderSide, OrderType
        
        sim = ExecutionSimulator(SimulationConfig(order_rejection_rate=0.0))
        sim.start()
        
        # Submit some orders
        for _ in range(5):
            sim.submit_order(
                symbol="BTC/USD",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=1.0,
                market_price=50000,
            )
        
        result = sim.calculate_result()
        
        assert result.total_orders == 5
        assert result.resilience_score >= 0
        assert len(result.recommendations) > 0


class TestFailureInjector:
    """Tests for FailureInjector"""
    
    def test_injector_initialization(self):
        """Test failure injector initialization"""
        from simulation.failures import FailureInjector, FailureType
        
        injector = FailureInjector()
        
        assert not injector.is_active
    
    def test_start_stop(self):
        """Test starting and stopping injector"""
        from simulation.failures import FailureInjector
        
        injector = FailureInjector()
        injector.start()
        
        assert injector.is_active
        
        injector.stop()
        
        assert not injector.is_active
    
    def test_inject_failure(self):
        """Test failure injection"""
        from simulation.failures import FailureInjector, FailureType
        
        injector = FailureInjector()
        injector.start()
        
        # Inject a failure (with short duration)
        info = injector.inject_failure(
            FailureType.API_ERROR,
            duration_ms=100,
        )
        
        assert info["injected"] is True
        assert info["type"] == FailureType.API_ERROR.value
        
        injector.stop()
    
    def test_failure_callback(self):
        """Test failure callbacks"""
        from simulation.failures import FailureInjector, FailureType
        
        injector = FailureInjector()
        
        received = []
        def callback(info):
            received.append(info)
        
        injector.on_failure(callback)
        injector.start()
        injector.inject_failure(FailureType.NETWORK_TIMEOUT, duration_ms=50)
        
        assert len(received) == 1
        
        injector.stop()
    
    def test_network_conditions(self):
        """Test network conditions"""
        from simulation.failures import NetworkConditions
        
        conditions = NetworkConditions(
            latency_ms=100,
            jitter_ms=10,
            packet_loss_rate=0.05,
        )
        
        # Test latency with jitter
        latency = conditions.apply_latency()
        assert 90 <= latency <= 110
        
        # Test packet drop
        dropped = 0
        for _ in range(100):
            if conditions.should_drop_packet():
                dropped += 1
        
        assert 0 <= dropped <= 15  # Roughly 5%


class TestIncidentRecorder:
    """Tests for IncidentRecorder"""
    
    def test_recorder_initialization(self):
        """Test incident recorder initialization"""
        from simulation.incidents import IncidentRecorder
        
        recorder = IncidentRecorder(storage_path="/tmp/test_incidents")
        
        assert not recorder.is_recording()
    
    def test_start_stop_recording(self):
        """Test starting and stopping recording"""
        from simulation.incidents import IncidentRecorder
        
        recorder = IncidentRecorder()
        recorder.start_recording("test_1", "Test Incident", "Description")
        
        assert recorder.is_recording()
        
        incident = recorder.stop_recording()
        
        assert incident is not None
        assert incident.incident_id == "test_1"
        assert not recorder.is_recording()
    
    def test_record_events(self):
        """Test recording events"""
        from simulation.incidents import IncidentRecorder
        
        recorder = IncidentRecorder()
        recorder.start_recording("test_2", "Test Incident", "Description")
        
        recorder.record_event("test_event", {"key": "value"})
        recorder.record_error("ERROR", "Test error", {"context": "test"})
        
        incident = recorder.stop_recording()
        
        assert len(incident.events) == 2
        assert incident.events[0]["type"] == "test_event"


class TestIncidentReplayer:
    """Tests for IncidentReplayer"""
    
    def test_replayer_initialization(self):
        """Test incident replayer initialization"""
        from simulation.incidents import IncidentRecorder, IncidentReplayer
        
        recorder = IncidentRecorder()
        replayer = IncidentReplayer(recorder)
        
        assert not replayer.is_playing
    
    def test_playback_speed(self):
        """Test playback speed setting"""
        from simulation.incidents import IncidentRecorder, IncidentReplayer
        
        recorder = IncidentRecorder()
        replayer = IncidentReplayer(recorder)
        
        replayer.set_playback_speed(2.0)
        
        # Speed should be set (implementation check)
        assert replayer._playback_speed == 2.0
    
    def test_replay(self):
        """Test incident replay"""
        from simulation.incidents import IncidentRecorder, IncidentReplayer, Incident
        
        recorder = IncidentRecorder()
        replayer = IncidentReplayer(recorder)
        
        # Create a test incident
        incident = Incident(
            incident_id="test_replay",
            name="Test Replay",
            description="Test",
            start_time=time.time(),
            end_time=time.time() + 0.5,
            severity="low",
            events=[
                {"type": "test", "timestamp": time.time(), "data": {}},
            ]
        )
        
        replayer.set_playback_speed(10.0)  # Speed up playback
        
        results = replayer.replay(incident)
        
        assert results["success"] is True


class TestStressTestRunner:
    """Tests for StressTestRunner"""
    
    def test_config_initialization(self):
        """Test stress test config"""
        from simulation.stress_test import StressTestConfig
        
        config = StressTestConfig(
            name="Test Stress",
            duration_seconds=10,
            orders_per_second=5,
        )
        
        assert config.name == "Test Stress"
        assert config.duration_seconds == 10
    
    def test_runner_initialization(self):
        """Test stress test runner initialization"""
        from simulation.stress_test import StressTestRunner, StressTestConfig
        from simulation import ExecutionSimulator
        
        sim = ExecutionSimulator()
        
        # Mock strategy
        class MockStrategy:
            def on_tick(self, tick):
                return []
        
        runner = StressTestRunner(MockStrategy(), sim)
        
        assert runner.simulator is not None


class TestResilienceAnalyzer:
    """Tests for ResilienceAnalyzer"""
    
    def test_analyzer_initialization(self):
        """Test resilience analyzer initialization"""
        from simulation.resilience import ResilienceAnalyzer
        
        analyzer = ResilienceAnalyzer()
        
        assert len(analyzer._test_results) == 0
    
    def test_add_results(self):
        """Test adding test results"""
        from simulation.resilience import ResilienceAnalyzer
        
        analyzer = ResilienceAnalyzer()
        
        result = {
            "total_orders": 100,
            "successful_orders": 95,
            "avg_latency_ms": 50,
        }
        
        analyzer.add_test_result(result)
        
        assert len(analyzer._test_results) == 1
    
    def test_generate_report(self):
        """Test report generation"""
        from simulation.resilience import ResilienceAnalyzer
        
        analyzer = ResilienceAnalyzer()
        
        # Add test result
        analyzer.add_test_result({
            "total_orders": 100,
            "successful_orders": 95,
            "avg_latency_ms": 50,
            "network_failures": 1,
            "api_failures": 1,
            "recommendations": ["Good performance"],
            "fragile_strategies": [],
        })
        
        report = analyzer.generate_report()
        
        assert report is not None
        assert report.overall_score >= 0
        assert report.overall_score <= 100


class TestIntegration:
    """Integration tests"""
    
    def test_full_simulation_flow(self):
        """Test complete simulation flow"""
        from simulation import ExecutionSimulator, SimulationConfig
        from simulation.failures import FailureInjector, FailureType
        from simulation.resilience import ResilienceAnalyzer
        from simulation.simulator import OrderSide, OrderType
        
        # Setup
        config = SimulationConfig(order_rejection_rate=0.05)
        sim = ExecutionSimulator(config)
        injector = FailureInjector()
        analyzer = ResilienceAnalyzer()
        
        # Start simulation
        sim.start()
        injector.start()
        
        # Run simulation with failures
        for i in range(20):
            # Occasionally inject failure
            if i % 5 == 0:
                injector.inject_failure(FailureType.API_ERROR, duration_ms=50)
            
            # Submit orders
            order = sim.submit_order(
                symbol="BTC/USD",
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=1.0,
                market_price=50000 + i * 10,
            )
        
        # Stop
        injector.stop()
        sim.stop()
        
        # Get results
        result = sim.calculate_result()
        
        # Add to analyzer
        analyzer.add_test_result(result.to_dict())
        
        # Generate report
        report = analyzer.generate_report()
        
        assert report.overall_score >= 0
        assert len(report.recommendations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
