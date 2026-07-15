"""
Immutable Audit Log
==================

Tamper-evident, hash-chained audit logs.
"""

import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class LogEntryType(Enum):
    """Types of log entries"""
    AUDIT_RECORD = "audit_record"
    CONFIG_CHANGE = "config_change"
    DEPLOYMENT = "deployment"
    MODEL_TRAINING = "model_training"
    APPROVAL = "approval"
    SYSTEM_EVENT = "system_event"
    SECURITY_EVENT = "security_event"
    USER_ACTION = "user_action"


class LogIntegrityError(Exception):
    """Raised when log integrity is compromised"""
    pass


@dataclass
class LogEntry:
    """A single immutable log entry"""
    entry_id: str
    timestamp: datetime
    entry_type: LogEntryType
    data: Dict[str, Any]
    hash: str
    previous_hash: str
    signature: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "entry_type": self.entry_type.value,
            "data": self.data,
            "hash": self.hash,
            "previous_hash": self.previous_hash,
            "signature": self.signature
        }


class ImmutableAuditLog:
    """
    Immutable, hash-chained audit log.
    
    Features:
    - Hash chaining for tamper evidence
    - Merkle tree verification
    - Digital signatures (optional)
    - Append-only (no delete/update)
    - Full audit trail
    """
    
    def __init__(
        self,
        db_path: str = "data/governance/immutable_log.db",
        genesis_hash: str = "GENESIS"
    ):
        self.db_path = db_path
        self.genesis_hash = genesis_hash
        self._last_hash = genesis_hash
        
        self._ensure_database()
        self._initialize_genesis()
    
    def _ensure_database(self) -> None:
        """Initialize database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS log_entries (
                entry_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                data TEXT NOT NULL,
                hash TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                signature TEXT,
                merkle_proof TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON log_entries(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entry_type ON log_entries(entry_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hash ON log_entries(hash)
        """)
        
        conn.commit()
        conn.close()
    
    def _initialize_genesis(self) -> None:
        """Initialize genesis block if needed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM log_entries")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Create genesis entry
            genesis_data = {
                "message": "Genesis block",
                "initialized_at": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            entry = LogEntry(
                entry_id="GENESIS",
                timestamp=datetime.now(),
                entry_type=LogEntryType.SYSTEM_EVENT,
                data=genesis_data,
                hash=self.genesis_hash,
                previous_hash="NONE"
            )
            
            self._store_entry(entry)
            self._last_hash = self.genesis_hash
        
        # Get last hash
        cursor.execute(
            "SELECT hash FROM log_entries ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            self._last_hash = row[0]
        
        conn.close()
    
    def append(
        self,
        entry_type: LogEntryType,
        data: Dict[str, Any],
        signature: Optional[str] = None
    ) -> LogEntry:
        """
        Append a new entry to the log.
        
        Args:
            entry_type: Type of entry
            data: Entry data
            signature: Optional digital signature
            
        Returns:
            Created LogEntry
        """
        entry_id = str(uuid4())
        timestamp = datetime.now()
        
        # Create entry
        entry = LogEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            entry_type=entry_type,
            data=data,
            hash="",  # Will be calculated
            previous_hash=self._last_hash,
            signature=signature
        )
        
        # Calculate hash
        entry.hash = self._calculate_hash(entry)
        
        # Store
        self._store_entry(entry)
        
        # Update last hash
        self._last_hash = entry.hash
        
        logger.info(f"Appended log entry: {entry_id} type={entry_type.value}")
        
        return entry
    
    def _calculate_hash(self, entry: LogEntry) -> str:
        """Calculate hash for entry"""
        # Create deterministic representation
        hash_input = {
            "entry_id": entry.entry_id,
            "timestamp": entry.timestamp.isoformat(),
            "entry_type": entry.entry_type.value,
            "data": entry.data,
            "previous_hash": entry.previous_hash
        }
        
        # Create hash
        hash_str = json.dumps(hash_input, sort_keys=True)
        return hashlib.sha256(hash_str.encode()).hexdigest()
    
    def _store_entry(self, entry: LogEntry) -> None:
        """Store entry in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO log_entries (
                entry_id, timestamp, entry_type, data,
                hash, previous_hash, signature
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.entry_id,
            entry.timestamp.isoformat(),
            entry.entry_type.value,
            json.dumps(entry.data),
            entry.hash,
            entry.previous_hash,
            entry.signature
        ))
        
        conn.commit()
        conn.close()
    
    def verify_integrity(self) -> Dict[str, Any]:
        """
        Verify the integrity of the entire log.
        
        Returns:
            Verification result with details
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT entry_id, timestamp, entry_type, data, hash, previous_hash "
            "FROM log_entries ORDER BY timestamp"
        )
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {"valid": True, "entries": 0, "message": "Empty log"}
        
        # Verify chain
        valid = True
        broken_at = None
        verified_entries = 0
        
        for i, row in enumerate(rows):
            entry_id, timestamp, entry_type, data, current_hash, previous_hash = row
            
            # Verify hash
            expected_data = json.loads(data)
            temp_entry = LogEntry(
                entry_id=entry_id,
                timestamp=datetime.fromisoformat(timestamp),
                entry_type=LogEntryType(entry_type),
                data=expected_data,
                hash="",  # Will be recalculated
                previous_hash=previous_hash
            )
            expected_hash = self._calculate_hash(temp_entry)
            
            if current_hash != expected_hash:
                valid = False
                broken_at = i
                break
            
            # Verify chain linkage
            if i > 0:
                expected_prev = rows[i-1][4]  # hash of previous
                if previous_hash != expected_prev:
                    valid = False
                    broken_at = i
                    break
            
            verified_entries += 1
        
        return {
            "valid": valid,
            "entries": len(rows),
            "verified": verified_entries,
            "broken_at": broken_at,
            "first_hash": rows[0][4] if rows else None,
            "last_hash": rows[-1][4] if rows else None,
            "timestamp_range": {
                "first": rows[0][1] if rows else None,
                "last": rows[-1][1] if rows else None
            }
        }
    
    def get_entry(self, entry_id: str) -> Optional[LogEntry]:
        """Get entry by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT entry_id, timestamp, entry_type, data, hash, previous_hash, signature "
            "FROM log_entries WHERE entry_id = ?",
            (entry_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_entry(row)
        return None
    
    def get_entries(
        self,
        entry_type: Optional[LogEntryType] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100
    ) -> List[LogEntry]:
        """Get entries with filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM log_entries WHERE 1=1"
        params = []
        
        if entry_type:
            query += " AND entry_type = ?"
            params.append(entry_type.value)
        
        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())
        
        if until:
            query += " AND timestamp <= ?"
            params.append(until.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_entry(row) for row in rows]
    
    def _row_to_entry(self, row: tuple) -> LogEntry:
        """Convert database row to LogEntry"""
        return LogEntry(
            entry_id=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            entry_type=LogEntryType(row[2]),
            data=json.loads(row[3]),
            hash=row[4],
            previous_hash=row[5],
            signature=row[6]
        )
    
    def get_proof(
        self,
        entry_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get proof of entry existence in log.
        
        Returns Merkle proof for the entry.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT hash FROM log_entries ORDER BY timestamp"
        )
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return None
        
        hashes = [row[0] for row in rows]
        
        try:
            index = next(i for i, h in enumerate(hashes) 
                        if self.get_entry(entry_id) and self.get_entry(entry_id).hash == h)
        except StopIteration:
            return None
        
        # Build Merkle proof
        proof = self._build_merkle_proof(hashes, index)
        
        return {
            "entry_id": entry_id,
            "entry_hash": hashes[index],
            "merkle_root": proof["root"],
            "proof": proof["path"]
        }
    
    def _build_merkle_proof(
        self,
        hashes: List[str],
        index: int
    ) -> Dict[str, Any]:
        """Build Merkle proof for a hash at index"""
        if len(hashes) == 1:
            return {"root": hashes[0], "path": []}
        
        # Build tree bottom-up
        current_level = hashes.copy()
        proof = []
        
        while len(current_level) > 1:
            if len(current_level) % 2 == 1:
                current_level.append(current_level[-1])
            
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1]
                
                # Hash pair
                combined = hashlib.sha256(
                    (left + right).encode()
                ).hexdigest()
                next_level.append(combined)
                
                # Add to proof if our index is in this pair
                if i // 2 == index // 2 and index % 2 == 0:
                    proof.append({"position": "right", "hash": right})
                elif i // 2 == (index - 1) // 2 and index % 2 == 1:
                    proof.append({"position": "left", "hash": left})
            
            current_level = next_level
            index = index // 2
        
        return {"root": current_level[0], "path": proof}
    
    def export_log(self, format: str = "json") -> str:
        """Export entire log for backup/audit"""
        entries = self.get_entries(limit=100000)
        
        if format == "json":
            return json.dumps([e.to_dict() for e in entries], indent=2)
        else:
            lines = []
            for e in entries:
                lines.append(f"{e.timestamp.isoformat()} | {e.entry_type.value} | {e.hash}")
            return "\n".join(lines)
