"""
Dynamic Position Sizer — confidence and edge-based position sizing.

Computes an optimal position size for every trade by combining:
  1. Kelly Criterion from historical win rate and average win/loss ratio
  2. Fractional Kelly scaling (configurable, default 25%)
  3. Quadratic confidence scaling — size grows with the *square* of
     confidence so that low-Confidence trades are drastically reduced
  4. Regime-aware multipliers — trending regimes get a boost, random
     markets are penalised
  5. Entropy discount — lower entropy (more structure) justifies a
     larger position
  6. Historical edge multiplier — positive edge is rewarded, negative
     edge is punished
  7. Hard safety limits — never exceed a percentage of the account
     balance, never trade below the minimum trade amount
  8. Consecutive-loss cooldown — after a string of losses, position
     size is automatically reduced

All sizing decisions are logged with full reasoning so that operators
can audit and tune the sizing logic.
"""

import logging
import os
import sqlite3
import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

_DEFAULT_MIN_TRADE_AMOUNT = 1.0
_DEFAULT_MAX_POSITION_PCT = 5.0      # % of account balance
_DEFAULT_LOSS_COOLDOWN_REDUCTION = 0.5
_DEFAULT_KELLY_FRACTION = 0.25
_DEFAULT_LOSS_COOLDOWN_THRESHOLD = 3  # consecutive losses before reduction

_REGIME_MULTIPLIERS: Dict[str, float] = {
    "TRENDING_UP": 1.2,
    "TRENDING_DOWN": 1.2,
    "MEAN_REVERTING": 1.0,
    "RANDOM": 0.5,
    "HIGH_VOLATILITY": 0.7,
    "LOW_VOLATILITY": 0.8,
}

_STATS_DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS sizing_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   REAL    NOT NULL,
    amount      REAL    NOT NULL,
    fraction    REAL    NOT NULL,
    confidence  REAL    NOT NULL,
    regime      TEXT    NOT NULL,
    entropy     REAL,
    edge        REAL,
    kelly_raw   REAL,
    adjusted    INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sizing_ts ON sizing_log(timestamp DESC);
"""

MAX_LOG_ENTRIES = 5000


# ── SQLite sizing log ───────────────────────────────────────────────────

class _SizingLog:
    """Lightweight SQLite log for sizing decisions (audit trail)."""

    def __init__(self, db_path: str = "sizing_log.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        try:
            with self._conn() as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=3000")
                conn.executescript(_STATS_DB_SCHEMA)
        except Exception as exc:
            logger.warning("Sizing log DB init failed: %s", exc)

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

    def log(
        self,
        amount: float,
        fraction: float,
        confidence: float,
        regime: str,
        entropy: float,
        edge: float,
        kelly_raw: float,
        adjusted: bool,
    ) -> None:
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO sizing_log
                       (timestamp, amount, fraction, confidence, regime,
                        entropy, edge, kelly_raw, adjusted)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (time.time(), amount, fraction, confidence, regime,
                     entropy, edge, kelly_raw, int(adjusted)),
                )
        except Exception as exc:
            logger.debug("Sizing log write failed: %s", exc)

    def get_stats(self) -> Dict[str, Any]:
        try:
            with self._conn() as conn:
                total = conn.execute("SELECT COUNT(*) FROM sizing_log").fetchone()[0]
                amounts = [
                    row["amount"]
                    for row in conn.execute(
                        "SELECT amount FROM sizing_log ORDER BY timestamp DESC LIMIT 500"
                    ).fetchall()
                ]
                fractions = [
                    row["fraction"]
                    for row in conn.execute(
                        "SELECT fraction FROM sizing_log ORDER BY timestamp DESC LIMIT 500"
                    ).fetchall()
                ]
                regimes = conn.execute(
                    "SELECT regime, COUNT(*) as cnt FROM sizing_log GROUP BY regime"
                ).fetchall()
                adjusted_count = conn.execute(
                    "SELECT COUNT(*) FROM sizing_log WHERE adjusted = 1"
                ).fetchone()[0]

            stats: Dict[str, Any] = {
                "total_sizing_decisions": total,
                "adjusted_decisions": adjusted_count,
                "adjustment_rate": round(
                    adjusted_count / total * 100, 1
                ) if total > 0 else 0.0,
                "regime_distribution": {row["regime"]: row["cnt"] for row in regimes},
            }

            if amounts:
                arr = np.array(amounts)
                stats["avg_amount"] = round(float(arr.mean()), 4)
                stats["median_amount"] = round(float(np.median(arr)), 4)
                stats["min_amount"] = round(float(arr.min()), 4)
                stats["max_amount"] = round(float(arr.max()), 4)
                stats["std_amount"] = round(float(arr.std()), 4)

            if fractions:
                farr = np.array(fractions)
                stats["avg_fraction"] = round(float(farr.mean()), 6)

            return stats
        except Exception as exc:
            logger.error("Sizing stats query failed: %s", exc)
            return {}


# ── DynamicSizer ─────────────────────────────────────────────────────────

class DynamicSizer:
    """Dynamic position sizing based on confidence, regime, entropy, and edge.

    Thread-safe — all mutable state is protected by a reentrant lock.

    Parameters
    ----------
    trade_memory : TradeMemory or None
        Reference to the trade memory for historical statistics.  If
        ``None``, sizing relies entirely on the supplied parameters.
    settings : Settings or None
        System settings object.  When provided, initial limits are read
        from ``settings.kelly_fraction``, ``settings.base_amount``, and
        ``settings.max_consecutive_losses``.
    """

    def __init__(
        self,
        trade_memory: Any = None,
        settings: Any = None,
    ) -> None:
        self._memory = trade_memory
        self._lock = threading.RLock()

        # ── Configurable limits ───────────────────────────────────────────
        self._min_amount = _DEFAULT_MIN_TRADE_AMOUNT
        self._max_pct = _DEFAULT_MAX_POSITION_PCT
        self._loss_cooldown_reduction = _DEFAULT_LOSS_COOLDOWN_REDUCTION
        self._loss_cooldown_threshold = _DEFAULT_LOSS_COOLDOWN_THRESHOLD
        self._kelly_fraction = _DEFAULT_KELLY_FRACTION

        if settings is not None:
            self._kelly_fraction = getattr(settings, "kelly_fraction", self._kelly_fraction)
            self._min_amount = getattr(settings, "base_amount", self._min_amount)
            self._loss_cooldown_threshold = getattr(
                settings, "max_consecutive_losses", self._loss_cooldown_threshold
            )

        # ── Historical statistics (refreshed via update_from_memory) ──────
        self._hist_win_rate: float = 0.5
        self._hist_avg_win: float = 0.0
        self._hist_avg_loss: float = 0.0
        self._hist_edge: float = 0.0
        self._hist_trades: int = 0

        # ── Session counters ──────────────────────────────────────────────
        self._consecutive_losses: int = 0
        self._recent_amounts: deque = deque(maxlen=500)
        self._recent_adjustments: deque = deque(maxlen=500)
        self._kelly_raw_values: deque = deque(maxlen=500)
        self._total_calculations: int = 0
        self._creation_time: float = time.time()

        # ── Sizing log ────────────────────────────────────────────────────
        self._log = _SizingLog()

        # Load historical stats if memory is available
        if self._memory is not None:
            self.update_from_memory()

        logger.info(
            "DynamicSizer initialised: min=%.2f, max_pct=%.1f%%, kelly_frac=%.2f, "
            "loss_cooldown_threshold=%d",
            self._min_amount, self._max_pct, self._kelly_fraction,
            self._loss_cooldown_threshold,
        )

    # ── Core sizing method ────────────────────────────────────────────────

    def calculate_size(
        self,
        confidence: float,
        regime: str,
        entropy: float,
        historical_edge: float,
        kelly_fraction: Optional[float] = None,
        base_amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Calculate the optimal position size for a proposed trade.

        Parameters
        ----------
        confidence : float
            Trade confidence in ``[0, 100]``.
        regime : str
            Current market regime label.
        entropy : float
            Shannon entropy in bits (0 = deterministic, ~3.32 = random).
        historical_edge : float
            Estimated edge from historical analysis (positive = profitable).
        kelly_fraction : float or None
            Override for the fractional-Kelly parameter.  Defaults to
            the value set at init / via ``set_limits``.
        base_amount : float or None
            Override for the base trade amount.  Defaults to
            ``self._min_amount``.

        Returns
        -------
        dict
            Keys: ``amount`` (float), ``fraction`` (float),
            ``reasoning`` (str), ``kelly_raw`` (float), ``adjusted`` (bool).
        """
        with self._lock:
            kf = kelly_fraction if kelly_fraction is not None else self._kelly_fraction
            base = base_amount if base_amount is not None else self._min_amount
            balance = self._get_balance()

            # ── 1. Kelly Criterion ────────────────────────────────────────
            kelly_raw = self._compute_kelly_raw(
                self._hist_win_rate,
                self._hist_avg_win,
                self._hist_avg_loss,
            )
            kelly_adjusted = kelly_raw * kf  # fractional Kelly

            # ── 2. Base amount from Kelly ──────────────────────────────────
            amount = balance * kelly_adjusted if kelly_adjusted > 0 else base

            # ── 3. Confidence scaling (quadratic) ─────────────────────────
            conf_01 = float(np.clip(confidence / 100.0, 0.0, 1.0))
            conf_multiplier = conf_01 ** 2  # quadratic — heavily penalises low confidence
            amount *= conf_multiplier

            # ── 4. Regime multiplier ───────────────────────────────────────
            regime_mult = _REGIME_MULTIPLIERS.get(regime.upper(), 0.7)
            amount *= regime_mult

            # ── 5. Entropy discount ───────────────────────────────────────
            # Lower entropy → more pattern → more edge → larger position
            max_entropy = 3.32
            entropy_factor = 1.0 - (entropy / max_entropy)  # 0 = fully random, 1 = deterministic
            entropy_factor = float(np.clip(entropy_factor, 0.1, 1.5))
            amount *= entropy_factor

            # ── 6. Historical edge multiplier ─────────────────────────────
            edge = historical_edge
            if edge > 0.1:
                amount *= 1.1
            elif edge < -0.05:
                amount *= 0.5

            # ── 7. Hard limits ─────────────────────────────────────────────
            max_amount = balance * (self._max_pct / 100.0)
            amount_before_cooldown = amount
            amount = float(np.clip(amount, self._min_amount, max_amount))

            # ── 8. Cooldown sizing (consecutive losses) ───────────────────
            adjusted = False
            reasoning_parts: List[str] = []

            if self._consecutive_losses >= self._loss_cooldown_threshold:
                amount *= self._loss_cooldown_reduction
                adjusted = True
                reasoning_parts.append(
                    f"Cooldown active: {self._consecutive_losses} consecutive losses "
                    f"-> size reduced by {(1 - self._loss_cooldown_reduction) * 100:.0f}%"
                )

            # Re-enforce minimum after cooldown
            amount = max(amount, self._min_amount)

            # ── Build reasoning ────────────────────────────────────────────
            if not reasoning_parts:
                reasoning_parts.append("No cooldown applied")

            reasoning_parts.insert(0, (
                f"Kelly raw={kelly_raw:.4f}, fractional={kelly_adjusted:.4f} "
                f"(x{kf:.2f}), balance={balance:.2f}"
            ))
            reasoning_parts.append(
                f"Conf scaling: ({confidence:.0f}/100)²={conf_multiplier:.4f}"
            )
            reasoning_parts.append(
                f"Regime: {regime} (x{regime_mult:.2f})"
            )
            reasoning_parts.append(
                f"Entropy: {entropy:.2f}/3.32 bits (factor={entropy_factor:.3f})"
            )
            if edge > 0.1:
                reasoning_parts.append(f"Edge positive ({edge:+.3f}) -> x1.1")
            elif edge < -0.05:
                reasoning_parts.append(f"Edge negative ({edge:+.3f}) -> x0.5")
            else:
                reasoning_parts.append(f"Edge neutral ({edge:+.3f})")
            reasoning_parts.append(
                f"Limits: min={self._min_amount:.2f}, max={max_amount:.2f} "
                f"({self._max_pct:.1f}% of {balance:.2f})"
            )

            fraction = amount / balance if balance > 0 else 0.0

            result = {
                "amount": round(amount, 4),
                "fraction": round(fraction, 6),
                "reasoning": " | ".join(reasoning_parts),
                "kelly_raw": round(kelly_raw, 6),
                "adjusted": adjusted,
            }

            # Track
            self._total_calculations += 1
            self._recent_amounts.append(amount)
            self._recent_adjustments.append(adjusted)
            self._kelly_raw_values.append(kelly_raw)

            # Log to SQLite
            self._log.log(
                amount=amount,
                fraction=fraction,
                confidence=confidence,
                regime=regime,
                entropy=entropy,
                edge=edge,
                kelly_raw=kelly_raw,
                adjusted=adjusted,
            )

            logger.debug(
                "Size calculated: %.4f (kelly=%.4f, conf=%.0f, regime=%s, "
                "entropy=%.2f, edge=%+.3f, adjusted=%s)",
                amount, kelly_raw, confidence, regime, entropy, edge, adjusted,
            )
            return result

    # ── Historical statistics refresh ─�───────────────────────────────────

    def update_from_memory(self) -> None:
        """Refresh historical win rate, avg win/loss, and edge from trade memory.

        Safe to call periodically (e.g. every N trades) to keep sizing
        statistics current.
        """
        with self._lock:
            if self._memory is None:
                logger.debug("No trade memory — skipping update")
                return

            try:
                stats = self._memory.get_stats()
                if not stats:
                    return

                wins = stats.get("wins", 0)
                losses = stats.get("losses", 0)
                total_closed = stats.get("closed_trades", 0)
                avg_profit = stats.get("avg_profit", 0.0)

                self._hist_trades = total_closed
                self._hist_win_rate = (wins / total_closed) if total_closed > 0 else 0.5

                # Approximate avg_win and avg_loss from available data
                profit_factor = stats.get("profit_factor", 1.0)
                if profit_factor == float("inf"):
                    profit_factor = 5.0

                # Use avg_profit and win_rate to back out avg_win and avg_loss
                if self._hist_win_rate > 0 and self._hist_win_rate < 1.0:
                    # avg_profit = win_rate * avg_win - (1 - win_rate) * avg_loss
                    # profit_factor = (win_rate * avg_win) / ((1 - win_rate) * avg_loss)
                    # Solving: avg_win = avg_loss * profit_factor * (1 - wr) / wr
                    # Substituting into avg_profit equation:
                    # avg_profit = avg_loss * (profit_factor - 1)
                    # avg_loss = avg_profit / (profit_factor - 1) ... but this can be negative
                    # Safer approach: use direct ratios
                    self._hist_avg_win = abs(avg_profit) * profit_factor if avg_profit >= 0 else abs(avg_profit)
                    self._hist_avg_loss = abs(avg_profit) if avg_profit >= 0 else abs(avg_profit) * profit_factor
                    self._hist_edge = self._hist_win_rate - (1.0 - self._hist_win_rate) / max(profit_factor, 0.01)
                else:
                    self._hist_avg_win = abs(avg_profit) if avg_profit != 0 else 1.0
                    self._hist_avg_loss = abs(avg_profit) if avg_profit != 0 else 1.0
                    self._hist_edge = 0.0

                logger.info(
                    "Sizing stats updated: win_rate=%.2f%%, avg_win=%.4f, avg_loss=%.4f, "
                    "edge=%+.4f, trades=%d",
                    self._hist_win_rate * 100,
                    self._hist_avg_win,
                    self._hist_avg_loss,
                    self._hist_edge,
                    self._hist_trades,
                )

            except Exception as exc:
                logger.error("update_from_memory failed: %s", exc, exc_info=True)

    # ── Runtime limit changes ─────────────────────────────────────────────

    def set_limits(
        self,
        min_amount: Optional[float] = None,
        max_pct: Optional[float] = None,
        max_loss_cooldown: Optional[int] = None,
        loss_cooldown_reduction: Optional[float] = None,
        kelly_fraction: Optional[float] = None,
    ) -> None:
        """Adjust sizing limits at runtime.

        Parameters
        ----------
        min_amount : float or None
            Minimum trade amount (never go below this).
        max_pct : float or None
            Maximum position as a percentage of account balance.
        max_loss_cooldown : int or None
            Number of consecutive losses before cooldown reduction.
        loss_cooldown_reduction : float or None
            Multiplier applied during cooldown (0.0–1.0).
        kelly_fraction : float or None
            Fraction of Kelly to use (0.0–1.0).
        """
        with self._lock:
            if min_amount is not None:
                self._min_amount = max(0.01, min_amount)
            if max_pct is not None:
                self._max_pct = float(np.clip(max_pct, 0.1, 100.0))
            if max_loss_cooldown is not None:
                self._loss_cooldown_threshold = max(1, max_loss_cooldown)
            if loss_cooldown_reduction is not None:
                self._loss_cooldown_reduction = float(np.clip(loss_cooldown_reduction, 0.0, 1.0))
            if kelly_fraction is not None:
                self._kelly_fraction = float(np.clip(kelly_fraction, 0.0, 1.0))

            logger.info(
                "Sizing limits updated: min=%.2f, max_pct=%.1f%%, "
                "cooldown_threshold=%d, cooldown_reduction=%.2f, kelly_frac=%.2f",
                self._min_amount,
                self._max_pct,
                self._loss_cooldown_threshold,
                self._loss_cooldown_reduction,
                self._kelly_fraction,
            )

    # ── Loss tracking ─────────────────────────────────────────────────────

    def record_trade_outcome(self, profit: float) -> None:
        """Update consecutive-loss tracking after a trade settles.

        Call this after every completed trade so the cooldown logic
        stays accurate.
        """
        with self._lock:
            if profit < 0:
                self._consecutive_losses += 1
                logger.info(
                    "Loss recorded (%.4f) — consecutive losses now %d",
                    profit, self._consecutive_losses,
                )
            else:
                if self._consecutive_losses > 0:
                    logger.info(
                        "Win/break-even recorded (%.4f) — consecutive losses reset from %d",
                        profit, self._consecutive_losses,
                    )
                self._consecutive_losses = 0

    # ── Statistics ─────────────────────────────────────────────────────────

    def get_sizing_stats(self) -> Dict[str, Any]:
        """Return comprehensive sizing statistics for monitoring.

        Returns
        -------
        dict
            Keys: ``total_calculations``, ``avg_amount``, ``amount_distribution``,
            ``edge_usage``, ``kelly_stats``, ``consecutive_losses``,
            ``limits``, ``uptime_hours``.
        """
        with self._lock:
            uptime = (time.time() - self._creation_time) / 3600.0

            stats: Dict[str, Any] = {
                "total_calculations": self._total_calculations,
                "consecutive_losses": self._consecutive_losses,
                "uptime_hours": round(uptime, 2),
                "limits": {
                    "min_amount": self._min_amount,
                    "max_pct": self._max_pct,
                    "loss_cooldown_threshold": self._loss_cooldown_threshold,
                    "loss_cooldown_reduction": self._loss_cooldown_reduction,
                    "kelly_fraction": self._kelly_fraction,
                },
                "historical_stats": {
                    "win_rate": round(self._hist_win_rate, 4),
                    "avg_win": round(self._hist_avg_win, 4),
                    "avg_loss": round(self._hist_avg_loss, 4),
                    "edge": round(self._hist_edge, 4),
                    "total_trades": self._hist_trades,
                },
            }

            if self._recent_amounts:
                arr = np.array(list(self._recent_amounts))
                stats["avg_amount"] = round(float(arr.mean()), 4)
                stats["median_amount"] = round(float(np.median(arr)), 4)
                stats["min_amount_recent"] = round(float(arr.min()), 4)
                stats["max_amount_recent"] = round(float(arr.max()), 4)
                stats["std_amount"] = round(float(arr.std()), 4)

                # Distribution buckets
                percentiles = [10, 25, 50, 75, 90]
                pcts = np.percentile(arr, percentiles)
                stats["amount_distribution"] = {
                    f"p{p}": round(float(v), 4) for p, v in zip(percentiles, pcts)
                }
            else:
                stats["avg_amount"] = 0.0
                stats["amount_distribution"] = {}

            if self._recent_adjustments:
                adj_arr = np.array(list(self._recent_adjustments))
                stats["adjustment_rate"] = round(float(adj_arr.mean()) * 100, 1)
            else:
                stats["adjustment_rate"] = 0.0

            if self._kelly_raw_values:
                kelly_arr = np.array(list(self._kelly_raw_values))
                stats["kelly_stats"] = {
                    "avg_raw": round(float(kelly_arr.mean()), 6),
                    "max_raw": round(float(kelly_arr.max()), 6),
                    "min_raw": round(float(kelly_arr.min()), 6),
                }
            else:
                stats["kelly_stats"] = {"avg_raw": 0.0, "max_raw": 0.0, "min_raw": 0.0}

            # Merge SQLite log stats
            log_stats = self._log.get_stats()
            stats["log_stats"] = log_stats

            return stats

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _compute_kelly_raw(
        win_rate: float,
        avg_win: float,
        avg_loss: float,
    ) -> float:
        """Compute the raw Kelly fraction.

        f* = (p * b - q) / b
        where p = win probability, q = 1 - p, b = avg_win / avg_loss.

        Returns a value clamped to ``[0, 0.25]`` as a safety measure.
        """
        if avg_loss <= 0 or avg_win <= 0:
            return 0.0

        b = avg_win / avg_loss  # win/loss ratio
        p = float(np.clip(win_rate, 0.0, 1.0))
        q = 1.0 - p

        kelly = (p * b - q) / b
        # Clamp to [0, 0.25] for safety — never bet more than 25% raw
        return float(np.clip(kelly, 0.0, 0.25))

    def _get_balance(self) -> float:
        """Retrieve the current account balance from the trade memory or return a default."""
        if self._memory is not None:
            try:
                stats = self._memory.get_stats()
                total_pnl = stats.get("total_pnl", 0.0)
                # Assume starting balance of 10000 if unknown
                return 10000.0 + total_pnl
            except Exception:
                pass
        return 10000.0
