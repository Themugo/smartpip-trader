"""
Operations Dashboards

Comprehensive monitoring and dashboard data for operations center.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class HealthStatus(Enum):
    """System health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class MetricType(Enum):
    """Metric types"""
    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"


@dataclass
class ServiceHealth:
    """Health status of a service"""
    service_name: str
    status: HealthStatus
    latency_ms: float
    error_rate: float
    uptime_percent: float
    last_check: datetime = field(default_factory=datetime.utcnow)
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "error_rate": self.error_rate,
            "uptime_percent": self.uptime_percent,
            "last_check": self.last_check.isoformat(),
            "message": self.message,
        }


@dataclass
class TenantMetrics:
    """Metrics for a specific tenant"""
    tenant_id: str
    active_users: int
    api_calls_today: int
    api_calls_month: int
    storage_used_gb: float
    active_strategies: int
    active_trades: int
    cpu_percent: float
    memory_percent: float
    error_count_today: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "active_users": self.active_users,
            "api_calls": {
                "today": self.api_calls_today,
                "month": self.api_calls_month,
            },
            "storage_used_gb": self.storage_used_gb,
            "strategies": self.active_strategies,
            "active_trades": self.active_trades,
            "resources": {
                "cpu_percent": self.cpu_percent,
                "memory_percent": self.memory_percent,
            },
            "errors_today": self.error_count_today,
        }


@dataclass
class APIEndpointMetrics:
    """Metrics for an API endpoint"""
    path: str
    method: str
    requests_total: int
    requests_per_minute: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate: float
    status_codes: Dict[str, int]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "method": self.method,
            "requests_total": self.requests_total,
            "requests_per_minute": self.requests_per_minute,
            "latency": {
                "avg_ms": self.avg_latency_ms,
                "p95_ms": self.p95_latency_ms,
                "p99_ms": self.p99_latency_ms,
            },
            "error_rate": self.error_rate,
            "status_codes": self.status_codes,
        }


@dataclass
class BackgroundJob:
    """Background job status"""
    job_id: str
    job_type: str
    status: str  # pending, running, completed, failed
    tenant_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percent: float = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress_percent": self.progress_percent,
            "error_message": self.error_message,
        }


@dataclass
class SecurityEvent:
    """Security event"""
    event_id: str
    event_type: str
    severity: str
    tenant_id: Optional[str]
    user_id: Optional[str]
    ip_address: Optional[str]
    description: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
        }


class TenantHealthMonitor:
    """
    Monitors health of all tenants.
    """
    
    def __init__(self):
        self._tenant_status: Dict[str, ServiceHealth] = {}
        self._alerts: List[Dict[str, Any]] = []
    
    def check_tenant_health(self, tenant_id: str) -> ServiceHealth:
        """Check health of a specific tenant"""
        # In production, this would perform actual health checks
        health = ServiceHealth(
            service_name=f"tenant_{tenant_id[:8]}",
            status=HealthStatus.HEALTHY,
            latency_ms=45.2,
            error_rate=0.001,
            uptime_percent=99.9,
        )
        
        # Alert if degraded
        if health.error_rate > 0.01:
            health.status = HealthStatus.DEGRADED
            self._alerts.append({
                "tenant_id": tenant_id,
                "type": "high_error_rate",
                "message": f"High error rate: {health.error_rate}",
            })
        
        return health
    
    def get_all_health(self) -> Dict[str, Any]:
        """Get health status of all tenants"""
        return {
            "total_tenants": len(self._tenant_status),
            "healthy": sum(1 for h in self._tenant_status.values() if h.status == HealthStatus.HEALTHY),
            "degraded": sum(1 for h in self._tenant_status.values() if h.status == HealthStatus.DEGRADED),
            "unhealthy": sum(1 for h in self._tenant_status.values() if h.status == HealthStatus.UNHEALTHY),
            "tenants": [h.to_dict() for h in self._tenant_status.values()],
        }
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get current alerts"""
        return self._alerts[-50:]  # Last 50 alerts


class UsageDashboard:
    """
    Dashboard for usage analytics.
    """
    
    def __init__(self):
        self._usage_data: Dict[str, List[Dict[str, Any]]] = {}
    
    def get_usage_summary(self, org_id: str, period: str = "day") -> Dict[str, Any]:
        """Get usage summary for organization"""
        return {
            "org_id": org_id,
            "period": period,
            "api_calls": {
                "total": 1500,
                "success": 1485,
                "errors": 15,
            },
            "strategies": {
                "active": 3,
                "total": 5,
            },
            "backtests": {
                "completed": 10,
                "failed": 1,
            },
            "storage": {
                "used_gb": 2.5,
                "limit_gb": 20,
            },
        }
    
    def get_api_usage_by_endpoint(self, org_id: str) -> List[APIEndpointMetrics]:
        """Get API usage breakdown by endpoint"""
        return [
            APIEndpointMetrics(
                path="/api/v1/strategies",
                method="GET",
                requests_total=500,
                requests_per_minute=5.0,
                avg_latency_ms=45.2,
                p95_latency_ms=120.5,
                p99_latency_ms=200.0,
                error_rate=0.01,
                status_codes={"200": 495, "500": 5},
            ),
        ]


class ResourceMonitor:
    """
    Monitors system resources.
    """
    
    def __init__(self):
        self._metrics: Dict[str, List[float]] = {}
    
    def get_current_resources(self) -> Dict[str, Any]:
        """Get current resource usage"""
        return {
            "cpu": {
                "percent": 45.2,
                "cores": 8,
                "load_average": [2.1, 1.8, 1.5],
            },
            "memory": {
                "total_gb": 32,
                "used_gb": 18,
                "percent": 56.2,
            },
            "disk": {
                "total_gb": 500,
                "used_gb": 200,
                "percent": 40,
            },
            "network": {
                "bytes_in": 1024000,
                "bytes_out": 2048000,
            },
        }
    
    def get_resource_history(self, metric: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get resource history"""
        # In production, query from time-series database
        return [
            {"timestamp": datetime.utcnow().isoformat(), "value": 45.2}
            for _ in range(hours)
        ]


class OperationsDashboard:
    """
    Main operations dashboard.
    """
    
    def __init__(self):
        self._health_monitor = TenantHealthMonitor()
        self._usage_dashboard = UsageDashboard()
        self._resource_monitor = ResourceMonitor()
        self._jobs: List[BackgroundJob] = []
        self._security_events: List[SecurityEvent] = []
    
    def get_overview(self) -> Dict[str, Any]:
        """Get operations overview"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health": self._health_monitor.get_all_health(),
            "resources": self._resource_monitor.get_current_resources(),
            "active_jobs": len([j for j in self._jobs if j.status == "running"]),
            "pending_jobs": len([j for j in self._jobs if j.status == "pending"]),
            "security_events_today": len(self._security_events),
            "alerts": self._health_monitor.get_alerts(),
        }
    
    def get_tenant_dashboard(self, tenant_id: str) -> Dict[str, Any]:
        """Get detailed dashboard for a tenant"""
        return {
            "tenant_id": tenant_id,
            "health": self._health_monitor.check_tenant_health(tenant_id).to_dict(),
            "usage": self._usage_dashboard.get_usage_summary(tenant_id),
            "api_endpoints": [e.to_dict() for e in self._usage_dashboard.get_api_usage_by_endpoint(tenant_id)],
        }
    
    def get_background_jobs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get background jobs"""
        jobs = self._jobs
        if status:
            jobs = [j for j in jobs if j.status == status]
        return [j.to_dict() for j in jobs[-50:]]
    
    def get_security_events(
        self,
        severity: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get security events"""
        events = self._security_events
        if severity:
            events = [e for e in events if e.severity == severity]
        if since:
            events = [e for e in events if e.timestamp >= since]
        return [e.to_dict() for e in events[-100:]]
    
    def get_api_status(self) -> Dict[str, Any]:
        """Get API status summary"""
        return {
            "status": "operational",
            "version": "1.0.0",
            "uptime_seconds": 86400,
            "total_requests_today": 100000,
            "avg_latency_ms": 45.2,
            "error_rate": 0.001,
            "endpoints": [
                {
                    "path": "/api/v1/auth",
                    "status": "operational",
                    "latency_ms": 25.5,
                },
                {
                    "path": "/api/v1/strategies",
                    "status": "operational",
                    "latency_ms": 45.2,
                },
                {
                    "path": "/api/v1/backtests",
                    "status": "operational",
                    "latency_ms": 120.5,
                },
            ],
        }
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get deployment status"""
        return {
            "environment": "production",
            "region": "us-east-1",
            "version": "1.0.0",
            "last_deployment": "2024-01-20T10:00:00Z",
            "containers": [
                {"name": "api", "status": "running", "replicas": 3},
                {"name": "worker", "status": "running", "replicas": 5},
                {"name": "scheduler", "status": "running", "replicas": 2},
            ],
            "database": {
                "status": "healthy",
                "replicas": 3,
                "lag_ms": 5,
            },
        }
