"""
Calendar & Scheduling Schemas
Sprint 14: Calendar & Scheduling System

Pydantic schemas for calendar functionality.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# Calendar Schemas
# ============================================================================

class CalendarCreate(BaseModel):
    """Create a calendar"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    type: str = Field("event", description="event, vendor, personal, shared")
    color: str = Field("#3788d8", regex="^#[0-9A-Fa-f]{6}$")

    event_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None

    settings: Dict[str, Any] = Field(default_factory=lambda: {
        "timezone": "UTC",
        "week_start": "monday",
        "work_hours_start": "09:00",
        "work_hours_end": "18:00",
        "default_view": "month",
        "default_duration": 60
    })

    is_public: bool = False
    is_default: bool = False


class CalendarUpdate(BaseModel):
    """Update a calendar"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    color: Optional[str] = Field(None, regex="^#[0-9A-Fa-f]{6}$")
    settings: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None


class CalendarResponse(BaseModel):
    """Calendar response"""
    id: UUID
    user_id: Optional[UUID]
    event_id: Optional[UUID]
    vendor_id: Optional[UUID]

    name: str
    description: Optional[str]
    type: str
    color: str

    settings: Dict[str, Any]

    is_public: bool
    is_default: bool
    is_active: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Calendar Event Schemas
# ============================================================================

class AttendeeBase(BaseModel):
    """Attendee information"""
    email: str
    name: Optional[str] = None
    status: str = "pending"  # pending, accepted, declined, tentative


class ReminderBase(BaseModel):
    """Reminder configuration"""
    type: str = "email"  # email, push, sms
    minutes_before: int = Field(30, ge=0)


class CalendarEventCreate(BaseModel):
    """Create a calendar event"""
    calendar_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = None

    start_time: datetime
    end_time: datetime
    all_day: bool = False
    timezone: str = "UTC"

    event_id: Optional[UUID] = None
    booking_id: Optional[UUID] = None
    task_id: Optional[UUID] = None

    attendees: List[AttendeeBase] = Field(default_factory=list)
    reminders: List[ReminderBase] = Field(default_factory=list)

    status: str = "confirmed"
    is_private: bool = False

    metadata: Dict[str, Any] = Field(default_factory=dict)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)

    @validator('end_time')
    def validate_end_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class CalendarEventUpdate(BaseModel):
    """Update a calendar event"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = None

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    timezone: Optional[str] = None

    attendees: Optional[List[AttendeeBase]] = None
    reminders: Optional[List[ReminderBase]] = None

    status: Optional[str] = None
    is_private: Optional[bool] = None

    metadata: Optional[Dict[str, Any]] = None


class CalendarEventResponse(BaseModel):
    """Calendar event response"""
    id: UUID
    calendar_id: UUID

    title: str
    description: Optional[str]
    location: Optional[str]

    start_time: datetime
    end_time: datetime
    all_day: bool
    timezone: str

    is_recurring: bool
    recurrence_rule_id: Optional[UUID]

    event_id: Optional[UUID]
    booking_id: Optional[UUID]
    task_id: Optional[UUID]

    attendees: List[Dict[str, Any]]
    reminders: List[Dict[str, Any]]

    status: str
    is_private: bool

    metadata: Dict[str, Any]
    attachments: List[Dict[str, Any]]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Recurring Event Schemas
# ============================================================================

class RecurringEventRuleCreate(BaseModel):
    """Create a recurring event rule"""
    frequency: str = Field(..., description="daily, weekly, monthly, yearly")
    interval: int = Field(1, ge=1, description="Every N days/weeks/months/years")

    by_day: Optional[List[str]] = Field(None, description="['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']")
    by_month_day: Optional[List[int]] = Field(None, description="Day of month [1-31]")
    by_set_pos: Optional[int] = Field(None, description="1st, 2nd, -1st (last)")
    by_month: Optional[List[int]] = Field(None, description="Month numbers [1-12]")

    count: Optional[int] = Field(None, ge=1, description="Number of occurrences")
    until: Optional[datetime] = Field(None, description="End date")

    exception_dates: List[datetime] = Field(default_factory=list)


class RecurringEventRuleResponse(BaseModel):
    """Recurring event rule response"""
    id: UUID
    frequency: str
    interval: int

    by_day: Optional[List[str]]
    by_month_day: Optional[List[int]]
    by_set_pos: Optional[int]
    by_month: Optional[List[int]]

    count: Optional[int]
    until: Optional[datetime]

    exception_dates: List[datetime]
    rrule_string: Optional[str]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecurringEventCreate(CalendarEventCreate):
    """Create a recurring event"""
    recurrence_rule: RecurringEventRuleCreate


# ============================================================================
# Vendor Availability Schemas
# ============================================================================

class VendorAvailabilityCreate(BaseModel):
    """Create vendor availability slot"""
    vendor_id: UUID
    start_time: datetime
    end_time: datetime
    status: str = "available"

    booking_id: Optional[UUID] = None
    event_id: Optional[UUID] = None

    is_recurring: bool = False
    recurrence_rule: Optional[RecurringEventRuleCreate] = None

    notes: Optional[str] = None
    reason: Optional[str] = None

    @validator('end_time')
    def validate_end_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class VendorAvailabilityUpdate(BaseModel):
    """Update vendor availability slot"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    reason: Optional[str] = None


class VendorAvailabilityResponse(BaseModel):
    """Vendor availability response"""
    id: UUID
    vendor_id: UUID

    start_time: datetime
    end_time: datetime
    status: str

    booking_id: Optional[UUID]
    event_id: Optional[UUID]

    is_recurring: bool
    recurrence_rule_id: Optional[UUID]

    notes: Optional[str]
    reason: Optional[str]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AvailabilityCheckRequest(BaseModel):
    """Check vendor availability"""
    vendor_id: UUID
    start_time: datetime
    end_time: datetime


class AvailabilityCheckResponse(BaseModel):
    """Availability check result"""
    is_available: bool
    conflicting_slots: List[VendorAvailabilityResponse] = Field(default_factory=list)
    suggested_times: List[Dict[str, datetime]] = Field(default_factory=list)


# ============================================================================
# Booking Conflict Schemas
# ============================================================================

class BookingConflictResponse(BaseModel):
    """Booking conflict response"""
    id: UUID
    conflict_type: str

    booking_id: Optional[UUID]
    vendor_id: Optional[UUID]
    event_id: Optional[UUID]

    conflicting_booking_id: Optional[UUID]
    conflicting_event_id: Optional[UUID]

    conflict_start: datetime
    conflict_end: datetime

    description: str
    severity: str

    is_resolved: bool
    resolved_at: Optional[datetime]
    resolved_by: Optional[UUID]
    resolution_notes: Optional[str]

    detected_at: datetime

    class Config:
        from_attributes = True


class ConflictResolutionRequest(BaseModel):
    """Resolve a booking conflict"""
    resolution_notes: str = Field(..., min_length=1)


# ============================================================================
# Calendar Sync Schemas
# ============================================================================

class CalendarSyncCreate(BaseModel):
    """Create calendar sync configuration"""
    calendar_id: UUID
    provider: str = Field(..., description="google, outlook, apple, ical")
    external_calendar_id: str = Field(..., min_length=1, max_length=200)
    external_calendar_name: Optional[str] = None

    sync_direction: str = Field("two_way", description="one_way_to_external, one_way_from_external, two_way")
    sync_enabled: bool = True
    sync_frequency_minutes: int = Field(15, ge=5, le=1440)


class CalendarSyncUpdate(BaseModel):
    """Update calendar sync configuration"""
    sync_direction: Optional[str] = None
    sync_enabled: Optional[bool] = None
    sync_frequency_minutes: Optional[int] = Field(None, ge=5, le=1440)


class CalendarSyncResponse(BaseModel):
    """Calendar sync response"""
    id: UUID
    calendar_id: UUID
    user_id: UUID

    provider: str
    external_calendar_id: str
    external_calendar_name: Optional[str]

    sync_direction: str
    sync_enabled: bool
    sync_frequency_minutes: int

    last_sync_at: Optional[datetime]
    last_sync_status: str
    last_sync_error: Optional[str]
    sync_count: int

    events_synced_to_external: int
    events_synced_from_external: int

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SyncNowRequest(BaseModel):
    """Trigger immediate sync"""
    force: bool = False


# ============================================================================
# Calendar Share Schemas
# ============================================================================

class CalendarShareCreate(BaseModel):
    """Share calendar with user"""
    calendar_id: UUID
    shared_with_user_id: UUID
    permission: str = Field("view", description="view, edit, admin")

    can_invite_others: bool = False
    send_notifications: bool = True

    expires_at: Optional[datetime] = None


class CalendarShareUpdate(BaseModel):
    """Update calendar share"""
    permission: Optional[str] = None
    can_invite_others: Optional[bool] = None
    send_notifications: Optional[bool] = None
    is_active: Optional[bool] = None


class CalendarShareResponse(BaseModel):
    """Calendar share response"""
    id: UUID
    calendar_id: UUID
    shared_with_user_id: UUID
    shared_by_user_id: UUID

    permission: str

    can_invite_others: bool
    send_notifications: bool

    is_active: bool
    accepted_at: Optional[datetime]
    expires_at: Optional[datetime]

    shared_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Calendar View Schemas
# ============================================================================

class CalendarViewQuery(BaseModel):
    """Query parameters for calendar views"""
    calendar_id: UUID
    view_type: str = Field("month", description="month, week, day, agenda, timeline")
    start_date: datetime
    end_date: datetime
    include_private: bool = False


class CalendarEventSummary(BaseModel):
    """Summary of calendar event for views"""
    id: UUID
    title: str
    start_time: datetime
    end_time: datetime
    all_day: bool
    color: Optional[str]
    is_private: bool
    status: str


class CalendarViewResponse(BaseModel):
    """Calendar view response"""
    calendar_id: UUID
    view_type: str
    start_date: datetime
    end_date: datetime

    events: List[CalendarEventSummary]
    conflicts: List[BookingConflictResponse] = Field(default_factory=list)

    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# iCal Export Schemas
# ============================================================================

class ICalExportRequest(BaseModel):
    """Request iCal export"""
    calendar_id: UUID
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_private: bool = False


class ICalExportResponse(BaseModel):
    """iCal export response"""
    ical_data: str
    event_count: int
    generated_at: datetime


# ============================================================================
# Conflict Detection Schemas
# ============================================================================

class ConflictDetectionRequest(BaseModel):
    """Request conflict detection"""
    start_time: datetime
    end_time: datetime

    vendor_ids: List[UUID] = Field(default_factory=list)
    event_id: Optional[UUID] = None
    exclude_booking_ids: List[UUID] = Field(default_factory=list)


class ConflictDetectionResponse(BaseModel):
    """Conflict detection results"""
    has_conflicts: bool
    conflicts: List[BookingConflictResponse]
    affected_vendors: List[UUID]
    suggested_resolution: Optional[str] = None


# ============================================================================
# Bulk Operations Schemas
# ============================================================================

class BulkAvailabilityCreate(BaseModel):
    """Bulk create availability slots"""
    vendor_id: UUID
    slots: List[Dict[str, datetime]] = Field(..., min_items=1)
    status: str = "available"
    notes: Optional[str] = None


class BulkEventCreate(BaseModel):
    """Bulk create calendar events"""
    calendar_id: UUID
    events: List[CalendarEventCreate] = Field(..., min_items=1)
