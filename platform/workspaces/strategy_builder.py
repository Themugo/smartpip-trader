from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import WorkspaceBase

logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    strategy_id: str
    name: str
    version: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    indicators: List[str] = field(default_factory=list)
    rules: List[Dict[str, Any]] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "version": self.version,
            "parameters": self.parameters,
            "indicators": self.indicators,
            "rules": self.rules,
            "enabled": self.enabled,
        }


@dataclass
class SignalPreview:
    preview_id: str
    strategy_id: str
    signals: List[Dict[str, Any]] = field(default_factory=list)
    win_probability: float = 0.0
    risk_reward: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preview_id": self.preview_id,
            "strategy_id": self.strategy_id,
            "signals": self.signals,
            "win_probability": self.win_probability,
            "risk_reward": self.risk_reward,
        }


class StrategyBuilderWorkspace(WorkspaceBase):
    """Visual/configurable strategy creation, parameter tuning, signal preview."""

    def __init__(self) -> None:
        super().__init__("strategy_builder", "Strategy Builder", "build")
        self._strategies: Dict[str, StrategyConfig] = {}
        self._active_strategy_id: Optional[str] = None
        self._available_indicators = [
            "RSI", "MACD", "EMA", "SMA", "Bollinger Bands",
            "ATR", "Stochastic", "ADX", "Ichimoku", "VWAP",
        ]
        self._previews: List[SignalPreview] = []

    def initialize(self) -> bool:
        logger.info("StrategyBuilder workspace initialized")
        return True

    def get_layout(self) -> Dict[str, Any]:
        return {
            "columns": 3,
            "rows": 2,
            "panels": [
                {"id": "indicator_picker", "title": "Indicators", "col_span": 1, "row_span": 2, "widget": "list_picker"},
                {"id": "parameter_editor", "title": "Parameters", "col_span": 1, "row_span": 1, "widget": "parameter_form"},
                {"id": "rule_builder", "title": "Entry/Exit Rules", "col_span": 1, "row_span": 1, "widget": "rule_editor"},
                {"id": "signal_preview", "title": "Signal Preview", "col_span": 2, "row_span": 1, "widget": "signal_chart"},
                {"id": "strategy_list", "title": "Saved Strategies", "col_span": 2, "row_span": 1, "widget": "table"},
            ],
        }

    def create_strategy(self, name: str, parameters: Optional[Dict[str, Any]] = None) -> StrategyConfig:
        sid = f"SB{len(self._strategies)+1:04d}"
        config = StrategyConfig(
            strategy_id=sid,
            name=name,
            version="1.0.0",
            parameters=parameters or {},
        )
        self._strategies[sid] = config
        self._active_strategy_id = sid
        logger.info("Strategy created: %s (%s)", name, sid)
        return config

    def update_parameters(self, strategy_id: str, params: Dict[str, Any]) -> bool:
        if strategy_id not in self._strategies:
            return False
        self._strategies[strategy_id].parameters.update(params)
        logger.info("Parameters updated for %s: %s", strategy_id, params)
        return True

    def add_indicator(self, strategy_id: str, indicator: str) -> bool:
        if strategy_id not in self._strategies:
            return False
        strat = self._strategies[strategy_id]
        if indicator not in strat.indicators:
            strat.indicators.append(indicator)
            logger.info("Indicator %s added to %s", indicator, strategy_id)
        return True

    def remove_indicator(self, strategy_id: str, indicator: str) -> bool:
        if strategy_id not in self._strategies:
            return False
        strat = self._strategies[strategy_id]
        if indicator in strat.indicators:
            strat.indicators.remove(indicator)
        return True

    def add_rule(self, strategy_id: str, rule: Dict[str, Any]) -> bool:
        if strategy_id not in self._strategies:
            return False
        self._strategies[strategy_id].rules.append(rule)
        logger.info("Rule added to %s: %s", strategy_id, rule.get("type", "unknown"))
        return True

    def preview_signals(self, strategy_id: str, data: Optional[List[Dict[str, Any]]] = None) -> Optional[SignalPreview]:
        if strategy_id not in self._strategies:
            return None
        strat = self._strategies[strategy_id]
        signals = data or []
        preview = SignalPreview(
            preview_id=f"PV{len(self._previews)+1:04d}",
            strategy_id=strategy_id,
            signals=signals[:50],
            win_probability=0.0,
            risk_reward=0.0,
        )
        self._previews.append(preview)
        logger.info("Signal preview generated for %s: %d signals", strategy_id, len(signals))
        return preview

    def get_strategies(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._strategies.values()]

    def get_available_indicators(self) -> List[str]:
        return list(self._available_indicators)

    def delete_strategy(self, strategy_id: str) -> bool:
        if strategy_id in self._strategies:
            del self._strategies[strategy_id]
            if self._active_strategy_id == strategy_id:
                self._active_strategy_id = None
            logger.info("Strategy deleted: %s", strategy_id)
            return True
        return False

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["state"]["active_strategy"] = self._active_strategy_id
        state["state"]["strategy_count"] = len(self._strategies)
        return state
