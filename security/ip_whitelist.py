from typing import Set, Optional
import os
from fastapi import Request, HTTPException
from functools import wraps


class IPWhitelist:
    """IP whitelist management for system security"""
    
    def __init__(self):
        self.whitelisted_ips: Set[str] = set()
        self.blacklisted_ips: Set[str] = set()
        self.load_configuration()
    
    def load_configuration(self):
        """Load IP whitelist/blacklist from environment"""
        whitelist = os.getenv("WHITELISTED_IPS", "")
        if whitelist:
            self.whitelisted_ips = set(whitelist.split(","))
        
        blacklist = os.getenv("BLACKLISTED_IPS", "")
        if blacklist:
            self.blacklisted_ips = set(blacklist.split(","))
    
    def is_allowed(self, ip: str) -> bool:
        """Check if IP is allowed"""
        # Check blacklist first
        if ip in self.blacklisted_ips:
            return False
        
        # If whitelist is configured, check it
        if self.whitelisted_ips:
            return ip in self.whitelisted_ips
        
        # If no whitelist configured, allow all
        return True
    
    def add_to_whitelist(self, ip: str):
        """Add IP to whitelist"""
        self.whitelisted_ips.add(ip)
    
    def remove_from_whitelist(self, ip: str):
        """Remove IP from whitelist"""
        self.whitelisted_ips.discard(ip)
    
    def add_to_blacklist(self, ip: str):
        """Add IP to blacklist"""
        self.blacklisted_ips.add(ip)
    
    def remove_from_blacklist(self, ip: str):
        """Remove IP from blacklist"""
        self.blacklisted_ips.discard(ip)
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP from request"""
        # Check for forwarded IP (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Use direct IP
        return request.client.host if request.client else "unknown"
    
    def check_ip(self, request: Request) -> bool:
        """Check if request IP is allowed"""
        ip = self.get_client_ip(request)
        return self.is_allowed(ip)
    
    def require_whitelist(self):
        """Decorator to require IP whitelist check"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract request from kwargs
                request = kwargs.get('request')
                if not request:
                    raise HTTPException(status_code=500, detail="Request object not found")
                
                if not self.check_ip(request):
                    raise HTTPException(status_code=403, detail="IP not allowed")
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
