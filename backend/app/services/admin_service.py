"""
CelebraTech Event Management System - Admin Service
Sprint 21: Admin & Moderation System
Business logic for admin and moderation operations
"""
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID

from app.models.admin import AdminAction, ModerationQueue, SystemConfig
from app.models.user import User
from app.models.vendor import Vendor
from app.repositories.admin_repository import AdminRepository


class AdminService:
    """Service for admin and moderation operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.admin_repo = AdminRepository(db)

    def _verify_admin(self, user: User):
        """Verify user is admin"""
        # TODO: Implement proper admin role check
        # For now, assume all users with is_superuser or specific role are admins
        pass

    # ========================================================================
    # Admin Action Logging
    # ========================================================================

    async def log_action(
        self,
        action_type: str,
        current_user: User,
        target_type: Optional[str] = None,
        target_id: Optional[UUID] = None,
        changes: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        request: Optional[Request] = None
    ) -> AdminAction:
        """Log an admin action"""
        self._verify_admin(current_user)

        ip_address = None
        if request:
            ip_address = request.client.host if request.client else None

        action = await self.admin_repo.log_admin_action(
            current_user.id,
            action_type,
            target_type,
            target_id,
            changes,
            reason,
            ip_address
        )

        await self.db.commit()
        return action

    async def get_admin_actions(
        self,
        current_user: User,
        admin_id: Optional[UUID] = None,
        action_type: Optional[str] = None,
        target_type: Optional[str] = None,
        days_back: int = 30,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[AdminAction], int]:
        """Get admin action log"""
        self._verify_admin(current_user)

        offset = (page - 1) * page_size

        actions, total = await self.admin_repo.get_admin_actions(
            admin_id,
            action_type,
            target_type,
            days_back,
            page_size,
            offset
        )

        return actions, total

    async def get_admin_stats(
        self,
        current_user: User,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get admin action statistics"""
        self._verify_admin(current_user)

        stats = await self.admin_repo.get_admin_action_stats(days_back)
        return stats

    # ========================================================================
    # User Management
    # ========================================================================

    async def suspend_user(
        self,
        user_id: UUID,
        reason: str,
        current_user: User,
        duration_days: Optional[int] = None,
        request: Optional[Request] = None
    ) -> bool:
        """Suspend a user"""
        self._verify_admin(current_user)

        success = await self.admin_repo.suspend_user(user_id, reason, duration_days)

        if success:
            # Log action
            await self.admin_repo.log_admin_action(
                current_user.id,
                "user_suspend",
                "user",
                user_id,
                {"duration_days": duration_days},
                reason,
                request.client.host if request and request.client else None
            )

            await self.db.commit()

        return success

    async def unsuspend_user(
        self,
        user_id: UUID,
        current_user: User,
        request: Optional[Request] = None
    ) -> bool:
        """Unsuspend a user"""
        self._verify_admin(current_user)

        success = await self.admin_repo.unsuspend_user(user_id)

        if success:
            # Log action
            await self.admin_repo.log_admin_action(
                current_user.id,
                "user_unsuspend",
                "user",
                user_id,
                ip_address=request.client.host if request and request.client else None
            )

            await self.db.commit()

        return success

    async def delete_user(
        self,
        user_id: UUID,
        reason: str,
        current_user: User,
        request: Optional[Request] = None
    ) -> bool:
        """Delete a user"""
        self._verify_admin(current_user)

        success = await self.admin_repo.delete_user(user_id)

        if success:
            # Log action
            await self.admin_repo.log_admin_action(
                current_user.id,
                "user_delete",
                "user",
                user_id,
                reason=reason,
                ip_address=request.client.host if request and request.client else None
            )

            await self.db.commit()

        return success

    # ========================================================================
    # Vendor Management
    # ========================================================================

    async def approve_vendor(
        self,
        vendor_id: UUID,
        current_user: User,
        notes: Optional[str] = None,
        request: Optional[Request] = None
    ) -> bool:
        """Approve a vendor"""
        self._verify_admin(current_user)

        success = await self.admin_repo.approve_vendor(vendor_id)

        if success:
            # Log action
            await self.admin_repo.log_admin_action(
                current_user.id,
                "vendor_approve",
                "vendor",
                vendor_id,
                reason=notes,
                ip_address=request.client.host if request and request.client else None
            )

            await self.db.commit()

        return success

    async def reject_vendor(
        self,
        vendor_id: UUID,
        reason: str,
        current_user: User,
        request: Optional[Request] = None
    ) -> bool:
        """Reject a vendor"""
        self._verify_admin(current_user)

        success = await self.admin_repo.reject_vendor(vendor_id, reason)

        if success:
            # Log action
            await self.admin_repo.log_admin_action(
                current_user.id,
                "vendor_reject",
                "vendor",
                vendor_id,
                reason=reason,
                ip_address=request.client.host if request and request.client else None
            )

            await self.db.commit()

        return success

    async def suspend_vendor(
        self,
        vendor_id: UUID,
        reason: str,
        current_user: User,
        request: Optional[Request] = None
    ) -> bool:
        """Suspend a vendor"""
        self._verify_admin(current_user)

        success = await self.admin_repo.suspend_vendor(vendor_id, reason)

        if success:
            # Log action
            await self.admin_repo.log_admin_action(
                current_user.id,
                "vendor_suspend",
                "vendor",
                vendor_id,
                reason=reason,
                ip_address=request.client.host if request and request.client else None
            )

            await self.db.commit()

        return success

    async def get_pending_vendors(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[Vendor], int]:
        """Get vendors pending approval"""
        self._verify_admin(current_user)

        offset = (page - 1) * page_size

        vendors, total = await self.admin_repo.get_pending_vendors(
            page_size,
            offset
        )

        return vendors, total

    # ========================================================================
    # Moderation Queue
    # ========================================================================

    async def add_to_moderation_queue(
        self,
        content_type: str,
        content_id: UUID,
        reason: str,
        current_user: User
    ) -> ModerationQueue:
        """Add content to moderation queue"""
        item = await self.admin_repo.add_to_moderation_queue(
            content_type,
            content_id,
            reason
        )

        await self.db.commit()
        return item

    async def get_moderation_queue(
        self,
        current_user: User,
        status: Optional[str] = None,
        content_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[ModerationQueue], int]:
        """Get moderation queue"""
        self._verify_admin(current_user)

        offset = (page - 1) * page_size

        items, total = await self.admin_repo.get_moderation_queue(
            status,
            content_type,
            page_size,
            offset
        )

        return items, total

    async def review_moderation_item(
        self,
        item_id: UUID,
        decision: str,
        current_user: User,
        notes: Optional[str] = None,
        request: Optional[Request] = None
    ) -> ModerationQueue:
        """Review a moderation item"""
        self._verify_admin(current_user)

        item = await self.admin_repo.review_moderation_item(
            item_id,
            current_user.id,
            decision,
            notes
        )

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Moderation item not found"
            )

        # Log action
        await self.admin_repo.log_admin_action(
            current_user.id,
            "content_moderation",
            item.content_type,
            item.content_id,
            {"decision": decision},
            notes,
            request.client.host if request and request.client else None
        )

        await self.db.commit()
        return item

    async def get_moderation_stats(
        self,
        current_user: User
    ) -> Dict[str, Any]:
        """Get moderation statistics"""
        self._verify_admin(current_user)

        stats = await self.admin_repo.get_moderation_stats()
        return stats

    # ========================================================================
    # System Configuration
    # ========================================================================

    async def get_config(
        self,
        config_key: str,
        current_user: User
    ) -> Optional[SystemConfig]:
        """Get system configuration"""
        self._verify_admin(current_user)

        config = await self.admin_repo.get_config(config_key)
        return config

    async def get_all_configs(
        self,
        current_user: User,
        category: Optional[str] = None,
        include_sensitive: bool = False
    ) -> List[SystemConfig]:
        """Get all system configurations"""
        self._verify_admin(current_user)

        configs = await self.admin_repo.get_all_configs(category)

        # Filter out sensitive configs if requested
        if not include_sensitive:
            configs = [c for c in configs if not c.is_sensitive]

        return configs

    async def set_config(
        self,
        config_key: str,
        config_value: Any,
        category: str,
        current_user: User,
        is_sensitive: bool = False,
        request: Optional[Request] = None
    ) -> SystemConfig:
        """Set system configuration"""
        self._verify_admin(current_user)

        config = await self.admin_repo.set_config(
            config_key,
            config_value,
            category,
            current_user.id,
            is_sensitive
        )

        # Log action
        await self.admin_repo.log_admin_action(
            current_user.id,
            "config_update",
            "system_config",
            config.id,
            {"config_key": config_key, "category": category},
            ip_address=request.client.host if request and request.client else None
        )

        await self.db.commit()
        return config

    async def delete_config(
        self,
        config_key: str,
        current_user: User,
        request: Optional[Request] = None
    ) -> bool:
        """Delete system configuration"""
        self._verify_admin(current_user)

        success = await self.admin_repo.delete_config(config_key)

        if success:
            # Log action
            await self.admin_repo.log_admin_action(
                current_user.id,
                "config_delete",
                "system_config",
                None,
                {"config_key": config_key},
                ip_address=request.client.host if request and request.client else None
            )

            await self.db.commit()

        return success

    # ========================================================================
    # Dashboard
    # ========================================================================

    async def get_dashboard_stats(
        self,
        current_user: User
    ) -> Dict[str, Any]:
        """Get admin dashboard statistics"""
        self._verify_admin(current_user)

        stats = await self.admin_repo.get_dashboard_stats()
        return stats
