"""
Enterprise Authenticator

Comprehensive authentication service with:
- Password authentication
- Multi-factor authentication
- OAuth2 integration
- Brute force protection
- Account lockout
"""

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from passlib.context import CryptContext
import pyotp

from enterprise.models.user import EnterpriseUser, MFAType
from enterprise.models.audit import AuditLogger, AuditEventType, AuditSeverity


class AuthMethod(Enum):
    """Authentication methods"""
    PASSWORD = "password"
    MFA_TOTP = "totp"
    MFA_SMS = "sms"
    MFA_EMAIL = "email"
    MFA_WEBAUTHN = "webauthn"
    OAUTH_GOOGLE = "google"
    OAUTH_GITHUB = "github"
    API_KEY = "api_key"
    REFRESH_TOKEN = "refresh_token"


@dataclass
class AuthenticationResult:
    """Result of authentication attempt"""
    success: bool
    user: Optional[EnterpriseUser] = None
    session_id: Optional[str] = None
    mfa_required: bool = False
    mfa_challenge: Optional["MFAChallenge"] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    # Token info
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    
    # Security info
    requires_mfa_verification: bool = False
    new_device: bool = False
    new_location: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "error": self.error,
            "error_code": self.error_code,
            "mfa_required": self.mfa_required,
            "requires_mfa_verification": self.requires_mfa_verification,
            "new_device": self.new_device,
            "new_location": self.new_location,
        }
        
        if self.user:
            result["user"] = {
                "user_id": self.user.user_id,
                "email": self.user.email,
                "mfa_enabled": self.user.mfa_enabled,
            }
        
        if self.session_id:
            result["session_id"] = self.session_id
            
        if self.access_token:
            result["access_token"] = self.access_token
            result["token_type"] = "Bearer"
            result["expires_in"] = self.expires_in or 3600
            
        if self.refresh_token:
            result["refresh_token"] = self.refresh_token
            
        if self.mfa_required and self.mfa_challenge:
            result["mfa_challenge"] = self.mfa_challenge.to_dict()
            
        return result


@dataclass
class MFAChallenge:
    """MFA challenge for second-factor authentication"""
    challenge_id: str
    user_id: str
    methods: List[MFAType]
    method: Optional[MFAType] = None
    code: Optional[str] = None
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=5))
    attempts: int = 0
    verified: bool = False
    
    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at
    
    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.verified and self.attempts < 5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "user_id": self.user_id,
            "methods": [m.value for m in self.methods],
            "method": self.method.value if self.method else None,
            "expires_at": self.expires_at.isoformat(),
            "attempts": self.attempts,
        }


@dataclass
class BruteForceProtection:
    """Brute force protection state"""
    ip_attempts: Dict[str, int] = field(default_factory=dict)
    user_attempts: Dict[str, int] = field(default_factory=dict)
    lockouts: Dict[str, datetime] = field(default_factory=dict)
    
    max_attempts: int = 5
    lockout_duration: int = 15  # minutes
    tracking_window: int = 60  # minutes
    
    def record_attempt(self, identifier: str, is_ip: bool = True) -> Tuple[bool, Optional[int]]:
        """
        Record an authentication attempt.
        Returns (is_locked, attempts_remaining)
        """
        current_time = time.time()
        window_start = current_time - (self.tracking_window * 60)
        
        # Clean old attempts
        if is_ip:
            self.ip_attempts = {
                k: v for k, v in self.ip_attempts.items()
                if v > window_start
            }
            self.ip_attempts[identifier] = current_time
            attempts = len(self.ip_attempts)
        else:
            self.user_attempts = {
                k: v for k, v in self.user_attempts.items()
                if v > window_start
            }
            self.user_attempts[identifier] = current_time
            attempts = len(self.user_attempts)
        
        if attempts >= self.max_attempts:
            self.lockouts[identifier] = datetime.now(timezone.utc) + timedelta(minutes=self.lockout_duration)
            return True, 0
        
        return False, self.max_attempts - attempts
    
    def is_locked(self, identifier: str) -> bool:
        """Check if identifier is locked"""
        if identifier in self.lockouts:
            if datetime.now(timezone.utc) >= self.lockouts[identifier]:
                # Lock expired
                del self.lockouts[identifier]
                return False
            return True
        return False
    
    def get_lockout_remaining(self, identifier: str) -> int:
        """Get remaining lockout time in seconds"""
        if identifier in self.lockouts:
            remaining = (self.lockouts[identifier] - datetime.now(timezone.utc)).total_seconds()
            return max(0, int(remaining))
        return 0
    
    def reset(self, identifier: str) -> None:
        """Reset attempts for identifier"""
        self.ip_attempts.pop(identifier, None)
        self.user_attempts.pop(identifier, None)
        self.lockouts.pop(identifier, None)


class EnterpriseAuthenticator:
    """
    Enterprise authentication service.
    
    Features:
    - Secure password hashing with bcrypt
    - Multi-factor authentication
    - Brute force protection
    - Account lockout
    - Audit logging
    - Session management
    """
    
    def __init__(
        self,
        jwt_secret: str = "default-secret-change-in-production",
        jwt_algorithm: str = "HS256",
        access_token_expire: int = 3600,  # 1 hour
        refresh_token_expire: int = 604800,  # 7 days
        mfa_code_expire: int = 300,  # 5 minutes
    ):
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = jwt_algorithm
        self._access_token_expire = access_token_expire
        self._refresh_token_expire = refresh_token_expire
        self._mfa_code_expire = mfa_code_expire
        
        self._brute_force = BruteForceProtection()
        self._audit = AuditLogger()
        
        # User store (in production, this would be a database)
        self._users: Dict[str, EnterpriseUser] = {}
        self._email_index: Dict[str, str] = {}  # email -> user_id
        
        # Active MFA challenges
        self._mfa_challenges: Dict[str, MFAChallenge] = {}
        
        # Refresh tokens
        self._refresh_tokens: Dict[str, Dict[str, Any]] = {}
        
        # API keys
        self._api_keys: Dict[str, Dict[str, Any]] = {}
    
    # ─────────────────────────────────────────────────────────────
    # User Management
    # ─────────────────────────────────────────────────────────────
    
    def create_user(
        self,
        email: str,
        password: Optional[str] = None,
        full_name: str = "",
        send_verification: bool = True,
    ) -> Tuple[EnterpriseUser, str]:
        """Create a new user"""
        # Check if email exists
        if email.lower() in self._email_index:
            raise ValueError("Email already registered")
        
        # Hash password if provided
        password_hash = None
        if password:
            password_hash = self._pwd_context.hash(password)
        
        # Create user
        user = EnterpriseUser.create(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
        )
        
        self._users[user.user_id] = user
        self._email_index[email.lower()] = user.user_id
        
        # Generate email verification token
        verification_token = secrets.token_urlsafe(32)
        
        # Log user creation
        self._audit.log(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.INFO,
            user_id=user.user_id,
            description=f"User created: {email}",
        )
        
        return user, verification_token
    
    def get_user_by_email(self, email: str) -> Optional[EnterpriseUser]:
        """Get user by email"""
        user_id = self._email_index.get(email.lower())
        if user_id:
            return self._users.get(user_id)
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[EnterpriseUser]:
        """Get user by ID"""
        return self._users.get(user_id)
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[EnterpriseUser]:
        """Update user profile"""
        user = self._users.get(user_id)
        if not user:
            return None
        
        # Allowed updates
        allowed_fields = ["full_name", "display_name", "phone", "timezone", "language", "theme"]
        for field_name in allowed_fields:
            if field_name in updates:
                setattr(user, field_name, updates[field_name])
        
        user.updated_at = datetime.now(timezone.utc)
        return user
    
    def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> Tuple[bool, Optional[str]]:
        """Change user password"""
        user = self._users.get(user_id)
        if not user:
            return False, "User not found"
        
        # Verify old password
        if user.password_hash:
            if not self._pwd_context.verify(old_password, user.password_hash):
                return False, "Current password is incorrect"
        
        # Hash new password
        user.password_hash = self._pwd_context.hash(new_password)
        user.password_changed_at = datetime.now(timezone.utc)
        
        # Reset brute force protection
        self._brute_force.reset(user_id)
        
        # Log password change
        self._audit.log(
            event_type=AuditEventType.PASSWORD_CHANGED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            description="Password changed",
        )
        
        return True, None
    
    def reset_password(self, email: str, reset_token: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """Reset password with reset token"""
        user = self.get_user_by_email(email)
        if not user:
            return False, "User not found"
        
        # In production, verify reset token from email
        # For now, we assume token is valid
        
        user.password_hash = self._pwd_context.hash(new_password)
        user.password_changed_at = datetime.now(timezone.utc)
        
        # Log password reset
        self._audit.log(
            event_type=AuditEventType.PASSWORD_RESET,
            severity=AuditSeverity.INFO,
            user_id=user.user_id,
            description="Password reset via email",
        )
        
        return True, None
    
    # ─────────────────────────────────────────────────────────────
    # Authentication
    # ─────────────────────────────────────────────────────────────
    
    def authenticate(
        self,
        email: str,
        password: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> AuthenticationResult:
        """Authenticate user with email and password"""
        # Check IP lockout
        if self._brute_force.is_locked(ip_address):
            remaining = self._brute_force.get_lockout_remaining(ip_address)
            self._audit.log_security(
                event_type="suspicious",
                user_id=None,
                description=f"Login attempt from locked IP: {ip_address}",
                severity=AuditSeverity.WARNING,
            )
            return AuthenticationResult(
                success=False,
                error=f"Account temporarily locked. Try again in {remaining} seconds.",
                error_code="ACCOUNT_LOCKED",
            )
        
        # Get user
        user = self.get_user_by_email(email)
        if not user:
            self._brute_force.record_attempt(ip_address, is_ip=True)
            self._audit.log_login(user_id=None, success=False, ip_address=ip_address)
            return AuthenticationResult(
                success=False,
                error="Invalid email or password",
                error_code="INVALID_CREDENTIALS",
            )
        
        # Check user lockout
        if user.is_locked:
            self._audit.log_security(
                event_type="alert",
                user_id=user.user_id,
                description=f"Login attempt to locked account: {email}",
                severity=AuditSeverity.WARNING,
            )
            return AuthenticationResult(
                success=False,
                error="Account is locked",
                error_code="ACCOUNT_LOCKED",
            )
        
        # Verify password
        if not user.password_hash or not self._pwd_context.verify(password, user.password_hash):
            is_locked, remaining = self._brute_force.record_attempt(ip_address, is_ip=True)
            self._brute_force.record_attempt(user.user_id, is_ip=False)
            user.record_login(success=False)
            
            self._audit.log_login(user_id=user.user_id, success=False, ip_address=ip_address)
            
            if is_locked:
                return AuthenticationResult(
                    success=False,
                    error="Too many failed attempts. Account temporarily locked.",
                    error_code="ACCOUNT_LOCKED",
                )
            
            return AuthenticationResult(
                success=False,
                error="Invalid email or password",
                error_code="INVALID_CREDENTIALS",
            )
        
        # Check if MFA is required
        if user.mfa_enabled:
            challenge = self._create_mfa_challenge(user, ip_address)
            user.record_login(success=True)
            
            return AuthenticationResult(
                success=False,
                user=user,
                mfa_required=True,
                mfa_challenge=challenge,
                requires_mfa_verification=True,
            )
        
        # Successful login
        self._brute_force.reset(ip_address)
        self._brute_force.reset(user.user_id)
        user.record_login(success=True)
        
        # Generate tokens
        session_id = secrets.token_urlsafe(32)
        access_token, expires_in = self._generate_access_token(user, session_id)
        refresh_token = self._generate_refresh_token(user, session_id)
        
        self._audit.log_login(user_id=user.user_id, success=True, ip_address=ip_address)
        
        return AuthenticationResult(
            success=True,
            user=user,
            session_id=session_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )
    
    def verify_mfa(
        self,
        challenge_id: str,
        code: str,
        method: MFAType,
    ) -> AuthenticationResult:
        """Verify MFA code"""
        challenge = self._mfa_challenges.get(challenge_id)
        if not challenge or not challenge.is_valid:
            return AuthenticationResult(
                success=False,
                error="Invalid or expired MFA challenge",
                error_code="INVALID_CHALLENGE",
            )
        
        user = self.get_user_by_id(challenge.user_id)
        if not user:
            return AuthenticationResult(
                success=False,
                error="User not found",
                error_code="USER_NOT_FOUND",
            )
        
        challenge.attempts += 1
        
        # Verify code based on method
        verified = False
        if method == MFAType.TOTP:
            verified = self._verify_totp(user, code)
        elif method == MFAType.EMAIL:
            verified = self._verify_email_code(user, code)
        elif method == MFAType.SMS:
            verified = self._verify_sms_code(user, code)
        
        if not verified:
            return AuthenticationResult(
                success=False,
                error="Invalid verification code",
                error_code="INVALID_CODE",
            )
        
        # Mark challenge as verified
        challenge.verified = True
        
        # Generate tokens
        session_id = secrets.token_urlsafe(32)
        access_token, expires_in = self._generate_access_token(user, session_id)
        refresh_token = self._generate_refresh_token(user, session_id)
        
        # Log MFA verification
        self._audit.log_mfa(
            user_id=user.user_id,
            action="verified",
            ip_address="",
            description=f"MFA verified via {method.value}",
        )
        
        return AuthenticationResult(
            success=True,
            user=user,
            session_id=session_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )
    
    def refresh_access_token(self, refresh_token: str) -> Tuple[bool, Optional[str], Optional[int]]:
        """Refresh access token using refresh token"""
        token_data = self._refresh_tokens.get(refresh_token)
        if not token_data:
            return False, None, None
        
        if datetime.now(timezone.utc) > datetime.fromisoformat(token_data["expires_at"]):
            del self._refresh_tokens[refresh_token]
            return False, None, None
        
        user = self.get_user_by_id(token_data["user_id"])
        if not user or not user.is_active:
            return False, None, None
        
        # Generate new access token
        access_token, expires_in = self._generate_access_token(user, token_data["session_id"])
        return True, access_token, expires_in
    
    def revoke_token(self, token: str, token_type: str = "access") -> bool:
        """Revoke a token"""
        if token_type == "refresh":
            if token in self._refresh_tokens:
                del self._refresh_tokens[token]
                return True
        return False
    
    def verify_api_key(self, api_key: str) -> Optional[Tuple[EnterpriseUser, Dict[str, Any]]]:
        """Verify API key and return user and key info"""
        key_data = self._api_keys.get(api_key)
        if not key_data:
            return None
        
        if not key_data.get("active", False):
            return None
        
        user = self.get_user_by_id(key_data["user_id"])
        if not user or not user.is_active:
            return None
        
        return user, key_data
    
    # ─────────────────────────────────────────────────────────────
    # MFA Management
    # ─────────────────────────────────────────────────────────────
    
    def setup_mfa_totp(self, user_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Setup TOTP MFA for user.
        Returns (success, secret, qr_url)
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False, None, None
        
        # Generate TOTP secret
        secret = pyotp.random_base32()
        
        # Store secret temporarily (not confirmed yet)
        user.mfa_totp_secret = secret
        user.enable_mfa(MFAType.TOTP, secret)
        
        # Generate QR URL
        totp = pyotp.TOTP(secret)
        qr_url = totp.provisioning_uri(
            name=user.email,
            issuer_name="SmartPip Trader",
        )
        
        return True, secret, qr_url
    
    def confirm_mfa_totp(self, user_id: str, code: str) -> bool:
        """Confirm TOTP setup with verification code"""
        user = self.get_user_by_id(user_id)
        if not user or not user.mfa_totp_secret:
            return False
        
        totp = pyotp.TOTP(user.mfa_totp_secret)
        if not totp.verify(code):
            return False
        
        # MFA is now confirmed and enabled
        user.mfa_recovery_codes = user._generate_recovery_codes()
        
        self._audit.log_mfa(
            user_id=user_id,
            action="enabled",
            ip_address="",
            description="TOTP MFA enabled",
        )
        
        return True
    
    def disable_mfa(self, user_id: str, password: str) -> Tuple[bool, Optional[str]]:
        """Disable MFA with password verification"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False, "User not found"
        
        if not self._pwd_context.verify(password, user.password_hash):
            return False, "Invalid password"
        
        user.disable_mfa()
        
        self._audit.log_mfa(
            user_id=user_id,
            action="disabled",
            ip_address="",
            description="MFA disabled",
        )
        
        return True, None
    
    def _create_mfa_challenge(self, user: EnterpriseUser, ip_address: str) -> MFAChallenge:
        """Create MFA challenge for user"""
        challenge = MFAChallenge(
            challenge_id=secrets.token_urlsafe(32),
            user_id=user.user_id,
            methods=user.mfa_methods,
        )
        
        self._mfa_challenges[challenge.challenge_id] = challenge
        
        # Send code via email if enabled
        if MFAType.EMAIL in user.mfa_methods:
            self._send_email_code(user)
        
        return challenge
    
    def _verify_totp(self, user: EnterpriseUser, code: str) -> bool:
        """Verify TOTP code"""
        if not user.mfa_totp_secret:
            return False
        
        totp = pyotp.TOTP(user.mfa_totp_secret)
        return totp.verify(code)
    
    def _verify_email_code(self, user: EnterpriseUser, code: str) -> bool:
        """Verify email code"""
        # In production, this would verify against stored email code
        # For now, accept any 6-digit code for testing
        return len(code) == 6 and code.isdigit()
    
    def _verify_sms_code(self, user: EnterpriseUser, code: str) -> bool:
        """Verify SMS code"""
        # In production, this would verify against stored SMS code
        return len(code) == 6 and code.isdigit()
    
    def _send_email_code(self, user: EnterpriseUser) -> None:
        """Send verification code via email"""
        # In production, generate and store code, then send via email
        pass
    
    # ─────────────────────────────────────────────────────────────
    # Token Generation
    # ─────────────────────────────────────────────────────────────
    
    def _generate_access_token(self, user: EnterpriseUser, session_id: str) -> Tuple[str, int]:
        """Generate JWT access token"""
        import jwt
        
        expires = datetime.now(timezone.utc) + timedelta(seconds=self._access_token_expire)
        payload = {
            "sub": user.user_id,
            "email": user.email,
            "session_id": session_id,
            "type": "access",
            "exp": expires,
            "iat": datetime.now(timezone.utc),
        }
        
        token = jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)
        return token, self._access_token_expire
    
    def _generate_refresh_token(self, user: EnterpriseUser, session_id: str) -> str:
        """Generate refresh token"""
        token = secrets.token_urlsafe(64)
        self._refresh_tokens[token] = {
            "user_id": user.user_id,
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=self._refresh_token_expire)).isoformat(),
        }
        return token
    
    def _verify_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        import jwt
        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=[self._jwt_algorithm])
            return payload
        except jwt.PyJWTError:
            return None
    
    # ─────────────────────────────────────────────────────────────
    # API Key Management
    # ─────────────────────────────────────────────────────────────
    
    def create_api_key(
        self,
        user_id: str,
        name: str,
        scopes: Optional[List[str]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Create API key for user"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        api_key = f"sp_{secrets.token_urlsafe(32)}"
        key_data = {
            "key_id": secrets.token_urlsafe(16),
            "user_id": user_id,
            "name": name,
            "key": api_key,
            "scopes": scopes or ["read"],
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used": None,
        }
        
        self._api_keys[api_key] = key_data
        
        self._audit.log(
            event_type=AuditEventType.API_KEY_CREATED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            description=f"API key created: {name}",
        )
        
        return api_key, key_data
    
    def revoke_api_key(self, api_key: str, user_id: str) -> bool:
        """Revoke API key"""
        key_data = self._api_keys.get(api_key)
        if not key_data or key_data["user_id"] != user_id:
            return False
        
        key_data["active"] = False
        
        self._audit.log(
            event_type=AuditEventType.API_KEY_REVOKED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            description=f"API key revoked: {key_data['name']}",
        )
        
        return True
    
    def get_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all API keys for user"""
        return [
            {
                "key_id": k["key_id"],
                "name": k["name"],
                "scopes": k["scopes"],
                "active": k["active"],
                "created_at": k["created_at"],
                "last_used": k["last_used"],
            }
            for k in self._api_keys.values()
            if k["user_id"] == user_id
        ]
