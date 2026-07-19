"""
Model Explainability - AI Model Interpretation

Complete explainability system with:
- Feature importance
- Permutation analysis
- Local explanations
- Global explanations
- Uncertainty estimation
"""

import json
import logging
import uuid
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class ExplanationType(Enum):
    """Types of explanations"""
    FEATURE_IMPORTANCE = "feature_importance"
    PERMUTATION = "permutation"
    SHAP = "shap"
    LIME = "lime"
    COUNTERFACTUAL = "counterfactual"
    PROTOTYPE = "prototype"
    ADVERSARIAL = "adversarial"


class UncertaintyType(Enum):
    """Types of uncertainty"""
    ALEATORIC = "aleatoric"  # Irreducible uncertainty
    EPISTEMIC = "epistemic"  # Model uncertainty
    TOTAL = "total"


@dataclass
class FeatureImportance:
    """Feature importance scores"""
    feature_name: str
    importance_score: float
    importance_type: str = "default"  # "default", "permutation", "shap"
    
    # Statistics
    std: Optional[float] = None
    confidence_interval: Tuple[float, float] = None
    
    # Metadata
    rank: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "importance_score": self.importance_score,
            "importance_type": self.importance_type,
            "std": self.std,
            "confidence_interval": self.confidence_interval,
            "rank": self.rank,
        }


@dataclass
class PermutationResult:
    """Result of permutation importance analysis"""
    feature_name: str
    
    # Baseline performance
    baseline_score: float
    
    # Permuted scores
    permuted_scores: List[float] = field(default_factory=list)
    
    # Calculated metrics
    importance: float = 0.0
    std: float = 0.0
    p_value: float = 1.0
    
    # Confidence
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "baseline_score": self.baseline_score,
            "permuted_scores": self.permuted_scores,
            "importance": self.importance,
            "std": self.std,
            "p_value": self.p_value,
            "confidence_interval": self.confidence_interval,
        }


@dataclass
class FeatureContribution:
    """Contribution of a single feature"""
    feature_name: str
    contribution: float  # Positive = supports prediction, Negative = contradicts
    
    # Context
    feature_value: float
    baseline_value: Optional[float] = None
    
    # Direction
    direction: str = "positive"  # "positive", "negative", "neutral"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "contribution": self.contribution,
            "feature_value": self.feature_value,
            "baseline_value": self.baseline_value,
            "direction": self.direction,
        }


@dataclass
class LocalExplanation:
    """Local explanation for a single prediction"""
    explanation_id: str
    prediction_id: str
    
    # Output (required, before optional fields)
    prediction: float
    input_features: Dict[str, float] = field(default_factory=dict)
    actual_outcome: Optional[float] = None
    
    # Feature contributions
    feature_contributions: List[FeatureContribution] = field(default_factory=list)
    
    # Local metrics
    local_importance: Dict[str, float] = field(default_factory=dict)
    
    # Confidence
    confidence: float = 0.0
    uncertainty: Optional[float] = None
    
    # Method used
    method: str = "shap"  # "shap", "lime", "integrated_gradients"
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanation_id": self.explanation_id,
            "prediction_id": self.prediction_id,
            "input_features": self.input_features,
            "prediction": self.prediction,
            "actual_outcome": self.actual_outcome,
            "feature_contributions": [f.to_dict() for f in self.feature_contributions],
            "local_importance": self.local_importance,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "method": self.method,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class FeatureInteraction:
    """Interaction between two features"""
    feature_1: str
    feature_2: str
    
    # Interaction strength
    interaction_strength: float = 0.0
    interaction_type: str = "unknown"  # "synergy", "redundancy", "antagonism"
    
    # Statistics
    correlation: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_1": self.feature_1,
            "feature_2": self.feature_2,
            "interaction_strength": self.interaction_strength,
            "interaction_type": self.interaction_type,
            "correlation": self.correlation,
        }


@dataclass
class GlobalExplanation:
    """Global model explanation"""
    explanation_id: str
    
    # Feature importance ranking
    feature_importance: List[FeatureImportance] = field(default_factory=list)
    
    # Feature interactions
    interactions: List[FeatureInteraction] = field(default_factory=list)
    
    # Feature statistics
    feature_statistics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Model behavior
    decision_boundary: Optional[Dict[str, Any]] = None
    
    # Summary
    summary_text: str = ""
    
    # Metadata
    model_id: str = ""
    model_version: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanation_id": self.explanation_id,
            "feature_importance": [f.to_dict() for f in self.feature_importance],
            "interactions": [i.to_dict() for i in self.interactions],
            "feature_statistics": self.feature_statistics,
            "decision_boundary": self.decision_boundary,
            "summary_text": self.summary_text,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class UncertaintyEstimate:
    """Uncertainty estimate for a prediction"""
    prediction_id: str
    
    # Types of uncertainty
    aleatoric: float = 0.0
    epistemic: float = 0.0
    total: float = 0.0
    
    # Confidence intervals
    confidence_interval_lower: float = 0.0
    confidence_interval_upper: float = 0.0
    
    # Prediction intervals (for regression)
    prediction_interval_lower: float = 0.0
    prediction_interval_upper: float = 0.0
    
    # Calibration
    is_calibrated: bool = False
    calibration_error: float = 0.0
    
    # Method
    method: str = "ensemble"  # "ensemble", "dropout", "bayesian"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "aleatoric": self.aleatoric,
            "epistemic": self.epistemic,
            "total": self.total,
            "confidence_interval_lower": self.confidence_interval_lower,
            "confidence_interval_upper": self.confidence_interval_upper,
            "prediction_interval_lower": self.prediction_interval_lower,
            "prediction_interval_upper": self.prediction_interval_upper,
            "is_calibrated": self.is_calibrated,
            "calibration_error": self.calibration_error,
            "method": self.method,
        }


class ModelExplainability:
    """
    Model Explainability for interpreting ML models.
    
    Features:
    - Feature importance analysis
    - Permutation importance
    - SHAP/LIME explanations
    - Local explanations
    - Global explanations
    - Uncertainty estimation
    - Feature interactions
    """
    
    def __init__(self, storage_path: str = "data/explainability"):
        self._storage_path = storage_path
        self._explanations: Dict[str, LocalExplanation] = {}
        self._global_explanations: Dict[str, GlobalExplanation] = {}
        
        import os
        os.makedirs(storage_path, exist_ok=True)
    
    # Feature Importance
    def calculate_feature_importance(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        method: str = "default",
    ) -> List[FeatureImportance]:
        """Calculate feature importance scores"""
        importance_list = []
        
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        
        if method == "default" and hasattr(model, "feature_importances_"):
            # Tree-based models
            importances = model.feature_importances_
            for i, (name, imp) in enumerate(zip(feature_names, importances)):
                importance_list.append(FeatureImportance(
                    feature_name=name,
                    importance_score=float(imp),
                    importance_type="default",
                ))
        
        elif method == "permutation":
            # Use permutation importance
            perm_results = self.calculate_permutation_importance(
                model, X, y, feature_names
            )
            for result in perm_results:
                importance_list.append(FeatureImportance(
                    feature_name=result.feature_name,
                    importance_score=result.importance,
                    importance_type="permutation",
                    std=result.std,
                ))
        
        # Sort by importance
        importance_list.sort(key=lambda x: x.importance_score, reverse=True)
        
        # Assign ranks
        for rank, imp in enumerate(importance_list, 1):
            imp.rank = rank
        
        return importance_list
    
    def calculate_permutation_importance(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        n_repeats: int = 10,
        scoring_func: Optional[Callable] = None,
    ) -> List[PermutationResult]:
        """Calculate permutation importance"""
        from sklearn.inspection import permutation_importance
        from sklearn.metrics import accuracy_score
        
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        
        if scoring_func is None:
            # Default scoring
            if hasattr(model, "predict_proba"):
                scoring_func = lambda m, x, y: accuracy_score(y, m.predict(x))
            else:
                scoring_func = lambda m, x, y: accuracy_score(y, m.predict(x))
        
        try:
            result = permutation_importance(
                model, X, y,
                n_repeats=n_repeats,
                random_state=42,
                scoring=scoring_func,
            )
            
            perm_results = []
            for i, name in enumerate(feature_names):
                perm_result = PermutationResult(
                    feature_name=name,
                    baseline_score=result.baseline_score[i] if hasattr(result, 'baseline_score') else 0,
                    permuted_scores=result.importances[i].tolist(),
                    importance=float(result.importances_mean[i]),
                    std=float(result.importances_std[i]),
                )
                perm_results.append(perm_result)
            
            return perm_results
            
        except Exception as e:
            logger.error(f"Permutation importance failed: {e}")
            return []
    
    # SHAP Explanations
    def calculate_shap_values(
        self,
        model: Any,
        X: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> Tuple[np.ndarray, Optional[Any]]:
        """Calculate SHAP values"""
        try:
            import shap
            
            if feature_names is None:
                feature_names = [f"feature_{i}" for i in range(X.shape[1])]
            
            # Create explainer
            if hasattr(model, "predict_proba"):
                if model.predict_proba(X[:1]).shape[1] == 2:
                    explainer = shap.TreeExplainer(model)
                else:
                    explainer = shap.TreeExplainer(model)
            else:
                explainer = shap.TreeExplainer(model)
            
            # Calculate SHAP values
            shap_values = explainer.shap_values(X)
            
            return shap_values, explainer
            
        except ImportError:
            logger.warning("SHAP not installed, using fallback")
            return self._calculate_fallback_shap(model, X, feature_names)
        except Exception as e:
            logger.error(f"SHAP calculation failed: {e}")
            return self._calculate_fallback_shap(model, X, feature_names)
    
    def _calculate_fallback_shap(
        self,
        model: Any,
        X: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> Tuple[np.ndarray, None]:
        """Fallback SHAP-like calculation using feature contribution"""
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        
        # Simple linear approximation
        n_samples = X.shape[0]
        n_features = X.shape[1]
        
        # Calculate baseline prediction
        if hasattr(model, "predict"):
            baseline = model.predict(X[:1])[0]
        else:
            baseline = 0.0
        
        # Calculate feature contributions (simplified)
        shap_values = np.zeros((n_samples, n_features))
        
        for i in range(n_features):
            # Calculate marginal contribution
            feature_values = X[:, i]
            feature_std = np.std(feature_values)
            
            if hasattr(model, "predict_proba"):
                preds = model.predict_proba(X)[:, 1]
            else:
                preds = model.predict(X)
            
            # Simple correlation-based approximation
            if preds.std() > 0:
                correlation = np.corrcoef(feature_values, preds)[0, 1]
                shap_values[:, i] = correlation * feature_std
        
        return shap_values, None
    
    # Local Explanations
    def explain_prediction(
        self,
        model: Any,
        X_sample: np.ndarray,
        feature_names: Optional[List[str]] = None,
        method: str = "shap",
        baseline: Optional[np.ndarray] = None,
    ) -> LocalExplanation:
        """Generate local explanation for a single prediction"""
        explanation = LocalExplanation(
            explanation_id=str(uuid.uuid4()),
            prediction_id=str(uuid.uuid4()),
            method=method,
        )
        
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(X_sample.shape[0])]
        
        # Reshape if needed
        if len(X_sample.shape) == 1:
            X_sample = X_sample.reshape(1, -1)
        
        # Get prediction
        if hasattr(model, "predict_proba"):
            pred_proba = model.predict_proba(X_sample)[0]
            prediction = float(pred_proba[1] if len(pred_proba) > 1 else pred_proba[0])
        else:
            prediction = float(model.predict(X_sample)[0])
        
        explanation.prediction = prediction
        explanation.confidence = prediction if prediction <= 1 else 0.5
        
        # Calculate feature contributions
        if method == "shap":
            shap_values, _ = self.calculate_shap_values(
                model, X_sample, feature_names
            )
            if isinstance(shap_values, list):
                shap_values = shap_values[0] if len(shap_values) > 0 else np.zeros(len(feature_names))
            else:
                shap_values = shap_values[0] if len(shap_values.shape) > 1 else shap_values
        else:
            shap_values = self._calculate_simple_contributions(model, X_sample, feature_names)
        
        # Create feature contributions
        for i, (name, value, contribution) in enumerate(zip(
            feature_names, X_sample[0], shap_values
        )):
            direction = "positive" if contribution > 0 else "negative" if contribution < 0 else "neutral"
            
            contribution_obj = FeatureContribution(
                feature_name=name,
                contribution=float(contribution),
                feature_value=float(value),
                baseline_value=float(baseline[i]) if baseline is not None else None,
                direction=direction,
            )
            explanation.feature_contributions.append(contribution_obj)
            
            explanation.local_importance[name] = abs(float(contribution))
            explanation.input_features[name] = float(value)
        
        # Sort by importance
        explanation.feature_contributions.sort(key=lambda x: abs(x.contribution), reverse=True)
        
        return explanation
    
    def _calculate_simple_contributions(
        self,
        model: Any,
        X_sample: np.ndarray,
        feature_names: List[str],
    ) -> np.ndarray:
        """Calculate simple feature contributions"""
        n_features = len(feature_names)
        contributions = np.zeros(n_features)
        
        # Get baseline prediction
        baseline = np.zeros(n_features)
        if hasattr(model, "predict_proba"):
            baseline_pred = model.predict_proba(baseline.reshape(1, -1))[0]
            baseline_pred = baseline_pred[1] if len(baseline_pred) > 1 else baseline_pred[0]
        else:
            baseline_pred = float(model.predict(baseline.reshape(1, -1))[0])
        
        # Calculate marginal contributions
        for i in range(n_features):
            test_features = baseline.copy()
            test_features[i] = X_sample[0, i]
            
            if hasattr(model, "predict_proba"):
                test_pred = model.predict_proba(test_features.reshape(1, -1))[0]
                test_pred = test_pred[1] if len(test_pred) > 1 else test_pred[0]
            else:
                test_pred = float(model.predict(test_features.reshape(1, -1))[0])
            
            contributions[i] = test_pred - baseline_pred
        
        return contributions
    
    # Global Explanations
    def generate_global_explanation(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> GlobalExplanation:
        """Generate global model explanation"""
        explanation = GlobalExplanation(
            explanation_id=str(uuid.uuid4()),
        )
        
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        
        # Calculate feature importance
        importance_list = self.calculate_feature_importance(
            model, X, y, feature_names, method="permutation"
        )
        explanation.feature_importance = importance_list
        
        # Calculate feature statistics
        for i, name in enumerate(feature_names):
            explanation.feature_statistics[name] = {
                "mean": float(np.mean(X[:, i])),
                "std": float(np.std(X[:, i])),
                "min": float(np.min(X[:, i])),
                "max": float(np.max(X[:, i])),
                "median": float(np.median(X[:, i])),
            }
        
        # Calculate feature interactions (simplified)
        explanation.interactions = self._calculate_feature_interactions(X, feature_names)
        
        # Generate summary
        explanation.summary_text = self._generate_summary_text(explanation)
        
        return explanation
    
    def _calculate_feature_interactions(
        self,
        X: np.ndarray,
        feature_names: List[str],
        max_interactions: int = 20,
    ) -> List[FeatureInteraction]:
        """Calculate feature interactions using correlation"""
        interactions = []
        
        n_features = min(X.shape[1], len(feature_names))
        
        # Calculate correlation matrix
        corr_matrix = np.corrcoef(X[:, :n_features].T)
        
        for i in range(n_features):
            for j in range(i + 1, n_features):
                if len(interactions) >= max_interactions:
                    break
                
                corr = float(corr_matrix[i, j])
                
                # Only include strong interactions
                if abs(corr) > 0.5:
                    interaction_type = "synergy" if corr > 0 else "redundancy"
                    
                    interaction = FeatureInteraction(
                        feature_1=feature_names[i],
                        feature_2=feature_names[j],
                        interaction_strength=abs(corr),
                        interaction_type=interaction_type,
                        correlation=corr,
                    )
                    interactions.append(interaction)
        
        # Sort by strength
        interactions.sort(key=lambda x: x.interaction_strength, reverse=True)
        
        return interactions[:max_interactions]
    
    def _generate_summary_text(self, explanation: GlobalExplanation) -> str:
        """Generate human-readable summary"""
        if not explanation.feature_importance:
            return "No significant features found."
        
        top_features = explanation.feature_importance[:3]
        
        summary = "Key insights:\n"
        for i, feature in enumerate(top_features, 1):
            direction = "increases" if feature.importance_score > 0 else "decreases"
            summary += f"{i}. {feature.feature_name}: {direction} prediction (importance: {feature.importance_score:.3f})\n"
        
        if explanation.interactions:
            top_interaction = explanation.interactions[0]
            summary += f"\nNotable interaction: {top_interaction.feature_1} and {top_interaction.feature_2} show {top_interaction.interaction_type}\n"
        
        return summary
    
    # Uncertainty Estimation
    def estimate_uncertainty(
        self,
        model: Any,
        X: np.ndarray,
        method: str = "ensemble",
        n_samples: int = 100,
    ) -> UncertaintyEstimate:
        """Estimate prediction uncertainty"""
        estimate = UncertaintyEstimate(
            prediction_id=str(uuid.uuid4()),
            method=method,
        )
        
        if len(X.shape) == 1:
            X = X.reshape(1, -1)
        
        # Get predictions from multiple forward passes
        if method == "ensemble" and hasattr(model, "estimators_"):
            # Use ensemble variance
            predictions = np.array([
                estimator.predict(X) for estimator in model.estimators_
            ])
            
            estimate.epistemic = float(np.std(predictions))
            estimate.aleatoric = float(np.mean(predictions) * (1 - np.mean(predictions)))  # Binary assumption
            estimate.total = np.sqrt(estimate.epistemic ** 2 + estimate.aleatoric ** 2)
        
        elif method == "dropout":
            # Monte Carlo Dropout approximation
            # This would require a model with dropout layers
            estimate.epistemic = float(np.std([0.5] * n_samples))  # Placeholder
            estimate.total = estimate.epistemic
        
        else:
            # Simple prediction-based uncertainty
            if hasattr(model, "predict_proba"):
                probas = model.predict_proba(X)[0]
                max_proba = max(probas)
                uncertainty = 1 - max_proba
                
                estimate.epistemic = float(uncertainty)
                estimate.total = float(uncertainty)
            else:
                estimate.total = 0.1  # Default uncertainty
        
        # Calculate confidence intervals (95%)
        if hasattr(model, "predict_proba"):
            probas = model.predict_proba(X)
            if probas.shape[1] == 2:
                positive_probas = probas[:, 1]
                estimate.confidence_interval_lower = float(np.percentile(positive_probas, 2.5))
                estimate.confidence_interval_upper = float(np.percentile(positive_probas, 97.5))
        
        return estimate
    
    # Calibration Analysis
    def analyze_calibration(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
        n_bins: int = 10,
    ) -> Dict[str, Any]:
        """Analyze model calibration"""
        from sklearn.calibration import calibration_curve
        
        if hasattr(model, "predict_proba"):
            probas = model.predict_proba(X)[:, 1]
        else:
            probas = model.predict(X)
        
        # Calculate calibration curve
        fraction_positives, mean_predicted = calibration_curve(
            y, probas, n_bins=n_bins, strategy="uniform"
        )
        
        # Calculate Expected Calibration Error (ECE)
        ece = np.sum(np.abs(fraction_positives - mean_predicted) * (1 / n_bins))
        
        # Calculate Maximum Calibration Error (MCE)
        mce = np.max(np.abs(fraction_positives - mean_predicted))
        
        return {
            "fraction_positives": fraction_positives.tolist(),
            "mean_predicted": mean_predicted.tolist(),
            "expected_calibration_error": float(ece),
            "maximum_calibration_error": float(mce),
            "n_bins": n_bins,
        }
    
    # Counterfactual Explanations
    def generate_counterfactuals(
        self,
        model: Any,
        X_sample: np.ndarray,
        feature_names: List[str],
        desired_outcome: float,
        n_candidates: int = 10,
    ) -> List[Dict[str, Any]]:
        """Generate counterfactual explanations"""
        counterfactuals = []
        
        if len(X_sample.shape) == 1:
            X_sample = X_sample.reshape(1, -1)
        
        # Simple random perturbation approach
        for _ in range(n_candidates):
            # Randomly perturb features
            perturbation = np.random.randn(len(feature_names)) * 0.1
            cf_sample = X_sample + perturbation
            
            # Get prediction
            if hasattr(model, "predict_proba"):
                cf_pred = model.predict_proba(cf_sample)[0][1]
            else:
                cf_pred = model.predict(cf_sample)[0]
            
            # Check if close to desired outcome
            if abs(cf_pred - desired_outcome) < 0.1:
                # Calculate feature changes
                changes = {}
                for i, name in enumerate(feature_names):
                    if abs(cf_sample[0, i] - X_sample[0, i]) > 0.01:
                        changes[name] = {
                            "original": float(X_sample[0, i]),
                            "counterfactual": float(cf_sample[0, i]),
                            "change": float(cf_sample[0, i] - X_sample[0, i]),
                        }
                
                counterfactuals.append({
                    "prediction": float(cf_pred),
                    "feature_changes": changes,
                })
        
        # Sort by minimal changes
        counterfactuals.sort(key=lambda x: len(x["feature_changes"]))
        
        return counterfactuals[:5]  # Return top 5
    
    # Save and Load
    def save_explanation(self, explanation: LocalExplanation) -> None:
        """Save a local explanation"""
        self._explanations[explanation.explanation_id] = explanation
    
    def get_explanation(self, explanation_id: str) -> Optional[LocalExplanation]:
        """Get a local explanation"""
        return self._explanations.get(explanation_id)
    
    def save_global_explanation(self, explanation: GlobalExplanation) -> None:
        """Save a global explanation"""
        self._global_explanations[explanation.explanation_id] = explanation
    
    def get_global_explanation(self, explanation_id: str) -> Optional[GlobalExplanation]:
        """Get a global explanation"""
        return self._global_explanations.get(explanation_id)


import os
