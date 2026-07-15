"""
Tests for Replay Engine
=====================
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from replay import (
    ReplayEngine,
    ReplayEvent,
    ReplayEventType,
    ReplaySession,
    ReplayConfig,
    TickData,
    EventStream,
    PlaybackController,
    PlaybackSpeed,
    TransportState,
    Bookmark,
    EventSynchronizer,
    EventSelector,
    SelectionMode,
    DeterministicEngine,
    ReproducibilityVerifier,
    ReplayExporter,
    ExportFormat,
    ExportOptions
)


class TestReplayEvent:
    """Tests for replay events"""
    
    def test_create_event(self):
        """Test creating a replay event"""
        event = ReplayEvent(
            event_id="test_001",
            event_type=ReplayEventType.TICK,
            timestamp=datetime.now(),
            sequence=1,
            data={"symbol": "R_50", "bid": 1.2345, "ask": 1.2350}
        )
        
        assert event.event_id == "test_001"
        assert event.event_type == ReplayEventType.TICK
        assert event.data["symbol"] == "R_50"
        assert len(event.deterministic_hash) == 64  # SHA256
    
    def test_event_hash_deterministic(self):
        """Test that event hash is deterministic"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        
        event1 = ReplayEvent(
            event_id="same_id",
            event_type=ReplayEventType.TICK,
            timestamp=timestamp,
            sequence=1,
            data={"value": 100}
        )
        
        event2 = ReplayEvent(
            event_id="same_id",
            event_type=ReplayEventType.TICK,
            timestamp=timestamp,
            sequence=1,
            data={"value": 100}
        )
        
        assert event1.deterministic_hash == event2.deterministic_hash


class TestTickData:
    """Tests for tick data"""
    
    def test_tick_properties(self):
        """Test tick data properties"""
        tick = TickData(
            timestamp=datetime.now(),
            symbol="R_50",
            bid=1.2345,
            ask=1.2350,
            bid_size=1000,
            ask_size=1000,
            volume=50000
        )
        
        assert abs(tick.mid - 1.23475) < 0.0001
        assert abs(tick.spread - 0.0005) < 0.0001


class TestEventStream:
    """Tests for event stream"""
    
    def test_stream_iteration(self):
        """Test iterating through events"""
        events = [
            ReplayEvent(f"e{i}", ReplayEventType.TICK, datetime.now(), i, {"i": i})
            for i in range(10)
        ]
        
        stream = EventStream(events)
        
        count = 0
        for event in stream:
            count += 1
        
        assert count == 10
    
    def test_stream_seek(self):
        """Test seeking in stream"""
        events = [
            ReplayEvent(f"e{i}", ReplayEventType.TICK, datetime.now(), i, {"i": i})
            for i in range(10)
        ]
        
        stream = EventStream(events)
        stream.seek(5)
        
        assert stream.position == 5
    
    def test_stream_seek_time(self):
        """Test seeking to timestamp"""
        base = datetime(2024, 1, 1, 12, 0, 0)
        events = [
            ReplayEvent(f"e{i}", ReplayEventType.TICK, base + timedelta(seconds=i*10), i, {})
            for i in range(10)
        ]
        
        stream = EventStream(events)
        target = base + timedelta(seconds=50)
        pos = stream.seek_time(target)
        
        assert pos == 5  # Closest to 50 seconds


class TestReplayEngine:
    """Tests for replay engine"""
    
    def test_initialization(self, tmp_path):
        """Test engine initialization"""
        config = ReplayConfig(default_speed=2.0)
        engine = ReplayEngine(config=config, db_path=str(tmp_path / "test.db"))
        
        assert engine.current_speed == 2.0
        assert engine.is_playing is False
    
    def test_create_session(self, tmp_path):
        """Test creating a session"""
        engine = ReplayEngine(db_path=str(tmp_path / "test.db"))
        
        events = [
            ReplayEvent(f"e{i}", ReplayEventType.TICK, datetime.now(), i, {"i": i})
            for i in range(5)
        ]
        
        session = engine.create_session("Test Session", events)
        
        assert session.name == "Test Session"
        assert len(session.events) == 5
    
    def test_add_bookmark(self, tmp_path):
        """Test adding bookmark"""
        engine = ReplayEngine(db_path=str(tmp_path / "test.db"))
        
        events = [
            ReplayEvent(f"e{i}", ReplayEventType.TICK, datetime.now(), i, {"i": i})
            for i in range(5)
        ]
        engine.create_session("Test", events)
        
        bookmark_id = engine.add_bookmark(datetime.now(), "Test bookmark")
        
        assert bookmark_id is not None
        assert len(engine.current_session.bookmarks) == 1
    
    def test_playback_controls(self, tmp_path):
        """Test playback controls"""
        engine = ReplayEngine(db_path=str(tmp_path / "test.db"))
        
        events = [
            ReplayEvent(f"e{i}", ReplayEventType.TICK, datetime.now(), i, {"i": i})
            for i in range(10)
        ]
        engine.create_session("Test", events)
        
        engine.play()
        assert engine.is_playing is True
        
        engine.pause()
        assert engine.is_playing is False
        
        engine.set_speed(100.0)
        assert engine.current_speed == 100.0
        
        engine.jump_to_start()
        assert engine.position == 0
        
        engine.jump_to_end()
        assert engine.position == len(events) - 1
    
    def test_step_forward_backward(self, tmp_path):
        """Test frame-by-frame stepping"""
        engine = ReplayEngine(db_path=str(tmp_path / "test.db"))
        
        events = [
            ReplayEvent(f"e{i}", ReplayEventType.TICK, datetime.now(), i, {"i": i})
            for i in range(5)
        ]
        engine.create_session("Test", events)
        
        # Step forward
        event = engine.step_forward()
        assert event.sequence == 0
        assert engine.position == 1
        
        engine.step_forward()
        event = engine.step_backward()
        assert event.sequence == 1
        assert engine.position == 1
    
    def test_verify_determinism(self, tmp_path):
        """Test determinism verification"""
        engine = ReplayEngine(db_path=str(tmp_path / "test.db"))
        
        events = [
            ReplayEvent(f"e{i}", ReplayEventType.TICK, datetime.now(), i, {"i": i})
            for i in range(5)
        ]
        engine.create_session("Test", events)
        
        result = engine.verify_determinism()
        
        assert result["valid"] is True


class TestPlaybackController:
    """Tests for playback controller"""
    
    def test_initialization(self):
        """Test controller initialization"""
        engine = MagicMock()
        engine.get_state.return_value = {"position": 0, "total_events": 10, "progress": 0.0}
        engine.current_time = datetime.now()
        engine.position = 0
        engine.current_speed = 1.0
        
        controller = PlaybackController(engine)
        
        assert controller.state == TransportState.STOPPED
        assert controller.current_speed == 1.0
    
    def test_set_speed(self):
        """Test setting speed"""
        engine = MagicMock()
        engine.get_state.return_value = {}
        engine.current_time = datetime.now()
        engine.position = 0
        engine.current_speed = 1.0
        
        controller = PlaybackController(engine)
        controller.set_speed(500.0)
        
        assert controller.current_speed == 500.0
    
    def test_bookmarks(self):
        """Test bookmark management"""
        engine = MagicMock()
        engine.get_state.return_value = {}
        engine.current_time = datetime.now()
        engine.position = 0
        engine.current_speed = 1.0
        
        controller = PlaybackController(engine)
        
        bookmark = controller.add_bookmark(datetime.now(), "Test bookmark", "test")
        
        assert bookmark.description == "Test bookmark"
        assert bookmark.category == "test"
        
        bookmarks = controller.get_bookmarks("test")
        assert len(bookmarks) == 1
    
    def test_annotations(self):
        """Test annotation management"""
        engine = MagicMock()
        engine.get_state.return_value = {}
        engine.current_time = datetime.now()
        engine.position = 0
        engine.current_speed = 1.0
        
        controller = PlaybackController(engine)
        
        annotation = controller.add_annotation(datetime.now(), "Test annotation")
        
        assert annotation.text == "Test annotation"
        
        annotations = controller.get_annotations()
        assert len(annotations) == 1


class TestEventSelector:
    """Tests for event selector"""
    
    def test_select_all(self):
        """Test selecting all events"""
        selector = EventSelector()
        selector.select_all()
        
        events = [
            ReplayEvent(f"e{i}", ReplayEventType.TICK, datetime.now(), i, {"i": i})
            for i in range(10)
        ]
        
        filtered = selector.apply(events)
        
        assert len(filtered) == 10
    
    def test_select_by_types(self):
        """Test selecting by event types"""
        selector = EventSelector()
        selector.select_by_types(["tick"])
        
        events = [
            ReplayEvent("e1", ReplayEventType.TICK, datetime.now(), 1, {}),
            ReplayEvent("e2", ReplayEventType.RISK_CHECK, datetime.now(), 2, {}),
            ReplayEvent("e3", ReplayEventType.TICK, datetime.now(), 3, {}),
        ]
        
        filtered = selector.apply(events)
        
        assert len(filtered) == 2
        assert all(e.event_type == ReplayEventType.TICK for e in filtered)
    
    def test_select_trades_only(self):
        """Test selecting trade events only"""
        selector = EventSelector()
        selector.select_trades_only()
        
        events = [
            ReplayEvent("e1", ReplayEventType.TICK, datetime.now(), 1, {}),
            ReplayEvent("e2", ReplayEventType.TRADE_ENTRY, datetime.now(), 2, {"trade_id": "T1"}),
            ReplayEvent("e3", ReplayEventType.RISK_CHECK, datetime.now(), 3, {}),
        ]
        
        filtered = selector.apply(events)
        
        assert len(filtered) == 1
        assert filtered[0].event_type == ReplayEventType.TRADE_ENTRY
    
    def test_select_strategy_only(self):
        """Test selecting strategy decisions only"""
        selector = EventSelector()
        selector.select_strategy_decisions_only()
        
        events = [
            ReplayEvent("e1", ReplayEventType.TICK, datetime.now(), 1, {}),
            ReplayEvent("e2", ReplayEventType.STRATEGY_DECISION, datetime.now(), 2, {}),
            ReplayEvent("e3", ReplayEventType.SIGNAL_GENERATED, datetime.now(), 3, {}),
        ]
        
        filtered = selector.apply(events)
        
        assert len(filtered) == 2
        assert ReplayEventType.STRATEGY_DECISION in [e.event_type for e in filtered]


class TestDeterministicEngine:
    """Tests for deterministic engine"""
    
    def test_compute_event_hash(self):
        """Test computing event hash"""
        engine = DeterministicEngine()
        
        event = ReplayEvent(
            "test_001",
            ReplayEventType.TICK,
            datetime(2024, 1, 1, 12, 0, 0),
            1,
            {"value": 100}
        )
        
        hash1 = engine.compute_event_hash(event)
        hash2 = engine.compute_event_hash(event)
        
        assert hash1 == hash2
        assert len(hash1) == 64
    
    def test_record_event(self):
        """Test recording events"""
        engine = DeterministicEngine()
        
        event = ReplayEvent("test", ReplayEventType.TICK, datetime.now(), 1, {"v": 1})
        
        hash_val = engine.record_event(event, {"output": 100})
        
        assert hash_val == engine.input_hashes[event.event_id]
        assert event.event_id in engine.output_hashes
    
    def test_verify_determinism(self):
        """Test determinism verification"""
        engine = DeterministicEngine()
        
        events = [
            ReplayEvent(f"e{i}", ReplayEventType.TICK, datetime.now(), i, {"i": i})
            for i in range(5)
        ]
        
        for event in events:
            engine.record_event(event)
        
        result = engine.verify_determinism(events, {})
        
        assert result["verified"] is True


class TestReproducibilityVerifier:
    """Tests for reproducibility verifier"""
    
    def test_register_session(self):
        """Test registering a session"""
        verifier = ReproducibilityVerifier()
        
        events = [
            ReplayEvent(f"e{i}", ReplayEventType.TICK, datetime.now(), i, {"i": i})
            for i in range(5)
        ]
        
        hash_val = verifier.register_session("session_1", events)
        
        assert hash_val is not None
        assert len(hash_val) == 64
    
    def test_verify_reproducibility(self):
        """Test verifying reproducibility"""
        verifier = ReproducibilityVerifier()
        
        events = [
            ReplayEvent(f"e{i}", ReplayEventType.TICK, datetime.now(), i, {"i": i})
            for i in range(5)
        ]
        
        verifier.register_session("session_1", events)
        
        # Same events should be reproducible
        result = verifier.verify_reproducibility("session_1", events)
        
        assert result["reproducible"] is True


class TestReplayExporter:
    """Tests for replay exporter"""
    
    def test_export_json(self, tmp_path):
        """Test JSON export"""
        exporter = ReplayExporter(output_dir=str(tmp_path))
        
        session = ReplaySession(
            "sess_001",
            "Test Session",
            datetime.now(),
            datetime.now() + timedelta(hours=1),
            [
                ReplayEvent("e1", ReplayEventType.TICK, datetime.now(), 1, {"v": 1}),
                ReplayEvent("e2", ReplayEventType.RISK_CHECK, datetime.now(), 2, {"r": "ok"})
            ],
            {},
            []
        )
        
        path = exporter.export_session(session, ExportOptions(format=ExportFormat.JSON))
        
        assert path.endswith(".json")
        assert "sess_001" in path
    
    def test_export_csv(self, tmp_path):
        """Test CSV export"""
        exporter = ReplayExporter(output_dir=str(tmp_path))
        
        session = ReplaySession(
            "sess_001",
            "Test Session",
            datetime.now(),
            datetime.now() + timedelta(hours=1),
            [
                ReplayEvent("e1", ReplayEventType.TICK, datetime.now(), 1, {"v": 1})
            ],
            {},
            []
        )
        
        path = exporter.export_session(session, ExportOptions(format=ExportFormat.CSV))
        
        assert path.endswith(".csv")


class TestEventSynchronizer:
    """Tests for event synchronizer"""
    
    def test_build_timeline(self):
        """Test building synchronized timeline"""
        sync = EventSynchronizer()
        
        events = [
            ReplayEvent("e1", ReplayEventType.TICK, datetime.now(), 1, {"tick": 1}),
            ReplayEvent("e2", ReplayEventType.RISK_CHECK, datetime.now(), 2, {"risk": 1}),
            ReplayEvent("e3", ReplayEventType.TICK, datetime.now(), 3, {"tick": 2}),
        ]
        
        sync.build_timeline(events)
        
        assert sync._total_frames == 3
        assert sync._is_synchronized is True
    
    def test_seek_operations(self):
        """Test seeking in synchronizer"""
        sync = EventSynchronizer()
        
        base = datetime(2024, 1, 1, 12, 0, 0)
        events = [
            ReplayEvent(f"e{i}", ReplayEventType.TICK, base + timedelta(seconds=i), i, {})
            for i in range(10)
        ]
        
        sync.build_timeline(events)
        
        # Seek to frame 5
        frame = sync.seek_to_frame(5)
        assert frame.frame == 5
        
        # Step forward
        frame = sync.step_forward()
        assert frame.frame == 6
        
        # Step backward
        frame = sync.step_backward()
        assert frame.frame == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
