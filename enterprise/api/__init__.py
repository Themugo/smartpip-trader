"""
Enterprise API Platform

Comprehensive REST API for:
- Account management
- Strategy management
- Backtesting
- Reporting
- Experiment tracking
- Notifications
- Plugin lifecycle
- System monitoring
"""

from enterprise.api.routes import setup_enterprise_routes
from enterprise.api.documentation import APIDocumentation
from enterprise.api.middleware import (
    AuthMiddleware,
    RateLimitMiddleware,
    TenantMiddleware,
)

# Import FastAPI
try:
    from fastapi import FastAPI
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


class APIServer:
    """Enterprise API Server wrapper"""
    
    def __init__(self, title: str = "SmartPip Enterprise API"):
        if not HAS_FASTAPI:
            raise ImportError("FastAPI is required for APIServer")
        
        self.app = FastAPI(
            title=title,
            description="Enterprise trading platform API",
            version="1.0.0",
        )
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes"""
        setup_enterprise_routes(self.app)
    
    def mount(self, path: str, app) -> None:
        """Mount another FastAPI app"""
        self.app.mount(path, app)


__all__ = [
    "setup_enterprise_routes",
    "APIDocumentation",
    "AuthMiddleware",
    "RateLimitMiddleware",
    "TenantMiddleware",
    "APIServer",
]
