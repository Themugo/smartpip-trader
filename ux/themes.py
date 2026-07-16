"""
Theme System
===========

Customizable themes and color palettes.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ColorPalette:
    """Color palette for a theme"""
    name: str
    
    # Primary colors
    primary: str = "#2196F3"  # Blue
    primary_variant: str = "#1976D2"
    on_primary: str = "#FFFFFF"
    
    # Secondary colors
    secondary: str = "#FF9800"  # Orange
    secondary_variant: str = "#F57C00"
    on_secondary: str = "#000000"
    
    # Background colors
    background: str = "#121212"
    surface: str = "#1E1E1E"
    surface_variant: str = "#2D2D2D"
    on_background: str = "#FFFFFF"
    on_surface: str = "#FFFFFF"
    
    # Status colors
    success: str = "#4CAF50"  # Green
    warning: str = "#FFC107"  # Amber
    error: str = "#F44336"    # Red
    info: str = "#2196F3"     # Blue
    
    # Text colors
    text_primary: str = "#FFFFFF"
    text_secondary: str = "#B0B0B0"
    text_disabled: str = "#606060"
    text_hint: str = "#808080"
    
    # Border colors
    border: str = "#3D3D3D"
    border_focus: str = "#2196F3"
    
    # Chart colors
    chart_1: str = "#2196F3"
    chart_2: str = "#4CAF50"
    chart_3: str = "#FF9800"
    chart_4: str = "#9C27B0"
    chart_5: str = "#00BCD4"
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "primary": self.primary,
            "secondary": self.secondary,
            "background": self.background,
            "surface": self.surface,
            "success": self.success,
            "warning": self.warning,
            "error": self.error,
            "text_primary": self.text_primary,
            "text_secondary": self.text_secondary,
        }


@dataclass
class Typography:
    """Typography configuration"""
    font_family: str = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    mono_font_family: str = "JetBrains Mono, Consolas, monospace"
    
    # Font sizes
    font_size_xs: str = "0.75rem"   # 12px
    font_size_sm: str = "0.875rem"   # 14px
    font_size_base: str = "1rem"     # 16px
    font_size_lg: str = "1.125rem"   # 18px
    font_size_xl: str = "1.25rem"    # 20px
    font_size_2xl: str = "1.5rem"    # 24px
    font_size_3xl: str = "1.875rem" # 30px
    font_size_4xl: str = "2.25rem"   # 36px
    
    # Font weights
    font_weight_light: int = 300
    font_weight_normal: int = 400
    font_weight_medium: int = 500
    font_weight_semibold: int = 600
    font_weight_bold: int = 700
    
    # Line heights
    line_height_tight: float = 1.25
    line_height_normal: float = 1.5
    line_height_relaxed: float = 1.75
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "font_family": self.font_family,
            "font_size_base": self.font_size_base,
            "font_weight_normal": self.font_weight_normal,
            "line_height": self.line_height_normal,
        }


@dataclass
class Theme:
    """Complete theme configuration"""
    theme_id: str
    name: str
    is_dark: bool = True
    
    # Colors
    colors: ColorPalette = field(default_factory=ColorPalette)
    
    # Typography
    typography: Typography = field(default_factory=Typography)
    
    # Spacing
    spacing_unit: int = 4
    border_radius: str = "4px"
    border_radius_lg: str = "8px"
    border_radius_full: str = "9999px"
    
    # Shadows
    shadow_sm: str = "0 1px 2px rgba(0,0,0,0.3)"
    shadow_md: str = "0 4px 6px rgba(0,0,0,0.3)"
    shadow_lg: str = "0 10px 15px rgba(0,0,0,0.3)"
    shadow_xl: str = "0 20px 25px rgba(0,0,0,0.4)"
    
    # Transitions
    transition_fast: str = "150ms ease"
    transition_normal: str = "250ms ease"
    transition_slow: str = "350ms ease"
    
    # Layout
    sidebar_width: int = 260
    header_height: int = 56
    footer_height: int = 40
    
    # Custom properties (for CSS variables)
    custom_properties: Dict[str, str] = field(default_factory=dict)
    
    def to_css_variables(self) -> str:
        """Generate CSS variables string"""
        css = f"""
        :root {{
            --color-primary: {self.colors.primary};
            --color-secondary: {self.colors.secondary};
            --color-background: {self.colors.background};
            --color-surface: {self.colors.surface};
            --color-success: {self.colors.success};
            --color-warning: {self.colors.warning};
            --color-error: {self.colors.error};
            --color-text-primary: {self.colors.text_primary};
            --color-text-secondary: {self.colors.text_secondary};
            --color-border: {self.colors.border};
            
            --font-family: {self.typography.font_family};
            --font-size-base: {self.typography.font_size_base};
            
            --sidebar-width: {self.sidebar_width}px;
            --header-height: {self.header_height}px;
            
            --border-radius: {self.border_radius};
            --border-radius-lg: {self.border_radius_lg};
            
            --shadow-sm: {self.shadow_sm};
            --shadow-md: {self.shadow_md};
            --shadow-lg: {self.shadow_lg};
        }}
        """
        
        # Add custom properties
        for key, value in self.custom_properties.items():
            css += f"            --{key}: {value};\n"
        
        return css + "        }"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "name": self.name,
            "is_dark": self.is_dark,
            "colors": self.colors.to_dict(),
        }


class DefaultThemes:
    """Pre-built themes"""
    
    @staticmethod
    def dark() -> Theme:
        """Dark theme (default)"""
        return Theme(
            theme_id="dark",
            name="Dark",
            is_dark=True,
            colors=ColorPalette(name="dark"),
            custom_properties={
                "scrollbar-color": "#3D3D3D #1E1E1E",
            }
        )
    
    @staticmethod
    def light() -> Theme:
        """Light theme"""
        colors = ColorPalette(name="light")
        colors.background = "#FAFAFA"
        colors.surface = "#FFFFFF"
        colors.on_background = "#1A1A1A"
        colors.on_surface = "#1A1A1A"
        colors.text_primary = "#1A1A1A"
        colors.text_secondary = "#666666"
        colors.border = "#E0E0E0"
        colors.shadow_sm = "0 1px 2px rgba(0,0,0,0.1)"
        colors.shadow_md = "0 4px 6px rgba(0,0,0,0.1)"
        
        return Theme(
            theme_id="light",
            name="Light",
            is_dark=False,
            colors=colors,
            custom_properties={
                "scrollbar-color": "#BDBDBD #F5F5F5",
            }
        )
    
    @staticmethod
    def high_contrast() -> Theme:
        """High contrast theme for accessibility"""
        colors = ColorPalette(name="high_contrast")
        colors.primary = "#00BFFF"
        colors.secondary = "#FFD700"
        colors.background = "#000000"
        colors.surface = "#1A1A1A"
        colors.text_primary = "#FFFFFF"
        colors.text_secondary = "#FFFF00"
        colors.success = "#00FF00"
        colors.error = "#FF0000"
        colors.warning = "#FFFF00"
        colors.border = "#FFFFFF"
        
        return Theme(
            theme_id="high_contrast",
            name="High Contrast",
            is_dark=True,
            colors=colors,
        )


class ThemeManager:
    """
    Manages themes and user preferences.
    """
    
    def __init__(self):
        self._themes: Dict[str, Theme] = {}
        self._current_theme_id: Optional[str] = None
        self._listeners: List[Callable] = []
        
        # Initialize default themes
        self._initialize_default_themes()
    
    def _initialize_default_themes(self) -> None:
        """Initialize default themes"""
        self._themes["dark"] = DefaultThemes.dark()
        self._themes["light"] = DefaultThemes.light()
        self._themes["high_contrast"] = DefaultThemes.high_contrast()
        self._current_theme_id = "dark"
    
    # ========== Theme Management ==========
    
    def register_theme(self, theme: Theme) -> None:
        """Register a custom theme"""
        self._themes[theme.theme_id] = theme
        logger.info(f"Registered theme: {theme.name}")
    
    def unregister_theme(self, theme_id: str) -> bool:
        """Unregister a theme"""
        if theme_id in ["dark", "light", "high_contrast"]:
            return False  # Can't remove defaults
        return self._themes.pop(theme_id, None) is not None
    
    def get_theme(self, theme_id: str) -> Optional[Theme]:
        """Get a theme by ID"""
        return self._themes.get(theme_id)
    
    def get_current_theme(self) -> Optional[Theme]:
        """Get the current theme"""
        if self._current_theme_id:
            return self._themes.get(self._current_theme_id)
        return None
    
    def get_all_themes(self) -> List[Theme]:
        """Get all available themes"""
        return list(self._themes.values())
    
    def set_current_theme(self, theme_id: str) -> bool:
        """Set the current theme"""
        if theme_id not in self._themes:
            return False
        
        self._current_theme_id = theme_id
        self._notify_listeners()
        logger.info(f"Switched to theme: {theme_id}")
        return True
    
    # ========== Customization ==========
    
    def create_custom_theme(
        self,
        name: str,
        base_theme_id: str = "dark",
        overrides: Optional[Dict[str, Any]] = None
    ) -> Theme:
        """Create a custom theme based on an existing one"""
        base = self._themes.get(base_theme_id)
        if not base:
            base = DefaultThemes.dark()
        
        colors = ColorPalette(
            name=name,
            primary=overrides.get("primary", base.colors.primary) if overrides else base.colors.primary,
        )
        
        theme = Theme(
            theme_id=str(uuid.uuid4()),
            name=name,
            is_dark=base.is_dark,
            colors=colors,
        )
        
        if overrides:
            if "colors" in overrides:
                for key, value in overrides["colors"].items():
                    if hasattr(colors, key):
                        setattr(colors, key, value)
            
            if "spacing_unit" in overrides:
                theme.spacing_unit = overrides["spacing_unit"]
            if "border_radius" in overrides:
                theme.border_radius = overrides["border_radius"]
        
        self._themes[theme.theme_id] = theme
        return theme
    
    # ========== Listeners ==========
    
    def on_theme_change(self, callback: Callable[[Theme], None]) -> None:
        """Register a theme change listener"""
        self._listeners.append(callback)
    
    def _notify_listeners(self) -> None:
        """Notify all listeners of theme change"""
        theme = self.get_current_theme()
        if theme:
            for callback in self._listeners:
                try:
                    callback(theme)
                except Exception as e:
                    logger.error(f"Theme listener error: {e}")
    
    # ========== Export ==========
    
    def export_theme(self, theme_id: str) -> Optional[Dict[str, Any]]:
        """Export a theme for sharing"""
        theme = self._themes.get(theme_id)
        if not theme:
            return None
        
        return theme.to_dict()
    
    def import_theme(self, data: Dict[str, Any]) -> Theme:
        """Import a theme from data"""
        colors = ColorPalette(
            name=data.get("name", "Custom"),
            **{k: v for k, v in data.get("colors", {}).items() if hasattr(ColorPalette, k)}
        )
        
        theme = Theme(
            theme_id=data.get("theme_id", str(uuid.uuid4())),
            name=data.get("name", "Custom"),
            is_dark=data.get("is_dark", True),
            colors=colors,
        )
        
        self._themes[theme.theme_id] = theme
        return theme
