"""
Observability - System Monitoring

Comprehensive monitoring dashboards:
- CPU, Memory, GPU tracking
- Network latency monitoring
- API/WebSocket health
- Plugin health
- AI health
- Database health
"""

from observability.dashboard import ObservabilityDashboard, MetricSnapshot

__all__ = [
    "ObservabilityDashboard",
    "MetricSnapshot",
]
