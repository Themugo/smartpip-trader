"""
Team Manager and Invitation System

Manages:
- Team creation and management
- Team invitations
- Invitation lifecycle
- Team membership
"""

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from enterprise.models.tenant import (
    Team,
    TeamMembership,
    TeamStatus,
    Workspace,
    WorkspaceType,
)
from enterprise.models.audit import AuditLogger, AuditEventType, AuditSeverity


class InvitationStatus(Enum):
    """Invitation status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class Invitation:
    """Team invitation"""
    invitation_id: str
    team_id: str
    organization_id: str
    
    # Invitation details
    email: str
    role_id: str
    role_name: str
    
    # Lifecycle
    status: InvitationStatus
    invited_by: str
    invited_by_name: str
    
    # Token
    token: str
    
    # Timestamps (defaults first)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=7))
    created_at: datetime = field(default_factory=datetime.utcnow)
    accepted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    
    # Message
    personal_message: Optional[str] = None
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at
    
    @property
    def is_valid(self) -> bool:
        return self.status == InvitationStatus.PENDING and not self.is_expired
    
    def to_dict(self, include_token: bool = False) -> Dict[str, Any]:
        result = {
            "invitation_id": self.invitation_id,
            "team_id": self.team_id,
            "organization_id": self.organization_id,
            "email": self.email,
            "role_id": self.role_id,
            "role_name": self.role_name,
            "status": self.status.value,
            "invited_by": self.invited_by,
            "invited_by_name": self.invited_by_name,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "declined_at": self.declined_at.isoformat() if self.declined_at else None,
            "personal_message": self.personal_message,
            "is_expired": self.is_expired,
        }
        
        if include_token:
            result["token"] = self.token
        
        return result


class TeamManager:
    """
    Manages teams within an organization.
    
    Features:
    - Team CRUD
    - Member management
    - Team settings
    - Shared resources
    """
    
    def __init__(self):
        self._teams: Dict[str, Team] = {}
        self._org_teams: Dict[str, List[str]] = {}  # org_id -> [team_ids]
        self._team_members: Dict[str, List[TeamMembership]] = {}  # team_id -> [memberships]
        self._user_teams: Dict[str, List[str]] = {}  # user_id -> [team_ids]
        self._audit = AuditLogger()
    
    def create_team(
        self,
        organization_id: str,
        name: str,
        description: str,
        created_by: str,
    ) -> Team:
        """Create a new team"""
        team = Team.create(
            organization_id=organization_id,
            name=name,
            description=description,
            created_by=created_by,
        )
        
        self._teams[team.team_id] = team
        
        if organization_id not in self._org_teams:
            self._org_teams[organization_id] = []
        self._org_teams[organization_id].append(team.team_id)
        
        # Add creator as team admin
        self._add_member(team.team_id, created_by, created_by, self._get_admin_role_id(team.team_id))
        
        self._audit.log_team(
            team_id=team.team_id,
            org_id=organization_id,
            action="created",
            user_id=created_by,
            description=f"Team created: {name}",
        )
        
        return team
    
    def get_team(self, team_id: str) -> Optional[Team]:
        """Get team by ID"""
        return self._teams.get(team_id)
    
    def get_org_teams(self, organization_id: str) -> List[Team]:
        """Get all teams in an organization"""
        team_ids = self._org_teams.get(organization_id, [])
        return [self._teams[tid] for tid in team_ids if tid in self._teams]
    
    def get_user_teams(self, user_id: str) -> List[Team]:
        """Get all teams for a user"""
        team_ids = self._user_teams.get(user_id, [])
        return [self._teams[tid] for tid in team_ids if tid in self._teams]
    
    def update_team(
        self,
        team_id: str,
        updates: Dict[str, Any],
        updated_by: str,
    ) -> Optional[Team]:
        """Update team details"""
        team = self._teams.get(team_id)
        if not team:
            return None
        
        if "name" in updates:
            team.name = updates["name"]
        if "description" in updates:
            team.description = updates["description"]
        
        team.updated_at = datetime.utcnow()
        
        self._audit.log_team(
            team_id=team_id,
            org_id=team.organization_id,
            action="updated",
            user_id=updated_by,
            description=f"Team updated: {updates}",
        )
        
        return team
    
    def delete_team(self, team_id: str, deleted_by: str) -> bool:
        """Delete a team"""
        team = self._teams.get(team_id)
        if not team:
            return False
        
        org_id = team.organization_id
        
        # Remove from indexes
        if org_id in self._org_teams:
            self._org_teams[org_id].remove(team_id)
        
        # Remove all memberships
        for membership in self._team_members.get(team_id, []):
            user_id = membership.user_id
            if user_id in self._user_teams:
                self._user_teams[user_id].remove(team_id)
        
        del self._team_members[team_id]
        del self._teams[team_id]
        
        self._audit.log_team(
            team_id=team_id,
            org_id=org_id,
            action="deleted",
            user_id=deleted_by,
            description="Team deleted",
        )
        
        return True
    
    # ─────────────────────────────────────────────────────────────
    # Member Management
    # ─────────────────────────────────────────────────────────────
    
    def _add_member(
        self,
        team_id: str,
        user_id: str,
        invited_by: str,
        role_id: str,
    ) -> TeamMembership:
        """Add member to team"""
        membership = TeamMembership.create(
            team_id=team_id,
            user_id=user_id,
            role_id=role_id,
            invited_by=invited_by,
        )
        
        if team_id not in self._team_members:
            self._team_members[team_id] = []
        self._team_members[team_id].append(membership)
        
        if user_id not in self._user_teams:
            self._user_teams[user_id] = []
        if team_id not in self._user_teams[user_id]:
            self._user_teams[user_id].append(team_id)
        
        return membership
    
    def add_member(
        self,
        team_id: str,
        user_id: str,
        role_id: str,
        added_by: str,
    ) -> bool:
        """Add member to team with audit logging"""
        team = self._teams.get(team_id)
        if not team:
            return False
        
        membership = self._add_member(team_id, user_id, added_by, role_id)
        
        self._audit.log_team(
            team_id=team_id,
            org_id=team.organization_id,
            action="member_added",
            user_id=added_by,
            description=f"Member added: {user_id}",
        )
        
        return True
    
    def remove_member(
        self,
        team_id: str,
        user_id: str,
        removed_by: str,
    ) -> bool:
        """Remove member from team"""
        team = self._teams.get(team_id)
        if not team:
            return False
        
        memberships = self._team_members.get(team_id, [])
        self._team_members[team_id] = [
            m for m in memberships if m.user_id != user_id
        ]
        
        if user_id in self._user_teams:
            self._user_teams[user_id].remove(team_id)
        
        self._audit.log_team(
            team_id=team_id,
            org_id=team.organization_id,
            action="member_removed",
            user_id=removed_by,
            description=f"Member removed: {user_id}",
        )
        
        return True
    
    def get_members(self, team_id: str) -> List[TeamMembership]:
        """Get all members of team"""
        return self._team_members.get(team_id, [])
    
    def get_user_team_membership(
        self,
        team_id: str,
        user_id: str,
    ) -> Optional[TeamMembership]:
        """Get user's membership in team"""
        for membership in self._team_members.get(team_id, []):
            if membership.user_id == user_id:
                return membership
        return None
    
    def is_member(self, team_id: str, user_id: str) -> bool:
        """Check if user is a member of team"""
        return self.get_user_team_membership(team_id, user_id) is not None
    
    def _get_admin_role_id(self, team_id: str) -> str:
        """Get or create admin role for team"""
        return f"team_admin_{team_id[:8]}"
    
    # ─────────────────────────────────────────────────────────────
    # Shared Workspaces
    # ─────────────────────────────────────────────────────────────
    
    def get_shared_workspaces(self, team_id: str) -> List[Workspace]:
        """Get workspaces shared with team"""
        # In production, this would query workspace storage
        return []


class InvitationManager:
    """
    Manages team invitations.
    
    Features:
    - Invitation creation
    - Invitation acceptance/decline
    - Invitation expiration
    - Batch invitations
    """
    
    def __init__(
        self,
        team_manager: TeamManager = None,
        invitation_ttl_days: int = 7,
    ):
        self._team_manager = team_manager
        self._invitation_ttl = timedelta(days=invitation_ttl_days)
        
        self._invitations: Dict[str, Invitation] = {}
        self._pending_by_email: Dict[str, List[str]] = {}  # email -> [invitation_ids]
        self._pending_by_team: Dict[str, List[str]] = {}  # team_id -> [invitation_ids]
        self._audit = AuditLogger()
    
    def create_invitation(
        self,
        team_id: str,
        email: str,
        role_id: str,
        role_name: str,
        invited_by: str,
        invited_by_name: str,
        personal_message: Optional[str] = None,
    ) -> Invitation:
        """Create a new invitation"""
        team = self._team_manager.get_team(team_id)
        if not team:
            raise ValueError("Team not found")
        
        invitation_id = secrets.token_urlsafe(16)
        token = secrets.token_urlsafe(32)
        
        invitation = Invitation(
            invitation_id=invitation_id,
            team_id=team_id,
            organization_id=team.organization_id,
            email=email.lower(),
            role_id=role_id,
            role_name=role_name,
            status=InvitationStatus.PENDING,
            invited_by=invited_by,
            invited_by_name=invited_by_name,
            token=token,
            expires_at=datetime.utcnow() + self._invitation_ttl,
            personal_message=personal_message,
        )
        
        self._invitations[invitation_id] = invitation
        
        # Index by email
        if email.lower() not in self._pending_by_email:
            self._pending_by_email[email.lower()] = []
        self._pending_by_email[email.lower()].append(invitation_id)
        
        # Index by team
        if team_id not in self._pending_by_team:
            self._pending_by_team[team_id] = []
        self._pending_by_team[team_id].append(invitation_id)
        
        self._audit.log_team(
            team_id=team_id,
            org_id=team.organization_id,
            action="member_invited",
            user_id=invited_by,
            description=f"Invitation sent to: {email}",
        )
        
        return invitation
    
    def create_batch_invitations(
        self,
        team_id: str,
        invitations: List[Dict[str, Any]],
        invited_by: str,
        invited_by_name: str,
    ) -> List[Invitation]:
        """Create multiple invitations at once"""
        team = self._team_manager.get_team(team_id)
        if not team:
            raise ValueError("Team not found")
        
        created = []
        for inv_data in invitations:
            invitation = self.create_invitation(
                team_id=team_id,
                email=inv_data["email"],
                role_id=inv_data.get("role_id", ""),
                role_name=inv_data.get("role_name", "member"),
                invited_by=invited_by,
                invited_by_name=invited_by_name,
                personal_message=inv_data.get("message"),
            )
            created.append(invitation)
        
        return created
    
    def get_invitation(self, invitation_id: str) -> Optional[Invitation]:
        """Get invitation by ID"""
        invitation = self._invitations.get(invitation_id)
        
        # Check expiration
        if invitation and invitation.is_expired:
            invitation.status = InvitationStatus.EXPIRED
        
        return invitation
    
    def get_invitation_by_token(self, token: str) -> Optional[Invitation]:
        """Get invitation by token"""
        for invitation in self._invitations.values():
            if invitation.token == token:
                if invitation.is_expired:
                    invitation.status = InvitationStatus.EXPIRED
                return invitation
        return None
    
    def get_pending_for_email(self, email: str) -> List[Invitation]:
        """Get all pending invitations for an email"""
        invitation_ids = self._pending_by_email.get(email.lower(), [])
        pending = []
        
        for inv_id in invitation_ids:
            invitation = self._invitations.get(inv_id)
            if invitation and invitation.is_valid:
                pending.append(invitation)
            elif invitation and invitation.status == InvitationStatus.EXPIRED:
                # Clean up expired
                self._pending_by_email[email.lower()].remove(inv_id)
        
        return pending
    
    def get_team_invitations(self, team_id: str) -> List[Invitation]:
        """Get all invitations for a team"""
        invitation_ids = self._pending_by_team.get(team_id, [])
        return [self._invitations[iid] for iid in invitation_ids if iid in self._invitations]
    
    def accept_invitation(
        self,
        invitation_id: str,
        user_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Accept an invitation.
        Returns (success, error_message)
        """
        invitation = self._invitations.get(invitation_id)
        if not invitation:
            return False, "Invitation not found"
        
        if not invitation.is_valid:
            if invitation.status != InvitationStatus.PENDING:
                return False, f"Invitation has been {invitation.status.value}"
            return False, "Invitation has expired"
        
        # Add user to team
        success = self._team_manager.add_member(
            team_id=invitation.team_id,
            user_id=user_id,
            role_id=invitation.role_id,
            added_by=invitation.invited_by,
        )
        
        if success:
            invitation.status = InvitationStatus.ACCEPTED
            invitation.accepted_at = datetime.utcnow()
            
            # Update indexes
            self._pending_by_email.get(invitation.email, []).remove(invitation_id)
            self._pending_by_team.get(invitation.team_id, []).remove(invitation_id)
            
            self._audit.log_team(
                team_id=invitation.team_id,
                org_id=invitation.organization_id,
                action="member_joined",
                user_id=user_id,
                description=f"Invitation accepted by: {invitation.email}",
            )
        
        return success, None
    
    def decline_invitation(
        self,
        invitation_id: str,
        user_id: str,
    ) -> bool:
        """Decline an invitation"""
        invitation = self._invitations.get(invitation_id)
        if not invitation or not invitation.is_valid:
            return False
        
        invitation.status = InvitationStatus.DECLINED
        invitation.declined_at = datetime.utcnow()
        
        # Update indexes
        if invitation.email in self._pending_by_email:
            if invitation_id in self._pending_by_email[invitation.email]:
                self._pending_by_email[invitation.email].remove(invitation_id)
        if invitation.team_id in self._pending_by_team:
            if invitation_id in self._pending_by_team[invitation.team_id]:
                self._pending_by_team[invitation.team_id].remove(invitation_id)
        
        self._audit.log_team(
            team_id=invitation.team_id,
            org_id=invitation.organization_id,
            action="member_declined",
            user_id=user_id,
            description=f"Invitation declined by: {invitation.email}",
        )
        
        return True
    
    def revoke_invitation(
        self,
        invitation_id: str,
        revoked_by: str,
    ) -> bool:
        """Revoke an invitation"""
        invitation = self._invitations.get(invitation_id)
        if not invitation or invitation.status != InvitationStatus.PENDING:
            return False
        
        invitation.status = InvitationStatus.REVOKED
        
        self._audit.log_team(
            team_id=invitation.team_id,
            org_id=invitation.organization_id,
            action="invitation_revoked",
            user_id=revoked_by,
            description=f"Invitation revoked: {invitation.email}",
        )
        
        return True
    
    def resend_invitation(self, invitation_id: str) -> bool:
        """Resend an invitation (reset expiration)"""
        invitation = self._invitations.get(invitation_id)
        if not invitation or invitation.status != InvitationStatus.PENDING:
            return False
        
        invitation.expires_at = datetime.utcnow() + self._invitation_ttl
        
        return True
    
    def cleanup_expired(self) -> int:
        """Clean up expired invitations"""
        expired = []
        
        for inv_id, invitation in self._invitations.items():
            if invitation.is_expired and invitation.status == InvitationStatus.PENDING:
                invitation.status = InvitationStatus.EXPIRED
                expired.append(inv_id)
        
        return len(expired)
    
    def get_pending_count(self, email: str) -> int:
        """Get count of pending invitations for email"""
        return len(self.get_pending_for_email(email))
