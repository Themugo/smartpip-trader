"""
Analysis Manager v3 — 10 analyzers including PatternRecognizer.
Dynamic confidence, entropy-aware signal gating, and smarter consensus logic.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from models import Prediction, AnalysisResult
from .even_odd_analyzer import EvenOddAnalyzer
from .rise_fall_analyzer import RiseFallAnalyzer
from .over_under_analyzer import OverUnderAnalyzer
from .match_diff_analyzer import MatchDiffAnalyzer
from .digit_analyzer import DigitAnalyzer
from .volatility_analyzer import VolatilityAnalyzer
from .technical_analyzer import TechnicalAnalyzer
from .ml_analyzer import MLAnalyzer
from .multitimeframe_analyzer import MultiTimeframeAnalyzer
from .adaptive_confidence import AdaptiveConfidence
from .pattern_recognizer import PatternRecognizer

logger = logging.getLogger(__name__)

ANALYZER_BASE_WEIGHTS = {
    "even_odd":          0.12,
    "rise_fall":         0.15,
    "over_under":        0.12,
    "match_diff":        0.10,
    "digit_analysis":    0.08,
    "volatility_analysis": 0.05,
    "technical":         0.15,
    "ml":                0.13,
    "multitimeframe":    0.05,
    "pattern_recognizer": 0.05,
}


class AnalysisManager:
    """Manages all analysis models and coordinates predictions. v3.0"""

    def __init__(self):
        self.analyzers = {
            "even_odd":            EvenOddAnalyzer(),
            "rise_fall":           RiseFallAnalyzer(),
            "over_under":          OverUnderAnalyzer(),
            "match_diff":          MatchDiffAnalyzer(),
            "digit_analysis":      DigitAnalyzer(),
            "volatility_analysis": VolatilityAnalyzer(),
            "technical":           TechnicalAnalyzer(),
            "ml":                  MLAnalyzer(),
            "multitimeframe":      MultiTimeframeAnalyzer(),
            "pattern_recognizer":  PatternRecognizer(),
        }
        self.adaptive_confidence = AdaptiveConfidence(base_threshold=70)
        self.analysis_result: Dict[str, Any] = {}
        self.trade_signals: List[Dict] = []
        self.best_prediction: Optional[Dict] = None
        self.recent_trades: List[Dict] = []
        self._analyzer_weights = ANALYZER_BASE_WEIGHTS.copy()

        # Entropy state (set by PatternRecognizer after each run)
        self._last_entropy: float = 3.32  # assume random until measured
        self._entropy_filter_threshold: float = 2.2

    # ── Public API ─────────────────────────────────────────────────────────

    def set_analyzer_enabled(self, analyzer_name: str, enabled: bool):
        if analyzer_name in self.analyzers:
            self.analyzers[analyzer_name].set_enabled(enabled)

    def update_weights(self, new_weights: Dict[str, float]):
        """Called by AdaptiveStrategyManager to update per-analyzer weights."""
        for name, w in new_weights.items():
            if name in self._analyzer_weights:
                self._analyzer_weights[name] = max(0.02, min(0.35, w))

    def set_entropy_filter(self, threshold: float):
        self._entropy_filter_threshold = threshold

    async def get_comprehensive_analysis_async(self, data: Dict[str, Any]) -> Dict[str, Any]:
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "last_20_digits": data.get("last_20_digits", []),
            "current_price": data.get("current_price", 0),
            "market": data.get("market", ""),
        }

        tasks = [
            self._run_analyzer_async(name, analyzer, data)
            for name, analyzer in self.analyzers.items()
            if analyzer.is_enabled()
        ]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    continue
                name, ar = result
                analysis[name] = {
                    "prediction": ar.prediction,
                    "confidence": ar.confidence,
                    "data": ar.data,
                }
                # Track entropy from pattern recognizer
                if name == "pattern_recognizer":
                    self._last_entropy = ar.data.get("entropy", self._last_entropy)

        self.analysis_result = analysis
        self.generate_best_prediction()
        return analysis

    async def _run_analyzer_async(self, name, analyzer, data):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, analyzer.analyze, data)
        return name, result

    def get_comprehensive_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "last_20_digits": data.get("last_20_digits", []),
            "current_price": data.get("current_price", 0),
            "market": data.get("market", ""),
        }
        for name, analyzer in self.analyzers.items():
            if analyzer.is_enabled():
                try:
                    result = analyzer.analyze(data)
                    analysis[name] = {
                        "prediction": result.prediction,
                        "confidence": result.confidence,
                        "data": result.data,
                    }
                    if name == "pattern_recognizer":
                        self._last_entropy = result.data.get("entropy", self._last_entropy)
                except Exception as e:
                    logger.warning("Analyzer %s failed: %s", name, e)

        self.analysis_result = analysis
        self.generate_best_prediction()
        return analysis

    def generate_best_prediction(self) -> Optional[Dict]:
        """
        Build weighted-vote consensus across all analyzers.
        Applies entropy filter: skips trade if market is too random.
        """
        predictions: List[Dict] = []

        for name, analyzer in self.analyzers.items():
            if not analyzer.is_enabled():
                continue
            result = self.analysis_result.get(name, {})
            pred = result.get("prediction")
            conf = result.get("confidence", 0)
            if not pred or conf < 55:
                continue
            weight = self._analyzer_weights.get(name, 0.1)
            predictions.append({
                "analyzer": name,
                "direction": pred,
                "confidence": conf,
                "weight": weight,
                "reason": result.get("data", {}).get("reason", name),
            })

        # Entropy filter: if market is near-random, require higher consensus
        entropy_penalty = 0
        if self._last_entropy > 3.1:
            entropy_penalty = 10  # require 10% more confidence
        elif self._last_entropy > 2.8:
            entropy_penalty = 5

        if not predictions:
            self.trade_signals = []
            self.best_prediction = None
            return None

        # Weighted vote
        call_score = sum(p["confidence"] * p["weight"] for p in predictions if "CALL" in p["direction"] or "RISE" in p["direction"] or "EVEN" in p["direction"])
        put_score = sum(p["confidence"] * p["weight"] for p in predictions if "PUT" in p["direction"] or "FALL" in p["direction"] or "ODD" in p["direction"])
        total_weight = sum(p["weight"] for p in predictions)

        if total_weight == 0:
            self.best_prediction = None
            return None

        # Agreement ratio
        total_active = len(predictions)
        call_count = sum(1 for p in predictions if "CALL" in p["direction"] or "RISE" in p["direction"] or "EVEN" in p["direction"])
        put_count = total_active - call_count
        agreement = max(call_count, put_count) / max(total_active, 1)

        consensus_dir = "CALL" if call_score >= put_score else "PUT"
        consensus_conf = (max(call_score, put_score) / total_weight)

        # Boost for high agreement
        if agreement >= 0.8:
            consensus_conf = min(95, consensus_conf * 1.1)
        elif agreement < 0.6:
            consensus_conf *= 0.9  # penalise low agreement

        consensus_conf -= entropy_penalty
        consensus_conf = max(0, min(95, consensus_conf))

        contributing = [p for p in predictions if (
            ("CALL" in p["direction"] or "RISE" in p["direction"] or "EVEN" in p["direction"])
            if consensus_dir == "CALL"
            else ("PUT" in p["direction"] or "FALL" in p["direction"] or "ODD" in p["direction"])
        )]

        best = {
            "type": "CONSENSUS",
            "direction": consensus_dir,
            "confidence": round(consensus_conf, 1),
            "agreement": round(agreement * 100, 1),
            "active_analyzers": total_active,
            "contributing": len(contributing),
            "entropy": round(self._last_entropy, 3),
            "entropy_pct": round(self._last_entropy / 3.321928 * 100, 1),
            "reason": f"{len(contributing)}/{total_active} analyzers → {consensus_dir} ({consensus_conf:.0f}%) [entropy={self._last_entropy:.2f}]",
            "signals": predictions,
        }
        self.trade_signals = predictions
        self.best_prediction = best
        return best

    def get_best_prediction(self) -> Optional[Dict]:
        return self.best_prediction

    def get_trade_signals(self) -> List[Dict]:
        return self.trade_signals

    def get_market_entropy(self) -> float:
        return self._last_entropy

    def get_pattern_health(self) -> Dict[str, Any]:
        pr = self.analyzers.get("pattern_recognizer")
        if pr and hasattr(pr, "get_market_health"):
            return pr.get_market_health()
        return {"status": "unknown"}

    def get_analyzer_weights(self) -> Dict[str, float]:
        return dict(self._analyzer_weights)
