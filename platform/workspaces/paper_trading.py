from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import WorkspaceBase

logger = logging.getLogger(__name__)


@dataclass
class VirtualTrade:
    trade_id: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    pnl: float
    strategy: str
    timestamp: str = ""
    closed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "pnl": self.pnl,
            "strategy": self.strategy,
            "timestamp": self.timestamp,
            "closed": self.closed,
        }


class PaperTradingWorkspace(WorkspaceBase):
    """Simulated trading with virtual balance — identical to live, no real execution."""

    def __init__(self, virtual_balance: float = 10000.0) -> None:
        super().__init__("paper_trading", "Paper Trading", "science")
        self.virtual_balance = virtual_balance
        self.initial_balance = virtual_balance
        self.virtual_trades: List[VirtualTrade] = []
        self._total_pnl = 0.0
        self._max_balance = virtual_balance
        self._min_balance = virtual_balance
        self._active_positions: List[VirtualTrade] = []

    def initialize(self) -> bool:
        logger.info("PaperTrading workspace initialized with balance %.2f", self.virtual_balance)
        return True

    def get_layout(self) -> Dict[str, Any]:
        return {
            "columns": 3,
            "rows": 2,
            "panels": [
                {"id": "virtual_balance", "title": "Virtual Balance", "col_span": 1, "row_span": 1, "widget": "stat_card"},
                {"id": "virtual_pnl", "title": "Virtual P&L", "col_span": 1, "row_span": 1, "widget": "stat_card"},
                {"id": "win_rate", "title": "Win Rate", "col_span": 1, "row_span": 1, "widget": "stat_card"},
                {"id": "open_virtual", "title": "Open Positions", "col_span": 2, "row_span": 1, "widget": "table"},
                {"id": "virtual_history", "title": "Trade History", "col_span": 1, "row_span": 1, "widget": "table"},
                {"id": "pnl_curve", "title": "P&L Curve", "col_span": 3, "row_span": 1, "widget": "line_chart"},
            ],
        }

    def open_trade(self, symbol: str, direction: str, entry_price: float, strategy: str, lot_size: float = 0.01) -> VirtualTrade:
        trade_id = f"P{len(self.virtual_trades)+1:06d}"
        trade = VirtualTrade(
            trade_id=trade_id,
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            exit_price=0.0,
            pnl=0.0,
            strategy=strategy,
            timestamp=datetime.utcnow().isoformat(),
        )
        self._active_positions.append(trade)
        logger.info("Paper trade opened: %s %s %s @ %.5f", trade_id, symbol, direction, entry_price)
        return trade

    def close_trade(self, trade_id: str, exit_price: float) -> Optional[VirtualTrade]:
        for trade in self._active_positions:
            if trade.trade_id == trade_id:
                trade.exit_price = exit_price
                trade.closed = True
                if trade.direction == "buy":
                    trade.pnl = exit_price - trade.entry_price
                else:
                    trade.pnl = trade.entry_price - exit_price
                self.virtual_balance += trade.pnl
                self._total_pnl += trade.pnl
                self._max_balance = max(self._max_balance, self.virtual_balance)
                self._min_balance = min(self._min_balance, self.virtual_balance)
                self.virtual_trades.append(trade)
                self._active_positions.remove(trade)
                logger.info("Paper trade closed: %s pnl=%.2f", trade_id, trade.pnl)
                return trade
        return None

    def get_virtual_pnl(self) -> float:
        return self._total_pnl

    def get_win_rate(self) -> float:
        if not self.virtual_trades:
            return 0.0
        wins = sum(1 for t in self.virtual_trades if t.pnl > 0)
        return wins / len(self.virtual_trades)

    def get_max_drawdown(self) -> float:
        if self._max_balance == 0:
            return 0.0
        return (self._max_balance - self._min_balance) / self._max_balance

    def reset(self, new_balance: float = 10000.0) -> None:
        self.virtual_balance = new_balance
        self.initial_balance = new_balance
        self.virtual_trades.clear()
        self._active_positions.clear()
        self._total_pnl = 0.0
        self._max_balance = new_balance
        self._min_balance = new_balance
        logger.info("Paper trading reset to %.2f", new_balance)

    def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.virtual_trades[-limit:]]

    def get_open_positions(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._active_positions]

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["state"]["virtual_balance"] = self.virtual_balance
        state["state"]["total_pnl"] = self._total_pnl
        state["state"]["trade_count"] = len(self.virtual_trades)
        state["state"]["open_count"] = len(self._active_positions)
        return state
