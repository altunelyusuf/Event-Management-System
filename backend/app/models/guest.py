"""
Guest Management Models

This module defines the database models for guest management system including
guests, invitations, RSVPs, seating arrangements, and check-ins.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


# Enums
class GuestStatus(str, enum.Enum):
    """Guest status"""
    PENDING = "pending"  # Invitation not sent
    INVITED = "invited"  # Invitation sent
    CONFIRMED = "confirmed"  # RSVP confirmed
    DECLINED = "declined"  # RSVP declined
    TENTATIVE = "tentative"  # Maybe attending
    CHECKED_IN = "checked_in"  # Checked in at event
    NO_SHOW = "no_show"  # Did not attend


class RSVPStatus(str, enum.Enum):
    """RSVP response status"""
    PENDING = "pending"
    ATTENDING = "attending"
    NOT_ATTENDING = "not_attending"
    MAYBE = "maybe"


class InvitationStatus(str, enum.Enum):
    """Invitation delivery status"""
    DRAFT = "draft"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    RESPONDED = "responded"
    FAILED = "failed"


class GuestCategory(str, enum.Enum):
    """Guest category/group"""
    FAMILY = "family"
    FRIENDS = "friends"
    COLLEAGUES = "colleagues"
    VIP = "vip"
    BRIDE_SIDE = "bride_side"
    GROOM_SIDE = "groom_side"
    OTHER = "other"


class MealPreference(str, enum.Enum):
    """Meal preference types"""
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    HALAL = "halal"
    KOSHER = "kosher"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    NUT_ALLERGY = "nut_allergy"
    SEAFOOD_ALLERGY = "seafood_allergy"
    OTHER = "other"


class Guest(Base):
    """
    Guest model representing an individual guest for an event.

    A guest can be associated with an event, have RSVP status, dietary preferences,
    seating assignment, and check-in information.
    """
    __tablename__ = "guests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)

    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)

    # Guest Classification
    category = Column(String(20), default=GuestCategory.OTHER.value)
    status = Column(String(20), default=GuestStatus.PENDING.value)
    is_vip = Column(Boolean, default=False)

    # RSVP Information
    rsvp_status = Column(String(20), default=RSVPStatus.PENDING.value)
    rsvp_responded_at = Column(DateTime, nullable=True)
    attending_count = Column(Integer, default=1)  # Including plus-ones

    # Plus-One Information
    allows_plus_one = Column(Boolean, default=False)
    plus_one_name = Column(String(200), nullable=True)

    # Dietary & Special Requirements
    dietary_restrictions = Column(ARRAY(String(50)), default=list)
    meal_preference = Column(String(50), nullable=True)
    special_requirements = Column(Text, nullable=True)
    accessibility_needs = Column(Text, nullable=True)

    # Seating Information
    table_number = Column(Integer, nullable=True)
    seat_number = Column(Integer, nullable=True)
    seating_preference = Column(Text, nullable=True)  # Preferred to sit with

    # Check-In Information
    checked_in = Column(Boolean, default=False)
    checked_in_at = Column(DateTime, nullable=True)
    checked_in_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Contact & Communication
    invitation_sent_at = Column(DateTime, nullable=True)
    invitation_opened_at = Column(DateTime, nullable=True)
    reminder_sent_count = Column(Integer, default=0)
    last_reminder_sent_at = Column(DateTime, nullable=True)

    # Gift Registry (placeholder)
    gift_given = Column(Boolean, default=False)
    gift_description = Column(Text, nullable=True)

    # Additional Information
    notes = Column(Text, nullable=True)
    tags = Column(ARRAY(String(50)), default=list)
    age_group = Column(String(20), nullable=True)  # child, adult, senior

    # Group Membership
    group_id = Column(UUID(as_uuid=True), ForeignKey("guest_groups.id"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    event = relationship("Event", back_populates="guests")
    group = relationship("GuestGroup", back_populates="guests")
    invitations = relationship("GuestInvitation", back_populates="guest", cascade="all, delete-orphan")
    rsvp_responses = relationship("RSVPResponse", back_populates="guest", cascade="all, delete-orphan")
    checked_in_by_user = relationship("User", foreign_keys=[checked_in_by])
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        Index("idx_guest_event", "event_id"),
        Index("idx_guest_status", "status"),
        Index("idx_guest_rsvp_status", "rsvp_status"),
        Index("idx_guest_category", "category"),
        Index("idx_guest_email", "email"),
        Index("idx_guest_group", "group_id"),
        Index("idx_guest_table", "table_number"),
    )

    def __repr__(self):
        return f"<Guest {self.first_name} {self.last_name} ({self.email})>"


class GuestGroup(Base):
    """
    Guest group model for categorizing guests (family, friends, etc.)
    """
    __tablename__ = "guest_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)

    # Group Information
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(20), default=GuestCategory.OTHER.value)
    color_code = Column(String(7), nullable=True)  # Hex color for UI

    # Group Stats (denormalized for performance)
    total_guests = Column(Integer, default=0)
    confirmed_guests = Column(Integer, default=0)
    declined_guests = Column(Integer, default=0)
    pending_guests = Column(Integer, default=0)

    # Seating Preferences
    preferred_tables = Column(ARRAY(Integer), default=list)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    event = relationship("Event", back_populates="guest_groups")
    guests = relationship("Guest", back_populates="group")
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        Index("idx_guest_group_event", "event_id"),
        Index("idx_guest_group_category", "category"),
    )

    def __repr__(self):
        return f"<GuestGroup {self.name} ({self.total_guests} guests)>"


class GuestInvitation(Base):
    """
    Guest invitation model tracking invitation delivery and status
    """
    __tablename__ = "guest_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)

    # Invitation Details
    status = Column(String(20), default=InvitationStatus.DRAFT.value)
    invitation_type = Column(String(20), default="email")  # email, sms, physical

    # Content
    subject = Column(String(200), nullable=True)
    message = Column(Text, nullable=True)
    template_id = Column(UUID(as_uuid=True), nullable=True)  # Future: template system

    # Delivery Tracking
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    failure_reason = Column(Text, nullable=True)

    # Engagement Tracking
    open_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    last_opened_at = Column(DateTime, nullable=True)

    # Communication Channel
    sent_to_email = Column(String(255), nullable=True)
    sent_to_phone = Column(String(20), nullable=True)

    # Reminder
    is_reminder = Column(Boolean, default=False)
    reminder_number = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    sent_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    guest = relationship("Guest", back_populates="invitations")
    event = relationship("Event", back_populates="guest_invitations")
    sender = relationship("User", foreign_keys=[sent_by])

    # Indexes
    __table_args__ = (
        Index("idx_guest_invitation_guest", "guest_id"),
        Index("idx_guest_invitation_event", "event_id"),
        Index("idx_guest_invitation_status", "status"),
        Index("idx_guest_invitation_sent_at", "sent_at"),
    )

    def __repr__(self):
        return f"<GuestInvitation {self.invitation_type} - {self.status}>"


class RSVPResponse(Base):
    """
    RSVP response model tracking guest responses to invitations
    """
    __tablename__ = "rsvp_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)

    # Response Details
    status = Column(String(20), default=RSVPStatus.PENDING.value)
    attending_count = Column(Integer, default=1)  # Number of people attending

    # Plus-One Details
    plus_one_attending = Column(Boolean, default=False)
    plus_one_name = Column(String(200), nullable=True)
    plus_one_dietary_restrictions = Column(ARRAY(String(50)), default=list)

    # Dietary Information
    dietary_restrictions = Column(ARRAY(String(50)), default=list)
    meal_preference = Column(String(50), nullable=True)

    # Response Message
    message = Column(Text, nullable=True)  # Guest's message/note
    special_requests = Column(Text, nullable=True)

    # Song Requests (for wedding receptions)
    song_requests = Column(ARRAY(String(200)), default=list)

    # Accommodation Needs
    needs_accommodation = Column(Boolean, default=False)
    accommodation_details = Column(Text, nullable=True)

    # Transportation
    needs_transportation = Column(Boolean, default=False)
    transportation_details = Column(Text, nullable=True)

    # Response Tracking
    responded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    response_method = Column(String(20), nullable=True)  # web, email, phone, sms
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Updates
    is_latest = Column(Boolean, default=True)  # Track if this is the latest response
    previous_response_id = Column(UUID(as_uuid=True), ForeignKey("rsvp_responses.id"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    guest = relationship("Guest", back_populates="rsvp_responses")
    event = relationship("Event", back_populates="rsvp_responses")
    previous_response = relationship("RSVPResponse", remote_side=[id], foreign_keys=[previous_response_id])

    # Indexes
    __table_args__ = (
        Index("idx_rsvp_guest", "guest_id"),
        Index("idx_rsvp_event", "event_id"),
        Index("idx_rsvp_status", "status"),
        Index("idx_rsvp_is_latest", "is_latest"),
        Index("idx_rsvp_responded_at", "responded_at"),
    )

    def __repr__(self):
        return f"<RSVPResponse {self.status} - {self.attending_count} attending>"


class SeatingArrangement(Base):
    """
    Seating arrangement model for managing table and seat assignments
    """
    __tablename__ = "seating_arrangements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)

    # Table Information
    table_number = Column(Integer, nullable=False)
    table_name = Column(String(100), nullable=True)  # Optional table name (VIP, Family, etc.)
    table_capacity = Column(Integer, default=8)
    table_shape = Column(String(20), nullable=True)  # round, rectangle, square

    # Location
    section = Column(String(50), nullable=True)  # Main hall, Garden, etc.
    position_x = Column(Integer, nullable=True)  # For floor plan
    position_y = Column(Integer, nullable=True)

    # Table Details
    is_vip_table = Column(Boolean, default=False)
    is_kids_table = Column(Boolean, default=False)
    table_type = Column(String(20), nullable=True)  # head_table, guest_table, vendor_table

    # Occupancy
    assigned_seats = Column(Integer, default=0)
    reserved_seats = Column(Integer, default=0)

    # Special Features
    special_features = Column(ARRAY(String(50)), default=list)  # centerpiece, vip_service, etc.
    notes = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    event = relationship("Event", back_populates="seating_arrangements")
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        Index("idx_seating_event", "event_id"),
        Index("idx_seating_table_number", "table_number"),
        UniqueConstraint("event_id", "table_number", name="uq_event_table_number"),
    )

    def __repr__(self):
        return f"<SeatingArrangement Table {self.table_number} ({self.assigned_seats}/{self.table_capacity})>"


class GuestCheckIn(Base):
    """
    Guest check-in model for tracking guest arrivals at events
    """
    __tablename__ = "guest_checkins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)

    # Check-In Details
    checked_in_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    checked_in_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Attendance
    actual_attending_count = Column(Integer, default=1)
    plus_one_checked_in = Column(Boolean, default=False)
    plus_one_name = Column(String(200), nullable=True)

    # Check-In Method
    check_in_method = Column(String(20), default="manual")  # manual, qr_code, nfc
    qr_code_scanned = Column(Boolean, default=False)

    # Location
    check_in_location = Column(String(100), nullable=True)  # Main entrance, VIP entrance
    check_in_device = Column(String(100), nullable=True)  # Device used for check-in

    # Gift/Favor
    gift_bag_given = Column(Boolean, default=False)
    name_tag_given = Column(Boolean, default=False)
    table_card_given = Column(Boolean, default=False)

    # Special Notes
    notes = Column(Text, nullable=True)
    special_assistance_provided = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    guest = relationship("Guest", foreign_keys=[guest_id])
    event = relationship("Event", back_populates="guest_checkins")
    checked_in_by_user = relationship("User", foreign_keys=[checked_in_by])

    # Indexes
    __table_args__ = (
        Index("idx_checkin_guest", "guest_id"),
        Index("idx_checkin_event", "event_id"),
        Index("idx_checkin_time", "checked_in_at"),
        # Prevent duplicate check-ins
        UniqueConstraint("guest_id", "event_id", name="uq_guest_event_checkin"),
    )

    def __repr__(self):
        return f"<GuestCheckIn {self.guest_id} at {self.checked_in_at}>"


class DietaryRestriction(Base):
    """
    Dietary restriction model for tracking meal preferences and allergies
    """
    __tablename__ = "dietary_restrictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Restriction Details
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # allergy, preference, religious
    severity = Column(String(20), nullable=True)  # mild, moderate, severe (for allergies)

    # Meal Planning
    alternative_options = Column(Text, nullable=True)
    kitchen_notes = Column(Text, nullable=True)

    # Usage Statistics
    usage_count = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    is_common = Column(Boolean, default=False)  # Common restrictions shown first

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_dietary_restriction_name", "name"),
        Index("idx_dietary_restriction_category", "category"),
        Index("idx_dietary_restriction_active", "is_active"),
    )

    def __repr__(self):
        return f"<DietaryRestriction {self.name}>"
