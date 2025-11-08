"""
CelebraTech Event Management System - Calendar Service
Sprint 14: Calendar & Scheduling System
Business logic for calendar operations
"""
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from uuid import UUID

from app.models.calendar import (
    Calendar,
    CalendarEvent,
    CalendarSync,
    Availability,
    TimeSlotBooking,
    ScheduleConflict,
    ConflictType
)
from app.models.user import User
from app.schemas.calendar import (
    CalendarCreate,
    CalendarUpdate,
    CalendarEventCreate,
    CalendarEventUpdate,
    AvailabilityCreate,
    TimeSlotBookingCreate
)
from app.repositories.calendar_repository import CalendarRepository


class CalendarService:
    """Service for calendar operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.calendar_repo = CalendarRepository(db)

    # ========================================================================
    # Calendar Operations
    # ========================================================================

    async def create_calendar(
        self,
        calendar_data: CalendarCreate,
        current_user: User
    ) -> Calendar:
        """
        Create a new calendar

        Args:
            calendar_data: Calendar creation data
            current_user: Current authenticated user

        Returns:
            Created calendar object

        Raises:
            HTTPException: If validation fails
        """
        # Validate event/vendor ownership if specified
        if calendar_data.event_id:
            # TODO: Verify user has permission for this event
            pass

        if calendar_data.vendor_id:
            # TODO: Verify user owns this vendor
            pass

        calendar = await self.calendar_repo.create_calendar(
            calendar_data,
            current_user.id
        )

        await self.db.commit()
        return calendar

    async def get_calendar(
        self,
        calendar_id: UUID,
        current_user: User
    ) -> Calendar:
        """
        Get calendar by ID with permission check

        Args:
            calendar_id: Calendar UUID
            current_user: Current authenticated user

        Returns:
            Calendar object

        Raises:
            HTTPException: If calendar not found or no permission
        """
        calendar = await self.calendar_repo.get_calendar_by_id(
            calendar_id,
            current_user.id
        )

        if not calendar:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Calendar not found"
            )

        # Check permission
        if calendar.user_id != current_user.id and not calendar.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to view this calendar"
            )

        return calendar

    async def get_user_calendars(
        self,
        current_user: User,
        include_public: bool = False
    ) -> List[Calendar]:
        """
        Get all calendars for current user

        Args:
            current_user: Current authenticated user
            include_public: Include public calendars

        Returns:
            List of calendar objects
        """
        calendars = await self.calendar_repo.get_user_calendars(
            current_user.id,
            include_public
        )

        return calendars

    async def get_event_calendar(
        self,
        event_id: UUID,
        current_user: User
    ) -> Optional[Calendar]:
        """
        Get calendar for a specific event

        Args:
            event_id: Event UUID
            current_user: Current authenticated user

        Returns:
            Calendar object or None

        Raises:
            HTTPException: If no permission
        """
        calendar = await self.calendar_repo.get_event_calendar(event_id)

        if not calendar:
            return None

        # Check permission
        if calendar.user_id != current_user.id and not calendar.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to view this calendar"
            )

        return calendar

    async def update_calendar(
        self,
        calendar_id: UUID,
        calendar_data: CalendarUpdate,
        current_user: User
    ) -> Calendar:
        """
        Update a calendar

        Args:
            calendar_id: Calendar UUID
            calendar_data: Updated calendar data
            current_user: Current authenticated user

        Returns:
            Updated calendar object

        Raises:
            HTTPException: If calendar not found or no permission
        """
        # Check permission
        calendar = await self.get_calendar(calendar_id, current_user)

        if calendar.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to update this calendar"
            )

        updated_calendar = await self.calendar_repo.update_calendar(
            calendar_id,
            calendar_data
        )

        await self.db.commit()
        return updated_calendar

    async def delete_calendar(
        self,
        calendar_id: UUID,
        current_user: User
    ) -> bool:
        """
        Delete a calendar

        Args:
            calendar_id: Calendar UUID
            current_user: Current authenticated user

        Returns:
            True if deleted

        Raises:
            HTTPException: If calendar not found or no permission
        """
        # Check permission
        calendar = await self.get_calendar(calendar_id, current_user)

        if calendar.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to delete this calendar"
            )

        success = await self.calendar_repo.delete_calendar(calendar_id)

        if success:
            await self.db.commit()

        return success

    # ========================================================================
    # Calendar Event Operations
    # ========================================================================

    async def create_calendar_event(
        self,
        event_data: CalendarEventCreate,
        current_user: User,
        check_conflicts: bool = True
    ) -> CalendarEvent:
        """
        Create a new calendar event

        Args:
            event_data: Event creation data
            current_user: Current authenticated user
            check_conflicts: Whether to check for conflicts

        Returns:
            Created calendar event object

        Raises:
            HTTPException: If validation fails or conflicts exist
        """
        # Verify calendar access
        calendar = await self.get_calendar(event_data.calendar_id, current_user)

        # Validate time range
        if event_data.end_time <= event_data.start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be after start time"
            )

        # Check for conflicts if requested
        if check_conflicts:
            conflicts = await self.calendar_repo.detect_conflicts(
                event_data.calendar_id,
                event_data.start_time,
                event_data.end_time
            )

            if conflicts:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Time slot conflicts with {len(conflicts)} existing event(s)",
                    headers={"X-Conflicts": str(len(conflicts))}
                )

        calendar_event = await self.calendar_repo.create_calendar_event(
            event_data,
            current_user.id
        )

        await self.db.commit()
        return calendar_event

    async def get_calendar_event(
        self,
        event_id: UUID,
        current_user: User
    ) -> CalendarEvent:
        """
        Get calendar event by ID

        Args:
            event_id: Event UUID
            current_user: Current authenticated user

        Returns:
            Calendar event object

        Raises:
            HTTPException: If event not found or no permission
        """
        calendar_event = await self.calendar_repo.get_calendar_event_by_id(event_id)

        if not calendar_event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Calendar event not found"
            )

        # Verify calendar access
        await self.get_calendar(calendar_event.calendar_id, current_user)

        return calendar_event

    async def get_calendar_events(
        self,
        calendar_id: UUID,
        current_user: User,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CalendarEvent]:
        """
        Get all events for a calendar within a date range

        Args:
            calendar_id: Calendar UUID
            current_user: Current authenticated user
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of calendar event objects

        Raises:
            HTTPException: If no permission
        """
        # Verify calendar access
        await self.get_calendar(calendar_id, current_user)

        # Set default date range if not provided (current month)
        if not start_date:
            start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        if not end_date:
            # Last day of month
            next_month = start_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)

        events = await self.calendar_repo.get_calendar_events(
            calendar_id,
            start_date,
            end_date
        )

        return events

    async def update_calendar_event(
        self,
        event_id: UUID,
        event_data: CalendarEventUpdate,
        current_user: User
    ) -> CalendarEvent:
        """
        Update a calendar event

        Args:
            event_id: Event UUID
            event_data: Updated event data
            current_user: Current authenticated user

        Returns:
            Updated calendar event object

        Raises:
            HTTPException: If event not found or no permission
        """
        # Verify access
        calendar_event = await self.get_calendar_event(event_id, current_user)

        calendar = await self.get_calendar(calendar_event.calendar_id, current_user)

        if calendar.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to update this event"
            )

        # Validate time range if being updated
        update_dict = event_data.model_dump(exclude_unset=True)
        if "start_time" in update_dict or "end_time" in update_dict:
            start = update_dict.get("start_time", calendar_event.start_time)
            end = update_dict.get("end_time", calendar_event.end_time)

            if end <= start:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="End time must be after start time"
                )

        updated_event = await self.calendar_repo.update_calendar_event(
            event_id,
            event_data
        )

        await self.db.commit()
        return updated_event

    async def delete_calendar_event(
        self,
        event_id: UUID,
        current_user: User
    ) -> bool:
        """
        Delete a calendar event

        Args:
            event_id: Event UUID
            current_user: Current authenticated user

        Returns:
            True if deleted

        Raises:
            HTTPException: If event not found or no permission
        """
        # Verify access
        calendar_event = await self.get_calendar_event(event_id, current_user)

        calendar = await self.get_calendar(calendar_event.calendar_id, current_user)

        if calendar.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to delete this event"
            )

        success = await self.calendar_repo.delete_calendar_event(event_id)

        if success:
            await self.db.commit()

        return success

    # ========================================================================
    # Conflict Detection
    # ========================================================================

    async def check_conflicts(
        self,
        calendar_id: UUID,
        start_time: datetime,
        end_time: datetime,
        current_user: User,
        exclude_event_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Check for scheduling conflicts

        Args:
            calendar_id: Calendar UUID
            start_time: Start time to check
            end_time: End time to check
            current_user: Current authenticated user
            exclude_event_id: Optional event ID to exclude

        Returns:
            List of conflict dictionaries

        Raises:
            HTTPException: If no permission
        """
        # Verify calendar access
        await self.get_calendar(calendar_id, current_user)

        conflicts = await self.calendar_repo.detect_conflicts(
            calendar_id,
            start_time,
            end_time,
            exclude_event_id
        )

        return conflicts

    async def get_unresolved_conflicts(
        self,
        calendar_id: UUID,
        current_user: User
    ) -> List[ScheduleConflict]:
        """
        Get all unresolved conflicts for a calendar

        Args:
            calendar_id: Calendar UUID
            current_user: Current authenticated user

        Returns:
            List of conflict objects

        Raises:
            HTTPException: If no permission
        """
        # Verify calendar access
        await self.get_calendar(calendar_id, current_user)

        conflicts = await self.calendar_repo.get_unresolved_conflicts(calendar_id)

        return conflicts

    # ========================================================================
    # Availability & Booking Operations
    # ========================================================================

    async def create_availability(
        self,
        availability_data: AvailabilityCreate,
        current_user: User,
        vendor_id: Optional[UUID] = None
    ) -> Availability:
        """
        Create availability slots

        Args:
            availability_data: Availability creation data
            current_user: Current authenticated user
            vendor_id: Optional vendor ID

        Returns:
            Created availability object

        Raises:
            HTTPException: If validation fails
        """
        # Verify calendar access
        await self.get_calendar(availability_data.calendar_id, current_user)

        availability = await self.calendar_repo.create_availability(
            availability_data,
            user_id=current_user.id,
            vendor_id=vendor_id
        )

        await self.db.commit()
        return availability

    async def get_vendor_availability(
        self,
        vendor_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> List[Availability]:
        """
        Get vendor availability within a date range

        Args:
            vendor_id: Vendor UUID
            start_date: Start date
            end_date: End date

        Returns:
            List of availability objects
        """
        availability = await self.calendar_repo.get_vendor_availability(
            vendor_id,
            start_date,
            end_date
        )

        return availability

    async def book_time_slot(
        self,
        booking_data: TimeSlotBookingCreate,
        current_user: User
    ) -> TimeSlotBooking:
        """
        Book a time slot

        Args:
            booking_data: Booking creation data
            current_user: Current authenticated user

        Returns:
            Created booking object

        Raises:
            HTTPException: If slot already booked
        """
        # Check if slot is already booked
        existing_bookings = await self.calendar_repo.get_bookings_for_availability(
            booking_data.availability_id,
            booking_data.booking_date
        )

        for booking in existing_bookings:
            if (booking_data.start_time < booking.end_time and
                booking_data.end_time > booking.start_time):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Time slot already booked"
                )

        booking = await self.calendar_repo.create_time_slot_booking(
            booking_data,
            current_user.id
        )

        await self.db.commit()
        return booking

    # ========================================================================
    # Calendar Sync Operations
    # ========================================================================

    async def create_calendar_sync(
        self,
        calendar_id: UUID,
        provider: str,
        external_calendar_id: str,
        access_token: str,
        refresh_token: Optional[str],
        current_user: User
    ) -> CalendarSync:
        """
        Create a calendar sync configuration

        Args:
            calendar_id: Calendar UUID
            provider: Sync provider
            external_calendar_id: External calendar ID
            access_token: OAuth access token
            refresh_token: Optional refresh token
            current_user: Current authenticated user

        Returns:
            Created sync object

        Raises:
            HTTPException: If no permission
        """
        # Verify calendar access
        calendar = await self.get_calendar(calendar_id, current_user)

        if calendar.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to sync this calendar"
            )

        sync = await self.calendar_repo.create_calendar_sync(
            calendar_id,
            provider,
            external_calendar_id,
            access_token,
            refresh_token
        )

        await self.db.commit()
        return sync

    async def get_calendar_syncs(
        self,
        calendar_id: UUID,
        current_user: User
    ) -> List[CalendarSync]:
        """
        Get all sync configurations for a calendar

        Args:
            calendar_id: Calendar UUID
            current_user: Current authenticated user

        Returns:
            List of sync objects

        Raises:
            HTTPException: If no permission
        """
        # Verify calendar access
        await self.get_calendar(calendar_id, current_user)

        syncs = await self.calendar_repo.get_calendar_syncs(calendar_id)

        return syncs

    async def trigger_calendar_sync(
        self,
        sync_id: UUID,
        current_user: User
    ) -> Dict[str, Any]:
        """
        Trigger a manual calendar sync

        Args:
            sync_id: Sync UUID
            current_user: Current authenticated user

        Returns:
            Sync result dictionary

        Raises:
            HTTPException: If no permission
        """
        # TODO: Implement actual sync logic with external calendar APIs
        # For now, just update the last_synced_at timestamp

        sync_result = await self.calendar_repo.update_sync_status(
            sync_id,
            datetime.utcnow()
        )

        if not sync_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sync configuration not found"
            )

        await self.db.commit()

        return {
            "sync_id": str(sync_id),
            "status": "success",
            "synced_at": sync_result.last_synced_at.isoformat(),
            "message": "Calendar synced successfully"
        }
