"""
API Middleware

Middleware components for:
- Authentication
- Rate limiting
- Tenant isolation
- Request logging
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional
from collections import defaultdict
import threading


class RateLimitStore:
    """Thread-safe rate limit storage"""
    
    def __init__(self):
        self._store: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
    
    def add_request(self, key: str) -> None:
        with self._lock:
            self._store[key].append(time.time())
    
    def get_count(self, key: str, window_seconds: int) -> int:
        with self._lock:
            cutoff = time.time() - window_seconds
            self._store[key] = [t for t in self._store[key] if t > cutoff]
            return len(self._store[key])
    
    def clear_expired(self) -> None:
        with self._lock:
            for key in list(self._store.keys()):
                self._store[key] = [t for t in self._store[key] if t > time.time() - 3600]
                if not self._store[key]:
                    del self._store[key]


class AuthMiddleware:
    """
    Authentication middleware for FastAPI.
    
    Validates JWT tokens and extracts user information.
    """
    
    def __init__(self, jwt_secret: str, jwt_algorithm: str = "HS256"):
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = jwt_algorithm
    
    async def __call__(self, request, call_next):
        # Skip auth for public endpoints
        public_paths = ["/api/v1/auth/login", "/api/v1/auth/register", "/health"]
        if any(request.url.path.startswith(p) for p in public_paths):
            return await call_next(request)
        
        # Extract token from header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return {"error": "Missing or invalid authorization header"}
        
        token = auth_header[7:]
        
        # Validate token
        import jwt
        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=[self._jwt_algorithm])
            request.state.user_id = payload.get("sub")
            request.state.session_id = payload.get("session_id")
            request.state.org_id = payload.get("org_id")
        except jwt.PyJWTError:
            return {"error": "Invalid or expired token"}
        
        return await call_next(request)


class RateLimitMiddleware:
    """
    Rate limiting middleware.
    
    Implements sliding window rate limiting per user/IP.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_day: int = 10000,
        store: Optional[RateLimitStore] = None,
    ):
        self._rpm = requests_per_minute
        self._rpd = requests_per_day
        self._store = store or RateLimitStore()
    
    async def __call__(self, request, call_next):
        # Get identifier (user_id or IP)
        identifier = getattr(request.state, "user_id", None)
        if not identifier:
            identifier = request.client.host if request.client else "unknown"
        
        # Check rate limits
        minute_count = self._store.get_count(f"{identifier}:minute", 60)
        day_count = self._store.get_count(f"{identifier}:day", 86400)
        
        if minute_count >= self._rpm:
            return {
                "error": "Rate limit exceeded",
                "limit": self._rpm,
                "window": "minute",
                "retry_after": 60,
            }
        
        if day_count >= self._rpd:
            return {
                "error": "Daily rate limit exceeded",
                "limit": self._rpd,
                "window": "day",
                "retry_after": 86400 - (time.time() % 86400),
            }
        
        # Record request
        self._store.add_request(f"{identifier}:minute")
        self._store.add_request(f"{identifier}:day")
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self._rpm)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self._rpm - minute_count - 1))
        
        return response


class TenantMiddleware:
    """
    Multi-tenant isolation middleware.
    
    Extracts organization context and enforces data isolation.
    """
    
    def __init__(self):
        self._tenant_cache: Dict[str, Dict[str, Any]] = {}
    
    async def __call__(self, request, call_next):
        # Skip for non-tenant endpoints
        public_paths = ["/api/v1/auth", "/health"]
        if any(request.url.path.startswith(p) for p in public_paths):
            return await call_next(request)
        
        # Get organization from JWT or header
        org_id = getattr(request.state, "org_id", None)
        if not org_id:
            org_id = request.headers.get("X-Organization-ID")
        
        if not org_id:
            return {"error": "Organization context required"}
        
        # Validate organization access
        user_id = getattr(request.state, "user_id", None)
        if user_id and not self._validate_org_access(user_id, org_id):
            return {"error": "Access denied to organization"}
        
        # Set tenant context
        request.state.org_id = org_id
        request.state.tenant_id = self._get_tenant_id(org_id)
        
        response = await call_next(request)
        
        # Add tenant headers
        response.headers["X-Tenant-ID"] = request.state.tenant_id
        
        return response
    
    def _validate_org_access(self, user_id: str, org_id: str) -> bool:
        """Validate user has access to organization"""
        # In production, check against database
        return True
    
    def _get_tenant_id(self, org_id: str) -> str:
        """Get tenant ID from organization"""
        # Use first 8 chars of org_id as tenant namespace
        return f"tenant_{org_id[:8]}"


class RequestLoggingMiddleware:
    """
    Request logging middleware.
    
    Logs all requests with timing and correlation IDs.
    """
    
    def __init__(self, logger=None):
        self._logger = logger
    
    async def __call__(self, request, call_next):
        # Generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            self._log_error(request, request_id, e)
            raise
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log request
        self._log_request(request, response, request_id, duration_ms)
        
        # Add headers
        if hasattr(response, "headers"):
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        
        return response
    
    def _log_request(self, request, response, request_id: str, duration_ms: float):
        """Log request details"""
        if self._logger:
            self._logger.info(
                f"{request.method} {request.url.path} "
                f"→ {response.status_code if hasattr(response, 'status_code') else '?'} "
                f"[{duration_ms:.2f}ms] "
                f"(req_id={request_id})"
            )
    
    def _log_error(self, request, request_id: str, error: Exception):
        """Log request error"""
        if self._logger:
            self._logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"(req_id={request_id}): {str(error)}"
            )


class CORSMiddleware:
    """
    CORS middleware for API access.
    """
    
    def __init__(
        self,
        allowed_origins: list = None,
        allowed_methods: list = None,
        allowed_headers: list = None,
    ):
        self._origins = allowed_origins or ["*"]
        self._methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self._headers = allowed_headers or ["*"]
    
    async def __call__(self, request, call_next):
        origin = request.headers.get("Origin")
        
        response = await call_next(request)
        
        # Set CORS headers
        if "*" in self._origins or origin in self._origins:
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self._methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self._headers)
            response.headers["Access-Control-Max-Age"] = "3600"
        
        return response
