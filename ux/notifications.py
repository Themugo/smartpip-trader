"""
Notifications System
==================

Notification center and notification management.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(Enum):
    """Notification types"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    TRADE = "trade"
    ALERT = "alert"
    SYSTEM = "system"


@dataclass
class Notification:
    """A notification"""
    notification_id: str
    title: str
    message: str
    notification_type: NotificationType
    priority: NotificationPriority
    
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    
    # Actions
    actions: List[Dict[str, Any]] = field(default_factory=list)  # [{label, action}]
    
    # Source
    source: str = ""  # Component or system that created it
    source_id: str = ""  # ID of the related entity
    
    # State
    is_read: bool = False
    is_dismissed: bool = False
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if notification has expired"""
        if self.expires_at:
            return time.time() > self.expires_at
        return False
    
    def dismiss(self) -> None:
        """Dismiss the notification"""
        self.is_dismissed = True
    
    def mark_read(self) -> None:
        """Mark as read"""
        self.is_read = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "title": self.title,
            "message": self.message,
            "type": self.notification_type.value,
            "priority": self.priority.value,
            "created_at": self.created_at,
            "is_read": self.is_read,
            "source": self.source,
        }


class NotificationCenter:
    """
    Central notification management.
    """
    
    def __init__(self, max_notifications: int = 100):
        self._notifications: List[Notification] = []
        self._max_notifications = max_notifications
        self._listeners: List[Callable] = []
        self._filters: Dict[str, Callable] = {}
    
    def add(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        source: str = "",
        source_id: str = "",
        actions: Optional[List[Dict[str, Any]]] = None,
        expires_in: Optional[int] = None
    ) -> Notification:
        """Add a new notification"""
        notification = Notification(
            notification_id=str(uuid.uuid4()),
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            source=source,
            source_id=source_id,
            actions=actions or [],
            expires_at=time.time() + expires_in if expires_in else None,
        )
        
        self._notifications.insert(0, notification)
        
        # Trim old notifications
        while len(self._notifications) > self._max_notifications:
            self._notifications.pop()
        
        self._notify_listeners(notification)
        return notification
    
    def dismiss(self, notification_id: str) -> bool:
        """Dismiss a notification"""
        for n in self._notifications:
            if n.notification_id == notification_id:
                n.dismiss()
                return True
        return False
    
    def mark_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        for n in self._notifications:
            if n.notification_id == notification_id:
                n.mark_read()
                return True
        return False
    
    def mark_all_read(self) -> None:
        """Mark all notifications as read"""
        for n in self._notifications:
            n.mark_read()
    
    def get(
        self,
        include_dismissed: bool = False,
        type_filter: Optional[NotificationType] = None,
        priority_filter: Optional[NotificationPriority] = None,
        source_filter: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications with optional filters"""
        results = self._notifications
        
        # Apply filters
        if not include_dismissed:
            results = [n for n in results if not n.is_dismissed]
        
        if type_filter:
            results = [n for n in results if n.notification_type == type_filter]
        
        if priority_filter:
            results = [n for n in results if n.priority == priority_filter]
        
        if source_filter:
            results = [n for n in results if n.source == source_filter]
        
        if unread_only:
            results = [n for n in results if not n.is_read]
        
        # Remove expired
        results = [n for n in results if not n.is_expired()]
        
        return results[:limit]
    
    def get_unread_count(self) -> int:
        """Get count of unread notifications"""
        return len([n for n in self._notifications if not n.is_read and not n.is_dismissed])
    
    def clear_all(self) -> None:
        """Clear all notifications"""
        self._notifications.clear()
    
    def clear_by_type(self, notification_type: NotificationType) -> int:
        """Clear notifications of a specific type"""
        original = len(self._notifications)
        self._notifications = [
            n for n in self._notifications
            if n.notification_type != notification_type
        ]
        return original - len(self._notifications)
    
    # ========== Convenience Methods ==========
    
    def info(self, title: str, message: str, **kwargs) -> Notification:
        """Add info notification"""
        return self.add(title, message, NotificationType.INFO, **kwargs)
    
    def success(self, title: str, message: str, **kwargs) -> Notification:
        """Add success notification"""
        return self.add(title, message, NotificationType.SUCCESS, **kwargs)
    
    def warning(self, title: str, message: str, **kwargs) -> Notification:
        """Add warning notification"""
        return self.add(title, message, NotificationType.WARNING, NotificationPriority.HIGH, **kwargs)
    
    def error(self, title: str, message: str, **kwargs) -> Notification:
        """Add error notification"""
        return self.add(title, message, NotificationType.ERROR, NotificationPriority.HIGH, **kwargs)
    
    def trade(self, title: str, message: str, **kwargs) -> Notification:
        """Add trade notification"""
        return self.add(title, message, NotificationType.TRADE, NotificationPriority.NORMAL, **kwargs)
    
    def alert(self, title: str, message: str, **kwargs) -> Notification:
        """Add alert notification"""
        return self.add(title, message, NotificationType.ALERT, NotificationPriority.CRITICAL, **kwargs)
    
    # ========== Listeners ==========
    
    def on_notification(self, callback: Callable[[Notification], None]) -> None:
        """Register notification listener"""
        self._listeners.append(callback)
    
    def _notify_listeners(self, notification: Notification) -> None:
        """Notify listeners of new notification"""
        for callback in self._listeners:
            try:
                callback(notification)
            except Exception as e:
                logger.error(f"Notification listener error: {e}")
