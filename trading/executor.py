import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from models import Prediction

logger = logging.getLogger(__name__)


class TradeExecutor:
    """Executes trades based on predictions"""
    
    def __init__(self):
        self.active_trades = {}
    
    async def execute_trade(
        self,
        websocket,
        prediction: Prediction,
        market: str,
        currency: str,
        amount: float,
        current_price: float
    ) -> Optional[str]:
        """Execute trade based on prediction"""
        # Map prediction to Deriv contract type
        direction = None
        if prediction.type == "RISE_FALL":
            direction = "CALL" if prediction.direction == "RISE" else "PUT"
        elif prediction.type == "EVEN_ODD":
            direction = "CALL" if prediction.direction == "EVEN" else "PUT"
        else:
            direction = "CALL"
        
        trade_msg = {
            "buy": 1,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": direction.lower(),
                "currency": currency,
                "duration": 2,
                "duration_unit": "m",
                "symbol": market
            }
        }
        
        try:
            await websocket.send(json.dumps(trade_msg))
            response = await websocket.recv()
            data = json.loads(response)
            
            if "buy" in data:
                contract_id = data["buy"]["contract_id"]
                trade = {
                    "id": contract_id,
                    "market": market,
                    "type": prediction.type,
                    "direction": prediction.direction,
                    "amount": amount,
                    "confidence": prediction.confidence,
                    "reason": prediction.reason,
                    "entry_price": current_price,
                    "entry_time": datetime.now().isoformat()
                }
                self.active_trades[contract_id] = trade
                logger.info(f"🎯 TRADE: {prediction.type} - {prediction.direction} | ${amount} | {prediction.confidence:.0f}%")
                return contract_id
        except Exception as e:
            logger.error(f"Trade error: {e}")
        
        return None
    
    def get_active_trades(self) -> Dict:
        """Get all active trades"""
        return self.active_trades
    
    def remove_trade(self, contract_id: str):
        """Remove trade from active trades"""
        if contract_id in self.active_trades:
            del self.active_trades[contract_id]
    
    def get_trade(self, contract_id: str) -> Optional[Dict]:
        """Get specific trade"""
        return self.active_trades.get(contract_id)
