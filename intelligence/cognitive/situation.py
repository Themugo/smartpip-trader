"""
Layer 2 — Situation Assessment
==============================

Identifies current market regime, quantifies uncertainty, and detects
transitions and anomalies.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .perception import PerceptionResult, TickData

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime types"""
    UNKNOWN = "unknown"
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    QUIESCENT = "quiescent"
    BREAKOUT_IMMINENT = "breakout_imminent"
    REVERSAL_IMMINENT = "reversal_imminent"


class TrendDirection(Enum):
    """Trend direction"""
    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


@dataclass
class RegimeMetrics:
    """Metrics for regime detection"""
    volatility: float  # 0-1 scale
    trend_strength: float  # 0-1 scale
    mean_reversion_strength: float  # 0-1 scale
    volume_profile: str  # increasing, decreasing, stable
    momentum: float  # -1 to 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "volatility": self.volatility,
            "trend_strength": self.trend_strength,
            "mean_reversion_strength": self.mean_reversion_strength,
            "volume_profile": self.volume_profile,
            "momentum": self.momentum
        }


@dataclass
class SituationResult:
    """Result from situation assessment layer"""
    session_id: str
    timestamp: datetime
    regime: MarketRegime
    regime_confidence: float  # 0-1
    trend: TrendDirection
    trend_confidence: float  # 0-1
    volatility: float  # 0-1
    uncertainty: float  # 0-1 (higher = more uncertain)
    regime_transition_detected: bool
    previous_regime: Optional[MarketRegime]
    transition_probability: float  # probability of regime change
    anomalies_detected: List[str]
    metrics: RegimeMetrics
    is_tradeable: bool  # whether current situation is suitable for trading
    confidence: float  # Overall confidence in assessment
    recommended_action: str  # cautious, neutral, aggressive
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "regime": self.regime.value,
            "regime_confidence": self.regime_confidence,
            "trend": self.trend.value,
            "trend_confidence": self.trend_confidence,
            "volatility": self.volatility,
            "uncertainty": self.uncertainty,
            "transition_detected": self.regime_transition_detected,
            "previous_regime": self.previous_regime.value if self.previous_regime else None,
            "transition_probability": self.transition_probability,
            "anomalies": self.anomalies_detected,
            "metrics": self.metrics.to_dict(),
            "is_tradeable": self.is_tradeable,
            "confidence": self.confidence,
            "recommended_action": self.recommended_action
        }


class SituationAssessmentLayer:
    """
    Layer 2: Situation Assessment
    
    Responsible for:
    - Identifying current market regime
    - Quantifying uncertainty
    - Detecting regime transitions and anomalies
    """
    
    def __init__(
        self,
        lookback_periods: int = 50,
        volatility_window: int = 20,
        trend_threshold: float = 0.6,
        volatility_threshold_high: float = 0.7,
        volatility_threshold_low: float = 0.3
    ):
        self.lookback_periods = lookback_periods
        self.volatility_window = volatility_window
        self.trend_threshold = trend_threshold
        self.volatility_threshold_high = volatility_threshold_high
        self.volatility_threshold_low = volatility_threshold_low
        
        self._previous_regime: Optional[MarketRegime] = None
        self._regime_history: List[MarketRegime] = []
        self._price_history: List[float] = []
        self._session_id: Optional[str] = None
        
    def process(
        self,
        perception_result: PerceptionResult,
        historical_ticks: Optional[List[TickData]] = None
    ) -> SituationResult:
        """
        Assess current market situation.
        
        Args:
            perception_result: Result from perception layer
            historical_ticks: Historical tick data for analysis
            
        Returns:
            SituationResult with regime assessment
        """
        self._session_id = perception_result.session_id
        
        # Get price series
        ticks = historical_ticks or perception_result.recent_ticks
        if not ticks:
            return self._create_unknown_result(perception_result, "No data available")
        
        prices = np.array([t.mid_price for t in ticks])
        self._update_price_history(prices)
        
        # Calculate metrics
        metrics = self._calculate_regime_metrics(prices)
        
        # Detect regime
        regime, regime_confidence = self._detect_regime(prices, metrics)
        
        # Detect trend
        trend, trend_confidence = self._detect_trend(prices)
        
        # Check for regime transition
        transition_detected, transition_prob = self._detect_transition(regime)
        
        # Detect anomalies
        anomalies = self._detect_situation_anomalies(prices, metrics)
        
        # Calculate uncertainty
        uncertainty = self._calculate_uncertainty(metrics, regime_confidence, transition_prob)
        
        # Determine if tradeable
        is_tradeable = self._assess_tradeability(
            regime, metrics, transition_detected, uncertainty
        )
        
        # Determine recommended action
        recommended_action = self._get_recommended_action(
            regime, uncertainty, transition_detected
        )
        
        # Calculate overall confidence
        confidence = regime_confidence * 0.5 + trend_confidence * 0.3 + (1 - uncertainty) * 0.2
        confidence = max(0.0, min(1.0, confidence))
        
        # Update history
        self._previous_regime = regime
        self._regime_history.append(regime)
        if len(self._regime_history) > 100:
            self._regime_history.pop(0)
        
        result = SituationResult(
            session_id=self._session_id,
            timestamp=datetime.now(),
            regime=regime,
            regime_confidence=regime_confidence,
            trend=trend,
            trend_confidence=trend_confidence,
            volatility=metrics.volatility,
            uncertainty=uncertainty,
            regime_transition_detected=transition_detected,
            previous_regime=self._previous_regime,
            transition_probability=transition_prob,
            anomalies_detected=anomalies,
            metrics=metrics,
            is_tradeable=is_tradeable,
            confidence=confidence,
            recommended_action=recommended_action
        )
        
        logger.debug(f"Situation: regime={regime.value}, confidence={confidence:.2f}")
        return result
    
    def _calculate_regime_metrics(self, prices: np.ndarray) -> RegimeMetrics:
        """Calculate metrics for regime detection"""
        if len(prices) < 10:
            return RegimeMetrics(
                volatility=0.5,
                trend_strength=0.5,
                mean_reversion_strength=0.5,
                volume_profile="stable",
                momentum=0.0
            )
        
        # Calculate returns
        returns = np.diff(prices) / prices[:-1]
        
        # Volatility (normalized)
        volatility = min(1.0, np.std(returns) * 10) if len(returns) > 0 else 0.5
        
        # Trend strength (using linear regression slope)
        x = np.arange(len(prices))
        if len(prices) > 1:
            slope, _ = np.polyfit(x, prices, 1)
            normalized_slope = abs(slope) / (np.mean(prices) + 1e-10)
            trend_strength = min(1.0, normalized_slope * 100)
        else:
            trend_strength = 0.5
        
        # Mean reversion strength (using autocorrelation)
        if len(returns) > 5:
            autocorr = np.corrcoef(returns[:-1], returns[1:])[0, 1]
            mean_reversion = max(0, autocorr) if not np.isnan(autocorr) else 0.5
        else:
            mean_reversion = 0.5
        
        # Momentum
        if len(prices) >= 10:
            momentum = (prices[-1] - prices[-10]) / prices[-10] if prices[-10] != 0 else 0
            momentum = max(-1, min(1, momentum))
        else:
            momentum = 0.0
        
        # Volume profile (simplified - would need volume data)
        volume_profile = "stable"
        
        return RegimeMetrics(
            volatility=volatility,
            trend_strength=trend_strength,
            mean_reversion_strength=mean_reversion,
            volume_profile=volume_profile,
            momentum=momentum
        )
    
    def _detect_regime(self, prices: np.ndarray, metrics: RegimeMetrics) -> Tuple[MarketRegime, float]:
        """Detect current market regime"""
        if len(prices) < 20:
            return MarketRegime.UNKNOWN, 0.3
        
        confidence = 0.7
        
        # High volatility
        if metrics.volatility > self.volatility_threshold_high:
            return MarketRegime.VOLATILE, min(0.9, metrics.volatility)
        
        # Low volatility
        if metrics.volatility < self.volatility_threshold_low:
            return MarketRegime.QUIESCENT, min(0.9, 1 - metrics.volatility)
        
        # Strong trend detection
        if metrics.trend_strength > self.trend_threshold:
            if metrics.momentum > 0.1:
                return MarketRegime.TRENDING_UP, metrics.trend_strength
            elif metrics.momentum < -0.1:
                return MarketRegime.TRENDING_DOWN, metrics.trend_strength
        
        # Mean reversion (ranging)
        if metrics.mean_reversion_strength > 0.5:
            return MarketRegime.RANGING, metrics.mean_reversion_strength
        
        # Breakout/reversal detection (simplified)
        if len(prices) >= 20:
            recent_range = np.ptp(prices[-20:])
            historical_avg_range = np.mean([np.ptp(prices[max(0, i-20):i]) for i in range(20, len(prices))])
            
            if recent_range > historical_avg_range * 1.5:
                return MarketRegime.BREAKOUT_IMMINENT, 0.6
        
        return MarketRegime.RANGING, confidence
    
    def _detect_trend(self, prices: np.ndarray) -> Tuple[TrendDirection, float]:
        """Detect trend direction"""
        if len(prices) < 10:
            return TrendDirection.NEUTRAL, 0.3
        
        # Simple moving average crossover
        sma_short = np.mean(prices[-5:])
        sma_long = np.mean(prices[-20:]) if len(prices) >= 20 else np.mean(prices)
        
        diff_pct = (sma_short - sma_long) / sma_long if sma_long != 0 else 0
        
        if diff_pct > 0.01:  # 1% threshold
            return TrendDirection.UP, min(0.9, abs(diff_pct) * 50 + 0.5)
        elif diff_pct < -0.01:
            return TrendDirection.DOWN, min(0.9, abs(diff_pct) * 50 + 0.5)
        
        return TrendDirection.NEUTRAL, 0.5
    
    def _detect_transition(
        self,
        current_regime: MarketRegime
    ) -> Tuple[bool, float]:
        """Detect if regime transition is occurring"""
        if not self._previous_regime or self._previous_regime == MarketRegime.UNKNOWN:
            return False, 0.0
        
        if current_regime != self._previous_regime:
            # Check if this is a stable change or just noise
            recent_regimes = self._regime_history[-5:] if len(self._regime_history) >= 5 else self._regime_history
            if recent_regimes.count(current_regime) >= 3:
                return True, 0.8
        
        # Check for imminent transitions
        if current_regime == MarketRegime.QUIESCENT:
            return True, 0.5  # Low volatility often precedes volatility
        
        return False, 0.0
    
    def _detect_situation_anomalies(self, prices: np.ndarray, metrics: RegimeMetrics) -> List[str]:
        """Detect situational anomalies"""
        anomalies = []
        
        if len(prices) < 10:
            return anomalies
        
        # Detect unusual momentum
        if abs(metrics.momentum) > 0.5:
            anomalies.append("unusual_momentum")
        
        # Detect volatility regime change
        if len(self._price_history) >= self.volatility_window * 2:
            current_window = prices[-self.volatility_window:]
            previous_window = self._price_history[-self.volatility_window*2:-self.volatility_window]
            
            current_vol = np.std(np.diff(current_window) / current_window[:-1])
            previous_vol = np.std(np.diff(previous_window) / previous_window[:-1])
            
            if current_vol > previous_vol * 2:
                anomalies.append("volatility_regime_change")
        
        # Detect momentum divergence
        if metrics.trend_strength > 0.7 and metrics.mean_reversion_strength > 0.7:
            anomalies.append("mixed_regime_signals")
        
        return anomalies
    
    def _calculate_uncertainty(
        self,
        metrics: RegimeMetrics,
        regime_confidence: float,
        transition_probability: float
    ) -> float:
        """Calculate overall uncertainty"""
        # Base uncertainty from regime confidence
        base_uncertainty = 1 - regime_confidence
        
        # Add uncertainty from transition probability
        transition_uncertainty = transition_probability * 0.3
        
        # Add uncertainty from mixed signals
        mixed_signal_penalty = 0.2 if (
            metrics.trend_strength > 0.7 and metrics.mean_reversion_strength > 0.7
        ) else 0.0
        
        # High volatility adds uncertainty
        volatility_uncertainty = metrics.volatility * 0.2
        
        uncertainty = base_uncertainty + transition_uncertainty + mixed_signal_penalty + volatility_uncertainty
        return max(0.0, min(1.0, uncertainty))
    
    def _assess_tradeability(
        self,
        regime: MarketRegime,
        metrics: RegimeMetrics,
        transition_detected: bool,
        uncertainty: float
    ) -> bool:
        """Assess if current situation is suitable for trading"""
        # Don't trade in unknown or highly uncertain situations
        if regime == MarketRegime.UNKNOWN or uncertainty > 0.7:
            return False
        
        # Don't trade during regime transitions without confirmation
        if transition_detected and regime in [MarketRegime.BREAKOUT_IMMINENT, MarketRegime.REVERSAL_IMMINENT]:
            return False
        
        # Don't trade in extreme volatility
        if regime == MarketRegime.VOLATILE and uncertainty > 0.5:
            return False
        
        return True
    
    def _get_recommended_action(
        self,
        regime: MarketRegime,
        uncertainty: float,
        transition_detected: bool
    ) -> str:
        """Get recommended action based on situation"""
        if regime == MarketRegime.UNKNOWN or uncertainty > 0.8:
            return "cautious"
        
        if transition_detected:
            return "cautious"
        
        if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            if uncertainty < 0.3:
                return "aggressive"
            return "neutral"
        
        if regime == MarketRegime.RANGING:
            return "neutral"
        
        if regime in [MarketRegime.VOLATILE, MarketRegime.QUIESCENT]:
            return "cautious"
        
        return "neutral"
    
    def _update_price_history(self, prices: np.ndarray) -> None:
        """Update price history"""
        self._price_history.extend(prices.tolist())
        if len(self._price_history) > 500:
            self._price_history = self._price_history[-500:]
    
    def _create_unknown_result(
        self,
        perception_result: PerceptionResult,
        reason: str
    ) -> SituationResult:
        """Create an unknown regime result"""
        return SituationResult(
            session_id=perception_result.session_id,
            timestamp=datetime.now(),
            regime=MarketRegime.UNKNOWN,
            regime_confidence=0.0,
            trend=TrendDirection.NEUTRAL,
            trend_confidence=0.0,
            volatility=0.5,
            uncertainty=1.0,
            regime_transition_detected=False,
            previous_regime=None,
            transition_probability=0.0,
            anomalies_detected=[reason],
            metrics=RegimeMetrics(0.5, 0.5, 0.5, "stable", 0.0),
            is_tradeable=False,
            confidence=0.0,
            recommended_action="cautious",
            metadata={"reason": reason}
        )
    
    def reset(self) -> None:
        """Reset situation assessment state"""
        self._previous_regime = None
        self._regime_history.clear()
        self._price_history.clear()
        logger.info("Situation assessment layer reset")
