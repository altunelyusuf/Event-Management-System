"""
CelebraTech Event Management System - Collaboration API
Sprint 16: Collaboration & Sharing System
FastAPI endpoints for collaboration and sharing
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.collaboration import InvitationStatus
from app.schemas.collaboration import (
    EventCollaboratorCreate,
    EventCollaboratorUpdate,
    EventCollaboratorResponse,
    EventInvitationCreate,
    EventInvitationResponse,
    ActivityLogResponse,
    CommentCreate,
    CommentResponse,
    ShareLinkCreate,
    ShareLinkResponse,
    CollaborationPresenceResponse
)
from app.services.collaboration_service import CollaborationService

router = APIRouter(prefix="/collaboration", tags=["Collaboration & Sharing"])


# ============================================================================
# Collaborator Endpoints
# ============================================================================

@router.post(
    "/events/{event_id}/collaborators",
    response_model=EventCollaboratorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add collaborator",
    description="Add a collaborator to an event"
)
async def add_collaborator(
    event_id: UUID,
    collaborator_data: EventCollaboratorCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a collaborator to an event"""
    collab_service = CollaborationService(db)
    collaborator = await collab_service.add_collaborator(
        event_id,
        collaborator_data,
        current_user
    )
    return EventCollaboratorResponse.from_orm(collaborator)


@router.get(
    "/events/{event_id}/collaborators",
    response_model=List[EventCollaboratorResponse],
    summary="Get event collaborators",
    description="Get all collaborators for an event"
)
async def get_event_collaborators(
    event_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get collaborators for an event"""
    collab_service = CollaborationService(db)
    collaborators = await collab_service.get_event_collaborators(event_id, current_user)
    return [EventCollaboratorResponse.from_orm(c) for c in collaborators]


@router.put(
    "/events/{event_id}/collaborators/{user_id}",
    response_model=EventCollaboratorResponse,
    summary="Update collaborator",
    description="Update a collaborator's role and permissions"
)
async def update_collaborator(
    event_id: UUID,
    user_id: UUID,
    collaborator_data: EventCollaboratorUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a collaborator"""
    collab_service = CollaborationService(db)
    collaborator = await collab_service.update_collaborator(
        event_id,
        user_id,
        collaborator_data,
        current_user
    )
    return EventCollaboratorResponse.from_orm(collaborator)


@router.delete(
    "/events/{event_id}/collaborators/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove collaborator",
    description="Remove a collaborator from an event"
)
async def remove_collaborator(
    event_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a collaborator"""
    collab_service = CollaborationService(db)
    await collab_service.remove_collaborator(event_id, user_id, current_user)


# ============================================================================
# Invitation Endpoints
# ============================================================================

@router.post(
    "/events/{event_id}/invitations",
    response_model=EventInvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create invitation",
    description="Invite someone to collaborate on an event"
)
async def create_invitation(
    event_id: UUID,
    invitation_data: EventInvitationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create an event invitation"""
    collab_service = CollaborationService(db)
    invitation = await collab_service.create_invitation(
        event_id,
        invitation_data,
        current_user
    )
    return EventInvitationResponse.from_orm(invitation)


@router.get(
    "/events/{event_id}/invitations",
    response_model=List[EventInvitationResponse],
    summary="Get event invitations",
    description="Get all invitations for an event"
)
async def get_event_invitations(
    event_id: UUID,
    status_filter: Optional[InvitationStatus] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get invitations for an event"""
    collab_service = CollaborationService(db)
    invitations = await collab_service.get_event_invitations(
        event_id,
        current_user,
        status_filter
    )
    return [EventInvitationResponse.from_orm(i) for i in invitations]


@router.post(
    "/invitations/{invitation_id}/accept",
    response_model=EventCollaboratorResponse,
    summary="Accept invitation",
    description="Accept an event invitation"
)
async def accept_invitation(
    invitation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Accept an invitation"""
    collab_service = CollaborationService(db)
    collaborator = await collab_service.accept_invitation(invitation_id, current_user)
    return EventCollaboratorResponse.from_orm(collaborator)


# ============================================================================
# Activity Log Endpoints
# ============================================================================

@router.get(
    "/events/{event_id}/activity",
    response_model=List[ActivityLogResponse],
    summary="Get event activity",
    description="Get activity log for an event"
)
async def get_event_activity(
    event_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get activity log for an event"""
    collab_service = CollaborationService(db)
    activities = await collab_service.get_event_activity(
        event_id,
        current_user,
        limit,
        offset
    )
    return [ActivityLogResponse.from_orm(a) for a in activities]


# ============================================================================
# Comment Endpoints
# ============================================================================

@router.post(
    "/events/{event_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create comment",
    description="Add a comment to an entity"
)
async def create_comment(
    event_id: UUID,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a comment"""
    collab_service = CollaborationService(db)
    comment = await collab_service.create_comment(event_id, comment_data, current_user)
    return CommentResponse.from_orm(comment)


@router.get(
    "/comments/{entity_type}/{entity_id}",
    response_model=List[CommentResponse],
    summary="Get entity comments",
    description="Get all comments for an entity"
)
async def get_entity_comments(
    entity_type: str,
    entity_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get comments for an entity"""
    collab_service = CollaborationService(db)
    comments = await collab_service.get_entity_comments(entity_type, entity_id)
    return [CommentResponse.from_orm(c) for c in comments]


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete comment",
    description="Delete a comment"
)
async def delete_comment(
    comment_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a comment"""
    collab_service = CollaborationService(db)
    await collab_service.delete_comment(comment_id, current_user)


# ============================================================================
# Share Link Endpoints
# ============================================================================

@router.post(
    "/events/{event_id}/share-links",
    response_model=ShareLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create share link",
    description="Create a shareable link for an event"
)
async def create_share_link(
    event_id: UUID,
    share_data: ShareLinkCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a share link"""
    collab_service = CollaborationService(db)
    share_link = await collab_service.create_share_link(
        event_id,
        share_data,
        current_user
    )
    return ShareLinkResponse.from_orm(share_link)


@router.get(
    "/events/{event_id}/share-links",
    response_model=List[ShareLinkResponse],
    summary="Get share links",
    description="Get all share links for an event"
)
async def get_event_share_links(
    event_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get share links for an event"""
    collab_service = CollaborationService(db)
    share_links = await collab_service.get_event_share_links(event_id, current_user)
    return [ShareLinkResponse.from_orm(s) for s in share_links]


@router.post(
    "/share-links/{token}/join",
    response_model=EventCollaboratorResponse,
    summary="Join via share link",
    description="Use a share link to join as a collaborator"
)
async def use_share_link(
    token: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Use a share link to join"""
    collab_service = CollaborationService(db)
    collaborator = await collab_service.use_share_link(token, current_user)
    return EventCollaboratorResponse.from_orm(collaborator)


@router.delete(
    "/share-links/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate share link",
    description="Deactivate a share link"
)
async def deactivate_share_link(
    link_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a share link"""
    collab_service = CollaborationService(db)
    await collab_service.deactivate_share_link(link_id, current_user)


# ============================================================================
# Presence Endpoints
# ============================================================================

@router.post(
    "/events/{event_id}/presence",
    response_model=CollaborationPresenceResponse,
    summary="Update presence",
    description="Update user presence for real-time collaboration"
)
async def update_presence(
    event_id: UUID,
    page_url: Optional[str] = Query(None, description="Current page URL"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user presence"""
    collab_service = CollaborationService(db)
    presence = await collab_service.update_presence(event_id, current_user, page_url)
    return CollaborationPresenceResponse.from_orm(presence)


@router.get(
    "/events/{event_id}/active-users",
    response_model=List[CollaborationPresenceResponse],
    summary="Get active users",
    description="Get currently active users for an event"
)
async def get_active_users(
    event_id: UUID,
    minutes: int = Query(5, ge=1, le=60, description="Activity window in minutes"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get active users"""
    collab_service = CollaborationService(db)
    active_users = await collab_service.get_active_users(event_id, current_user, minutes)
    return [CollaborationPresenceResponse.from_orm(u) for u in active_users]
