"""
Billing and Subscription Management

Handles:
- Subscription lifecycle
- Usage tracking
- Quota management
- Billing operations
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from enterprise.models.tenant import (
    Organization,
    BillingAccount,
    SubscriptionTier,
)
from enterprise.subscription.plans import (
    SubscriptionPlan,
    get_plan_by_tier,
    BillingInterval,
)


class SubscriptionStatus(Enum):
    """Subscription status"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    SUSPENDED = "suspended"
    TRIALING = "trialing"


class UsageMetric(Enum):
    """Usage metric types"""
    API_CALLS = "api_calls"
    STORAGE_GB = "storage_gb"
    TRADES = "trades"
    BACKTESTS = "backtests"
    EXPORT_ROWS = "export_rows"
    USERS = "users"
    TEAMS = "teams"
    WORKSPACES = "workspaces"
    STRATEGIES = "strategies"


@dataclass
class UsageRecord:
    """Usage record for a metric"""
    metric: UsageMetric
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=1))


@dataclass
class QuotaStatus:
    """Quota status for a metric"""
    metric: UsageMetric
    used: float
    limit: float
    percentage: float
    remaining: float
    is_exceeded: bool
    reset_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric.value,
            "used": self.used,
            "limit": self.limit,
            "percentage": self.percentage,
            "remaining": self.remaining,
            "is_exceeded": self.is_exceeded,
            "reset_at": self.reset_at.isoformat() if self.reset_at else None,
        }


@dataclass
class SubscriptionInfo:
    """Complete subscription information"""
    organization_id: str
    plan: SubscriptionPlan
    status: SubscriptionStatus
    
    # Period
    current_period_start: datetime
    current_period_end: datetime
    
    # Trial
    is_trial: bool = False
    trial_ends_at: Optional[datetime] = None
    
    # Cancel
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    
    # Payment
    payment_method: str = "card"
    last_payment_date: Optional[datetime] = None
    next_payment_date: Optional[datetime] = None
    next_payment_amount: float = 0
    
    def days_remaining(self) -> int:
        """Days remaining in current period"""
        remaining = (self.current_period_end - datetime.now(timezone.utc)).total_seconds()
        return max(0, int(remaining / 86400))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "plan": self.plan.tier.value,
            "plan_name": self.plan.name,
            "status": self.status.value,
            "current_period_start": self.current_period_start.isoformat(),
            "current_period_end": self.current_period_end.isoformat(),
            "days_remaining": self.days_remaining(),
            "is_trial": self.is_trial,
            "trial_ends_at": self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "canceled_at": self.canceled_at.isoformat() if self.canceled_at else None,
            "payment_method": self.payment_method,
            "next_payment_date": self.next_payment_date.isoformat() if self.next_payment_date else None,
            "next_payment_amount": self.next_payment_amount,
        }


class UsageTracker:
    """
    Tracks resource usage for an organization.
    
    Features:
    - Per-metric tracking
    - Rolling windows
    - Usage history
    """
    
    def __init__(self, organization_id: str):
        self._organization_id = organization_id
        self._usage: Dict[UsageMetric, List[UsageRecord]] = {
            m: [] for m in UsageMetric
        }
    
    def record_usage(self, metric: UsageMetric, value: float, timestamp: Optional[datetime] = None) -> None:
        """Record usage for a metric"""
        now = timestamp or datetime.now(timezone.utc)
        
        record = UsageRecord(
            metric=metric,
            value=value,
            timestamp=now,
            period_start=now,
            period_end=now + timedelta(days=1),
        )
        
        self._usage[metric].append(record)
    
    def get_current_usage(self, metric: UsageMetric, window_hours: int = 24) -> float:
        """Get current usage for a metric within time window"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        
        return sum(
            r.value for r in self._usage[metric]
            if r.timestamp >= cutoff
        )
    
    def get_usage_history(
        self,
        metric: UsageMetric,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get usage history for a metric"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        return [
            {
                "timestamp": r.timestamp.isoformat(),
                "value": r.value,
            }
            for r in self._usage[metric]
            if r.timestamp >= cutoff
        ]
    
    def reset_usage(self, metric: UsageMetric) -> None:
        """Reset usage for a metric"""
        self._usage[metric] = []
    
    def get_all_current_usage(self, window_hours: int = 24) -> Dict[str, float]:
        """Get current usage for all metrics"""
        return {
            metric.value: self.get_current_usage(metric, window_hours)
            for metric in UsageMetric
        }


class QuotaManager:
    """
    Manages quota enforcement.
    
    Features:
    - Per-resource quotas
    - Soft/hard limits
    - Grace periods
    - Notifications
    """
    
    def __init__(self, plan: SubscriptionPlan):
        self._plan = plan
        self._overrides: Dict[str, int] = {}  # metric -> override limit
    
    def get_limit(self, metric: UsageMetric) -> int:
        """Get limit for a metric"""
        # Check for override
        metric_name = f"max_{metric.value}"
        if metric_name in self._overrides:
            return self._overrides[metric_name]
        
        return getattr(self._plan.limits, metric_name, 0)
    
    def set_override(self, metric: UsageMetric, limit: int) -> None:
        """Set an override limit for a metric"""
        self._overrides[f"max_{metric.value}"] = limit
    
    def clear_override(self, metric: UsageMetric) -> None:
        """Clear override for a metric"""
        self._overrides.pop(f"max_{metric.value}", None)
    
    def check_quota(
        self,
        metric: UsageMetric,
        current_usage: float,
        requested_additional: float = 0,
    ) -> Tuple[bool, QuotaStatus]:
        """
        Check if quota allows an operation.
        Returns (allowed, status)
        """
        limit = self.get_limit(metric)
        
        if limit == 0:
            # Unlimited
            return True, QuotaStatus(
                metric=metric,
                used=current_usage,
                limit=float('inf'),
                percentage=0,
                remaining=float('inf'),
                is_exceeded=False,
            )
        
        new_usage = current_usage + requested_additional
        percentage = (new_usage / limit) * 100 if limit > 0 else 0
        remaining = max(0, limit - new_usage)
        is_exceeded = new_usage > limit
        
        # Calculate reset time (assume daily reset)
        now = datetime.now(timezone.utc)
        reset_at = datetime.combine(
            now.date() + timedelta(days=1),
            datetime.min.time(),
        )
        
        status = QuotaStatus(
            metric=metric,
            used=current_usage,
            limit=limit,
            percentage=min(percentage, 100),
            remaining=remaining,
            is_exceeded=is_exceeded,
            reset_at=reset_at,
        )
        
        allowed = not is_exceeded
        
        # Allow soft overage for some metrics (with warning)
        soft_limit_metrics = {UsageMetric.API_CALLS, UsageMetric.BACKTESTS}
        if metric in soft_limit_metrics and is_exceeded:
            allowed = True  # Allow with warning
        
        return allowed, status
    
    def get_all_quota_status(self, usage_tracker: UsageTracker) -> List[QuotaStatus]:
        """Get quota status for all metrics"""
        statuses = []
        
        for metric in UsageMetric:
            usage = usage_tracker.get_current_usage(metric)
            _, status = self.check_quota(metric, usage)
            statuses.append(status)
        
        return statuses


class SubscriptionManager:
    """
    Manages subscription lifecycle.
    
    Features:
    - Subscription creation and updates
    - Plan changes
    - Trial management
    - Cancellation
    """
    
    def __init__(self):
        self._subscriptions: Dict[str, SubscriptionInfo] = {}
        self._usage_trackers: Dict[str, UsageTracker] = {}
        self._quota_managers: Dict[str, QuotaManager] = {}
        self._billing_accounts: Dict[str, BillingAccount] = {}
    
    def create_subscription(
        self,
        organization: Organization,
        tier: SubscriptionTier,
        interval: BillingInterval = BillingInterval.MONTHLY,
        is_trial: bool = False,
        trial_days: int = 0,
    ) -> SubscriptionInfo:
        """Create a new subscription"""
        plan = get_plan_by_tier(tier)
        
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30 if interval == BillingInterval.MONTHLY else 365)
        
        trial_ends_at = None
        status = SubscriptionStatus.ACTIVE
        
        if is_trial and trial_days > 0:
            trial_ends_at = now + timedelta(days=trial_days)
            status = SubscriptionStatus.TRIALING
            period_end = trial_ends_at
        
        subscription = SubscriptionInfo(
            organization_id=organization.org_id,
            plan=plan,
            status=status,
            current_period_start=now,
            current_period_end=period_end,
            is_trial=is_trial,
            trial_ends_at=trial_ends_at,
            next_payment_date=period_end if not is_trial else None,
            next_payment_amount=plan.pricing.monthly_price if interval == BillingInterval.MONTHLY else plan.pricing.yearly_price,
        )
        
        self._subscriptions[organization.org_id] = subscription
        
        # Create usage tracker and quota manager
        self._usage_trackers[organization.org_id] = UsageTracker(organization.org_id)
        self._quota_managers[organization.org_id] = QuotaManager(plan)
        
        return subscription
    
    def get_subscription(self, organization_id: str) -> Optional[SubscriptionInfo]:
        """Get subscription for organization"""
        return self._subscriptions.get(organization_id)
    
    def update_subscription(
        self,
        organization_id: str,
        new_tier: Optional[SubscriptionTier] = None,
        interval: Optional[BillingInterval] = None,
    ) -> Optional[SubscriptionInfo]:
        """Update subscription (plan change, billing cycle)"""
        subscription = self._subscriptions.get(organization_id)
        if not subscription:
            return None
        
        if new_tier and new_tier != subscription.plan.tier:
            subscription.plan = get_plan_by_tier(new_tier)
            # Update quota manager with new plan
            self._quota_managers[organization_id] = QuotaManager(subscription.plan)
        
        if interval:
            # Update billing period
            now = datetime.now(timezone.utc)
            if interval == BillingInterval.MONTHLY:
                subscription.current_period_end = now + timedelta(days=30)
                subscription.next_payment_amount = subscription.plan.pricing.monthly_price
            else:
                subscription.current_period_end = now + timedelta(days=365)
                subscription.next_payment_amount = subscription.plan.pricing.yearly_price
        
        return subscription
    
    def cancel_subscription(
        self,
        organization_id: str,
        cancel_at_period_end: bool = True,
    ) -> bool:
        """Cancel subscription"""
        subscription = self._subscriptions.get(organization_id)
        if not subscription:
            return False
        
        if cancel_at_period_end:
            subscription.cancel_at_period_end = True
            subscription.canceled_at = datetime.now(timezone.utc)
        else:
            subscription.status = SubscriptionStatus.CANCELED
        
        return True
    
    def reactivate_subscription(self, organization_id: str) -> bool:
        """Reactivate a canceled subscription"""
        subscription = self._subscriptions.get(organization_id)
        if not subscription:
            return False
        
        if subscription.cancel_at_period_end:
            subscription.cancel_at_period_end = False
            subscription.canceled_at = None
            subscription.status = SubscriptionStatus.ACTIVE
        
        return True
    
    def convert_trial_to_paid(self, organization_id: str) -> bool:
        """Convert trial subscription to paid"""
        subscription = self._subscriptions.get(organization_id)
        if not subscription or not subscription.is_trial:
            return False
        
        subscription.is_trial = False
        subscription.trial_ends_at = None
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.current_period_start = datetime.now(timezone.utc)
        subscription.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
        subscription.next_payment_date = subscription.current_period_end
        
        return True
    
    def get_usage_tracker(self, organization_id: str) -> Optional[UsageTracker]:
        """Get usage tracker for organization"""
        return self._usage_trackers.get(organization_id)
    
    def get_quota_manager(self, organization_id: str) -> Optional[QuotaManager]:
        """Get quota manager for organization"""
        return self._quota_managers.get(organization_id)
    
    def check_feature_access(
        self,
        organization_id: str,
        feature_code: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if organization has access to a feature.
        Returns (has_access, error_message)
        """
        subscription = self._subscriptions.get(organization_id)
        if not subscription:
            return False, "No active subscription"
        
        has_feature = subscription.plan.has_feature(feature_code)
        
        if not has_feature:
            return False, f"Feature '{feature_code}' requires {subscription.plan.name} plan or higher"
        
        return True, None
    
    def check_quota_and_usage(
        self,
        organization_id: str,
        metric: UsageMetric,
        additional_usage: float = 0,
    ) -> Tuple[bool, QuotaStatus]:
        """
        Check quota and return status.
        Returns (allowed, status)
        """
        quota_manager = self._quota_managers.get(organization_id)
        usage_tracker = self._usage_trackers.get(organization_id)
        
        if not quota_manager or not usage_tracker:
            return True, QuotaStatus(
                metric=metric,
                used=0,
                limit=0,
                percentage=0,
                remaining=0,
                is_exceeded=False,
            )
        
        current_usage = usage_tracker.get_current_usage(metric)
        return quota_manager.check_quota(metric, current_usage, additional_usage)


class BillingService:
    """
    Handles billing operations.
    
    Features:
    - Payment processing (stub)
    - Invoice generation (stub)
    - Payment method management
    """
    
    def __init__(self):
        self._invoices: Dict[str, Dict[str, Any]] = {}
        self._payment_methods: Dict[str, List[Dict[str, Any]]] = {}
    
    def create_invoice(
        self,
        organization_id: str,
        amount: float,
        currency: str = "USD",
        description: str = "",
        items: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Create an invoice"""
        invoice_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
        
        invoice = {
            "invoice_id": invoice_id,
            "organization_id": organization_id,
            "amount": amount,
            "currency": currency,
            "description": description,
            "items": items or [],
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "paid_at": None,
        }
        
        self._invoices[invoice_id] = invoice
        return invoice_id
    
    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Get invoice by ID"""
        return self._invoices.get(invoice_id)
    
    def get_organization_invoices(
        self,
        organization_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get invoices for organization"""
        return [
            inv for inv in self._invoices.values()
            if inv["organization_id"] == organization_id
        ][:limit]
    
    def process_payment(
        self,
        organization_id: str,
        invoice_id: str,
        payment_method_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Process payment for an invoice.
        Returns (success, error_message)
        """
        invoice = self._invoices.get(invoice_id)
        if not invoice:
            return False, "Invoice not found"
        
        # Stub: In production, integrate with Stripe
        # Simulate successful payment
        invoice["status"] = "paid"
        invoice["paid_at"] = datetime.now(timezone.utc).isoformat()
        
        return True, None
    
    def add_payment_method(
        self,
        organization_id: str,
        method_type: str,
        details: Dict[str, Any],
    ) -> str:
        """Add a payment method"""
        method_id = f"PM-{uuid.uuid4().hex[:8].upper()}"
        
        method = {
            "method_id": method_id,
            "type": method_type,
            "details": details,
            "is_default": len(self._payment_methods.get(organization_id, [])) == 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        if organization_id not in self._payment_methods:
            self._payment_methods[organization_id] = []
        
        self._payment_methods[organization_id].append(method)
        return method_id
    
    def get_payment_methods(self, organization_id: str) -> List[Dict[str, Any]]:
        """Get payment methods for organization"""
        return self._payment_methods.get(organization_id, [])
    
    def remove_payment_method(self, organization_id: str, method_id: str) -> bool:
        """Remove a payment method"""
        if organization_id not in self._payment_methods:
            return False
        
        methods = self._payment_methods[organization_id]
        self._payment_methods[organization_id] = [
            m for m in methods if m["method_id"] != method_id
        ]
        return True
    
    def set_default_payment_method(self, organization_id: str, method_id: str) -> bool:
        """Set default payment method"""
        if organization_id not in self._payment_methods:
            return False
        
        for method in self._payment_methods[organization_id]:
            method["is_default"] = method["method_id"] == method_id
        
        return True
