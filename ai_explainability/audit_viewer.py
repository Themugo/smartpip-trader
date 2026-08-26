"""
AI Audit Viewer - Reconstruct Historical Decisions

Provides capabilities to:
- Replay explanations during historical sessions
- Reconstruct decisions from stored evidence
- Verify decision integrity
- Generate audit reports
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Iterator

logger = logging.getLogger(__name__)


@dataclass
class DecisionReconstruction:
    """Complete reconstruction of a historical decision"""
    explanation_id: str
    decision_id: str
    timestamp: datetime
    
    # Original decision data
    original_action: str
    original_confidence: float
    original_expected_value: float
    
    # Evidence chain (as stored)
    evidence_chain: List[Dict[str, Any]]
    
    # Analyzer signals at decision time
    analyzer_signals: Dict[str, Dict]
    
    # Decision tree
    decision_tree: List[Dict]
    
    # Alternatives considered
    alternatives: List[Dict]
    
    # Rejection reasons (if no trade)
    rejection_reasons: List[str]
    
    # Feature importance
    feature_importance: Dict[str, float]
    
    # Historical analogues
    historical_analogues: List[Dict]
    
    # Market conditions at decision time
    market_conditions: Dict[str, Any]
    
    # Post-decision data (outcome if available)
    actual_outcome: Optional[float] = None
    actual_vs_expected: Optional[float] = None
    
    # Verification
    integrity_verified: bool = False
    reconstruction_notes: List[str] = field(default_factory=list)


@dataclass  
class AuditReport:
    """Complete audit report for a decision"""
    report_id: str
    generated_at: datetime
    explanation_id: str
    decision_id: str
    
    # Reconstruction
    reconstruction: DecisionReconstruction
    
    # Verification results
    integrity_check: Dict[str, bool]
    completeness_score: float
    
    # Analysis
    decision_validity: str  # VALID, INVALID, UNCERTAIN
    confidence_validity: str
    risk_assessment_validity: str
    
    # Recommendations
    findings: List[str]
    recommendations: List[str]
    
    # Full explanation at each level
    beginner_explanation: Dict
    advanced_explanation: Dict
    developer_explanation: Dict
    researcher_explanation: Dict


class AuditViewer:
    """
    AI Audit Viewer - Reconstruct and analyze historical AI decisions.
    
    Capabilities:
    - Reconstruct any historical decision from stored evidence
    - Verify decision integrity
    - Replay explanations at any time
    - Generate compliance reports
    """
    
    def __init__(self, storage):
        """
        Initialize audit viewer.
        
        Args:
            storage: ExplanationStorage instance
        """
        self.storage = storage
        self.logger = logging.getLogger(f"{__name__}.AuditViewer")
    
    def reconstruct_decision(
        self, 
        explanation_id: str,
        include_outcome: bool = False
    ) -> Optional[DecisionReconstruction]:
        """
        Reconstruct a historical decision from stored evidence.
        
        Args:
            explanation_id: ID of the explanation to reconstruct
            include_outcome: Whether to include outcome data
            
        Returns:
            DecisionReconstruction or None if not found
        """
        # Get full explanation with all evidence
        explanation = self.storage.get_explanation_with_evidence(explanation_id)
        
        if not explanation:
            self.logger.warning(f"Explanation {explanation_id} not found")
            return None
        
        # Parse timestamp
        timestamp = explanation.get("timestamp", "")
        try:
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            timestamp = datetime.utcnow()
        
        # Get evidence chain
        evidence_chain = []
        for item in explanation.get("evidence_items", []):
            evidence_chain.append({
                "type": item.get("evidence_type", ""),
                "timestamp": item.get("timestamp", ""),
                "weight": item.get("weight", 0),
                "data": item.get("data", {}),
            })
        
        # Reconstruct analyzer signals
        analyzer_signals = {}
        for signal in explanation.get("analyzer_signals", []):
            name = signal.get("analyzer_name", "")
            analyzer_signals[name] = {
                "prediction": signal.get("prediction"),
                "confidence": signal.get("confidence", 0),
                "weight": signal.get("weight", 0),
                "reason": signal.get("reason"),
                "data": signal.get("data", {}),
            }
        
        # Reconstruct decision tree
        decision_tree = [
            {
                "step": item.get("step_index", i),
                "description": item.get("step_description", ""),
                "type": item.get("step_type", ""),
            }
            for i, item in enumerate(explanation.get("decision_tree", []))
        ]
        
        # Get alternatives
        alternatives = []
        for alt in explanation.get("alternatives", []):
            alternatives.append({
                "action": alt.get("action"),
                "expected_value": alt.get("expected_value", 0),
                "risk_score": alt.get("risk_score", 0),
                "rejection_reason": alt.get("rejection_reason"),
                "similarity_to_chosen": alt.get("similarity_to_chosen", 0),
            })
        
        # Get rejection reasons
        rejection_reasons = []
        for alt in alternatives:
            if alt.get("rejection_reason"):
                rejection_reasons.append(alt["rejection_reason"])
        
        # Reconstruct feature importance
        feature_importance = {}
        for feature in explanation.get("features", []):
            feature_importance[feature.get("feature_name", "")] = feature.get("importance", 0)
        
        # Get historical analogues
        analogues = []
        for analogue in explanation.get("historical_analogues", []):
            analogues.append({
                "decision_id": analogue.get("past_decision_id", ""),
                "timestamp": analogue.get("timestamp"),
                "action": analogue.get("action"),
                "confidence": analogue.get("confidence", 0),
                "outcome": analogue.get("outcome"),
                "similarity_score": analogue.get("similarity_score", 0),
                "market_conditions": analogue.get("market_conditions", {}),
            })
        
        # Market conditions from executive summary
        exec_summary = explanation.get("executive_summary", {})
        market_conditions = {
            "regime": explanation.get("market_regime"),
            "volatility": explanation.get("volatility"),
            "symbol": explanation.get("symbol"),
        }
        
        # Build reconstruction
        reconstruction = DecisionReconstruction(
            explanation_id=explanation_id,
            decision_id=explanation.get("decision_id", ""),
            timestamp=timestamp,
            original_action=explanation.get("action", ""),
            original_confidence=explanation.get("confidence", 0),
            original_expected_value=explanation.get("expected_value", 0),
            evidence_chain=evidence_chain,
            analyzer_signals=analyzer_signals,
            decision_tree=decision_tree,
            alternatives=alternatives,
            rejection_reasons=rejection_reasons,
            feature_importance=feature_importance,
            historical_analogues=analogues,
            market_conditions=market_conditions,
        )
        
        # Verify integrity
        reconstruction.integrity_verified = self._verify_integrity(reconstruction, explanation)
        reconstruction.reconstruction_notes = self._generate_reconstruction_notes(reconstruction)
        
        return reconstruction
    
    def _verify_integrity(
        self, 
        reconstruction: DecisionReconstruction, 
        explanation: Dict
    ) -> bool:
        """Verify the integrity of a reconstruction"""
        checks = []
        
        # Check evidence chain exists
        checks.append(len(reconstruction.evidence_chain) > 0)
        
        # Check decision tree exists
        checks.append(len(reconstruction.decision_tree) > 0)
        
        # Check all analyzer signals have required fields
        for name, signal in reconstruction.analyzer_signals.items():
            has_prediction = signal.get("prediction") is not None
            has_confidence = signal.get("confidence") is not None
            checks.append(has_prediction and has_confidence)
        
        # Check feature importance is not empty
        checks.append(len(reconstruction.feature_importance) > 0)
        
        return all(checks)
    
    def _generate_reconstruction_notes(
        self, 
        reconstruction: DecisionReconstruction
    ) -> List[str]:
        """Generate notes about the reconstruction"""
        notes = []
        
        # Evidence quality
        if len(reconstruction.evidence_chain) >= 5:
            notes.append("Rich evidence chain with 5+ items")
        elif len(reconstruction.evidence_chain) >= 3:
            notes.append("Adequate evidence chain with 3+ items")
        else:
            notes.append("Limited evidence chain - may have gaps")
        
        # Analyzer coverage
        num_analyzers = len(reconstruction.analyzer_signals)
        if num_analyzers >= 8:
            notes.append(f"Strong analyzer coverage ({num_analyzers} analyzers)")
        elif num_analyzers >= 5:
            notes.append(f"Moderate analyzer coverage ({num_analyzers} analyzers)")
        else:
            notes.append(f"Limited analyzer coverage ({num_analyzers} analyzers)")
        
        # Decision confidence
        if reconstruction.original_confidence >= 80:
            notes.append("High confidence decision (80%+)")
        elif reconstruction.original_confidence >= 60:
            notes.append("Moderate confidence decision (60-79%)")
        else:
            notes.append("Low confidence decision (<60%)")
        
        # Historical analogues
        if reconstruction.historical_analogues:
            avg_similarity = sum(
                a.get("similarity_score", 0) for a in reconstruction.historical_analogues
            ) / len(reconstruction.historical_analogues)
            notes.append(f"{len(reconstruction.historical_analogues)} similar past decisions (avg similarity: {avg_similarity:.0%})")
        
        return notes
    
    def generate_audit_report(
        self, 
        explanation_id: str,
        include_explanations: bool = True
    ) -> Optional[AuditReport]:
        """
        Generate a complete audit report for a decision.
        
        Args:
            explanation_id: ID of the explanation
            include_explanations: Include full explanations in report
            
        Returns:
            AuditReport or None if not found
        """
        # Get explanation
        explanation = self.storage.get_explanation_with_evidence(explanation_id)
        
        if not explanation:
            return None
        
        # Reconstruct decision
        reconstruction = self.reconstruct_decision(explanation_id)
        
        if not reconstruction:
            return None
        
        # Run integrity checks
        integrity_check = self._run_integrity_checks(reconstruction)
        
        # Calculate completeness score
        completeness_score = self._calculate_completeness(explanation)
        
        # Validate decision
        decision_validity = self._validate_decision(reconstruction)
        confidence_validity = self._validate_confidence(reconstruction)
        risk_assessment_validity = self._validate_risk_assessment(reconstruction)
        
        # Generate findings
        findings = self._generate_findings(reconstruction, integrity_check)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            reconstruction, findings, completeness_score
        )
        
        # Get explanations at each level
        beginner = explanation.get("beginner", {})
        advanced = explanation.get("advanced", {})
        developer = explanation.get("developer", {})
        researcher = explanation.get("researcher", {})
        
        return AuditReport(
            report_id=f"AUDIT-{explanation_id[:8]}",
            generated_at=datetime.utcnow(),
            explanation_id=explanation_id,
            decision_id=explanation.get("decision_id", ""),
            reconstruction=reconstruction,
            integrity_check=integrity_check,
            completeness_score=completeness_score,
            decision_validity=decision_validity,
            confidence_validity=confidence_validity,
            risk_assessment_validity=risk_assessment_validity,
            findings=findings,
            recommendations=recommendations,
            beginner_explanation=beginner if include_explanations else {},
            advanced_explanation=advanced if include_explanations else {},
            developer_explanation=developer if include_explanations else {},
            researcher_explanation=researcher if include_explanations else {},
        )
    
    def _run_integrity_checks(
        self, 
        reconstruction: DecisionReconstruction
    ) -> Dict[str, bool]:
        """Run integrity checks on reconstruction"""
        return {
            "has_evidence_chain": len(reconstruction.evidence_chain) > 0,
            "has_decision_tree": len(reconstruction.decision_tree) > 0,
            "has_analyzer_signals": len(reconstruction.analyzer_signals) > 0,
            "has_feature_importance": len(reconstruction.feature_importance) > 0,
            "confidence_in_range": 0 <= reconstruction.original_confidence <= 100,
            "expected_value_calculated": reconstruction.original_expected_value != 0,
            "market_conditions_known": reconstruction.market_conditions.get("regime") is not None,
        }
    
    def _calculate_completeness(self, explanation: Dict) -> float:
        """Calculate completeness score (0-1)"""
        score = 0.0
        total_checks = 10
        
        # Check each component exists
        checks = [
            explanation.get("explanation_id"),
            explanation.get("decision_id"),
            explanation.get("action"),
            explanation.get("confidence"),
            explanation.get("executive_summary"),
            explanation.get("beginner"),
            explanation.get("advanced"),
            explanation.get("developer"),
            explanation.get("researcher"),
            explanation.get("evidence_items"),
        ]
        
        score = sum(1 for c in checks if c is not None)
        return score / total_checks
    
    def _validate_decision(
        self, 
        reconstruction: DecisionReconstruction
    ) -> str:
        """Validate the decision was reasonable"""
        # Check confidence is in valid range
        if not (0 <= reconstruction.original_confidence <= 100):
            return "INVALID"
        
        # Check decision has an action
        if not reconstruction.original_action:
            return "INVALID"
        
        # Check evidence chain supports decision
        supporting_evidence = sum(
            1 for e in reconstruction.evidence_chain 
            if e.get("type") in ["analyzer_signal", "consensus"]
        )
        
        if supporting_evidence >= 3:
            return "VALID"
        elif supporting_evidence >= 1:
            return "UNCERTAIN"
        else:
            return "INVALID"
    
    def _validate_confidence(
        self, 
        reconstruction: DecisionReconstruction
    ) -> str:
        """Validate the confidence score"""
        confidence = reconstruction.original_confidence
        
        # Check if historical analogues support confidence
        analogues = reconstruction.historical_analogues
        if analogues:
            avg_outcome_confidence = sum(
                a.get("confidence", 0) for a in analogues
            ) / len(analogues)
            
            # If actual confidence is far from historical average, flag it
            if abs(confidence - avg_outcome_confidence) > 30:
                return "UNCERTAIN"
        
        # Confidence should be in reasonable range
        if 40 <= confidence <= 95:
            return "VALID"
        elif 30 <= confidence < 40 or 95 < confidence <= 100:
            return "UNCERTAIN"
        else:
            return "INVALID"
    
    def _validate_risk_assessment(
        self, 
        reconstruction: DecisionReconstruction
    ) -> str:
        """Validate risk assessment"""
        # Check market conditions are known
        if not reconstruction.market_conditions.get("regime"):
            return "UNCERTAIN"
        
        # Check expected value is reasonable
        ev = reconstruction.original_expected_value
        if ev == 0:
            return "UNCERTAIN"
        
        return "VALID"
    
    def _generate_findings(
        self, 
        reconstruction: DecisionReconstruction,
        integrity_check: Dict[str, bool]
    ) -> List[str]:
        """Generate findings from audit"""
        findings = []
        
        # Integrity findings
        if integrity_check.get("has_evidence_chain"):
            findings.append("Evidence chain is complete and verifiable")
        else:
            findings.append("WARNING: Evidence chain is incomplete or missing")
        
        if integrity_check.get("has_decision_tree"):
            findings.append(f"Decision tree contains {len(reconstruction.decision_tree)} steps")
        else:
            findings.append("WARNING: Decision tree is missing")
        
        # Confidence findings
        if reconstruction.original_confidence >= 70:
            findings.append(f"High confidence decision ({reconstruction.original_confidence:.0f}%)")
        elif reconstruction.original_confidence < 50:
            findings.append(f"Low confidence decision ({reconstruction.original_confidence:.0f}%)")
        
        # Analyzer findings
        num_analyzers = len(reconstruction.analyzer_signals)
        findings.append(f"{num_analyzers} analyzers contributed to this decision")
        
        # Historical context
        if reconstruction.historical_analogues:
            findings.append(
                f"Based on {len(reconstruction.historical_analogues)} similar historical decisions"
            )
        
        # Rejection reasons
        if reconstruction.rejection_reasons:
            findings.append(
                f"Decision skipped {len(reconstruction.rejection_reasons)} alternative actions"
            )
        
        return findings
    
    def _generate_recommendations(
        self,
        reconstruction: DecisionReconstruction,
        findings: List[str],
        completeness: float
    ) -> List[str]:
        """Generate recommendations based on audit"""
        recommendations = []
        
        # Completeness recommendation
        if completeness < 0.7:
            recommendations.append(
                "Improve explanation completeness - some components are missing"
            )
        
        # Evidence recommendations
        if len(reconstruction.evidence_chain) < 3:
            recommendations.append(
                "Consider adding more evidence sources for better transparency"
            )
        
        # Confidence recommendations
        if reconstruction.original_confidence < 50:
            recommendations.append(
                "Review low-confidence decisions - may need model retraining"
            )
        
        # Historical analogue recommendations
        if not reconstruction.historical_analogues:
            recommendations.append(
                "No similar historical decisions found - consider gathering more data"
            )
        
        # Decision tree recommendations
        if len(reconstruction.decision_tree) < 3:
            recommendations.append(
                "Decision tree could be more detailed for better explainability"
            )
        
        return recommendations
    
    def replay_explanation(
        self, 
        explanation_id: str,
        level: str = "advanced"
    ) -> Optional[Dict[str, Any]]:
        """
        Replay an explanation at a specific level.
        
        Args:
            explanation_id: ID of the explanation
            level: Explanation level (beginner, advanced, developer, researcher)
            
        Returns:
            Explanation data at specified level
        """
        explanation = self.storage.get_explanation(explanation_id)
        
        if not explanation:
            return None
        
        level_map = {
            "beginner": "beginner",
            "advanced": "advanced",
            "developer": "developer",
            "researcher": "researcher",
        }
        
        actual_level = level_map.get(level, "advanced")
        return explanation.get(actual_level, {})
    
    def get_decision_timeline(
        self, 
        decision_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get timeline of events around a decision.
        
        Args:
            decision_id: Decision ID
            
        Returns:
            List of timeline events
        """
        # Get the main explanation
        explanation = self.storage.get_explanation_by_decision(decision_id)
        
        if not explanation:
            return []
        
        timeline = []
        
        # Add generation event
        timeline.append({
            "timestamp": explanation.get("timestamp"),
            "event": "Explanation Generated",
            "description": f"AI explanation created for {explanation.get('action')} decision",
            "type": "generation",
        })
        
        # Add evidence chain events
        evidence_items = explanation.get("evidence_items", [])
        for item in evidence_items:
            timeline.append({
                "timestamp": item.get("timestamp"),
                "event": f"Evidence: {item.get('evidence_type')}",
                "description": str(item.get("data", {}))[:100],
                "type": "evidence",
                "weight": item.get("weight"),
            })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x.get("timestamp", ""))
        
        return timeline
    
    def export_audit_package(
        self, 
        explanation_id: str,
        format: str = "json"
    ) -> Optional[Dict[str, Any]]:
        """
        Export complete audit package for a decision.
        
        Args:
            explanation_id: ID of the explanation
            format: Export format (json, dict)
            
        Returns:
            Complete audit data package
        """
        # Generate audit report
        report = self.generate_audit_report(explanation_id)
        
        if not report:
            return None
        
        # Build package
        package = {
            "audit_package_id": report.report_id,
            "generated_at": report.generated_at.isoformat(),
            "explanation_id": report.explanation_id,
            "decision_id": report.decision_id,
            
            # Reconstruction summary
            "reconstruction": {
                "timestamp": report.reconstruction.timestamp.isoformat(),
                "action": report.reconstruction.original_action,
                "confidence": report.reconstruction.original_confidence,
                "expected_value": report.reconstruction.original_expected_value,
                "evidence_count": len(report.reconstruction.evidence_chain),
                "analyzer_count": len(report.reconstruction.analyzer_signals),
                "decision_tree_depth": len(report.reconstruction.decision_tree),
            },
            
            # Verification
            "integrity_check": report.integrity_check,
            "completeness_score": report.completeness_score,
            
            # Validity
            "decision_validity": report.decision_validity,
            "confidence_validity": report.confidence_validity,
            "risk_assessment_validity": report.risk_assessment_validity,
            
            # Analysis
            "findings": report.findings,
            "recommendations": report.recommendations,
            
            # Full evidence chain
            "evidence_chain": [
                {
                    "type": e.type,
                    "timestamp": e.timestamp,
                    "weight": e.weight,
                    "data": e.data,
                }
                for e in report.reconstruction.evidence_chain
            ],
            
            # Analyzer signals
            "analyzer_signals": report.reconstruction.analyzer_signals,
            
            # Decision tree
            "decision_tree": report.reconstruction.decision_tree,
            
            # Alternatives
            "alternatives": report.reconstruction.alternatives,
            
            # Feature importance
            "feature_importance": report.reconstruction.feature_importance,
            
            # Market conditions
            "market_conditions": report.reconstruction.market_conditions,
        }
        
        if format == "json":
            package["explanations"] = {
                "beginner": report.beginner_explanation,
                "advanced": report.advanced_explanation,
                "developer": report.developer_explanation,
                "researcher": report.researcher_explanation,
            }
        
        return package
