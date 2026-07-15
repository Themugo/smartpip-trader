"""
Backtesting Cluster - High-Performance Strategy Testing

Enterprise backtesting with parallel execution and comprehensive analysis.
"""

import asyncio
import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Backtest job status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TestType(Enum):
    """Type of backtest"""
    STANDARD = "standard"
    WALK_FORWARD = "walk_forward"
    MONTE_CARLO = "monte_carlo"
    PARAMETER_SWEEP = "parameter_sweep"
    STRESS_TEST = "stress_test"


@dataclass
class BacktestJob:
    """A backtest job"""
    id: str
    strategy_id: str
    strategy_name: str
    test_type: TestType
    
    # Data configuration
    dataset_name: str
    start_date: datetime
    end_date: datetime
    symbols: List[str]
    
    # Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    status: JobStatus = JobStatus.PENDING
    progress: float = 0  # 0-100
    
    # Results
    metrics: Dict[str, float] = field(default_factory=dict)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    
    # Execution
    worker_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_seconds: float = 0
    
    # Errors
    errors: List[str] = field(default_factory=list)
    
    # Priority
    priority: int = 0
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "test_type": self.test_type.value,
            "dataset_name": self.dataset_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "symbols": self.symbols,
            "parameters": self.parameters,
            "status": self.status.value,
            "progress": self.progress,
            "metrics": self.metrics,
            "trades_count": len(self.trades),
            "execution_time_seconds": self.execution_time_seconds,
            "errors": self.errors,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class BacktestResult:
    """Results from a backtest"""
    job_id: str
    success: bool
    
    # Performance metrics
    total_return: float = 0
    sharpe_ratio: float = 0
    sortino_ratio: float = 0
    max_drawdown: float = 0
    win_rate: float = 0
    expectancy: float = 0
    profit_factor: float = 0
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_trade_duration: float = 0
    
    # Risk metrics
    var_95: float = 0
    cvar_95: float = 0
    calmar_ratio: float = 0
    
    # Quality metrics
    calibration_score: float = 0
    overfitting_score: float = 0
    
    # Detailed data
    equity_curve: List[Dict[str, float]] = field(default_factory=list)
    drawdown_curve: List[Dict[str, float]] = field(default_factory=list)
    trade_log: List[Dict[str, Any]] = field(default_factory=list)
    
    # Analysis
    best_trade: Dict[str, Any] = field(default_factory=dict)
    worst_trade: Dict[str, Any] = field(default_factory=dict)
    largest_win: float = 0
    largest_loss: float = 0
    
    execution_time_seconds: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "success": self.success,
            "total_return": self.total_return,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "expectancy": self.expectancy,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "calibration_score": self.calibration_score,
            "overfitting_score": self.overfitting_score,
        }


class BacktestingCluster:
    """
    High-performance backtesting cluster.
    
    Features:
    - Parallel job execution
    - Multiple test types
    - Resource management
    - Job queuing and prioritization
    - Result aggregation
    """
    
    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers
        self._jobs: Dict[str, BacktestJob] = {}
        self._job_queue: deque = deque()
        self._running_jobs: Dict[str, BacktestJob] = {}
        self._completed_jobs: Dict[str, BacktestResult] = {}
        self._backtest_func: Optional[Callable] = None
        self._running = False
        
        logger.info(f"Backtesting cluster initialized with {max_workers} workers")
    
    def set_backtest_function(self, func: Callable) -> None:
        """Set the backtest execution function"""
        self._backtest_func = func
    
    def submit_job(
        self,
        strategy_id: str,
        strategy_name: str,
        test_type: TestType,
        dataset_name: str,
        start_date: datetime,
        end_date: datetime,
        symbols: List[str],
        parameters: Optional[Dict[str, Any]] = None,
        priority: int = 0,
    ) -> BacktestJob:
        """Submit a backtest job"""
        job = BacktestJob(
            id=str(uuid.uuid4()),
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            test_type=test_type,
            dataset_name=dataset_name,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
            parameters=parameters or {},
            priority=priority,
        )
        
        self._jobs[job.id] = job
        self._job_queue.append(job)
        
        # Sort by priority
        self._job_queue = deque(sorted(self._job_queue, key=lambda j: j.priority, reverse=True))
        
        logger.info(f"Submitted backtest job: {job.id}")
        
        # Start processing if not running
        if not self._running:
            asyncio.create_task(self._process_jobs())
        
        return job
    
    def submit_parameter_sweep(
        self,
        strategy_id: str,
        strategy_name: str,
        dataset_name: str,
        start_date: datetime,
        end_date: datetime,
        symbols: List[str],
        parameter_ranges: Dict[str, List[Any]],
        priority: int = 0,
    ) -> List[BacktestJob]:
        """Submit a parameter sweep (multiple jobs)"""
        import itertools
        
        jobs = []
        param_combinations = list(itertools.product(*parameter_ranges.values()))
        param_names = list(parameter_ranges.keys())
        
        for combination in param_combinations:
            params = dict(zip(param_names, combination))
            
            job = self.submit_job(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                test_type=TestType.PARAMETER_SWEEP,
                dataset_name=dataset_name,
                start_date=start_date,
                end_date=end_date,
                symbols=symbols,
                parameters=params,
                priority=priority,
            )
            jobs.append(job)
        
        logger.info(f"Submitted parameter sweep with {len(jobs)} combinations")
        return jobs
    
    async def _process_jobs(self) -> None:
        """Process jobs in the queue"""
        self._running = True
        
        while self._job_queue and len(self._running_jobs) < self._max_workers:
            job = self._job_queue.popleft()
            
            # Check if job was cancelled
            if job.status == JobStatus.CANCELLED:
                continue
            
            self._running_jobs[job.id] = job
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            
            # Start job execution
            asyncio.create_task(self._execute_job(job))
        
        self._running = False
    
    async def _execute_job(self, job: BacktestJob) -> None:
        """Execute a single backtest job"""
        import time
        start_time = time.time()
        
        try:
            if self._backtest_func:
                result = await asyncio.to_thread(
                    self._backtest_func,
                    job.strategy_id,
                    job.parameters,
                    job.start_date,
                    job.end_date,
                    job.symbols,
                )
                
                # Update job with results
                job.metrics = result.get("metrics", {})
                job.trades = result.get("trades", [])
                job.status = JobStatus.COMPLETED
                
            else:
                # Simulate backtest
                await asyncio.sleep(1)  # Simulate work
                job.status = JobStatus.COMPLETED
                job.progress = 100
            
            job.completed_at = datetime.utcnow()
            job.execution_time_seconds = time.time() - start_time
            
            # Store result
            self._completed_jobs[job.id] = self._create_result(job)
            
            logger.info(f"Completed backtest job: {job.id} ({job.execution_time_seconds:.2f}s)")
            
        except Exception as e:
            logger.error(f"Backtest job failed: {job.id} - {e}")
            job.status = JobStatus.FAILED
            job.errors.append(str(e))
            job.completed_at = datetime.utcnow()
            job.execution_time_seconds = time.time() - start_time
        
        finally:
            # Remove from running jobs
            if job.id in self._running_jobs:
                del self._running_jobs[job.id]
            
            # Continue processing
            if self._job_queue:
                asyncio.create_task(self._process_jobs())
    
    def _create_result(self, job: BacktestJob) -> BacktestResult:
        """Create a BacktestResult from a job"""
        metrics = job.metrics
        
        return BacktestResult(
            job_id=job.id,
            success=job.status == JobStatus.COMPLETED,
            total_return=metrics.get("total_return", 0),
            sharpe_ratio=metrics.get("sharpe_ratio", 0),
            sortino_ratio=metrics.get("sortino_ratio", 0),
            max_drawdown=metrics.get("max_drawdown", 0),
            win_rate=metrics.get("win_rate", 0),
            expectancy=metrics.get("expectancy", 0),
            profit_factor=metrics.get("profit_factor", 0),
            total_trades=metrics.get("total_trades", 0),
            execution_time_seconds=job.execution_time_seconds,
        )
    
    def get_job(self, job_id: str) -> Optional[BacktestJob]:
        """Get a job by ID"""
        return self._jobs.get(job_id)
    
    def get_jobs(
        self,
        status: Optional[JobStatus] = None,
        strategy_id: Optional[str] = None,
    ) -> List[BacktestJob]:
        """Get jobs with optional filtering"""
        jobs = list(self._jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        if strategy_id:
            jobs = [j for j in jobs if j.strategy_id == strategy_id]
        
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)
    
    def get_result(self, job_id: str) -> Optional[BacktestResult]:
        """Get the result of a completed job"""
        return self._completed_jobs.get(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job"""
        job = self._jobs.get(job_id)
        if not job:
            return False
        
        if job.status in (JobStatus.RUNNING, JobStatus.COMPLETED):
            return False
        
        job.status = JobStatus.CANCELLED
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cluster statistics"""
        jobs = list(self._jobs.values())
        
        return {
            "total_jobs": len(jobs),
            "pending": sum(1 for j in jobs if j.status == JobStatus.PENDING),
            "running": len(self._running_jobs),
            "completed": sum(1 for j in jobs if j.status == JobStatus.COMPLETED),
            "failed": sum(1 for j in jobs if j.status == JobStatus.FAILED),
            "max_workers": self._max_workers,
        }
    
    def aggregate_results(
        self,
        job_ids: List[str],
    ) -> Dict[str, Any]:
        """Aggregate results from multiple jobs"""
        results = []
        
        for job_id in job_ids:
            result = self._completed_jobs.get(job_id)
            if result:
                results.append(result)
        
        if not results:
            return {}
        
        return {
            "count": len(results),
            "avg_return": sum(r.total_return for r in results) / len(results),
            "avg_sharpe": sum(r.sharpe_ratio for r in results) / len(results),
            "avg_drawdown": sum(r.max_drawdown for r in results) / len(results),
            "best_sharpe": max(r.sharpe_ratio for r in results),
            "worst_sharpe": min(r.sharpe_ratio for r in results),
        }
