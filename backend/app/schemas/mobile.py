"""
Mobile App Foundation Schemas
Sprint 18: Mobile App Foundation

Pydantic schemas for mobile app support including device management,
push notifications, sessions, deep linking, offline sync, and app versioning.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# Mobile Device Schemas
# ============================================================================

class MobileDeviceBase(BaseModel):
    """Base schema for mobile devices"""
    device_id: str = Field(..., max_length=255)
    device_name: Optional[str] = Field(None, max_length=200)
    platform: str
    device_type: str = Field("phone")
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    os_version: Optional[str] = Field(None, max_length=50)
    app_version: Optional[str] = Field(None, max_length=50)
    build_number: Optional[str] = Field(None, max_length=50)
    app_environment: str = Field("production")


class MobileDeviceRegister(MobileDeviceBase):
    """Schema for registering device"""
    push_token: Optional[str] = Field(None, max_length=500)
    push_provider: Optional[str] = None
    push_enabled: bool = Field(True)
    capabilities: Optional[Dict[str, Any]] = None
    screen_width: Optional[int] = Field(None, gt=0)
    screen_height: Optional[int] = Field(None, gt=0)
    screen_density: Optional[float] = Field(None, gt=0)
    locale: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)


class MobileDeviceUpdate(BaseModel):
    """Schema for updating device"""
    device_name: Optional[str] = Field(None, max_length=200)
    push_token: Optional[str] = Field(None, max_length=500)
    push_provider: Optional[str] = None
    push_enabled: Optional[bool] = None
    app_version: Optional[str] = Field(None, max_length=50)
    build_number: Optional[str] = Field(None, max_length=50)
    os_version: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None
    locale: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)


class MobileDeviceResponse(MobileDeviceBase):
    """Schema for device response"""
    id: UUID
    user_id: UUID
    push_enabled: bool
    capabilities: Optional[Dict[str, Any]]
    screen_width: Optional[int]
    screen_height: Optional[int]
    screen_density: Optional[float]
    locale: Optional[str]
    timezone: Optional[str]
    is_active: bool
    is_primary: bool
    last_active_at: Optional[datetime]
    is_trusted: bool
    trust_score: Optional[float]
    first_seen_at: datetime
    registered_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeviceListResponse(BaseModel):
    """Schema for device list"""
    devices: List[MobileDeviceResponse]
    total: int
    active_count: int


# ============================================================================
# Mobile Session Schemas
# ============================================================================

class MobileSessionStart(BaseModel):
    """Schema for starting session"""
    device_id: UUID
    app_version: Optional[str] = Field(None, max_length=50)
    network_type: Optional[str] = None
    location_data: Optional[Dict[str, Any]] = None


class MobileSessionUpdate(BaseModel):
    """Schema for updating session"""
    screen_views: Optional[int] = Field(None, ge=0)
    interactions: Optional[int] = Field(None, ge=0)
    events_tracked: Optional[int] = Field(None, ge=0)
    screens_visited: Optional[List[str]] = None
    crash_count: Optional[int] = Field(None, ge=0)
    error_count: Optional[int] = Field(None, ge=0)


class MobileSessionEnd(BaseModel):
    """Schema for ending session"""
    foreground_time: int = Field(..., ge=0)
    background_time: int = Field(..., ge=0)
    exit_screen: Optional[str] = None


class MobileSessionResponse(BaseModel):
    """Schema for session response"""
    id: UUID
    user_id: UUID
    device_id: UUID
    session_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    is_active: bool
    app_version: Optional[str]
    foreground_time: Optional[int]
    background_time: Optional[int]
    screen_views: int
    interactions: int
    events_tracked: int
    screens_visited: Optional[List[str]]
    entry_screen: Optional[str]
    exit_screen: Optional[str]
    network_type: Optional[str]
    crash_count: int
    error_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class SessionAnalytics(BaseModel):
    """Schema for session analytics"""
    total_sessions: int
    average_duration: float
    average_screen_views: float
    average_interactions: float
    total_crashes: int
    crash_rate: float
    most_visited_screens: List[Dict[str, Any]]


# ============================================================================
# Push Notification Schemas
# ============================================================================

class PushNotificationCreate(BaseModel):
    """Schema for creating push notification"""
    user_id: Optional[UUID] = None
    device_id: Optional[UUID] = None
    title: str = Field(..., max_length=200)
    body: str
    subtitle: Optional[str] = Field(None, max_length=200)
    image_url: Optional[str] = Field(None, max_length=500)
    action_type: Optional[str] = None
    action_data: Optional[Dict[str, Any]] = None
    deep_link: Optional[str] = Field(None, max_length=500)
    deep_link_type: Optional[str] = None
    badge_count: Optional[int] = Field(None, ge=0)
    sound: str = Field("default", max_length=100)
    priority: str = Field("normal")
    category: Optional[str] = Field(None, max_length=100)
    channel_id: Optional[str] = Field(None, max_length=100)
    ios_data: Optional[Dict[str, Any]] = None
    android_data: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None


class PushNotificationBulkCreate(BaseModel):
    """Schema for bulk push notifications"""
    user_ids: Optional[List[UUID]] = None
    device_ids: Optional[List[UUID]] = None
    title: str = Field(..., max_length=200)
    body: str
    subtitle: Optional[str] = Field(None, max_length=200)
    deep_link: Optional[str] = None
    campaign_id: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class PushNotificationResponse(BaseModel):
    """Schema for push notification response"""
    id: UUID
    user_id: Optional[UUID]
    device_id: Optional[UUID]
    title: str
    body: str
    subtitle: Optional[str]
    image_url: Optional[str]
    action_type: Optional[str]
    deep_link: Optional[str]
    deep_link_type: Optional[str]
    badge_count: Optional[int]
    sound: str
    priority: str
    scheduled_at: Optional[datetime]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    opened_at: Optional[datetime]
    status: str
    provider: Optional[str]
    error_message: Optional[str]
    retry_count: int
    campaign_id: Optional[str]
    batch_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PushNotificationStats(BaseModel):
    """Schema for push notification statistics"""
    total_sent: int
    delivered_count: int
    opened_count: int
    failed_count: int
    delivery_rate: float
    open_rate: float


# ============================================================================
# Deep Link Schemas
# ============================================================================

class DeepLinkCreate(BaseModel):
    """Schema for creating deep link"""
    link_type: str
    target_entity_type: Optional[str] = None
    target_entity_id: Optional[UUID] = None
    destination_screen: Optional[str] = Field(None, max_length=100)
    destination_params: Optional[Dict[str, Any]] = None
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)
    web_url: Optional[str] = Field(None, max_length=500)
    fallback_url: Optional[str] = Field(None, max_length=500)
    campaign_name: Optional[str] = Field(None, max_length=200)
    campaign_source: Optional[str] = Field(None, max_length=100)
    campaign_medium: Optional[str] = Field(None, max_length=100)
    utm_parameters: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class DeepLinkUpdate(BaseModel):
    """Schema for updating deep link"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class DeepLinkResponse(BaseModel):
    """Schema for deep link response"""
    id: UUID
    link_code: str
    link_url: str
    link_type: str
    target_entity_type: Optional[str]
    target_entity_id: Optional[UUID]
    destination_screen: Optional[str]
    destination_params: Optional[Dict[str, Any]]
    title: Optional[str]
    description: Optional[str]
    image_url: Optional[str]
    web_url: Optional[str]
    fallback_url: Optional[str]
    campaign_name: Optional[str]
    campaign_source: Optional[str]
    campaign_medium: Optional[str]
    is_active: bool
    expires_at: Optional[datetime]
    click_count: int
    install_count: int
    open_count: int
    conversion_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeepLinkClickCreate(BaseModel):
    """Schema for tracking deep link click"""
    deep_link_id: UUID
    platform: Optional[str] = None
    device_type: Optional[str] = None
    app_installed: bool = False
    app_version: Optional[str] = None
    referrer: Optional[str] = None


class DeepLinkAnalytics(BaseModel):
    """Schema for deep link analytics"""
    link_code: str
    total_clicks: int
    install_count: int
    open_count: int
    conversion_count: int
    install_rate: float
    conversion_rate: float
    top_platforms: Dict[str, int]
    top_countries: Dict[str, int]


# ============================================================================
# Offline Sync Schemas
# ============================================================================

class OfflineSyncQueueCreate(BaseModel):
    """Schema for creating offline sync operation"""
    device_id: UUID
    operation_type: str
    entity_type: str
    entity_id: Optional[UUID] = None
    operation_data: Dict[str, Any]
    client_id: Optional[str] = None
    client_timestamp: Optional[datetime] = None
    priority: int = Field(0, ge=0)


class OfflineSyncQueueUpdate(BaseModel):
    """Schema for updating sync status"""
    status: str
    error_message: Optional[str] = None


class OfflineSyncQueueResponse(BaseModel):
    """Schema for offline sync response"""
    id: UUID
    user_id: UUID
    device_id: UUID
    operation_type: str
    entity_type: str
    entity_id: Optional[UUID]
    operation_data: Dict[str, Any]
    client_id: Optional[str]
    client_timestamp: Optional[datetime]
    status: str
    sync_attempts: int
    last_sync_attempt_at: Optional[datetime]
    synced_at: Optional[datetime]
    conflict_data: Optional[Dict[str, Any]]
    conflict_resolved: bool
    conflict_resolution: Optional[str]
    error_message: Optional[str]
    priority: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SyncStatusResponse(BaseModel):
    """Schema for sync status"""
    pending_count: int
    syncing_count: int
    failed_count: int
    conflict_count: int
    pending_operations: List[OfflineSyncQueueResponse]


# ============================================================================
# App Version Schemas
# ============================================================================

class AppVersionCreate(BaseModel):
    """Schema for creating app version"""
    version: str = Field(..., max_length=50)
    build_number: str = Field(..., max_length=50)
    version_code: Optional[int] = None
    platform: str
    environment: str = Field("production")
    release_notes: Optional[str] = None
    release_date: Optional[datetime] = None
    min_os_version: Optional[str] = Field(None, max_length=50)
    max_os_version: Optional[str] = Field(None, max_length=50)
    force_update: bool = Field(False)
    min_supported_version: Optional[str] = Field(None, max_length=50)
    app_store_url: Optional[str] = Field(None, max_length=500)
    play_store_url: Optional[str] = Field(None, max_length=500)
    app_gallery_url: Optional[str] = Field(None, max_length=500)
    features: Optional[List[str]] = None
    bug_fixes: Optional[List[str]] = None
    rollout_percentage: float = Field(100.0, ge=0.0, le=100.0)


class AppVersionUpdate(BaseModel):
    """Schema for updating app version"""
    status: Optional[str] = None
    is_current: Optional[bool] = None
    force_update: Optional[bool] = None
    rollout_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    release_notes: Optional[str] = None


class AppVersionResponse(BaseModel):
    """Schema for app version response"""
    id: UUID
    version: str
    build_number: str
    version_code: Optional[int]
    platform: str
    environment: str
    release_notes: Optional[str]
    release_date: Optional[datetime]
    status: str
    is_current: bool
    min_os_version: Optional[str]
    max_os_version: Optional[str]
    force_update: bool
    min_supported_version: Optional[str]
    app_store_url: Optional[str]
    play_store_url: Optional[str]
    app_gallery_url: Optional[str]
    binary_url: Optional[str]
    binary_size_mb: Optional[float]
    features: Optional[List[str]]
    bug_fixes: Optional[List[str]]
    rollout_percentage: float
    install_count: int
    active_users: int
    crash_rate: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppVersionCheckRequest(BaseModel):
    """Schema for app version check"""
    platform: str
    current_version: str
    build_number: str
    os_version: Optional[str] = None


class AppVersionCheckResponse(BaseModel):
    """Schema for app version check response"""
    update_available: bool
    force_update: bool
    latest_version: Optional[AppVersionResponse] = None
    update_url: Optional[str] = None
    release_notes: Optional[str] = None


# ============================================================================
# Feature Flag Schemas
# ============================================================================

class MobileFeatureFlagCreate(BaseModel):
    """Schema for creating feature flag"""
    feature_key: str = Field(..., max_length=200)
    feature_name: str = Field(..., max_length=200)
    description: Optional[str] = None
    status: str = Field("disabled")
    platforms: Optional[List[str]] = None
    min_app_version: Optional[str] = Field(None, max_length=50)
    max_app_version: Optional[str] = Field(None, max_length=50)
    rollout_percentage: float = Field(0.0, ge=0.0, le=100.0)
    rollout_strategy: Optional[str] = None
    target_user_segments: Optional[List[str]] = None
    variants: Optional[List[Dict[str, Any]]] = None
    config: Optional[Dict[str, Any]] = None


class MobileFeatureFlagUpdate(BaseModel):
    """Schema for updating feature flag"""
    feature_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None
    rollout_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    config: Optional[Dict[str, Any]] = None
    enabled_at: Optional[datetime] = None
    disabled_at: Optional[datetime] = None


class MobileFeatureFlagResponse(BaseModel):
    """Schema for feature flag response"""
    id: UUID
    feature_key: str
    feature_name: str
    description: Optional[str]
    status: str
    platforms: Optional[List[str]]
    min_app_version: Optional[str]
    max_app_version: Optional[str]
    rollout_percentage: float
    rollout_strategy: Optional[str]
    target_user_segments: Optional[List[str]]
    variants: Optional[List[Dict[str, Any]]]
    config: Optional[Dict[str, Any]]
    enabled_at: Optional[datetime]
    disabled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeatureFlagsRequest(BaseModel):
    """Schema for requesting feature flags"""
    device_id: UUID
    app_version: str
    platform: str


class FeatureFlagsResponse(BaseModel):
    """Schema for feature flags response"""
    features: Dict[str, Any]  # {feature_key: {enabled, config, variant}}
    timestamp: datetime


# ============================================================================
# Mobile Analytics Schemas
# ============================================================================

class MobileAnalyticsEventCreate(BaseModel):
    """Schema for creating analytics event"""
    device_id: UUID
    session_id: Optional[UUID] = None
    event_name: str = Field(..., max_length=100)
    event_category: Optional[str] = Field(None, max_length=100)
    event_properties: Optional[Dict[str, Any]] = None
    event_value: Optional[float] = None
    screen_name: Optional[str] = Field(None, max_length=100)
    screen_class: Optional[str] = Field(None, max_length=100)
    network_type: Optional[str] = None
    is_offline: bool = Field(False)


class MobileAnalyticsEventBatch(BaseModel):
    """Schema for batch analytics events"""
    device_id: UUID
    session_id: Optional[UUID] = None
    events: List[Dict[str, Any]]


class MobileScreenViewCreate(BaseModel):
    """Schema for creating screen view"""
    device_id: UUID
    session_id: Optional[UUID] = None
    screen_name: str = Field(..., max_length=100)
    screen_class: Optional[str] = Field(None, max_length=100)
    previous_screen: Optional[str] = Field(None, max_length=100)
    screen_parameters: Optional[Dict[str, Any]] = None


class MobileScreenViewEnd(BaseModel):
    """Schema for ending screen view"""
    scroll_depth: Optional[float] = Field(None, ge=0.0, le=1.0)
    interactions: int = Field(0, ge=0)


class MobileScreenViewResponse(BaseModel):
    """Schema for screen view response"""
    id: UUID
    user_id: Optional[UUID]
    device_id: UUID
    session_id: Optional[UUID]
    screen_name: str
    screen_class: Optional[str]
    previous_screen: Optional[str]
    viewed_at: datetime
    exit_at: Optional[datetime]
    duration_seconds: Optional[int]
    scroll_depth: Optional[float]
    interactions: int
    screen_parameters: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class AnalyticsEventStats(BaseModel):
    """Schema for analytics event statistics"""
    event_name: str
    total_count: int
    unique_users: int
    average_value: Optional[float]
    top_screens: List[Dict[str, Any]]


class ScreenFlowAnalytics(BaseModel):
    """Schema for screen flow analytics"""
    screen_name: str
    total_views: int
    average_duration: float
    top_next_screens: List[Dict[str, Any]]
    top_previous_screens: List[Dict[str, Any]]
    exit_rate: float


# ============================================================================
# Bulk Operations Schemas
# ============================================================================

class BulkDeviceUpdate(BaseModel):
    """Schema for bulk device update"""
    device_ids: List[UUID]
    push_enabled: Optional[bool] = None
    is_active: Optional[bool] = None


class BulkPushNotification(BaseModel):
    """Schema for bulk push notifications"""
    target_criteria: Dict[str, Any]  # {platform, app_version, segments}
    notification: PushNotificationCreate
    campaign_id: str
    batch_size: int = Field(100, gt=0, le=1000)


# ============================================================================
# Configuration Schemas
# ============================================================================

class MobileAppConfig(BaseModel):
    """Schema for mobile app configuration"""
    api_endpoint: str
    api_version: str
    features: Dict[str, Any]
    theme: Optional[Dict[str, Any]] = None
    analytics_enabled: bool = True
    crash_reporting_enabled: bool = True
    push_enabled: bool = True
    offline_mode_enabled: bool = True
    cache_size_mb: int = Field(100, gt=0)
    sync_interval_minutes: int = Field(15, gt=0)


class MobileSettings(BaseModel):
    """Schema for user mobile settings"""
    notifications_enabled: bool = True
    push_enabled: bool = True
    offline_sync_enabled: bool = True
    wifi_only_sync: bool = False
    auto_download_media: bool = True
    theme: str = Field("auto")  # auto, light, dark
    language: str = Field("en")
    data_saver_mode: bool = False


class MobileSettingsResponse(MobileSettings):
    """Schema for mobile settings response"""
    id: UUID
    user_id: UUID
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Diagnostics & Health Schemas
# ============================================================================

class AppHealthCheck(BaseModel):
    """Schema for app health check"""
    device_id: UUID
    app_version: str
    platform: str
    os_version: str
    memory_usage_mb: float
    storage_available_mb: float
    battery_level: Optional[float] = Field(None, ge=0.0, le=100.0)
    network_type: str
    crash_count: int = Field(0, ge=0)
    error_count: int = Field(0, ge=0)


class AppHealthResponse(BaseModel):
    """Schema for app health response"""
    status: str  # healthy, degraded, critical
    recommendations: List[str]
    warnings: List[str]


class CrashReport(BaseModel):
    """Schema for crash report"""
    device_id: UUID
    session_id: Optional[UUID] = None
    app_version: str
    platform: str
    os_version: str
    crash_type: str
    crash_message: str
    stack_trace: str
    breadcrumbs: Optional[List[Dict[str, Any]]] = None
    device_state: Optional[Dict[str, Any]] = None
    occurred_at: datetime


class ErrorReport(BaseModel):
    """Schema for error report"""
    device_id: UUID
    session_id: Optional[UUID] = None
    error_type: str
    error_message: str
    error_code: Optional[str] = None
    screen_name: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    occurred_at: datetime
