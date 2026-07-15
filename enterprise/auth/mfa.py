"""
MFA Service

Multi-factor authentication service with:
- TOTP (Time-based One-Time Password)
- Email-based codes
- SMS codes (stub)
- Recovery codes
- WebAuthn support (stub)
"""

import secrets
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pyotp
import qrcode
import base64
from io import BytesIO

from enterprise.models.user import EnterpriseUser, MFAType


class MFAServiceError(Exception):
    """MFA service error"""
    pass


class MFAService:
    """
    Multi-factor authentication service.
    
    Supports:
    - TOTP (Google Authenticator, Authy, etc.)
    - Email verification codes
    - SMS codes (requires external provider)
    - Recovery codes
    """
    
    def __init__(
        self,
        code_length: int = 6,
        code_ttl_seconds: int = 300,  # 5 minutes
        max_attempts: int = 3,
        recovery_code_count: int = 10,
    ):
        self._code_length = code_length
        self._code_ttl = code_ttl_seconds
        self._max_attempts = max_attempts
        self._recovery_code_count = recovery_code_count
        
        # Code storage: user_id -> {code: code, expires_at: datetime, attempts: int}
        self._pending_codes: Dict[str, Dict[str, Any]] = {}
        
        # Email provider (stub for external integration)
        self._email_provider = None
    
    def generate_totp_secret(self) -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()
    
    def get_totp_uri(self, secret: str, email: str, issuer: str = "SmartPip") -> str:
        """
        Get TOTP provisioning URI for QR code generation.
        
        Format: otpauth://totp/{issuer}:{email}?secret={secret}&issuer={issuer}
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)
    
    def generate_totp_qr(self, secret: str, email: str, issuer: str = "SmartPip") -> str:
        """
        Generate QR code image as base64 string.
        """
        uri = self.get_totp_uri(secret, email, issuer)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    def verify_totp(self, secret: str, code: str, valid_window: int = 1) -> bool:
        """
        Verify a TOTP code.
        
        Args:
            secret: TOTP secret
            code: User-provided code
            valid_window: Number of intervals before/after to accept
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=valid_window)
    
    def generate_email_code(self, user_id: str, email: str) -> str:
        """
        Generate and send email verification code.
        Returns the code (for testing) or sends via email.
        """
        code = "".join(secrets.choice("0123456789") for _ in range(self._code_length))
        
        # Store code
        self._pending_codes[user_id] = {
            "code": code,
            "method": MFAType.EMAIL,
            "expires_at": datetime.utcnow() + timedelta(seconds=self._code_ttl),
            "attempts": 0,
            "destination": email,
        }
        
        # Send email (in production, this would use an email service)
        self._send_email(email, f"Your verification code is: {code}")
        
        return code  # Return for testing; remove in production
    
    def generate_sms_code(self, user_id: str, phone: str) -> str:
        """
        Generate and send SMS verification code.
        Returns the code (for testing) or sends via SMS.
        """
        code = "".join(secrets.choice("0123456789") for _ in range(self._code_length))
        
        # Store code
        self._pending_codes[user_id] = {
            "code": code,
            "method": MFAType.SMS,
            "expires_at": datetime.utcnow() + timedelta(seconds=self._code_ttl),
            "attempts": 0,
            "destination": phone,
        }
        
        # Send SMS (in production, this would use Twilio or similar)
        self._send_sms(phone, f"Your verification code is: {code}")
        
        return code  # Return for testing; remove in production
    
    def verify_email_code(self, user_id: str, code: str) -> Tuple[bool, Optional[str]]:
        """
        Verify email code.
        Returns (success, error_message)
        """
        return self._verify_code(user_id, code, MFAType.EMAIL)
    
    def verify_sms_code(self, user_id: str, code: str) -> Tuple[bool, Optional[str]]:
        """
        Verify SMS code.
        Returns (success, error_message)
        """
        return self._verify_code(user_id, code, MFAType.SMS)
    
    def _verify_code(
        self,
        user_id: str,
        code: str,
        expected_method: MFAType,
    ) -> Tuple[bool, Optional[str]]:
        """Internal code verification"""
        stored = self._pending_codes.get(user_id)
        
        if not stored:
            return False, "No pending code"
        
        # Check method
        if stored["method"] != expected_method:
            return False, "Invalid code method"
        
        # Check expiration
        if datetime.utcnow() > stored["expires_at"]:
            del self._pending_codes[user_id]
            return False, "Code has expired"
        
        # Check attempts
        if stored["attempts"] >= self._max_attempts:
            del self._pending_codes[user_id]
            return False, "Too many attempts"
        
        # Verify code
        stored["attempts"] += 1
        
        if secrets.compare_digest(stored["code"], code):
            del self._pending_codes[user_id]
            return True, None
        
        return False, "Invalid code"
    
    def clear_pending_code(self, user_id: str) -> None:
        """Clear pending code for user"""
        self._pending_codes.pop(user_id, None)
    
    def has_pending_code(self, user_id: str) -> bool:
        """Check if user has pending code"""
        stored = self._pending_codes.get(user_id)
        if not stored:
            return False
        
        if datetime.utcnow() > stored["expires_at"]:
            del self._pending_codes[user_id]
            return False
        
        return True
    
    def get_pending_code_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get info about pending code (without the actual code)"""
        stored = self._pending_codes.get(user_id)
        if not stored:
            return None
        
        if datetime.utcnow() > stored["expires_at"]:
            return None
        
        return {
            "method": stored["method"].value,
            "expires_at": stored["expires_at"].isoformat(),
            "attempts_remaining": self._max_attempts - stored["attempts"],
            "masked_destination": self._mask_destination(stored["destination"]),
        }
    
    @staticmethod
    def _mask_destination(destination: str) -> str:
        """Mask email or phone number"""
        if "@" in destination:
            # Email
            parts = destination.split("@")
            return f"{parts[0][:2]}***@{parts[1]}"
        else:
            # Phone
            return f"***-***-{destination[-4:]}"
    
    def _send_email(self, to: str, body: str) -> None:
        """Send email (stub for external integration)"""
        # In production, integrate with SendGrid, AWS SES, etc.
        pass
    
    def _send_sms(self, to: str, body: str) -> None:
        """Send SMS (stub for external integration)"""
        # In production, integrate with Twilio, AWS SNS, etc.
        pass


class TOTPProvider:
    """TOTP-specific provider for advanced TOTP management"""
    
    def __init__(self, issuer: str = "SmartPip"):
        self._issuer = issuer
    
    def create_secret(self) -> str:
        """Create a new TOTP secret"""
        return pyotp.random_base32()
    
    def get_provisioning_uri(self, secret: str, email: str) -> str:
        """Get provisioning URI for QR code"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=self._issuer)
    
    def verify(self, secret: str, token: str, valid_window: int = 1) -> bool:
        """Verify a token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=valid_window)
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup/recovery codes"""
        return [secrets.token_urlsafe(8) for _ in range(count)]


class RecoveryCodeManager:
    """
    Manages recovery codes for MFA.
    
    Features:
    - Code generation
    - Code validation (one-time use)
    - Code regeneration when low
    """
    
    def __init__(self, code_length: int = 8, low_threshold: int = 3):
        self._code_length = code_length
        self._low_threshold = low_threshold
    
    def generate_codes(self, count: int = 10) -> List[str]:
        """Generate a set of recovery codes"""
        return [self._generate_code() for _ in range(count)]
    
    def _generate_code(self) -> str:
        """Generate a single recovery code"""
        return secrets.token_urlsafe(self._code_length)
    
    def verify_code(self, codes: List[str], provided_code: str) -> Tuple[bool, List[str]]:
        """
        Verify a recovery code.
        Returns (is_valid, remaining_codes)
        """
        # Normalize codes
        normalized_provided = provided_code.lower().replace("-", "").replace(" ", "")
        
        for i, code in enumerate(codes):
            normalized_code = code.lower().replace("-", "").replace(" ", "")
            if secrets.compare_digest(normalized_code, normalized_provided):
                # Remove used code
                remaining = codes[:i] + codes[i+1:]
                return True, remaining
        
        return False, codes
    
    def should_regenerate(self, codes: List[str]) -> bool:
        """Check if codes should be regenerated (running low)"""
        return len(codes) <= self._low_threshold
    
    def regenerate_if_needed(self, codes: List[str]) -> Tuple[List[str], bool]:
        """
        Regenerate codes if running low.
        Returns (codes, was_regenerated)
        """
        if self.should_regenerate(codes):
            return self.generate_codes(), True
        return codes, False


class EmailProvider:
    """
    Email-based MFA provider.
    
    Handles sending and verifying email codes.
    """
    
    def __init__(
        self,
        code_length: int = 6,
        ttl_seconds: int = 300,
        max_attempts: int = 3,
    ):
        self._code_length = code_length
        self._ttl = ttl_seconds
        self._max_attempts = max_attempts
        self._codes: Dict[str, Dict[str, Any]] = {}
    
    def send_code(self, user_id: str, email: str, template: str = "mfa_code") -> str:
        """
        Generate and send verification code.
        Returns the code (for testing/debugging).
        """
        code = "".join(secrets.choice("0123456789") for _ in range(self._code_length))
        
        self._codes[user_id] = {
            "code": code,
            "email": email,
            "expires_at": datetime.utcnow() + timedelta(seconds=self._ttl),
            "attempts": 0,
        }
        
        # Send email
        self._send_email(
            to=email,
            subject="Your SmartPip verification code",
            body=f"Your verification code is: {code}\n\nThis code expires in 5 minutes.",
        )
        
        return code
    
    def verify(self, user_id: str, code: str) -> Tuple[bool, Optional[str]]:
        """
        Verify code for user.
        Returns (success, error_message)
        """
        stored = self._codes.get(user_id)
        
        if not stored:
            return False, "No code requested"
        
        if datetime.utcnow() > stored["expires_at"]:
            del self._codes[user_id]
            return False, "Code expired"
        
        if stored["attempts"] >= self._max_attempts:
            del self._codes[user_id]
            return False, "Too many attempts"
        
        stored["attempts"] += 1
        
        if secrets.compare_digest(stored["code"], code):
            del self._codes[user_id]
            return True, None
        
        return False, "Invalid code"
    
    def _send_email(self, to: str, subject: str, body: str) -> None:
        """Send email (implement with email service)"""
        # Stub for external email service integration
        pass
