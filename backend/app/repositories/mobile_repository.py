"""
Mobile App Foundation Repository
Sprint 18: Mobile App Foundation

Repository layer for mobile app features including device management,
push notifications, deep linking, offline sync, and analytics.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import secrets

from app.models.mobile import (
    MobileDevice, MobileSession, PushNotification, DeepLink, DeepLinkClick,
    OfflineSyncQueue, AppVersion, MobileFeatureFlag, MobileFeatureFlagAssignment,
    MobileAnalyticsEvent, MobileScreenView,
    SyncStatus, FeatureFlagStatus
)
from app.schemas.mobile import (
    MobileDeviceRegister, MobileDeviceUpdate,
    PushNotificationCreate, DeepLinkCreate,
    OfflineSyncQueueCreate, AppVersionCreate,
    MobileFeatureFlagCreate
)


class MobileRepository:
    """Repository for mobile app operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Device Management
    # ========================================================================

    async def register_device(
        self,
        device_data: MobileDeviceRegister,
        user_id: UUID
    ) -> MobileDevice:
        """Register or update a mobile device"""
        # Check if device already exists
        stmt = select(MobileDevice).where(
            and_(
                MobileDevice.user_id == user_id,
                MobileDevice.device_id == device_data.device_id
            )
        )
        result = await self.db.execute(stmt)
        existing_device = result.scalar_one_or_none()

        if existing_device:
            # Update existing device
            for key, value in device_data.dict(exclude_unset=True).items():
                setattr(existing_device, key, value)
            existing_device.last_active_at = datetime.utcnow()
            existing_device.updated_at = datetime.utcnow()
            return existing_device
        else:
            # Create new device
            device = MobileDevice(
                user_id=user_id,
                **device_data.dict()
            )
            self.db.add(device)
            await self.db.flush()
            return device

    async def get_device_by_id(
        self,
        device_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[MobileDevice]:
        """Get device by ID"""
        stmt = select(MobileDevice).where(MobileDevice.id == device_id)
        if user_id:
            stmt = stmt.where(MobileDevice.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_devices(
        self,
        user_id: UUID,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[MobileDevice], int]:
        """Get all devices for a user"""
        stmt = select(MobileDevice).where(MobileDevice.user_id == user_id)
        if active_only:
            stmt = stmt.where(MobileDevice.is_active == True)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar()

        stmt = stmt.offset(skip).limit(limit).order_by(MobileDevice.last_active_at.desc())
        result = await self.db.execute(stmt)
        devices = result.scalars().all()

        return list(devices), total

    async def update_device(
        self,
        device_id: UUID,
        user_id: UUID,
        device_update: MobileDeviceUpdate
    ) -> Optional[MobileDevice]:
        """Update device settings"""
        device = await self.get_device_by_id(device_id, user_id)
        if not device:
            return None

        for key, value in device_update.dict(exclude_unset=True).items():
            setattr(device, key, value)

        device.updated_at = datetime.utcnow()
        return device

    async def deactivate_device(
        self,
        device_id: UUID,
        user_id: UUID
    ) -> bool:
        """Deactivate a device"""
        stmt = update(MobileDevice).where(
            and_(
                MobileDevice.id == device_id,
                MobileDevice.user_id == user_id
            )
        ).values(is_active=False, updated_at=datetime.utcnow())

        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def update_device_activity(
        self,
        device_id: UUID,
        ip_address: Optional[str] = None
    ) -> None:
        """Update device last activity timestamp"""
        stmt = update(MobileDevice).where(
            MobileDevice.id == device_id
        ).values(
            last_active_at=datetime.utcnow(),
            ip_address=ip_address or MobileDevice.ip_address
        )
        await self.db.execute(stmt)

    # ========================================================================
    # Session Management
    # ========================================================================

    async def start_session(
        self,
        user_id: UUID,
        device_id: UUID,
        app_version: Optional[str] = None,
        network_type: Optional[str] = None
    ) -> MobileSession:
        """Start a new mobile session"""
        session_id = secrets.token_urlsafe(32)

        session = MobileSession(
            user_id=user_id,
            device_id=device_id,
            session_id=session_id,
            app_version=app_version,
            network_type=network_type
        )

        self.db.add(session)
        await self.db.flush()

        # Update device activity
        await self.update_device_activity(device_id)

        return session

    async def get_session_by_id(
        self,
        session_id: UUID
    ) -> Optional[MobileSession]:
        """Get session by ID"""
        stmt = select(MobileSession).where(MobileSession.id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_session(
        self,
        device_id: UUID
    ) -> Optional[MobileSession]:
        """Get active session for device"""
        stmt = select(MobileSession).where(
            and_(
                MobileSession.device_id == device_id,
                MobileSession.is_active == True
            )
        ).order_by(MobileSession.started_at.desc())

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def end_session(
        self,
        session_id: UUID,
        foreground_time: int,
        background_time: int,
        exit_screen: Optional[str] = None
    ) -> Optional[MobileSession]:
        """End a mobile session"""
        session = await self.get_session_by_id(session_id)
        if not session:
            return None

        session.ended_at = datetime.utcnow()
        session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())
        session.is_active = False
        session.foreground_time = foreground_time
        session.background_time = background_time
        session.exit_screen = exit_screen

        return session

    # ========================================================================
    # Push Notifications
    # ========================================================================

    async def create_push_notification(
        self,
        notification_data: PushNotificationCreate,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None
    ) -> PushNotification:
        """Create a push notification"""
        notification = PushNotification(
            **notification_data.dict(),
            entity_type=entity_type,
            entity_id=entity_id
        )

        self.db.add(notification)
        await self.db.flush()
        return notification

    async def get_notification_by_id(
        self,
        notification_id: UUID
    ) -> Optional[PushNotification]:
        """Get notification by ID"""
        stmt = select(PushNotification).where(PushNotification.id == notification_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_notifications(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[PushNotification], int]:
        """Get notifications for user"""
        stmt = select(PushNotification).where(PushNotification.user_id == user_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar()

        stmt = stmt.offset(skip).limit(limit).order_by(PushNotification.created_at.desc())
        result = await self.db.execute(stmt)
        notifications = result.scalars().all()

        return list(notifications), total

    async def get_pending_notifications(
        self,
        limit: int = 100
    ) -> List[PushNotification]:
        """Get pending notifications to send"""
        stmt = select(PushNotification).where(
            and_(
                PushNotification.status == "pending",
                or_(
                    PushNotification.scheduled_at.is_(None),
                    PushNotification.scheduled_at <= datetime.utcnow()
                )
            )
        ).limit(limit).order_by(PushNotification.created_at.asc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_notification_status(
        self,
        notification_id: UUID,
        status: str,
        provider: Optional[str] = None,
        provider_message_id: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Update notification delivery status"""
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }

        if status == "sent":
            update_data["sent_at"] = datetime.utcnow()
        elif status == "delivered":
            update_data["delivered_at"] = datetime.utcnow()
        elif status == "opened":
            update_data["opened_at"] = datetime.utcnow()

        if provider:
            update_data["provider"] = provider
        if provider_message_id:
            update_data["provider_message_id"] = provider_message_id
        if error_code:
            update_data["error_code"] = error_code
        if error_message:
            update_data["error_message"] = error_message

        stmt = update(PushNotification).where(
            PushNotification.id == notification_id
        ).values(**update_data)

        await self.db.execute(stmt)

    async def get_notification_stats(
        self,
        user_id: Optional[UUID] = None,
        campaign_id: Optional[str] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get push notification statistics"""
        since_date = datetime.utcnow() - timedelta(days=days_back)

        stmt = select(PushNotification).where(
            PushNotification.created_at >= since_date
        )

        if user_id:
            stmt = stmt.where(PushNotification.user_id == user_id)
        if campaign_id:
            stmt = stmt.where(PushNotification.campaign_id == campaign_id)

        result = await self.db.execute(stmt)
        notifications = result.scalars().all()

        total_sent = sum(1 for n in notifications if n.status in ["sent", "delivered", "opened"])
        delivered_count = sum(1 for n in notifications if n.status in ["delivered", "opened"])
        opened_count = sum(1 for n in notifications if n.status == "opened")
        failed_count = sum(1 for n in notifications if n.status == "failed")

        delivery_rate = (delivered_count / total_sent * 100) if total_sent > 0 else 0
        open_rate = (opened_count / delivered_count * 100) if delivered_count > 0 else 0

        return {
            "total_sent": total_sent,
            "delivered_count": delivered_count,
            "opened_count": opened_count,
            "failed_count": failed_count,
            "delivery_rate": delivery_rate,
            "open_rate": open_rate
        }

    # ========================================================================
    # Deep Links
    # ========================================================================

    async def create_deep_link(
        self,
        deep_link_data: DeepLinkCreate,
        created_by: UUID
    ) -> DeepLink:
        """Create a deep link"""
        # Generate unique link code
        link_code = secrets.token_urlsafe(8)

        # Construct full deep link URL
        link_url = f"celebratech://link/{link_code}"

        deep_link = DeepLink(
            link_code=link_code,
            link_url=link_url,
            created_by=created_by,
            **deep_link_data.dict()
        )

        self.db.add(deep_link)
        await self.db.flush()
        return deep_link

    async def get_deep_link_by_id(
        self,
        deep_link_id: UUID
    ) -> Optional[DeepLink]:
        """Get deep link by ID"""
        stmt = select(DeepLink).where(DeepLink.id == deep_link_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_deep_link_by_code(
        self,
        link_code: str
    ) -> Optional[DeepLink]:
        """Get deep link by code"""
        stmt = select(DeepLink).where(DeepLink.link_code == link_code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def track_deep_link_click(
        self,
        deep_link_id: UUID,
        user_id: Optional[UUID] = None,
        device_id: Optional[UUID] = None,
        platform: Optional[str] = None,
        app_installed: bool = False,
        ip_address: Optional[str] = None
    ) -> DeepLinkClick:
        """Track a deep link click"""
        click = DeepLinkClick(
            deep_link_id=deep_link_id,
            user_id=user_id,
            device_id=device_id,
            platform=platform,
            app_installed=app_installed,
            ip_address=ip_address
        )

        self.db.add(click)

        # Increment click count on deep link
        stmt = update(DeepLink).where(
            DeepLink.id == deep_link_id
        ).values(click_count=DeepLink.click_count + 1)
        await self.db.execute(stmt)

        await self.db.flush()
        return click

    async def get_deep_link_analytics(
        self,
        deep_link_id: UUID
    ) -> Dict[str, Any]:
        """Get analytics for a deep link"""
        deep_link = await self.get_deep_link_by_id(deep_link_id)
        if not deep_link:
            return {}

        # Get all clicks
        stmt = select(DeepLinkClick).where(DeepLinkClick.deep_link_id == deep_link_id)
        result = await self.db.execute(stmt)
        clicks = result.scalars().all()

        total_clicks = len(clicks)
        install_count = sum(1 for c in clicks if not c.app_installed and c.action_taken == "installed")
        open_count = sum(1 for c in clicks if c.action_taken == "opened")
        conversion_count = sum(1 for c in clicks if c.converted)

        install_rate = (install_count / total_clicks * 100) if total_clicks > 0 else 0
        conversion_rate = (conversion_count / total_clicks * 100) if total_clicks > 0 else 0

        # Platform breakdown
        platform_counts = {}
        for click in clicks:
            if click.platform:
                platform_counts[click.platform] = platform_counts.get(click.platform, 0) + 1

        return {
            "link_code": deep_link.link_code,
            "total_clicks": total_clicks,
            "install_count": install_count,
            "open_count": open_count,
            "conversion_count": conversion_count,
            "install_rate": install_rate,
            "conversion_rate": conversion_rate,
            "top_platforms": platform_counts,
            "top_countries": {}  # Would need geolocation data
        }

    # ========================================================================
    # Offline Sync
    # ========================================================================

    async def add_to_sync_queue(
        self,
        user_id: UUID,
        device_id: UUID,
        operation_type: str,
        entity_type: str,
        entity_id: Optional[UUID],
        operation_data: Dict[str, Any],
        priority: int = 0
    ) -> OfflineSyncQueue:
        """Add operation to offline sync queue"""
        sync_item = OfflineSyncQueue(
            user_id=user_id,
            device_id=device_id,
            operation_type=operation_type,
            entity_type=entity_type,
            entity_id=entity_id,
            operation_data=operation_data,
            priority=priority
        )

        self.db.add(sync_item)
        await self.db.flush()
        return sync_item

    async def get_pending_sync_items(
        self,
        user_id: UUID,
        device_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[OfflineSyncQueue]:
        """Get pending sync items"""
        stmt = select(OfflineSyncQueue).where(
            and_(
                OfflineSyncQueue.user_id == user_id,
                OfflineSyncQueue.status == SyncStatus.PENDING
            )
        )

        if device_id:
            stmt = stmt.where(OfflineSyncQueue.device_id == device_id)

        stmt = stmt.order_by(
            OfflineSyncQueue.priority.desc(),
            OfflineSyncQueue.created_at.asc()
        ).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_sync_status(
        self,
        sync_item_id: UUID,
        status: SyncStatus,
        error_message: Optional[str] = None
    ) -> None:
        """Update sync item status"""
        update_data = {
            "status": status,
            "sync_attempts": OfflineSyncQueue.sync_attempts + 1,
            "last_sync_attempt_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        if status == SyncStatus.SYNCED:
            update_data["synced_at"] = datetime.utcnow()

        if error_message:
            update_data["error_message"] = error_message

        stmt = update(OfflineSyncQueue).where(
            OfflineSyncQueue.id == sync_item_id
        ).values(**update_data)

        await self.db.execute(stmt)

    # ========================================================================
    # App Versions
    # ========================================================================

    async def create_app_version(
        self,
        version_data: AppVersionCreate,
        created_by: UUID
    ) -> AppVersion:
        """Create a new app version"""
        app_version = AppVersion(
            created_by=created_by,
            **version_data.dict()
        )

        self.db.add(app_version)
        await self.db.flush()
        return app_version

    async def get_current_version(
        self,
        platform: str,
        environment: str = "production"
    ) -> Optional[AppVersion]:
        """Get current app version for platform"""
        stmt = select(AppVersion).where(
            and_(
                AppVersion.platform == platform,
                AppVersion.environment == environment,
                AppVersion.is_current == True
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def check_version_update(
        self,
        platform: str,
        current_version: str,
        build_number: str
    ) -> Optional[AppVersion]:
        """Check if update is available"""
        current = await self.get_current_version(platform)

        if not current:
            return None

        # Simple version comparison (should use proper semver)
        if current.version != current_version or current.build_number != build_number:
            return current

        return None

    # ========================================================================
    # Feature Flags
    # ========================================================================

    async def create_feature_flag(
        self,
        flag_data: MobileFeatureFlagCreate,
        created_by: UUID
    ) -> MobileFeatureFlag:
        """Create a feature flag"""
        feature_flag = MobileFeatureFlag(
            created_by=created_by,
            **flag_data.dict()
        )

        self.db.add(feature_flag)
        await self.db.flush()
        return feature_flag

    async def get_feature_flags(
        self,
        platform: str,
        app_version: str,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get feature flags for user/device"""
        stmt = select(MobileFeatureFlag).where(
            and_(
                MobileFeatureFlag.status.in_([FeatureFlagStatus.ENABLED, FeatureFlagStatus.ROLLOUT]),
                or_(
                    MobileFeatureFlag.platforms.is_(None),
                    MobileFeatureFlag.platforms.contains([platform])
                )
            )
        )

        result = await self.db.execute(stmt)
        flags = result.scalars().all()

        features = {}
        for flag in flags:
            # Simple rollout logic (should be more sophisticated)
            is_enabled = flag.status == FeatureFlagStatus.ENABLED

            if flag.status == FeatureFlagStatus.ROLLOUT:
                # Use user_id hash for consistent assignment
                if user_id:
                    hash_val = hash(str(user_id) + flag.feature_key) % 100
                    is_enabled = hash_val < flag.rollout_percentage

            features[flag.feature_key] = {
                "enabled": is_enabled,
                "config": flag.config or {},
                "variant": None
            }

        return features

    # ========================================================================
    # Mobile Analytics
    # ========================================================================

    async def track_analytics_event(
        self,
        user_id: UUID,
        device_id: UUID,
        session_id: Optional[UUID],
        event_name: str,
        event_category: Optional[str] = None,
        event_properties: Optional[Dict[str, Any]] = None,
        event_value: Optional[float] = None,
        screen_name: Optional[str] = None
    ) -> MobileAnalyticsEvent:
        """Track a mobile analytics event"""
        event = MobileAnalyticsEvent(
            user_id=user_id,
            device_id=device_id,
            session_id=session_id,
            event_name=event_name,
            event_category=event_category,
            event_properties=event_properties,
            event_value=event_value,
            screen_name=screen_name
        )

        self.db.add(event)
        await self.db.flush()
        return event

    async def track_screen_view(
        self,
        user_id: UUID,
        device_id: UUID,
        session_id: Optional[UUID],
        screen_name: str,
        screen_class: Optional[str] = None,
        previous_screen: Optional[str] = None
    ) -> MobileScreenView:
        """Track a screen view"""
        screen_view = MobileScreenView(
            user_id=user_id,
            device_id=device_id,
            session_id=session_id,
            screen_name=screen_name,
            screen_class=screen_class,
            previous_screen=previous_screen
        )

        self.db.add(screen_view)
        await self.db.flush()

        # Update session screen view count
        if session_id:
            stmt = update(MobileSession).where(
                MobileSession.id == session_id
            ).values(screen_views=MobileSession.screen_views + 1)
            await self.db.execute(stmt)

        return screen_view

    async def end_screen_view(
        self,
        screen_view_id: UUID,
        scroll_depth: Optional[float] = None,
        interactions: int = 0
    ) -> None:
        """End a screen view and record metrics"""
        screen_view = await self.db.get(MobileScreenView, screen_view_id)
        if not screen_view:
            return

        screen_view.exit_at = datetime.utcnow()
        screen_view.duration_seconds = int((screen_view.exit_at - screen_view.viewed_at).total_seconds())
        screen_view.scroll_depth = scroll_depth
        screen_view.interactions = interactions

    async def get_event_stats(
        self,
        event_name: str,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """Get statistics for an analytics event"""
        since_date = datetime.utcnow() - timedelta(days=days_back)

        stmt = select(MobileAnalyticsEvent).where(
            and_(
                MobileAnalyticsEvent.event_name == event_name,
                MobileAnalyticsEvent.occurred_at >= since_date
            )
        )

        result = await self.db.execute(stmt)
        events = result.scalars().all()

        total_count = len(events)
        unique_users = len(set(e.user_id for e in events if e.user_id))

        event_values = [e.event_value for e in events if e.event_value is not None]
        average_value = sum(event_values) / len(event_values) if event_values else None

        return {
            "event_name": event_name,
            "total_count": total_count,
            "unique_users": unique_users,
            "average_value": average_value,
            "top_screens": []
        }
