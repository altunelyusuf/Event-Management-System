"""
CelebraTech Event Management System - Event Schemas
Sprint 2: Event Management Core
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.event import (
    EventType,
    EventStatus,
    EventPhaseType,
    EventVisibility,
    OrganizerRole,
    OrganizerStatus,
    PhaseStatus
)


# Base schemas
class EventBase(BaseModel):
    """Base event schema"""
    name: str = Field(..., min_length=1, max_length=255)
    type: EventType
    description: Optional[str] = None
    event_date: datetime
    end_date: Optional[datetime] = None


class EventCreate(EventBase):
    """Schema for event creation"""
    venue_name: Optional[str] = Field(None, max_length=255)
    venue_address: Optional[str] = None
    guest_count_estimate: Optional[int] = Field(None, ge=0)
    budget_amount: Optional[Decimal] = Field(None, ge=0)
    budget_currency: str = Field("TRY", max_length=3)
    cultural_type: Optional[str] = Field(None, max_length=100)
    visibility: EventVisibility = EventVisibility.PRIVATE

    @validator('end_date')
    def validate_end_date(cls, v, values):
        """Validate end date is after event date"""
        if v and 'event_date' in values and v < values['event_date']:
            raise ValueError("End date must be after event date")
        return v

    @validator('event_date')
    def validate_event_date(cls, v):
        """Validate event date is in the future"""
        if v < datetime.now():
            raise ValueError("Event date must be in the future")
        return v


class EventUpdate(BaseModel):
    """Schema for updating event"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    event_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    venue_name: Optional[str] = Field(None, max_length=255)
    venue_address: Optional[str] = None
    guest_count_estimate: Optional[int] = Field(None, ge=0)
    budget_amount: Optional[Decimal] = Field(None, ge=0)
    budget_currency: Optional[str] = Field(None, max_length=3)
    cultural_type: Optional[str] = Field(None, max_length=100)
    visibility: Optional[EventVisibility] = None


class EventResponse(EventBase):
    """Schema for event response"""
    id: UUID
    status: EventStatus
    current_phase: EventPhaseType
    venue_name: Optional[str]
    venue_address: Optional[str]
    guest_count_estimate: Optional[int]
    guest_count_confirmed: int
    budget_amount: Optional[Decimal]
    budget_currency: str
    spent_amount: Decimal
    cultural_type: Optional[str]
    sustainability_score: Optional[Decimal]
    visibility: EventVisibility
    created_by: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class EventDetailResponse(EventResponse):
    """Schema for detailed event response with relationships"""
    organizers: List["EventOrganizerResponse"] = []
    phases: List["EventPhaseResponse"] = []
    milestones: List["EventMilestoneResponse"] = []
    task_count: Optional[int] = 0

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """Schema for paginated event list"""
    events: List[EventResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# Event Organizer schemas
class EventOrganizerBase(BaseModel):
    """Base event organizer schema"""
    role: OrganizerRole
    permissions: Dict[str, bool] = {
        "view": True,
        "edit": False,
        "invite": False,
        "book": False,
        "financial": False
    }


class EventOrganizerInvite(EventOrganizerBase):
    """Schema for inviting organizer"""
    user_email: str


class EventOrganizerUpdate(BaseModel):
    """Schema for updating organizer"""
    role: Optional[OrganizerRole] = None
    permissions: Optional[Dict[str, bool]] = None


class EventOrganizerResponse(EventOrganizerBase):
    """Schema for event organizer response"""
    event_id: UUID
    user_id: UUID
    status: OrganizerStatus
    invited_at: datetime
    accepted_at: Optional[datetime]

    class Config:
        from_attributes = True


# Event Phase schemas
class EventPhaseResponse(BaseModel):
    """Schema for event phase response"""
    id: UUID
    event_id: UUID
    phase_name: EventPhaseType
    phase_order: int
    status: PhaseStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    completion_percentage: Decimal
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class EventPhaseUpdate(BaseModel):
    """Schema for updating phase"""
    status: Optional[PhaseStatus] = None
    completion_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class AdvancePhaseRequest(BaseModel):
    """Schema for advancing to next phase"""
    skip_validation: bool = False


# Event Milestone schemas
class EventMilestoneBase(BaseModel):
    """Base milestone schema"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: datetime
    is_critical: bool = False


class EventMilestoneCreate(EventMilestoneBase):
    """Schema for creating milestone"""
    order_index: int = 0


class EventMilestoneUpdate(BaseModel):
    """Schema for updating milestone"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    is_critical: Optional[bool] = None
    order_index: Optional[int] = None
    completed_at: Optional[datetime] = None


class EventMilestoneResponse(EventMilestoneBase):
    """Schema for milestone response"""
    id: UUID
    event_id: UUID
    order_index: int
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# Cultural Element schemas
class EventCulturalElementBase(BaseModel):
    """Base cultural element schema"""
    element_type: str = Field(..., max_length=100)
    element_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    timing: Optional[str] = Field(None, max_length=100)
    is_required: bool = False
    is_included: bool = False
    notes: Optional[str] = None


class EventCulturalElementCreate(EventCulturalElementBase):
    """Schema for creating cultural element"""
    pass


class EventCulturalElementUpdate(BaseModel):
    """Schema for updating cultural element"""
    element_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    timing: Optional[str] = Field(None, max_length=100)
    is_included: Optional[bool] = None
    notes: Optional[str] = None


class EventCulturalElementResponse(EventCulturalElementBase):
    """Schema for cultural element response"""
    id: UUID
    event_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Event Statistics
class EventStatistics(BaseModel):
    """Schema for event statistics"""
    total_budget: Decimal
    spent_amount: Decimal
    budget_utilization_percentage: Decimal
    guest_count_confirmed: int
    guest_count_estimate: int
    vendor_count: int
    completed_tasks: int
    total_tasks: int
    task_completion_percentage: Decimal
    days_until_event: int
    current_phase: EventPhaseType
    phase_completion_percentage: Decimal


# Phase Progress
class PhaseProgress(BaseModel):
    """Schema for phase progress"""
    phase: EventPhaseType
    status: PhaseStatus
    completion_percentage: Decimal
    tasks_total: int
    tasks_completed: int


# Event Timeline
class EventTimelineItem(BaseModel):
    """Schema for timeline item"""
    id: UUID
    type: str  # "milestone", "task", "booking", "phase_change"
    title: str
    description: Optional[str]
    date: datetime
    status: str
    is_completed: bool


class EventTimelineResponse(BaseModel):
    """Schema for event timeline"""
    event_id: UUID
    items: List[EventTimelineItem]
    critical_path: List[UUID]


# Dashboard
class EventDashboard(BaseModel):
    """Schema for event dashboard"""
    event: EventDetailResponse
    statistics: EventStatistics
    upcoming_milestones: List[EventMilestoneResponse]
    pending_tasks: List["TaskResponse"]
    recent_activity: List[Dict[str, Any]]
    budget_alerts: List[str]
    timeline_alerts: List[str]


# Forward references
from app.schemas.task import TaskResponse
EventDashboard.update_forward_refs()
EventDetailResponse.update_forward_refs()
