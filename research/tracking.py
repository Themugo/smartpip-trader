"""
Experiment Tracking Module

Tracks experiments, metrics, and results.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    ACCURACY = "accuracy"
    LOSS = "loss"
    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1"
    SHARPE = "sharpe"
    DRAWDOWN = "drawdown"
    WIN_RATE = "win_rate"
    CUSTOM = "custom"


@dataclass
class MetricRecord:
    """A single metric record"""
    metric_id: str
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "value": self.value,
            "metric_type": self.metric_type.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


class MetricTracker:
    """Tracks metrics for experiments"""
    
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.metrics: Dict[str, List[MetricRecord]] = {}
    
    def log_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.CUSTOM,
        tags: Optional[Dict[str, str]] = None,
    ) -> MetricRecord:
        """Log a metric value"""
        record = MetricRecord(
            metric_id=str(uuid.uuid4()),
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags or {},
        )
        
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(record)
        
        logger.debug(f"Logged metric: {name}={value}")
        return record
    
    def get_metric_history(self, name: str) -> List[MetricRecord]:
        """Get history of a metric"""
        return self.metrics.get(name, [])
    
    def get_latest(self, name: str) -> Optional[float]:
        """Get latest value of a metric"""
        history = self.get_metric_history(name)
        return history[-1].value if history else None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "metrics": {k: [m.to_dict() for m in v] for k, v in self.metrics.items()},
        }


class ExperimentTracker:
    """Tracks experiments and their status"""
    
    def __init__(self, storage_path: str = "data/experiments"):
        self._storage_path = storage_path
        self._experiments: Dict[str, Dict[str, Any]] = {}
        self._load_index()
    
    def _load_index(self) -> None:
        """Load experiment index"""
        import os
        os.makedirs(self._storage_path, exist_ok=True)
        
        index_file = f"{self._storage_path}/index.json"
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    self._experiments = json.load(f)
            except Exception:
                pass
    
    def _save_index(self) -> None:
        """Save experiment index"""
        index_file = f"{self._storage_path}/index.json"
        with open(index_file, "w") as f:
            json.dump(self._experiments, f, indent=2)
    
    def register_experiment(
        self,
        experiment_id: str,
        name: str,
        config: Dict[str, Any],
    ) -> None:
        """Register a new experiment"""
        self._experiments[experiment_id] = {
            "name": name,
            "config": config,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_index()
        logger.info(f"Registered experiment: {experiment_id}")
    
    def update_status(
        self,
        experiment_id: str,
        status: str,
    ) -> None:
        """Update experiment status"""
        if experiment_id in self._experiments:
            self._experiments[experiment_id]["status"] = status
            self._experiments[experiment_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_index()
    
    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment details"""
        return self._experiments.get(experiment_id)
    
    def list_experiments(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all experiments"""
        if status:
            return [e for e in self._experiments.values() if e.get("status") == status]
        return list(self._experiments.values())
