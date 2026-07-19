"""
Dashboard Data API
==================

Provides data for observability dashboards.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    """A snapshot of a metric"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class DashboardData:
    """
    Central dashboard data provider.
    
    Provides data for:
    - Latency dashboards
    - Resource usage (CPU, Memory, Disk, GPU)
    - Queue length
    - WebSocket/API/Strategy health
    - Model drift
    - Risk events
    - Prediction accuracy
    - Expected value
    - Opportunity metrics
    - Paper vs Live performance
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
    
    def get_latency_data(
        self,
        metric_name: str,
        since: Optional[float] = None,
        until: Optional[float] = None,
        buckets: int = 60
    ) -> Dict[str, Any]:
        """Get latency data for dashboard"""
        # Import metrics
        from observability.metrics import registry
        
        data = registry.query_aggregated(metric_name, since=since, until=until, aggregation="avg")
        
        return {
            "metric": metric_name,
            "current": data,
            "p50": registry.query_percentile(metric_name, 50, since=since, until=until),
            "p95": registry.query_percentile(metric_name, 95, since=since, until=until),
            "p99": registry.query_percentile(metric_name, 99, since=since, until=until),
            "max": registry.query_aggregated(metric_name, since=since, until=until, aggregation="max"),
            "min": registry.query_aggregated(metric_name, since=since, until=until, aggregation="min"),
            "count": registry.query_aggregated(metric_name, since=since, until=until, aggregation="count"),
        }
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage"""
        import psutil
        
        return {
            "timestamp": time.time(),
            "cpu": {
                "percent": psutil.cpu_percent(interval=0.1),
                "count": psutil.cpu_count(),
                "per_cpu": psutil.cpu_percent(interval=0.1, percpu=True),
            },
            "memory": {
                "percent": psutil.virtual_memory().percent,
                "used_mb": psutil.virtual_memory().used / (1024 * 1024),
                "available_mb": psutil.virtual_memory().available / (1024 * 1024),
                "total_mb": psutil.virtual_memory().total / (1024 * 1024),
            },
            "disk": {
                "percent": psutil.disk_usage("/").percent,
                "used_gb": psutil.disk_usage("/").used / (1024 * 1024 * 1024),
                "total_gb": psutil.disk_usage("/").total / (1024 * 1024 * 1024),
            },
            "network": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv,
            },
            "process": {
                "memory_mb": psutil.Process().memory_info().rss / (1024 * 1024),
                "cpu_percent": psutil.Process().cpu_percent(),
                "threads": psutil.Process().num_threads(),
                "open_files": len(psutil.Process().open_files()),
            }
        }
    
    def get_queue_health(self) -> Dict[str, Any]:
        """Get queue health metrics"""
        from observability.metrics import metrics
        
        return {
            "timestamp": time.time(),
            "length": metrics.gauge("queue_length").get(),
            "processing_time": metrics.gauge("queue_processing_time").get(),
            "backlog": metrics.gauge("queue_backlog").get() if hasattr(metrics.gauge("queue_backlog"), 'get') else 0,
        }
    
    def get_websocket_health(self) -> Dict[str, Any]:
        """Get WebSocket health metrics"""
        from observability.metrics import metrics
        
        return {
            "timestamp": time.time(),
            "connections": metrics.gauge("websocket_connections").get(),
            "messages_sent": metrics.counter("websocket_messages_sent").get(),
            "messages_received": metrics.counter("websocket_messages_received").get(),
            "latency_p50": metrics.summary("websocket_latency").get_quantiles().get(0.5, 0),
            "latency_p99": metrics.summary("websocket_latency").get_quantiles().get(0.99, 0),
        }
    
    def get_api_health(self) -> Dict[str, Any]:
        """Get API health metrics"""
        from observability.metrics import metrics
        
        return {
            "timestamp": time.time(),
            "requests_total": metrics.counter("api_requests_total").get(),
            "latency_p50": metrics.histogram("api_request_duration").get_stats().get("avg", 0) * 1000,
            "latency_p95": metrics.histogram("api_request_duration").get_stats().get("buckets", {}).get(1.0, 0),
            "errors": metrics.counter("api_errors_total").get() if hasattr(metrics.counter("api_errors_total"), 'get') else 0,
        }
    
    def get_strategy_health(self) -> Dict[str, Any]:
        """Get strategy health metrics"""
        from observability.kpi import kpi_tracker
        
        return {
            "timestamp": time.time(),
            "pnl": kpi_tracker.get("strategy_pnl"),
            "pnl_daily": kpi_tracker.get("strategy_pnl_daily"),
            "positions": kpi_tracker.get("strategy_positions"),
            "drawdown": kpi_tracker.get("strategy_drawdown"),
            "max_drawdown": kpi_tracker.get("max_drawdown"),
            "sharpe_ratio": kpi_tracker.get("sharpe_ratio"),
            "paper_vs_live": kpi_tracker.get("paper_vs_live_ratio"),
        }
    
    def get_model_health(self) -> Dict[str, Any]:
        """Get AI/Model health metrics"""
        from observability.kpi import kpi_tracker
        from observability.alerts import anomaly_detector
        
        model_stats = anomaly_detector.get_statistics("model_drift")
        
        return {
            "timestamp": time.time(),
            "drift_score": kpi_tracker.get("model_drift"),
            "prediction_accuracy": kpi_tracker.get("prediction_accuracy"),
            "prediction_confidence": kpi_tracker.get("prediction_confidence"),
            "inference_latency": kpi_tracker.get("inference_latency"),
            "model_version": kpi_tracker.get("model_version"),
            "drift_statistics": model_stats,
        }
    
    def get_execution_health(self) -> Dict[str, Any]:
        """Get execution health metrics"""
        from observability.kpi import kpi_tracker
        from observability.metrics import metrics
        
        return {
            "timestamp": time.time(),
            "orders_submitted": kpi_tracker.get("orders_submitted"),
            "orders_filled": kpi_tracker.get("orders_filled"),
            "orders_rejected": kpi_tracker.get("orders_rejected"),
            "fill_rate": kpi_tracker.get("fill_rate"),
            "execution_latency": kpi_tracker.get("execution_latency"),
            "slippage_bps": kpi_tracker.get("slippage_bps"),
            "rejection_rate": kpi_tracker.get("rejection_rate"),
        }
    
    def get_opportunity_metrics(self) -> Dict[str, Any]:
        """Get opportunity metrics"""
        from observability.kpi import kpi_tracker
        from observability.events import event_bus
        from observability.events import EventType
        
        counts = event_bus.get_event_counts(since=time.time() - 86400)
        
        return {
            "timestamp": time.time(),
            "opportunities_detected": kpi_tracker.get("opportunities_detected"),
            "opportunities_accepted": kpi_tracker.get("opportunities_accepted"),
            "opportunities_rejected": kpi_tracker.get("opportunities_rejected"),
            "acceptance_rate": kpi_tracker.get("acceptance_rate"),
            "opportunity_score": kpi_tracker.get("opportunity_score"),
            "expected_value": kpi_tracker.get("expected_value"),
            "decision_frequency": kpi_tracker.get("decision_frequency"),
            "event_counts_24h": counts,
        }
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get risk metrics"""
        from observability.events import event_bus
        from observability.events import EventType
        
        risk_events = event_bus.get_events(
            event_type=EventType.RISK_LIMIT_HIT,
            since=time.time() - 86400
        )
        
        return {
            "timestamp": time.time(),
            "risk_events_24h": len(risk_events),
            "risk_alerts": [
                {
                    "id": e.id,
                    "message": e.data.get("message", ""),
                    "timestamp": e.timestamp,
                    "severity": e.severity
                }
                for e in risk_events[-10:]
            ],
        }
    
    def get_comprehensive_dashboard(self) -> Dict[str, Any]:
        """Get all dashboard data"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resources": self.get_resource_usage(),
            "queue": self.get_queue_health(),
            "websocket": self.get_websocket_health(),
            "api": self.get_api_health(),
            "strategy": self.get_strategy_health(),
            "model": self.get_model_health(),
            "execution": self.get_execution_health(),
            "opportunities": self.get_opportunity_metrics(),
            "risk": self.get_risk_metrics(),
        }
    
    def get_historical_data(
        self,
        metric_name: str,
        since: float,
        until: float,
        bucket_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """Get historical data with bucketing"""
        from observability.metrics import registry
        
        # Calculate bucket size
        bucket_seconds = bucket_minutes * 60
        num_buckets = int((until - since) / bucket_seconds)
        
        result = []
        for i in range(num_buckets):
            bucket_start = since + i * bucket_seconds
            bucket_end = bucket_start + bucket_seconds
            
            avg = registry.query_aggregated(
                metric_name,
                since=bucket_start,
                until=bucket_end,
                aggregation="avg"
            )
            
            result.append({
                "timestamp": bucket_start,
                "avg": avg,
                "min": registry.query_aggregated(metric_name, since=bucket_start, until=bucket_end, aggregation="min"),
                "max": registry.query_aggregated(metric_name, since=bucket_start, until=bucket_end, aggregation="max"),
                "count": registry.query_aggregated(metric_name, since=bucket_start, until=bucket_end, aggregation="count"),
            })
        
        return result


# Global dashboard data instance
dashboard_data = DashboardData()
