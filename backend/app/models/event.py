"""
CelebraTech Event Management System - Event Models
Sprint 2: Event Management Core
FR-002: Event Creation & Lifecycle Management
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer, Numeric, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class EventType(str, enum.Enum):
    """Event type enumeration"""
    TURKISH_WEDDING = "TURKISH_WEDDING"
    MIDDLE_EASTERN_WEDDING = "MIDDLE_EASTERN_WEDDING"
    INDIAN_WEDDING = "INDIAN_WEDDING"
    ENGAGEMENT = "ENGAGEMENT"
    CIRCUMCISION = "CIRCUMCISION"
    BABY_SHOWER = "BABY_SHOWER"
    ANNIVERSARY = "ANNIVERSARY"
    OTHER = "OTHER"


class EventStatus(str, enum.Enum):
    """Event status enumeration"""
    DRAFT = "DRAFT"
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EventPhaseType(str, enum.Enum):
    """Event phase enumeration (11 phases)"""
    IDEATION = "IDEATION"
    BUDGETING = "BUDGETING"
    VENDOR_RESEARCH = "VENDOR_RESEARCH"
    BOOKING = "BOOKING"
    DETAILED_PLANNING = "DETAILED_PLANNING"
    GUEST_MANAGEMENT = "GUEST_MANAGEMENT"
    TIMELINE_CREATION = "TIMELINE_CREATION"
    FINAL_COORDINATION = "FINAL_COORDINATION"
    EXECUTION = "EXECUTION"
    POST_EVENT = "POST_EVENT"
    ANALYSIS = "ANALYSIS"


class EventVisibility(str, enum.Enum):
    """Event visibility enumeration"""
    PRIVATE = "PRIVATE"
    SHARED = "SHARED"
    PUBLIC = "PUBLIC"


class Event(Base):
    """
    Event model - Core event entity
    Manages complete event lifecycle through 11 phases
    """
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    type = Column(SQLEnum(EventType), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Event dates
    event_date = Column(DateTime(timezone=True), nullable=False, index=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    # Status and phase
    status = Column(SQLEnum(EventStatus), default=EventStatus.DRAFT, nullable=False, index=True)
    current_phase = Column(SQLEnum(EventPhaseType), default=EventPhaseType.IDEATION, nullable=False, index=True)

    # Venue
    venue_id = Column(UUID(as_uuid=True), nullable=True)  # Will link to vendors later
    venue_name = Column(String(255), nullable=True)
    venue_address = Column(Text, nullable=True)

    # Guest count
    guest_count_estimate = Column(Integer, nullable=True)
    guest_count_confirmed = Column(Integer, default=0)

    # Budget
    budget_amount = Column(Numeric(15, 2), nullable=True)
    budget_currency = Column(String(3), default="TRY")
    spent_amount = Column(Numeric(15, 2), default=0)

    # Cultural context
    cultural_type = Column(String(100), nullable=True)

    # Sustainability
    sustainability_score = Column(Numeric(5, 2), nullable=True)

    # Visibility
    visibility = Column(SQLEnum(EventVisibility), default=EventVisibility.PRIVATE, nullable=False)

    # Metadata
    metadata = Column(JSON, default={})

    # Ownership
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    organizers = relationship("EventOrganizer", back_populates="event", cascade="all, delete-orphan")
    phases = relationship("EventPhase", back_populates="event", cascade="all, delete-orphan")
    milestones = relationship("EventMilestone", back_populates="event", cascade="all, delete-orphan")
    cultural_elements = relationship("EventCulturalElement", back_populates="event", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Event {self.name} ({self.type})>"


class OrganizerRole(str, enum.Enum):
    """Event organizer role enumeration"""
    PRIMARY = "PRIMARY"
    CO_ORGANIZER = "CO_ORGANIZER"
    FAMILY_MEMBER = "FAMILY_MEMBER"
    PLANNER = "PLANNER"
    VIEWER = "VIEWER"


class OrganizerStatus(str, enum.Enum):
    """Organizer invitation status"""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    REMOVED = "REMOVED"


class EventOrganizer(Base):
    """
    Event organizer model - Many-to-many relationship with permissions
    Manages collaboration between multiple organizers
    """
    __tablename__ = "event_organizers"

    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    role = Column(SQLEnum(OrganizerRole), nullable=False, index=True)

    # Permissions
    permissions = Column(JSON, default={
        "view": True,
        "edit": False,
        "invite": False,
        "book": False,
        "financial": False
    })

    # Invitation tracking
    invited_at = Column(DateTime(timezone=True), server_default=func.now())
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(OrganizerStatus), default=OrganizerStatus.PENDING)

    # Relationships
    event = relationship("Event", back_populates="organizers")
    user = relationship("User")

    def __repr__(self):
        return f"<EventOrganizer {self.user_id} for {self.event_id} ({self.role})>"


class PhaseStatus(str, enum.Enum):
    """Phase status enumeration"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"


class EventPhase(Base):
    """
    Event phase model - Tracks progress through 11 event phases
    """
    __tablename__ = "event_phases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    phase_name = Column(SQLEnum(EventPhaseType), nullable=False)
    phase_order = Column(Integer, nullable=False)
    status = Column(SQLEnum(PhaseStatus), default=PhaseStatus.PENDING, nullable=False, index=True)

    # Progress tracking
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completion_percentage = Column(Numeric(5, 2), default=0)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    event = relationship("Event", back_populates="phases")

    def __repr__(self):
        return f"<EventPhase {self.phase_name} for event {self.event_id}>"


class EventMilestone(Base):
    """
    Event milestone model - Key milestones in event timeline
    """
    __tablename__ = "event_milestones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    is_critical = Column(Boolean, default=False)
    order_index = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    event = relationship("Event", back_populates="milestones")

    def __repr__(self):
        return f"<EventMilestone {self.title} for event {self.event_id}>"


class EventCulturalElement(Base):
    """
    Event cultural element model - Tracks cultural traditions and rituals
    """
    __tablename__ = "event_cultural_elements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    element_type = Column(String(100), nullable=False, index=True)
    element_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    timing = Column(String(100), nullable=True)
    is_required = Column(Boolean, default=False)
    is_included = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    event = relationship("Event", back_populates="cultural_elements")

    def __repr__(self):
        return f"<EventCulturalElement {self.element_name} for event {self.event_id}>"
