"""
Recommendation Engine
====================

Recommends relevant historical work when building new strategies.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

from .core import KnowledgeEntry

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    """A recommendation"""
    recommendation_id: str
    target_entity_id: str  # The entity being built/created
    target_entity_type: str  # "strategy", "model", etc.
    
    # What is recommended
    recommended_entity_id: str
    recommended_entity_name: str
    recommended_entity_type: str
    
    # Relevance
    relevance_score: float  # 0.0 - 1.0
    reason: str  # Why this is recommended
    
    # Context
    context: str  # e.g., "You might find this useful because..."
    usage_examples: List[str] = field(default_factory=list)
    
    # Metadata
    recommendation_type: str = "similar"  # "similar", "related", "based_on"
    created_at: float = field(default_factory=time.time)
    viewed: bool = False
    used: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "target_entity_id": self.target_entity_id,
            "recommended_entity_name": self.recommended_entity_name,
            "relevance_score": self.relevance_score,
            "reason": self.reason,
            "context": self.context,
            "created_at": self.created_at,
        }


class RecommendationEngine:
    """
    Recommends relevant historical work.
    
    Uses:
    - Content similarity
    - Tag matching
    - Link analysis
    - Usage patterns
    """
    
    def __init__(self, knowledge_store=None, cross_linker=None):
        self.store = knowledge_store
        self.cross_linker = cross_linker
        
        # Recommendation history
        self._recommendations: List[Recommendation] = []
        self._usage_patterns: Dict[str, List[str]] = {}  # entry_id -> list of viewed/used related IDs
    
    def recommend_for_new_strategy(
        self,
        strategy_name: str,
        strategy_description: str,
        strategy_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Recommendation]:
        """Recommend relevant historical work for a new strategy"""
        recommendations = []
        
        if not self.store:
            return recommendations
        
        # Find similar strategies
        similar = self._find_similar_strategies(
            strategy_name,
            strategy_description,
            strategy_type,
            tags,
            limit
        )
        recommendations.extend(similar)
        
        # Find related experiments
        experiments = self._find_relevant_experiments(
            strategy_description,
            tags,
            limit=3
        )
        recommendations.extend(experiments)
        
        # Find related models
        models = self._find_relevant_models(
            strategy_description,
            tags,
            limit=2
        )
        recommendations.extend(models)
        
        # Sort by relevance
        recommendations.sort(key=lambda r: r.relevance_score, reverse=True)
        
        return recommendations[:limit]
    
    def recommend_for_experiment(
        self,
        experiment_description: str,
        target_strategy_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Recommendation]:
        """Recommend relevant work for a new experiment"""
        recommendations = []
        
        if not self.store:
            return recommendations
        
        # Find related strategies
        if target_strategy_id:
            strategy = self.store.get_entry(target_strategy_id)
            if strategy:
                recommendations.append(Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    target_entity_id="",
                    target_entity_type="experiment",
                    recommended_entity_id=strategy.entry_id,
                    recommended_entity_name=strategy.name,
                    recommended_entity_type=strategy.entry_type,
                    relevance_score=0.95,
                    reason="This experiment tests this strategy",
                    context=f"You are testing {strategy.name}",
                    recommendation_type="related",
                ))
        
        # Find similar experiments
        similar = self._find_similar_experiments(
            experiment_description,
            tags,
            limit
        )
        recommendations.extend(similar)
        
        recommendations.sort(key=lambda r: r.relevance_score, reverse=True)
        return recommendations[:limit]
    
    def recommend_for_model(
        self,
        model_description: str,
        use_case: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Recommendation]:
        """Recommend relevant work for a new model"""
        recommendations = []
        
        if not self.store:
            return recommendations
        
        # Find related datasets
        datasets = self._find_relevant_datasets(
            model_description,
            tags,
            limit=3
        )
        recommendations.extend(datasets)
        
        # Find similar models
        similar = self._find_similar_models(
            model_description,
            tags,
            limit
        )
        recommendations.extend(similar)
        
        # Find strategies using similar models
        strategy_recommendations = self._find_strategies_using_models(
            model_description,
            limit=2
        )
        recommendations.extend(strategy_recommendations)
        
        recommendations.sort(key=lambda r: r.relevance_score, reverse=True)
        return recommendations[:limit]
    
    def _find_similar_strategies(
        self,
        name: str,
        description: str,
        strategy_type: Optional[str],
        tags: Optional[List[str]],
        limit: int
    ) -> List[Recommendation]:
        """Find similar strategies"""
        recommendations = []
        
        if not self.store:
            return recommendations
        
        strategies = self.store.get_entries_by_type("strategy")
        
        # Score each strategy
        scored = []
        name_lower = name.lower()
        desc_lower = description.lower()
        tag_set = set(t.lower() for t in (tags or []))
        
        for strategy in strategies:
            score = 0.0
            reasons = []
            
            # Name similarity
            if name_lower in strategy.name.lower():
                score += 0.3
                reasons.append("Similar name")
            elif any(word in strategy.name.lower() for word in name_lower.split()):
                score += 0.15
            
            # Description similarity
            if any(word in strategy.description.lower() for word in desc_lower.split()):
                score += 0.2
            
            # Tag overlap
            strategy_tags = set(t.lower() for t in strategy.tags)
            if tag_set & strategy_tags:
                overlap = len(tag_set & strategy_tags) / max(len(tag_set), 1)
                score += overlap * 0.3
                reasons.append("Shared tags")
            
            # Content similarity
            if any(word in strategy.content.lower() for word in desc_lower.split()[:5]):
                score += 0.2
            
            if score > 0.1:
                scored.append((strategy, score, reasons))
        
        # Sort and take top
        scored.sort(key=lambda x: x[1], reverse=True)
        
        for strategy, score, reasons in scored[:limit]:
            recommendations.append(Recommendation(
                recommendation_id=str(uuid.uuid4()),
                target_entity_id="",
                target_entity_type="strategy",
                recommended_entity_id=strategy.entry_id,
                recommended_entity_name=strategy.name,
                recommended_entity_type=strategy.entry_type,
                relevance_score=min(0.99, score),
                reason="; ".join(reasons) if reasons else "Similar strategy",
                context=f"This strategy may provide insights: {strategy.description[:100]}...",
                recommendation_type="similar",
            ))
        
        return recommendations
    
    def _find_relevant_experiments(
        self,
        description: str,
        tags: Optional[List[str]],
        limit: int
    ) -> List[Recommendation]:
        """Find relevant experiments"""
        recommendations = []
        
        if not self.store:
            return recommendations
        
        experiments = self.store.get_entries_by_type("experiment")
        
        scored = []
        desc_lower = description.lower()
        tag_set = set(t.lower() for t in (tags or []))
        
        for experiment in experiments:
            score = 0.0
            
            # Content match
            if any(word in experiment.content.lower() for word in desc_lower.split()[:5]):
                score += 0.4
            
            # Tag match
            exp_tags = set(t.lower() for t in experiment.tags)
            if tag_set & exp_tags:
                score += 0.3
            
            # Usage count (frequently used = valuable)
            score += min(0.2, experiment.usage_count * 0.01)
            
            if score > 0.1:
                scored.append((experiment, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        for experiment, score in scored[:limit]:
            recommendations.append(Recommendation(
                recommendation_id=str(uuid.uuid4()),
                target_entity_id="",
                target_entity_type="strategy",
                recommended_entity_id=experiment.entry_id,
                recommended_entity_name=experiment.name,
                recommended_entity_type=experiment.entry_type,
                relevance_score=min(0.95, score),
                reason="Relevant experiment",
                context=f"Previous experiment: {experiment.description[:100]}",
                recommendation_type="related",
            ))
        
        return recommendations
    
    def _find_relevant_models(
        self,
        description: str,
        tags: Optional[List[str]],
        limit: int
    ) -> List[Recommendation]:
        """Find relevant models"""
        recommendations = []
        
        if not self.store:
            return recommendations
        
        models = self.store.get_entries_by_type("model")
        
        scored = []
        desc_lower = description.lower()
        
        for model in models:
            score = 0.0
            
            # Description match
            if any(word in model.description.lower() for word in desc_lower.split()[:5]):
                score += 0.5
            
            # Content match
            if any(word in model.content.lower() for word in desc_lower.split()[:3]):
                score += 0.3
            
            if score > 0.1:
                scored.append((model, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        for model, score in scored[:limit]:
            recommendations.append(Recommendation(
                recommendation_id=str(uuid.uuid4()),
                target_entity_id="",
                target_entity_type="strategy",
                recommended_entity_id=model.entry_id,
                recommended_entity_name=model.name,
                recommended_entity_type=model.entry_type,
                relevance_score=min(0.9, score),
                reason="Uses similar models",
                context=f"Model: {model.description[:100]}",
                recommendation_type="related",
            ))
        
        return recommendations
    
    def _find_similar_experiments(
        self,
        description: str,
        tags: Optional[List[str]],
        limit: int
    ) -> List[Recommendation]:
        """Find similar experiments"""
        # Similar to _find_similar_strategies but for experiments
        recommendations = []
        
        if not self.store:
            return recommendations
        
        experiments = self.store.get_entries_by_type("experiment")
        desc_lower = description.lower()
        
        scored = []
        for exp in experiments:
            score = 0.0
            
            if any(word in exp.description.lower() for word in desc_lower.split()):
                score += 0.4
            
            if any(word in exp.content.lower() for word in desc_lower.split()[:5]):
                score += 0.3
            
            if score > 0.1:
                scored.append((exp, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        for exp, score in scored[:limit]:
            recommendations.append(Recommendation(
                recommendation_id=str(uuid.uuid4()),
                target_entity_id="",
                target_entity_type="experiment",
                recommended_entity_id=exp.entry_id,
                recommended_entity_name=exp.name,
                recommended_entity_type=exp.entry_type,
                relevance_score=min(0.9, score),
                reason="Similar experiment",
                context=f"Previous experiment: {exp.description[:100]}",
                recommendation_type="similar",
            ))
        
        return recommendations
    
    def _find_similar_models(
        self,
        description: str,
        tags: Optional[List[str]],
        limit: int
    ) -> List[Recommendation]:
        """Find similar models"""
        recommendations = []
        
        if not self.store:
            return recommendations
        
        models = self.store.get_entries_by_type("model")
        desc_lower = description.lower()
        
        scored = []
        for model in models:
            score = 0.0
            
            if any(word in model.description.lower() for word in desc_lower.split()):
                score += 0.5
            
            if any(word in model.name.lower() for word in desc_lower.split()):
                score += 0.3
            
            if score > 0.1:
                scored.append((model, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        for model, score in scored[:limit]:
            recommendations.append(Recommendation(
                recommendation_id=str(uuid.uuid4()),
                target_entity_id="",
                target_entity_type="model",
                recommended_entity_id=model.entry_id,
                recommended_entity_name=model.name,
                recommended_entity_type=model.entry_type,
                relevance_score=min(0.9, score),
                reason="Similar model architecture",
                context=f"Similar model: {model.description[:100]}",
                recommendation_type="similar",
            ))
        
        return recommendations
    
    def _find_relevant_datasets(
        self,
        description: str,
        tags: Optional[List[str]],
        limit: int
    ) -> List[Recommendation]:
        """Find relevant datasets"""
        recommendations = []
        
        if not self.store:
            return recommendations
        
        datasets = self.store.get_entries_by_type("dataset")
        desc_lower = description.lower()
        
        scored = []
        for dataset in datasets:
            score = 0.0
            
            if any(word in dataset.description.lower() for word in desc_lower.split()):
                score += 0.4
            
            if any(word in dataset.name.lower() for word in desc_lower.split()):
                score += 0.3
            
            if score > 0.1:
                scored.append((dataset, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        for dataset, score in scored[:limit]:
            recommendations.append(Recommendation(
                recommendation_id=str(uuid.uuid4()),
                target_entity_id="",
                target_entity_type="model",
                recommended_entity_id=dataset.entry_id,
                recommended_entity_name=dataset.name,
                recommended_entity_type=dataset.entry_type,
                relevance_score=min(0.9, score),
                reason="Uses this dataset",
                context=f"Dataset: {dataset.description[:100]}",
                recommendation_type="related",
            ))
        
        return recommendations
    
    def _find_strategies_using_models(
        self,
        model_description: str,
        limit: int
    ) -> List[Recommendation]:
        """Find strategies that use similar models"""
        recommendations = []
        
        if not self.store:
            return recommendations
        
        # Get strategies that link to models
        strategies = self.store.get_entries_by_type("strategy")
        
        for strategy in strategies:
            for link in strategy.links:
                if link.link_type == "uses_model":
                    model = self.store.get_entry(link.target_id)
                    if model:
                        # Check if this model is similar
                        if any(word in model.content.lower() 
                               for word in model_description.lower().split()[:5]):
                            recommendations.append(Recommendation(
                                recommendation_id=str(uuid.uuid4()),
                                target_entity_id="",
                                target_entity_type="model",
                                recommended_entity_id=strategy.entry_id,
                                recommended_entity_name=strategy.name,
                                recommended_entity_type=strategy.entry_type,
                                relevance_score=0.7,
                                reason="Uses similar model",
                                context=f"Strategy {strategy.name} uses {model.name}",
                                recommendation_type="based_on",
                            ))
        
        recommendations.sort(key=lambda r: r.relevance_score, reverse=True)
        return recommendations[:limit]
    
    def record_usage(self, recommendation: Recommendation, used: bool = True) -> None:
        """Record that a recommendation was used"""
        recommendation.used = used
        
        # Update patterns
        if recommendation.target_entity_id:
            if recommendation.target_entity_id not in self._usage_patterns:
                self._usage_patterns[recommendation.target_entity_id] = []
            self._usage_patterns[recommendation.target_entity_id].append(
                recommendation.recommended_entity_id
            )
    
    def get_recommendation_stats(self) -> Dict[str, Any]:
        """Get recommendation statistics"""
        total = len(self._recommendations)
        used = sum(1 for r in self._recommendations if r.used)
        viewed = sum(1 for r in self._recommendations if r.viewed)
        
        return {
            "total_recommendations": total,
            "used": used,
            "viewed": viewed,
            "usage_rate": used / total if total > 0 else 0,
            "view_rate": viewed / total if total > 0 else 0,
        }
