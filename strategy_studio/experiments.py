"""
Experiment Tracking - Automated Experiment Recording

Records every experiment with full context and searchable history.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Experiment:
    """An experiment record"""
    id: str
    name: str
    strategy_id: str
    strategy_version: str
    
    # Context
    dataset: str
    start_date: datetime
    end_date: datetime
    
    # Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Results
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # Status
    status: str = "running"  # running, completed, failed
    outcome: str = ""  # success, failure, inconclusive
    
    # Execution
    execution_time_seconds: float = 0
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "dataset": self.dataset,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "parameters": self.parameters,
            "metrics": self.metrics,
            "status": self.status,
            "outcome": self.outcome,
            "execution_time_seconds": self.execution_time_seconds,
            "tags": self.tags,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ExperimentTracker:
    """
    Experiment Tracker for recording and searching experiments.
    
    Features:
    - Automatic experiment recording
    - Full context capture
    - Searchable history
    - Reproducibility support
    """
    
    def __init__(self, storage_path: str = "data/experiments"):
        self._storage_path = storage_path
        self._experiments: Dict[str, Experiment] = {}
        
        import os
        os.makedirs(storage_path, exist_ok=True)
        self._load_experiments()
    
    def _load_experiments(self) -> None:
        """Load experiments from storage"""
        index_file = f"{self._storage_path}/index.json"
        
        try:
            with open(index_file, "r") as f:
                data = json.load(f)
            
            for exp_data in data.get("experiments", []):
                exp_data["start_date"] = datetime.fromisoformat(exp_data["start_date"])
                exp_data["end_date"] = datetime.fromisoformat(exp_data["end_date"])
                if exp_data.get("completed_at"):
                    exp_data["completed_at"] = datetime.fromisoformat(exp_data["completed_at"])
                
                exp = Experiment(**exp_data)
                self._experiments[exp.id] = exp
            
            logger.info(f"Loaded {len(self._experiments)} experiments")
        except Exception as e:
            logger.warning(f"Could not load experiments: {e}")
    
    def _save_experiments(self) -> None:
        """Save experiments to storage"""
        index_file = f"{self._storage_path}/index.json"
        
        data = {
            "experiments": [e.to_dict() for e in self._experiments.values()],
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def start_experiment(
        self,
        name: str,
        strategy_id: str,
        strategy_version: str,
        dataset: str,
        start_date: datetime,
        end_date: datetime,
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Experiment:
        """Start a new experiment"""
        exp = Experiment(
            id=str(uuid.uuid4()),
            name=name,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            dataset=dataset,
            start_date=start_date,
            end_date=end_date,
            parameters=parameters or {},
            tags=tags or [],
        )
        
        self._experiments[exp.id] = exp
        self._save_experiments()
        
        logger.info(f"Started experiment: {name} ({exp.id})")
        return exp
    
    def complete_experiment(
        self,
        experiment_id: str,
        metrics: Dict[str, float],
        outcome: str,
        notes: str = "",
    ) -> bool:
        """Complete an experiment"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        
        exp.metrics = metrics
        exp.status = "completed"
        exp.outcome = outcome
        exp.notes = notes
        exp.completed_at = datetime.utcnow()
        exp.execution_time_seconds = (
            exp.completed_at - exp.created_at
        ).total_seconds()
        
        self._save_experiments()
        
        logger.info(f"Completed experiment: {exp.name} ({exp.id})")
        return True
    
    def fail_experiment(self, experiment_id: str, error: str) -> bool:
        """Mark an experiment as failed"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        
        exp.status = "failed"
        exp.outcome = "failure"
        exp.notes = error
        exp.completed_at = datetime.utcnow()
        
        self._save_experiments()
        return True
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get an experiment by ID"""
        return self._experiments.get(experiment_id)
    
    def search(
        self,
        strategy_id: Optional[str] = None,
        dataset: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None,
        outcome: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Experiment]:
        """Search experiments"""
        results = list(self._experiments.values())
        
        if strategy_id:
            results = [e for e in results if e.strategy_id == strategy_id]
        
        if dataset:
            results = [e for e in results if dataset in e.dataset]
        
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        
        if status:
            results = [e for e in results if e.status == status]
        
        if outcome:
            results = [e for e in results if e.outcome == outcome]
        
        if since:
            results = [e for e in results if e.created_at >= since]
        
        # Sort by date
        results.sort(key=lambda e: e.created_at, reverse=True)
        
        return results[:limit]
    
    def get_strategy_experiments(
        self,
        strategy_id: str,
        limit: int = 50,
    ) -> List[Experiment]:
        """Get all experiments for a strategy"""
        return self.search(strategy_id=strategy_id, limit=limit)
    
    def get_best_experiment(
        self,
        strategy_id: str,
        metric: str = "sharpe_ratio",
    ) -> Optional[Experiment]:
        """Get the best experiment by metric"""
        experiments = self.get_strategy_experiments(strategy_id)
        
        if not experiments:
            return None
        
        return max(
            experiments,
            key=lambda e: e.metrics.get(metric, 0),
        )
