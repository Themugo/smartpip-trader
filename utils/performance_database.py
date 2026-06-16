import sqlite3
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import defaultdict
import json


class PerformanceDatabase:
    """Database for tracking real trading performance with Deriv data"""
    
    def __init__(self, db_path: str = "performance.db"):
        self.db_path = db_path
        self.conn = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database schema"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                market TEXT NOT NULL,
                direction TEXT NOT NULL,
                amount REAL NOT NULL,
                confidence REAL NOT NULL,
                entry_price REAL,
                exit_price REAL,
                profit REAL,
                strategy TEXT,
                analysis_type TEXT,
                volatility_regime TEXT,
                trend_regime TEXT,
                digit_regime TEXT,
                digits TEXT,
                market_flow TEXT,
                status TEXT
            )
        """)
        
        # Strategy performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                avg_win REAL,
                avg_loss REAL,
                profit_factor REAL,
                total_profit REAL
            )
        """)
        
        # Market performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                avg_profit REAL,
                total_profit REAL,
                volatility_regime TEXT,
                trend_regime TEXT
            )
        """)
        
        # Time performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hour INTEGER NOT NULL,
                day_of_week INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                avg_profit REAL,
                total_profit REAL
            )
        """)
        
        # Regime performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regime_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volatility_regime TEXT,
                trend_regime TEXT,
                digit_regime TEXT,
                timestamp TEXT NOT NULL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                avg_profit REAL
            )
        """)
        
        # Daily summary table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                total_profit REAL,
                max_drawdown REAL,
                sharpe_ratio REAL,
                best_market TEXT,
                best_strategy TEXT
            )
        """)
        
        self.conn.commit()
    
    def record_trade(self, trade_data: Dict[str, Any]):
        """Record a trade with real Deriv data"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO trades (
                timestamp, market, direction, amount, confidence,
                entry_price, exit_price, profit, strategy, analysis_type,
                volatility_regime, trend_regime, digit_regime,
                digits, market_flow, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_data.get("timestamp", datetime.now().isoformat()),
            trade_data.get("market", ""),
            trade_data.get("direction", ""),
            trade_data.get("amount", 0),
            trade_data.get("confidence", 0),
            trade_data.get("entry_price"),
            trade_data.get("exit_price"),
            trade_data.get("profit"),
            trade_data.get("strategy", ""),
            trade_data.get("analysis_type", ""),
            trade_data.get("volatility_regime", ""),
            trade_data.get("trend_regime", ""),
            trade_data.get("digit_regime", ""),
            json.dumps(trade_data.get("digits", [])),
            json.dumps(trade_data.get("market_flow", {})),
            trade_data.get("status", "completed")
        ))
        
        self.conn.commit()
        
        # Update performance tables
        self._update_strategy_performance(trade_data)
        self._update_market_performance(trade_data)
        self._update_time_performance(trade_data)
        self._update_regime_performance(trade_data)
    
    def _update_strategy_performance(self, trade_data: Dict[str, Any]):
        """Update strategy performance metrics"""
        cursor = self.conn.cursor()
        
        strategy = trade_data.get("strategy", "unified")
        profit = trade_data.get("profit", 0)
        
        # Get current performance
        cursor.execute("""
            SELECT total_trades, winning_trades, losing_trades, total_profit
            FROM strategy_performance
            WHERE strategy = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (strategy,))
        
        result = cursor.fetchone()
        
        if result:
            total_trades = result["total_trades"] + 1
            winning_trades = result["winning_trades"] + (1 if profit > 0 else 0)
            losing_trades = result["losing_trades"] + (1 if profit < 0 else 0)
            total_profit = result["total_profit"] + profit
        else:
            total_trades = 1
            winning_trades = 1 if profit > 0 else 0
            losing_trades = 1 if profit < 0 else 0
            total_profit = profit
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Calculate average win and loss
        cursor.execute("""
            SELECT AVG(profit) as avg_profit
            FROM trades
            WHERE strategy = ? AND profit > 0
        """, (strategy,))
        avg_win = cursor.fetchone()["avg_profit"] or 0
        
        cursor.execute("""
            SELECT AVG(profit) as avg_loss
            FROM trades
            WHERE strategy = ? AND profit < 0
        """, (strategy,))
        avg_loss = abs(cursor.fetchone()["avg_loss"] or 0)
        
        profit_factor = (avg_win / avg_loss) if avg_loss > 0 else 0
        
        cursor.execute("""
            INSERT INTO strategy_performance (
                strategy, timestamp, total_trades, winning_trades,
                losing_trades, win_rate, avg_win, avg_loss, profit_factor, total_profit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strategy,
            datetime.now().isoformat(),
            total_trades,
            winning_trades,
            losing_trades,
            win_rate,
            avg_win,
            avg_loss,
            profit_factor,
            total_profit
        ))
        
        self.conn.commit()
    
    def _update_market_performance(self, trade_data: Dict[str, Any]):
        """Update market performance metrics"""
        cursor = self.conn.cursor()
        
        market = trade_data.get("market", "")
        profit = trade_data.get("profit", 0)
        volatility_regime = trade_data.get("volatility_regime", "")
        trend_regime = trade_data.get("trend_regime", "")
        
        # Get current performance
        cursor.execute("""
            SELECT total_trades, winning_trades, losing_trades, total_profit
            FROM market_performance
            WHERE market = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (market,))
        
        result = cursor.fetchone()
        
        if result:
            total_trades = result["total_trades"] + 1
            winning_trades = result["winning_trades"] + (1 if profit > 0 else 0)
            losing_trades = result["losing_trades"] + (1 if profit < 0 else 0)
            total_profit = result["total_profit"] + profit
        else:
            total_trades = 1
            winning_trades = 1 if profit > 0 else 0
            losing_trades = 1 if profit < 0 else 0
            total_profit = profit
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        cursor.execute("""
            INSERT INTO market_performance (
                market, timestamp, total_trades, winning_trades,
                losing_trades, win_rate, avg_profit, total_profit,
                volatility_regime, trend_regime
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            market,
            datetime.now().isoformat(),
            total_trades,
            winning_trades,
            losing_trades,
            win_rate,
            avg_profit,
            total_profit,
            volatility_regime,
            trend_regime
        ))
        
        self.conn.commit()
    
    def _update_time_performance(self, trade_data: Dict[str, Any]):
        """Update time-based performance metrics"""
        cursor = self.conn.cursor()
        
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()
        profit = trade_data.get("profit", 0)
        
        # Get current performance
        cursor.execute("""
            SELECT total_trades, winning_trades, losing_trades, total_profit
            FROM time_performance
            WHERE hour = ? AND day_of_week = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (hour, day_of_week))
        
        result = cursor.fetchone()
        
        if result:
            total_trades = result["total_trades"] + 1
            winning_trades = result["winning_trades"] + (1 if profit > 0 else 0)
            losing_trades = result["losing_trades"] + (1 if profit < 0 else 0)
            total_profit = result["total_profit"] + profit
        else:
            total_trades = 1
            winning_trades = 1 if profit > 0 else 0
            losing_trades = 1 if profit < 0 else 0
            total_profit = profit
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        cursor.execute("""
            INSERT INTO time_performance (
                hour, day_of_week, timestamp, total_trades, winning_trades,
                losing_trades, win_rate, avg_profit, total_profit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hour,
            day_of_week,
            datetime.now().isoformat(),
            total_trades,
            winning_trades,
            losing_trades,
            win_rate,
            avg_profit,
            total_profit
        ))
        
        self.conn.commit()
    
    def _update_regime_performance(self, trade_data: Dict[str, Any]):
        """Update regime-based performance metrics"""
        cursor = self.conn.cursor()
        
        volatility_regime = trade_data.get("volatility_regime", "")
        trend_regime = trade_data.get("trend_regime", "")
        digit_regime = trade_data.get("digit_regime", "")
        profit = trade_data.get("profit", 0)
        
        # Get current performance
        cursor.execute("""
            SELECT total_trades, winning_trades, losing_trades
            FROM regime_performance
            WHERE volatility_regime = ? AND trend_regime = ? AND digit_regime = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (volatility_regime, trend_regime, digit_regime))
        
        result = cursor.fetchone()
        
        if result:
            total_trades = result["total_trades"] + 1
            winning_trades = result["winning_trades"] + (1 if profit > 0 else 0)
            losing_trades = result["losing_trades"] + (1 if profit < 0 else 0)
        else:
            total_trades = 1
            winning_trades = 1 if profit > 0 else 0
            losing_trades = 1 if profit < 0 else 0
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        cursor.execute("""
            SELECT AVG(profit) as avg_profit
            FROM trades
            WHERE volatility_regime = ? AND trend_regime = ? AND digit_regime = ?
        """, (volatility_regime, trend_regime, digit_regime))
        avg_profit = cursor.fetchone()["avg_profit"] or 0
        
        cursor.execute("""
            INSERT INTO regime_performance (
                volatility_regime, trend_regime, digit_regime, timestamp,
                total_trades, winning_trades, losing_trades, win_rate, avg_profit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            volatility_regime,
            trend_regime,
            digit_regime,
            datetime.now().isoformat(),
            total_trades,
            winning_trades,
            losing_trades,
            win_rate,
            avg_profit
        ))
        
        self.conn.commit()
    
    def get_strategy_performance(self, strategy: str = None) -> Dict[str, Any]:
        """Get strategy performance metrics"""
        cursor = self.conn.cursor()
        
        if strategy:
            cursor.execute("""
                SELECT * FROM strategy_performance
                WHERE strategy = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (strategy,))
            result = cursor.fetchone()
            
            if result:
                return dict(result)
        else:
            cursor.execute("""
                SELECT * FROM strategy_performance
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            results = cursor.fetchall()
            return [dict(r) for r in results]
        
        return {}
    
    def get_market_performance(self, market: str = None) -> Dict[str, Any]:
        """Get market performance metrics"""
        cursor = self.conn.cursor()
        
        if market:
            cursor.execute("""
                SELECT * FROM market_performance
                WHERE market = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (market,))
            result = cursor.fetchone()
            
            if result:
                return dict(result)
        else:
            cursor.execute("""
                SELECT * FROM market_performance
                ORDER BY timestamp DESC
                LIMIT 12
            """)
            results = cursor.fetchall()
            return [dict(r) for r in results]
        
        return {}
    
    def get_time_performance(self) -> List[Dict[str, Any]]:
        """Get time-based performance metrics"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM time_performance
            ORDER BY timestamp DESC
            LIMIT 24
        """)
        results = cursor.fetchall()
        return [dict(r) for r in results]
    
    def get_regime_performance(self) -> List[Dict[str, Any]]:
        """Get regime-based performance metrics"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM regime_performance
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        results = cursor.fetchall()
        return [dict(r) for r in results]
    
    def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trades"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM trades
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        results = cursor.fetchall()
        return [dict(r) for r in results]
    
    def get_daily_summary(self, date: str = None) -> Dict[str, Any]:
        """Get daily performance summary"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM daily_summary
            WHERE date = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (date,))
        result = cursor.fetchone()
        
        if result:
            return dict(result)
        
        # Calculate summary if not exists
        return self._calculate_daily_summary(date)
    
    def _calculate_daily_summary(self, date: str) -> Dict[str, Any]:
        """Calculate daily summary from trades"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(profit) as total_profit
            FROM trades
            WHERE DATE(timestamp) = ?
        """, (date,))
        
        result = cursor.fetchone()
        
        if not result or result["total_trades"] == 0:
            return {}
        
        win_rate = result["winning_trades"] / result["total_trades"]
        
        # Calculate max drawdown
        cursor.execute("""
            SELECT profit FROM trades
            WHERE DATE(timestamp) = ?
            ORDER BY timestamp
        """, (date,))
        trades = cursor.fetchall()
        
        max_drawdown = 0
        peak = 0
        for trade in trades:
            peak = max(peak, peak + trade["profit"])
            drawdown = peak - (peak + trade["profit"])
            max_drawdown = max(max_drawdown, drawdown)
        
        # Find best market
        cursor.execute("""
            SELECT market, SUM(profit) as total_profit
            FROM trades
            WHERE DATE(timestamp) = ?
            GROUP BY market
            ORDER BY total_profit DESC
            LIMIT 1
        """, (date,))
        best_market_result = cursor.fetchone()
        best_market = best_market_result["market"] if best_market_result else None
        
        # Find best strategy
        cursor.execute("""
            SELECT strategy, SUM(profit) as total_profit
            FROM trades
            WHERE DATE(timestamp) = ?
            GROUP BY strategy
            ORDER BY total_profit DESC
            LIMIT 1
        """, (date,))
        best_strategy_result = cursor.fetchone()
        best_strategy = best_strategy_result["strategy"] if best_strategy_result else None
        
        summary = {
            "date": date,
            "total_trades": result["total_trades"],
            "winning_trades": result["winning_trades"],
            "losing_trades": result["losing_trades"],
            "win_rate": win_rate,
            "total_profit": result["total_profit"],
            "max_drawdown": max_drawdown,
            "best_market": best_market,
            "best_strategy": best_strategy
        }
        
        # Store summary
        cursor.execute("""
            INSERT INTO daily_summary (
                date, total_trades, winning_trades, losing_trades,
                win_rate, total_profit, max_drawdown, best_market, best_strategy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date,
            summary["total_trades"],
            summary["winning_trades"],
            summary["losing_trades"],
            summary["win_rate"],
            summary["total_profit"],
            summary["max_drawdown"],
            summary["best_market"],
            summary["best_strategy"]
        ))
        
        self.conn.commit()
        
        return summary
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
