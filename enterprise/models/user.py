"""
Enterprise User Models

Extended user models for enterprise features:
- User profiles
- Session management
- Device management
- User preferences
"""

import uuid
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class MFAType(Enum):
    """Multi-factor authentication types"""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    WEBAUTHN = "webauthn"


class SessionStatus(Enum):
    """Session status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class EnterpriseUser:
    """Enterprise user profile"""
    user_id: str
    email: str
    email_verified: bool = False
    
    # Profile
    full_name: str = ""
    display_name: str = ""
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    phone_verified: bool = False
    
    # Authentication
    password_hash: Optional[str] = None
    password_changed_at: Optional[datetime] = None
    
    # MFA
    mfa_enabled: bool = False
    mfa_methods: List[MFAType] = field(default_factory=list)
    mfa_totp_secret: Optional[str] = None
    mfa_recovery_codes: List[str] = field(default_factory=list)
    
    # Account status
    is_active: bool = True
    is_locked: bool = False
    lock_reason: Optional[str] = None
    failed_login_attempts: int = 0
    
    # Organization membership
    primary_org_id: Optional[str] = None
    organizations: List[str] = field(default_factory=list)  # List of org_ids
    
    # Preferences
    timezone: str = "UTC"
    language: str = "en"
    theme: str = "dark"
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    last_active: Optional[datetime] = None
    
    # External identity
    oauth_providers: Dict[str, str] = field(default_factory=dict)  # provider -> provider_user_id
    
    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.full_name or self.email.split("@")[0]
    
    @classmethod
    def create(
        cls,
        email: str,
        full_name: str = "",
        password_hash: Optional[str] = None,
    ) -> "EnterpriseUser":
        """Create a new enterprise user"""
        return cls(
            user_id=str(uuid.uuid4()),
            email=email.lower(),
            full_name=full_name,
            display_name=full_name or email.split("@")[0],
            password_hash=password_hash,
            mfa_recovery_codes=cls._generate_recovery_codes(),
        )
    
    @staticmethod
    def _generate_recovery_codes(count: int = 10) -> List[str]:
        """Generate recovery codes"""
        return [secrets.token_urlsafe(8) for _ in range(count)]
    
    def enable_mfa(self, method: MFAType, secret: Optional[str] = None) -> None:
        """Enable MFA for a specific method"""
        if method not in self.mfa_methods:
            self.mfa_methods.append(method)
        self.mfa_enabled = True
        if method == MFAType.TOTP:
            self.mfa_totp_secret = secret
        self.mfa_recovery_codes = self._generate_recovery_codes()
    
    def disable_mfa(self) -> None:
        """Disable all MFA"""
        self.mfa_enabled = False
        self.mfa_methods = []
        self.mfa_totp_secret = None
        self.mfa_recovery_codes = []
    
    def consume_recovery_code(self, code: str) -> bool:
        """Consume a recovery code (one-time use)"""
        if code in self.mfa_recovery_codes:
            self.mfa_recovery_codes.remove(code)
            if len(self.mfa_recovery_codes) < 3:
                self.mfa_recovery_codes = self._generate_recovery_codes()
            return True
        return False
    
    def lock_account(self, reason: str) -> None:
        """Lock user account"""
        self.is_locked = True
        self.lock_reason = reason
    
    def unlock_account(self) -> None:
        """Unlock user account"""
        self.is_locked = False
        self.lock_reason = None
        self.failed_login_attempts = 0
    
    def record_login(self, success: bool) -> None:
        """Record login attempt"""
        self.last_login = datetime.utcnow()
        if success:
            self.failed_login_attempts = 0
        else:
            self.failed_login_attempts += 1
            if self.failed_login_attempts >= 5:
                self.lock_account("Too many failed login attempts")
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        result = {
            "user_id": self.user_id,
            "email": self.email,
            "email_verified": self.email_verified,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "phone": self.phone,
            "phone_verified": self.phone_verified,
            "mfa_enabled": self.mfa_enabled,
            "mfa_methods": [m.value for m in self.mfa_methods],
            "is_active": self.is_active,
            "is_locked": self.is_locked,
            "organizations": self.organizations,
            "primary_org_id": self.primary_org_id,
            "timezone": self.timezone,
            "language": self.language,
            "theme": self.theme,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "oauth_providers": list(self.oauth_providers.keys()),
        }
        
        if include_sensitive:
            result["password_hash"] = self.password_hash
            result["mfa_totp_secret"] = self.mfa_totp_secret
            result["mfa_recovery_codes_count"] = len(self.mfa_recovery_codes)
            result["lock_reason"] = self.lock_reason
            result["failed_login_attempts"] = self.failed_login_attempts
        
        return result


@dataclass
class UserSession:
    """User session for tracking active logins"""
    session_id: str
    user_id: str
    organization_id: Optional[str] = None
    
    # Session info
    ip_address: str = ""
    user_agent: str = ""
    device_id: Optional[str] = None
    device_name: str = "Unknown"
    device_type: str = "desktop"  # "desktop", "mobile", "tablet"
    
    # Location
    city: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Tokens
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    
    # Status
    status: SessionStatus = SessionStatus.ACTIVE
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=24))
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    # Metadata
    created_by: str = "password"  # "password", "oauth", "api_key"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at
    
    @property
    def is_valid(self) -> bool:
        return self.status == SessionStatus.ACTIVE and not self.is_expired
    
    @property
    def age_seconds(self) -> float:
        return (datetime.utcnow() - self.created_at).total_seconds()
    
    def extend(self, hours: int = 24) -> None:
        """Extend session expiration"""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.last_activity = datetime.utcnow()
    
    def revoke(self) -> None:
        """Revoke this session"""
        self.status = SessionStatus.REVOKED
    
    def touch(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def to_dict(self, include_tokens: bool = False) -> Dict[str, Any]:
        result = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent[:100] if self.user_agent else "",
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "city": self.city,
            "country": self.country,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "created_by": self.created_by,
            "is_current": False,  # To be set by caller
        }
        
        if include_tokens:
            result["access_token"] = self.access_token
            result["refresh_token"] = self.refresh_token
        
        return result


@dataclass
class UserDevice:
    """User device for device management"""
    device_id: str
    user_id: str
    
    # Device info
    name: str
    device_type: str  # "desktop", "mobile", "tablet", "api"
    
    # Browser/OS info
    browser: Optional[str] = None
    browser_version: Optional[str] = None
    os: Optional[str] = None
    os_version: Optional[str] = None
    
    # Hardware
    is_mobile: bool = False
    touch_capable: bool = False
    
    # Identity
    fingerprint: Optional[str] = None
    client_cert_id: Optional[str] = None
    
    # Status
    is_trusted: bool = False
    is_current: bool = False
    last_seen: datetime = field(default_factory=datetime.utcnow)
    first_seen: datetime = field(default_factory=datetime.utcnow)
    
    # Sessions on this device
    active_sessions: int = 0
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        user_id: str,
        name: str,
        device_type: str,
        user_agent: str = "",
    ) -> "UserDevice":
        """Create a new device record"""
        device = cls(
            device_id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            device_type=device_type,
        )
        
        # Parse user agent
        if user_agent:
            device._parse_user_agent(user_agent)
        
        # Generate fingerprint
        device.fingerprint = cls._generate_fingerprint(device)
        
        return device
    
    def _parse_user_agent(self, user_agent: str) -> None:
        """Parse user agent string"""
        ua_lower = user_agent.lower()
        
        # Detect browser
        if "chrome" in ua_lower:
            self.browser = "Chrome"
        elif "firefox" in ua_lower:
            self.browser = "Firefox"
        elif "safari" in ua_lower:
            self.browser = "Safari"
        elif "edge" in ua_lower:
            self.browser = "Edge"
        
        # Detect OS
        if "windows" in ua_lower:
            self.os = "Windows"
        elif "mac" in ua_lower:
            self.os = "macOS"
        elif "linux" in ua_lower:
            self.os = "Linux"
        elif "android" in ua_lower:
            self.os = "Android"
            self.is_mobile = True
        elif "iphone" in ua_lower or "ipad" in ua_lower:
            self.os = "iOS"
            self.is_mobile = True
        
        # Mobile detection
        if any(m in ua_lower for m in ["mobile", "android", "iphone", "ipad"]):
            self.is_mobile = True
        
        # Touch capable
        self.touch_capable = "touch" in ua_lower or self.is_mobile
    
    @staticmethod
    def _generate_fingerprint(device: "UserDevice") -> str:
        """Generate device fingerprint"""
        data = f"{device.user_id}:{device.browser}:{device.os}:{device.device_type}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]
    
    def trust(self) -> None:
        """Mark device as trusted"""
        self.is_trusted = True
    
    def distrust(self) -> None:
        """Mark device as untrusted"""
        self.is_trusted = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "user_id": self.user_id,
            "name": self.name,
            "device_type": self.device_type,
            "browser": self.browser,
            "browser_version": self.browser_version,
            "os": self.os,
            "os_version": self.os_version,
            "is_trusted": self.is_trusted,
            "is_current": self.is_current,
            "last_seen": self.last_seen.isoformat(),
            "first_seen": self.first_seen.isoformat(),
            "active_sessions": self.active_sessions,
        }


@dataclass
class UserPreferences:
    """User preferences and settings"""
    user_id: str
    
    # Notification preferences
    email_notifications: bool = True
    push_notifications: bool = True
    sms_notifications: bool = False
    
    # Notification types
    notify_trade_executed: bool = True
    notify_trade_closed: bool = True
    notify_strategy_error: bool = True
    notify_risk_alert: bool = True
    notify_daily_summary: bool = False
    notify_weekly_report: bool = True
    notify_team_activity: bool = True
    
    # Trading preferences
    default_market: str = "R_100"
    default_stake: float = 10.0
    auto_trading_enabled: bool = False
    max_daily_trades: int = 20
    
    # Display preferences
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    time_format: str = "24h"
    currency_display: str = "USD"
    
    # Privacy
    show_profile: bool = True
    show_trades: bool = True
    allow_team_view: bool = True
    
    # API preferences
    api_key_rotation_days: int = 90
    api_rate_limit_override: Optional[int] = None
    
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @classmethod
    def create(cls, user_id: str) -> "UserPreferences":
        """Create default preferences"""
        return cls(user_id=user_id)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "notifications": {
                "email": self.email_notifications,
                "push": self.push_notifications,
                "sms": self.sms_notifications,
                "trade_executed": self.notify_trade_executed,
                "trade_closed": self.notify_trade_closed,
                "strategy_error": self.notify_strategy_error,
                "risk_alert": self.notify_risk_alert,
                "daily_summary": self.notify_daily_summary,
                "weekly_report": self.notify_weekly_report,
                "team_activity": self.notify_team_activity,
            },
            "trading": {
                "default_market": self.default_market,
                "default_stake": self.default_stake,
                "auto_trading_enabled": self.auto_trading_enabled,
                "max_daily_trades": self.max_daily_trades,
            },
            "display": {
                "timezone": self.timezone,
                "date_format": self.date_format,
                "time_format": self.time_format,
                "currency_display": self.currency_display,
            },
            "privacy": {
                "show_profile": self.show_profile,
                "show_trades": self.show_trades,
                "allow_team_view": self.allow_team_view,
            },
            "api": {
                "api_key_rotation_days": self.api_key_rotation_days,
                "api_rate_limit_override": self.api_rate_limit_override,
            },
            "updated_at": self.updated_at.isoformat(),
        }
