"""
Tests for UX modules: Dashboard, Search, Themes, Notifications
"""

import unittest
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ux.dashboard import (
    DashboardWidget, DashboardLayout, Dashboard, DashboardManager,
    DEFAULT_WIDGET_TYPES
)
from ux.search import (
    SearchResultType, SearchResult, FilterCriteria, SavedSearch, GlobalSearch
)
from ux.themes import (
    ColorPalette, Typography, Theme, DefaultThemes, ThemeManager
)
from ux.notifications import (
    NotificationPriority, NotificationType, Notification, NotificationCenter
)


class TestDashboardWidget(unittest.TestCase):
    """Test DashboardWidget functionality"""
    
    def test_widget_creation(self):
        """Test creating a widget"""
        widget = DashboardWidget(
            widget_id="w1",
            widget_type="chart",
            title="Price Chart"
        )
        
        self.assertEqual(widget.widget_id, "w1")
        self.assertEqual(widget.widget_type, "chart")
        self.assertEqual(widget.title, "Price Chart")
        self.assertTrue(widget.is_visible)
        self.assertEqual(widget.x, 0)
        self.assertEqual(widget.y, 0)
    
    def test_widget_to_dict(self):
        """Test widget serialization"""
        widget = DashboardWidget(
            widget_id="w1",
            widget_type="chart",
            title="Price Chart",
            width=4,
            height=3
        )
        
        data = widget.to_dict()
        
        self.assertEqual(data["widget_id"], "w1")
        self.assertEqual(data["widget_type"], "chart")
        self.assertEqual(data["title"], "Price Chart")
        self.assertEqual(data["position"]["w"], 4)
        self.assertEqual(data["position"]["h"], 3)


class TestDashboard(unittest.TestCase):
    """Test Dashboard functionality"""
    
    def test_dashboard_creation(self):
        """Test creating a dashboard"""
        dashboard = Dashboard(
            dashboard_id="d1",
            name="My Dashboard"
        )
        
        self.assertEqual(dashboard.dashboard_id, "d1")
        self.assertEqual(dashboard.name, "My Dashboard")
        self.assertEqual(len(dashboard.widgets), 0)
    
    def test_add_widget(self):
        """Test adding widgets to dashboard"""
        dashboard = Dashboard(dashboard_id="d1", name="Test")
        widget = DashboardWidget(
            widget_id="w1",
            widget_type="chart",
            title="Chart"
        )
        
        dashboard.add_widget(widget)
        
        self.assertEqual(len(dashboard.widgets), 1)
        self.assertEqual(dashboard.widgets[0].widget_id, "w1")
    
    def test_remove_widget(self):
        """Test removing widgets"""
        dashboard = Dashboard(dashboard_id="d1", name="Test")
        widget = DashboardWidget(
            widget_id="w1",
            widget_type="chart",
            title="Chart"
        )
        dashboard.add_widget(widget)
        
        removed = dashboard.remove_widget("w1")
        
        self.assertEqual(len(dashboard.widgets), 0)
        self.assertIsNotNone(removed)
    
    def test_get_widget(self):
        """Test getting widget by ID"""
        dashboard = Dashboard(dashboard_id="d1", name="Test")
        widget = DashboardWidget(
            widget_id="w1",
            widget_type="chart",
            title="Chart"
        )
        dashboard.add_widget(widget)
        
        found = dashboard.get_widget("w1")
        
        self.assertIsNotNone(found)
        self.assertEqual(found.title, "Chart")
    
    def test_update_widget(self):
        """Test updating widget properties"""
        dashboard = Dashboard(dashboard_id="d1", name="Test")
        widget = DashboardWidget(
            widget_id="w1",
            widget_type="chart",
            title="Chart"
        )
        dashboard.add_widget(widget)
        
        dashboard.update_widget("w1", {"title": "Updated Chart"})
        
        self.assertEqual(dashboard.get_widget("w1").title, "Updated Chart")
    
    def test_reorder_widgets(self):
        """Test reordering widgets"""
        dashboard = Dashboard(dashboard_id="d1", name="Test")
        dashboard.add_widget(DashboardWidget("w1", "chart", "Chart 1"))
        dashboard.add_widget(DashboardWidget("w2", "table", "Chart 2"))
        dashboard.add_widget(DashboardWidget("w3", "metric", "Chart 3"))
        
        dashboard.reorder_widgets(["w3", "w1", "w2"])
        
        self.assertEqual(dashboard.widgets[0].widget_id, "w3")
        self.assertEqual(dashboard.widgets[1].widget_id, "w1")
        self.assertEqual(dashboard.widgets[2].widget_id, "w2")


class TestDashboardManager(unittest.TestCase):
    """Test DashboardManager functionality"""
    
    def setUp(self):
        self.manager = DashboardManager()
    
    def test_create_dashboard(self):
        """Test creating a dashboard via manager"""
        dashboard = self.manager.create_dashboard("Trading")
        
        self.assertIsNotNone(dashboard)
        self.assertEqual(dashboard.name, "Trading")
        self.assertIn(dashboard.dashboard_id, self.manager._dashboards)
    
    def test_get_dashboard(self):
        """Test getting dashboard by ID"""
        created = self.manager.create_dashboard("Trading")
        
        retrieved = self.manager.get_dashboard(created.dashboard_id)
        
        self.assertEqual(retrieved.dashboard_id, created.dashboard_id)
    
    def test_get_all_dashboards(self):
        """Test getting all dashboards"""
        self.manager.create_dashboard("Dashboard 1")
        self.manager.create_dashboard("Dashboard 2")
        
        all_dashboards = self.manager.get_all_dashboards()
        
        self.assertEqual(len(all_dashboards), 2)
    
    def test_delete_dashboard(self):
        """Test deleting dashboard"""
        dashboard = self.manager.create_dashboard("Trading")
        
        self.manager.delete_dashboard(dashboard.dashboard_id)
        
        self.assertIsNone(self.manager.get_dashboard(dashboard.dashboard_id))
    
    def test_duplicate_dashboard(self):
        """Test duplicating dashboard"""
        original = self.manager.create_dashboard("Original")
        original.add_widget(DashboardWidget("w1", "chart", "Chart"))
        
        duplicate = self.manager.duplicate_dashboard(original.dashboard_id)
        
        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate.name, "Original (Copy)")
        self.assertEqual(len(duplicate.widgets), 1)
    
    def test_add_widget_to_dashboard(self):
        """Test adding widget via manager"""
        dashboard = self.manager.create_dashboard("Trading")
        
        widget = self.manager.add_widget(
            dashboard.dashboard_id,
            "chart",
            "Price Chart"
        )
        
        self.assertIsNotNone(widget)
        self.assertEqual(widget.title, "Price Chart")


class TestSearchResult(unittest.TestCase):
    """Test SearchResult functionality"""
    
    def test_search_result_creation(self):
        """Test creating a search result"""
        result = SearchResult(
            result_id="r1",
            type=SearchResultType.TRADE,
            title="BTC Trade",
            description="Long position on BTC"
        )
        
        self.assertEqual(result.result_id, "r1")
        self.assertEqual(result.type, SearchResultType.TRADE)
        self.assertEqual(result.title, "BTC Trade")
    
    def test_search_result_to_dict(self):
        """Test search result serialization"""
        result = SearchResult(
            result_id="r1",
            type=SearchResultType.TRADE,
            title="BTC Trade",
            description="Long position",
            score=0.95
        )
        
        data = result.to_dict()
        
        self.assertEqual(data["result_id"], "r1")
        self.assertEqual(data["type"], "trade")
        self.assertEqual(data["score"], 0.95)


class TestFilterCriteria(unittest.TestCase):
    """Test FilterCriteria functionality"""
    
    def test_equals_filter(self):
        """Test equals filter"""
        filter_criteria = FilterCriteria("status", "eq", "active")
        
        self.assertTrue(filter_criteria.matches({"status": "active"}))
        self.assertFalse(filter_criteria.matches({"status": "inactive"}))
    
    def test_contains_filter(self):
        """Test contains filter"""
        filter_criteria = FilterCriteria("name", "contains", "test")
        
        self.assertTrue(filter_criteria.matches({"name": "test_widget"}))
        self.assertFalse(filter_criteria.matches({"name": "widget"}))
    
    def test_gt_filter(self):
        """Test greater than filter"""
        filter_criteria = FilterCriteria("amount", "gt", 100)
        
        self.assertTrue(filter_criteria.matches({"amount": 150}))
        self.assertFalse(filter_criteria.matches({"amount": 50}))


class TestGlobalSearch(unittest.TestCase):
    """Test GlobalSearch functionality"""
    
    def setUp(self):
        self.search = GlobalSearch()
    
    def test_index_items(self):
        """Test indexing items"""
        items = [
            {"id": "1", "title": "BTC Trade", "description": "Long position"},
            {"id": "2", "title": "ETH Trade", "description": "Short position"}
        ]
        
        self.search.index(SearchResultType.TRADE, items)
        
        self.assertIn(SearchResultType.TRADE, self.search._indexes)
        self.assertEqual(len(self.search._indexes[SearchResultType.TRADE]), 2)
    
    def test_add_to_index(self):
        """Test adding single item to index"""
        item = {"id": "1", "title": "New Trade"}
        
        self.search.add_to_index(SearchResultType.TRADE, item)
        
        self.assertEqual(len(self.search._indexes[SearchResultType.TRADE]), 1)
    
    def test_search_basic(self):
        """Test basic search"""
        self.search.index(SearchResultType.TRADE, [
            {"id": "1", "title": "BTC Trade", "symbol": "BTCUSD"},
            {"id": "2", "title": "ETH Trade", "symbol": "ETHUSD"}
        ])
        
        results = self.search.search("BTC")
        
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].title, "BTC Trade")
    
    def test_search_with_type_filter(self):
        """Test search filtering by type"""
        self.search.index(SearchResultType.TRADE, [
            {"id": "1", "title": "BTC Trade"}
        ])
        self.search.index(SearchResultType.STRATEGY, [
            {"id": "2", "title": "BTC Strategy"}
        ])
        
        results = self.search.search("BTC", types=[SearchResultType.TRADE])
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].type, SearchResultType.TRADE)
    
    def test_save_and_execute_search(self):
        """Test saving and executing saved searches"""
        self.search.index(SearchResultType.TRADE, [
            {"id": "1", "title": "BTC Trade"}
        ])
        
        saved = self.search.save_search("BTC Trades", "BTC", icon="chart")
        
        self.assertIsNotNone(saved)
        self.assertEqual(saved.name, "BTC Trades")
        
        results = self.search.execute_saved_search(saved.search_id)
        
        self.assertGreater(len(results), 0)
    
    def test_search_history(self):
        """Test search history recording"""
        self.search.index(SearchResultType.TRADE, [
            {"id": "1", "title": "BTC"}
        ])
        
        self.search.search("BTC")
        self.search.search("ETH")
        
        history = self.search.get_history()
        
        self.assertEqual(len(history), 2)


class TestTheme(unittest.TestCase):
    """Test Theme functionality"""
    
    def test_color_palette_creation(self):
        """Test creating a color palette"""
        palette = ColorPalette(name="custom")
        
        self.assertEqual(palette.name, "custom")
        self.assertEqual(palette.primary, "#2196F3")
    
    def test_color_palette_to_dict(self):
        """Test color palette serialization"""
        palette = ColorPalette(name="custom")
        
        data = palette.to_dict()
        
        self.assertEqual(data["name"], "custom")
        self.assertEqual(data["primary"], "#2196F3")
    
    def test_theme_creation(self):
        """Test creating a theme"""
        theme = Theme(
            theme_id="custom",
            name="Custom Theme",
            is_dark=True,
            colors=ColorPalette(name="custom")
        )
        
        self.assertEqual(theme.theme_id, "custom")
        self.assertTrue(theme.is_dark)
    
    def test_theme_to_css_variables(self):
        """Test CSS variables generation"""
        theme = Theme(
            theme_id="custom",
            name="Custom",
            colors=ColorPalette(name="custom")
        )
        
        css = theme.to_css_variables()
        
        self.assertIn("--color-primary", css)
        self.assertIn("--font-family", css)


class TestDefaultThemes(unittest.TestCase):
    """Test DefaultThemes"""
    
    def test_dark_theme(self):
        """Test dark theme"""
        theme = DefaultThemes.dark()
        
        self.assertEqual(theme.theme_id, "dark")
        self.assertTrue(theme.is_dark)
        self.assertEqual(theme.colors.background, "#121212")
    
    def test_light_theme(self):
        """Test light theme"""
        theme = DefaultThemes.light()
        
        self.assertEqual(theme.theme_id, "light")
        self.assertFalse(theme.is_dark)
        self.assertEqual(theme.colors.background, "#FAFAFA")
    
    def test_high_contrast_theme(self):
        """Test high contrast theme"""
        theme = DefaultThemes.high_contrast()
        
        self.assertEqual(theme.theme_id, "high_contrast")
        self.assertTrue(theme.is_dark)


class TestThemeManager(unittest.TestCase):
    """Test ThemeManager functionality"""
    
    def setUp(self):
        self.manager = ThemeManager()
    
    def test_initialization(self):
        """Test manager initializes with defaults"""
        themes = self.manager.get_all_themes()
        
        self.assertEqual(len(themes), 3)
        self.assertIsNotNone(self.manager.get_current_theme())
    
    def test_get_theme(self):
        """Test getting theme by ID"""
        theme = self.manager.get_theme("dark")
        
        self.assertIsNotNone(theme)
        self.assertEqual(theme.theme_id, "dark")
    
    def test_set_current_theme(self):
        """Test setting current theme"""
        result = self.manager.set_current_theme("light")
        
        self.assertTrue(result)
        self.assertEqual(self.manager._current_theme_id, "light")
    
    def test_register_custom_theme(self):
        """Test registering custom theme"""
        custom = Theme(theme_id="custom", name="Custom Dark", is_dark=True, colors=ColorPalette(name="custom"))
        
        self.manager.register_theme(custom)
        
        self.assertIsNotNone(self.manager.get_theme("custom"))
    
    def test_create_custom_theme(self):
        """Test creating custom theme from base"""
        custom = self.manager.create_custom_theme(
            "My Theme",
            base_theme_id="dark",
            overrides={"primary": "#FF0000"}
        )
        
        self.assertIsNotNone(custom)
        self.assertEqual(custom.colors.primary, "#FF0000")


class TestNotification(unittest.TestCase):
    """Test Notification functionality"""
    
    def test_notification_creation(self):
        """Test creating a notification"""
        notification = Notification(
            notification_id="n1",
            title="Trade Alert",
            message="BTC price dropped",
            notification_type=NotificationType.ALERT,
            priority=NotificationPriority.HIGH
        )
        
        self.assertEqual(notification.title, "Trade Alert")
        self.assertEqual(notification.notification_type, NotificationType.ALERT)
        self.assertFalse(notification.is_read)
    
    def test_mark_read(self):
        """Test marking notification as read"""
        notification = Notification(
            notification_id="n1",
            title="Test",
            message="Test",
            notification_type=NotificationType.INFO,
            priority=NotificationPriority.NORMAL
        )
        
        notification.mark_read()
        
        self.assertTrue(notification.is_read)
    
    def test_dismiss(self):
        """Test dismissing notification"""
        notification = Notification(
            notification_id="n1",
            title="Test",
            message="Test",
            notification_type=NotificationType.INFO,
            priority=NotificationPriority.NORMAL
        )
        
        notification.dismiss()
        
        self.assertTrue(notification.is_dismissed)
    
    def test_expiration(self):
        """Test notification expiration"""
        notification = Notification(
            notification_id="n1",
            title="Test",
            message="Test",
            notification_type=NotificationType.INFO,
            priority=NotificationPriority.NORMAL,
            expires_at=time.time() - 100  # Expired
        )
        
        self.assertTrue(notification.is_expired())


class TestNotificationCenter(unittest.TestCase):
    """Test NotificationCenter functionality"""
    
    def setUp(self):
        self.center = NotificationCenter(max_notifications=10)
    
    def test_add_notification(self):
        """Test adding a notification"""
        notification = self.center.add(
            title="Test Alert",
            message="This is a test",
            notification_type=NotificationType.INFO
        )
        
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, "Test Alert")
    
    def test_info_convenience_method(self):
        """Test info() convenience method"""
        notification = self.center.info("Info", "Information message")
        
        self.assertEqual(notification.notification_type, NotificationType.INFO)
    
    def test_success_convenience_method(self):
        """Test success() convenience method"""
        notification = self.center.success("Success", "Operation completed")
        
        self.assertEqual(notification.notification_type, NotificationType.SUCCESS)
    
    def test_warning_convenience_method(self):
        """Test warning() convenience method"""
        notification = self.center.warning("Warning", "Something is wrong")
        
        self.assertEqual(notification.notification_type, NotificationType.WARNING)
    
    def test_error_convenience_method(self):
        """Test error() convenience method"""
        notification = self.center.error("Error", "An error occurred")
        
        self.assertEqual(notification.notification_type, NotificationType.ERROR)
    
    def test_trade_convenience_method(self):
        """Test trade() convenience method"""
        notification = self.center.trade("Trade Update", "Position closed")
        
        self.assertEqual(notification.notification_type, NotificationType.TRADE)
    
    def test_get_notifications(self):
        """Test getting notifications"""
        self.center.add("Test 1", "Message", NotificationType.INFO)
        self.center.add("Test 2", "Message", NotificationType.INFO)
        
        notifications = self.center.get()
        
        self.assertEqual(len(notifications), 2)
    
    def test_get_unread_notifications(self):
        """Test getting unread notifications"""
        self.center.add("Test 1", "Message")
        n2 = self.center.add("Test 2", "Message")
        n2.mark_read()
        
        unread = self.center.get(unread_only=True)
        
        self.assertEqual(len(unread), 1)
    
    def test_mark_read(self):
        """Test marking notification as read"""
        n1 = self.center.add("Test", "Message")
        
        self.center.mark_read(n1.notification_id)
        
        self.assertTrue(n1.is_read)
    
    def test_mark_all_read(self):
        """Test marking all as read"""
        self.center.add("Test 1", "Message")
        self.center.add("Test 2", "Message")
        
        self.center.mark_all_read()
        
        for n in self.center.get():
            self.assertTrue(n.is_read)
    
    def test_dismiss_notification(self):
        """Test dismissing notification"""
        n1 = self.center.add("Test", "Message")
        
        self.center.dismiss(n1.notification_id)
        
        self.assertTrue(n1.is_dismissed)
    
    def test_clear_all(self):
        """Test clearing all notifications"""
        self.center.add("Test 1", "Message")
        self.center.add("Test 2", "Message")
        
        self.center.clear_all()
        
        self.assertEqual(len(self.center.get()), 0)
    
    def test_unread_count(self):
        """Test getting unread count"""
        self.center.add("Test 1", "Message")
        self.center.add("Test 2", "Message")
        
        count = self.center.get_unread_count()
        
        self.assertEqual(count, 2)
    
    def test_max_notifications_limit(self):
        """Test max notifications limit"""
        center = NotificationCenter(max_notifications=3)
        
        for i in range(5):
            center.add(f"Test {i}", "Message")
        
        notifications = center.get()
        
        self.assertEqual(len(notifications), 3)


if __name__ == "__main__":
    unittest.main()
