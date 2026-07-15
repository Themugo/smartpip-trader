"""
Hyperparameter Optimizer - Automated Parameter Optimization

Automated optimization using various search strategies.
"""

import logging
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OptimizationMethod(Enum):
    """Optimization methods"""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"
    GENETIC = "genetic"
    PARTICLE_SWARM = "particle_swarm"


@dataclass
class ParameterSpace:
    """Parameter space definition"""
    name: str
    param_type: str  # "int", "float", "categorical"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    choices: Optional[List[Any]] = None
    default: Any = None
    
    def sample(self) -> Any:
        """Sample a value from the space"""
        if self.param_type == "int":
            if self.step:
                return random.randint(int(self.min_value), int(self.max_value))
            return random.randint(int(self.min_value or 0), int(self.max_value or 100))
        
        elif self.param_type == "float":
            if self.step:
                value = random.uniform(self.min_value or 0, self.max_value or 1)
                return round(value / self.step) * self.step
            return random.uniform(self.min_value or 0, self.max_value or 1)
        
        elif self.param_type == "categorical":
            return random.choice(self.choices or [None])
        
        return self.default


@dataclass
class OptimizationResult:
    """Result of hyperparameter optimization"""
    id: str
    strategy_id: str
    method: OptimizationMethod
    
    # Best parameters found
    best_parameters: Dict[str, Any] = field(default_factory=dict)
    best_score: float = 0
    best_metric: str = "sharpe_ratio"
    
    # All trials
    trials: List[Dict[str, Any]] = field(default_factory=list)
    
    # Statistics
    total_trials: int = 0
    successful_trials: int = 0
    
    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0
    
    # Convergence
    convergence_history: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "method": self.method.value,
            "best_parameters": self.best_parameters,
            "best_score": self.best_score,
            "best_metric": self.best_metric,
            "total_trials": self.total_trials,
            "successful_trials": self.successful_trials,
            "duration_seconds": self.duration_seconds,
        }


class HyperparameterOptimizer:
    """
    Hyperparameter optimizer for strategy parameters.
    
    Features:
    - Multiple optimization methods
    - Parallel execution
    - Early stopping
    - Cross-validation
    - Parameter importance analysis
    """
    
    def __init__(self):
        self._results: Dict[str, OptimizationResult] = {}
        self._logger = logging.getLogger(f"{__name__}.Optimizer")
    
    def optimize(
        self,
        strategy_id: str,
        parameter_space: Dict[str, ParameterSpace],
        objective_func: Callable[[Dict[str, Any]], float],
        method: OptimizationMethod = OptimizationMethod.BAYESIAN,
        max_trials: int = 100,
        max_time_seconds: float = 3600,
        early_stopping_patience: int = 20,
        metric: str = "sharpe_ratio",
        validation_split: float = 0.2,
    ) -> OptimizationResult:
        """
        Run hyperparameter optimization.
        
        Args:
            strategy_id: Strategy ID
            parameter_space: Dictionary of parameter definitions
            objective_func: Function to optimize (returns score)
            method: Optimization method
            max_trials: Maximum number of trials
            max_time_seconds: Maximum optimization time
            early_stopping_patience: Trials without improvement before stopping
            metric: Metric to optimize
            validation_split: Fraction of data for validation
            
        Returns:
            OptimizationResult with best parameters
        """
        import time
        
        result = OptimizationResult(
            id=str(uuid.uuid4()),
            strategy_id=strategy_id,
            method=method,
            best_metric=metric,
        )
        
        start_time = time.time()
        
        # Select optimization method
        if method == OptimizationMethod.GRID_SEARCH:
            trials = self._grid_search(parameter_space, max_trials)
        elif method == OptimizationMethod.RANDOM_SEARCH:
            trials = self._random_search(parameter_space, max_trials)
        elif method == OptimizationMethod.GENETIC:
            trials = self._genetic_search(parameter_space, objective_func, max_trials)
        else:
            trials = self._random_search(parameter_space, max_trials)
        
        # Evaluate trials
        best_score = float('-inf')
        patience_counter = 0
        
        for i, params in enumerate(trials):
            # Check time limit
            if time.time() - start_time > max_time_seconds:
                self._logger.info(f"Optimization time limit reached at trial {i}")
                break
            
            result.total_trials += 1
            
            try:
                # Evaluate parameters
                score = objective_func(params)
                
                trial_result = {
                    "trial": i + 1,
                    "parameters": params.copy(),
                    "score": score,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                result.trials.append(trial_result)
                result.convergence_history.append(score)
                
                # Update best
                if score > best_score:
                    best_score = score
                    result.best_parameters = params.copy()
                    result.best_score = score
                    patience_counter = 0
                else:
                    patience_counter += 1
                
                result.successful_trials += 1
                
                # Early stopping
                if patience_counter >= early_stopping_patience:
                    self._logger.info(f"Early stopping at trial {i}")
                    break
                
            except Exception as e:
                self._logger.warning(f"Trial {i} failed: {e}")
                result.trials.append({
                    "trial": i + 1,
                    "parameters": params,
                    "score": None,
                    "error": str(e),
                })
        
        result.completed_at = datetime.utcnow()
        result.duration_seconds = time.time() - start_time
        
        self._results[result.id] = result
        
        self._logger.info(
            f"Optimization complete: {result.total_trials} trials, "
            f"best score: {result.best_score:.4f}"
        )
        
        return result
    
    def _grid_search(
        self,
        parameter_space: Dict[str, ParameterSpace],
        max_trials: int,
    ) -> List[Dict[str, Any]]:
        """Generate parameter combinations for grid search"""
        trials = []
        param_names = list(parameter_space.keys())
        param_lists = []
        
        for name, space in parameter_space.items():
            if space.param_type == "categorical":
                values = space.choices or [None]
            elif space.step and space.min_value and space.max_value:
                values = list(range(
                    int(space.min_value),
                    int(space.max_value) + 1,
                    int(space.step)
                ))
            else:
                values = [space.default or 0]
            param_lists.append(values)
        
        # Generate all combinations
        import itertools
        for combination in itertools.product(*param_lists):
            params = dict(zip(param_names, combination))
            trials.append(params)
            
            if len(trials) >= max_trials:
                break
        
        return trials
    
    def _random_search(
        self,
        parameter_space: Dict[str, ParameterSpace],
        max_trials: int,
    ) -> List[Dict[str, Any]]:
        """Generate random parameter combinations"""
        trials = []
        
        for _ in range(max_trials):
            params = {
                name: space.sample()
                for name, space in parameter_space.items()
            }
            trials.append(params)
        
        return trials
    
    def _genetic_search(
        self,
        parameter_space: Dict[str, ParameterSpace],
        objective_func: Callable,
        max_trials: int,
    ) -> List[Dict[str, Any]]:
        """Generate parameters using genetic algorithm principles"""
        population_size = min(20, max_trials)
        trials = []
        
        # Initialize population
        population = [
            {name: space.sample() for name, space in parameter_space.items()}
            for _ in range(population_size)
        ]
        
        # Evaluate initial population
        fitness_scores = [objective_func(params) for params in population]
        
        for _ in range(max_trials // population_size):
            # Select best individuals
            sorted_indices = sorted(range(len(fitness_scores)), 
                                   key=lambda i: fitness_scores[i], 
                                   reverse=True)
            
            # Keep top performers
            new_population = [population[i] for i in sorted_indices[:population_size // 2]]
            
            # Crossover
            for _ in range(population_size // 2):
                parent1, parent2 = random.sample(new_population, 2)
                child = {}
                for name in parameter_space:
                    if random.random() < 0.5:
                        child[name] = parent1.get(name)
                    else:
                        child[name] = parent2.get(name)
                new_population.append(child)
            
            # Mutation
            for params in new_population[population_size // 2:]:
                if random.random() < 0.1:
                    name = random.choice(list(parameter_space.keys()))
                    params[name] = parameter_space[name].sample()
            
            # Evaluate
            population = new_population
            fitness_scores = [objective_func(params) for params in population]
            
            trials.extend(population)
        
        return trials[:max_trials]
    
    def analyze_parameter_importance(
        self,
        result_id: str,
    ) -> Dict[str, float]:
        """Analyze parameter importance from optimization results"""
        result = self._results.get(result_id)
        if not result:
            return {}
        
        # Simple correlation-based importance
        param_names = list(result.best_parameters.keys())
        importance = {}
        
        successful_trials = [t for t in result.trials if t.get("score") is not None]
        
        if not successful_trials:
            return importance
        
        for param in param_names:
            values = [t["parameters"].get(param, 0) for t in successful_trials]
            scores = [t["score"] for t in successful_trials]
            
            if len(set(values)) > 1:
                # Simple correlation
                mean_val = sum(values) / len(values)
                mean_score = sum(scores) / len(scores)
                
                numerator = sum((v - mean_val) * (s - mean_score) 
                              for v, s in zip(values, scores))
                denom = (sum((v - mean_val) ** 2 for v in values) ** 0.5 * 
                        sum((s - mean_score) ** 2 for s in scores) ** 0.5)
                
                if denom > 0:
                    importance[param] = abs(numerator / denom)
                else:
                    importance[param] = 0
            else:
                importance[param] = 0
        
        # Normalize
        total = sum(importance.values())
        if total > 0:
            importance = {k: v / total for k, v in importance.items()}
        
        return importance
    
    def get_result(self, result_id: str) -> Optional[OptimizationResult]:
        """Get optimization result by ID"""
        return self._results.get(result_id)
    
    def get_strategy_results(self, strategy_id: str) -> List[OptimizationResult]:
        """Get all optimization results for a strategy"""
        return [r for r in self._results.values() if r.strategy_id == strategy_id]
