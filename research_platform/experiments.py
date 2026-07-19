"""
Experiment Manager - Research Experiment Tracking

Complete experiment management with:
- Parameter tracking
- Execution history
- Metrics collection
- Comparison framework
- Reproducibility
"""

import json
import logging
import uuid
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


class ExperimentType(Enum):
    """Types of experiments"""
    BACKTEST = "backtest"
    FORWARD_TEST = "forward_test"
    WALK_FORWARD = "walk_forward"
    HYPERPARAMETER_TUNING = "hyperparameter_tuning"
    PARAMETER_SWEEP = "parameter_sweep"
    FEATURE_SELECTION = "feature_selection"
    MODEL_COMPARISON = "model_comparison"
    STRATEGY_COMPARE = "strategy_compare"
    MONTE_CARLO = "monte_carlo"
    SENSITIVITY = "sensitivity"
    CUSTOM = "custom"


class ExperimentStatus(Enum):
    """Experiment status"""
    PLANNED = "planned"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class MetricType(Enum):
    """Metric types"""
    PERFORMANCE = "performance"
    RISK = "risk"
    EFFICIENCY = "efficiency"
    STATISTICAL = "statistical"
    CUSTOM = "custom"


@dataclass
class ParameterSpec:
    """Parameter specification"""
    name: str
    type: str  # "int", "float", "str", "bool", "list"
    
    # Constraints
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    default: Any = None
    options: List[Any] = field(default_factory=list)
    
    # Description
    description: str = ""
    unit: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "default": self.default,
            "options": self.options,
            "description": self.description,
            "unit": self.unit,
        }


@dataclass
class ParameterSet:
    """A set of parameters for an experiment"""
    params: Dict[str, Any] = field(default_factory=dict)
    param_specs: Dict[str, ParameterSpec] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "params": self.params,
            "param_specs": {k: v.to_dict() for k, v in self.param_specs.items()},
        }
    
    def checksum(self) -> str:
        """Compute parameter checksum for reproducibility"""
        content = json.dumps(self.params, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate parameters against specs"""
        errors = []
        
        for name, spec in self.param_specs.items():
            value = self.params.get(name)
            
            if value is None:
                if spec.default is None:
                    errors.append(f"Missing required parameter: {name}")
                continue
            
            # Type validation
            if spec.type == "int" and not isinstance(value, int):
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    errors.append(f"{name} must be an integer")
            
            elif spec.type == "float" and not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    errors.append(f"{name} must be a number")
            
            # Range validation
            if spec.min_value is not None and value < spec.min_value:
                errors.append(f"{name} must be >= {spec.min_value}")
            if spec.max_value is not None and value > spec.max_value:
                errors.append(f"{name} must be <= {spec.max_value}")
            
            # Options validation
            if spec.options and value not in spec.options:
                errors.append(f"{name} must be one of {spec.options}")
        
        return len(errors) == 0, errors


@dataclass
class MetricValue:
    """A single metric value"""
    name: str
    value: float
    type: MetricType = MetricType.PERFORMANCE
    
    # Statistics
    std: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    
    # Context
    unit: str = ""
    higher_is_better: bool = True
    tags: Dict[str, str] = field(default_factory=dict)
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.type.value,
            "std": self.std,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "unit": self.unit,
            "higher_is_better": self.higher_is_better,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class MetricSummary:
    """Summary of metrics for an experiment"""
    metrics: Dict[str, MetricValue] = field(default_factory=dict)
    
    # Aggregated stats
    total_runs: int = 0
    successful_runs: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
        }
    
    def get_primary_metric(self, primary_metric_name: str) -> Optional[MetricValue]:
        """Get primary metric value"""
        return self.metrics.get(primary_metric_name)


@dataclass
class ExecutionRecord:
    """Record of a single experiment execution"""
    run_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    # Parameters used
    parameters: Dict[str, Any] = field(default_factory=dict)
    parameter_checksum: str = ""
    
    # Results
    metrics: Dict[str, MetricValue] = field(default_factory=dict)
    summary_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Status
    status: ExperimentStatus = ExperimentStatus.RUNNING
    error_message: str = ""
    
    # Artifacts
    artifacts: Dict[str, str] = field(default_factory=dict)  # name -> path
    
    # Data used
    dataset_id: Optional[str] = None
    feature_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "parameters": self.parameters,
            "parameter_checksum": self.parameter_checksum,
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "summary_metrics": self.summary_metrics,
            "status": self.status.value,
            "error_message": self.error_message,
            "artifacts": self.artifacts,
            "dataset_id": self.dataset_id,
            "feature_ids": self.feature_ids,
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.completed_at else None
            ),
        }
    
    def duration(self) -> Optional[float]:
        """Get execution duration in seconds"""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class Experiment:
    """A research experiment"""
    id: str
    name: str
    description: str
    experiment_type: ExperimentType
    
    # Configuration
    parameter_specs: List[ParameterSpec] = field(default_factory=list)
    base_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Metrics to track
    metric_names: List[str] = field(default_factory=list)
    primary_metric: str = ""
    
    # Data configuration
    dataset_id: Optional[str] = None
    feature_ids: List[str] = field(default_factory=list)
    
    # Execution
    runs: List[ExecutionRecord] = field(default_factory=list)
    
    # Status
    status: ExperimentStatus = ExperimentStatus.PLANNED
    
    # Metadata
    author: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Notebook linkage
    notebook_id: Optional[str] = None
    hypothesis_ids: List[str] = field(default_factory=list)
    
    # Environment
    environment: Dict[str, str] = field(default_factory=dict)  # Reproducibility
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "experiment_type": self.experiment_type.value,
            "parameter_specs": [p.to_dict() for p in self.parameter_specs],
            "base_parameters": self.base_parameters,
            "metric_names": self.metric_names,
            "primary_metric": self.primary_metric,
            "dataset_id": self.dataset_id,
            "feature_ids": self.feature_ids,
            "runs": [r.to_dict() for r in self.runs],
            "status": self.status.value,
            "author": self.author,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "notebook_id": self.notebook_id,
            "hypothesis_ids": self.hypothesis_ids,
            "environment": self.environment,
        }
    
    def get_best_run(self) -> Optional[ExecutionRecord]:
        """Get the best run by primary metric"""
        if not self.runs or not self.primary_metric:
            return None
        
        valid_runs = [r for r in self.runs if r.status == ExperimentStatus.COMPLETED]
        if not valid_runs:
            return None
        
        # Find run with best primary metric
        primary_metric = self.metric_names[0] if not self.primary_metric else self.primary_metric
        best_run = min(
            valid_runs,
            key=lambda r: r.summary_metrics.get(primary_metric, float('inf')),
        )
        return best_run
    
    def get_metric_history(self, metric_name: str) -> List[float]:
        """Get history of a metric across runs"""
        history = []
        for run in sorted(self.runs, key=lambda r: r.started_at):
            if run.status == ExperimentStatus.COMPLETED:
                value = run.summary_metrics.get(metric_name)
                if value is not None:
                    history.append(value)
        return history
    
    def compute_summary(self) -> MetricSummary:
        """Compute summary statistics across all runs"""
        summary = MetricSummary()
        summary.total_runs = len(self.runs)
        summary.successful_runs = sum(
            1 for r in self.runs if r.status == ExperimentStatus.COMPLETED
        )
        
        completed_runs = [
            r for r in self.runs if r.status == ExperimentStatus.COMPLETED
        ]
        
        for metric_name in self.metric_names:
            values = [
                r.summary_metrics.get(metric_name)
                for r in completed_runs
                if metric_name in r.summary_metrics
            ]
            
            if values:
                metric = MetricValue(
                    name=metric_name,
                    value=float(np.mean(values)),
                    std=float(np.std(values)) if len(values) > 1 else 0,
                )
                if len(values) > 1:
                    metric.ci_lower = float(np.percentile(values, 2.5))
                    metric.ci_upper = float(np.percentile(values, 97.5))
                
                summary.metrics[metric_name] = metric
        
        return summary


@dataclass
class ExperimentResult:
    """Result of an experiment comparison"""
    experiment_id: str
    experiment_name: str
    
    # Comparison results
    best_run_id: str
    best_parameters: Dict[str, Any]
    best_metrics: Dict[str, float]
    
    # All results
    all_runs: List[ExecutionRecord]
    rankings: Dict[str, int]  # run_id -> rank
    
    # Comparison with benchmarks
    benchmark_comparison: Dict[str, float] = field(default_factory=dict)
    
    # Statistical tests
    statistical_tests: Dict[str, Any] = field(default_factory=dict)
    
    # Execution info
    total_runs: int = 0
    successful_runs: int = 0
    execution_time: float = 0.0
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "experiment_name": self.experiment_name,
            "best_run_id": self.best_run_id,
            "best_parameters": self.best_parameters,
            "best_metrics": self.best_metrics,
            "all_runs": [r.to_dict() for r in self.all_runs],
            "rankings": self.rankings,
            "benchmark_comparison": self.benchmark_comparison,
            "statistical_tests": self.statistical_tests,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "execution_time": self.execution_time,
            "generated_at": self.generated_at.isoformat(),
        }


class ExperimentManager:
    """
    Experiment Manager for research experimentation.
    
    Features:
    - Experiment creation and tracking
    - Parameter management
    - Execution history
    - Metric collection
    - Comparison framework
    - Reproducibility tracking
    - Statistical analysis
    """
    
    def __init__(self, storage_path: str = "data/experiments"):
        self._storage_path = storage_path
        self._experiments: Dict[str, Experiment] = {}
        self._metric_history: Dict[str, List[MetricValue]] = defaultdict(list)
        
        import os
        os.makedirs(storage_path, exist_ok=True)
        self._load_experiments()
    
    def _load_experiments(self) -> None:
        """Load experiments from storage"""
        index_file = f"{self._storage_path}/index.json"
        
        try:
            if os.path.exists(index_file):
                with open(index_file, "r") as f:
                    data = json.load(f)
                
                for exp_data in data.get("experiments", []):
                    exp_data["created_at"] = datetime.fromisoformat(exp_data["created_at"])
                    exp_data["updated_at"] = datetime.fromisoformat(exp_data["updated_at"])
                    if exp_data.get("started_at"):
                        exp_data["started_at"] = datetime.fromisoformat(exp_data["started_at"])
                    if exp_data.get("completed_at"):
                        exp_data["completed_at"] = datetime.fromisoformat(exp_data["completed_at"])
                    
                    # Parse parameter specs
                    exp_data["parameter_specs"] = [
                        ParameterSpec(**p) for p in exp_data.get("parameter_specs", [])
                    ]
                    
                    # Parse runs
                    for run in exp_data.get("runs", []):
                        run["started_at"] = datetime.fromisoformat(run["started_at"])
                        if run.get("completed_at"):
                            run["completed_at"] = datetime.fromisoformat(run["completed_at"])
                        
                        # Parse metrics
                        for m in run.get("metrics", {}).values():
                            m["timestamp"] = datetime.fromisoformat(m["timestamp"])
                            run["metrics"][m["name"]] = MetricValue(**m)
                        run["metrics"] = {
                            k: v for k, v in run.get("metrics", {}).items()
                            if isinstance(v, MetricValue)
                        }
                    
                    exp_data["runs"] = [ExecutionRecord(**r) for r in exp_data.get("runs", [])]
                    
                    exp = Experiment(**exp_data)
                    self._experiments[exp.id] = exp
                
                logger.info(f"Loaded {len(self._experiments)} experiments")
        except Exception as e:
            logger.warning(f"Could not load experiments: {e}")
    
    def _save_experiments(self) -> None:
        """Save experiments to storage"""
        index_file = f"{self._storage_path}/index.json"
        
        data = {
            "experiments": [exp.to_dict() for exp in self._experiments.values()],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    # Experiment Management
    def create_experiment(
        self,
        name: str,
        description: str,
        experiment_type: ExperimentType,
        author: str = "",
        tags: Optional[List[str]] = None,
        parameter_specs: Optional[List[ParameterSpec]] = None,
        base_parameters: Optional[Dict[str, Any]] = None,
        metric_names: Optional[List[str]] = None,
        primary_metric: str = "",
        dataset_id: Optional[str] = None,
        feature_ids: Optional[List[str]] = None,
        notebook_id: Optional[str] = None,
        hypothesis_ids: Optional[List[str]] = None,
    ) -> Experiment:
        """Create a new experiment"""
        experiment = Experiment(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            experiment_type=experiment_type,
            author=author,
            tags=tags or [],
            parameter_specs=parameter_specs or [],
            base_parameters=base_parameters or {},
            metric_names=metric_names or [],
            primary_metric=primary_metric,
            dataset_id=dataset_id,
            feature_ids=feature_ids or [],
            notebook_id=notebook_id,
            hypothesis_ids=hypothesis_ids or [],
            environment=self._capture_environment(),
        )
        
        self._experiments[experiment.id] = experiment
        self._save_experiments()
        
        logger.info(f"Created experiment: {name}")
        return experiment
    
    def _capture_environment(self) -> Dict[str, str]:
        """Capture environment for reproducibility"""
        import platform
        import sys
        
        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get an experiment by ID"""
        return self._experiments.get(experiment_id)
    
    def update_experiment(
        self,
        experiment_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[ExperimentStatus] = None,
    ) -> bool:
        """Update an experiment"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        
        if name is not None:
            exp.name = name
        if description is not None:
            exp.description = description
        if status is not None:
            exp.status = status
            if status == ExperimentStatus.RUNNING and not exp.started_at:
                exp.started_at = datetime.now(timezone.utc)
            elif status in [ExperimentStatus.COMPLETED, ExperimentStatus.FAILED, ExperimentStatus.CANCELLED]:
                exp.completed_at = datetime.now(timezone.utc)
        
        exp.updated_at = datetime.now(timezone.utc)
        self._save_experiments()
        return True
    
    # Run Management
    def create_run(
        self,
        experiment_id: str,
        parameters: Dict[str, Any],
        dataset_id: Optional[str] = None,
        feature_ids: Optional[List[str]] = None,
    ) -> Optional[ExecutionRecord]:
        """Create a new run for an experiment"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        
        # Merge with base parameters
        full_params = {**exp.base_parameters, **parameters}
        
        # Create parameter set for validation
        param_set = ParameterSet(
            params=full_params,
            param_specs={p.name: p for p in exp.parameter_specs},
        )
        
        # Validate
        valid, errors = param_set.validate()
        if not valid:
            logger.warning(f"Parameter validation failed: {errors}")
        
        run = ExecutionRecord(
            run_id=str(uuid.uuid4()),
            parameters=full_params,
            parameter_checksum=param_set.checksum(),
            dataset_id=dataset_id or exp.dataset_id,
            feature_ids=feature_ids or exp.feature_ids,
        )
        
        exp.runs.append(run)
        exp.updated_at = datetime.now(timezone.utc)
        
        return run
    
    def update_run(
        self,
        experiment_id: str,
        run_id: str,
        status: Optional[ExperimentStatus] = None,
        metrics: Optional[Dict[str, float]] = None,
        error_message: Optional[str] = None,
        artifacts: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Update a run"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        
        for run in exp.runs:
            if run.run_id == run_id:
                if status is not None:
                    run.status = status
                    if status in [ExperimentStatus.COMPLETED, ExperimentStatus.FAILED, ExperimentStatus.CANCELLED]:
                        run.completed_at = datetime.now(timezone.utc)
                
                if metrics is not None:
                    run.summary_metrics = metrics
                    for name, value in metrics.items():
                        metric = MetricValue(name=name, value=value)
                        run.metrics[name] = metric
                        self._metric_history[name].append(metric)
                
                if error_message is not None:
                    run.error_message = error_message
                
                if artifacts is not None:
                    run.artifacts.update(artifacts)
                
                exp.updated_at = datetime.now(timezone.utc)
                self._save_experiments()
                return True
        
        return False
    
    def complete_run(
        self,
        experiment_id: str,
        run_id: str,
        metrics: Dict[str, float],
        artifacts: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Mark a run as completed"""
        return self.update_run(
            experiment_id=experiment_id,
            run_id=run_id,
            status=ExperimentStatus.COMPLETED,
            metrics=metrics,
            artifacts=artifacts,
        )
    
    def fail_run(
        self,
        experiment_id: str,
        run_id: str,
        error_message: str,
    ) -> bool:
        """Mark a run as failed"""
        return self.update_run(
            experiment_id=experiment_id,
            run_id=run_id,
            status=ExperimentStatus.FAILED,
            error_message=error_message,
        )
    
    # Parameter Sweep
    def create_parameter_sweep(
        self,
        experiment_id: str,
        parameter: str,
        values: List[Any],
        combine_with_existing: bool = True,
    ) -> List[ExecutionRecord]:
        """Create multiple runs for a parameter sweep"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return []
        
        runs = []
        
        for value in values:
            params = {parameter: value}
            if combine_with_existing:
                params = {**exp.base_parameters, **params}
            
            run = self.create_run(experiment_id, params)
            if run:
                runs.append(run)
        
        return runs
    
    def create_grid_search(
        self,
        experiment_id: str,
        param_grid: Dict[str, List[Any]],
    ) -> List[ExecutionRecord]:
        """Create runs for a grid search"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return []
        
        # Generate all combinations
        import itertools
        
        keys = list(param_grid.keys())
        combinations = list(itertools.product(*[param_grid[k] for k in keys]))
        
        runs = []
        for combo in combinations:
            params = dict(zip(keys, combo))
            params = {**exp.base_parameters, **params}
            
            run = self.create_run(experiment_id, params)
            if run:
                runs.append(run)
        
        return runs
    
    # Comparison
    def compare_runs(
        self,
        experiment_id: str,
        metric_name: Optional[str] = None,
        higher_is_better: bool = True,
    ) -> Dict[str, Any]:
        """Compare all runs of an experiment"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {}
        
        metric = metric_name or exp.primary_metric or (exp.metric_names[0] if exp.metric_names else "")
        
        completed_runs = [
            r for r in exp.runs if r.status == ExperimentStatus.COMPLETED and metric in r.summary_metrics
        ]
        
        if not completed_runs:
            return {"error": "No completed runs"}
        
        # Rank runs
        sorted_runs = sorted(
            completed_runs,
            key=lambda r: r.summary_metrics.get(metric, float('-inf')),
            reverse=higher_is_better,
        )
        
        rankings = {r.run_id: rank + 1 for rank, r in enumerate(sorted_runs)}
        
        # Statistical comparison
        values = [r.summary_metrics[metric] for r in completed_runs]
        
        return {
            "metric": metric,
            "higher_is_better": higher_is_better,
            "total_runs": len(completed_runs),
            "best_run_id": sorted_runs[0].run_id if sorted_runs else None,
            "best_value": sorted_runs[0].summary_metrics[metric] if sorted_runs else None,
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "median": float(np.median(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "rankings": rankings,
        }
    
    def compare_experiments(
        self,
        experiment_ids: List[str],
        metric_name: str,
        higher_is_better: bool = True,
    ) -> Dict[str, Any]:
        """Compare multiple experiments"""
        results = []
        
        for exp_id in experiment_ids:
            exp = self._experiments.get(exp_id)
            if not exp:
                continue
            
            comparison = self.compare_runs(exp_id, metric_name, higher_is_better)
            if "error" not in comparison:
                results.append({
                    "experiment_id": exp_id,
                    "experiment_name": exp.name,
                    **comparison,
                })
        
        # Rank experiments
        results.sort(
            key=lambda r: r.get("best_value", float('-inf')),
            reverse=higher_is_better,
        )
        
        for rank, result in enumerate(results, 1):
            result["rank"] = rank
        
        return {
            "metric": metric_name,
            "experiments": results,
        }
    
    # Reproducibility
    def replay_run(
        self,
        experiment_id: str,
        run_id: str,
        executor: Callable[[Dict[str, Any]], Dict[str, float]],
    ) -> Optional[ExecutionRecord]:
        """Replay a run with the same parameters"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        
        # Find original run
        original_run = None
        for run in exp.runs:
            if run.run_id == run_id:
                original_run = run
                break
        
        if not original_run:
            return None
        
        # Create new run with same parameters
        new_run = self.create_run(
            experiment_id,
            original_run.parameters.copy(),
            original_run.dataset_id,
            original_run.feature_ids.copy(),
        )
        
        if not new_run:
            return None
        
        # Execute
        try:
            metrics = executor(new_run.parameters)
            self.complete_run(experiment_id, new_run.run_id, metrics)
            
            # Compare with original
            comparison = {}
            for metric_name in exp.metric_names:
                original = original_run.summary_metrics.get(metric_name)
                replayed = metrics.get(metric_name)
                if original is not None and replayed is not None:
                    diff_pct = abs(replayed - original) / abs(original) * 100 if original != 0 else 0
                    comparison[metric_name] = {
                        "original": original,
                        "replayed": replayed,
                        "difference_pct": diff_pct,
                    }
            
            logger.info(f"Replay comparison: {comparison}")
            return new_run
            
        except Exception as e:
            self.fail_run(experiment_id, new_run.run_id, str(e))
            return None
    
    def verify_reproducibility(
        self,
        experiment_id: str,
        executor: Callable[[Dict[str, Any]], Dict[str, float]],
        sample_size: int = 3,
    ) -> Dict[str, Any]:
        """Verify experiment reproducibility"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {}
        
        # Get completed runs
        completed_runs = [
            r for r in exp.runs
            if r.status == ExperimentStatus.COMPLETED
        ]
        
        if not completed_runs:
            return {"error": "No completed runs to verify"}
        
        # Sample runs
        sample_runs = completed_runs[:min(sample_size, len(completed_runs))]
        
        results = []
        for run in sample_runs:
            # Replay run
            new_run = self.replay_run(exp.id, run.run_id, executor)
            
            if new_run and new_run.status == ExperimentStatus.COMPLETED:
                comparison = {}
                for metric_name in exp.metric_names:
                    original = run.summary_metrics.get(metric_name)
                    replayed = new_run.summary_metrics.get(metric_name)
                    if original is not None and replayed is not None:
                        diff_pct = abs(replayed - original) / abs(original) * 100 if original != 0 else 0
                        comparison[metric_name] = {
                            "original": original,
                            "replayed": replayed,
                            "difference_pct": diff_pct,
                            "reproducible": diff_pct < 1.0,  # Within 1%
                        }
                
                results.append({
                    "original_run_id": run.run_id,
                    "replayed_run_id": new_run.run_id,
                    "comparisons": comparison,
                    "fully_reproducible": all(
                        c.get("reproducible", False)
                        for c in comparison.values()
                    ),
                })
        
        reproducible_count = sum(1 for r in results if r["fully_reproducible"])
        
        return {
            "experiment_id": experiment_id,
            "total_verified": len(results),
            "fully_reproducible": reproducible_count,
            "reproducibility_rate": reproducible_count / len(results) if results else 0,
            "results": results,
            "environment": exp.environment,
        }
    
    # Search
    def search_experiments(
        self,
        query: Optional[str] = None,
        experiment_types: Optional[List[ExperimentType]] = None,
        status: Optional[ExperimentStatus] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        limit: int = 50,
    ) -> List[Experiment]:
        """Search experiments"""
        results = list(self._experiments.values())
        
        if query:
            query_lower = query.lower()
            results = [
                e for e in results
                if query_lower in e.name.lower()
                or query_lower in e.description.lower()
            ]
        
        if experiment_types:
            results = [e for e in results if e.experiment_type in experiment_types]
        
        if status:
            results = [e for e in results if e.status == status]
        
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        
        if author:
            results = [e for e in results if author.lower() in e.author.lower()]
        
        if date_range:
            start, end = date_range
            results = [e for e in results
                      if e.created_at >= start and e.created_at <= end]
        
        # Sort by updated time
        results.sort(key=lambda e: e.updated_at, reverse=True)
        return results[:limit]
    
    def get_metric_history(
        self,
        metric_name: str,
        experiment_id: Optional[str] = None,
    ) -> List[MetricValue]:
        """Get historical values of a metric"""
        if experiment_id:
            exp = self._experiments.get(experiment_id)
            if not exp:
                return []
            return [
                m for run in exp.runs
                for m in run.metrics.values()
                if m.name == metric_name
            ]
        
        return self._metric_history.get(metric_name, [])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get experiment statistics"""
        experiments = list(self._experiments.values())
        
        return {
            "total_experiments": len(experiments),
            "by_type": {
                etype.value: sum(1 for e in experiments if e.experiment_type == etype)
                for etype in ExperimentType
            },
            "by_status": {
                status.value: sum(1 for e in experiments if e.status == status)
                for status in ExperimentStatus
            },
            "total_runs": sum(len(e.runs) for e in experiments),
            "completed_runs": sum(
                sum(1 for r in e.runs if r.status == ExperimentStatus.COMPLETED)
                for e in experiments
            ),
        }


import os
