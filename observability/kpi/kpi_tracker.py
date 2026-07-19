"""
KPI Tracker
===========

Tracks Business, Strategy, AI, and Execution KPIs.
"""

import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import deque
from datetime import datetime, timezone, timedelta, timedelta

logger = logging.getLogger(__name__)


@dataclass
class KPIDefinition:
    """Definition of a KPI"""
    name: str
    category: str  # business, strategy, ai, execution
    description: str = ""
    unit: str = ""
    aggregation: str = "last"  # last, avg, sum, min, max
    target: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None


@dataclass
class KPIValue:
    """A single KPI value"""
    timestamp: float
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BusinessKPI:
    """Business performance indicators"""
    
    def __init__(self, tracker: 'KPITracker'):
        self.tracker = tracker
        self._register_kpis()
    
    def _register_kpis(self) -> None:
        """Register business KPIs"""
        self.tracker.register(
            "opportunities_detected",
            category="business",
            description="Total opportunities detected",
            unit="count"
        )
        self.tracker.register(
            "opportunities_accepted",
            category="business",
            description="Accepted opportunities",
            unit="count"
        )
        self.tracker.register(
            "opportunities_rejected",
            category="business",
            description="Rejected opportunities",
            unit="count"
        )
        self.tracker.register(
            "acceptance_rate",
            category="business",
            description="Opportunity acceptance rate",
            unit="percent",
            aggregation="avg"
        )
        self.tracker.register(
            "opportunity_score",
            category="business",
            description="Current opportunity score",
            unit="score",
            target=70.0,
            warning_threshold=60.0,
            critical_threshold=50.0
        )
        self.tracker.register(
            "expected_value",
            category="business",
            description="Expected value per trade",
            unit="currency",
            target=1.0,
            warning_threshold=0.5,
            critical_threshold=0.0
        )
        self.tracker.register(
            "win_rate",
            category="business",
            description="Win rate percentage",
            unit="percent",
            target=55.0,
            warning_threshold=50.0,
            critical_threshold=45.0
        )
        self.tracker.register(
            "profit_factor",
            category="business",
            description="Profit factor (gross profit / gross loss)",
            unit="ratio",
            target=1.5,
            warning_threshold=1.2,
            critical_threshold=1.0
        )


class StrategyKPI:
    """Strategy performance indicators"""
    
    def __init__(self, tracker: 'KPITracker'):
        self.tracker = tracker
        self._register_kpis()
    
    def _register_kpis(self) -> None:
        """Register strategy KPIs"""
        self.tracker.register(
            "strategy_pnl",
            category="strategy",
            description="Strategy profit and loss",
            unit="currency"
        )
        self.tracker.register(
            "strategy_pnl_daily",
            category="strategy",
            description="Daily P&L",
            unit="currency"
        )
        self.tracker.register(
            "strategy_positions",
            category="strategy",
            description="Number of open positions",
            unit="count"
        )
        self.tracker.register(
            "strategy_drawdown",
            category="strategy",
            description="Current drawdown",
            unit="percent",
            warning_threshold=10.0,
            critical_threshold=20.0
        )
        self.tracker.register(
            "max_drawdown",
            category="strategy",
            description="Maximum drawdown",
            unit="percent"
        )
        self.tracker.register(
            "sharpe_ratio",
            category="strategy",
            description="Sharpe ratio",
            unit="ratio",
            target=1.5,
            warning_threshold=1.0,
            critical_threshold=0.5
        )
        self.tracker.register(
            "sortino_ratio",
            category="strategy",
            description="Sortino ratio",
            unit="ratio",
            target=2.0,
            warning_threshold=1.5,
            critical_threshold=1.0
        )
        self.tracker.register(
            "calmar_ratio",
            category="strategy",
            description="Calmar ratio",
            unit="ratio",
            target=2.0,
            warning_threshold=1.0,
            critical_threshold=0.5
        )
        self.tracker.register(
            "decision_frequency",
            category="strategy",
            description="Decisions per minute",
            unit="Hz"
        )
        self.tracker.register(
            "paper_vs_live_ratio",
            category="strategy",
            description="Paper to live performance ratio",
            unit="ratio",
            target=1.0,
            warning_threshold=0.8,
            critical_threshold=0.5
        )


class AIKPI:
    """AI/ML performance indicators"""
    
    def __init__(self, tracker: 'KPITracker'):
        self.tracker = tracker
        self._register_kpis()
    
    def _register_kpis(self) -> None:
        """Register AI KPIs"""
        self.tracker.register(
            "prediction_accuracy",
            category="ai",
            description="Model prediction accuracy",
            unit="percent",
            target=70.0,
            warning_threshold=60.0,
            critical_threshold=50.0
        )
        self.tracker.register(
            "prediction_confidence",
            category="ai",
            description="Average prediction confidence",
            unit="percent",
            target=80.0,
            warning_threshold=70.0,
            critical_threshold=60.0
        )
        self.tracker.register(
            "model_drift",
            category="ai",
            description="Model drift score",
            unit="score",
            warning_threshold=0.7,
            critical_threshold=0.9
        )
        self.tracker.register(
            "training_samples",
            category="ai",
            description="Training samples used",
            unit="count"
        )
        self.tracker.register(
            "inference_latency",
            category="ai",
            description="Model inference latency",
            unit="ms"
        )
        self.tracker.register(
            "model_version",
            category="ai",
            description="Active model version",
            unit="version"
        )
        self.tracker.register(
            "retraining_frequency",
            category="ai",
            description="Model retraining frequency",
            unit="times_per_day"
        )


class ExecutionKPI:
    """Execution performance indicators"""
    
    def __init__(self, tracker: 'KPITracker'):
        self.tracker = tracker
        self._register_kpis()
    
    def _register_kpis(self) -> None:
        """Register execution KPIs"""
        self.tracker.register(
            "orders_submitted",
            category="execution",
            description="Total orders submitted",
            unit="count"
        )
        self.tracker.register(
            "orders_filled",
            category="execution",
            description="Orders filled",
            unit="count"
        )
        self.tracker.register(
            "orders_rejected",
            category="execution",
            description="Orders rejected",
            unit="count"
        )
        self.tracker.register(
            "fill_rate",
            category="execution",
            description="Order fill rate",
            unit="percent",
            target=99.0,
            warning_threshold=95.0,
            critical_threshold=90.0
        )
        self.tracker.register(
            "execution_latency",
            category="execution",
            description="Execution latency",
            unit="ms"
        )
        self.tracker.register(
            "slippage_bps",
            category="execution",
            description="Average slippage in basis points",
            unit="bps",
            warning_threshold=5.0,
            critical_threshold=10.0
        )
        self.tracker.register(
            "market_impact_bps",
            category="execution",
            description="Market impact in basis points",
            unit="bps"
        )
        self.tracker.register(
            "queue_length",
            category="execution",
            description="Order queue length",
            unit="count",
            warning_threshold=100,
            critical_threshold=500
        )
        self.tracker.register(
            "rejection_rate",
            category="execution",
            description="Order rejection rate",
            unit="percent",
            warning_threshold=5.0,
            critical_threshold=10.0
        )


class KPITracker:
    """
    Central KPI tracking system.
    
    Tracks:
    - Business KPIs (opportunities, acceptance rate, etc.)
    - Strategy KPIs (P&L, drawdown, ratios, etc.)
    - AI KPIs (prediction accuracy, drift, etc.)
    - Execution KPIs (fill rate, latency, etc.)
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._definitions: Dict[str, KPIDefinition] = {}
        self._values: Dict[str, deque] = {}
        self._lock = threading.Lock()
        self._callbacks: Dict[str, List[Callable]] = {}
        
        # Initialize category trackers
        self.business = BusinessKPI(self)
        self.strategy = StrategyKPI(self)
        self.ai = AIKPI(self)
        self.execution = ExecutionKPI(self)
        
        self._initialized = True
    
    def register(
        self,
        name: str,
        category: str,
        description: str = "",
        unit: str = "",
        aggregation: str = "last",
        target: Optional[float] = None,
        warning_threshold: Optional[float] = None,
        critical_threshold: Optional[float] = None
    ) -> KPIDefinition:
        """Register a new KPI"""
        with self._lock:
            definition = KPIDefinition(
                name=name,
                category=category,
                description=description,
                unit=unit,
                aggregation=aggregation,
                target=target,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold
            )
            self._definitions[name] = definition
            self._values[name] = deque(maxlen=10000)
            return definition
    
    def record(
        self,
        name: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a KPI value"""
        with self._lock:
            if name not in self._definitions:
                # Auto-register
                self._definitions[name] = KPIDefinition(name=name, category="general")
                self._values[name] = deque(maxlen=10000)
            
            kpi_value = KPIValue(
                timestamp=time.time(),
                value=value,
                metadata=metadata or {}
            )
            self._values[name].append(kpi_value)
        
        # Check thresholds and notify
        self._check_thresholds(name, value)
    
    def get(
        self,
        name: str,
        since: Optional[float] = None,
        until: Optional[float] = None,
        aggregation: Optional[str] = None
    ) -> float:
        """Get aggregated KPI value"""
        with self._lock:
            if name not in self._values:
                return 0.0
            
            values = list(self._values[name])
        
        # Filter by time
        if since:
            values = [v for v in values if v.timestamp >= since]
        if until:
            values = [v for v in values if v.timestamp <= until]
        
        if not values:
            return 0.0
        
        # Apply aggregation
        agg = aggregation or self._definitions.get(name, KPIDefinition(name=name, category="")).aggregation
        
        if agg == "avg":
            return sum(v.value for v in values) / len(values)
        elif agg == "sum":
            return sum(v.value for v in values)
        elif agg == "min":
            return min(v.value for v in values)
        elif agg == "max":
            return max(v.value for v in values)
        elif agg == "last":
            return values[-1].value
        else:
            return values[-1].value
    
    def get_timeseries(
        self,
        name: str,
        since: Optional[float] = None,
        until: Optional[float] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get KPI time series"""
        with self._lock:
            if name not in self._values:
                return []
            
            values = list(self._values[name])
        
        if since:
            values = [v for v in values if v.timestamp >= since]
        if until:
            values = [v for v in values if v.timestamp <= until]
        
        return [
            {
                "timestamp": v.timestamp,
                "value": v.value,
                "metadata": v.metadata
            }
            for v in values[-limit:]
        ]
    
    def get_definition(self, name: str) -> Optional[KPIDefinition]:
        """Get KPI definition"""
        with self._lock:
            return self._definitions.get(name)
    
    def list_kpis(self, category: Optional[str] = None) -> List[KPIDefinition]:
        """List all KPI definitions"""
        with self._lock:
            if category:
                return [d for d in self._definitions.values() if d.category == category]
            return list(self._definitions.values())
    
    def get_status(self, name: str) -> str:
        """Get KPI status (ok, warning, critical)"""
        definition = self.get_definition(name)
        if not definition:
            return "unknown"
        
        value = self.get(name, since=time.time() - 3600)  # Last hour
        
        if definition.critical_threshold and value >= definition.critical_threshold:
            return "critical"
        if definition.warning_threshold and value >= definition.warning_threshold:
            return "warning"
        
        return "ok"
    
    def get_all_status(self) -> Dict[str, str]:
        """Get status of all KPIs"""
        return {name: self.get_status(name) for name in self._definitions}
    
    def _check_thresholds(self, name: str, value: float) -> None:
        """Check thresholds and notify callbacks"""
        definition = self.get_definition(name)
        if not definition:
            return
        
        callbacks = self._callbacks.get(name, [])
        
        status = "ok"
        if definition.critical_threshold and value >= definition.critical_threshold:
            status = "critical"
        elif definition.warning_threshold and value >= definition.warning_threshold:
            status = "warning"
        
        for callback in callbacks:
            try:
                callback(name, value, status)
            except Exception as e:
                logger.error(f"KPI callback error: {e}")
    
    def subscribe(
        self,
        name: str,
        callback: Callable[[str, float, str], None]
    ) -> None:
        """Subscribe to KPI updates"""
        with self._lock:
            if name not in self._callbacks:
                self._callbacks[name] = []
            self._callbacks[name].append(callback)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get KPI summary"""
        with self._lock:
            by_category = {}
            for name, definition in self._definitions.items():
                if definition.category not in by_category:
                    by_category[definition.category] = []
                
                latest_value = 0.0
                if self._values.get(name):
                    latest_value = self._values[name][-1].value if self._values[name] else 0.0
                
                by_category[definition.category].append({
                    "name": name,
                    "value": latest_value,
                    "unit": definition.unit,
                    "status": self.get_status(name),
                    "target": definition.target,
                })
        
        return {
            "categories": by_category,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global KPI tracker instance
kpi_tracker = KPITracker()
