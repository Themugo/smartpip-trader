import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Awaitable

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None

logger = logging.getLogger(__name__)


class DerivConnection:
    """Single-owner Deriv WebSocket connection with request correlation.

    The receiver task is the only coroutine that calls ``recv``. Requests wait
    on futures keyed by ``req_id``, while unsolicited subscription messages are
    delivered to registered handlers. This prevents response/tick races.
    """

    def __init__(self, max_retries: int = 5, initial_backoff: float = 1.0):
        self.websocket = None
        self.connected = False
        self.authorized = False
        self.api_token = os.getenv("DERIV_API_TOKEN")
        self.app_id = os.getenv("DERIV_APP_ID", "1089")
        self.account_id = os.getenv("DERIV_ACCOUNT_ID", "")
        self.api_base_url = os.getenv("DERIV_API_URL", "https://api.derivws.com").rstrip("/")
        self.demo_only = os.getenv("DERIV_DEMO_ONLY", "false").lower() in {"1", "true", "yes", "on"}
        self.legacy_ws_url = os.getenv("DERIV_WS_URL", "")
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.reconnect_attempts = 0
        self.on_reconnect: Optional[Callable[..., Awaitable[Any]]] = None
        self.on_disconnect: Optional[Callable[..., Awaitable[Any]]] = None
        self._connection_lock = asyncio.Lock()
        self._send_lock = asyncio.Lock()
        self._request_id = 0
        self._pending: Dict[int, asyncio.Future] = {}
        self._subscription_handlers: Dict[str, list[Callable[[dict], Awaitable[Any] | Any]]] = {}
        self._receiver_task: Optional[asyncio.Task] = None
        self._stopping = False

    def set_reconnect_callback(self, callback: Callable):
        self.on_reconnect = callback

    def set_disconnect_callback(self, callback: Callable):
        self.on_disconnect = callback

    def add_handler(self, msg_type: str, callback: Callable[[dict], Awaitable[Any] | Any]) -> None:
        self._subscription_handlers.setdefault(msg_type, []).append(callback)

    def remove_handler(self, msg_type: str, callback: Callable) -> None:
        handlers = self._subscription_handlers.get(msg_type, [])
        if callback in handlers:
            handlers.remove(callback)
        if not handlers:
            self._subscription_handlers.pop(msg_type, None)

    def _next_req_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _get_authenticated_ws_url(self) -> str:
        """Obtain a current authenticated demo/real WebSocket URL via Deriv OTP."""
        if not self.account_id:
            raise RuntimeError("DERIV_ACCOUNT_ID is required for current Deriv authenticated WebSocket API")
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("httpx is required for Deriv OTP authentication") from exc

        url = f"{self.api_base_url}/trading/v1/options/accounts/{self.account_id}/otp"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Deriv-App-ID": self.app_id,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            body = response.json()
        ws_url = ((body.get("data") or {}).get("url") or "").strip()
        if not ws_url:
            raise RuntimeError("Deriv OTP response did not contain an authenticated WebSocket URL")
        if self.demo_only and "/real" in ws_url:
            raise PermissionError("DERIV_DEMO_ONLY is enabled but Deriv returned a real-account WebSocket URL")
        return ws_url

    async def connect(self) -> bool:
        if not self.api_token:
            logger.error("No DERIV_API_TOKEN configured")
            return False
        if not websockets:
            logger.error("websockets library not installed")
            return False

        async with self._connection_lock:
            self._stopping = False
            for attempt in range(self.max_retries):
                try:
                    logger.info("Deriv connection attempt %d/%d", attempt + 1, self.max_retries)
                    if self.account_id:
                        self.ws_url = await self._get_authenticated_ws_url()
                    elif self.legacy_ws_url:
                        self.ws_url = self.legacy_ws_url
                        logger.warning("Using legacy Deriv WebSocket authentication; migrate to DERIV_ACCOUNT_ID + OTP authentication")
                    else:
                        raise RuntimeError("DERIV_ACCOUNT_ID is required for current Deriv authentication")

                    self.websocket = await asyncio.wait_for(
                        websockets.connect(self.ws_url, ping_interval=20, ping_timeout=20),
                        timeout=10.0,
                    )
                    self.connected = True
                    self.authorized = bool(self.account_id)
                    self._receiver_task = asyncio.create_task(
                        self._receiver_loop(),
                        name="deriv-receiver",
                    )

                    if not self.account_id:
                        auth = await self.request(
                            {"authorize": self.api_token},
                            timeout=10.0,
                        )
                        if auth.get("error"):
                            raise RuntimeError(auth["error"].get("message", "Authorization failed"))
                        self.authorized = True
                    self.reconnect_attempts = 0
                    logger.info("Connected and authorized to Deriv")
                    if self.on_reconnect:
                        result = self.on_reconnect()
                        if asyncio.iscoroutine(result):
                            await result
                    return True
                except Exception as exc:
                    logger.error("Deriv connection failed: %s", exc)
                    await self._close_socket_only()
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.initial_backoff * (2 ** attempt))
            self.reconnect_attempts += 1
            return False

    async def reconnect(self) -> bool:
        self.connected = False
        self.authorized = False
        if self.on_disconnect:
            result = self.on_disconnect()
            if asyncio.iscoroutine(result):
                await result
        return await self.connect()

    async def request(self, payload: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        if not self.is_connected():
            raise ConnectionError("Deriv connection is not active")
        req_id = self._next_req_id()
        message = dict(payload)
        message["req_id"] = req_id
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending[req_id] = future
        try:
            async with self._send_lock:
                await self.websocket.send(json.dumps(message))
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending.pop(req_id, None)

    async def send(self, message: dict) -> bool:
        if not self.is_connected():
            return False
        try:
            async with self._send_lock:
                await self.websocket.send(json.dumps(message))
            return True
        except Exception as exc:
            logger.error("Deriv send failed: %s", exc)
            self.connected = False
            return False

    async def _receiver_loop(self) -> None:
        try:
            while self.is_connected():
                raw = await self.websocket.recv()
                data = json.loads(raw)
                req_id = data.get("req_id")
                if req_id is not None and req_id in self._pending:
                    future = self._pending.get(req_id)
                    if future and not future.done():
                        future.set_result(data)
                msg_type = data.get("msg_type")
                if msg_type:
                    for callback in list(self._subscription_handlers.get(msg_type, [])):
                        try:
                            result = callback(data)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception:
                            logger.exception("Deriv %s handler failed", msg_type)
                # Errors without a matching req_id are observable but do not
                # poison unrelated request futures.
                if data.get("error") and req_id is None:
                    logger.warning("Unsolicited Deriv error: %s", data["error"])
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Deriv receiver stopped: %s", exc)
        finally:
            self.connected = False
            self.authorized = False
            for future in list(self._pending.values()):
                if not future.done():
                    future.set_exception(ConnectionError("Deriv connection closed"))

    async def subscribe(self, payload: Dict[str, Any], msg_type: str, handler: Optional[Callable] = None) -> Dict[str, Any]:
        if handler:
            self.add_handler(msg_type, handler)
        body = dict(payload)
        body["subscribe"] = 1
        return await self.request(body)

    async def keep_alive(self, interval: float = 30.0):
        while self.is_connected() and not self._stopping:
            await asyncio.sleep(interval)
            if self.is_connected():
                await self.send({"ping": 1})

    async def _close_socket_only(self):
        self.connected = False
        self.authorized = False
        if self._receiver_task and not self._receiver_task.done():
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass
        self._receiver_task = None
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass
        self.websocket = None

    async def close(self):
        async with self._connection_lock:
            self._stopping = True
            await self._close_socket_only()
            logger.info("Deriv connection closed")

    def is_connected(self) -> bool:
        return bool(self.connected and self.websocket)

    # Legacy compatibility: callers that used raw recv must migrate to request/handlers.
    async def recv(self) -> dict:
        raise RuntimeError(
            "Direct recv() is disabled. Use request() or subscription handlers so responses stay correlated."
        )
