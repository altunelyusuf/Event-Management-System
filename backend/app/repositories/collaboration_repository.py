"""
CelebraTech Event Management System - Collaboration Repository
Sprint 16: Collaboration & Sharing System
Data access layer for collaboration operations
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from uuid import UUID

from app.models.collaboration import (
    EventCollaborator,
    EventTeam,
    TeamMember,
    EventInvitation,
    ActivityLog,
    Comment,
    Mention,
    ShareLink,
    ResourceLock,
    CollaborationPresence,
    CollaboratorRole,
    InvitationStatus,
    ActivityType
)
from app.schemas.collaboration import (
    EventCollaboratorCreate,
    EventInvitationCreate,
    CommentCreate,
    ShareLinkCreate
)


class CollaborationRepository:
    """Repository for collaboration database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Event Collaborator Operations
    # ========================================================================

    async def create_collaborator(
        self,
        event_id: UUID,
        user_id: UUID,
        role: CollaboratorRole,
        permissions: Dict[str, bool]
    ) -> EventCollaborator:
        """Create a new event collaborator"""
        collaborator = EventCollaborator(
            event_id=event_id,
            user_id=user_id,
            role=role,
            can_view=permissions.get("can_view", True),
            can_edit=permissions.get("can_edit", False),
            can_delete=permissions.get("can_delete", False),
            can_share=permissions.get("can_share", False),
            can_manage_collaborators=permissions.get("can_manage_collaborators", False)
        )

        self.db.add(collaborator)
        await self.db.flush()
        await self.db.refresh(collaborator)

        return collaborator

    async def get_event_collaborators(self, event_id: UUID) -> List[EventCollaborator]:
        """Get all collaborators for an event"""
        query = select(EventCollaborator).where(
            EventCollaborator.event_id == event_id
        ).order_by(EventCollaborator.created_at)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_collaborator(
        self,
        event_id: UUID,
        user_id: UUID
    ) -> Optional[EventCollaborator]:
        """Get a specific collaborator"""
        query = select(EventCollaborator).where(
            and_(
                EventCollaborator.event_id == event_id,
                EventCollaborator.user_id == user_id
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_collaborator_role(
        self,
        event_id: UUID,
        user_id: UUID,
        role: CollaboratorRole,
        permissions: Dict[str, bool]
    ) -> Optional[EventCollaborator]:
        """Update a collaborator's role and permissions"""
        collaborator = await self.get_collaborator(event_id, user_id)
        if not collaborator:
            return None

        collaborator.role = role
        collaborator.can_view = permissions.get("can_view", True)
        collaborator.can_edit = permissions.get("can_edit", False)
        collaborator.can_delete = permissions.get("can_delete", False)
        collaborator.can_share = permissions.get("can_share", False)
        collaborator.can_manage_collaborators = permissions.get("can_manage_collaborators", False)
        collaborator.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(collaborator)

        return collaborator

    async def remove_collaborator(self, event_id: UUID, user_id: UUID) -> bool:
        """Remove a collaborator from an event"""
        collaborator = await self.get_collaborator(event_id, user_id)
        if not collaborator:
            return False

        await self.db.delete(collaborator)
        await self.db.flush()

        return True

    # ========================================================================
    # Invitation Operations
    # ========================================================================

    async def create_invitation(
        self,
        event_id: UUID,
        email: str,
        role: CollaboratorRole,
        invited_by: UUID,
        expires_at: Optional[datetime] = None
    ) -> EventInvitation:
        """Create an event invitation"""
        if not expires_at:
            expires_at = datetime.utcnow() + timedelta(days=7)

        invitation = EventInvitation(
            event_id=event_id,
            email=email,
            role=role,
            invited_by=invited_by,
            status=InvitationStatus.PENDING,
            expires_at=expires_at
        )

        self.db.add(invitation)
        await self.db.flush()
        await self.db.refresh(invitation)

        return invitation

    async def get_invitation_by_id(self, invitation_id: UUID) -> Optional[EventInvitation]:
        """Get invitation by ID"""
        query = select(EventInvitation).where(EventInvitation.id == invitation_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_event_invitations(
        self,
        event_id: UUID,
        status: Optional[InvitationStatus] = None
    ) -> List[EventInvitation]:
        """Get all invitations for an event"""
        query = select(EventInvitation).where(EventInvitation.event_id == event_id)

        if status:
            query = query.where(EventInvitation.status == status)

        query = query.order_by(EventInvitation.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def accept_invitation(
        self,
        invitation_id: UUID,
        user_id: UUID
    ) -> Optional[EventInvitation]:
        """Accept an invitation"""
        invitation = await self.get_invitation_by_id(invitation_id)
        if not invitation:
            return None

        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.utcnow()
        invitation.accepted_by = user_id

        await self.db.flush()
        await self.db.refresh(invitation)

        return invitation

    # ========================================================================
    # Activity Log Operations
    # ========================================================================

    async def create_activity_log(
        self,
        event_id: UUID,
        user_id: UUID,
        activity_type: ActivityType,
        description: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ActivityLog:
        """Create an activity log entry"""
        activity = ActivityLog(
            event_id=event_id,
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {}
        )

        self.db.add(activity)
        await self.db.flush()
        await self.db.refresh(activity)

        return activity

    async def get_event_activity(
        self,
        event_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[ActivityLog]:
        """Get activity log for an event"""
        query = select(ActivityLog).where(
            ActivityLog.event_id == event_id
        ).order_by(ActivityLog.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Comment Operations
    # ========================================================================

    async def create_comment(
        self,
        event_id: UUID,
        user_id: UUID,
        entity_type: str,
        entity_id: UUID,
        content: str,
        parent_id: Optional[UUID] = None
    ) -> Comment:
        """Create a comment"""
        comment = Comment(
            event_id=event_id,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            content=content,
            parent_id=parent_id
        )

        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)

        return comment

    async def get_entity_comments(
        self,
        entity_type: str,
        entity_id: UUID
    ) -> List[Comment]:
        """Get all comments for an entity"""
        query = select(Comment).where(
            and_(
                Comment.entity_type == entity_type,
                Comment.entity_id == entity_id,
                Comment.is_deleted == False
            )
        ).order_by(Comment.created_at)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_comment(self, comment_id: UUID) -> bool:
        """Soft delete a comment"""
        query = select(Comment).where(Comment.id == comment_id)
        result = await self.db.execute(query)
        comment = result.scalar_one_or_none()

        if not comment:
            return False

        comment.is_deleted = True
        comment.updated_at = datetime.utcnow()

        await self.db.flush()

        return True

    # ========================================================================
    # Share Link Operations
    # ========================================================================

    async def create_share_link(
        self,
        event_id: UUID,
        created_by: UUID,
        token: str,
        permission_level: str,
        expires_at: Optional[datetime] = None,
        max_uses: Optional[int] = None
    ) -> ShareLink:
        """Create a share link"""
        share_link = ShareLink(
            event_id=event_id,
            token=token,
            permission_level=permission_level,
            expires_at=expires_at,
            max_uses=max_uses,
            use_count=0,
            is_active=True,
            created_by=created_by
        )

        self.db.add(share_link)
        await self.db.flush()
        await self.db.refresh(share_link)

        return share_link

    async def get_share_link_by_token(self, token: str) -> Optional[ShareLink]:
        """Get share link by token"""
        query = select(ShareLink).where(
            and_(
                ShareLink.token == token,
                ShareLink.is_active == True
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def increment_share_link_usage(self, link_id: UUID) -> Optional[ShareLink]:
        """Increment share link usage count"""
        query = select(ShareLink).where(ShareLink.id == link_id)
        result = await self.db.execute(query)
        link = result.scalar_one_or_none()

        if not link:
            return None

        link.use_count += 1
        link.last_used_at = datetime.utcnow()

        # Deactivate if max uses reached
        if link.max_uses and link.use_count >= link.max_uses:
            link.is_active = False

        await self.db.flush()
        await self.db.refresh(link)

        return link

    async def get_event_share_links(self, event_id: UUID) -> List[ShareLink]:
        """Get all share links for an event"""
        query = select(ShareLink).where(
            ShareLink.event_id == event_id
        ).order_by(ShareLink.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def deactivate_share_link(self, link_id: UUID) -> bool:
        """Deactivate a share link"""
        query = select(ShareLink).where(ShareLink.id == link_id)
        result = await self.db.execute(query)
        link = result.scalar_one_or_none()

        if not link:
            return False

        link.is_active = False
        link.updated_at = datetime.utcnow()

        await self.db.flush()

        return True

    # ========================================================================
    # Collaboration Presence Operations
    # ========================================================================

    async def update_presence(
        self,
        event_id: UUID,
        user_id: UUID,
        page_url: Optional[str] = None
    ) -> CollaborationPresence:
        """Update or create user presence"""
        query = select(CollaborationPresence).where(
            and_(
                CollaborationPresence.event_id == event_id,
                CollaborationPresence.user_id == user_id
            )
        )

        result = await self.db.execute(query)
        presence = result.scalar_one_or_none()

        if presence:
            presence.last_seen_at = datetime.utcnow()
            presence.is_active = True
            if page_url:
                presence.page_url = page_url
        else:
            presence = CollaborationPresence(
                event_id=event_id,
                user_id=user_id,
                is_active=True,
                page_url=page_url
            )
            self.db.add(presence)

        await self.db.flush()
        await self.db.refresh(presence)

        return presence

    async def get_active_presence(
        self,
        event_id: UUID,
        minutes: int = 5
    ) -> List[CollaborationPresence]:
        """Get active users in the last N minutes"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        query = select(CollaborationPresence).where(
            and_(
                CollaborationPresence.event_id == event_id,
                CollaborationPresence.is_active == True,
                CollaborationPresence.last_seen_at >= cutoff_time
            )
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())
