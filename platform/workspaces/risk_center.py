from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from .base import WorkspaceBase

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreaker:
    breaker_id: str
    name: str
    threshold: float
    current_value: float = 0.0
    triggered: bool = False
    action: str = "pause_all"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "breaker_id": self.breaker_id,
            "name": self.name,
            "threshold": self.threshold,
            "current_value": self.current_value,
            "triggered": self.triggered,
            "action": self.action,
        }


@dataclass
class ExposureSnapshot:
    total_exposure: float = 0.0
    long_exposure: float = 0.0
    short_exposure: float = 0.0
    by_symbol: Dict[str, float] = field(default_factory=dict)
    by_strategy: Dict[str, float] = field(default_factory=dict)
    max_position_pct: float = 0.0
    max_correlated_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_exposure": self.total_exposure,
            "long_exposure": self.long_exposure,
            "short_exposure": self.short_exposure,
            "by_symbol": self.by_symbol,
            "by_strategy": self.by_strategy,
            "max_position_pct": self.max_position_pct,
            "max_correlated_pct": self.max_correlated_pct,
        }


class RiskCenterWorkspace(WorkspaceBase):
    """Risk dashboard: circuit breakers, drawdown monitor, position sizing, exposure."""

    def __init__(self) -> None:
        super().__init__("risk_center", "Risk Center", "shield")
        self._circuit_breakers: List[CircuitBreaker] = []
        self._exposure = ExposureSnapshot()
        self._drawdown_history: List[Dict[str, Any]] = []
        self._max_daily_loss = 0.0
        self._current_daily_loss = 0.0
        self._risk_params = {
            "max_risk_per_trade": 0.02,
            "max_daily_loss_pct": 0.05,
            "max_drawdown_pct": 0.10,
            "max_positions": 5,
            "max_correlated_positions": 2,
        }

    def initialize(self) -> bool:
        self._circuit_breakers = [
            CircuitBreaker("CB1", "Max Daily Loss", self._risk_params["max_daily_loss_pct"]),
            CircuitBreaker("CB2", "Max Drawdown", self._risk_params["max_drawdown_pct"]),
            CircuitBreaker("CB3", "Max Positions", float(self._risk_params["max_positions"])),
            CircuitBreaker("CB4", "Max Exposure", 0.30),
        ]
        logger.info("RiskCenter initialized with %d circuit breakers", len(self._circuit_breakers))
        return True

    def get_layout(self) -> Dict[str, Any]:
        return {
            "columns": 3,
            "rows": 2,
            "panels": [
                {"id": "circuit_breakers", "title": "Circuit Breakers", "col_span": 1, "row_span": 1, "widget": "indicator_grid"},
                {"id": "drawdown_monitor", "title": "Drawdown Monitor", "col_span": 2, "row_span": 1, "widget": "gauge_chart"},
                {"id": "position_sizing", "title": "Position Sizing", "col_span": 1, "row_span": 1, "widget": "calculator"},
                {"id": "exposure_map", "title": "Exposure Map", "col_span": 2, "row_span": 1, "widget": "heatmap"},
                {"id": "risk_params", "title": "Risk Parameters", "col_span": 1, "row_span": 1, "widget": "config_form"},
            ],
        }

    def update_circuit_breaker(self, breaker_id: str, value: float) -> bool:
        for cb in self._circuit_breakers:
            if cb.breaker_id == breaker_id:
                cb.current_value = value
                if value >= cb.threshold and not cb.triggered:
                    cb.triggered = True
                    logger.warning("Circuit breaker TRIGGERED: %s (%.2f >= %.2f)", cb.name, value, cb.threshold)
                    return True
                elif value < cb.threshold * 0.9:
                    cb.triggered = False
                return True
        return False

    def check_all_breakers(self) -> List[Dict[str, Any]]:
        triggered = [cb.to_dict() for cb in self._circuit_breakers if cb.triggered]
        return triggered

    def update_drawdown(self, equity: float, peak_equity: float) -> float:
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
        self._drawdown_history.append({
            "drawdown": dd,
            "equity": equity,
            "peak": peak_equity,
        })
        self.update_circuit_breaker("CB2", dd)
        return dd

    def update_exposure(self, positions: List[Dict[str, Any]], account_balance: float) -> ExposureSnapshot:
        long_exp = 0.0
        short_exp = 0.0
        by_symbol: Dict[str, float] = {}
        by_strategy: Dict[str, float] = {}
        for pos in positions:
            size = abs(pos.get("size", 0.0))
            direction = pos.get("direction", "buy")
            symbol = pos.get("symbol", "unknown")
            strategy = pos.get("strategy", "unknown")
            if direction == "buy":
                long_exp += size
            else:
                short_exp += size
            by_symbol[symbol] = by_symbol.get(symbol, 0.0) + size
            by_strategy[strategy] = by_strategy.get(strategy, 0.0) + size
        total = long_exp + short_exp
        self._exposure = ExposureSnapshot(
            total_exposure=total,
            long_exposure=long_exp,
            short_exposure=short_exp,
            by_symbol=by_symbol,
            by_strategy=by_strategy,
            max_position_pct=max(by_symbol.values()) / account_balance if by_symbol and account_balance > 0 else 0.0,
            max_correlated_pct=0.0,
        )
        return self._exposure

    def calculate_position_size(self, account_balance: float, entry_price: float, sl_price: float, risk_pct: Optional[float] = None) -> float:
        risk = risk_pct or self._risk_params["max_risk_per_trade"]
        risk_amount = account_balance * risk
        sl_distance = abs(entry_price - sl_price)
        if sl_distance == 0:
            return 0.0
        size = risk_amount / sl_distance
        logger.debug("Position size calculated: %.4f (risk=%.2f%%, sl_dist=%.5f)", size, risk * 100, sl_distance)
        return size

    def update_risk_params(self, params: Dict[str, Any]) -> None:
        self._risk_params.update(params)
        for cb in self._circuit_breakers:
            if cb.name == "Max Daily Loss" and "max_daily_loss_pct" in params:
                cb.threshold = params["max_daily_loss_pct"]
            elif cb.name == "Max Drawdown" and "max_drawdown_pct" in params:
                cb.threshold = params["max_drawdown_pct"]
        logger.info("Risk params updated: %s", params)

    def get_risk_summary(self) -> Dict[str, Any]:
        return {
            "circuit_breakers": [cb.to_dict() for cb in self._circuit_breakers],
            "exposure": self._exposure.to_dict(),
            "drawdown_history": self._drawdown_history[-100:],
            "risk_params": dict(self._risk_params),
        }

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["state"]["risk_params"] = dict(self._risk_params)
        state["state"]["triggered_breakers"] = sum(1 for cb in self._circuit_breakers if cb.triggered)
        return state
