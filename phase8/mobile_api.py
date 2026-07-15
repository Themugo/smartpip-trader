"""
Mobile API - Mobile Companion App Interface

REST API for mobile companion applications.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """Device types"""
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


@dataclass
class Device:
    """Registered mobile device"""
    id: str
    device_type: DeviceType
    device_name: str
    device_token: str  # Push notification token
    
    user_id: str
    is_active: bool = True
    
    # Settings
    notifications_enabled: bool = True
    notification_types: List[str] = field(default_factory=lambda: ["all"])
    
    # Timestamps
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PushNotification:
    """A push notification"""
    id: str
    title: str
    body: str
    
    # Targeting
    user_id: str
    device_ids: List[str] = field(default_factory=list)
    
    # Content
    data: Dict[str, Any] = field(default_factory=dict)
    badge: int = 0
    sound: str = "default"
    
    # Status
    sent_at: Optional[datetime] = None
    delivered: int = 0
    failed: int = 0
    
    created_at: datetime = field(default_factory=datetime.utcnow)


class MobileAPI:
    """
    Mobile API for companion apps.
    
    Features:
    - Device registration
    - Push notifications
    - Secure API endpoints
    - Real-time updates via WebSocket
    - Trade monitoring
    - Risk alerts
    - Account switching
    """
    
    def __init__(self):
        self._devices: Dict[str, Device] = {}
        self._notifications: Dict[str, PushNotification] = {}
        self._api_keys: Dict[str, str] = {}  # api_key -> user_id
    
    # =========================================================================
    # Device Management
    # =========================================================================
    
    def register_device(
        self,
        user_id: str,
        device_type: DeviceType,
        device_name: str,
        device_token: str,
    ) -> Device:
        """Register a mobile device"""
        device = Device(
            id=str(uuid.uuid4()),
            device_type=device_type,
            device_name=device_name,
            device_token=device_token,
            user_id=user_id,
        )
        
        self._devices[device.id] = device
        logger.info(f"Registered device: {device.id}")
        
        return device
    
    def get_user_devices(self, user_id: str) -> List[Device]:
        """Get all devices for a user"""
        return [d for d in self._devices.values() if d.user_id == user_id and d.is_active]
    
    def update_device(
        self,
        device_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Device]:
        """Update device settings"""
        device = self._devices.get(device_id)
        if not device:
            return None
        
        if "notifications_enabled" in updates:
            device.notifications_enabled = updates["notifications_enabled"]
        if "notification_types" in updates:
            device.notification_types = updates["notification_types"]
        
        device.last_active = datetime.utcnow()
        return device
    
    def unregister_device(self, device_id: str) -> bool:
        """Unregister a device"""
        device = self._devices.get(device_id)
        if device:
            device.is_active = False
            return True
        return False
    
    # =========================================================================
    # Push Notifications
    # =========================================================================
    
    def send_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        notification_type: str = "general",
    ) -> PushNotification:
        """Send a push notification to user"""
        # Get user devices
        devices = self.get_user_devices(user_id)
        
        notification = PushNotification(
            id=str(uuid.uuid4()),
            title=title,
            body=body,
            user_id=user_id,
            device_ids=[d.id for d in devices],
            data=data or {},
        )
        
        # Filter by notification type
        notification.device_ids = [
            d.id for d in devices
            if d.notifications_enabled
            and (notification_type in d.notification_types or "all" in d.notification_types)
        ]
        
        self._notifications[notification.id] = notification
        
        # Send to devices (in production, would integrate with FCM/APNS)
        self._deliver_notification(notification)
        
        return notification
    
    def _deliver_notification(self, notification: PushNotification) -> None:
        """Deliver notification to devices"""
        # In production, would call FCM/APNS API
        notification.sent_at = datetime.utcnow()
        notification.delivered = len(notification.device_ids)
        
        logger.info(f"Sent notification: {notification.id} to {notification.delivered} devices")
    
    def send_trade_alert(
        self,
        user_id: str,
        trade_data: Dict[str, Any],
    ) -> PushNotification:
        """Send trade execution alert"""
        action = trade_data.get("action", "TRADE")
        symbol = trade_data.get("symbol", "")
        amount = trade_data.get("amount", 0)
        status = trade_data.get("status", "")
        
        return self.send_notification(
            user_id=user_id,
            title=f"Trade {status}",
            body=f"{action} {amount} {symbol} - {status}",
            data={"type": "trade", "trade_data": trade_data},
            notification_type="trades",
        )
    
    def send_risk_alert(
        self,
        user_id: str,
        risk_data: Dict[str, Any],
    ) -> PushNotification:
        """Send risk alert"""
        alert_type = risk_data.get("type", "risk")
        message = risk_data.get("message", "Risk alert")
        
        severity = risk_data.get("severity", "warning")
        
        title = {
            "warning": "⚠️ Risk Warning",
            "critical": "🚨 Risk Alert",
            "info": "ℹ️ Risk Update",
        }.get(severity, "Risk Alert")
        
        return self.send_notification(
            user_id=user_id,
            title=title,
            body=message,
            data={"type": "risk", "risk_data": risk_data},
            notification_type="risk",
        )
    
    # =========================================================================
    # API Endpoints
    # =========================================================================
    
    def get_account_summary(self, user_id: str) -> Dict[str, Any]:
        """Get account summary for mobile"""
        return {
            "accounts": [
                {
                    "id": "demo_1",
                    "type": "demo",
                    "balance": 10000.0,
                    "currency": "USD",
                    "equity": 10050.0,
                },
                {
                    "id": "real_1",
                    "type": "real",
                    "balance": 5000.0,
                    "currency": "USD",
                    "equity": 4950.0,
                },
            ],
            "active_positions": 2,
            "daily_pnl": 50.0,
            "total_pnl": 500.0,
        }
    
    def get_positions(self, user_id: str, account_id: str) -> List[Dict[str, Any]]:
        """Get open positions"""
        return [
            {
                "id": "pos_1",
                "symbol": "EUR/USD",
                "side": "buy",
                "amount": 100,
                "entry_price": 1.0850,
                "current_price": 1.0860,
                "pnl": 10.0,
                "opened_at": "2024-01-15T10:00:00Z",
            },
        ]
    
    def get_notifications(
        self,
        user_id: str,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get notification history"""
        notifications = [
            n for n in self._notifications.values()
            if n.user_id == user_id
            and (since is None or n.created_at >= since)
        ]
        
        return [
            {
                "id": n.id,
                "title": n.title,
                "body": n.body,
                "data": n.data,
                "created_at": n.created_at.isoformat(),
            }
            for n in sorted(notifications, key=lambda x: x.created_at, reverse=True)[:limit]
        ]
    
    def emergency_stop(self, user_id: str, reason: str = "User requested") -> Dict[str, Any]:
        """Execute emergency stop"""
        logger.warning(f"Emergency stop requested by user {user_id}: {reason}")
        
        # In production, would trigger kill switch
        return {
            "success": True,
            "message": "Emergency stop activated",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def switch_account(self, user_id: str, account_id: str) -> Dict[str, Any]:
        """Switch active account"""
        return {
            "success": True,
            "active_account": account_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    # =========================================================================
    # Authentication
    # =========================================================================
    
    def create_api_key(self, user_id: str) -> str:
        """Create API key for mobile app"""
        api_key = str(uuid.uuid4())
        self._api_keys[api_key] = user_id
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[str]:
        """Validate API key and return user_id"""
        return self._api_keys.get(api_key)
