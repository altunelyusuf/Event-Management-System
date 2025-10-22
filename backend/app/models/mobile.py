"""
Mobile App Foundation Models
Sprint 18: Mobile App Foundation

Database models for mobile app support including device management,
push notifications, sessions, deep linking, offline sync, and app versioning.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    Text, ForeignKey, JSON, Index, UniqueConstraint, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


# ============================================================================
# Enums
# ============================================================================

class MobilePlatform(str, enum.Enum):
    """Mobile platforms"""
    IOS = "ios"
    ANDROID = "android"
    HUAWEI = "huawei"  # Huawei AppGallery


class DeviceType(str, enum.Enum):
    """Device types"""
    PHONE = "phone"
    TABLET = "tablet"
    WATCH = "watch"
    OTHER = "other"


class AppEnvironment(str, enum.Enum):
    """App environments"""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    BETA = "beta"


class PushNotificationProvider(str, enum.Enum):
    """Push notification providers"""
    FCM = "fcm"  # Firebase Cloud Messaging (Android & iOS)
    APNS = "apns"  # Apple Push Notification Service
    HMS = "hms"  # Huawei Mobile Services


class SyncStatus(str, enum.Enum):
    """Sync status for offline operations"""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    FAILED = "failed"
    CONFLICT = "conflict"


class DeepLinkType(str, enum.Enum):
    """Deep link types"""
    EVENT = "event"
    VENDOR = "vendor"
    BOOKING = "booking"
    MESSAGE = "message"
    NOTIFICATION = "notification"
    TASK = "task"
    DOCUMENT = "document"
    CALENDAR = "calendar"
    PROFILE = "profile"
    CUSTOM = "custom"


class FeatureFlagStatus(str, enum.Enum):
    """Feature flag status"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ROLLOUT = "rollout"  # Gradual rollout
    AB_TEST = "ab_test"  # A/B testing


# ============================================================================
# Device Management Models
# ============================================================================

class MobileDevice(Base):
    """
    Mobile device registration and management.

    Tracks user devices for push notifications, analytics,
    and multi-device support.
    """
    __tablename__ = "mobile_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Device identification
    device_id = Column(String(255), nullable=False, index=True)  # Unique device identifier
    device_name = Column(String(200), nullable=True)  # User-assigned name

    # Device details
    platform = Column(String(50), nullable=False, index=True)  # MobilePlatform
    device_type = Column(String(50), nullable=False, default="phone")  # DeviceType

    # Device info
    manufacturer = Column(String(100), nullable=True)  # Apple, Samsung, Huawei, etc.
    model = Column(String(100), nullable=True)  # iPhone 13, Galaxy S21, etc.
    os_version = Column(String(50), nullable=True)  # iOS 16.0, Android 13, etc.

    # App info
    app_version = Column(String(50), nullable=True)  # 1.2.3
    build_number = Column(String(50), nullable=True)  # 123
    app_environment = Column(String(50), nullable=False, default="production")  # AppEnvironment

    # Push notification token
    push_token = Column(String(500), nullable=True, index=True)
    push_provider = Column(String(50), nullable=True)  # PushNotificationProvider
    push_enabled = Column(Boolean, default=True)

    # Device capabilities
    capabilities = Column(JSON, nullable=True)  # {camera, biometric, nfc, etc.}

    # Screen info
    screen_width = Column(Integer, nullable=True)
    screen_height = Column(Integer, nullable=True)
    screen_density = Column(Float, nullable=True)

    # Locale and timezone
    locale = Column(String(10), nullable=True)  # en-US, tr-TR, etc.
    timezone = Column(String(50), nullable=True)  # Europe/Istanbul

    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_primary = Column(Boolean, default=False)  # User's primary device

    # Tracking
    last_active_at = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Security
    is_trusted = Column(Boolean, default=False)
    trust_score = Column(Float, nullable=True)  # 0-1 trust score

    # Metadata
    first_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    registered_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'device_id', name='uq_user_device'),
        Index('ix_mobile_devices_user_active', 'user_id', 'is_active'),
        Index('ix_mobile_devices_platform', 'platform'),
        Index('ix_mobile_devices_push_token', 'push_token'),
    )


class MobileSession(Base):
    """
    Mobile app session tracking.

    Tracks user sessions for analytics and engagement metrics.
    """
    __tablename__ = "mobile_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="CASCADE"), nullable=False, index=True)

    # Session details
    session_id = Column(String(255), unique=True, nullable=False, index=True)

    # Timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Session state
    is_active = Column(Boolean, default=True, index=True)

    # App state
    app_version = Column(String(50), nullable=True)
    foreground_time = Column(Integer, nullable=True)  # Time app was in foreground
    background_time = Column(Integer, nullable=True)  # Time app was in background

    # Engagement
    screen_views = Column(Integer, default=0)
    interactions = Column(Integer, default=0)
    events_tracked = Column(Integer, default=0)

    # Screens visited
    screens_visited = Column(ARRAY(String), nullable=True)
    entry_screen = Column(String(100), nullable=True)
    exit_screen = Column(String(100), nullable=True)

    # Network
    network_type = Column(String(50), nullable=True)  # wifi, cellular, offline

    # Location (if permitted)
    location_data = Column(JSON, nullable=True)  # {city, country, lat, lon}

    # Crash/errors
    crash_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)

    # Metadata
    session_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_mobile_sessions_user_started', 'user_id', 'started_at'),
        Index('ix_mobile_sessions_device_started', 'device_id', 'started_at'),
        Index('ix_mobile_sessions_active', 'is_active'),
    )


# ============================================================================
# Push Notification Models
# ============================================================================

class PushNotification(Base):
    """
    Push notifications sent to mobile devices.

    Tracks all push notifications for delivery and analytics.
    """
    __tablename__ = "push_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Target
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="CASCADE"), nullable=True, index=True)

    # Notification content
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    subtitle = Column(String(200), nullable=True)  # iOS subtitle

    # Image/media
    image_url = Column(String(500), nullable=True)

    # Action
    action_type = Column(String(50), nullable=True)  # open_app, open_url, deep_link
    action_data = Column(JSON, nullable=True)  # Additional action data

    # Deep link
    deep_link = Column(String(500), nullable=True)
    deep_link_type = Column(String(50), nullable=True)  # DeepLinkType

    # Notification settings
    badge_count = Column(Integer, nullable=True)  # iOS badge
    sound = Column(String(100), nullable=True, default="default")
    priority = Column(String(50), nullable=False, default="normal")  # low, normal, high

    # Category/channel
    category = Column(String(100), nullable=True)  # iOS notification category
    channel_id = Column(String(100), nullable=True)  # Android notification channel

    # Platform-specific data
    ios_data = Column(JSON, nullable=True)
    android_data = Column(JSON, nullable=True)

    # Scheduling
    scheduled_at = Column(DateTime, nullable=True, index=True)

    # Delivery
    sent_at = Column(DateTime, nullable=True, index=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)

    # Status
    status = Column(String(50), nullable=False, default="pending", index=True)  # pending, sent, delivered, opened, failed

    # Delivery details
    provider = Column(String(50), nullable=True)  # PushNotificationProvider
    provider_message_id = Column(String(255), nullable=True)

    # Failure info
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Campaign/batch
    campaign_id = Column(String(100), nullable=True, index=True)
    batch_id = Column(String(100), nullable=True, index=True)

    # Related entity
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('ix_push_notifications_user_created', 'user_id', 'created_at'),
        Index('ix_push_notifications_device_created', 'device_id', 'created_at'),
        Index('ix_push_notifications_status', 'status'),
        Index('ix_push_notifications_scheduled', 'scheduled_at'),
        Index('ix_push_notifications_campaign', 'campaign_id'),
    )


# ============================================================================
# Deep Linking Models
# ============================================================================

class DeepLink(Base):
    """
    Deep link management and analytics.

    Tracks deep links for attribution and navigation.
    """
    __tablename__ = "deep_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link identity
    link_code = Column(String(100), unique=True, nullable=False, index=True)
    link_url = Column(String(500), nullable=False)  # Full deep link URL

    # Target
    link_type = Column(String(50), nullable=False, index=True)  # DeepLinkType
    target_entity_type = Column(String(50), nullable=True)
    target_entity_id = Column(UUID(as_uuid=True), nullable=True)

    # Destination
    destination_screen = Column(String(100), nullable=True)
    destination_params = Column(JSON, nullable=True)

    # Link info
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)

    # Fallback
    web_url = Column(String(500), nullable=True)  # Fallback for web
    fallback_url = Column(String(500), nullable=True)  # Fallback if app not installed

    # Campaign tracking
    campaign_name = Column(String(200), nullable=True, index=True)
    campaign_source = Column(String(100), nullable=True)  # email, sms, social
    campaign_medium = Column(String(100), nullable=True)
    campaign_content = Column(String(200), nullable=True)

    # Attribution
    utm_parameters = Column(JSON, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Expiration
    expires_at = Column(DateTime, nullable=True, index=True)

    # Analytics
    click_count = Column(Integer, default=0)
    install_count = Column(Integer, default=0)
    open_count = Column(Integer, default=0)
    conversion_count = Column(Integer, default=0)

    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        Index('ix_deep_links_type', 'link_type'),
        Index('ix_deep_links_campaign', 'campaign_name'),
        Index('ix_deep_links_active', 'is_active'),
    )


class DeepLinkClick(Base):
    """
    Deep link click tracking.

    Tracks individual clicks on deep links for analytics.
    """
    __tablename__ = "deep_link_clicks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link reference
    deep_link_id = Column(UUID(as_uuid=True), ForeignKey("deep_links.id", ondelete="CASCADE"), nullable=False, index=True)

    # User (if authenticated)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Device info
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="SET NULL"), nullable=True)
    platform = Column(String(50), nullable=True)
    device_type = Column(String(50), nullable=True)

    # App info
    app_installed = Column(Boolean, default=False)
    app_version = Column(String(50), nullable=True)

    # Click details
    clicked_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Outcome
    action_taken = Column(String(50), nullable=True)  # installed, opened, converted
    converted = Column(Boolean, default=False)
    converted_at = Column(DateTime, nullable=True)

    # Attribution
    referrer = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Location
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)

    # Metadata
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_deep_link_clicks_link_clicked', 'deep_link_id', 'clicked_at'),
        Index('ix_deep_link_clicks_user', 'user_id'),
    )


# ============================================================================
# Offline Sync Models
# ============================================================================

class OfflineSyncQueue(Base):
    """
    Queue for offline operations to sync when online.

    Stores operations performed offline for later sync.
    """
    __tablename__ = "offline_sync_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User and device
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="CASCADE"), nullable=False, index=True)

    # Operation details
    operation_type = Column(String(50), nullable=False, index=True)  # create, update, delete
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)

    # Operation data
    operation_data = Column(JSON, nullable=False)

    # Client-side ID (for conflict resolution)
    client_id = Column(String(255), nullable=True)
    client_timestamp = Column(DateTime, nullable=True)

    # Sync status
    status = Column(String(50), nullable=False, default="pending", index=True)  # SyncStatus

    # Sync attempts
    sync_attempts = Column(Integer, default=0)
    last_sync_attempt_at = Column(DateTime, nullable=True)
    synced_at = Column(DateTime, nullable=True)

    # Conflict resolution
    conflict_data = Column(JSON, nullable=True)
    conflict_resolved = Column(Boolean, default=False)
    conflict_resolution = Column(String(50), nullable=True)  # server_wins, client_wins, merge

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Priority
    priority = Column(Integer, default=0)  # Higher = higher priority

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        Index('ix_offline_sync_queue_user_status', 'user_id', 'status'),
        Index('ix_offline_sync_queue_device_status', 'device_id', 'status'),
        Index('ix_offline_sync_queue_entity', 'entity_type', 'entity_id'),
    )


# ============================================================================
# App Version & Update Models
# ============================================================================

class AppVersion(Base):
    """
    App version registry and management.

    Tracks app versions for update management and compatibility.
    """
    __tablename__ = "app_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Version info
    version = Column(String(50), nullable=False)  # 1.2.3
    build_number = Column(String(50), nullable=False)  # 123
    version_code = Column(Integer, nullable=True)  # Android version code

    # Platform
    platform = Column(String(50), nullable=False, index=True)  # MobilePlatform
    environment = Column(String(50), nullable=False, default="production")  # AppEnvironment

    # Release info
    release_notes = Column(Text, nullable=True)
    release_date = Column(DateTime, nullable=True)

    # Status
    status = Column(String(50), nullable=False, default="beta")  # beta, production, deprecated
    is_current = Column(Boolean, default=False)

    # Requirements
    min_os_version = Column(String(50), nullable=True)
    max_os_version = Column(String(50), nullable=True)

    # Update settings
    force_update = Column(Boolean, default=False)  # Force users to update
    min_supported_version = Column(String(50), nullable=True)  # Minimum version still supported

    # Store URLs
    app_store_url = Column(String(500), nullable=True)  # iOS App Store
    play_store_url = Column(String(500), nullable=True)  # Google Play
    app_gallery_url = Column(String(500), nullable=True)  # Huawei AppGallery

    # Binary info
    binary_url = Column(String(500), nullable=True)
    binary_size_mb = Column(Float, nullable=True)
    binary_checksum = Column(String(255), nullable=True)

    # Features
    features = Column(ARRAY(String), nullable=True)
    bug_fixes = Column(ARRAY(String), nullable=True)

    # Rollout
    rollout_percentage = Column(Float, default=100.0)  # Gradual rollout 0-100

    # Analytics
    install_count = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    crash_rate = Column(Float, nullable=True)

    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint('platform', 'version', 'build_number', name='uq_app_version'),
        Index('ix_app_versions_platform_current', 'platform', 'is_current'),
    )


# ============================================================================
# Feature Flags Models
# ============================================================================

class MobileFeatureFlag(Base):
    """
    Feature flags for mobile app features.

    Control feature rollout and A/B testing on mobile.
    """
    __tablename__ = "mobile_feature_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Feature info
    feature_key = Column(String(200), unique=True, nullable=False, index=True)
    feature_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Status
    status = Column(String(50), nullable=False, default="disabled", index=True)  # FeatureFlagStatus

    # Platform targeting
    platforms = Column(ARRAY(String), nullable=True)  # [ios, android] or null for all

    # Version targeting
    min_app_version = Column(String(50), nullable=True)
    max_app_version = Column(String(50), nullable=True)

    # Rollout
    rollout_percentage = Column(Float, default=0.0)  # 0-100
    rollout_strategy = Column(String(50), nullable=True)  # random, user_id, device_id

    # User targeting
    target_user_segments = Column(ARRAY(String), nullable=True)
    target_user_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)

    # A/B testing
    variants = Column(JSON, nullable=True)  # [{name, percentage, config}]

    # Configuration
    config = Column(JSON, nullable=True)  # Feature configuration

    # Scheduling
    enabled_at = Column(DateTime, nullable=True)
    disabled_at = Column(DateTime, nullable=True)

    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('ix_mobile_feature_flags_status', 'status'),
    )


class MobileFeatureFlagAssignment(Base):
    """
    User/device feature flag assignments.

    Tracks which features are enabled for which users/devices.
    """
    __tablename__ = "mobile_feature_flag_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    feature_flag_id = Column(UUID(as_uuid=True), ForeignKey("mobile_feature_flags.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="CASCADE"), nullable=True, index=True)

    # Assignment
    is_enabled = Column(Boolean, nullable=False)
    variant = Column(String(50), nullable=True)  # For A/B testing

    # Tracking
    first_exposed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_checked_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        Index('ix_mobile_feature_flag_assignments_flag_user', 'feature_flag_id', 'user_id'),
        Index('ix_mobile_feature_flag_assignments_flag_device', 'feature_flag_id', 'device_id'),
    )


# ============================================================================
# Mobile Analytics Models
# ============================================================================

class MobileAnalyticsEvent(Base):
    """
    Mobile app analytics events.

    Tracks custom events for analytics and insights.
    """
    __tablename__ = "mobile_analytics_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User and device
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="CASCADE"), nullable=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("mobile_sessions.id", ondelete="CASCADE"), nullable=True, index=True)

    # Event details
    event_name = Column(String(100), nullable=False, index=True)
    event_category = Column(String(100), nullable=True, index=True)

    # Event data
    event_properties = Column(JSON, nullable=True)
    event_value = Column(Float, nullable=True)

    # Screen context
    screen_name = Column(String(100), nullable=True)
    screen_class = Column(String(100), nullable=True)

    # Timing
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Device context
    platform = Column(String(50), nullable=True)
    app_version = Column(String(50), nullable=True)

    # Network
    network_type = Column(String(50), nullable=True)
    is_offline = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_mobile_analytics_events_user_occurred', 'user_id', 'occurred_at'),
        Index('ix_mobile_analytics_events_name_occurred', 'event_name', 'occurred_at'),
        Index('ix_mobile_analytics_events_category', 'event_category'),
    )


class MobileScreenView(Base):
    """
    Mobile screen view tracking.

    Tracks screen views for navigation analytics.
    """
    __tablename__ = "mobile_screen_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User and device
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="CASCADE"), nullable=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("mobile_sessions.id", ondelete="CASCADE"), nullable=True, index=True)

    # Screen details
    screen_name = Column(String(100), nullable=False, index=True)
    screen_class = Column(String(100), nullable=True)

    # Previous screen (for flow analysis)
    previous_screen = Column(String(100), nullable=True)

    # Timing
    viewed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    exit_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Engagement
    scroll_depth = Column(Float, nullable=True)  # 0-1 percentage
    interactions = Column(Integer, default=0)

    # Context
    screen_parameters = Column(JSON, nullable=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_mobile_screen_views_user_viewed', 'user_id', 'viewed_at'),
        Index('ix_mobile_screen_views_session', 'session_id'),
        Index('ix_mobile_screen_views_screen', 'screen_name'),
    )
