import os
import json
import logging
import asyncio
import time
try:
    import websockets
except ImportError:
    websockets = None
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class DerivConnection:
    """Manages WebSocket connection to Deriv API with robust reconnection logic"""
    
    def __init__(self, max_retries: int = 5, initial_backoff: float = 1.0):
        """
        Initialize connection manager
        
        Args:
            max_retries: Maximum number of reconnection attempts
            initial_backoff: Initial backoff time in seconds (exponential)
        """
        self.websocket = None
        self.connected = False
        self.api_token = os.getenv("DERIV_API_TOKEN")
        self.app_id = os.getenv("DERIV_APP_ID", "1089")
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.reconnect_attempts = 0
        self.on_reconnect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None
        self._connection_lock = asyncio.Lock()
    
    def set_reconnect_callback(self, callback: Callable):
        """Set callback to be called on successful reconnection"""
        self.on_reconnect = callback
    
    def set_disconnect_callback(self, callback: Callable):
        """Set callback to be called on disconnection"""
        self.on_disconnect = callback
    
    async def connect(self) -> bool:
        """Connect to Deriv WebSocket API with retry logic"""
        if not self.api_token:
            logger.error("No API token found!")
            return False
        
        if not websockets:
            logger.error("websockets library not installed")
            return False
        
        url = f"wss://ws.binaryws.com/websockets/v3?app_id={self.app_id}"
        
        async with self._connection_lock:
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"Connection attempt {attempt + 1}/{self.max_retries}")
                    
                    self.websocket = await asyncio.wait_for(
                        websockets.connect(url),
                        timeout=10.0
                    )
                    
                    await self.websocket.send(json.dumps({"authorize": self.api_token}))
                    response = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=10.0
                    )
                    auth_data = json.loads(response)
                    
                    if auth_data.get("error"):
                        logger.error(f"Auth failed: {auth_data['error']['message']}")
                        await self.websocket.close()
                        continue
                    
                    self.connected = True
                    self.reconnect_attempts = 0
                    logger.info("Connected to Deriv!")
                    
                    if self.on_reconnect:
                        await self.on_reconnect()
                    
                    return True
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Connection timeout on attempt {attempt + 1}")
                except Exception as e:
                    logger.error(f"Connection failed on attempt {attempt + 1}: {e}")
                    if self.websocket:
                        try:
                            await self.websocket.close()
                        except:
                            pass
                
                # Exponential backoff
                if attempt < self.max_retries - 1:
                    backoff = self.initial_backoff * (2 ** attempt)
                    logger.info(f"Waiting {backoff:.1f}s before retry...")
                    await asyncio.sleep(backoff)
            
            self.reconnect_attempts += 1
            logger.error(f"Failed to connect after {self.max_retries} attempts")
            return False
    
    async def reconnect(self) -> bool:
        """Attempt to reconnect with exponential backoff"""
        logger.info("Attempting to reconnect...")
        self.connected = False
        
        if self.on_disconnect:
            await self.on_disconnect()
        
        return await self.connect()
    
    async def send(self, message: dict):
        """Send message to WebSocket with error handling"""
        if not self.connected or not self.websocket:
            logger.warning("Cannot send: not connected")
            return False
        
        try:
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Send failed: {e}")
            self.connected = False
            return False
    
    async def recv(self) -> dict:
        """Receive message from WebSocket with error handling"""
        if not self.connected or not self.websocket:
            logger.warning("Cannot receive: not connected")
            return {}
        
        try:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=30.0)
            return json.loads(response)
        except asyncio.TimeoutError:
            logger.warning("Receive timeout")
            self.connected = False
            return {}
        except Exception as e:
            logger.error(f"Receive failed: {e}")
            self.connected = False
            return {}
    
    async def close(self):
        """Close WebSocket connection"""
        async with self._connection_lock:
            if self.websocket:
                try:
                    await self.websocket.close()
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
                finally:
                    self.websocket = None
                    self.connected = False
                    logger.info("Connection closed")
    
    async def keep_alive(self, interval: float = 30.0):
        """Send periodic keep-alive ping to maintain connection"""
        while self.connected:
            try:
                await asyncio.sleep(interval)
                if self.connected:
                    await self.send({"ping": 1})
                    logger.debug("Keep-alive ping sent")
            except Exception as e:
                logger.error(f"Keep-alive failed: {e}")
                break
    
    def is_connected(self) -> bool:
        """Check if connection is active"""
        return self.connected and self.websocket is not None
