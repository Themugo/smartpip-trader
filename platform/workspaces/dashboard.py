from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import WorkspaceBase

logger = logging.getLogger(__name__)


@dataclass
class RiskAlert:
    alert_id: str
    level: str
    message: str
    timestamp: str = ""
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
        }


@dataclass
class DashboardSnapshot:
    balance: float = 0.0
    equity: float = 0.0
    open_positions: int = 0
    open_pnl: float = 0.0
    daily_pnl: float = 0.0
    active_strategies: int = 0
    risk_alerts: List[Dict[str, Any]] = field(default_factory=list)
    recent_trades: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "balance": self.balance,
            "equity": self.equity,
            "open_positions": self.open_positions,
            "open_pnl": self.open_pnl,
            "daily_pnl": self.daily_pnl,
            "active_strategies": self.active_strategies,
            "risk_alerts": self.risk_alerts,
            "recent_trades": self.recent_trades,
        }


class DashboardWorkspace(WorkspaceBase):
    """Live overview: balance, positions, trades, strategies, P&L, alerts."""

    def __init__(self) -> None:
        super().__init__("dashboard", "Dashboard", "grid_view")
        self._snapshot = DashboardSnapshot()
        self._pnl_history: List[Dict[str, Any]] = []
        self._alerts: List[RiskAlert] = []

    def initialize(self) -> bool:
        logger.info("Dashboard workspace initialized")
        return True

    def get_layout(self) -> Dict[str, Any]:
        return {
            "columns": 3,
            "rows": 2,
            "panels": [
                {"id": "balance_card", "title": "Account Balance", "col_span": 1, "row_span": 1, "widget": "stat_card"},
                {"id": "open_pnl_card", "title": "Open P&L", "col_span": 1, "row_span": 1, "widget": "stat_card"},
                {"id": "daily_pnl_card", "title": "Daily P&L", "col_span": 1, "row_span": 1, "widget": "stat_card"},
                {"id": "positions_table", "title": "Open Positions", "col_span": 2, "row_span": 1, "widget": "table"},
                {"id": "risk_alerts", "title": "Risk Alerts", "col_span": 1, "row_span": 1, "widget": "alert_list"},
                {"id": "pnl_chart", "title": "P&L Chart", "col_span": 2, "row_span": 1, "widget": "line_chart"},
                {"id": "recent_trades", "title": "Recent Trades", "col_span": 1, "row_span": 1, "widget": "table"},
            ],
        }

    def on_data_update(self, data: Dict[str, Any]) -> None:
        if "balance" in data:
            self._snapshot.balance = data["balance"]
        if "equity" in data:
            self._snapshot.equity = data["equity"]
        if "open_positions" in data:
            self._snapshot.open_positions = data["open_positions"]
        if "open_pnl" in data:
            self._snapshot.open_pnl = data["open_pnl"]
        if "daily_pnl" in data:
            self._snapshot.daily_pnl = data["daily_pnl"]
            self._pnl_history.append({
                "value": data["daily_pnl"],
                "timestamp": datetime.utcnow().isoformat(),
            })
        if "recent_trades" in data:
            self._snapshot.recent_trades = data["recent_trades"]
        logger.debug("Dashboard data updated")

    def add_risk_alert(self, alert: RiskAlert) -> None:
        self._alerts.append(alert)
        self._snapshot.risk_alerts = [a.to_dict() for a in self._alerts[-20:]]
        logger.info("Risk alert added: %s", alert.level)

    def acknowledge_alert(self, alert_id: str) -> bool:
        for a in self._alerts:
            if a.alert_id == alert_id:
                a.acknowledged = True
                self._snapshot.risk_alerts = [al.to_dict() for al in self._alerts[-20:]]
                return True
        return False

    def get_snapshot(self) -> DashboardSnapshot:
        return self._snapshot

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["state"]["pnl_history"] = self._pnl_history[-500:]
        state["state"]["alert_count"] = len(self._alerts)
        return state
