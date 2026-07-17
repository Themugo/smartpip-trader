import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PositionSnapshot:
    """Point-in-time snapshot of a single open position."""
    contract_id: str
    symbol: str
    trade_type: str
    entry_price: float
    current_price: float
    stake: float
    payout: float
    opened_at: float
    duration: float = 0.0
    profit: float = 0.0
    is_closed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "symbol": self.symbol,
            "trade_type": self.trade_type,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "stake": self.stake,
            "payout": self.payout,
            "opened_at": self.opened_at,
            "duration": self.duration,
            "profit": self.profit,
            "is_closed": self.is_closed,
        }


@dataclass
class PortfolioMetrics:
    """Aggregated portfolio-level metrics."""
    total_exposure: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    open_count: int = 0
    margin_used: float = 0.0
    free_margin: float = 0.0
    margin_level: float = 0.0
    win_rate: float = 0.0
    avg_profit: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_exposure": self.total_exposure,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "open_count": self.open_count,
            "margin_used": self.margin_used,
            "free_margin": self.free_margin,
            "margin_level": self.margin_level,
            "win_rate": self.win_rate,
            "avg_profit": self.avg_profit,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
        }


class PortfolioTracker:
    """Tracks open positions, P&L, and portfolio-level metrics.

    This is a pure in-memory tracker that can be fed with data from the
    ``AccountCenter`` or directly by the trading engine.  It uses numpy
    for vectorised metric computation.
    """

    def __init__(self, account_balance: float = 0.0) -> None:
        self._balance = account_balance
        self._positions: Dict[str, PositionSnapshot] = {}
        self._closed_positions: List[PositionSnapshot] = []
        self._pnl_history: List[float] = []
        self._peak_balance: float = account_balance
        logger.debug("PortfolioTracker created (balance=%.2f)", account_balance)

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def update_position(self, contract_id: str, data: Dict[str, Any]) -> None:
        """Add or update a position identified by *contract_id*."""
        now = time.time()
        existing = self._positions.get(contract_id)

        if existing is not None:
            existing.current_price = float(data.get("current_price", existing.current_price))
            existing.stake = float(data.get("stake", existing.stake))
            existing.payout = float(data.get("payout", existing.payout))
            existing.duration = now - existing.opened_at
            raw_profit = data.get("profit", None)
            if raw_profit is not None:
                existing.profit = float(raw_profit)
            else:
                existing.profit = _estimate_profit(existing)
            logger.debug("Position %s updated (pnl=%.4f)", contract_id, existing.profit)
        else:
            entry = float(data.get("entry_price", 0.0))
            current = float(data.get("current_price", entry))
            stake = float(data.get("stake", 0.0))
            payout = float(data.get("payout", 0.0))
            snap = PositionSnapshot(
                contract_id=contract_id,
                symbol=str(data.get("symbol", "UNKNOWN")),
                trade_type=str(data.get("trade_type", "CALL")),
                entry_price=entry,
                current_price=current,
                stake=stake,
                payout=payout,
                opened_at=float(data.get("opened_at", now)),
                duration=now - float(data.get("opened_at", now)),
                profit=float(data.get("profit", 0.0)),
            )
            if snap.profit == 0.0:
                snap.profit = _estimate_profit(snap)
            self._positions[contract_id] = snap
            logger.info(
                "New position %s: %s %s @ %.5f (stake=%.2f)",
                contract_id, snap.trade_type, snap.symbol,
                snap.entry_price, snap.stake,
            )

    def close_position(self, contract_id: str, profit: float) -> None:
        """Mark a position as closed and archive it."""
        pos = self._positions.pop(contract_id, None)
        if pos is None:
            logger.warning("close_position: unknown contract_id=%s", contract_id)
            return
        pos.profit = profit
        pos.is_closed = True
        pos.duration = time.time() - pos.opened_at
        self._closed_positions.append(pos)
        self._pnl_history.append(profit)
        self._balance += profit
        self._update_peak()
        logger.info(
            "Closed position %s (%.2f USD, duration=%.1fs)",
            contract_id, profit, pos.duration,
        )

    def sync_balance(self, new_balance: float) -> None:
        """Update the tracker's view of the account balance."""
        self._balance = new_balance
        self._update_peak()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Return all open positions as plain dicts."""
        return [p.to_dict() for p in self._positions.values()]

    def get_open_count(self) -> int:
        return len(self._positions)

    def get_total_exposure(self) -> float:
        """Sum of stakes across all open positions."""
        return float(np.sum([p.stake for p in self._positions.values()])) if self._positions else 0.0

    def get_unrealized_pnl(self) -> float:
        """Sum of unrealised P&L across open positions."""
        return float(np.sum([p.profit for p in self._positions.values()])) if self._positions else 0.0

    def get_realized_pnl(self) -> float:
        """Sum of P&L from closed positions."""
        if not self._pnl_history:
            return 0.0
        return float(np.sum(self._pnl_history))

    # ------------------------------------------------------------------
    # Aggregate metrics
    # ------------------------------------------------------------------

    def get_portfolio_metrics(self) -> Dict[str, Any]:
        """Compute and return full portfolio-level metrics."""
        exposure = self.get_total_exposure()
        unrealized = self.get_unrealized_pnl()
        realized = self.get_realized_pnl()
        open_count = self.get_open_count()
        margin_used = exposure
        free_margin = max(self._balance - margin_used, 0.0)
        margin_level = (
            (self._balance / margin_used * 100.0)
            if margin_used > 0
            else 0.0
        )

        win_rate = 0.0
        avg_profit = 0.0
        max_dd = 0.0
        sharpe = 0.0

        if self._pnl_history:
            arr = np.array(self._pnl_history, dtype=np.float64)
            wins = float(np.sum(arr > 0))
            win_rate = (wins / len(arr)) * 100.0
            avg_profit = float(np.mean(arr))
            max_dd = _max_drawdown(arr)
            sharpe = _sharpe_ratio(arr)

        metrics = PortfolioMetrics(
            total_exposure=exposure,
            unrealized_pnl=unrealized,
            realized_pnl=realized,
            open_count=open_count,
            margin_used=margin_used,
            free_margin=free_margin,
            margin_level=margin_level,
            win_rate=win_rate,
            avg_profit=avg_profit,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
        )
        return metrics.to_dict()

    def get_position(self, contract_id: str) -> Optional[Dict[str, Any]]:
        pos = self._positions.get(contract_id)
        return pos.to_dict() if pos else None

    def get_symbol_exposure(self, symbol: str) -> float:
        """Total stake for a specific symbol."""
        total = sum(p.stake for p in self._positions.values() if p.symbol == symbol)
        return float(total)

    def get_symbol_pnl(self, symbol: str) -> float:
        """Total P&L (open + closed) for a symbol."""
        open_pnl = sum(p.profit for p in self._positions.values() if p.symbol == symbol)
        closed_pnl = sum(p.profit for p in self._closed_positions if p.symbol == symbol)
        return float(open_pnl + closed_pnl)

    def get_trade_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent closed trades."""
        recent = self._closed_positions[-limit:]
        return [p.to_dict() for p in reversed(recent)]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_peak(self) -> None:
        if self._balance > self._peak_balance:
            self._peak_balance = self._balance

    def reset(self) -> None:
        """Reset tracker state (e.g. on account switch)."""
        self._positions.clear()
        self._closed_positions.clear()
        self._pnl_history.clear()
        self._peak_balance = self._balance
        logger.info("Portfolio tracker reset")


# ======================================================================
# Pure helper functions (numpy-powered)
# ======================================================================


def _estimate_profit(pos: PositionSnapshot) -> float:
    """Rough P&L estimate for a binary option position."""
    if pos.stake <= 0:
        return 0.0
    if pos.trade_type in ("CALL", "DIGITUP", "RISE", "MATCH"):
        progress = (pos.current_price - pos.entry_price) / pos.entry_price if pos.entry_price else 0.0
    elif pos.trade_type in ("PUT", "DIGITDOWN", "FALL", "DIFFER"):
        progress = (pos.entry_price - pos.current_price) / pos.entry_price if pos.entry_price else 0.0
    else:
        progress = 0.0
    capped = float(np.clip(progress, -1.0, 1.0))
    return capped * pos.stake


def _max_drawdown(pnl_array: np.ndarray) -> float:
    """Compute maximum drawdown from an array of P&L values."""
    if len(pnl_array) == 0:
        return 0.0
    cumulative = np.cumsum(pnl_array)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = running_max - cumulative
    return float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0


def _sharpe_ratio(pnl_array: np.ndarray, risk_free: float = 0.0) -> float:
    """Annualised Sharpe-like ratio (assuming 1-period intervals)."""
    if len(pnl_array) < 2:
        return 0.0
    excess = pnl_array - risk_free
    mean_excess = float(np.mean(excess))
    std = float(np.std(excess, ddof=1))
    if std == 0.0:
        return 0.0
    return mean_excess / std
