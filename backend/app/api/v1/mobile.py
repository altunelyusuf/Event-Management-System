"""
Mobile App Foundation API
Sprint 18: Mobile App Foundation

API endpoints for mobile app features including device management,
push notifications, deep linking, offline sync, and analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.mobile_service import MobileService
from app.schemas.mobile import (
    # Device schemas
    MobileDeviceRegister, MobileDeviceUpdate, MobileDeviceResponse, DeviceListResponse,
    # Session schemas
    MobileSessionStart, MobileSessionEnd, MobileSessionResponse,
    # Push notification schemas
    PushNotificationCreate, PushNotificationResponse, PushNotificationStats,
    # Deep link schemas
    DeepLinkCreate, DeepLinkUpdate, DeepLinkResponse, DeepLinkAnalytics,
    # Offline sync schemas
    OfflineSyncQueueCreate, SyncStatusResponse,
    # App version schemas
    AppVersionCreate, AppVersionUpdate, AppVersionResponse,
    AppVersionCheckRequest, AppVersionCheckResponse,
    # Feature flag schemas
    MobileFeatureFlagCreate, MobileFeatureFlagUpdate, MobileFeatureFlagResponse,
    FeatureFlagsRequest, FeatureFlagsResponse,
    # Analytics schemas
    MobileAnalyticsEventCreate, MobileAnalyticsEventBatch,
    MobileScreenViewCreate, MobileScreenViewEnd,
    AnalyticsEventStats
)

router = APIRouter(prefix="/mobile", tags=["mobile"])


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_mobile_service(db: AsyncSession = Depends(get_db)) -> MobileService:
    """Get mobile service instance"""
    return MobileService(db)


# ============================================================================
# Device Management Endpoints
# ============================================================================

@router.post("/devices", response_model=MobileDeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    device_data: MobileDeviceRegister,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Register or update a mobile device.

    - **device_id**: Unique device identifier
    - **platform**: ios, android, or huawei
    - **device_type**: phone, tablet, watch, or other
    - **push_token**: FCM/APNS/HMS push notification token
    """
    return await mobile_service.register_device(device_data, current_user)


@router.get("/devices", response_model=DeviceListResponse)
async def get_user_devices(
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """Get all devices for the current user"""
    devices, total = await mobile_service.get_user_devices(
        current_user,
        active_only=active_only,
        skip=skip,
        limit=limit
    )

    active_count = len([d for d in devices if d.is_active])

    return DeviceListResponse(
        devices=devices,
        total=total,
        active_count=active_count
    )


@router.get("/devices/{device_id}", response_model=MobileDeviceResponse)
async def get_device(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """Get device by ID"""
    return await mobile_service.get_device(device_id, current_user)


@router.put("/devices/{device_id}", response_model=MobileDeviceResponse)
async def update_device(
    device_id: UUID,
    device_update: MobileDeviceUpdate,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """Update device settings"""
    return await mobile_service.update_device(device_id, device_update, current_user)


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_device(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """Deactivate a device"""
    await mobile_service.deactivate_device(device_id, current_user)


# ============================================================================
# Session Management Endpoints
# ============================================================================

@router.post("/sessions", response_model=MobileSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    session_data: MobileSessionStart,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Start a new mobile session.

    Automatically ends any active sessions for the device.
    """
    return await mobile_service.start_session(session_data, current_user)


@router.post("/sessions/{session_id}/end", response_model=MobileSessionResponse)
async def end_session(
    session_id: UUID,
    session_end: MobileSessionEnd,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """End a mobile session"""
    return await mobile_service.end_session(
        session_id,
        session_end.foreground_time,
        session_end.background_time,
        session_end.exit_screen,
        current_user
    )


# ============================================================================
# Push Notification Endpoints
# ============================================================================

@router.post("/push", response_model=PushNotificationResponse, status_code=status.HTTP_201_CREATED)
async def send_push_notification(
    notification_data: PushNotificationCreate,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Create and queue a push notification for delivery.

    Supports:
    - Rich notifications with images
    - Deep links for navigation
    - Platform-specific data (iOS/Android)
    - Scheduled delivery
    """
    return await mobile_service.send_push_notification(
        notification_data,
        current_user
    )


@router.get("/push", response_model=List[PushNotificationResponse])
async def get_user_notifications(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """Get push notifications for current user"""
    notifications, _ = await mobile_service.get_user_notifications(
        current_user,
        skip=skip,
        limit=limit
    )
    return notifications


@router.post("/push/{notification_id}/open", response_model=PushNotificationResponse)
async def mark_notification_opened(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """Mark a notification as opened"""
    return await mobile_service.mark_notification_opened(notification_id, current_user)


@router.get("/push/stats", response_model=PushNotificationStats)
async def get_notification_stats(
    campaign_id: Optional[str] = None,
    days_back: int = 30,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """Get push notification statistics"""
    return await mobile_service.get_notification_stats(
        current_user,
        campaign_id=campaign_id,
        days_back=days_back
    )


# ============================================================================
# Deep Link Endpoints
# ============================================================================

@router.post("/deep-links", response_model=DeepLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_deep_link(
    deep_link_data: DeepLinkCreate,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Create a deep link for mobile app navigation.

    Deep links support:
    - App navigation to specific screens
    - Attribution tracking (campaign, source, medium)
    - Fallback URLs for web or app install
    - Expiration dates
    """
    return await mobile_service.create_deep_link(deep_link_data, current_user)


@router.get("/deep-links/{link_code}", response_model=DeepLinkResponse)
async def get_deep_link(
    link_code: str,
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Get deep link by code (public endpoint).

    Returns the deep link configuration for app navigation.
    """
    return await mobile_service.get_deep_link(link_code)


@router.post("/deep-links/{link_code}/click", response_model=DeepLinkResponse)
async def track_deep_link_click(
    link_code: str,
    platform: Optional[str] = None,
    app_installed: bool = False,
    device_id: Optional[UUID] = None,
    request: Request = None,
    current_user: Optional[User] = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Track a deep link click.

    Records click analytics including platform, device, and user.
    """
    ip_address = request.client.host if request and request.client else None

    return await mobile_service.track_deep_link_click(
        link_code,
        platform=platform,
        app_installed=app_installed,
        current_user=current_user,
        device_id=device_id,
        ip_address=ip_address
    )


@router.get("/deep-links/{deep_link_id}/analytics", response_model=DeepLinkAnalytics)
async def get_deep_link_analytics(
    deep_link_id: UUID,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """Get analytics for a deep link"""
    return await mobile_service.get_deep_link_analytics(deep_link_id, current_user)


# ============================================================================
# Offline Sync Endpoints
# ============================================================================

@router.get("/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Get offline sync status for a device.

    Returns pending, syncing, failed, and conflict operations.
    """
    return await mobile_service.get_sync_status(device_id, current_user)


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def process_offline_sync(
    sync_data: OfflineSyncQueueCreate,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Process an offline sync operation.

    Queues operations performed offline for server sync.
    Handles conflict resolution for concurrent updates.
    """
    return await mobile_service.process_offline_sync(sync_data, current_user)


# ============================================================================
# App Version Endpoints
# ============================================================================

@router.post("/versions", response_model=AppVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_app_version(
    version_data: AppVersionCreate,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Create a new app version (admin only).

    Used for managing app releases and update notifications.
    """
    return await mobile_service.create_app_version(version_data, current_user)


@router.post("/versions/check", response_model=AppVersionCheckResponse)
async def check_app_version(
    version_check: AppVersionCheckRequest,
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Check if an app update is available.

    Returns update information including:
    - Update availability
    - Force update requirement
    - Latest version details
    - App store URL
    """
    return await mobile_service.check_app_version(version_check)


# ============================================================================
# Feature Flag Endpoints
# ============================================================================

@router.post("/feature-flags", response_model=MobileFeatureFlagResponse, status_code=status.HTTP_201_CREATED)
async def create_feature_flag(
    flag_data: MobileFeatureFlagCreate,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Create a feature flag (admin only).

    Feature flags enable:
    - Gradual feature rollout
    - A/B testing
    - Platform-specific features
    - Version targeting
    """
    return await mobile_service.create_feature_flag(flag_data, current_user)


@router.post("/feature-flags/get", response_model=FeatureFlagsResponse)
async def get_feature_flags(
    request_data: FeatureFlagsRequest,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Get feature flags for current user and device.

    Returns enabled features with their configuration.
    """
    return await mobile_service.get_feature_flags(
        request_data.platform,
        request_data.app_version,
        current_user
    )


# ============================================================================
# Analytics Endpoints
# ============================================================================

@router.post("/analytics/events", status_code=status.HTTP_201_CREATED)
async def track_analytics_event(
    event_data: MobileAnalyticsEventCreate,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Track a mobile analytics event.

    Events can include:
    - Custom event names and categories
    - Event properties (JSON)
    - Event values (numeric)
    - Screen context
    """
    return await mobile_service.track_event(event_data, current_user)


@router.post("/analytics/events/batch", status_code=status.HTTP_201_CREATED)
async def track_analytics_events_batch(
    batch_data: MobileAnalyticsEventBatch,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Track multiple analytics events in batch.

    More efficient than individual event tracking for offline sync.
    """
    results = []
    for event_dict in batch_data.events:
        try:
            event_data = MobileAnalyticsEventCreate(
                device_id=batch_data.device_id,
                session_id=batch_data.session_id,
                **event_dict
            )
            await mobile_service.track_event(event_data, current_user)
            results.append({"status": "success"})
        except Exception as e:
            results.append({"status": "error", "error": str(e)})

    return {"results": results}


@router.post("/analytics/screen-views", response_model=dict)
async def track_screen_view(
    screen_data: MobileScreenViewCreate,
    current_user: User = Depends(get_current_user),
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """
    Track a screen view.

    Returns the screen view ID for later updating with exit metrics.
    """
    screen_view_id = await mobile_service.track_screen_view(screen_data, current_user)
    return {"screen_view_id": screen_view_id}


@router.get("/analytics/events/{event_name}/stats", response_model=AnalyticsEventStats)
async def get_event_stats(
    event_name: str,
    days_back: int = 7,
    mobile_service: MobileService = Depends(get_mobile_service)
):
    """Get statistics for a specific analytics event"""
    return await mobile_service.get_event_stats(event_name, days_back)


# ============================================================================
# Health & Diagnostics Endpoints
# ============================================================================

@router.get("/health")
async def mobile_health_check():
    """
    Mobile service health check.

    Returns service status and availability.
    """
    return {
        "status": "healthy",
        "service": "mobile",
        "features": {
            "push_notifications": True,
            "deep_links": True,
            "offline_sync": True,
            "feature_flags": True,
            "analytics": True
        }
    }


@router.get("/config")
async def get_mobile_config(
    current_user: User = Depends(get_current_user)
):
    """
    Get mobile app configuration.

    Returns configuration needed for app initialization.
    """
    return {
        "api_endpoint": "/api/v1",
        "api_version": "1.0.0",
        "features": {
            "push_enabled": True,
            "offline_mode_enabled": True,
            "analytics_enabled": True,
            "deep_links_enabled": True
        },
        "sync_interval_minutes": 15,
        "cache_size_mb": 100
    }
