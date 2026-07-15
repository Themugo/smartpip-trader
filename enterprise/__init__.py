"""
SmartPip Trader Enterprise Platform

A comprehensive enterprise SaaS platform for algorithmic trading.

Features:
- Multi-tenant architecture with organizations, teams, workspaces
- Secure authentication with MFA, sessions, device management
- Subscription management with feature flags
- Role-based access control
- Cloud synchronization
- Plugin marketplace with sandbox execution
- Comprehensive API platform
- Operations center dashboards
- Reporting with PDF, Excel, CSV export
- Developer SDK
- Centralized monitoring and observability

Usage:

    from enterprise import SmartPipPlatform
    
    # Initialize platform
    platform = SmartPipPlatform(config)
    
    # Create organization
    org = platform.organizations.create("My Trading Firm")
    
    # Add team members
    platform.teams.invite(org.org_id, "trader@example.com", "trader")
    
    # Create and run strategy
    strategy = platform.strategies.create(name="RSI Reversal", ...)
    results = platform.backtests.run(strategy.id, ...)
    
    # Generate report
    report = platform.reports.generate("weekly_review", format="pdf")
"""

from enterprise.models import (
    Organization,
    Team,
    Workspace,
    UserRole,
    BillingAccount,
    EnterpriseUser,
    AuditEvent,
)
from enterprise.auth import (
    EnterpriseAuthenticator,
    SessionManager,
    DeviceManager,
    MFAService,
)
from enterprise.subscription import (
    SubscriptionManager,
    BillingService,
    SubscriptionPlan,
)
from enterprise.organization import (
    OrganizationManager,
    TeamManager,
    RBACService,
)
from enterprise.reporting import ReportGenerator
from enterprise.marketplace import MarketplaceCatalog, SandboxExecutor
from enterprise.sdk import SmartPipClient, SmartPipConfig
from enterprise.monitoring import ObservabilityManager, AlertManager
from enterprise.operations import OperationsDashboard


class SmartPipPlatform:
    """
    Main platform class for SmartPip Trader Enterprise.
    
    Provides unified access to all platform features.
    """
    
    def __init__(self, config: dict):
        self._config = config
        
        # Initialize components
        self._init_auth()
        self._init_organizations()
        self._init_subscriptions()
        self._init_reporting()
        self._init_marketplace()
        self._init_monitoring()
        self._init_operations()
    
    def _init_auth(self):
        """Initialize authentication components"""
        jwt_secret = self._config.get("jwt_secret", "change-me-in-production")
        
        self.authenticator = EnterpriseAuthenticator(
            jwt_secret=jwt_secret,
        )
        self.sessions = SessionManager()
        self.devices = DeviceManager()
        self.mfa = MFAService()
    
    def _init_organizations(self):
        """Initialize organization management"""
        self.org_manager = OrganizationManager()
        self.teams = TeamManager()
        self.rbac = RBACService()
    
    def _init_subscriptions(self):
        """Initialize subscription management"""
        self.subscriptions = SubscriptionManager()
        self.billing = BillingService()
    
    def _init_reporting(self):
        """Initialize reporting"""
        self.reports = ReportGenerator()
    
    def _init_marketplace(self):
        """Initialize marketplace"""
        self.marketplace = MarketplaceCatalog()
        self.sandbox = SandboxExecutor()
    
    def _init_monitoring(self):
        """Initialize monitoring"""
        self.observability = ObservabilityManager("smartpip-platform")
        self.alerts = AlertManager()
    
    def _init_operations(self):
        """Initialize operations center"""
        self.operations = OperationsDashboard()
    
    @property
    def organizations(self):
        """Organization management"""
        return self.org_manager
    
    @property
    def strategies(self):
        """Strategy management (placeholder)"""
        return StrategyManager(self)
    
    @property
    def backtests(self):
        """Backtest management (placeholder)"""
        return BacktestManager(self)


class StrategyManager:
    """Strategy management operations"""
    
    def __init__(self, platform: SmartPipPlatform):
        self._platform = platform


class BacktestManager:
    """Backtest management operations"""
    
    def __init__(self, platform: SmartPipPlatform):
        self._platform = platform


__all__ = [
    "SmartPipPlatform",
    "Organization",
    "Team",
    "Workspace",
    "UserRole",
    "BillingAccount",
    "EnterpriseUser",
    "AuditEvent",
    "EnterpriseAuthenticator",
    "SessionManager",
    "DeviceManager",
    "MFAService",
    "SubscriptionManager",
    "BillingService",
    "SubscriptionPlan",
    "OrganizationManager",
    "TeamManager",
    "RBACService",
    "ReportGenerator",
    "MarketplaceCatalog",
    "SandboxExecutor",
    "SmartPipClient",
    "SmartPipConfig",
    "ObservabilityManager",
    "AlertManager",
    "OperationsDashboard",
]
