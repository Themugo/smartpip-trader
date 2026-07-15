"""
Capital Preservation Layer — institutional-grade risk gate and position sizer.

Sits between the intelligence layer and order execution to enforce hard risk
limits that can never be overridden by AI components:

  1. Continuous risk-state evaluation (LOW / MEDIUM / HIGH / CRITICAL)
  2. Kelly Criterion position sizing with fractional Kelly, drawdown-aware
     reduction, confidence scaling, and regime adjustment
  3. Deterministic trade gate checking every risk limit before order entry
  4. Circuit-breaker halting trading when daily loss exceeds threshold
  5. Full persistence via joblib
"""

import logging
import time
import threading
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import joblib

logger = logging.getLogger(__name__)

# ── Defaults ─────────────────────────────────────────────────────────────

DEFAULT_MAX_DAILY_LOSS_PCT: float = 3.0
DEFAULT_MAX_DRAWDOWN_PCT: float = 8.0
DEFAULT_MAX_POSITION_PCT: float = 5.0
DEFAULT_MAX_CORRELATED_EXPOSURE_PCT: float = 20.0
DEFAULT_MAX_TRADES_PER_HOUR: int = 12
DEFAULT_KELLY_FRACTION: float = 0.25
DEFAULT_MAX_CONSECUTIVE_LOSSES: int = 5
DEFAULT_CIRCUIT_BREAKER_PCT: float = 5.0
DEFAULT_DD_REDUCTION_FACTOR: float = 0.5
DEFAULT_COOLDOWN_SECONDS: float = 300.0
DEFAULT_BASE_BALANCE: float = 10000.0

REGIME_MULTIPLIERS: Dict[str, float] = {
    "TRENDING_UP": 1.15,
    "TRENDING_DOWN": 1.15,
    "MEAN_REVERTING": 1.0,
    "RANDOM": 0.6,
    "HIGH_VOLATILITY": 0.65,
    "LOW_VOLATILITY": 0.85,
}

_HISTORY_WINDOW: int = 200


# ── Helpers ──────────────────────────────────────────────────────────────

def _kelly_raw(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Raw Kelly fraction f*=(p*b-q)/b, clamped [0, 0.25]."""
    if avg_loss <= 0 or avg_win <= 0:
        return 0.0
    b = avg_win / avg_loss
    p = float(np.clip(win_rate, 0.0, 1.0))
    return float(np.clip((p * b - (1.0 - p)) / b, 0.0, 0.25))


def _dd_to_risk_level(dd: float) -> str:
    if dd < 2.0:
        return "LOW"
    if dd < 5.0:
        return "MEDIUM"
    if dd < 7.0:
        return "HIGH"
    return "CRITICAL"


_SEVERITY = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


# ── Dataclasses ──────────────────────────────────────────────────────────

@dataclass
class RiskState:
    """Snapshot of the current risk posture."""
    daily_pnl: float
    drawdown_from_peak: float
    consecutive_losses: int
    trades_today: int
    risk_level: str
    max_position_size: float
    current_exposure: float
    kelly_adjusted_fraction: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "daily_pnl": round(self.daily_pnl, 4),
            "drawdown_from_peak": round(self.drawdown_from_peak, 4),
            "consecutive_losses": self.consecutive_losses,
            "trades_today": self.trades_today,
            "risk_level": self.risk_level,
            "max_position_size": round(self.max_position_size, 4),
            "current_exposure": round(self.current_exposure, 4),
            "kelly_adjusted_fraction": round(self.kelly_adjusted_fraction, 6),
        }


@dataclass
class TradeDecision:
    """Result of the trade gate check."""
    allowed: bool
    reason: str
    suggested_size: float
    risk_state: RiskState
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "suggested_size": round(self.suggested_size, 4),
            "risk_state": self.risk_state.to_dict(),
            "timestamp": self.timestamp,
        }


# ── Main class ───────────────────────────────────────────────────────────

class CapitalPreservation:
    """Institutional-grade risk gate and position sizer.

    Thread-safe — all mutable state protected by a reentrant lock.
    """

    def __init__(
        self,
        max_daily_loss_pct: float = DEFAULT_MAX_DAILY_LOSS_PCT,
        max_drawdown_pct: float = DEFAULT_MAX_DRAWDOWN_PCT,
        max_position_pct: float = DEFAULT_MAX_POSITION_PCT,
        max_correlated_exposure: float = DEFAULT_MAX_CORRELATED_EXPOSURE_PCT,
        max_trades_per_hour: int = DEFAULT_MAX_TRADES_PER_HOUR,
        kelly_fraction: float = DEFAULT_KELLY_FRACTION,
        circuit_breaker_pct: float = DEFAULT_CIRCUIT_BREAKER_PCT,
    ) -> None:
        self._lock = threading.RLock()
        self._max_daily_loss_pct = float(np.clip(max_daily_loss_pct, 0.1, 50.0))
        self._max_drawdown_pct = float(np.clip(max_drawdown_pct, 0.5, 100.0))
        self._max_position_pct = float(np.clip(max_position_pct, 0.1, 100.0))
        self._max_corr_exposure_pct = float(np.clip(max_correlated_exposure, 1.0, 100.0))
        self._max_trades_hr = max(1, max_trades_per_hour)
        self._kelly_frac = float(np.clip(kelly_fraction, 0.05, 0.5))
        self._cb_pct = float(np.clip(circuit_breaker_pct, 0.5, 100.0))

        self._equity_peak: float = DEFAULT_BASE_BALANCE
        self._balance: float = DEFAULT_BASE_BALANCE
        self._daily_pnl: float = 0.0
        self._daily_start: float = DEFAULT_BASE_BALANCE
        self._consec_losses: int = 0
        self._trades_today: int = 0
        self._cb_active: bool = False
        self._cb_until: float = 0.0
        self._cooldown_until: float = 0.0
        self._trade_ts: deque = deque(maxlen=_HISTORY_WINDOW)
        self._trade_pnls: deque = deque(maxlen=_HISTORY_WINDOW)
        self._all_pnls: List[float] = []
        self._open_exposure_pct: float = 0.0
        self._session_start: float = time.time()
        self._day_key: str = self._today()

        logger.info(
            "CapitalPreservation init: daily=%.1f%% dd=%.1f%% pos=%.1f%% "
            "corr=%.1f%% hr=%d kelly=%.2f cb=%.1f%%",
            self._max_daily_loss_pct, self._max_drawdown_pct,
            self._max_position_pct, self._max_corr_exposure_pct,
            self._max_trades_hr, self._kelly_frac, self._cb_pct,
        )

    # ── Public API ───────────────────────────────────────────────────────

    def evaluate_risk(self, current_exposure_pct: float = 0.0) -> RiskState:
        """Evaluate current risk posture and return a RiskState."""
        with self._lock:
            self._check_day()
            dd = self._drawdown()
            rl = self._risk_level(dd)
            return RiskState(
                daily_pnl=round(self._daily_pnl / self._balance * 100, 4) if self._balance > 0 else 0.0,
                drawdown_from_peak=round(dd, 4),
                consecutive_losses=self._consec_losses,
                trades_today=self._trades_today,
                risk_level=rl,
                max_position_size=round(self._max_pos_size(), 4),
                current_exposure=round(current_exposure_pct, 4),
                kelly_adjusted_fraction=round(self._kelly_adj(dd), 6),
            )

    def calculate_position_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        confidence: float,
        regime: str = "RANDOM",
        current_exposure_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """Kelly Criterion position sizing with multi-factor adjustment.

        Scales the raw Kelly fraction by: fractional Kelly parameter,
        confidence (quadratic), regime multiplier, drawdown reduction,
        and consecutive-loss cooldown.  Returns amount, fraction, multipliers,
        and a human-readable reasoning string.
        """
        with self._lock:
            bal = self._balance
            dd = self._drawdown()

            kr = _kelly_raw(win_rate, avg_win, avg_loss)
            ka = kr * self._kelly_frac

            c01 = float(np.clip(confidence / 100.0, 0.0, 1.0))
            c_mult = c01 ** 2
            r_mult = REGIME_MULTIPLIERS.get(regime.upper(), 0.7)
            dd_mult = self._dd_multiplier(dd)
            loss_mult = self._loss_multiplier()

            frac = ka * c_mult * r_mult * dd_mult * loss_mult
            amount = bal * frac

            max_amt = bal * (self._max_position_pct / 100.0)
            corr_used = bal * (self._max_corr_exposure_pct / 100.0) * (current_exposure_pct / 100.0 if current_exposure_pct > 0 else 0.0)
            eff_max = max(0.0, min(max_amt, max_amt - corr_used))

            if kr > 0 and amount < 1.0:
                amount = 1.0
            amount = float(np.clip(amount, 0.0, eff_max))
            fraction = amount / bal if bal > 0 else 0.0

            multipliers = {
                "kelly_raw": round(kr, 6), "kelly_fraction": self._kelly_frac,
                "confidence": round(c_mult, 4), "regime": round(r_mult, 4),
                "drawdown": round(dd_mult, 4), "consecutive_loss": round(loss_mult, 4),
            }
            reasoning = (
                f"Kelly raw={kr:.4f} adj={ka:.4f}(x{self._kelly_frac:.2f}) | "
                f"conf={confidence:.0f}(x{c_mult:.4f}) | regime={regime}(x{r_mult:.2f}) | "
                f"dd={dd:.2f}%(x{dd_mult:.2f}) | losses={self._consec_losses}(x{loss_mult:.2f}) | "
                f"bal={bal:.2f} max={eff_max:.2f}"
            )

            return {
                "amount": round(amount, 4),
                "fraction_of_balance": round(fraction, 6),
                "kelly_raw": round(kr, 6),
                "kelly_adjusted": round(ka, 6),
                "multipliers": multipliers,
                "reasoning": reasoning,
            }

    def should_allow_trade(
        self,
        confidence: float = 0.0,
        current_exposure_pct: float = 0.0,
    ) -> TradeDecision:
        """Gate checking all risk limits.  Returns TradeDecision with allowed=True
        only when every check passes; otherwise carries a reason string."""
        with self._lock:
            self._check_day()
            now = time.time()

            # Check 1: Circuit breaker
            if self._cb_active:
                if now < self._cb_until:
                    return self._deny(
                        f"CIRCUIT BREAKER — loss {abs(self._daily_pnl/self._balance*100):.2f}% "
                        f"exceeded {self._cb_pct:.1f}%, halted until "
                        f"{time.strftime('%H:%M:%S', time.localtime(self._cb_until))}.",
                        current_exposure_pct, now,
                    )
                self._cb_active = False
                logger.info("Circuit breaker expired")

            # Check 2: Cooldown
            if now < self._cooldown_until:
                rem = self._cooldown_until - now
                return self._deny(
                    f"Cooldown: {rem:.0f}s remaining after {self._consec_losses} losses.",
                    current_exposure_pct, now,
                )

            # Check 3: Daily loss
            d_pct = self._daily_pnl / self._balance * 100 if self._balance > 0 else 0.0
            if d_pct < -self._max_daily_loss_pct:
                self._activate_cb(now)
                return self._deny(
                    f"Daily loss {d_pct:.2f}% breached limit {self._max_daily_loss_pct:.1f}%.",
                    current_exposure_pct, now,
                )

            # Check 4: Drawdown
            dd = self._drawdown()
            if dd >= self._max_drawdown_pct:
                return self._deny(
                    f"Drawdown {dd:.2f}% breached limit {self._max_drawdown_pct:.1f}%.",
                    current_exposure_pct, now,
                )

            # Check 5: Rate limit
            hr_ago = now - 3600.0
            recent = sum(1 for t in self._trade_ts if t > hr_ago)
            if recent >= self._max_trades_hr:
                return self._deny(
                    f"Rate limit: {recent}/{self._max_trades_hr} trades/hr.",
                    current_exposure_pct, now,
                )

            # Check 6: Correlated exposure
            if current_exposure_pct >= self._max_corr_exposure_pct:
                return self._deny(
                    f"Exposure {current_exposure_pct:.2f}% >= limit {self._max_corr_exposure_pct:.1f}%.",
                    current_exposure_pct, now,
                )

            # Check 7: CRITICAL risk
            st = self._build_state(current_exposure_pct)
            if st.risk_level == "CRITICAL":
                return self._deny(
                    f"Risk CRITICAL (dd={dd:.2f}% pnl={d_pct:.2f}%).",
                    current_exposure_pct, now,
                )

            # All clear — suggest position size
            size = self.calculate_position_size(
                self._roll_win_rate(), self._roll_avg_win(),
                self._roll_avg_loss(), confidence, "RANDOM", current_exposure_pct,
            )
            logger.debug("Trade ALLOWED: size=%.4f risk=%s", size["amount"], st.risk_level)
            return TradeDecision(True, "", size["amount"], st, now)

    def update_after_trade(self, pnl: float, position_notional_pct: float = 0.0) -> None:
        """Update internal state after a trade settles."""
        with self._lock:
            self._check_day()
            self._balance += pnl
            self._daily_pnl += pnl

            if self._balance > self._equity_peak:
                self._equity_peak = self._balance

            self._all_pnls.append(pnl)
            self._trade_pnls.append(pnl)
            self._trade_ts.append(time.time())
            self._trades_today += 1

            if pnl < 0:
                self._consec_losses += 1
                if self._consec_losses >= DEFAULT_MAX_CONSECUTIVE_LOSSES:
                    self._cooldown_until = time.time() + DEFAULT_COOLDOWN_SECONDS
                    logger.warning("Cooldown: %ds after %d losses",
                                   DEFAULT_COOLDOWN_SECONDS, self._consec_losses)
            else:
                self._consec_losses = 0

            self._open_exposure_pct = max(0.0, self._open_exposure_pct - position_notional_pct)

            dl = abs(self._daily_pnl) / self._balance * 100 if self._balance > 0 and self._daily_pnl < 0 else 0.0
            if dl >= self._cb_pct:
                self._activate_cb(time.time())

            logger.info(
                "Trade: pnl=%.4f bal=%.4f d_pnl=%.4f peak=%.4f dd=%.2f%% today=%d",
                pnl, self._balance, self._daily_pnl, self._equity_peak,
                self._drawdown(), self._trades_today,
            )

    def get_risk_report(self) -> Dict[str, Any]:
        """Comprehensive risk dashboard: state, limits, drawdown, frequency,
        Kelly stats, circuit breaker, and trade outcomes."""
        with self._lock:
            self._check_day()
            dd = self._drawdown()
            dp = self._daily_pnl / self._balance * 100 if self._balance > 0 else 0.0
            now = time.time()

            recent = list(self._trade_pnls)
            wins = sum(1 for p in recent if p > 0)
            losses = sum(1 for p in recent if p < 0)
            kr = _kelly_raw(self._roll_win_rate(), self._roll_avg_win(), self._roll_avg_loss())
            hr_count = sum(1 for t in self._trade_ts if t > now - 3600.0)
            fm_count = sum(1 for t in self._trade_ts if t > now - 300.0)

            return {
                "risk_state": self._build_state(self._open_exposure_pct).to_dict(),
                "limits": {
                    "max_daily_loss_pct": self._max_daily_loss_pct,
                    "max_drawdown_pct": self._max_drawdown_pct,
                    "max_position_pct": self._max_position_pct,
                    "max_correlated_exposure_pct": self._max_corr_exposure_pct,
                    "max_trades_per_hour": self._max_trades_hr,
                    "kelly_fraction": self._kelly_frac,
                    "circuit_breaker_pct": self._cb_pct,
                },
                "balance": {
                    "current": round(self._balance, 4),
                    "peak": round(self._equity_peak, 4),
                    "daily_start": round(self._daily_start, 4),
                    "daily_pnl": round(self._daily_pnl, 4),
                    "daily_pnl_pct": round(dp, 4),
                },
                "drawdown": {
                    "current_pct": round(dd, 4),
                    "max_allowed_pct": self._max_drawdown_pct,
                    "headroom_pct": round(self._max_drawdown_pct - dd, 4),
                },
                "trade_frequency": {
                    "trades_today": self._trades_today,
                    "last_hour": hr_count,
                    "last_5min": fm_count,
                    "max_per_hour": self._max_trades_hr,
                    "utilisation_pct": round(hr_count / self._max_trades_hr * 100, 1) if self._max_trades_hr else 0.0,
                },
                "kelly": {
                    "raw": round(kr, 6),
                    "adjusted": round(kr * self._kelly_frac, 6),
                    "win_rate": round(self._roll_win_rate(), 4),
                    "avg_win": round(self._roll_avg_win(), 4),
                    "avg_loss": round(self._roll_avg_loss(), 4),
                    "sample_size": len(recent),
                },
                "consecutive_losses": self._consec_losses,
                "circuit_breaker": {
                    "active": self._cb_active,
                    "trigger_pct": self._cb_pct,
                    "expires_at": self._cb_until if self._cb_active else None,
                },
                "cooldown": {
                    "active": now < self._cooldown_until,
                    "expires_at": self._cooldown_until if now < self._cooldown_until else None,
                },
                "trade_outcomes": {
                    "wins": wins,
                    "losses": losses,
                    "win_rate_pct": round(wins / len(recent) * 100, 1) if recent else 0.0,
                    "avg_pnl": round(float(np.mean(recent)), 4) if recent else 0.0,
                    "total_pnl": round(sum(recent), 4) if recent else 0.0,
                },
                "session_uptime_hours": round((now - self._session_start) / 3600.0, 2),
            }

    def set_balance(self, balance: float) -> None:
        """Update account balance (for deposits/withdrawals)."""
        with self._lock:
            if balance > 0:
                self._balance = balance
                if balance > self._equity_peak:
                    self._equity_peak = balance

    def set_open_exposure(self, exposure_pct: float) -> None:
        """Update open exposure percentage."""
        with self._lock:
            self._open_exposure_pct = max(0.0, exposure_pct)

    def reset_daily(self) -> None:
        """Reset daily counters (called automatically on day rollover)."""
        with self._lock:
            self._daily_pnl = 0.0
            self._daily_start = self._balance
            self._trades_today = 0
            self._trade_pnls.clear()
            self._cb_active = False
            self._day_key = self._today()
            logger.info("Daily reset — bal=%.4f", self._balance)

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        """Serialise full state to *path* via joblib."""
        try:
            joblib.dump({
                "max_daily_loss_pct": self._max_daily_loss_pct,
                "max_drawdown_pct": self._max_drawdown_pct,
                "max_position_pct": self._max_position_pct,
                "max_corr_exposure_pct": self._max_corr_exposure_pct,
                "max_trades_hr": self._max_trades_hr,
                "kelly_frac": self._kelly_frac,
                "cb_pct": self._cb_pct,
                "equity_peak": self._equity_peak,
                "balance": self._balance,
                "daily_pnl": self._daily_pnl,
                "daily_start": self._daily_start,
                "consec_losses": self._consec_losses,
                "trades_today": self._trades_today,
                "cb_active": self._cb_active,
                "cb_until": self._cb_until,
                "cooldown_until": self._cooldown_until,
                "trade_ts": list(self._trade_ts),
                "trade_pnls": list(self._trade_pnls),
                "all_pnls": self._all_pnls[-2000:],
                "open_exposure_pct": self._open_exposure_pct,
                "session_start": self._session_start,
                "day_key": self._day_key,
            }, path)
            logger.info("Saved to %s", path)
        except Exception as exc:
            logger.error("Save failed: %s", exc, exc_info=True)

    def load(self, path: str) -> bool:
        """Restore state from *path*. Returns True on success."""
        try:
            s = joblib.load(path)
            self._max_daily_loss_pct = s["max_daily_loss_pct"]
            self._max_drawdown_pct = s["max_drawdown_pct"]
            self._max_position_pct = s["max_position_pct"]
            self._max_corr_exposure_pct = s["max_corr_exposure_pct"]
            self._max_trades_hr = s["max_trades_hr"]
            self._kelly_frac = s["kelly_frac"]
            self._cb_pct = s["cb_pct"]
            self._equity_peak = s["equity_peak"]
            self._balance = s["balance"]
            self._daily_pnl = s["daily_pnl"]
            self._daily_start = s["daily_start"]
            self._consec_losses = s["consec_losses"]
            self._trades_today = s["trades_today"]
            self._cb_active = s["cb_active"]
            self._cb_until = s["cb_until"]
            self._cooldown_until = s["cooldown_until"]
            self._trade_ts = deque(s["trade_ts"], maxlen=_HISTORY_WINDOW)
            self._trade_pnls = deque(s["trade_pnls"], maxlen=_HISTORY_WINDOW)
            self._all_pnls = s["all_pnls"]
            self._open_exposure_pct = s["open_exposure_pct"]
            self._session_start = s["session_start"]
            self._day_key = s["day_key"]
            logger.info("Loaded from %s", path)
            return True
        except Exception as exc:
            logger.error("Load failed: %s", exc, exc_info=True)
            return False

    # ── Runtime config ────────────────────────────────────────────────────

    def update_limits(
        self,
        max_daily_loss_pct: Optional[float] = None,
        max_drawdown_pct: Optional[float] = None,
        max_position_pct: Optional[float] = None,
        max_correlated_exposure: Optional[float] = None,
        max_trades_per_hour: Optional[int] = None,
        kelly_fraction: Optional[float] = None,
        circuit_breaker_pct: Optional[float] = None,
    ) -> None:
        """Adjust risk limits at runtime. Only supplied values are updated."""
        with self._lock:
            if max_daily_loss_pct is not None:
                self._max_daily_loss_pct = float(np.clip(max_daily_loss_pct, 0.1, 50.0))
            if max_drawdown_pct is not None:
                self._max_drawdown_pct = float(np.clip(max_drawdown_pct, 0.5, 100.0))
            if max_position_pct is not None:
                self._max_position_pct = float(np.clip(max_position_pct, 0.1, 100.0))
            if max_correlated_exposure is not None:
                self._max_corr_exposure_pct = float(np.clip(max_correlated_exposure, 1.0, 100.0))
            if max_trades_per_hour is not None:
                self._max_trades_hr = max(1, max_trades_per_hour)
            if kelly_fraction is not None:
                self._kelly_frac = float(np.clip(kelly_fraction, 0.05, 0.5))
            if circuit_breaker_pct is not None:
                self._cb_pct = float(np.clip(circuit_breaker_pct, 0.5, 100.0))

    # ── Internals ─────────────────────────────────────────────────────────

    def _drawdown(self) -> float:
        if self._equity_peak <= 0:
            return 0.0
        return max(0.0, (self._equity_peak - self._balance) / self._equity_peak * 100.0)

    def _dd_multiplier(self, dd: float) -> float:
        if dd <= 0.0:
            return 1.0
        r = min(dd / self._max_drawdown_pct, 1.0)
        return float(np.clip(1.0 - r * (1.0 - DEFAULT_DD_REDUCTION_FACTOR),
                            DEFAULT_DD_REDUCTION_FACTOR, 1.0))

    def _kelly_adj(self, dd: float) -> float:
        return self._kelly_frac * self._dd_multiplier(dd)

    def _loss_multiplier(self) -> float:
        if self._consec_losses <= 0:
            return 1.0
        return max(0.25, 1.0 - self._consec_losses * 0.15)

    def _max_pos_size(self) -> float:
        return max(0.0, self._balance * (self._max_position_pct / 100.0) * self._dd_multiplier(self._drawdown()))

    def _risk_level(self, dd: float) -> str:
        levels = [_dd_to_risk_level(dd)]
        if self._balance > 0:
            dp = self._daily_pnl / self._balance * 100
            if dp < -self._cb_pct:
                levels.append("CRITICAL")
            elif dp < -self._max_daily_loss_pct:
                levels.append("HIGH")
            elif dp < -self._max_daily_loss_pct * 0.5:
                levels.append("MEDIUM")
            else:
                levels.append("LOW")
        if self._consec_losses >= 5:
            levels.append("CRITICAL")
        elif self._consec_losses >= 3:
            levels.append("HIGH")
        elif self._consec_losses >= 1:
            levels.append("MEDIUM")
        else:
            levels.append("LOW")
        if self._cb_active:
            levels.append("CRITICAL")
        return max(levels, key=lambda l: _SEVERITY.get(l, 0))

    def _roll_win_rate(self) -> float:
        p = list(self._trade_pnls)[-50:]
        return sum(1 for x in p if x > 0) / len(p) if p else 0.5

    def _roll_avg_win(self) -> float:
        w = [p for p in list(self._trade_pnls)[-50:] if p > 0]
        return float(np.mean(w)) if w else 1.0

    def _roll_avg_loss(self) -> float:
        ls = [abs(p) for p in list(self._trade_pnls)[-50:] if p < 0]
        return float(np.mean(ls)) if ls else 1.0

    def _activate_cb(self, now: float) -> None:
        if not self._cb_active:
            self._cb_active = True
            until_mid = self._secs_to_midnight(now)
            halt = min(4.0 * 3600.0, until_mid)
            self._cb_until = now + halt
            logger.critical(
                "CIRCUIT BREAKER — halted %.0fs (loss=%.2f%% cb=%.1f%%)",
                halt,
                abs(self._daily_pnl / self._balance * 100) if self._balance > 0 else 0.0,
                self._cb_pct,
            )

    def _build_state(self, exp: float) -> RiskState:
        dd = self._drawdown()
        rl = self._risk_level(dd)
        dp = self._daily_pnl / self._balance * 100 if self._balance > 0 else 0.0
        return RiskState(
            daily_pnl=round(dp, 4),
            drawdown_from_peak=round(dd, 4),
            consecutive_losses=self._consec_losses,
            trades_today=self._trades_today,
            risk_level=rl,
            max_position_size=round(self._max_pos_size(), 4),
            current_exposure=round(exp, 4),
            kelly_adjusted_fraction=round(self._kelly_adj(dd), 6),
        )

    def _deny(self, reason: str, exp: float, now: float) -> TradeDecision:
        return TradeDecision(False, reason, 0.0, self._build_state(exp), now)

    def _check_day(self) -> None:
        k = self._today()
        if k != self._day_key:
            logger.info("Day rollover %s -> %s", self._day_key, k)
            self.reset_daily()

    @staticmethod
    def _today() -> str:
        return time.strftime("%Y-%m-%d", time.localtime())

    @staticmethod
    def _secs_to_midnight(now: float) -> float:
        lt = time.localtime(now)
        mid = time.mktime(time.struct_time(
            (lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, lt.tm_wday, lt.tm_yday, lt.tm_isdst)
        ))
        return max(0.0, mid + 86400.0 - now)
