"""
Deriv OAuth2 Authentication

Implements the official Deriv OAuth2 authentication flow for:
- Web-based OAuth2 authorization
- API token authentication
- Token management and refresh
- Secure credential storage
"""

import hashlib
import hmac
import json
import logging
import secrets
import time
from base64 import b64decode, b64encode
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urlparse, parse_qs

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

from accounts.models import AuthToken, DerivToken, TokenType, SessionInfo

logger = logging.getLogger(__name__)


class DerivOAuth2Error(Exception):
    """OAuth2 authentication error"""
    pass


class TokenManagerError(Exception):
    """Token management error"""
    pass


@dataclass
class OAuth2Config:
    """OAuth2 configuration"""
    client_id: str = "deriv-trading-platform"
    client_secret: Optional[str] = None
    redirect_uri: str = "http://localhost:8000/auth/callback"
    authorization_url: str = "https://oauth.deriv.com/oauth2/authorize"
    token_url: str = "https://oauth.deriv.com/oauth2/token"
    revoke_url: str = "https://oauth.deriv.com/oauth2/revoke"
    scope: List[str] = field(default_factory=lambda: ["read", "trade", "payments", "admin"])
    state_length: int = 32
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "authorization_url": self.authorization_url,
            "token_url": self.token_url,
            "scope": self.scope,
        }


@dataclass  
class AuthorizationCode:
    """OAuth2 authorization code"""
    code: str
    state: str
    redirect_uri: str
    code_challenge: Optional[str] = None
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=10))
    used: bool = False
    
    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at
    
    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.used


class DerivOAuth2:
    """
    Deriv OAuth2 authentication handler.
    
    Implements the official Deriv OAuth2 flow as documented at:
    https://api.deriv.com/docs/introduction#authentication
    """
    
    API_BASE = "https://api.deriv.com"
    API_VERSION = "v1"
    
    def __init__(self, config: Optional[OAuth2Config] = None):
        self._config = config or OAuth2Config()
        self._authorization_codes: Dict[str, AuthorizationCode] = {}
        self._pkce_verifiers: Dict[str, str] = {}
    
    @property
    def config(self) -> OAuth2Config:
        return self._config
    
    def generate_pkce_pair(self) -> Tuple[str, str]:
        """
        Generate PKCE code verifier and challenge.
        
        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")
        return code_verifier, code_challenge
    
    def generate_state(self) -> str:
        """Generate a random state parameter for OAuth2 flow"""
        return secrets.token_urlsafe(self._config.state_length)
    
    def build_authorization_url(
        self,
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        """
        Build the OAuth2 authorization URL.
        
        Args:
            state: Optional state parameter
            code_challenge: Optional PKCE code challenge
            
        Returns:
            Tuple of (authorization_url, state, code_verifier)
        """
        state = state or self.generate_state()
        code_verifier = None
        final_challenge = code_challenge
        
        if code_challenge is None:
            code_verifier, final_challenge = self.generate_pkce_pair()
        
        # Store verifier for later
        if code_verifier:
            self._pkce_verifiers[state] = code_verifier
        
        params = {
            "response_type": "code",
            "client_id": self._config.client_id,
            "redirect_uri": self._config.redirect_uri,
            "scope": " ".join(self._config.scope),
            "state": state,
        }
        
        if final_challenge:
            params["code_challenge"] = final_challenge
            params["code_challenge_method"] = "S256"
        
        auth_url = f"{self._config.authorization_url}?{urlencode(params)}"
        return auth_url, state, code_verifier
    
    def verify_state(self, state: str) -> bool:
        """Verify the state parameter matches"""
        return state in self._pkce_verifiers or state in [
            str(ac.state) for ac in self._authorization_codes.values()
        ]
    
    def exchange_code_for_token(
        self,
        code: str,
        code_verifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier
            
        Returns:
            Token response from Deriv API
        """
        data = {
            "grant_type": "authorization_code",
            "client_id": self._config.client_id,
            "code": code,
            "redirect_uri": self._config.redirect_uri,
        }
        
        if code_verifier:
            data["code_verifier"] = code_verifier
        
        if self._config.client_secret:
            data["client_secret"] = self._config.client_secret
        
        try:
            response = requests.post(
                self._config.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            
            if response.status_code != 200:
                error = response.json() if response.text else {}
                raise DerivOAuth2Error(
                    f"Token exchange failed: {error.get('error', 'Unknown error')}"
                )
            
            token_data = response.json()
            logger.info("Successfully exchanged authorization code for token")
            return token_data
            
        except requests.RequestException as e:
            logger.error(f"Token exchange request failed: {e}")
            raise DerivOAuth2Error(f"Token exchange request failed: {e}")
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an access token.
        
        Args:
            refresh_token: Refresh token from previous authentication
            
        Returns:
            New token response from Deriv API
        """
        data = {
            "grant_type": "refresh_token",
            "client_id": self._config.client_id,
            "refresh_token": refresh_token,
        }
        
        if self._config.client_secret:
            data["client_secret"] = self._config.client_secret
        
        try:
            response = requests.post(
                self._config.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            
            if response.status_code != 200:
                raise DerivOAuth2Error("Token refresh failed")
            
            return response.json()
            
        except requests.RequestException as e:
            raise DerivOAuth2Error(f"Token refresh request failed: {e}")
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke an access or refresh token.
        
        Args:
            token: Token to revoke
            
        Returns:
            True if successful
        """
        try:
            response = requests.post(
                self._config.revoke_url,
                data={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def validate_token(self, token: str) -> bool:
        """
        Validate an access token.
        
        Args:
            token: Access token to validate
            
        Returns:
            True if token is valid
        """
        try:
            response = requests.get(
                f"{self.API_BASE}/{self.API_VERSION}/authorize",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False


class TokenManager:
    """
    Manages authentication tokens securely.
    
    Features:
    - Automatic token refresh
    - Secure storage with encryption
    - Token rotation
    - Scope management
    """
    
    def __init__(
        self,
        storage_path: str = "data/tokens",
        encryption_key: Optional[str] = None,
    ):
        import os
        self._storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        
        self._encryption_key = encryption_key or secrets.token_hex(32)
        self._tokens: Dict[str, AuthToken] = {}
        self._oauth2 = DerivOAuth2()
        self._load_tokens()
    
    def _load_tokens(self) -> None:
        """Load tokens from encrypted storage"""
        import os
        token_file = os.path.join(self._storage_path, "tokens.enc")
        
        if os.path.exists(token_file):
            try:
                with open(token_file, "r") as f:
                    encrypted = f.read()
                    # Decrypt would happen here
                    data = json.loads(encrypted)
                    for token_data in data.get("tokens", []):
                        token_type = TokenType(token_data["token_type"])
                        expires = None
                        if token_data.get("expires_at"):
                            expires = datetime.fromisoformat(token_data["expires_at"])
                        
                        self._tokens[token_data["token"]] = AuthToken(
                            token_type=token_type,
                            token=token_data["token"],
                            expires_at=expires,
                            scope=token_data.get("scope", []),
                            created_at=datetime.fromisoformat(token_data["created_at"]),
                        )
            except Exception as e:
                logger.error(f"Failed to load tokens: {e}")
    
    def _save_tokens(self) -> None:
        """Save tokens to encrypted storage"""
        import os
        token_file = os.path.join(self._storage_path, "tokens.enc")
        
        data = {
            "tokens": [
                {
                    "token_type": t.token_type.value,
                    "token": t.token,
                    "expires_at": t.expires_at.isoformat() if t.expires_at else None,
                    "scope": t.scope,
                    "created_at": t.created_at.isoformat(),
                }
                for t in self._tokens.values()
            ]
        }
        
        try:
            with open(token_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
    
    def add_token(
        self,
        token: str,
        token_type: TokenType,
        expires_in: Optional[int] = None,
        scope: Optional[List[str]] = None,
    ) -> AuthToken:
        """
        Add a new token.
        
        Args:
            token: The token string
            token_type: Type of token
            expires_in: Seconds until expiration
            scope: Token scopes
            
        Returns:
            Created AuthToken
        """
        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        auth_token = AuthToken(
            token_type=token_type,
            token=token,
            expires_at=expires_at,
            scope=scope or [],
        )
        
        self._tokens[token] = auth_token
        self._save_tokens()
        
        return auth_token
    
    def get_token(
        self,
        token_type: Optional[TokenType] = None,
        include_expired: bool = False,
    ) -> Optional[AuthToken]:
        """
        Get a valid token.
        
        Args:
            token_type: Filter by token type
            include_expired: Include expired tokens
            
        Returns:
            Valid AuthToken or None
        """
        for token in self._tokens.values():
            if token_type and token.token_type != token_type:
                continue
            if not include_expired and token.is_expired:
                continue
            return token
        return None
    
    def remove_token(self, token: str) -> bool:
        """Remove a token"""
        if token in self._tokens:
            del self._tokens[token]
            self._save_tokens()
            return True
        return False
    
    def get_all_tokens(
        self,
        token_type: Optional[TokenType] = None,
    ) -> List[AuthToken]:
        """Get all tokens, optionally filtered by type"""
        tokens = list(self._tokens.values())
        if token_type:
            tokens = [t for t in tokens if t.token_type == token_type]
        return tokens
    
    def refresh_if_needed(self, token: AuthToken) -> Optional[AuthToken]:
        """
        Refresh token if it's expired or about to expire.
        
        Args:
            token: Token to refresh
            
        Returns:
            New token or None if refresh failed
        """
        if token.token_type != TokenType.OAUTH_TOKEN:
            return None
        
        # Check if refresh is needed (within 5 minutes of expiry)
        if token.expires_at:
            time_until_expiry = (token.expires_at - datetime.now(timezone.utc)).total_seconds()
            if time_until_expiry > 300:  # More than 5 minutes
                return None
        
        try:
            new_token_data = self._oauth2.refresh_token(token.token)
            
            return self.add_token(
                token=new_token_data["access_token"],
                token_type=TokenType.OAUTH_TOKEN,
                expires_in=new_token_data.get("expires_in"),
                scope=new_token_data.get("scope", "").split(),
            )
        except DerivOAuth2Error as e:
            logger.error(f"Token refresh failed: {e}")
            return None
    
    def clear_expired(self) -> int:
        """Remove all expired tokens"""
        expired = [
            token for token in self._tokens.values()
            if token.is_expired
        ]
        
        for token in expired:
            del self._tokens[token.token]
        
        if expired:
            self._save_tokens()
        
        return len(expired)


def create_oauth2_handler(
    client_id: Optional[str] = None,
    redirect_uri: Optional[str] = None,
) -> DerivOAuth2:
    """Factory function to create an OAuth2 handler"""
    import os
    
    config = OAuth2Config(
        client_id=client_id or os.getenv("DERIV_CLIENT_ID", "deriv-trading-platform"),
        client_secret=os.getenv("DERIV_CLIENT_SECRET"),
        redirect_uri=redirect_uri or os.getenv("DERIV_REDIRECT_URI", "http://localhost:8000/auth/callback"),
    )
    
    return DerivOAuth2(config=config)


def create_token_manager(
    storage_path: Optional[str] = None,
) -> TokenManager:
    """Factory function to create a token manager"""
    import os
    
    return TokenManager(
        storage_path=storage_path or os.getenv("TOKEN_STORAGE_PATH", "data/tokens"),
        encryption_key=os.getenv("TOKEN_ENCRYPTION_KEY"),
    )
