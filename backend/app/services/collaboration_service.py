"""
CelebraTech Event Management System - Collaboration Service
Sprint 16: Collaboration & Sharing System
Business logic for collaboration operations
"""
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID
import secrets

from app.models.collaboration import (
    EventCollaborator,
    EventInvitation,
    ActivityLog,
    Comment,
    ShareLink,
    CollaborationPresence,
    CollaboratorRole,
    InvitationStatus,
    ActivityType
)
from app.models.user import User
from app.schemas.collaboration import (
    EventCollaboratorCreate,
    EventCollaboratorUpdate,
    EventInvitationCreate,
    CommentCreate,
    ShareLinkCreate
)
from app.repositories.collaboration_repository import CollaborationRepository


class CollaborationService:
    """Service for collaboration operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.collab_repo = CollaborationRepository(db)

    # ========================================================================
    # Collaborator Operations
    # ========================================================================

    async def add_collaborator(
        self,
        event_id: UUID,
        collaborator_data: EventCollaboratorCreate,
        current_user: User
    ) -> EventCollaborator:
        """Add a collaborator to an event"""
        # TODO: Verify user has manage_collaborators permission

        permissions = self._get_role_permissions(collaborator_data.role)

        collaborator = await self.collab_repo.create_collaborator(
            event_id,
            collaborator_data.user_id,
            collaborator_data.role,
            permissions
        )

        # Log activity
        await self.collab_repo.create_activity_log(
            event_id,
            current_user.id,
            ActivityType.COLLABORATOR_ADDED,
            f"Added {collaborator_data.role} collaborator"
        )

        await self.db.commit()
        return collaborator

    async def get_event_collaborators(
        self,
        event_id: UUID,
        current_user: User
    ) -> List[EventCollaborator]:
        """Get all collaborators for an event"""
        # TODO: Verify user has access to this event

        collaborators = await self.collab_repo.get_event_collaborators(event_id)
        return collaborators

    async def update_collaborator(
        self,
        event_id: UUID,
        user_id: UUID,
        collaborator_data: EventCollaboratorUpdate,
        current_user: User
    ) -> EventCollaborator:
        """Update a collaborator's role and permissions"""
        # TODO: Verify user has manage_collaborators permission

        permissions = self._get_role_permissions(collaborator_data.role)

        updated_collaborator = await self.collab_repo.update_collaborator_role(
            event_id,
            user_id,
            collaborator_data.role,
            permissions
        )

        if not updated_collaborator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collaborator not found"
            )

        # Log activity
        await self.collab_repo.create_activity_log(
            event_id,
            current_user.id,
            ActivityType.COLLABORATOR_ROLE_CHANGED,
            f"Changed collaborator role to {collaborator_data.role}"
        )

        await self.db.commit()
        return updated_collaborator

    async def remove_collaborator(
        self,
        event_id: UUID,
        user_id: UUID,
        current_user: User
    ) -> bool:
        """Remove a collaborator from an event"""
        # TODO: Verify user has manage_collaborators permission

        success = await self.collab_repo.remove_collaborator(event_id, user_id)

        if success:
            # Log activity
            await self.collab_repo.create_activity_log(
                event_id,
                current_user.id,
                ActivityType.COLLABORATOR_REMOVED,
                "Removed collaborator"
            )

            await self.db.commit()

        return success

    def _get_role_permissions(self, role: CollaboratorRole) -> Dict[str, bool]:
        """Get permissions for a role"""
        role_permissions = {
            CollaboratorRole.VIEWER: {
                "can_view": True,
                "can_edit": False,
                "can_delete": False,
                "can_share": False,
                "can_manage_collaborators": False
            },
            CollaboratorRole.COMMENTER: {
                "can_view": True,
                "can_edit": False,
                "can_delete": False,
                "can_share": False,
                "can_manage_collaborators": False
            },
            CollaboratorRole.EDITOR: {
                "can_view": True,
                "can_edit": True,
                "can_delete": False,
                "can_share": True,
                "can_manage_collaborators": False
            },
            CollaboratorRole.ADMIN: {
                "can_view": True,
                "can_edit": True,
                "can_delete": True,
                "can_share": True,
                "can_manage_collaborators": True
            },
            CollaboratorRole.OWNER: {
                "can_view": True,
                "can_edit": True,
                "can_delete": True,
                "can_share": True,
                "can_manage_collaborators": True
            }
        }

        return role_permissions.get(role, role_permissions[CollaboratorRole.VIEWER])

    # ========================================================================
    # Invitation Operations
    # ========================================================================

    async def create_invitation(
        self,
        event_id: UUID,
        invitation_data: EventInvitationCreate,
        current_user: User
    ) -> EventInvitation:
        """Create an event invitation"""
        # TODO: Verify user has manage_collaborators permission

        invitation = await self.collab_repo.create_invitation(
            event_id,
            invitation_data.email,
            invitation_data.role,
            current_user.id,
            invitation_data.expires_at
        )

        await self.db.commit()
        return invitation

    async def get_event_invitations(
        self,
        event_id: UUID,
        current_user: User,
        status: Optional[InvitationStatus] = None
    ) -> List[EventInvitation]:
        """Get invitations for an event"""
        # TODO: Verify user has access

        invitations = await self.collab_repo.get_event_invitations(event_id, status)
        return invitations

    async def accept_invitation(
        self,
        invitation_id: UUID,
        current_user: User
    ) -> EventCollaborator:
        """Accept an invitation and create collaborator"""
        invitation = await self.collab_repo.get_invitation_by_id(invitation_id)

        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )

        if invitation.status != InvitationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation already processed"
            )

        if invitation.expires_at and invitation.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has expired"
            )

        # Accept invitation
        await self.collab_repo.accept_invitation(invitation_id, current_user.id)

        # Create collaborator
        permissions = self._get_role_permissions(invitation.role)
        collaborator = await self.collab_repo.create_collaborator(
            invitation.event_id,
            current_user.id,
            invitation.role,
            permissions
        )

        await self.db.commit()
        return collaborator

    # ========================================================================
    # Activity Log Operations
    # ========================================================================

    async def get_event_activity(
        self,
        event_id: UUID,
        current_user: User,
        limit: int = 50,
        offset: int = 0
    ) -> List[ActivityLog]:
        """Get activity log for an event"""
        # TODO: Verify user has access

        activities = await self.collab_repo.get_event_activity(event_id, limit, offset)
        return activities

    async def log_activity(
        self,
        event_id: UUID,
        activity_type: ActivityType,
        description: str,
        current_user: User,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ActivityLog:
        """Log an activity"""
        activity = await self.collab_repo.create_activity_log(
            event_id,
            current_user.id,
            activity_type,
            description,
            entity_type,
            entity_id,
            metadata
        )

        await self.db.commit()
        return activity

    # ========================================================================
    # Comment Operations
    # ========================================================================

    async def create_comment(
        self,
        event_id: UUID,
        comment_data: CommentCreate,
        current_user: User
    ) -> Comment:
        """Create a comment"""
        # TODO: Verify user has access

        comment = await self.collab_repo.create_comment(
            event_id,
            current_user.id,
            comment_data.entity_type,
            comment_data.entity_id,
            comment_data.content,
            comment_data.parent_id
        )

        # Log activity
        await self.collab_repo.create_activity_log(
            event_id,
            current_user.id,
            ActivityType.COMMENT_ADDED,
            "Added a comment",
            comment_data.entity_type,
            comment_data.entity_id
        )

        await self.db.commit()
        return comment

    async def get_entity_comments(
        self,
        entity_type: str,
        entity_id: UUID
    ) -> List[Comment]:
        """Get comments for an entity"""
        comments = await self.collab_repo.get_entity_comments(entity_type, entity_id)
        return comments

    async def delete_comment(
        self,
        comment_id: UUID,
        current_user: User
    ) -> bool:
        """Delete a comment"""
        # TODO: Verify user owns comment or has delete permission

        success = await self.collab_repo.delete_comment(comment_id)

        if success:
            await self.db.commit()

        return success

    # ========================================================================
    # Share Link Operations
    # ========================================================================

    async def create_share_link(
        self,
        event_id: UUID,
        share_data: ShareLinkCreate,
        current_user: User
    ) -> ShareLink:
        """Create a share link"""
        # TODO: Verify user has share permission

        # Generate secure token
        token = secrets.token_urlsafe(32)

        share_link = await self.collab_repo.create_share_link(
            event_id,
            current_user.id,
            token,
            share_data.permission_level,
            share_data.expires_at,
            share_data.max_uses
        )

        await self.db.commit()
        return share_link

    async def get_share_link_by_token(
        self,
        token: str
    ) -> Optional[ShareLink]:
        """Get share link by token and validate"""
        share_link = await self.collab_repo.get_share_link_by_token(token)

        if not share_link:
            return None

        # Check expiration
        if share_link.expires_at and share_link.expires_at < datetime.utcnow():
            return None

        # Check max uses
        if share_link.max_uses and share_link.use_count >= share_link.max_uses:
            return None

        return share_link

    async def use_share_link(
        self,
        token: str,
        current_user: User
    ) -> EventCollaborator:
        """Use a share link to join as collaborator"""
        share_link = await self.get_share_link_by_token(token)

        if not share_link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share link not found or expired"
            )

        # Increment usage
        await self.collab_repo.increment_share_link_usage(share_link.id)

        # Create collaborator if not already exists
        existing_collab = await self.collab_repo.get_collaborator(
            share_link.event_id,
            current_user.id
        )

        if existing_collab:
            await self.db.commit()
            return existing_collab

        # Create new collaborator based on permission level
        role = CollaboratorRole.VIEWER if share_link.permission_level == "view" else CollaboratorRole.EDITOR
        permissions = self._get_role_permissions(role)

        collaborator = await self.collab_repo.create_collaborator(
            share_link.event_id,
            current_user.id,
            role,
            permissions
        )

        await self.db.commit()
        return collaborator

    async def get_event_share_links(
        self,
        event_id: UUID,
        current_user: User
    ) -> List[ShareLink]:
        """Get all share links for an event"""
        # TODO: Verify user has access

        share_links = await self.collab_repo.get_event_share_links(event_id)
        return share_links

    async def deactivate_share_link(
        self,
        link_id: UUID,
        current_user: User
    ) -> bool:
        """Deactivate a share link"""
        # TODO: Verify user has permission

        success = await self.collab_repo.deactivate_share_link(link_id)

        if success:
            await self.db.commit()

        return success

    # ========================================================================
    # Presence Operations
    # ========================================================================

    async def update_presence(
        self,
        event_id: UUID,
        current_user: User,
        page_url: Optional[str] = None
    ) -> CollaborationPresence:
        """Update user presence"""
        presence = await self.collab_repo.update_presence(
            event_id,
            current_user.id,
            page_url
        )

        await self.db.commit()
        return presence

    async def get_active_users(
        self,
        event_id: UUID,
        current_user: User,
        minutes: int = 5
    ) -> List[CollaborationPresence]:
        """Get currently active users"""
        # TODO: Verify user has access

        active_users = await self.collab_repo.get_active_presence(event_id, minutes)
        return active_users
