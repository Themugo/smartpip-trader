import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database persistence for trades and statistics"""
    
    def __init__(self, db_path: str = "trading.db"):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._initialize_database()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _initialize_database(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    market TEXT NOT NULL,
                    type TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    amount REAL NOT NULL,
                    confidence REAL NOT NULL,
                    reason TEXT,
                    entry_price REAL NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    profit REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_trades INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    total_profit REAL DEFAULT 0,
                    session_pnl REAL DEFAULT 0,
                    best_trade REAL DEFAULT 0,
                    worst_trade REAL DEFAULT 0,
                    avg_win REAL DEFAULT 0,
                    avg_loss REAL DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(market)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name ON performance_metrics(metric_name)")
            
            # Initialize statistics row if not exists
            cursor.execute("INSERT OR IGNORE INTO statistics (id) VALUES (1)")
    
    def save_trade(self, trade: Dict[str, Any]) -> bool:
        """
        Save trade to database
        
        Args:
            trade: Trade data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO trades 
                    (id, market, type, direction, amount, confidence, reason, entry_price, entry_time, exit_time, profit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade.get("id"),
                    trade.get("market"),
                    trade.get("type"),
                    trade.get("direction"),
                    trade.get("amount"),
                    trade.get("confidence"),
                    trade.get("reason"),
                    trade.get("entry_price"),
                    trade.get("entry_time"),
                    trade.get("exit_time"),
                    trade.get("profit")
                ))
                return True
        except Exception as e:
            logger.error(f"Failed to save trade: {e}")
            return False
    
    def get_trade(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """
        Get trade by ID
        
        Args:
            trade_id: Trade ID
            
        Returns:
            Trade data or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_recent_trades(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent trades
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of trade data
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades 
                ORDER BY entry_time DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trades_by_market(self, market: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get trades for specific market
        
        Args:
            market: Market symbol
            limit: Maximum number of trades to return
            
        Returns:
            List of trade data
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades 
                WHERE market = ?
                ORDER BY entry_time DESC 
                LIMIT ?
            """, (market, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_statistics(self, stats: Dict[str, Any]) -> bool:
        """
        Update statistics in database
        
        Args:
            stats: Statistics dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE statistics SET
                        total_trades = ?,
                        wins = ?,
                        losses = ?,
                        win_rate = ?,
                        total_profit = ?,
                        session_pnl = ?,
                        best_trade = ?,
                        worst_trade = ?,
                        avg_win = ?,
                        avg_loss = ?,
                        updated_at = ?
                    WHERE id = 1
                """, (
                    stats.get("total_trades", 0),
                    stats.get("wins", 0),
                    stats.get("losses", 0),
                    stats.get("win_rate", 0),
                    stats.get("total_profit", 0),
                    stats.get("session_pnl", 0),
                    stats.get("best_trade", 0),
                    stats.get("worst_trade", 0),
                    stats.get("avg_win", 0),
                    stats.get("avg_loss", 0),
                    datetime.now().isoformat()
                ))
                return True
        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")
            return False
    
    def get_statistics(self) -> Optional[Dict[str, Any]]:
        """
        Get current statistics
        
        Returns:
            Statistics dictionary or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM statistics WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def save_performance_metric(self, metric_name: str, metric_value: float) -> bool:
        """
        Save performance metric
        
        Args:
            metric_name: Name of the metric
            metric_value: Value of the metric
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO performance_metrics (metric_name, metric_value)
                    VALUES (?, ?)
                """, (metric_name, metric_value))
                return True
        except Exception as e:
            logger.error(f"Failed to save performance metric: {e}")
            return False
    
    def get_performance_metrics(self, metric_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get performance metrics for a specific metric
        
        Args:
            metric_name: Name of the metric
            limit: Maximum number of records to return
            
        Returns:
            List of metric data
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM performance_metrics 
                WHERE metric_name = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (metric_name, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trade_statistics_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for trades
        
        Returns:
            Dictionary with trade statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total trades
            cursor.execute("SELECT COUNT(*) as count FROM trades")
            total_trades = cursor.fetchone()["count"]
            
            # Total profit
            cursor.execute("SELECT SUM(profit) as total FROM trades WHERE profit IS NOT NULL")
            total_profit = cursor.fetchone()["total"] or 0
            
            # Win rate
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN profit > 0 THEN 1 END) as wins,
                    COUNT(CASE WHEN profit < 0 THEN 1 END) as losses
                FROM trades WHERE profit IS NOT NULL
            """)
            row = cursor.fetchone()
            wins = row["wins"] or 0
            losses = row["losses"] or 0
            win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
            
            # Average win/loss
            cursor.execute("SELECT AVG(profit) as avg FROM trades WHERE profit > 0")
            avg_win = cursor.fetchone()["avg"] or 0
            
            cursor.execute("SELECT AVG(profit) as avg FROM trades WHERE profit < 0")
            avg_loss = cursor.fetchone()["avg"] or 0
            
            return {
                "total_trades": total_trades,
                "total_profit": total_profit,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss
            }
    
    def cleanup_old_metrics(self, days: int = 7):
        """
        Clean up old performance metrics
        
        Args:
            days: Keep metrics from last N days
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM performance_metrics 
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            """, (days,))
            deleted = cursor.rowcount
            logger.info(f"Cleaned up {deleted} old performance metrics")
