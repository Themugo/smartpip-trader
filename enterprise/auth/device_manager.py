"""
Device Manager

Manages user devices with:
- Device registration
- Device trust
- Device fingerprinting
- Session-device association
- Device revocation
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from enterprise.models.user import UserDevice
from enterprise.models.audit import AuditLogger, AuditEventType, AuditSeverity


@dataclass
class DeviceFingerprint:
    """Device fingerprint data"""
    user_agent: str
    accept_language: str
    accept_encoding: str
    accept: str
    screen_resolution: Optional[str] = None
    timezone: Optional[str] = None
    platform: Optional[str] = None
    touch_points: Optional[int] = None
    color_depth: Optional[int] = None
    canvas_fingerprint: Optional[str] = None
    webgl_fingerprint: Optional[str] = None
    audio_fingerprint: Optional[str] = None
    
    def to_hash(self) -> str:
        """Generate fingerprint hash"""
        data = "|".join([
            self.user_agent[:100],
            self.accept_language[:20],
            str(self.screen_resolution or ""),
            str(self.timezone or ""),
        ])
        return hashlib.sha256(data.encode()).hexdigest()[:32]


class DeviceManager:
    """
    Manages user devices.
    
    Features:
    - Device registration and tracking
    - Device trust management
    - Device fingerprinting
    - Device revocation
    - Session association
    """
    
    def __init__(
        self,
        max_trusted_devices: int = 10,
        device_age_threshold_days: int = 30,
    ):
        self._max_trusted_devices = max_trusted_devices
        self._device_age_threshold_days = device_age_threshold_days
        
        # Device storage: device_id -> UserDevice
        self._devices: Dict[str, UserDevice] = {}
        # User device index: user_id -> [device_ids]
        self._user_devices: Dict[str, List[str]] = {}
        # Fingerprint index: fingerprint -> device_id
        self._fingerprints: Dict[str, str] = {}
        
        self._audit = AuditLogger()
    
    def register_device(
        self,
        user_id: str,
        fingerprint: DeviceFingerprint,
        name: Optional[str] = None,
        user_agent: str = "",
    ) -> Tuple[UserDevice, bool]:
        """
        Register a device for a user.
        Returns (device, is_new_device)
        """
        # Check if fingerprint already exists
        fp_hash = fingerprint.to_hash()
        existing_device_id = self._fingerprints.get(fp_hash)
        
        if existing_device_id and existing_device_id in self._devices:
            existing_device = self._devices[existing_device_id]
            if existing_device.user_id == user_id:
                # Existing device for same user
                existing_device.last_seen = datetime.utcnow()
                existing_device.touch()
                return existing_device, False
        
        # Create new device
        device_name = name or self._generate_device_name(user_agent)
        device_type = self._parse_device_type(user_agent)
        
        device = UserDevice.create(
            user_id=user_id,
            name=device_name,
            device_type=device_type,
            user_agent=user_agent,
        )
        device.fingerprint = fp_hash
        device.is_current = True
        
        # Store device
        self._devices[device.device_id] = device
        self._fingerprints[fp_hash] = device.device_id
        
        # Index by user
        if user_id not in self._user_devices:
            self._user_devices[user_id] = []
        self._user_devices[user_id].append(device.device_id)
        
        # Log new device registration
        self._audit.log(
            event_type=AuditEventType.DEVICE_TRUSTED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            description=f"New device registered: {device_name}",
            metadata={"device_id": device.device_id},
        )
        
        return device, True
    
    def get_device(self, device_id: str) -> Optional[UserDevice]:
        """Get device by ID"""
        return self._devices.get(device_id)
    
    def get_user_devices(self, user_id: str) -> List[UserDevice]:
        """Get all devices for a user"""
        device_ids = self._user_devices.get(user_id, [])
        return [
            self._devices[did]
            for did in device_ids
            if did in self._devices
        ]
    
    def get_active_devices(self, user_id: str) -> List[UserDevice]:
        """Get active devices (seen recently)"""
        threshold = datetime.utcnow() - timedelta(days=self._device_age_threshold_days)
        devices = self.get_user_devices(user_id)
        return [
            d for d in devices
            if d.last_seen >= threshold
        ]
    
    def trust_device(self, device_id: str, user_id: str) -> bool:
        """Mark a device as trusted"""
        device = self._devices.get(device_id)
        if not device or device.user_id != user_id:
            return False
        
        # Check if user already has max trusted devices
        trusted_count = sum(
            1 for d in self.get_user_devices(user_id)
            if d.is_trusted
        )
        
        if trusted_count >= self._max_trusted_devices and not device.is_trusted:
            # Untrust oldest trusted device
            oldest_trusted = min(
                (d for d in self.get_user_devices(user_id) if d.is_trusted),
                key=lambda d: d.last_seen,
                default=None
            )
            if oldest_trusted:
                oldest_trusted.is_trusted = False
        
        device.is_trusted = True
        
        self._audit.log(
            event_type=AuditEventType.DEVICE_TRUSTED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            description=f"Device trusted: {device.name}",
            metadata={"device_id": device_id},
        )
        
        return True
    
    def distrust_device(self, device_id: str, user_id: str) -> bool:
        """Mark a device as untrusted"""
        device = self._devices.get(device_id)
        if not device or device.user_id != user_id:
            return False
        
        device.is_trusted = False
        
        self._audit.log(
            event_type=AuditEventType.DEVICE_DISTRUSTED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            description=f"Device distrusted: {device.name}",
            metadata={"device_id": device_id},
        )
        
        return True
    
    def remove_device(self, device_id: str, user_id: str) -> bool:
        """Remove a device"""
        device = self._devices.get(device_id)
        if not device or device.user_id != user_id:
            return False
        
        # Remove from indices
        self._fingerprints.pop(device.fingerprint, None)
        if user_id in self._user_devices:
            self._user_devices[user_id] = [
                did for did in self._user_devices[user_id]
                if did != device_id
            ]
        
        # Remove device
        del self._devices[device_id]
        
        self._audit.log(
            event_type=AuditEventType.DEVICE_DISTRUSTED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            description=f"Device removed: {device.name}",
            metadata={"device_id": device_id},
        )
        
        return True
    
    def remove_all_devices(self, user_id: str) -> int:
        """Remove all devices for a user"""
        device_ids = self._user_devices.get(user_id, [])
        count = len(device_ids)
        
        for device_id in device_ids:
            device = self._devices.pop(device_id, None)
            if device:
                self._fingerprints.pop(device.fingerprint, None)
        
        self._user_devices[user_id] = []
        
        return count
    
    def is_device_trusted(self, device_id: str, user_id: str) -> bool:
        """Check if device is trusted"""
        device = self._devices.get(device_id)
        if not device or device.user_id != user_id:
            return False
        return device.is_trusted
    
    def is_known_device(self, fingerprint: DeviceFingerprint, user_id: str) -> bool:
        """Check if device fingerprint is known for user"""
        fp_hash = fingerprint.to_hash()
        device_id = self._fingerprints.get(fp_hash)
        
        if not device_id:
            return False
        
        device = self._devices.get(device_id)
        return device and device.user_id == user_id
    
    def update_device_activity(self, device_id: str) -> bool:
        """Update device last seen timestamp"""
        device = self._devices.get(device_id)
        if device:
            device.last_seen = datetime.utcnow()
            return True
        return False
    
    def set_current_device(self, device_id: str, user_id: str) -> bool:
        """Set device as current"""
        # Unset current for all other devices
        for device in self.get_user_devices(user_id):
            device.is_current = False
        
        # Set current
        device = self._devices.get(device_id)
        if device and device.user_id == user_id:
            device.is_current = True
            return True
        
        return False
    
    def get_device_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user devices"""
        devices = self.get_user_devices(user_id)
        
        trusted = [d for d in devices if d.is_trusted]
        recent = [d for d in devices if d.last_seen >= datetime.utcnow() - timedelta(days=7)]
        current = [d for d in devices if d.is_current]
        
        return {
            "total_devices": len(devices),
            "trusted_count": len(trusted),
            "recent_count": len(recent),
            "max_trusted": self._max_trusted_devices,
            "devices": [
                {
                    "device_id": d.device_id,
                    "name": d.name,
                    "device_type": d.device_type,
                    "browser": d.browser,
                    "os": d.os,
                    "is_trusted": d.is_trusted,
                    "is_current": d.is_current,
                    "first_seen": d.first_seen.isoformat(),
                    "last_seen": d.last_seen.isoformat(),
                }
                for d in sorted(devices, key=lambda d: d.last_seen, reverse=True)
            ],
        }
    
    @staticmethod
    def _generate_device_name(user_agent: str) -> str:
        """Generate device name from user agent"""
        ua_lower = user_agent.lower()
        
        # Browser detection
        browser = "Browser"
        if "chrome" in ua_lower:
            browser = "Chrome"
        elif "firefox" in ua_lower:
            browser = "Firefox"
        elif "safari" in ua_lower:
            browser = "Safari"
        elif "edge" in ua_lower:
            browser = "Edge"
        
        # OS detection
        os_name = "Device"
        if "windows" in ua_lower:
            os_name = "Windows PC"
        elif "mac" in ua_lower:
            os_name = "Mac"
        elif "linux" in ua_lower:
            os_name = "Linux"
        elif "android" in ua_lower:
            os_name = "Android"
        elif "iphone" in ua_lower or "ipad" in ua_lower:
            os_name = "iOS"
        
        return f"{browser} on {os_name}"
    
    @staticmethod
    def _parse_device_type(user_agent: str) -> str:
        """Parse device type from user agent"""
        ua_lower = user_agent.lower()
        
        if "tablet" in ua_lower or "ipad" in ua_lower:
            return "tablet"
        if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            return "mobile"
        
        return "desktop"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get device manager statistics"""
        total_devices = len(self._devices)
        total_trusted = sum(1 for d in self._devices.values() if d.is_trusted)
        total_users_with_devices = len(self._user_devices)
        
        # Device type distribution
        type_counts = {}
        for device in self._devices.values():
            dt = device.device_type
            type_counts[dt] = type_counts.get(dt, 0) + 1
        
        return {
            "total_devices": total_devices,
            "trusted_devices": total_trusted,
            "users_with_devices": total_users_with_devices,
            "max_trusted_per_user": self._max_trusted_devices,
            "device_types": type_counts,
        }
