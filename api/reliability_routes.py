"""
Reliability Engineering API Routes
================================

Provides endpoints for monitoring and managing reliability infrastructure.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reliability", tags=["Reliability"])

# Global instances (would normally be managed by DI/injected)
_circuit_breakers = {}
_health_monitors = {}
_heartbeat_monitors = {}
_rate_limiters = {}


# ============= Health Monitor Routes =============

@router.get("/health")
async def get_overall_health():
    """Get overall system health"""
    all_health = {}
    
    for name, monitor in _health_monitors.items():
        try:
            all_health[name] = monitor.get_health_report()
        except Exception:
            pass
    
    statuses = []
    for report in all_health.values():
        if "service" in report:
            statuses.append(report["service"].get("status", "unknown"))
    
    overall = "healthy"
    if "unhealthy" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses:
        overall = "degraded"
    
    return {
        "overall_status": overall,
        "services": all_health,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health/{service_name}")
async def get_service_health(service_name: str):
    """Get health for a specific service"""
    if service_name not in _health_monitors:
        raise HTTPException(status_code=404, detail="Health monitor not found")
    
    return _health_monitors[service_name].get_health_report()


# ============= Circuit Breaker Routes =============

@router.get("/circuit-breakers")
async def list_circuit_breakers():
    """List all circuit breakers"""
    return {
        "circuit_breakers": {
            name: cb.get_health_report()
            for name, cb in _circuit_breakers.items()
        }
    }


@router.get("/circuit-breakers/{name}")
async def get_circuit_breaker(name: str):
    """Get circuit breaker details"""
    if name not in _circuit_breakers:
        raise HTTPException(status_code=404, detail="Circuit breaker not found")
    
    return _circuit_breakers[name].get_health_report()


# ============= Rate Limiter Routes =============

@router.get("/rate-limiters")
async def list_rate_limiters():
    """List all rate limiters"""
    return {
        "rate_limiters": {
            name: limiter.get_health_report()
            for name, limiter in _rate_limiters.items()
        }
    }


# ============= Heartbeat Routes =============

@router.get("/heartbeats")
async def list_heartbeats():
    """List all service heartbeats"""
    all_heartbeats = {}
    
    for name, monitor in _heartbeat_monitors.items():
        try:
            hb = monitor.get_heartbeat()
            all_heartbeats[name] = {
                "status": str(hb.status.value) if hasattr(hb.status, 'value') else str(hb.status),
                "last_heartbeat": hb.last_heartbeat,
                "total_heartbeats": hb.total_heartbeats,
                "uptime_seconds": hb.uptime_seconds
            }
        except Exception:
            pass
    
    return {"heartbeats": all_heartbeats}


# ============= System Dashboard =============

@router.get("/dashboard")
async def get_reliability_dashboard():
    """Get comprehensive reliability dashboard data"""
    dashboard = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "healthy",
        "circuit_breakers": {},
        "health_monitors": {},
        "heartbeats": {},
        "rate_limiters": {},
    }
    
    try:
        from reliability import CircuitState, HealthStatus
        
        for name, cb in _circuit_breakers.items():
            try:
                dashboard["circuit_breakers"][name] = cb.get_health_report()
            except Exception:
                pass
        
        for name, monitor in _health_monitors.items():
            try:
                dashboard["health_monitors"][name] = monitor.get_health_report()
            except Exception:
                pass
        
        for name, monitor in _heartbeat_monitors.items():
            try:
                dashboard["heartbeats"][name] = monitor.get_health_report()
            except Exception:
                pass
        
        for name, limiter in _rate_limiters.items():
            try:
                dashboard["rate_limiters"][name] = limiter.get_health_report()
            except Exception:
                pass
        
        # Calculate overall status
        statuses = []
        
        for cb in _circuit_breakers.values():
            try:
                if cb.state == CircuitState.OPEN:
                    statuses.append("degraded")
                elif cb.state == CircuitState.HALF_OPEN:
                    statuses.append("warning")
            except Exception:
                pass
        
        for monitor in _health_monitors.values():
            try:
                health = monitor.get_health()
                if health.status == HealthStatus.UNHEALTHY:
                    statuses.append("unhealthy")
                elif health.status == HealthStatus.DEGRADED:
                    statuses.append("degraded")
            except Exception:
                pass
        
        if "unhealthy" in statuses:
            dashboard["overall_status"] = "unhealthy"
        elif "degraded" in statuses:
            dashboard["overall_status"] = "degraded"
        elif "warning" in statuses:
            dashboard["overall_status"] = "warning"
    
    except ImportError:
        pass  # Reliability module not fully loaded
    
    return dashboard


def register_reliability_router(app):
    """Register the reliability router with the FastAPI app"""
    app.include_router(router)
