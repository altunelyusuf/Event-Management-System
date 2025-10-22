"""
CelebraTech Event Management System - Event Service
Sprint 2: Event Management Core
Business logic for event operations
"""
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, OrganizerRole
from app.models.user import User
from app.schemas.event import EventCreate, EventUpdate
from app.repositories.event_repository import EventRepository


class EventService:
    """Service for event operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.event_repo = EventRepository(db)

    async def create_event(
        self,
        event_data: EventCreate,
        current_user: User
    ) -> Event:
        """
        Create a new event

        Args:
            event_data: Event creation data
            current_user: Current authenticated user

        Returns:
            Created event object
        """
        event = await self.event_repo.create(event_data, str(current_user.id))
        return event

    async def get_event(
        self,
        event_id: str,
        current_user: User,
        load_relationships: bool = False
    ) -> Event:
        """
        Get event by ID with permission check

        Args:
            event_id: Event UUID
            current_user: Current authenticated user
            load_relationships: Whether to load relationships

        Returns:
            Event object

        Raises:
            HTTPException: If event not found or no permission
        """
        event = await self.event_repo.get_by_id(event_id, load_relationships)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        # Check permission
        has_view_permission = await self.event_repo.has_permission(
            event_id, str(current_user.id), "view"
        )
        if not has_view_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to view this event"
            )

        return event

    async def get_user_events(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None
    ) -> Tuple[List[Event], int]:
        """
        Get events for current user

        Args:
            current_user: Current authenticated user
            page: Page number
            page_size: Items per page
            status: Optional status filter

        Returns:
            Tuple of (events list, total count)
        """
        events, total = await self.event_repo.get_by_user(
            str(current_user.id),
            page,
            page_size,
            status
        )
        return events, total

    async def update_event(
        self,
        event_id: str,
        event_data: EventUpdate,
        current_user: User
    ) -> Event:
        """
        Update event

        Args:
            event_id: Event UUID
            event_data: Update data
            current_user: Current authenticated user

        Returns:
            Updated event object

        Raises:
            HTTPException: If event not found or no permission
        """
        # Check edit permission
        has_edit_permission = await self.event_repo.has_permission(
            event_id, str(current_user.id), "edit"
        )
        if not has_edit_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to edit this event"
            )

        event = await self.event_repo.update(event_id, event_data)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        return event

    async def delete_event(
        self,
        event_id: str,
        current_user: User
    ) -> bool:
        """
        Delete event

        Args:
            event_id: Event UUID
            current_user: Current authenticated user

        Returns:
            True if deleted

        Raises:
            HTTPException: If event not found or no permission
        """
        # Only primary organizer can delete
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        if str(event.created_by) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the creator can delete this event"
            )

        await self.event_repo.delete(event_id)
        return True

    async def advance_phase(
        self,
        event_id: str,
        current_user: User
    ) -> Event:
        """
        Advance event to next phase

        Args:
            event_id: Event UUID
            current_user: Current authenticated user

        Returns:
            Updated event

        Raises:
            HTTPException: If event not found or no permission
        """
        has_edit_permission = await self.event_repo.has_permission(
            event_id, str(current_user.id), "edit"
        )
        if not has_edit_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to advance phase"
            )

        event = await self.event_repo.advance_phase(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        return event

    async def invite_organizer(
        self,
        event_id: str,
        user_email: str,
        role: OrganizerRole,
        permissions: dict,
        current_user: User
    ) -> bool:
        """
        Invite organizer to event

        Args:
            event_id: Event UUID
            user_email: Email of user to invite
            role: Organizer role
            permissions: Permission dictionary
            current_user: Current authenticated user

        Returns:
            True if invited

        Raises:
            HTTPException: If no permission
        """
        has_invite_permission = await self.event_repo.has_permission(
            event_id, str(current_user.id), "invite"
        )
        if not has_invite_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to invite organizers"
            )

        # TODO: Look up user by email and send invitation
        # For now, this is a placeholder
        return True

    async def get_event_statistics(
        self,
        event_id: str,
        current_user: User
    ) -> dict:
        """
        Get event statistics

        Args:
            event_id: Event UUID
            current_user: Current authenticated user

        Returns:
            Dictionary with statistics
        """
        event = await self.get_event(event_id, current_user, load_relationships=True)

        total_tasks = await self.event_repo.get_task_count(event_id)
        completed_tasks = await self.event_repo.get_completed_task_count(event_id)

        task_completion_pct = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )

        budget_utilization_pct = (
            (float(event.spent_amount) / float(event.budget_amount) * 100)
            if event.budget_amount and event.budget_amount > 0 else 0
        )

        # Calculate days until event
        from datetime import datetime
        days_until = (event.event_date - datetime.now()).days

        return {
            "total_budget": event.budget_amount,
            "spent_amount": event.spent_amount,
            "budget_utilization_percentage": budget_utilization_pct,
            "guest_count_confirmed": event.guest_count_confirmed,
            "guest_count_estimate": event.guest_count_estimate,
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks,
            "task_completion_percentage": task_completion_pct,
            "days_until_event": days_until,
            "current_phase": event.current_phase,
        }
