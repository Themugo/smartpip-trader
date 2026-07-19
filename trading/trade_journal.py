"""
Trade Journal Engine — SQLite-backed journal for live trading.
Tracks entry/exit conditions, regime, confidence, P&L, and drawdown impact.
"""
import sqlite3
import json
import logging
import os
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta, timezone, timedelta
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("JOURNAL_DB_PATH", "journal.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    contract_type TEXT NOT NULL,
    entry_price REAL NOT NULL,
    entry_digit INTEGER,
    exit_price REAL,
    exit_digit INTEGER,
    duration_ticks INTEGER,
    amount REAL NOT NULL,
    confidence REAL NOT NULL,
    regime TEXT NOT NULL DEFAULT 'unknown',
    entry_conditions TEXT NOT NULL DEFAULT '[]',
    exit_conditions TEXT NOT NULL DEFAULT '[]',
    exit_reason TEXT,
    pnl REAL,
    running_balance REAL NOT NULL DEFAULT 1000,
    peak_balance REAL NOT NULL DEFAULT 1000,
    drawdown_impact REAL NOT NULL DEFAULT 0,
    entropy REAL,
    streak INTEGER,
    chi2 REAL,
    rsi REAL,
    macd REAL,
    score INTEGER,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    closed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_regime ON trades(regime);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);

CREATE TABLE IF NOT EXISTS weekly_insights_cache (
    week_start TEXT PRIMARY KEY,
    generated_at TEXT NOT NULL,
    insights TEXT NOT NULL
);
"""


class TradeJournal:
    """SQLite-backed trade journal with full condition tracking."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()
        self._peak_balance: float = 1000.0  # track running peak

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript(SCHEMA)
        logger.info("Trade journal initialised at %s", self.db_path)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Write API ─────────────────────────────────────────────────────────

    def log_trade(
        self,
        symbol: str,
        contract_type: str,
        entry_price: float,
        amount: float,
        confidence: float,
        regime: str,
        entry_conditions: List[str],
        entry_digit: Optional[int] = None,
        entropy: Optional[float] = None,
        streak: Optional[int] = None,
        chi2: Optional[float] = None,
        rsi: Optional[float] = None,
        macd: Optional[float] = None,
        score: Optional[int] = None,
        running_balance: float = 1000.0,
        notes: Optional[str] = None,
    ) -> str:
        """Log a new trade entry. Returns the trade ID."""
        trade_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Update peak balance
        if running_balance > self._peak_balance:
            self._peak_balance = running_balance

        with self._conn() as conn:
            conn.execute("""
                INSERT INTO trades (
                    id, timestamp, symbol, contract_type, entry_price, entry_digit,
                    amount, confidence, regime, entry_conditions, entropy, streak,
                    chi2, rsi, macd, score, running_balance, peak_balance,
                    drawdown_impact, notes, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
            """, (
                trade_id, now, symbol, contract_type, entry_price, entry_digit,
                amount, confidence, regime, json.dumps(entry_conditions),
                entropy, streak, chi2, rsi, macd, score,
                running_balance, self._peak_balance,
                max(0, (self._peak_balance - running_balance) / self._peak_balance * 100),
                notes, now,
            ))

        logger.info("Trade logged: %s %s %s conf=%.1f%%", trade_id[:8], symbol, contract_type, confidence)
        return trade_id

    def close_trade(
        self,
        trade_id: str,
        pnl: float,
        exit_price: float,
        exit_digit: Optional[int] = None,
        exit_conditions: Optional[List[str]] = None,
        exit_reason: str = "contract_settled",
        duration_ticks: Optional[int] = None,
        running_balance: float = 1000.0,
    ) -> bool:
        """Close a trade and record outcome, P&L, and drawdown impact."""
        now = datetime.now(timezone.utc).isoformat()
        exit_conditions = exit_conditions or []

        if running_balance > self._peak_balance:
            self._peak_balance = running_balance
        dd_impact = max(0, (self._peak_balance - running_balance) / self._peak_balance * 100)

        with self._conn() as conn:
            cur = conn.execute("""
                UPDATE trades SET
                    exit_price=?, exit_digit=?, duration_ticks=?,
                    exit_conditions=?, exit_reason=?,
                    pnl=?, running_balance=?, peak_balance=?, drawdown_impact=?,
                    status='closed', closed_at=?
                WHERE id=? AND status='open'
            """, (
                exit_price, exit_digit, duration_ticks,
                json.dumps(exit_conditions), exit_reason,
                pnl, running_balance, self._peak_balance, dd_impact,
                now, trade_id,
            ))
            updated = cur.rowcount > 0

        if updated:
            outcome = "WIN" if pnl > 0 else "LOSS"
            logger.info("Trade closed: %s → %s P&L=$%.4f DD=%.2f%%", trade_id[:8], outcome, pnl, dd_impact)
        return updated

    def add_note(self, trade_id: str, note: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("UPDATE trades SET notes=? WHERE id=?", (note, trade_id))
            return cur.rowcount > 0

    # ── Read API ──────────────────────────────────────────────────────────

    def get_trades(
        self,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        regime: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict]:
        filters, params = [], []
        if status:
            filters.append("status=?"); params.append(status)
        if symbol:
            filters.append("symbol=?"); params.append(symbol)
        if regime:
            filters.append("regime=?"); params.append(regime)
        if since:
            filters.append("timestamp >= ?"); params.append(since)
        if until:
            filters.append("timestamp <= ?"); params.append(until)

        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        params.extend([limit, offset])

        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM trades {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_trade(self, trade_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM trades WHERE id=?", (trade_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def get_week_trades(self, week_start: Optional[datetime] = None) -> List[Dict]:
        now = datetime.now(timezone.utc)
        if week_start is None:
            days_back = now.weekday()
            week_start = (now - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)
        return self.get_trades(
            since=week_start.isoformat(),
            until=week_end.isoformat(),
            limit=1000,
        )

    def get_open_trades(self) -> List[Dict]:
        return self.get_trades(status="open")

    def get_summary(self) -> Dict[str, Any]:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
            closed = conn.execute("SELECT COUNT(*) FROM trades WHERE status='closed'").fetchone()[0]
            wins = conn.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0").fetchone()[0]
            total_pnl = conn.execute("SELECT COALESCE(SUM(pnl),0) FROM trades WHERE status='closed'").fetchone()[0]
            last = conn.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 1").fetchone()
        wr = round(wins / closed * 100, 1) if closed > 0 else 0
        return {
            "total_trades": total,
            "closed_trades": closed,
            "open_trades": total - closed,
            "wins": wins,
            "losses": closed - wins,
            "win_rate": wr,
            "total_pnl": round(total_pnl, 4),
            "last_trade": self._row_to_dict(last) if last else None,
        }

    def cache_weekly_insights(self, week_start: str, insights: Dict):
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO weekly_insights_cache (week_start, generated_at, insights)
                VALUES (?, ?, ?)
            """, (week_start, datetime.now(timezone.utc).isoformat(), json.dumps(insights)))

    def get_cached_insights(self, week_start: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM weekly_insights_cache WHERE week_start=?", (week_start,)
            ).fetchone()
        if not row:
            return None
        # Expire cache after 6 hours
        generated = datetime.fromisoformat(row["generated_at"].replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - generated).total_seconds() > 21600:
            return None
        return json.loads(row["insights"])

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row) -> Dict:
        if row is None:
            return {}
        d = dict(row)
        for key in ("entry_conditions", "exit_conditions"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    d[key] = [d[key]]
        return d
