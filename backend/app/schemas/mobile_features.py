"""
Mobile App Features Schemas
Sprint 19: Mobile App Features

Pydantic schemas for advanced mobile features including QR codes,
mobile wallet, camera integration, biometrics, location features,
sharing, widgets, and quick actions.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# QR Code Schemas
# ============================================================================

class QRCodeCreate(BaseModel):
    """Schema for creating QR code"""
    qr_type: str
    entity_type: str
    entity_id: UUID
    qr_data: Dict[str, Any]
    display_text: Optional[str] = None
    foreground_color: str = Field("#000000", regex="^#[0-9A-Fa-f]{6}$")
    background_color: str = Field("#FFFFFF", regex="^#[0-9A-Fa-f]{6}$")
    error_correction: str = Field("M", regex="^[LMQH]$")
    image_size: Optional[int] = Field(500, gt=0, le=2000)
    expires_at: Optional[datetime] = None
    requires_authentication: bool = False
    max_scans: Optional[int] = Field(None, gt=0)


class QRCodeResponse(BaseModel):
    """Schema for QR code response"""
    id: UUID
    qr_code: str
    qr_type: str
    entity_type: str
    entity_id: UUID
    qr_data: Dict[str, Any]
    display_text: Optional[str]
    image_url: Optional[str]
    image_size: Optional[int]
    foreground_color: str
    background_color: str
    expires_at: Optional[datetime]
    is_active: bool
    scan_count: int
    last_scanned_at: Optional[datetime]
    unique_scanners: int
    requires_authentication: bool
    max_scans: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QRCodeScanCreate(BaseModel):
    """Schema for recording QR scan"""
    qr_code: str
    location_data: Optional[Dict[str, Any]] = None
    action_taken: Optional[str] = None


class QRCodeScanResponse(BaseModel):
    """Schema for QR scan response"""
    id: UUID
    qr_code_id: UUID
    user_id: Optional[UUID]
    device_id: Optional[UUID]
    scanned_at: datetime
    location_data: Optional[Dict[str, Any]]
    action_taken: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class QRCodeAnalytics(BaseModel):
    """Schema for QR code analytics"""
    qr_code_id: UUID
    total_scans: int
    unique_scanners: int
    scan_trend: List[Dict[str, Any]]
    top_locations: List[Dict[str, Any]]
    recent_scans: List[QRCodeScanResponse]


# ============================================================================
# Mobile Wallet Schemas
# ============================================================================

class MobileWalletPassCreate(BaseModel):
    """Schema for creating wallet pass"""
    provider: str
    pass_type_id: str
    entity_type: str
    entity_id: UUID
    pass_data: Dict[str, Any]
    logo_url: Optional[str] = None
    background_image_url: Optional[str] = None
    icon_url: Optional[str] = None
    foreground_color: Optional[str] = Field(None, regex="^#[0-9A-Fa-f]{6}$")
    background_color: Optional[str] = Field(None, regex="^#[0-9A-Fa-f]{6}$")
    barcode_format: Optional[str] = None
    barcode_message: Optional[str] = None
    relevant_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    locations: Optional[List[Dict[str, float]]] = None


class MobileWalletPassResponse(BaseModel):
    """Schema for wallet pass response"""
    id: UUID
    user_id: UUID
    device_id: Optional[UUID]
    provider: str
    pass_type_id: str
    serial_number: str
    entity_type: str
    entity_id: UUID
    pass_data: Dict[str, Any]
    logo_url: Optional[str]
    background_image_url: Optional[str]
    icon_url: Optional[str]
    foreground_color: Optional[str]
    background_color: Optional[str]
    barcode_format: Optional[str]
    barcode_message: Optional[str]
    is_installed: bool
    installed_at: Optional[datetime]
    relevant_date: Optional[datetime]
    expiration_date: Optional[datetime]
    is_active: bool
    is_voided: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WalletPassUpdate(BaseModel):
    """Schema for updating wallet pass"""
    pass_data: Optional[Dict[str, Any]] = None
    is_voided: Optional[bool] = None


# ============================================================================
# Camera & Media Schemas
# ============================================================================

class MobileMediaUploadCreate(BaseModel):
    """Schema for media upload"""
    media_type: str
    file_url: str
    thumbnail_url: Optional[str] = None
    file_size: Optional[int] = Field(None, gt=0)
    mime_type: Optional[str] = None
    file_name: Optional[str] = None
    width: Optional[int] = Field(None, gt=0)
    height: Optional[int] = Field(None, gt=0)
    duration_seconds: Optional[int] = Field(None, gt=0)
    source: str
    camera_position: Optional[str] = None
    location_data: Optional[Dict[str, Any]] = None
    exif_data: Optional[Dict[str, Any]] = None
    is_compressed: bool = False
    original_size: Optional[int] = None
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None


class MobileMediaUploadResponse(BaseModel):
    """Schema for media upload response"""
    id: UUID
    user_id: UUID
    device_id: Optional[UUID]
    media_type: str
    file_url: str
    thumbnail_url: Optional[str]
    file_size: Optional[int]
    mime_type: Optional[str]
    width: Optional[int]
    height: Optional[int]
    duration_seconds: Optional[int]
    source: str
    location_data: Optional[Dict[str, Any]]
    is_compressed: bool
    original_size: Optional[int]
    entity_type: Optional[str]
    entity_id: Optional[UUID]
    is_processed: bool
    processing_status: Optional[str]
    uploaded_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Biometric Authentication Schemas
# ============================================================================

class BiometricAuthEnable(BaseModel):
    """Schema for enabling biometric auth"""
    device_id: UUID
    biometric_type: str
    public_key: Optional[str] = None


class BiometricAuthResponse(BaseModel):
    """Schema for biometric auth response"""
    id: UUID
    user_id: UUID
    device_id: UUID
    biometric_type: str
    is_enabled: bool
    enabled_at: Optional[datetime]
    last_authenticated_at: Optional[datetime]
    auth_count: int
    failed_attempts: int
    is_locked: bool
    locked_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BiometricAuthVerify(BaseModel):
    """Schema for biometric verification"""
    device_id: UUID
    biometric_type: str
    challenge: str
    signature: str


# ============================================================================
# Location Features Schemas
# ============================================================================

class MobileLocationCreate(BaseModel):
    """Schema for recording location"""
    device_id: UUID
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: Optional[float] = None
    accuracy: Optional[float] = Field(None, ge=0)
    heading: Optional[float] = Field(None, ge=0, lt=360)
    speed: Optional[float] = Field(None, ge=0)
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    permission_level: str
    source: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None


class MobileLocationResponse(BaseModel):
    """Schema for location response"""
    id: UUID
    user_id: UUID
    device_id: UUID
    latitude: float
    longitude: float
    altitude: Optional[float]
    accuracy: Optional[float]
    heading: Optional[float]
    speed: Optional[float]
    address: Optional[str]
    city: Optional[str]
    country: Optional[str]
    permission_level: str
    source: Optional[str]
    entity_type: Optional[str]
    entity_id: Optional[UUID]
    recorded_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class GeofenceCreate(BaseModel):
    """Schema for creating geofence"""
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_meters: float = Field(..., gt=0)
    entity_type: str
    entity_id: UUID
    trigger_on_entry: bool = True
    trigger_on_exit: bool = False
    trigger_on_dwell: bool = False
    dwell_time_seconds: Optional[int] = Field(None, gt=0)
    actions: Optional[List[Dict[str, Any]]] = None
    active_from: Optional[datetime] = None
    active_until: Optional[datetime] = None


class GeofenceResponse(BaseModel):
    """Schema for geofence response"""
    id: UUID
    name: str
    description: Optional[str]
    latitude: float
    longitude: float
    radius_meters: float
    entity_type: str
    entity_id: UUID
    trigger_on_entry: bool
    trigger_on_exit: bool
    trigger_on_dwell: bool
    dwell_time_seconds: Optional[int]
    actions: Optional[List[Dict[str, Any]]]
    is_active: bool
    active_from: Optional[datetime]
    active_until: Optional[datetime]
    entry_count: int
    exit_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GeofenceEvent(BaseModel):
    """Schema for geofence event"""
    geofence_id: UUID
    event_type: str = Field(..., regex="^(entry|exit|dwell)$")
    device_id: UUID
    location_data: Dict[str, float]


# ============================================================================
# Mobile Sharing Schemas
# ============================================================================

class MobileShareCreate(BaseModel):
    """Schema for recording share"""
    device_id: UUID
    content_type: str
    content_id: UUID
    share_method: str
    share_text: Optional[str] = None
    share_url: Optional[str] = None
    share_image_url: Optional[str] = None
    recipient_info: Optional[Dict[str, Any]] = None
    was_successful: bool = True
    error_message: Optional[str] = None


class MobileShareResponse(BaseModel):
    """Schema for share response"""
    id: UUID
    user_id: UUID
    device_id: Optional[UUID]
    content_type: str
    content_id: UUID
    share_method: str
    share_text: Optional[str]
    share_url: Optional[str]
    was_successful: bool
    shared_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ShareAnalytics(BaseModel):
    """Schema for share analytics"""
    total_shares: int
    shares_by_method: Dict[str, int]
    shares_by_content_type: Dict[str, int]
    success_rate: float
    trending_shares: List[Dict[str, Any]]


# ============================================================================
# Mobile Widget Schemas
# ============================================================================

class MobileWidgetCreate(BaseModel):
    """Schema for creating widget"""
    device_id: UUID
    widget_type: str
    widget_family: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None


class MobileWidgetUpdate(BaseModel):
    """Schema for updating widget"""
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class MobileWidgetResponse(BaseModel):
    """Schema for widget response"""
    id: UUID
    user_id: UUID
    device_id: UUID
    widget_type: str
    widget_family: Optional[str]
    config: Optional[Dict[str, Any]]
    entity_type: Optional[str]
    entity_id: Optional[UUID]
    is_active: bool
    last_refreshed_at: Optional[datetime]
    refresh_count: int
    tap_count: int
    last_tapped_at: Optional[datetime]
    installed_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WidgetRefreshRequest(BaseModel):
    """Schema for widget refresh"""
    widget_id: UUID


class WidgetRefreshResponse(BaseModel):
    """Schema for widget refresh response"""
    widget_id: UUID
    widget_data: Dict[str, Any]
    last_refreshed_at: datetime


# ============================================================================
# Quick Actions Schemas
# ============================================================================

class QuickActionCreate(BaseModel):
    """Schema for creating quick action"""
    action_type: str
    action_title: str = Field(..., max_length=100)
    action_subtitle: Optional[str] = Field(None, max_length=200)
    action_icon: Optional[str] = None
    platform: str
    action_data: Optional[Dict[str, Any]] = None
    deep_link: Optional[str] = None
    priority: int = Field(0)


class QuickActionUpdate(BaseModel):
    """Schema for updating quick action"""
    action_title: Optional[str] = Field(None, max_length=100)
    action_subtitle: Optional[str] = Field(None, max_length=200)
    action_icon: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class QuickActionResponse(BaseModel):
    """Schema for quick action response"""
    id: UUID
    action_type: str
    action_title: str
    action_subtitle: Optional[str]
    action_icon: Optional[str]
    platform: str
    action_data: Optional[Dict[str, Any]]
    deep_link: Optional[str]
    is_active: bool
    is_default: bool
    priority: int
    use_count: int
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuickActionUsageCreate(BaseModel):
    """Schema for recording quick action usage"""
    quick_action_id: UUID
    device_id: UUID
    action_completed: bool = False


class QuickActionAnalytics(BaseModel):
    """Schema for quick action analytics"""
    total_uses: int
    most_used_actions: List[Dict[str, Any]]
    completion_rate: float
    platform_distribution: Dict[str, int]


# ============================================================================
# Combined Feature Schemas
# ============================================================================

class MobileFeaturesStatus(BaseModel):
    """Schema for mobile features status"""
    user_id: UUID
    device_id: UUID
    biometric_enabled: bool
    location_permission: str
    camera_permission: bool
    notifications_enabled: bool
    widgets_count: int
    wallet_passes_count: int
    quick_actions_available: List[QuickActionResponse]


class MobileCapabilities(BaseModel):
    """Schema for device capabilities"""
    has_camera: bool
    has_biometric: bool
    has_nfc: bool
    has_ar: bool
    has_wallet: bool
    location_services: bool
    push_notifications: bool


# ============================================================================
# Bulk Operations Schemas
# ============================================================================

class BulkQRCodeGenerate(BaseModel):
    """Schema for bulk QR code generation"""
    codes: List[QRCodeCreate]


class BulkGeofenceCreate(BaseModel):
    """Schema for bulk geofence creation"""
    geofences: List[GeofenceCreate]
