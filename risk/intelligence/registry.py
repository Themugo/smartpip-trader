"""
Risk Registry
=============

Central registry for risk events, metrics, and state.
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


class EventSeverity(Enum):
    """Event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RiskRegistry:
    """
    Central registry for risk management data.
    """
    
    def __init__(self, db_path: str = "data/risk_registry.db"):
        self.db_path = db_path
        
        # Ensure database
        self._ensure_database()
        
        # In-memory cache
        self._metrics_cache: Dict[str, Any] = {}
        self._events_cache: List[Dict[str, Any]] = []
    
    def _ensure_database(self) -> None:
        """Initialize database tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL,
                metadata TEXT
            )
        """)
        
        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT,
                data TEXT
            )
        """)
        
        # State table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def record_metric(
        self,
        metric_type: str,
        value: float,
        metadata: Optional[Dict] = None
    ) -> None:
        """Record a metric value"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO metrics (id, timestamp, metric_type, value, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(uuid4()),
            datetime.now().isoformat(),
            metric_type,
            value,
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
        conn.close()
        
        # Update cache
        self._metrics_cache[metric_type] = {
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
    
    def record_event(
        self,
        event_type: str,
        severity: EventSeverity,
        message: str,
        data: Optional[Dict] = None
    ) -> None:
        """Record a risk event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO events (id, timestamp, event_type, severity, message, data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid4()),
            datetime.now().isoformat(),
            event_type,
            severity.value,
            message,
            json.dumps(data) if data else None
        ))
        
        conn.commit()
        conn.close()
        
        # Update cache
        self._events_cache.append({
            "type": event_type,
            "severity": severity.value,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Trim cache
        if len(self._events_cache) > 100:
            self._events_cache = self._events_cache[-100:]
    
    def set_state(self, key: str, value: Any) -> None:
        """Set a state value"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO state (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, json.dumps(value), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_state(self, key: str) -> Optional[Any]:
        """Get a state value"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM state WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    
    def get_metrics(
        self,
        metric_type: str,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get metrics of a specific type"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if since:
            cursor.execute("""
                SELECT id, timestamp, value, metadata FROM metrics
                WHERE metric_type = ? AND timestamp > ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (metric_type, since.isoformat(), limit))
        else:
            cursor.execute("""
                SELECT id, timestamp, value, metadata FROM metrics
                WHERE metric_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (metric_type, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": row[0],
                "timestamp": row[1],
                "value": row[2],
                "metadata": json.loads(row[3]) if row[3] else None
            }
            for row in rows
        ]
    
    def get_events(
        self,
        since: Optional[datetime] = None,
        severity: Optional[EventSeverity] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get events with optional filtering"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT id, timestamp, event_type, severity, message, data FROM events WHERE 1=1"
        params = []
        
        if since:
            query += " AND timestamp > ?"
            params.append(since.isoformat())
        
        if severity:
            query += " AND severity = ?"
            params.append(severity.value)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": row[0],
                "timestamp": row[1],
                "event_type": row[2],
                "severity": row[3],
                "message": row[4],
                "data": json.loads(row[5]) if row[5] else None
            }
            for row in rows
        ]
    
    def get_recent_events(
        self,
        hours: int = 24,
        min_severity: Optional[EventSeverity] = None
    ) -> List[Dict[str, Any]]:
        """Get recent events within time window"""
        since = datetime.now() - timedelta(hours=hours)
        
        severity_order = {
            EventSeverity.INFO: 1,
            EventSeverity.WARNING: 2,
            EventSeverity.ERROR: 3,
            EventSeverity.CRITICAL: 4
        }
        
        events = self.get_events(since=since, limit=1000)
        
        if min_severity:
            min_level = severity_order.get(min_severity, 1)
            events = [
                e for e in events
                if severity_order.get(EventSeverity(e["severity"]), 0) >= min_level
            ]
        
        return events
    
    def get_event_summary(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get summary of events in time window"""
        events = self.get_recent_events(hours=hours)
        
        severity_counts = {}
        for event in events:
            severity = event["severity"]
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "total_events": len(events),
            "by_severity": severity_counts,
            "time_window_hours": hours,
            "oldest_event": events[-1]["timestamp"] if events else None,
            "newest_event": events[0]["timestamp"] if events else None
        }
    
    def clear_old_events(self, days: int = 30) -> int:
        """Clear events older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM events WHERE timestamp < ?",
            (cutoff.isoformat(),)
        )
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Cleared {deleted} old events")
        return deleted
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current system state summary"""
        # Get recent critical events
        critical_events = self.get_recent_events(hours=24, min_severity=EventSeverity.ERROR)
        
        # Get recent metrics
        risk_scores = self.get_metrics("risk_score", limit=10)
        
        return {
            "critical_events_24h": len(critical_events),
            "risk_score_trend": [m["value"] for m in risk_scores] if risk_scores else [],
            "registry_status": "OK"
        }
