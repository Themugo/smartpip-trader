"""
Observability Platform
====================

Complete observability infrastructure for the trading platform.
Collects metrics, logs, traces, events, and KPIs.
"""

__version__ = "1.0.0"

# Metrics
from observability.metrics import MetricsCollector, Counter, Gauge, Histogram, Summary, metrics, MetricsRegistry, registry

# Logs
from observability.logs import StructuredLogger, LogLevel, structured_logger, log, log_event, set_trace_context, LogContext

# Traces
from observability.traces import Tracer, Span, SpanKind, SpanStatus, tracer, trace, SpanContext

# Events
from observability.events import EventBus, Event, EventType, event_bus, emit_opportunity_detected, emit_trade_executed, emit_risk_alert, emit_model_drift

# KPIs
from observability.kpi import KPITracker, KPIDefinition, KPIValue, BusinessKPI, StrategyKPI, AIKPI, ExecutionKPI, kpi_tracker

# Alerts
from observability.alerts import AlertManager, AlertRule, Alert, AlertSeverity, AlertStatus, alert_manager, setup_default_alerts, AnomalyDetector, AnomalyResult, anomaly_detector

# Dashboards
from observability.dashboards import DashboardData, MetricSnapshot, dashboard_data

# Legacy compatibility
from observability.dashboard import ObservabilityDashboard

__all__ = [
    # Metrics
    "MetricsCollector",
    "Counter",
    "Gauge",
    "Histogram",
    "Summary",
    "metrics",
    "MetricsRegistry",
    "registry",
    # Logs
    "StructuredLogger",
    "LogLevel",
    "structured_logger",
    "log",
    "log_event",
    "set_trace_context",
    "LogContext",
    # Traces
    "Tracer",
    "Span",
    "SpanKind",
    "SpanStatus",
    "tracer",
    "trace",
    "SpanContext",
    # Events
    "EventBus",
    "Event",
    "EventType",
    "event_bus",
    "emit_opportunity_detected",
    "emit_trade_executed",
    "emit_risk_alert",
    "emit_model_drift",
    # KPIs
    "KPITracker",
    "KPIDefinition",
    "KPIValue",
    "BusinessKPI",
    "StrategyKPI",
    "AIKPI",
    "ExecutionKPI",
    "kpi_tracker",
    # Alerts
    "AlertManager",
    "AlertRule",
    "Alert",
    "AlertSeverity",
    "AlertStatus",
    "alert_manager",
    "setup_default_alerts",
    "AnomalyDetector",
    "AnomalyResult",
    "anomaly_detector",
    # Dashboards
    "DashboardData",
    "MetricSnapshot",
    "dashboard_data",
    # Legacy
    "ObservabilityDashboard",
]
