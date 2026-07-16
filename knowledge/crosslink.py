"""
Cross-Linking Engine
====================

Automatically creates links between related knowledge entities.
"""

import time
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

from .core import Link, KnowledgeEntry

logger = logging.getLogger(__name__)


class LinkType:
    """Predefined link types"""
    REFERENCES = "references"
    RELATED_TO = "related_to"
    INSPIRED_BY = "inspired_by"
    IMPROVED_FROM = "improved_from"
    BUILT_ON = "built_on"
    REPLACES = "replaces"
    DEPENDS_ON = "depends_on"
    USES_FEATURE = "uses_feature"
    USES_MODEL = "uses_model"
    USES_DATASET = "uses_dataset"
    VALIDATES = "validates"
    PROVES = "proves"
    CONTRADICTS = "contradicts"
    EXTENDS = "extends"
    DERIVED_FROM = "derived_from"


@dataclass
class LinkCandidate:
    """A candidate link between entities"""
    source_id: str
    target_id: str
    link_type: str
    confidence: float  # 0.0 - 1.0
    reason: str
    evidence: List[str] = field(default_factory=list)


class CrossLinker:
    """
    Automatically creates and manages cross-links between knowledge entities.
    
    Link types:
    - STRATEGIES ↔ FEATURES (strategies use features)
    - STRATEGIES ↔ MODELS (strategies use models)
    - STRATEGIES ↔ EXPERIMENTS (experiments test strategies)
    - MODELS ↔ DATASETS (models trained on datasets)
    - REPORTS ↔ STRATEGIES (reports analyze strategies)
    - REPORTS ↔ EXPERIMENTS (reports document experiments)
    """
    
    def __init__(self, knowledge_store=None):
        self.store = knowledge_store
        self._link_rules: List[Dict[str, Any]] = []
        self._initialize_rules()
    
    def _initialize_rules(self) -> None:
        """Initialize cross-linking rules"""
        self._link_rules = [
            # Strategy uses Feature
            {
                "source_type": "strategy",
                "target_type": "feature",
                "link_type": LinkType.USES_FEATURE,
                "condition": self._extract_feature_references,
            },
            # Strategy uses Model
            {
                "source_type": "strategy",
                "target_type": "model",
                "link_type": LinkType.USES_MODEL,
                "condition": self._extract_model_references,
            },
            # Experiment tests Strategy
            {
                "source_type": "experiment",
                "target_type": "strategy",
                "link_type": LinkType.VALIDATES,
                "condition": self._extract_strategy_references,
            },
            # Model trained on Dataset
            {
                "source_type": "model",
                "target_type": "dataset",
                "link_type": LinkType.USES_DATASET,
                "condition": self._extract_dataset_references,
            },
            # Report analyzes Strategy
            {
                "source_type": "report",
                "target_type": "strategy",
                "link_type": LinkType.REFERENCES,
                "condition": self._extract_strategy_references,
            },
            # Improvement links
            {
                "source_type": "strategy",
                "target_type": "strategy",
                "link_type": LinkType.IMPROVED_FROM,
                "condition": self._extract_improvement_references,
            },
        ]
    
    def analyze_and_link(self, entry: KnowledgeEntry) -> List[LinkCandidate]:
        """Analyze an entry and generate link candidates"""
        candidates = []
        
        # Apply each rule
        for rule in self._link_rules:
            if rule["source_type"] == entry.entry_type or rule["source_type"] == "*":
                references = rule["condition"](entry)
                
                for ref in references:
                    target_id, confidence, reason, evidence = ref
                    if target_id:
                        candidates.append(LinkCandidate(
                            source_id=entry.entry_id,
                            target_id=target_id,
                            link_type=rule["link_type"],
                            confidence=confidence,
                            reason=reason,
                            evidence=evidence,
                        ))
        
        return candidates
    
    def _extract_feature_references(
        self,
        entry: KnowledgeEntry
    ) -> List[Tuple[str, float, str, List[str]]]:
        """Extract feature references from entry"""
        results = []
        
        # Look for feature names/IDs in content
        content = entry.content.lower()
        
        # Common feature patterns
        patterns = [
            r'feature[:\s]+(\w+)',
            r'use[s]?\s+(\w+)\s+feature',
            r'(\w+)\s+indicator',
            r'rsi|macd|moving\s*average|bollinger',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                feature_name = match.lower().replace(' ', '_')
                
                # Look up feature entry
                feature_entries = self._find_entries_by_type_and_name(
                    "feature",
                    feature_name
                )
                
                for feature_id in feature_entries:
                    results.append((
                        feature_id,
                        0.8,
                        f"References feature: {feature_name}",
                        [f"Found in content: '{match}'"]
                    ))
        
        return results
    
    def _extract_model_references(
        self,
        entry: KnowledgeEntry
    ) -> List[Tuple[str, float, str, List[str]]]:
        """Extract model references from entry"""
        results = []
        content = entry.content.lower()
        
        patterns = [
            r'model[:\s]+(\w+)',
            r'use[s]?\s+(\w+)\s+model',
            r'ml\s+model',
            r'neural\s+network',
            r'random\s+forest|xgboost|lightgbm',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                model_name = match.lower().replace(' ', '_')
                
                model_entries = self._find_entries_by_type_and_name(
                    "model",
                    model_name
                )
                
                for model_id in model_entries:
                    results.append((
                        model_id,
                        0.85,
                        f"Uses model: {model_name}",
                        [f"Found in content: '{match}'"]
                    ))
        
        return results
    
    def _extract_dataset_references(
        self,
        entry: KnowledgeEntry
    ) -> List[Tuple[str, float, str, List[str]]]:
        """Extract dataset references from entry"""
        results = []
        content = entry.content.lower()
        
        patterns = [
            r'dataset[:\s]+(\w+)',
            r'train(?:ed|ing)?\s+on\s+(\w+)',
            r'data\s+from\s+(\w+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                dataset_name = match.lower().replace(' ', '_')
                
                dataset_entries = self._find_entries_by_type_and_name(
                    "dataset",
                    dataset_name
                )
                
                for dataset_id in dataset_entries:
                    results.append((
                        dataset_id,
                        0.9,
                        f"Trained on dataset: {dataset_name}",
                        [f"Found in content: '{match}'"]
                    ))
        
        return results
    
    def _extract_strategy_references(
        self,
        entry: KnowledgeEntry
    ) -> List[Tuple[str, float, str, List[str]]]:
        """Extract strategy references from entry"""
        results = []
        content = entry.content.lower()
        
        patterns = [
            r'strategy[:\s]+(\w+)',
            r'(\w+)\s+strategy',
            r'testing\s+(\w+)',
            r'analyz(?:e|ing)\s+(\w+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                strategy_name = match.lower().replace(' ', '_')
                
                strategy_entries = self._find_entries_by_type_and_name(
                    "strategy",
                    strategy_name
                )
                
                for strategy_id in strategy_entries:
                    results.append((
                        strategy_id,
                        0.75,
                        f"References strategy: {strategy_name}",
                        [f"Found in content: '{match}'"]
                    ))
        
        return results
    
    def _extract_improvement_references(
        self,
        entry: KnowledgeEntry
    ) -> List[Tuple[str, float, str, List[str]]]:
        """Extract improvement references (e.g., v2 improves v1)"""
        results = []
        content = entry.content.lower()
        
        # Look for version patterns
        patterns = [
            r'(v\d+)\s+improves?\s+(v\d+)',
            r'improved\s+from\s+(v\d+)',
            r'replaces?\s+(v\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                old_version = match[0] if len(match) > 0 else match
                
                # Look for previous version entries
                prev_entries = self._find_entries_by_type_and_name(
                    entry.entry_type,
                    entry.name.replace('v2', old_version).replace('v3', old_version)
                )
                
                for prev_id in prev_entries:
                    results.append((
                        prev_id,
                        0.95,
                        f"Improves over: {old_version}",
                        [f"Found in content: '{match}'"]
                    ))
        
        return results
    
    def _find_entries_by_type_and_name(
        self,
        entry_type: str,
        name: str
    ) -> List[str]:
        """Find entries by type and name"""
        if not self.store:
            return []
        
        entries = self.store.get_entries_by_type(entry_type)
        matching_ids = []
        
        name_lower = name.lower()
        
        for entry in entries:
            if name_lower in entry.name.lower():
                matching_ids.append(entry.entry_id)
        
        return matching_ids
    
    def suggest_links(
        self,
        entry: KnowledgeEntry,
        min_confidence: float = 0.5
    ) -> List[LinkCandidate]:
        """Get suggested links for an entry"""
        candidates = self.analyze_and_link(entry)
        return [c for c in candidates if c.confidence >= min_confidence]
    
    def create_links(
        self,
        candidates: List[LinkCandidate]
    ) -> List[Link]:
        """Create actual links from candidates"""
        created_links = []
        
        for candidate in candidates:
            if self.store:
                link = self.store.add_link(
                    source_id=candidate.source_id,
                    target_id=candidate.target_id,
                    link_type=candidate.link_type,
                    strength=candidate.confidence,
                )
                if link:
                    created_links.append(link)
        
        return created_links
    
    def find_transitive_relationships(
        self,
        entry_id: str,
        link_type: Optional[str] = None,
        max_depth: int = 3
    ) -> Dict[str, List[str]]:
        """Find transitive relationships"""
        if not self.store:
            return {}
        
        entry = self.store.get_entry(entry_id)
        if not entry:
            return {}
        
        relationships = {}
        visited = set()
        
        def traverse(current_id: str, depth: int) -> None:
            if depth > max_depth or current_id in visited:
                return
            
            visited.add(current_id)
            
            related = self.store.get_related(current_id, link_type)
            related_ids = [r.entry_id for r in related]
            
            relationships[f"depth_{depth}"] = related_ids
            
            for related_entry in related:
                traverse(related_entry.entry_id, depth + 1)
        
        traverse(entry_id, 0)
        
        return relationships
    
    def get_knowledge_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph"""
        if not self.store:
            return {}
        
        entries = list(self.store.entries.values())
        
        # Count link types
        link_type_counts: Dict[str, int] = {}
        for entry in entries:
            for link in entry.links:
                link_type_counts[link.link_type] = link_type_counts.get(link.link_type, 0) + 1
        
        # Find most connected entities
        connectivity = [
            (e.entry_id, e.name, len(e.links))
            for e in entries
        ]
        connectivity.sort(key=lambda x: x[2], reverse=True)
        
        return {
            "total_entries": len(entries),
            "total_links": self.store.stats["total_links"],
            "links_by_type": link_type_counts,
            "most_connected": connectivity[:10],
        }
