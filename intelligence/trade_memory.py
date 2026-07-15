"""
Trade Memory — feature-store for continual learning.

Stores every trade with full market context in a SQLite database, enabling
historical similarity retrieval, feature-matrix extraction for ML, and
comprehensive performance analytics.
"""

import json
import logging
import math
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

DEFAULT_DB_PATH = os.getenv("TRADE_MEMORY_DB_PATH", "trades_memory.db")
RETENTION_DAYS = 90

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    trade_id        TEXT PRIMARY KEY,
    timestamp       REAL    NOT NULL,
    market          TEXT    NOT NULL,
    direction       TEXT    NOT NULL,
    amount          REAL    NOT NULL,
    entry_price     REAL    NOT NULL,
    exit_price      REAL,
    profit          REAL,
    pnl_pct         REAL,
    confidence      REAL    NOT NULL,
    analyzer_outputs TEXT   NOT NULL DEFAULT '{}',
    market_features  TEXT   NOT NULL DEFAULT '{}',
    regime          TEXT    NOT NULL DEFAULT 'unknown',
    entropy         REAL,
    volatility      REAL,
    digit_pattern   TEXT    NOT NULL DEFAULT '[]',
    outcome         TEXT    NOT NULL DEFAULT 'OPEN',
    duration_seconds REAL,
    metadata        TEXT    NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_trades_ts       ON trades(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_market   ON trades(market);
CREATE INDEX IF NOT EXISTS idx_trades_regime   ON trades(regime);
CREATE INDEX IF NOT EXISTS idx_trades_outcome  ON trades(outcome);
"""


# ── Dataclass ────────────────────────────────────────────────────────────

@dataclass
class TradeRecord:
    """Immutable record of a single completed trade.

    Attributes:
        trade_id: Unique identifier (UUID4).
        timestamp: Unix epoch time when the trade was opened.
        market: Market symbol (e.g. ``"Volatility 75"``).
        direction: ``"CALL"`` or ``"PUT"``.
        amount: Position size in account currency.
        entry_price: Price at entry.
        exit_price: Price at exit.
        profit: Absolute profit/loss in account currency.
        pnl_pct: Profit/loss as percentage of amount.
        confidence: Confidence at time of trade [0-100].
        analyzer_outputs: Raw output dict from all analyzers.
        market_features: Extracted market features at time of trade.
        regime: Market regime label from ``RegimeDetector``.
        entropy: Shannon entropy at time of trade.
        volatility: Annualised volatility at time of trade.
        digit_pattern: List of recent digits at time of trade.
        outcome: ``"WIN"`` / ``"LOSS"`` / ``"BREAK_EVEN"`` / ``"OPEN"``.
        duration_seconds: Trade duration in seconds.
        metadata: Arbitrary extra data.
    """
    trade_id: str
    timestamp: float
    market: str
    direction: str
    amount: float
    entry_price: float
    exit_price: float = 0.0
    profit: float = 0.0
    pnl_pct: float = 0.0
    confidence: float = 0.0
    analyzer_outputs: Dict[str, Any] = field(default_factory=dict)
    market_features: Dict[str, Any] = field(default_factory=dict)
    regime: str = "unknown"
    entropy: float = 0.0
    volatility: float = 0.0
    digit_pattern: List[int] = field(default_factory=list)
    outcome: str = "OPEN"
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary."""
        return {
            "trade_id": self.trade_id,
            "timestamp": self.timestamp,
            "market": self.market,
            "direction": self.direction,
            "amount": self.amount,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "profit": self.profit,
            "pnl_pct": self.pnl_pct,
            "confidence": self.confidence,
            "analyzer_outputs": self.analyzer_outputs,
            "market_features": self.market_features,
            "regime": self.regime,
            "entropy": self.entropy,
            "volatility": self.volatility,
            "digit_pattern": self.digit_pattern,
            "outcome": self.outcome,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


# ── Feature vector helpers ──────────────────────────────────────────────

# Canonical feature order for cosine-similarity and ML extraction
_FEATURE_KEYS: List[str] = [
    "confidence",
    "entropy",
    "volatility",
    "entry_price",
    "amount",
    "direction_sign",
    "regime_trending_up",
    "regime_trending_down",
    "regime_mean_reverting",
    "regime_random",
    "regime_high_volatility",
    "regime_low_volatility",
    "digit_mean",
    "digit_std",
    "hour_sin",
    "hour_cos",
]

_REGIME_ONE_HOT = {
    "TRENDING_UP": 0,
    "TRENDING_DOWN": 1,
    "MEAN_REVERTING": 2,
    "RANDOM": 3,
    "HIGH_VOLATILITY": 4,
    "LOW_VOLATILITY": 5,
}


def _record_to_feature_vector(record: TradeRecord) -> List[float]:
    """Convert a TradeRecord into a fixed-length numeric feature vector."""
    regime = record.regime.upper()
    hour = datetime.fromtimestamp(record.timestamp, tz=timezone.utc).hour

    digits = record.digit_pattern if record.digit_pattern else []
    digit_mean = float(np.mean(digits)) if digits else 5.0
    digit_std = float(np.std(digits)) if digits else 3.0

    direction_sign = 1.0 if record.direction.upper() == "CALL" else -1.0

    regime_oh = [0.0] * 6
    idx = _REGIME_ONE_HOT.get(regime)
    if idx is not None:
        regime_oh[idx] = 1.0

    return [
        record.confidence,
        record.entropy,
        record.volatility,
        record.entry_price,
        record.amount,
        direction_sign,
        *regime_oh,
        digit_mean,
        digit_std,
        math.sin(2 * math.pi * hour / 24),
        math.cos(2 * math.pi * hour / 24),
    ]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors."""
    a_arr = np.asarray(a, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))


# ── TradeMemory ──────────────────────────────────────────────────────────

class TradeMemory:
    """SQLite-backed trade memory with full context storage.

    Provides comprehensive query, analytics, and ML-ready feature extraction.

    Usage::

        memory = TradeMemory()
        memory.record_trade(trade_record)
        similar = memory.get_similar_trades(features, n=10)
        X, y = memory.get_feature_matrix()
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Create tables and indexes if they don't exist.  Enable WAL mode."""
        with self._conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.executescript(SCHEMA)
        logger.info("TradeMemory initialised at %s", self.db_path)

    @contextmanager
    def _conn(self):
        """Context-managed database connection with auto-commit."""
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

    # ── Serialisation helpers ─────────────────────────────────────────────

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> TradeRecord:
        """Convert a database row to a TradeRecord."""
        d = dict(row)
        return TradeRecord(
            trade_id=d["trade_id"],
            timestamp=d["timestamp"],
            market=d["market"],
            direction=d["direction"],
            amount=d["amount"],
            entry_price=d["entry_price"],
            exit_price=d.get("exit_price") or 0.0,
            profit=d.get("profit") or 0.0,
            pnl_pct=d.get("pnl_pct") or 0.0,
            confidence=d["confidence"],
            analyzer_outputs=json.loads(d.get("analyzer_outputs") or "{}"),
            market_features=json.loads(d.get("market_features") or "{}"),
            regime=d.get("regime") or "unknown",
            entropy=d.get("entropy") or 0.0,
            volatility=d.get("volatility") or 0.0,
            digit_pattern=json.loads(d.get("digit_pattern") or "[]"),
            outcome=d.get("outcome") or "OPEN",
            duration_seconds=d.get("duration_seconds") or 0.0,
            metadata=json.loads(d.get("metadata") or "{}"),
        )

    @staticmethod
    def _record_to_params(rec: TradeRecord) -> tuple:
        """Serialise a TradeRecord to a tuple for SQL insertion."""
        return (
            rec.trade_id,
            rec.timestamp,
            rec.market,
            rec.direction,
            rec.amount,
            rec.entry_price,
            rec.exit_price,
            rec.profit,
            rec.pnl_pct,
            rec.confidence,
            json.dumps(rec.analyzer_outputs),
            json.dumps(rec.market_features),
            rec.regime,
            rec.entropy,
            rec.volatility,
            json.dumps(rec.digit_pattern),
            rec.outcome,
            rec.duration_seconds,
            json.dumps(rec.metadata),
        )

    # ── Write API ─────────────────────────────────────────────────────────

    def record_trade(self, trade_record: TradeRecord) -> None:
        """Persist a trade record to the database.

        If a record with the same ``trade_id`` already exists it is
        overwritten (upsert).
        """
        try:
            params = self._record_to_params(trade_record)
            with self._conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO trades (
                        trade_id, timestamp, market, direction, amount,
                        entry_price, exit_price, profit, pnl_pct, confidence,
                        analyzer_outputs, market_features, regime, entropy,
                        volatility, digit_pattern, outcome, duration_seconds,
                        metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, params)
            logger.debug(
                "Trade recorded: %s %s %s %s conf=%.1f",
                trade_record.trade_id[:8], trade_record.market,
                trade_record.direction, trade_record.outcome,
                trade_record.confidence,
            )
        except Exception as exc:
            logger.error("Failed to record trade: %s", exc, exc_info=True)

    # ── Read API ──────────────────────────────────────────────────────────

    def get_recent(self, n: int = 100) -> List[TradeRecord]:
        """Return the *n* most recent trades, newest first."""
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?",
                    (n,),
                ).fetchall()
            return [self._row_to_record(r) for r in rows]
        except Exception as exc:
            logger.error("get_recent failed: %s", exc, exc_info=True)
            return []

    def get_by_market(self, market: str, n: int = 50) -> List[TradeRecord]:
        """Return up to *n* trades for a specific market."""
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE market = ? ORDER BY timestamp DESC LIMIT ?",
                    (market, n),
                ).fetchall()
            return [self._row_to_record(r) for r in rows]
        except Exception as exc:
            logger.error("get_by_market failed: %s", exc, exc_info=True)
            return []

    def get_by_regime(self, regime: str, n: int = 50) -> List[TradeRecord]:
        """Return up to *n* trades for a specific regime."""
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE regime = ? ORDER BY timestamp DESC LIMIT ?",
                    (regime, n),
                ).fetchall()
            return [self._row_to_record(r) for r in rows]
        except Exception as exc:
            logger.error("get_by_regime failed: %s", exc, exc_info=True)
            return []

    def get_winning_trades(self, n: int = 50) -> List[TradeRecord]:
        """Return up to *n* winning trades."""
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE outcome = 'WIN' ORDER BY timestamp DESC LIMIT ?",
                    (n,),
                ).fetchall()
            return [self._row_to_record(r) for r in rows]
        except Exception as exc:
            logger.error("get_winning_trades failed: %s", exc, exc_info=True)
            return []

    def get_losing_trades(self, n: int = 50) -> List[TradeRecord]:
        """Return up to *n* losing trades."""
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE outcome = 'LOSS' ORDER BY timestamp DESC LIMIT ?",
                    (n,),
                ).fetchall()
            return [self._row_to_record(r) for r in rows]
        except Exception as exc:
            logger.error("get_losing_trades failed: %s", exc, exc_info=True)
            return []

    # ── ML feature extraction ─────────────────────────────────────────────

    def get_feature_matrix(self) -> Tuple[List[List[float]], List[str]]:
        """Build a feature matrix from all closed trades.

        Returns:
            ``(features_list, outcomes_list)`` where each feature vector
            is a fixed-length list of floats and each outcome is ``"WIN"``
            or ``"LOSS"``.  Break-even trades are excluded.
        """
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE outcome IN ('WIN', 'LOSS') ORDER BY timestamp"
                ).fetchall()

            features: List[List[float]] = []
            outcomes: List[str] = []
            for row in rows:
                rec = self._row_to_record(row)
                fv = _record_to_feature_vector(rec)
                features.append(fv)
                outcomes.append(rec.outcome)
            return features, outcomes
        except Exception as exc:
            logger.error("get_feature_matrix failed: %s", exc, exc_info=True)
            return [], []

    # ── Similarity retrieval ──────────────────────────────────────────────

    def get_similar_trades(
        self,
        features: Dict[str, Any],
        n: int = 10,
    ) -> List[TradeRecord]:
        """Retrieve the *n* most similar past trades using cosine similarity.

        The *features* dict is converted to the canonical feature vector
        format used internally.
        """
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE outcome IN ('WIN', 'LOSS') ORDER BY timestamp DESC LIMIT 500"
                ).fetchall()

            if not rows:
                return []

            # Build query vector from the provided features dict
            query_vec = self._features_dict_to_vector(features)

            scored: List[Tuple[float, TradeRecord]] = []
            for row in rows:
                rec = self._row_to_record(row)
                rec_vec = _record_to_feature_vector(rec)
                sim = _cosine_similarity(query_vec, rec_vec)
                scored.append((sim, rec))

            scored.sort(key=lambda x: x[0], reverse=True)
            return [rec for _, rec in scored[:n]]
        except Exception as exc:
            logger.error("get_similar_trades failed: %s", exc, exc_info=True)
            return []

    @staticmethod
    def _features_dict_to_vector(features: Dict[str, Any]) -> List[float]:
        """Convert a loose feature dict to the canonical vector format."""
        regime = str(features.get("regime", "unknown")).upper()
        direction = str(features.get("direction", "CALL")).upper()
        hour = int(features.get("hour", 12))
        digits = features.get("digit_pattern", [])
        if isinstance(digits, str):
            try:
                digits = json.loads(digits)
            except Exception:
                digits = []

        digit_mean = float(np.mean(digits)) if digits else 5.0
        digit_std = float(np.std(digits)) if digits else 3.0
        direction_sign = 1.0 if direction == "CALL" else -1.0

        regime_oh = [0.0] * 6
        idx = _REGIME_ONE_HOT.get(regime)
        if idx is not None:
            regime_oh[idx] = 1.0

        return [
            float(features.get("confidence", 50.0)),
            float(features.get("entropy", 2.5)),
            float(features.get("volatility", 0.15)),
            float(features.get("entry_price", 0.0)),
            float(features.get("amount", 1.0)),
            direction_sign,
            *regime_oh,
            digit_mean,
            digit_std,
            math.sin(2 * math.pi * hour / 24),
            math.cos(2 * math.pi * hour / 24),
        ]

    # ── Statistics ────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Comprehensive trading statistics.

        Includes win rate, avg profit, Sharpe ratio, max drawdown, and
        per-market breakdown.
        """
        try:
            with self._conn() as conn:
                total = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
                closed = conn.execute(
                    "SELECT COUNT(*) FROM trades WHERE outcome != 'OPEN'"
                ).fetchone()[0]
                wins = conn.execute(
                    "SELECT COUNT(*) FROM trades WHERE outcome = 'WIN'"
                ).fetchone()[0]
                losses = conn.execute(
                    "SELECT COUNT(*) FROM trades WHERE outcome = 'LOSS'"
                ).fetchone()[0]
                be_count = conn.execute(
                    "SELECT COUNT(*) FROM trades WHERE outcome = 'BREAK_EVEN'"
                ).fetchone()[0]

                pnl_rows = conn.execute(
                    "SELECT profit FROM trades WHERE outcome != 'OPEN' ORDER BY timestamp"
                ).fetchall()

            stats: Dict[str, Any] = {
                "total_trades": total,
                "closed_trades": closed,
                "open_trades": total - closed,
                "wins": wins,
                "losses": losses,
                "break_even": be_count,
                "win_rate": round(wins / closed * 100, 2) if closed > 0 else 0.0,
            }

            if not pnl_rows:
                return stats

            pnls = [row["profit"] for row in pnl_rows]
            arr = np.array(pnls, dtype=np.float64)

            stats["total_pnl"] = round(float(arr.sum()), 4)
            stats["avg_profit"] = round(float(arr.mean()), 4)
            stats["median_profit"] = round(float(np.median(arr)), 4)
            stats["profit_std"] = round(float(arr.std()), 4)

            # Profit factor
            gross_profit = float(arr[arr > 0].sum()) if np.any(arr > 0) else 0.0
            gross_loss = float(np.abs(arr[arr < 0]).sum()) if np.any(arr < 0) else 0.0
            stats["profit_factor"] = round(
                gross_profit / gross_loss, 4
            ) if gross_loss > 0 else float("inf")

            # Sharpe ratio (annualised, assume ~252 trades/year)
            if len(arr) > 1 and float(arr.std()) > 0:
                mean_r = float(arr.mean())
                std_r = float(arr.std())
                stats["sharpe_ratio"] = round(
                    (mean_r / std_r) * math.sqrt(252), 4
                )
            else:
                stats["sharpe_ratio"] = 0.0

            # Max drawdown
            equity = np.cumsum(arr)
            running_max = np.maximum.accumulate(equity)
            drawdowns = running_max - equity
            max_dd = float(drawdowns.max())
            stats["max_drawdown"] = round(max_dd, 4)

            # Per-market breakdown
            with self._conn() as conn:
                market_rows = conn.execute(
                    "SELECT market, profit, outcome FROM trades WHERE outcome != 'OPEN'"
                ).fetchall()

            from collections import defaultdict
            market_data: Dict[str, Dict[str, Any]] = defaultdict(
                lambda: {"trades": 0, "wins": 0, "total_pnl": 0.0}
            )
            for row in market_rows:
                mkt = row["market"]
                market_data[mkt]["trades"] += 1
                market_data[mkt]["total_pnl"] += row["profit"]
                if row["outcome"] == "WIN":
                    market_data[mkt]["wins"] += 1

            market_breakdown: Dict[str, Dict[str, Any]] = {}
            for mkt, data in market_data.items():
                n = data["trades"]
                market_breakdown[mkt] = {
                    "trades": n,
                    "win_rate": round(data["wins"] / n * 100, 1) if n > 0 else 0,
                    "total_pnl": round(data["total_pnl"], 4),
                    "avg_pnl": round(data["total_pnl"] / n, 4) if n > 0 else 0,
                }
            stats["per_market"] = market_breakdown

            return stats

        except Exception as exc:
            logger.error("get_stats failed: %s", exc, exc_info=True)
            return {"error": str(exc)}

    # ── Maintenance ───────────────────────────────────────────────────────

    def cleanup_old(self, days: int = RETENTION_DAYS) -> int:
        """Remove trades older than *days* days.  Returns count removed."""
        try:
            cutoff = time.time() - (days * 86400)
            with self._conn() as conn:
                cur = conn.execute(
                    "DELETE FROM trades WHERE timestamp < ?", (cutoff,)
                )
                removed = cur.rowcount
            if removed > 0:
                logger.info("Cleaned up %d old trade records (>%d days)", removed, days)
            return removed
        except Exception as exc:
            logger.error("cleanup_old failed: %s", exc, exc_info=True)
            return 0

    def export_json(self, path: str) -> int:
        """Export all trades to a JSON file.  Returns count exported."""
        try:
            records = self.get_recent(n=999999)
            data = [r.to_dict() for r in records]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            logger.info("Exported %d trades to %s", len(data), path)
            return len(data)
        except Exception as exc:
            logger.error("export_json failed: %s", exc, exc_info=True)
            return 0
