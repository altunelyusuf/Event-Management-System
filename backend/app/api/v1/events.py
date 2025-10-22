"""
CelebraTech Event Management System - Event API
Sprint 2: Event Management Core
FR-002: Event Creation & Lifecycle Management
FastAPI endpoints for event management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.event import EventStatus
from app.schemas.event import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventDetailResponse,
    EventListResponse,
    EventStatistics,
    AdvancePhaseRequest
)
from app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["Events"])


@router.post(
    "",
    response_model=EventDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new event",
    description="Create a new event. User becomes primary organizer with full permissions."
)
async def create_event(
    event_data: EventCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new event

    - **name**: Event name (required)
    - **type**: Event type (TURKISH_WEDDING, ENGAGEMENT, etc.)
    - **event_date**: Event date (must be in future)
    - **end_date**: Optional end date
    - **guest_count_estimate**: Estimated guest count
    - **budget_amount**: Budget amount
    - **budget_currency**: Currency (default: TRY)

    Returns created event with initial phases
    """
    event_service = EventService(db)
    event = await event_service.create_event(event_data, current_user)
    return EventDetailResponse.from_orm(event)


@router.get(
    "",
    response_model=EventListResponse,
    summary="Get user's events",
    description="Get all events where user is an organizer"
)
async def get_user_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[EventStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get events for current user

    Query parameters:
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **status**: Filter by status (optional)

    Returns paginated list of events
    """
    event_service = EventService(db)
    events, total = await event_service.get_user_events(
        current_user,
        page,
        page_size,
        status
    )

    return EventListResponse(
        events=[EventResponse.from_orm(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.get(
    "/{event_id}",
    response_model=EventDetailResponse,
    summary="Get event by ID",
    description="Get event details with full information"
)
async def get_event(
    event_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get event by ID

    Requires view permission on the event.
    Returns event with all related data (organizers, phases, milestones).
    """
    event_service = EventService(db)
    event = await event_service.get_event(event_id, current_user, load_relationships=True)
    return EventDetailResponse.from_orm(event)


@router.put(
    "/{event_id}",
    response_model=EventResponse,
    summary="Update event",
    description="Update event details"
)
async def update_event(
    event_id: str,
    event_data: EventUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update event

    Requires edit permission on the event.
    All fields are optional - only provided fields will be updated.
    """
    event_service = EventService(db)
    event = await event_service.update_event(event_id, event_data, current_user)
    return EventResponse.from_orm(event)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete event",
    description="Soft delete event (only creator can delete)"
)
async def delete_event(
    event_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete event

    Only the event creator (primary organizer) can delete the event.
    This is a soft delete - event data is preserved but marked as deleted.
    """
    event_service = EventService(db)
    await event_service.delete_event(event_id, current_user)
    return None


@router.post(
    "/{event_id}/advance-phase",
    response_model=EventDetailResponse,
    summary="Advance to next phase",
    description="Move event to the next phase in lifecycle"
)
async def advance_phase(
    event_id: str,
    request: AdvancePhaseRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Advance event to next phase

    Marks current phase as completed and moves to next phase.
    Requires edit permission.

    The 11 phases are:
    1. IDEATION
    2. BUDGETING
    3. VENDOR_RESEARCH
    4. BOOKING
    5. DETAILED_PLANNING
    6. GUEST_MANAGEMENT
    7. TIMELINE_CREATION
    8. FINAL_COORDINATION
    9. EXECUTION
    10. POST_EVENT
    11. ANALYSIS
    """
    event_service = EventService(db)
    event = await event_service.advance_phase(event_id, current_user)
    return EventDetailResponse.from_orm(event)


@router.get(
    "/{event_id}/statistics",
    response_model=EventStatistics,
    summary="Get event statistics",
    description="Get comprehensive event statistics"
)
async def get_event_statistics(
    event_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get event statistics

    Returns:
    - Budget information and utilization
    - Guest counts
    - Task completion stats
    - Days until event
    - Current phase

    Requires view permission.
    """
    event_service = EventService(db)
    stats = await event_service.get_event_statistics(event_id, current_user)
    return EventStatistics(**stats)


# Phase management endpoints
@router.get(
    "/{event_id}/phases",
    response_model=list,
    summary="Get event phases",
    description="Get all phases for an event"
)
async def get_event_phases(
    event_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all phases for an event

    Returns list of all 11 phases with their status and progress.
    """
    event_service = EventService(db)
    event = await event_service.get_event(event_id, current_user, load_relationships=True)
    return [
        {
            "id": str(phase.id),
            "phase_name": phase.phase_name,
            "phase_order": phase.phase_order,
            "status": phase.status,
            "completion_percentage": float(phase.completion_percentage),
            "started_at": phase.started_at.isoformat() if phase.started_at else None,
            "completed_at": phase.completed_at.isoformat() if phase.completed_at else None
        }
        for phase in event.phases
    ]


# Milestone management
@router.get(
    "/{event_id}/milestones",
    response_model=list,
    summary="Get event milestones",
    description="Get all milestones for an event"
)
async def get_event_milestones(
    event_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all milestones for an event

    Returns list of milestones ordered by date.
    """
    event_service = EventService(db)
    event = await event_service.get_event(event_id, current_user, load_relationships=True)
    return [
        {
            "id": str(milestone.id),
            "title": milestone.title,
            "description": milestone.description,
            "due_date": milestone.due_date.isoformat(),
            "is_critical": milestone.is_critical,
            "completed_at": milestone.completed_at.isoformat() if milestone.completed_at else None
        }
        for milestone in event.milestones
    ]
