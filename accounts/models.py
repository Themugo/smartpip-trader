"""
Account data models for the unified account center.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AccountType(Enum):
    """Deriv account types"""
    DEMO = "demo"
    REAL = "real"
    MT5_DEMO = "mt5_demo"
    MT5_REAL = "mt5_real"
    DERIV_GO = "deriv_go"


class TokenType(Enum):
    """Token types for Deriv API"""
    API_TOKEN = "api_token"
    OAUTH_TOKEN = "oauth_token"
    REFRESH_TOKEN = "refresh_token"


@dataclass
class AccountInfo:
    """Complete account information"""
    account_id: str
    account_type: AccountType
    currency: str
    balance: float
    loginid: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    is_virtual: bool = True
    is_primary: bool = False
    created_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "account_type": self.account_type.value,
            "currency": self.currency,
            "balance": self.balance,
            "loginid": self.loginid,
            "email": self.email,
            "display_name": self.display_name,
            "is_virtual": self.is_virtual,
            "is_primary": self.is_primary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_deriv_api(cls, data: Dict[str, Any]) -> "AccountInfo":
        """Create AccountInfo from Deriv API response"""
        account_type = cls._determine_account_type(data)
        
        return cls(
            account_id=data.get("account_id", data.get("client_id", "")),
            account_type=account_type,
            currency=data.get("currency", "USD"),
            balance=float(data.get("balance", 0)),
            loginid=data.get("loginid", ""),
            email=data.get("email"),
            display_name=data.get("display_name"),
            is_virtual=data.get("is_virtual", True),
            is_primary=data.get("is_primary", False),
            created_at=None,
            last_used=datetime.utcnow(),
            metadata=data,
        )
    
    @staticmethod
    def _determine_account_type(data: Dict[str, Any]) -> AccountType:
        """Determine account type from Deriv API data"""
        if data.get("is_virtual"):
            if data.get("account_type") == "mt5":
                return AccountType.MT5_DEMO
            return AccountType.DEMO
        
        if data.get("account_type") == "mt5":
            return AccountType.MT5_REAL
        elif data.get("account_type") == "deriv_go":
            return AccountType.DERIV_GO
        return AccountType.REAL
    
    @property
    def is_demo(self) -> bool:
        return self.account_type in (
            AccountType.DEMO,
            AccountType.MT5_DEMO,
        )
    
    @property
    def is_mt5(self) -> bool:
        return self.account_type in (
            AccountType.MT5_DEMO,
            AccountType.MT5_REAL,
        )


@dataclass
class AuthToken:
    """Authentication token information"""
    token_type: TokenType
    token: str
    expires_at: Optional[datetime] = None
    scope: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at
    
    @property
    def is_valid(self) -> bool:
        return not self.is_expired
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_type": self.token_type.value,
            "token": self.token[:8] + "..." if len(self.token) > 8 else self.token,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
            "is_valid": self.is_valid,
        }


@dataclass
class DerivToken:
    """Deriv API token for authentication"""
    token: str
    display_name: str
    wallet_id: str
    permissions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    is_active: bool = True
    
    def has_permission(self, permission: str) -> bool:
        """Check if token has a specific permission"""
        if "admin" in self.permissions:
            return True
        return permission in self.permissions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "token": self.token[:8] + "..." if len(self.token) > 8 else self.token,
            "display_name": self.display_name,
            "wallet_id": self.wallet_id,
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "is_active": self.is_active,
        }


@dataclass
class SessionInfo:
    """User session information"""
    session_id: str
    user_id: str
    email: str
    tokens: List[AuthToken] = field(default_factory=list)
    accounts: List[AccountInfo] = field(default_factory=list)
    active_account_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_activity: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at
    
    @property
    def active_account(self) -> Optional[AccountInfo]:
        if not self.active_account_id:
            return self.accounts[0] if self.accounts else None
        return next(
            (a for a in self.accounts if a.account_id == self.active_account_id),
            None,
        )
    
    def get_account(self, account_id: str) -> Optional[AccountInfo]:
        return next(
            (a for a in self.accounts if a.account_id == account_id),
            None,
        )
    
    def get_demo_accounts(self) -> List[AccountInfo]:
        return [a for a in self.accounts if a.is_demo]
    
    def get_real_accounts(self) -> List[AccountInfo]:
        return [a for a in self.accounts if not a.is_demo]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "email": self.email,
            "tokens": [t.to_dict() for t in self.tokens],
            "accounts": [a.to_dict() for a in self.accounts],
            "active_account_id": self.active_account_id,
            "active_account": self.active_account.to_dict() if self.active_account else None,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_activity": self.last_activity.isoformat(),
            "is_expired": self.is_expired,
        }
