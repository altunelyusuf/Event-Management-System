"""
Mobile App Foundation Service
Sprint 18: Mobile App Foundation

Service layer for mobile app features including device management,
push notifications, deep linking, offline sync, and analytics.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
import logging

from app.repositories.mobile_repository import MobileRepository
from app.models.user import User
from app.schemas.mobile import (
    MobileDeviceRegister, MobileDeviceUpdate, MobileDeviceResponse,
    PushNotificationCreate, PushNotificationResponse,
    DeepLinkCreate, DeepLinkResponse,
    OfflineSyncQueueCreate, OfflineSyncQueueResponse,
    AppVersionCreate, AppVersionResponse, AppVersionCheckRequest, AppVersionCheckResponse,
    MobileFeatureFlagCreate, MobileFeatureFlagResponse,
    MobileSessionStart, MobileSessionResponse,
    MobileAnalyticsEventCreate, MobileScreenViewCreate
)

logger = logging.getLogger(__name__)


class MobileService:
    """Service for mobile app operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.mobile_repo = MobileRepository(db)

    # ========================================================================
    # Device Management
    # ========================================================================

    async def register_device(
        self,
        device_data: MobileDeviceRegister,
        current_user: User
    ) -> MobileDeviceResponse:
        """
        Register or update a mobile device.

        If device already exists for user, updates it.
        Otherwise creates a new device registration.
        """
        device = await self.mobile_repo.register_device(device_data, current_user.id)
        await self.db.commit()
        await self.db.refresh(device)

        return MobileDeviceResponse.from_orm(device)

    async def get_device(
        self,
        device_id: UUID,
        current_user: User
    ) -> MobileDeviceResponse:
        """Get device by ID"""
        device = await self.mobile_repo.get_device_by_id(device_id, current_user.id)

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        return MobileDeviceResponse.from_orm(device)

    async def get_user_devices(
        self,
        current_user: User,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[MobileDeviceResponse], int]:
        """Get all devices for current user"""
        devices, total = await self.mobile_repo.get_user_devices(
            current_user.id,
            active_only=active_only,
            skip=skip,
            limit=limit
        )

        device_responses = [MobileDeviceResponse.from_orm(d) for d in devices]
        return device_responses, total

    async def update_device(
        self,
        device_id: UUID,
        device_update: MobileDeviceUpdate,
        current_user: User
    ) -> MobileDeviceResponse:
        """Update device settings"""
        device = await self.mobile_repo.update_device(
            device_id,
            current_user.id,
            device_update
        )

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        await self.db.commit()
        await self.db.refresh(device)

        return MobileDeviceResponse.from_orm(device)

    async def deactivate_device(
        self,
        device_id: UUID,
        current_user: User
    ) -> bool:
        """Deactivate a device"""
        success = await self.mobile_repo.deactivate_device(device_id, current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        await self.db.commit()
        return True

    # ========================================================================
    # Session Management
    # ========================================================================

    async def start_session(
        self,
        session_data: MobileSessionStart,
        current_user: User
    ) -> MobileSessionResponse:
        """Start a new mobile session"""
        # Verify device belongs to user
        device = await self.mobile_repo.get_device_by_id(
            session_data.device_id,
            current_user.id
        )

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        # End any active sessions for this device
        active_session = await self.mobile_repo.get_active_session(session_data.device_id)
        if active_session:
            await self.mobile_repo.end_session(
                active_session.id,
                foreground_time=0,
                background_time=0
            )

        # Create new session
        session = await self.mobile_repo.start_session(
            current_user.id,
            session_data.device_id,
            session_data.app_version,
            session_data.network_type
        )

        await self.db.commit()
        await self.db.refresh(session)

        return MobileSessionResponse.from_orm(session)

    async def end_session(
        self,
        session_id: UUID,
        foreground_time: int,
        background_time: int,
        exit_screen: Optional[str],
        current_user: User
    ) -> MobileSessionResponse:
        """End a mobile session"""
        session = await self.mobile_repo.end_session(
            session_id,
            foreground_time,
            background_time,
            exit_screen
        )

        if not session or session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        await self.db.commit()
        await self.db.refresh(session)

        return MobileSessionResponse.from_orm(session)

    # ========================================================================
    # Push Notifications
    # ========================================================================

    async def send_push_notification(
        self,
        notification_data: PushNotificationCreate,
        current_user: User,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None
    ) -> PushNotificationResponse:
        """
        Create and queue a push notification for delivery.

        Note: Actual delivery to FCM/APNS/HMS is handled by background workers.
        This method just creates the notification record.
        """
        notification = await self.mobile_repo.create_push_notification(
            notification_data,
            entity_type=entity_type,
            entity_id=entity_id
        )

        await self.db.commit()
        await self.db.refresh(notification)

        # In production, trigger background task to send via FCM/APNS/HMS
        # await send_push_notification_task.delay(notification.id)

        return PushNotificationResponse.from_orm(notification)

    async def get_user_notifications(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[PushNotificationResponse], int]:
        """Get notifications for current user"""
        notifications, total = await self.mobile_repo.get_user_notifications(
            current_user.id,
            skip=skip,
            limit=limit
        )

        notification_responses = [
            PushNotificationResponse.from_orm(n) for n in notifications
        ]

        return notification_responses, total

    async def mark_notification_opened(
        self,
        notification_id: UUID,
        current_user: User
    ) -> PushNotificationResponse:
        """Mark a notification as opened"""
        notification = await self.mobile_repo.get_notification_by_id(notification_id)

        if not notification or notification.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )

        await self.mobile_repo.update_notification_status(
            notification_id,
            status="opened"
        )

        await self.db.commit()
        await self.db.refresh(notification)

        return PushNotificationResponse.from_orm(notification)

    async def get_notification_stats(
        self,
        current_user: User,
        campaign_id: Optional[str] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get push notification statistics"""
        stats = await self.mobile_repo.get_notification_stats(
            user_id=current_user.id,
            campaign_id=campaign_id,
            days_back=days_back
        )

        return stats

    # ========================================================================
    # Deep Links
    # ========================================================================

    async def create_deep_link(
        self,
        deep_link_data: DeepLinkCreate,
        current_user: User
    ) -> DeepLinkResponse:
        """Create a deep link for mobile navigation"""
        deep_link = await self.mobile_repo.create_deep_link(
            deep_link_data,
            created_by=current_user.id
        )

        await self.db.commit()
        await self.db.refresh(deep_link)

        return DeepLinkResponse.from_orm(deep_link)

    async def get_deep_link(
        self,
        link_code: str
    ) -> DeepLinkResponse:
        """Get deep link by code (public access)"""
        deep_link = await self.mobile_repo.get_deep_link_by_code(link_code)

        if not deep_link or not deep_link.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deep link not found or expired"
            )

        # Check expiration
        if deep_link.expires_at and deep_link.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Deep link has expired"
            )

        return DeepLinkResponse.from_orm(deep_link)

    async def track_deep_link_click(
        self,
        link_code: str,
        platform: Optional[str] = None,
        app_installed: bool = False,
        current_user: Optional[User] = None,
        device_id: Optional[UUID] = None,
        ip_address: Optional[str] = None
    ) -> DeepLinkResponse:
        """Track a deep link click"""
        deep_link = await self.mobile_repo.get_deep_link_by_code(link_code)

        if not deep_link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deep link not found"
            )

        # Track the click
        await self.mobile_repo.track_deep_link_click(
            deep_link.id,
            user_id=current_user.id if current_user else None,
            device_id=device_id,
            platform=platform,
            app_installed=app_installed,
            ip_address=ip_address
        )

        await self.db.commit()
        await self.db.refresh(deep_link)

        return DeepLinkResponse.from_orm(deep_link)

    async def get_deep_link_analytics(
        self,
        deep_link_id: UUID,
        current_user: User
    ) -> Dict[str, Any]:
        """Get analytics for a deep link"""
        deep_link = await self.mobile_repo.get_deep_link_by_id(deep_link_id)

        if not deep_link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deep link not found"
            )

        # Verify ownership
        if deep_link.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view analytics for this link"
            )

        analytics = await self.mobile_repo.get_deep_link_analytics(deep_link_id)
        return analytics

    # ========================================================================
    # Offline Sync
    # ========================================================================

    async def get_sync_status(
        self,
        device_id: UUID,
        current_user: User
    ) -> Dict[str, Any]:
        """Get offline sync status for device"""
        # Verify device belongs to user
        device = await self.mobile_repo.get_device_by_id(device_id, current_user.id)

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        pending_items = await self.mobile_repo.get_pending_sync_items(
            current_user.id,
            device_id=device_id
        )

        pending_count = len([i for i in pending_items if i.status == "pending"])
        syncing_count = len([i for i in pending_items if i.status == "syncing"])
        failed_count = len([i for i in pending_items if i.status == "failed"])
        conflict_count = len([i for i in pending_items if i.status == "conflict"])

        return {
            "pending_count": pending_count,
            "syncing_count": syncing_count,
            "failed_count": failed_count,
            "conflict_count": conflict_count,
            "pending_operations": [
                OfflineSyncQueueResponse.from_orm(i) for i in pending_items[:10]
            ]
        }

    async def process_offline_sync(
        self,
        sync_data: OfflineSyncQueueCreate,
        current_user: User
    ) -> OfflineSyncQueueResponse:
        """
        Process an offline sync operation.

        In production, this would apply the operation and handle conflicts.
        For now, just queues it for processing.
        """
        # Verify device belongs to user
        device = await self.mobile_repo.get_device_by_id(
            sync_data.device_id,
            current_user.id
        )

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        sync_item = await self.mobile_repo.add_to_sync_queue(
            user_id=current_user.id,
            device_id=sync_data.device_id,
            operation_type=sync_data.operation_type,
            entity_type=sync_data.entity_type,
            entity_id=sync_data.entity_id,
            operation_data=sync_data.operation_data,
            priority=sync_data.priority
        )

        await self.db.commit()
        await self.db.refresh(sync_item)

        # In production, trigger background sync processor
        # await process_sync_queue.delay(sync_item.id)

        return OfflineSyncQueueResponse.from_orm(sync_item)

    # ========================================================================
    # App Versions
    # ========================================================================

    async def create_app_version(
        self,
        version_data: AppVersionCreate,
        current_user: User
    ) -> AppVersionResponse:
        """Create a new app version (admin only)"""
        # In production, check if user is admin
        # if not current_user.is_admin:
        #     raise HTTPException(status_code=403, detail="Admin access required")

        app_version = await self.mobile_repo.create_app_version(
            version_data,
            created_by=current_user.id
        )

        await self.db.commit()
        await self.db.refresh(app_version)

        return AppVersionResponse.from_orm(app_version)

    async def check_app_version(
        self,
        version_check: AppVersionCheckRequest
    ) -> AppVersionCheckResponse:
        """Check if app update is available"""
        latest_version = await self.mobile_repo.check_version_update(
            version_check.platform,
            version_check.current_version,
            version_check.build_number
        )

        if not latest_version:
            return AppVersionCheckResponse(
                update_available=False,
                force_update=False
            )

        # Determine update URL based on platform
        update_url = None
        if version_check.platform == "ios":
            update_url = latest_version.app_store_url
        elif version_check.platform == "android":
            update_url = latest_version.play_store_url
        elif version_check.platform == "huawei":
            update_url = latest_version.app_gallery_url

        return AppVersionCheckResponse(
            update_available=True,
            force_update=latest_version.force_update,
            latest_version=AppVersionResponse.from_orm(latest_version),
            update_url=update_url,
            release_notes=latest_version.release_notes
        )

    # ========================================================================
    # Feature Flags
    # ========================================================================

    async def create_feature_flag(
        self,
        flag_data: MobileFeatureFlagCreate,
        current_user: User
    ) -> MobileFeatureFlagResponse:
        """Create a feature flag (admin only)"""
        # In production, check if user is admin
        # if not current_user.is_admin:
        #     raise HTTPException(status_code=403, detail="Admin access required")

        feature_flag = await self.mobile_repo.create_feature_flag(
            flag_data,
            created_by=current_user.id
        )

        await self.db.commit()
        await self.db.refresh(feature_flag)

        return MobileFeatureFlagResponse.from_orm(feature_flag)

    async def get_feature_flags(
        self,
        platform: str,
        app_version: str,
        current_user: User
    ) -> Dict[str, Any]:
        """Get feature flags for current user and device"""
        features = await self.mobile_repo.get_feature_flags(
            platform=platform,
            app_version=app_version,
            user_id=current_user.id
        )

        return {
            "features": features,
            "timestamp": datetime.utcnow()
        }

    # ========================================================================
    # Mobile Analytics
    # ========================================================================

    async def track_event(
        self,
        event_data: MobileAnalyticsEventCreate,
        current_user: User
    ) -> Dict[str, str]:
        """Track a mobile analytics event"""
        # Verify device belongs to user
        device = await self.mobile_repo.get_device_by_id(
            event_data.device_id,
            current_user.id
        )

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        await self.mobile_repo.track_analytics_event(
            user_id=current_user.id,
            device_id=event_data.device_id,
            session_id=event_data.session_id,
            event_name=event_data.event_name,
            event_category=event_data.event_category,
            event_properties=event_data.event_properties,
            event_value=event_data.event_value,
            screen_name=event_data.screen_name
        )

        await self.db.commit()

        return {"status": "success"}

    async def track_screen_view(
        self,
        screen_data: MobileScreenViewCreate,
        current_user: User
    ) -> UUID:
        """Track a screen view"""
        # Verify device belongs to user
        device = await self.mobile_repo.get_device_by_id(
            screen_data.device_id,
            current_user.id
        )

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        screen_view = await self.mobile_repo.track_screen_view(
            user_id=current_user.id,
            device_id=screen_data.device_id,
            session_id=screen_data.session_id,
            screen_name=screen_data.screen_name,
            screen_class=screen_data.screen_class,
            previous_screen=screen_data.previous_screen
        )

        await self.db.commit()

        return screen_view.id

    async def get_event_stats(
        self,
        event_name: str,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """Get statistics for an analytics event"""
        stats = await self.mobile_repo.get_event_stats(event_name, days_back)
        return stats
