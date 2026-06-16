from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from models import Prediction


class BacktestStrategy(ABC):
    """Base class for backtesting strategies"""
    
    def __init__(self, name: str):
        self.name = name
        self.trades = []
        self.balance = 10000.0
        self.initial_balance = 10000.0
        self.position = None
        self.entry_price = None
        self.entry_time = None
    
    @abstractmethod
    def generate_signal(self, data: Dict[str, Any]) -> Optional[Prediction]:
        """Generate trading signal based on data"""
        pass
    
    def execute_trade(self, prediction: Prediction, price: float, amount: float = 1.0) -> Dict[str, Any]:
        """Execute a trade in backtest"""
        trade = {
            "type": prediction.type,
            "direction": prediction.direction,
            "entry_price": price,
            "amount": amount,
            "confidence": prediction.confidence,
            "entry_time": datetime.now().isoformat(),
            "exit_price": None,
            "exit_time": None,
            "profit": None,
            "reason": prediction.reason
        }
        
        self.trades.append(trade)
        return trade
    
    def close_trade(self, trade: Dict[str, Any], exit_price: float) -> Dict[str, Any]:
        """Close a trade and calculate profit"""
        trade["exit_price"] = exit_price
        trade["exit_time"] = datetime.now().isoformat()
        
        # Calculate profit based on direction
        if trade["direction"] == "CALL":
            profit = (exit_price - trade["entry_price"]) * 100 * trade["amount"]
        elif trade["direction"] == "PUT":
            profit = (trade["entry_price"] - exit_price) * 100 * trade["amount"]
        else:
            profit = 0
        
        trade["profit"] = profit
        self.balance += profit
        
        return trade
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get backtest statistics"""
        completed_trades = [t for t in self.trades if t["profit"] is not None]
        
        if not completed_trades:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "total_profit": 0,
                "final_balance": self.balance,
                "roi": 0
            }
        
        wins = sum(1 for t in completed_trades if t["profit"] > 0)
        losses = sum(1 for t in completed_trades if t["profit"] < 0)
        total_profit = sum(t["profit"] for t in completed_trades)
        
        return {
            "total_trades": len(completed_trades),
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / len(completed_trades)) * 100 if completed_trades else 0,
            "total_profit": total_profit,
            "final_balance": self.balance,
            "roi": ((self.balance - self.initial_balance) / self.initial_balance) * 100,
            "avg_win": sum(t["profit"] for t in completed_trades if t["profit"] > 0) / wins if wins > 0 else 0,
            "avg_loss": sum(t["profit"] for t in completed_trades if t["profit"] < 0) / losses if losses > 0 else 0,
            "max_drawdown": self._calculate_max_drawdown()
        }
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        if not self.trades:
            return 0
        
        balance_history = [self.initial_balance]
        running_balance = self.initial_balance
        
        for trade in self.trades:
            if trade["profit"] is not None:
                running_balance += trade["profit"]
                balance_history.append(running_balance)
        
        peak = balance_history[0]
        max_drawdown = 0
        
        for balance in balance_history:
            if balance > peak:
                peak = balance
            drawdown = (peak - balance) / peak if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown * 100
    
    def reset(self):
        """Reset strategy state"""
        self.trades = []
        self.balance = self.initial_balance
        self.position = None
        self.entry_price = None
        self.entry_time = None
