"""
Command Palette
==============

Advanced command palette with fuzzy search and quick actions.
"""

import time
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CommandCategory(Enum):
    """Command categories"""
    NAVIGATION = "navigation"
    ACTION = "action"
    EDIT = "edit"
    VIEW = "view"
    FILE = "file"
    SEARCH = "search"
    SETTINGS = "settings"
    WINDOW = "window"
    HELP = "help"


@dataclass
class Command:
    """A command that can be executed"""
    command_id: str
    name: str
    description: str
    category: CommandCategory
    
    # Execution
    action: str  # Command identifier or function name
    handler: Optional[Callable] = None  # Function to call
    
    # Display
    icon: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    
    # Shortcut
    shortcut: Optional[str] = None  # e.g., "Ctrl+K"
    
    # Arguments
    arguments: List[Dict[str, Any]] = field(default_factory=list)  # Expected args
    requires_args: bool = False
    
    # State
    is_enabled: bool = True
    is_visible: bool = True
    
    # History
    use_count: int = 0
    last_used: Optional[float] = None
    
    def execute(self, args: Optional[Dict[str, Any]] = None) -> Any:
        """Execute the command"""
        if self.handler:
            return self.handler(args or {})
        return None
    
    def matches(self, query: str) -> bool:
        """Check if command matches query"""
        query = query.lower()
        
        # Check name
        if query in self.name.lower():
            return True
        
        # Check description
        if query in self.description.lower():
            return True
        
        # Check keywords
        for keyword in self.keywords:
            if query in keyword.lower():
                return True
        
        return False
    
    def score(self, query: str) -> float:
        """Calculate match score (higher = better)"""
        if not query:
            return 0.5  # Neutral score for empty query
        
        query = query.lower()
        name = self.name.lower()
        desc = self.description.lower()
        
        score = 0.0
        
        # Exact name match
        if name == query:
            score += 1.0
        # Name starts with query
        elif name.startswith(query):
            score += 0.8
        # Name contains query
        elif query in name:
            score += 0.6
        # Description contains query
        elif query in desc:
            score += 0.4
        # Keyword match
        else:
            for keyword in self.keywords:
                if query in keyword.lower():
                    score += 0.3
                    break
        
        # Boost recently used
        if self.last_used:
            days_ago = (time.time() - self.last_used) / 86400
            if days_ago < 1:
                score += 0.2
            elif days_ago < 7:
                score += 0.1
        
        # Boost frequently used
        if self.use_count > 10:
            score += 0.1
        
        return score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "shortcut": self.shortcut,
            "icon": self.icon,
        }


class CommandExecutor:
    """
    Executes commands and manages execution context.
    """
    
    def __init__(self):
        self._context: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []
        self._max_history = 100
    
    def execute(
        self,
        command: Command,
        args: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a command"""
        if not command.is_enabled:
            return None
        
        start_time = time.time()
        
        try:
            # Execute the command
            result = command.execute(args)
            
            # Record in history
            self._history.append({
                "command_id": command.command_id,
                "name": command.name,
                "args": args,
                "result": result,
                "success": True,
                "timestamp": start_time,
                "duration_ms": (time.time() - start_time) * 1000,
            })
            
            # Update command stats
            command.use_count += 1
            command.last_used = time.time()
            
            return result
            
        except Exception as e:
            # Record failed execution
            self._history.append({
                "command_id": command.command_id,
                "name": command.name,
                "args": args,
                "error": str(e),
                "success": False,
                "timestamp": start_time,
                "duration_ms": (time.time() - start_time) * 1000,
            })
            
            logger.error(f"Command execution error: {command.name} - {e}")
            raise
    
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get command execution history"""
        return self._history[-limit:]
    
    def get_frequent_commands(self, limit: int = 10) -> List[Command]:
        """Get most frequently used commands"""
        # This would need access to the command registry
        return []
    
    def set_context(self, key: str, value: Any) -> None:
        """Set execution context"""
        self._context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get execution context"""
        return self._context.get(key, default)


class CommandPalette:
    """
    Advanced command palette with fuzzy search and quick actions.
    """
    
    def __init__(self):
        self._commands: Dict[str, Command] = {}
        self._categories: Dict[CommandCategory, List[Command]] = {}
        self._recent: List[str] = []  # Command IDs
        self._favorites: List[str] = []  # Command IDs
        self._executor = CommandExecutor()
        
        # Initialize default commands
        self._initialize_default_commands()
    
    def _initialize_default_commands(self) -> None:
        """Initialize default commands"""
        commands = [
            # Navigation
            Command(
                command_id="cmd_go_dashboard",
                name="Go to Dashboard",
                description="Navigate to the main dashboard",
                category=CommandCategory.NAVIGATION,
                action="navigate.dashboard",
                shortcut="G D",
            ),
            Command(
                command_id="cmd_go_positions",
                name="Go to Positions",
                description="Navigate to the positions view",
                category=CommandCategory.NAVIGATION,
                action="navigate.positions",
                shortcut="G P",
            ),
            Command(
                command_id="cmd_go_orders",
                name="Go to Orders",
                description="Navigate to the orders view",
                category=CommandCategory.NAVIGATION,
                action="navigate.orders",
                shortcut="G O",
            ),
            
            # Actions
            Command(
                command_id="cmd_new_order",
                name="New Order",
                description="Create a new trading order",
                category=CommandCategory.ACTION,
                action="order.new",
                shortcut="Ctrl+N",
                icon="add",
            ),
            Command(
                command_id="cmd_close_position",
                name="Close Position",
                description="Close the selected position",
                category=CommandCategory.ACTION,
                action="position.close",
                shortcut="Ctrl+W",
            ),
            Command(
                command_id="cmd_refresh",
                name="Refresh",
                description="Refresh current view",
                category=CommandCategory.ACTION,
                action="view.refresh",
                shortcut="F5",
            ),
            
            # View
            Command(
                command_id="cmd_toggle_sidebar",
                name="Toggle Sidebar",
                description="Show or hide the sidebar",
                category=CommandCategory.VIEW,
                action="view.toggle_sidebar",
                shortcut="Ctrl+B",
            ),
            Command(
                command_id="cmd_fullscreen",
                name="Toggle Fullscreen",
                description="Toggle fullscreen mode",
                category=CommandCategory.VIEW,
                action="view.fullscreen",
                shortcut="F11",
            ),
            
            # Settings
            Command(
                command_id="cmd_settings",
                name="Open Settings",
                description="Open the settings dialog",
                category=CommandCategory.SETTINGS,
                action="settings.open",
                shortcut="Ctrl+,",
            ),
            Command(
                command_id="cmd_themes",
                name="Change Theme",
                description="Switch to a different theme",
                category=CommandCategory.SETTINGS,
                action="settings.theme",
            ),
            
            # Search
            Command(
                command_id="cmd_global_search",
                name="Global Search",
                description="Search across all data",
                category=CommandCategory.SEARCH,
                action="search.global",
                shortcut="Ctrl+Shift+F",
            ),
            Command(
                command_id="cmd_search_orders",
                name="Search Orders",
                description="Search for orders",
                category=CommandCategory.SEARCH,
                action="search.orders",
                shortcut="Ctrl+F",
            ),
            
            # Help
            Command(
                command_id="cmd_help",
                name="Help",
                description="Open help documentation",
                category=CommandCategory.HELP,
                action="help.open",
                shortcut="F1",
            ),
            Command(
                command_id="cmd_shortcuts",
                name="Keyboard Shortcuts",
                description="View all keyboard shortcuts",
                category=CommandCategory.HELP,
                action="help.shortcuts",
                shortcut="Ctrl+/",
            ),
        ]
        
        for command in commands:
            self.register(command)
    
    # ========== Command Management ==========
    
    def register(self, command: Command) -> None:
        """Register a command"""
        self._commands[command.command_id] = command
        
        # Add to category
        if command.category not in self._categories:
            self._categories[command.category] = []
        self._categories[command.category].append(command)
    
    def unregister(self, command_id: str) -> Optional[Command]:
        """Unregister a command"""
        command = self._commands.pop(command_id, None)
        if command and command.category in self._categories:
            self._categories[command.category].remove(command)
        return command
    
    def get_command(self, command_id: str) -> Optional[Command]:
        """Get a command by ID"""
        return self._commands.get(command_id)
    
    def get_all_commands(self) -> List[Command]:
        """Get all registered commands"""
        return list(self._commands.values())
    
    def get_commands_by_category(
        self,
        category: CommandCategory
    ) -> List[Command]:
        """Get commands by category"""
        return self._categories.get(category, [])
    
    # ========== Search ==========
    
    def search(self, query: str, limit: int = 20) -> List[Command]:
        """
        Search commands with fuzzy matching.
        
        Returns commands sorted by relevance score.
        """
        if not query:
            # Return recent commands
            return self.get_recent(limit)
        
        query = query.lower().strip()
        
        # Score all commands
        scored = []
        for command in self._commands.values():
            if not command.is_visible:
                continue
            
            score = command.score(query)
            if score > 0:
                scored.append((command, score))
        
        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [cmd for cmd, score in scored[:limit]]
    
    def search_by_category(
        self,
        query: str,
        category: CommandCategory,
        limit: int = 10
    ) -> List[Command]:
        """Search commands within a category"""
        commands = self._categories.get(category, [])
        
        if not query:
            return commands[:limit]
        
        query = query.lower()
        scored = []
        
        for command in commands:
            if not command.is_visible:
                continue
            
            score = command.score(query)
            if score > 0:
                scored.append((command, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [cmd for cmd, score in scored[:limit]]
    
    # ========== Favorites ==========
    
    def toggle_favorite(self, command_id: str) -> bool:
        """Toggle favorite status of a command"""
        if command_id in self._favorites:
            self._favorites.remove(command_id)
            return False
        else:
            self._favorites.append(command_id)
            return True
    
    def is_favorite(self, command_id: str) -> bool:
        """Check if command is a favorite"""
        return command_id in self._favorites
    
    def get_favorites(self) -> List[Command]:
        """Get favorite commands"""
        return [
            self._commands[cid]
            for cid in self._favorites
            if cid in self._commands
        ]
    
    # ========== Recent ==========
    
    def get_recent(self, limit: int = 10) -> List[Command]:
        """Get recently used commands"""
        recent = []
        for cid in self._recent[:limit]:
            if cid in self._commands:
                recent.append(self._commands[cid])
        return recent
    
    def record_use(self, command_id: str) -> None:
        """Record command usage"""
        if command_id in self._recent:
            self._recent.remove(command_id)
        self._recent.insert(0, command_id)
        self._recent = self._recent[:50]  # Keep last 50
    
    # ========== Execution ==========
    
    def execute(
        self,
        command_id: str,
        args: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a command by ID"""
        command = self._commands.get(command_id)
        if not command:
            raise ValueError(f"Command not found: {command_id}")
        
        self.record_use(command_id)
        return self._executor.execute(command, args)
    
    def execute_by_name(
        self,
        name: str,
        args: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a command by name"""
        results = self.search(name, limit=1)
        if results:
            return self.execute(results[0].command_id, args)
        raise ValueError(f"Command not found: {name}")
    
    # ========== Quick Actions ==========
    
    def get_quick_actions(self) -> List[Command]:
        """Get commands suitable for quick action bar"""
        # Return favorites + recent + top commands
        actions = []
        actions.extend(self.get_favorites())
        actions.extend(self.get_recent(5))
        
        # Add high-use commands
        for command in sorted(
            self._commands.values(),
            key=lambda c: c.use_count,
            reverse=True
        )[:5]:
            if command not in actions:
                actions.append(command)
        
        return actions[:10]
    
    # ========== Suggestions ==========
    
    def get_suggestions(
        self,
        query: str,
        max_suggestions: int = 8
    ) -> List[Dict[str, Any]]:
        """Get suggestions for autocomplete"""
        commands = self.search(query, limit=max_suggestions)
        
        suggestions = []
        for command in commands:
            suggestions.append({
                "text": command.name,
                "description": command.description,
                "icon": command.icon,
                "shortcut": command.shortcut,
                "category": command.category.value,
                "action": command.action,
            })
        
        return suggestions


# Quick Actions
QUICK_ACTIONS = {
    "new_order": "cmd_new_order",
    "close_position": "cmd_close_position",
    "refresh": "cmd_refresh",
    "search": "cmd_global_search",
    "settings": "cmd_settings",
}
