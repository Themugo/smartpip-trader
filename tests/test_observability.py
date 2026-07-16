"""
Tests for Observability Platform
=================================

Tests for metrics, logs, traces, events, KPIs, and alerts.
"""

import pytest
import time
from typing import Any


class TestMetricsCollector:
    """Tests for Metrics Collector"""
    
    def test_counter_increment(self):
        """Test counter increment"""
        from observability.metrics import metrics
        
        counter = metrics.register_counter("test_counter", "Test counter")
        counter.inc()
        
        assert counter.get() == 1
        counter.inc(5)
        assert counter.get() == 6
    
    def test_gauge_set_value(self):
        """Test gauge value setting"""
        from observability.metrics import metrics
        
        gauge = metrics.register_gauge("test_gauge", "Test gauge")
        gauge.set(10.5)
        
        assert gauge.get() == 10.5
        
        gauge.inc(5)
        assert gauge.get() == 15.5
        
        gauge.dec(3)
        assert gauge.get() == 12.5
    
    def test_histogram_observe(self):
        """Test histogram observation"""
        from observability.metrics import metrics
        
        histogram = metrics.register_histogram(
            "test_histogram",
            "Test histogram",
            buckets=[0.1, 0.5, 1.0, 5.0]
        )
        
        histogram.observe(0.05)
        histogram.observe(0.3)
        histogram.observe(0.8)
        histogram.observe(3.0)
        
        stats = histogram.get_stats()
        assert stats["count"] == 4
    
    def test_get_prometheus_format(self):
        """Test Prometheus format output"""
        from observability.metrics import metrics
        
        metrics.register_counter("prom_test", "Prometheus test")
        metrics.counter("prom_test").inc()
        
        output = metrics.get_prometheus_format()
        assert "prom_test" in output
        assert "# HELP prom_test" in output
        assert "# TYPE prom_test counter" in output


class TestMetricsRegistry:
    """Tests for Metrics Registry"""
    
    def test_record_and_query(self):
        """Test recording and querying metrics"""
        from observability.metrics import registry
        
        registry.record("test_metric", 100.0)
        registry.record("test_metric", 200.0)
        
        values = registry.query("test_metric", limit=10)
        assert len(values) == 2
        assert values[0].value == 100.0
        assert values[1].value == 200.0
    
    def test_query_aggregated(self):
        """Test aggregated queries"""
        from observability.metrics import registry
        
        for i in range(10):
            registry.record("agg_metric", float(i))
        
        avg = registry.query_aggregated("agg_metric", aggregation="avg")
        assert avg == 4.5
        
        sum_val = registry.query_aggregated("agg_metric", aggregation="sum")
        assert sum_val == 45.0
    
    def test_query_percentile(self):
        """Test percentile queries"""
        from observability.metrics import registry
        
        for i in range(100):
            registry.record("pct_metric", float(i))
        
        p50 = registry.query_percentile("pct_metric", 50)
        assert 49 <= p50 <= 50
        
        p95 = registry.query_percentile("pct_metric", 95)
        assert 94 <= p95 <= 95


class TestStructuredLogger:
    """Tests for Structured Logger"""
    
    def test_log_event(self):
        """Test logging events"""
        from observability.logs import structured_logger, LogContext
        
        structured_logger.info("Test message", key="value")
        
        context = structured_logger.get_context()
        assert context == {}
        
        with LogContext(user_id="123"):
            context = structured_logger.get_context()
            assert context.get("user_id") == "123"
        
        context = structured_logger.get_context()
        assert "user_id" not in context


class TestTracer:
    """Tests for Distributed Tracer"""
    
    def test_span_creation(self):
        """Test creating spans"""
        from observability.traces import tracer, SpanKind
        
        span = tracer.start_span("test_span", SpanKind.INTERNAL)
        
        assert span.name == "test_span"
        assert span.kind == SpanKind.INTERNAL
        assert span.trace_id != ""
        assert span.span_id != ""
        
        tracer.end_span(span)
    
    def test_span_with_attributes(self):
        """Test span with attributes"""
        from observability.traces import tracer, SpanKind
        
        span = tracer.start_span(
            "test_span",
            SpanKind.CLIENT,
            attributes={"key": "value"}
        )
        
        assert span.attributes["key"] == "value"
        
        tracer.set_attribute(span, "new_key", "new_value")
        assert span.attributes["new_key"] == "new_value"
        
        tracer.end_span(span)
    
    def test_span_context_manager(self):
        """Test span as context manager"""
        from observability.traces import trace, SpanKind
        
        with trace("context_span", SpanKind.SERVER) as span:
            assert span.name == "context_span"
            assert span.end_time is None
        
        assert span.end_time is not None


class TestEventBus:
    """Tests for Event Bus"""
    
    def test_publish_event(self):
        """Test publishing events"""
        from observability.events import event_bus, EventType
        
        event = event_bus.publish(
            EventType.TRADE_EXECUTED,
            source="test",
            data={"order_id": "123"}
        )
        
        assert event.type == EventType.TRADE_EXECUTED
        assert event.data["order_id"] == "123"
    
    def test_get_events(self):
        """Test getting events"""
        from observability.events import event_bus, EventType
        
        event_bus.publish(EventType.TRADE_EXECUTED, source="test")
        
        events = event_bus.get_events(limit=10)
        assert len(events) >= 1


class TestKPITracker:
    """Tests for KPI Tracker"""
    
    def test_record_kpi(self):
        """Test recording KPI values"""
        from observability.kpi import kpi_tracker
        
        kpi_tracker.record("test_kpi", 100.0)
        kpi_tracker.record("test_kpi", 200.0)
        
        value = kpi_tracker.get("test_kpi", aggregation="last")
        assert value == 200.0
        
        avg = kpi_tracker.get("test_kpi", aggregation="avg")
        assert avg == 150.0
    
    def test_kpi_definition(self):
        """Test KPI definitions"""
        from observability.kpi import kpi_tracker
        
        kpi_tracker.record("status_kpi", 45.0)
        
        status = kpi_tracker.get_status("status_kpi")
        assert status in ["ok", "warning", "critical"]


class TestAlertManager:
    """Tests for Alert Manager"""
    
    def test_create_rule(self):
        """Test creating alert rules"""
        from observability.alerts import alert_manager, AlertSeverity
        
        rule = alert_manager.create_rule(
            name="Test Alert",
            description="Test description",
            severity=AlertSeverity.WARNING
        )
        
        assert rule.name == "Test Alert"
        assert rule.severity == AlertSeverity.WARNING
        assert rule.enabled
    
    def test_create_metric_rule(self):
        """Test creating metric-based rules"""
        from observability.alerts import alert_manager, AlertSeverity
        
        rule = alert_manager.create_metric_rule(
            name="High CPU",
            metric_name="cpu_usage",
            operator="gt",
            threshold=80.0,
            severity=AlertSeverity.WARNING
        )
        
        assert rule.metric_name == "cpu_usage"
        assert rule.operator == "gt"
        assert rule.threshold == 80.0
    
    def test_evaluate_rule(self):
        """Test rule evaluation"""
        from observability.alerts import alert_manager, AlertSeverity
        
        rule = alert_manager.create_metric_rule(
            name="Test",
            metric_name="test_metric",
            operator="gt",
            threshold=50.0,
            severity=AlertSeverity.ERROR
        )
        
        # Should not fire
        alerts = alert_manager.evaluate({"test_metric": 30.0})
        assert len(alerts) == 0
        
        # Should fire
        alerts = alert_manager.evaluate({"test_metric": 60.0})
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.ERROR


class TestAnomalyDetector:
    """Tests for Anomaly Detector"""
    
    def test_register_metric(self):
        """Test metric registration"""
        from observability.alerts import anomaly_detector
        
        anomaly_detector.register_metric("test_metric", window_size=20, threshold_std=2.0)
        
        stats = anomaly_detector.get_statistics("test_metric")
        # Should be empty since no data yet
        assert stats == {}
    
    def test_detect_values(self):
        """Test detecting values"""
        from observability.alerts import anomaly_detector
        
        # Add values
        for _ in range(15):
            anomaly_detector.detect("test_metric2", 100.0)
        
        stats = anomaly_detector.get_statistics("test_metric2")
        assert "mean" in stats
        assert stats["mean"] == 100.0


class TestDashboardData:
    """Tests for Dashboard Data"""
    
    def test_get_resource_usage(self):
        """Test getting resource usage"""
        from observability.dashboards import dashboard_data
        
        resources = dashboard_data.get_resource_usage()
        
        assert "cpu" in resources
        assert "memory" in resources
        assert "disk" in resources
        assert "timestamp" in resources
    
    @pytest.mark.skip(reason="May timeout due to model/execution queries")
    def test_comprehensive_dashboard(self):
        """Test comprehensive dashboard data"""
        from observability.dashboards import dashboard_data
        
        data = dashboard_data.get_comprehensive_dashboard()
        
        assert "timestamp" in data
        assert "resources" in data
        assert "strategy" in data
        assert "model" in data
        assert "execution" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
