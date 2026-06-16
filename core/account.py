import logging
from typing import Dict

logger = logging.getLogger(__name__)


class AccountManager:
    """Manages account information and balance"""
    
    def __init__(self):
        self.accounts = {
            "demo": {"balance": 10000.00, "initial": 10000.00, "pnl": 0.00},
            "real": {"balance": 0.00, "initial": 0.00, "pnl": 0.00}
        }
        self.active_account = "demo"
        self.current_balance = 10000.00
        self.currency = "USD"
    
    def set_active_account(self, account_type: str):
        """Set active account type"""
        if account_type in self.accounts:
            self.active_account = account_type
            self.current_balance = self.accounts[account_type]["balance"]
    
    async def update_balance(self, websocket):
        """Update balance from API"""
        try:
            import json
            await websocket.send(json.dumps({"balance": 1}))
            response = await websocket.recv()
            data = json.loads(response)
            if "balance" in data:
                self.current_balance = float(data["balance"]["balance"])
                self.currency = data["balance"]["currency"]
                self.accounts[self.active_account]["balance"] = self.current_balance
        except Exception as e:
            logger.error(f"Balance update failed: {e}")
    
    def get_balance(self) -> float:
        """Get current balance"""
        return self.current_balance
    
    def get_currency(self) -> str:
        """Get currency"""
        return self.currency
