from typing import Dict, Any, List, Optional
from datetime import datetime
from .asset import Asset


class PortfolioManager:
    """Manages multiple assets and portfolio-level metrics"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.available_cash = initial_capital
        self.assets: Dict[str, Asset] = {}
        self.total_value = initial_capital
        self.total_pnl = 0.0
        self.total_return = 0.0
    
    def add_asset(self, symbol: str, market_type: str) -> Asset:
        """Add a new asset to the portfolio"""
        if symbol in self.assets:
            return self.assets[symbol]
        
        asset = Asset(symbol=symbol, market_type=market_type)
        self.assets[symbol] = asset
        return asset
    
    def get_asset(self, symbol: str) -> Optional[Asset]:
        """Get an asset by symbol"""
        return self.assets.get(symbol)
    
    def buy_asset(self, symbol: str, quantity: float, price: float) -> bool:
        """Buy an asset"""
        cost = quantity * price
        
        if cost > self.available_cash:
            return False
        
        if symbol not in self.assets:
            self.add_asset(symbol, "UNKNOWN")
        
        self.assets[symbol].add_position(quantity, price)
        self.available_cash -= cost
        self._update_portfolio_value()
        
        return True
    
    def sell_asset(self, symbol: str, quantity: float, price: float) -> bool:
        """Sell an asset"""
        if symbol not in self.assets:
            return False
        
        asset = self.assets[symbol]
        
        if quantity > asset.quantity:
            return False
        
        asset.reduce_position(quantity, price)
        self.available_cash += quantity * price
        self._update_portfolio_value()
        
        # Remove asset if position is closed
        if asset.quantity == 0:
            del self.assets[symbol]
        
        return True
    
    def update_asset_price(self, symbol: str, price: float):
        """Update price for an asset"""
        if symbol in self.assets:
            self.assets[symbol].update_price(price)
            self._update_portfolio_value()
    
    def _update_portfolio_value(self):
        """Recalculate total portfolio value"""
        assets_value = sum(asset.current_value for asset in self.assets.values())
        self.total_value = self.available_cash + assets_value
        self.total_pnl = self.total_value - self.initial_capital
        self.total_return = (self.total_pnl / self.initial_capital) * 100 if self.initial_capital > 0 else 0
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary"""
        return {
            "initial_capital": self.initial_capital,
            "available_cash": self.available_cash,
            "total_value": self.total_value,
            "total_pnl": self.total_pnl,
            "total_return": self.total_return,
            "assets_count": len(self.assets),
            "assets": {symbol: asset.to_dict() for symbol, asset in self.assets.items()},
            "cash_allocation": (self.available_cash / self.total_value * 100) if self.total_value > 0 else 0,
            "asset_allocation": {
                symbol: (asset.current_value / self.total_value * 100) if self.total_value > 0 else 0
                for symbol, asset in self.assets.items()
            }
        }
    
    def get_asset_allocation(self) -> Dict[str, float]:
        """Get asset allocation percentages"""
        if self.total_value == 0:
            return {}
        
        allocation = {"cash": (self.available_cash / self.total_value) * 100}
        
        for symbol, asset in self.assets.items():
            allocation[symbol] = (asset.current_value / self.total_value) * 100
        
        return allocation
    
    def rebalance(self, target_allocation: Dict[str, float]) -> bool:
        """
        Rebalance portfolio to target allocation
        
        Args:
            target_allocation: Dictionary of symbol -> target percentage (e.g., {"R_100": 50, "cash": 50})
        
        Returns:
            True if rebalancing successful
        """
        if self.total_value == 0:
            return False
        
        # Calculate target values
        target_values = {
            symbol: (percentage / 100) * self.total_value
            for symbol, percentage in target_allocation.items()
        }
        
        # Calculate current values
        current_values = {"cash": self.available_cash}
        for symbol, asset in self.assets.items():
            current_values[symbol] = asset.current_value
        
        # Calculate required trades
        trades = []
        for symbol, target_value in target_values.items():
            current_value = current_values.get(symbol, 0)
            diff = target_value - current_value
            
            if abs(diff) > 100:  # Minimum trade threshold
                if symbol == "cash":
                    # Adjust cash by buying/selling assets
                    pass
                else:
                    if diff > 0:
                        # Buy more of this asset
                        trades.append({"symbol": symbol, "action": "buy", "value": diff})
                    else:
                        # Sell some of this asset
                        trades.append({"symbol": symbol, "action": "sell", "value": abs(diff)})
        
        return trades
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get portfolio performance metrics"""
        if not self.assets:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "best_performing_asset": None,
                "worst_performing_asset": None
            }
        
        winning_assets = sum(1 for asset in self.assets.values() if asset.realized_pnl > 0)
        losing_assets = sum(1 for asset in self.assets.values() if asset.realized_pnl < 0)
        
        best_asset = max(self.assets.values(), key=lambda a: a.realized_pnl) if self.assets else None
        worst_asset = min(self.assets.values(), key=lambda a: a.realized_pnl) if self.assets else None
        
        return {
            "total_trades": len(self.assets),
            "winning_trades": winning_assets,
            "losing_trades": losing_assets,
            "win_rate": (winning_assets / len(self.assets)) * 100 if self.assets else 0,
            "best_performing_asset": best_asset.symbol if best_asset else None,
            "worst_performing_asset": worst_asset.symbol if worst_asset else None
        }
    
    def reset(self):
        """Reset portfolio to initial state"""
        self.available_cash = self.initial_capital
        self.assets.clear()
        self.total_value = self.initial_capital
        self.total_pnl = 0.0
        self.total_return = 0.0
