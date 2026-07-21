from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class Asset:
    """Represents a trading asset/instrument"""
    
    symbol: str
    market_type: str
    current_price: float = 0.0
    quantity: float = 0.0
    average_cost: float = 0.0
    total_cost: float = 0.0
    current_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    last_updated: Optional[str] = None
    
    def update_price(self, price: float):
        """Update current price and recalculate values"""
        self.current_price = price
        self.current_value = self.quantity * price
        self.unrealized_pnl = (self.current_price - self.average_cost) * self.quantity if self.quantity > 0 else 0
        self.last_updated = datetime.now().isoformat()
    
    def add_position(self, quantity: float, price: float):
        """Add to position (buy)"""
        if self.quantity == 0:
            self.average_cost = price
        else:
            total_cost = (self.quantity * self.average_cost) + (quantity * price)
            self.quantity += quantity
            self.average_cost = total_cost / self.quantity
        else:
            self.quantity += quantity
            self.average_cost = ((self.quantity - quantity) * self.average_cost + quantity * price) / self.quantity
        
        self.total_cost = self.quantity * self.average_cost
        self.current_value = self.quantity * self.current_price
        self.unrealized_pnl = (self.current_price - self.average_cost) * self.quantity
    
    def reduce_position(self, quantity: float, price: float):
        """Reduce position (sell)"""
        if quantity > self.quantity:
            raise ValueError("Cannot sell more than owned")
        
        realized = (price - self.average_cost) * quantity
        self.realized_pnl += realized
        self.quantity -= quantity
        self.total_cost = self.quantity * self.average_cost
        self.current_value = self.quantity * self.current_price
        self.unrealized_pnl = (self.current_price - self.average_cost) * self.quantity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "market_type": self.market_type,
            "current_price": self.current_price,
            "quantity": self.quantity,
            "average_cost": self.average_cost,
            "total_cost": self.total_cost,
            "current_value": self.current_value,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "last_updated": self.last_updated
        }
