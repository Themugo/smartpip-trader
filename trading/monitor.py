import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Callable

logger = logging.getLogger(__name__)


class TradeMonitor:
    """Monitors active trades and updates statistics"""
    
    def __init__(self):
        self.active_trades = {}
        self.trade_history = []
    
    async def monitor_trade(
        self,
        websocket,
        contract_id: str,
        seconds: int,
        on_trade_complete: Callable
    ):
        """Monitor a trade for specified duration"""
        await asyncio.sleep(seconds)
        
        try:
            await websocket.send(json.dumps({"portfolio": 1}))
            response = await websocket.recv()
            data = json.loads(response)
            
            profit = 0
            if "portfolio" in data:
                for contract in data["portfolio"].get("contracts", []):
                    if contract["contract_id"] == contract_id:
                        profit = float(contract.get("profit", 0))
                        break
            
            # Call callback with trade result
            await on_trade_complete(contract_id, profit)
            
        except Exception as e:
            logger.error(f"Monitor error: {e}")
    
    def add_trade(self, contract_id: str, trade_data: Dict):
        """Add trade to active trades"""
        self.active_trades[contract_id] = trade_data
    
    def complete_trade(self, contract_id: str, profit: float):
        """Mark trade as complete and add to history"""
        if contract_id in self.active_trades:
            trade = self.active_trades[contract_id]
            trade["profit"] = profit
            trade["exit_time"] = datetime.now().isoformat()
            self.trade_history.append(trade)
            del self.active_trades[contract_id]
    
    def get_active_trades_count(self) -> int:
        """Get count of active trades"""
        return len(self.active_trades)
    
    def get_trade_history(self, limit: int = 20) -> list:
        """Get recent trade history"""
        return self.trade_history[-limit:]
    
    def get_all_trade_history(self) -> list:
        """Get all trade history"""
        return self.trade_history
