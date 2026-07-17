import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from .auth import DerivAuthManager, DERIV_WS_BASE

logger = logging.getLogger(__name__)

_POSITION_POLL_INTERVAL = 5.0
_BALANCE_POLL_INTERVAL = 10.0


@dataclass
class AccountInfo:
    """Information about a single Deriv account."""
    login_id: str
    account_type: str
    currency: str
    balance: float = 0.0
    is_active: bool = False
    pip_value: float = 0.0
    margin: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "login_id": self.login_id,
            "account_type": self.account_type,
            "currency": self.currency,
            "balance": self.balance,
            "is_active": self.is_active,
            "pip_value": self.pip_value,
            "margin": self.margin,
        }


@dataclass
class TradeRecord:
    """One historical trade record."""
    timestamp: str
    symbol: str
    trade_type: str
    entry_price: float
    exit_price: float
    profit: float
    payout: float
    duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "trade_type": self.trade_type,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "profit": self.profit,
            "payout": self.payout,
            "duration": self.duration,
        }


@dataclass
class PortfolioState:
    """Snapshot of the current portfolio."""
    open_positions: List[Dict[str, Any]] = field(default_factory=list)
    total_profit: float = 0.0
    margin_used: float = 0.0
    free_margin: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "open_positions": self.open_positions,
            "total_profit": self.total_profit,
            "margin_used": self.margin_used,
            "free_margin": self.free_margin,
        }


@dataclass
class AccountState:
    """Full account state for the trading engine."""
    login_id: str
    account_type: str
    currency: str
    balance: float
    open_positions: List[Dict[str, Any]]
    total_profit: float
    margin_used: float
    free_margin: float
    pip_value: float
    is_demo: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "login_id": self.login_id,
            "account_type": self.account_type,
            "currency": self.currency,
            "balance": self.balance,
            "open_positions": self.open_positions,
            "total_profit": self.total_profit,
            "margin_used": self.margin_used,
            "free_margin": self.free_margin,
            "pip_value": self.pip_value,
            "is_demo": self.is_demo,
        }


class AccountCenter:
    """Unified Account Center for SmartPip Trader.

    Provides a single entry point for:
      * Connecting to the Deriv WebSocket API with an authorised token.
      * Listing and switching between demo / real accounts.
      * Querying balances, portfolios, and trade history.
      * Real-time balance subscriptions.
    """

    def __init__(self, auth_manager: DerivAuthManager) -> None:
        self._auth = auth_manager
        self._ws = None
        self._connected = False
        self._request_id = 0
        self._pending: Dict[int, asyncio.Future] = {}
        self._active_login_id: Optional[str] = None
        self._accounts: Dict[str, AccountInfo] = {}
        self._balance_subscriptions: List[Callable] = []
        self._listener_task: Optional[asyncio.Task] = None
        self._balance_cache: Dict[str, float] = {}
        logger.debug("AccountCenter initialised")

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Establish a WebSocket connection using the current auth token."""
        token = self._auth.get_token()
        if token is None:
            logger.error("Cannot connect: no valid token")
            return False

        try:
            import websockets
        except ImportError:
            logger.error("websockets library is required")
            return False

        app_id = self._auth.app_id
        url = f"{DERIV_WS_BASE}?app_id={app_id}"
        try:
            self._ws = await asyncio.wait_for(websockets.connect(url), timeout=15.0)
        except Exception as exc:
            logger.error("WebSocket connection failed: %s", exc)
            return False

        auth_resp = await self._send({"authorize": token})
        if auth_resp.get("error"):
            msg = auth_resp["error"].get("message", "unknown")
            logger.error("Authorisation failed: %s", msg)
            await self._close_ws()
            return False

        self._connected = True
        auth_data = auth_resp.get("authorize", {})
        login_id = auth_data.get("loginid", "")
        self._active_login_id = login_id
        self._accounts[login_id] = _parse_account_info(auth_data, is_active=True)
        logger.info("Connected as %s", login_id)

        self._listener_task = asyncio.ensure_future(self._listen_loop())
        await self._fetch_account_list()
        return True

    async def disconnect(self) -> None:
        """Gracefully disconnect from the API."""
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        await self._close_ws()
        self._connected = False
        logger.info("Disconnected")

    # ------------------------------------------------------------------
    # Account queries
    # ------------------------------------------------------------------

    async def get_accounts(self) -> List[AccountInfo]:
        """List all authorised accounts (demo + real)."""
        if not self._connected:
            logger.warning("get_accounts called while disconnected")
            return list(self._accounts.values())
        await self._fetch_account_list()
        return list(self._accounts.values())

    async def switch_account(self, login_id: str) -> bool:
        """Switch the active account to *login_id*."""
        if login_id not in self._accounts:
            logger.error("Unknown login_id: %s", login_id)
            return False
        token = self._auth.get_token()
        if token is None:
            return False
        resp = await self._send({"switch_account": login_id})
        if resp.get("error"):
            logger.error("switch_account failed: %s", resp["error"].get("message"))
            return False
        for aid, info in self._accounts.items():
            info.is_active = aid == login_id
        self._active_login_id = login_id
        logger.info("Switched to account %s", login_id)
        return True

    def get_active_account(self) -> Optional[AccountInfo]:
        """Return the currently active ``AccountInfo``."""
        if self._active_login_id is None:
            return None
        return self._accounts.get(self._active_login_id)

    async def get_balance(self) -> float:
        """Fetch and return the current balance."""
        resp = await self._send({"balance": 1})
        if resp.get("error"):
            logger.error("get_balance failed: %s", resp["error"].get("message"))
            return 0.0
        bal_data = resp.get("balance", {})
        balance = float(bal_data.get("balance", 0.0))
        login_id = bal_data.get("loginid", self._active_login_id or "")
        self._balance_cache[login_id] = balance
        if login_id in self._accounts:
            self._accounts[login_id].balance = balance
        return balance

    async def get_all_balances(self) -> Dict[str, float]:
        """Fetch balances for every authorised account."""
        balances: Dict[str, float] = {}
        current_login = self._active_login_id
        for login_id in self._accounts:
            if current_login and login_id != current_login:
                resp = await self._send({"switch_account": login_id})
                if resp.get("error"):
                    continue
            bal_resp = await self._send({"balance": 1})
            if not bal_resp.get("error"):
                bal = float(bal_resp.get("balance", {}).get("balance", 0.0))
                balances[login_id] = bal
                self._balance_cache[login_id] = bal
                if login_id in self._accounts:
                    self._accounts[login_id].balance = bal
        if current_login and current_login != self._active_login_id:
            await self._send({"switch_account": current_login})
        return balances

    # ------------------------------------------------------------------
    # Trade history & portfolio
    # ------------------------------------------------------------------

    async def get_account_history(self, days: int = 30) -> List[TradeRecord]:
        """Fetch the trade statement for the last *days* days."""
        now = int(time.time())
        start = now - days * 86400
        resp = await self._send({
            "statement": 1,
            "date_from": start,
            "date_to": now,
            "limit": 500,
        })
        if resp.get("error"):
            logger.error("statement failed: %s", resp["error"].get("message"))
            return []
        records: List[TradeRecord] = []
        for entry in resp.get("statement", {}).get("transactions", []):
            try:
                records.append(TradeRecord(
                    timestamp=entry.get("transaction_time", ""),
                    symbol=entry.get("symbol", ""),
                    trade_type=entry.get("contract_type", ""),
                    entry_price=float(entry.get("buy_price", 0.0)),
                    exit_price=float(entry.get("sell_price", 0.0)),
                    profit=float(entry.get("profit", 0.0)),
                    payout=float(entry.get("payout", 0.0)),
                    duration=float(entry.get("duration", 0.0)),
                ))
            except (KeyError, ValueError, TypeError) as exc:
                logger.debug("Skipping malformed statement entry: %s", exc)
        return records

    async def get_portfolio(self) -> PortfolioState:
        """Fetch the current open portfolio."""
        resp = await self._send({"portfolio": 1})
        if resp.get("error"):
            logger.error("portfolio failed: %s", resp["error"].get("message"))
            return PortfolioState()
        contracts = resp.get("portfolio", {}).get("contracts", [])
        positions: List[Dict[str, Any]] = []
        total_profit = 0.0
        margin_used = 0.0
        for c in contracts:
            profit = float(c.get("profit", 0.0))
            stake = float(c.get("buy_price", 0.0))
            total_profit += profit
            margin_used += stake
            positions.append({
                "contract_id": c.get("contract_id", ""),
                "symbol": c.get("symbol", ""),
                "trade_type": c.get("contract_type", ""),
                "entry_price": float(c.get("entry_tick_price", 0.0)),
                "stake": stake,
                "payout": float(c.get("payout", 0.0)),
                "profit": profit,
                "duration": float(c.get("duration", 0.0)),
            })
        bal = await self.get_balance()
        free_margin = max(bal - margin_used, 0.0)
        return PortfolioState(
            open_positions=positions,
            total_profit=total_profit,
            margin_used=margin_used,
            free_margin=free_margin,
        )

    async def get_account_state(self) -> AccountState:
        """Return a fully-populated ``AccountState`` for the trading engine."""
        acct = self.get_active_account()
        portfolio = await self.get_portfolio()
        balance = acct.balance if acct else 0.0
        return AccountState(
            login_id=acct.login_id if acct else "",
            account_type=acct.account_type if acct else "demo",
            currency=acct.currency if acct else "USD",
            balance=balance,
            open_positions=portfolio.open_positions,
            total_profit=portfolio.total_profit,
            margin_used=portfolio.margin_used,
            free_margin=portfolio.free_margin,
            pip_value=acct.pip_value if acct else 0.0,
            is_demo=acct.account_type == "demo" if acct else True,
        )

    # ------------------------------------------------------------------
    # Real-time subscriptions
    # ------------------------------------------------------------------

    async def subscribe_to_balance(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to real-time balance updates via ``balance`` stream."""
        self._balance_subscriptions.append(callback)
        if not self._connected:
            return
        resp = await self._send({"balance": 1, "subscribe": 1})
        if resp.get("error"):
            logger.error("balance subscribe failed: %s", resp["error"].get("message"))

    async def unsubscribe_balance(self, callback: Callable) -> None:
        """Remove *callback* from balance subscribers."""
        if callback in self._balance_subscriptions:
            self._balance_subscriptions.remove(callback)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> bool:
        """Persist account centre state to *path* via joblib."""
        try:
            import joblib
            state = {
                "active_login_id": self._active_login_id,
                "accounts": {k: v.to_dict() for k, v in self._accounts.items()},
                "balance_cache": self._balance_cache,
            }
            joblib.dump(state, path)
            logger.info("AccountCenter saved to %s", path)
            return True
        except Exception as exc:
            logger.error("save failed: %s", exc)
            return False

    def load(self, path: str) -> bool:
        """Restore account centre state from *path*."""
        try:
            import joblib
            state = joblib.load(path)
            self._active_login_id = state.get("active_login_id")
            self._accounts = {
                k: AccountInfo(**v) for k, v in state.get("accounts", {}).items()
            }
            self._balance_cache = state.get("balance_cache", {})
            logger.info("AccountCenter loaded from %s", path)
            return True
        except FileNotFoundError:
            logger.warning("File not found: %s", path)
            return False
        except Exception as exc:
            logger.error("load failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Internal WebSocket helpers
    # ------------------------------------------------------------------

    async def _send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request and wait for the matching response."""
        if not self._ws:
            return {"error": {"message": "not connected"}}
        self._request_id += 1
        rid = self._request_id
        payload["req_id"] = rid
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[rid] = fut
        try:
            await self._ws.send(json.dumps(payload))
            result = await asyncio.wait_for(fut, timeout=15.0)
            return result
        except asyncio.TimeoutError:
            logger.warning("Request %d timed out", rid)
            return {"error": {"message": "timeout"}}
        finally:
            self._pending.pop(rid, None)

    async def _listen_loop(self) -> None:
        """Background listener that dispatches messages to futures and callbacks."""
        try:
            while self._connected and self._ws:
                raw = await self._ws.recv()
                data: Dict[str, Any] = json.loads(raw)
                rid = data.get("req_id")
                if rid and rid in self._pending:
                    self._pending[rid].set_result(data)
                if "balance" in data:
                    await self._dispatch_balance(data["balance"])
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Listener error: %s", exc)
            self._connected = False

    async def _dispatch_balance(self, bal_data: Dict[str, Any]) -> None:
        """Push a balance update to all registered subscribers."""
        login_id = bal_data.get("loginid", self._active_login_id or "")
        balance = float(bal_data.get("balance", 0.0))
        self._balance_cache[login_id] = balance
        if login_id in self._accounts:
            self._accounts[login_id].balance = balance
        payload = {"login_id": login_id, "balance": balance, "currency": bal_data.get("currency", "USD")}
        for cb in self._balance_subscriptions:
            try:
                cb(payload)
            except Exception as exc:
                logger.error("Balance callback error: %s", exc)

    async def _fetch_account_list(self) -> None:
        """Populate the account cache from the ``get_settings`` response."""
        resp = await self._send({"get_settings": 1})
        if resp.get("error"):
            return
        settings = resp.get("get_settings", {})
        login_id = settings.get("loginid", self._active_login_id or "")
        if login_id and login_id not in self._accounts:
            self._accounts[login_id] = AccountInfo(
                login_id=login_id,
                account_type="demo" if login_id.startswith("VR") else "real",
                currency=settings.get("currency", "USD"),
                is_active=login_id == self._active_login_id,
            )

    async def _close_ws(self) -> None:
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None


def _parse_account_info(auth_data: Dict[str, Any], is_active: bool = True) -> AccountInfo:
    """Create an ``AccountInfo`` from an ``authorize`` response payload."""
    login_id = auth_data.get("loginid", "")
    is_virtual = auth_data.get("is_virtual", 0) == 1
    balance = float(auth_data.get("balance", 0.0))
    currency = auth_data.get("currency", "USD")
    pip_value = _estimate_pip_value(currency)
    return AccountInfo(
        login_id=login_id,
        account_type="demo" if is_virtual or login_id.startswith("VR") else "real",
        currency=currency,
        balance=balance,
        is_active=is_active,
        pip_value=pip_value,
        margin=balance,
    )


def _estimate_pip_value(currency: str) -> float:
    """Rough pip value estimate for common Deriv currencies."""
    mapping = {"USD": 0.0001, "EUR": 0.0001, "GBP": 0.0001, "AUD": 0.0001, "KES": 0.01}
    return mapping.get(currency, 0.0001)
