"""
CelebraTech Event Management System - Messaging Models
Sprint 7: Messaging System
FR-007: Real-time Communication
SQLAlchemy models for direct messaging
"""
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, Numeric,
    DateTime, ForeignKey, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
import enum

from app.core.database import Base


# ============================================================================
# Enumerations
# ============================================================================

class ConversationType(str, enum.Enum):
    """Conversation type"""
    DIRECT = "direct"  # One-on-one conversation
    GROUP = "group"  # Group conversation (future)
    SUPPORT = "support"  # Support conversation


class ConversationStatus(str, enum.Enum):
    """Conversation status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    BLOCKED = "blocked"


class MessageType(str, enum.Enum):
    """Message type"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"  # System-generated messages


class MessageStatus(str, enum.Enum):
    """Message delivery status"""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class ParticipantRole(str, enum.Enum):
    """Participant role in conversation"""
    OWNER = "owner"  # Conversation creator
    MEMBER = "member"  # Regular participant
    ADMIN = "admin"  # Group admin (future)


# ============================================================================
# Models
# ============================================================================

class Conversation(Base):
    """
    Conversation thread

    Represents a messaging thread between participants.
    Can be direct (1-on-1) or group (future).
    """
    __tablename__ = "conversations"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Conversation Type
    type = Column(String(20), default=ConversationType.DIRECT.value, nullable=False)
    status = Column(String(20), default=ConversationStatus.ACTIVE.value, nullable=False)

    # Conversation Details
    title = Column(String(200), nullable=True)  # For group conversations
    description = Column(Text, nullable=True)

    # Context (optional linking to booking, event, etc.)
    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Creator
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Last Activity
    last_message_at = Column(DateTime, nullable=True)
    last_message_preview = Column(Text, nullable=True)  # Last message preview

    # Message Count
    message_count = Column(Integer, default=0)

    # Metadata
    metadata = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    booking = relationship("Booking", foreign_keys=[booking_id])
    event = relationship("Event", foreign_keys=[event_id])

    participants = relationship(
        "ConversationParticipant",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )

    # Indexes
    __table_args__ = (
        Index('idx_conversations_type_status', 'type', 'status'),
        Index('idx_conversations_last_message', 'last_message_at'),
        Index('idx_conversations_booking', 'booking_id'),
        Index('idx_conversations_event', 'event_id'),
    )

    def __repr__(self):
        return f"<Conversation {self.id} ({self.type})>"


class ConversationParticipant(Base):
    """
    Conversation participant

    Tracks users participating in a conversation with their role,
    read status, and notification preferences.
    """
    __tablename__ = "conversation_participants"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Role
    role = Column(String(20), default=ParticipantRole.MEMBER.value, nullable=False)

    # Read Status
    last_read_at = Column(DateTime, nullable=True)
    last_read_message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True
    )
    unread_count = Column(Integer, default=0)

    # Notification Preferences
    notifications_enabled = Column(Boolean, default=True)
    notification_sound = Column(Boolean, default=True)

    # Participation Status
    is_active = Column(Boolean, default=True)  # Active in conversation
    is_muted = Column(Boolean, default=False)  # Muted notifications
    is_pinned = Column(Boolean, default=False)  # Pinned conversation

    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    left_at = Column(DateTime, nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="participants")
    user = relationship("User", foreign_keys=[user_id])
    last_read_message = relationship("Message", foreign_keys=[last_read_message_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint('conversation_id', 'user_id', name='unique_conversation_user'),
        Index('idx_participants_conversation', 'conversation_id'),
        Index('idx_participants_user', 'user_id'),
        Index('idx_participants_unread', 'user_id', 'unread_count'),
    )

    def __repr__(self):
        return f"<ConversationParticipant {self.user_id} in {self.conversation_id}>"


class Message(Base):
    """
    Message in a conversation

    Represents individual messages with content, attachments,
    delivery status, and read receipts.
    """
    __tablename__ = "messages"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sender_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Reply To (threading)
    reply_to_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Message Type
    type = Column(String(20), default=MessageType.TEXT.value, nullable=False)

    # Content
    content = Column(Text, nullable=True)  # Text content
    attachments = Column(ARRAY(JSONB), default=list)  # Array of attachment objects

    # Status
    status = Column(String(20), default=MessageStatus.SENT.value, nullable=False)

    # Delivery Tracking
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    delivered_at = Column(DateTime, nullable=True)
    read_by_all_at = Column(DateTime, nullable=True)

    # Metadata
    metadata = Column(JSONB, default={})

    # Editing
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime, nullable=True)

    # Deletion
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_for_everyone = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])
    reply_to = relationship("Message", remote_side=[id], foreign_keys=[reply_to_id])

    read_receipts = relationship(
        "MessageReadReceipt",
        back_populates="message",
        cascade="all, delete-orphan"
    )
    attachments_rel = relationship(
        "MessageAttachment",
        back_populates="message",
        cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index('idx_messages_conversation_created', 'conversation_id', 'created_at'),
        Index('idx_messages_sender', 'sender_id'),
        Index('idx_messages_reply', 'reply_to_id'),
        Index('idx_messages_status', 'status'),
        CheckConstraint('content IS NOT NULL OR type != \'text\'', name='check_text_content'),
    )

    def __repr__(self):
        return f"<Message {self.id} from {self.sender_id}>"


class MessageReadReceipt(Base):
    """
    Message read receipt

    Tracks when each participant read a message.
    """
    __tablename__ = "message_read_receipts"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Read Status
    read_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    message = relationship("Message", back_populates="read_receipts")
    user = relationship("User")

    # Constraints
    __table_args__ = (
        UniqueConstraint('message_id', 'user_id', name='unique_message_user_read'),
        Index('idx_read_receipts_message', 'message_id'),
        Index('idx_read_receipts_user', 'user_id'),
    )

    def __repr__(self):
        return f"<MessageReadReceipt {self.user_id} read {self.message_id}>"


class MessageAttachment(Base):
    """
    Message attachment

    Stores file attachments for messages with metadata.
    """
    __tablename__ = "message_attachments"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    uploaded_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # File Details
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)  # MIME type
    file_size = Column(Integer, nullable=False)  # Bytes
    file_url = Column(String(500), nullable=False)

    # Image/Video Metadata (if applicable)
    thumbnail_url = Column(String(500), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)  # For videos/audio in seconds

    # Metadata
    metadata = Column(JSONB, default={})

    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    message = relationship("Message", back_populates="attachments_rel")
    uploader = relationship("User", foreign_keys=[uploaded_by])

    # Indexes
    __table_args__ = (
        Index('idx_attachments_message', 'message_id'),
        Index('idx_attachments_uploader', 'uploaded_by'),
        Index('idx_attachments_type', 'file_type'),
        CheckConstraint('file_size > 0', name='check_file_size'),
    )

    def __repr__(self):
        return f"<MessageAttachment {self.file_name}>"


class TypingIndicator(Base):
    """
    Typing indicator

    Tracks active typing status in conversations.
    Short-lived records (typically 5-10 seconds).
    """
    __tablename__ = "typing_indicators"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Status
    is_typing = Column(Boolean, default=True, nullable=False)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)  # Auto-expire after 10 seconds

    # Relationships
    conversation = relationship("Conversation")
    user = relationship("User")

    # Constraints
    __table_args__ = (
        UniqueConstraint('conversation_id', 'user_id', name='unique_typing_user'),
        Index('idx_typing_conversation', 'conversation_id'),
        Index('idx_typing_expires', 'expires_at'),
    )

    def __repr__(self):
        return f"<TypingIndicator {self.user_id} in {self.conversation_id}>"


class MessageReaction(Base):
    """
    Message reaction (emoji reactions)

    Allows users to react to messages with emojis.
    """
    __tablename__ = "message_reactions"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Reaction
    emoji = Column(String(10), nullable=False)  # Unicode emoji

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    message = relationship("Message")
    user = relationship("User")

    # Constraints
    __table_args__ = (
        UniqueConstraint('message_id', 'user_id', 'emoji', name='unique_message_user_reaction'),
        Index('idx_reactions_message', 'message_id'),
        Index('idx_reactions_user', 'user_id'),
    )

    def __repr__(self):
        return f"<MessageReaction {self.emoji} by {self.user_id}>"
