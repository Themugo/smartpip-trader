"""
Research Lab - AI Experimentation and Benchmarking

Provides comprehensive research capabilities:
- Strategy comparison
- AI model evaluation
- Feature set analysis
- Ensemble configuration
- Parameter sweeps
- Experiment tracking
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    """Experiment status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExperimentType(Enum):
    """Type of experiment"""
    STRATEGY_COMPARE = "strategy_compare"
    MODEL_COMPARE = "model_compare"
    FEATURE_SET = "feature_set"
    ENSEMBLE_CONFIG = "ensemble_config"
    PARAMETER_SWEEP = "parameter_sweep"
    HYPERPARAMETER_TUNING = "hyperparameter_tuning"
    BACKTEST = "backtest"
    FORWARD_TEST = "forward_test"


@dataclass
class MetricValue:
    """A single metric value"""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


@dataclass
class ExperimentConfig:
    """Configuration for an experiment"""
    experiment_type: ExperimentType
    name: str
    description: str = ""
    
    # Subject configuration
    subjects: List[str] = field(default_factory=list)  # Strategy/model IDs
    subject_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Data configuration
    data_source: str = "historical"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    symbols: List[str] = field(default_factory=list)
    
    # Evaluation configuration
    metrics: List[str] = field(default_factory=list)
    primary_metric: str = "sharpe_ratio"
    optimization_direction: str = "maximize"  # maximize or minimize
    
    # Execution configuration
    parallel: bool = False
    max_workers: int = 4
    timeout: int = 3600  # seconds
    
    # Additional parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_type": self.experiment_type.value,
            "name": self.name,
            "description": self.description,
            "subjects": self.subjects,
            "subject_configs": self.subject_configs,
            "data_source": self.data_source,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "symbols": self.symbols,
            "metrics": self.metrics,
            "primary_metric": self.primary_metric,
            "optimization_direction": self.optimization_direction,
            "parallel": self.parallel,
            "max_workers": self.max_workers,
            "timeout": self.timeout,
            "parameters": self.parameters,
        }


@dataclass
class Experiment:
    """An experiment definition"""
    id: str
    config: ExperimentConfig
    status: ExperimentStatus = ExperimentStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    
    # Results
    results: Dict[str, Dict[str, float]] = field(default_factory=dict)  # subject_id -> metrics
    best_subject: Optional[str] = None
    
    # Metadata
    tags: Dict[str, str] = field(default_factory=dict)
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "config": self.config.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_by": self.created_by,
            "results": self.results,
            "best_subject": self.best_subject,
            "tags": self.tags,
            "notes": self.notes,
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.started_at and self.completed_at else None
            ),
        }


@dataclass
class ExperimentResult:
    """Result of a completed experiment"""
    experiment_id: str
    best_subject: str
    best_metrics: Dict[str, float]
    all_results: Dict[str, Dict[str, float]]
    rankings: Dict[str, int]  # subject_id -> rank
    comparison_summary: Dict[str, Any]
    execution_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "best_subject": self.best_subject,
            "best_metrics": self.best_metrics,
            "all_results": self.all_results,
            "rankings": self.rankings,
            "comparison_summary": self.comparison_summary,
            "execution_time": self.execution_time,
        }


class ResearchLab:
    """
    AI Research Lab for experiments and benchmarking.
    
    Features:
    - Experiment creation and management
    - Strategy comparison
    - Model evaluation
    - Feature set analysis
    - Parameter sweeps
    - Results ranking
    - Reproducibility
    """
    
    def __init__(self, storage_path: str = "data/research"):
        self._storage_path = storage_path
        self._experiments: Dict[str, Experiment] = {}
        self._experiment_configs: Dict[str, Dict[str, Any]] = {}
        self._metrics: Dict[str, List[MetricValue]] = defaultdict(list)
        self._callbacks: Dict[str, List[Callable]] = {
            "on_experiment_start": [],
            "on_experiment_complete": [],
            "on_experiment_fail": [],
            "on_metric_update": [],
        }
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_experiments()
    
    def _load_experiments(self) -> None:
        """Load experiments from storage"""
        index_file = os.path.join(self._storage_path, "experiments.json")
        
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                
                for exp_id, exp_data in data.get("experiments", {}).items():
                    exp_data["config"] = ExperimentConfig(**exp_data["config"])
                    self._experiments[exp_id] = Experiment(**exp_data)
                
                logger.info(f"Loaded {len(self._experiments)} experiments")
            except Exception as e:
                logger.error(f"Failed to load experiments: {e}")
    
    def _save_experiments(self) -> None:
        """Save experiments to storage"""
        index_file = os.path.join(self._storage_path, "experiments.json")
        
        data = {
            "experiments": {
                exp_id: {
                    k: v for k, v in exp.to_dict().items()
                    if k != "config"
                }
                for exp_id, exp in self._experiments.items()
            }
        }
        
        try:
            with open(index_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save experiments: {e}")
    
    def create_experiment(
        self,
        config: ExperimentConfig,
        created_by: Optional[str] = None,
    ) -> Experiment:
        """
        Create a new experiment.
        
        Args:
            config: Experiment configuration
            created_by: User creating the experiment
            
        Returns:
            Created experiment
        """
        experiment = Experiment(
            id=str(uuid.uuid4()),
            config=config,
            status=ExperimentStatus.PENDING,
            created_by=created_by,
        )
        
        self._experiments[experiment.id] = experiment
        self._save_experiments()
        
        logger.info(f"Created experiment: {experiment.id}")
        return experiment
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get an experiment by ID"""
        return self._experiments.get(experiment_id)
    
    def get_all_experiments(
        self,
        status: Optional[ExperimentStatus] = None,
        experiment_type: Optional[ExperimentType] = None,
        limit: int = 100,
    ) -> List[Experiment]:
        """Get all experiments with optional filtering"""
        experiments = list(self._experiments.values())
        
        if status:
            experiments = [e for e in experiments if e.status == status]
        
        if experiment_type:
            experiments = [
                e for e in experiments
                if e.config.experiment_type == experiment_type
            ]
        
        # Sort by creation date (newest first)
        experiments.sort(key=lambda e: e.created_at, reverse=True)
        
        return experiments[:limit]
    
    def start_experiment(
        self,
        experiment_id: str,
        evaluator: Callable[[str, ExperimentConfig], Dict[str, float]],
    ) -> bool:
        """
        Start running an experiment.
        
        Args:
            experiment_id: Experiment to start
            evaluator: Function to evaluate a subject and return metrics
            
        Returns:
            True if started successfully
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return False
        
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.utcnow()
        
        self._fire_callback("on_experiment_start", experiment)
        
        try:
            # Run evaluation for each subject
            for subject_id in experiment.config.subjects:
                subject_config = experiment.config.subject_configs.get(subject_id, {})
                
                # Call evaluator
                metrics = evaluator(subject_id, experiment.config, subject_config)
                
                experiment.results[subject_id] = metrics
                
                # Track metrics
                for metric_name, metric_value in metrics.items():
                    self._metrics[metric_name].append(MetricValue(
                        name=metric_name,
                        value=metric_value,
                        tags={
                            "experiment_id": experiment_id,
                            "subject_id": subject_id,
                        },
                    ))
            
            # Determine best subject
            self._rank_results(experiment)
            
            experiment.status = ExperimentStatus.COMPLETED
            experiment.completed_at = datetime.utcnow()
            
            self._fire_callback("on_experiment_complete", experiment)
            self._save_experiments()
            
            logger.info(f"Experiment {experiment_id} completed")
            return True
            
        except Exception as e:
            logger.error(f"Experiment {experiment_id} failed: {e}")
            experiment.status = ExperimentStatus.FAILED
            experiment.completed_at = datetime.utcnow()
            self._fire_callback("on_experiment_fail", experiment, str(e))
            self._save_experiments()
            return False
    
    def _rank_results(self, experiment: Experiment) -> None:
        """Rank experiment results"""
        if not experiment.results:
            return
        
        primary_metric = experiment.config.primary_metric
        direction = experiment.config.optimization_direction
        
        # Sort subjects by primary metric
        sorted_subjects = sorted(
            experiment.results.items(),
            key=lambda x: x[1].get(primary_metric, 0),
            reverse=(direction == "maximize"),
        )
        
        # Assign ranks
        rankings = {}
        for rank, (subject_id, metrics) in enumerate(sorted_subjects, 1):
            rankings[subject_id] = rank
        
        experiment.best_subject = sorted_subjects[0][0] if sorted_subjects else None
        
        # Store rankings in results
        for subject_id, metrics in experiment.results.items():
            metrics["_rank"] = rankings.get(subject_id, 0)
    
    def cancel_experiment(self, experiment_id: str) -> bool:
        """Cancel a running experiment"""
        experiment = self._experiments.get(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return False
        
        experiment.status = ExperimentStatus.CANCELLED
        experiment.completed_at = datetime.utcnow()
        self._save_experiments()
        
        return True
    
    def delete_experiment(self, experiment_id: str) -> bool:
        """Delete an experiment"""
        if experiment_id in self._experiments:
            del self._experiments[experiment_id]
            self._save_experiments()
            return True
        return False
    
    def compare_strategies(
        self,
        strategy_ids: List[str],
        config: ExperimentConfig,
    ) -> Experiment:
        """Create and run a strategy comparison experiment"""
        config.experiment_type = ExperimentType.STRATEGY_COMPARE
        config.subjects = strategy_ids
        
        experiment = self.create_experiment(config)
        
        # Default metrics for strategy comparison
        default_metrics = [
            "win_rate",
            "expectancy",
            "sharpe_ratio",
            "sortino_ratio",
            "profit_factor",
            "max_drawdown",
            "total_trades",
            "avg_trade_duration",
        ]
        
        if not config.metrics:
            config.metrics = default_metrics
        
        return experiment
    
    def run_parameter_sweep(
        self,
        base_config: ExperimentConfig,
        parameter_name: str,
        parameter_values: List[Any],
    ) -> List[Experiment]:
        """Run a parameter sweep experiment"""
        experiments = []
        
        for value in parameter_values:
            config = ExperimentConfig(
                experiment_type=ExperimentType.PARAMETER_SWEEP,
                name=f"{base_config.name} - {parameter_name}={value}",
                description=f"Sweep of {parameter_name}",
                subjects=base_config.subjects.copy(),
                parameters={parameter_name: value},
            )
            
            experiment = self.create_experiment(config)
            experiments.append(experiment)
        
        return experiments
    
    def get_metric_history(
        self,
        metric_name: str,
        experiment_id: Optional[str] = None,
        subject_id: Optional[str] = None,
    ) -> List[MetricValue]:
        """Get historical values of a metric"""
        values = self._metrics.get(metric_name, [])
        
        if experiment_id or subject_id:
            values = [
                v for v in values
                if (not experiment_id or v.tags.get("experiment_id") == experiment_id)
                and (not subject_id or v.tags.get("subject_id") == subject_id)
            ]
        
        return values
    
    def get_leaderboard(
        self,
        metric_name: str,
        experiment_type: Optional[ExperimentType] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get leaderboard for a metric"""
        # Aggregate best results per subject
        subject_best: Dict[str, float] = {}
        
        for experiment in self._experiments.values():
            if experiment.status != ExperimentStatus.COMPLETED:
                continue
            
            if experiment_type and experiment.config.experiment_type != experiment_type:
                continue
            
            for subject_id, metrics in experiment.results.items():
                value = metrics.get(metric_name)
                if value is not None:
                    if subject_id not in subject_best or value > subject_best[subject_id]:
                        subject_best[subject_id] = value
        
        # Sort by metric value
        leaderboard = sorted(
            [
                {"subject_id": sid, "value": val}
                for sid, val in subject_best.items()
            ],
            key=lambda x: x["value"],
            reverse=True,
        )[:limit]
        
        # Add ranks
        for rank, entry in enumerate(leaderboard, 1):
            entry["rank"] = rank
        
        return leaderboard
    
    def export_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Export an experiment for sharing"""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return None
        
        return experiment.to_dict()
    
    def import_experiment(
        self,
        data: Dict[str, Any],
        new_id: Optional[str] = None,
    ) -> Optional[Experiment]:
        """Import an experiment"""
        try:
            data["id"] = new_id or str(uuid.uuid4())
            data["config"] = ExperimentConfig(**data["config"])
            experiment = Experiment(**data)
            
            self._experiments[experiment.id] = experiment
            self._save_experiments()
            
            return experiment
        except Exception as e:
            logger.error(f"Failed to import experiment: {e}")
            return None
    
    def register_callback(
        self,
        event_type: str,
        callback: Callable,
    ) -> None:
        """Register a callback"""
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
    
    def _fire_callback(self, event_type: str, *args) -> None:
        """Fire registered callbacks"""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"Callback error: {e}")
