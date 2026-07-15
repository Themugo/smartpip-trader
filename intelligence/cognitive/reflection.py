"""
Layer 7 — Reflection
=====================

After every completed trade: compares expected vs realized outcome, identifies
reasoning errors, updates confidence calibration, and generates lessons learned.
"""

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .decision import DecisionResult, DecisionStatus, Objective
from .critic import CriticResult
from .situation import SituationResult, MarketRegime

logger = logging.getLogger(__name__)


class OutcomeType(Enum):
    """Trade outcome types"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    NO_TRADE = "no_trade"


class ReasoningError(Enum):
    """Types of reasoning errors"""
    NONE = "none"
    MISJUDGED_REGIME = "misjudged_regime"
    MISJUDGED_TREND = "misjudged_trend"
    MISJUDGED_CONFIDENCE = "misjudged_confidence"
    IGNORED_RISK_SIGNALS = "ignored_risk_signals"
    OVERCONFIDENT = "overconfident"
    UNDERCONFIDENT = "underconfident"
    POOR_DATA_QUALITY = "poor_data_quality"
    REGIME_CHANGE = "regime_change"
    EXTERNAL_FACTOR = "external_factor"


@dataclass
class LessonLearned:
    """A lesson learned from trade reflection"""
    id: str
    category: str
    description: str
    confidence_impact: float  # How much this should affect future confidence
    applicable_regimes: List[str]
    applicable_conditions: List[str]
    occurrence_count: int = 1
    success_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "confidence_impact": self.confidence_impact,
            "applicable_regimes": self.applicable_regimes,
            "applicable_conditions": self.applicable_conditions,
            "occurrence_count": self.occurrence_count,
            "success_count": self.success_count,
            "success_rate": self.success_count / self.occurrence_count if self.occurrence_count > 0 else 0,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ReflectionResult:
    """Result from reflection layer"""
    session_id: str
    timestamp: datetime
    trade_id: Optional[str]
    outcome: OutcomeType
    expected_outcome: Optional[float]
    realized_outcome: Optional[float]
    outcome_vs_expected: Optional[float]  # realized - expected
    reasoning_errors: List[ReasoningError]
    error_analysis: str
    lessons_learned: List[LessonLearned]
    confidence_calibration_delta: float  # How much to adjust calibration
    situation_correctness: float  # How correct was the situation assessment
    prediction_accuracy: float  # How accurate was the prediction
    calibration_updated: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "trade_id": self.trade_id,
            "outcome": self.outcome.value,
            "expected_outcome": self.expected_outcome,
            "realized_outcome": self.realized_outcome,
            "outcome_vs_expected": self.outcome_vs_expected,
            "reasoning_errors": [e.value for e in self.reasoning_errors],
            "error_analysis": self.error_analysis,
            "lessons_count": len(self.lessons_learned),
            "confidence_calibration_delta": self.confidence_calibration_delta,
            "situation_correctness": self.situation_correctness,
            "prediction_accuracy": self.prediction_accuracy,
            "calibration_updated": self.calibration_updated
        }


class ReflectionLayer:
    """
    Layer 7: Reflection
    
    Responsible for:
    - Comparing expected vs realized outcomes
    - Identifying reasoning errors
    - Updating confidence calibration
    - Generating lessons learned
    """
    
    def __init__(
        self,
        db_path: str = "data/cognitive_reflection.db",
        calibration_window: int = 50
    ):
        self.db_path = db_path
        self.calibration_window = calibration_window
        
        # Calibration state
        self._prediction_history: List[Tuple[float, float]] = []  # (predicted_prob, actual_outcome)
        self._confidence_history: List[Tuple[float, float]] = []  # (stated_confidence, accuracy)
        
        # Lessons learned
        self._lessons: Dict[str, LessonLearned] = {}
        
        # Error patterns
        self._error_patterns: Dict[ReasoningError, int] = {e: 0 for e in ReasoningError}
        
        self._ensure_database()
        
    def _ensure_database(self) -> None:
        """Ensure database exists and is initialized"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trade outcomes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_outcomes (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                trade_id TEXT,
                timestamp TEXT NOT NULL,
                outcome TEXT NOT NULL,
                expected_outcome REAL,
                realized_outcome REAL,
                expected_probability REAL,
                decision_confidence REAL,
                regime TEXT,
                trend TEXT,
                reasoning_errors TEXT,
                error_analysis TEXT,
                situation_correctness REAL,
                prediction_accuracy REAL,
                metadata TEXT
            )
        """)
        
        # Lessons table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                confidence_impact REAL,
                applicable_regimes TEXT,
                applicable_conditions TEXT,
                occurrence_count INTEGER,
                success_count INTEGER,
                created_at TEXT
            )
        """)
        
        # Calibration history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calibration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                predicted_probability REAL,
                actual_outcome REAL,
                stated_confidence REAL,
                accuracy REAL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def process(
        self,
        decision_result: DecisionResult,
        critic_result: CriticResult,
        situation_result: SituationResult,
        realized_pnl: float,
        trade_id: Optional[str] = None
    ) -> ReflectionResult:
        """
        Reflect on completed trade and extract learnings.
        
        Args:
            decision_result: Result from decision layer
            critic_result: Result from critic layer
            situation_result: Result from situation assessment
            realized_pnl: Actual profit/loss from the trade
            trade_id: Optional trade identifier
            
        Returns:
            ReflectionResult with analysis and lessons
        """
        # Determine outcome
        outcome = self._determine_outcome(realized_pnl, decision_result)
        
        # Get expected outcome
        expected = decision_result.selected_action.expected_value if decision_result.selected_action else 0
        
        # Calculate outcome vs expected
        outcome_vs_expected = realized_pnl - expected if expected is not None else None
        
        # Identify reasoning errors
        errors = self._identify_reasoning_errors(
            decision_result, critic_result, situation_result, outcome, realized_pnl
        )
        
        # Generate error analysis
        error_analysis = self._generate_error_analysis(errors, outcome, situation_result)
        
        # Identify lessons learned
        lessons = self._extract_lessons(
            decision_result, situation_result, outcome, errors
        )
        
        # Calculate calibration delta
        calibration_delta = self._calculate_calibration_delta(
            decision_result, outcome, realized_pnl
        )
        
        # Calculate correctness metrics
        situation_correctness = self._assess_situation_correctness(
            situation_result, outcome
        )
        prediction_accuracy = self._assess_prediction_accuracy(
            decision_result, realized_pnl
        )
        
        # Store results
        self._store_outcome(
            session_id=decision_result.session_id,
            trade_id=trade_id,
            outcome=outcome,
            expected_outcome=expected,
            realized_outcome=realized_pnl,
            decision_confidence=decision_result.confidence,
            situation_result=situation_result,
            errors=errors,
            error_analysis=error_analysis,
            situation_correctness=situation_correctness,
            prediction_accuracy=prediction_accuracy
        )
        
        # Update calibration
        self._update_calibration(decision_result, outcome, realized_pnl)
        
        # Store lessons
        for lesson in lessons:
            self._store_lesson(lesson)
        
        # Update error patterns
        for error in errors:
            self._error_patterns[error] = self._error_patterns.get(error, 0) + 1
        
        result = ReflectionResult(
            session_id=decision_result.session_id,
            timestamp=datetime.now(),
            trade_id=trade_id,
            outcome=outcome,
            expected_outcome=expected,
            realized_outcome=realized_pnl,
            outcome_vs_expected=outcome_vs_expected,
            reasoning_errors=errors,
            error_analysis=error_analysis,
            lessons_learned=lessons,
            confidence_calibration_delta=calibration_delta,
            situation_correctness=situation_correctness,
            prediction_accuracy=prediction_accuracy,
            calibration_updated=True,
            metadata={
                "regime": situation_result.regime.value,
                "trend": situation_result.trend.value,
                "decision_objective": decision_result.objective.value
            }
        )
        
        logger.info(f"Reflection: outcome={outcome.value}, errors={[e.value for e in errors]}, "
                   f"calibration_delta={calibration_delta:.3f}")
        return result
    
    def process_no_trade(
        self,
        decision_result: DecisionResult,
        reason: str
    ) -> ReflectionResult:
        """Process when no trade was executed"""
        return ReflectionResult(
            session_id=decision_result.session_id,
            timestamp=datetime.now(),
            trade_id=None,
            outcome=OutcomeType.NO_TRADE,
            expected_outcome=None,
            realized_outcome=0.0,
            outcome_vs_expected=None,
            reasoning_errors=[],
            error_analysis=f"No trade taken: {reason}",
            lessons_learned=[],
            confidence_calibration_delta=0.0,
            situation_correctness=0.0,
            prediction_accuracy=0.0,
            calibration_updated=False,
            metadata={"reason": reason, "no_trade": True}
        )
    
    def _determine_outcome(
        self,
        realized_pnl: float,
        decision_result: DecisionResult
    ) -> OutcomeType:
        """Determine outcome type from PnL"""
        if realized_pnl > 0.5:  # Significant profit
            return OutcomeType.SUCCESS
        elif realized_pnl > -0.2:  # Small profit or small loss
            return OutcomeType.PARTIAL
        else:  # Significant loss
            return OutcomeType.FAILURE
    
    def _identify_reasoning_errors(
        self,
        decision_result: DecisionResult,
        critic_result: CriticResult,
        situation_result: SituationResult,
        outcome: OutcomeType,
        realized_pnl: float
    ) -> List[ReasoningError]:
        """Identify reasoning errors in the decision"""
        errors = []
        
        # No action = no errors to identify
        if not decision_result.selected_action:
            return errors
        
        action = decision_result.selected_action
        
        # Check for overconfidence
        if outcome == OutcomeType.FAILURE and action.confidence > 0.8:
            errors.append(ReasoningError.OVERCONFIDENT)
        
        # Check for underconfidence
        if outcome == OutcomeType.SUCCESS and action.confidence < 0.4:
            errors.append(ReasoningError.UNDERCONFIDENT)
        
        # Check if regime was misjudged
        if outcome == OutcomeType.FAILURE:
            if situation_result.regime_transition_detected and not situation_result.is_tradeable:
                errors.append(ReasoningError.IGNORED_RISK_SIGNALS)
            
            # High uncertainty with action
            if situation_result.uncertainty > 0.6 and action.confidence > 0.6:
                errors.append(ReasoningError.MISJUDGED_CONFIDENCE)
        
        # Check for regime change during trade
        # This would need historical context - simplified here
        if outcome == OutcomeType.FAILURE and situation_result.regime != MarketRegime.UNKNOWN:
            # If regime transition was detected but we traded anyway
            if situation_result.regime_transition_detected:
                errors.append(ReasoningError.REGIME_CHANGE)
        
        # Check if critique warnings were ignored
        severe_critiques = [c for c in critic_result.critiques 
                           if c.severity.value in ['severe', 'block']]
        if severe_critiques and outcome == OutcomeType.FAILURE:
            errors.append(ReasoningError.IGNORED_RISK_SIGNALS)
        
        # Check expected vs realized mismatch
        expected = action.expected_value
        if expected > 0 and realized_pnl < -0.3:
            # Expected profit but large loss
            if situation_result.uncertainty < 0.4:
                errors.append(ReasoningError.MISJUDGED_CONFIDENCE)
        
        return errors
    
    def _generate_error_analysis(
        self,
        errors: List[ReasoningError],
        outcome: OutcomeType,
        situation_result: SituationResult
    ) -> str:
        """Generate natural language error analysis"""
        if not errors:
            return "No reasoning errors identified. Trade was executed according to analysis."
        
        analysis_parts = []
        
        error_descriptions = {
            ReasoningError.MISJUDGED_REGIME: "The market regime was incorrectly assessed.",
            ReasoningError.MISJUDGED_TREND: "The trend direction was misjudged.",
            ReasoningError.MISJUDGED_CONFIDENCE: "Confidence levels did not match actual uncertainty.",
            ReasoningError.IGNORED_RISK_SIGNALS: "Risk warning signals were present but not heeded.",
            ReasoningError.OVERCONFIDENT: "The system was overconfident in its prediction.",
            ReasoningError.UNDERCONFIDENT: "The system was underconfident despite good signals.",
            ReasoningError.POOR_DATA_QUALITY: "Input data quality was insufficient.",
            ReasoningError.REGIME_CHANGE: "Market regime changed during the trade.",
            ReasoningError.EXTERNAL_FACTOR: "External factors affected the outcome."
        }
        
        for error in errors:
            desc = error_descriptions.get(error, str(error.value))
            analysis_parts.append(desc)
        
        # Add outcome context
        if outcome == OutcomeType.SUCCESS:
            analysis_parts.append("Despite these issues, the trade was profitable.")
        elif outcome == OutcomeType.PARTIAL:
            analysis_parts.append("The trade result was mixed given the circumstances.")
        else:
            analysis_parts.append("These errors contributed to the unfavorable outcome.")
        
        return " ".join(analysis_parts)
    
    def _extract_lessons(
        self,
        decision_result: DecisionResult,
        situation_result: SituationResult,
        outcome: OutcomeType,
        errors: List[ReasoningError]
    ) -> List[LessonLearned]:
        """Extract lessons learned from the trade"""
        lessons = []
        
        if not decision_result.selected_action:
            return lessons
        
        action = decision_result.selected_action
        
        # Lesson 1: Confidence calibration
        if errors:
            for error in errors:
                if error == ReasoningError.OVERCONFIDENT:
                    lessons.append(LessonLearned(
                        id=str(uuid4()),
                        category="confidence",
                        description="Reduce confidence when multiple risk factors are present",
                        confidence_impact=-0.1,
                        applicable_regimes=[situation_result.regime.value],
                        applicable_conditions=["high_risk", "uncertain_market"]
                    ))
                elif error == ReasoningError.MISJUDGED_CONFIDENCE:
                    lessons.append(LessonLearned(
                        id=str(uuid4()),
                        category="calibration",
                        description="Reassess confidence calculation under uncertainty",
                        confidence_impact=-0.05,
                        applicable_regimes=[situation_result.regime.value],
                        applicable_conditions=["uncertain"]
                    ))
        
        # Lesson 2: Regime awareness
        if situation_result.regime_transition_detected and outcome != OutcomeType.SUCCESS:
            lessons.append(LessonLearned(
                id=str(uuid4()),
                category="regime",
                description="Avoid trading during detected regime transitions",
                confidence_impact=-0.15,
                applicable_regimes=[situation_result.regime.value],
                applicable_conditions=["transition", "volatile"]
            ))
        
        # Lesson 3: Data quality
        # This would need to be passed from earlier layers
        
        # Lesson 4: Success case
        if outcome == OutcomeType.SUCCESS:
            lessons.append(LessonLearned(
                id=str(uuid4()),
                category="success_pattern",
                description=f"Successful trade in {situation_result.regime.value} regime",
                confidence_impact=0.05,
                applicable_regimes=[situation_result.regime.value],
                applicable_conditions=["favorable"]
            ))
        
        return lessons
    
    def _calculate_calibration_delta(
        self,
        decision_result: DecisionResult,
        outcome: OutcomeType,
        realized_pnl: float
    ) -> float:
        """Calculate how much to adjust confidence calibration"""
        if not decision_result.selected_action:
            return 0.0
        
        action = decision_result.selected_action
        
        # Expected win probability
        expected_prob = action.win_probability
        
        # Actual outcome (1 for win, 0 for loss)
        actual_outcome = 1.0 if realized_pnl > 0 else 0.0
        
        # Calibration error
        calibration_error = expected_prob - actual_outcome
        
        # Adjust based on outcome
        delta = -calibration_error * 0.1  # Small adjustment
        
        # Additional adjustment for extreme confidence
        if action.confidence > 0.9 and outcome == OutcomeType.FAILURE:
            delta -= 0.1  # Further reduce for overconfidence
        elif action.confidence < 0.4 and outcome == OutcomeType.SUCCESS:
            delta += 0.05  # Increase for underconfidence
        
        return max(-0.2, min(0.2, delta))
    
    def _assess_situation_correctness(
        self,
        situation_result: SituationResult,
        outcome: OutcomeType
    ) -> float:
        """Assess how correct the situation assessment was"""
        base_correctness = situation_result.confidence
        
        # Reduce if regime transition was detected but ignored
        if situation_result.regime_transition_detected and not situation_result.is_tradeable:
            if outcome != OutcomeType.SUCCESS:
                base_correctness *= 0.7
        
        # Reduce if uncertainty was high but confidence was also high
        if situation_result.uncertainty > 0.5 and situation_result.confidence > 0.7:
            base_correctness *= 0.8
        
        return max(0, min(1, base_correctness))
    
    def _assess_prediction_accuracy(
        self,
        decision_result: DecisionResult,
        realized_pnl: float
    ) -> float:
        """Assess how accurate the prediction was"""
        if not decision_result.selected_action:
            return 0.0
        
        action = decision_result.selected_action
        
        # Base accuracy from expected value match
        expected = action.expected_value
        
        # Map PnL to [0, 1] scale
        if expected > 0:
            # Positive expected value
            if realized_pnl > 0:
                accuracy = 1.0 - min(1, abs(realized_pnl - expected) / max(abs(expected), 0.1))
            else:
                accuracy = max(0, 0.5 - abs(realized_pnl - expected))
        else:
            # Negative expected value
            if realized_pnl < 0:
                accuracy = 1.0
            else:
                accuracy = max(0, realized_pnl)
        
        return max(0, min(1, accuracy))
    
    def _store_outcome(
        self,
        session_id: str,
        trade_id: Optional[str],
        outcome: OutcomeType,
        expected_outcome: Optional[float],
        realized_outcome: float,
        decision_confidence: float,
        situation_result: SituationResult,
        errors: List[ReasoningError],
        error_analysis: str,
        situation_correctness: float,
        prediction_accuracy: float
    ) -> None:
        """Store trade outcome in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO trade_outcomes (
                id, session_id, trade_id, timestamp, outcome, expected_outcome,
                realized_outcome, expected_probability, decision_confidence,
                regime, trend, reasoning_errors, error_analysis,
                situation_correctness, prediction_accuracy, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid4()),
            session_id,
            trade_id,
            datetime.now().isoformat(),
            outcome.value,
            expected_outcome,
            realized_outcome,
            None,  # expected_probability
            decision_confidence,
            situation_result.regime.value,
            situation_result.trend.value,
            json.dumps([e.value for e in errors]),
            error_analysis,
            situation_correctness,
            prediction_accuracy,
            json.dumps({})
        ))
        
        conn.commit()
        conn.close()
    
    def _update_calibration(
        self,
        decision_result: DecisionResult,
        outcome: OutcomeType,
        realized_pnl: float
    ) -> None:
        """Update calibration history"""
        if not decision_result.selected_action:
            return
        
        action = decision_result.selected_action
        
        actual_outcome = 1.0 if realized_pnl > 0 else 0.0
        
        self._prediction_history.append((action.win_probability, actual_outcome))
        self._confidence_history.append((action.confidence, 1.0 if outcome == OutcomeType.SUCCESS else 0.0))
        
        # Keep window size
        if len(self._prediction_history) > self.calibration_window:
            self._prediction_history = self._prediction_history[-self.calibration_window:]
        if len(self._confidence_history) > self.calibration_window:
            self._confidence_history = self._confidence_history[-self.calibration_window:]
    
    def _store_lesson(self, lesson: LessonLearned) -> None:
        """Store or update a lesson in the database"""
        # Check if similar lesson exists
        existing = None
        for lid, l in self._lessons.items():
            if l.description == lesson.description:
                existing = lid
                break
        
        if existing:
            # Update existing lesson
            l = self._lessons[existing]
            l.occurrence_count += 1
            if lesson.confidence_impact > 0:
                l.success_count += 1
            lesson = l
        else:
            self._lessons[lesson.id] = lesson
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO lessons (
                id, category, description, confidence_impact,
                applicable_regimes, applicable_conditions,
                occurrence_count, success_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lesson.id,
            lesson.category,
            lesson.description,
            lesson.confidence_impact,
            json.dumps(lesson.applicable_regimes),
            json.dumps(lesson.applicable_conditions),
            lesson.occurrence_count,
            lesson.success_count,
            lesson.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_calibration_error(self) -> float:
        """Get current calibration error"""
        if len(self._prediction_history) < 10:
            return 0.0
        
        recent = self._prediction_history[-20:]
        predicted = np.mean([p for p, _ in recent])
        actual = np.mean([a for _, a in recent])
        
        return predicted - actual
    
    def get_lessons(self, category: Optional[str] = None) -> List[LessonLearned]:
        """Get lessons, optionally filtered by category"""
        lessons = list(self._lessons.values())
        
        if category:
            lessons = [l for l in lessons if l.category == category]
        
        # Sort by occurrence count (most common first)
        lessons.sort(key=lambda l: l.occurrence_count, reverse=True)
        
        return lessons
    
    def get_error_patterns(self) -> Dict[str, int]:
        """Get error patterns"""
        return {e.value: count for e, count in self._error_patterns.items() if count > 0}
    
    def reset(self) -> None:
        """Reset reflection layer state"""
        self._prediction_history.clear()
        self._confidence_history.clear()
        self._lessons.clear()
        self._error_patterns = {e: 0 for e in ReasoningError}
        logger.info("Reflection layer reset")


