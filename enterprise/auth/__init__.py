"""
Enterprise Authentication Module

Enhanced authentication with:
- Multi-factor authentication (TOTP, SMS, Email, WebAuthn)
- Session management
- Device management
- Rate limiting
- Brute force protection
"""

from enterprise.auth.authenticator import (
    EnterpriseAuthenticator,
    AuthenticationResult,
    MFAChallenge,
)
from enterprise.auth.session_manager import (
    SessionManager,
    SessionConfig,
)
from enterprise.auth.device_manager import (
    DeviceManager,
    DeviceFingerprint,
)
from enterprise.auth.mfa import (
    MFAService,
    TOTPProvider,
    EmailProvider,
    RecoveryCodeManager,
)

__all__ = [
    "EnterpriseAuthenticator",
    "AuthenticationResult",
    "MFAChallenge",
    "SessionManager",
    "SessionConfig",
    "DeviceManager",
    "DeviceFingerprint",
    "MFAService",
    "TOTPProvider",
    "EmailProvider",
    "RecoveryCodeManager",
]
