"""
Notification SDK
================

SDK for sending notifications and alerts.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from .base import SmartPipSDK, SDKConfig, SDKError, SDKLogger

logger = SDKLogger("notification")


class NotificationChannel(Enum):
    """Notification channel types"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    LOG = "log"


class NotificationPriority(Enum):
    """Notification priority"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """Notification message"""
    title: str
    message: str
    channel: NotificationChannel
    priority: NotificationPriority = NotificationPriority.NORMAL
    recipients: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class NotificationTemplate:
    """Notification template"""
    template_id: str
    name: str
    title_template: str
    message_template: str
    default_channel: NotificationChannel = NotificationChannel.EMAIL
    default_priority: NotificationPriority = NotificationPriority.NORMAL


class NotificationClient(SmartPipSDK):
    """
    Notification client for sending alerts and notifications.
    """
    
    def __init__(self, config: Optional[SDKConfig] = None):
        super().__init__(config)
        self._templates: Dict[str, NotificationTemplate] = {}
        self._channels: Dict[NotificationChannel, Any] = {}
    
    def _on_initialize(self) -> None:
        """Initialize notification client"""
        self._setup_default_channels()
    
    def _setup_default_channels(self) -> None:
        """Setup default notification channels"""
        # Add log channel by default
        self._channels[NotificationChannel.LOG] = self._log_handler
    
    def _log_handler(self, notification: Notification) -> bool:
        """Log notification handler"""
        logger.info(f"Notification: [{notification.priority.value}] {notification.title}")
        return True
    
    def register_channel(self, channel: NotificationChannel, handler: Any) -> None:
        """Register a notification channel handler"""
        self._channels[channel] = handler
        logger.info(f"Registered channel: {channel.value}")
    
    def register_template(self, template: NotificationTemplate) -> None:
        """Register a notification template"""
        self._templates[template.template_id] = template
    
    def send(self, notification: Notification) -> bool:
        """Send a notification"""
        if notification.channel not in self._channels:
            logger.error(f"Channel not registered: {notification.channel}")
            return False
        
        handler = self._channels[notification.channel]
        
        try:
            return handler(notification)
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    def send_alert(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        **metadata
    ) -> bool:
        """Send an alert"""
        notification = Notification(
            title=title,
            message=message,
            channel=NotificationChannel.LOG,
            priority=priority,
            metadata=metadata
        )
        return self.send(notification)
    
    def send_trade_alert(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        pnl: float
    ) -> bool:
        """Send a trade alert"""
        return self.send_alert(
            title=f"Trade Executed: {symbol}",
            message=f"{side.upper()} {quantity} {symbol} @ {price:.2f} | P&L: ${pnl:.2f}",
            metadata={
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "pnl": pnl
            }
        )
    
    def send_risk_alert(
        self,
        alert_type: str,
        message: str,
        details: Dict[str, Any]
    ) -> bool:
        """Send a risk alert"""
        return self.send_alert(
            title=f"Risk Alert: {alert_type}",
            message=message,
            priority=NotificationPriority.HIGH,
            metadata=details
        )
    
    def send_error(
        self,
        error_type: str,
        message: str,
        details: Dict[str, Any]
    ) -> bool:
        """Send an error notification"""
        return self.send_alert(
            title=f"Error: {error_type}",
            message=message,
            priority=NotificationPriority.HIGH,
            metadata=details
        )
    
    def render_template(
        self,
        template_id: str,
        variables: Dict[str, Any]
    ) -> Optional[Notification]:
        """Render a notification from template"""
        template = self._templates.get(template_id)
        if not template:
            return None
        
        title = template.title_template.format(**variables)
        message = template.message_template.format(**variables)
        
        return Notification(
            title=title,
            message=message,
            channel=template.default_channel,
            priority=template.default_priority
        )
