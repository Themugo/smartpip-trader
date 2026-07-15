"""
AI Research Notebook - Experiment Documentation

Notebook environment for documenting experiments and linking to strategies.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CellType(Enum):
    """Notebook cell types"""
    MARKDOWN = "markdown"
    CODE = "code"
    CHART = "chart"
    TABLE = "table"
    METRIC = "metric"
    TEXT = "text"


@dataclass
class NotebookCell:
    """A single cell in the notebook"""
    id: str
    cell_type: CellType
    content: str
    
    # For code cells
    outputs: List[str] = field(default_factory=list)
    
    # Metadata
    order: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cell_type": self.cell_type.value,
            "content": self.content,
            "outputs": self.outputs,
            "order": self.order,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ResearchNotebook:
    """AI Research Notebook"""
    id: str
    title: str
    strategy_id: Optional[str]
    strategy_version: Optional[str]
    experiment_id: Optional[str]
    
    # Cells
    cells: List[NotebookCell] = field(default_factory=list)
    
    # Metadata
    author: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "experiment_id": self.experiment_id,
            "cells": [c.to_dict() for c in self.cells],
            "author": self.author,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ResearchNotebookManager:
    """
    Research Notebook Manager for documenting experiments.
    
    Features:
    - Create notebooks linked to strategies/experiments
    - Add cells (markdown, code, charts, metrics)
    - Search notebooks
    - Export to various formats
    """
    
    def __init__(self, storage_path: str = "data/notebooks"):
        self._storage_path = storage_path
        self._notebooks: Dict[str, ResearchNotebook] = {}
        
        import os
        os.makedirs(storage_path, exist_ok=True)
        self._load_notebooks()
    
    def _load_notebooks(self) -> None:
        """Load notebooks from storage"""
        index_file = f"{self._storage_path}/index.json"
        
        try:
            with open(index_file, "r") as f:
                data = json.load(f)
            
            for nb_data in data.get("notebooks", []):
                nb_data["created_at"] = datetime.fromisoformat(nb_data["created_at"])
                nb_data["updated_at"] = datetime.fromisoformat(nb_data["updated_at"])
                
                for cell in nb_data.get("cells", []):
                    cell["created_at"] = datetime.fromisoformat(cell["created_at"])
                
                nb = ResearchNotebook(**nb_data)
                self._notebooks[nb.id] = nb
            
            logger.info(f"Loaded {len(self._notebooks)} notebooks")
        except Exception as e:
            logger.warning(f"Could not load notebooks: {e}")
    
    def _save_notebooks(self) -> None:
        """Save notebooks to storage"""
        index_file = f"{self._storage_path}/index.json"
        
        data = {
            "notebooks": [n.to_dict() for n in self._notebooks.values()],
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def create_notebook(
        self,
        title: str,
        author: str = "",
        strategy_id: Optional[str] = None,
        strategy_version: Optional[str] = None,
        experiment_id: Optional[str] = None,
    ) -> ResearchNotebook:
        """Create a new notebook"""
        notebook = ResearchNotebook(
            id=str(uuid.uuid4()),
            title=title,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            experiment_id=experiment_id,
            author=author,
        )
        
        # Add default template
        self._add_template(notebook)
        
        self._notebooks[notebook.id] = notebook
        self._save_notebooks()
        
        return notebook
    
    def _add_template(self, notebook: ResearchNotebook) -> None:
        """Add default template to new notebook"""
        template = [
            ("markdown", "# Research Notes\n\nAdd your hypotheses and observations here."),
            ("markdown", "## Strategy Information\n\n- Strategy: {strategy_id}\n- Version: {version}"),
            ("markdown", "## Hypothesis\n\nWhat are you testing?"),
            ("markdown", "## Methodology\n\nDescribe your approach."),
            ("code", "# Your analysis code here"),
            ("markdown", "## Results\n\nRecord your findings."),
            ("markdown", "## Conclusions\n\nWhat did you learn?"),
        ]
        
        for order, (cell_type, content) in enumerate(template):
            content = content.format(
                strategy_id=notebook.strategy_id or "N/A",
                version=notebook.strategy_version or "N/A",
            )
            
            cell = NotebookCell(
                id=str(uuid.uuid4()),
                cell_type=CellType(cell_type),
                content=content,
                order=order,
            )
            notebook.cells.append(cell)
    
    def add_cell(
        self,
        notebook_id: str,
        cell_type: CellType,
        content: str,
        order: Optional[int] = None,
    ) -> Optional[NotebookCell]:
        """Add a cell to a notebook"""
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            return None
        
        if order is None:
            order = len(notebook.cells)
        
        cell = NotebookCell(
            id=str(uuid.uuid4()),
            cell_type=cell_type,
            content=content,
            order=order,
        )
        
        notebook.cells.insert(order, cell)
        
        # Reorder
        for i, c in enumerate(notebook.cells):
            c.order = i
        
        notebook.updated_at = datetime.utcnow()
        self._save_notebooks()
        
        return cell
    
    def update_cell(
        self,
        notebook_id: str,
        cell_id: str,
        content: str,
    ) -> bool:
        """Update cell content"""
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            return False
        
        for cell in notebook.cells:
            if cell.id == cell_id:
                cell.content = content
                notebook.updated_at = datetime.utcnow()
                self._save_notebooks()
                return True
        
        return False
    
    def delete_cell(self, notebook_id: str, cell_id: str) -> bool:
        """Delete a cell"""
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            return False
        
        notebook.cells = [c for c in notebook.cells if c.id != cell_id]
        
        # Reorder
        for i, c in enumerate(notebook.cells):
            c.order = i
        
        notebook.updated_at = datetime.utcnow()
        self._save_notebooks()
        
        return True
    
    def get_notebook(self, notebook_id: str) -> Optional[ResearchNotebook]:
        """Get a notebook by ID"""
        return self._notebooks.get(notebook_id)
    
    def search_notebooks(
        self,
        query: Optional[str] = None,
        strategy_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[ResearchNotebook]:
        """Search notebooks"""
        results = list(self._notebooks.values())
        
        if query:
            query_lower = query.lower()
            results = [
                n for n in results
                if query_lower in n.title.lower()
                or any(query_lower in c.content.lower() for c in n.cells)
            ]
        
        if strategy_id:
            results = [n for n in results if n.strategy_id == strategy_id]
        
        if tags:
            results = [n for n in results if any(t in n.tags for t in tags)]
        
        results.sort(key=lambda n: n.updated_at, reverse=True)
        return results[:limit]
    
    def get_strategy_notebooks(self, strategy_id: str) -> List[ResearchNotebook]:
        """Get all notebooks for a strategy"""
        return self.search_notebooks(strategy_id=strategy_id)
    
    def export_notebook(self, notebook_id: str, format: str = "json") -> Optional[str]:
        """Export notebook to various formats"""
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            return None
        
        if format == "json":
            return json.dumps(notebook.to_dict(), indent=2)
        
        elif format == "markdown":
            lines = [f"# {notebook.title}\n"]
            
            for cell in notebook.cells:
                if cell.cell_type == CellType.MARKDOWN:
                    lines.append(cell.content)
                elif cell.cell_type == CellType.CODE:
                    lines.append(f"\n```python\n{cell.content}\n```\n")
                elif cell.cell_type == CellType.TEXT:
                    lines.append(f"\n{cell.content}\n")
            
            return "\n".join(lines)
        
        return None
