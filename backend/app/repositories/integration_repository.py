"""
Integration Hub Repository
Sprint 20: Integration Hub

Repository layer for third-party integrations, webhooks, and OAuth management.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import secrets
import json

from app.models.integration import (
    Integration, Webhook, WebhookDelivery,
    IntegrationType, IntegrationStatus
)
from app.schemas.integration import (
    IntegrationCreate, IntegrationUpdate,
    WebhookCreate, WebhookUpdate
)


class IntegrationRepository:
    """Repository for integration operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Integration Operations
    # ========================================================================

    async def create_integration(
        self,
        integration_data: IntegrationCreate,
        user_id: UUID
    ) -> Integration:
        """Create a new integration"""
        # In production, encrypt credentials before storing
        # encrypted_credentials = encrypt(integration_data.credentials)

        integration = Integration(
            user_id=user_id,
            integration_type=integration_data.integration_type,
            provider=integration_data.provider,
            credentials=integration_data.credentials,  # Should be encrypted
            config=integration_data.config,
            status=IntegrationStatus.ACTIVE
        )

        self.db.add(integration)
        await self.db.flush()
        return integration

    async def get_integration_by_id(
        self,
        integration_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[Integration]:
        """Get integration by ID"""
        stmt = select(Integration).where(Integration.id == integration_id)
        if user_id:
            stmt = stmt.where(Integration.user_id == user_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_integrations(
        self,
        user_id: UUID,
        integration_type: Optional[str] = None,
        provider: Optional[str] = None
    ) -> List[Integration]:
        """Get all integrations for a user"""
        stmt = select(Integration).where(Integration.user_id == user_id)

        if integration_type:
            stmt = stmt.where(Integration.integration_type == integration_type)
        if provider:
            stmt = stmt.where(Integration.provider == provider)

        stmt = stmt.order_by(Integration.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_integration_by_provider(
        self,
        user_id: UUID,
        provider: str
    ) -> Optional[Integration]:
        """Get integration for a specific provider"""
        stmt = select(Integration).where(
            and_(
                Integration.user_id == user_id,
                Integration.provider == provider,
                Integration.status == IntegrationStatus.ACTIVE
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_integration(
        self,
        integration_id: UUID,
        user_id: UUID,
        integration_update: IntegrationUpdate
    ) -> Optional[Integration]:
        """Update integration"""
        integration = await self.get_integration_by_id(integration_id, user_id)
        if not integration:
            return None

        update_data = integration_update.dict(exclude_unset=True)

        # In production, encrypt credentials if being updated
        if 'credentials' in update_data:
            # update_data['credentials'] = encrypt(update_data['credentials'])
            pass

        for key, value in update_data.items():
            setattr(integration, key, value)

        integration.updated_at = datetime.utcnow()
        return integration

    async def delete_integration(
        self,
        integration_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete integration"""
        stmt = delete(Integration).where(
            and_(
                Integration.id == integration_id,
                Integration.user_id == user_id
            )
        )

        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def update_integration_sync(
        self,
        integration_id: UUID,
        success: bool,
        error_message: Optional[str] = None
    ) -> None:
        """Update integration sync status"""
        update_data = {
            "last_sync_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        if success:
            update_data["status"] = IntegrationStatus.ACTIVE
            update_data["error_message"] = None
        else:
            update_data["status"] = IntegrationStatus.ERROR
            update_data["error_message"] = error_message

        stmt = update(Integration).where(
            Integration.id == integration_id
        ).values(**update_data)

        await self.db.execute(stmt)

    async def get_credentials(
        self,
        integration_id: UUID,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get decrypted credentials for an integration"""
        integration = await self.get_integration_by_id(integration_id, user_id)
        if not integration:
            return None

        # In production, decrypt credentials
        # credentials = decrypt(integration.credentials)
        credentials = integration.credentials

        return credentials

    # ========================================================================
    # Webhook Operations
    # ========================================================================

    async def create_webhook(
        self,
        webhook_data: WebhookCreate,
        user_id: UUID
    ) -> Webhook:
        """Create a new webhook"""
        # Generate secret if not provided
        secret = webhook_data.secret or secrets.token_urlsafe(32)

        webhook = Webhook(
            user_id=user_id,
            event_type=webhook_data.event_type,
            url=str(webhook_data.url),
            secret=secret,
            is_active=True
        )

        self.db.add(webhook)
        await self.db.flush()
        return webhook

    async def get_webhook_by_id(
        self,
        webhook_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[Webhook]:
        """Get webhook by ID"""
        stmt = select(Webhook).where(Webhook.id == webhook_id)
        if user_id:
            stmt = stmt.where(Webhook.user_id == user_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_webhooks(
        self,
        user_id: UUID,
        event_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[Webhook]:
        """Get all webhooks for a user"""
        stmt = select(Webhook).where(Webhook.user_id == user_id)

        if event_type:
            stmt = stmt.where(Webhook.event_type == event_type)
        if active_only:
            stmt = stmt.where(Webhook.is_active == True)

        stmt = stmt.order_by(Webhook.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_webhooks_by_event(
        self,
        event_type: str,
        user_id: Optional[UUID] = None
    ) -> List[Webhook]:
        """Get all active webhooks for an event type"""
        stmt = select(Webhook).where(
            and_(
                Webhook.event_type == event_type,
                Webhook.is_active == True
            )
        )

        if user_id:
            stmt = stmt.where(Webhook.user_id == user_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_webhook(
        self,
        webhook_id: UUID,
        user_id: UUID,
        webhook_update: WebhookUpdate
    ) -> Optional[Webhook]:
        """Update webhook"""
        webhook = await self.get_webhook_by_id(webhook_id, user_id)
        if not webhook:
            return None

        update_data = webhook_update.dict(exclude_unset=True)

        if 'url' in update_data:
            update_data['url'] = str(update_data['url'])

        for key, value in update_data.items():
            setattr(webhook, key, value)

        return webhook

    async def delete_webhook(
        self,
        webhook_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete webhook"""
        stmt = delete(Webhook).where(
            and_(
                Webhook.id == webhook_id,
                Webhook.user_id == user_id
            )
        )

        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def toggle_webhook(
        self,
        webhook_id: UUID,
        user_id: UUID,
        is_active: bool
    ) -> Optional[Webhook]:
        """Enable or disable a webhook"""
        webhook = await self.get_webhook_by_id(webhook_id, user_id)
        if not webhook:
            return None

        webhook.is_active = is_active
        return webhook

    # ========================================================================
    # Webhook Delivery Operations
    # ========================================================================

    async def create_webhook_delivery(
        self,
        webhook_id: UUID,
        payload: Dict[str, Any],
        status_code: Optional[int] = None,
        response_body: Optional[str] = None
    ) -> WebhookDelivery:
        """Record a webhook delivery attempt"""
        delivery = WebhookDelivery(
            webhook_id=webhook_id,
            payload=payload,
            status_code=status_code,
            response_body=response_body
        )

        self.db.add(delivery)
        await self.db.flush()
        return delivery

    async def get_webhook_deliveries(
        self,
        webhook_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[WebhookDelivery], int]:
        """Get delivery history for a webhook"""
        stmt = select(WebhookDelivery).where(
            WebhookDelivery.webhook_id == webhook_id
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar()

        stmt = stmt.offset(skip).limit(limit).order_by(
            WebhookDelivery.delivered_at.desc()
        )

        result = await self.db.execute(stmt)
        deliveries = result.scalars().all()

        return list(deliveries), total

    async def get_recent_deliveries(
        self,
        webhook_id: UUID,
        hours_back: int = 24,
        limit: int = 100
    ) -> List[WebhookDelivery]:
        """Get recent webhook deliveries"""
        since_date = datetime.utcnow() - timedelta(hours=hours_back)

        stmt = select(WebhookDelivery).where(
            and_(
                WebhookDelivery.webhook_id == webhook_id,
                WebhookDelivery.delivered_at >= since_date
            )
        ).order_by(WebhookDelivery.delivered_at.desc()).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_webhook_delivery_stats(
        self,
        webhook_id: UUID,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """Get webhook delivery statistics"""
        since_date = datetime.utcnow() - timedelta(days=days_back)

        stmt = select(WebhookDelivery).where(
            and_(
                WebhookDelivery.webhook_id == webhook_id,
                WebhookDelivery.delivered_at >= since_date
            )
        )

        result = await self.db.execute(stmt)
        deliveries = result.scalars().all()

        total_deliveries = len(deliveries)
        successful_deliveries = sum(
            1 for d in deliveries
            if d.status_code and 200 <= d.status_code < 300
        )
        failed_deliveries = total_deliveries - successful_deliveries

        success_rate = (
            (successful_deliveries / total_deliveries * 100)
            if total_deliveries > 0 else 0
        )

        return {
            "total_deliveries": total_deliveries,
            "successful_deliveries": successful_deliveries,
            "failed_deliveries": failed_deliveries,
            "success_rate": success_rate
        }

    # ========================================================================
    # Integration Analytics
    # ========================================================================

    async def get_integration_stats(
        self,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get integration statistics for user"""
        stmt = select(Integration).where(Integration.user_id == user_id)
        result = await self.db.execute(stmt)
        integrations = result.scalars().all()

        total_integrations = len(integrations)
        active_integrations = sum(
            1 for i in integrations
            if i.status == IntegrationStatus.ACTIVE
        )
        error_integrations = sum(
            1 for i in integrations
            if i.status == IntegrationStatus.ERROR
        )

        # Group by type
        by_type = {}
        for integration in integrations:
            type_name = integration.integration_type
            by_type[type_name] = by_type.get(type_name, 0) + 1

        # Group by provider
        by_provider = {}
        for integration in integrations:
            provider = integration.provider
            by_provider[provider] = by_provider.get(provider, 0) + 1

        return {
            "total_integrations": total_integrations,
            "active_integrations": active_integrations,
            "error_integrations": error_integrations,
            "by_type": by_type,
            "by_provider": by_provider
        }

    async def get_webhook_stats(
        self,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get webhook statistics for user"""
        stmt = select(Webhook).where(Webhook.user_id == user_id)
        result = await self.db.execute(stmt)
        webhooks = result.scalars().all()

        total_webhooks = len(webhooks)
        active_webhooks = sum(1 for w in webhooks if w.is_active)

        # Group by event type
        by_event = {}
        for webhook in webhooks:
            event_type = webhook.event_type
            by_event[event_type] = by_event.get(event_type, 0) + 1

        return {
            "total_webhooks": total_webhooks,
            "active_webhooks": active_webhooks,
            "inactive_webhooks": total_webhooks - active_webhooks,
            "by_event_type": by_event
        }

    # ========================================================================
    # Bulk Operations
    # ========================================================================

    async def get_integrations_for_sync(
        self,
        integration_type: Optional[str] = None,
        older_than_hours: int = 24,
        limit: int = 100
    ) -> List[Integration]:
        """Get integrations that need syncing"""
        since_date = datetime.utcnow() - timedelta(hours=older_than_hours)

        stmt = select(Integration).where(
            and_(
                Integration.status == IntegrationStatus.ACTIVE,
                or_(
                    Integration.last_sync_at.is_(None),
                    Integration.last_sync_at < since_date
                )
            )
        )

        if integration_type:
            stmt = stmt.where(Integration.integration_type == integration_type)

        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def cleanup_old_webhook_deliveries(
        self,
        days_to_keep: int = 30
    ) -> int:
        """Delete old webhook delivery records"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        stmt = delete(WebhookDelivery).where(
            WebhookDelivery.delivered_at < cutoff_date
        )

        result = await self.db.execute(stmt)
        return result.rowcount
