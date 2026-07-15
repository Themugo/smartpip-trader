"""
Dashboard Panels
===============

All panel implementations for the Decision Intelligence Dashboard.
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    EXCELLENT = "excellent"  # Green
    GOOD = "good"  # Blue
    WARNING = "warning"  # Yellow
    CRITICAL = "critical"  # Red
    UNKNOWN = "unknown"  # Gray


@dataclass
class HealthMetrics:
    """Health metrics for a component"""
    status: HealthStatus
    score: float  # 0-100
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "score": self.score,
            "message": self.message,
            "details": self.details,
            "last_updated": self.last_updated.isoformat()
        }


class HealthPanel:
    """Base class for health panels"""
    
    def __init__(self, panel_id: str):
        self.panel_id = panel_id
    
    def get_health(self) -> HealthMetrics:
        """Get current health metrics"""
        raise NotImplementedError
    
    def get_history(self, hours: int = 24) -> List[HealthMetrics]:
        """Get health history"""
        raise NotImplementedError


class StrategyHealthPanel(HealthPanel):
    """Strategy health monitoring panel"""
    
    def get_health(self) -> HealthMetrics:
        # Simulated data
        score = random.uniform(70, 100)
        
        if score >= 90:
            status = HealthStatus.EXCELLENT
            message = "All strategies performing optimally"
        elif score >= 75:
            status = HealthStatus.GOOD
            message = "Minor performance degradation detected"
        elif score >= 50:
            status = HealthStatus.WARNING
            message = "Some strategies underperforming"
        else:
            status = HealthStatus.CRITICAL
            message = "Critical strategy issues detected"
        
        return HealthMetrics(
            status=status,
            score=score,
            message=message,
            details={
                "active_strategies": random.randint(3, 8),
                "total_strategies": random.randint(5, 10),
                "avg_sharpe": round(random.uniform(0.8, 2.0), 2),
                "drawdown": round(random.uniform(0.02, 0.15), 2),
                "signals_generated": random.randint(10, 50),
                "execution_rate": round(random.uniform(0.85, 0.99), 2)
            }
        )


class ModelHealthPanel(HealthPanel):
    """Model health monitoring panel"""
    
    def get_health(self) -> HealthMetrics:
        score = random.uniform(75, 100)
        
        if score >= 90:
            status = HealthStatus.EXCELLENT
            message = "All AI models operating normally"
        elif score >= 75:
            status = HealthStatus.GOOD
            message = "Minor model drift detected"
        else:
            status = HealthStatus.WARNING
            message = "Model performance degradation"
        
        return HealthMetrics(
            status=status,
            score=score,
            message=message,
            details={
                "active_models": random.randint(2, 5),
                "model_accuracy": round(random.uniform(0.72, 0.92), 3),
                "confidence_avg": round(random.uniform(0.65, 0.85), 2),
                "drift_detected": random.choice([True, False]),
                "last_training": (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat(),
                "prediction_latency_ms": round(random.uniform(10, 50), 1)
            }
        )


class PluginHealthPanel(HealthPanel):
    """Plugin health monitoring panel"""
    
    def get_health(self) -> HealthMetrics:
        score = random.uniform(80, 100)
        status = HealthStatus.EXCELLENT if score >= 90 else HealthStatus.GOOD
        
        return HealthMetrics(
            status=status,
            score=score,
            message=f"{random.randint(5, 10)} plugins active",
            details={
                "active_plugins": random.randint(5, 10),
                "total_plugins": random.randint(8, 12),
                "plugin_errors": random.randint(0, 2),
                "memory_usage_mb": random.randint(50, 200),
                "cpu_usage_pct": round(random.uniform(1, 10), 1)
            }
        )


class ExecutionHealthPanel(HealthPanel):
    """Execution health monitoring panel"""
    
    def get_health(self) -> HealthMetrics:
        latency = random.uniform(20, 150)
        fill_rate = random.uniform(0.90, 0.99)
        
        if latency < 50 and fill_rate > 0.95:
            status = HealthStatus.EXCELLENT
            message = "Execution performance optimal"
        elif latency < 100 and fill_rate > 0.90:
            status = HealthStatus.GOOD
            message = "Normal execution performance"
        elif latency < 150:
            status = HealthStatus.WARNING
            message = "Elevated latency detected"
        else:
            status = HealthStatus.CRITICAL
            message = "Execution issues detected"
        
        return HealthMetrics(
            status=status,
            score=100 - (latency / 2),  # Lower latency = higher score
            message=message,
            details={
                "avg_latency_ms": round(latency, 1),
                "fill_rate": round(fill_rate, 3),
                "orders_today": random.randint(50, 200),
                "rejections_pct": round(random.uniform(0, 0.05), 3),
                "slippage_avg": round(random.uniform(0.0001, 0.001), 4),
                "queue_depth": random.randint(0, 10)
            }
        )


class PortfolioHealthPanel(HealthPanel):
    """Portfolio health monitoring panel"""
    
    def get_health(self) -> HealthMetrics:
        pnl = random.uniform(-0.05, 0.15)
        dd = random.uniform(0.02, 0.12)
        
        if pnl > 0.05 and dd < 0.05:
            status = HealthStatus.EXCELLENT
            message = "Portfolio performing exceptionally"
        elif pnl > 0 and dd < 0.10:
            status = HealthStatus.GOOD
            message = "Portfolio within risk parameters"
        elif pnl > -0.02:
            status = HealthStatus.WARNING
            message = "Portfolio underperforming"
        else:
            status = HealthStatus.CRITICAL
            message = "Significant portfolio losses"
        
        return HealthMetrics(
            status=status,
            score=max(0, min(100, 50 + (pnl * 500) - (dd * 200))),
            message=message,
            details={
                "total_equity": round(random.uniform(500000, 2000000), 2),
                "daily_pnl": round(pnl * 100000, 2),
                "daily_return": round(pnl * 100, 2),
                "current_drawdown": round(dd * 100, 2),
                "open_positions": random.randint(5, 20),
                "exposure_pct": round(random.uniform(20, 80), 1)
            }
        )


class AccountHealthPanel(HealthPanel):
    """Account health monitoring panel"""
    
    def get_health(self) -> HealthMetrics:
        margin_used = random.uniform(10, 40)
        margin_available = 100 - margin_used
        
        if margin_available > 60:
            status = HealthStatus.EXCELLENT
            message = "Ample margin available"
        elif margin_available > 40:
            status = HealthStatus.GOOD
            message = "Comfortable margin levels"
        elif margin_available > 20:
            status = HealthStatus.WARNING
            message = "Margin levels elevated"
        else:
            status = HealthStatus.CRITICAL
            message = "Margin warning - action required"
        
        return HealthMetrics(
            status=status,
            score=margin_available,
            message=message,
            details={
                "balance": round(random.uniform(100000, 500000), 2),
                "equity": round(random.uniform(100000, 550000), 2),
                "margin_used_pct": round(margin_used, 1),
                "margin_available_pct": round(margin_available, 1),
                "buying_power": round(random.uniform(200000, 1000000), 2),
                "day_trades_remaining": random.randint(0, 3)
            }
        )


class IntelligencePanel:
    """Base class for intelligence panels"""
    
    def __init__(self, panel_id: str):
        self.panel_id = panel_id
    
    def get_value(self) -> Any:
        """Get current value"""
        raise NotImplementedError


class MarketRegimePanel(IntelligencePanel):
    """Market regime detection panel"""
    
    REGIMES = ["trending_up", "trending_down", "ranging", "volatile", "quiet"]
    
    def get_value(self) -> Dict[str, Any]:
        regime = random.choice(self.REGIMES)
        
        return {
            "current_regime": regime,
            "confidence": round(random.uniform(0.70, 0.95), 2),
            "volatility": round(random.uniform(0.5, 2.0), 2),
            "trend_strength": round(random.uniform(0.3, 0.9), 2),
            "volume_profile": random.choice(["high", "normal", "low"]),
            "regime_duration_hours": random.randint(1, 48)
        }


class AIConfidencePanel(IntelligencePanel):
    """AI confidence panel"""
    
    def get_value(self) -> Dict[str, Any]:
        confidence = random.uniform(0.55, 0.95)
        
        return {
            "confidence": round(confidence, 3),
            "confidence_level": self._get_level(confidence),
            "calibrated_confidence": round(confidence * random.uniform(0.95, 1.05), 3),
            "uncertainty": round(1 - confidence, 3),
            "sample_size": random.randint(50, 500)
        }
    
    def _get_level(self, confidence: float) -> str:
        if confidence >= 0.90:
            return "very_high"
        elif confidence >= 0.75:
            return "high"
        elif confidence >= 0.60:
            return "moderate"
        elif confidence >= 0.45:
            return "low"
        else:
            return "very_low"


class OpportunityScorePanel(IntelligencePanel):
    """Opportunity scoring panel"""
    
    def get_value(self) -> Dict[str, Any]:
        score = random.uniform(0.2, 0.9)
        
        return {
            "score": round(score, 3),
            "level": self._get_level(score),
            "signal_strength": round(random.uniform(0.3, 1.0), 2),
            "risk_reward": round(random.uniform(1.5, 4.0), 2),
            "time_horizon": random.choice(["scalp", "day", "swing"]),
            "confidence": round(random.uniform(0.6, 0.95), 2)
        }
    
    def _get_level(self, score: float) -> str:
        if score >= 0.80:
            return "excellent"
        elif score >= 0.65:
            return "good"
        elif score >= 0.50:
            return "moderate"
        elif score >= 0.35:
            return "weak"
        else:
            return "poor"


class RiskScorePanel(IntelligencePanel):
    """Risk scoring panel"""
    
    def get_value(self) -> Dict[str, Any]:
        score = random.uniform(0.1, 0.6)
        
        return {
            "risk_score": round(score, 3),
            "level": self._get_level(score),
            "var_95": round(random.uniform(0.01, 0.05), 4),
            "var_99": round(random.uniform(0.02, 0.08), 4),
            "volatility": round(random.uniform(0.5, 2.0), 2),
            "beta": round(random.uniform(0.5, 1.5), 2),
            "correlations": {
                "vs_benchmark": round(random.uniform(-0.2, 0.8), 2),
                "vs_portfolio": round(random.uniform(-0.3, 0.6), 2)
            }
        }
    
    def _get_level(self, score: float) -> str:
        if score >= 0.50:
            return "high"
        elif score >= 0.35:
            return "elevated"
        elif score >= 0.20:
            return "moderate"
        else:
            return "low"


class AIThoughtsPanel(IntelligencePanel):
    """AI reasoning/thoughts panel"""
    
    def get_value(self) -> Dict[str, Any]:
        return {
            "current_thought": self._generate_thought(),
            "reasoning_chain": [
                self._generate_thought(),
                self._generate_thought(),
                self._generate_thought()
            ],
            "alternatives_considered": random.randint(1, 5),
            "confidence_evolution": [round(random.uniform(0.5, 0.9), 2) for _ in range(5)],
            "key_factors": random.sample([
                "Price action", "Volume", "Volatility", "Trend",
                "Support/Resistance", "Moving Averages", "Momentum",
                "Sentiment", "News", "Earnings"
            ], k=random.randint(3, 6))
        }
    
    def _generate_thought(self) -> str:
        thoughts = [
            "Analyzing recent price action for momentum signals",
            "Cross-referencing with historical patterns",
            "Evaluating volume profile for confirmation",
            "Assessing risk-reward ratio",
            "Checking correlation with sector ETF",
            "Reviewing recent news catalysts",
            "Comparing with similar historical setups",
            "Monitoring key support/resistance levels"
        ]
        return random.choice(thoughts)


class AnalyzerAgreementPanel(IntelligencePanel):
    """Analyzer agreement/voting panel"""
    
    def get_value(self) -> Dict[str, Any]:
        analyzers = random.randint(3, 8)
        votes = [random.choice(["bullish", "bearish", "neutral"]) for _ in range(analyzers)]
        
        bullish = votes.count("bullish")
        bearish = votes.count("bearish")
        neutral = votes.count("neutral")
        
        return {
            "total_analyzers": analyzers,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
            "agreement_pct": round(max(bullish, bearish, neutral) / analyzers * 100, 1),
            "consensus": "bullish" if bullish > bearish else "bearish" if bearish > bullish else "neutral",
            "divergence_score": round(random.uniform(0.1, 0.5), 2)
        }


class HistoricalSimilarityPanel(IntelligencePanel):
    """Historical pattern similarity panel"""
    
    def get_value(self) -> Dict[str, Any]:
        similarity = random.uniform(0.65, 0.95)
        
        return {
            "similarity_score": round(similarity, 3),
            "similar_period": "2023-Q4 Rally",
            "similarity_duration_days": random.randint(10, 45),
            "outcome_probability": round(random.uniform(0.55, 0.80), 2),
            "expected_move_pct": round(random.uniform(2, 10), 1),
            "confidence": round(random.uniform(0.6, 0.9), 2),
            "pattern_match_pct": round(random.uniform(70, 95), 1)
        }


class ExpectedValuePanel(IntelligencePanel):
    """Expected value analysis panel"""
    
    def get_value(self) -> Dict[str, Any]:
        return {
            "expected_value": round(random.uniform(-0.001, 0.005), 5),
            "expected_return": round(random.uniform(-0.1, 0.3), 3),
            "expected_risk": round(random.uniform(0.02, 0.10), 3),
            "sharpe_estimate": round(random.uniform(0.5, 2.5), 2),
            "kelly_fraction": round(random.uniform(0.05, 0.30), 3),
            "confidence_interval": [
                round(random.uniform(-0.02, 0), 4),
                round(random.uniform(0, 0.02), 4)
            ]
        }


class TradeAccuracyPanel(IntelligencePanel):
    """Trade accuracy tracking panel"""
    
    def get_value(self) -> Dict[str, Any]:
        return {
            "recent_accuracy": round(random.uniform(0.55, 0.80), 3),
            "accuracy_trend": random.choice(["improving", "stable", "declining"]),
            "avg_confidence_when_correct": round(random.uniform(0.7, 0.9), 2),
            "avg_confidence_when_wrong": round(random.uniform(0.4, 0.7), 2),
            "calibration_error": round(random.uniform(0.02, 0.10), 3),
            "n_trades": random.randint(50, 200),
            "n_correct": random.randint(30, 150)
        }


class DrawdownPanel(IntelligencePanel):
    """Drawdown monitoring panel"""
    
    def get_value(self) -> Dict[str, Any]:
        current_dd = random.uniform(0.01, 0.15)
        max_dd = random.uniform(current_dd, 0.25)
        
        return {
            "current_drawdown": round(current_dd * 100, 2),
            "max_drawdown": round(max_dd * 100, 2),
            "drawdown_duration_days": random.randint(1, 30),
            "days_since_peak": random.randint(0, 20),
            "recovery_progress": round((1 - current_dd / max_dd) * 100, 1) if max_dd > 0 else 100,
            "consecutive_losing_days": random.randint(0, 8)
        }


class CapitalAllocationPanel(IntelligencePanel):
    """Capital allocation panel"""
    
    def get_value(self) -> Dict[str, Any]:
        return {
            "total_capital": round(random.uniform(500000, 2000000), 2),
            "allocated_capital": round(random.uniform(300000, 1500000), 2),
            "unallocated_capital": round(random.uniform(50000, 500000), 2),
            "allocation_pct": round(random.uniform(50, 85), 1),
            "strategies": {
                f"strategy_{i}": round(random.uniform(50000, 300000), 2)
                for i in range(1, random.randint(3, 6))
            },
            "risk_per_trade": round(random.uniform(0.5, 2.0), 2)
        }


class TradeQueuePanel(IntelligencePanel):
    """Trade queue panel"""
    
    def get_value(self) -> Dict[str, Any]:
        n_trades = random.randint(0, 15)
        
        return {
            "queue_length": n_trades,
            "trades": [
                {
                    "trade_id": f"T{i:04d}",
                    "symbol": random.choice(["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]),
                    "direction": random.choice(["buy", "sell"]),
                    "size": round(random.uniform(0.1, 2.0), 1),
                    "entry_price": round(random.uniform(1.0, 1.5), 5),
                    "wait_time_sec": random.randint(0, 120),
                    "priority": random.choice(["high", "normal", "low"])
                }
                for i in range(n_trades)
            ],
            "avg_wait_time": random.randint(10, 60)
        }


class PendingDecisionsPanel(IntelligencePanel):
    """Pending decisions panel"""
    
    def get_value(self) -> Dict[str, Any]:
        n_pending = random.randint(0, 8)
        
        return {
            "pending_count": n_pending,
            "decisions": [
                {
                    "decision_id": f"D{i:04d}",
                    "type": random.choice(["enter", "exit", "adjust"]),
                    "reason": random.choice([
                        "Awaiting confirmation", "Risk check pending",
                        "Margin check", "Signal validation"
                    ]),
                    "urgency": random.choice(["high", "medium", "low"]),
                    "age_seconds": random.randint(5, 300)
                }
                for i in range(n_pending)
            ]
        }


class OpportunityTrackerPanel(IntelligencePanel):
    """Opportunity tracking panel"""
    
    def get_value(self) -> Dict[str, Any]:
        return {
            "total_opportunities": random.randint(10, 50),
            "accepted": random.randint(5, 30),
            "rejected": random.randint(5, 20),
            "pending": random.randint(0, 10),
            "acceptance_rate": round(random.uniform(0.4, 0.8), 2),
            "avg_opportunity_score": round(random.uniform(0.4, 0.7), 2),
            "rejection_reasons": {
                "low_confidence": random.randint(1, 10),
                "risk_exceeded": random.randint(1, 5),
                "poor_rr": random.randint(1, 5),
                "signal_conflict": random.randint(0, 3)
            }
        }


class SystemMonitorPanel(IntelligencePanel):
    """System resource monitoring panel"""
    
    def get_value(self) -> Dict[str, Any]:
        return {
            "memory": {
                "used_mb": random.randint(500, 2000),
                "total_mb": 4096,
                "used_pct": round(random.uniform(30, 70), 1),
                "trend": random.choice(["stable", "increasing", "decreasing"])
            },
            "cpu": {
                "usage_pct": round(random.uniform(5, 40), 1),
                "cores": 8,
                "load_avg": [round(random.uniform(0.5, 3), 2) for _ in range(3)]
            },
            "gpu": {
                "available": random.choice([True, False]),
                "usage_pct": round(random.uniform(0, 80), 1) if random.random() > 0.3 else 0,
                "memory_mb": random.randint(0, 4000) if random.random() > 0.3 else 0
            },
            "disk": {
                "used_gb": random.randint(50, 200),
                "total_gb": 500,
                "used_pct": round(random.uniform(20, 60), 1)
            }
        }


class ServiceStatusPanel(IntelligencePanel):
    """Service/component status panel"""
    
    def get_value(self) -> Dict[str, Any]:
        services = {
            "websocket": random.choice(["connected", "connected", "connected", "disconnected"]),
            "database": random.choice(["healthy", "healthy", "degraded"]),
            "api_gateway": random.choice(["healthy", "healthy", "degraded"]),
            "execution_engine": random.choice(["operational", "operational"]),
            "ml_pipeline": random.choice(["running", "running", "idle"]),
            "data_feeds": random.choice(["active", "active"]),
            "cache": random.choice(["healthy", "healthy"])
        }
        
        healthy_count = sum(1 for s in services.values() if s == "healthy" or s == "operational" or s == "active" or s == "connected")
        
        return {
            "services": services,
            "healthy_count": healthy_count,
            "total_count": len(services),
            "overall_status": "healthy" if healthy_count == len(services) else "degraded",
            "latencies": {
                "database_ms": round(random.uniform(5, 30), 1),
                "api_ms": round(random.uniform(10, 100), 1),
                "websocket_ms": round(random.uniform(1, 10), 1)
            }
        }


# Export panel classes
__all__ = [
    "HealthStatus",
    "HealthMetrics",
    "HealthPanel",
    "StrategyHealthPanel",
    "ModelHealthPanel",
    "PluginHealthPanel",
    "ExecutionHealthPanel",
    "PortfolioHealthPanel",
    "AccountHealthPanel",
    "IntelligencePanel",
    "MarketRegimePanel",
    "AIConfidencePanel",
    "OpportunityScorePanel",
    "RiskScorePanel",
    "AIThoughtsPanel",
    "AnalyzerAgreementPanel",
    "HistoricalSimilarityPanel",
    "ExpectedValuePanel",
    "TradeAccuracyPanel",
    "DrawdownPanel",
    "CapitalAllocationPanel",
    "TradeQueuePanel",
    "PendingDecisionsPanel",
    "OpportunityTrackerPanel",
    "SystemMonitorPanel",
    "ServiceStatusPanel",
]
