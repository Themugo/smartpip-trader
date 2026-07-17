from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import WorkspaceBase

logger = logging.getLogger(__name__)


@dataclass
class TradeSignal:
    signal_id: str
    strategy: str
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    sl: float = 0.0
    tp: float = 0.0
    timestamp: str = ""
    executed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "strategy": self.strategy,
            "symbol": self.symbol,
            "direction": self.direction,
            "confidence": self.confidence,
            "entry_price": self.entry_price,
            "sl": self.sl,
            "tp": self.tp,
            "timestamp": self.timestamp,
            "executed": self.executed,
        }


@dataclass
class TradeRecord:
    trade_id: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    pnl: float
    strategy: str
    status: str = "closed"
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "pnl": self.pnl,
            "strategy": self.strategy,
            "status": self.status,
            "timestamp": self.timestamp,
        }


class LiveTradingWorkspace(WorkspaceBase):
    """Real-time trading interface with strategy selector, signals, history, and override."""

    def __init__(self) -> None:
        super().__init__("live_trading", "Live Trading", "play_arrow")
        self._active_strategies: List[str] = []
        self._pending_signals: List[TradeSignal] = []
        self._trade_history: List[TradeRecord] = []
        self._manual_override = False
        self._selected_symbol = "Volatility 75"

    def initialize(self) -> bool:
        logger.info("LiveTrading workspace initialized")
        return True

    def get_layout(self) -> Dict[str, Any]:
        return {
            "columns": 3,
            "rows": 2,
            "panels": [
                {"id": "strategy_selector", "title": "Active Strategies", "col_span": 1, "row_span": 1, "widget": "strategy_picker"},
                {"id": "signal_display", "title": "Live Signals", "col_span": 2, "row_span": 1, "widget": "signal_feed"},
                {"id": "trade_history", "title": "Trade History", "col_span": 2, "row_span": 1, "widget": "table"},
                {"id": "manual_override", "title": "Manual Override", "col_span": 1, "row_span": 1, "widget": "toggle_panel"},
            ],
        }

    def set_active_strategies(self, strategies: List[str]) -> None:
        self._active_strategies = list(strategies)
        self._state["active_strategies"] = self._active_strategies
        logger.info("Active strategies set: %s", self._active_strategies)

    def receive_signal(self, signal: TradeSignal) -> None:
        self._pending_signals.append(signal)
        if not self._manual_override and signal.confidence >= 0.7:
            self._execute_signal(signal)
        logger.info("Signal received: %s %s (conf=%.2f)", signal.symbol, signal.direction, signal.confidence)

    def _execute_signal(self, signal: TradeSignal) -> None:
        signal.executed = True
        record = TradeRecord(
            trade_id=f"T{len(self._trade_history)+1:06d}",
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=signal.entry_price,
            exit_price=0.0,
            pnl=0.0,
            strategy=signal.strategy,
            status="open",
            timestamp=signal.timestamp,
        )
        self._trade_history.append(record)
        logger.info("Signal executed: %s", record.trade_id)

    def toggle_manual_override(self) -> bool:
        self._manual_override = not self._manual_override
        logger.info("Manual override: %s", self._manual_override)
        return self._manual_override

    def get_pending_signals(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._pending_signals[-50:]]

    def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._trade_history[-limit:]]

    def set_symbol(self, symbol: str) -> None:
        self._selected_symbol = symbol
        logger.info("Symbol changed to %s", symbol)

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["state"]["active_strategies"] = self._active_strategies
        state["state"]["manual_override"] = self._manual_override
        state["state"]["selected_symbol"] = self._selected_symbol
        state["state"]["trade_count"] = len(self._trade_history)
        return state
