"""
CelebraTech Event Management System - Messaging API
Sprint 7: Messaging System
FR-007: Real-time Communication
FastAPI endpoints for messaging operations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import math

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.services.messaging_service import MessagingService
from app.schemas.messaging import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
    MessageCreate,
    MessageUpdate,
    MessageResponse,
    MessageListResponse,
    ParticipantAdd,
    ParticipantUpdate,
    ConversationParticipantInfo,
    MarkAsRead,
    MarkConversationAsRead,
    TypingIndicatorCreate,
    TypingIndicatorResponse,
    MessageReactionCreate,
    MessageReactionResponse,
    ConversationFilters,
    MessageSearch,
    ConversationStats,
    ConversationType,
    ConversationStatus
)

router = APIRouter(prefix="/messaging", tags=["Messaging"])


# ============================================================================
# Conversation Endpoints
# ============================================================================

@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create conversation",
    description="Create a new conversation"
)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new conversation

    Business rules:
    - Direct conversations: Auto-reuse if exists between participants
    - Group conversations: Require title
    - Creator becomes owner
    """
    service = MessagingService(db)
    conversation = await service.create_conversation(conversation_data, current_user)
    return ConversationResponse.from_orm(conversation)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation",
    description="Get conversation by ID"
)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation by ID"""
    service = MessagingService(db)
    conversation = await service.get_conversation(conversation_id, current_user)
    return ConversationResponse.from_orm(conversation)


@router.put(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Update conversation",
    description="Update conversation details"
)
async def update_conversation(
    conversation_id: UUID,
    conversation_data: ConversationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update conversation

    Business rules:
    - Only owner can update
    - Can update title, description, status
    """
    service = MessagingService(db)
    conversation = await service.update_conversation(
        conversation_id,
        conversation_data,
        current_user
    )
    return ConversationResponse.from_orm(conversation)


@router.post(
    "/conversations/{conversation_id}/archive",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive conversation",
    description="Archive a conversation"
)
async def archive_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Archive conversation"""
    service = MessagingService(db)
    await service.archive_conversation(conversation_id, current_user)
    return None


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List conversations",
    description="List user's conversations with filters"
)
async def list_conversations(
    type: Optional[ConversationType] = Query(None, description="Filter by type"),
    status: Optional[ConversationStatus] = Query(None, description="Filter by status"),
    has_unread: Optional[bool] = Query(None, description="Filter by unread status"),
    is_pinned: Optional[bool] = Query(None, description="Filter by pinned"),
    is_muted: Optional[bool] = Query(None, description="Filter by muted"),
    booking_id: Optional[UUID] = Query(None, description="Filter by booking"),
    event_id: Optional[UUID] = Query(None, description="Filter by event"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List conversations with filtering

    Filters:
    - type: Conversation type (direct, group, support)
    - status: Conversation status (active, archived, blocked)
    - has_unread: Filter by unread messages
    - is_pinned: Filter by pinned conversations
    - is_muted: Filter by muted conversations
    - booking_id: Filter by related booking
    - event_id: Filter by related event
    """
    service = MessagingService(db)

    filters = ConversationFilters(
        type=type,
        status=status,
        has_unread=has_unread,
        is_pinned=is_pinned,
        is_muted=is_muted,
        booking_id=booking_id,
        event_id=event_id
    )

    conversations, total = await service.list_conversations(
        current_user,
        filters,
        page,
        page_size
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return ConversationListResponse(
        conversations=[ConversationResponse.from_orm(c) for c in conversations],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


# ============================================================================
# Participant Endpoints
# ============================================================================

@router.post(
    "/conversations/{conversation_id}/participants",
    response_model=ConversationParticipantInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Add participant",
    description="Add participant to conversation"
)
async def add_participant(
    conversation_id: UUID,
    participant_data: ParticipantAdd,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add participant to conversation

    Business rules:
    - Only owner can add participants
    - Cannot add to direct conversations
    """
    service = MessagingService(db)
    participant = await service.add_participant(
        conversation_id,
        participant_data,
        current_user
    )
    return ConversationParticipantInfo.from_orm(participant)


@router.put(
    "/conversations/{conversation_id}/settings",
    response_model=ConversationParticipantInfo,
    summary="Update participant settings",
    description="Update own participant settings"
)
async def update_participant_settings(
    conversation_id: UUID,
    settings_data: ParticipantUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update participant settings

    Can update:
    - Notifications enabled/disabled
    - Notification sound
    - Mute status
    - Pin status
    """
    service = MessagingService(db)
    participant = await service.update_participant_settings(
        conversation_id,
        settings_data,
        current_user
    )
    return ConversationParticipantInfo.from_orm(participant)


@router.post(
    "/conversations/{conversation_id}/leave",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Leave conversation",
    description="Leave a conversation"
)
async def leave_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Leave conversation"""
    service = MessagingService(db)
    await service.leave_conversation(conversation_id, current_user)
    return None


# ============================================================================
# Message Endpoints
# ============================================================================

@router.post(
    "/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send message",
    description="Send a message in a conversation"
)
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message

    Business rules:
    - Must be participant in conversation
    - Content required for text messages
    - Attachments required for file/image messages
    """
    service = MessagingService(db)
    message = await service.send_message(message_data, current_user)
    return MessageResponse.from_orm(message)


@router.get(
    "/messages/{message_id}",
    response_model=MessageResponse,
    summary="Get message",
    description="Get message by ID"
)
async def get_message(
    message_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get message by ID"""
    service = MessagingService(db)
    message = await service.get_message(message_id, current_user)
    return MessageResponse.from_orm(message)


@router.put(
    "/messages/{message_id}",
    response_model=MessageResponse,
    summary="Update message",
    description="Update message content"
)
async def update_message(
    message_id: UUID,
    message_data: MessageUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update message

    Business rules:
    - Only sender can update
    - Can update within 15 minutes
    - Cannot update deleted messages
    """
    service = MessagingService(db)
    message = await service.update_message(message_id, message_data, current_user)
    return MessageResponse.from_orm(message)


@router.delete(
    "/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete message",
    description="Delete a message"
)
async def delete_message(
    message_id: UUID,
    delete_for_everyone: bool = Query(False, description="Delete for everyone"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete message

    Business rules:
    - Only sender can delete
    - Delete for everyone: within 1 hour
    - Delete for self: anytime
    """
    service = MessagingService(db)
    await service.delete_message(message_id, delete_for_everyone, current_user)
    return None


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
    summary="List messages",
    description="List messages in a conversation"
)
async def list_messages(
    conversation_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    before_message_id: Optional[UUID] = Query(None, description="Get messages before this ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List messages in conversation

    Supports cursor-based pagination with before_message_id
    Returns messages in chronological order (oldest first after reversal)
    """
    service = MessagingService(db)

    messages, total = await service.list_messages(
        conversation_id,
        current_user,
        page,
        page_size,
        before_message_id
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return MessageListResponse(
        messages=[MessageResponse.from_orm(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


@router.post(
    "/messages/search",
    response_model=MessageListResponse,
    summary="Search messages",
    description="Search messages across conversations"
)
async def search_messages(
    search_data: MessageSearch,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search messages

    Search across all conversations or within a specific conversation
    """
    service = MessagingService(db)

    messages, total = await service.search_messages(
        search_data,
        current_user,
        page,
        page_size
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return MessageListResponse(
        messages=[MessageResponse.from_orm(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


# ============================================================================
# Read Receipt Endpoints
# ============================================================================

@router.post(
    "/messages/read",
    response_model=dict,
    summary="Mark messages as read",
    description="Mark multiple messages as read"
)
async def mark_messages_as_read(
    mark_data: MarkAsRead,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark messages as read

    Creates read receipts for specified messages
    """
    service = MessagingService(db)
    receipts = await service.mark_messages_as_read(mark_data, current_user)
    return {"marked_count": len(receipts)}


@router.post(
    "/conversations/{conversation_id}/read",
    response_model=dict,
    summary="Mark conversation as read",
    description="Mark entire conversation as read"
)
async def mark_conversation_as_read(
    conversation_id: UUID,
    mark_data: MarkConversationAsRead,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark conversation as read

    Marks all messages up to a specific message (or all) as read
    """
    service = MessagingService(db)
    result = await service.mark_conversation_as_read(
        conversation_id,
        mark_data,
        current_user
    )
    return result


# ============================================================================
# Typing Indicator Endpoints
# ============================================================================

@router.post(
    "/typing",
    response_model=TypingIndicatorResponse,
    summary="Set typing indicator",
    description="Set typing indicator in conversation"
)
async def set_typing_indicator(
    typing_data: TypingIndicatorCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Set typing indicator

    Indicates user is typing in conversation
    Auto-expires after 10 seconds
    """
    service = MessagingService(db)
    indicator = await service.set_typing_indicator(typing_data, current_user)
    return TypingIndicatorResponse.from_orm(indicator)


@router.get(
    "/conversations/{conversation_id}/typing",
    response_model=List[TypingIndicatorResponse],
    summary="Get typing indicators",
    description="Get active typing indicators"
)
async def get_typing_indicators(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get active typing indicators in conversation"""
    service = MessagingService(db)
    indicators = await service.get_typing_indicators(conversation_id, current_user)
    return [TypingIndicatorResponse.from_orm(i) for i in indicators]


# ============================================================================
# Reaction Endpoints
# ============================================================================

@router.post(
    "/messages/{message_id}/reactions",
    response_model=MessageReactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add reaction",
    description="Add emoji reaction to message"
)
async def add_reaction(
    message_id: UUID,
    reaction_data: MessageReactionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add reaction to message

    Add emoji reaction to a message
    """
    service = MessagingService(db)
    reaction = await service.add_reaction(message_id, reaction_data, current_user)
    return MessageReactionResponse.from_orm(reaction)


@router.delete(
    "/messages/{message_id}/reactions/{emoji}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove reaction",
    description="Remove emoji reaction from message"
)
async def remove_reaction(
    message_id: UUID,
    emoji: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove reaction from message"""
    service = MessagingService(db)
    await service.remove_reaction(message_id, emoji, current_user)
    return None


@router.get(
    "/messages/{message_id}/reactions",
    response_model=List[MessageReactionResponse],
    summary="Get message reactions",
    description="Get all reactions for a message"
)
async def get_message_reactions(
    message_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all reactions for a message"""
    service = MessagingService(db)
    reactions = await service.get_message_reactions(message_id, current_user)
    return [MessageReactionResponse.from_orm(r) for r in reactions]


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get(
    "/stats",
    response_model=ConversationStats,
    summary="Get conversation statistics",
    description="Get user's conversation statistics"
)
async def get_conversation_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get conversation statistics

    Returns:
    - Total conversations
    - Unread conversations count
    - Total unread messages
    """
    service = MessagingService(db)
    stats = await service.get_conversation_stats(current_user)

    return ConversationStats(
        total_conversations=stats["total_conversations"],
        active_conversations=stats["total_conversations"],  # All are active
        archived_conversations=0,
        unread_conversations=stats["unread_conversations"],
        total_unread_messages=stats["total_unread_messages"],
        pinned_conversations=0
    )
