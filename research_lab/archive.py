"""
Research Archive
================

Archives completed research findings.
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

logger = logging.getLogger(__name__)


class ArchiveStatus(Enum):
    """Archive status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass
class ArchivedResearch:
    """An archived research item"""
    id: str
    idea_id: str
    hypothesis: Dict[str, Any]
    experiment_results: Dict[str, Any]
    statistical_results: Dict[str, Any]
    benchmark_results: Dict[str, Any]
    summary: Dict[str, Any]
    tags: List[str]
    status: ArchiveStatus
    archived_at: datetime
    searchable_text: str  # For full-text search
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "idea_id": self.idea_id,
            "hypothesis": self.hypothesis,
            "archived_at": self.archived_at.isoformat(),
            "tags": self.tags,
            "status": self.status.value
        }


class ResearchArchive:
    """
    Archives and retrieves completed research.
    """
    
    def __init__(self, db_path: str = "data/research_archive.db"):
        self.db_path = db_path
        self.archive: Dict[str, ArchivedResearch] = {}
        self._conn = None  # Shared connection for in-memory DB
        
        self._ensure_database()
    
    def _ensure_database(self) -> None:
        """Initialize archive database"""
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archived_research (
                id TEXT PRIMARY KEY,
                idea_id TEXT,
                hypothesis TEXT,
                experiment_results TEXT,
                statistical_results TEXT,
                benchmark_results TEXT,
                summary TEXT,
                tags TEXT,
                status TEXT,
                archived_at TEXT,
                searchable_text TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_archived_at ON archived_research(archived_at)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags ON archived_research(tags)
        """)
        
        conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        if self.db_path == ":memory:":
            if self._conn is None:
                self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            return self._conn
        else:
            return sqlite3.connect(self.db_path)
    
    def archive_research(self, idea: Any) -> ArchivedResearch:
        """
        Archive a research item.
        
        Args:
            idea: ResearchIdea object
            
        Returns:
            ArchivedResearch
        """
        archived = ArchivedResearch(
            id=str(uuid4()),
            idea_id=idea.id,
            hypothesis=idea.hypothesis.to_dict() if hasattr(idea.hypothesis, 'to_dict') else {},
            experiment_results={},
            statistical_results={},
            benchmark_results={},
            summary={
                "priority": idea.priority,
                "novelty": idea.novelty_score,
                "feasibility": idea.feasibility_score,
                "potential_impact": idea.potential_impact,
                "final_status": idea.status
            },
            tags=self._generate_tags(idea),
            status=ArchiveStatus.ARCHIVED,
            archived_at=datetime.now(),
            searchable_text=self._generate_searchable_text(idea)
        )
        
        # Store in memory
        self.archive[archived.id] = archived
        
        # Store in database
        self._store_archived(archived)
        
        logger.info(f"Archived research: {idea.id}")
        
        return archived
    
    def _generate_tags(self, idea: Any) -> List[str]:
        """Generate tags for research"""
        tags = []
        
        # Type tags
        if hasattr(idea.hypothesis, 'type'):
            htype = idea.hypothesis.type.value if hasattr(idea.hypothesis.type, 'value') else str(idea.hypothesis.type)
            tags.append(htype)
        
        # Priority tags
        if idea.priority > 0.7:
            tags.append("high_priority")
        elif idea.priority > 0.4:
            tags.append("medium_priority")
        else:
            tags.append("low_priority")
        
        # Status tags
        tags.append(idea.status)
        
        # Result tags
        if idea.status == "completed":
            tags.append("tested")
        if idea.novelty_score > 0.7:
            tags.append("novel")
        
        return tags
    
    def _generate_searchable_text(self, idea: Any) -> str:
        """Generate searchable text for full-text search"""
        parts = [
            idea.hypothesis.description if hasattr(idea.hypothesis, 'description') else "",
            idea.hypothesis.rationale if hasattr(idea.hypothesis, 'rationale') else ""
        ]
        
        # Add variable descriptions
        if hasattr(idea.hypothesis, 'variables'):
            for var in idea.hypothesis.variables:
                parts.append(var.description)
        
        return " ".join(parts)
    
    def _store_archived(self, archived: ArchivedResearch) -> None:
        """Store archived research in database"""
        self._ensure_database()  # Ensure table exists
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO archived_research (
                id, idea_id, hypothesis, experiment_results, statistical_results,
                benchmark_results, summary, tags, status, archived_at, searchable_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            archived.id,
            archived.idea_id,
            json.dumps(archived.hypothesis),
            json.dumps(archived.experiment_results),
            json.dumps(archived.statistical_results),
            json.dumps(archived.benchmark_results),
            json.dumps(archived.summary),
            json.dumps(archived.tags),
            archived.status.value,
            archived.archived_at.isoformat(),
            archived.searchable_text
        ))
        
        conn.commit()
    
    def search(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ArchivedResearch]:
        """
        Search archived research.
        
        Args:
            query: Text search query
            tags: Filter by tags
            since: Only return items archived after this date
            limit: Maximum results
            
        Returns:
            List of archived research items
        """
        results = list(self.archive.values())
        
        # Filter by tags
        if tags:
            results = [r for r in results if any(t in r.tags for t in tags)]
        
        # Filter by date
        if since:
            results = [r for r in results if r.archived_at >= since]
        
        # Sort by archived date (newest first)
        results.sort(key=lambda x: x.archived_at, reverse=True)
        
        # Limit results
        return results[:limit]
    
    def get_by_id(self, archive_id: str) -> Optional[ArchivedResearch]:
        """Get archived research by ID"""
        return self.archive.get(archive_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get archive statistics"""
        if not self.archive:
            return {
                "total_archived": 0,
                "by_status": {},
                "by_tags": {},
                "date_range": None
            }
        
        # Count by status
        by_status = {}
        for r in self.archive.values():
            status = r.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        # Count by tags
        by_tags = {}
        for r in self.archive.values():
            for tag in r.tags:
                by_tags[tag] = by_tags.get(tag, 0) + 1
        
        # Date range
        dates = [r.archived_at for r in self.archive.values()]
        
        return {
            "total_archived": len(self.archive),
            "by_status": by_status,
            "by_tags": by_tags,
            "date_range": {
                "oldest": min(dates).isoformat() if dates else None,
                "newest": max(dates).isoformat() if dates else None
            }
        }
    
    def get_recent(self, n: int = 10) -> List[ArchivedResearch]:
        """Get n most recent archived items"""
        sorted_items = sorted(
            self.archive.values(),
            key=lambda x: x.archived_at,
            reverse=True
        )
        return sorted_items[:n]
    
    def get_by_tag(self, tag: str) -> List[ArchivedResearch]:
        """Get all archived items with a specific tag"""
        return [r for r in self.archive.values() if tag in r.tags]
    
    def delete(self, archive_id: str) -> bool:
        """Delete an archived item"""
        if archive_id in self.archive:
            self.archive[archive_id].status = ArchiveStatus.DELETED
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE archived_research SET status = ? WHERE id = ?",
                (ArchiveStatus.DELETED.value, archive_id)
            )
            conn.commit()
            conn.close()
            
            return True
        return False
    
    def cleanup_old(self, days: int = 90) -> int:
        """Remove archived items older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        to_remove = [
            archive_id for archive_id, r in self.archive.items()
            if r.archived_at < cutoff
        ]
        
        for archive_id in to_remove:
            del self.archive[archive_id]
        
        if to_remove:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM archived_research WHERE archived_at < ?",
                (cutoff.isoformat(),)
            )
            conn.commit()
            conn.close()
        
        logger.info(f"Cleaned up {len(to_remove)} old archived items")
        return len(to_remove)
