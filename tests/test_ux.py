"""
Tests for UX Platform
==================
"""

import pytest
import time


class TestWorkspace:
    """Tests for workspace management"""
    
    def test_workspace_creation(self):
        """Test creating a workspace"""
        from ux.core import Workspace, Window
        
        workspace = Workspace(
            workspace_id="ws_1",
            name="Test Workspace",
        )
        
        assert workspace.name == "Test Workspace"
        assert workspace.workspace_id == "ws_1"
    
    def test_add_window(self):
        """Test adding a window to workspace"""
        from ux.core import Workspace, Window
        
        workspace = Workspace(workspace_id="ws_1", name="Test")
        window = Window(window_id="win_1", title="Test Window", component="test")
        
        workspace.add_window(window)
        
        assert "win_1" in workspace.windows
        assert workspace.get_window("win_1").title == "Test Window"
    
    def test_window_visibility(self):
        """Test window visibility"""
        from ux.core import Workspace, Window
        
        workspace = Workspace(workspace_id="ws_1", name="Test")
        
        workspace.add_window(Window(window_id="w1", title="W1", component="c", is_visible=True))
        workspace.add_window(Window(window_id="w2", title="W2", component="c", is_visible=False))
        
        visible = workspace.get_visible_windows()
        assert len(visible) == 1


class TestWorkspaceManager:
    """Tests for workspace manager"""
    
    def test_create_workspace(self):
        """Test workspace creation"""
        from ux.workspace import WorkspaceManager
        
        manager = WorkspaceManager()
        workspace = manager.create_workspace("My Workspace")
        
        assert workspace is not None
        assert workspace.name == "My Workspace"
    
    def test_get_workspace(self):
        """Test getting workspace"""
        from ux.workspace import WorkspaceManager
        
        manager = WorkspaceManager()
        created = manager.create_workspace("Test")
        
        retrieved = manager.get_workspace(created.workspace_id)
        assert retrieved is not None
        assert retrieved.workspace_id == created.workspace_id


class TestCommandPalette:
    """Tests for command palette"""
    
    def test_command_creation(self):
        """Test creating a command"""
        from ux.command_palette import Command, CommandCategory
        
        cmd = Command(
            command_id="test_cmd",
            name="Test Command",
            description="A test command",
            category=CommandCategory.ACTION,
            action="test.action",
        )
        
        assert cmd.name == "Test Command"
        assert cmd.is_enabled
    
    def test_command_search(self):
        """Test command searching"""
        from ux.command_palette import CommandPalette
        
        palette = CommandPalette()
        results = palette.search("Go")
        
        assert len(results) > 0
        assert any("Go" in cmd.name for cmd in results)
    
    def test_command_execution(self):
        """Test command execution"""
        from ux.command_palette import Command, CommandCategory
        
        executed = []
        def handler(args):
            executed.append(args)
        
        cmd = Command(
            command_id="test",
            name="Test",
            description="Test",
            category=CommandCategory.ACTION,
            action="test",
            handler=handler,
        )
        
        cmd.execute({"key": "value"})
        assert len(executed) == 1


class TestKeyboardShortcuts:
    """Tests for keyboard shortcuts"""
    
    def test_shortcut_binding(self):
        """Test shortcut binding"""
        from ux.shortcuts import ShortcutBinding
        
        binding = ShortcutBinding(
            binding_id="test",
            shortcut="Ctrl+K",
            action="test.action",
            description="Test shortcut",
        )
        
        assert binding.matches("Ctrl+K")
        assert not binding.matches("Ctrl+L")
    
    def test_shortcut_manager(self):
        """Test shortcut manager"""
        from ux.shortcuts import ShortcutManager
        
        manager = ShortcutManager()
        bindings = manager.get_all_bindings()
        
        assert len(bindings) > 0


class TestThemes:
    """Tests for theme system"""
    
    def test_default_themes(self):
        """Test default themes"""
        from ux.themes import ThemeManager, DefaultThemes
        
        manager = ThemeManager()
        themes = manager.get_all_themes()
        
        assert len(themes) >= 3  # dark, light, high_contrast
    
    def test_theme_switching(self):
        """Test theme switching"""
        from ux.themes import ThemeManager
        
        manager = ThemeManager()
        result = manager.set_current_theme("light")
        
        assert result is True
        assert manager.get_current_theme().theme_id == "light"
    
    def test_css_variables(self):
        """Test CSS variable generation"""
        from ux.themes import DefaultThemes
        
        theme = DefaultThemes.dark()
        css = theme.to_css_variables()
        
        assert "--color-primary" in css
        assert "--font-family" in css


class TestNotifications:
    """Tests for notification system"""
    
    def test_notification_creation(self):
        """Test creating a notification"""
        from ux.notifications import Notification, NotificationType, NotificationPriority
        
        notification = Notification(
            notification_id="notif_1",
            title="Test",
            message="Test message",
            notification_type=NotificationType.INFO,
            priority=NotificationPriority.NORMAL,
        )
        
        assert notification.title == "Test"
        assert not notification.is_read
    
    def test_notification_center(self):
        """Test notification center"""
        from ux.notifications import NotificationCenter, NotificationType
        
        center = NotificationCenter()
        center.add("Title", "Message", NotificationType.INFO)
        
        notifications = center.get()
        assert len(notifications) == 1
    
    def test_notification_filters(self):
        """Test notification filtering"""
        from ux.notifications import NotificationCenter, NotificationType
        
        center = NotificationCenter()
        center.add("Info", "Message", NotificationType.INFO)
        center.add("Error", "Message", NotificationType.ERROR)
        
        errors = center.get(type_filter=NotificationType.ERROR)
        assert len(errors) == 1


class TestGlobalSearch:
    """Tests for global search"""
    
    def test_indexing(self):
        """Test indexing items"""
        from ux.search import GlobalSearch, SearchResultType
        
        search = GlobalSearch()
        search.index(SearchResultType.TRADE, [
            {"id": "1", "title": "BTC Trade", "description": "BTC trade"},
            {"id": "2", "title": "ETH Trade", "description": "ETH trade"},
        ])
        
        assert SearchResultType.TRADE in search._indexes
    
    def test_search(self):
        """Test searching"""
        from ux.search import GlobalSearch, SearchResultType
        
        search = GlobalSearch()
        search.index(SearchResultType.TRADE, [
            {"id": "1", "title": "BTC Trade", "description": "BTC"},
        ])
        
        results = search.search("BTC")
        assert len(results) > 0
    
    def test_saved_search(self):
        """Test saving searches"""
        from ux.search import GlobalSearch
        
        search = GlobalSearch()
        saved = search.save_search("My Search", "BTC")
        
        assert saved.name == "My Search"


class TestAccessibility:
    """Tests for accessibility"""
    
    def test_accessibility_manager(self):
        """Test accessibility manager"""
        from ux.accessibility import AccessibilityManager
        
        manager = AccessibilityManager()
        
        manager.set_screen_reader_enabled(True)
        assert manager.get_screen_reader().enabled is True
        
        manager.set_high_contrast_enabled(True)
        assert manager.get_high_contrast().enabled is True


class TestOnboarding:
    """Tests for onboarding"""
    
    def test_tutorial_creation(self):
        """Test tutorial creation"""
        from ux.onboarding import Tutorial, OnboardingStep
        
        tutorial = Tutorial(
            tutorial_id="test",
            name="Test Tutorial",
            description="A test",
            steps=[
                OnboardingStep(step_id="1", title="Step 1", content="Content 1"),
                OnboardingStep(step_id="2", title="Step 2", content="Content 2"),
            ],
        )
        
        assert len(tutorial.steps) == 2
    
    def test_tutorial_navigation(self):
        """Test tutorial navigation"""
        from ux.onboarding import Tutorial, OnboardingStep
        
        tutorial = Tutorial(
            tutorial_id="test",
            name="Test",
            description="A test tutorial",
            steps=[
                OnboardingStep(step_id="1", title="S1", content="C1"),
                OnboardingStep(step_id="2", title="S2", content="C2"),
            ],
        )
        
        assert tutorial.current_step_index == 0
        tutorial.next_step()
        assert tutorial.current_step_index == 1
        tutorial.previous_step()
        assert tutorial.current_step_index == 0
    
    def test_onboarding_manager(self):
        """Test onboarding manager"""
        from ux.onboarding import OnboardingManager
        
        manager = OnboardingManager()
        tutorials = manager.get_all_tutorials()
        
        assert len(tutorials) >= 1


class TestDashboard:
    """Tests for dashboard system"""
    
    def test_dashboard_creation(self):
        """Test creating a dashboard"""
        from ux.dashboard import Dashboard, DashboardWidget
        
        dashboard = Dashboard(
            dashboard_id="dash_1",
            name="Test Dashboard",
        )
        
        dashboard.add_widget(DashboardWidget(
            widget_id="w1",
            widget_type="chart",
            title="Chart",
        ))
        
        assert len(dashboard.widgets) == 1
    
    def test_dashboard_manager(self):
        """Test dashboard manager"""
        from ux.dashboard import DashboardManager
        
        manager = DashboardManager()
        dashboard = manager.create_dashboard("My Dashboard")
        
        assert dashboard.name == "My Dashboard"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
