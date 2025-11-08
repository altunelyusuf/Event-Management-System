"""
CelebraTech Event Management System - Notification Repository
Sprint 8: Notification System
FR-008: Multi-channel Notification System
Data access layer for notifications
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, update, delete
from sqlalchemy.orm import joinedload, selectinload
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
from uuid import UUID

from app.models.notification import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationTemplate,
    NotificationDevice,
    NotificationBatch,
    NotificationStatus,
    DeliveryStatus
)
from app.schemas.notification import (
    NotificationCreate,
    NotificationUpdate,
    NotificationFilters
)


class NotificationRepository:
    """Repository for notification data access"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Notification Operations
    # ========================================================================

    async def create_notification(
        self,
        notification_data: NotificationCreate
    ) -> Notification:
        """Create a new notification"""
        notification = Notification(
            user_id=notification_data.user_id,
            type=notification_data.type.value,
            priority=notification_data.priority.value,
            title=notification_data.title,
            message=notification_data.message,
            data=notification_data.data,
            action_url=notification_data.action_url,
            action_text=notification_data.action_text,
            context_type=notification_data.context_type,
            context_id=notification_data.context_id,
            actor_id=notification_data.actor_id,
            channels=[ch.value for ch in notification_data.channels],
            group_key=notification_data.group_key,
            expires_at=notification_data.expires_at,
            status=NotificationStatus.PENDING.value
        )

        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)

        # Create delivery records for each channel
        for channel in notification_data.channels:
            delivery = NotificationDelivery(
                notification_id=notification.id,
                channel=channel.value,
                status=DeliveryStatus.PENDING.value
            )
            self.db.add(delivery)

        await self.db.flush()

        return notification

    async def get_notification_by_id(
        self,
        notification_id: UUID,
        load_relations: bool = False
    ) -> Optional[Notification]:
        """Get notification by ID"""
        query = select(Notification).where(Notification.id == notification_id)

        if load_relations:
            query = query.options(
                joinedload(Notification.user),
                joinedload(Notification.actor),
                selectinload(Notification.deliveries)
            )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_notification(
        self,
        notification_id: UUID,
        notification_data: NotificationUpdate
    ) -> Optional[Notification]:
        """Update notification"""
        notification = await self.get_notification_by_id(notification_id)
        if not notification:
            return None

        update_data = notification_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(notification, field, value)

        notification.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(notification)

        return notification

    async def mark_as_read(
        self,
        notification_id: UUID
    ) -> Optional[Notification]:
        """Mark notification as read"""
        notification = await self.get_notification_by_id(notification_id)
        if not notification:
            return None

        if not notification.read_at:
            notification.status = NotificationStatus.READ.value
            notification.read_at = datetime.utcnow()
            await self.db.flush()

        return notification

    async def mark_all_as_read(
        self,
        user_id: UUID,
        before_date: Optional[datetime] = None
    ) -> int:
        """Mark all notifications as read for user"""
        query = update(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.read_at.is_(None)
            )
        )

        if before_date:
            query = query.where(Notification.created_at <= before_date)

        query = query.values(
            status=NotificationStatus.READ.value,
            read_at=datetime.utcnow()
        )

        result = await self.db.execute(query)
        await self.db.flush()

        return result.rowcount

    async def delete_notification(self, notification_id: UUID) -> bool:
        """Delete notification"""
        result = await self.db.execute(
            delete(Notification).where(Notification.id == notification_id)
        )
        await self.db.flush()
        return result.rowcount > 0

    async def list_user_notifications(
        self,
        user_id: UUID,
        filters: Optional[NotificationFilters] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Notification], int]:
        """List user's notifications with filters"""
        query = select(Notification).where(Notification.user_id == user_id)

        # Apply filters
        if filters:
            if filters.type:
                query = query.where(Notification.type == filters.type)
            if filters.status:
                query = query.where(Notification.status == filters.status.value)
            if filters.priority:
                query = query.where(Notification.priority == filters.priority.value)
            if filters.is_read is not None:
                if filters.is_read:
                    query = query.where(Notification.read_at.isnot(None))
                else:
                    query = query.where(Notification.read_at.is_(None))
            if filters.context_type:
                query = query.where(Notification.context_type == filters.context_type)
            if filters.context_id:
                query = query.where(Notification.context_id == filters.context_id)
            if filters.start_date:
                query = query.where(Notification.created_at >= filters.start_date)
            if filters.end_date:
                query = query.where(Notification.created_at <= filters.end_date)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Sort by created_at descending
        query = query.order_by(desc(Notification.created_at))

        # Pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Load relations
        query = query.options(
            joinedload(Notification.actor),
            selectinload(Notification.deliveries)
        )

        result = await self.db.execute(query)
        notifications = result.scalars().unique().all()

        return list(notifications), total

    async def get_unread_count(self, user_id: UUID) -> int:
        """Get unread notification count"""
        query = select(func.count()).select_from(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
                or_(
                    Notification.expires_at.is_(None),
                    Notification.expires_at > datetime.utcnow()
                )
            )
        )
        result = await self.db.execute(query)
        return result.scalar()

    async def get_notification_stats(self, user_id: UUID) -> Dict:
        """Get notification statistics for user"""
        # Total count
        total_query = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id
        )
        total_result = await self.db.execute(total_query)
        total = total_result.scalar()

        # Unread count
        unread = await self.get_unread_count(user_id)

        # By type
        type_query = select(
            Notification.type,
            func.count(Notification.id)
        ).where(
            Notification.user_id == user_id
        ).group_by(Notification.type)

        type_result = await self.db.execute(type_query)
        by_type = {row[0]: row[1] for row in type_result.all()}

        # By priority
        priority_query = select(
            Notification.priority,
            func.count(Notification.id)
        ).where(
            Notification.user_id == user_id
        ).group_by(Notification.priority)

        priority_result = await self.db.execute(priority_query)
        by_priority = {row[0]: row[1] for row in priority_result.all()}

        return {
            "total_notifications": total,
            "unread_count": unread,
            "read_count": total - unread,
            "by_type": by_type,
            "by_priority": by_priority
        }

    # ========================================================================
    # Notification Preference Operations
    # ========================================================================

    async def get_user_preference(
        self,
        user_id: UUID,
        notification_type: str
    ) -> Optional[NotificationPreference]:
        """Get user preference for notification type"""
        query = select(NotificationPreference).where(
            and_(
                NotificationPreference.user_id == user_id,
                NotificationPreference.notification_type == notification_type
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_preferences(
        self,
        user_id: UUID
    ) -> List[NotificationPreference]:
        """Get all user preferences"""
        query = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id
        ).order_by(NotificationPreference.notification_type)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_preference(
        self,
        user_id: UUID,
        **preference_data
    ) -> NotificationPreference:
        """Create notification preference"""
        preference = NotificationPreference(
            user_id=user_id,
            **preference_data
        )

        self.db.add(preference)
        await self.db.flush()
        await self.db.refresh(preference)

        return preference

    async def update_preference(
        self,
        preference_id: UUID,
        **preference_data
    ) -> Optional[NotificationPreference]:
        """Update notification preference"""
        preference = await self.db.get(NotificationPreference, preference_id)
        if not preference:
            return None

        for key, value in preference_data.items():
            if hasattr(preference, key) and value is not None:
                setattr(preference, key, value)

        preference.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(preference)

        return preference

    # ========================================================================
    # Notification Device Operations
    # ========================================================================

    async def register_device(
        self,
        user_id: UUID,
        **device_data
    ) -> NotificationDevice:
        """Register a device for push notifications"""
        # Check if device token already exists
        existing_query = select(NotificationDevice).where(
            NotificationDevice.device_token == device_data['device_token']
        )
        existing_result = await self.db.execute(existing_query)
        existing_device = existing_result.scalar_one_or_none()

        if existing_device:
            # Update existing device
            existing_device.user_id = user_id
            existing_device.is_active = True
            existing_device.last_used_at = datetime.utcnow()

            for key, value in device_data.items():
                if hasattr(existing_device, key):
                    setattr(existing_device, key, value)

            await self.db.flush()
            await self.db.refresh(existing_device)
            return existing_device

        # Create new device
        device = NotificationDevice(
            user_id=user_id,
            **device_data
        )

        self.db.add(device)
        await self.db.flush()
        await self.db.refresh(device)

        return device

    async def get_user_devices(
        self,
        user_id: UUID,
        active_only: bool = True
    ) -> List[NotificationDevice]:
        """Get user's devices"""
        query = select(NotificationDevice).where(
            NotificationDevice.user_id == user_id
        )

        if active_only:
            query = query.where(NotificationDevice.is_active == True)

        query = query.order_by(desc(NotificationDevice.last_used_at))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def deactivate_device(self, device_id: UUID) -> bool:
        """Deactivate a device"""
        device = await self.db.get(NotificationDevice, device_id)
        if not device:
            return False

        device.is_active = False
        await self.db.flush()

        return True

    # ========================================================================
    # Notification Template Operations
    # ========================================================================

    async def get_template(
        self,
        notification_type: str
    ) -> Optional[NotificationTemplate]:
        """Get notification template"""
        query = select(NotificationTemplate).where(
            and_(
                NotificationTemplate.notification_type == notification_type,
                NotificationTemplate.is_active == True
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_template(
        self,
        **template_data
    ) -> NotificationTemplate:
        """Create notification template"""
        template = NotificationTemplate(**template_data)

        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)

        return template

    async def update_template(
        self,
        template_id: UUID,
        **template_data
    ) -> Optional[NotificationTemplate]:
        """Update notification template"""
        template = await self.db.get(NotificationTemplate, template_id)
        if not template:
            return None

        for key, value in template_data.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)

        template.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(template)

        return template

    # ========================================================================
    # Notification Delivery Operations
    # ========================================================================

    async def update_delivery_status(
        self,
        delivery_id: UUID,
        status: str,
        **delivery_data
    ) -> Optional[NotificationDelivery]:
        """Update delivery status"""
        delivery = await self.db.get(NotificationDelivery, delivery_id)
        if not delivery:
            return None

        delivery.status = status

        # Set timestamps based on status
        if status == DeliveryStatus.SENT.value and not delivery.sent_at:
            delivery.sent_at = datetime.utcnow()
        elif status == DeliveryStatus.DELIVERED.value and not delivery.delivered_at:
            delivery.delivered_at = datetime.utcnow()
        elif status == DeliveryStatus.FAILED.value and not delivery.failed_at:
            delivery.failed_at = datetime.utcnow()
        elif status == DeliveryStatus.BOUNCED.value and not delivery.bounced_at:
            delivery.bounced_at = datetime.utcnow()

        # Update other fields
        for key, value in delivery_data.items():
            if hasattr(delivery, key):
                setattr(delivery, key, value)

        delivery.updated_at = datetime.utcnow()

        await self.db.flush()

        # Update notification status
        await self._update_notification_status(delivery.notification_id)

        return delivery

    async def _update_notification_status(self, notification_id: UUID):
        """Update notification status based on deliveries"""
        notification = await self.get_notification_by_id(notification_id, load_relations=True)
        if not notification:
            return

        # Get all deliveries
        deliveries = notification.deliveries

        if not deliveries:
            return

        # Check if all deliveries are completed
        all_sent = all(d.status == DeliveryStatus.SENT.value for d in deliveries)
        all_delivered = all(d.status == DeliveryStatus.DELIVERED.value for d in deliveries)
        any_failed = any(d.status in [DeliveryStatus.FAILED.value, DeliveryStatus.BOUNCED.value] for d in deliveries)

        if all_delivered:
            notification.status = NotificationStatus.DELIVERED.value
            if not notification.delivered_at:
                notification.delivered_at = datetime.utcnow()
        elif all_sent:
            notification.status = NotificationStatus.SENT.value
            if not notification.sent_at:
                notification.sent_at = datetime.utcnow()
        elif any_failed and len(deliveries) == 1:
            notification.status = NotificationStatus.FAILED.value
            if not notification.failed_at:
                notification.failed_at = datetime.utcnow()

        await self.db.flush()

    # ========================================================================
    # Cleanup Operations
    # ========================================================================

    async def cleanup_expired_notifications(self) -> int:
        """Delete expired notifications"""
        result = await self.db.execute(
            delete(Notification).where(
                and_(
                    Notification.expires_at.isnot(None),
                    Notification.expires_at < datetime.utcnow()
                )
            )
        )

        await self.db.flush()
        return result.rowcount

    async def cleanup_old_read_notifications(self, days: int = 90) -> int:
        """Delete old read notifications"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            delete(Notification).where(
                and_(
                    Notification.read_at.isnot(None),
                    Notification.read_at < cutoff_date
                )
            )
        )

        await self.db.flush()
        return result.rowcount
