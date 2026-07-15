"""
Data Managers
============

Historical data and tick dataset management with versioning.
"""

import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Tuple
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


class DatasetType(Enum):
    """Types of datasets"""
    TICK = "tick"
    OHLCV = "ohlcv"
    ORDERBOOK = "orderbook"
    FUNDAMENTAL = "fundamental"


@dataclass
class DatasetVersion:
    """Version information for a dataset"""
    version_id: str
    created_at: datetime
    dataset_type: DatasetType
    symbol: str
    start_date: datetime
    end_date: datetime
    tick_count: int
    checksum: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "created_at": self.created_at.isoformat(),
            "dataset_type": self.dataset_type.value,
            "symbol": self.symbol,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "tick_count": self.tick_count,
            "checksum": self.checksum,
            "metadata": self.metadata
        }


@dataclass
class Tick:
    """Single tick of market data"""
    timestamp: datetime
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    volume: float
    
    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2
    
    @property
    def spread(self) -> float:
        return self.ask - self.bid
    
    @property
    def spread_pips(self) -> float:
        return self.spread * 10000


@dataclass
class OHLCV:
    """OHLCV bar data"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @property
    def range(self) -> float:
        return self.high - self.low


class TickDatasetManager:
    """
    Memory-efficient tick dataset manager.
    
    Supports streaming through large datasets.
    """
    
    def __init__(
        self,
        db_path: str = "data/backtest/ticks.db",
        cache_size: int = 10000
    ):
        self.db_path = db_path
        self.cache_size = cache_size
        self._ensure_database()
    
    def _ensure_database(self) -> None:
        """Initialize database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                bid REAL,
                ask REAL,
                bid_size INTEGER,
                ask_size INTEGER,
                volume REAL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_time ON ticks(symbol, timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def store_ticks(
        self,
        symbol: str,
        ticks: List[Tick]
    ) -> str:
        """Store ticks and return version ID"""
        version_id = str(uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate checksum
        tick_data = "".join(f"{t.bid}{t.ask}{t.volume}" for t in ticks)
        checksum = hashlib.sha256(tick_data.encode()).hexdigest()[:16]
        
        # Insert ticks
        for tick in ticks:
            cursor.execute("""
                INSERT INTO ticks (symbol, timestamp, bid, ask, bid_size, ask_size, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                tick.timestamp.isoformat(),
                tick.bid,
                tick.ask,
                tick.bid_size,
                tick.ask_size,
                tick.volume
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Stored {len(ticks)} ticks for {symbol}")
        
        return version_id
    
    def load_ticks(
        self,
        symbol: str,
        start: datetime,
        end: datetime
    ) -> List[Tick]:
        """Load ticks for a time range"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, bid, ask, bid_size, ask_size, volume
            FROM ticks
            WHERE symbol = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
        """, (symbol, start.isoformat(), end.isoformat()))
        
        ticks = []
        for row in cursor.fetchall():
            ticks.append(Tick(
                timestamp=datetime.fromisoformat(row[0]),
                bid=row[1],
                ask=row[2],
                bid_size=row[3],
                ask_size=row[4],
                volume=row[5]
            ))
        
        conn.close()
        
        return ticks
    
    def stream_ticks(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        chunk_size: int = 1000
    ) -> Iterator[List[Tick]]:
        """Stream ticks in chunks for memory efficiency"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, bid, ask, bid_size, ask_size, volume
            FROM ticks
            WHERE symbol = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
        """, (symbol, start.isoformat(), end.isoformat()))
        
        chunk = []
        for row in cursor:
            chunk.append(Tick(
                timestamp=datetime.fromisoformat(row[0]),
                bid=row[1],
                ask=row[2],
                bid_size=row[3],
                ask_size=row[4],
                volume=row[5]
            ))
            
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        
        if chunk:
            yield chunk
        
        conn.close()
    
    def get_time_range(
        self,
        symbol: str
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get available time range for symbol"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT MIN(timestamp), MAX(timestamp)
            FROM ticks
            WHERE symbol = ?
        """, (symbol,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return datetime.fromisoformat(row[0]), datetime.fromisoformat(row[1])
        return None, None


class HistoricalDataManager:
    """
    Historical data manager with versioning and validation.
    
    Manages multiple datasets, versions, and ensures data integrity.
    """
    
    def __init__(
        self,
        db_path: str = "data/backtest/historical.db"
    ):
        self.db_path = db_path
        self.tick_manager = TickDatasetManager()
        self._ensure_database()
    
    def _ensure_database(self) -> None:
        """Initialize database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                version_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                dataset_type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                tick_count INTEGER,
                checksum TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS train_test_splits (
                split_id TEXT PRIMARY KEY,
                version_id TEXT,
                train_start TEXT,
                train_end TEXT,
                test_start TEXT,
                test_end TEXT,
                split_ratio REAL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_version(
        self,
        symbol: str,
        dataset_type: DatasetType,
        ticks: List[Tick],
        metadata: Dict[str, Any] = None
    ) -> DatasetVersion:
        """Create a new dataset version"""
        version_id = str(uuid4())
        
        # Store ticks
        self.tick_manager.store_ticks(symbol, ticks)
        
        # Calculate metadata
        start_date = ticks[0].timestamp if ticks else datetime.now()
        end_date = ticks[-1].timestamp if ticks else datetime.now()
        
        tick_data = "".join(f"{t.bid}{t.ask}{t.volume}" for t in ticks)
        checksum = hashlib.sha256(tick_data.encode()).hexdigest()
        
        version = DatasetVersion(
            version_id=version_id,
            created_at=datetime.now(),
            dataset_type=dataset_type,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            tick_count=len(ticks),
            checksum=checksum,
            metadata=metadata or {}
        )
        
        # Store version
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO datasets (
                version_id, created_at, dataset_type, symbol,
                start_date, end_date, tick_count, checksum, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            version.version_id,
            version.created_at.isoformat(),
            version.dataset_type.value,
            version.symbol,
            version.start_date.isoformat(),
            version.end_date.isoformat(),
            version.tick_count,
            version.checksum,
            json.dumps(version.metadata)
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created dataset version: {version_id}")
        
        return version
    
    def get_version(
        self,
        version_id: str
    ) -> Optional[DatasetVersion]:
        """Get a specific version"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM datasets WHERE version_id = ?
        """, (version_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return DatasetVersion(
                version_id=row[0],
                created_at=datetime.fromisoformat(row[1]),
                dataset_type=DatasetType(row[2]),
                symbol=row[3],
                start_date=datetime.fromisoformat(row[4]),
                end_date=datetime.fromisoformat(row[5]),
                tick_count=row[6],
                checksum=row[7],
                metadata=json.loads(row[8]) if row[8] else {}
            )
        
        return None
    
    def list_versions(
        self,
        symbol: Optional[str] = None
    ) -> List[DatasetVersion]:
        """List all versions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute("""
                SELECT * FROM datasets WHERE symbol = ? ORDER BY created_at DESC
            """, (symbol,))
        else:
            cursor.execute("SELECT * FROM datasets ORDER BY created_at DESC")
        
        versions = []
        for row in cursor.fetchall():
            versions.append(DatasetVersion(
                version_id=row[0],
                created_at=datetime.fromisoformat(row[1]),
                dataset_type=DatasetType(row[2]),
                symbol=row[3],
                start_date=datetime.fromisoformat(row[4]),
                end_date=datetime.fromisoformat(row[5]),
                tick_count=row[6],
                checksum=row[7],
                metadata=json.loads(row[8]) if row[8] else {}
            ))
        
        conn.close()
        return versions
    
    def create_train_test_split(
        self,
        version_id: str,
        train_ratio: float = 0.7
    ) -> Dict[str, datetime]:
        """Create train/test split from version"""
        version = self.get_version(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")
        
        total_days = (version.end_date - version.start_date).days
        train_end = version.start_date + timedelta(days=int(total_days * train_ratio))
        test_start = train_end
        
        split_id = str(uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO train_test_splits (
                split_id, version_id, train_start, train_end,
                test_start, test_end, split_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            split_id,
            version_id,
            version.start_date.isoformat(),
            train_end.isoformat(),
            test_start.isoformat(),
            version.end_date.isoformat(),
            train_ratio
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "split_id": split_id,
            "train_start": version.start_date,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": version.end_date
        }
    
    def load_data_for_version(
        self,
        version_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> List[Tick]:
        """Load data for a version"""
        version = self.get_version(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")
        
        start = start or version.start_date
        end = end or version.end_date
        
        return self.tick_manager.load_ticks(version.symbol, start, end)
    
    def verify_integrity(
        self,
        version_id: str
    ) -> Dict[str, Any]:
        """Verify dataset integrity"""
        version = self.get_version(version_id)
        if not version:
            return {"valid": False, "reason": "Version not found"}
        
        ticks = self.tick_manager.load_ticks(
            version.symbol,
            version.start_date,
            version.end_date
        )
        
        # Verify count
        if len(ticks) != version.tick_count:
            return {
                "valid": False,
                "reason": "Tick count mismatch",
                "expected": version.tick_count,
                "actual": len(ticks)
            }
        
        # Verify checksum
        tick_data = "".join(f"{t.bid}{t.ask}{t.volume}" for t in ticks)
        checksum = hashlib.sha256(tick_data.encode()).hexdigest()
        
        if checksum != version.checksum:
            return {
                "valid": False,
                "reason": "Checksum mismatch"
            }
        
        return {"valid": True, "tick_count": len(ticks)}
