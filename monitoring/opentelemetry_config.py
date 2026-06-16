"""
OpenTelemetry Configuration for SmartPip Trading System
Provides centralized observability with metrics, traces, and logs
"""

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
import os
import logging

logger = logging.getLogger(__name__)


def configure_opentelemetry(app=None, service_name="smartpip-trader"):
    """
    Configure OpenTelemetry for observability
    
    Args:
        app: FastAPI application (optional)
        service_name: Name of the service
    """
    # Create resource with service information
    resource = Resource.create({
        SERVICE_NAME: service_name,
        "service.version": os.getenv("APP_VERSION", "2.1.0"),
        "deployment.environment": os.getenv("ENVIRONMENT", "production"),
        "service.instance.id": os.getenv("INSTANCE_ID", "unknown")
    })
    
    # Configure tracing
    trace_provider = TracerProvider(resource=resource)
    
    # OTLP exporter for traces (sends to Jaeger/Tempo/OTLP collector)
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
    otlp_insecure = os.getenv("OTLP_INSECURE", "false").lower() == "true"
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=otlp_insecure)
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace_provider.add_span_processor(span_processor)
    
    # Set global trace provider
    trace.set_tracer_provider(trace_provider)
    
    # Configure metrics
    metric_readers = []
    
    # Prometheus exporter for metrics (for Grafana/Prometheus)
    prometheus_reader = PrometheusMetricReader()
    metric_readers.append(prometheus_reader)
    
    # OTLP exporter for metrics (optional)
    if os.getenv("ENABLE_OTLP_METRICS", "false").lower() == "true":
        otlp_metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=otlp_insecure)
        metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter, export_interval_millis=15000)
        metric_readers.append(metric_reader)
    
    meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(meter_provider)
    
    # Instrument FastAPI if provided
    if app:
        FastAPIInstrumentor.instrument_app(app)
    
    # Instrument logging
    LoggingInstrumentor().instrument()
    
    logger.info(f"OpenTelemetry configured for {service_name}")
    
    return {
        "trace_provider": trace_provider,
        "meter_provider": meter_provider,
        "prometheus_reader": prometheus_reader
    }


def get_tracer(name: str):
    """Get a tracer for a specific component"""
    return trace.get_tracer(name)


def get_meter(name: str):
    """Get a meter for a specific component"""
    return metrics.get_meter(name)


class TradingMetrics:
    """Custom metrics for trading operations"""
    
    def __init__(self):
        self.meter = get_meter("trading")
        
        # Counter metrics
        self.trade_counter = self.meter.create_counter(
            "trades_total",
            description="Total number of trades executed"
        )
        
        self.trade_wins = self.meter.create_counter(
            "trades_wins_total",
            description="Total number of winning trades"
        )
        
        self.trade_losses = self.meter.create_counter(
            "trades_losses_total",
            description="Total number of losing trades"
        )
        
        # Histogram metrics
        self.trade_duration = self.meter.create_histogram(
            "trade_duration_seconds",
            description="Trade execution duration in seconds"
        )
        
        self.trade_profit = self.meter.create_histogram(
            "trade_profit_amount",
            description="Trade profit/loss amount"
        )
        
        # Gauge metrics
        self.active_trades = self.meter.create_gauge(
            "active_trades",
            description="Number of currently active trades"
        )
        
        self.account_balance = self.meter.create_gauge(
            "account_balance",
            description="Current account balance"
        )
        
        # System metrics
        self.api_latency = self.meter.create_histogram(
            "api_latency_seconds",
            description="API request latency"
        )
        
        self.websocket_connections = self.meter.create_gauge(
            "websocket_connections",
            description="Number of active WebSocket connections"
        )
        
        self.kill_switch_activations = self.meter.create_counter(
            "kill_switch_activations_total",
            description="Number of kill switch activations"
        )
        
        self.rate_limit_blocks = self.meter.create_counter(
            "rate_limit_blocks_total",
            description="Number of rate limit blocks"
        )
    
    def record_trade(self, market: str, direction: str, profit: float, duration: float):
        """Record a trade execution"""
        self.trade_counter.add(1, {"market": market, "direction": direction})
        
        if profit > 0:
            self.trade_wins.add(1, {"market": market})
        else:
            self.trade_losses.add(1, {"market": market})
        
        self.trade_profit.record(profit, {"market": market})
        self.trade_duration.record(duration, {"market": market})
    
    def update_active_trades(self, count: int):
        """Update active trades gauge"""
        self.active_trades.set(count)
    
    def update_balance(self, balance: float):
        """Update account balance gauge"""
        self.account_balance.set(balance)
    
    def record_api_latency(self, endpoint: str, duration: float):
        """Record API request latency"""
        self.api_latency.record(duration, {"endpoint": endpoint})
    
    def update_websocket_connections(self, count: int):
        """Update WebSocket connections gauge"""
        self.websocket_connections.set(count)
    
    def record_kill_switch_activation(self, reason: str):
        """Record kill switch activation"""
        self.kill_switch_activations.add(1, {"reason": reason})
    
    def record_rate_limit_block(self, client_type: str):
        """Record rate limit block"""
        self.rate_limit_blocks.add(1, {"client_type": client_type})


class SecurityMetrics:
    """Custom metrics for security events"""
    
    def __init__(self):
        self.meter = get_meter("security")
        
        # Counter metrics
        self.failed_logins = self.meter.create_counter(
            "security_failed_logins_total",
            description="Total number of failed login attempts"
        )
        
        self.blocked_ips = self.meter.create_counter(
            "security_blocked_ips_total",
            description="Total number of blocked IP addresses"
        )
        
        self.xss_attempts = self.meter.create_counter(
            "security_xss_attempts_total",
            description="Total number of XSS attack attempts"
        )
        
        self.sql_injection_attempts = self.meter.create_counter(
            "security_sql_injection_attempts_total",
            description="Total number of SQL injection attempts"
        )
        
        self.replay_attacks = self.meter.create_counter(
            "security_replay_attacks_total",
            description="Total number of replay attack attempts"
        )
        
        # Gauge metrics
        self.active_sessions = self.meter.create_gauge(
            "security_active_sessions",
            description="Number of active user sessions"
        )
    
    def record_failed_login(self, ip_address: str, reason: str):
        """Record failed login attempt"""
        self.failed_logins.add(1, {"reason": reason})
    
    def record_blocked_ip(self, ip_address: str):
        """Record blocked IP address"""
        self.blocked_ips.add(1)
    
    def record_xss_attempt(self, source: str):
        """Record XSS attack attempt"""
        self.xss_attempts.add(1, {"source": source})
    
    def record_sql_injection_attempt(self, source: str):
        """Record SQL injection attempt"""
        self.sql_injection_attempts.add(1, {"source": source})
    
    def record_replay_attack(self, nonce: str):
        """Record replay attack attempt"""
        self.replay_attacks.add(1)
    
    def update_active_sessions(self, count: int):
        """Update active sessions gauge"""
        self.active_sessions.set(count)


# Global metric instances
trading_metrics = TradingMetrics()
security_metrics = SecurityMetrics()
