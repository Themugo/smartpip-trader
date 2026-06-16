import websockets
import json
import asyncio
from typing import Dict, Any, Optional, Callable
import os
import logging

logger = logging.getLogger(__name__)


class DerivAPI:
    """Real Deriv API integration for live trading"""
    
    def __init__(self, api_token: str = None, app_id: str = "1089"):
        self.api_token = api_token or os.getenv("DERIV_API_TOKEN")
        self.app_id = app_id or os.getenv("DERIV_APP_ID", "1089")
        self.ws_url = f"wss://ws.binaryws.com/websockets/v3?app_id={self.app_id}"
        self.websocket = None
        self.request_id = 0
        self.response_handlers = {}
        self.tick_handler = None
        self.authorized = False
    
    async def connect(self):
        """Connect to Deriv API"""
        self.websocket = await websockets.connect(self.ws_url)
        
        # Authorize
        await self.authorize()
        
        # Start message listener
        asyncio.create_task(self._listen_messages())
    
    async def authorize(self):
        """Authorize with API token"""
        if not self.api_token:
            raise ValueError("API token required for authorization")
        
        response = await self.send_request({
            "authorize": self.api_token
        })
        
        if response.get("error"):
            raise Exception(f"Authorization failed: {response['error']['message']}")
        
        self.authorized = True
        return response
    
    async def send_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to Deriv API"""
        self.request_id += 1
        payload["req_id"] = self.request_id
        
        await self.websocket.send(json.dumps(payload))
        
        # Wait for response
        response = await self._wait_for_response(self.request_id)
        
        return response
    
    async def _wait_for_response(self, req_id: int, timeout: float = 10.0) -> Dict[str, Any]:
        """Wait for response with specific request ID"""
        future = asyncio.Future()
        self.response_handlers[req_id] = future
        
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            raise Exception(f"Request {req_id} timed out")
        finally:
            self.response_handlers.pop(req_id, None)
    
    async def _listen_messages(self):
        """Listen for incoming messages"""
        while True:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                # Handle tick data
                if "tick" in data:
                    if self.tick_handler:
                        await self.tick_handler(data["tick"])
                
                # Handle response
                if "req_id" in data:
                    req_id = data["req_id"]
                    if req_id in self.response_handlers:
                        self.response_handlers[req_id].set_result(data)
                
            except Exception as e:
                logger.error(f"Error listening to messages: {e}")
                break
    
    async def subscribe_ticks(self, symbol: str, handler: Callable):
        """Subscribe to tick data for a symbol"""
        self.tick_handler = handler
        
        await self.send_request({
            "ticks": symbol,
            "subscribe": 1
        })
    
    async def buy_contract(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Buy a contract"""
        if not self.authorized:
            raise Exception("Not authorized. Call authorize() first.")
        
        response = await self.send_request({
            "buy": 1,
            "price": parameters.get("amount", 1),
            "parameters": {
                "amount": parameters.get("amount", 1),
                "basis": parameters.get("basis", "stake"),
                "contract_type": parameters.get("contract_type", "CALL"),
                "currency": parameters.get("currency", "USD"),
                "duration": parameters.get("duration", 1),
                "duration_unit": parameters.get("duration_unit", "m"),
                "symbol": parameters.get("symbol", "R_100")
            }
        })
        
        return response
    
    async def get_balance(self) -> Dict[str, Any]:
        """Get account balance"""
        if not self.authorized:
            raise Exception("Not authorized. Call authorize() first.")
        
        response = await self.send_request({
            "balance": 1
        })
        
        return response
    
    async def get_portfolio(self) -> Dict[str, Any]:
        """Get portfolio (open positions)"""
        if not self.authorized:
            raise Exception("Not authorized. Call authorize() first.")
        
        response = await self.send_request({
            "portfolio": 1
        })
        
        return response
    
    async def close_contract(self, contract_id: str) -> Dict[str, Any]:
        """Close an open contract"""
        if not self.authorized:
            raise Exception("Not authorized. Call authorize() first.")
        
        response = await self.send_request({
            "sell": contract_id,
            "price": 0  # Market price
        })
        
        return response
    
    async def disconnect(self):
        """Disconnect from API"""
        if self.websocket:
            await self.websocket.close()
            self.authorized = False
