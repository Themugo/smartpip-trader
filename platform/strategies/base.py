"""
Strategy Plugin Base — standard lifecycle for all trading strategies.

Every strategy plugin implements:
  initialize()   -> setup resources, validate config
  on_tick()      -> called on every market tick
  generate_signal() -> return a Signal or None
  validate_signal() -> risk-check before execution
  on_trade_complete() -> learn from outcomes
  cleanup()      -> release resources
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Direction(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


class Outcome(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAK_EVEN = "BREAK_EVEN"


class Category(str, Enum):
    TREND = "trend"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    HYBRID = "hybrid"


class AccountType(str, Enum):
    DEMO = "demo"
    REAL = "real"


class SignalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TickData:
    """Single market tick delivered to strategies."""
    price: float
    digit: int
    timestamp: float
    market: str
    volume: float = 0.0
    bid: float = 0.0
    ask: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "price": self.price,
            "digit": self.digit,
            "timestamp": self.timestamp,
            "market": self.market,
            "volume": self.volume,
            "bid": self.bid,
            "ask": self.ask,
        }


@dataclass
class Signal:
    """Normalised signal produced by a strategy."""
    strategy_id: str
    direction: Direction
    confidence: float
    amount: float
    reasoning: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    status: SignalStatus = SignalStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "direction": self.direction.value,
            "confidence": self.confidence,
            "amount": self.amount,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "status": self.status.value,
        }


@dataclass
class SignalValidation:
    """Result of centralized risk validation on a signal."""
    allowed: bool
    reason: str
    adjusted_amount: float
    risk_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "adjusted_amount": self.adjusted_amount,
            "risk_score": self.risk_score,
        }


@dataclass
class TradeResult:
    """Outcome of a closed trade."""
    signal: Signal
    profit: float
    pnl_pct: float
    outcome: Outcome
    duration_seconds: float
    exit_price: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal": self.signal.to_dict(),
            "profit": self.profit,
            "pnl_pct": self.pnl_pct,
            "outcome": self.outcome.value,
            "duration_seconds": self.duration_seconds,
            "exit_price": self.exit_price,
        }


@dataclass
class StrategyMetadata:
    """Declarative metadata for a strategy plugin."""
    strategy_id: str
    name: str
    version: str
    author: str
    description: str
    category: Category
    tags: List[str] = field(default_factory=list)
    min_balance: float = 0.0
    supported_markets: List[str] = field(default_factory=list)
    supported_timeframes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "category": self.category.value,
            "tags": self.tags,
            "min_balance": self.min_balance,
            "supported_markets": self.supported_markets,
            "supported_timeframes": self.supported_timeframes,
        }


@dataclass
class StrategyPerformance:
    """Aggregate performance metrics for a strategy."""
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_trade_duration: float = 0.0
    expectancy: float = 0.0
    total_pnl: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "avg_trade_duration": self.avg_trade_duration,
            "expectancy": self.expectancy,
            "total_pnl": self.total_pnl,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
        }


@dataclass
class CompatibilityCheck:
    """Result of checking whether a strategy works with a market/account."""
    compatible: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compatible": self.compatible,
            "issues": self.issues,
            "warnings": self.warnings,
        }


@dataclass
class AccountState:
    """Snapshot of the trading account."""
    balance: float
    equity: float
    currency: str
    account_type: str
    open_positions: int = 0
    daily_pnl: float = 0.0
    drawdown: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "balance": self.balance,
            "equity": self.equity,
            "currency": self.currency,
            "account_type": self.account_type,
            "open_positions": self.open_positions,
            "daily_pnl": self.daily_pnl,
            "drawdown": self.drawdown,
        }


# ---------------------------------------------------------------------------
# Strategy base class
# ---------------------------------------------------------------------------

class StrategyBase(ABC):
    """Abstract base class that every strategy plugin must inherit from.

    Provides a standard lifecycle (initialize -> on_tick -> generate_signal ->
    validate_signal -> on_trade_complete -> cleanup) together with built-in
    performance tracking, state serialisation, config hot-updating, and
    compatibility checking.
    """

    def __init__(self, strategy_id: str, config: Optional[Dict[str, Any]] = None) -> None:
        self._strategy_id = strategy_id
        self._config: Dict[str, Any] = config if config is not None else {}
        self._logger = logging.getLogger(f"strategy.{strategy_id}")
        self._initialized: bool = False

        self._trade_results: List[TradeResult] = []
        self._performance = StrategyPerformance()
        self._peak_pnl: float = 0.0

    # ------------------------------------------------------------------
    # Abstract interface — every plugin must implement
    # ------------------------------------------------------------------

    @abstractmethod
    def initialize(self) -> bool:
        """Set up resources and validate configuration.

        Returns True when the strategy is ready to receive ticks.
        """
        ...

    @abstractmethod
    def on_tick(self, tick: TickData) -> Optional[Signal]:
        """Called on every market tick.

        Implementations should return a ``Signal`` when they detect an
        actionable opportunity, or ``None`` otherwise.
        """
        ...

    @abstractmethod
    def validate_signal(
        self,
        signal: Signal,
        account_state: AccountState,
    ) -> SignalValidation:
        """Risk-check a signal before it is sent to execution.

        Must return a ``SignalValidation`` describing whether the signal
        is allowed, the reason, any amount adjustment, and a risk score.
        """
        ...

    @abstractmethod
    def on_trade_complete(self, trade_result: TradeResult) -> None:
        """Learn from a completed trade.

        Implementations may update internal models, statistics, or
        adaptive parameters based on the outcome.
        """
        ...

    @abstractmethod
    def cleanup(self) -> None:
        """Release external resources (threads, sockets, file handles)."""
        ...

    # ------------------------------------------------------------------
    # Metadata — subclasses should override to provide real values
    # ------------------------------------------------------------------

    def get_metadata(self) -> StrategyMetadata:
        """Return metadata describing this strategy.

        The default implementation returns a minimal placeholder.  Subclasses
        are expected to override this with accurate information.
        """
        return StrategyMetadata(
            strategy_id=self._strategy_id,
            name=self._strategy_id,
            version="0.0.0",
            author="unknown",
            description="",
            category=Category.HYBRID,
        )

    # ------------------------------------------------------------------
    # Performance tracking
    # ------------------------------------------------------------------

    def get_performance(self) -> StrategyPerformance:
        """Return current performance metrics.

        Metrics are automatically updated each time ``on_trade_complete``
        is called via ``_update_performance``.
        """
        return self._performance

    def _update_performance(self, result: TradeResult) -> None:
        """Recompute performance metrics after a new trade result."""
        self._trade_results.append(result)
        trades = self._trade_results

        total = len(trades)
        wins = [t for t in trades if t.outcome == Outcome.WIN]
        losses = [t for t in trades if t.outcome == Outcome.LOSS]

        win_count = len(wins)
        loss_count = len(losses)

        self._performance.total_trades = total
        self._performance.win_rate = (
            (win_count / total) * 100.0 if total > 0 else 0.0
        )

        gross_profit = sum(t.profit for t in wins) if wins else 0.0
        gross_loss = abs(sum(t.profit for t in losses)) if losses else 0.0
        self._performance.profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else float("inf") if gross_profit > 0 else 0.0
        )

        self._performance.total_pnl = sum(t.profit for t in trades)

        durations = [t.duration_seconds for t in trades]
        self._performance.avg_trade_duration = (
            sum(durations) / len(durations) if durations else 0.0
        )

        self._performance.expectancy = (
            self._performance.total_pnl / total if total > 0 else 0.0
        )

        self._performance.max_drawdown = self._compute_max_drawdown()

        self._update_consecutive_streaks(trades)
        self._update_sharpe_ratio()

    def _compute_max_drawdown(self) -> float:
        """Compute max drawdown (as a percentage) across all trade P&L."""
        if not self._trade_results:
            return 0.0

        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0

        for result in self._trade_results:
            cumulative += result.profit
            if cumulative > peak:
                peak = cumulative
            dd = (peak - cumulative) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        return max_dd * 100.0

    def _update_consecutive_streaks(self, trades: List[TradeResult]) -> None:
        """Track the current consecutive win / loss counts."""
        if not trades:
            self._performance.consecutive_wins = 0
            self._performance.consecutive_losses = 0
            return

        current_streak = 1
        last_outcome = trades[-1].outcome

        for result in reversed(trades[:-1]):
            if result.outcome == last_outcome:
                current_streak += 1
            else:
                break

        if last_outcome == Outcome.WIN:
            self._performance.consecutive_wins = current_streak
            self._performance.consecutive_losses = 0
        elif last_outcome == Outcome.LOSS:
            self._performance.consecutive_losses = current_streak
            self._performance.consecutive_wins = 0
        else:
            self._performance.consecutive_wins = 0
            self._performance.consecutive_losses = 0

    def _update_sharpe_ratio(self) -> None:
        """Compute a simple Sharpe-like ratio from trade P&L series."""
        if len(self._trade_results) < 2:
            self._performance.sharpe_ratio = 0.0
            return

        import numpy as np

        returns = np.array([t.pnl_pct for t in self._trade_results], dtype=np.float64)
        mean_return = float(np.mean(returns))
        std_return = float(np.std(returns, ddof=1))

        if std_return == 0.0:
            self._performance.sharpe_ratio = 0.0
        else:
            self._performance.sharpe_ratio = mean_return / std_return

    # ------------------------------------------------------------------
    # Compatibility
    # ------------------------------------------------------------------

    def is_compatible(
        self,
        market: str,
        account_type: str,
    ) -> CompatibilityCheck:
        """Check whether this strategy supports the given market and account type.

        Subclasses should override to declare their own supported markets and
        timeframes.  The default implementation accepts everything with a
        warning about unvalidated support.
        """
        meta = self.get_metadata()
        issues: List[str] = []
        warnings: List[str] = []

        if meta.supported_markets and market not in meta.supported_markets:
            issues.append(
                f"Market '{market}' not in supported markets: {meta.supported_markets}"
            )

        if account_type not in ("demo", "real"):
            issues.append(f"Unknown account type '{account_type}'")

        if not meta.supported_markets:
            warnings.append("No supported_markets declared; compatibility is unvalidated")

        return CompatibilityCheck(
            compatible=len(issues) == 0,
            issues=issues,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Config management
    # ------------------------------------------------------------------

    def update_config(self, config: Dict[str, Any]) -> None:
        """Hot-update configuration at runtime.

        Merges *config* into the existing configuration dict.  Subclasses
        should override to validate new values before accepting them.
        """
        self._config.update(config)
        self._logger.info("Config updated: %s", list(config.keys()))

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    # ------------------------------------------------------------------
    # State serialisation
    # ------------------------------------------------------------------

    def get_state(self) -> Dict[str, Any]:
        """Serialize mutable state for persistence.

        Subclasses should extend this method to include their own fields.
        The base implementation stores strategy id, config, and performance.
        """
        return {
            "strategy_id": self._strategy_id,
            "config": self._config,
            "performance": self._performance.to_dict(),
            "trade_count": len(self._trade_results),
        }

    def set_state(self, state: Dict[str, Any]) -> None:
        """Restore mutable state from a previously serialized dict.

        Subclasses should extend this to restore their own fields.
        """
        self._config = state.get("config", self._config)

        perf_data = state.get("performance")
        if perf_data is not None:
            self._performance = StrategyPerformance(
                total_trades=perf_data.get("total_trades", 0),
                win_rate=perf_data.get("win_rate", 0.0),
                profit_factor=perf_data.get("profit_factor", 0.0),
                sharpe_ratio=perf_data.get("sharpe_ratio", 0.0),
                max_drawdown=perf_data.get("max_drawdown", 0.0),
                avg_trade_duration=perf_data.get("avg_trade_duration", 0.0),
                expectancy=perf_data.get("expectancy", 0.0),
                total_pnl=perf_data.get("total_pnl", 0.0),
                consecutive_wins=perf_data.get("consecutive_wins", 0),
                consecutive_losses=perf_data.get("consecutive_losses", 0),
            )

        self._logger.info(
            "State restored: %d trades loaded", self._performance.total_trades
        )

    # ------------------------------------------------------------------
    # Helpers for subclasses
    # ------------------------------------------------------------------

    def _clamp_confidence(self, value: float) -> float:
        """Clamp a confidence value to [0, 100]."""
        return max(0.0, min(100.0, value))

    def _create_signal(
        self,
        direction: Direction,
        confidence: float,
        amount: float,
        reasoning: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Signal:
        """Convenience factory for creating a Signal tied to this strategy."""
        return Signal(
            strategy_id=self._strategy_id,
            direction=direction,
            confidence=self._clamp_confidence(confidence),
            amount=amount,
            reasoning=reasoning or [],
            metadata=metadata or {},
        )

    def _default_validation(
        self,
        signal: Signal,
        account_state: AccountState,
    ) -> SignalValidation:
        """A sensible default risk-check that subclasses can delegate to.

        Rules:
        - Account equity must be positive.
        - Signal confidence must be >= 50.
        - Requested amount must not exceed account equity.
        - Daily loss limit: 10% of balance.
        """
        issues: List[str] = []

        if account_state.equity <= 0:
            issues.append("Account equity is non-positive")

        if signal.confidence < 50:
            issues.append(f"Confidence {signal.confidence:.1f} below minimum 50")

        if signal.amount > account_state.equity:
            issues.append(
                f"Amount {signal.amount:.2f} exceeds equity {account_state.equity:.2f}"
            )

        daily_loss_limit = account_state.balance * 0.10
        if account_state.daily_pnl < -daily_loss_limit:
            issues.append(
                f"Daily loss limit breached: {account_state.daily_pnl:.2f} < -{daily_loss_limit:.2f}"
            )

        risk_score = 0.0
        if account_state.equity > 0:
            risk_score += (signal.amount / account_state.equity) * 40.0
        risk_score += (100.0 - signal.confidence) * 0.3
        risk_score += min(account_state.open_positions * 5.0, 20.0)
        risk_score = max(0.0, min(100.0, risk_score))

        allowed = len(issues) == 0
        reason = "; ".join(issues) if issues else "All checks passed"
        adjusted = signal.amount if allowed else 0.0

        return SignalValidation(
            allowed=allowed,
            reason=reason,
            adjusted_amount=adjusted,
            risk_score=risk_score,
        )

    def _log_signal(self, signal: Signal) -> None:
        """Emit a structured log line for a generated signal."""
        self._logger.info(
            "Signal: %s %s conf=%.1f amt=%.2f",
            signal.strategy_id,
            signal.direction.value,
            signal.confidence,
            signal.amount,
        )

    def _log_trade_result(self, result: TradeResult) -> None:
        """Emit a structured log line for a completed trade."""
        self._logger.info(
            "Trade %s: pnl=%.2f (%.1f%%) dur=%.1fs",
            result.outcome.value,
            result.profit,
            result.pnl_pct,
            result.duration_seconds,
        )
