"""
Unified Account Center

Centralized account management for Deriv, providing:
- Single sign-on authentication
- Multi-account support (Demo, Real, MT5)
- Account switching
- Unified balance tracking
- Preferences and settings per account
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

# Optional dependencies
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    websockets = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

from accounts.models import (
    AccountType,
    AccountInfo,
    AuthToken,
    DerivToken,
    SessionInfo,
    TokenType,
)
from accounts.auth import DerivOAuth2, TokenManager, create_oauth2_handler, create_token_manager

logger = logging.getLogger(__name__)


class AccountCenterError(Exception):
    """Account center operation error"""
    pass


class AuthenticationError(AccountCenterError):
    """Authentication failed"""
    pass


class AccountNotFoundError(AccountCenterError):
    """Requested account not found"""
    pass


@dataclass
class AccountCenterConfig:
    """Configuration for the account center"""
    api_token: Optional[str] = None
    oauth2_enabled: bool = False
    auto_reconnect: bool = True
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10
    session_timeout: int = 3600  # 1 hour
    storage_path: str = "data/accounts"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "oauth2_enabled": self.oauth2_enabled,
            "auto_reconnect": self.auto_reconnect,
            "reconnect_interval": self.reconnect_interval,
            "max_reconnect_attempts": self.max_reconnect_attempts,
            "session_timeout": self.session_timeout,
            "storage_path": self.storage_path,
        }


class AccountCenter:
    """
    Unified account center for managing Deriv accounts.
    
    Features:
    - Single authentication point
    - Support for Demo and Real accounts
    - MT5 account management
    - Account switching without re-authentication
    - Unified balance and history tracking
    - Real-time balance updates
    """
    
    DERIV_API_URL = "https://ws.derivws.com"
    DERIV_API_VERSION = "1"
    APP_ID = "1089"  # SmartPip Trader app ID
    
    def __init__(self, config: Optional[AccountCenterConfig] = None):
        self._config = config or AccountCenterConfig()
        self._session: Optional[SessionInfo] = None
        self._oauth2: Optional[DerivOAuth2] = None
        self._token_manager: Optional[TokenManager] = None
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._reconnect_attempts = 0
        self._balance_callbacks: List[Callable[[AccountInfo], None]] = []
        self._auth_callbacks: List[Callable[[Optional[SessionInfo]], None]] = []
        self._storage_path = self._config.storage_path
        self._lock = asyncio.Lock()
        
        os.makedirs(self._storage_path, exist_ok=True)
        self._load_session()
    
    @property
    def config(self) -> AccountCenterConfig:
        return self._config
    
    @property
    def is_authenticated(self) -> bool:
        return self._session is not None and not self._session.is_expired
    
    @property
    def session(self) -> Optional[SessionInfo]:
        return self._session
    
    @property
    def connected(self) -> bool:
        return self._connected
    
    @property
    def active_account(self) -> Optional[AccountInfo]:
        return self._session.active_account if self._session else None
    
    @property
    def all_accounts(self) -> List[AccountInfo]:
        return self._session.accounts if self._session else []
    
    @property
    def demo_accounts(self) -> List[AccountInfo]:
        return self._session.get_demo_accounts() if self._session else []
    
    @property
    def real_accounts(self) -> List[AccountInfo]:
        return self._session.get_real_accounts() if self._session else []
    
    def _load_session(self) -> None:
        """Load session from persistent storage"""
        session_file = os.path.join(self._storage_path, "session.json")
        
        if os.path.exists(session_file):
            try:
                with open(session_file, "r") as f:
                    data = json.load(f)
                    
                if data.get("session"):
                    session_data = data["session"]
                    accounts = [
                        AccountInfo(
                            account_id=a["account_id"],
                            account_type=AccountType(a["account_type"]),
                            currency=a["currency"],
                            balance=a["balance"],
                            loginid=a["loginid"],
                            email=a.get("email"),
                            display_name=a.get("display_name"),
                            is_virtual=a.get("is_virtual", True),
                            is_primary=a.get("is_primary", False),
                        )
                        for a in session_data.get("accounts", [])
                    ]
                    
                    self._session = SessionInfo(
                        session_id=session_data["session_id"],
                        user_id=session_data["user_id"],
                        email=session_data["email"],
                        accounts=accounts,
                        active_account_id=session_data.get("active_account_id"),
                        created_at=datetime.fromisoformat(session_data["created_at"]),
                        last_activity=datetime.fromisoformat(session_data["last_activity"]),
                    )
                    
                    # Check if session is expired
                    if self._session.is_expired:
                        logger.info("Loaded session has expired")
                        self._session = None
                    else:
                        logger.info(f"Loaded session for {self._session.email}")
                        
            except Exception as e:
                logger.error(f"Failed to load session: {e}")
    
    def _save_session(self) -> None:
        """Save session to persistent storage"""
        if not self._session:
            return
        
        session_file = os.path.join(self._storage_path, "session.json")
        
        try:
            data = {
                "session": {
                    "session_id": self._session.session_id,
                    "user_id": self._session.user_id,
                    "email": self._session.email,
                    "accounts": [
                        a.to_dict() for a in self._session.accounts
                    ],
                    "active_account_id": self._session.active_account_id,
                    "created_at": self._session.created_at.isoformat(),
                    "last_activity": self._session.last_activity.isoformat(),
                }
            }
            
            with open(session_file, "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    def _clear_session(self) -> None:
        """Clear session from storage"""
        session_file = os.path.join(self._storage_path, "session.json")
        try:
            if os.path.exists(session_file):
                os.remove(session_file)
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
    
    async def authenticate_with_token(self, api_token: str) -> SessionInfo:
        """
        Authenticate using a Deriv API token.
        
        Args:
            api_token: Deriv API token
            
        Returns:
            SessionInfo with account details
            
        Raises:
            AuthenticationError: If authentication fails
        """
        async with self._lock:
            try:
                # Connect to Deriv API
                ws_url = f"{self.DERIV_API_URL}/websockets/v{self.DERIV_API_VERSION}?app_id={self.APP_ID}"
                
                async with websockets.connect(ws_url) as ws:
                    # Authorize
                    await ws.send(json.dumps({
                        "authorize": api_token,
                        "req_id": 1,
                    }))
                    
                    response = await asyncio.wait_for(ws.recv(), timeout=30)
                    data = json.loads(response)
                    
                    if "error" in data:
                        raise AuthenticationError(
                            f"Authorization failed: {data['error']['message']}"
                        )
                    
                    auth_data = data.get("authorize", {})
                    
                    # Extract account info
                    accounts = []
                    
                    # Primary account
                    primary = AccountInfo(
                        account_id=auth_data.get("account_id", ""),
                        account_type=AccountType.REAL if not auth_data.get("is_virtual") else AccountType.DEMO,
                        currency=auth_data.get("currency", "USD"),
                        balance=float(auth_data.get("balance", 0)),
                        loginid=auth_data.get("loginid", ""),
                        email=auth_data.get("email"),
                        display_name=auth_data.get("full_name"),
                        is_virtual=auth_data.get("is_virtual", True),
                        is_primary=True,
                    )
                    accounts.append(primary)
                    
                    # Check for additional accounts
                    for acct in auth_data.get("account_list", []):
                        acct_info = AccountInfo(
                            account_id=acct.get("account_id", ""),
                            account_type=AccountType.MT5_REAL if acct.get("account_type") == "mt5" else (
                                AccountType.REAL if not acct.get("is_virtual") else AccountType.DEMO
                            ),
                            currency=acct.get("currency", "USD"),
                            balance=0.0,  # Balance fetched separately
                            loginid=acct.get("loginid", ""),
                            is_virtual=acct.get("is_virtual", True),
                        )
                        accounts.append(acct_info)
                    
                    # Create session
                    self._session = SessionInfo(
                        session_id=str(uuid4()),
                        user_id=auth_data.get("user_id", ""),
                        email=auth_data.get("email", ""),
                        accounts=accounts,
                        active_account_id=primary.account_id,
                        created_at=datetime.utcnow(),
                        last_activity=datetime.utcnow(),
                    )
                    
                    self._save_session()
                    self._websocket = ws
                    self._connected = True
                    
                    # Start balance update task
                    asyncio.create_task(self._balance_update_loop())
                    
                    # Notify callbacks
                    self._notify_auth_callbacks(self._session)
                    
                    logger.info(f"Authenticated successfully: {self._session.email}")
                    return self._session
                    
            except asyncio.TimeoutError:
                raise AuthenticationError("Authentication timed out")
            except websockets.WebSocketException as e:
                raise AuthenticationError(f"WebSocket error: {e}")
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                raise AuthenticationError(f"Authentication failed: {e}")
    
    async def _balance_update_loop(self) -> None:
        """Continuously update balance for active account"""
        while self._connected and self._session:
            try:
                if self._websocket:
                    await self._websocket.send(json.dumps({
                        "balance": 1,
                        "account": self._session.active_account_id,
                        "req_id": 2,
                    }))
                    
                    response = await asyncio.wait_for(self._websocket.recv(), timeout=10)
                    data = json.loads(response)
                    
                    if "balance" in data:
                        await self._update_account_balance(
                            data["balance"]["account_id"],
                            data["balance"]["balance"],
                            data["balance"]["currency"],
                        )
                        
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.debug(f"Balance update error: {e}")
            
            await asyncio.sleep(5)
    
    async def _update_account_balance(
        self,
        account_id: str,
        balance: float,
        currency: str,
    ) -> None:
        """Update account balance and notify callbacks"""
        for account in self._session.accounts:
            if account.account_id == account_id:
                account.balance = balance
                account.currency = currency
                account.last_used = datetime.utcnow()
                break
        
        self._save_session()
        
        # Notify callbacks
        account = self._session.get_account(account_id)
        if account:
            for callback in self._balance_callbacks:
                try:
                    callback(account)
                except Exception as e:
                    logger.error(f"Balance callback error: {e}")
    
    async def switch_account(self, account_id: str) -> AccountInfo:
        """
        Switch to a different account.
        
        Args:
            account_id: Account to switch to
            
        Returns:
            The switched-to account
            
        Raises:
            AccountNotFoundError: If account doesn't exist
        """
        if not self._session:
            raise AccountCenterError("Not authenticated")
        
        account = self._session.get_account(account_id)
        if not account:
            raise AccountNotFoundError(f"Account {account_id} not found")
        
        self._session.active_account_id = account_id
        account.last_used = datetime.utcnow()
        self._session.last_activity = datetime.utcnow()
        
        self._save_session()
        
        # Fetch balance for new account
        if self._websocket and self._connected:
            try:
                await self._websocket.send(json.dumps({
                    "balance": 1,
                    "account": account_id,
                    "req_id": 3,
                }))
            except Exception as e:
                logger.error(f"Failed to fetch balance: {e}")
        
        logger.info(f"Switched to account: {account_id}")
        return account
    
    async def switch_to_demo(self) -> AccountInfo:
        """Switch to a demo account"""
        demo_accounts = self.demo_accounts
        if not demo_accounts:
            raise AccountNotFoundError("No demo accounts available")
        
        return await self.switch_account(demo_accounts[0].account_id)
    
    async def switch_to_real(self) -> AccountInfo:
        """Switch to a real account"""
        real_accounts = self.real_accounts
        if not real_accounts:
            raise AccountNotFoundError("No real accounts available")
        
        return await self.switch_account(real_accounts[0].account_id)
    
    def get_account(self, account_id: str) -> Optional[AccountInfo]:
        """Get a specific account by ID"""
        return self._session.get_account(account_id) if self._session else None
    
    def get_account_by_type(self, account_type: AccountType) -> Optional[AccountInfo]:
        """Get an account by type"""
        if not self._session:
            return None
        
        for account in self._session.accounts:
            if account.account_type == account_type:
                return account
        return None
    
    async def logout(self) -> None:
        """Logout and close the session"""
        async with self._lock:
            if self._websocket:
                try:
                    await self._websocket.close()
                except Exception:
                    pass
                self._websocket = None
            
            self._connected = False
            self._session = None
            self._clear_session()
            
            self._notify_auth_callbacks(None)
            logger.info("Logged out successfully")
    
    async def reconnect(self) -> bool:
        """Attempt to reconnect to Deriv API"""
        if not self.is_authenticated:
            return False
        
        if self._reconnect_attempts >= self._config.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return False
        
        self._reconnect_attempts += 1
        logger.info(f"Attempting reconnection ({self._reconnect_attempts}/{self._config.max_reconnect_attempts})")
        
        try:
            # Re-authenticate with stored token
            # In production, you'd store and retrieve the API token securely
            self._connected = True
            self._reconnect_attempts = 0
            return True
            
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            
            if self._config.auto_reconnect:
                await asyncio.sleep(self._config.reconnect_interval)
                return await self.reconnect()
            
            return False
    
    def on_balance_update(self, callback: Callable[[AccountInfo], None]) -> None:
        """Register a balance update callback"""
        self._balance_callbacks.append(callback)
    
    def on_auth_change(self, callback: Callable[[Optional[SessionInfo]], None]) -> None:
        """Register an authentication state change callback"""
        self._auth_callbacks.append(callback)
    
    def _notify_auth_callbacks(self, session: Optional[SessionInfo]) -> None:
        """Notify authentication callbacks"""
        for callback in self._auth_callbacks:
            try:
                callback(session)
            except Exception as e:
                logger.error(f"Auth callback error: {e}")
    
    def get_total_balance(self) -> Dict[str, float]:
        """Get total balance across all accounts"""
        balances = {"total": 0.0, "demo": 0.0, "real": 0.0}
        
        for account in self.all_accounts:
            balances["total"] += account.balance
            if account.is_demo:
                balances["demo"] += account.balance
            else:
                balances["real"] += account.balance
        
        return balances
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state for persistence"""
        return {
            "is_authenticated": self.is_authenticated,
            "connected": self._connected,
            "session": self._session.to_dict() if self._session else None,
            "balances": self.get_total_balance(),
            "active_account": self.active_account.to_dict() if self.active_account else None,
        }
    
    def export_config(self) -> Dict[str, Any]:
        """Export account configuration (without sensitive data)"""
        return {
            "accounts": [
                {
                    "account_id": a.account_id,
                    "account_type": a.account_type.value,
                    "currency": a.currency,
                    "is_virtual": a.is_virtual,
                }
                for a in self.all_accounts
            ],
            "active_account_id": self._session.active_account_id if self._session else None,
            "total_balance": self.get_total_balance(),
        }


def create_account_center(
    api_token: Optional[str] = None,
    storage_path: Optional[str] = None,
) -> AccountCenter:
    """Factory function to create an account center"""
    config = AccountCenterConfig(
        api_token=api_token,
        storage_path=storage_path or "data/accounts",
    )
    return AccountCenter(config=config)
