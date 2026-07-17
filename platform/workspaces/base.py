from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceInfo:
    workspace_id: str
    title: str
    icon: str
    is_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "title": self.title,
            "icon": self.icon,
            "is_active": self.is_active,
        }


class WorkspaceBase(ABC):
    """Abstract base for all professional workspaces."""

    def __init__(self, workspace_id: str, title: str, icon: str = "") -> None:
        self.workspace_id = workspace_id
        self.title = title
        self.icon = icon
        self._active = False
        self._initialized = False
        self._state: Dict[str, Any] = {}
        logger.info("Workspace created: %s (%s)", title, workspace_id)

    @abstractmethod
    def initialize(self) -> bool:
        """Set up workspace resources. Return True on success."""
        ...

    @abstractmethod
    def get_layout(self) -> Dict[str, Any]:
        """Return layout config describing panels and widgets."""
        ...

    def activate(self) -> None:
        """Called when user switches to this workspace."""
        self._active = True
        logger.debug("Workspace activated: %s", self.workspace_id)

    def deactivate(self) -> None:
        """Called when user leaves this workspace."""
        self._active = False
        logger.debug("Workspace deactivated: %s", self.workspace_id)

    def on_data_update(self, data: Dict[str, Any]) -> None:
        """Receive live data updates from the platform."""
        pass

    def get_state(self) -> Dict[str, Any]:
        """Return workspace state for persistence."""
        return {
            "workspace_id": self.workspace_id,
            "title": self.title,
            "icon": self.icon,
            "state": dict(self._state),
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore workspace state from persistence."""
        self._state.update(state.get("state", {}))
        logger.debug("State restored for %s", self.workspace_id)

    def cleanup(self) -> None:
        """Release resources when workspace is destroyed."""
        self._state.clear()
        logger.info("Workspace cleaned up: %s", self.workspace_id)

    def info(self) -> WorkspaceInfo:
        return WorkspaceInfo(self.workspace_id, self.title, self.icon, self._active)


class WorkspaceManager:
    """Manages registration, switching, and persistence of workspaces."""

    def __init__(self) -> None:
        self._workspaces: Dict[str, WorkspaceBase] = {}
        self._active_id: Optional[str] = None
        logger.info("WorkspaceManager initialized")

    def register_workspace(self, workspace: WorkspaceBase) -> None:
        if workspace.workspace_id in self._workspaces:
            logger.warning("Overwriting workspace %s", workspace.workspace_id)
        self._workspaces[workspace.workspace_id] = workspace
        if not workspace._initialized:
            workspace.initialize()
            workspace._initialized = True
        logger.info("Workspace registered: %s", workspace.workspace_id)

    def switch_to(self, workspace_id: str) -> bool:
        if workspace_id not in self._workspaces:
            logger.error("Workspace not found: %s", workspace_id)
            return False
        if self._active_id:
            self._workspaces[self._active_id].deactivate()
        self._workspaces[workspace_id].activate()
        self._active_id = workspace_id
        logger.info("Switched to workspace: %s", workspace_id)
        return True

    def get_active(self) -> Optional[WorkspaceBase]:
        if self._active_id and self._active_id in self._workspaces:
            return self._workspaces[self._active_id]
        return None

    def get_workspace(self, workspace_id: str) -> Optional[WorkspaceBase]:
        return self._workspaces.get(workspace_id)

    def list_all(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for ws in self._workspaces.values():
            info = ws.info()
            result.append(info.to_dict())
        return result

    def broadcast_data(self, data: Dict[str, Any]) -> None:
        for ws in self._workspaces.values():
            if ws._active:
                ws.on_data_update(data)

    def save_state(self, path: str) -> None:
        state: Dict[str, Any] = {
            "active_id": self._active_id,
            "workspaces": {},
        }
        for wid, ws in self._workspaces.items():
            state["workspaces"][wid] = ws.get_state()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        logger.info("Workspace state saved to %s", path)

    def load_state(self, path: str) -> None:
        target = Path(path)
        if not target.exists():
            logger.warning("No state file at %s", path)
            return
        raw = json.loads(target.read_text(encoding="utf-8"))
        self._active_id = raw.get("active_id")
        for wid, ws_state in raw.get("workspaces", {}).items():
            if wid in self._workspaces:
                self._workspaces[wid].restore_state(ws_state)
        logger.info("Workspace state loaded from %s", path)

    def cleanup_all(self) -> None:
        for ws in self._workspaces.values():
            ws.cleanup()
        self._workspaces.clear()
        self._active_id = None
        logger.info("All workspaces cleaned up")
