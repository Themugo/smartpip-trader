"""
Research Laboratory Core
=======================

Main orchestrator for autonomous quant research.
"""

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np

from .hypothesis import HypothesisGenerator, Hypothesis
from .planner import ExperimentPlanner, ExperimentPlan
from .runner import ExperimentRunner, ExperimentResult
from .statistics import StatisticalEvaluator, StatisticalResult
from .benchmark import BenchmarkComparator, BenchmarkResult
from .archive import ResearchArchive
from .summarizer import ConclusionSummarizer, ResearchSummary
from .journal import ResearchJournal
from .weekly_report import WeeklyReportGenerator, WeeklyReport

logger = logging.getLogger(__name__)


class LabStatus(Enum):
    """Laboratory status"""
    IDLE = "idle"
    GENERATING_HYPOTHESES = "generating_hypotheses"
    PLANNING_EXPERIMENTS = "planning_experiments"
    RUNNING_EXPERIMENTS = "running_experiments"
    EVALUATING = "evaluating"
    ARCHIVING = "archiving"
    REPORTING = "reporting"


@dataclass
class LabConfig:
    """Laboratory configuration"""
    auto_generate_hypotheses: bool = True
    hypothesis_generation_interval_hours: int = 24
    min_statistical_power: float = 0.80
    max_experiments_per_week: int = 10
    archive_after_weeks: int = 4
    benchmark_strategy: str = "buy_and_hold"
    confidence_level: float = 0.95


@dataclass
class ResearchIdea:
    """A research idea from hypothesis"""
    id: str
    hypothesis: Hypothesis
    priority: float  # 0-1
    novelty_score: float  # 0-1
    feasibility_score: float  # 0-1
    potential_impact: float  # 0-1
    status: str  # pending, planned, running, completed, archived


class ResearchLaboratory:
    """
    Autonomous Quant Research Laboratory
    
    A self-directed research system that:
    - Generates research hypotheses
    - Creates and runs experiments
    - Evaluates statistical significance
    - Compares against benchmarks
    - Archives findings
    - Summarizes conclusions
    - Generates weekly reports
    """
    
    def __init__(
        self,
        config: Optional[LabConfig] = None,
        db_path: str = "data/research_lab.db"
    ):
        self.config = config or LabConfig()
        self.db_path = db_path
        
        # Initialize components
        self.hypothesis_generator = HypothesisGenerator()
        self.experiment_planner = ExperimentPlanner()
        self.experiment_runner = ExperimentRunner()
        self.statistical_evaluator = StatisticalEvaluator(self.config.confidence_level)
        self.benchmark_comparator = BenchmarkComparator(self.config.benchmark_strategy)
        self.archive = ResearchArchive(db_path)
        self.summarizer = ConclusionSummarizer()
        self.journal = ResearchJournal(db_path)
        self.weekly_reporter = WeeklyReportGenerator(self.journal)
        
        # State
        self.status = LabStatus.IDLE
        self.active_ideas: Dict[str, ResearchIdea] = {}
        self.ideas_history: List[ResearchIdea] = []
        
        # Ensure database
        self._ensure_database()
        
        logger.info("Research Laboratory initialized")
    
    def _ensure_database(self) -> None:
        """Initialize database tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Research ideas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_ideas (
                id TEXT PRIMARY KEY,
                hypothesis_id TEXT,
                priority REAL,
                novelty_score REAL,
                feasibility_score REAL,
                potential_impact REAL,
                status TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Experiment plans
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiment_plans (
                id TEXT PRIMARY KEY,
                idea_id TEXT,
                name TEXT,
                parameters TEXT,
                status TEXT,
                created_at TEXT
            )
        """)
        
        # Experiment results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiment_results (
                id TEXT PRIMARY KEY,
                plan_id TEXT,
                metrics TEXT,
                data TEXT,
                completed_at TEXT
            )
        """)
        
        # Statistical results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statistical_results (
                id TEXT PRIMARY KEY,
                experiment_id TEXT,
                p_value REAL,
                confidence_interval TEXT,
                effect_size REAL,
                power REAL,
                is_significant INTEGER
            )
        """)
        
        # Weekly reports
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_reports (
                id TEXT PRIMARY KEY,
                week_start TEXT,
                week_end TEXT,
                content TEXT,
                recommendations TEXT,
                generated_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def run_research_cycle(self) -> Dict[str, Any]:
        """
        Run a complete research cycle.
        
        Returns:
            Summary of what was done
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "hypotheses_generated": 0,
            "experiments_planned": 0,
            "experiments_run": 0,
            "ideas_archived": 0
        }
        
        logger.info("Starting research cycle")
        
        # Step 1: Generate hypotheses
        self.status = LabStatus.GENERATING_HYPOTHESES
        new_hypotheses = self._generate_hypotheses()
        results["hypotheses_generated"] = len(new_hypotheses)
        
        # Step 2: Create experiment plans
        self.status = LabStatus.PLANNING_EXPERIMENTS
        new_plans = self._plan_experiments()
        results["experiments_planned"] = len(new_plans)
        
        # Step 3: Run experiments
        self.status = LabStatus.RUNNING_EXPERIMENTS
        experiments_run = self._run_experiments()
        results["experiments_run"] = experiments_run
        
        # Step 4: Archive completed research
        self.status = LabStatus.ARCHIVING
        archived = self._archive_completed()
        results["ideas_archived"] = archived
        
        self.status = LabStatus.IDLE
        logger.info(f"Research cycle complete: {results}")
        
        return results
    
    def _generate_hypotheses(self) -> List[Hypothesis]:
        """Generate new research hypotheses"""
        hypotheses = self.hypothesis_generator.generate_hypotheses(
            count=5,
            existing_hypotheses=[idea.hypothesis for idea in self.active_ideas.values()]
        )
        
        for h in hypotheses:
            idea = ResearchIdea(
                id=str(uuid4()),
                hypothesis=h,
                priority=self._calculate_priority(h),
                novelty_score=self.hypothesis_generator._assess_novelty(h),
                feasibility_score=self._assess_feasibility(h),
                potential_impact=self._assess_impact(h),
                status="pending"
            )
            self.active_ideas[idea.id] = idea
            
            # Log to journal
            self.journal.log_hypothesis(h, idea.id)
        
        return hypotheses
    
    def _plan_experiments(self) -> List[ExperimentPlan]:
        """Plan experiments for pending ideas"""
        pending_ideas = [
            (id, idea) for id, idea in self.active_ideas.items()
            if idea.status == "pending"
        ][:self.config.max_experiments_per_week]
        
        plans = []
        for idea_id, idea in pending_ideas:
            plan = self.experiment_planner.create_plan(
                hypothesis=idea.hypothesis,
                idea_id=idea_id
            )
            idea.status = "planned"
            plans.append(plan)
            
            # Store in database
            self._store_plan(plan, idea_id)
        
        return plans
    
    def _run_experiments(self) -> int:
        """Run planned experiments"""
        planned_ideas = [
            (id, idea) for id, idea in self.active_ideas.items()
            if idea.status == "planned"
        ]
        
        run_count = 0
        for idea_id, idea in planned_ideas:
            # Get experiment plan
            plan = self._get_plan_for_idea(idea_id)
            if not plan:
                continue
            
            # Run experiment
            result = self.experiment_runner.run(plan)
            idea.status = "running"
            
            # Statistical evaluation
            stats = self.statistical_evaluator.evaluate(result)
            
            # Benchmark comparison
            benchmark = self.benchmark_comparator.compare(result)
            
            # Store results
            self._store_results(idea_id, plan.id, result, stats, benchmark)
            
            idea.status = "completed"
            run_count += 1
            
            # Generate summary
            summary = self.summarizer.summarize(
                hypothesis=idea.hypothesis,
                experiment_result=result,
                statistical_result=stats,
                benchmark_result=benchmark
            )
            
            # Log to journal
            self.journal.log_experiment(
                idea_id=idea_id,
                plan_id=plan.id,
                result=result,
                stats=stats,
                summary=summary
            )
        
        return run_count
    
    def _archive_completed(self) -> int:
        """Archive completed research"""
        completed_ideas = [
            (id, idea) for id, idea in self.active_ideas.items()
            if idea.status == "completed"
        ]
        
        archived_count = 0
        for idea_id, idea in completed_ideas:
            # Check if should archive
            if self._should_archive(idea):
                self.archive.archive_research(idea)
                idea.status = "archived"
                self.ideas_history.append(idea)
                del self.active_ideas[idea_id]
                archived_count += 1
        
        return archived_count
    
    def generate_weekly_report(self) -> WeeklyReport:
        """Generate weekly research report"""
        self.status = LabStatus.REPORTING
        
        report = self.weekly_reporter.generate(
            ideas=list(self.active_ideas.values()),
            archived=self.ideas_history[-10:]  # Recent archived
        )
        
        # Store report
        self._store_report(report)
        
        self.status = LabStatus.IDLE
        return report
    
    def _calculate_priority(self, hypothesis: Hypothesis) -> float:
        """Calculate priority score for hypothesis"""
        # Simplified priority calculation
        novelty = self.hypothesis_generator._assess_novelty(hypothesis)
        feasibility = self._assess_feasibility(hypothesis)
        impact = self._assess_impact(hypothesis)
        
        return (novelty * 0.3 + feasibility * 0.3 + impact * 0.4)
    
    def _assess_feasibility(self, hypothesis: Hypothesis) -> float:
        """Assess feasibility of testing hypothesis"""
        # Simplified assessment
        if "simple" in hypothesis.description.lower():
            return 0.8
        elif "complex" in hypothesis.description.lower():
            return 0.4
        return 0.6
    
    def _assess_impact(self, hypothesis: Hypothesis) -> float:
        """Assess potential impact of hypothesis"""
        # Simplified assessment
        if "improve" in hypothesis.description.lower():
            return 0.7
        elif "predict" in hypothesis.description.lower():
            return 0.8
        return 0.5
    
    def _should_archive(self, idea: ResearchIdea) -> bool:
        """Check if idea should be archived"""
        # Archive if completed and old enough, or if clearly negative
        # Simplified - archive after 4 weeks or if stats show no significance
        return True  # Simplified for now
    
    def _store_plan(self, plan: ExperimentPlan, idea_id: str) -> None:
        """Store experiment plan in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO experiment_plans (id, idea_id, name, parameters, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            plan.id,
            idea_id,
            plan.name,
            json.dumps(plan.parameters),
            "planned",
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _get_plan_for_idea(self, idea_id: str) -> Optional[ExperimentPlan]:
        """Get experiment plan for idea"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, name, parameters FROM experiment_plans WHERE idea_id = ?",
            (idea_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return ExperimentPlan(
                id=row[0],
                name=row[1],
                hypothesis=Hypothesis(id="", type="", description="", variables=[]),
                parameters=json.loads(row[2]),
                datasets=[],
                metrics=[],
                status="planned"
            )
        return None
    
    def _store_results(
        self,
        idea_id: str,
        plan_id: str,
        result: ExperimentResult,
        stats: StatisticalResult,
        benchmark: BenchmarkResult
    ) -> None:
        """Store experiment results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Store experiment result
        cursor.execute("""
            INSERT INTO experiment_results (id, plan_id, metrics, data, completed_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(uuid4()),
            plan_id,
            json.dumps(result.metrics),
            json.dumps({"returns": result.returns[:100] if len(result.returns) > 100 else result.returns}),
            datetime.now().isoformat()
        ))
        
        # Store statistical result
        cursor.execute("""
            INSERT INTO statistical_results (
                id, experiment_id, p_value, confidence_interval,
                effect_size, power, is_significant
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid4()),
            plan_id,
            stats.p_value,
            json.dumps(stats.confidence_interval),
            stats.effect_size,
            stats.power,
            1 if stats.is_significant else 0
        ))
        
        conn.commit()
        conn.close()
    
    def _store_report(self, report: WeeklyReport) -> None:
        """Store weekly report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO weekly_reports (
                id, week_start, week_end, content, recommendations, generated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            report.id,
            report.week_start.isoformat(),
            report.week_end.isoformat(),
            json.dumps(report.content),
            json.dumps(report.recommendations),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_status(self) -> Dict[str, Any]:
        """Get laboratory status"""
        return {
            "status": self.status.value,
            "active_ideas": len(self.active_ideas),
            "ideas_by_status": self._count_by_status(),
            "total_archived": len(self.ideas_history)
        }
    
    def _count_by_status(self) -> Dict[str, int]:
        """Count ideas by status"""
        counts = {}
        for idea in self.active_ideas.values():
            counts[idea.status] = counts.get(idea.status, 0) + 1
        return counts
    
    def get_research_summary(self) -> Dict[str, Any]:
        """Get summary of all research"""
        return {
            "active_count": len(self.active_ideas),
            "archived_count": len(self.ideas_history),
            "ideas": [
                {
                    "id": idea.id,
                    "hypothesis": idea.hypothesis.description[:100],
                    "status": idea.status,
                    "priority": idea.priority
                }
                for idea in list(self.active_ideas.values())[:10]
            ]
        }
    
    def reset(self) -> None:
        """Reset laboratory state"""
        self.active_ideas.clear()
        self.ideas_history.clear()
        self.status = LabStatus.IDLE
        logger.info("Research Laboratory reset")


# Import for use in this module
from .hypothesis import HypothesisGenerator
