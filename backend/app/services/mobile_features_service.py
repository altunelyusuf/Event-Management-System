"""
Mobile App Features Service
Sprint 19: Mobile App Features

Service layer for advanced mobile features including QR codes,
wallet passes, biometrics, geofencing, sharing, widgets, and quick actions.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
import logging
import math

from app.repositories.mobile_features_repository import MobileFeaturesRepository
from app.models.user import User
from app.schemas.mobile_features import (
    # QR Code schemas
    QRCodeCreate, QRCodeResponse, QRCodeScanCreate, QRCodeScanResponse, QRCodeAnalytics,
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

logger = logging.getLogger(__name__)


class MobileFeaturesService:
    """Service for advanced mobile features"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.features_repo = MobileFeaturesRepository(db)

    # ========================================================================
    # QR Code Operations
    # ========================================================================

    async def create_qr_code(
        self,
        qr_data: QRCodeCreate,
        current_user: User
    ) -> QRCodeResponse:
        """
        Create a QR code for an entity.

        QR codes can be generated for events, tickets, check-ins, etc.
        """
        qr_code = await self.features_repo.create_qr_code(qr_data, current_user.id)
        await self.db.commit()
        await self.db.refresh(qr_code)

        # In production, generate actual QR code image and upload to storage
        # image_url = await generate_qr_image(qr_code.qr_code, qr_code.foreground_color, qr_code.background_color)
        # qr_code.image_url = image_url

        return QRCodeResponse.from_orm(qr_code)

    async def get_qr_code(
        self,
        qr_code_id: UUID,
        current_user: User
    ) -> QRCodeResponse:
        """Get QR code by ID"""
        qr_code = await self.features_repo.get_qr_code_by_id(qr_code_id)

        if not qr_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR code not found"
            )

        # Verify user has access (simplified - in production check entity permissions)
        if qr_code.created_by != current_user.id:
            # Check if user has access to the entity
            pass

        return QRCodeResponse.from_orm(qr_code)

    async def get_entity_qr_codes(
        self,
        entity_type: str,
        entity_id: UUID,
        current_user: User
    ) -> List[QRCodeResponse]:
        """Get all QR codes for an entity"""
        qr_codes = await self.features_repo.get_qr_codes_by_entity(entity_type, entity_id)
        return [QRCodeResponse.from_orm(qr) for qr in qr_codes]

    async def scan_qr_code(
        self,
        scan_data: QRCodeScanCreate,
        current_user: User,
        device_id: Optional[UUID] = None,
        platform: Optional[str] = None,
        app_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a QR code scan.

        Returns the QR code data and records the scan for analytics.
        """
        qr_code = await self.features_repo.get_qr_code_by_string(scan_data.qr_code)

        if not qr_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR code not found"
            )

        # Check if expired
        if qr_code.expires_at and qr_code.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="QR code has expired"
            )

        # Check if active
        if not qr_code.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="QR code is no longer active"
            )

        # Check max scans
        if qr_code.max_scans and qr_code.scan_count >= qr_code.max_scans:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="QR code has reached maximum scans"
            )

        # Check authentication requirement
        if qr_code.requires_authentication and not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to scan this QR code"
            )

        # Record the scan
        await self.features_repo.record_qr_scan(
            qr_code.id,
            current_user.id if current_user else None,
            device_id,
            scan_data.location_data,
            scan_data.action_taken,
            platform,
            app_version
        )

        await self.db.commit()

        return {
            "qr_code_id": qr_code.id,
            "qr_type": qr_code.qr_type,
            "entity_type": qr_code.entity_type,
            "entity_id": qr_code.entity_id,
            "qr_data": qr_code.qr_data,
            "display_text": qr_code.display_text
        }

    async def get_qr_analytics(
        self,
        qr_code_id: UUID,
        current_user: User,
        days_back: int = 30
    ) -> QRCodeAnalytics:
        """Get QR code scan analytics"""
        qr_code = await self.features_repo.get_qr_code_by_id(qr_code_id)

        if not qr_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR code not found"
            )

        # Verify ownership
        if qr_code.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view analytics"
            )

        analytics = await self.features_repo.get_qr_scan_analytics(qr_code_id, days_back)

        return QRCodeAnalytics(
            qr_code_id=qr_code_id,
            total_scans=analytics["total_scans"],
            unique_scanners=analytics["unique_scanners"],
            scan_trend=analytics["scan_trend"],
            top_locations=analytics["top_locations"],
            recent_scans=[QRCodeScanResponse.from_orm(s) for s in analytics["recent_scans"]]
        )

    # ========================================================================
    # Wallet Pass Operations
    # ========================================================================

    async def create_wallet_pass(
        self,
        pass_data: MobileWalletPassCreate,
        current_user: User,
        device_id: Optional[UUID] = None
    ) -> MobileWalletPassResponse:
        """
        Create a mobile wallet pass (Apple Wallet / Google Pay).

        Generates a pass that can be added to mobile wallets.
        """
        wallet_pass = await self.features_repo.create_wallet_pass(
            pass_data,
            current_user.id,
            device_id
        )

        await self.db.commit()
        await self.db.refresh(wallet_pass)

        # In production, generate actual pass file (.pkpass for Apple, JWT for Google)
        # pass_url = await generate_wallet_pass(wallet_pass)

        return MobileWalletPassResponse.from_orm(wallet_pass)

    async def get_wallet_pass(
        self,
        pass_id: UUID,
        current_user: User
    ) -> MobileWalletPassResponse:
        """Get wallet pass by ID"""
        wallet_pass = await self.features_repo.get_wallet_pass_by_id(pass_id, current_user.id)

        if not wallet_pass:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet pass not found"
            )

        return MobileWalletPassResponse.from_orm(wallet_pass)

    async def get_user_wallet_passes(
        self,
        current_user: User,
        active_only: bool = True
    ) -> List[MobileWalletPassResponse]:
        """Get all wallet passes for user"""
        passes = await self.features_repo.get_user_wallet_passes(
            current_user.id,
            active_only=active_only
        )

        return [MobileWalletPassResponse.from_orm(p) for p in passes]

    async def mark_pass_installed(
        self,
        pass_id: UUID,
        current_user: User
    ) -> MobileWalletPassResponse:
        """Mark wallet pass as installed on device"""
        wallet_pass = await self.features_repo.get_wallet_pass_by_id(pass_id, current_user.id)

        if not wallet_pass:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet pass not found"
            )

        await self.features_repo.mark_pass_installed(pass_id)
        await self.db.commit()
        await self.db.refresh(wallet_pass)

        return MobileWalletPassResponse.from_orm(wallet_pass)

    async def update_wallet_pass(
        self,
        pass_id: UUID,
        pass_update: WalletPassUpdate,
        current_user: User
    ) -> MobileWalletPassResponse:
        """Update wallet pass data"""
        wallet_pass = await self.features_repo.get_wallet_pass_by_id(pass_id, current_user.id)

        if not wallet_pass:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet pass not found"
            )

        if pass_update.pass_data:
            wallet_pass.pass_data = pass_update.pass_data
        if pass_update.is_voided is not None:
            if pass_update.is_voided:
                await self.features_repo.void_wallet_pass(pass_id)

        wallet_pass.last_updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(wallet_pass)

        # In production, send push notification to update pass on device
        # await notify_pass_update(wallet_pass.serial_number)

        return MobileWalletPassResponse.from_orm(wallet_pass)

    # ========================================================================
    # Media Upload Operations
    # ========================================================================

    async def create_media_upload(
        self,
        media_data: MobileMediaUploadCreate,
        current_user: User,
        device_id: UUID
    ) -> MobileMediaUploadResponse:
        """Record a media upload from mobile device"""
        media = await self.features_repo.create_media_upload(
            media_data,
            current_user.id,
            device_id
        )

        await self.db.commit()
        await self.db.refresh(media)

        # In production, trigger background processing for the media
        # - Generate thumbnails
        # - Extract EXIF data
        # - Run image recognition / moderation
        # await process_media_upload.delay(media.id)

        return MobileMediaUploadResponse.from_orm(media)

    async def get_user_media_uploads(
        self,
        current_user: User,
        media_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[MobileMediaUploadResponse], int]:
        """Get user's media uploads"""
        media_list, total = await self.features_repo.get_user_media_uploads(
            current_user.id,
            media_type=media_type,
            skip=skip,
            limit=limit
        )

        media_responses = [MobileMediaUploadResponse.from_orm(m) for m in media_list]
        return media_responses, total

    # ========================================================================
    # Biometric Auth Operations
    # ========================================================================

    async def enable_biometric(
        self,
        biometric_data: BiometricAuthEnable,
        current_user: User
    ) -> BiometricAuthResponse:
        """Enable biometric authentication for device"""
        biometric = await self.features_repo.enable_biometric_auth(
            current_user.id,
            biometric_data.device_id,
            biometric_data.biometric_type,
            biometric_data.public_key
        )

        await self.db.commit()
        await self.db.refresh(biometric)

        return BiometricAuthResponse.from_orm(biometric)

    async def get_device_biometrics(
        self,
        device_id: UUID,
        current_user: User
    ) -> List[BiometricAuthResponse]:
        """Get biometric settings for device"""
        biometrics = await self.features_repo.get_device_biometrics(
            current_user.id,
            device_id
        )

        return [BiometricAuthResponse.from_orm(b) for b in biometrics]

    async def verify_biometric(
        self,
        verify_data: BiometricAuthVerify,
        current_user: User
    ) -> Dict[str, bool]:
        """
        Verify biometric authentication attempt.

        In production, this would:
        - Verify the signature against the stored public key
        - Check for device tampering
        - Implement anti-spoofing measures
        """
        biometrics = await self.features_repo.get_device_biometrics(
            current_user.id,
            verify_data.device_id
        )

        biometric = next(
            (b for b in biometrics if b.biometric_type == verify_data.biometric_type and b.is_enabled),
            None
        )

        if not biometric:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Biometric authentication not enabled"
            )

        # Check if locked
        if biometric.is_locked:
            if biometric.locked_until and biometric.locked_until > datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Biometric authentication temporarily locked"
                )

        # In production: verify signature with public key
        # success = verify_signature(verify_data.challenge, verify_data.signature, biometric.public_key)
        success = True  # Simplified for now

        await self.features_repo.record_biometric_auth_attempt(biometric.id, success)
        await self.db.commit()

        return {"verified": success}

    async def disable_biometric(
        self,
        biometric_id: UUID,
        current_user: User
    ) -> Dict[str, str]:
        """Disable biometric authentication"""
        biometrics = await self.features_repo.get_device_biometrics(current_user.id, None)
        biometric = next((b for b in biometrics if b.id == biometric_id), None)

        if not biometric or biometric.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Biometric authentication not found"
            )

        await self.features_repo.disable_biometric_auth(biometric_id)
        await self.db.commit()

        return {"status": "disabled"}

    # ========================================================================
    # Location Operations
    # ========================================================================

    async def record_location(
        self,
        location_data: MobileLocationCreate,
        current_user: User
    ) -> MobileLocationResponse:
        """Record user location"""
        location = await self.features_repo.record_location(location_data, current_user.id)

        await self.db.commit()
        await self.db.refresh(location)

        # Check for nearby geofences
        geofences = await self.features_repo.get_nearby_geofences(
            location_data.latitude,
            location_data.longitude
        )

        # In production, trigger geofence events
        # for geofence in geofences:
        #     await check_geofence_trigger(geofence, location)

        return MobileLocationResponse.from_orm(location)

    async def get_location_history(
        self,
        current_user: User,
        days_back: int = 7
    ) -> List[MobileLocationResponse]:
        """Get user's location history"""
        locations = await self.features_repo.get_user_location_history(
            current_user.id,
            days_back=days_back
        )

        return [MobileLocationResponse.from_orm(loc) for loc in locations]

    # ========================================================================
    # Geofence Operations
    # ========================================================================

    async def create_geofence(
        self,
        geofence_data: GeofenceCreate,
        current_user: User
    ) -> GeofenceResponse:
        """Create a geofence for location-based triggers"""
        geofence = await self.features_repo.create_geofence(geofence_data, current_user.id)

        await self.db.commit()
        await self.db.refresh(geofence)

        return GeofenceResponse.from_orm(geofence)

    async def get_entity_geofences(
        self,
        entity_type: str,
        entity_id: UUID,
        current_user: User
    ) -> List[GeofenceResponse]:
        """Get all geofences for an entity"""
        geofences = await self.features_repo.get_geofences_by_entity(entity_type, entity_id)
        return [GeofenceResponse.from_orm(g) for g in geofences]

    async def trigger_geofence_event(
        self,
        event_data: GeofenceEvent,
        current_user: User
    ) -> Dict[str, Any]:
        """Process a geofence entry/exit/dwell event"""
        geofence = await self.features_repo.get_geofence_by_id(event_data.geofence_id)

        if not geofence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Geofence not found"
            )

        # Record the event
        await self.features_repo.record_geofence_event(
            event_data.geofence_id,
            event_data.event_type
        )

        await self.db.commit()

        # Execute actions
        actions_triggered = []
        if geofence.actions:
            for action in geofence.actions:
                # In production, execute the action (send notification, update status, etc.)
                actions_triggered.append(action["type"])

        return {
            "geofence_id": geofence.id,
            "event_type": event_data.event_type,
            "actions_triggered": actions_triggered
        }

    # ========================================================================
    # Share Operations
    # ========================================================================

    async def record_share(
        self,
        share_data: MobileShareCreate,
        current_user: User
    ) -> MobileShareResponse:
        """Record a content share"""
        share = await self.features_repo.record_share(share_data, current_user.id)

        await self.db.commit()
        await self.db.refresh(share)

        return MobileShareResponse.from_orm(share)

    async def get_share_analytics(
        self,
        current_user: User,
        content_type: Optional[str] = None,
        days_back: int = 30
    ) -> ShareAnalytics:
        """Get sharing analytics"""
        analytics = await self.features_repo.get_share_analytics(
            user_id=current_user.id,
            content_type=content_type,
            days_back=days_back
        )

        return ShareAnalytics(**analytics)

    # ========================================================================
    # Widget Operations
    # ========================================================================

    async def install_widget(
        self,
        widget_data: MobileWidgetCreate,
        current_user: User
    ) -> MobileWidgetResponse:
        """Install a home screen widget"""
        widget = await self.features_repo.create_widget(widget_data, current_user.id)

        await self.db.commit()
        await self.db.refresh(widget)

        return MobileWidgetResponse.from_orm(widget)

    async def get_device_widgets(
        self,
        device_id: UUID,
        current_user: User
    ) -> List[MobileWidgetResponse]:
        """Get widgets installed on device"""
        widgets = await self.features_repo.get_device_widgets(current_user.id, device_id)
        return [MobileWidgetResponse.from_orm(w) for w in widgets]

    async def refresh_widget(
        self,
        widget_id: UUID,
        current_user: User
    ) -> WidgetRefreshResponse:
        """Refresh widget data"""
        widget = await self.features_repo.get_widget_by_id(widget_id, current_user.id)

        if not widget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Widget not found"
            )

        await self.features_repo.refresh_widget(widget_id)
        await self.db.commit()

        # Generate widget data based on type
        widget_data = await self._generate_widget_data(widget)

        return WidgetRefreshResponse(
            widget_id=widget_id,
            widget_data=widget_data,
            last_refreshed_at=datetime.utcnow()
        )

    async def _generate_widget_data(self, widget) -> Dict[str, Any]:
        """Generate data for widget based on type"""
        # In production, fetch actual data based on widget type
        # e.g., upcoming events, countdown, task list, budget summary
        return {
            "widget_type": widget.widget_type,
            "data": {},
            "timestamp": datetime.utcnow().isoformat()
        }

    async def update_widget(
        self,
        widget_id: UUID,
        widget_update: MobileWidgetUpdate,
        current_user: User
    ) -> MobileWidgetResponse:
        """Update widget configuration"""
        widget = await self.features_repo.get_widget_by_id(widget_id, current_user.id)

        if not widget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Widget not found"
            )

        if widget_update.config:
            widget.config = widget_update.config
        if widget_update.is_active is not None:
            widget.is_active = widget_update.is_active

        await self.db.commit()
        await self.db.refresh(widget)

        return MobileWidgetResponse.from_orm(widget)

    async def uninstall_widget(
        self,
        widget_id: UUID,
        current_user: User
    ) -> Dict[str, str]:
        """Uninstall a widget"""
        widget = await self.features_repo.get_widget_by_id(widget_id, current_user.id)

        if not widget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Widget not found"
            )

        await self.features_repo.deactivate_widget(widget_id)
        await self.db.commit()

        return {"status": "uninstalled"}

    # ========================================================================
    # Quick Action Operations
    # ========================================================================

    async def create_quick_action(
        self,
        action_data: QuickActionCreate,
        current_user: User
    ) -> QuickActionResponse:
        """Create a quick action (admin only)"""
        # In production, verify admin privileges
        # if not current_user.is_admin:
        #     raise HTTPException(status_code=403, detail="Admin access required")

        action = await self.features_repo.create_quick_action(action_data)

        await self.db.commit()
        await self.db.refresh(action)

        return QuickActionResponse.from_orm(action)

    async def get_platform_quick_actions(
        self,
        platform: str
    ) -> List[QuickActionResponse]:
        """Get available quick actions for platform"""
        actions = await self.features_repo.get_platform_quick_actions(platform)
        return [QuickActionResponse.from_orm(a) for a in actions]

    async def use_quick_action(
        self,
        usage_data: QuickActionUsageCreate,
        current_user: User
    ) -> Dict[str, str]:
        """Record quick action usage"""
        action = await self.features_repo.get_quick_action_by_id(usage_data.quick_action_id)

        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quick action not found"
            )

        await self.features_repo.record_quick_action_usage(
            usage_data.quick_action_id,
            current_user.id,
            usage_data.device_id,
            usage_data.action_completed
        )

        await self.db.commit()

        return {"status": "recorded"}

    async def get_quick_action_analytics(
        self,
        days_back: int = 30
    ) -> QuickActionAnalytics:
        """Get quick action analytics"""
        analytics = await self.features_repo.get_quick_action_analytics(days_back)
        return QuickActionAnalytics(**analytics)
