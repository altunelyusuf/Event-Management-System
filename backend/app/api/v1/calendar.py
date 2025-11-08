"""
CelebraTech Event Management System - Calendar API
Sprint 14: Calendar & Scheduling System
FastAPI endpoints for calendar management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.calendar import (
    CalendarCreate,
    CalendarUpdate,
    CalendarResponse,
    CalendarEventCreate,
    CalendarEventUpdate,
    CalendarEventResponse,
    AvailabilityCreate,
    AvailabilityResponse,
    TimeSlotBookingCreate,
    TimeSlotBookingResponse,
    ConflictCheckRequest,
    ConflictCheckResponse,
    CalendarSyncCreate,
    CalendarSyncResponse
)
from app.services.calendar_service import CalendarService

router = APIRouter(prefix="/calendar", tags=["Calendar & Scheduling"])


# ============================================================================
# Calendar Endpoints
# ============================================================================

@router.post(
    "/calendars",
    response_model=CalendarResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new calendar",
    description="Create a new calendar for events, vendors, or personal use"
)
async def create_calendar(
    calendar_data: CalendarCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new calendar

    - **name**: Calendar name (required)
    - **type**: Calendar type (event, vendor, personal, shared)
    - **color**: Hex color code for display
    - **event_id**: Optional event association
    - **vendor_id**: Optional vendor association
    - **settings**: Calendar settings (timezone, work hours, etc.)

    Returns created calendar object
    """
    calendar_service = CalendarService(db)
    calendar = await calendar_service.create_calendar(calendar_data, current_user)
    return CalendarResponse.from_orm(calendar)


@router.get(
    "/calendars",
    response_model=List[CalendarResponse],
    summary="Get user's calendars",
    description="Get all calendars for the current user"
)
async def get_user_calendars(
    include_public: bool = Query(False, description="Include public calendars"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get calendars for current user

    Query parameters:
    - **include_public**: Include public calendars (default: false)

    Returns list of calendar objects
    """
    calendar_service = CalendarService(db)
    calendars = await calendar_service.get_user_calendars(
        current_user,
        include_public
    )

    return [CalendarResponse.from_orm(c) for c in calendars]


@router.get(
    "/calendars/{calendar_id}",
    response_model=CalendarResponse,
    summary="Get calendar by ID",
    description="Get a specific calendar by ID"
)
async def get_calendar(
    calendar_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get calendar by ID

    Returns calendar object
    """
    calendar_service = CalendarService(db)
    calendar = await calendar_service.get_calendar(calendar_id, current_user)
    return CalendarResponse.from_orm(calendar)


@router.get(
    "/events/{event_id}/calendar",
    response_model=CalendarResponse,
    summary="Get calendar for event",
    description="Get the calendar associated with a specific event"
)
async def get_event_calendar(
    event_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get calendar for a specific event

    Returns calendar object or 404 if not found
    """
    calendar_service = CalendarService(db)
    calendar = await calendar_service.get_event_calendar(event_id, current_user)

    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar not found for this event"
        )

    return CalendarResponse.from_orm(calendar)


@router.put(
    "/calendars/{calendar_id}",
    response_model=CalendarResponse,
    summary="Update calendar",
    description="Update a calendar's properties"
)
async def update_calendar(
    calendar_id: UUID,
    calendar_data: CalendarUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a calendar

    Returns updated calendar object
    """
    calendar_service = CalendarService(db)
    calendar = await calendar_service.update_calendar(
        calendar_id,
        calendar_data,
        current_user
    )
    return CalendarResponse.from_orm(calendar)


@router.delete(
    "/calendars/{calendar_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete calendar",
    description="Soft delete a calendar"
)
async def delete_calendar(
    calendar_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a calendar (soft delete)

    Returns 204 No Content on success
    """
    calendar_service = CalendarService(db)
    await calendar_service.delete_calendar(calendar_id, current_user)


# ============================================================================
# Calendar Event Endpoints
# ============================================================================

@router.post(
    "/events",
    response_model=CalendarEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create calendar event",
    description="Create a new event in a calendar"
)
async def create_calendar_event(
    event_data: CalendarEventCreate,
    check_conflicts: bool = Query(True, description="Check for scheduling conflicts"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new calendar event

    - **calendar_id**: Calendar to add event to (required)
    - **title**: Event title (required)
    - **start_time**: Start date and time (required)
    - **end_time**: End date and time (required)
    - **description**: Event description
    - **location**: Event location
    - **attendees**: List of attendees with email and status
    - **reminders**: List of reminders (email, push, sms)

    Returns created calendar event object

    May return 409 Conflict if check_conflicts=true and time slot is occupied
    """
    calendar_service = CalendarService(db)
    calendar_event = await calendar_service.create_calendar_event(
        event_data,
        current_user,
        check_conflicts
    )
    return CalendarEventResponse.from_orm(calendar_event)


@router.get(
    "/calendars/{calendar_id}/events",
    response_model=List[CalendarEventResponse],
    summary="Get calendar events",
    description="Get all events for a calendar within a date range"
)
async def get_calendar_events(
    calendar_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get calendar events

    Query parameters:
    - **start_date**: Start date for filtering (defaults to start of current month)
    - **end_date**: End date for filtering (defaults to end of current month)

    Returns list of calendar event objects
    """
    calendar_service = CalendarService(db)
    events = await calendar_service.get_calendar_events(
        calendar_id,
        current_user,
        start_date,
        end_date
    )

    return [CalendarEventResponse.from_orm(e) for e in events]


@router.get(
    "/events/{event_id}",
    response_model=CalendarEventResponse,
    summary="Get calendar event",
    description="Get a specific calendar event by ID"
)
async def get_calendar_event(
    event_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get calendar event by ID

    Returns calendar event object
    """
    calendar_service = CalendarService(db)
    calendar_event = await calendar_service.get_calendar_event(event_id, current_user)
    return CalendarEventResponse.from_orm(calendar_event)


@router.put(
    "/events/{event_id}",
    response_model=CalendarEventResponse,
    summary="Update calendar event",
    description="Update a calendar event's properties"
)
async def update_calendar_event(
    event_id: UUID,
    event_data: CalendarEventUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a calendar event

    Returns updated calendar event object
    """
    calendar_service = CalendarService(db)
    calendar_event = await calendar_service.update_calendar_event(
        event_id,
        event_data,
        current_user
    )
    return CalendarEventResponse.from_orm(calendar_event)


@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete calendar event",
    description="Delete a calendar event"
)
async def delete_calendar_event(
    event_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a calendar event

    Returns 204 No Content on success
    """
    calendar_service = CalendarService(db)
    await calendar_service.delete_calendar_event(event_id, current_user)


# ============================================================================
# Conflict Detection Endpoints
# ============================================================================

@router.post(
    "/calendars/{calendar_id}/check-conflicts",
    response_model=ConflictCheckResponse,
    summary="Check for conflicts",
    description="Check if a time slot has any scheduling conflicts"
)
async def check_conflicts(
    calendar_id: UUID,
    conflict_check: ConflictCheckRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check for scheduling conflicts

    - **start_time**: Proposed start time
    - **end_time**: Proposed end time
    - **exclude_event_id**: Optional event ID to exclude (for updates)

    Returns list of conflicting events
    """
    calendar_service = CalendarService(db)
    conflicts = await calendar_service.check_conflicts(
        calendar_id,
        conflict_check.start_time,
        conflict_check.end_time,
        current_user,
        conflict_check.exclude_event_id
    )

    return ConflictCheckResponse(
        has_conflicts=len(conflicts) > 0,
        conflict_count=len(conflicts),
        conflicts=conflicts
    )


@router.get(
    "/calendars/{calendar_id}/conflicts",
    response_model=List[dict],
    summary="Get unresolved conflicts",
    description="Get all unresolved scheduling conflicts for a calendar"
)
async def get_unresolved_conflicts(
    calendar_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get unresolved conflicts

    Returns list of conflict objects
    """
    calendar_service = CalendarService(db)
    conflicts = await calendar_service.get_unresolved_conflicts(
        calendar_id,
        current_user
    )

    return [
        {
            "id": str(conflict.id),
            "event1_id": str(conflict.event1_id),
            "event2_id": str(conflict.event2_id),
            "conflict_type": conflict.conflict_type,
            "created_at": conflict.created_at.isoformat()
        }
        for conflict in conflicts
    ]


# ============================================================================
# Availability & Booking Endpoints
# ============================================================================

@router.post(
    "/availability",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create availability",
    description="Create availability slots for booking"
)
async def create_availability(
    availability_data: AvailabilityCreate,
    vendor_id: Optional[UUID] = Query(None, description="Vendor ID if creating vendor availability"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create availability slots

    - **calendar_id**: Calendar to add availability to
    - **day_of_week**: Day of week (0=Monday, 6=Sunday)
    - **start_time**: Start time (HH:MM format)
    - **end_time**: End time (HH:MM format)
    - **slot_duration_minutes**: Duration of each bookable slot
    - **status**: Availability status (available, booked, blocked, tentative)

    Returns created availability object
    """
    calendar_service = CalendarService(db)
    availability = await calendar_service.create_availability(
        availability_data,
        current_user,
        vendor_id
    )
    return AvailabilityResponse.from_orm(availability)


@router.get(
    "/vendors/{vendor_id}/availability",
    response_model=List[AvailabilityResponse],
    summary="Get vendor availability",
    description="Get availability slots for a vendor"
)
async def get_vendor_availability(
    vendor_id: UUID,
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get vendor availability

    Query parameters:
    - **start_date**: Start date for availability
    - **end_date**: End date for availability

    Returns list of availability objects
    """
    calendar_service = CalendarService(db)
    availability = await calendar_service.get_vendor_availability(
        vendor_id,
        start_date,
        end_date
    )

    return [AvailabilityResponse.from_orm(a) for a in availability]


@router.post(
    "/bookings",
    response_model=TimeSlotBookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book time slot",
    description="Book an available time slot"
)
async def book_time_slot(
    booking_data: TimeSlotBookingCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Book a time slot

    - **availability_id**: Availability slot to book
    - **event_id**: Event this booking is for
    - **booking_date**: Date of the booking
    - **start_time**: Start time
    - **end_time**: End time

    Returns created booking object

    May return 409 Conflict if slot already booked
    """
    calendar_service = CalendarService(db)
    booking = await calendar_service.book_time_slot(booking_data, current_user)
    return TimeSlotBookingResponse.from_orm(booking)


# ============================================================================
# Calendar Sync Endpoints
# ============================================================================

@router.post(
    "/calendars/{calendar_id}/sync",
    response_model=CalendarSyncResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Setup calendar sync",
    description="Configure synchronization with external calendar (Google, Outlook, Apple)"
)
async def create_calendar_sync(
    calendar_id: UUID,
    sync_data: CalendarSyncCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Setup calendar sync

    - **provider**: Sync provider (google, outlook, apple, ical)
    - **external_calendar_id**: External calendar ID
    - **access_token**: OAuth access token
    - **refresh_token**: Optional refresh token

    Returns created sync configuration
    """
    calendar_service = CalendarService(db)
    sync = await calendar_service.create_calendar_sync(
        calendar_id,
        sync_data.provider,
        sync_data.external_calendar_id,
        sync_data.access_token,
        sync_data.refresh_token,
        current_user
    )
    return CalendarSyncResponse.from_orm(sync)


@router.get(
    "/calendars/{calendar_id}/syncs",
    response_model=List[CalendarSyncResponse],
    summary="Get calendar syncs",
    description="Get all sync configurations for a calendar"
)
async def get_calendar_syncs(
    calendar_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get calendar syncs

    Returns list of sync configuration objects
    """
    calendar_service = CalendarService(db)
    syncs = await calendar_service.get_calendar_syncs(calendar_id, current_user)

    return [CalendarSyncResponse.from_orm(s) for s in syncs]


@router.post(
    "/syncs/{sync_id}/trigger",
    response_model=dict,
    summary="Trigger manual sync",
    description="Manually trigger a calendar synchronization"
)
async def trigger_calendar_sync(
    sync_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger manual sync

    Returns sync result with status
    """
    calendar_service = CalendarService(db)
    result = await calendar_service.trigger_calendar_sync(sync_id, current_user)
    return result
