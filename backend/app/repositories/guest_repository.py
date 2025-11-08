"""
Guest Management Repository

Data access layer for guest management system providing CRUD operations
and database queries for guests, RSVPs, invitations, and seating.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import joinedload, selectinload
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.models.guest import (
    Guest, GuestGroup, GuestInvitation, RSVPResponse,
    SeatingArrangement, GuestCheckIn, DietaryRestriction,
    GuestStatus, RSVPStatus, InvitationStatus
)
from app.schemas.guest import (
    GuestCreate, GuestUpdate, GuestGroupCreate, GuestGroupUpdate,
    GuestInvitationCreate, RSVPResponseCreate, RSVPResponseUpdate,
    SeatingArrangementCreate, SeatingArrangementUpdate,
    GuestCheckInCreate, DietaryRestrictionCreate, DietaryRestrictionUpdate
)


class GuestRepository:
    """Repository for guest-related database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Guest CRUD Operations
    # ========================================================================

    async def create_guest(self, guest_data: GuestCreate, created_by: UUID) -> Guest:
        """Create a new guest"""
        guest = Guest(
            **guest_data.model_dump(exclude={'event_id'}),
            event_id=guest_data.event_id,
            created_by=created_by
        )
        self.db.add(guest)
        await self.db.flush()
        await self.db.refresh(guest)
        return guest

    async def get_guest(self, guest_id: UUID) -> Optional[Guest]:
        """Get a guest by ID"""
        query = select(Guest).where(Guest.id == guest_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_guests_by_event(
        self,
        event_id: UUID,
        status: Optional[GuestStatus] = None,
        rsvp_status: Optional[RSVPStatus] = None,
        category: Optional[str] = None,
        group_id: Optional[UUID] = None,
        is_vip: Optional[bool] = None,
        checked_in: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Guest]:
        """Get guests for an event with filters"""
        query = select(Guest).where(Guest.event_id == event_id)

        # Apply filters
        if status:
            query = query.where(Guest.status == status.value)
        if rsvp_status:
            query = query.where(Guest.rsvp_status == rsvp_status.value)
        if category:
            query = query.where(Guest.category == category)
        if group_id:
            query = query.where(Guest.group_id == group_id)
        if is_vip is not None:
            query = query.where(Guest.is_vip == is_vip)
        if checked_in is not None:
            query = query.where(Guest.checked_in == checked_in)

        # Search by name or email
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Guest.first_name.ilike(search_pattern),
                    Guest.last_name.ilike(search_pattern),
                    Guest.email.ilike(search_pattern),
                    Guest.phone.ilike(search_pattern)
                )
            )

        # Order and paginate
        query = query.order_by(Guest.last_name, Guest.first_name).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_guest(self, guest_id: UUID, guest_data: GuestUpdate) -> Optional[Guest]:
        """Update a guest"""
        guest = await self.get_guest(guest_id)
        if not guest:
            return None

        update_data = guest_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(guest, key, value)

        guest.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(guest)
        return guest

    async def delete_guest(self, guest_id: UUID) -> bool:
        """Delete a guest"""
        guest = await self.get_guest(guest_id)
        if not guest:
            return False

        await self.db.delete(guest)
        await self.db.flush()
        return True

    async def bulk_create_guests(self, guests_data: List[GuestCreate], created_by: UUID) -> List[Guest]:
        """Bulk create guests"""
        guests = []
        for guest_data in guests_data:
            guest = Guest(
                **guest_data.model_dump(exclude={'event_id'}),
                event_id=guest_data.event_id,
                created_by=created_by
            )
            guests.append(guest)
            self.db.add(guest)

        await self.db.flush()
        for guest in guests:
            await self.db.refresh(guest)
        return guests

    async def get_guest_count(self, event_id: UUID, **filters) -> int:
        """Get total guest count for an event with filters"""
        query = select(func.count(Guest.id)).where(Guest.event_id == event_id)

        if filters.get('status'):
            query = query.where(Guest.status == filters['status'])
        if filters.get('rsvp_status'):
            query = query.where(Guest.rsvp_status == filters['rsvp_status'])
        if filters.get('category'):
            query = query.where(Guest.category == filters['category'])

        result = await self.db.execute(query)
        return result.scalar_one()

    # ========================================================================
    # Guest Group Operations
    # ========================================================================

    async def create_guest_group(self, group_data: GuestGroupCreate, created_by: UUID) -> GuestGroup:
        """Create a new guest group"""
        group = GuestGroup(
            **group_data.model_dump(exclude={'event_id'}),
            event_id=group_data.event_id,
            created_by=created_by
        )
        self.db.add(group)
        await self.db.flush()
        await self.db.refresh(group)
        return group

    async def get_guest_group(self, group_id: UUID) -> Optional[GuestGroup]:
        """Get a guest group by ID"""
        query = select(GuestGroup).where(GuestGroup.id == group_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_guest_groups_by_event(self, event_id: UUID) -> List[GuestGroup]:
        """Get all guest groups for an event"""
        query = select(GuestGroup).where(GuestGroup.event_id == event_id).order_by(GuestGroup.name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_guest_group(self, group_id: UUID, group_data: GuestGroupUpdate) -> Optional[GuestGroup]:
        """Update a guest group"""
        group = await self.get_guest_group(group_id)
        if not group:
            return None

        update_data = group_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(group, key, value)

        group.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(group)
        return group

    async def delete_guest_group(self, group_id: UUID) -> bool:
        """Delete a guest group"""
        group = await self.get_guest_group(group_id)
        if not group:
            return False

        # Unassign guests from this group
        await self.db.execute(
            update(Guest)
            .where(Guest.group_id == group_id)
            .values(group_id=None)
        )

        await self.db.delete(group)
        await self.db.flush()
        return True

    async def update_group_stats(self, group_id: UUID) -> Optional[GuestGroup]:
        """Update guest group statistics"""
        group = await self.get_guest_group(group_id)
        if not group:
            return None

        # Count guests by status
        total_query = select(func.count(Guest.id)).where(Guest.group_id == group_id)
        confirmed_query = select(func.count(Guest.id)).where(
            and_(Guest.group_id == group_id, Guest.rsvp_status == RSVPStatus.ATTENDING.value)
        )
        declined_query = select(func.count(Guest.id)).where(
            and_(Guest.group_id == group_id, Guest.rsvp_status == RSVPStatus.NOT_ATTENDING.value)
        )
        pending_query = select(func.count(Guest.id)).where(
            and_(Guest.group_id == group_id, Guest.rsvp_status == RSVPStatus.PENDING.value)
        )

        total = (await self.db.execute(total_query)).scalar_one()
        confirmed = (await self.db.execute(confirmed_query)).scalar_one()
        declined = (await self.db.execute(declined_query)).scalar_one()
        pending = (await self.db.execute(pending_query)).scalar_one()

        group.total_guests = total
        group.confirmed_guests = confirmed
        group.declined_guests = declined
        group.pending_guests = pending
        group.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(group)
        return group

    # ========================================================================
    # Invitation Operations
    # ========================================================================

    async def create_invitation(self, invitation_data: GuestInvitationCreate, sent_by: UUID) -> GuestInvitation:
        """Create a new invitation"""
        # Determine reminder number if this is a reminder
        reminder_number = 0
        if invitation_data.is_reminder:
            existing_count = await self.db.execute(
                select(func.count(GuestInvitation.id))
                .where(
                    and_(
                        GuestInvitation.guest_id == invitation_data.guest_id,
                        GuestInvitation.is_reminder == True
                    )
                )
            )
            reminder_number = existing_count.scalar_one() + 1

        invitation = GuestInvitation(
            **invitation_data.model_dump(),
            sent_by=sent_by,
            reminder_number=reminder_number
        )
        self.db.add(invitation)
        await self.db.flush()
        await self.db.refresh(invitation)
        return invitation

    async def get_invitation(self, invitation_id: UUID) -> Optional[GuestInvitation]:
        """Get an invitation by ID"""
        query = select(GuestInvitation).where(GuestInvitation.id == invitation_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_invitations_by_guest(self, guest_id: UUID) -> List[GuestInvitation]:
        """Get all invitations for a guest"""
        query = select(GuestInvitation).where(GuestInvitation.guest_id == guest_id).order_by(GuestInvitation.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_invitations_by_event(
        self,
        event_id: UUID,
        status: Optional[InvitationStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[GuestInvitation]:
        """Get invitations for an event"""
        query = select(GuestInvitation).where(GuestInvitation.event_id == event_id)

        if status:
            query = query.where(GuestInvitation.status == status.value)

        query = query.order_by(GuestInvitation.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_invitation_sent(self, invitation_id: UUID) -> Optional[GuestInvitation]:
        """Mark invitation as sent"""
        invitation = await self.get_invitation(invitation_id)
        if not invitation:
            return None

        invitation.status = InvitationStatus.SENT.value
        invitation.sent_at = datetime.utcnow()
        invitation.updated_at = datetime.utcnow()

        # Update guest
        await self.db.execute(
            update(Guest)
            .where(Guest.id == invitation.guest_id)
            .values(
                status=GuestStatus.INVITED.value,
                invitation_sent_at=datetime.utcnow()
            )
        )

        await self.db.flush()
        await self.db.refresh(invitation)
        return invitation

    async def mark_invitation_opened(self, invitation_id: UUID) -> Optional[GuestInvitation]:
        """Mark invitation as opened"""
        invitation = await self.get_invitation(invitation_id)
        if not invitation:
            return None

        invitation.status = InvitationStatus.OPENED.value
        invitation.opened_at = datetime.utcnow()
        invitation.open_count += 1
        invitation.last_opened_at = datetime.utcnow()
        invitation.updated_at = datetime.utcnow()

        # Update guest
        if not invitation.guest.invitation_opened_at:
            await self.db.execute(
                update(Guest)
                .where(Guest.id == invitation.guest_id)
                .values(invitation_opened_at=datetime.utcnow())
            )

        await self.db.flush()
        await self.db.refresh(invitation)
        return invitation

    # ========================================================================
    # RSVP Operations
    # ========================================================================

    async def create_rsvp_response(self, rsvp_data: RSVPResponseCreate) -> RSVPResponse:
        """Create a new RSVP response"""
        # Mark previous responses as not latest
        await self.db.execute(
            update(RSVPResponse)
            .where(
                and_(
                    RSVPResponse.guest_id == rsvp_data.guest_id,
                    RSVPResponse.is_latest == True
                )
            )
            .values(is_latest=False)
        )

        rsvp = RSVPResponse(**rsvp_data.model_dump())
        self.db.add(rsvp)

        # Update guest RSVP status
        attending_count = rsvp_data.attending_count
        if rsvp_data.plus_one_attending:
            attending_count += 1

        guest_status = GuestStatus.CONFIRMED
        if rsvp_data.status == RSVPStatus.NOT_ATTENDING:
            guest_status = GuestStatus.DECLINED
        elif rsvp_data.status == RSVPStatus.MAYBE:
            guest_status = GuestStatus.TENTATIVE

        await self.db.execute(
            update(Guest)
            .where(Guest.id == rsvp_data.guest_id)
            .values(
                rsvp_status=rsvp_data.status.value,
                rsvp_responded_at=datetime.utcnow(),
                attending_count=attending_count,
                status=guest_status.value,
                dietary_restrictions=rsvp_data.dietary_restrictions,
                meal_preference=rsvp_data.meal_preference,
                plus_one_name=rsvp_data.plus_one_name if rsvp_data.plus_one_attending else None
            )
        )

        await self.db.flush()
        await self.db.refresh(rsvp)
        return rsvp

    async def get_rsvp_response(self, rsvp_id: UUID) -> Optional[RSVPResponse]:
        """Get an RSVP response by ID"""
        query = select(RSVPResponse).where(RSVPResponse.id == rsvp_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_rsvp_by_guest(self, guest_id: UUID) -> Optional[RSVPResponse]:
        """Get the latest RSVP response for a guest"""
        query = select(RSVPResponse).where(
            and_(
                RSVPResponse.guest_id == guest_id,
                RSVPResponse.is_latest == True
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_rsvp_responses_by_event(
        self,
        event_id: UUID,
        status: Optional[RSVPStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[RSVPResponse]:
        """Get RSVP responses for an event"""
        query = select(RSVPResponse).where(
            and_(
                RSVPResponse.event_id == event_id,
                RSVPResponse.is_latest == True
            )
        )

        if status:
            query = query.where(RSVPResponse.status == status.value)

        query = query.order_by(RSVPResponse.responded_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Seating Arrangement Operations
    # ========================================================================

    async def create_seating_arrangement(
        self,
        seating_data: SeatingArrangementCreate,
        created_by: UUID
    ) -> SeatingArrangement:
        """Create a new seating arrangement"""
        seating = SeatingArrangement(
            **seating_data.model_dump(exclude={'event_id'}),
            event_id=seating_data.event_id,
            created_by=created_by
        )
        self.db.add(seating)
        await self.db.flush()
        await self.db.refresh(seating)
        return seating

    async def get_seating_arrangement(self, seating_id: UUID) -> Optional[SeatingArrangement]:
        """Get a seating arrangement by ID"""
        query = select(SeatingArrangement).where(SeatingArrangement.id == seating_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_seating_by_event(self, event_id: UUID) -> List[SeatingArrangement]:
        """Get all seating arrangements for an event"""
        query = select(SeatingArrangement).where(
            SeatingArrangement.event_id == event_id
        ).order_by(SeatingArrangement.table_number)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_seating_by_table_number(self, event_id: UUID, table_number: int) -> Optional[SeatingArrangement]:
        """Get seating arrangement by table number"""
        query = select(SeatingArrangement).where(
            and_(
                SeatingArrangement.event_id == event_id,
                SeatingArrangement.table_number == table_number
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_seating_arrangement(
        self,
        seating_id: UUID,
        seating_data: SeatingArrangementUpdate
    ) -> Optional[SeatingArrangement]:
        """Update a seating arrangement"""
        seating = await self.get_seating_arrangement(seating_id)
        if not seating:
            return None

        update_data = seating_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(seating, key, value)

        seating.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(seating)
        return seating

    async def delete_seating_arrangement(self, seating_id: UUID) -> bool:
        """Delete a seating arrangement"""
        seating = await self.get_seating_arrangement(seating_id)
        if not seating:
            return False

        # Unassign guests from this table
        await self.db.execute(
            update(Guest)
            .where(Guest.table_number == seating.table_number)
            .values(table_number=None, seat_number=None)
        )

        await self.db.delete(seating)
        await self.db.flush()
        return True

    async def update_seating_occupancy(self, event_id: UUID, table_number: int) -> Optional[SeatingArrangement]:
        """Update seating occupancy count"""
        seating = await self.get_seating_by_table_number(event_id, table_number)
        if not seating:
            return None

        # Count assigned guests
        assigned_count = await self.db.execute(
            select(func.count(Guest.id))
            .where(
                and_(
                    Guest.event_id == event_id,
                    Guest.table_number == table_number
                )
            )
        )
        seating.assigned_seats = assigned_count.scalar_one()
        seating.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(seating)
        return seating

    # ========================================================================
    # Check-In Operations
    # ========================================================================

    async def create_check_in(self, checkin_data: GuestCheckInCreate, checked_in_by: UUID) -> GuestCheckIn:
        """Create a new guest check-in"""
        checkin = GuestCheckIn(
            **checkin_data.model_dump(),
            checked_in_by=checked_in_by
        )
        self.db.add(checkin)

        # Update guest status
        await self.db.execute(
            update(Guest)
            .where(Guest.id == checkin_data.guest_id)
            .values(
                checked_in=True,
                checked_in_at=datetime.utcnow(),
                checked_in_by=checked_in_by,
                status=GuestStatus.CHECKED_IN.value
            )
        )

        await self.db.flush()
        await self.db.refresh(checkin)
        return checkin

    async def get_check_in(self, checkin_id: UUID) -> Optional[GuestCheckIn]:
        """Get a check-in by ID"""
        query = select(GuestCheckIn).where(GuestCheckIn.id == checkin_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_check_in_by_guest(self, guest_id: UUID, event_id: UUID) -> Optional[GuestCheckIn]:
        """Get check-in for a guest at an event"""
        query = select(GuestCheckIn).where(
            and_(
                GuestCheckIn.guest_id == guest_id,
                GuestCheckIn.event_id == event_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_check_ins_by_event(self, event_id: UUID, skip: int = 0, limit: int = 100) -> List[GuestCheckIn]:
        """Get all check-ins for an event"""
        query = select(GuestCheckIn).where(
            GuestCheckIn.event_id == event_id
        ).order_by(GuestCheckIn.checked_in_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Dietary Restriction Operations
    # ========================================================================

    async def create_dietary_restriction(self, restriction_data: DietaryRestrictionCreate) -> DietaryRestriction:
        """Create a new dietary restriction"""
        restriction = DietaryRestriction(**restriction_data.model_dump())
        self.db.add(restriction)
        await self.db.flush()
        await self.db.refresh(restriction)
        return restriction

    async def get_dietary_restriction(self, restriction_id: UUID) -> Optional[DietaryRestriction]:
        """Get a dietary restriction by ID"""
        query = select(DietaryRestriction).where(DietaryRestriction.id == restriction_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_dietary_restriction_by_name(self, name: str) -> Optional[DietaryRestriction]:
        """Get a dietary restriction by name"""
        query = select(DietaryRestriction).where(DietaryRestriction.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_dietary_restrictions(self, active_only: bool = True) -> List[DietaryRestriction]:
        """Get all dietary restrictions"""
        query = select(DietaryRestriction)

        if active_only:
            query = query.where(DietaryRestriction.is_active == True)

        query = query.order_by(DietaryRestriction.is_common.desc(), DietaryRestriction.name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_dietary_restriction(
        self,
        restriction_id: UUID,
        restriction_data: DietaryRestrictionUpdate
    ) -> Optional[DietaryRestriction]:
        """Update a dietary restriction"""
        restriction = await self.get_dietary_restriction(restriction_id)
        if not restriction:
            return None

        update_data = restriction_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(restriction, key, value)

        restriction.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(restriction)
        return restriction

    # ========================================================================
    # Statistics and Analytics
    # ========================================================================

    async def get_guest_statistics(self, event_id: UUID) -> dict:
        """Get comprehensive guest statistics for an event"""
        # Total counts
        total_guests = await self.get_guest_count(event_id)
        invited = await self.get_guest_count(event_id, status=GuestStatus.INVITED.value)
        confirmed = await self.get_guest_count(event_id, rsvp_status=RSVPStatus.ATTENDING.value)
        declined = await self.get_guest_count(event_id, rsvp_status=RSVPStatus.NOT_ATTENDING.value)
        tentative = await self.get_guest_count(event_id, rsvp_status=RSVPStatus.MAYBE.value)
        pending = await self.get_guest_count(event_id, rsvp_status=RSVPStatus.PENDING.value)

        # Count checked-in guests
        checked_in_query = select(func.count(Guest.id)).where(
            and_(Guest.event_id == event_id, Guest.checked_in == True)
        )
        checked_in = (await self.db.execute(checked_in_query)).scalar_one()

        # Count total attending (including plus-ones)
        attending_sum_query = select(func.sum(Guest.attending_count)).where(
            and_(
                Guest.event_id == event_id,
                Guest.rsvp_status == RSVPStatus.ATTENDING.value
            )
        )
        total_attending = (await self.db.execute(attending_sum_query)).scalar_one() or 0

        # Count plus-ones
        plus_ones_query = select(func.count(Guest.id)).where(
            and_(
                Guest.event_id == event_id,
                Guest.plus_one_name.isnot(None)
            )
        )
        plus_ones = (await self.db.execute(plus_ones_query)).scalar_one()

        # Response rate
        rsvp_response_rate = 0.0
        if total_guests > 0:
            responded = confirmed + declined + tentative
            rsvp_response_rate = (responded / total_guests) * 100

        # Check-in rate
        check_in_rate = 0.0
        if confirmed > 0:
            check_in_rate = (checked_in / confirmed) * 100

        return {
            "total_guests": total_guests,
            "invited_guests": invited,
            "confirmed_guests": confirmed,
            "declined_guests": declined,
            "tentative_guests": tentative,
            "pending_guests": pending,
            "checked_in_guests": checked_in,
            "total_attending": int(total_attending),
            "plus_ones_count": plus_ones,
            "rsvp_response_rate": round(rsvp_response_rate, 2),
            "check_in_rate": round(check_in_rate, 2)
        }

    async def get_seating_statistics(self, event_id: UUID) -> dict:
        """Get seating statistics for an event"""
        # Get all seating arrangements
        seatings = await self.get_seating_by_event(event_id)

        total_tables = len(seatings)
        total_capacity = sum(s.table_capacity for s in seatings)
        assigned_seats = sum(s.assigned_seats for s in seatings)
        available_seats = total_capacity - assigned_seats

        occupancy_rate = 0.0
        if total_capacity > 0:
            occupancy_rate = (assigned_seats / total_capacity) * 100

        vip_tables = sum(1 for s in seatings if s.is_vip_table)
        kids_tables = sum(1 for s in seatings if s.is_kids_table)

        return {
            "total_tables": total_tables,
            "total_capacity": total_capacity,
            "assigned_seats": assigned_seats,
            "available_seats": available_seats,
            "occupancy_rate": round(occupancy_rate, 2),
            "vip_tables": vip_tables,
            "kids_tables": kids_tables
        }
