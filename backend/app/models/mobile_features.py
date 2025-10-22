"""
Mobile App Features Models
Sprint 19: Mobile App Features

Database models for advanced mobile features including QR codes,
mobile wallet, camera integration, biometrics, location features,
sharing, widgets, and quick actions.
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

class QRCodeType(str, enum.Enum):
    """QR code types"""
    EVENT = "event"
    VENDOR = "vendor"
    BOOKING = "booking"
    TICKET = "ticket"
    CHECK_IN = "check_in"
    PAYMENT = "payment"
    CONTACT = "contact"
    CUSTOM = "custom"


class BiometricType(str, enum.Enum):
    """Biometric authentication types"""
    FACE_ID = "face_id"
    TOUCH_ID = "touch_id"
    FINGERPRINT = "fingerprint"
    IRIS = "iris"


class MobileWalletProvider(str, enum.Enum):
    """Mobile wallet providers"""
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    SAMSUNG_PAY = "samsung_pay"


class LocationPermissionLevel(str, enum.Enum):
    """Location permission levels"""
    ALWAYS = "always"
    WHEN_IN_USE = "when_in_use"
    NEVER = "never"


class ShareMethod(str, enum.Enum):
    """Mobile sharing methods"""
    NATIVE_SHARE = "native_share"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    EMAIL = "email"
    SMS = "sms"
    COPY_LINK = "copy_link"


class WidgetType(str, enum.Enum):
    """Mobile widget types"""
    UPCOMING_EVENTS = "upcoming_events"
    COUNTDOWN = "countdown"
    TASK_LIST = "task_list"
    BUDGET_SUMMARY = "budget_summary"
    QUICK_ACTION = "quick_action"


class QuickActionType(str, enum.Enum):
    """Quick action types"""
    CREATE_EVENT = "create_event"
    SCAN_QR = "scan_qr"
    QUICK_MESSAGE = "quick_message"
    ADD_TASK = "add_task"
    ADD_EXPENSE = "add_expense"


# ============================================================================
# QR Code Models
# ============================================================================

class QRCode(Base):
    """
    QR code generation and tracking.

    Generate and track QR codes for various entities
    like events, tickets, check-ins, etc.
    """
    __tablename__ = "qr_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # QR code identity
    qr_code = Column(String(500), unique=True, nullable=False, index=True)
    qr_type = Column(String(50), nullable=False, index=True)  # QRCodeType

    # Target entity
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # QR code data
    qr_data = Column(JSON, nullable=False)  # Data encoded in QR
    display_text = Column(String(500), nullable=True)  # Text to show with QR

    # Image
    image_url = Column(String(500), nullable=True)  # Generated QR image
    image_size = Column(Integer, nullable=True)  # Size in pixels

    # Settings
    foreground_color = Column(String(7), nullable=True, default="#000000")
    background_color = Column(String(7), nullable=True, default="#FFFFFF")
    error_correction = Column(String(1), nullable=True, default="M")  # L, M, Q, H

    # Expiration
    expires_at = Column(DateTime, nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)

    # Usage tracking
    scan_count = Column(Integer, default=0)
    last_scanned_at = Column(DateTime, nullable=True)
    unique_scanners = Column(Integer, default=0)

    # Security
    requires_authentication = Column(Boolean, default=False)
    max_scans = Column(Integer, nullable=True)  # Limit scans

    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        Index('ix_qr_codes_entity', 'entity_type', 'entity_id'),
        Index('ix_qr_codes_type', 'qr_type'),
    )


class QRCodeScan(Base):
    """
    QR code scan tracking.

    Track individual QR code scans for analytics.
    """
    __tablename__ = "qr_code_scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # QR code reference
    qr_code_id = Column(UUID(as_uuid=True), ForeignKey("qr_codes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Scanner (if authenticated)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="SET NULL"), nullable=True)

    # Scan details
    scanned_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Location (if permitted)
    location_data = Column(JSON, nullable=True)  # {lat, lon, city, country}

    # Device info
    platform = Column(String(50), nullable=True)
    app_version = Column(String(50), nullable=True)

    # Action taken
    action_taken = Column(String(100), nullable=True)  # checked_in, viewed_event, etc.

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_qr_code_scans_qr_scanned', 'qr_code_id', 'scanned_at'),
        Index('ix_qr_code_scans_user', 'user_id'),
    )


# ============================================================================
# Mobile Wallet Models
# ============================================================================

class MobileWalletPass(Base):
    """
    Mobile wallet passes (Apple Wallet, Google Pay).

    Generate and manage wallet passes for tickets, loyalty cards, etc.
    """
    __tablename__ = "mobile_wallet_passes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User and device
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="SET NULL"), nullable=True)

    # Provider
    provider = Column(String(50), nullable=False, index=True)  # MobileWalletProvider

    # Pass identity
    pass_type_id = Column(String(255), nullable=False)  # com.celebratech.event.ticket
    serial_number = Column(String(255), unique=True, nullable=False, index=True)

    # Target entity
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Pass data
    pass_data = Column(JSON, nullable=False)  # Complete pass structure

    # Visual
    logo_url = Column(String(500), nullable=True)
    background_image_url = Column(String(500), nullable=True)
    icon_url = Column(String(500), nullable=True)
    strip_image_url = Column(String(500), nullable=True)

    # Colors
    foreground_color = Column(String(7), nullable=True)
    background_color = Column(String(7), nullable=True)
    label_color = Column(String(7), nullable=True)

    # Barcodes
    barcode_format = Column(String(50), nullable=True)  # QR, Aztec, PDF417
    barcode_message = Column(String(500), nullable=True)

    # Updates
    supports_updates = Column(Boolean, default=True)
    last_updated_at = Column(DateTime, nullable=True)

    # Installation
    is_installed = Column(Boolean, default=False)
    installed_at = Column(DateTime, nullable=True)
    uninstalled_at = Column(DateTime, nullable=True)

    # Expiration
    relevant_date = Column(DateTime, nullable=True)  # When pass is relevant
    expiration_date = Column(DateTime, nullable=True)

    # Location relevance
    locations = Column(JSON, nullable=True)  # [{lat, lon, radius}]

    # Status
    is_active = Column(Boolean, default=True)
    is_voided = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        Index('ix_mobile_wallet_passes_user', 'user_id'),
        Index('ix_mobile_wallet_passes_entity', 'entity_type', 'entity_id'),
        Index('ix_mobile_wallet_passes_provider', 'provider'),
    )


# ============================================================================
# Camera & Media Models
# ============================================================================

class MobileMediaUpload(Base):
    """
    Mobile media uploads from camera or gallery.

    Track photos/videos uploaded from mobile devices.
    """
    __tablename__ = "mobile_media_uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User and device
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="SET NULL"), nullable=True)

    # Media info
    media_type = Column(String(50), nullable=False)  # photo, video, live_photo
    file_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)

    # File details
    file_size = Column(Integer, nullable=True)  # Bytes
    mime_type = Column(String(100), nullable=True)
    file_name = Column(String(255), nullable=True)

    # Dimensions
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # For videos

    # Source
    source = Column(String(50), nullable=False)  # camera, gallery, screenshot
    camera_position = Column(String(20), nullable=True)  # front, back

    # Location (if permitted)
    location_data = Column(JSON, nullable=True)  # {lat, lon, altitude}

    # EXIF data
    exif_data = Column(JSON, nullable=True)

    # Compression
    is_compressed = Column(Boolean, default=False)
    original_size = Column(Integer, nullable=True)

    # Associated entity
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Processing
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50), nullable=True)

    # Metadata
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_mobile_media_uploads_user_uploaded', 'user_id', 'uploaded_at'),
        Index('ix_mobile_media_uploads_entity', 'entity_type', 'entity_id'),
    )


# ============================================================================
# Biometric Authentication Models
# ============================================================================

class BiometricAuth(Base):
    """
    Biometric authentication tracking.

    Track biometric authentication usage and security.
    """
    __tablename__ = "biometric_auth"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User and device
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="CASCADE"), nullable=False, index=True)

    # Biometric type
    biometric_type = Column(String(50), nullable=False)  # BiometricType

    # Settings
    is_enabled = Column(Boolean, default=False)
    enabled_at = Column(DateTime, nullable=True)
    disabled_at = Column(DateTime, nullable=True)

    # Security
    public_key = Column(Text, nullable=True)  # For key-based biometrics
    last_authenticated_at = Column(DateTime, nullable=True)

    # Usage stats
    auth_count = Column(Integer, default=0)
    failed_attempts = Column(Integer, default=0)
    last_failed_at = Column(DateTime, nullable=True)

    # Lockout
    is_locked = Column(Boolean, default=False)
    locked_until = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'device_id', 'biometric_type', name='uq_biometric_auth'),
        Index('ix_biometric_auth_user_device', 'user_id', 'device_id'),
    )


# ============================================================================
# Location Features Models
# ============================================================================

class MobileLocation(Base):
    """
    Mobile location tracking (with user consent).

    Track user locations for location-based features.
    """
    __tablename__ = "mobile_locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User and device
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="CASCADE"), nullable=False, index=True)

    # Location data
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)  # Meters
    heading = Column(Float, nullable=True)  # Degrees
    speed = Column(Float, nullable=True)  # m/s

    # Geocoded address
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)
    postal_code = Column(String(20), nullable=True)

    # Context
    permission_level = Column(String(50), nullable=False)  # LocationPermissionLevel
    source = Column(String(50), nullable=True)  # gps, network, manual

    # Associated entity (e.g., check-in at venue)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Timestamp
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_mobile_locations_user_recorded', 'user_id', 'recorded_at'),
        Index('ix_mobile_locations_coords', 'latitude', 'longitude'),
        Index('ix_mobile_locations_city', 'city'),
    )


class Geofence(Base):
    """
    Geofencing for location-based triggers.

    Define geographic boundaries for notifications and actions.
    """
    __tablename__ = "geofences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Geofence identity
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Center point
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_meters = Column(Float, nullable=False)

    # Associated entity
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Triggers
    trigger_on_entry = Column(Boolean, default=True)
    trigger_on_exit = Column(Boolean, default=False)
    trigger_on_dwell = Column(Boolean, default=False)
    dwell_time_seconds = Column(Integer, nullable=True)

    # Actions
    actions = Column(JSON, nullable=True)  # [{type, params}]

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Schedule
    active_from = Column(DateTime, nullable=True)
    active_until = Column(DateTime, nullable=True)

    # Stats
    entry_count = Column(Integer, default=0)
    exit_count = Column(Integer, default=0)

    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('ix_geofences_entity', 'entity_type', 'entity_id'),
        Index('ix_geofences_coords', 'latitude', 'longitude'),
        Index('ix_geofences_active', 'is_active'),
    )


# ============================================================================
# Mobile Sharing Models
# ============================================================================

class MobileShare(Base):
    """
    Mobile sharing activity tracking.

    Track when users share content via mobile.
    """
    __tablename__ = "mobile_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User and device
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="SET NULL"), nullable=True)

    # Shared content
    content_type = Column(String(50), nullable=False, index=True)
    content_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Share method
    share_method = Column(String(50), nullable=False, index=True)  # ShareMethod

    # Share data
    share_text = Column(Text, nullable=True)
    share_url = Column(String(500), nullable=True)
    share_image_url = Column(String(500), nullable=True)

    # Recipient info (if available)
    recipient_info = Column(JSON, nullable=True)

    # Success
    was_successful = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # Tracking
    shared_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_mobile_shares_user_shared', 'user_id', 'shared_at'),
        Index('ix_mobile_shares_content', 'content_type', 'content_id'),
        Index('ix_mobile_shares_method', 'share_method'),
    )


# ============================================================================
# Mobile Widget Models
# ============================================================================

class MobileWidget(Base):
    """
    Mobile home screen widgets.

    Manage user's installed widgets.
    """
    __tablename__ = "mobile_widgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User and device
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="CASCADE"), nullable=False, index=True)

    # Widget info
    widget_type = Column(String(50), nullable=False, index=True)  # WidgetType
    widget_family = Column(String(50), nullable=True)  # small, medium, large, extraLarge

    # Configuration
    config = Column(JSON, nullable=True)  # Widget-specific config

    # Target entity (if applicable)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Refresh
    last_refreshed_at = Column(DateTime, nullable=True)
    refresh_count = Column(Integer, default=0)

    # Interaction
    tap_count = Column(Integer, default=0)
    last_tapped_at = Column(DateTime, nullable=True)

    # Metadata
    installed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        Index('ix_mobile_widgets_user_device', 'user_id', 'device_id'),
        Index('ix_mobile_widgets_type', 'widget_type'),
    )


# ============================================================================
# Quick Actions Models
# ============================================================================

class QuickAction(Base):
    """
    App icon quick actions (3D Touch, Long Press).

    Define and track quick action usage.
    """
    __tablename__ = "quick_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Action info
    action_type = Column(String(50), nullable=False, index=True)  # QuickActionType
    action_title = Column(String(100), nullable=False)
    action_subtitle = Column(String(200), nullable=True)
    action_icon = Column(String(100), nullable=True)

    # Platform
    platform = Column(String(50), nullable=False)  # ios, android

    # Action data
    action_data = Column(JSON, nullable=True)

    # Deep link
    deep_link = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Pre-installed action

    # Priority
    priority = Column(Integer, default=0)  # Display order

    # Usage stats
    use_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('ix_quick_actions_type', 'action_type'),
        Index('ix_quick_actions_platform', 'platform'),
    )


class QuickActionUsage(Base):
    """
    Quick action usage tracking.

    Track when users use quick actions.
    """
    __tablename__ = "quick_action_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Quick action reference
    quick_action_id = Column(UUID(as_uuid=True), ForeignKey("quick_actions.id", ondelete="CASCADE"), nullable=False, index=True)

    # User and device
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mobile_devices.id", ondelete="SET NULL"), nullable=True)

    # Usage
    used_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Outcome
    action_completed = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_quick_action_usage_action_used', 'quick_action_id', 'used_at'),
        Index('ix_quick_action_usage_user', 'user_id'),
    )
