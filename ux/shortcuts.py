"""
Keyboard Shortcuts
=================

Comprehensive keyboard shortcut management with customizable bindings.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


@dataclass
class ShortcutBinding:
    """Keyboard shortcut binding"""
    binding_id: str
    shortcut: str  # e.g., "Ctrl+Shift+K"
    action: str
    description: str
    
    # Context
    context: Optional[str] = None  # e.g., "chart", "order_entry"
    
    # Properties
    is_enabled: bool = True
    is_default: bool = False
    modifier: str = ""  # ctrl, shift, alt, meta
    
    # Conflicts
    conflicts_with: List[str] = field(default_factory=list)  # Other binding IDs
    
    def matches(self, key_sequence: str) -> bool:
        """Check if this binding matches the key sequence"""
        return self.shortcut.lower() == key_sequence.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "shortcut": self.shortcut,
            "action": self.action,
            "description": self.description,
            "context": self.context,
            "is_enabled": self.is_enabled,
        }


class KeyboardShortcuts:
    """
    Collection of default keyboard shortcuts.
    """
    
    # Global shortcuts
    GLOBAL = [
        ShortcutBinding(
            binding_id="global_search",
            shortcut="Ctrl+Shift+P",
            action="search.global",
            description="Open global search",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="command_palette",
            shortcut="Ctrl+Shift+K",
            action="command.palette",
            description="Open command palette",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="settings",
            shortcut="Ctrl+,",
            action="settings.open",
            description="Open settings",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="help",
            shortcut="F1",
            action="help.open",
            description="Open help",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="quit",
            shortcut="Ctrl+Q",
            action="app.quit",
            description="Quit application",
            is_default=True,
        ),
    ]
    
    # Navigation shortcuts
    NAVIGATION = [
        ShortcutBinding(
            binding_id="go_dashboard",
            shortcut="G D",
            action="navigate.dashboard",
            description="Go to dashboard",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="go_positions",
            shortcut="G P",
            action="navigate.positions",
            description="Go to positions",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="go_orders",
            shortcut="G O",
            action="navigate.orders",
            description="Go to orders",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="go_history",
            shortcut="G H",
            action="navigate.history",
            description="Go to history",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="go_watchlist",
            shortcut="G W",
            action="navigate.watchlist",
            description="Go to watchlist",
            is_default=True,
        ),
    ]
    
    # Trading shortcuts
    TRADING = [
        ShortcutBinding(
            binding_id="new_order",
            shortcut="Ctrl+N",
            action="order.new",
            description="New order",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="close_position",
            shortcut="Ctrl+W",
            action="position.close",
            description="Close position",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="cancel_order",
            shortcut="Escape",
            action="order.cancel",
            description="Cancel order",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="confirm_order",
            shortcut="Enter",
            action="order.confirm",
            description="Confirm order",
            is_default=True,
        ),
    ]
    
    # View shortcuts
    VIEW = [
        ShortcutBinding(
            binding_id="refresh",
            shortcut="F5",
            action="view.refresh",
            description="Refresh view",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="fullscreen",
            shortcut="F11",
            action="view.fullscreen",
            description="Toggle fullscreen",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="toggle_sidebar",
            shortcut="Ctrl+B",
            action="view.toggle_sidebar",
            description="Toggle sidebar",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="zoom_in",
            shortcut="Ctrl+=",
            action="view.zoom_in",
            description="Zoom in",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="zoom_out",
            shortcut="Ctrl+-",
            action="view.zoom_out",
            description="Zoom out",
            is_default=True,
        ),
    ]
    
    # Edit shortcuts
    EDIT = [
        ShortcutBinding(
            binding_id="undo",
            shortcut="Ctrl+Z",
            action="edit.undo",
            description="Undo",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="redo",
            shortcut="Ctrl+Shift+Z",
            action="edit.redo",
            description="Redo",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="copy",
            shortcut="Ctrl+C",
            action="edit.copy",
            description="Copy",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="paste",
            shortcut="Ctrl+V",
            action="edit.paste",
            description="Paste",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="select_all",
            shortcut="Ctrl+A",
            action="edit.select_all",
            description="Select all",
            is_default=True,
        ),
    ]
    
    # Chart shortcuts
    CHART = [
        ShortcutBinding(
            binding_id="chart_zoom_in",
            shortcut="+",
            action="chart.zoom_in",
            description="Zoom in chart",
            context="chart",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="chart_zoom_out",
            shortcut="-",
            action="chart.zoom_out",
            description="Zoom out chart",
            context="chart",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="chart_reset",
            shortcut="0",
            action="chart.reset",
            description="Reset chart",
            context="chart",
            is_default=True,
        ),
        ShortcutBinding(
            binding_id="chart_crosshair",
            shortcut="C",
            action="chart.crosshair",
            description="Toggle crosshair",
            context="chart",
            is_default=True,
        ),
    ]
    
    @classmethod
    def get_all(cls) -> List[ShortcutBinding]:
        """Get all default shortcuts"""
        all_shortcuts = []
        for category in [cls.GLOBAL, cls.NAVIGATION, cls.TRADING, cls.VIEW, cls.EDIT, cls.CHART]:
            all_shortcuts.extend(category)
        return all_shortcuts


class ShortcutManager:
    """
    Manages keyboard shortcuts with customizable bindings.
    """
    
    def __init__(self):
        self._bindings: Dict[str, ShortcutBinding] = {}
        self._action_handlers: Dict[str, Callable] = {}
        self._context_stack: List[str] = []
        
        # Initialize defaults
        self._initialize_defaults()
        
        # Callbacks
        self._action_callbacks: Dict[str, List[Callable]] = {}
    
    def _initialize_defaults(self) -> None:
        """Initialize default shortcuts"""
        for shortcut in KeyboardShortcuts.get_all():
            self._bindings[shortcut.binding_id] = shortcut
    
    # ========== Binding Management ==========
    
    def register_binding(
        self,
        shortcut: str,
        action: str,
        description: str,
        binding_id: Optional[str] = None,
        context: Optional[str] = None,
        override: bool = False
    ) -> ShortcutBinding:
        """Register a new keyboard shortcut binding"""
        binding_id = binding_id or str(uuid.uuid4())
        
        # Check for conflicts
        if not override:
            existing = self.get_by_shortcut(shortcut)
            if existing:
                raise ValueError(f"Shortcut {shortcut} is already bound to {existing.action}")
        
        binding = ShortcutBinding(
            binding_id=binding_id,
            shortcut=shortcut,
            action=action,
            description=description,
            context=context,
            is_default=False,
        )
        
        self._bindings[binding_id] = binding
        return binding
    
    def unregister_binding(self, binding_id: str) -> Optional[ShortcutBinding]:
        """Unregister a binding"""
        binding = self._bindings.pop(binding_id, None)
        return binding
    
    def get_binding(self, binding_id: str) -> Optional[ShortcutBinding]:
        """Get a binding by ID"""
        return self._bindings.get(binding_id)
    
    def get_by_shortcut(self, shortcut: str) -> Optional[ShortcutBinding]:
        """Get binding by shortcut"""
        for binding in self._bindings.values():
            if binding.matches(shortcut):
                return binding
        return None
    
    def get_all_bindings(self) -> List[ShortcutBinding]:
        """Get all registered bindings"""
        return list(self._bindings.values())
    
    def get_bindings_by_context(self, context: str) -> List[ShortcutBinding]:
        """Get bindings for a specific context"""
        return [
            b for b in self._bindings.values()
            if b.context == context or b.context is None
        ]
    
    # ========== Context Management ==========
    
    def push_context(self, context: str) -> None:
        """Push a context onto the stack"""
        self._context_stack.append(context)
    
    def pop_context(self) -> Optional[str]:
        """Pop a context from the stack"""
        return self._context_stack.pop() if self._context_stack else None
    
    def get_current_context(self) -> Optional[str]:
        """Get the current context"""
        return self._context_stack[-1] if self._context_stack else None
    
    # ========== Action Handling ==========
    
    def register_handler(self, action: str, handler: Callable) -> None:
        """Register an action handler"""
        self._action_handlers[action] = handler
    
    def on_action(self, action: str, callback: Callable) -> None:
        """Register an action callback"""
        if action not in self._action_callbacks:
            self._action_callbacks[action] = []
        self._action_callbacks[action].append(callback)
    
    def execute_action(self, action: str, args: Optional[Dict[str, Any]] = None) -> Any:
        """Execute an action"""
        # Call registered handler
        handler = self._action_handlers.get(action)
        if handler:
            result = handler(args or {})
        else:
            result = None
        
        # Call callbacks
        callbacks = self._action_callbacks.get(action, [])
        for callback in callbacks:
            try:
                callback(action, args)
            except Exception as e:
                logger.error(f"Action callback error: {action} - {e}")
        
        return result
    
    # ========== Key Handling ==========
    
    def handle_key(self, key_sequence: str) -> Optional[Any]:
        """
        Handle a key sequence.
        
        Returns the result of the action if executed, None otherwise.
        """
        # Get current context
        current_context = self.get_current_context()
        
        # Find matching binding
        for binding in self._bindings.values():
            if not binding.is_enabled:
                continue
            
            # Check context
            if binding.context and binding.context != current_context:
                continue
            
            if binding.matches(key_sequence):
                logger.debug(f"Executing shortcut: {binding.action}")
                return self.execute_action(binding.action)
        
        return None
    
    def is_bound(self, shortcut: str) -> bool:
        """Check if a shortcut is bound"""
        return self.get_by_shortcut(shortcut) is not None
    
    # ========== Customization ==========
    
    def rebind(
        self,
        binding_id: str,
        new_shortcut: str
    ) -> Optional[ShortcutBinding]:
        """Change the shortcut for a binding"""
        binding = self._bindings.get(binding_id)
        if not binding:
            return None
        
        # Check for conflicts
        existing = self.get_by_shortcut(new_shortcut)
        if existing and existing.binding_id != binding_id:
            raise ValueError(f"Shortcut {new_shortcut} is already bound")
        
        binding.shortcut = new_shortcut
        return binding
    
    def reset_to_defaults(self) -> None:
        """Reset all bindings to defaults"""
        # Remove custom bindings
        self._bindings = {
            b.binding_id: b
            for b in self._bindings.values()
            if b.is_default
        }
        
        # Re-add defaults
        self._initialize_defaults()
    
    def export_bindings(self) -> List[Dict[str, Any]]:
        """Export bindings for saving"""
        return [
            b.to_dict()
            for b in self._bindings.values()
            if not b.is_default
        ]
    
    def import_bindings(self, bindings: List[Dict[str, Any]]) -> None:
        """Import bindings from saved data"""
        for data in bindings:
            self.register_binding(
                shortcut=data["shortcut"],
                action=data["action"],
                description=data.get("description", ""),
                binding_id=data.get("binding_id"),
                context=data.get("context"),
                override=True,
            )
