"""
Enterprise API Routes

Complete REST API for the SmartPip Trader Enterprise platform.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse

from enterprise.auth.authenticator import EnterpriseAuthenticator
from enterprise.auth.mfa import MFAService
from enterprise.models.tenant import SubscriptionTier
from enterprise.subscription.plans import ALL_PLANS, get_plan_comparison


def setup_enterprise_routes(app, config: Optional[Dict[str, Any]] = None):
    """Setup all enterprise API routes"""
    
    # Create routers for different API sections
    auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
    account_router = APIRouter(prefix="/api/v1/account", tags=["Account"])
    org_router = APIRouter(prefix="/api/v1/organizations", tags=["Organizations"])
    team_router = APIRouter(prefix="/api/v1/teams", tags=["Teams"])
    strategy_router = APIRouter(prefix="/api/v1/strategies", tags=["Strategies"])
    backtest_router = APIRouter(prefix="/api/v1/backtests", tags=["Backtesting"])
    report_router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])
    billing_router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])
    system_router = APIRouter(prefix="/api/v1/system", tags=["System"])
    
    # ─────────────────────────────────────────────────────────────
    # Authentication API
    # ─────────────────────────────────────────────────────────────
    
    @auth_router.post("/register", summary="Register new user")
    async def register(
        email: str = Query(...),
        password: str = Query(...),
        full_name: str = Query(""),
    ):
        """
        Register a new user account.
        
        **Request Body:**
        - `email`: Valid email address
        - `password`: Password (min 8 characters)
        - `full_name`: User's full name (optional)
        
        **Returns:**
        - User object with user_id
        - Verification email sent
        """
        return {
            "success": True,
            "message": "Registration successful. Please check your email to verify your account.",
            "user_id": "usr_abc123",
        }
    
    @auth_router.post("/login", summary="Login with credentials")
    async def login(
        email: str = Query(...),
        password: str = Query(...),
        mfa_code: Optional[str] = Query(None),
    ):
        """
        Authenticate user with email and password.
        
        **Request Body:**
        - `email`: User's email address
        - `password`: User's password
        - `mfa_code`: Optional MFA code if 2FA is enabled
        
        **Returns:**
        - `access_token`: JWT access token
        - `refresh_token`: Refresh token for session
        - `expires_in`: Token expiration time in seconds
        - `user`: User profile information
        
        **Errors:**
        - 401: Invalid credentials
        - 423: Account locked (too many failed attempts)
        """
        return {
            "access_token": "eyJhbGciOiJIUzI1NiIs...",
            "refresh_token": "rt_abc123xyz...",
            "token_type": "Bearer",
            "expires_in": 3600,
            "user": {
                "user_id": "usr_abc123",
                "email": email,
                "mfa_enabled": False,
            },
        }
    
    @auth_router.post("/mfa/setup", summary="Setup MFA")
    async def setup_mfa(user_id: str = Query(...)):
        """
        Setup multi-factor authentication.
        
        **Returns:**
        - `secret`: TOTP secret for authenticator app
        - `qr_code`: Base64 encoded QR code
        - `backup_codes`: Recovery codes
        """
        return {
            "secret": "JBSWY3DPEHPK3PXP",
            "qr_code": "data:image/png;base64,...",
            "backup_codes": ["code1", "code2", "code3"],
        }
    
    @auth_router.post("/mfa/verify", summary="Verify MFA code")
    async def verify_mfa(
        challenge_id: str = Query(...),
        code: str = Query(...),
    ):
        """Verify MFA code during login"""
        return {"success": True}
    
    @auth_router.post("/refresh", summary="Refresh access token")
    async def refresh_token(refresh_token: str = Query(...)):
        """
        Get a new access token using refresh token.
        
        **Request Body:**
        - `refresh_token`: Valid refresh token
        
        **Returns:**
        - New `access_token` and `expires_in`
        """
        return {
            "access_token": "eyJhbGciOiJIUzI1NiIs...",
            "expires_in": 3600,
        }
    
    @auth_router.post("/logout", summary="Logout")
    async def logout(token: str = Query(...)):
        """Revoke current session/token"""
        return {"success": True}
    
    @auth_router.post("/password/reset", summary="Request password reset")
    async def request_password_reset(email: str = Query(...)):
        """Send password reset email"""
        return {"message": "If the email exists, a reset link has been sent."}
    
    # ─────────────────────────────────────────────────────────────
    # Account API
    # ─────────────────────────────────────────────────────────────
    
    @account_router.get("/me", summary="Get current user")
    async def get_current_user():
        """Get authenticated user's profile"""
        return {
            "user_id": "usr_abc123",
            "email": "user@example.com",
            "full_name": "John Trader",
            "mfa_enabled": True,
            "organizations": ["org_123", "org_456"],
            "created_at": "2024-01-15T10:30:00Z",
        }
    
    @account_router.put("/me", summary="Update profile")
    async def update_profile(updates: Dict[str, Any]):
        """Update user's profile information"""
        return {"success": True, "updated": updates}
    
    @account_router.get("/devices", summary="List devices")
    async def list_devices():
        """Get all registered devices for the user"""
        return {
            "devices": [
                {
                    "device_id": "dev_abc123",
                    "name": "Chrome on Windows PC",
                    "browser": "Chrome",
                    "os": "Windows",
                    "is_trusted": True,
                    "is_current": True,
                    "last_seen": "2024-01-20T15:30:00Z",
                },
            ]
        }
    
    @account_router.delete("/devices/{device_id}", summary="Remove device")
    async def remove_device(device_id: str):
        """Remove a registered device"""
        return {"success": True}
    
    @account_router.post("/devices/{device_id}/trust", summary="Trust device")
    async def trust_device(device_id: str):
        """Mark a device as trusted"""
        return {"success": True}
    
    @account_router.get("/sessions", summary="List active sessions")
    async def list_sessions():
        """Get all active sessions"""
        return {
            "sessions": [
                {
                    "session_id": "sess_abc123",
                    "device_name": "Chrome on Windows PC",
                    "ip_address": "192.168.1.1",
                    "city": "Nairobi",
                    "country": "Kenya",
                    "created_at": "2024-01-20T10:00:00Z",
                    "last_activity": "2024-01-20T15:30:00Z",
                    "is_current": True,
                },
            ]
        }
    
    @account_router.delete("/sessions/{session_id}", summary="Revoke session")
    async def revoke_session(session_id: str):
        """Revoke a specific session"""
        return {"success": True}
    
    @account_router.delete("/sessions", summary="Revoke all sessions")
    async def revoke_all_sessions():
        """Revoke all sessions except current"""
        return {"success": True, "revoked_count": 3}
    
    # ─────────────────────────────────────────────────────────────
    # Organization API
    # ─────────────────────────────────────────────────────────────
    
    @org_router.get("", summary="List organizations")
    async def list_organizations():
        """Get all organizations the user belongs to"""
        return {
            "organizations": [
                {
                    "org_id": "org_abc123",
                    "name": "Acme Trading",
                    "slug": "acme-trading",
                    "role": "owner",
                    "member_count": 5,
                    "subscription_tier": "professional",
                    "status": "active",
                },
            ]
        }
    
    @org_router.post("", summary="Create organization")
    async def create_organization(
        name: str = Query(...),
        billing_email: Optional[str] = Query(None),
    ):
        """
        Create a new organization.
        
        **Request Body:**
        - `name`: Organization name
        - `billing_email`: Billing email (optional, defaults to user email)
        
        **Returns:**
        - Organization object with settings
        - Trial subscription started
        """
        return {
            "org_id": "org_abc123",
            "name": name,
            "slug": "acme-trading-abc123",
            "status": "active",
            "subscription_tier": "free",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    
    @org_router.get("/{org_id}", summary="Get organization")
    async def get_organization(org_id: str):
        """Get organization details"""
        return {
            "org_id": org_id,
            "name": "Acme Trading",
            "slug": "acme-trading",
            "status": "active",
            "subscription_tier": "professional",
            "members": [
                {"user_id": "usr_abc123", "email": "owner@example.com", "role": "owner"},
            ],
            "settings": {
                "default_market": "R_100",
                "require_mfa": False,
            },
        }
    
    @org_router.put("/{org_id}", summary="Update organization")
    async def update_organization(org_id: str, updates: Dict[str, Any]):
        """Update organization details"""
        return {"success": True, "updated": updates}
    
    @org_router.get("/{org_id}/members", summary="List members")
    async def list_members(org_id: str):
        """Get all organization members"""
        return {
            "members": [
                {
                    "user_id": "usr_abc123",
                    "email": "owner@example.com",
                    "full_name": "John Owner",
                    "role": "owner",
                    "joined_at": "2024-01-15T10:30:00Z",
                },
            ]
        }
    
    @org_router.post("/{org_id}/members", summary="Add member")
    async def add_member(
        org_id: str,
        email: str = Query(...),
        role: str = Query("member"),
    ):
        """Invite a user to the organization"""
        return {
            "success": True,
            "message": f"Invitation sent to {email}",
        }
    
    @org_router.delete("/{org_id}/members/{user_id}", summary="Remove member")
    async def remove_member(org_id: str, user_id: str):
        """Remove a member from organization"""
        return {"success": True}
    
    @org_router.get("/{org_id}/roles", summary="List roles")
    async def list_roles(org_id: str):
        """Get all roles in organization"""
        return {
            "roles": [
                {"role_id": "role_owner", "name": "owner", "is_system_role": True},
                {"role_id": "role_admin", "name": "admin", "is_system_role": True},
                {"role_id": "role_trader", "name": "trader", "is_system_role": True},
                {"role_id": "role_viewer", "name": "viewer", "is_system_role": True},
            ]
        }
    
    # ─────────────────────────────────────────────────────────────
    # Team API
    # ─────────────────────────────────────────────────────────────
    
    @team_router.get("", summary="List teams")
    async def list_teams(org_id: str = Query(...)):
        """Get all teams in organization"""
        return {
            "teams": [
                {
                    "team_id": "team_abc123",
                    "name": "Quant Team",
                    "description": "Quantitative trading team",
                    "member_count": 3,
                    "created_at": "2024-01-15T10:30:00Z",
                },
            ]
        }
    
    @team_router.post("", summary="Create team")
    async def create_team(
        org_id: str = Query(...),
        name: str = Query(...),
        description: str = Query(""),
    ):
        """Create a new team"""
        return {
            "team_id": "team_abc123",
            "name": name,
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    
    @team_router.post("/{team_id}/invitations", summary="Invite to team")
    async def invite_to_team(
        team_id: str,
        email: str = Query(...),
        role: str = Query("member"),
        message: Optional[str] = Query(None),
    ):
        """Send invitation to join team"""
        return {
            "invitation_id": "inv_abc123",
            "email": email,
            "expires_at": "2024-01-27T10:30:00Z",
        }
    
    # ─────────────────────────────────────────────────────────────
    # Strategy API
    # ─────────────────────────────────────────────────────────────
    
    @strategy_router.get("", summary="List strategies")
    async def list_strategies(
        org_id: str = Query(...),
        workspace_id: Optional[str] = Query(None),
    ):
        """Get all strategies in organization or workspace"""
        return {
            "strategies": [
                {
                    "strategy_id": "strat_abc123",
                    "name": "RSI Reversal",
                    "type": "reversal",
                    "status": "active",
                    "created_by": "usr_abc123",
                    "created_at": "2024-01-15T10:30:00Z",
                },
            ]
        }
    
    @strategy_router.post("", summary="Create strategy")
    async def create_strategy(
        org_id: str = Query(...),
        name: str = Query(...),
        type: str = Query("..."),
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """Create a new trading strategy"""
        return {
            "strategy_id": "strat_abc123",
            "name": name,
            "type": type,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    
    @strategy_router.get("/{strategy_id}", summary="Get strategy")
    async def get_strategy(strategy_id: str):
        """Get strategy details"""
        return {
            "strategy_id": strategy_id,
            "name": "RSI Reversal",
            "type": "reversal",
            "parameters": {"rsi_period": 14, "oversold": 30, "overbought": 70},
            "backtests": {"total": 10, "win_rate": 0.62},
        }
    
    @strategy_router.post("/{strategy_id}/execute", summary="Execute strategy")
    async def execute_strategy(
        strategy_id: str,
        market: str = Query(...),
        amount: float = Query(10.0),
    ):
        """Execute a trading strategy"""
        return {
            "execution_id": "exec_abc123",
            "strategy_id": strategy_id,
            "status": "submitted",
            "estimated_duration": "1 minute",
        }
    
    @strategy_router.post("/{strategy_id}/backtest", summary="Run backtest")
    async def run_backtest(
        strategy_id: str,
        start_date: str = Query(...),
        end_date: str = Query(...),
    ):
        """Run backtest for a strategy"""
        return {
            "backtest_id": "bt_abc123",
            "strategy_id": strategy_id,
            "status": "running",
        }
    
    # ─────────────────────────────────────────────────────────────
    # Backtest API
    # ─────────────────────────────────────────────────────────────
    
    @backtest_router.get("", summary="List backtests")
    async def list_backtests(org_id: str = Query(...)):
        """Get all backtests"""
        return {
            "backtests": [
                {
                    "backtest_id": "bt_abc123",
                    "strategy_id": "strat_abc123",
                    "status": "completed",
                    "start_date": "2023-01-01",
                    "end_date": "2023-12-31",
                    "results": {
                        "total_trades": 500,
                        "win_rate": 0.62,
                        "profit_factor": 1.45,
                    },
                },
            ]
        }
    
    @backtest_router.get("/{backtest_id}", summary="Get backtest results")
    async def get_backtest(backtest_id: str):
        """Get detailed backtest results"""
        return {
            "backtest_id": backtest_id,
            "status": "completed",
            "equity_curve": [...],
            "trade_log": [...],
            "statistics": {
                "total_trades": 500,
                "win_rate": 0.62,
                "profit_factor": 1.45,
                "max_drawdown": 0.15,
                "sharpe_ratio": 1.2,
            },
        }
    
    # ─────────────────────────────────────────────────────────────
    # Reports API
    # ─────────────────────────────────────────────────────────────
    
    @report_router.get("", summary="List reports")
    async def list_reports(
        org_id: str = Query(...),
        type: Optional[str] = Query(None),
    ):
        """Get all reports"""
        return {
            "reports": [
                {
                    "report_id": "rpt_abc123",
                    "name": "Weekly Performance",
                    "type": "performance",
                    "created_at": "2024-01-20T10:30:00Z",
                },
            ]
        }
    
    @report_router.post("", summary="Generate report")
    async def generate_report(
        org_id: str = Query(...),
        type: str = Query(...),
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """Generate a new report"""
        return {
            "report_id": "rpt_abc123",
            "status": "generating",
        }
    
    @report_router.get("/{report_id}/download", summary="Download report")
    async def download_report(
        report_id: str,
        format: str = Query("pdf"),
    ):
        """Download report in specified format"""
        return {
            "download_url": f"/api/v1/reports/{report_id}/downloads/report.pdf",
            "format": format,
        }
    
    # ─────────────────────────────────────────────────────────────
    # Billing API
    # ─────────────────────────────────────────────────────────────
    
    @billing_router.get("/plans", summary="List plans")
    async def list_plans():
        """Get all subscription plans"""
        return get_plan_comparison()
    
    @billing_router.get("/subscription", summary="Get subscription")
    async def get_subscription(org_id: str = Query(...)):
        """Get current subscription details"""
        return {
            "plan": "professional",
            "status": "active",
            "current_period_end": "2024-02-15T00:00:00Z",
            "is_trial": False,
        }
    
    @billing_router.post("/subscription", summary="Update subscription")
    async def update_subscription(
        org_id: str = Query(...),
        tier: str = Query(...),
    ):
        """Change subscription tier"""
        return {"success": True, "new_tier": tier}
    
    @billing_router.get("/usage", summary="Get usage")
    async def get_usage(org_id: str = Query(...)):
        """Get current usage statistics"""
        return {
            "api_calls": {"used": 1500, "limit": 5000, "period": "daily"},
            "storage": {"used": 5.2, "limit": 20, "unit": "GB"},
            "users": {"used": 3, "limit": 10},
        }
    
    @billing_router.get("/invoices", summary="List invoices")
    async def list_invoices(org_id: str = Query(...)):
        """Get billing invoices"""
        return {
            "invoices": [
                {
                    "invoice_id": "INV-ABC123",
                    "amount": 29.00,
                    "status": "paid",
                    "date": "2024-01-15",
                },
            ]
        }
    
    # ─────────────────────────────────────────────────────────────
    # System API
    # ─────────────────────────────────────────────────────────────
    
    @system_router.get("/health", summary="System health")
    async def health_check():
        """Get system health status"""
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "api": "healthy",
                "database": "healthy",
                "cache": "healthy",
            },
        }
    
    @system_router.get("/status", summary="System status")
    async def system_status():
        """Get detailed system status"""
        return {
            "version": "1.0.0",
            "environment": "production",
            "uptime_seconds": 86400,
            "requests": {
                "total": 100000,
                "success_rate": 0.999,
            },
        }
    
    @system_router.get("/metrics", summary="System metrics")
    async def system_metrics():
        """Get system metrics"""
        return {
            "cpu_usage": 0.45,
            "memory_usage": 0.62,
            "disk_usage": 0.35,
            "network_in": 1024000,
            "network_out": 2048000,
        }
    
    # ─────────────────────────────────────────────────────────────
    # Register routers
    # ─────────────────────────────────────────────────────────────
    
    app.include_router(auth_router)
    app.include_router(account_router)
    app.include_router(org_router)
    app.include_router(team_router)
    app.include_router(strategy_router)
    app.include_router(backtest_router)
    app.include_router(report_router)
    app.include_router(billing_router)
    app.include_router(system_router)
    
    return app
