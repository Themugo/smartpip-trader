"""
Deterministic Replay Engine
==========================

Ensures identical inputs produce identical outputs.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class DeterministicState:
    """State snapshot for deterministic replay"""
    snapshot_id: str
    timestamp: datetime
    sequence: int
    state_hash: str
    events_hash: str
    inputs_hash: str
    output_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class DeterministicEngine:
    """
    Ensures deterministic replay where identical inputs always produce identical outputs.
    
    Features:
    - Input hashing
    - Output verification
    - State snapshots
    - Determinism verification
    """
    
    def __init__(self):
        self.state_snapshots: List[DeterministicState] = []
        self.input_hashes: Dict[str, str] = {}  # event_id -> hash
        self.output_hashes: Dict[str, str] = {}  # event_id -> hash
        self.determinism_failures: List[Dict[str, Any]] = []
        
        # Verification state
        self._verification_enabled = True
        self._baseline_hashes: Optional[Dict[str, str]] = None
    
    def compute_event_hash(self, event: Any) -> str:
        """
        Compute deterministic hash for an event.
        
        This hash must be identical for identical events across replays.
        """
        # Extract deterministic components
        hash_input = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "sequence": event.sequence,
            "data": event.data
        }
        
        # Create deterministic JSON
        import json
        hash_str = json.dumps(hash_input, sort_keys=True, default=str)
        
        # Compute SHA-256
        return hashlib.sha256(hash_str.encode()).hexdigest()
    
    def compute_state_hash(self, state: Dict[str, Any]) -> str:
        """
        Compute deterministic hash for state.
        
        Args:
            state: State dictionary
            
        Returns:
            SHA-256 hash
        """
        import json
        
        # Sort keys for determinism
        state_str = json.dumps(state, sort_keys=True, default=str)
        return hashlib.sha256(state_str.encode()).hexdigest()
    
    def record_event(self, event: Any, output: Any = None) -> str:
        """
        Record event and compute hash.
        
        Args:
            event: Replay event
            output: Optional output generated from event
            
        Returns:
            Event hash
        """
        event_hash = self.compute_event_hash(event)
        self.input_hashes[event.event_id] = event_hash
        
        if output is not None:
            # Compute output hash
            output_hash = self.compute_state_hash({"output": output})
            self.output_hashes[event.event_id] = output_hash
        
        return event_hash
    
    def take_snapshot(
        self,
        timestamp: datetime,
        sequence: int,
        state: Dict[str, Any],
        events: List[Any],
        inputs: Dict[str, Any] = None
    ) -> DeterministicState:
        """
        Take a state snapshot.
        
        Args:
            timestamp: Snapshot timestamp
            sequence: Event sequence number
            state: Current state
            events: Events leading to this state
            inputs: Input parameters
            
        Returns:
            DeterministicState snapshot
        """
        # Compute state hash
        state_hash = self.compute_state_hash(state)
        
        # Compute events hash
        events_hash = self._compute_sequence_hash(events)
        
        # Compute inputs hash
        inputs_hash = ""
        if inputs:
            inputs_hash = self.compute_state_hash(inputs)
        
        # Compute output hash (state after processing)
        output_hash = state_hash  # State is the output
        
        snapshot = DeterministicState(
            snapshot_id=str(uuid4()),
            timestamp=timestamp,
            sequence=sequence,
            state_hash=state_hash,
            events_hash=events_hash,
            inputs_hash=inputs_hash,
            output_hash=output_hash,
            metadata={
                "event_count": len(events),
                "state_keys": list(state.keys())
            }
        )
        
        self.state_snapshots.append(snapshot)
        logger.debug(f"Snapshot {snapshot.snapshot_id}: seq={sequence}")
        
        return snapshot
    
    def _compute_sequence_hash(self, events: List[Any]) -> str:
        """Compute hash for a sequence of events"""
        hashes = [self.compute_event_hash(e) for e in events]
        combined = "".join(hashes)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def verify_determinism(
        self,
        events: List[Any],
        outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify that replay is deterministic.
        
        Args:
            events: List of events
            outputs: Dict mapping event_id -> output
            
        Returns:
            Verification result
        """
        if not self._verification_enabled:
            return {"verified": True, "message": "Verification disabled"}
        
        failures = []
        
        # Verify event hashes
        for event in events:
            hash1 = self.compute_event_hash(event)
            hash2 = self.input_hashes.get(event.event_id)
            
            if hash2 and hash1 != hash2:
                failures.append({
                    "type": "event_hash_mismatch",
                    "event_id": event.event_id,
                    "expected": hash2,
                    "actual": hash1
                })
        
        # Verify output determinism
        if self._baseline_hashes:
            for event_id, baseline_hash in self._baseline_hashes.items():
                output_hash = self.output_hashes.get(event_id)
                
                if output_hash and baseline_hash != output_hash:
                    failures.append({
                        "type": "output_hash_mismatch",
                        "event_id": event_id,
                        "expected": baseline_hash,
                        "actual": output_hash
                    })
        
        return {
            "verified": len(failures) == 0,
            "total_events": len(events),
            "failures": failures,
            "failure_count": len(failures)
        }
    
    def set_baseline(
        self,
        events: List[Any],
        outputs: Dict[str, Any]
    ) -> None:
        """
        Set baseline for determinism verification.
        
        Args:
            events: Baseline events
            outputs: Baseline outputs
        """
        self._baseline_hashes = {}
        
        for event in events:
            event_hash = self.compute_event_hash(event)
            self._baseline_hashes[event.event_id] = event_hash
        
        for event_id, output in outputs.items():
            output_hash = self.compute_state_hash({"output": output})
            self._baseline_hashes[event_id] = output_hash
        
        logger.info(f"Set baseline with {len(events)} events")
    
    def clear_baseline(self) -> None:
        """Clear baseline"""
        self._baseline_hashes = None
        logger.info("Cleared baseline")
    
    def compare_runs(
        self,
        run1: List[Any],
        run2: List[Any]
    ) -> Dict[str, Any]:
        """
        Compare two replay runs for determinism.
        
        Args:
            run1: First run events
            run2: Second run events
            
        Returns:
            Comparison result
        """
        if len(run1) != len(run2):
            return {
                "deterministic": False,
                "reason": "Different event counts",
                "run1_count": len(run1),
                "run2_count": len(run2)
            }
        
        differences = []
        
        for i, (e1, e2) in enumerate(zip(run1, run2)):
            hash1 = self.compute_event_hash(e1)
            hash2 = self.compute_event_hash(e2)
            
            if hash1 != hash2:
                differences.append({
                    "position": i,
                    "event1_id": e1.event_id,
                    "event2_id": e2.event_id,
                    "hash1": hash1[:16],
                    "hash2": hash2[:16]
                })
        
        return {
            "deterministic": len(differences) == 0,
            "total_events": len(run1),
            "differences": differences,
            "difference_count": len(differences)
        }
    
    def get_determinism_report(self) -> Dict[str, Any]:
        """Generate determinism report"""
        return {
            "snapshots_count": len(self.state_snapshots),
            "recorded_events": len(self.input_hashes),
            "recorded_outputs": len(self.output_hashes),
            "failures_count": len(self.determinism_failures),
            "baseline_set": self._baseline_hashes is not None,
            "verification_enabled": self._verification_enabled,
            "snapshots": [
                {
                    "id": s.snapshot_id,
                    "timestamp": s.timestamp.isoformat(),
                    "sequence": s.sequence,
                    "state_hash": s.state_hash[:16]
                }
                for s in self.state_snapshots[-10:]  # Last 10
            ]
        }
    
    def enable_verification(self) -> None:
        """Enable determinism verification"""
        self._verification_enabled = True
        logger.info("Determinism verification enabled")
    
    def disable_verification(self) -> None:
        """Disable determinism verification"""
        self._verification_enabled = False
        logger.info("Determinism verification disabled")
    
    def reset(self) -> None:
        """Reset engine state"""
        self.state_snapshots.clear()
        self.input_hashes.clear()
        self.output_hashes.clear()
        self.determinism_failures.clear()
        self._baseline_hashes = None
        logger.info("DeterministicEngine reset")


class ReproducibilityVerifier:
    """
    Verifies reproducibility of replay sessions.
    """
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    def register_session(
        self,
        session_id: str,
        events: List[Any],
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Register a session for reproducibility verification.
        
        Args:
            session_id: Session identifier
            events: Session events
            metadata: Optional metadata
            
        Returns:
            Session hash
        """
        engine = DeterministicEngine()
        hashes = [engine.compute_event_hash(e) for e in events]
        combined = "".join(hashes)
        session_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        self.sessions[session_id] = {
            "session_hash": session_hash,
            "event_count": len(events),
            "event_hashes": hashes,
            "metadata": metadata or {},
            "registered_at": datetime.now().isoformat()
        }
        
        logger.info(f"Registered session {session_id}: {session_hash[:16]}")
        
        return session_hash
    
    def verify_reproducibility(
        self,
        session_id: str,
        replay_events: List[Any]
    ) -> Dict[str, Any]:
        """
        Verify that replay reproduces the original session.
        
        Args:
            session_id: Original session ID
            replay_events: Replay events to verify
            
        Returns:
            Verification result
        """
        if session_id not in self.sessions:
            return {
                "reproducible": False,
                "reason": "Session not found"
            }
        
        original = self.sessions[session_id]
        engine = DeterministicEngine()
        
        # Compare event counts
        if len(replay_events) != original["event_count"]:
            return {
                "reproducible": False,
                "reason": "Event count mismatch",
                "original_count": original["event_count"],
                "replay_count": len(replay_events)
            }
        
        # Compare hashes
        replay_hashes = [engine.compute_event_hash(e) for e in replay_events]
        
        mismatches = []
        for i, (h1, h2) in enumerate(zip(original["event_hashes"], replay_hashes)):
            if h1 != h2:
                mismatches.append({
                    "position": i,
                    "original_hash": h1[:16],
                    "replay_hash": h2[:16]
                })
        
        return {
            "reproducible": len(mismatches) == 0,
            "session_id": session_id,
            "event_count": original["event_count"],
            "mismatches": mismatches,
            "match_percentage": (
                (len(replay_hashes) - len(mismatches)) / len(replay_hashes) * 100
                if replay_hashes else 0
            )
        }
    
    def get_session_hash(self, session_id: str) -> Optional[str]:
        """Get session hash"""
        session = self.sessions.get(session_id)
        return session["session_hash"] if session else None
