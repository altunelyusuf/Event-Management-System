"""
Guest Management Service

Business logic layer for guest management system handling validation,
authorization, and complex operations for guests, RSVPs, and seating.
"""

from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.guest import GuestStatus, RSVPStatus
from app.repositories.guest_repository import GuestRepository
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


class GuestService:
    """Service for guest management business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = GuestRepository(db)

    async def _check_event_access(self, event_id: UUID, user: User) -> None:
        """Check if user has access to event"""
        # TODO: Implement event access check
        # For now, assume organizers and admins have access
        if user.role not in [UserRole.ORGANIZER.value, UserRole.ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this event"
            )

    # ========================================================================
    # Guest Operations
    # ========================================================================

    async def create_guest(
        self,
        guest_data: GuestCreate,
        current_user: User
    ) -> GuestResponse:
        """Create a new guest"""
        await self._check_event_access(guest_data.event_id, current_user)

        guest = await self.repo.create_guest(guest_data, current_user.id)

        # Update group stats if guest is assigned to a group
        if guest.group_id:
            await self.repo.update_group_stats(guest.group_id)

        await self.db.commit()
        return GuestResponse.model_validate(guest)

    async def get_guest(self, guest_id: UUID, current_user: User) -> GuestResponse:
        """Get a guest by ID"""
        guest = await self.repo.get_guest(guest_id)
        if not guest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest not found"
            )

        await self._check_event_access(guest.event_id, current_user)
        return GuestResponse.model_validate(guest)

    async def get_guests_by_event(
        self,
        event_id: UUID,
        current_user: User,
        status: Optional[GuestStatus] = None,
        rsvp_status: Optional[RSVPStatus] = None,
        category: Optional[str] = None,
        group_id: Optional[UUID] = None,
        is_vip: Optional[bool] = None,
        checked_in: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[GuestResponse]:
        """Get guests for an event with filters"""
        await self._check_event_access(event_id, current_user)

        guests = await self.repo.get_guests_by_event(
            event_id=event_id,
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
        return [GuestResponse.model_validate(g) for g in guests]

    async def update_guest(
        self,
        guest_id: UUID,
        guest_data: GuestUpdate,
        current_user: User
    ) -> GuestResponse:
        """Update a guest"""
        guest = await self.repo.get_guest(guest_id)
        if not guest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest not found"
            )

        await self._check_event_access(guest.event_id, current_user)

        old_group_id = guest.group_id
        updated_guest = await self.repo.update_guest(guest_id, guest_data)

        # Update group stats if group changed
        if old_group_id and old_group_id != updated_guest.group_id:
            await self.repo.update_group_stats(old_group_id)
        if updated_guest.group_id:
            await self.repo.update_group_stats(updated_guest.group_id)

        # Update seating occupancy if table changed
        if guest_data.table_number is not None and guest_data.table_number != guest.table_number:
            if guest.table_number:
                await self.repo.update_seating_occupancy(guest.event_id, guest.table_number)
            if updated_guest.table_number:
                await self.repo.update_seating_occupancy(guest.event_id, updated_guest.table_number)

        await self.db.commit()
        return GuestResponse.model_validate(updated_guest)

    async def delete_guest(self, guest_id: UUID, current_user: User) -> dict:
        """Delete a guest"""
        guest = await self.repo.get_guest(guest_id)
        if not guest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest not found"
            )

        await self._check_event_access(guest.event_id, current_user)

        group_id = guest.group_id
        table_number = guest.table_number
        event_id = guest.event_id

        success = await self.repo.delete_guest(guest_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete guest"
            )

        # Update group stats
        if group_id:
            await self.repo.update_group_stats(group_id)

        # Update seating occupancy
        if table_number:
            await self.repo.update_seating_occupancy(event_id, table_number)

        await self.db.commit()
        return {"message": "Guest deleted successfully"}

    async def bulk_import_guests(
        self,
        import_data: GuestBulkImport,
        current_user: User
    ) -> dict:
        """Bulk import guests"""
        # Check access for all events
        event_ids = set(g.event_id for g in import_data.guests)
        for event_id in event_ids:
            await self._check_event_access(event_id, current_user)

        guests = await self.repo.bulk_create_guests(import_data.guests, current_user.id)

        # Update group stats for affected groups
        group_ids = set(g.group_id for g in guests if g.group_id)
        for group_id in group_ids:
            await self.repo.update_group_stats(group_id)

        await self.db.commit()
        return {
            "message": f"Successfully imported {len(guests)} guests",
            "imported_count": len(guests),
            "guests": [GuestResponse.model_validate(g) for g in guests]
        }

    # ========================================================================
    # Guest Group Operations
    # ========================================================================

    async def create_guest_group(
        self,
        group_data: GuestGroupCreate,
        current_user: User
    ) -> GuestGroupResponse:
        """Create a new guest group"""
        await self._check_event_access(group_data.event_id, current_user)

        group = await self.repo.create_guest_group(group_data, current_user.id)
        await self.db.commit()
        return GuestGroupResponse.model_validate(group)

    async def get_guest_group(
        self,
        group_id: UUID,
        current_user: User
    ) -> GuestGroupResponse:
        """Get a guest group by ID"""
        group = await self.repo.get_guest_group(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )

        await self._check_event_access(group.event_id, current_user)
        return GuestGroupResponse.model_validate(group)

    async def get_guest_groups_by_event(
        self,
        event_id: UUID,
        current_user: User
    ) -> List[GuestGroupResponse]:
        """Get all guest groups for an event"""
        await self._check_event_access(event_id, current_user)

        groups = await self.repo.get_guest_groups_by_event(event_id)
        return [GuestGroupResponse.model_validate(g) for g in groups]

    async def update_guest_group(
        self,
        group_id: UUID,
        group_data: GuestGroupUpdate,
        current_user: User
    ) -> GuestGroupResponse:
        """Update a guest group"""
        group = await self.repo.get_guest_group(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )

        await self._check_event_access(group.event_id, current_user)

        updated_group = await self.repo.update_guest_group(group_id, group_data)
        await self.db.commit()
        return GuestGroupResponse.model_validate(updated_group)

    async def delete_guest_group(
        self,
        group_id: UUID,
        current_user: User
    ) -> dict:
        """Delete a guest group"""
        group = await self.repo.get_guest_group(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest group not found"
            )

        await self._check_event_access(group.event_id, current_user)

        success = await self.repo.delete_guest_group(group_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete guest group"
            )

        await self.db.commit()
        return {"message": "Guest group deleted successfully"}

    # ========================================================================
    # Invitation Operations
    # ========================================================================

    async def create_invitation(
        self,
        invitation_data: GuestInvitationCreate,
        current_user: User
    ) -> GuestInvitationResponse:
        """Create and send an invitation"""
        await self._check_event_access(invitation_data.event_id, current_user)

        # Check if guest exists
        guest = await self.repo.get_guest(invitation_data.guest_id)
        if not guest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest not found"
            )

        invitation = await self.repo.create_invitation(invitation_data, current_user.id)

        # Mark as sent immediately (in production, would integrate with email/SMS service)
        await self.repo.mark_invitation_sent(invitation.id)

        await self.db.commit()
        return GuestInvitationResponse.model_validate(invitation)

    async def send_bulk_invitations(
        self,
        bulk_data: GuestInvitationBulkCreate,
        current_user: User
    ) -> dict:
        """Send invitations to multiple guests"""
        await self._check_event_access(bulk_data.event_id, current_user)

        invitations = []
        for guest_id in bulk_data.guest_ids:
            invitation_data = GuestInvitationCreate(
                guest_id=guest_id,
                event_id=bulk_data.event_id,
                invitation_type=bulk_data.invitation_type,
                subject=bulk_data.subject,
                message=bulk_data.message
            )
            invitation = await self.repo.create_invitation(invitation_data, current_user.id)
            await self.repo.mark_invitation_sent(invitation.id)
            invitations.append(invitation)

        await self.db.commit()
        return {
            "message": f"Successfully sent {len(invitations)} invitations",
            "sent_count": len(invitations),
            "invitations": [GuestInvitationResponse.model_validate(i) for i in invitations]
        }

    async def mark_invitation_opened(
        self,
        invitation_id: UUID,
        current_user: User
    ) -> GuestInvitationResponse:
        """Mark invitation as opened (called when guest opens invitation)"""
        invitation = await self.repo.get_invitation(invitation_id)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )

        updated_invitation = await self.repo.mark_invitation_opened(invitation_id)
        await self.db.commit()
        return GuestInvitationResponse.model_validate(updated_invitation)

    # ========================================================================
    # RSVP Operations
    # ========================================================================

    async def create_rsvp_response(
        self,
        rsvp_data: RSVPResponseCreate,
        current_user: Optional[User] = None
    ) -> RSVPResponseResponse:
        """Create an RSVP response (public endpoint - guest can RSVP without login)"""
        # Check if guest exists
        guest = await self.repo.get_guest(rsvp_data.guest_id)
        if not guest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest not found"
            )

        # Validate plus-one if attempting to RSVP with one
        if rsvp_data.plus_one_attending and not guest.allows_plus_one:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plus-one not allowed for this guest"
            )

        rsvp = await self.repo.create_rsvp_response(rsvp_data)

        # Update group stats
        if guest.group_id:
            await self.repo.update_group_stats(guest.group_id)

        await self.db.commit()
        return RSVPResponseResponse.model_validate(rsvp)

    async def get_rsvp_response(
        self,
        rsvp_id: UUID,
        current_user: User
    ) -> RSVPResponseResponse:
        """Get an RSVP response by ID"""
        rsvp = await self.repo.get_rsvp_response(rsvp_id)
        if not rsvp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="RSVP response not found"
            )

        await self._check_event_access(rsvp.event_id, current_user)
        return RSVPResponseResponse.model_validate(rsvp)

    async def get_latest_rsvp_by_guest(
        self,
        guest_id: UUID,
        current_user: User
    ) -> RSVPResponseResponse:
        """Get the latest RSVP response for a guest"""
        guest = await self.repo.get_guest(guest_id)
        if not guest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest not found"
            )

        await self._check_event_access(guest.event_id, current_user)

        rsvp = await self.repo.get_latest_rsvp_by_guest(guest_id)
        if not rsvp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No RSVP response found for this guest"
            )

        return RSVPResponseResponse.model_validate(rsvp)

    async def get_rsvp_responses_by_event(
        self,
        event_id: UUID,
        current_user: User,
        status: Optional[RSVPStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[RSVPResponseResponse]:
        """Get RSVP responses for an event"""
        await self._check_event_access(event_id, current_user)

        rsvps = await self.repo.get_rsvp_responses_by_event(
            event_id=event_id,
            status=status,
            skip=skip,
            limit=limit
        )
        return [RSVPResponseResponse.model_validate(r) for r in rsvps]

    # ========================================================================
    # Seating Arrangement Operations
    # ========================================================================

    async def create_seating_arrangement(
        self,
        seating_data: SeatingArrangementCreate,
        current_user: User
    ) -> SeatingArrangementResponse:
        """Create a new seating arrangement"""
        await self._check_event_access(seating_data.event_id, current_user)

        # Check if table number already exists
        existing = await self.repo.get_seating_by_table_number(
            seating_data.event_id,
            seating_data.table_number
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table number {seating_data.table_number} already exists for this event"
            )

        seating = await self.repo.create_seating_arrangement(seating_data, current_user.id)
        await self.db.commit()
        return SeatingArrangementResponse.model_validate(seating)

    async def get_seating_arrangement(
        self,
        seating_id: UUID,
        current_user: User
    ) -> SeatingArrangementResponse:
        """Get a seating arrangement by ID"""
        seating = await self.repo.get_seating_arrangement(seating_id)
        if not seating:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Seating arrangement not found"
            )

        await self._check_event_access(seating.event_id, current_user)
        return SeatingArrangementResponse.model_validate(seating)

    async def get_seating_by_event(
        self,
        event_id: UUID,
        current_user: User
    ) -> List[SeatingArrangementResponse]:
        """Get all seating arrangements for an event"""
        await self._check_event_access(event_id, current_user)

        seatings = await self.repo.get_seating_by_event(event_id)
        return [SeatingArrangementResponse.model_validate(s) for s in seatings]

    async def update_seating_arrangement(
        self,
        seating_id: UUID,
        seating_data: SeatingArrangementUpdate,
        current_user: User
    ) -> SeatingArrangementResponse:
        """Update a seating arrangement"""
        seating = await self.repo.get_seating_arrangement(seating_id)
        if not seating:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Seating arrangement not found"
            )

        await self._check_event_access(seating.event_id, current_user)

        # Check if new table number conflicts
        if seating_data.table_number and seating_data.table_number != seating.table_number:
            existing = await self.repo.get_seating_by_table_number(
                seating.event_id,
                seating_data.table_number
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Table number {seating_data.table_number} already exists for this event"
                )

        updated_seating = await self.repo.update_seating_arrangement(seating_id, seating_data)
        await self.db.commit()
        return SeatingArrangementResponse.model_validate(updated_seating)

    async def delete_seating_arrangement(
        self,
        seating_id: UUID,
        current_user: User
    ) -> dict:
        """Delete a seating arrangement"""
        seating = await self.repo.get_seating_arrangement(seating_id)
        if not seating:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Seating arrangement not found"
            )

        await self._check_event_access(seating.event_id, current_user)

        success = await self.repo.delete_seating_arrangement(seating_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete seating arrangement"
            )

        await self.db.commit()
        return {"message": "Seating arrangement deleted successfully"}

    # ========================================================================
    # Check-In Operations
    # ========================================================================

    async def check_in_guest(
        self,
        checkin_data: GuestCheckInCreate,
        current_user: User
    ) -> GuestCheckInResponse:
        """Check in a guest at the event"""
        await self._check_event_access(checkin_data.event_id, current_user)

        # Check if guest exists
        guest = await self.repo.get_guest(checkin_data.guest_id)
        if not guest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest not found"
            )

        # Check if already checked in
        existing_checkin = await self.repo.get_check_in_by_guest(
            checkin_data.guest_id,
            checkin_data.event_id
        )
        if existing_checkin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Guest already checked in"
            )

        checkin = await self.repo.create_check_in(checkin_data, current_user.id)
        await self.db.commit()
        return GuestCheckInResponse.model_validate(checkin)

    async def get_check_ins_by_event(
        self,
        event_id: UUID,
        current_user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[GuestCheckInResponse]:
        """Get all check-ins for an event"""
        await self._check_event_access(event_id, current_user)

        checkins = await self.repo.get_check_ins_by_event(event_id, skip, limit)
        return [GuestCheckInResponse.model_validate(c) for c in checkins]

    # ========================================================================
    # Dietary Restriction Operations
    # ========================================================================

    async def create_dietary_restriction(
        self,
        restriction_data: DietaryRestrictionCreate,
        current_user: User
    ) -> DietaryRestrictionResponse:
        """Create a new dietary restriction (admin only)"""
        if current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        # Check if already exists
        existing = await self.repo.get_dietary_restriction_by_name(restriction_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dietary restriction '{restriction_data.name}' already exists"
            )

        restriction = await self.repo.create_dietary_restriction(restriction_data)
        await self.db.commit()
        return DietaryRestrictionResponse.model_validate(restriction)

    async def get_all_dietary_restrictions(
        self,
        active_only: bool = True
    ) -> List[DietaryRestrictionResponse]:
        """Get all dietary restrictions"""
        restrictions = await self.repo.get_all_dietary_restrictions(active_only)
        return [DietaryRestrictionResponse.model_validate(r) for r in restrictions]

    async def update_dietary_restriction(
        self,
        restriction_id: UUID,
        restriction_data: DietaryRestrictionUpdate,
        current_user: User
    ) -> DietaryRestrictionResponse:
        """Update a dietary restriction (admin only)"""
        if current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        restriction = await self.repo.get_dietary_restriction(restriction_id)
        if not restriction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dietary restriction not found"
            )

        updated_restriction = await self.repo.update_dietary_restriction(
            restriction_id,
            restriction_data
        )
        await self.db.commit()
        return DietaryRestrictionResponse.model_validate(updated_restriction)

    # ========================================================================
    # Statistics
    # ========================================================================

    async def get_guest_statistics(
        self,
        event_id: UUID,
        current_user: User
    ) -> GuestStatistics:
        """Get comprehensive guest statistics for an event"""
        await self._check_event_access(event_id, current_user)

        stats = await self.repo.get_guest_statistics(event_id)

        # Get category breakdown
        by_category = {}
        for category in ["family", "friends", "colleagues", "vip", "bride_side", "groom_side", "other"]:
            count = await self.repo.get_guest_count(event_id, category=category)
            by_category[category] = count

        # Get dietary restrictions summary
        # TODO: Implement dietary restrictions summary

        # Get seating stats
        seating_stats = await self.repo.get_seating_statistics(event_id)

        return GuestStatistics(
            **stats,
            by_category=by_category,
            dietary_restrictions_summary={},
            total_tables=seating_stats["total_tables"],
            assigned_seats=seating_stats["assigned_seats"],
            available_seats=seating_stats["available_seats"]
        )

    async def get_seating_statistics(
        self,
        event_id: UUID,
        current_user: User
    ) -> SeatingStatistics:
        """Get seating statistics for an event"""
        await self._check_event_access(event_id, current_user)

        stats = await self.repo.get_seating_statistics(event_id)
        return SeatingStatistics(
            **stats,
            tables_by_section={},
            tables_by_type={}
        )
