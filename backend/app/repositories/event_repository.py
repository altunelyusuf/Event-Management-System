"""
CelebraTech Event Management System - Event Repository
Sprint 2: Event Management Core
Data access layer for event operations
"""
from typing import Optional, List, Tuple
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.models.event import (
    Event,
    EventOrganizer,
    EventPhase,
    EventMilestone,
    EventCulturalElement,
    EventStatus,
    EventPhaseType,
    OrganizerRole,
    OrganizerStatus,
    PhaseStatus
)
from app.models.task import Task
from app.schemas.event import EventCreate, EventUpdate


class EventRepository:
    """Repository for event database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, event_data: EventCreate, created_by: str) -> Event:
        """
        Create a new event with initial phases

        Args:
            event_data: Event creation data
            created_by: UUID of user creating the event

        Returns:
            Created event object
        """
        event = Event(
            type=event_data.type,
            name=event_data.name,
            description=event_data.description,
            event_date=event_data.event_date,
            end_date=event_data.end_date,
            venue_name=event_data.venue_name,
            venue_address=event_data.venue_address,
            guest_count_estimate=event_data.guest_count_estimate,
            budget_amount=event_data.budget_amount,
            budget_currency=event_data.budget_currency,
            cultural_type=event_data.cultural_type,
            visibility=event_data.visibility,
            created_by=created_by,
            status=EventStatus.DRAFT,
            current_phase=EventPhaseType.IDEATION
        )

        self.db.add(event)
        await self.db.flush()  # Flush to get event.id

        # Add creator as primary organizer
        primary_organizer = EventOrganizer(
            event_id=event.id,
            user_id=created_by,
            role=OrganizerRole.PRIMARY,
            status=OrganizerStatus.ACCEPTED,
            accepted_at=datetime.utcnow(),
            permissions={
                "view": True,
                "edit": True,
                "invite": True,
                "book": True,
                "financial": True
            }
        )
        self.db.add(primary_organizer)

        # Initialize all 11 phases
        phases = []
        phase_order = 1
        for phase_type in EventPhaseType:
            phase = EventPhase(
                event_id=event.id,
                phase_name=phase_type,
                phase_order=phase_order,
                status=PhaseStatus.PENDING if phase_order > 1 else PhaseStatus.IN_PROGRESS
            )
            phases.append(phase)
            phase_order += 1

        self.db.add_all(phases)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_by_id(
        self,
        event_id: str,
        load_relationships: bool = False
    ) -> Optional[Event]:
        """
        Get event by ID

        Args:
            event_id: Event UUID
            load_relationships: Whether to eagerly load relationships

        Returns:
            Event object or None
        """
        query = select(Event).where(
            and_(
                Event.id == event_id,
                Event.deleted_at.is_(None)
            )
        )

        if load_relationships:
            query = query.options(
                selectinload(Event.organizers),
                selectinload(Event.phases),
                selectinload(Event.milestones),
                selectinload(Event.cultural_elements)
            )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[EventStatus] = None
    ) -> Tuple[List[Event], int]:
        """
        Get events for a user (as creator or organizer)

        Args:
            user_id: User UUID
            page: Page number (1-indexed)
            page_size: Items per page
            status: Optional status filter

        Returns:
            Tuple of (events list, total count)
        """
        # Build base query
        base_query = select(Event).join(
            EventOrganizer,
            Event.id == EventOrganizer.event_id
        ).where(
            and_(
                EventOrganizer.user_id == user_id,
                EventOrganizer.status == OrganizerStatus.ACCEPTED,
                Event.deleted_at.is_(None)
            )
        )

        if status:
            base_query = base_query.where(Event.status == status)

        # Count query
        count_query = select(func.count()).select_from(
            base_query.subquery()
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Data query with pagination
        data_query = base_query.order_by(desc(Event.created_at)).offset(
            (page - 1) * page_size
        ).limit(page_size)

        result = await self.db.execute(data_query)
        events = result.scalars().all()

        return events, total

    async def update(
        self,
        event_id: str,
        event_data: EventUpdate
    ) -> Optional[Event]:
        """
        Update event

        Args:
            event_id: Event UUID
            event_data: Update data

        Returns:
            Updated event object or None
        """
        event = await self.get_by_id(event_id)
        if not event:
            return None

        update_data = event_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(event, field, value)

        event.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def delete(self, event_id: str) -> bool:
        """
        Soft delete event

        Args:
            event_id: Event UUID

        Returns:
            True if deleted, False otherwise
        """
        event = await self.get_by_id(event_id)
        if not event:
            return False

        event.deleted_at = datetime.utcnow()
        event.status = EventStatus.CANCELLED
        await self.db.commit()
        return True

    async def advance_phase(self, event_id: str) -> Optional[Event]:
        """
        Advance event to next phase

        Args:
            event_id: Event UUID

        Returns:
            Updated event or None
        """
        event = await self.get_by_id(event_id, load_relationships=True)
        if not event:
            return None

        # Get current phase
        current_phase_obj = next(
            (p for p in event.phases if p.phase_name == event.current_phase),
            None
        )

        if current_phase_obj:
            # Mark current phase as completed
            current_phase_obj.status = PhaseStatus.COMPLETED
            current_phase_obj.completed_at = datetime.utcnow()
            current_phase_obj.completion_percentage = 100

        # Get next phase
        next_phase_order = current_phase_obj.phase_order + 1 if current_phase_obj else 1
        next_phase_obj = next(
            (p for p in event.phases if p.phase_order == next_phase_order),
            None
        )

        if next_phase_obj:
            # Advance to next phase
            event.current_phase = next_phase_obj.phase_name
            next_phase_obj.status = PhaseStatus.IN_PROGRESS
            next_phase_obj.started_at = datetime.utcnow()
        else:
            # All phases completed
            event.status = EventStatus.COMPLETED
            event.completed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def update_phase_progress(
        self,
        event_id: str,
        phase_name: EventPhaseType,
        completion_percentage: float,
        notes: Optional[str] = None
    ) -> bool:
        """Update phase progress"""
        result = await self.db.execute(
            select(EventPhase).where(
                and_(
                    EventPhase.event_id == event_id,
                    EventPhase.phase_name == phase_name
                )
            )
        )
        phase = result.scalar_one_or_none()
        if not phase:
            return False

        phase.completion_percentage = completion_percentage
        if notes:
            phase.notes = notes

        if completion_percentage >= 100:
            phase.status = PhaseStatus.COMPLETED
            phase.completed_at = datetime.utcnow()

        await self.db.commit()
        return True

    # Organizer management
    async def add_organizer(
        self,
        event_id: str,
        user_id: str,
        role: OrganizerRole,
        permissions: dict
    ) -> EventOrganizer:
        """Add organizer to event"""
        organizer = EventOrganizer(
            event_id=event_id,
            user_id=user_id,
            role=role,
            permissions=permissions,
            status=OrganizerStatus.PENDING
        )
        self.db.add(organizer)
        await self.db.commit()
        await self.db.refresh(organizer)
        return organizer

    async def update_organizer(
        self,
        event_id: str,
        user_id: str,
        role: Optional[OrganizerRole] = None,
        permissions: Optional[dict] = None
    ) -> Optional[EventOrganizer]:
        """Update organizer"""
        result = await self.db.execute(
            select(EventOrganizer).where(
                and_(
                    EventOrganizer.event_id == event_id,
                    EventOrganizer.user_id == user_id
                )
            )
        )
        organizer = result.scalar_one_or_none()
        if not organizer:
            return None

        if role:
            organizer.role = role
        if permissions:
            organizer.permissions = permissions

        await self.db.commit()
        await self.db.refresh(organizer)
        return organizer

    async def accept_organizer_invite(
        self,
        event_id: str,
        user_id: str
    ) -> bool:
        """Accept organizer invitation"""
        result = await self.db.execute(
            select(EventOrganizer).where(
                and_(
                    EventOrganizer.event_id == event_id,
                    EventOrganizer.user_id == user_id
                )
            )
        )
        organizer = result.scalar_one_or_none()
        if not organizer:
            return False

        organizer.status = OrganizerStatus.ACCEPTED
        organizer.accepted_at = datetime.utcnow()
        await self.db.commit()
        return True

    async def remove_organizer(self, event_id: str, user_id: str) -> bool:
        """Remove organizer from event"""
        result = await self.db.execute(
            select(EventOrganizer).where(
                and_(
                    EventOrganizer.event_id == event_id,
                    EventOrganizer.user_id == user_id,
                    EventOrganizer.role != OrganizerRole.PRIMARY
                )
            )
        )
        organizer = result.scalar_one_or_none()
        if not organizer:
            return False

        organizer.status = OrganizerStatus.REMOVED
        await self.db.commit()
        return True

    # Milestone management
    async def create_milestone(
        self,
        event_id: str,
        title: str,
        description: Optional[str],
        due_date: datetime,
        is_critical: bool,
        order_index: int
    ) -> EventMilestone:
        """Create event milestone"""
        milestone = EventMilestone(
            event_id=event_id,
            title=title,
            description=description,
            due_date=due_date,
            is_critical=is_critical,
            order_index=order_index
        )
        self.db.add(milestone)
        await self.db.commit()
        await self.db.refresh(milestone)
        return milestone

    async def get_milestones(self, event_id: str) -> List[EventMilestone]:
        """Get all milestones for an event"""
        result = await self.db.execute(
            select(EventMilestone).where(
                EventMilestone.event_id == event_id
            ).order_by(EventMilestone.order_index)
        )
        return result.scalars().all()

    async def complete_milestone(
        self,
        milestone_id: str
    ) -> Optional[EventMilestone]:
        """Mark milestone as completed"""
        result = await self.db.execute(
            select(EventMilestone).where(EventMilestone.id == milestone_id)
        )
        milestone = result.scalar_one_or_none()
        if not milestone:
            return None

        milestone.completed_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(milestone)
        return milestone

    # Cultural elements
    async def add_cultural_element(
        self,
        event_id: str,
        element_type: str,
        element_name: str,
        description: Optional[str],
        timing: Optional[str],
        is_required: bool,
        is_included: bool
    ) -> EventCulturalElement:
        """Add cultural element to event"""
        element = EventCulturalElement(
            event_id=event_id,
            element_type=element_type,
            element_name=element_name,
            description=description,
            timing=timing,
            is_required=is_required,
            is_included=is_included
        )
        self.db.add(element)
        await self.db.commit()
        await self.db.refresh(element)
        return element

    async def get_cultural_elements(
        self,
        event_id: str
    ) -> List[EventCulturalElement]:
        """Get all cultural elements for an event"""
        result = await self.db.execute(
            select(EventCulturalElement).where(
                EventCulturalElement.event_id == event_id
            )
        )
        return result.scalars().all()

    # Statistics
    async def get_task_count(self, event_id: str) -> int:
        """Get total task count for event"""
        result = await self.db.execute(
            select(func.count()).select_from(Task).where(
                Task.event_id == event_id
            )
        )
        return result.scalar()

    async def get_completed_task_count(self, event_id: str) -> int:
        """Get completed task count for event"""
        from app.models.task import TaskStatus
        result = await self.db.execute(
            select(func.count()).select_from(Task).where(
                and_(
                    Task.event_id == event_id,
                    Task.status == TaskStatus.COMPLETED
                )
            )
        )
        return result.scalar()

    async def has_permission(
        self,
        event_id: str,
        user_id: str,
        permission: str
    ) -> bool:
        """Check if user has specific permission for event"""
        result = await self.db.execute(
            select(EventOrganizer).where(
                and_(
                    EventOrganizer.event_id == event_id,
                    EventOrganizer.user_id == user_id,
                    EventOrganizer.status == OrganizerStatus.ACCEPTED
                )
            )
        )
        organizer = result.scalar_one_or_none()
        if not organizer:
            return False

        return organizer.permissions.get(permission, False)
