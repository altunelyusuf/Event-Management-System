"""
CelebraTech Event Management System - Admin Repository
Sprint 21: Admin & Moderation System
Data access layer for admin and moderation operations
"""
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, and_, or_, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from uuid import UUID

from app.models.admin import AdminAction, ModerationQueue, SystemConfig
from app.models.user import User
from app.models.vendor import Vendor
from app.models.event import Event


class AdminRepository:
    """Repository for admin and moderation operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Admin Action Logging
    # ========================================================================

    async def log_admin_action(
        self,
        admin_id: UUID,
        action_type: str,
        target_type: Optional[str] = None,
        target_id: Optional[UUID] = None,
        changes: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> AdminAction:
        """Log an admin action"""
        action = AdminAction(
            admin_id=admin_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            changes=changes or {},
            reason=reason,
            ip_address=ip_address,
            performed_at=datetime.utcnow()
        )

        self.db.add(action)
        await self.db.flush()
        await self.db.refresh(action)

        return action

    async def get_admin_actions(
        self,
        admin_id: Optional[UUID] = None,
        action_type: Optional[str] = None,
        target_type: Optional[str] = None,
        days_back: int = 30,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[AdminAction], int]:
        """Get admin action log with filters"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        query = select(AdminAction).where(
            AdminAction.performed_at >= cutoff_date
        )

        if admin_id:
            query = query.where(AdminAction.admin_id == admin_id)
        if action_type:
            query = query.where(AdminAction.action_type == action_type)
        if target_type:
            query = query.where(AdminAction.target_type == target_type)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get paginated results
        query = query.order_by(AdminAction.performed_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        actions = list(result.scalars().all())

        return actions, total

    async def get_admin_action_stats(
        self,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get statistics on admin actions"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Count by action type
        query = select(
            AdminAction.action_type,
            func.count(AdminAction.id).label('count')
        ).where(
            AdminAction.performed_at >= cutoff_date
        ).group_by(AdminAction.action_type)

        result = await self.db.execute(query)
        action_counts = {row.action_type: row.count for row in result.all()}

        # Total actions
        total_query = select(func.count(AdminAction.id)).where(
            AdminAction.performed_at >= cutoff_date
        )
        total_result = await self.db.execute(total_query)
        total_actions = total_result.scalar()

        # Most active admins
        admin_query = select(
            AdminAction.admin_id,
            func.count(AdminAction.id).label('count')
        ).where(
            AdminAction.performed_at >= cutoff_date
        ).group_by(AdminAction.admin_id).order_by(desc('count')).limit(10)

        admin_result = await self.db.execute(admin_query)
        top_admins = [
            {"admin_id": str(row.admin_id), "action_count": row.count}
            for row in admin_result.all()
        ]

        return {
            "total_actions": total_actions,
            "action_counts": action_counts,
            "top_admins": top_admins
        }

    # ========================================================================
    # User Management
    # ========================================================================

    async def suspend_user(
        self,
        user_id: UUID,
        reason: str,
        duration_days: Optional[int] = None
    ) -> bool:
        """Suspend a user"""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return False

        user.is_active = False
        user.suspension_reason = reason
        if duration_days:
            user.suspended_until = datetime.utcnow() + timedelta(days=duration_days)

        await self.db.flush()
        return True

    async def unsuspend_user(self, user_id: UUID) -> bool:
        """Unsuspend a user"""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return False

        user.is_active = True
        user.suspension_reason = None
        user.suspended_until = None

        await self.db.flush()
        return True

    async def delete_user(self, user_id: UUID) -> bool:
        """Delete a user (soft delete)"""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return False

        user.is_deleted = True
        user.deleted_at = datetime.utcnow()

        await self.db.flush()
        return True

    # ========================================================================
    # Vendor Management
    # ========================================================================

    async def approve_vendor(self, vendor_id: UUID) -> bool:
        """Approve a vendor"""
        query = select(Vendor).where(Vendor.id == vendor_id)
        result = await self.db.execute(query)
        vendor = result.scalar_one_or_none()

        if not vendor:
            return False

        vendor.is_verified = True
        vendor.verification_date = datetime.utcnow()

        await self.db.flush()
        return True

    async def reject_vendor(self, vendor_id: UUID, reason: str) -> bool:
        """Reject a vendor"""
        query = select(Vendor).where(Vendor.id == vendor_id)
        result = await self.db.execute(query)
        vendor = result.scalar_one_or_none()

        if not vendor:
            return False

        vendor.is_verified = False
        vendor.rejection_reason = reason

        await self.db.flush()
        return True

    async def suspend_vendor(self, vendor_id: UUID, reason: str) -> bool:
        """Suspend a vendor"""
        query = select(Vendor).where(Vendor.id == vendor_id)
        result = await self.db.execute(query)
        vendor = result.scalar_one_or_none()

        if not vendor:
            return False

        vendor.is_active = False
        vendor.suspension_reason = reason

        await self.db.flush()
        return True

    async def get_pending_vendors(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Vendor], int]:
        """Get vendors pending approval"""
        query = select(Vendor).where(
            and_(
                Vendor.is_verified == False,
                or_(
                    Vendor.rejection_reason.is_(None),
                    Vendor.rejection_reason == ""
                )
            )
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get paginated results
        query = query.order_by(Vendor.created_at).limit(limit).offset(offset)
        result = await self.db.execute(query)
        vendors = list(result.scalars().all())

        return vendors, total

    # ========================================================================
    # Moderation Queue
    # ========================================================================

    async def add_to_moderation_queue(
        self,
        content_type: str,
        content_id: UUID,
        reason: str
    ) -> ModerationQueue:
        """Add content to moderation queue"""
        item = ModerationQueue(
            content_type=content_type,
            content_id=content_id,
            reason=reason,
            status="pending"
        )

        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)

        return item

    async def get_moderation_queue(
        self,
        status: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[ModerationQueue], int]:
        """Get moderation queue items"""
        query = select(ModerationQueue)

        if status:
            query = query.where(ModerationQueue.status == status)
        if content_type:
            query = query.where(ModerationQueue.content_type == content_type)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get paginated results
        query = query.order_by(ModerationQueue.created_at).limit(limit).offset(offset)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def review_moderation_item(
        self,
        item_id: UUID,
        reviewer_id: UUID,
        decision: str,
        notes: Optional[str] = None
    ) -> Optional[ModerationQueue]:
        """Review a moderation queue item"""
        query = select(ModerationQueue).where(ModerationQueue.id == item_id)
        result = await self.db.execute(query)
        item = result.scalar_one_or_none()

        if not item:
            return None

        item.reviewed_by = reviewer_id
        item.decision = decision
        item.notes = notes
        item.status = "reviewed"
        item.reviewed_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(item)

        return item

    async def get_moderation_stats(self) -> Dict[str, Any]:
        """Get moderation queue statistics"""
        # Total pending
        pending_query = select(func.count(ModerationQueue.id)).where(
            ModerationQueue.status == "pending"
        )
        pending_result = await self.db.execute(pending_query)
        pending_count = pending_result.scalar()

        # Count by content type
        type_query = select(
            ModerationQueue.content_type,
            func.count(ModerationQueue.id).label('count')
        ).where(
            ModerationQueue.status == "pending"
        ).group_by(ModerationQueue.content_type)

        type_result = await self.db.execute(type_query)
        type_counts = {row.content_type: row.count for row in type_result.all()}

        # Average review time
        avg_query = select(
            func.avg(
                func.extract('epoch', ModerationQueue.reviewed_at - ModerationQueue.created_at)
            )
        ).where(
            ModerationQueue.reviewed_at.isnot(None)
        )
        avg_result = await self.db.execute(avg_query)
        avg_review_time_seconds = avg_result.scalar() or 0

        return {
            "pending_count": pending_count,
            "type_counts": type_counts,
            "avg_review_time_hours": avg_review_time_seconds / 3600
        }

    # ========================================================================
    # System Configuration
    # ========================================================================

    async def get_config(self, config_key: str) -> Optional[SystemConfig]:
        """Get system configuration by key"""
        query = select(SystemConfig).where(SystemConfig.config_key == config_key)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_configs(
        self,
        category: Optional[str] = None
    ) -> List[SystemConfig]:
        """Get all system configurations"""
        query = select(SystemConfig)

        if category:
            query = query.where(SystemConfig.category == category)

        query = query.order_by(SystemConfig.category, SystemConfig.config_key)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def set_config(
        self,
        config_key: str,
        config_value: Any,
        category: str,
        updated_by: UUID,
        is_sensitive: bool = False
    ) -> SystemConfig:
        """Set system configuration"""
        # Check if exists
        existing = await self.get_config(config_key)

        if existing:
            existing.config_value = config_value
            existing.category = category
            existing.is_sensitive = is_sensitive
            existing.updated_by = updated_by
            existing.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            config = SystemConfig(
                config_key=config_key,
                config_value=config_value,
                category=category,
                is_sensitive=is_sensitive,
                updated_by=updated_by
            )
            self.db.add(config)
            await self.db.flush()
            await self.db.refresh(config)
            return config

    async def delete_config(self, config_key: str) -> bool:
        """Delete system configuration"""
        config = await self.get_config(config_key)
        if not config:
            return False

        await self.db.delete(config)
        await self.db.flush()
        return True

    # ========================================================================
    # Dashboard Statistics
    # ========================================================================

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get admin dashboard statistics"""
        # Total users
        users_query = select(func.count(User.id))
        users_result = await self.db.execute(users_query)
        total_users = users_result.scalar()

        # Active users (last 30 days)
        active_cutoff = datetime.utcnow() - timedelta(days=30)
        active_users_query = select(func.count(User.id)).where(
            User.last_login >= active_cutoff
        )
        active_result = await self.db.execute(active_users_query)
        active_users = active_result.scalar()

        # Total vendors
        vendors_query = select(func.count(Vendor.id))
        vendors_result = await self.db.execute(vendors_query)
        total_vendors = vendors_result.scalar()

        # Pending vendor approvals
        pending_vendors_query = select(func.count(Vendor.id)).where(
            Vendor.is_verified == False
        )
        pending_vendors_result = await self.db.execute(pending_vendors_query)
        pending_vendors = pending_vendors_result.scalar()

        # Total events
        events_query = select(func.count(Event.id))
        events_result = await self.db.execute(events_query)
        total_events = events_result.scalar()

        # Moderation queue size
        moderation_stats = await self.get_moderation_stats()

        return {
            "total_users": total_users,
            "active_users_30d": active_users,
            "total_vendors": total_vendors,
            "pending_vendor_approvals": pending_vendors,
            "total_events": total_events,
            "moderation_queue_size": moderation_stats["pending_count"],
            "moderation_stats": moderation_stats
        }
