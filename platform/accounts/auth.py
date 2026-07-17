import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DERIV_OAUTH_BASE = "https://oauth.deriv.com/oauth2/authorize"
DERIV_WS_BASE = "wss://ws.binaryws.com/websockets/v3"
DEFAULT_APP_ID = "1089"
TOKEN_EXPIRY_BUFFER = 300


@dataclass
class AuthResult:
    """Result of an authentication attempt."""
    success: bool
    token: Optional[str] = None
    login_id: Optional[str] = None
    email: Optional[str] = None
    currency: Optional[str] = None
    is_demo: bool = False
    scopes: List[str] = field(default_factory=list)
    expiry: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "token": self.token,
            "login_id": self.login_id,
            "email": self.email,
            "currency": self.currency,
            "is_demo": self.is_demo,
            "scopes": self.scopes,
            "expiry": self.expiry,
        }


@dataclass
class TokenInfo:
    """Internal representation of a stored token with metadata."""
    token: str
    login_id: str
    email: str
    currency: str
    is_demo: bool
    scopes: List[str]
    issued_at: int
    expiry: int

    @property
    def is_expired(self) -> bool:
        return time.time() > (self.expiry - TOKEN_EXPIRY_BUFFER)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token": self.token,
            "login_id": self.login_id,
            "email": self.email,
            "currency": self.currency,
            "is_demo": self.is_demo,
            "scopes": self.scopes,
            "issued_at": self.issued_at,
            "expiry": self.expiry,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenInfo":
        return cls(
            token=data["token"],
            login_id=data["login_id"],
            email=data["email"],
            currency=data["currency"],
            is_demo=data["is_demo"],
            scopes=data.get("scopes", []),
            issued_at=data.get("issued_at", 0),
            expiry=data.get("expiry", 0),
        )


class DerivAuthManager:
    """Manages Deriv OAuth authentication, token lifecycle, and session persistence.

    Uses the official Deriv OAuth 2.0 flow:
      1. Redirect user to the OAuth authorize URL.
      2. User grants permission, Deriv redirects back with a token.
      3. Exchange / validate the token via the WebSocket ``authorize`` call.
      4. Optionally persist sessions to disk with joblib.
    """

    def __init__(self, app_id: str = DEFAULT_APP_ID) -> None:
        self.app_id = app_id or os.getenv("DERIV_APP_ID", DEFAULT_APP_ID)
        self.oauth_url = f"{DERIV_OAUTH_BASE}?app_id={self.app_id}"
        self._token_info: Optional[TokenInfo] = None
        self._connection = None
        self._connected = False
        logger.debug("DerivAuthManager initialised with app_id=%s", self.app_id)

    # ------------------------------------------------------------------
    # OAuth helpers
    # ------------------------------------------------------------------

    def get_auth_url(self) -> str:
        """Return the full Deriv OAuth URL the user should visit."""
        return self.oauth_url

    def handle_callback(self, token: str) -> AuthResult:
        """Process an OAuth callback token (synchronous validation wrapper).

        Validates the token locally, then attempts a quick WebSocket
        ``authorize`` call to fetch the full account profile.  When the
        event-loop is not running (e.g. CLI callback handler) the
        synchronous ``_validate_token_sync`` path is used.
        """
        logger.info("Handling OAuth callback token (len=%d)", len(token))
        try:
            result = _validate_token_sync(token, self.app_id)
        except Exception as exc:
            logger.error("Token validation failed: %s", exc)
            return AuthResult(success=False)

        if result.success:
            self._token_info = TokenInfo(
                token=token,
                login_id=result.login_id or "",
                email=result.email or "",
                currency=result.currency or "USD",
                is_demo=result.is_demo,
                scopes=result.scopes,
                issued_at=int(time.time()),
                expiry=result.expiry or 0,
            )
            logger.info(
                "Authenticated as %s (demo=%s)",
                self._token_info.login_id,
                self._token_info.is_demo,
            )
        return result

    def authorize(self, api_token: str) -> AuthResult:
        """Directly authorise with a pre-existing API token.

        This is the most common path when the user already has a token
        (e.g. from the Deriv dashboard or a previous session).
        """
        logger.info("Authorising with provided token (len=%d)", len(api_token))
        try:
            result = _validate_token_sync(api_token, self.app_id)
        except Exception as exc:
            logger.error("Direct authorisation failed: %s", exc)
            return AuthResult(success=False)

        if result.success:
            self._token_info = TokenInfo(
                token=api_token,
                login_id=result.login_id or "",
                email=result.email or "",
                currency=result.currency or "USD",
                is_demo=result.is_demo,
                scopes=result.scopes,
                issued_at=int(time.time()),
                expiry=result.expiry or 0,
            )
            logger.info("Direct auth succeeded for %s", self._token_info.login_id)
        return result

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def refresh_token(self) -> bool:
        """Refresh an expired token.

        Deriv refresh tokens are obtained by re-authorising via the
        original ``api_token``.  If the stored token is still valid we
        simply return ``True`` without hitting the network.
        """
        if self._token_info is None:
            logger.warning("No token to refresh")
            return False

        if not self._token_info.is_expired:
            logger.debug("Token still valid, no refresh needed")
            return True

        logger.info("Refreshing token for %s", self._token_info.login_id)
        result = _validate_token_sync(self._token_info.token, self.app_id)
        if result.success and result.token:
            self._token_info.token = result.token
            self._token_info.expiry = result.expiry or 0
            self._token_info.issued_at = int(time.time())
            logger.info("Token refreshed successfully")
            return True

        logger.warning("Token refresh failed")
        return False

    def is_authenticated(self) -> bool:
        """Return ``True`` if a valid (non-expired) token is held."""
        if self._token_info is None:
            return False
        if self._token_info.is_expired:
            logger.debug("Token expired for %s", self._token_info.login_id)
            return False
        return True

    def get_token(self) -> Optional[str]:
        """Return the raw API token or ``None``."""
        if self._token_info is None:
            return None
        if self._token_info.is_expired:
            return None
        return self._token_info.token

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Return cached account info from the last successful auth."""
        if self._token_info is None:
            return None
        return self._token_info.to_dict()

    def logout(self) -> None:
        """Clear the current token and disconnect."""
        logger.info("Logging out")
        self._token_info = None
        self._connected = False
        if self._connection is not None:
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                loop.create_task(_safe_close(self._connection))
            except RuntimeError:
                pass
            self._connection = None

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def save_session(self, path: str) -> bool:
        """Persist the current session to *path* using joblib."""
        if self._token_info is None:
            logger.warning("No session to save")
            return False
        try:
            import joblib
            session_data = {
                "app_id": self.app_id,
                "token_info": self._token_info.to_dict(),
            }
            joblib.dump(session_data, path)
            logger.info("Session saved to %s", path)
            return True
        except Exception as exc:
            logger.error("Failed to save session: %s", exc)
            return False

    def load_session(self, path: str) -> bool:
        """Restore a previously saved session from *path*."""
        try:
            import joblib
            session_data = joblib.load(path)
            self.app_id = session_data.get("app_id", self.app_id)
            self._token_info = TokenInfo.from_dict(session_data["token_info"])
            logger.info(
                "Session loaded from %s (login_id=%s)",
                path,
                self._token_info.login_id,
            )
            return not self._token_info.is_expired
        except FileNotFoundError:
            logger.warning("Session file not found: %s", path)
            return False
        except Exception as exc:
            logger.error("Failed to load session: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def get_scopes(self) -> List[str]:
        """Return the scopes from the current token."""
        if self._token_info is None:
            return []
        return list(self._token_info.scopes)

    def get_login_id(self) -> Optional[str]:
        if self._token_info is None:
            return None
        return self._token_info.login_id

    def is_demo_account(self) -> bool:
        if self._token_info is None:
            return True
        return self._token_info.is_demo


# ======================================================================
# Module-level helpers (synchronous WebSocket validation)
# ======================================================================


def _validate_token_sync(token: str, app_id: str) -> AuthResult:
    """Validate *token* by opening a WebSocket ``authorize`` call.

    This is a **blocking** helper intended for CLI / startup flows.
    For async contexts prefer the ``AccountCenter.connect`` path.
    """
    try:
        import websockets
        import asyncio

        url = f"{DERIV_WS_BASE}?app_id={app_id}"
        loop: Optional[asyncio.AbstractEventLoop] = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            return _validate_token_threaded(token, app_id)

        return asyncio.get_event_loop().run_until_complete(
            _validate_token_async(token, url)
        )
    except Exception as exc:
        logger.error("_validate_token_sync error: %s", exc)
        return AuthResult(success=False)


def _validate_token_threaded(token: str, app_id: str) -> AuthResult:
    """Run async validation in a new thread when an event-loop is active."""
    import threading

    result_holder: List[AuthResult] = [AuthResult(success=False)]

    def _worker() -> None:
        try:
            import asyncio
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            url = f"{DERIV_WS_BASE}?app_id={app_id}"
            result_holder[0] = new_loop.run_until_complete(
                _validate_token_async(token, url)
            )
            new_loop.close()
        except Exception as exc:
            logger.error("Threaded validation failed: %s", exc)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=15.0)
    if t.is_alive():
        logger.error("Token validation thread timed out")
    return result_holder[0]


async def _validate_token_async(token: str, url: str) -> AuthResult:
    """Open a WebSocket, send ``authorize``, and parse the response."""
    import websockets

    try:
        ws = await asyncio.wait_for(websockets.connect(url), timeout=10.0)
        try:
            payload = json.dumps({"authorize": token, "req_id": 1})
            await ws.send(payload)

            raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
            data: Dict[str, Any] = json.loads(raw)

            if "error" in data:
                msg = data["error"].get("message", "Unknown error")
                logger.error("Authorize error: %s", msg)
                return AuthResult(success=False)

            auth = data.get("authorize", {})
            scopes_raw = auth.get("scope", "")
            scopes = [s.strip() for s in scopes_raw.split(",") if s.strip()]
            login_id = auth.get("loginid", "")
            is_demo = login_id.startswith("VR") or auth.get("is_virtual", 0) == 1

            return AuthResult(
                success=True,
                token=token,
                login_id=login_id,
                email=auth.get("email", ""),
                currency=auth.get("currency", "USD"),
                is_demo=is_demo,
                scopes=scopes,
                expiry=auth.get("expiry", 0),
            )
        finally:
            await ws.close()
    except Exception as exc:
        logger.error("WebSocket validation failed: %s", exc)
        return AuthResult(success=False)


async def _safe_close(ws: Any) -> None:
    """Best-effort WebSocket close."""
    try:
        await ws.close()
    except Exception:
        pass
