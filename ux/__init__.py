"""
User Experience Platform
=====================

Institutional-grade user experience framework.

Features:
- Multi-monitor layouts
- Dockable windows
- Workspace templates
- Command palette
- Keyboard shortcuts
- Saved searches
- Quick actions
- Accessibility support
- Responsive layouts
- Advanced filtering
- Context-sensitive help
- Interactive onboarding
- Custom themes
- Custom dashboards
- Notification center
- Recent activity
- Favorites
- Global search
- Command history
"""

__version__ = "1.0.0"

from .core import (
    Window,
    WindowState,
    DockPosition,
    Layout,
    Monitor,
    Workspace,
    WorkspaceTemplate,
)
from .workspace import (
    WorkspaceManager,
    WorkspaceSettings,
)
from .command_palette import (
    CommandPalette,
    Command,
    CommandCategory,
    CommandExecutor,
)
from .shortcuts import (
    KeyboardShortcuts,
    ShortcutBinding,
    ShortcutManager,
)
from .search import (
    GlobalSearch,
    SavedSearch,
    SearchResult,
    FilterCriteria,
)
from .themes import (
    Theme,
    ThemeManager,
    ColorPalette,
    Typography,
)
from .notifications import (
    Notification,
    NotificationCenter,
    NotificationPriority,
    NotificationType,
)
from .accessibility import (
    AccessibilityManager,
    ScreenReader,
    HighContrast,
)
from .onboarding import (
    OnboardingManager,
    OnboardingStep,
    Tutorial,
)
from .dashboard import (
    Dashboard,
    DashboardWidget,
    DashboardLayout,
)

__all__ = [
    "Window",
    "WindowState",
    "DockPosition",
    "Layout",
    "Monitor",
    "Workspace",
    "WorkspaceTemplate",
    "WorkspaceManager",
    "WorkspaceSettings",
    "CommandPalette",
    "Command",
    "CommandCategory",
    "CommandExecutor",
    "KeyboardShortcuts",
    "ShortcutBinding",
    "ShortcutManager",
    "GlobalSearch",
    "SavedSearch",
    "SearchResult",
    "FilterCriteria",
    "Theme",
    "ThemeManager",
    "ColorPalette",
    "Typography",
    "Notification",
    "NotificationCenter",
    "NotificationPriority",
    "NotificationType",
    "AccessibilityManager",
    "ScreenReader",
    "HighContrast",
    "OnboardingManager",
    "OnboardingStep",
    "Tutorial",
    "Dashboard",
    "DashboardWidget",
    "DashboardLayout",
]
