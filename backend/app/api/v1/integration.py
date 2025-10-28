"""
Integration Hub API
Sprint 20: Integration Hub

API endpoints for third-party integrations, webhooks, and OAuth management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.integration_service import IntegrationService
from app.schemas.integration import (
    # Integration schemas
    IntegrationCreate, IntegrationUpdate, IntegrationResponse,
    IntegrationTestRequest, IntegrationTestResponse,
    # Webhook schemas
    WebhookCreate, WebhookUpdate, WebhookResponse,
    WebhookDeliveryResponse, WebhookTestRequest,
    WebhookDeliveryStats,
    # OAuth schemas
    OAuthAuthorizeRequest, OAuthCallbackRequest,
    # Provider-specific schemas
    StripeConnectRequest, PayPalConnectRequest,
    CalendarSyncRequest, CalendarSyncResponse,
    EmailProviderConnect, SMSProviderConnect,
    CloudStorageConnect
)

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_integration_service(db: AsyncSession = Depends(get_db)) -> IntegrationService:
    """Get integration service instance"""
    async with IntegrationService(db) as service:
        yield service


# ============================================================================
# Integration Management Endpoints
# ============================================================================

@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    integration_data: IntegrationCreate,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """
    Create a new third-party integration.

    Supported integration types:
    - payment: Stripe, PayPal, Square
    - calendar: Google Calendar, Outlook, Apple Calendar
    - email: SendGrid, Mailchimp, AWS SES
    - sms: Twilio, Nexmo
    - cloud_storage: Dropbox, Google Drive, OneDrive
    - social_media: Facebook, Instagram, Twitter
    - analytics: Google Analytics, Mixpanel
    """
    return await integration_service.create_integration(integration_data, current_user)


@router.get("", response_model=List[IntegrationResponse])
async def list_integrations(
    integration_type: Optional[str] = None,
    provider: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """List all integrations for the current user"""
    return await integration_service.list_integrations(
        current_user,
        integration_type=integration_type,
        provider=provider
    )


@router.get("/marketplace")
async def get_integration_marketplace(
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """
    Get integration marketplace.

    Returns:
    - Available integrations
    - Installed integrations
    - Recommended integrations
    """
    return await integration_service.get_available_integrations(current_user)


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: UUID,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Get integration by ID"""
    return await integration_service.get_integration(integration_id, current_user)


@router.put("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: UUID,
    integration_update: IntegrationUpdate,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Update integration settings"""
    return await integration_service.update_integration(
        integration_id,
        integration_update,
        current_user
    )


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: UUID,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Delete an integration"""
    await integration_service.delete_integration(integration_id, current_user)


@router.post("/{integration_id}/test", response_model=IntegrationTestResponse)
async def test_integration(
    integration_id: UUID,
    test_type: str = "connection",
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """
    Test an integration.

    Test types:
    - connection: Test API connectivity
    - api_call: Test a sample API call
    - webhook: Test webhook delivery
    """
    return await integration_service.test_integration(
        integration_id,
        current_user,
        test_type=test_type
    )


@router.get("/stats", response_model=Dict[str, Any])
async def get_integration_stats(
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Get integration usage statistics"""
    return await integration_service.get_integration_stats(current_user)


# ============================================================================
# OAuth Endpoints
# ============================================================================

@router.post("/oauth/authorize")
async def oauth_authorize(
    oauth_request: OAuthAuthorizeRequest,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """
    Get OAuth authorization URL for a provider.

    Supported providers:
    - google: Google services (Calendar, Drive, etc.)
    - facebook: Facebook
    - stripe: Stripe Connect
    - github: GitHub
    """
    return await integration_service.get_oauth_authorize_url(oauth_request, current_user)


@router.post("/oauth/callback/{provider}", response_model=IntegrationResponse)
async def oauth_callback(
    provider: str,
    callback_data: OAuthCallbackRequest,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Handle OAuth callback and create integration"""
    return await integration_service.handle_oauth_callback(
        provider,
        callback_data,
        current_user
    )


# ============================================================================
# Webhook Management Endpoints
# ============================================================================

@router.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    webhook_data: WebhookCreate,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """
    Create a new webhook endpoint.

    Webhooks allow you to receive real-time notifications when events occur.

    Supported event types:
    - event.created, event.updated, event.deleted
    - booking.created, booking.confirmed, booking.cancelled
    - payment.succeeded, payment.failed
    - task.created, task.completed
    - guest.rsvp_received
    """
    return await integration_service.create_webhook(webhook_data, current_user)


@router.get("/webhooks", response_model=List[WebhookResponse])
async def list_webhooks(
    event_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """List all webhooks for the current user"""
    return await integration_service.list_webhooks(current_user, event_type=event_type)


@router.get("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: UUID,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Get webhook by ID"""
    return await integration_service.get_webhook(webhook_id, current_user)


@router.put("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: UUID,
    webhook_update: WebhookUpdate,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Update webhook settings"""
    return await integration_service.update_webhook(webhook_id, webhook_update, current_user)


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: UUID,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Delete a webhook"""
    await integration_service.delete_webhook(webhook_id, current_user)


@router.post("/webhooks/{webhook_id}/toggle", response_model=WebhookResponse)
async def toggle_webhook(
    webhook_id: UUID,
    is_active: bool,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Enable or disable a webhook"""
    return await integration_service.toggle_webhook(webhook_id, is_active, current_user)


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: UUID,
    test_payload: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """
    Test webhook delivery with a sample payload.

    Sends a test event to the webhook URL to verify connectivity.
    """
    return await integration_service.test_webhook(webhook_id, test_payload, current_user)


@router.get("/webhooks/{webhook_id}/deliveries", response_model=List[WebhookDeliveryResponse])
async def get_webhook_deliveries(
    webhook_id: UUID,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Get webhook delivery history"""
    deliveries, _ = await integration_service.get_webhook_deliveries(
        webhook_id,
        current_user,
        skip=skip,
        limit=limit
    )
    return deliveries


@router.get("/webhooks/{webhook_id}/stats", response_model=WebhookDeliveryStats)
async def get_webhook_stats(
    webhook_id: UUID,
    days_back: int = 7,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Get webhook delivery statistics"""
    return await integration_service.get_webhook_stats(webhook_id, current_user, days_back)


@router.get("/webhooks/stats/all")
async def get_all_webhook_stats(
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Get statistics for all webhooks"""
    return await integration_service.get_all_webhook_stats(current_user)


# ============================================================================
# Provider-Specific Endpoints
# ============================================================================

# Payment Providers

@router.post("/providers/stripe/connect")
async def connect_stripe(
    stripe_data: StripeConnectRequest,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Connect Stripe payment gateway"""
    integration_data = IntegrationCreate(
        integration_type="payment",
        provider="stripe",
        credentials={"authorization_code": stripe_data.authorization_code}
    )
    return await integration_service.create_integration(integration_data, current_user)


@router.post("/providers/paypal/connect")
async def connect_paypal(
    paypal_data: PayPalConnectRequest,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Connect PayPal payment gateway"""
    integration_data = IntegrationCreate(
        integration_type="payment",
        provider="paypal",
        credentials={"authorization_code": paypal_data.authorization_code}
    )
    return await integration_service.create_integration(integration_data, current_user)


# Calendar Providers

@router.post("/providers/calendar/sync")
async def sync_calendar(
    sync_request: CalendarSyncRequest,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """
    Sync events with calendar provider.

    Supports bidirectional sync with Google Calendar, Outlook, and Apple Calendar.
    """
    # In production, implement actual calendar sync logic
    return CalendarSyncResponse(
        provider="google_calendar",
        events_synced=0,
        events_created=0,
        events_updated=0,
        events_deleted=0,
        last_sync_at=datetime.utcnow()
    )


# Email Providers

@router.post("/providers/email/connect")
async def connect_email_provider(
    email_data: EmailProviderConnect,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Connect email service provider"""
    integration_data = IntegrationCreate(
        integration_type="email",
        provider=email_data.provider,
        credentials={"api_key": email_data.api_key},
        config=email_data.config
    )
    return await integration_service.create_integration(integration_data, current_user)


# SMS Providers

@router.post("/providers/sms/connect")
async def connect_sms_provider(
    sms_data: SMSProviderConnect,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Connect SMS service provider"""
    integration_data = IntegrationCreate(
        integration_type="sms",
        provider=sms_data.provider,
        credentials={
            "account_sid": sms_data.account_sid,
            "auth_token": sms_data.auth_token
        },
        config={"phone_number": sms_data.phone_number} if sms_data.phone_number else None
    )
    return await integration_service.create_integration(integration_data, current_user)


# Cloud Storage Providers

@router.post("/providers/storage/connect")
async def connect_cloud_storage(
    storage_data: CloudStorageConnect,
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Connect cloud storage provider"""
    integration_data = IntegrationCreate(
        integration_type="cloud_storage",
        provider=storage_data.provider,
        credentials=storage_data.credentials
    )
    return await integration_service.create_integration(integration_data, current_user)


# ============================================================================
# Health & Diagnostics Endpoints
# ============================================================================

@router.get("/health")
async def health_check():
    """Integration Hub health check"""
    return {
        "status": "healthy",
        "service": "integration-hub",
        "features": {
            "integrations": True,
            "webhooks": True,
            "oauth": True,
            "supported_providers": [
                "stripe", "paypal", "google_calendar",
                "sendgrid", "twilio", "dropbox",
                "facebook", "instagram", "twitter"
            ]
        }
    }


@router.get("/event-types")
async def get_available_event_types():
    """
    Get available webhook event types.

    Returns all event types that can be subscribed to via webhooks.
    """
    return {
        "event_types": [
            # Event lifecycle
            "event.created",
            "event.updated",
            "event.deleted",
            "event.published",
            # Booking lifecycle
            "booking.created",
            "booking.confirmed",
            "booking.cancelled",
            "booking.completed",
            # Payment events
            "payment.initiated",
            "payment.succeeded",
            "payment.failed",
            "payment.refunded",
            # Task events
            "task.created",
            "task.assigned",
            "task.completed",
            "task.overdue",
            # Guest events
            "guest.invited",
            "guest.rsvp_received",
            "guest.checked_in",
            # Review events
            "review.submitted",
            "review.approved",
            # Document events
            "document.uploaded",
            "document.shared",
            # Message events
            "message.received",
            "message.sent"
        ]
    }


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.post("/webhooks/validate-signature")
async def validate_webhook_signature(
    payload: Dict[str, Any],
    signature: str,
    secret: str
):
    """
    Validate webhook signature.

    Helper endpoint for webhook consumers to validate HMAC signatures.
    """
    import hmac
    import hashlib
    import json

    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    expected_signature = hmac.new(
        secret.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    return {
        "is_valid": hmac.compare_digest(signature, expected_signature),
        "expected_signature": expected_signature
    }


from datetime import datetime
