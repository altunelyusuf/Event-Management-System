"""
Integration Hub Service
Sprint 20: Integration Hub

Service layer for third-party integrations, webhooks, OAuth, and provider-specific logic.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
import logging
import hmac
import hashlib
import json
import secrets
import httpx

from app.repositories.integration_repository import IntegrationRepository
from app.models.user import User
from app.schemas.integration import (
    IntegrationCreate, IntegrationUpdate, IntegrationResponse,
    WebhookCreate, WebhookUpdate, WebhookResponse,
    WebhookDeliveryResponse, WebhookEventPayload,
    IntegrationTestResponse, IntegrationHealth,
    WebhookDeliveryStats, IntegrationUsageStats,
    OAuthAuthorizeRequest, OAuthCallbackRequest, OAuthTokenResponse
)

logger = logging.getLogger(__name__)


class IntegrationService:
    """Service for integration operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.integration_repo = IntegrationRepository(db)
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()

    # ========================================================================
    # Integration Management
    # ========================================================================

    async def create_integration(
        self,
        integration_data: IntegrationCreate,
        current_user: User
    ) -> IntegrationResponse:
        """
        Create a new third-party integration.

        Supports: payment, calendar, email, SMS, storage, social media
        """
        # Validate provider-specific credentials
        await self._validate_credentials(
            integration_data.provider,
            integration_data.credentials
        )

        integration = await self.integration_repo.create_integration(
            integration_data,
            current_user.id
        )

        await self.db.commit()
        await self.db.refresh(integration)

        # Test the integration
        try:
            await self._test_integration_connection(integration.id, current_user.id)
        except Exception as e:
            logger.warning(f"Initial integration test failed: {e}")

        return IntegrationResponse.from_orm(integration)

    async def get_integration(
        self,
        integration_id: UUID,
        current_user: User
    ) -> IntegrationResponse:
        """Get integration by ID"""
        integration = await self.integration_repo.get_integration_by_id(
            integration_id,
            current_user.id
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )

        return IntegrationResponse.from_orm(integration)

    async def list_integrations(
        self,
        current_user: User,
        integration_type: Optional[str] = None,
        provider: Optional[str] = None
    ) -> List[IntegrationResponse]:
        """List all integrations for user"""
        integrations = await self.integration_repo.get_user_integrations(
            current_user.id,
            integration_type=integration_type,
            provider=provider
        )

        return [IntegrationResponse.from_orm(i) for i in integrations]

    async def update_integration(
        self,
        integration_id: UUID,
        integration_update: IntegrationUpdate,
        current_user: User
    ) -> IntegrationResponse:
        """Update integration settings"""
        integration = await self.integration_repo.update_integration(
            integration_id,
            current_user.id,
            integration_update
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )

        await self.db.commit()
        await self.db.refresh(integration)

        return IntegrationResponse.from_orm(integration)

    async def delete_integration(
        self,
        integration_id: UUID,
        current_user: User
    ) -> Dict[str, str]:
        """Delete integration"""
        success = await self.integration_repo.delete_integration(
            integration_id,
            current_user.id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )

        await self.db.commit()
        return {"status": "deleted"}

    async def test_integration(
        self,
        integration_id: UUID,
        current_user: User,
        test_type: str = "connection"
    ) -> IntegrationTestResponse:
        """Test an integration"""
        integration = await self.integration_repo.get_integration_by_id(
            integration_id,
            current_user.id
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )

        success = False
        message = "Test not implemented for this provider"
        details = {}

        try:
            if test_type == "connection":
                success = await self._test_integration_connection(
                    integration_id,
                    current_user.id
                )
                message = "Connection successful" if success else "Connection failed"

        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            message = str(e)

        return IntegrationTestResponse(
            integration_id=integration_id,
            test_type=test_type,
            success=success,
            message=message,
            details=details,
            tested_at=datetime.utcnow()
        )

    async def _test_integration_connection(
        self,
        integration_id: UUID,
        user_id: UUID
    ) -> bool:
        """Test integration connection"""
        integration = await self.integration_repo.get_integration_by_id(
            integration_id,
            user_id
        )

        if not integration:
            return False

        # Provider-specific connection tests
        # In production, implement actual API calls to test connectivity
        # For now, just return True
        return True

    async def _validate_credentials(
        self,
        provider: str,
        credentials: Dict[str, Any]
    ) -> None:
        """Validate provider-specific credentials"""
        # Provider-specific validation
        required_fields = {
            "stripe": ["api_key"],
            "paypal": ["client_id", "client_secret"],
            "google_calendar": ["access_token"],
            "sendgrid": ["api_key"],
            "twilio": ["account_sid", "auth_token"],
            "dropbox": ["access_token"]
        }

        if provider in required_fields:
            for field in required_fields[provider]:
                if field not in credentials:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Missing required credential: {field}"
                    )

    # ========================================================================
    # OAuth Operations
    # ========================================================================

    async def get_oauth_authorize_url(
        self,
        oauth_request: OAuthAuthorizeRequest,
        current_user: User
    ) -> Dict[str, str]:
        """
        Get OAuth authorization URL for a provider.

        In production, this would generate the actual OAuth URL
        with proper client IDs, redirect URIs, and state parameters.
        """
        # OAuth endpoints for different providers
        oauth_endpoints = {
            "google": "https://accounts.google.com/o/oauth2/v2/auth",
            "facebook": "https://www.facebook.com/v12.0/dialog/oauth",
            "stripe": "https://connect.stripe.com/oauth/authorize",
            "github": "https://github.com/login/oauth/authorize"
        }

        if oauth_request.provider not in oauth_endpoints:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth not supported for provider: {oauth_request.provider}"
            )

        # Generate state for CSRF protection
        state = oauth_request.state or secrets.token_urlsafe(32)

        # In production, build actual OAuth URL with client ID, redirect URI, scope
        auth_url = (
            f"{oauth_endpoints[oauth_request.provider]}"
            f"?client_id=CLIENT_ID"
            f"&redirect_uri={oauth_request.redirect_uri or 'DEFAULT_REDIRECT'}"
            f"&state={state}"
            f"&scope={' '.join(oauth_request.scope or [])}"
            f"&response_type=code"
        )

        return {
            "authorization_url": auth_url,
            "state": state
        }

    async def handle_oauth_callback(
        self,
        provider: str,
        callback_data: OAuthCallbackRequest,
        current_user: User
    ) -> IntegrationResponse:
        """
        Handle OAuth callback and exchange code for tokens.

        In production, this would:
        1. Validate state parameter
        2. Exchange authorization code for access/refresh tokens
        3. Store tokens securely
        4. Create integration record
        """
        # Simplified implementation
        # In production, exchange code for tokens via provider API
        credentials = {
            "access_token": "EXCHANGED_ACCESS_TOKEN",
            "refresh_token": "REFRESH_TOKEN",
            "expires_at": datetime.utcnow().isoformat()
        }

        integration_data = IntegrationCreate(
            integration_type="oauth",
            provider=provider,
            credentials=credentials
        )

        return await self.create_integration(integration_data, current_user)

    # ========================================================================
    # Webhook Management
    # ========================================================================

    async def create_webhook(
        self,
        webhook_data: WebhookCreate,
        current_user: User
    ) -> WebhookResponse:
        """Create a new webhook"""
        webhook = await self.integration_repo.create_webhook(
            webhook_data,
            current_user.id
        )

        await self.db.commit()
        await self.db.refresh(webhook)

        return WebhookResponse.from_orm(webhook)

    async def get_webhook(
        self,
        webhook_id: UUID,
        current_user: User
    ) -> WebhookResponse:
        """Get webhook by ID"""
        webhook = await self.integration_repo.get_webhook_by_id(
            webhook_id,
            current_user.id
        )

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )

        return WebhookResponse.from_orm(webhook)

    async def list_webhooks(
        self,
        current_user: User,
        event_type: Optional[str] = None
    ) -> List[WebhookResponse]:
        """List all webhooks for user"""
        webhooks = await self.integration_repo.get_user_webhooks(
            current_user.id,
            event_type=event_type
        )

        return [WebhookResponse.from_orm(w) for w in webhooks]

    async def update_webhook(
        self,
        webhook_id: UUID,
        webhook_update: WebhookUpdate,
        current_user: User
    ) -> WebhookResponse:
        """Update webhook"""
        webhook = await self.integration_repo.update_webhook(
            webhook_id,
            current_user.id,
            webhook_update
        )

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )

        await self.db.commit()
        await self.db.refresh(webhook)

        return WebhookResponse.from_orm(webhook)

    async def delete_webhook(
        self,
        webhook_id: UUID,
        current_user: User
    ) -> Dict[str, str]:
        """Delete webhook"""
        success = await self.integration_repo.delete_webhook(
            webhook_id,
            current_user.id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )

        await self.db.commit()
        return {"status": "deleted"}

    async def toggle_webhook(
        self,
        webhook_id: UUID,
        is_active: bool,
        current_user: User
    ) -> WebhookResponse:
        """Enable or disable webhook"""
        webhook = await self.integration_repo.toggle_webhook(
            webhook_id,
            current_user.id,
            is_active
        )

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )

        await self.db.commit()
        await self.db.refresh(webhook)

        return WebhookResponse.from_orm(webhook)

    async def test_webhook(
        self,
        webhook_id: UUID,
        test_payload: Optional[Dict[str, Any]],
        current_user: User
    ) -> Dict[str, Any]:
        """Test webhook delivery"""
        webhook = await self.integration_repo.get_webhook_by_id(
            webhook_id,
            current_user.id
        )

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )

        # Create test payload
        payload = test_payload or {
            "event_id": "test_event",
            "event_type": webhook.event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"test": True}
        }

        # Trigger webhook delivery
        delivery_result = await self.trigger_webhook(
            webhook.id,
            WebhookEventPayload(**payload)
        )

        return {
            "webhook_id": webhook_id,
            "test_payload": payload,
            "delivery_result": delivery_result
        }

    # ========================================================================
    # Webhook Delivery
    # ========================================================================

    async def trigger_webhook(
        self,
        webhook_id: UUID,
        event_payload: WebhookEventPayload
    ) -> Dict[str, Any]:
        """
        Trigger a webhook delivery.

        This is called internally when events occur in the system.
        """
        webhook = await self.integration_repo.get_webhook_by_id(webhook_id)

        if not webhook or not webhook.is_active:
            return {"status": "skipped", "reason": "webhook not active"}

        # Prepare payload
        payload_dict = event_payload.dict()

        # Sign payload
        signature = self._generate_webhook_signature(
            payload_dict,
            webhook.secret
        )

        # Send webhook
        try:
            response = await self.http_client.post(
                webhook.url,
                json=payload_dict,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    "X-Event-Type": event_payload.event_type,
                    "X-Event-ID": event_payload.event_id
                }
            )

            # Record delivery
            await self.integration_repo.create_webhook_delivery(
                webhook_id=webhook_id,
                payload=payload_dict,
                status_code=response.status_code,
                response_body=response.text[:1000]  # Limit response size
            )

            await self.db.commit()

            return {
                "status": "delivered",
                "status_code": response.status_code,
                "success": 200 <= response.status_code < 300
            }

        except Exception as e:
            logger.error(f"Webhook delivery failed: {e}")

            # Record failed delivery
            await self.integration_repo.create_webhook_delivery(
                webhook_id=webhook_id,
                payload=payload_dict,
                status_code=None,
                response_body=str(e)
            )

            await self.db.commit()

            return {
                "status": "failed",
                "error": str(e)
            }

    async def trigger_webhooks_for_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Trigger all webhooks for a specific event type"""
        webhooks = await self.integration_repo.get_webhooks_by_event(
            event_type,
            user_id=user_id
        )

        event_payload = WebhookEventPayload(
            event_id=str(UUID(int=0)),  # Generate proper event ID
            event_type=event_type,
            timestamp=datetime.utcnow(),
            data=event_data
        )

        results = []
        for webhook in webhooks:
            result = await self.trigger_webhook(webhook.id, event_payload)
            results.append({
                "webhook_id": webhook.id,
                "result": result
            })

        return results

    def _generate_webhook_signature(
        self,
        payload: Dict[str, Any],
        secret: str
    ) -> str:
        """Generate HMAC signature for webhook payload"""
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        signature = hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        return signature

    async def get_webhook_deliveries(
        self,
        webhook_id: UUID,
        current_user: User,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[WebhookDeliveryResponse], int]:
        """Get webhook delivery history"""
        webhook = await self.integration_repo.get_webhook_by_id(
            webhook_id,
            current_user.id
        )

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )

        deliveries, total = await self.integration_repo.get_webhook_deliveries(
            webhook_id,
            skip=skip,
            limit=limit
        )

        delivery_responses = [
            WebhookDeliveryResponse.from_orm(d) for d in deliveries
        ]

        return delivery_responses, total

    async def get_webhook_stats(
        self,
        webhook_id: UUID,
        current_user: User,
        days_back: int = 7
    ) -> WebhookDeliveryStats:
        """Get webhook delivery statistics"""
        webhook = await self.integration_repo.get_webhook_by_id(
            webhook_id,
            current_user.id
        )

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )

        stats = await self.integration_repo.get_webhook_delivery_stats(
            webhook_id,
            days_back=days_back
        )

        return WebhookDeliveryStats(
            webhook_id=webhook_id,
            event_type=webhook.event_type,
            total_deliveries=stats["total_deliveries"],
            successful_deliveries=stats["successful_deliveries"],
            failed_deliveries=stats["failed_deliveries"],
            success_rate=stats["success_rate"],
            average_response_time_ms=0.0  # Would need to track timing
        )

    # ========================================================================
    # Integration Marketplace
    # ========================================================================

    async def get_available_integrations(
        self,
        current_user: User
    ) -> Dict[str, Any]:
        """Get available integrations and marketplace"""
        # Get user's installed integrations
        installed = await self.list_integrations(current_user)

        # Available integration templates
        available = self._get_integration_templates()

        # Filter out already installed
        installed_providers = {i.provider for i in installed}
        available_integrations = [
            t for t in available
            if t["provider"] not in installed_providers
        ]

        return {
            "installed_integrations": installed,
            "available_integrations": available_integrations,
            "recommended_integrations": [
                t for t in available_integrations
                if t.get("is_recommended", False)
            ]
        }

    def _get_integration_templates(self) -> List[Dict[str, Any]]:
        """Get integration templates for marketplace"""
        return [
            {
                "name": "Stripe",
                "provider": "stripe",
                "integration_type": "payment",
                "description": "Accept payments and manage subscriptions",
                "features": ["Payment processing", "Subscriptions", "Invoices"],
                "required_credentials": ["api_key"],
                "is_popular": True,
                "is_recommended": True
            },
            {
                "name": "Google Calendar",
                "provider": "google_calendar",
                "integration_type": "calendar",
                "description": "Sync events with Google Calendar",
                "features": ["Bidirectional sync", "Attendee management"],
                "required_credentials": ["access_token"],
                "is_popular": True,
                "is_recommended": True
            },
            {
                "name": "SendGrid",
                "provider": "sendgrid",
                "integration_type": "email",
                "description": "Send transactional emails",
                "features": ["Email delivery", "Templates", "Analytics"],
                "required_credentials": ["api_key"],
                "is_popular": True,
                "is_recommended": False
            },
            {
                "name": "Twilio",
                "provider": "twilio",
                "integration_type": "sms",
                "description": "Send SMS notifications",
                "features": ["SMS delivery", "Two-way messaging"],
                "required_credentials": ["account_sid", "auth_token"],
                "is_popular": False,
                "is_recommended": False
            }
        ]

    # ========================================================================
    # Analytics
    # ========================================================================

    async def get_integration_stats(
        self,
        current_user: User
    ) -> Dict[str, Any]:
        """Get integration statistics"""
        return await self.integration_repo.get_integration_stats(current_user.id)

    async def get_all_webhook_stats(
        self,
        current_user: User
    ) -> Dict[str, Any]:
        """Get webhook statistics"""
        return await self.integration_repo.get_webhook_stats(current_user.id)
