"""
CelebraTech Event Management System - Notification Service
Sprint 8: Notification System
FR-008: Multi-channel Notification System
Business logic for notification operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from uuid import UUID

from app.repositories.notification_repository import NotificationRepository
from app.models.user import User, UserRole
from app.schemas.notification import (
    NotificationCreate,
    NotificationBulkCreate,
    NotificationUpdate,
    NotificationPreferenceCreate,
    NotificationPreferenceUpdate,
    NotificationDeviceCreate,
    NotificationDeviceUpdate,
    NotificationFilters,
    MarkNotificationAsRead,
    MarkAllAsRead
)


class NotificationService:
    """Service for notification business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotificationRepository(db)

    # ========================================================================
    # Notification Operations
    # ========================================================================

    async def create_notification(
        self,
        notification_data: NotificationCreate,
        current_user: Optional[User] = None
    ):
        """
        Create a notification

        Business rules:
        - System can create notifications for any user
        - Users can only create notifications for themselves (if allowed)
        """
        # Permission check if user-created
        if current_user and str(notification_data.user_id) != str(current_user.id):
            if current_user.role != UserRole.ADMIN.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Can only create notifications for yourself"
                )

        # Create notification
        notification = await self.repo.create_notification(notification_data)
        await self.db.commit()

        # TODO: Trigger actual delivery (email, push, SMS)
        # This would integrate with SendGrid, Firebase, Twilio, etc.

        return notification

    async def create_bulk_notifications(
        self,
        bulk_data: NotificationBulkCreate,
        current_user: User
    ):
        """
        Create notifications for multiple users (admin only)

        Business rules:
        - Only admin can create bulk notifications
        """
        if current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        notifications = []
        for user_id in bulk_data.user_ids:
            notification_data = NotificationCreate(
                user_id=user_id,
                type=bulk_data.type,
                title=bulk_data.title,
                message=bulk_data.message,
                priority=bulk_data.priority,
                channels=bulk_data.channels,
                data=bulk_data.data,
                action_url=bulk_data.action_url,
                context_type=bulk_data.context_type,
                context_id=bulk_data.context_id
            )

            notification = await self.repo.create_notification(notification_data)
            notifications.append(notification)

        await self.db.commit()

        return {
            "created_count": len(notifications),
            "notifications": notifications
        }

    async def get_notification(
        self,
        notification_id: UUID,
        current_user: User
    ):
        """Get notification by ID"""
        notification = await self.repo.get_notification_by_id(
            notification_id,
            load_relations=True
        )

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )

        # Check if user owns notification or is admin
        if str(notification.user_id) != str(current_user.id):
            if current_user.role != UserRole.ADMIN.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view this notification"
                )

        return notification

    async def mark_as_read(
        self,
        notification_id: UUID,
        current_user: User
    ):
        """Mark notification as read"""
        notification = await self.repo.get_notification_by_id(notification_id)
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )

        # Check if user owns notification
        if str(notification.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to mark this notification as read"
            )

        # Mark as read
        notification = await self.repo.mark_as_read(notification_id)
        await self.db.commit()

        return notification

    async def mark_all_as_read(
        self,
        mark_data: MarkAllAsRead,
        current_user: User
    ):
        """Mark all notifications as read"""
        count = await self.repo.mark_all_as_read(
            current_user.id,
            mark_data.before_date
        )

        await self.db.commit()

        return {"marked_count": count}

    async def delete_notification(
        self,
        notification_id: UUID,
        current_user: User
    ):
        """Delete notification"""
        notification = await self.repo.get_notification_by_id(notification_id)
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )

        # Check if user owns notification or is admin
        if str(notification.user_id) != str(current_user.id):
            if current_user.role != UserRole.ADMIN.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to delete this notification"
                )

        # Delete
        success = await self.repo.delete_notification(notification_id)
        await self.db.commit()

        return success

    async def list_notifications(
        self,
        current_user: User,
        filters: Optional[NotificationFilters] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List, int]:
        """List user's notifications"""
        return await self.repo.list_user_notifications(
            current_user.id,
            filters,
            page,
            page_size
        )

    async def get_unread_count(self, current_user: User) -> int:
        """Get unread notification count"""
        return await self.repo.get_unread_count(current_user.id)

    async def get_stats(self, current_user: User) -> Dict:
        """Get notification statistics"""
        return await self.repo.get_notification_stats(current_user.id)

    # ========================================================================
    # Notification Preference Operations
    # ========================================================================

    async def get_preferences(self, current_user: User):
        """Get user's notification preferences"""
        return await self.repo.get_user_preferences(current_user.id)

    async def create_preference(
        self,
        preference_data: NotificationPreferenceCreate,
        current_user: User
    ):
        """Create notification preference"""
        # Check if preference already exists
        existing = await self.repo.get_user_preference(
            current_user.id,
            preference_data.notification_type
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Preference already exists for this notification type"
            )

        # Create preference
        preference_dict = preference_data.dict()
        preference = await self.repo.create_preference(
            current_user.id,
            **preference_dict
        )

        await self.db.commit()

        return preference

    async def update_preference(
        self,
        preference_id: UUID,
        preference_data: NotificationPreferenceUpdate,
        current_user: User
    ):
        """Update notification preference"""
        # Get preference
        from app.models.notification import NotificationPreference
        preference = await self.db.get(NotificationPreference, preference_id)

        if not preference:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Preference not found"
            )

        # Check if user owns preference
        if str(preference.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this preference"
            )

        # Update
        preference_dict = preference_data.dict(exclude_unset=True)
        updated_preference = await self.repo.update_preference(
            preference_id,
            **preference_dict
        )

        await self.db.commit()

        return updated_preference

    # ========================================================================
    # Notification Device Operations
    # ========================================================================

    async def register_device(
        self,
        device_data: NotificationDeviceCreate,
        current_user: User
    ):
        """Register a device for push notifications"""
        device_dict = device_data.dict()
        device = await self.repo.register_device(
            current_user.id,
            **device_dict
        )

        await self.db.commit()

        return device

    async def get_devices(self, current_user: User):
        """Get user's devices"""
        return await self.repo.get_user_devices(current_user.id)

    async def deactivate_device(
        self,
        device_id: UUID,
        current_user: User
    ):
        """Deactivate a device"""
        from app.models.notification import NotificationDevice
        device = await self.db.get(NotificationDevice, device_id)

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        # Check if user owns device
        if str(device.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to deactivate this device"
            )

        # Deactivate
        success = await self.repo.deactivate_device(device_id)
        await self.db.commit()

        return success

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def send_booking_notification(
        self,
        user_id: UUID,
        notification_type: str,
        booking_id: UUID,
        actor_id: Optional[UUID] = None,
        **template_vars
    ):
        """Helper to send booking-related notification"""
        # Get template
        template = await self.repo.get_template(notification_type)

        if not template:
            # Use default template
            title = f"Booking Update"
            message = f"Your booking has been updated"
        else:
            # Render template with variables
            title = self._render_template(template.in_app_title, template_vars)
            message = self._render_template(template.in_app_message, template_vars)

        # Create notification
        from app.models.notification import NotificationType, NotificationPriority, NotificationChannel

        notification_data = NotificationCreate(
            user_id=user_id,
            type=NotificationType(notification_type),
            title=title,
            message=message,
            priority=NotificationPriority.NORMAL,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            context_type="booking",
            context_id=booking_id,
            actor_id=actor_id
        )

        return await self.create_notification(notification_data)

    def _render_template(self, template: Optional[str], variables: Dict) -> str:
        """Simple template rendering with variable substitution"""
        if not template:
            return ""

        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))

        return result
