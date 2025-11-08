"""
CelebraTech Event Management System - Calendar Repository
Sprint 14: Calendar & Scheduling System
Data access layer for calendar operations
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from uuid import UUID

from app.models.calendar import (
    Calendar,
    CalendarEvent,
    CalendarSync,
    EventSchedule,
    TimeBlock,
    EventReminder,
    ScheduleTemplate,
    RecurrenceRule,
    ScheduleConflict,
    Availability,
    TimeSlotBooking,
    CalendarType,
    AvailabilityStatus,
    ConflictType
)
from app.schemas.calendar import (
    CalendarCreate,
    CalendarUpdate,
    CalendarEventCreate,
    CalendarEventUpdate,
    AvailabilityCreate,
    TimeSlotBookingCreate
)


class CalendarRepository:
    """Repository for calendar database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Calendar CRUD Operations
    # ========================================================================

    async def create_calendar(
        self,
        calendar_data: CalendarCreate,
        user_id: UUID
    ) -> Calendar:
        """
        Create a new calendar

        Args:
            calendar_data: Calendar creation data
            user_id: UUID of user creating the calendar

        Returns:
            Created calendar object
        """
        calendar = Calendar(
            user_id=user_id,
            event_id=calendar_data.event_id,
            vendor_id=calendar_data.vendor_id,
            name=calendar_data.name,
            description=calendar_data.description,
            type=calendar_data.type,
            color=calendar_data.color,
            settings=calendar_data.settings,
            is_public=calendar_data.is_public,
            is_default=calendar_data.is_default,
            is_active=True
        )

        self.db.add(calendar)
        await self.db.flush()
        await self.db.refresh(calendar)

        return calendar

    async def get_calendar_by_id(
        self,
        calendar_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[Calendar]:
        """
        Get a calendar by ID

        Args:
            calendar_id: UUID of the calendar
            user_id: Optional user ID for permission check

        Returns:
            Calendar object or None
        """
        query = select(Calendar).where(Calendar.id == calendar_id)

        if user_id:
            query = query.where(
                or_(
                    Calendar.user_id == user_id,
                    Calendar.is_public == True
                )
            )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_calendars(
        self,
        user_id: UUID,
        include_public: bool = False
    ) -> List[Calendar]:
        """
        Get all calendars for a user

        Args:
            user_id: UUID of the user
            include_public: Include public calendars

        Returns:
            List of calendar objects
        """
        query = select(Calendar).where(Calendar.is_active == True)

        if include_public:
            query = query.where(
                or_(
                    Calendar.user_id == user_id,
                    Calendar.is_public == True
                )
            )
        else:
            query = query.where(Calendar.user_id == user_id)

        query = query.order_by(Calendar.is_default.desc(), Calendar.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_event_calendar(
        self,
        event_id: UUID
    ) -> Optional[Calendar]:
        """
        Get calendar for a specific event

        Args:
            event_id: UUID of the event

        Returns:
            Calendar object or None
        """
        query = select(Calendar).where(
            and_(
                Calendar.event_id == event_id,
                Calendar.is_active == True
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_calendar(
        self,
        calendar_id: UUID,
        calendar_data: CalendarUpdate
    ) -> Optional[Calendar]:
        """
        Update a calendar

        Args:
            calendar_id: UUID of the calendar
            calendar_data: Updated calendar data

        Returns:
            Updated calendar object or None
        """
        calendar = await self.get_calendar_by_id(calendar_id)
        if not calendar:
            return None

        update_data = calendar_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(calendar, field, value)

        calendar.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(calendar)

        return calendar

    async def delete_calendar(self, calendar_id: UUID) -> bool:
        """
        Soft delete a calendar

        Args:
            calendar_id: UUID of the calendar

        Returns:
            True if deleted, False otherwise
        """
        calendar = await self.get_calendar_by_id(calendar_id)
        if not calendar:
            return False

        calendar.is_active = False
        calendar.updated_at = datetime.utcnow()

        await self.db.flush()

        return True

    # ========================================================================
    # Calendar Event CRUD Operations
    # ========================================================================

    async def create_calendar_event(
        self,
        event_data: CalendarEventCreate,
        user_id: UUID
    ) -> CalendarEvent:
        """
        Create a new calendar event

        Args:
            event_data: Event creation data
            user_id: UUID of user creating the event

        Returns:
            Created calendar event object
        """
        calendar_event = CalendarEvent(
            calendar_id=event_data.calendar_id,
            title=event_data.title,
            description=event_data.description,
            location=event_data.location,
            start_time=event_data.start_time,
            end_time=event_data.end_time,
            is_all_day=event_data.is_all_day,
            attendees=event_data.attendees,
            reminders=event_data.reminders,
            color=event_data.color,
            metadata=event_data.metadata,
            created_by=user_id
        )

        self.db.add(calendar_event)
        await self.db.flush()
        await self.db.refresh(calendar_event)

        return calendar_event

    async def get_calendar_event_by_id(
        self,
        event_id: UUID
    ) -> Optional[CalendarEvent]:
        """
        Get a calendar event by ID

        Args:
            event_id: UUID of the event

        Returns:
            Calendar event object or None
        """
        query = select(CalendarEvent).where(CalendarEvent.id == event_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_calendar_events(
        self,
        calendar_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CalendarEvent]:
        """
        Get all events for a calendar within a date range

        Args:
            calendar_id: UUID of the calendar
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of calendar event objects
        """
        query = select(CalendarEvent).where(
            CalendarEvent.calendar_id == calendar_id
        )

        if start_date:
            query = query.where(CalendarEvent.end_time >= start_date)
        if end_date:
            query = query.where(CalendarEvent.start_time <= end_date)

        query = query.order_by(CalendarEvent.start_time)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_calendar_event(
        self,
        event_id: UUID,
        event_data: CalendarEventUpdate
    ) -> Optional[CalendarEvent]:
        """
        Update a calendar event

        Args:
            event_id: UUID of the event
            event_data: Updated event data

        Returns:
            Updated calendar event object or None
        """
        calendar_event = await self.get_calendar_event_by_id(event_id)
        if not calendar_event:
            return None

        update_data = event_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(calendar_event, field, value)

        calendar_event.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(calendar_event)

        return calendar_event

    async def delete_calendar_event(self, event_id: UUID) -> bool:
        """
        Delete a calendar event

        Args:
            event_id: UUID of the event

        Returns:
            True if deleted, False otherwise
        """
        calendar_event = await self.get_calendar_event_by_id(event_id)
        if not calendar_event:
            return False

        await self.db.delete(calendar_event)
        await self.db.flush()

        return True

    # ========================================================================
    # Schedule Conflict Detection
    # ========================================================================

    async def detect_conflicts(
        self,
        calendar_id: UUID,
        start_time: datetime,
        end_time: datetime,
        exclude_event_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect scheduling conflicts for a given time range

        Args:
            calendar_id: UUID of the calendar
            start_time: Start time of proposed event
            end_time: End time of proposed event
            exclude_event_id: Optional event ID to exclude (for updates)

        Returns:
            List of conflict dictionaries
        """
        query = select(CalendarEvent).where(
            and_(
                CalendarEvent.calendar_id == calendar_id,
                CalendarEvent.start_time < end_time,
                CalendarEvent.end_time > start_time
            )
        )

        if exclude_event_id:
            query = query.where(CalendarEvent.id != exclude_event_id)

        result = await self.db.execute(query)
        conflicting_events = result.scalars().all()

        conflicts = []
        for event in conflicting_events:
            conflicts.append({
                "event_id": event.id,
                "title": event.title,
                "start_time": event.start_time,
                "end_time": event.end_time,
                "conflict_type": ConflictType.TIME_OVERLAP.value
            })

        return conflicts

    async def create_conflict_record(
        self,
        calendar_id: UUID,
        event1_id: UUID,
        event2_id: UUID,
        conflict_type: ConflictType
    ) -> ScheduleConflict:
        """
        Create a conflict record

        Args:
            calendar_id: UUID of the calendar
            event1_id: First conflicting event
            event2_id: Second conflicting event
            conflict_type: Type of conflict

        Returns:
            Created conflict object
        """
        conflict = ScheduleConflict(
            calendar_id=calendar_id,
            event1_id=event1_id,
            event2_id=event2_id,
            conflict_type=conflict_type,
            is_resolved=False
        )

        self.db.add(conflict)
        await self.db.flush()
        await self.db.refresh(conflict)

        return conflict

    async def get_unresolved_conflicts(
        self,
        calendar_id: UUID
    ) -> List[ScheduleConflict]:
        """
        Get all unresolved conflicts for a calendar

        Args:
            calendar_id: UUID of the calendar

        Returns:
            List of conflict objects
        """
        query = select(ScheduleConflict).where(
            and_(
                ScheduleConflict.calendar_id == calendar_id,
                ScheduleConflict.is_resolved == False
            )
        ).order_by(ScheduleConflict.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Availability & Time Slot Booking
    # ========================================================================

    async def create_availability(
        self,
        availability_data: AvailabilityCreate,
        user_id: Optional[UUID] = None,
        vendor_id: Optional[UUID] = None
    ) -> Availability:
        """
        Create availability slots

        Args:
            availability_data: Availability creation data
            user_id: Optional user ID
            vendor_id: Optional vendor ID

        Returns:
            Created availability object
        """
        availability = Availability(
            user_id=user_id,
            vendor_id=vendor_id,
            calendar_id=availability_data.calendar_id,
            day_of_week=availability_data.day_of_week,
            start_time=availability_data.start_time,
            end_time=availability_data.end_time,
            slot_duration_minutes=availability_data.slot_duration_minutes,
            status=availability_data.status,
            metadata=availability_data.metadata
        )

        self.db.add(availability)
        await self.db.flush()
        await self.db.refresh(availability)

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
            vendor_id: UUID of the vendor
            start_date: Start date
            end_date: End date

        Returns:
            List of availability objects
        """
        query = select(Availability).where(
            and_(
                Availability.vendor_id == vendor_id,
                Availability.status == AvailabilityStatus.AVAILABLE
            )
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_time_slot_booking(
        self,
        booking_data: TimeSlotBookingCreate,
        user_id: UUID
    ) -> TimeSlotBooking:
        """
        Book a time slot

        Args:
            booking_data: Booking creation data
            user_id: UUID of user making the booking

        Returns:
            Created booking object
        """
        booking = TimeSlotBooking(
            availability_id=booking_data.availability_id,
            event_id=booking_data.event_id,
            user_id=user_id,
            booking_date=booking_data.booking_date,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            status="pending"
        )

        self.db.add(booking)
        await self.db.flush()
        await self.db.refresh(booking)

        return booking

    async def get_bookings_for_availability(
        self,
        availability_id: UUID,
        date: datetime
    ) -> List[TimeSlotBooking]:
        """
        Get all bookings for an availability slot on a specific date

        Args:
            availability_id: UUID of the availability
            date: Date to check

        Returns:
            List of booking objects
        """
        query = select(TimeSlotBooking).where(
            and_(
                TimeSlotBooking.availability_id == availability_id,
                func.date(TimeSlotBooking.booking_date) == date.date()
            )
        ).order_by(TimeSlotBooking.start_time)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Calendar Sync Operations
    # ========================================================================

    async def create_calendar_sync(
        self,
        calendar_id: UUID,
        provider: str,
        external_calendar_id: str,
        access_token: str,
        refresh_token: Optional[str] = None
    ) -> CalendarSync:
        """
        Create a calendar sync configuration

        Args:
            calendar_id: UUID of the calendar
            provider: Sync provider (google, outlook, apple)
            external_calendar_id: External calendar ID
            access_token: OAuth access token
            refresh_token: Optional refresh token

        Returns:
            Created sync object
        """
        sync = CalendarSync(
            calendar_id=calendar_id,
            provider=provider,
            external_calendar_id=external_calendar_id,
            access_token=access_token,
            refresh_token=refresh_token,
            is_active=True
        )

        self.db.add(sync)
        await self.db.flush()
        await self.db.refresh(sync)

        return sync

    async def get_calendar_syncs(
        self,
        calendar_id: UUID,
        active_only: bool = True
    ) -> List[CalendarSync]:
        """
        Get all sync configurations for a calendar

        Args:
            calendar_id: UUID of the calendar
            active_only: Only return active syncs

        Returns:
            List of sync objects
        """
        query = select(CalendarSync).where(
            CalendarSync.calendar_id == calendar_id
        )

        if active_only:
            query = query.where(CalendarSync.is_active == True)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_sync_status(
        self,
        sync_id: UUID,
        last_synced_at: datetime,
        error_message: Optional[str] = None
    ) -> Optional[CalendarSync]:
        """
        Update sync status after a sync operation

        Args:
            sync_id: UUID of the sync
            last_synced_at: Timestamp of last sync
            error_message: Optional error message

        Returns:
            Updated sync object or None
        """
        query = select(CalendarSync).where(CalendarSync.id == sync_id)
        result = await self.db.execute(query)
        sync = result.scalar_one_or_none()

        if not sync:
            return None

        sync.last_synced_at = last_synced_at
        if error_message:
            sync.sync_errors = {"error": error_message, "timestamp": datetime.utcnow().isoformat()}

        await self.db.flush()
        await self.db.refresh(sync)

        return sync
