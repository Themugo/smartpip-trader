import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class StatsManager:
    """Manages trading statistics"""
    
    def __init__(self):
        self.stats = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "total_profit": 0,
            "session_pnl": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "avg_win": 0,
            "avg_loss": 0
        }
    
    def update_stats(self, profit: float):
        """Update statistics with trade result"""
        self.stats["total_trades"] += 1
        self.stats["session_pnl"] += profit
        self.stats["total_profit"] += profit
        
        if profit > 0:
            self.stats["wins"] += 1
            if profit > self.stats["best_trade"]:
                self.stats["best_trade"] = profit
            logger.info(f"✅ WIN: +${profit:.2f}")
        else:
            self.stats["losses"] += 1
            if profit < self.stats["worst_trade"]:
                self.stats["worst_trade"] = profit
            logger.info(f"❌ LOSS: ${profit:.2f}")
        
        # Update win rate
        if self.stats["total_trades"] > 0:
            self.stats["win_rate"] = (self.stats["wins"] / self.stats["total_trades"]) * 100
    
    def update_averages(self, trade_history: list):
        """Update average win/loss from trade history"""
        wins = [t.get("profit", 0) for t in trade_history if t.get("profit", 0) > 0]
        losses = [t.get("profit", 0) for t in trade_history if t.get("profit", 0) < 0]
        self.stats["avg_win"] = sum(wins) / len(wins) if wins else 0
        self.stats["avg_loss"] = sum(losses) / len(losses) if losses else 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return self.stats
    
    def reset_stats(self):
        """Reset all statistics"""
        self.stats = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "total_profit": 0,
            "session_pnl": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "avg_win": 0,
            "avg_loss": 0
        }
