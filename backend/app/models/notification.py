"""
CelebraTech Event Management System - Notification Models
Sprint 8: Notification System
FR-008: Multi-channel Notification System
SQLAlchemy models for notifications
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

class NotificationType(str, enum.Enum):
    """Notification type"""
    # Booking notifications
    BOOKING_REQUEST_RECEIVED = "booking_request_received"
    BOOKING_REQUEST_ACCEPTED = "booking_request_accepted"
    BOOKING_REQUEST_REJECTED = "booking_request_rejected"
    QUOTE_RECEIVED = "quote_received"
    QUOTE_ACCEPTED = "quote_accepted"
    QUOTE_REJECTED = "quote_rejected"
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"

    # Payment notifications
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    REFUND_PROCESSED = "refund_processed"
    PAYOUT_PROCESSED = "payout_processed"

    # Review notifications
    REVIEW_RECEIVED = "review_received"
    REVIEW_RESPONSE_RECEIVED = "review_response_received"

    # Messaging notifications
    MESSAGE_RECEIVED = "message_received"

    # Event notifications
    EVENT_REMINDER = "event_reminder"
    EVENT_UPDATE = "event_update"

    # System notifications
    ACCOUNT_VERIFIED = "account_verified"
    PASSWORD_RESET = "password_reset"
    SECURITY_ALERT = "security_alert"
    SYSTEM_ANNOUNCEMENT = "system_announcement"


class NotificationPriority(str, enum.Enum):
    """Notification priority"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, enum.Enum):
    """Notification status"""
    PENDING = "pending"  # Created, not yet sent
    SENT = "sent"  # Sent to user
    DELIVERED = "delivered"  # Delivered to device
    READ = "read"  # User opened/read
    FAILED = "failed"  # Failed to send
    CANCELLED = "cancelled"  # Cancelled before sending


class NotificationChannel(str, enum.Enum):
    """Notification delivery channel"""
    IN_APP = "in_app"  # In-app notification
    EMAIL = "email"  # Email notification
    PUSH = "push"  # Push notification
    SMS = "sms"  # SMS notification


class DeliveryStatus(str, enum.Enum):
    """Delivery status for a specific channel"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


# ============================================================================
# Models
# ============================================================================

class Notification(Base):
    """
    Notification entity

    Represents a notification to a user across multiple channels.
    """
    __tablename__ = "notifications"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Recipient
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Notification Details
    type = Column(String(50), nullable=False, index=True)  # NotificationType
    priority = Column(String(20), default=NotificationPriority.NORMAL.value)
    status = Column(String(20), default=NotificationStatus.PENDING.value, index=True)

    # Content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    # Rich Content
    data = Column(JSONB, default={})  # Additional structured data

    # Action
    action_url = Column(String(500), nullable=True)  # Deep link or URL
    action_text = Column(String(100), nullable=True)  # Button text

    # Context (what triggered this notification)
    context_type = Column(String(50), nullable=True)  # booking, event, message, etc.
    context_id = Column(UUID(as_uuid=True), nullable=True)  # ID of the related entity

    # Actor (who triggered this notification)
    actor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Delivery Channels
    channels = Column(ARRAY(String(20)), default=list)  # List of NotificationChannel

    # Status Tracking
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)

    # Expiration
    expires_at = Column(DateTime, nullable=True)

    # Grouping (for notification grouping)
    group_key = Column(String(100), nullable=True, index=True)

    # Metadata
    metadata = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    actor = relationship("User", foreign_keys=[actor_id])

    deliveries = relationship(
        "NotificationDelivery",
        back_populates="notification",
        cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index('idx_notifications_user_status', 'user_id', 'status'),
        Index('idx_notifications_user_created', 'user_id', 'created_at'),
        Index('idx_notifications_type', 'type'),
        Index('idx_notifications_group', 'group_key'),
        Index('idx_notifications_context', 'context_type', 'context_id'),
    )

    def __repr__(self):
        return f"<Notification {self.id}: {self.type} to {self.user_id}>"


class NotificationDelivery(Base):
    """
    Notification delivery per channel

    Tracks delivery status for each channel (email, push, SMS).
    """
    __tablename__ = "notification_deliveries"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    notification_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Channel
    channel = Column(String(20), nullable=False)  # NotificationChannel

    # Status
    status = Column(String(20), default=DeliveryStatus.PENDING.value)

    # Delivery Details
    recipient = Column(String(255), nullable=True)  # Email address, phone number, device token

    # Provider Details (if using external service)
    provider = Column(String(50), nullable=True)  # SendGrid, Firebase, Twilio, etc.
    provider_id = Column(String(255), nullable=True)  # External ID from provider
    provider_response = Column(JSONB, nullable=True)  # Response from provider

    # Status Tracking
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    bounced_at = Column(DateTime, nullable=True)

    # Error Details
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    # Retry
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    notification = relationship("Notification", back_populates="deliveries")

    # Indexes
    __table_args__ = (
        Index('idx_deliveries_notification', 'notification_id'),
        Index('idx_deliveries_channel_status', 'channel', 'status'),
        Index('idx_deliveries_retry', 'next_retry_at'),
    )

    def __repr__(self):
        return f"<NotificationDelivery {self.id}: {self.channel} - {self.status}>"


class NotificationPreference(Base):
    """
    User notification preferences

    Controls which notifications a user receives and through which channels.
    """
    __tablename__ = "notification_preferences"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Notification Type
    notification_type = Column(String(50), nullable=False)  # NotificationType or 'all'

    # Channel Preferences
    in_app_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)

    # Frequency Control
    frequency = Column(String(20), default="immediate")  # immediate, daily_digest, weekly_digest

    # Quiet Hours
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(String(5), nullable=True)  # HH:MM format
    quiet_hours_end = Column(String(5), nullable=True)  # HH:MM format

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="notification_preferences")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'notification_type', name='unique_user_notification_type'),
        Index('idx_preferences_user', 'user_id'),
        Index('idx_preferences_type', 'notification_type'),
    )

    def __repr__(self):
        return f"<NotificationPreference {self.user_id}: {self.notification_type}>"


class NotificationTemplate(Base):
    """
    Notification template

    Templates for different notification types with variable substitution.
    """
    __tablename__ = "notification_templates"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Template Details
    notification_type = Column(String(50), nullable=False, unique=True)  # NotificationType
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Channel-specific Templates
    # In-app
    in_app_title = Column(String(200), nullable=True)
    in_app_message = Column(Text, nullable=True)

    # Email
    email_subject = Column(String(200), nullable=True)
    email_body_html = Column(Text, nullable=True)
    email_body_text = Column(Text, nullable=True)

    # Push
    push_title = Column(String(100), nullable=True)
    push_body = Column(String(200), nullable=True)

    # SMS
    sms_message = Column(String(160), nullable=True)

    # Variables (JSON schema of available variables)
    variables = Column(JSONB, default={})

    # Default Settings
    default_channels = Column(ARRAY(String(20)), default=list)
    default_priority = Column(String(20), default=NotificationPriority.NORMAL.value)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_templates_type', 'notification_type'),
        Index('idx_templates_active', 'is_active'),
    )

    def __repr__(self):
        return f"<NotificationTemplate {self.notification_type}>"


class NotificationDevice(Base):
    """
    User device for push notifications

    Stores device tokens for push notification delivery.
    """
    __tablename__ = "notification_devices"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Device Details
    device_token = Column(String(500), nullable=False, unique=True)  # FCM/APNS token
    device_type = Column(String(20), nullable=False)  # ios, android, web
    device_name = Column(String(200), nullable=True)  # User-friendly name

    # Platform Details
    platform = Column(String(20), nullable=False)  # fcm, apns
    app_version = Column(String(50), nullable=True)
    os_version = Column(String(50), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Last Activity
    last_used_at = Column(DateTime, default=datetime.utcnow)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="notification_devices")

    # Indexes
    __table_args__ = (
        Index('idx_devices_user', 'user_id'),
        Index('idx_devices_token', 'device_token'),
        Index('idx_devices_active', 'is_active'),
    )

    def __repr__(self):
        return f"<NotificationDevice {self.id}: {self.device_type}>"


class NotificationBatch(Base):
    """
    Notification batch for bulk sending

    Groups multiple notifications for efficient processing.
    """
    __tablename__ = "notification_batches"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Batch Details
    name = Column(String(200), nullable=False)
    notification_type = Column(String(50), nullable=False)

    # Target
    target_users = Column(ARRAY(UUID(as_uuid=True)), default=list)  # Specific users
    target_criteria = Column(JSONB, nullable=True)  # Query criteria for dynamic targeting

    # Content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSONB, default={})

    # Channels
    channels = Column(ARRAY(String(20)), default=list)

    # Scheduling
    scheduled_at = Column(DateTime, nullable=True)

    # Status
    status = Column(String(20), default="draft")  # draft, scheduled, processing, completed, failed

    # Progress
    total_count = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    # Processing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Created By
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        Index('idx_batches_status', 'status'),
        Index('idx_batches_scheduled', 'scheduled_at'),
    )

    def __repr__(self):
        return f"<NotificationBatch {self.id}: {self.name}>"
