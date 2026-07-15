"""
Self-Improvement Pipeline — automated model improvement with versioning, metric
comparison, conditional promotion, and rollback capability.

Provides a full improvement cycle: archive the current state → retrain →
compare against incumbent → promote if better → rollback if worse.
All attempts are logged and persisted for audit / history review.
"""

import os
import time
import logging
import shutil
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, TypeVar

import numpy as np
import joblib

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ARCHIVE_DIR = "model_archives"
_HISTORY_FILE = os.path.join(_ARCHIVE_DIR, "improvement_history.joblib")
_STATE_FILE = os.path.join(_ARCHIVE_DIR, "pipeline_state.joblib")
_DEFAULT_DEGRADE_THRESHOLD = -0.05  # -5 % → auto-rollback
_PRIMARY_METRIC = "f1"


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class ImprovementAttempt:
    """Record of a single self-improvement cycle."""

    attempt_id: str
    timestamp: str
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float]
    improvement_pct: float
    promoted: bool
    rolled_back: bool
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class SelfImprovementPipeline:
    """Orchestrate model improvement cycles with versioning and rollback.

    The pipeline manages a set of *components* (e.g., model files, scalers,
    config dicts) that together define the "current version".  Each
    improvement cycle:

    1. Archives a snapshot of all tracked components.
    2. Delegates retraining to a provided callable (or the RetrainingPipeline).
    3. Compares post-retrain metrics against pre-retrain metrics.
    4. Promotes the new version if metrics improve beyond a threshold.
    5. Rolls back automatically if performance degrades beyond a threshold.

    Parameters
    ----------
    component_paths : dict of str → str
        Mapping of logical component names to their filesystem paths.
        Example:  {"ensemble_model": "ensemble_models/model.joblib",
                    "scaler": "ensemble_models/scaler.joblib"}
    metrics_fn : callable, optional
        Function that takes no arguments and returns a dict of metric name →
        float for the *current* active version.  If not provided the pipeline
        falls back to the last-known metrics stored in state.
    retrain_fn : callable
        Function that performs retraining and returns a dict of post-training
        metrics.  Called as ``retrain_fn()``.
    degrade_threshold : float
        Relative change below which an automatic rollback is triggered.
        Default -0.05 (i.e., a 5 % drop in the primary metric).
    primary_metric : str
        The metric name used as the primary signal for promotion / rollback.
    archive_dir : str
        Directory where timestamped version archives are stored.
    """

    def __init__(
        self,
        component_paths: Dict[str, str],
        retrain_fn: callable,
        metrics_fn: Optional[callable] = None,
        degrade_threshold: float = _DEFAULT_DEGRADE_THRESHOLD,
        primary_metric: str = _PRIMARY_METRIC,
        archive_dir: str = _ARCHIVE_DIR,
    ) -> None:
        self._component_paths = dict(component_paths)
        self._retrain_fn = retrain_fn
        self._metrics_fn = metrics_fn
        self._degrade_threshold = degrade_threshold
        self._primary_metric = primary_metric
        self._archive_dir = archive_dir

        # In-memory state
        self._attempt_counter: int = 0
        self._history: List[ImprovementAttempt] = []
        self._current_version_id: Optional[str] = None
        self._best_version_id: Optional[str] = None
        self._best_metrics: Dict[str, float] = {}
        self._last_known_metrics: Dict[str, float] = {}
        self._version_metrics: Dict[str, Dict[str, float]] = {}

        os.makedirs(self._archive_dir, exist_ok=True)
        self._load()
        logger.info(
            "SelfImprovementPipeline initialised (archive_dir=%s, primary=%s)",
            self._archive_dir,
            self._primary_metric,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def archive_current(self) -> str:
        """Save the current component state to a timestamped archive directory.

        Returns
        -------
        str
            Archive version id (the directory basename).
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        version_id = f"v{self._attempt_counter:04d}_{ts}"
        archive_path = os.path.join(self._archive_dir, version_id)
        os.makedirs(archive_path, exist_ok=True)

        for name, path in self._component_paths.items():
            if os.path.exists(path):
                dest = os.path.join(archive_path, os.path.basename(path))
                shutil.copy2(path, dest)
            else:
                logger.warning("Component '%s' not found at %s — skipped", name, path)

        # Persist metadata
        meta: Dict[str, Any] = {
            "version_id": version_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": list(self._component_paths.keys()),
            "metrics": self._last_known_metrics,
        }
        meta_path = os.path.join(archive_path, "metadata.joblib")
        joblib.dump(meta, meta_path)

        self._current_version_id = version_id
        self._version_metrics[version_id] = dict(self._last_known_metrics)
        self._save()
        logger.info("Archived current state as %s", version_id)
        return version_id

    def compare_versions(
        self, version_a: str, version_b: str
    ) -> float:
        """Compare metrics between two archived versions.

        Parameters
        ----------
        version_a : str
            The baseline version id.
        version_b : str
            The candidate version id.

        Returns
        -------
        float
            Improvement percentage of version_b over version_a for the
            primary metric.
        """
        metrics_a = self._load_version_metrics(version_a)
        metrics_b = self._load_version_metrics(version_b)

        val_a = metrics_a.get(self._primary_metric, 0.0)
        val_b = metrics_b.get(self._primary_metric, 0.0)

        if val_a == 0.0:
            return 0.0
        return (val_b - val_a) / val_a

    def promote_version(self, version_id: str) -> bool:
        """Promote an archived version to be the current active version.

        Copies the archived component files over the active paths and
        records the version as the current one.

        Parameters
        ----------
        version_id : str
            The archive version id to promote.

        Returns
        -------
        bool
            True if promotion succeeded.
        """
        archive_path = os.path.join(self._archive_dir, version_id)
        if not os.path.isdir(archive_path):
            logger.error("Cannot promote %s — archive not found", version_id)
            return False

        meta = self._load_archive_metadata(version_id)
        if meta is None:
            logger.error("Cannot promote %s — metadata missing", version_id)
            return False

        try:
            for name, path in self._component_paths.items():
                archive_component = os.path.join(
                    archive_path, os.path.basename(path)
                )
                if os.path.exists(archive_component):
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    shutil.copy2(archive_component, path)
                else:
                    logger.warning(
                        "Component '%s' missing in archive %s — skipped", name, version_id
                    )

            self._current_version_id = version_id
            if version_id in self._version_metrics:
                self._last_known_metrics = dict(self._version_metrics[version_id])

            self._update_best_version(version_id)
            logger.info("Promoted version %s to active", version_id)
            return True
        except Exception as exc:
            logger.error("Promotion failed for %s: %s", version_id, exc)
            return False

    def rollback(self, version_id: Optional[str] = None) -> bool:
        """Revert to a previous version.

        If *version_id* is None, roll back to the best known version.
        Falls back to the most recent archived version if no best version
        exists.

        Parameters
        ----------
        version_id : str, optional
            Specific version to restore.

        Returns
        -------
        bool
            True if rollback succeeded.
        """
        target = version_id or self._best_version_id
        if target is None:
            target = self._find_latest_archive()
        if target is None:
            logger.warning("No archive available for rollback")
            return False

        logger.info("Rolling back to version %s", target)
        success = self.promote_version(target)
        if success:
            self._record_attempt(
                metrics_before=dict(self._last_known_metrics),
                metrics_after=self._load_version_metrics(target),
                improvement_pct=0.0,
                promoted=False,
                rolled_back=True,
                description=f"Rollback to {target}",
            )
        return success

    def run_improvement_cycle(
        self, description: str = "Scheduled improvement cycle"
    ) -> ImprovementAttempt:
        """Execute a full improvement cycle.

        Steps
        -----
        1. Capture pre-retrain metrics and archive current state.
        2. Execute the retrain callback.
        3. Capture post-retrain metrics.
        4. Compare — if improvement is positive, promote; else auto-rollback.
        5. Record and persist the attempt.

        Parameters
        ----------
        description : str
            Human-readable label for this cycle.

        Returns
        -------
        ImprovementAttempt
            Record of the attempt with outcome.
        """
        self._attempt_counter += 1

        # --- 1. Pre-retrain metrics & archive ---
        metrics_before = self._capture_metrics()
        self._last_known_metrics = dict(metrics_before)
        archive_id = self.archive_current()
        logger.info(
            "Improvement cycle #%d — pre-retrain metrics: %s",
            self._attempt_counter,
            metrics_before,
        )

        # --- 2. Retrain ---
        try:
            t0 = time.time()
            metrics_after = self._retrain_fn()
            elapsed = time.time() - t0
            logger.info(
                "Retrain completed in %.2fs — post-retrain metrics: %s",
                elapsed,
                metrics_after,
            )
        except Exception as exc:
            logger.error("Retrain failed in cycle #%d: %s", self._attempt_counter, exc)
            attempt = self._record_attempt(
                metrics_before=metrics_before,
                metrics_after={},
                improvement_pct=0.0,
                promoted=False,
                rolled_back=True,
                description=f"{description} (retrain failed)",
            )
            self.rollback(archive_id)
            return attempt

        # --- 3. Register post-retrain metrics ---
        self._version_metrics[archive_id] = dict(metrics_after)
        self._last_known_metrics = dict(metrics_after)

        # --- 4. Compare ---
        improvement_pct = self._compute_weighted_improvement(
            metrics_before, metrics_after
        )
        logger.info(
            "Improvement cycle #%d — weighted improvement: %+.4f",
            self._attempt_counter,
            improvement_pct,
        )

        promoted = False
        rolled_back = False

        if improvement_pct > 0:
            # Promote only if the primary metric also improved (or is stable)
            primary_before = metrics_before.get(self._primary_metric, 0.0)
            primary_after = metrics_after.get(self._primary_metric, 0.0)
            if primary_after >= primary_before or self._primary_metric in metrics_after:
                success = self.promote_version(archive_id)
                if success:
                    promoted = True
                    logger.info(
                        "Cycle #%d — promoted (improvement=%.2f%%)",
                        self._attempt_counter,
                        improvement_pct * 100,
                    )
                else:
                    logger.warning("Cycle #%d — promotion failed", self._attempt_counter)
            else:
                logger.info(
                    "Cycle #%d — primary metric %s declined (%.4f → %.4f), "
                    "skipping promotion",
                    self._attempt_counter,
                    self._primary_metric,
                    primary_before,
                    primary_after,
                )
        else:
            # --- 5. Auto-rollback if degradation exceeds threshold ---
            if improvement_pct < self._degrade_threshold:
                logger.warning(
                    "Cycle #%d — degradation %.2f%% exceeds threshold %.2f%%, "
                    "auto-rolling back",
                    self._attempt_counter,
                    improvement_pct * 100,
                    self._degrade_threshold * 100,
                )
                self.rollback(archive_id)
                rolled_back = True
            else:
                logger.info(
                    "Cycle #%d — minor or no improvement, keeping current version",
                    self._attempt_counter,
                )

        # --- 6. Record ---
        attempt = self._record_attempt(
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            improvement_pct=round(improvement_pct, 6),
            promoted=promoted,
            rolled_back=rolled_back,
            description=description,
        )
        return attempt

    def get_improvement_history(self) -> List[ImprovementAttempt]:
        """Return all recorded improvement attempts sorted newest first."""
        return list(reversed(self._history))

    def get_best_version(self) -> Optional[str]:
        """Return the version id with the best primary metric."""
        if self._best_version_id is not None:
            return self._best_version_id

        best_vid: Optional[str] = None
        best_val = -float("inf")
        for vid, metrics in self._version_metrics.items():
            val = metrics.get(self._primary_metric, -float("inf"))
            if val > best_val:
                best_val = val
                best_vid = vid

        # Also scan archives on disk
        if best_vid is None:
            best_vid = self._scan_archives_for_best()

        self._best_version_id = best_vid
        return best_vid

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Return summary statistics for the self-improvement pipeline."""
        total = len(self._history)
        promoted = sum(1 for a in self._history if a.promoted)
        rolled_back = sum(1 for a in self._history if a.rolled_back)
        failed = sum(1 for a in self._history if "failed" in a.description.lower())

        improvements = [
            a.improvement_pct
            for a in self._history
            if a.improvement_pct > 0
        ]
        avg_improvement = float(np.mean(improvements)) if improvements else 0.0

        best_version = self.get_best_version()
        best_metrics = {}
        if best_version and best_version in self._version_metrics:
            best_metrics = self._version_metrics[best_version]

        return {
            "total_attempts": total,
            "promoted_count": promoted,
            "rolled_back_count": rolled_back,
            "failed_count": failed,
            "promotion_rate": round(promoted / total, 4) if total else 0.0,
            "average_improvement_pct": round(avg_improvement, 6),
            "best_version_id": best_version,
            "best_metrics": best_metrics,
            "current_version_id": self._current_version_id,
            "current_metrics": dict(self._last_known_metrics),
            "degrade_threshold": self._degrade_threshold,
            "primary_metric": self._primary_metric,
            "archive_count": len(self._list_archives()),
            "tracked_components": list(self._component_paths.keys()),
        }

    def save(self, path: Optional[str] = None) -> str:
        """Persist the full pipeline state to disk.

        Parameters
        ----------
        path : str, optional
            Destination path.  Defaults to ``model_archives/pipeline_state.joblib``.

        Returns
        -------
        str
            The path used.
        """
        target = path or _STATE_FILE
        os.makedirs(os.path.dirname(target), exist_ok=True)
        state: Dict[str, Any] = {
            "attempt_counter": self._attempt_counter,
            "history": [a.to_dict() for a in self._history],
            "current_version_id": self._current_version_id,
            "best_version_id": self._best_version_id,
            "best_metrics": self._best_metrics,
            "last_known_metrics": self._last_known_metrics,
            "version_metrics": self._version_metrics,
            "component_paths": self._component_paths,
            "degrade_threshold": self._degrade_threshold,
            "primary_metric": self._primary_metric,
        }
        joblib.dump(state, target)
        logger.info("Pipeline state saved to %s", target)
        return target

    def load(self, path: Optional[str] = None) -> bool:
        """Restore pipeline state from disk.

        Parameters
        ----------
        path : str, optional
            Source path.  Defaults to ``model_archives/pipeline_state.joblib``.

        Returns
        -------
        bool
            True if state was loaded.
        """
        target = path or _STATE_FILE
        if not os.path.exists(target):
            logger.warning("No state file found at %s", target)
            return False
        try:
            state: Dict[str, Any] = joblib.load(target)
            self._attempt_counter = state.get("attempt_counter", 0)
            self._history = [
                ImprovementAttempt(**h) for h in state.get("history", [])
            ]
            self._current_version_id = state.get("current_version_id")
            self._best_version_id = state.get("best_version_id")
            self._best_metrics = state.get("best_metrics", {})
            self._last_known_metrics = state.get("last_known_metrics", {})
            self._version_metrics = state.get("version_metrics", {})
            logger.info("Pipeline state loaded from %s", target)
            return True
        except Exception as exc:
            logger.error("Failed to load pipeline state: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _capture_metrics(self) -> Dict[str, float]:
        if self._metrics_fn is not None:
            try:
                return dict(self._metrics_fn())
            except Exception as exc:
                logger.warning("Metrics function failed: %s", exc)

        return dict(self._last_known_metrics) if self._last_known_metrics else {}

    def _compute_weighted_improvement(
        self, before: Dict[str, float], after: Dict[str, float]
    ) -> float:
        """Compute a composite improvement across all shared metrics.

        Returns the average relative change across all metrics that exist
        in both dicts.
        """
        changes: List[float] = []
        for key in before:
            if key in after:
                old_val = before[key]
                new_val = after[key]
                if old_val != 0.0:
                    changes.append((new_val - old_val) / abs(old_val))
                elif new_val != 0.0:
                    changes.append(1.0)
                else:
                    changes.append(0.0)

        if not changes:
            return 0.0
        return float(np.mean(changes))

    def _update_best_version(self, version_id: str) -> None:
        metrics = self._version_metrics.get(version_id, {})
        val = metrics.get(self._primary_metric, -float("inf"))
        best_val = self._best_metrics.get(self._primary_metric, -float("inf"))
        if val > best_val:
            self._best_version_id = version_id
            self._best_metrics = dict(metrics)
            logger.info(
                "New best version: %s (%s=%.4f)",
                version_id,
                self._primary_metric,
                val,
            )

    def _record_attempt(
        self,
        metrics_before: Dict[str, float],
        metrics_after: Dict[str, float],
        improvement_pct: float,
        promoted: bool,
        rolled_back: bool,
        description: str,
    ) -> ImprovementAttempt:
        attempt = ImprovementAttempt(
            attempt_id=f"cycle_{self._attempt_counter:04d}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            improvement_pct=improvement_pct,
            promoted=promoted,
            rolled_back=rolled_back,
            description=description,
        )
        self._history.append(attempt)
        self._save()
        return attempt

    def _load_version_metrics(self, version_id: str) -> Dict[str, float]:
        if version_id in self._version_metrics:
            return self._version_metrics[version_id]
        meta = self._load_archive_metadata(version_id)
        if meta and "metrics" in meta:
            return dict(meta["metrics"])
        return {}

    def _load_archive_metadata(self, version_id: str) -> Optional[Dict[str, Any]]:
        meta_path = os.path.join(self._archive_dir, version_id, "metadata.joblib")
        if os.path.exists(meta_path):
            try:
                return joblib.load(meta_path)
            except Exception as exc:
                logger.warning("Failed to load metadata for %s: %s", version_id, exc)
        return None

    def _find_latest_archive(self) -> Optional[str]:
        archives = self._list_archives()
        return archives[0] if archives else None

    def _list_archives(self) -> List[str]:
        if not os.path.isdir(self._archive_dir):
            return []
        entries = [
            d
            for d in os.listdir(self._archive_dir)
            if os.path.isdir(os.path.join(self._archive_dir, d))
            and not d.startswith(".")
        ]
        return sorted(entries, reverse=True)

    def _scan_archives_for_best(self) -> Optional[str]:
        best_vid: Optional[str] = None
        best_val = -float("inf")
        for vid in self._list_archives():
            metrics = self._load_version_metrics(vid)
            val = metrics.get(self._primary_metric, -float("inf"))
            if val > best_val:
                best_val = val
                best_vid = vid
                self._version_metrics[vid] = metrics
        return best_vid

    def _save(self) -> None:
        self.save()

    def _load(self) -> None:
        self.load()
