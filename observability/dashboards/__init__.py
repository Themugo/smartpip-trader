"""
Dashboards Package
==================

Dashboard data API for observability.
"""

from .dashboard_data import (
    DashboardData,
    MetricSnapshot,
    dashboard_data,
)

__all__ = [
    "DashboardData",
    "MetricSnapshot",
    "dashboard_data",
]
