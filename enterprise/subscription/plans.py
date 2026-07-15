"""
Subscription Plans

Defines all subscription tiers with:
- Feature flags
- Resource limits
- Pricing
- Trial periods
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from enterprise.models.tenant import SubscriptionTier


class BillingInterval(Enum):
    """Billing intervals"""
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class PlanFeature:
    """Individual feature within a plan"""
    code: str
    name: str
    description: str
    enabled: bool = True
    limit: Optional[int] = None
    unit: Optional[str] = None  # e.g., "strategies", "users", "GB"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "limit": self.limit,
            "unit": self.unit,
        }


@dataclass
class PlanLimits:
    """Resource limits for a plan"""
    max_users: int
    max_teams: int
    max_workspaces: int
    max_strategies: int
    max_backtests_per_day: int
    max_api_calls_per_day: int
    max_storage_gb: int
    max_export_rows: int
    max_concurrent_trades: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_users": self.max_users,
            "max_teams": self.max_teams,
            "max_workspaces": self.max_workspaces,
            "max_strategies": self.max_strategies,
            "max_backtests_per_day": self.max_backtests_per_day,
            "max_api_calls_per_day": self.max_api_calls_per_day,
            "max_storage_gb": self.max_storage_gb,
            "max_export_rows": self.max_export_rows,
            "max_concurrent_trades": self.max_concurrent_trades,
        }


@dataclass
class PlanPricing:
    """Pricing information for a plan"""
    monthly_price: float
    yearly_price: float
    currency: str = "USD"
    
    @property
    def monthly_price_formatted(self) -> str:
        return f"${self.monthly_price:.2f}/month"
    
    @property
    def yearly_price_formatted(self) -> str:
        return f"${self.yearly_price:.2f}/year"
    
    @property
    def yearly_savings(self) -> float:
        return (self.monthly_price * 12) - self.yearly_price
    
    @property
    def yearly_savings_percent(self) -> float:
        return ((self.monthly_price * 12) - self.yearly_price) / (self.monthly_price * 12) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "monthly_price": self.monthly_price,
            "yearly_price": self.yearly_price,
            "currency": self.currency,
            "monthly_formatted": self.monthly_price_formatted,
            "yearly_formatted": self.yearly_price_formatted,
            "yearly_savings": self.yearly_savings,
            "yearly_savings_percent": self.yearly_savings_percent,
        }


@dataclass
class PlanFeatures:
    """All features for a plan"""
    # Core features
    basic_strategies: bool = False
    advanced_strategies: bool = False
    custom_strategies: bool = False
    
    # Backtesting
    basic_backtesting: bool = False
    advanced_backtesting: bool = False
    walk_forward_analysis: bool = False
    monte_carlo: bool = False
    
    # Collaboration
    team_collaboration: bool = False
    shared_workspaces: bool = False
    shared_strategies: bool = False
    approval_workflows: bool = False
    
    # Analytics
    basic_analytics: bool = False
    advanced_analytics: bool = False
    custom_analytics: bool = False
    
    # Support
    community_support: bool = False
    email_support: bool = False
    priority_support: bool = False
    dedicated_support: bool = False
    sla_guarantee: bool = False
    
    # Export & Integrations
    export_csv: bool = False
    export_excel: bool = False
    export_pdf: bool = False
    api_access: bool = False
    webhooks: bool = False
    custom_integrations: bool = False
    
    # Security
    basic_security: bool = False
    advanced_security: bool = False
    sso: bool = False
    audit_logs: bool = False
    ip_whitelist: bool = False
    
    # Advanced
    hft_mode: bool = False
    custom_indicators: bool = False
    plugin_marketplace: bool = False
    strategy_marketplace: bool = False
    
    def to_dict(self) -> Dict[str, bool]:
        return {
            "basic_strategies": self.basic_strategies,
            "advanced_strategies": self.advanced_strategies,
            "custom_strategies": self.custom_strategies,
            "basic_backtesting": self.basic_backtesting,
            "advanced_backtesting": self.advanced_backtesting,
            "walk_forward_analysis": self.walk_forward_analysis,
            "monte_carlo": self.monte_carlo,
            "team_collaboration": self.team_collaboration,
            "shared_workspaces": self.shared_workspaces,
            "shared_strategies": self.shared_strategies,
            "approval_workflows": self.approval_workflows,
            "basic_analytics": self.basic_analytics,
            "advanced_analytics": self.advanced_analytics,
            "custom_analytics": self.custom_analytics,
            "community_support": self.community_support,
            "email_support": self.email_support,
            "priority_support": self.priority_support,
            "dedicated_support": self.dedicated_support,
            "sla_guarantee": self.sla_guarantee,
            "export_csv": self.export_csv,
            "export_excel": self.export_excel,
            "export_pdf": self.export_pdf,
            "api_access": self.api_access,
            "webhooks": self.webhooks,
            "custom_integrations": self.custom_integrations,
            "basic_security": self.basic_security,
            "advanced_security": self.advanced_security,
            "sso": self.sso,
            "audit_logs": self.audit_logs,
            "ip_whitelist": self.ip_whitelist,
            "hft_mode": self.hft_mode,
            "custom_indicators": self.custom_indicators,
            "plugin_marketplace": self.plugin_marketplace,
            "strategy_marketplace": self.strategy_marketplace,
        }


@dataclass
class SubscriptionPlan:
    """Complete subscription plan definition"""
    tier: SubscriptionTier
    name: str
    description: str
    
    # Pricing
    pricing: PlanPricing
    
    # Features
    features: PlanFeatures
    
    # Limits
    limits: PlanLimits
    
    # Trial
    trial_days: int = 0
    
    # Display
    highlight: bool = False
    badge: Optional[str] = None  # e.g., "POPULAR", "BEST VALUE"
    
    def has_feature(self, feature_code: str) -> bool:
        """Check if plan has a feature enabled"""
        return getattr(self.features, feature_code, False)
    
    def get_limit(self, limit_code: str) -> int:
        """Get a specific limit value"""
        return getattr(self.limits, limit_code, 0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value,
            "name": self.name,
            "description": self.description,
            "pricing": self.pricing.to_dict(),
            "features": self.features.to_dict(),
            "limits": self.limits.to_dict(),
            "trial_days": self.trial_days,
            "highlight": self.highlight,
            "badge": self.badge,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Plan Definitions
# ─────────────────────────────────────────────────────────────────────────────

FREE_PLAN = SubscriptionPlan(
    tier=SubscriptionTier.FREE,
    name="Free",
    description="Get started with basic trading strategies",
    pricing=PlanPricing(monthly_price=0, yearly_price=0),
    features=PlanFeatures(
        basic_strategies=True,
        basic_backtesting=True,
        community_support=True,
        basic_analytics=True,
        export_csv=True,
        basic_security=True,
    ),
    limits=PlanLimits(
        max_users=1,
        max_teams=0,
        max_workspaces=1,
        max_strategies=3,
        max_backtests_per_day=10,
        max_api_calls_per_day=100,
        max_storage_gb=1,
        max_export_rows=1000,
        max_concurrent_trades=1,
    ),
)

PROFESSIONAL_PLAN = SubscriptionPlan(
    tier=SubscriptionTier.PROFESSIONAL,
    name="Professional",
    description="For serious traders who need more power",
    pricing=PlanPricing(monthly_price=29, yearly_price=290),
    features=PlanFeatures(
        basic_strategies=True,
        advanced_strategies=True,
        basic_backtesting=True,
        advanced_backtesting=True,
        shared_workspaces=True,
        basic_analytics=True,
        advanced_analytics=True,
        email_support=True,
        export_csv=True,
        export_excel=True,
        api_access=True,
        basic_security=True,
        audit_logs=True,
    ),
    limits=PlanLimits(
        max_users=3,
        max_teams=2,
        max_workspaces=5,
        max_strategies=20,
        max_backtests_per_day=100,
        max_api_calls_per_day=5000,
        max_storage_gb=20,
        max_export_rows=50000,
        max_concurrent_trades=3,
    ),
    highlight=True,
    badge="POPULAR",
)

BUSINESS_PLAN = SubscriptionPlan(
    tier=SubscriptionTier.BUSINESS,
    name="Business",
    description="For teams and businesses with advanced needs",
    pricing=PlanPricing(monthly_price=99, yearly_price=990),
    features=PlanFeatures(
        basic_strategies=True,
        advanced_strategies=True,
        custom_strategies=True,
        basic_backtesting=True,
        advanced_backtesting=True,
        walk_forward_analysis=True,
        monte_carlo=True,
        team_collaboration=True,
        shared_workspaces=True,
        shared_strategies=True,
        approval_workflows=True,
        basic_analytics=True,
        advanced_analytics=True,
        priority_support=True,
        export_csv=True,
        export_excel=True,
        export_pdf=True,
        api_access=True,
        webhooks=True,
        advanced_security=True,
        audit_logs=True,
        ip_whitelist=True,
        custom_indicators=True,
    ),
    limits=PlanLimits(
        max_users=15,
        max_teams=10,
        max_workspaces=25,
        max_strategies=100,
        max_backtests_per_day=500,
        max_api_calls_per_day=50000,
        max_storage_gb=100,
        max_export_rows=500000,
        max_concurrent_trades=10,
    ),
)

ENTERPRISE_PLAN = SubscriptionPlan(
    tier=SubscriptionTier.ENTERPRISE,
    name="Enterprise",
    description="Maximum power with dedicated support and custom solutions",
    pricing=PlanPricing(monthly_price=499, yearly_price=4990),
    features=PlanFeatures(
        basic_strategies=True,
        advanced_strategies=True,
        custom_strategies=True,
        basic_backtesting=True,
        advanced_backtesting=True,
        walk_forward_analysis=True,
        monte_carlo=True,
        team_collaboration=True,
        shared_workspaces=True,
        shared_strategies=True,
        approval_workflows=True,
        basic_analytics=True,
        advanced_analytics=True,
        custom_analytics=True,
        dedicated_support=True,
        sla_guarantee=True,
        export_csv=True,
        export_excel=True,
        export_pdf=True,
        api_access=True,
        webhooks=True,
        custom_integrations=True,
        advanced_security=True,
        sso=True,
        audit_logs=True,
        ip_whitelist=True,
        hft_mode=True,
        custom_indicators=True,
        plugin_marketplace=True,
        strategy_marketplace=True,
    ),
    limits=PlanLimits(
        max_users=999999,
        max_teams=999999,
        max_workspaces=999999,
        max_strategies=999999,
        max_backtests_per_day=999999,
        max_api_calls_per_day=999999,
        max_storage_gb=999999,
        max_export_rows=999999,
        max_concurrent_trades=999999,
    ),
    badge="ENTERPRISE",
)

ALL_PLANS = {
    SubscriptionTier.FREE: FREE_PLAN,
    SubscriptionTier.PROFESSIONAL: PROFESSIONAL_PLAN,
    SubscriptionTier.BUSINESS: BUSINESS_PLAN,
    SubscriptionTier.ENTERPRISE: ENTERPRISE_PLAN,
}


def get_plan_by_tier(tier: SubscriptionTier) -> SubscriptionPlan:
    """Get plan definition by tier"""
    return ALL_PLANS.get(tier, FREE_PLAN)


def get_plan_comparison() -> Dict[str, Any]:
    """Get comparison of all plans"""
    return {
        "plans": [plan.to_dict() for plan in ALL_PLANS.values()],
        "features": {
            "core": [
                {"code": "basic_strategies", "name": "Basic Strategies"},
                {"code": "advanced_strategies", "name": "Advanced Strategies"},
                {"code": "custom_strategies", "name": "Custom Strategies"},
            ],
            "backtesting": [
                {"code": "basic_backtesting", "name": "Basic Backtesting"},
                {"code": "advanced_backtesting", "name": "Advanced Backtesting"},
                {"code": "walk_forward_analysis", "name": "Walk-Forward Analysis"},
                {"code": "monte_carlo", "name": "Monte Carlo Simulation"},
            ],
            "collaboration": [
                {"code": "team_collaboration", "name": "Team Collaboration"},
                {"code": "shared_workspaces", "name": "Shared Workspaces"},
                {"code": "shared_strategies", "name": "Shared Strategies"},
                {"code": "approval_workflows", "name": "Approval Workflows"},
            ],
            "analytics": [
                {"code": "basic_analytics", "name": "Basic Analytics"},
                {"code": "advanced_analytics", "name": "Advanced Analytics"},
                {"code": "custom_analytics", "name": "Custom Analytics"},
            ],
            "support": [
                {"code": "community_support", "name": "Community Support"},
                {"code": "email_support", "name": "Email Support"},
                {"code": "priority_support", "name": "Priority Support"},
                {"code": "dedicated_support", "name": "Dedicated Support"},
                {"code": "sla_guarantee", "name": "SLA Guarantee"},
            ],
            "export": [
                {"code": "export_csv", "name": "Export CSV"},
                {"code": "export_excel", "name": "Export Excel"},
                {"code": "export_pdf", "name": "Export PDF"},
            ],
            "api": [
                {"code": "api_access", "name": "API Access"},
                {"code": "webhooks", "name": "Webhooks"},
                {"code": "custom_integrations", "name": "Custom Integrations"},
            ],
            "security": [
                {"code": "basic_security", "name": "Basic Security"},
                {"code": "advanced_security", "name": "Advanced Security"},
                {"code": "sso", "name": "SSO"},
                {"code": "audit_logs", "name": "Audit Logs"},
                {"code": "ip_whitelist", "name": "IP Whitelist"},
            ],
            "advanced": [
                {"code": "hft_mode", "name": "HFT Mode"},
                {"code": "custom_indicators", "name": "Custom Indicators"},
                {"code": "plugin_marketplace", "name": "Plugin Marketplace"},
                {"code": "strategy_marketplace", "name": "Strategy Marketplace"},
            ],
        },
    }
