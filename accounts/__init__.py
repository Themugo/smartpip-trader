"""
Unified Account Center

Provides unified authentication and account management for Deriv, supporting:
- OAuth2 authentication flow
- Demo and Real account switching
- Multiple account types (MT5, Deriv Trader, Deriv Go)
- Centralized balance tracking
- Account preferences and settings
"""

from accounts.center import AccountCenter
from accounts.models import (
    AccountType,
    AccountInfo,
    AuthToken,
    DerivToken,
)
from accounts.auth import DerivOAuth2, TokenManager

__all__ = [
    "AccountCenter",
    "AccountType",
    "AccountInfo",
    "AuthToken",
    "DerivToken",
    "DerivOAuth2",
    "TokenManager",
]
