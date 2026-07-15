"""
Research Journal
================

Maintains comprehensive research records linking all components.
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


class JournalEntryType(Enum):
    """Types of journal entries"""
    HYPOTHESIS = "hypothesis"
    EXPERIMENT = "experiment"
    RESULT = "result"
    OBSERVATION = "observation"
    DECISION = "decision"
    NOTE = "note"


@dataclass
class JournalEntry:
    """A single journal entry"""
    id: str
    entry_type: JournalEntryType
    timestamp: datetime
    title: str
    content: str
    links: Dict[str, str]  # Links to other entries by type
    tags: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entry_type": self.entry_type.value,
            "timestamp": self.timestamp.isoformat(),
            "title": self.title,
            "content": self.content,
            "links": self.links,
            "tags": self.tags,
            "metadata": self.metadata
        }


class ResearchJournal:
    """
    Maintains comprehensive research journal with full traceability.
    """
    
    def __init__(self, db_path: str = "data/research_journal.db"):
        self.db_path = db_path
        self.entries: Dict[str, JournalEntry] = {}
        self._conn = None  # Shared connection for in-memory DB
        
        self._ensure_database()
    
    def _ensure_database(self) -> None:
        """Initialize journal database"""
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                id TEXT PRIMARY KEY,
                entry_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                title TEXT,
                content TEXT,
                links TEXT,
                tags TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entry_timestamp ON journal_entries(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entry_type ON journal_entries(entry_type)
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
    
    def log_hypothesis(
        self,
        hypothesis: Any,
        idea_id: str
    ) -> JournalEntry:
        """Log a new hypothesis"""
        entry = JournalEntry(
            id=str(uuid4()),
            entry_type=JournalEntryType.HYPOTHESIS,
            timestamp=datetime.now(),
            title=f"Hypothesis: {hypothesis.type.value if hasattr(hypothesis.type, 'value') else 'unknown'}",
            content=hypothesis.description,
            links={
                "idea_id": idea_id,
                "hypothesis_id": hypothesis.id
            },
            tags=[hypothesis.type.value if hasattr(hypothesis.type, 'value') else "unknown"],
            metadata={
                "variables": [v.__dict__ for v in hypothesis.variables] if hasattr(hypothesis, 'variables') else [],
                "confidence": hypothesis.confidence if hasattr(hypothesis, 'confidence') else 0,
                "rationale": hypothesis.rationale if hasattr(hypothesis, 'rationale') else ""
            }
        )
        
        self._store_entry(entry)
        self.entries[entry.id] = entry
        
        logger.info(f"Logged hypothesis: {entry.id}")
        return entry
    
    def log_experiment(
        self,
        idea_id: str,
        plan_id: str,
        result: Any,
        stats: Any,
        summary: Any
    ) -> JournalEntry:
        """Log experiment results"""
        # Get tags from result
        tags = []
        if result and hasattr(result, 'metrics'):
            if result.metrics.get('sharpe_ratio', 0) > 1:
                tags.append("high_sharpe")
            if result.metrics.get('total_return', 0) > 0:
                tags.append("profitable")
        
        if stats and hasattr(stats, 'is_significant'):
            if stats.is_significant:
                tags.append("significant")
            else:
                tags.append("not_significant")
        
        entry = JournalEntry(
            id=str(uuid4()),
            entry_type=JournalEntryType.RESULT,
            timestamp=datetime.now(),
            title=f"Experiment Result: {plan_id[:8]}",
            content=self._generate_result_summary(result, stats, summary),
            links={
                "idea_id": idea_id,
                "plan_id": plan_id,
                "experiment_id": result.id if result else "",
                "stats_id": stats.id if stats else ""
            },
            tags=tags,
            metadata={
                "metrics": result.metrics if result else {},
                "p_value": stats.p_value if stats else None,
                "conclusion": summary.main_conclusion.type.value if summary else None
            }
        )
        
        self._store_entry(entry)
        self.entries[entry.id] = entry
        
        logger.info(f"Logged experiment result: {entry.id}")
        return entry
    
    def log_observation(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        links: Optional[Dict[str, str]] = None
    ) -> JournalEntry:
        """Log a research observation"""
        entry = JournalEntry(
            id=str(uuid4()),
            entry_type=JournalEntryType.OBSERVATION,
            timestamp=datetime.now(),
            title=title,
            content=content,
            links=links or {},
            tags=tags or [],
            metadata={}
        )
        
        self._store_entry(entry)
        self.entries[entry.id] = entry
        
        return entry
    
    def log_decision(
        self,
        decision: str,
        reason: str,
        links: Optional[Dict[str, str]] = None
    ) -> JournalEntry:
        """Log a research decision"""
        entry = JournalEntry(
            id=str(uuid4()),
            entry_type=JournalEntryType.DECISION,
            timestamp=datetime.now(),
            title="Research Decision",
            content=f"{decision}\n\nReason: {reason}",
            links=links or {},
            tags=["decision"],
            metadata={"reason": reason}
        )
        
        self._store_entry(entry)
        self.entries[entry.id] = entry
        
        return entry
    
    def _store_entry(self, entry: JournalEntry) -> None:
        """Store entry in database"""
        self._ensure_database()  # Ensure table exists
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO journal_entries (
                id, entry_type, timestamp, title, content, links, tags, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id,
            entry.entry_type.value,
            entry.timestamp.isoformat(),
            entry.title,
            entry.content,
            json.dumps(entry.links),
            json.dumps(entry.tags),
            json.dumps(entry.metadata)
        ))
        
        conn.commit()
    
    def _generate_result_summary(
        self,
        result: Any,
        stats: Any,
        summary: Any
    ) -> str:
        """Generate result summary text"""
        parts = []
        
        if result:
            metrics = result.metrics
            parts.append(
                f"Total Return: {metrics.get('total_return', 0):.2%}\n"
                f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}\n"
                f"Max Drawdown: {metrics.get('max_drawdown', 0):.2%}\n"
                f"Win Rate: {metrics.get('win_rate', 0):.1%}\n"
                f"Trade Count: {metrics.get('trade_count', 0)}"
            )
        
        if stats:
            parts.append(
                f"\nStatistical Analysis:\n"
                f"P-value: {stats.p_value:.4f}\n"
                f"Effect Size: {stats.effect_size:.3f}\n"
                f"Significant: {stats.is_significant}"
            )
        
        if summary:
            parts.append(
                f"\nConclusion: {summary.main_conclusion.type.value}\n"
                f"{summary.main_conclusion.statement}"
            )
        
        return "\n".join(parts)
    
    def get_entries(
        self,
        entry_type: Optional[JournalEntryType] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[JournalEntry]:
        """Get journal entries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM journal_entries WHERE 1=1"
        params = []
        
        if entry_type:
            query += " AND entry_type = ?"
            params.append(entry_type.value)
        
        if since:
            query += " AND timestamp > ?"
            params.append(since.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        entries = []
        for row in rows:
            entry = JournalEntry(
                id=row[0],
                entry_type=JournalEntryType(row[1]),
                timestamp=datetime.fromisoformat(row[2]),
                title=row[3] or "",
                content=row[4] or "",
                links=json.loads(row[5]) if row[5] else {},
                tags=json.loads(row[6]) if row[6] else [],
                metadata=json.loads(row[7]) if row[7] else {}
            )
            entries.append(entry)
            self.entries[entry.id] = entry
        
        return entries
    
    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        """Get entry by ID"""
        if entry_id in self.entries:
            return self.entries[entry_id]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM journal_entries WHERE id = ?",
            (entry_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            entry = JournalEntry(
                id=row[0],
                entry_type=JournalEntryType(row[1]),
                timestamp=datetime.fromisoformat(row[2]),
                title=row[3] or "",
                content=row[4] or "",
                links=json.loads(row[5]) if row[5] else {},
                tags=json.loads(row[6]) if row[6] else [],
                metadata=json.loads(row[7]) if row[7] else {}
            )
            self.entries[entry.id] = entry
            return entry
        
        return None
    
    def get_trace(self, entry_id: str) -> List[JournalEntry]:
        """Get full trace of related entries"""
        entry = self.get_entry(entry_id)
        if not entry:
            return []
        
        trace = [entry]
        visited = {entry_id}
        
        # Follow links
        to_visit = list(entry.links.values())
        
        while to_visit:
            next_id = to_visit.pop(0)
            if next_id in visited:
                continue
            
            next_entry = self.get_entry(next_id)
            if next_entry:
                trace.append(next_entry)
                visited.add(next_id)
                to_visit.extend(next_entry.links.values())
        
        # Sort by timestamp
        trace.sort(key=lambda e: e.timestamp)
        
        return trace
    
    def search(
        self,
        query: str,
        entry_types: Optional[List[JournalEntryType]] = None,
        tags: Optional[List[str]] = None
    ) -> List[JournalEntry]:
        """Search journal entries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query_sql = "SELECT * FROM journal_entries WHERE 1=1"
        params = []
        
        if query:
            query_sql += " AND (title LIKE ? OR content LIKE ?)"
            search_term = f"%{query}%"
            params.extend([search_term, search_term])
        
        if entry_types:
            placeholders = ",".join("?" * len(entry_types))
            query_sql += f" AND entry_type IN ({placeholders})"
            params.extend([t.value for t in entry_types])
        
        query_sql += " ORDER BY timestamp DESC LIMIT 100"
        
        cursor.execute(query_sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        entries = []
        for row in rows:
            entry = JournalEntry(
                id=row[0],
                entry_type=JournalEntryType(row[1]),
                timestamp=datetime.fromisoformat(row[2]),
                title=row[3] or "",
                content=row[4] or "",
                links=json.loads(row[5]) if row[5] else {},
                tags=json.loads(row[6]) if row[6] else [],
                metadata=json.loads(row[7]) if row[7] else {}
            )
            
            # Filter by tags
            if tags and not any(t in entry.tags for t in tags):
                continue
            
            entries.append(entry)
        
        return entries
    
    def get_timeline(
        self,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get timeline of research activities"""
        entries = self.get_entries(since=since)
        
        timeline = []
        for entry in entries:
            timeline.append({
                "timestamp": entry.timestamp.isoformat(),
                "type": entry.entry_type.value,
                "title": entry.title,
                "content_preview": entry.content[:100] + "..." if len(entry.content) > 100 else entry.content,
                "tags": entry.tags
            })
        
        return timeline
