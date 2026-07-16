"""
Accessibility Features
====================

Accessibility support for users with disabilities.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScreenReader:
    """Screen reader configuration"""
    enabled: bool = False
    announce_actions: bool = True
    announce_navigation: bool = True
    announce_notifications: bool = True
    verbosity: str = "normal"  # minimal, normal, verbose
    
    # Focus management
    track_focus: bool = True
    announce_focus_changes: bool = True
    
    # Live regions
    live_region_politeness: str = "polite"  # polite, assertive


@dataclass
class HighContrast:
    """High contrast mode settings"""
    enabled: bool = False
    contrast_level: str = "high"  # normal, high, maximum
    increase_border_width: bool = True
    increase_text_size: bool = True
    text_size_multiplier: float = 1.2


@dataclass
class KeyboardNavigation:
    """Keyboard navigation settings"""
    visible_focus_indicator: bool = True
    focus_indicator_width: int = 2
    focus_indicator_color: str = "#2196F3"
    trap_focus_in_modals: bool = True
    skip_links_enabled: bool = True
    arrow_key_navigation: bool = True


class AccessibilityManager:
    """
    Manages accessibility features.
    """
    
    def __init__(self):
        self._screen_reader = ScreenReader()
        self._high_contrast = HighContrast()
        self._keyboard_navigation = KeyboardNavigation()
        
        # Reduced motion
        self._reduce_motion: bool = False
        
        # Text size
        self._text_size_multiplier: float = 1.0
        
        # Listeners
        self._listeners: List[Callable] = []
    
    # ========== Screen Reader ==========
    
    def get_screen_reader(self) -> ScreenReader:
        """Get screen reader settings"""
        return self._screen_reader
    
    def set_screen_reader_enabled(self, enabled: bool) -> None:
        """Enable/disable screen reader"""
        self._screen_reader.enabled = enabled
        self._notify_change("screen_reader")
    
    def announce(self, message: str, priority: str = "polite") -> None:
        """Announce a message to screen readers"""
        if self._screen_reader.enabled:
            logger.debug(f"Screen reader announcement ({priority}): {message}")
            # In a real implementation, this would use ARIA live regions
            self._notify_change("announcement", {"message": message, "priority": priority})
    
    # ========== High Contrast ==========
    
    def get_high_contrast(self) -> HighContrast:
        """Get high contrast settings"""
        return self._high_contrast
    
    def set_high_contrast_enabled(self, enabled: bool) -> None:
        """Enable/disable high contrast mode"""
        self._high_contrast.enabled = enabled
        self._notify_change("high_contrast")
    
    # ========== Keyboard Navigation ==========
    
    def get_keyboard_navigation(self) -> KeyboardNavigation:
        """Get keyboard navigation settings"""
        return self._keyboard_navigation
    
    # ========== Reduced Motion ==========
    
    def get_reduce_motion(self) -> bool:
        """Get reduce motion setting"""
        return self._reduce_motion
    
    def set_reduce_motion(self, enabled: bool) -> None:
        """Enable/disable reduced motion"""
        self._reduce_motion = enabled
        self._notify_change("reduce_motion")
    
    # ========== Text Size ==========
    
    def get_text_size_multiplier(self) -> float:
        """Get text size multiplier"""
        return self._text_size_multiplier
    
    def set_text_size_multiplier(self, multiplier: float) -> None:
        """Set text size multiplier"""
        self._text_size_multiplier = max(0.5, min(2.0, multiplier))
        self._notify_change("text_size")
    
    def increase_text_size(self) -> None:
        """Increase text size by one step"""
        self.set_text_size_multiplier(self._text_size_multiplier + 0.1)
    
    def decrease_text_size(self) -> None:
        """Decrease text size by one step"""
        self.set_text_size_multiplier(self._text_size_multiplier - 0.1)
    
    # ========== Preferences Export ==========
    
    def export_preferences(self) -> Dict[str, Any]:
        """Export accessibility preferences"""
        return {
            "screen_reader": self._screen_reader.__dict__,
            "high_contrast": self._high_contrast.__dict__,
            "keyboard_navigation": self._keyboard_navigation.__dict__,
            "reduce_motion": self._reduce_motion,
            "text_size_multiplier": self._text_size_multiplier,
        }
    
    def import_preferences(self, prefs: Dict[str, Any]) -> None:
        """Import accessibility preferences"""
        if "screen_reader" in prefs:
            for key, value in prefs["screen_reader"].items():
                if hasattr(self._screen_reader, key):
                    setattr(self._screen_reader, key, value)
        
        if "high_contrast" in prefs:
            for key, value in prefs["high_contrast"].items():
                if hasattr(self._high_contrast, key):
                    setattr(self._high_contrast, key, value)
        
        if "reduce_motion" in prefs:
            self._reduce_motion = prefs["reduce_motion"]
        
        if "text_size_multiplier" in prefs:
            self._text_size_multiplier = prefs["text_size_multiplier"]
        
        self._notify_change("preferences_imported")
    
    # ========== Listeners ==========
    
    def on_change(self, callback: Callable) -> None:
        """Register change listener"""
        self._listeners.append(callback)
    
    def _notify_change(self, change_type: str, data: Any = None) -> None:
        """Notify listeners of changes"""
        for callback in self._listeners:
            try:
                callback(change_type, data)
            except Exception as e:
                logger.error(f"Accessibility listener error: {e}")
