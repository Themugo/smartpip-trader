"""
Observability API Routes
=========================

Provides endpoints for metrics, logs, traces, events, KPIs, and dashboards.
"""

import time
import logging
from datetime import datetime, timezone, timedelta, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/observability", tags=["Observability"])


# ============= Metrics Routes =============

class MetricQuery(BaseModel):
    metric_name: str
    since: Optional[float] = None
    until: Optional[float] = None
    aggregation: Optional[str] = "avg"


@router.get("/metrics")
async def get_metrics():
    """Get all registered metrics"""
    from observability.metrics import metrics
    
    return metrics.get_all_metrics()


@router.get("/metrics/{metric_name}")
async def get_metric(
    metric_name: str,
    since: Optional[float] = None,
    until: Optional[float] = None,
    aggregation: str = "avg"
):
    """Get metric values"""
    from observability.metrics import registry
    
    value = registry.query_aggregated(
        metric_name,
        since=since,
        until=until,
        aggregation=aggregation
    )
    
    return {
        "metric_name": metric_name,
        "value": value,
        "aggregation": aggregation,
        "since": since,
        "until": until,
    }


@router.get("/metrics/{metric_name}/timeseries")
async def get_metric_timeseries(
    metric_name: str,
    since: float = Query(None),
    until: float = Query(None),
    limit: int = 100
):
    """Get metric time series"""
    from observability.metrics import registry
    
    data = registry.get_all_series(metric_name)
    
    return {
        "metric_name": metric_name,
        "series": data,
        "since": since,
        "until": until,
        "limit": limit,
    }


@router.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Get metrics in Prometheus text format"""
    from observability.metrics import metrics
    
    return metrics.get_prometheus_format()


# ============= KPIs Routes =============

@router.get("/kpis")
async def get_kpis():
    """Get all KPI definitions and values"""
    from observability.kpi import kpi_tracker
    
    kpis = kpi_tracker.list_kpis()
    
    result = []
    for kpi in kpis:
        result.append({
            "name": kpi.name,
            "category": kpi.category,
            "description": kpi.description,
            "unit": kpi.unit,
            "value": kpi_tracker.get(kpi.name, since=time.time() - 3600),
            "status": kpi_tracker.get_status(kpi.name),
            "target": kpi.target,
        })
    
    return {"kpis": result}


@router.get("/kpis/{category}")
async def get_kpis_by_category(category: str):
    """Get KPIs by category"""
    from observability.kpi import kpi_tracker
    
    kpis = kpi_tracker.list_kpis(category=category)
    
    result = []
    for kpi in kpis:
        result.append({
            "name": kpi.name,
            "description": kpi.description,
            "unit": kpi.unit,
            "value": kpi_tracker.get(kpi.name, since=time.time() - 3600),
            "status": kpi_tracker.get_status(kpi.name),
        })
    
    return {"category": category, "kpis": result}


@router.get("/kpis/{kpi_name}/timeseries")
async def get_kpi_timeseries(
    kpi_name: str,
    since: Optional[float] = None,
    until: Optional[float] = None,
    limit: int = 100
):
    """Get KPI time series"""
    from observability.kpi import kpi_tracker
    
    data = kpi_tracker.get_timeseries(
        kpi_name,
        since=since,
        until=until,
        limit=limit
    )
    
    return {
        "kpi_name": kpi_name,
        "timeseries": data,
    }


@router.get("/kpis/summary")
async def get_kpi_summary():
    """Get KPI summary"""
    from observability.kpi import kpi_tracker
    
    return kpi_tracker.get_summary()


# ============= Events Routes =============

@router.get("/events")
async def get_events(
    event_type: Optional[str] = None,
    since: Optional[float] = None,
    until: Optional[float] = None,
    limit: int = 100
):
    """Get events from event bus"""
    from observability.events import event_bus, EventType
    
    et = None
    if event_type:
        try:
            et = EventType(event_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event type")
    
    events = event_bus.get_events(
        event_type=et,
        since=since,
        until=until,
        limit=limit
    )
    
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events),
    }


@router.get("/events/counts")
async def get_event_counts(since: Optional[float] = None):
    """Get event counts by type"""
    from observability.events import event_bus
    
    counts = event_bus.get_event_counts(since=since)
    
    return {"counts": counts}


# ============= Alerts Routes =============

@router.get("/alerts")
async def get_active_alerts(
    severity: Optional[str] = None
):
    """Get active alerts"""
    from observability.alerts import alert_manager, AlertSeverity
    
    sev = None
    if severity:
        try:
            sev = AlertSeverity(severity)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid severity")
    
    alerts = alert_manager.get_active_alerts(severity=sev)
    
    return {
        "alerts": [a.to_dict() for a in alerts],
        "count": len(alerts),
    }


@router.get("/alerts/history")
async def get_alert_history(
    since: Optional[float] = None,
    until: Optional[float] = None,
    limit: int = 100
):
    """Get alert history"""
    from observability.alerts import alert_manager
    
    alerts = alert_manager.get_alert_history(
        since=since,
        until=until,
        limit=limit
    )
    
    return {
        "alerts": [a.to_dict() for a in alerts],
        "count": len(alerts),
    }


@router.get("/alerts/statistics")
async def get_alert_statistics():
    """Get alert statistics"""
    from observability.alerts import alert_manager
    
    return alert_manager.get_statistics()


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, acknowledged_by: str = "api"):
    """Acknowledge an alert"""
    from observability.alerts import alert_manager
    
    success = alert_manager.acknowledge(alert_id, acknowledged_by)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"success": True, "alert_id": alert_id}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve an alert"""
    from observability.alerts import alert_manager
    
    success = alert_manager.resolve(alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"success": True, "alert_id": alert_id}


# ============= Dashboard Routes =============

@router.get("/dashboard")
async def get_dashboard():
    """Get comprehensive dashboard data"""
    from observability.dashboards import dashboard_data
    
    return dashboard_data.get_comprehensive_dashboard()


@router.get("/dashboard/resources")
async def get_resource_usage():
    """Get resource usage metrics"""
    from observability.dashboards import dashboard_data
    
    return dashboard_data.get_resource_usage()


@router.get("/dashboard/latency")
async def get_latency_data(
    metric_name: str = "api_request_duration",
    since: Optional[float] = None,
    until: Optional[float] = None
):
    """Get latency metrics"""
    from observability.dashboards import dashboard_data
    
    return dashboard_data.get_latency_data(
        metric_name,
        since=since or (time.time() - 3600),
        until=until or time.time()
    )


@router.get("/dashboard/health")
async def get_health_metrics():
    """Get health metrics for all subsystems"""
    from observability.dashboards import dashboard_data
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "websocket": dashboard_data.get_websocket_health(),
        "api": dashboard_data.get_api_health(),
        "strategy": dashboard_data.get_strategy_health(),
        "model": dashboard_data.get_model_health(),
        "execution": dashboard_data.get_execution_health(),
    }


@router.get("/dashboard/opportunities")
async def get_opportunity_metrics():
    """Get opportunity metrics"""
    from observability.dashboards import dashboard_data
    
    return dashboard_data.get_opportunity_metrics()


@router.get("/dashboard/risk")
async def get_risk_metrics():
    """Get risk metrics"""
    from observability.dashboards import dashboard_data
    
    return dashboard_data.get_risk_metrics()


@router.get("/dashboard/historical/{metric_name}")
async def get_historical_data(
    metric_name: str,
    hours: int = 24,
    bucket_minutes: int = 5
):
    """Get historical data for a metric"""
    from observability.dashboards import dashboard_data
    
    since = time.time() - (hours * 3600)
    until = time.time()
    
    data = dashboard_data.get_historical_data(
        metric_name,
        since=since,
        until=until,
        bucket_minutes=bucket_minutes
    )
    
    return {
        "metric_name": metric_name,
        "hours": hours,
        "bucket_minutes": bucket_minutes,
        "data": data,
    }


# ============= Traces Routes =============

@router.get("/traces/stats")
async def get_trace_stats():
    """Get trace statistics"""
    from observability.traces import tracer
    
    return tracer.get_stats()


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get all spans for a trace"""
    from observability.traces import tracer
    
    spans = tracer.get_trace(trace_id)
    
    return {
        "trace_id": trace_id,
        "spans": [s.to_dict() for s in spans],
        "count": len(spans),
    }


@router.get("/traces/{trace_id}/{span_id}")
async def get_span(trace_id: str, span_id: str):
    """Get a specific span"""
    from observability.traces import tracer
    
    span = tracer.get_span(span_id)
    
    if not span or span.trace_id != trace_id:
        raise HTTPException(status_code=404, detail="Span not found")
    
    return span.to_dict()


# ============= Health Routes =============

@router.get("/health")
async def get_overall_health():
    """Get overall platform health"""
    from observability.dashboards import dashboard_data
    from observability.kpi import kpi_tracker
    from observability.alerts import alert_manager
    
    # Get alert count
    active_alerts = alert_manager.get_active_alerts()
    
    # Check critical alerts
    has_critical = any(
        a.severity.value == "critical" for a in active_alerts
    )
    
    # Get resource usage
    resources = dashboard_data.get_resource_usage()
    
    # Determine health status
    status = "healthy"
    if has_critical:
        status = "critical"
    elif resources["cpu"]["percent"] > 90 or resources["memory"]["percent"] > 90:
        status = "degraded"
    elif active_alerts:
        status = "warning"
    
    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_alerts": len(active_alerts),
        "resources": resources,
    }
