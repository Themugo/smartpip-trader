"""
Centralized Risk Engine — single source of truth for all risk decisions.
Every trade must pass through this engine before execution.
Uses numpy + scipy for statistical computations, joblib for persistence.
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


def _import_joblib():
    import importlib
    import sys
    from pathlib import Path as _P

    saved_platform = sys.modules.pop("platform", None)
    removed_paths = []
    for p in list(sys.path):
        try:
            if (_P(p) / "platform").is_dir():
                removed_paths.append(p)
                sys.path.remove(p)
        except Exception:
            pass

    import importlib as _imp
    real_platform = _imp.import_module("platform")
    sys.modules["platform"] = real_platform

    import joblib as _joblib

    sys.modules["platform"] = saved_platform
    for p in removed_paths:
        sys.path.insert(0, p)

    return _joblib.dump, _joblib.load


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RiskDecision:
    allowed: bool
    reason: str
    suggested_size: float = 0.0
    risk_score: float = 0.0
    risk_level: str = RiskLevel.LOW.value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskState:
    daily_pnl: float = 0.0
    drawdown_from_peak: float = 0.0
    consecutive_losses: int = 0
    trades_today: int = 0
    risk_level: str = RiskLevel.LOW.value
    open_positions: int = 0
    exposure: float = 0.0
    circuit_breaker_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CircuitBreaker:
    name: str
    triggered: bool = False
    triggered_at: float = 0.0
    cooldown_until: float = 0.0
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_DEFAULT_LIMITS: Dict[str, Any] = {
    "max_position_pct": 0.05,
    "max_daily_loss_pct": 0.03,
    "max_drawdown_pct": 0.10,
    "max_open_positions": 5,
    "max_trades_per_hour": 10,
    "max_correlated_exposure": 0.15,
    "circuit_breaker_loss_pct": 0.05,
    "cooldown_minutes_after_circuit_break": 30,
}

_CORRELATION_GROUPS: Dict[str, List[str]] = {
    "EUR_GROUP": ["EURUSD", "EURGBP", "EURJPY", "EURCHF", "EURAUD", "EURCAD", "EURNZD"],
    "GBP_GROUP": ["GBPUSD", "GBPJPY", "GBPCHF", "GBPAUD", "GBPCAD", "GBPNZD"],
    "JPY_GROUP": ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CADJPY", "CHFJPY"],
    "AUD_GROUP": ["AUDUSD", "AUDNZD", "AUDCAD", "AUDCHF", "AUDJPY"],
    "NZD_GROUP": ["NZDUSD", "NZDCAD", "NZDCHF", "NZDJPY"],
    "CAD_GROUP": ["USDCAD", "EURCAD", "GBPCAD", "AUDCAD", "NZDCAD", "CADJPY"],
    "CHF_GROUP": ["USDCHF", "EURCHF", "GBPCHF", "AUDCHF", "NZDCHF"],
    "COMMODITY_GROUP": ["XAUUSD", "XAGUSD"],
}


class RiskEngine:
    """Centralized risk engine — gatekeeper for every trade."""

    def __init__(self, settings: Optional[Dict[str, Any]] = None) -> None:
        self._limits: Dict[str, Any] = {**_DEFAULT_LIMITS}
        if settings:
            self._limits.update(settings)

        self._peak_balance: float = 0.0
        self._current_balance: float = 0.0
        self._daily_pnl: float = 0.0
        self._daily_start_balance: float = 0.0
        self._trades_today: int = 0
        self._consecutive_losses: int = 0
        self._trade_timestamps: List[float] = []
        self._open_positions: int = 0
        self._exposures: Dict[str, float] = {}
        self._daily_date: str = ""
        self._circuit_breakers: List[CircuitBreaker] = [
            CircuitBreaker(name="daily_loss"),
            CircuitBreaker(name="drawdown"),
            CircuitBreaker(name="consecutive_losses"),
            CircuitBreaker(name="trade_frequency"),
        ]
        self._trade_history: List[Dict[str, Any]] = []

        logger.info("RiskEngine initialized with limits: %s", self._limits)

    # ── Main gate ────────────────────────────────────────────────────────

    def validate_trade(
        self, signal: Dict[str, Any], account_state: Dict[str, Any]
    ) -> RiskDecision:
        """Validate whether a proposed trade is allowed under current risk limits."""
        self._refresh_daily(account_state)
        violations: List[str] = []
        risk_factors: List[float] = []

        cb_check = self.check_circuit_breakers()
        active_cbs = [cb for cb in cb_check if cb.triggered]
        if active_cbs:
            names = ", ".join(cb.name for cb in active_cbs)
            violations.append(f"Circuit breakers active: {names}")
            risk_factors.append(1.0)

        balance = account_state.get("balance", self._current_balance)
        if balance <= 0:
            violations.append("Account balance is zero or negative")
            risk_factors.append(1.0)

        max_daily_loss = self._limits["max_daily_loss_pct"] * self._daily_start_balance
        if self._daily_pnl <= -max_daily_loss:
            violations.append(
                f"Daily loss limit reached: {self._daily_pnl:.2f} "
                f"(limit: -{max_daily_loss:.2f})"
            )
            risk_factors.append(0.95)

        max_dd = self._limits["max_drawdown_pct"] * self._peak_balance
        current_dd = self._peak_balance - balance
        if self._peak_balance > 0 and current_dd >= max_dd:
            violations.append(
                f"Max drawdown breached: {current_dd:.2f} "
                f"(limit: {max_dd:.2f})"
            )
            risk_factors.append(1.0)

        if self._open_positions >= self._limits["max_open_positions"]:
            violations.append(
                f"Max open positions reached: {self._open_positions} "
                f"(limit: {self._limits['max_open_positions']})"
            )
            risk_factors.append(0.85)

        now = time.time()
        recent = [t for t in self._trade_timestamps if now - t < 3600]
        if len(recent) >= self._limits["max_trades_per_hour"]:
            violations.append(
                f"Trade frequency limit reached: {len(recent)} trades/hr "
                f"(limit: {self._limits['max_trades_per_hour']})"
            )
            risk_factors.append(0.75)

        market = signal.get("market", signal.get("symbol", ""))
        exposure_pct = self._check_correlated_exposure(market, account_state)
        max_corr = self._limits["max_correlated_exposure"]
        if exposure_pct > max_corr:
            violations.append(
                f"Correlated exposure too high for {market}: "
                f"{exposure_pct:.1%} (limit: {max_corr:.1%})"
            )
            risk_factors.append(0.7)

        size = self.calculate_position_size(signal, account_state)
        max_size_pct = self._limits["max_position_pct"] * balance
        if signal.get("amount", 0) > max_size_pct:
            violations.append(
                f"Requested size {signal.get('amount', 0):.2f} "
                f"exceeds max position size {max_size_pct:.2f}"
            )
            risk_factors.append(0.6)

        risk_score = min(np.mean(risk_factors) if risk_factors else 0.0, 1.0)
        risk_level = self._score_to_level(risk_score)

        if violations:
            logger.warning(
                "Trade BLOCKED — %d violation(s): %s",
                len(violations),
                "; ".join(violations),
            )
            return RiskDecision(
                allowed=False,
                reason="; ".join(violations),
                suggested_size=size,
                risk_score=risk_score,
                risk_level=risk_level,
            )

        logger.info(
            "Trade ALLOWED — risk_score=%.3f level=%s size=%.2f",
            risk_score,
            risk_level,
            size,
        )
        return RiskDecision(
            allowed=True,
            reason="All risk checks passed",
            suggested_size=size,
            risk_score=risk_score,
            risk_level=risk_level,
        )

    # ── Risk state ───────────────────────────────────────────────────────

    def get_risk_state(self) -> RiskState:
        """Return current risk dashboard snapshot."""
        balance = self._current_balance if self._current_balance > 0 else 1.0
        dd = (
            (self._peak_balance - self._current_balance) / self._peak_balance
            if self._peak_balance > 0
            else 0.0
        )
        cb_active = any(cb.triggered for cb in self._circuit_breakers)

        exposure = sum(self._exposures.values())
        exposure_pct = exposure / balance if balance > 0 else 0.0

        overall_score = 0.0
        if cb_active:
            overall_score = 1.0
        elif dd > self._limits["max_drawdown_pct"] * 0.5:
            overall_score = 0.7
        elif self._consecutive_losses >= 2:
            overall_score = 0.5
        elif exposure_pct > self._limits["max_correlated_exposure"] * 0.75:
            overall_score = 0.4
        else:
            overall_score = 0.1

        return RiskState(
            daily_pnl=round(self._daily_pnl, 4),
            drawdown_from_peak=round(dd, 4),
            consecutive_losses=self._consecutive_losses,
            trades_today=self._trades_today,
            risk_level=self._score_to_level(overall_score),
            open_positions=self._open_positions,
            exposure=round(exposure_pct, 4),
            circuit_breaker_active=cb_active,
        )

    # ── Update after trade ───────────────────────────────────────────────

    def update_after_trade(self, trade_result: Dict[str, Any]) -> None:
        """Update internal tracking after a trade completes."""
        pnl = trade_result.get("pnl", 0.0)
        balance = trade_result.get("balance", self._current_balance)
        market = trade_result.get("market", trade_result.get("symbol", ""))
        is_close = trade_result.get("is_close", True)

        self._daily_pnl += pnl
        self._current_balance = balance

        if balance > self._peak_balance:
            self._peak_balance = balance

        self._trade_timestamps.append(time.time())
        self._trades_today += 1

        if pnl < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

        if is_close:
            if market in self._exposures:
                self._exposures[market] = max(0.0, self._exposures[market] - abs(pnl))
                if self._exposures[market] <= 0:
                    del self._exposures[market]
                    self._open_positions = max(0, self._open_positions - 1)
            else:
                self._open_positions = max(0, self._open_positions - 1)
        else:
            self._exposures[market] = self._exposures.get(market, 0.0) + abs(
                trade_result.get("amount", 0.0)
            )
            if market not in [k for k in self._exposures if self._exposures[k] > 0]:
                self._open_positions += 1

        self._trade_history.append(trade_result)
        self._update_circuit_breakers()
        logger.info(
            "Trade recorded — pnl=%.4f balance=%.2f consecutive_losses=%d",
            pnl,
            balance,
            self._consecutive_losses,
        )

    # ── Circuit breakers ─────────────────────────────────────────────────

    def check_circuit_breakers(self) -> List[CircuitBreaker]:
        """Evaluate and return status of all circuit breakers."""
        now = time.time()
        balance = self._current_balance if self._current_balance > 0 else 1.0
        cb_list = list(self._circuit_breakers)

        daily_loss_cb = next(cb for cb in cb_list if cb.name == "daily_loss")
        max_daily_loss = self._limits["max_daily_loss_pct"] * self._daily_start_balance
        if self._daily_pnl <= -max_daily_loss:
            daily_loss_cb.triggered = True
            daily_loss_cb.triggered_at = now
            daily_loss_cb.cooldown_until = now + self._limits["cooldown_minutes_after_circuit_break"] * 60
            daily_loss_cb.reason = (
                f"Daily loss {self._daily_pnl:.2f} hit limit -{max_daily_loss:.2f}"
            )
        elif now > daily_loss_cb.cooldown_until:
            daily_loss_cb.triggered = False

        dd_cb = next(cb for cb in cb_list if cb.name == "drawdown")
        max_dd = self._limits["max_drawdown_pct"] * self._peak_balance
        current_dd = self._peak_balance - self._current_balance
        if self._peak_balance > 0 and current_dd >= max_dd:
            dd_cb.triggered = True
            dd_cb.triggered_at = now
            dd_cb.cooldown_until = now + self._limits["cooldown_minutes_after_circuit_break"] * 60
            dd_cb.reason = f"Drawdown {current_dd:.2f} hit limit {max_dd:.2f}"
        elif now > dd_cb.cooldown_until:
            dd_cb.triggered = False

        cl_cb = next(cb for cb in cb_list if cb.name == "consecutive_losses")
        max_cl = self._limits.get("max_consecutive_losses", 5)
        if self._consecutive_losses >= max_cl:
            cl_cb.triggered = True
            cl_cb.triggered_at = now
            cl_cb.cooldown_until = now + self._limits["cooldown_minutes_after_circuit_break"] * 60
            cl_cb.reason = f"{self._consecutive_losses} consecutive losses"
        elif now > cl_cb.cooldown_until:
            cl_cb.triggered = False

        tf_cb = next(cb for cb in cb_list if cb.name == "trade_frequency")
        recent = [t for t in self._trade_timestamps if now - t < 3600]
        if len(recent) >= self._limits["max_trades_per_hour"] * 2:
            tf_cb.triggered = True
            tf_cb.triggered_at = now
            tf_cb.cooldown_until = now + 600
            tf_cb.reason = f"Excessive trading: {len(recent)} trades/hr"
        elif now > tf_cb.cooldown_until:
            tf_cb.triggered = False

        self._circuit_breakers = cb_list
        return cb_list

    # ── Position sizing ──────────────────────────────────────────────────

    def calculate_position_size(
        self, signal: Dict[str, Any], account_state: Dict[str, Any]
    ) -> float:
        """Risk-adjusted position size using Kelly-inspired sizing."""
        balance = account_state.get("balance", 0.0)
        if balance <= 0:
            return 0.0

        confidence = signal.get("confidence", 0.5)
        risk_reward = signal.get("risk_reward_ratio", 1.0)

        win_prob = max(0.01, min(confidence, 0.99))
        avg_win = max(risk_reward, 0.01)
        avg_loss = 1.0
        b = avg_win / avg_loss

        kelly_f = (b * win_prob - (1 - win_prob)) / b if b > 0 else 0.0
        kelly_f = max(0.0, min(kelly_f, 0.5))
        half_kelly = kelly_f * 0.5

        max_pct = self._limits["max_position_pct"]
        base_pct = min(half_kelly, max_pct)

        if self._consecutive_losses >= 3:
            reduction = min(0.5, self._consecutive_losses * 0.1)
            base_pct *= (1.0 - reduction)

        dd = (
            (self._peak_balance - self._current_balance) / self._peak_balance
            if self._peak_balance > 0
            else 0.0
        )
        if dd > self._limits["max_drawdown_pct"] * 0.5:
            dd_penalty = min(0.5, dd / self._limits["max_drawdown_pct"])
            base_pct *= (1.0 - dd_penalty)

        size = balance * base_pct

        requested = signal.get("amount", 0.0)
        if requested > 0 and requested < size:
            size = requested

        return round(max(0.0, size), 4)

    # ── Daily stats ──────────────────────────────────────────────────────

    def get_daily_stats(self) -> Dict[str, Any]:
        """Return daily P&L, trade count, win rate, and other daily metrics."""
        today_trades = self._trade_history[
            -self._trades_today if self._trades_today > 0 else len(self._trade_history) :
        ]
        today_pnls = [t.get("pnl", 0.0) for t in today_trades]
        wins = sum(1 for p in today_pnls if p > 0)
        total = len(today_pnls)

        return {
            "date": self._daily_date,
            "daily_pnl": round(self._daily_pnl, 4),
            "trade_count": self._trades_today,
            "win_rate": round((wins / total * 100), 2) if total > 0 else 0.0,
            "wins": wins,
            "losses": total - wins,
            "best_trade": round(max(today_pnls), 4) if today_pnls else 0.0,
            "worst_trade": round(min(today_pnls), 4) if today_pnls else 0.0,
            "avg_pnl": round(np.mean(today_pnls), 4) if today_pnls else 0.0,
            "peak_balance": round(self._peak_balance, 4),
            "current_balance": round(self._current_balance, 4),
            "consecutive_losses": self._consecutive_losses,
            "circuit_breakers_active": [
                cb.to_dict() for cb in self._circuit_breakers if cb.triggered
            ],
        }

    # ── Persistence ──────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        """Persist engine state to disk via joblib."""
        dump, _ = _import_joblib()
        state = {
            "limits": self._limits,
            "peak_balance": self._peak_balance,
            "current_balance": self._current_balance,
            "daily_pnl": self._daily_pnl,
            "daily_start_balance": self._daily_start_balance,
            "trades_today": self._trades_today,
            "consecutive_losses": self._consecutive_losses,
            "trade_timestamps": self._trade_timestamps[-1000:],
            "open_positions": self._open_positions,
            "exposures": self._exposures,
            "daily_date": self._daily_date,
            "circuit_breakers": [asdict(cb) for cb in self._circuit_breakers],
            "trade_history": self._trade_history[-500:],
        }
        dump(state, path)
        logger.info("RiskEngine saved to %s", path)

    def load(self, path: str) -> None:
        """Restore engine state from disk via joblib."""
        if not Path(path).exists():
            logger.warning("No saved state found at %s", path)
            return
        _, joblib_load = _import_joblib()
        state = joblib_load(path)
        self._limits = state.get("limits", self._limits)
        self._peak_balance = state.get("peak_balance", 0.0)
        self._current_balance = state.get("current_balance", 0.0)
        self._daily_pnl = state.get("daily_pnl", 0.0)
        self._daily_start_balance = state.get("daily_start_balance", 0.0)
        self._trades_today = state.get("trades_today", 0)
        self._consecutive_losses = state.get("consecutive_losses", 0)
        self._trade_timestamps = state.get("trade_timestamps", [])
        self._open_positions = state.get("open_positions", 0)
        self._exposures = state.get("exposures", {})
        self._daily_date = state.get("daily_date", "")
        self._trade_history = state.get("trade_history", [])
        for cb_data in state.get("circuit_breakers", []):
            existing = next(
                (cb for cb in self._circuit_breakers if cb.name == cb_data["name"]),
                None,
            )
            if existing:
                existing.triggered = cb_data.get("triggered", False)
                existing.triggered_at = cb_data.get("triggered_at", 0.0)
                existing.cooldown_until = cb_data.get("cooldown_until", 0.0)
                existing.reason = cb_data.get("reason", "")
        logger.info("RiskEngine loaded from %s", path)

    # ── Internal helpers ─────────────────────────────────────────────────

    def _refresh_daily(self, account_state: Dict[str, Any]) -> None:
        """Reset daily counters if the trading day has changed."""
        today = time.strftime("%Y-%m-%d")
        if self._daily_date != today:
            logger.info("New trading day detected: %s → %s", self._daily_date, today)
            self._daily_date = today
            self._daily_pnl = 0.0
            self._daily_start_balance = account_state.get(
                "balance", self._current_balance
            )
            self._trades_today = 0
            self._trade_timestamps = []
            self._current_balance = account_state.get(
                "balance", self._current_balance
            )
            if self._peak_balance <= 0:
                self._peak_balance = self._current_balance
        self._current_balance = account_state.get("balance", self._current_balance)
        if self._current_balance > self._peak_balance:
            self._peak_balance = self._current_balance

    def _check_correlated_exposure(
        self, market: str, account_state: Dict[str, Any]
    ) -> float:
        """Calculate correlated exposure as a fraction of account balance."""
        balance = account_state.get("balance", self._current_balance)
        if balance <= 0:
            return 1.0
        group_symbols: List[str] = []
        for _group_name, symbols in _CORRELATION_GROUPS.items():
            if market in symbols:
                group_symbols.extend(symbols)
        if not group_symbols:
            group_symbols = [market]

        total_exposure = sum(
            self._exposures.get(s, 0.0) for s in group_symbols if s in self._exposures
        )
        return total_exposure / balance

    def _update_circuit_breakers(self) -> None:
        """Re-evaluate circuit breakers after state changes."""
        self.check_circuit_breakers()

    @staticmethod
    def _score_to_level(score: float) -> str:
        """Map a 0–1 risk score to a RiskLevel string."""
        if score >= 0.85:
            return RiskLevel.CRITICAL.value
        if score >= 0.6:
            return RiskLevel.HIGH.value
        if score >= 0.3:
            return RiskLevel.MEDIUM.value
        return RiskLevel.LOW.value
