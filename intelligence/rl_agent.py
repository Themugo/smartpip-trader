"""
Reinforcement Learning agent for optimal trade timing and abstention.

Tabular Q-learning with epsilon-greedy exploration.  The state space is
discretised along (regime, entropy_level, volatility_level,
consensus_strength, time_of_day) and the action space is
{TRADE, ABSTAIN}.
"""
import os
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

ACTION_TRADE = "TRADE"
ACTION_ABSTAIN = "ABSTAIN"
ACTION_SPACE = [ACTION_TRADE, ACTION_ABSTAIN]

# ── Discretisation bins ────────────────────────────────────────────────
_REGIME_BINS = {"trending": 0, "ranging": 1, "volatile": 2, "quiet": 3}
_NUM_REGIMES = 4

_ENTROPY_BINS = [0.0, 0.25, 0.5, 0.75, 1.01]
_NUM_ENTROPY = len(_ENTROPY_BINS) - 1

_VOLATILITY_BINS = [0.0, 0.01, 0.03, 0.06, 1.01]
_NUM_VOLATILITY = len(_VOLATILITY_BINS) - 1

_CONSENSUS_BINS = [0.0, 0.4, 0.6, 0.8, 1.01]
_NUM_CONSENSUS = len(_CONSENSUS_BINS) - 1

_TIME_BINS = list(range(0, 25, 6))
_NUM_TIME = len(_TIME_BINS) - 1


def _discretise(value: float, bins: list) -> int:
    for i in range(len(bins) - 1):
        if bins[i] <= value < bins[i + 1]:
            return i
    return len(bins) - 2


def _state_index(regime: str, entropy: float, volatility: float,
                 consensus: float, hour: int) -> int:
    r = _REGIME_BINS.get(regime.lower() if regime else "ranging", 1)
    e = _discretise(entropy, _ENTROPY_BINS)
    v = _discretise(volatility, _VOLATILITY_BINS)
    c = _discretise(consensus, _CONSENSUS_BINS)
    t = _discretise(hour, _TIME_BINS)
    idx = (((r * _NUM_ENTROPY + e) * _NUM_VOLATILITY + v) * _NUM_CONSENSUS + c) * _NUM_TIME + t
    return idx


_NUM_STATES = (_NUM_REGIMES * _NUM_ENTROPY * _NUM_VOLATILITY *
               _NUM_CONSENSUS * _NUM_TIME)


@dataclass
class RLAction:
    """Describes the action chosen by the RL agent."""

    action: str
    confidence: float
    expected_value: float
    q_values: Dict[str, float]
    state_features: Dict[str, Any]
    timestamp: float


class RLAgent:
    """Tabular Q-learning agent for TRADE vs ABSTAIN decisions.

    Parameters
    ----------
    alpha : float
        Learning rate.
    gamma : float
        Discount factor.
    epsilon_start : float
        Initial exploration rate.
    epsilon_end : float
        Final exploration rate after decay.
    decay_episodes : int
        Number of episodes over which epsilon linearly decays.
    """

    def __init__(
        self,
        alpha: float = 0.1,
        gamma: float = 0.95,
        epsilon_start: float = 0.3,
        epsilon_end: float = 0.05,
        decay_episodes: int = 1000,
    ) -> None:
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon_start
        self._epsilon_start = epsilon_start
        self._epsilon_end = epsilon_end
        self._decay_episodes = decay_episodes
        self._episode_count = 0

        self._q_table: np.ndarray = np.zeros((_NUM_STATES, len(ACTION_SPACE)), dtype=np.float64)
        self._visit_counts: np.ndarray = np.zeros((_NUM_STATES, len(ACTION_SPACE)), dtype=np.int64)
        self._total_updates = 0

        logger.info(
            "RLAgent initialised: states=%d actions=%d alpha=%.3f gamma=%.3f epsilon=%.3f",
            _NUM_STATES, len(ACTION_SPACE), alpha, gamma, self.epsilon,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_action(self, state: Dict[str, Any]) -> RLAction:
        """Select an action using epsilon-greedy policy.

        Parameters
        ----------
        state : dict
            Must contain keys: ``regime``, ``entropy``, ``volatility``,
            ``consensus``, ``hour``.
        """
        idx = self._state_index(state)
        q_vals = self._q_table[idx].copy()

        if np.random.random() < self.epsilon:
            action_idx = np.random.randint(len(ACTION_SPACE))
        else:
            action_idx = int(np.argmax(q_vals))

        action_name = ACTION_SPACE[action_idx]
        q_dict = {ACTION_SPACE[i]: round(float(q_vals[i]), 6) for i in range(len(ACTION_SPACE))}
        max_q = float(q_vals[action_idx])
        min_q = float(q_vals.min())
        q_range = max_q - min_q
        confidence = (max_q - min_q) / (abs(max_q) + abs(min_q) + 1e-8) if q_range > 0 else 0.5
        confidence = max(0.0, min(1.0, confidence))

        return RLAction(
            action=action_name,
            confidence=round(confidence, 4),
            expected_value=round(max_q, 6),
            q_values=q_dict,
            state_features=state,
            timestamp=float(time.time()),
        )

    def update(
        self,
        state: Dict[str, Any],
        action: str,
        reward: float,
        next_state: Dict[str, Any],
    ) -> None:
        """Q-learning update: Q(s,a) ← Q(s,a) + α[r + γ max Q(s',·) − Q(s,a)]."""
        s_idx = self._state_index(state)
        a_idx = ACTION_SPACE.index(action) if action in ACTION_SPACE else 0
        ns_idx = self._state_index(next_state)

        best_next = float(np.max(self._q_table[ns_idx]))
        td_target = reward + self.gamma * best_next
        td_error = td_target - self._q_table[s_idx, a_idx]
        self._q_table[s_idx, a_idx] += self.alpha * td_error
        self._visit_counts[s_idx, a_idx] += 1
        self._total_updates += 1

    def compute_reward(
        self,
        action: str,
        profit: float,
        would_have_profit: bool,
    ) -> float:
        """Compute the reward for a taken action given the outcome.

        Parameters
        ----------
        action : str
            ``"TRADE"`` or ``"ABSTAIN"``.
        profit : float
            Actual profit/loss of the trade (ignored when abstaining).
        would_have_profit : bool
            Whether the abstained trade *would* have been profitable.
        """
        if action == ACTION_TRADE:
            if profit > 0:
                return min(profit * 10.0, 5.0)
            else:
                return max(profit * 15.0, -5.0)
        else:
            if would_have_profit:
                return -0.3
            else:
                return 0.15

    def decay_epsilon(self) -> None:
        """Linearly decay epsilon after each learning step."""
        self._episode_count += 1
        if self._episode_count >= self._decay_episodes:
            self.epsilon = self._epsilon_end
        else:
            frac = self._episode_count / self._decay_episodes
            self.epsilon = self._epsilon_start + frac * (self._epsilon_end - self._epsilon_start)

    def get_q_table_stats(self) -> Dict[str, Any]:
        """Return statistics about the current Q-table."""
        visited = int(np.sum(self._visit_counts > 0))
        total_cells = _NUM_STATES * len(ACTION_SPACE)
        trade_visits = int(self._visit_counts[:, 0].sum())
        abstain_visits = int(self._visit_counts[:, 1].sum())
        total_visits = trade_visits + abstain_visits

        return {
            "num_states": _NUM_STATES,
            "num_actions": len(ACTION_SPACE),
            "states_visited": visited,
            "state_coverage": round(visited / total_cells, 6) if total_cells else 0.0,
            "total_updates": self._total_updates,
            "trade_visits": trade_visits,
            "abstain_visits": abstain_visits,
            "trade_pct": round(trade_visits / total_visits * 100, 2) if total_visits else 50.0,
            "avg_q_trade": round(float(self._q_table[:, 0].mean()), 6),
            "avg_q_abstain": round(float(self._q_table[:, 1].mean()), 6),
            "max_q": round(float(self._q_table.max()), 6),
            "min_q": round(float(self._q_table.min()), 6),
            "epsilon": round(self.epsilon, 6),
            "episode_count": self._episode_count,
        }

    def save(self, path: str) -> None:
        """Persist the Q-table and metadata to disk via joblib."""
        import joblib

        payload = {
            "q_table": self._q_table,
            "visit_counts": self._visit_counts,
            "epsilon": self.epsilon,
            "episode_count": self._episode_count,
            "alpha": self.alpha,
            "gamma": self.gamma,
            "total_updates": self._total_updates,
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        joblib.dump(payload, path)
        logger.info("RL Q-table saved to %s (%.1f KB)", path, os.path.getsize(path) / 1024)

    def load(self, path: str) -> bool:
        """Load a previously saved Q-table from disk."""
        import joblib

        if not os.path.exists(path):
            logger.warning("RL Q-table file not found: %s", path)
            return False
        try:
            payload = joblib.load(path)
            self._q_table = payload["q_table"]
            self._visit_counts = payload["visit_counts"]
            self.epsilon = payload.get("epsilon", self._epsilon_start)
            self._episode_count = payload.get("episode_count", 0)
            self.alpha = payload.get("alpha", self.alpha)
            self.gamma = payload.get("gamma", self.gamma)
            self._total_updates = payload.get("total_updates", 0)
            logger.info(
                "RL Q-table loaded from %s: %d states visited, epsilon=%.4f",
                path, int(np.sum(self._visit_counts > 0)), self.epsilon,
            )
            return True
        except Exception as exc:
            logger.error("Failed to load RL Q-table from %s: %s", path, exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _state_index(state: Dict[str, Any]) -> int:
        regime = state.get("regime", "ranging")
        entropy = float(state.get("entropy", 0.5))
        volatility = float(state.get("volatility", 0.02))
        consensus = float(state.get("consensus", 0.5))
        hour = int(state.get("hour", 12))
        idx = _state_index(regime, entropy, volatility, consensus, hour)
        return max(0, min(idx, _NUM_STATES - 1))
