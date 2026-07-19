"""
Collaboration Layer - Multi-User Support

Multi-user collaboration with comments, reviews, and approvals.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User roles"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    ANALYST = "analyst"
    VIEWER = "viewer"


class ReviewStatus(Enum):
    """Code review status"""
    PENDING = "pending"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    COMMENTED = "commented"


@dataclass
class User:
    """A platform user"""
    id: str
    username: str
    email: str
    role: UserRole = UserRole.VIEWER
    avatar_url: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Comment:
    """A comment on a strategy or version"""
    id: str
    strategy_id: str
    version: Optional[str]
    
    author_id: str
    author_name: str
    
    content: str
    line_number: Optional[int] = None
    
    # Threading
    parent_id: Optional[str] = None
    replies: List["Comment"] = field(default_factory=list)
    
    # Status
    is_resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "version": self.version,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "content": self.content,
            "line_number": self.line_number,
            "parent_id": self.parent_id,
            "is_resolved": self.is_resolved,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class ChangeRecord:
    """Record of a change to a strategy"""
    id: str
    strategy_id: str
    version: str
    
    author_id: str
    author_name: str
    
    change_type: str  # "created", "updated", "promoted", "archived"
    description: str
    
    # Diff
    changes_summary: Dict[str, Any] = field(default_factory=dict)
    
    # Review
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "version": self.version,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "change_type": self.change_type,
            "description": self.description,
            "review_status": self.review_status.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Approval:
    """An approval record"""
    id: str
    strategy_id: str
    target_state: str
    
    approver_id: str
    approver_name: str
    
    approved: bool
    reason: str = ""
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CollaborationLayer:
    """
    Collaboration layer for multi-user support.
    
    Features:
    - User management
    - Comments and threads
    - Change history
    - Code reviews
    - Approvals for state transitions
    """
    
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._comments: Dict[str, Comment] = {}
        self._changes: Dict[str, ChangeRecord] = {}
        self._approvals: Dict[str, Approval] = {}
        
        # Default admin user
        self._users["system"] = User(
            id="system",
            username="system",
            email="system@localhost",
            role=UserRole.ADMIN,
        )
    
    # =========================================================================
    # User Management
    # =========================================================================
    
    def create_user(
        self,
        username: str,
        email: str,
        role: UserRole = UserRole.VIEWER,
    ) -> User:
        """Create a new user"""
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            role=role,
        )
        self._users[user.id] = user
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        return self._users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username"""
        for user in self._users.values():
            if user.username == username:
                return user
        return None
    
    def list_users(self, role: Optional[UserRole] = None) -> List[User]:
        """List users"""
        users = list(self._users.values())
        if role:
            users = [u for u in users if u.role == role]
        return users
    
    # =========================================================================
    # Comments
    # =========================================================================
    
    def add_comment(
        self,
        strategy_id: str,
        author_id: str,
        author_name: str,
        content: str,
        version: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> Comment:
        """Add a comment"""
        comment = Comment(
            id=str(uuid.uuid4()),
            strategy_id=strategy_id,
            version=version,
            author_id=author_id,
            author_name=author_name,
            content=content,
            parent_id=parent_id,
        )
        
        self._comments[comment.id] = comment
        
        # Add to thread
        if parent_id:
            parent = self._comments.get(parent_id)
            if parent:
                parent.replies.append(comment)
        
        return comment
    
    def get_comments(
        self,
        strategy_id: str,
        version: Optional[str] = None,
        include_resolved: bool = True,
    ) -> List[Comment]:
        """Get comments for a strategy"""
        comments = [
            c for c in self._comments.values()
            if c.strategy_id == strategy_id
            and (version is None or c.version == version)
            and (include_resolved or not c.is_resolved)
            and c.parent_id is None  # Only root comments
        ]
        
        return sorted(comments, key=lambda c: c.created_at, reverse=True)
    
    def resolve_comment(self, comment_id: str, user_id: str) -> bool:
        """Resolve a comment"""
        comment = self._comments.get(comment_id)
        if not comment:
            return False
        
        comment.is_resolved = True
        comment.resolved_by = user_id
        comment.resolved_at = datetime.now(timezone.utc)
        return True
    
    # =========================================================================
    # Change History
    # =========================================================================
    
    def record_change(
        self,
        strategy_id: str,
        version: str,
        author_id: str,
        author_name: str,
        change_type: str,
        description: str,
        changes_summary: Optional[Dict[str, Any]] = None,
    ) -> ChangeRecord:
        """Record a change"""
        change = ChangeRecord(
            id=str(uuid.uuid4()),
            strategy_id=strategy_id,
            version=version,
            author_id=author_id,
            author_name=author_name,
            change_type=change_type,
            description=description,
            changes_summary=changes_summary or {},
        )
        
        self._changes[change.id] = change
        return change
    
    def get_change_history(
        self,
        strategy_id: str,
        limit: int = 50,
    ) -> List[ChangeRecord]:
        """Get change history for a strategy"""
        changes = [
            c for c in self._changes.values()
            if c.strategy_id == strategy_id
        ]
        return sorted(changes, key=lambda c: c.created_at, reverse=True)[:limit]
    
    # =========================================================================
    # Reviews
    # =========================================================================
    
    def submit_review(
        self,
        change_id: str,
        reviewer_id: str,
        reviewer_name: str,
        status: ReviewStatus,
        reason: str = "",
    ) -> bool:
        """Submit a code review"""
        change = self._changes.get(change_id)
        if not change:
            return False
        
        change.review_status = status
        change.reviewed_by = reviewer_id
        change.reviewed_at = datetime.now(timezone.utc)
        
        return True
    
    # =========================================================================
    # Approvals
    # =========================================================================
    
    def request_approval(
        self,
        strategy_id: str,
        target_state: str,
        requester_id: str,
        reason: str,
    ) -> str:
        """Request approval for a state transition"""
        approval_id = str(uuid.uuid4())
        # In real implementation, would send notification to approvers
        return approval_id
    
    def submit_approval(
        self,
        approval_id: str,
        approver_id: str,
        approver_name: str,
        approved: bool,
        reason: str = "",
    ) -> Approval:
        """Submit an approval decision"""
        approval = Approval(
            id=approval_id,
            strategy_id="",  # Would be set from request
            target_state="",
            approver_id=approver_id,
            approver_name=approver_name,
            approved=approved,
            reason=reason,
        )
        
        self._approvals[approval_id] = approval
        return approval
    
    # =========================================================================
    # Permissions
    # =========================================================================
    
    def can_edit_strategy(self, user_id: str) -> bool:
        """Check if user can edit strategies"""
        user = self._users.get(user_id)
        if not user:
            return False
        return user.role in [UserRole.ADMIN, UserRole.DEVELOPER]
    
    def can_promote_strategy(self, user_id: str) -> bool:
        """Check if user can promote strategies"""
        user = self._users.get(user_id)
        if not user:
            return False
        return user.role in [UserRole.ADMIN, UserRole.DEVELOPER]
    
    def can_view_strategy(self, user_id: str) -> bool:
        """Check if user can view strategies"""
        return user_id in self._users
