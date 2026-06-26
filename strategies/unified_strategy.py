"""
Unified Strategy v3 — Adaptive weights via AdaptiveStrategyManager,
market-regime awareness, and entropy-gated signal generation.
"""
from typing import Dict, Any, Optional
from collections import deque
from datetime import datetime

import numpy as np

from models import Prediction
from backtesting.strategy import BacktestStrategy
from analysis import AnalysisManager
from indicators import RSI, SMA, EMA, MACD, BollingerBands
from strategies.adaptive_strategy_manager import AdaptiveStrategyManager


class UnifiedStrategy(BacktestStrategy):
    """
    Combines all analyzers with adaptive, performance-tracked weights.
    Blocks trades when market entropy is too high (near-random conditions).
    """

    DEFAULT_WEIGHTS = {
        "even_odd":            0.12,
        "rise_fall":           0.15,
        "over_under":          0.12,
        "match_diff":          0.10,
        "technical":           0.15,
        "ml":                  0.13,
        "digit_analysis":      0.08,
        "volatility_analysis": 0.05,
        "multitimeframe":      0.05,
        "pattern_recognizer":  0.05,
    }

    def __init__(self, min_confidence: float = 75):
        super().__init__("unified")
        self.min_confidence = min_confidence
        self.analysis_manager = AnalysisManager()
        self.adaptive_manager = AdaptiveStrategyManager()

        # Entropy filter
        self._entropy_threshold = 2.8   # below this = patterned market → allow trade
        self._last_entropy: float = 3.32

        # Performance tracking for confidence calibration
        self._recent_outcomes: deque = deque(maxlen=30)
        self._calibration_factor: float = 1.0

        # Regime state
        self._current_regime: Dict[str, str] = {}

    # ── Public API ────────────────────────────────────────────────────────

    def generate_signal(self, data: Dict[str, Any]) -> Optional[Prediction]:
        price_history = data.get("price_history", [])
        if len(price_history) < 20:
            return None

        # Get adaptive weights from manager
        adaptive_weights = self.adaptive_manager.get_current_weights(
            market=data.get("market", "R_100"),
            regime=self._current_regime,
        )
        # Sync weights to analysis manager
        self.analysis_manager.update_weights(adaptive_weights)

        # Run comprehensive analysis
        analysis_result = self.analysis_manager.get_comprehensive_analysis(data)
        self._last_entropy = self.analysis_manager.get_market_entropy()

        # Entropy gate: skip if market is too random
        if self._last_entropy > self._entropy_threshold:
            return None  # market is near-random, no edge

        # Get consensus from analysis manager
        consensus = self.analysis_manager.generate_best_prediction()
        if not consensus:
            return None

        direction = consensus.get("direction")
        confidence = consensus.get("confidence", 0)
        agreement = consensus.get("agreement", 0)

        # Apply calibration factor (adjusts for recent performance)
        confidence *= self._calibration_factor

        # Require minimum confidence
        if confidence < self.min_confidence:
            return None

        # Require minimum agreement among analyzers
        if agreement < 55:
            return None

        reason = self._build_reason(consensus, adaptive_weights)

        return Prediction(
            type="UNIFIED",
            direction=direction,
            confidence=round(confidence, 1),
            reason=reason,
        )

    def record_trade_outcome(self, predicted_direction: str, actual_win: bool,
                              profit: float, market: str, analyzer_contributions: Dict[str, str]):
        """Feed trade result back to adaptive manager and calibrate confidence."""
        self._recent_outcomes.append(1 if actual_win else 0)

        # Update adaptive strategy manager
        for strategy_name, predicted in analyzer_contributions.items():
            self.adaptive_manager.update_strategy_performance(
                strategy=strategy_name,
                profit=profit,
                market=market,
                regime=self._current_regime,
                timestamp=datetime.now().isoformat(),
            )

        # Recalibrate confidence multiplier based on recent win rate
        if len(self._recent_outcomes) >= 10:
            recent_wr = sum(self._recent_outcomes) / len(self._recent_outcomes)
            # If win rate is higher than expected (>55%), boost; if lower, penalise
            self._calibration_factor = max(0.8, min(1.15, 0.85 + recent_wr))

    def set_regime(self, regime: Dict[str, str]):
        self._current_regime = regime

    def set_entropy_threshold(self, threshold: float):
        self._entropy_threshold = threshold

    def get_state(self) -> Dict[str, Any]:
        return {
            "min_confidence": self.min_confidence,
            "entropy_threshold": self._entropy_threshold,
            "last_entropy": round(self._last_entropy, 4),
            "calibration_factor": round(self._calibration_factor, 4),
            "recent_win_rate": (
                round(sum(self._recent_outcomes) / len(self._recent_outcomes) * 100, 1)
                if self._recent_outcomes else None
            ),
            "adaptive_weights": self.adaptive_manager.current_weights,
        }

    # ── Private helpers ───────────────────────────────────────────────────

    def _build_reason(self, consensus: Dict, weights: Dict) -> str:
        contributors = consensus.get("contributing", 0)
        total = consensus.get("active_analyzers", 0)
        entropy = consensus.get("entropy", self._last_entropy)
        direction = consensus.get("direction", "?")
        confidence = consensus.get("confidence", 0)
        top_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]
        weight_str = ", ".join(f"{k}={v:.2f}" for k, v in top_weights)
        return (
            f"Unified {direction} ({confidence:.0f}%) | "
            f"{contributors}/{total} analyzers | "
            f"entropy={entropy:.2f} | "
            f"top weights: {weight_str} | "
            f"cal={self._calibration_factor:.2f}"
        )
