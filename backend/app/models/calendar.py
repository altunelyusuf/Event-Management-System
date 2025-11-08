"""
Calendar & Scheduling Models
Sprint 14: Calendar & Scheduling System

Database models for calendar management, availability tracking,
booking conflicts, and external calendar synchronization.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    Text, ForeignKey, JSON, Index, UniqueConstraint, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


# ============================================================================
# Enums
# ============================================================================

class CalendarType(str, enum.Enum):
    """Calendar type enumeration"""
    EVENT = "event"
    VENDOR = "vendor"
    PERSONAL = "personal"
    SHARED = "shared"


class CalendarViewType(str, enum.Enum):
    """Calendar view types"""
    MONTH = "month"
    WEEK = "week"
    DAY = "day"
    AGENDA = "agenda"
    TIMELINE = "timeline"


class AvailabilityStatus(str, enum.Enum):
    """Availability status"""
    AVAILABLE = "available"
    BOOKED = "booked"
    BLOCKED = "blocked"
    TENTATIVE = "tentative"


class RecurrenceFrequency(str, enum.Enum):
    """Recurrence frequency"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class ConflictType(str, enum.Enum):
    """Booking conflict types"""
    DOUBLE_BOOKING = "double_booking"
    VENDOR_UNAVAILABLE = "vendor_unavailable"
    VENUE_CONFLICT = "venue_conflict"
    RESOURCE_CONFLICT = "resource_conflict"
    TIME_OVERLAP = "time_overlap"


class CalendarSyncProvider(str, enum.Enum):
    """External calendar providers"""
    GOOGLE = "google"
    OUTLOOK = "outlook"
    APPLE = "apple"
    ICAL = "ical"


class SharePermission(str, enum.Enum):
    """Calendar sharing permissions"""
    VIEW = "view"
    EDIT = "edit"
    ADMIN = "admin"


# ============================================================================
# Calendar Models
# ============================================================================

class Calendar(Base):
    """
    Calendar instances for events, vendors, or users.

    Supports multiple calendar types and views.
    Can be synced with external calendars.
    """
    __tablename__ = "calendars"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Ownership
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=True, index=True)

    # Calendar details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(20), default=CalendarType.EVENT.value, index=True)
    color = Column(String(7), default="#3788d8")  # Hex color for UI

    # Settings (JSON)
    settings = Column(JSON, default={
        "timezone": "UTC",
        "week_start": "monday",
        "work_hours_start": "09:00",
        "work_hours_end": "18:00",
        "default_view": "month",
        "default_duration": 60
    })

    # Visibility
    is_public = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="calendars")
    event = relationship("Event", foreign_keys=[event_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    calendar_events = relationship("CalendarEvent", back_populates="calendar", cascade="all, delete-orphan")
    shares = relationship("CalendarShare", back_populates="calendar", cascade="all, delete-orphan")
    syncs = relationship("CalendarSync", back_populates="calendar", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_calendar_user', 'user_id'),
        Index('idx_calendar_event', 'event_id'),
        Index('idx_calendar_vendor', 'vendor_id'),
        Index('idx_calendar_type', 'type'),
    )


# ============================================================================
# Calendar Event Models
# ============================================================================

class CalendarEvent(Base):
    """
    Events on calendars with scheduling information.

    Supports:
    - All-day and timed events
    - Recurring events
    - Reminders
    - Attachments
    - Location
    """
    __tablename__ = "calendar_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Calendar reference
    calendar_id = Column(UUID(as_uuid=True), ForeignKey("calendars.id", ondelete="CASCADE"), nullable=False, index=True)

    # Event details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)

    # Timing
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    all_day = Column(Boolean, default=False)
    timezone = Column(String(50), default="UTC")

    # Recurrence
    is_recurring = Column(Boolean, default=False)
    recurrence_rule_id = Column(UUID(as_uuid=True), ForeignKey("recurring_event_rules.id"), nullable=True)
    recurrence_parent_id = Column(UUID(as_uuid=True), ForeignKey("calendar_events.id"), nullable=True)

    # References
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True)  # Link to main event
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True)  # Link to booking
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)  # Link to task

    # Participants (JSON array)
    attendees = Column(JSON, default=[])  # [{email, name, status}]

    # Reminders (JSON array)
    reminders = Column(JSON, default=[])  # [{type: email/push, minutes_before: 30}]

    # Status
    status = Column(String(20), default="confirmed")  # confirmed, tentative, cancelled
    is_private = Column(Boolean, default=False)

    # Metadata
    metadata = Column(JSON, default={})
    attachments = Column(JSON, default=[])  # [{url, name, size}]

    # External sync
    external_id = Column(String(200), nullable=True)  # ID from external calendar
    sync_provider = Column(String(20), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    calendar = relationship("Calendar", back_populates="calendar_events")
    recurrence_rule = relationship("RecurringEventRule", foreign_keys=[recurrence_rule_id])
    recurrence_parent = relationship("CalendarEvent", remote_side=[id], backref="recurrence_instances")
    main_event = relationship("Event", foreign_keys=[event_id])
    booking = relationship("Booking", foreign_keys=[booking_id])
    task = relationship("Task", foreign_keys=[task_id])

    # Indexes
    __table_args__ = (
        Index('idx_calendar_event_calendar', 'calendar_id'),
        Index('idx_calendar_event_time', 'start_time', 'end_time'),
        Index('idx_calendar_event_recurring', 'is_recurring'),
        Index('idx_calendar_event_external', 'external_id'),
    )


# ============================================================================
# Recurring Event Rules
# ============================================================================

class RecurringEventRule(Base):
    """
    Rules for recurring events (RRULE format).

    Supports standard recurrence patterns:
    - Daily, weekly, monthly, yearly
    - Complex patterns with intervals
    - Exception dates
    """
    __tablename__ = "recurring_event_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Recurrence pattern
    frequency = Column(String(20), nullable=False)  # daily, weekly, monthly, yearly
    interval = Column(Integer, default=1)  # Every N days/weeks/months/years

    # Weekly recurrence
    by_day = Column(ARRAY(String(3)), nullable=True)  # ['MO', 'WE', 'FR']

    # Monthly recurrence
    by_month_day = Column(ARRAY(Integer), nullable=True)  # [1, 15]
    by_set_pos = Column(Integer, nullable=True)  # 1st, 2nd, -1st (last)

    # Yearly recurrence
    by_month = Column(ARRAY(Integer), nullable=True)  # [1, 6, 12]

    # End conditions
    count = Column(Integer, nullable=True)  # Number of occurrences
    until = Column(DateTime, nullable=True)  # End date

    # Exception dates
    exception_dates = Column(ARRAY(DateTime), default=list)

    # RRULE string (for iCal compatibility)
    rrule_string = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_recurring_rule_frequency', 'frequency'),
    )


# ============================================================================
# Vendor Availability Models
# ============================================================================

class VendorAvailability(Base):
    """
    Vendor availability slots and booking status.

    Tracks when vendors are available, booked, or blocked.
    Supports recurring availability patterns.
    """
    __tablename__ = "vendor_availability"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Vendor reference
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)

    # Time slot
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)

    # Status
    status = Column(String(20), default=AvailabilityStatus.AVAILABLE.value, index=True)

    # Booking reference (if booked)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True)

    # Recurring availability
    is_recurring = Column(Boolean, default=False)
    recurrence_rule_id = Column(UUID(as_uuid=True), ForeignKey("recurring_event_rules.id"), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)
    reason = Column(String(200), nullable=True)  # Reason for blocking

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    vendor = relationship("Vendor", backref="availability_slots")
    booking = relationship("Booking", foreign_keys=[booking_id])
    event = relationship("Event", foreign_keys=[event_id])
    recurrence_rule = relationship("RecurringEventRule")

    # Indexes
    __table_args__ = (
        Index('idx_vendor_availability_vendor', 'vendor_id'),
        Index('idx_vendor_availability_time', 'start_time', 'end_time'),
        Index('idx_vendor_availability_status', 'status'),
    )


# ============================================================================
# Booking Conflict Models
# ============================================================================

class BookingConflict(Base):
    """
    Detected booking conflicts.

    Tracks conflicts between bookings, availability,
    and calendar events for resolution.
    """
    __tablename__ = "booking_conflicts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Conflict type
    conflict_type = Column(String(30), nullable=False, index=True)

    # Involved entities
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True)

    # Conflicting entity
    conflicting_booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True)
    conflicting_event_id = Column(UUID(as_uuid=True), ForeignKey("calendar_events.id"), nullable=True)

    # Time details
    conflict_start = Column(DateTime, nullable=False)
    conflict_end = Column(DateTime, nullable=False)

    # Conflict details
    description = Column(Text, nullable=False)
    severity = Column(String(20), default="medium")  # low, medium, high, critical

    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Timestamps
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    booking = relationship("Booking", foreign_keys=[booking_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    event = relationship("Event", foreign_keys=[event_id])
    conflicting_booking = relationship("Booking", foreign_keys=[conflicting_booking_id])
    conflicting_event = relationship("CalendarEvent", foreign_keys=[conflicting_event_id])
    resolver = relationship("User", foreign_keys=[resolved_by])

    # Indexes
    __table_args__ = (
        Index('idx_conflict_type', 'conflict_type'),
        Index('idx_conflict_resolved', 'is_resolved'),
        Index('idx_conflict_detected', 'detected_at'),
        Index('idx_conflict_booking', 'booking_id'),
        Index('idx_conflict_vendor', 'vendor_id'),
    )


# ============================================================================
# Calendar Sync Models
# ============================================================================

class CalendarSync(Base):
    """
    External calendar synchronization configuration.

    Supports sync with Google Calendar, Outlook, Apple Calendar.
    Tracks sync status and errors.
    """
    __tablename__ = "calendar_syncs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Calendar reference
    calendar_id = Column(UUID(as_uuid=True), ForeignKey("calendars.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Provider details
    provider = Column(String(20), nullable=False, index=True)  # google, outlook, apple, ical
    external_calendar_id = Column(String(200), nullable=False)
    external_calendar_name = Column(String(200), nullable=True)

    # Sync settings
    sync_direction = Column(String(20), default="two_way")  # one_way_to_external, one_way_from_external, two_way
    sync_enabled = Column(Boolean, default=True)
    sync_frequency_minutes = Column(Integer, default=15)

    # Auth tokens (encrypted)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    # Sync status
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(20), default="pending")  # success, failed, pending
    last_sync_error = Column(Text, nullable=True)
    sync_count = Column(Integer, default=0)

    # Statistics
    events_synced_to_external = Column(Integer, default=0)
    events_synced_from_external = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    calendar = relationship("Calendar", back_populates="syncs")
    user = relationship("User", backref="calendar_syncs")

    # Indexes
    __table_args__ = (
        Index('idx_calendar_sync_calendar', 'calendar_id'),
        Index('idx_calendar_sync_provider', 'provider'),
        Index('idx_calendar_sync_enabled', 'sync_enabled'),
        UniqueConstraint('calendar_id', 'provider', 'external_calendar_id', name='uq_calendar_sync'),
    )


# ============================================================================
# Calendar Share Models
# ============================================================================

class CalendarShare(Base):
    """
    Calendar sharing with other users.

    Supports different permission levels:
    - View only
    - Edit events
    - Admin (share calendar, change settings)
    """
    __tablename__ = "calendar_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    calendar_id = Column(UUID(as_uuid=True), ForeignKey("calendars.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_with_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Permission
    permission = Column(String(20), default=SharePermission.VIEW.value)

    # Settings
    can_invite_others = Column(Boolean, default=False)
    send_notifications = Column(Boolean, default=True)

    # Status
    is_active = Column(Boolean, default=True)
    accepted_at = Column(DateTime, nullable=True)

    # Expiration
    expires_at = Column(DateTime, nullable=True)

    # Timestamps
    shared_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    calendar = relationship("Calendar", back_populates="shares")
    shared_with = relationship("User", foreign_keys=[shared_with_user_id], backref="shared_calendars")
    shared_by = relationship("User", foreign_keys=[shared_by_user_id])

    # Indexes
    __table_args__ = (
        Index('idx_calendar_share_calendar', 'calendar_id'),
        Index('idx_calendar_share_user', 'shared_with_user_id'),
        UniqueConstraint('calendar_id', 'shared_with_user_id', name='uq_calendar_share'),
    )
