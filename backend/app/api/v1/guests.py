"""
Guest Management API Endpoints

REST API endpoints for guest management system including guests, RSVPs,
invitations, seating arrangements, and check-ins.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user, get_optional_user
from app.models.user import User
from app.models.guest import GuestStatus, RSVPStatus, InvitationStatus
from app.services.guest_service import GuestService
from app.schemas.guest import (
    GuestCreate, GuestUpdate, GuestResponse, GuestBulkImport,
    GuestGroupCreate, GuestGroupUpdate, GuestGroupResponse,
    GuestInvitationCreate, GuestInvitationBulkCreate, GuestInvitationResponse,
    RSVPResponseCreate, RSVPResponseUpdate, RSVPResponseResponse,
    SeatingArrangementCreate, SeatingArrangementUpdate, SeatingArrangementResponse,
    GuestCheckInCreate, GuestCheckInResponse,
    DietaryRestrictionCreate, DietaryRestrictionUpdate, DietaryRestrictionResponse,
    GuestStatistics, SeatingStatistics
)


router = APIRouter(prefix="/guests", tags=["Guests"])


# ============================================================================
# Guest Endpoints
# ============================================================================

@router.post("", response_model=GuestResponse, status_code=status.HTTP_201_CREATED)
async def create_guest(
    guest_data: GuestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new guest for an event.

    Requires organizer or admin access.
    """
    service = GuestService(db)
    return await service.create_guest(guest_data, current_user)


@router.get("/{guest_id}", response_model=GuestResponse)
async def get_guest(
    guest_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a guest by ID.

    Requires access to the event.
    """
    service = GuestService(db)
    return await service.get_guest(guest_id, current_user)


@router.get("/event/{event_id}", response_model=List[GuestResponse])
async def get_guests_by_event(
    event_id: UUID,
    status: Optional[GuestStatus] = None,
    rsvp_status: Optional[RSVPStatus] = None,
    category: Optional[str] = None,
    group_id: Optional[UUID] = None,
    is_vip: Optional[bool] = None,
    checked_in: Optional[bool] = None,
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all guests for an event with optional filters.

    Supports filtering by status, RSVP status, category, group, VIP status,
    check-in status, and text search.
    """
    service = GuestService(db)
    return await service.get_guests_by_event(
        event_id=event_id,
        current_user=current_user,
        status=status,
        rsvp_status=rsvp_status,
        category=category,
        group_id=group_id,
        is_vip=is_vip,
        checked_in=checked_in,
        search=search,
        skip=skip,
        limit=limit
    )


@router.patch("/{guest_id}", response_model=GuestResponse)
async def update_guest(
    guest_id: UUID,
    guest_data: GuestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a guest.

    Automatically updates group statistics and seating occupancy if changed.
    """
    service = GuestService(db)
    return await service.update_guest(guest_id, guest_data, current_user)


@router.delete("/{guest_id}", status_code=status.HTTP_200_OK)
async def delete_guest(
    guest_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a guest.

    Also deletes all associated invitations, RSVPs, and check-ins.
    Updates group statistics and seating occupancy.
    """
    service = GuestService(db)
    return await service.delete_guest(guest_id, current_user)


@router.post("/bulk-import", status_code=status.HTTP_201_CREATED)
async def bulk_import_guests(
    import_data: GuestBulkImport,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Bulk import guests.

    Supports importing up to 1000 guests at once.
    """
    service = GuestService(db)
    return await service.bulk_import_guests(import_data, current_user)


# ============================================================================
# Guest Group Endpoints
# ============================================================================

@router.post("/groups", response_model=GuestGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_guest_group(
    group_data: GuestGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new guest group/category.

    Guest groups help organize guests into categories like family, friends, etc.
    """
    service = GuestService(db)
    return await service.create_guest_group(group_data, current_user)


@router.get("/groups/{group_id}", response_model=GuestGroupResponse)
async def get_guest_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a guest group by ID.
    """
    service = GuestService(db)
    return await service.get_guest_group(group_id, current_user)


@router.get("/groups/event/{event_id}", response_model=List[GuestGroupResponse])
async def get_guest_groups_by_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all guest groups for an event.

    Includes statistics for each group (confirmed, declined, pending).
    """
    service = GuestService(db)
    return await service.get_guest_groups_by_event(event_id, current_user)


@router.patch("/groups/{group_id}", response_model=GuestGroupResponse)
async def update_guest_group(
    group_id: UUID,
    group_data: GuestGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a guest group.
    """
    service = GuestService(db)
    return await service.update_guest_group(group_id, group_data, current_user)


@router.delete("/groups/{group_id}", status_code=status.HTTP_200_OK)
async def delete_guest_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a guest group.

    Guests in this group will be unassigned but not deleted.
    """
    service = GuestService(db)
    return await service.delete_guest_group(group_id, current_user)


# ============================================================================
# Invitation Endpoints
# ============================================================================

@router.post("/invitations", response_model=GuestInvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    invitation_data: GuestInvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create and send an invitation to a guest.

    Supports email, SMS, and physical invitation tracking.
    """
    service = GuestService(db)
    return await service.create_invitation(invitation_data, current_user)


@router.post("/invitations/bulk", status_code=status.HTTP_201_CREATED)
async def send_bulk_invitations(
    bulk_data: GuestInvitationBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send invitations to multiple guests.

    Supports sending up to 500 invitations at once.
    """
    service = GuestService(db)
    return await service.send_bulk_invitations(bulk_data, current_user)


@router.post("/invitations/{invitation_id}/opened", response_model=GuestInvitationResponse)
async def mark_invitation_opened(
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark an invitation as opened.

    Called when tracking pixels or links indicate the invitation was opened.
    """
    service = GuestService(db)
    return await service.mark_invitation_opened(invitation_id, current_user)


# ============================================================================
# RSVP Endpoints
# ============================================================================

@router.post("/rsvp", response_model=RSVPResponseResponse, status_code=status.HTTP_201_CREATED)
async def create_rsvp_response(
    rsvp_data: RSVPResponseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Create an RSVP response.

    Public endpoint - guests can RSVP without authentication.
    Automatically updates guest status and group statistics.
    """
    service = GuestService(db)
    return await service.create_rsvp_response(rsvp_data, current_user)


@router.get("/rsvp/{rsvp_id}", response_model=RSVPResponseResponse)
async def get_rsvp_response(
    rsvp_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get an RSVP response by ID.
    """
    service = GuestService(db)
    return await service.get_rsvp_response(rsvp_id, current_user)


@router.get("/rsvp/guest/{guest_id}/latest", response_model=RSVPResponseResponse)
async def get_latest_rsvp_by_guest(
    guest_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the latest RSVP response for a guest.

    Guests can update their RSVP, this returns the most recent one.
    """
    service = GuestService(db)
    return await service.get_latest_rsvp_by_guest(guest_id, current_user)


@router.get("/rsvp/event/{event_id}", response_model=List[RSVPResponseResponse])
async def get_rsvp_responses_by_event(
    event_id: UUID,
    status: Optional[RSVPStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all RSVP responses for an event.

    Optionally filter by RSVP status (attending, not attending, maybe, pending).
    Only returns latest responses per guest.
    """
    service = GuestService(db)
    return await service.get_rsvp_responses_by_event(
        event_id=event_id,
        current_user=current_user,
        status=status,
        skip=skip,
        limit=limit
    )


# ============================================================================
# Seating Arrangement Endpoints
# ============================================================================

@router.post("/seating", response_model=SeatingArrangementResponse, status_code=status.HTTP_201_CREATED)
async def create_seating_arrangement(
    seating_data: SeatingArrangementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new seating arrangement (table).

    Table numbers must be unique per event.
    """
    service = GuestService(db)
    return await service.create_seating_arrangement(seating_data, current_user)


@router.get("/seating/{seating_id}", response_model=SeatingArrangementResponse)
async def get_seating_arrangement(
    seating_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a seating arrangement by ID.
    """
    service = GuestService(db)
    return await service.get_seating_arrangement(seating_id, current_user)


@router.get("/seating/event/{event_id}", response_model=List[SeatingArrangementResponse])
async def get_seating_by_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all seating arrangements for an event.

    Returns all tables with occupancy information.
    """
    service = GuestService(db)
    return await service.get_seating_by_event(event_id, current_user)


@router.patch("/seating/{seating_id}", response_model=SeatingArrangementResponse)
async def update_seating_arrangement(
    seating_id: UUID,
    seating_data: SeatingArrangementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a seating arrangement.
    """
    service = GuestService(db)
    return await service.update_seating_arrangement(seating_id, seating_data, current_user)


@router.delete("/seating/{seating_id}", status_code=status.HTTP_200_OK)
async def delete_seating_arrangement(
    seating_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a seating arrangement.

    Guests assigned to this table will be unassigned.
    """
    service = GuestService(db)
    return await service.delete_seating_arrangement(seating_id, current_user)


# ============================================================================
# Check-In Endpoints
# ============================================================================

@router.post("/checkin", response_model=GuestCheckInResponse, status_code=status.HTTP_201_CREATED)
async def check_in_guest(
    checkin_data: GuestCheckInCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check in a guest at the event.

    Updates guest status to checked_in.
    Supports manual, QR code, and NFC check-in methods.
    """
    service = GuestService(db)
    return await service.check_in_guest(checkin_data, current_user)


@router.get("/checkin/event/{event_id}", response_model=List[GuestCheckInResponse])
async def get_check_ins_by_event(
    event_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all check-ins for an event.

    Returns check-in history with timestamps and details.
    """
    service = GuestService(db)
    return await service.get_check_ins_by_event(
        event_id=event_id,
        current_user=current_user,
        skip=skip,
        limit=limit
    )


# ============================================================================
# Dietary Restriction Endpoints
# ============================================================================

@router.post("/dietary-restrictions", response_model=DietaryRestrictionResponse, status_code=status.HTTP_201_CREATED)
async def create_dietary_restriction(
    restriction_data: DietaryRestrictionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new dietary restriction (admin only).

    Used to maintain a master list of dietary restrictions for selection.
    """
    service = GuestService(db)
    return await service.create_dietary_restriction(restriction_data, current_user)


@router.get("/dietary-restrictions", response_model=List[DietaryRestrictionResponse])
async def get_all_dietary_restrictions(
    active_only: bool = Query(True, description="Only return active restrictions"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all dietary restrictions.

    Public endpoint for displaying options to guests.
    """
    service = GuestService(db)
    return await service.get_all_dietary_restrictions(active_only)


@router.patch("/dietary-restrictions/{restriction_id}", response_model=DietaryRestrictionResponse)
async def update_dietary_restriction(
    restriction_id: UUID,
    restriction_data: DietaryRestrictionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a dietary restriction (admin only).
    """
    service = GuestService(db)
    return await service.update_dietary_restriction(
        restriction_id,
        restriction_data,
        current_user
    )


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/statistics/event/{event_id}", response_model=GuestStatistics)
async def get_guest_statistics(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive guest statistics for an event.

    Includes guest counts by status, RSVP statistics, check-in rates,
    category breakdown, dietary restrictions summary, and seating info.
    """
    service = GuestService(db)
    return await service.get_guest_statistics(event_id, current_user)


@router.get("/statistics/seating/{event_id}", response_model=SeatingStatistics)
async def get_seating_statistics(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get seating statistics for an event.

    Includes total tables, capacity, occupancy rate, and breakdown by section/type.
    """
    service = GuestService(db)
    return await service.get_seating_statistics(event_id, current_user)
