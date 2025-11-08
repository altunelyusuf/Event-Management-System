"""
Mobile App Features API
Sprint 19: Mobile App Features

API endpoints for advanced mobile features including QR codes,
wallet passes, biometrics, geofencing, sharing, widgets, and quick actions.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_user_optional
from app.models.user import User
from app.services.mobile_features_service import MobileFeaturesService
from app.schemas.mobile_features import (
    # QR Code schemas
    QRCodeCreate, QRCodeResponse, QRCodeScanCreate, QRCodeAnalytics,
    # Wallet Pass schemas
    MobileWalletPassCreate, MobileWalletPassResponse, WalletPassUpdate,
    # Media schemas
    MobileMediaUploadCreate, MobileMediaUploadResponse,
    # Biometric schemas
    BiometricAuthEnable, BiometricAuthResponse, BiometricAuthVerify,
    # Location schemas
    MobileLocationCreate, MobileLocationResponse,
    # Geofence schemas
    GeofenceCreate, GeofenceResponse, GeofenceEvent,
    # Share schemas
    MobileShareCreate, MobileShareResponse, ShareAnalytics,
    # Widget schemas
    MobileWidgetCreate, MobileWidgetUpdate, MobileWidgetResponse,
    WidgetRefreshRequest, WidgetRefreshResponse,
    # Quick Action schemas
    QuickActionCreate, QuickActionUpdate, QuickActionResponse,
    QuickActionUsageCreate, QuickActionAnalytics
)

router = APIRouter(prefix="/mobile-features", tags=["mobile-features"])


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_mobile_features_service(db: AsyncSession = Depends(get_db)) -> MobileFeaturesService:
    """Get mobile features service instance"""
    return MobileFeaturesService(db)


# ============================================================================
# QR Code Endpoints
# ============================================================================

@router.post("/qr-codes", response_model=QRCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_qr_code(
    qr_data: QRCodeCreate,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """
    Generate a QR code for an entity.

    Supports multiple QR code types:
    - event: Link to event details
    - ticket: Event ticket/admission
    - check_in: Check-in/attendance tracking
    - payment: Payment QR code
    - contact: Share contact info
    - custom: Custom data
    """
    return await features_service.create_qr_code(qr_data, current_user)


@router.get("/qr-codes/{qr_code_id}", response_model=QRCodeResponse)
async def get_qr_code(
    qr_code_id: UUID,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Get QR code details by ID"""
    return await features_service.get_qr_code(qr_code_id, current_user)


@router.get("/qr-codes/entity/{entity_type}/{entity_id}", response_model=List[QRCodeResponse])
async def get_entity_qr_codes(
    entity_type: str,
    entity_id: UUID,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Get all QR codes for a specific entity"""
    return await features_service.get_entity_qr_codes(entity_type, entity_id, current_user)


@router.post("/qr-codes/scan")
async def scan_qr_code(
    scan_data: QRCodeScanCreate,
    device_id: Optional[UUID] = None,
    platform: Optional[str] = None,
    app_version: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """
    Scan a QR code and return its data.

    Records the scan for analytics and returns the QR code payload.
    Some QR codes may require authentication.
    """
    return await features_service.scan_qr_code(
        scan_data,
        current_user,
        device_id=device_id,
        platform=platform,
        app_version=app_version
    )


@router.get("/qr-codes/{qr_code_id}/analytics", response_model=QRCodeAnalytics)
async def get_qr_analytics(
    qr_code_id: UUID,
    days_back: int = 30,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Get analytics for a QR code"""
    return await features_service.get_qr_analytics(qr_code_id, current_user, days_back)


# ============================================================================
# Wallet Pass Endpoints
# ============================================================================

@router.post("/wallet-passes", response_model=MobileWalletPassResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet_pass(
    pass_data: MobileWalletPassCreate,
    device_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """
    Create a mobile wallet pass (Apple Wallet / Google Pay).

    Wallet passes can be used for:
    - Event tickets
    - Loyalty cards
    - Coupons/vouchers
    - Boarding passes
    """
    return await features_service.create_wallet_pass(pass_data, current_user, device_id)


@router.get("/wallet-passes", response_model=List[MobileWalletPassResponse])
async def get_user_wallet_passes(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Get all wallet passes for current user"""
    return await features_service.get_user_wallet_passes(current_user, active_only)


@router.get("/wallet-passes/{pass_id}", response_model=MobileWalletPassResponse)
async def get_wallet_pass(
    pass_id: UUID,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Get wallet pass by ID"""
    return await features_service.get_wallet_pass(pass_id, current_user)


@router.post("/wallet-passes/{pass_id}/install", response_model=MobileWalletPassResponse)
async def mark_pass_installed(
    pass_id: UUID,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Mark wallet pass as installed on device"""
    return await features_service.mark_pass_installed(pass_id, current_user)


@router.put("/wallet-passes/{pass_id}", response_model=MobileWalletPassResponse)
async def update_wallet_pass(
    pass_id: UUID,
    pass_update: WalletPassUpdate,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Update wallet pass data"""
    return await features_service.update_wallet_pass(pass_id, pass_update, current_user)


# ============================================================================
# Media Upload Endpoints
# ============================================================================

@router.post("/media", response_model=MobileMediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    media_data: MobileMediaUploadCreate,
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """
    Record a media upload from mobile camera or gallery.

    Supports:
    - Photos
    - Videos
    - Live photos
    """
    return await features_service.create_media_upload(media_data, current_user, device_id)


@router.get("/media", response_model=List[MobileMediaUploadResponse])
async def get_user_media(
    media_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Get media uploads for current user"""
    media_list, _ = await features_service.get_user_media_uploads(
        current_user,
        media_type=media_type,
        skip=skip,
        limit=limit
    )
    return media_list


# ============================================================================
# Biometric Auth Endpoints
# ============================================================================

@router.post("/biometric/enable", response_model=BiometricAuthResponse)
async def enable_biometric(
    biometric_data: BiometricAuthEnable,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """
    Enable biometric authentication for device.

    Supports:
    - Face ID (iOS)
    - Touch ID (iOS)
    - Fingerprint (Android)
    - Iris scan
    """
    return await features_service.enable_biometric(biometric_data, current_user)


@router.get("/biometric/device/{device_id}", response_model=List[BiometricAuthResponse])
async def get_device_biometrics(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Get biometric authentication settings for device"""
    return await features_service.get_device_biometrics(device_id, current_user)


@router.post("/biometric/verify")
async def verify_biometric(
    verify_data: BiometricAuthVerify,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Verify a biometric authentication attempt"""
    return await features_service.verify_biometric(verify_data, current_user)


@router.delete("/biometric/{biometric_id}")
async def disable_biometric(
    biometric_id: UUID,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Disable biometric authentication"""
    return await features_service.disable_biometric(biometric_id, current_user)


# ============================================================================
# Location Endpoints
# ============================================================================

@router.post("/location", response_model=MobileLocationResponse, status_code=status.HTTP_201_CREATED)
async def record_location(
    location_data: MobileLocationCreate,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """
    Record user location (with consent).

    Used for:
    - Event check-ins
    - Location-based recommendations
    - Geofence triggers
    """
    return await features_service.record_location(location_data, current_user)


@router.get("/location/history", response_model=List[MobileLocationResponse])
async def get_location_history(
    days_back: int = 7,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Get user's location history"""
    return await features_service.get_location_history(current_user, days_back)


# ============================================================================
# Geofence Endpoints
# ============================================================================

@router.post("/geofences", response_model=GeofenceResponse, status_code=status.HTTP_201_CREATED)
async def create_geofence(
    geofence_data: GeofenceCreate,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """
    Create a geofence for location-based triggers.

    Geofences can trigger on:
    - Entry: User enters the area
    - Exit: User leaves the area
    - Dwell: User stays in area for specified time
    """
    return await features_service.create_geofence(geofence_data, current_user)


@router.get("/geofences/{entity_type}/{entity_id}", response_model=List[GeofenceResponse])
async def get_entity_geofences(
    entity_type: str,
    entity_id: UUID,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Get all geofences for an entity"""
    return await features_service.get_entity_geofences(entity_type, entity_id, current_user)


@router.post("/geofences/trigger")
async def trigger_geofence(
    event_data: GeofenceEvent,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Trigger a geofence event (entry/exit/dwell)"""
    return await features_service.trigger_geofence_event(event_data, current_user)


# ============================================================================
# Sharing Endpoints
# ============================================================================

@router.post("/share", response_model=MobileShareResponse, status_code=status.HTTP_201_CREATED)
async def share_content(
    share_data: MobileShareCreate,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """
    Record a content share via mobile.

    Share methods:
    - Native share sheet
    - WhatsApp, Instagram, Facebook, Twitter
    - Email, SMS
    - Copy link
    """
    return await features_service.record_share(share_data, current_user)


@router.get("/share/analytics", response_model=ShareAnalytics)
async def get_share_analytics(
    content_type: Optional[str] = None,
    days_back: int = 30,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Get sharing analytics"""
    return await features_service.get_share_analytics(current_user, content_type, days_back)


# ============================================================================
# Widget Endpoints
# ============================================================================

@router.post("/widgets", response_model=MobileWidgetResponse, status_code=status.HTTP_201_CREATED)
async def install_widget(
    widget_data: MobileWidgetCreate,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """
    Install a home screen widget.

    Widget types:
    - upcoming_events: Show upcoming events
    - countdown: Countdown to event
    - task_list: Quick task list
    - budget_summary: Budget overview
    - quick_action: Quick action buttons
    """
    return await features_service.install_widget(widget_data, current_user)


@router.get("/widgets/device/{device_id}", response_model=List[MobileWidgetResponse])
async def get_device_widgets(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Get widgets installed on device"""
    return await features_service.get_device_widgets(device_id, current_user)


@router.post("/widgets/{widget_id}/refresh", response_model=WidgetRefreshResponse)
async def refresh_widget(
    widget_id: UUID,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Refresh widget data"""
    return await features_service.refresh_widget(widget_id, current_user)


@router.put("/widgets/{widget_id}", response_model=MobileWidgetResponse)
async def update_widget(
    widget_id: UUID,
    widget_update: MobileWidgetUpdate,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Update widget configuration"""
    return await features_service.update_widget(widget_id, widget_update, current_user)


@router.delete("/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def uninstall_widget(
    widget_id: UUID,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Uninstall a widget"""
    await features_service.uninstall_widget(widget_id, current_user)


# ============================================================================
# Quick Action Endpoints
# ============================================================================

@router.post("/quick-actions", response_model=QuickActionResponse, status_code=status.HTTP_201_CREATED)
async def create_quick_action(
    action_data: QuickActionCreate,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """
    Create a quick action (admin only).

    Quick actions appear in:
    - 3D Touch menu (iOS)
    - Long-press menu (Android)
    - App shortcuts
    """
    return await features_service.create_quick_action(action_data, current_user)


@router.get("/quick-actions/{platform}", response_model=List[QuickActionResponse])
async def get_quick_actions(
    platform: str,
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Get available quick actions for platform"""
    return await features_service.get_platform_quick_actions(platform)


@router.post("/quick-actions/use")
async def use_quick_action(
    usage_data: QuickActionUsageCreate,
    current_user: User = Depends(get_current_user),
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Record quick action usage"""
    return await features_service.use_quick_action(usage_data, current_user)


@router.get("/quick-actions/analytics", response_model=QuickActionAnalytics)
async def get_quick_action_analytics(
    days_back: int = 30,
    features_service: MobileFeaturesService = Depends(get_mobile_features_service)
):
    """Get quick action analytics"""
    return await features_service.get_quick_action_analytics(days_back)


# ============================================================================
# Health & Diagnostics Endpoints
# ============================================================================

@router.get("/health")
async def health_check():
    """Mobile features health check"""
    return {
        "status": "healthy",
        "service": "mobile-features",
        "features": {
            "qr_codes": True,
            "wallet_passes": True,
            "camera": True,
            "biometric": True,
            "location": True,
            "geofencing": True,
            "sharing": True,
            "widgets": True,
            "quick_actions": True
        }
    }


@router.get("/capabilities")
async def get_capabilities(
    current_user: User = Depends(get_current_user)
):
    """
    Get available mobile features and capabilities.

    Returns what features are enabled for the user/platform.
    """
    return {
        "qr_codes": {
            "enabled": True,
            "max_codes_per_entity": 10,
            "supported_types": ["event", "ticket", "check_in", "payment", "contact", "custom"]
        },
        "wallet_passes": {
            "enabled": True,
            "providers": ["apple_pay", "google_pay", "samsung_pay"]
        },
        "biometric": {
            "enabled": True,
            "supported_types": ["face_id", "touch_id", "fingerprint", "iris"]
        },
        "geofencing": {
            "enabled": True,
            "max_geofences_per_entity": 5,
            "max_radius_meters": 10000
        },
        "widgets": {
            "enabled": True,
            "supported_types": ["upcoming_events", "countdown", "task_list", "budget_summary", "quick_action"]
        },
        "quick_actions": {
            "enabled": True,
            "max_actions": 4
        }
    }
