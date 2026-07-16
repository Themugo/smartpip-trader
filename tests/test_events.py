"""
Tests for Event Sourcing Platform
================================
"""

import pytest
import time
import numpy as np


class TestEventCore:
    """Tests for event core"""
    
    def test_event_creation(self):
        """Test creating an event"""
        from events.core import Event, EventType, EventMetadata
        
        metadata = EventMetadata(
            event_id="test_001",
            sequence_number=1,
            timestamp=time.time(),
            correlation_id="corr_001",
        )
        
        event = Event(
            event_type=EventType.MARKET_TICK,
            metadata=metadata,
            payload={"symbol": "BTCUSD", "price": 50000},
        )
        
        assert event.event_type == EventType.MARKET_TICK
        assert event.payload["symbol"] == "BTCUSD"
        assert event.metadata.checksum != ""
    
    def test_event_integrity(self):
        """Test event integrity verification"""
        from events.core import Event, EventType, EventMetadata
        
        event = Event(
            event_type=EventType.MARKET_TICK,
            metadata=EventMetadata(),
            payload={"symbol": "ETHUSD", "price": 3000},
        )
        
        assert event.verify_integrity() is True
    
    def test_event_serialization(self):
        """Test event serialization"""
        from events.core import Event, EventType, EventMetadata
        
        event = Event(
            event_type=EventType.AI_PREDICTION,
            metadata=EventMetadata(),
            payload={"prediction": "buy", "confidence": 0.85},
        )
        
        json_str = event.to_json()
        restored = Event.from_dict(eval(json_str))
        
        assert restored.event_type == EventType.AI_PREDICTION
        assert restored.payload["prediction"] == "buy"


class TestEventStore:
    """Tests for event store"""
    
    def test_append_event(self):
        """Test appending events"""
        from events.core import EventStore, Event, EventType, EventMetadata
        
        store = EventStore()
        
        event = Event(
            event_type=EventType.MARKET_TICK,
            metadata=EventMetadata(),
            payload={"symbol": "BTCUSD", "price": 50000},
        )
        
        result = store.append(event)
        
        assert result.metadata.sequence_number == 0
        assert store.count() == 1
    
    def test_query_events(self):
        """Test querying events"""
        from events.core import EventStore, Event, EventType, EventMetadata
        
        store = EventStore()
        
        for i in range(5):
            event = Event(
                event_type=EventType.MARKET_TICK,
                metadata=EventMetadata(correlation_id="corr_1"),
                payload={"price": 50000 + i},
            )
            store.append(event)
        
        events = store.get_events(correlation_id="corr_1")
        
        assert len(events) == 5
    
    def test_integrity_verification(self):
        """Test event chain integrity"""
        from events.core import EventStore, Event, EventType, EventMetadata
        
        store = EventStore()
        
        for i in range(3):
            event = Event(
                event_type=EventType.MARKET_TICK,
                metadata=EventMetadata(),
                payload={"sequence": i},
            )
            store.append(event)
        
        integrity = store.verify_integrity()
        
        assert integrity["valid"] is True
        assert integrity["total_events"] == 3


class TestMarketEvents:
    """Tests for market events"""
    
    def test_market_tick_event(self):
        """Test market tick event"""
        from events.market import MarketTickEvent
        
        event = MarketTickEvent(
            symbol="BTCUSD",
            price=50000,
            volume=100,
            bid=49999,
            ask=50001,
            timestamp=time.time(),
        )
        
        assert event.payload["symbol"] == "BTCUSD"
        assert event.payload["spread"] == 2


class TestStatisticalValidation:
    """Tests for statistical validation"""
    
    def test_basic_metrics(self):
        """Test basic metrics calculation"""
        from validation.statistical import _calculate_basic_metrics
        import numpy as np
        
        returns = np.array([0.01, -0.005, 0.02, -0.01, 0.015])
        
        metrics = _calculate_basic_metrics(returns)
        
        assert "win_rate" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics
    
    def test_walk_forward_validator(self):
        """Test walk-forward validation"""
        from validation.statistical import WalkForwardValidator
        import numpy as np
        
        # Generate returns
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 1000)
        
        validator = WalkForwardValidator()
        result = validator.validate(returns, window_size=100, step_size=50)
        
        assert result.validation_type.value == "walk_forward"
    
    def test_monte_carlo_validator(self):
        """Test Monte Carlo validation"""
        from validation.statistical import MonteCarloValidator
        import numpy as np
        
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 500)
        
        validator = MonteCarloValidator()
        result = validator.validate(returns, n_simulations=1000)
        
        assert result.validation_type.value == "monte_carlo"


class TestDataQuality:
    """Tests for data quality"""
    
    def test_quality_checker(self):
        """Test data quality checker"""
        from data_quality.checker import DataQualityChecker
        import pandas as pd
        
        # Create sample data
        data = {
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "symbol": ["BTCUSD"] * 100,
            "open": np.random.uniform(49000, 51000, 100),
            "high": np.random.uniform(49000, 51000, 100),
            "low": np.random.uniform(49000, 51000, 100),
            "close": np.random.uniform(49000, 51000, 100),
            "volume": np.random.uniform(100, 1000, 100),
        }
        df = pd.DataFrame(data)
        
        checker = DataQualityChecker()
        report = checker.check(df, "test_001", "Test Dataset")
        
        assert report.dataset_id == "test_001"
        assert report.quality_score > 0
    
    def test_missing_data_detection(self):
        """Test missing data detection"""
        from data_quality.checker import DataQualityChecker
        import pandas as pd
        import numpy as np
        
        data = {
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "symbol": ["BTCUSD"] * 100,
            "close": np.concatenate([np.random.uniform(49000, 51000, 80), [np.nan] * 20]),
        }
        df = pd.DataFrame(data)
        
        checker = DataQualityChecker()
        report = checker.check(df, "test_002", "Missing Data Test")
        
        assert report.metrics["missing_ratio"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
