"""
CelebraTech Event Management System - Messaging Schemas
Sprint 7: Messaging System
FR-007: Real-time Communication
Pydantic schemas for messaging data validation
"""
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from app.models.messaging import (
    ConversationType,
    ConversationStatus,
    MessageType,
    MessageStatus,
    ParticipantRole
)


# ============================================================================
# Conversation Schemas
# ============================================================================

class ConversationBase(BaseModel):
    """Base conversation fields"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    booking_id: Optional[UUID] = None
    event_id: Optional[UUID] = None


class ConversationCreate(BaseModel):
    """Schema for creating a conversation"""
    type: ConversationType = Field(ConversationType.DIRECT)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    participant_ids: List[UUID] = Field(..., min_items=1, max_items=50)
    booking_id: Optional[UUID] = None
    event_id: Optional[UUID] = None

    @validator('participant_ids')
    def validate_participants(cls, v, values):
        """Validate participant count based on conversation type"""
        conv_type = values.get('type', ConversationType.DIRECT)
        if conv_type == ConversationType.DIRECT and len(v) != 1:
            raise ValueError('Direct conversations must have exactly 1 other participant')
        return v

    @validator('title')
    def validate_title(cls, v, values):
        """Require title for group conversations"""
        conv_type = values.get('type')
        if conv_type == ConversationType.GROUP and not v:
            raise ValueError('Group conversations must have a title')
        return v


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[ConversationStatus] = None


class ConversationParticipantInfo(BaseModel):
    """Participant information"""
    id: UUID
    user_id: UUID
    role: str
    unread_count: int
    last_read_at: Optional[datetime]
    is_active: bool
    is_muted: bool
    is_pinned: bool
    joined_at: datetime

    # Extended user info (loaded separately)
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Response schema for conversation"""
    id: UUID
    type: str
    status: str
    title: Optional[str]
    description: Optional[str]
    booking_id: Optional[UUID]
    event_id: Optional[UUID]
    created_by: UUID
    last_message_at: Optional[datetime]
    last_message_preview: Optional[str]
    message_count: int
    created_at: datetime
    updated_at: Optional[datetime]

    # Participant info (loaded separately)
    participants: List[ConversationParticipantInfo] = []

    # Current user's participant info
    my_unread_count: Optional[int] = None
    my_last_read_at: Optional[datetime] = None
    is_muted: Optional[bool] = None
    is_pinned: Optional[bool] = None

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    """Summary schema for conversation list"""
    id: UUID
    type: str
    title: Optional[str]
    last_message_preview: Optional[str]
    last_message_at: Optional[datetime]
    unread_count: int
    is_muted: bool
    is_pinned: bool
    other_participants: List[str] = []  # Names of other participants

    class Config:
        from_attributes = True


# ============================================================================
# Message Schemas
# ============================================================================

class MessageAttachmentData(BaseModel):
    """Attachment data structure"""
    file_name: str
    file_type: str
    file_size: int
    file_url: str
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None


class MessageCreate(BaseModel):
    """Schema for creating a message"""
    conversation_id: UUID
    content: Optional[str] = Field(None, max_length=10000)
    type: MessageType = Field(MessageType.TEXT)
    reply_to_id: Optional[UUID] = None
    attachments: List[MessageAttachmentData] = Field(default_factory=list, max_items=10)

    @validator('content')
    def validate_content(cls, v, values):
        """Validate content based on message type"""
        msg_type = values.get('type', MessageType.TEXT)
        if msg_type == MessageType.TEXT and not v:
            raise ValueError('Text messages must have content')
        if v and len(v.strip()) == 0:
            raise ValueError('Content cannot be empty')
        return v

    @validator('attachments')
    def validate_attachments(cls, v, values):
        """Validate attachments based on message type"""
        msg_type = values.get('type', MessageType.TEXT)
        if msg_type in [MessageType.IMAGE, MessageType.FILE] and len(v) == 0:
            raise ValueError('Attachment messages must have at least one attachment')
        return v


class MessageUpdate(BaseModel):
    """Schema for updating a message"""
    content: str = Field(..., min_length=1, max_length=10000)


class MessageReadReceiptInfo(BaseModel):
    """Read receipt information"""
    user_id: UUID
    user_name: Optional[str] = None
    read_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Response schema for message"""
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    reply_to_id: Optional[UUID]
    type: str
    content: Optional[str]
    attachments: List[Dict[str, Any]] = []
    status: str
    sent_at: datetime
    delivered_at: Optional[datetime]
    read_by_all_at: Optional[datetime]
    is_edited: bool
    edited_at: Optional[datetime]
    is_deleted: bool
    created_at: datetime

    # Sender info (loaded separately)
    sender_name: Optional[str] = None
    sender_avatar: Optional[str] = None

    # Read receipts
    read_receipts: List[MessageReadReceiptInfo] = []

    # Reply info
    reply_to_preview: Optional[str] = None

    class Config:
        from_attributes = True


class MessageSummary(BaseModel):
    """Summary schema for message (list view)"""
    id: UUID
    sender_id: UUID
    sender_name: str
    content: Optional[str]
    type: str
    sent_at: datetime
    is_edited: bool

    class Config:
        from_attributes = True


# ============================================================================
# Participant Schemas
# ============================================================================

class ParticipantAdd(BaseModel):
    """Schema for adding participant to conversation"""
    user_id: UUID
    role: ParticipantRole = Field(ParticipantRole.MEMBER)


class ParticipantUpdate(BaseModel):
    """Schema for updating participant settings"""
    notifications_enabled: Optional[bool] = None
    notification_sound: Optional[bool] = None
    is_muted: Optional[bool] = None
    is_pinned: Optional[bool] = None


class ParticipantRoleUpdate(BaseModel):
    """Schema for updating participant role (admin only)"""
    role: ParticipantRole


# ============================================================================
# Read Receipt Schemas
# ============================================================================

class MarkAsRead(BaseModel):
    """Schema for marking messages as read"""
    message_ids: List[UUID] = Field(..., min_items=1, max_items=100)


class MarkConversationAsRead(BaseModel):
    """Schema for marking entire conversation as read"""
    up_to_message_id: Optional[UUID] = None  # If None, mark all as read


# ============================================================================
# Typing Indicator Schemas
# ============================================================================

class TypingIndicatorCreate(BaseModel):
    """Schema for typing indicator"""
    conversation_id: UUID
    is_typing: bool = Field(True)


class TypingIndicatorResponse(BaseModel):
    """Response schema for typing indicator"""
    conversation_id: UUID
    user_id: UUID
    user_name: str
    is_typing: bool
    started_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Message Reaction Schemas
# ============================================================================

class MessageReactionCreate(BaseModel):
    """Schema for adding reaction to message"""
    emoji: str = Field(..., min_length=1, max_length=10)

    @validator('emoji')
    def validate_emoji(cls, v):
        """Basic emoji validation"""
        # Allow common emojis (basic validation)
        # In production, use a proper emoji library
        if len(v.strip()) == 0:
            raise ValueError('Emoji cannot be empty')
        return v.strip()


class MessageReactionResponse(BaseModel):
    """Response schema for message reaction"""
    id: UUID
    message_id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    emoji: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageReactionSummary(BaseModel):
    """Summary of reactions on a message"""
    emoji: str
    count: int
    users: List[UUID] = []


# ============================================================================
# Attachment Schemas
# ============================================================================

class AttachmentUpload(BaseModel):
    """Schema for uploading attachment"""
    file_name: str = Field(..., max_length=255)
    file_type: str = Field(..., max_length=100)
    file_size: int = Field(..., gt=0, le=50_000_000)  # Max 50MB
    file_url: str = Field(..., max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    width: Optional[int] = Field(None, ge=0)
    height: Optional[int] = Field(None, ge=0)
    duration: Optional[int] = Field(None, ge=0)

    @validator('file_size')
    def validate_file_size(cls, v):
        """Validate file size"""
        max_size = 50 * 1024 * 1024  # 50MB
        if v > max_size:
            raise ValueError(f'File size cannot exceed {max_size} bytes')
        return v


class AttachmentResponse(BaseModel):
    """Response schema for attachment"""
    id: UUID
    message_id: UUID
    file_name: str
    file_type: str
    file_size: int
    file_url: str
    thumbnail_url: Optional[str]
    width: Optional[int]
    height: Optional[int]
    duration: Optional[int]
    uploaded_by: UUID
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Search and Filter Schemas
# ============================================================================

class ConversationFilters(BaseModel):
    """Filters for conversation queries"""
    type: Optional[ConversationType] = None
    status: Optional[ConversationStatus] = None
    has_unread: Optional[bool] = None
    is_pinned: Optional[bool] = None
    is_muted: Optional[bool] = None
    participant_id: Optional[UUID] = None
    booking_id: Optional[UUID] = None
    event_id: Optional[UUID] = None


class MessageSearch(BaseModel):
    """Schema for message search"""
    query: str = Field(..., min_length=2, max_length=200)
    conversation_id: Optional[UUID] = None
    sender_id: Optional[UUID] = None
    message_type: Optional[MessageType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @root_validator
    def validate_date_range(cls, values):
        """Ensure start_date <= end_date"""
        start = values.get('start_date')
        end = values.get('end_date')
        if start and end and start > end:
            raise ValueError('start_date cannot be after end_date')
        return values


# ============================================================================
# Pagination Schemas
# ============================================================================

class ConversationListResponse(BaseModel):
    """Paginated list of conversations"""
    conversations: List[ConversationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class MessageListResponse(BaseModel):
    """Paginated list of messages"""
    messages: List[MessageResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# ============================================================================
# Statistics Schemas
# ============================================================================

class ConversationStats(BaseModel):
    """Conversation statistics"""
    total_conversations: int
    active_conversations: int
    archived_conversations: int
    unread_conversations: int
    total_unread_messages: int
    pinned_conversations: int


class MessagingStats(BaseModel):
    """User messaging statistics"""
    total_messages_sent: int
    total_messages_received: int
    total_conversations: int
    average_response_time_minutes: Optional[float] = None
    most_active_conversation_id: Optional[UUID] = None


# ============================================================================
# Notification Schemas
# ============================================================================

class MessageNotification(BaseModel):
    """Schema for message notification"""
    conversation_id: UUID
    message_id: UUID
    sender_id: UUID
    sender_name: str
    content_preview: str
    timestamp: datetime


# ============================================================================
# Bulk Operations Schemas
# ============================================================================

class BulkArchiveConversations(BaseModel):
    """Schema for bulk archiving conversations"""
    conversation_ids: List[UUID] = Field(..., min_items=1, max_items=50)


class BulkDeleteMessages(BaseModel):
    """Schema for bulk deleting messages"""
    message_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    delete_for_everyone: bool = Field(False)


class BulkMarkAsRead(BaseModel):
    """Schema for bulk marking as read"""
    conversation_ids: List[UUID] = Field(..., min_items=1, max_items=50)
