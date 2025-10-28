"""
Mobile App Features Repository
Sprint 19: Mobile App Features

Repository layer for advanced mobile features including QR codes,
wallet passes, biometrics, geofencing, sharing, widgets, and quick actions.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import secrets
import hashlib

from app.models.mobile_features import (
    QRCode, QRCodeScan, MobileWalletPass, MobileMediaUpload,
    BiometricAuth, MobileLocation, Geofence,
    MobileShare, MobileWidget, QuickAction, QuickActionUsage
)
from app.schemas.mobile_features import (
    QRCodeCreate, MobileWalletPassCreate, MobileMediaUploadCreate,
    BiometricAuthEnable, MobileLocationCreate, GeofenceCreate,
    MobileShareCreate, MobileWidgetCreate, QuickActionCreate
)


class MobileFeaturesRepository:
    """Repository for advanced mobile features"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # QR Code Operations
    # ========================================================================

    async def create_qr_code(
        self,
        qr_data: QRCodeCreate,
        created_by: UUID
    ) -> QRCode:
        """Create a new QR code"""
        # Generate unique QR code string
        qr_string = self._generate_qr_string(qr_data.entity_type, qr_data.entity_id)

        qr_code = QRCode(
            qr_code=qr_string,
            created_by=created_by,
            **qr_data.dict()
        )

        self.db.add(qr_code)
        await self.db.flush()
        return qr_code

    def _generate_qr_string(self, entity_type: str, entity_id: UUID) -> str:
        """Generate unique QR code string"""
        # Create hash from entity info + timestamp
        data = f"{entity_type}:{entity_id}:{datetime.utcnow().timestamp()}"
        hash_val = hashlib.sha256(data.encode()).hexdigest()[:16]
        return f"CTC-{hash_val.upper()}"

    async def get_qr_code_by_id(
        self,
        qr_code_id: UUID
    ) -> Optional[QRCode]:
        """Get QR code by ID"""
        stmt = select(QRCode).where(QRCode.id == qr_code_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_qr_code_by_string(
        self,
        qr_string: str
    ) -> Optional[QRCode]:
        """Get QR code by string"""
        stmt = select(QRCode).where(QRCode.qr_code == qr_string)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_qr_codes_by_entity(
        self,
        entity_type: str,
        entity_id: UUID
    ) -> List[QRCode]:
        """Get all QR codes for an entity"""
        stmt = select(QRCode).where(
            and_(
                QRCode.entity_type == entity_type,
                QRCode.entity_id == entity_id,
                QRCode.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def record_qr_scan(
        self,
        qr_code_id: UUID,
        user_id: Optional[UUID],
        device_id: Optional[UUID],
        location_data: Optional[Dict[str, Any]],
        action_taken: Optional[str],
        platform: Optional[str],
        app_version: Optional[str]
    ) -> QRCodeScan:
        """Record a QR code scan"""
        scan = QRCodeScan(
            qr_code_id=qr_code_id,
            user_id=user_id,
            device_id=device_id,
            location_data=location_data,
            action_taken=action_taken,
            platform=platform,
            app_version=app_version
        )

        self.db.add(scan)

        # Update QR code stats
        stmt = update(QRCode).where(
            QRCode.id == qr_code_id
        ).values(
            scan_count=QRCode.scan_count + 1,
            last_scanned_at=datetime.utcnow()
        )
        await self.db.execute(stmt)

        await self.db.flush()
        return scan

    async def get_qr_scan_analytics(
        self,
        qr_code_id: UUID,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get scan analytics for a QR code"""
        since_date = datetime.utcnow() - timedelta(days=days_back)

        stmt = select(QRCodeScan).where(
            and_(
                QRCodeScan.qr_code_id == qr_code_id,
                QRCodeScan.scanned_at >= since_date
            )
        ).order_by(QRCodeScan.scanned_at.desc())

        result = await self.db.execute(stmt)
        scans = result.scalars().all()

        total_scans = len(scans)
        unique_scanners = len(set(s.user_id for s in scans if s.user_id))

        return {
            "total_scans": total_scans,
            "unique_scanners": unique_scanners,
            "scan_trend": [],
            "top_locations": [],
            "recent_scans": list(scans[:10])
        }

    # ========================================================================
    # Wallet Pass Operations
    # ========================================================================

    async def create_wallet_pass(
        self,
        pass_data: MobileWalletPassCreate,
        user_id: UUID,
        device_id: Optional[UUID] = None
    ) -> MobileWalletPass:
        """Create a mobile wallet pass"""
        # Generate unique serial number
        serial_number = f"{pass_data.pass_type_id}-{secrets.token_hex(8)}"

        wallet_pass = MobileWalletPass(
            user_id=user_id,
            device_id=device_id,
            serial_number=serial_number,
            **pass_data.dict()
        )

        self.db.add(wallet_pass)
        await self.db.flush()
        return wallet_pass

    async def get_wallet_pass_by_id(
        self,
        pass_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[MobileWalletPass]:
        """Get wallet pass by ID"""
        stmt = select(MobileWalletPass).where(MobileWalletPass.id == pass_id)
        if user_id:
            stmt = stmt.where(MobileWalletPass.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_wallet_pass_by_serial(
        self,
        serial_number: str
    ) -> Optional[MobileWalletPass]:
        """Get wallet pass by serial number"""
        stmt = select(MobileWalletPass).where(
            MobileWalletPass.serial_number == serial_number
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_wallet_passes(
        self,
        user_id: UUID,
        active_only: bool = True
    ) -> List[MobileWalletPass]:
        """Get all wallet passes for user"""
        stmt = select(MobileWalletPass).where(MobileWalletPass.user_id == user_id)

        if active_only:
            stmt = stmt.where(
                and_(
                    MobileWalletPass.is_active == True,
                    MobileWalletPass.is_voided == False
                )
            )

        stmt = stmt.order_by(MobileWalletPass.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def mark_pass_installed(
        self,
        pass_id: UUID
    ) -> None:
        """Mark wallet pass as installed"""
        stmt = update(MobileWalletPass).where(
            MobileWalletPass.id == pass_id
        ).values(
            is_installed=True,
            installed_at=datetime.utcnow()
        )
        await self.db.execute(stmt)

    async def void_wallet_pass(
        self,
        pass_id: UUID
    ) -> None:
        """Void a wallet pass"""
        stmt = update(MobileWalletPass).where(
            MobileWalletPass.id == pass_id
        ).values(
            is_voided=True,
            is_active=False,
            updated_at=datetime.utcnow()
        )
        await self.db.execute(stmt)

    # ========================================================================
    # Media Upload Operations
    # ========================================================================

    async def create_media_upload(
        self,
        media_data: MobileMediaUploadCreate,
        user_id: UUID,
        device_id: UUID
    ) -> MobileMediaUpload:
        """Record a media upload"""
        media = MobileMediaUpload(
            user_id=user_id,
            device_id=device_id,
            **media_data.dict()
        )

        self.db.add(media)
        await self.db.flush()
        return media

    async def get_media_upload_by_id(
        self,
        media_id: UUID
    ) -> Optional[MobileMediaUpload]:
        """Get media upload by ID"""
        stmt = select(MobileMediaUpload).where(MobileMediaUpload.id == media_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_media_uploads(
        self,
        user_id: UUID,
        media_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[MobileMediaUpload], int]:
        """Get media uploads for user"""
        stmt = select(MobileMediaUpload).where(MobileMediaUpload.user_id == user_id)

        if media_type:
            stmt = stmt.where(MobileMediaUpload.media_type == media_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar()

        stmt = stmt.offset(skip).limit(limit).order_by(MobileMediaUpload.uploaded_at.desc())
        result = await self.db.execute(stmt)
        media_list = result.scalars().all()

        return list(media_list), total

    # ========================================================================
    # Biometric Auth Operations
    # ========================================================================

    async def enable_biometric_auth(
        self,
        user_id: UUID,
        device_id: UUID,
        biometric_type: str,
        public_key: Optional[str] = None
    ) -> BiometricAuth:
        """Enable biometric authentication for device"""
        # Check if already exists
        stmt = select(BiometricAuth).where(
            and_(
                BiometricAuth.user_id == user_id,
                BiometricAuth.device_id == device_id,
                BiometricAuth.biometric_type == biometric_type
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.is_enabled = True
            existing.enabled_at = datetime.utcnow()
            existing.public_key = public_key or existing.public_key
            return existing

        biometric = BiometricAuth(
            user_id=user_id,
            device_id=device_id,
            biometric_type=biometric_type,
            is_enabled=True,
            enabled_at=datetime.utcnow(),
            public_key=public_key
        )

        self.db.add(biometric)
        await self.db.flush()
        return biometric

    async def get_device_biometrics(
        self,
        user_id: UUID,
        device_id: UUID
    ) -> List[BiometricAuth]:
        """Get all biometric auth for device"""
        stmt = select(BiometricAuth).where(
            and_(
                BiometricAuth.user_id == user_id,
                BiometricAuth.device_id == device_id
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def record_biometric_auth_attempt(
        self,
        biometric_id: UUID,
        success: bool
    ) -> None:
        """Record biometric authentication attempt"""
        if success:
            stmt = update(BiometricAuth).where(
                BiometricAuth.id == biometric_id
            ).values(
                auth_count=BiometricAuth.auth_count + 1,
                last_authenticated_at=datetime.utcnow(),
                failed_attempts=0
            )
        else:
            stmt = update(BiometricAuth).where(
                BiometricAuth.id == biometric_id
            ).values(
                failed_attempts=BiometricAuth.failed_attempts + 1,
                last_failed_at=datetime.utcnow()
            )

        await self.db.execute(stmt)

    async def disable_biometric_auth(
        self,
        biometric_id: UUID
    ) -> None:
        """Disable biometric authentication"""
        stmt = update(BiometricAuth).where(
            BiometricAuth.id == biometric_id
        ).values(
            is_enabled=False,
            disabled_at=datetime.utcnow()
        )
        await self.db.execute(stmt)

    # ========================================================================
    # Location Operations
    # ========================================================================

    async def record_location(
        self,
        location_data: MobileLocationCreate,
        user_id: UUID
    ) -> MobileLocation:
        """Record user location"""
        location = MobileLocation(
            user_id=user_id,
            **location_data.dict()
        )

        self.db.add(location)
        await self.db.flush()
        return location

    async def get_user_location_history(
        self,
        user_id: UUID,
        days_back: int = 7,
        limit: int = 100
    ) -> List[MobileLocation]:
        """Get user location history"""
        since_date = datetime.utcnow() - timedelta(days=days_back)

        stmt = select(MobileLocation).where(
            and_(
                MobileLocation.user_id == user_id,
                MobileLocation.recorded_at >= since_date
            )
        ).order_by(MobileLocation.recorded_at.desc()).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_user_location(
        self,
        user_id: UUID,
        device_id: Optional[UUID] = None
    ) -> Optional[MobileLocation]:
        """Get user's latest location"""
        stmt = select(MobileLocation).where(MobileLocation.user_id == user_id)

        if device_id:
            stmt = stmt.where(MobileLocation.device_id == device_id)

        stmt = stmt.order_by(MobileLocation.recorded_at.desc()).limit(1)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ========================================================================
    # Geofence Operations
    # ========================================================================

    async def create_geofence(
        self,
        geofence_data: GeofenceCreate,
        created_by: UUID
    ) -> Geofence:
        """Create a geofence"""
        geofence = Geofence(
            created_by=created_by,
            **geofence_data.dict()
        )

        self.db.add(geofence)
        await self.db.flush()
        return geofence

    async def get_geofence_by_id(
        self,
        geofence_id: UUID
    ) -> Optional[Geofence]:
        """Get geofence by ID"""
        stmt = select(Geofence).where(Geofence.id == geofence_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_geofences_by_entity(
        self,
        entity_type: str,
        entity_id: UUID
    ) -> List[Geofence]:
        """Get all geofences for an entity"""
        stmt = select(Geofence).where(
            and_(
                Geofence.entity_type == entity_type,
                Geofence.entity_id == entity_id,
                Geofence.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_nearby_geofences(
        self,
        latitude: float,
        longitude: float,
        search_radius_km: float = 10
    ) -> List[Geofence]:
        """
        Get geofences near a location.

        Note: This is a simplified implementation. In production,
        use PostGIS or similar for accurate geospatial queries.
        """
        # Simple bounding box calculation (approximate)
        lat_delta = search_radius_km / 111  # 1 degree latitude ≈ 111km
        lon_delta = search_radius_km / (111 * abs(latitude / 90))

        stmt = select(Geofence).where(
            and_(
                Geofence.is_active == True,
                Geofence.latitude.between(latitude - lat_delta, latitude + lat_delta),
                Geofence.longitude.between(longitude - lon_delta, longitude + lon_delta)
            )
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def record_geofence_event(
        self,
        geofence_id: UUID,
        event_type: str
    ) -> None:
        """Record geofence entry/exit event"""
        if event_type == "entry":
            stmt = update(Geofence).where(
                Geofence.id == geofence_id
            ).values(entry_count=Geofence.entry_count + 1)
        elif event_type == "exit":
            stmt = update(Geofence).where(
                Geofence.id == geofence_id
            ).values(exit_count=Geofence.exit_count + 1)

        await self.db.execute(stmt)

    # ========================================================================
    # Share Operations
    # ========================================================================

    async def record_share(
        self,
        share_data: MobileShareCreate,
        user_id: UUID
    ) -> MobileShare:
        """Record a content share"""
        share = MobileShare(
            user_id=user_id,
            **share_data.dict()
        )

        self.db.add(share)
        await self.db.flush()
        return share

    async def get_share_analytics(
        self,
        user_id: Optional[UUID] = None,
        content_type: Optional[str] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get sharing analytics"""
        since_date = datetime.utcnow() - timedelta(days=days_back)

        stmt = select(MobileShare).where(MobileShare.shared_at >= since_date)

        if user_id:
            stmt = stmt.where(MobileShare.user_id == user_id)
        if content_type:
            stmt = stmt.where(MobileShare.content_type == content_type)

        result = await self.db.execute(stmt)
        shares = result.scalars().all()

        total_shares = len(shares)
        successful_shares = sum(1 for s in shares if s.was_successful)

        # Group by method
        shares_by_method = {}
        for share in shares:
            shares_by_method[share.share_method] = shares_by_method.get(share.share_method, 0) + 1

        # Group by content type
        shares_by_content = {}
        for share in shares:
            shares_by_content[share.content_type] = shares_by_content.get(share.content_type, 0) + 1

        return {
            "total_shares": total_shares,
            "shares_by_method": shares_by_method,
            "shares_by_content_type": shares_by_content,
            "success_rate": (successful_shares / total_shares * 100) if total_shares > 0 else 0,
            "trending_shares": []
        }

    # ========================================================================
    # Widget Operations
    # ========================================================================

    async def create_widget(
        self,
        widget_data: MobileWidgetCreate,
        user_id: UUID
    ) -> MobileWidget:
        """Install a widget"""
        widget = MobileWidget(
            user_id=user_id,
            **widget_data.dict()
        )

        self.db.add(widget)
        await self.db.flush()
        return widget

    async def get_widget_by_id(
        self,
        widget_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[MobileWidget]:
        """Get widget by ID"""
        stmt = select(MobileWidget).where(MobileWidget.id == widget_id)
        if user_id:
            stmt = stmt.where(MobileWidget.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_device_widgets(
        self,
        user_id: UUID,
        device_id: UUID
    ) -> List[MobileWidget]:
        """Get all widgets for device"""
        stmt = select(MobileWidget).where(
            and_(
                MobileWidget.user_id == user_id,
                MobileWidget.device_id == device_id,
                MobileWidget.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def refresh_widget(
        self,
        widget_id: UUID
    ) -> None:
        """Record widget refresh"""
        stmt = update(MobileWidget).where(
            MobileWidget.id == widget_id
        ).values(
            last_refreshed_at=datetime.utcnow(),
            refresh_count=MobileWidget.refresh_count + 1
        )
        await self.db.execute(stmt)

    async def record_widget_tap(
        self,
        widget_id: UUID
    ) -> None:
        """Record widget tap"""
        stmt = update(MobileWidget).where(
            MobileWidget.id == widget_id
        ).values(
            last_tapped_at=datetime.utcnow(),
            tap_count=MobileWidget.tap_count + 1
        )
        await self.db.execute(stmt)

    async def deactivate_widget(
        self,
        widget_id: UUID
    ) -> None:
        """Deactivate a widget"""
        stmt = update(MobileWidget).where(
            MobileWidget.id == widget_id
        ).values(is_active=False)
        await self.db.execute(stmt)

    # ========================================================================
    # Quick Action Operations
    # ========================================================================

    async def create_quick_action(
        self,
        action_data: QuickActionCreate
    ) -> QuickAction:
        """Create a quick action"""
        action = QuickAction(**action_data.dict())
        self.db.add(action)
        await self.db.flush()
        return action

    async def get_quick_action_by_id(
        self,
        action_id: UUID
    ) -> Optional[QuickAction]:
        """Get quick action by ID"""
        stmt = select(QuickAction).where(QuickAction.id == action_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_platform_quick_actions(
        self,
        platform: str
    ) -> List[QuickAction]:
        """Get active quick actions for platform"""
        stmt = select(QuickAction).where(
            and_(
                QuickAction.platform == platform,
                QuickAction.is_active == True
            )
        ).order_by(QuickAction.priority.desc(), QuickAction.use_count.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def record_quick_action_usage(
        self,
        action_id: UUID,
        user_id: UUID,
        device_id: UUID,
        action_completed: bool
    ) -> QuickActionUsage:
        """Record quick action usage"""
        usage = QuickActionUsage(
            quick_action_id=action_id,
            user_id=user_id,
            device_id=device_id,
            action_completed=action_completed
        )

        self.db.add(usage)

        # Update quick action stats
        stmt = update(QuickAction).where(
            QuickAction.id == action_id
        ).values(
            use_count=QuickAction.use_count + 1,
            last_used_at=datetime.utcnow()
        )
        await self.db.execute(stmt)

        await self.db.flush()
        return usage

    async def get_quick_action_analytics(
        self,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get quick action analytics"""
        since_date = datetime.utcnow() - timedelta(days=days_back)

        stmt = select(QuickActionUsage).where(
            QuickActionUsage.used_at >= since_date
        )

        result = await self.db.execute(stmt)
        usages = result.scalars().all()

        total_uses = len(usages)
        completed_actions = sum(1 for u in usages if u.action_completed)

        return {
            "total_uses": total_uses,
            "most_used_actions": [],
            "completion_rate": (completed_actions / total_uses * 100) if total_uses > 0 else 0,
            "platform_distribution": {}
        }
