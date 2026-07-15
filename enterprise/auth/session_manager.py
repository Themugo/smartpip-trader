"""
Session Manager

Manages user sessions with:
- Session creation and validation
- Session expiration
- Session revocation
- Concurrent session limits
- Device tracking
"""

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import OrderedDict

from enterprise.models.user import UserSession, SessionStatus
from enterprise.models.audit import AuditLogger, AuditEventType, AuditSeverity


@dataclass
class SessionConfig:
    """Session configuration"""
    max_sessions_per_user: int = 5
    session_timeout_hours: int = 24
    absolute_timeout_hours: int = 168  # 7 days
    idle_timeout_minutes: int = 60
    allow_concurrent: bool = True
    track_device: bool = True
    enforce_ip_consistency: bool = False


class SessionManager:
    """
    Manages user sessions securely.
    
    Features:
    - Session creation with secure tokens
    - Session validation and refresh
    - Session revocation
    - Concurrent session limits
    - Idle timeout
    - Device tracking
    - Audit logging
    """
    
    def __init__(self, config: Optional[SessionConfig] = None):
        self._config = config or SessionConfig()
        self._sessions: Dict[str, UserSession] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        self._audit = AuditLogger()
    
    def create_session(
        self,
        user_id: str,
        ip_address: str = "",
        user_agent: str = "",
        device_id: Optional[str] = None,
        device_name: str = "Unknown",
        organization_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserSession:
        """Create a new session"""
        # Generate secure session ID
        session_id = secrets.token_urlsafe(32)
        
        # Determine device type from user agent
        device_type = self._parse_device_type(user_agent)
        
        # Create session
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            organization_id=organization_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            expires_at=datetime.utcnow() + timedelta(hours=self._config.session_timeout_hours),
            metadata=metadata or {},
        )
        
        # Store session
        self._sessions[session_id] = session
        
        # Track user sessions
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_id)
        
        # Enforce concurrent session limit
        if len(self._user_sessions[user_id]) > self._config.max_sessions_per_user:
            oldest_session_id = self._user_sessions[user_id][0]
            self.revoke_session(oldest_session_id, reason="Exceeded session limit")
        
        # Log session creation
        self._audit.log(
            event_type=AuditEventType.SESSION_CREATED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            description=f"New session created: {device_name}",
        )
        
        return session
    
    def validate_session(
        self,
        session_id: str,
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, Optional[UserSession], Optional[str]]:
        """
        Validate a session.
        Returns (is_valid, session, error_message)
        """
        session = self._sessions.get(session_id)
        
        if not session:
            return False, None, "Session not found"
        
        # Check if revoked
        if session.status == SessionStatus.REVOKED:
            return False, None, "Session has been revoked"
        
        # Check if expired
        if session.is_expired:
            session.status = SessionStatus.EXPIRED
            return False, None, "Session has expired"
        
        # Check absolute timeout
        age_hours = (datetime.utcnow() - session.created_at).total_seconds() / 3600
        if age_hours > self._config.absolute_timeout_hours:
            session.status = SessionStatus.EXPIRED
            return False, None, "Session has exceeded maximum lifetime"
        
        # Check IP consistency
        if self._config.enforce_ip_consistency and ip_address:
            if session.ip_address and session.ip_address != ip_address:
                # Log potential session hijacking
                self._audit.log_security(
                    event_type="suspicious",
                    user_id=session.user_id,
                    description=f"IP change detected for session: {session.ip_address} -> {ip_address}",
                    severity=AuditSeverity.WARNING,
                )
                # Allow but flag it
                session.metadata["ip_changed"] = True
        
        return True, session, None
    
    def refresh_session(self, session_id: str) -> Optional[UserSession]:
        """Refresh session (extend expiration)"""
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        if not session.is_valid:
            return None
        
        session.extend(hours=self._config.session_timeout_hours)
        return session
    
    def revoke_session(self, session_id: str, reason: str = "User logout") -> bool:
        """Revoke a specific session"""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.revoke()
        
        # Log revocation
        self._audit.log(
            event_type=AuditEventType.SESSION_REVOKED,
            severity=AuditSeverity.INFO,
            user_id=session.user_id,
            session_id=session_id,
            description=f"Session revoked: {reason}",
        )
        
        return True
    
    def revoke_all_user_sessions(self, user_id: str, except_session_id: Optional[str] = None) -> int:
        """Revoke all sessions for a user"""
        session_ids = self._user_sessions.get(user_id, [])
        revoked_count = 0
        
        for session_id in session_ids:
            if session_id != except_session_id:
                if self.revoke_session(session_id, reason="Revoked all sessions"):
                    revoked_count += 1
        
        return revoked_count
    
    def get_user_sessions(self, user_id: str) -> List[UserSession]:
        """Get all active sessions for a user"""
        session_ids = self._user_sessions.get(user_id, [])
        return [
            self._sessions[sid]
            for sid in session_ids
            if sid in self._sessions and self._sessions[sid].is_valid
        ]
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID"""
        return self._sessions.get(session_id)
    
    def update_session_activity(self, session_id: str) -> bool:
        """Update last activity timestamp"""
        session = self._sessions.get(session_id)
        if session and session.is_valid:
            session.touch()
            return True
        return False
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions"""
        expired_ids = [
            sid for sid, session in self._sessions.items()
            if not session.is_valid
        ]
        
        for session_id in expired_ids:
            session = self._sessions.pop(session_id)
            user_id = session.user_id
            if user_id in self._user_sessions:
                self._user_sessions[user_id] = [
                    sid for sid in self._user_sessions[user_id]
                    if sid != session_id
                ]
        
        return len(expired_ids)
    
    def get_session_count(self, user_id: str) -> int:
        """Get count of active sessions for a user"""
        return len(self.get_user_sessions(user_id))
    
    def get_active_sessions_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of active sessions"""
        sessions = self.get_user_sessions(user_id)
        
        return {
            "total": len(sessions),
            "max_allowed": self._config.max_sessions_per_user,
            "sessions": [
                {
                    "session_id": s.session_id,
                    "device_name": s.device_name,
                    "device_type": s.device_type,
                    "ip_address": s.ip_address,
                    "city": s.city,
                    "country": s.country,
                    "created_at": s.created_at.isoformat(),
                    "last_activity": s.last_activity.isoformat(),
                    "is_current": False,  # To be set by caller
                }
                for s in sessions
            ],
        }
    
    @staticmethod
    def _parse_device_type(user_agent: str) -> str:
        """Parse device type from user agent"""
        ua_lower = user_agent.lower()
        
        if "tablet" in ua_lower or "ipad" in ua_lower:
            return "tablet"
        if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            return "mobile"
        
        return "desktop"
    
    def get_active_session_count(self) -> int:
        """Get total count of active sessions"""
        return sum(
            1 for session in self._sessions.values()
            if session.is_valid
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics"""
        active_count = self.get_active_session_count()
        
        # Count by device type
        device_counts = {}
        for session in self._sessions.values():
            if session.is_valid:
                dt = session.device_type
                device_counts[dt] = device_counts.get(dt, 0) + 1
        
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": active_count,
            "max_per_user": self._config.max_sessions_per_user,
            "session_timeout_hours": self._config.session_timeout_hours,
            "idle_timeout_minutes": self._config.idle_timeout_minutes,
            "devices": device_counts,
        }
