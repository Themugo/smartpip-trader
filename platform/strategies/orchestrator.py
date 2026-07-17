"""
Strategy Orchestrator — Central coordinator for multi-strategy signal fusion.
Collects signals from marketplace strategies, combines via voting or weighted
consensus, validates against centralised risk checks, and exposes trade-
lifecycle hooks.  Persistence uses joblib for compact serialisation.
"""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from platform.strategies.base import (
    AccountState, Direction, Outcome, Signal,
    SignalStatus, SignalValidation, TickData, TradeResult,
)

logger = logging.getLogger(__name__)

VALID_MODES = frozenset({"voting", "weighted", "unanimous", "best"})
_DEFAULTS: Dict[str, Any] = {
    "max_position_pct": 0.02, "max_daily_loss_pct": 0.05,
    "max_drawdown_pct": 0.10, "max_open_positions": 5,
}
_WEIGHT_RECOMPUTE_INTERVAL = 50


# ── Dataclasses ────────────────────────────────────────────────────────────

@dataclass
class StrategyVote:
    """A single strategy's opinion on the current tick."""
    strategy_id: str
    signal: Signal
    weight: float
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "signal": self.signal.to_dict(),
            "weight": round(self.weight, 6),
            "timestamp": self.timestamp,
        }


@dataclass
class ConsensusResult:
    """Outcome of combining multiple strategy votes."""
    direction: Direction
    confidence: float
    agreement_ratio: float
    votes: List[StrategyVote]
    mode: str
    timestamp: float = field(
        default_factory=lambda: datetime.now(timezone.utc).timestamp()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction.value,
            "confidence": round(self.confidence, 4),
            "agreement_ratio": round(self.agreement_ratio, 4),
            "votes": [v.to_dict() for v in self.votes],
            "mode": self.mode, "timestamp": self.timestamp,
        }


# ── Orchestrator ───────────────────────────────────────────────────────────

class StrategyOrchestrator:
    """Coordinates multiple strategies and enforces unified risk policy."""

    def __init__(
        self,
        marketplace: Any | None = None,
        risk_manager: Any | None = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._marketplace_ref: Any = marketplace
        self.risk_manager = risk_manager
        self._settings: Dict[str, Any] = settings or {}
        self._combination_mode: str = self._settings.get("combination_mode", "weighted")
        self._min_confidence: float = self._settings.get("min_confidence", 55.0)
        self._weights: Dict[str, float] = {}
        self._last_weight_recompute: int = 0
        self._trades_since_recompute: int = 0
        self._active_signals: List[Dict[str, Any]] = []
        self._strategy_results: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"wins": 0.0, "losses": 0.0, "total_pnl": 0.0}
        )
        self._consensus_history: List[Dict[str, Any]] = []
        self._max_history: int = int(self._settings.get("max_history", 200))
        self._max_position_pct: float = self._settings.get("max_position_pct", _DEFAULTS["max_position_pct"])
        self._max_daily_loss_pct: float = self._settings.get("max_daily_loss_pct", _DEFAULTS["max_daily_loss_pct"])
        self._max_drawdown_pct: float = self._settings.get("max_drawdown_pct", _DEFAULTS["max_drawdown_pct"])
        self._max_open_positions: int = self._settings.get("max_open_positions", _DEFAULTS["max_open_positions"])
        self._tick_count: int = 0
        self._signals_generated: int = 0
        self._signals_rejected: int = 0
        self._created_at: datetime = datetime.now(timezone.utc)
        logger.info("Orchestrator initialised (mode=%s, min_conf=%.1f)",
                     self._combination_mode, self._min_confidence)

    # ── Marketplace accessor ───────────────────────────────────────────────

    @property
    def marketplace(self) -> Any:
        if self._marketplace_ref is None:
            raise RuntimeError("StrategyMarketplace not assigned")
        return self._marketplace_ref

    @marketplace.setter
    def marketplace(self, value: Any) -> None:
        self._marketplace_ref = value

    # ── Public pipeline ────────────────────────────────────────────────────

    def on_tick(self, tick: TickData, account_state: AccountState) -> Optional[Signal]:
        """Call once per market tick.  Collects votes, combines via the active
        consensus mode, runs centralised risk validation, and returns the
        final Signal or None."""
        self._tick_count += 1
        self._active_signals.clear()

        votes = self._collect_votes(tick, account_state)
        if not votes:
            logger.debug("No votes for %s", tick.market)
            return None

        self._active_signals = [v.to_dict() for v in votes]
        consensus = self._combine_votes(votes)
        if consensus is None:
            return None

        if consensus.confidence * 100 < self._min_confidence:
            return None

        signal = self._consensus_to_signal(consensus, tick)
        validation = self.validate_against_risk(signal, account_state)
        if not validation.allowed:
            self._signals_rejected += 1
            logger.info("Rejected: %s", validation.reason)
            return None

        if validation.adjusted_amount > 0:
            signal.confidence = self._clamp(
                validation.adjusted_amount * 100.0 / max(signal.amount, 1e-9)
            )
        signal.status = SignalStatus.APPROVED
        self._signals_generated += 1
        self._record_consensus(consensus, approved=True)
        return signal

    # ── Vote collection ────────────────────────────────────────────────────

    def _collect_votes(self, tick: TickData, account: AccountState) -> List[StrategyVote]:
        if self._marketplace_ref is None:
            return []
        votes: List[StrategyVote] = []
        now = datetime.now(timezone.utc).timestamp()
        self._ensure_weights()
        installed = self.marketplace.get_installed_strategies()

        for entry in installed:
            sid = entry.get("strategy_id", "")
            if not entry.get("active", False):
                continue
            compat = self.marketplace.check_compatibility(sid, tick.market, account.account_type)
            if not compat.compatible:
                continue
            instance = self.marketplace.get_strategy(sid)
            if instance is None:
                continue
            try:
                result = instance.on_tick(tick)
            except Exception:
                logger.exception("Strategy %s raised on tick", sid)
                continue
            if not isinstance(result, Signal):
                continue
            if result.direction not in (Direction.CALL, Direction.PUT):
                continue
            weight = self._weights.get(sid, 1.0 / max(len(installed), 1))
            votes.append(StrategyVote(strategy_id=sid, signal=result, weight=weight, timestamp=now))

        return votes

    # ── Combination modes ──────────────────────────────────────────────────

    def set_combination_mode(self, mode: str) -> None:
        mode = mode.lower().strip()
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}'. Choose from {VALID_MODES}")
        self._combination_mode = mode

    def _combine_votes(self, votes: List[StrategyVote]) -> Optional[ConsensusResult]:
        dispatch = {
            "voting": self._combine_voting,
            "weighted": self._combine_weighted,
            "unanimous": self._combine_unanimous,
            "best": self._combine_best,
        }
        return dispatch.get(self._combination_mode, lambda _: None)(votes)

    def _combine_voting(self, votes: List[StrategyVote]) -> Optional[ConsensusResult]:
        if not votes:
            return None
        call_n = sum(1 for v in votes if v.signal.direction == Direction.CALL)
        put_n = sum(1 for v in votes if v.signal.direction == Direction.PUT)
        if call_n == put_n:
            return None
        direction = Direction.CALL if call_n > put_n else Direction.PUT
        agreeing = call_n if direction == Direction.CALL else put_n
        total = len(votes)
        confs = [v.signal.confidence for v in votes if v.signal.direction == direction]
        confidence = float(np.mean(confs)) / 100.0 if confs else 0.0
        return ConsensusResult(direction=direction, confidence=confidence,
                               agreement_ratio=agreeing / total, votes=votes, mode="voting")

    def _combine_weighted(self, votes: List[StrategyVote]) -> Optional[ConsensusResult]:
        if not votes:
            return None
        tw = sum(v.weight for v in votes)
        if tw <= 0:
            return None
        cs = sum(v.weight * v.signal.confidence / 100.0 for v in votes if v.signal.direction == Direction.CALL)
        ps = sum(v.weight * v.signal.confidence / 100.0 for v in votes if v.signal.direction == Direction.PUT)
        if cs == ps:
            return None
        direction = Direction.CALL if cs > ps else Direction.PUT
        aw = sum(v.weight for v in votes if v.signal.direction == direction)
        confidence = max(cs, ps) / tw
        return ConsensusResult(direction=direction, confidence=float(confidence),
                               agreement_ratio=float(aw / tw), votes=votes, mode="weighted")

    def _combine_unanimous(self, votes: List[StrategyVote]) -> Optional[ConsensusResult]:
        if not votes:
            return None
        dirs = {v.signal.direction for v in votes}
        if len(dirs) != 1:
            return None
        direction = dirs.pop()
        avg = float(np.mean([v.signal.confidence for v in votes])) / 100.0
        return ConsensusResult(direction=direction, confidence=avg, agreement_ratio=1.0,
                               votes=votes, mode="unanimous")

    def _combine_best(self, votes: List[StrategyVote]) -> Optional[ConsensusResult]:
        if not votes:
            return None
        best = max(votes, key=lambda v: v.signal.confidence)
        return ConsensusResult(direction=best.signal.direction,
                               confidence=best.signal.confidence / 100.0,
                               agreement_ratio=1.0, votes=[best], mode="best")

    # ── Weight management ──────────────────────────────────────────────────

    def _ensure_weights(self) -> None:
        if self._marketplace_ref is None:
            return
        installed = self.marketplace.get_installed_strategies()
        active_ids = {e["strategy_id"] for e in installed if e.get("active")}
        stale = set(self._weights.keys()) != active_ids
        if stale or self._trades_since_recompute >= _WEIGHT_RECOMPUTE_INTERVAL or not self._weights:
            self._recompute_weights(installed)
            self._trades_since_recompute = 0

    def _recompute_weights(self, installed: Optional[List[Dict[str, Any]]] = None) -> None:
        """Derive weights from win_rate * profit_factor * sharpe_ratio, normalised to 1.0."""
        if installed is None:
            installed = self.marketplace.get_installed_strategies()
        raw: Dict[str, float] = {}
        for entry in installed:
            if not entry.get("active"):
                continue
            sid = entry["strategy_id"]
            inst = self.marketplace.get_strategy(sid)
            if inst is None or not hasattr(inst, "get_performance"):
                raw[sid] = 1e-9
                continue
            perf = inst.get_performance()
            wr = getattr(perf, "win_rate", 50.0) / 100.0
            pf = max(getattr(perf, "profit_factor", 1.0), 0.01)
            sr = max(getattr(perf, "sharpe_ratio", 1.0), 0.01)
            raw[sid] = max(wr * pf * sr, 1e-9)
        total = sum(raw.values())
        self._weights = {k: v / total for k, v in raw.items()} if total > 0 else {
            k: 1.0 / max(len(raw), 1) for k in raw
        }
        self._last_weight_recompute = int(time.time())

    # ── Risk validation ────────────────────────────────────────────────────

    def validate_against_risk(self, signal: Signal, account: AccountState) -> SignalValidation:
        """Centralised risk gate — checks position size, daily loss, drawdown,
        open positions, confidence floor, amount vs equity, and external risk manager."""
        issues: List[str] = []
        score = 0.0
        equity = account.equity if account.equity > 0 else account.balance

        if equity * self._max_position_pct <= 0:
            issues.append("Position size zero"); score += 25

        if equity > 0 and account.daily_pnl < 0:
            lr = abs(account.daily_pnl) / equity
            if lr >= self._max_daily_loss_pct:
                issues.append(f"Daily loss {lr:.2%} >= {self._max_daily_loss_pct:.2%}"); score += 30

        dd_limit = self._max_drawdown_pct * 100.0
        if account.drawdown >= dd_limit:
            issues.append(f"Drawdown {account.drawdown:.1f}% >= {dd_limit:.1f}%"); score += 30

        if account.open_positions >= self._max_open_positions:
            issues.append(f"Open positions {account.open_positions} >= {self._max_open_positions}"); score += 20

        if signal.confidence < 50.0:
            issues.append(f"Confidence {signal.confidence:.1f} < 50"); score += 15

        if equity > 0 and signal.amount > equity:
            issues.append(f"Amount {signal.amount:.2f} > equity {equity:.2f}"); score += 20

        if self.risk_manager is not None:
            try:
                rm = self.risk_manager.check_risk_limits(
                    session_pnl=account.daily_pnl,
                    consecutive_losses=account.open_positions,
                    settings=self._settings,
                )
                if isinstance(rm, tuple) and not rm[0]:
                    issues.append(f"Risk manager: {rm[1]}"); score += 25
            except Exception:
                logger.exception("External risk_manager error")

        score = max(0.0, min(100.0, score))
        return SignalValidation(
            allowed=len(issues) == 0,
            reason="; ".join(issues) if issues else "All checks passed",
            adjusted_amount=signal.amount if not issues else 0.0,
            risk_score=score,
        )

    # ── Trade lifecycle ────────────────────────────────────────────────────

    def on_trade_complete(self, trade_result: TradeResult) -> None:
        """Notify strategies of a trade outcome and update weights."""
        sid = trade_result.signal.strategy_id
        bucket = self._strategy_results[sid]
        if trade_result.outcome == Outcome.WIN:
            bucket["wins"] += 1
        else:
            bucket["losses"] += 1
        bucket["total_pnl"] += trade_result.profit

        if self._marketplace_ref is not None:
            self.marketplace.record_trade(sid, trade_result.profit)
            inst = self.marketplace.get_strategy(sid)
            if inst is not None and hasattr(inst, "on_trade_complete"):
                try:
                    inst.on_trade_complete(trade_result)
                except Exception:
                    logger.exception("Strategy %s on_trade_complete failed", sid)

        self._trades_since_recompute += 1
        self._ensure_weights()
        total = bucket["wins"] + bucket["losses"]
        wr = bucket["wins"] / total if total > 0 else 0.5
        logger.info("Trade %s: pnl=%.2f %s (wr=%.2f)", sid, trade_result.profit,
                     trade_result.outcome.value, wr)

    # ── Query helpers ──────────────────────────────────────────────────────

    def get_active_signals(self) -> List[Dict[str, Any]]:
        return list(self._active_signals)

    def get_orchestrator_state(self) -> Dict[str, Any]:
        return {
            "created_at": self._created_at.isoformat(),
            "tick_count": self._tick_count,
            "signals_generated": self._signals_generated,
            "signals_rejected": self._signals_rejected,
            "combination_mode": self._combination_mode,
            "min_confidence": self._min_confidence,
            "weights": dict(self._weights),
            "strategy_results": {s: dict(b) for s, b in self._strategy_results.items()},
            "consensus_history_len": len(self._consensus_history),
            "active_signals": self._active_signals,
            "risk_params": {
                "max_position_pct": self._max_position_pct,
                "max_daily_loss_pct": self._max_daily_loss_pct,
                "max_drawdown_pct": self._max_drawdown_pct,
                "max_open_positions": self._max_open_positions,
            },
            "marketplace_stats": (
                self.marketplace.get_marketplace_stats()
                if self._marketplace_ref is not None
                else {}
            ),
        }

    def update_settings(self, **kwargs: Any) -> None:
        if "combination_mode" in kwargs:
            self.set_combination_mode(kwargs.pop("combination_mode"))
        if "min_confidence" in kwargs:
            self._min_confidence = float(kwargs.pop("min_confidence"))
        for k, v in kwargs.items():
            if hasattr(self, f"_{k}"):
                setattr(self, f"_{k}", v)
            self._settings[k] = v

    # ── Consensus helpers ──────────────────────────────────────────────────

    def _consensus_to_signal(self, consensus: ConsensusResult, tick: TickData) -> Signal:
        contributors = [v.strategy_id for v in consensus.votes]
        avg_amt = float(np.mean([v.signal.amount for v in consensus.votes]))
        return Signal(
            strategy_id="orchestrator",
            direction=consensus.direction,
            confidence=round(consensus.confidence * 100, 2),
            amount=round(avg_amt, 4),
            reasoning=[f"mode={consensus.mode}", f"agree={consensus.agreement_ratio:.2f}",
                       f"from={contributors}"],
            metadata={"mode": consensus.mode, "agreement_ratio": consensus.agreement_ratio,
                       "contributors": contributors, "market": tick.market, "price": tick.price},
        )

    def _record_consensus(self, consensus: ConsensusResult, approved: bool) -> None:
        entry = consensus.to_dict()
        entry["approved"] = approved
        self._consensus_history.append(entry)
        if len(self._consensus_history) > self._max_history:
            self._consensus_history = self._consensus_history[-self._max_history:]

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(100.0, value))

    # ── Persistence ────────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        import joblib as _jl
        state = {
            "weights": self._weights,
            "strategy_results": dict(self._strategy_results),
            "consensus_history": self._consensus_history,
            "settings": self._settings,
            "combination_mode": self._combination_mode,
            "min_confidence": self._min_confidence,
            "tick_count": self._tick_count,
            "signals_generated": self._signals_generated,
            "signals_rejected": self._signals_rejected,
            "created_at": self._created_at.isoformat(),
            "risk_params": {k: getattr(self, f"_{k}") for k in _DEFAULTS},
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        _jl.dump(state, path)
        logger.info("Orchestrator saved to %s", path)

    def load(self, path: str) -> None:
        if not os.path.exists(path):
            logger.warning("No state at %s — starting fresh", path)
            return
        import joblib as _jl
        s = _jl.load(path)
        self._weights = s.get("weights", {})
        self._strategy_results = defaultdict(
            lambda: {"wins": 0.0, "losses": 0.0, "total_pnl": 0.0},
            s.get("strategy_results", {}),
        )
        self._consensus_history = s.get("consensus_history", [])
        self._settings = s.get("settings", {})
        self._combination_mode = s.get("combination_mode", "weighted")
        self._min_confidence = s.get("min_confidence", 55.0)
        self._tick_count = s.get("tick_count", 0)
        self._signals_generated = s.get("signals_generated", 0)
        self._signals_rejected = s.get("signals_rejected", 0)
        if "created_at" in s:
            self._created_at = datetime.fromisoformat(s["created_at"])
        for k, default in _DEFAULTS.items():
            setattr(self, f"_{k}", s.get("risk_params", {}).get(k, default))
        logger.info("Orchestrator loaded from %s", path)
