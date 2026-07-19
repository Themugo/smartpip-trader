"""
Research Workspace - AI-Powered Research Notebook

Complete research notebook with:
- Hypotheses
- Experiments
- Observations
- Conclusions
- Attached datasets
- Visualizations
"""

import json
import logging
import uuid
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class CellType(Enum):
    """Notebook cell types"""
    MARKDOWN = "markdown"
    CODE = "code"
    CHART = "chart"
    TABLE = "table"
    METRIC = "metric"
    HYPOTHESIS = "hypothesis"
    OBSERVATION = "observation"
    CONCLUSION = "conclusion"
    ATTACHMENT = "attachment"


class HypothesisStatus(Enum):
    """Hypothesis status"""
    DRAFT = "draft"
    TESTING = "testing"
    SUPPORTED = "supported"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class ExperimentStatus(Enum):
    """Experiment status tracking"""
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Hypothesis:
    """Research hypothesis"""
    id: str
    title: str
    description: str
    status: HypothesisStatus = HypothesisStatus.DRAFT
    
    # Variables
    independent_variables: List[str] = field(default_factory=list)
    dependent_variables: List[str] = field(default_factory=list)
    
    # Experiment linkage
    experiment_ids: List[str] = field(default_factory=list)
    
    # Results
    evidence: List[str] = field(default_factory=list)  # Supporting evidence
    counter_evidence: List[str] = field(default_factory=list)
    
    # Metadata
    author: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "independent_variables": self.independent_variables,
            "dependent_variables": self.dependent_variables,
            "experiment_ids": self.experiment_ids,
            "evidence": self.evidence,
            "counter_evidence": self.counter_evidence,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
        }


@dataclass
class Observation:
    """Research observation"""
    id: str
    timestamp: datetime
    description: str
    category: str  # e.g., "market", "behavior", "pattern", "anomaly"
    
    # Data linkage
    dataset_id: Optional[str] = None
    experiment_id: Optional[str] = None
    
    # Evidence
    data_points: List[Dict[str, Any]] = field(default_factory=list)
    visualization_config: Optional[Dict[str, Any]] = None
    
    # Impact
    related_hypotheses: List[str] = field(default_factory=list)
    significance: str = "normal"  # "low", "normal", "high", "critical"
    
    # Metadata
    author: str = ""
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "category": self.category,
            "dataset_id": self.dataset_id,
            "experiment_id": self.experiment_id,
            "data_points": self.data_points,
            "visualization_config": self.visualization_config,
            "related_hypotheses": self.related_hypotheses,
            "significance": self.significance,
            "author": self.author,
            "tags": self.tags,
        }


@dataclass
class Conclusion:
    """Research conclusion"""
    id: str
    title: str
    description: str
    
    # Source linkage
    hypothesis_ids: List[str] = field(default_factory=list)
    experiment_ids: List[str] = field(default_factory=list)
    observation_ids: List[str] = field(default_factory=list)
    
    # Findings
    key_findings: List[str] = field(default_factory=list)
    implications: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Confidence
    confidence_level: float = 0.0  # 0-100
    supporting_evidence_count: int = 0
    contradicting_evidence_count: int = 0
    
    # Metadata
    author: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "hypothesis_ids": self.hypothesis_ids,
            "experiment_ids": self.experiment_ids,
            "observation_ids": self.observation_ids,
            "key_findings": self.key_findings,
            "implications": self.implications,
            "recommendations": self.recommendations,
            "confidence_level": self.confidence_level,
            "supporting_evidence_count": self.supporting_evidence_count,
            "contradicting_evidence_count": self.contradicting_evidence_count,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
        }


@dataclass
class DatasetAttachment:
    """Attached dataset to notebook"""
    dataset_id: str
    name: str
    description: str
    version: str
    attachment_type: str = "snapshot"  # "snapshot", "link", "reference"
    added_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    added_by: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "attachment_type": self.attachment_type,
            "added_at": self.added_at.isoformat(),
            "added_by": self.added_by,
        }


@dataclass
class Visualization:
    """Chart or visualization"""
    id: str
    title: str
    chart_type: str  # "line", "bar", "scatter", "heatmap", "candlestick", etc.
    
    # Data
    data_source: str = ""  # Reference to data or inline data
    x_axis: str = ""
    y_axis: str = ""
    series: List[Dict[str, Any]] = field(default_factory=list)
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Linkage
    linked_cells: List[str] = field(default_factory=list)  # Cell IDs
    linked_observations: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "chart_type": self.chart_type,
            "data_source": self.data_source,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "series": self.series,
            "config": self.config,
            "linked_cells": self.linked_cells,
            "linked_observations": self.linked_observations,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class NotebookCell:
    """A single cell in the notebook"""
    id: str
    cell_type: CellType
    content: str
    
    # For code cells
    outputs: List[str] = field(default_factory=list)
    
    # For chart cells
    visualization_id: Optional[str] = None
    
    # For metric cells
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    order: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    execution_count: int = 0
    last_executed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cell_type": self.cell_type.value,
            "content": self.content,
            "outputs": self.outputs,
            "visualization_id": self.visualization_id,
            "metrics": self.metrics,
            "order": self.order,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "execution_count": self.execution_count,
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
        }


@dataclass
class ResearchWorkspace:
    """Complete AI Research Workspace"""
    id: str
    title: str
    author: str
    
    # Content
    cells: List[NotebookCell] = field(default_factory=list)
    
    # Research components
    hypotheses: List[Hypothesis] = field(default_factory=list)
    observations: List[Observation] = field(default_factory=list)
    conclusions: List[Conclusion] = field(default_factory=list)
    visualizations: List[Visualization] = field(default_factory=list)
    attached_datasets: List[DatasetAttachment] = field(default_factory=list)
    
    # Strategy linkage
    strategy_id: Optional[str] = None
    strategy_version: Optional[str] = None
    experiment_ids: List[str] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    description: str = ""
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # State
    is_locked: bool = False
    locked_by: Optional[str] = None
    version: int = 1
    checksum: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "cells": [c.to_dict() for c in self.cells],
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "observations": [o.to_dict() for o in self.observations],
            "conclusions": [c.to_dict() for c in self.conclusions],
            "visualizations": [v.to_dict() for v in self.visualizations],
            "attached_datasets": [d.to_dict() for d in self.attached_datasets],
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "experiment_ids": self.experiment_ids,
            "tags": self.tags,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_locked": self.is_locked,
            "locked_by": self.locked_by,
            "version": self.version,
            "checksum": self.checksum,
        }
    
    def compute_checksum(self) -> str:
        """Compute content checksum for version tracking"""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class ResearchWorkspaceManager:
    """
    Research Workspace Manager for comprehensive research documentation.
    
    Features:
    - Hypothesis formulation and tracking
    - Experiment documentation
    - Observation recording
    - Conclusion derivation
    - Dataset attachments
    - Visualization management
    - Version control and reproducibility
    """
    
    def __init__(self, storage_path: str = "data/research_workspaces"):
        self._storage_path = storage_path
        self._workspaces: Dict[str, ResearchWorkspace] = {}
        self._index: Dict[str, List[str]] = defaultdict(list)  # tag -> workspace IDs
        
        import os
        os.makedirs(storage_path, exist_ok=True)
        self._load_workspaces()
    
    def _load_workspaces(self) -> None:
        """Load workspaces from storage"""
        index_file = f"{self._storage_path}/index.json"
        
        try:
            if os.path.exists(index_file):
                with open(index_file, "r") as f:
                    data = json.load(f)
                
                for ws_data in data.get("workspaces", []):
                    ws_data["created_at"] = datetime.fromisoformat(ws_data["created_at"])
                    ws_data["updated_at"] = datetime.fromisoformat(ws_data["updated_at"])
                    
                    # Load cells
                    for cell in ws_data.get("cells", []):
                        cell["created_at"] = datetime.fromisoformat(cell["created_at"])
                        cell["updated_at"] = datetime.fromisoformat(cell["updated_at"])
                        if cell.get("last_executed_at"):
                            cell["last_executed_at"] = datetime.fromisoformat(cell["last_executed_at"])
                    
                    # Load hypotheses
                    for h in ws_data.get("hypotheses", []):
                        h["created_at"] = datetime.fromisoformat(h["created_at"])
                        h["updated_at"] = datetime.fromisoformat(h["updated_at"])
                    
                    # Load observations
                    for o in ws_data.get("observations", []):
                        o["timestamp"] = datetime.fromisoformat(o["timestamp"])
                    
                    # Load conclusions
                    for c in ws_data.get("conclusions", []):
                        c["created_at"] = datetime.fromisoformat(c["created_at"])
                    
                    # Load visualizations
                    for v in ws_data.get("visualizations", []):
                        v["created_at"] = datetime.fromisoformat(v["created_at"])
                    
                    # Load dataset attachments
                    for d in ws_data.get("attached_datasets", []):
                        d["added_at"] = datetime.fromisoformat(d["added_at"])
                    
                    ws = ResearchWorkspace(**ws_data)
                    self._workspaces[ws.id] = ws
                    
                    # Build index
                    for tag in ws.tags:
                        self._index[tag].append(ws.id)
                
                logger.info(f"Loaded {len(self._workspaces)} research workspaces")
        except Exception as e:
            logger.warning(f"Could not load workspaces: {e}")
    
    def _save_workspaces(self) -> None:
        """Save workspaces to storage"""
        index_file = f"{self._storage_path}/index.json"
        
        # Rebuild index
        self._index.clear()
        for ws in self._workspaces.values():
            for tag in ws.tags:
                self._index[tag].append(ws.id)
        
        data = {
            "workspaces": [ws.to_dict() for ws in self._workspaces.values()],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def create_workspace(
        self,
        title: str,
        author: str,
        description: str = "",
        strategy_id: Optional[str] = None,
        strategy_version: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> ResearchWorkspace:
        """Create a new research workspace"""
        workspace = ResearchWorkspace(
            id=str(uuid.uuid4()),
            title=title,
            author=author,
            description=description,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            tags=tags or [],
        )
        
        # Add default template
        self._add_default_template(workspace)
        
        self._workspaces[workspace.id] = workspace
        workspace.checksum = workspace.compute_checksum()
        self._save_workspaces()
        
        logger.info(f"Created workspace: {title}")
        return workspace
    
    def _add_default_template(self, workspace: ResearchWorkspace) -> None:
        """Add default research template"""
        # Title section
        workspace.cells.append(NotebookCell(
            id=str(uuid.uuid4()),
            cell_type=CellType.MARKDOWN,
            content=f"# {workspace.title}\n\n{workspace.description}",
            order=0,
        ))
        
        # Research sections
        sections = [
            (CellType.MARKDOWN, "## Executive Summary\n\nProvide a brief overview of this research."),
            (CellType.MARKDOWN, "## Research Questions\n\nWhat are you trying to discover?"),
            (CellType.HYPOTHESIS, "HYPOTHESIS: Formulate your first hypothesis here."),
            (CellType.MARKDOWN, "## Methodology\n\nDescribe your research approach."),
            (CellType.CODE, "# Data Loading\nimport pandas as pd\nimport numpy as np"),
            (CellType.MARKDOWN, "## Data Analysis\n\nAnalyze your data here."),
            (CellType.OBSERVATION, "OBSERVATION: Record key observations."),
            (CellType.CODE, "# Visualization\nimport matplotlib.pyplot as plt"),
            (CellType.MARKDOWN, "## Results\n\nPresent your findings."),
            (CellType.CONCLUSION, "CONCLUSION: Summarize your research conclusions."),
            (CellType.MARKDOWN, "## Next Steps\n\nWhat should be done next?"),
        ]
        
        for order, (cell_type, content) in enumerate(sections, 1):
            workspace.cells.append(NotebookCell(
                id=str(uuid.uuid4()),
                cell_type=cell_type,
                content=content,
                order=order,
            ))
    
    # Hypothesis Management
    def add_hypothesis(
        self,
        workspace_id: str,
        title: str,
        description: str,
        independent_variables: List[str],
        dependent_variables: List[str],
        author: str = "",
        tags: Optional[List[str]] = None,
    ) -> Optional[Hypothesis]:
        """Add a hypothesis to a workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        
        hypothesis = Hypothesis(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            independent_variables=independent_variables,
            dependent_variables=dependent_variables,
            author=author,
            tags=tags or [],
        )
        
        workspace.hypotheses.append(hypothesis)
        workspace.updated_at = datetime.now(timezone.utc)
        workspace.checksum = workspace.compute_checksum()
        self._save_workspaces()
        
        return hypothesis
    
    def update_hypothesis(
        self,
        workspace_id: str,
        hypothesis_id: str,
        status: Optional[HypothesisStatus] = None,
        evidence: Optional[List[str]] = None,
        counter_evidence: Optional[List[str]] = None,
    ) -> bool:
        """Update a hypothesis"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return False
        
        for h in workspace.hypotheses:
            if h.id == hypothesis_id:
                if status:
                    h.status = status
                if evidence:
                    h.evidence.extend(evidence)
                if counter_evidence:
                    h.counter_evidence.extend(counter_evidence)
                h.updated_at = datetime.now(timezone.utc)
                workspace.updated_at = datetime.now(timezone.utc)
                workspace.checksum = workspace.compute_checksum()
                self._save_workspaces()
                return True
        
        return False
    
    # Observation Management
    def add_observation(
        self,
        workspace_id: str,
        description: str,
        category: str,
        data_points: Optional[List[Dict[str, Any]]] = None,
        significance: str = "normal",
        author: str = "",
        tags: Optional[List[str]] = None,
    ) -> Optional[Observation]:
        """Add an observation to a workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        
        observation = Observation(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            description=description,
            category=category,
            data_points=data_points or [],
            significance=significance,
            author=author,
            tags=tags or [],
        )
        
        workspace.observations.append(observation)
        workspace.updated_at = datetime.now(timezone.utc)
        workspace.checksum = workspace.compute_checksum()
        self._save_workspaces()
        
        return observation
    
    def link_observation_to_hypothesis(
        self,
        workspace_id: str,
        observation_id: str,
        hypothesis_id: str,
    ) -> bool:
        """Link an observation to a hypothesis"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return False
        
        for o in workspace.observations:
            if o.id == observation_id:
                if hypothesis_id not in o.related_hypotheses:
                    o.related_hypotheses.append(hypothesis_id)
                workspace.updated_at = datetime.now(timezone.utc)
                self._save_workspaces()
                return True
        
        return False
    
    # Conclusion Management
    def add_conclusion(
        self,
        workspace_id: str,
        title: str,
        description: str,
        hypothesis_ids: Optional[List[str]] = None,
        experiment_ids: Optional[List[str]] = None,
        observation_ids: Optional[List[str]] = None,
        key_findings: Optional[List[str]] = None,
        implications: Optional[List[str]] = None,
        recommendations: Optional[List[str]] = None,
        author: str = "",
        tags: Optional[List[str]] = None,
    ) -> Optional[Conclusion]:
        """Add a conclusion to a workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        
        # Calculate confidence based on supporting evidence
        supporting_count = 0
        contradicting_count = 0
        
        for hid in (hypothesis_ids or []):
            for h in workspace.hypotheses:
                if h.id == hid:
                    if h.status == HypothesisStatus.SUPPORTED:
                        supporting_count += len(h.evidence)
                    elif h.status == HypothesisStatus.REJECTED:
                        contradicting_count += 1
        
        confidence = 50.0  # Base confidence
        if supporting_count > 0:
            confidence = min(95, 50 + supporting_count * 10)
        if contradicting_count > 0:
            confidence = max(5, confidence - contradicting_count * 20)
        
        conclusion = Conclusion(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            hypothesis_ids=hypothesis_ids or [],
            experiment_ids=experiment_ids or [],
            observation_ids=observation_ids or [],
            key_findings=key_findings or [],
            implications=implications or [],
            recommendations=recommendations or [],
            confidence_level=confidence,
            supporting_evidence_count=supporting_count,
            contradicting_evidence_count=contradicting_count,
            author=author,
            tags=tags or [],
        )
        
        workspace.conclusions.append(conclusion)
        workspace.updated_at = datetime.now(timezone.utc)
        workspace.checksum = workspace.compute_checksum()
        self._save_workspaces()
        
        return conclusion
    
    # Dataset Attachments
    def attach_dataset(
        self,
        workspace_id: str,
        dataset_id: str,
        name: str,
        description: str = "",
        version: str = "1.0",
        attachment_type: str = "link",
        added_by: str = "",
    ) -> bool:
        """Attach a dataset to a workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return False
        
        attachment = DatasetAttachment(
            dataset_id=dataset_id,
            name=name,
            description=description,
            version=version,
            attachment_type=attachment_type,
            added_by=added_by,
        )
        
        workspace.attached_datasets.append(attachment)
        workspace.updated_at = datetime.now(timezone.utc)
        self._save_workspaces()
        
        return True
    
    # Visualization Management
    def add_visualization(
        self,
        workspace_id: str,
        title: str,
        chart_type: str,
        data_source: str = "",
        x_axis: str = "",
        y_axis: str = "",
        series: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[Visualization]:
        """Add a visualization to a workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        
        visualization = Visualization(
            id=str(uuid.uuid4()),
            title=title,
            chart_type=chart_type,
            data_source=data_source,
            x_axis=x_axis,
            y_axis=y_axis,
            series=series or [],
            config=config or {},
        )
        
        workspace.visualizations.append(visualization)
        workspace.updated_at = datetime.now(timezone.utc)
        self._save_workspaces()
        
        return visualization
    
    # Cell Management
    def add_cell(
        self,
        workspace_id: str,
        cell_type: CellType,
        content: str,
        order: Optional[int] = None,
    ) -> Optional[NotebookCell]:
        """Add a cell to a workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        
        if order is None:
            order = len(workspace.cells)
        
        cell = NotebookCell(
            id=str(uuid.uuid4()),
            cell_type=cell_type,
            content=content,
            order=order,
        )
        
        workspace.cells.insert(order, cell)
        
        # Reorder
        for i, c in enumerate(workspace.cells):
            c.order = i
        
        workspace.updated_at = datetime.now(timezone.utc)
        workspace.checksum = workspace.compute_checksum()
        self._save_workspaces()
        
        return cell
    
    def update_cell(
        self,
        workspace_id: str,
        cell_id: str,
        content: Optional[str] = None,
        outputs: Optional[List[str]] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> bool:
        """Update a cell"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return False
        
        for cell in workspace.cells:
            if cell.id == cell_id:
                if content is not None:
                    cell.content = content
                if outputs is not None:
                    cell.outputs = outputs
                if metrics is not None:
                    cell.metrics = metrics
                cell.updated_at = datetime.now(timezone.utc)
                cell.execution_count += 1
                cell.last_executed_at = datetime.now(timezone.utc)
                workspace.updated_at = datetime.now(timezone.utc)
                workspace.checksum = workspace.compute_checksum()
                self._save_workspaces()
                return True
        
        return False
    
    def execute_cell(
        self,
        workspace_id: str,
        cell_id: str,
        code: str,
        executor: Callable[[str], Tuple[str, List[str], Dict[str, float]]],
    ) -> bool:
        """Execute a code cell"""
        try:
            stdout, outputs, metrics = executor(code)
            return self.update_cell(
                workspace_id=workspace_id,
                cell_id=cell_id,
                outputs=outputs + [stdout] if stdout else outputs,
                metrics=metrics,
            )
        except Exception as e:
            logger.error(f"Cell execution error: {e}")
            return self.update_cell(
                workspace_id=workspace_id,
                cell_id=cell_id,
                outputs=[f"Error: {str(e)}"],
            )
    
    # Retrieval Methods
    def get_workspace(self, workspace_id: str) -> Optional[ResearchWorkspace]:
        """Get a workspace by ID"""
        return self._workspaces.get(workspace_id)
    
    def search_workspaces(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        strategy_id: Optional[str] = None,
        author: Optional[str] = None,
        hypothesis_status: Optional[HypothesisStatus] = None,
        limit: int = 50,
    ) -> List[ResearchWorkspace]:
        """Search workspaces"""
        results = list(self._workspaces.values())
        
        if query:
            query_lower = query.lower()
            results = [
                ws for ws in results
                if query_lower in ws.title.lower()
                or query_lower in ws.description.lower()
                or any(query_lower in c.content.lower() for c in ws.cells)
                or any(query_lower in h.title.lower() for h in ws.hypotheses)
            ]
        
        if tags:
            results = [ws for ws in results if any(t in ws.tags for t in tags)]
        
        if strategy_id:
            results = [ws for ws in results if ws.strategy_id == strategy_id]
        
        if author:
            results = [ws for ws in results if author.lower() in ws.author.lower()]
        
        if hypothesis_status:
            results = [
                ws for ws in results
                if any(h.status == hypothesis_status for h in ws.hypotheses)
            ]
        
        results.sort(key=lambda ws: ws.updated_at, reverse=True)
        return results[:limit]
    
    def get_hypothesis_summary(self, workspace_id: str) -> Dict[str, Any]:
        """Get hypothesis status summary"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return {}
        
        summary = {status.value: 0 for status in HypothesisStatus}
        for h in workspace.hypotheses:
            summary[h.status.value] += 1
        
        return {
            "total": len(workspace.hypotheses),
            "by_status": summary,
        }
    
    def export_workspace(self, workspace_id: str, format: str = "json") -> Optional[str]:
        """Export workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        
        if format == "json":
            return json.dumps(workspace.to_dict(), indent=2)
        
        elif format == "markdown":
            return self._export_as_markdown(workspace)
        
        return None
    
    def _export_as_markdown(self, workspace: ResearchWorkspace) -> str:
        """Export workspace as markdown"""
        lines = [f"# {workspace.title}\n"]
        lines.append(f"**Author:** {workspace.author}\n")
        lines.append(f"**Created:** {workspace.created_at.strftime('%Y-%m-%d')}\n")
        lines.append(f"**Tags:** {', '.join(workspace.tags)}\n")
        lines.append(f"\n{workspace.description}\n")
        
        if workspace.hypotheses:
            lines.append("\n## Hypotheses\n")
            for h in workspace.hypotheses:
                lines.append(f"### {h.title} [{h.status.value}]\n")
                lines.append(f"{h.description}\n")
                lines.append(f"- Independent: {', '.join(h.independent_variables)}\n")
                lines.append(f"- Dependent: {', '.join(h.dependent_variables)}\n")
        
        if workspace.observations:
            lines.append("\n## Observations\n")
            for o in workspace.observations:
                lines.append(f"### [{o.category}] {o.timestamp.strftime('%Y-%m-%d %H:%M')}\n")
                lines.append(f"{o.description}\n")
        
        if workspace.conclusions:
            lines.append("\n## Conclusions\n")
            for c in workspace.conclusions:
                lines.append(f"### {c.title} (Confidence: {c.confidence_level:.0f}%)\n")
                lines.append(f"{c.description}\n")
        
        lines.append("\n## Research Notes\n")
        for cell in workspace.cells:
            if cell.cell_type == CellType.MARKDOWN:
                lines.append(f"\n{cell.content}\n")
            elif cell.cell_type == CellType.CODE:
                lines.append(f"\n```python\n{cell.content}\n```\n")
        
        return "\n".join(lines)
    
    def duplicate_workspace(
        self,
        workspace_id: str,
        new_title: str,
        new_author: str,
    ) -> Optional[ResearchWorkspace]:
        """Duplicate a workspace"""
        original = self._workspaces.get(workspace_id)
        if not original:
            return None
        
        new_ws = ResearchWorkspace(
            id=str(uuid.uuid4()),
            title=new_title,
            author=new_author,
            description=original.description,
            strategy_id=original.strategy_id,
            strategy_version=original.strategy_version,
            tags=original.tags.copy(),
        )
        
        # Deep copy cells
        for cell in original.cells:
            new_cell = NotebookCell(
                id=str(uuid.uuid4()),
                cell_type=cell.cell_type,
                content=cell.content,
                order=cell.order,
            )
            new_ws.cells.append(new_cell)
        
        # Deep copy hypotheses (without experiment links)
        for h in original.hypotheses:
            new_h = Hypothesis(
                id=str(uuid.uuid4()),
                title=h.title,
                description=h.description,
                status=HypothesisStatus.DRAFT,
                independent_variables=h.independent_variables.copy(),
                dependent_variables=h.dependent_variables.copy(),
                author=new_author,
                tags=h.tags.copy(),
            )
            new_ws.hypotheses.append(new_h)
        
        new_ws.checksum = new_ws.compute_checksum()
        self._workspaces[new_ws.id] = new_ws
        self._save_workspaces()
        
        return new_ws


import os
