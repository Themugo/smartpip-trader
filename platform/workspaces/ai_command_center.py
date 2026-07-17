from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import WorkspaceBase

logger = logging.getLogger(__name__)


@dataclass
class RegimeState:
    current_regime: str = "unknown"
    confidence: float = 0.0
    features: Dict[str, float] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_regime": self.current_regime,
            "confidence": self.confidence,
            "features": self.features,
            "history": self.history[-50:],
        }


@dataclass
class EnsembleStatus:
    active_models: List[Dict[str, Any]] = field(default_factory=list)
    consensus_signal: str = "neutral"
    agreement_score: float = 0.0
    model_weights: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_models": self.active_models,
            "consensus_signal": self.consensus_signal,
            "agreement_score": self.agreement_score,
            "model_weights": self.model_weights,
        }


@dataclass
class RLAgentStatus:
    agent_id: str = ""
    state: str = "idle"
    episodes_trained: int = 0
    avg_reward: float = 0.0
    epsilon: float = 0.0
    last_action: str = ""
    portfolio_value: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "state": self.state,
            "episodes_trained": self.episodes_trained,
            "avg_reward": self.avg_reward,
            "epsilon": self.epsilon,
            "last_action": self.last_action,
            "portfolio_value": self.portfolio_value,
        }


@dataclass
class DigitalTwinState:
    twin_id: str = "main"
    status: str = "inactive"
    simulated_balance: float = 0.0
    simulated_pnl: float = 0.0
    sync_lag_ms: float = 0.0
    scenario_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "twin_id": self.twin_id,
            "status": self.status,
            "simulated_balance": self.simulated_balance,
            "simulated_pnl": self.simulated_pnl,
            "sync_lag_ms": self.sync_lag_ms,
            "scenario_count": self.scenario_count,
        }


class AICommandCenterWorkspace(WorkspaceBase):
    """Intelligence layer: regime view, ensemble view, RL agent status, Digital Twin."""

    def __init__(self) -> None:
        super().__init__("ai_command_center", "AI Command Center", "psychology")
        self._regime = RegimeState()
        self._ensemble = EnsembleStatus()
        self._rl_agent = RLAgentStatus()
        self._digital_twin = DigitalTwinState()
        self._system_logs: List[Dict[str, Any]] = []

    def initialize(self) -> bool:
        logger.info("AICommandCenter workspace initialized")
        return True

    def get_layout(self) -> Dict[str, Any]:
        return {
            "columns": 2,
            "rows": 2,
            "panels": [
                {"id": "regime_view", "title": "Market Regime", "col_span": 1, "row_span": 1, "widget": "regime_indicator"},
                {"id": "ensemble_view", "title": "Ensemble Models", "col_span": 1, "row_span": 1, "widget": "model_grid"},
                {"id": "rl_agent", "title": "RL Agent", "col_span": 1, "row_span": 1, "widget": "agent_panel"},
                {"id": "digital_twin", "title": "Digital Twin", "col_span": 1, "row_span": 1, "widget": "twin_panel"},
                {"id": "ai_logs", "title": "AI System Logs", "col_span": 2, "row_span": 1, "widget": "log_viewer"},
            ],
        }

    def update_regime(self, regime: str, confidence: float, features: Optional[Dict[str, float]] = None) -> None:
        self._regime.current_regime = regime
        self._regime.confidence = confidence
        if features:
            self._regime.features = features
        self._regime.history.append({
            "regime": regime,
            "confidence": confidence,
        })
        logger.info("Regime updated: %s (%.2f)", regime, confidence)

    def update_ensemble(self, models: List[Dict[str, Any]], consensus: str, agreement: float) -> None:
        self._ensemble.active_models = models
        self._ensemble.consensus_signal = consensus
        self._ensemble.agreement_score = agreement
        self._ensemble.model_weights = {m.get("name", ""): m.get("weight", 0.0) for m in models}
        logger.info("Ensemble updated: consensus=%s, agreement=%.2f", consensus, agreement)

    def update_rl_agent(self, status: Dict[str, Any]) -> None:
        for k, v in status.items():
            if hasattr(self._rl_agent, k):
                setattr(self._rl_agent, k, v)
        logger.info("RL agent updated: state=%s", self._rl_agent.state)

    def update_digital_twin(self, status: Dict[str, Any]) -> None:
        for k, v in status.items():
            if hasattr(self._digital_twin, k):
                setattr(self._digital_twin, k, v)
        logger.info("Digital twin updated: status=%s", self._digital_twin.status)

    def add_system_log(self, level: str, message: str, source: str = "") -> None:
        self._system_logs.append({
            "level": level,
            "message": message,
            "source": source,
        })
        if len(self._system_logs) > 500:
            self._system_logs = self._system_logs[-500:]

    def get_overview(self) -> Dict[str, Any]:
        return {
            "regime": self._regime.to_dict(),
            "ensemble": self._ensemble.to_dict(),
            "rl_agent": self._rl_agent.to_dict(),
            "digital_twin": self._digital_twin.to_dict(),
        }

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["state"]["regime"] = self._regime.to_dict()
        state["state"]["ensemble_signal"] = self._ensemble.consensus_signal
        state["state"]["rl_state"] = self._rl_agent.state
        state["state"]["twin_status"] = self._digital_twin.status
        return state
