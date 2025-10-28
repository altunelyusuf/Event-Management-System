"""
Integration Hub Schemas
Sprint 20: Integration Hub

Pydantic schemas for third-party integrations including payment gateways,
calendar systems, social media, cloud storage, email services, and webhooks.
"""

from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# Integration Schemas
# ============================================================================

class IntegrationCreate(BaseModel):
    """Schema for creating an integration"""
    integration_type: str = Field(..., description="Type of integration (payment, calendar, etc.)")
    provider: str = Field(..., description="Provider name (stripe, google_calendar, etc.)")
    credentials: Dict[str, Any] = Field(..., description="Integration credentials (will be encrypted)")
    config: Optional[Dict[str, Any]] = Field(None, description="Additional configuration")


class IntegrationUpdate(BaseModel):
    """Schema for updating an integration"""
    credentials: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class IntegrationResponse(BaseModel):
    """Schema for integration response"""
    id: UUID
    user_id: UUID
    integration_type: str
    provider: str
    config: Optional[Dict[str, Any]]
    status: str
    last_sync_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntegrationCredentials(BaseModel):
    """Schema for OAuth credentials"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None


# ============================================================================
# OAuth Schemas
# ============================================================================

class OAuthAuthorizeRequest(BaseModel):
    """Schema for OAuth authorization request"""
    provider: str
    redirect_uri: Optional[str] = None
    state: Optional[str] = None
    scope: Optional[List[str]] = None


class OAuthCallbackRequest(BaseModel):
    """Schema for OAuth callback"""
    code: str
    state: Optional[str] = None


class OAuthTokenResponse(BaseModel):
    """Schema for OAuth token response"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    token_type: str = "Bearer"
    scope: Optional[str] = None


# ============================================================================
# Webhook Schemas
# ============================================================================

class WebhookCreate(BaseModel):
    """Schema for creating a webhook"""
    event_type: str = Field(..., description="Event type to subscribe to")
    url: HttpUrl = Field(..., description="Webhook endpoint URL")
    secret: Optional[str] = Field(None, description="Webhook signing secret (auto-generated if not provided)")

    @validator('url')
    def validate_url(cls, v):
        """Validate webhook URL"""
        if not str(v).startswith(('http://', 'https://')):
            raise ValueError('URL must use HTTP or HTTPS protocol')
        return v


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook"""
    url: Optional[HttpUrl] = None
    is_active: Optional[bool] = None
    secret: Optional[str] = None


class WebhookResponse(BaseModel):
    """Schema for webhook response"""
    id: UUID
    user_id: UUID
    event_type: str
    url: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliveryResponse(BaseModel):
    """Schema for webhook delivery response"""
    id: UUID
    webhook_id: UUID
    payload: Dict[str, Any]
    status_code: Optional[int]
    response_body: Optional[str]
    delivered_at: datetime

    class Config:
        from_attributes = True


class WebhookTestRequest(BaseModel):
    """Schema for testing a webhook"""
    webhook_id: UUID
    test_payload: Optional[Dict[str, Any]] = None


class WebhookEventPayload(BaseModel):
    """Schema for webhook event payload"""
    event_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# Payment Integration Schemas
# ============================================================================

class StripeConnectRequest(BaseModel):
    """Schema for Stripe Connect"""
    authorization_code: str


class PayPalConnectRequest(BaseModel):
    """Schema for PayPal Connect"""
    authorization_code: str


class PaymentProviderSync(BaseModel):
    """Schema for syncing payment provider"""
    sync_transactions: bool = True
    sync_customers: bool = False
    days_back: int = Field(30, gt=0, le=365)


# ============================================================================
# Calendar Integration Schemas
# ============================================================================

class CalendarSyncRequest(BaseModel):
    """Schema for calendar sync request"""
    calendar_id: Optional[str] = None
    sync_direction: str = Field("bidirectional", regex="^(to_provider|from_provider|bidirectional)$")


class CalendarEvent(BaseModel):
    """Schema for calendar event"""
    event_id: UUID
    external_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: Optional[List[str]] = None


class CalendarSyncResponse(BaseModel):
    """Schema for calendar sync response"""
    provider: str
    events_synced: int
    events_created: int
    events_updated: int
    events_deleted: int
    last_sync_at: datetime


# ============================================================================
# Email Integration Schemas
# ============================================================================

class EmailProviderConnect(BaseModel):
    """Schema for email provider connection"""
    provider: str = Field(..., regex="^(sendgrid|mailchimp|aws_ses)$")
    api_key: str
    config: Optional[Dict[str, Any]] = None


class EmailCampaignCreate(BaseModel):
    """Schema for creating email campaign"""
    campaign_name: str
    subject: str
    from_email: str
    from_name: Optional[str] = None
    recipient_list_id: Optional[str] = None
    html_content: str
    text_content: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class EmailSendRequest(BaseModel):
    """Schema for sending email"""
    to_email: str
    subject: str
    html_content: str
    text_content: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None


# ============================================================================
# SMS Integration Schemas
# ============================================================================

class SMSProviderConnect(BaseModel):
    """Schema for SMS provider connection"""
    provider: str = Field(..., regex="^(twilio|nexmo)$")
    account_sid: str
    auth_token: str
    phone_number: Optional[str] = None


class SMSSendRequest(BaseModel):
    """Schema for sending SMS"""
    to_phone: str = Field(..., regex="^\+[1-9]\d{1,14}$")
    message: str = Field(..., max_length=1600)
    from_phone: Optional[str] = None


class SMSResponse(BaseModel):
    """Schema for SMS response"""
    message_id: str
    status: str
    to_phone: str
    segments: int
    cost: Optional[float] = None


# ============================================================================
# Cloud Storage Integration Schemas
# ============================================================================

class CloudStorageConnect(BaseModel):
    """Schema for cloud storage connection"""
    provider: str = Field(..., regex="^(dropbox|google_drive|onedrive)$")
    credentials: Dict[str, Any]


class FileUploadRequest(BaseModel):
    """Schema for file upload to cloud storage"""
    file_path: str
    file_name: str
    folder_path: Optional[str] = "/"
    make_public: bool = False


class FileUploadResponse(BaseModel):
    """Schema for file upload response"""
    file_id: str
    file_name: str
    file_url: str
    provider: str
    size_bytes: int
    uploaded_at: datetime


# ============================================================================
# Social Media Integration Schemas
# ============================================================================

class SocialMediaConnect(BaseModel):
    """Schema for social media connection"""
    provider: str = Field(..., regex="^(facebook|instagram|twitter|linkedin)$")
    credentials: Dict[str, Any]


class SocialPostCreate(BaseModel):
    """Schema for creating social media post"""
    platforms: List[str]
    message: str = Field(..., max_length=5000)
    image_urls: Optional[List[str]] = None
    scheduled_at: Optional[datetime] = None


class SocialPostResponse(BaseModel):
    """Schema for social post response"""
    post_id: str
    platform: str
    status: str
    url: Optional[str] = None
    posted_at: datetime


# ============================================================================
# Integration Health & Status Schemas
# ============================================================================

class IntegrationHealth(BaseModel):
    """Schema for integration health check"""
    integration_id: UUID
    provider: str
    status: str
    is_healthy: bool
    last_checked_at: datetime
    error_message: Optional[str] = None


class IntegrationTestRequest(BaseModel):
    """Schema for testing an integration"""
    integration_id: UUID
    test_type: str = Field("connection", regex="^(connection|api_call|webhook)$")


class IntegrationTestResponse(BaseModel):
    """Schema for integration test response"""
    integration_id: UUID
    test_type: str
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    tested_at: datetime


# ============================================================================
# Integration Marketplace Schemas
# ============================================================================

class IntegrationTemplate(BaseModel):
    """Schema for integration template"""
    name: str
    provider: str
    integration_type: str
    description: str
    logo_url: Optional[str] = None
    features: List[str]
    required_credentials: List[str]
    setup_steps: List[str]
    is_popular: bool = False
    is_recommended: bool = False


class IntegrationMarketplace(BaseModel):
    """Schema for integration marketplace"""
    available_integrations: List[IntegrationTemplate]
    installed_integrations: List[IntegrationResponse]
    recommended_integrations: List[IntegrationTemplate]


# ============================================================================
# Bulk Operations Schemas
# ============================================================================

class BulkWebhookCreate(BaseModel):
    """Schema for bulk webhook creation"""
    webhooks: List[WebhookCreate]


class BulkIntegrationSync(BaseModel):
    """Schema for bulk integration sync"""
    integration_ids: List[UUID]
    sync_type: str = "full"


# ============================================================================
# Analytics Schemas
# ============================================================================

class IntegrationUsageStats(BaseModel):
    """Schema for integration usage statistics"""
    integration_id: UUID
    provider: str
    api_calls_count: int
    success_rate: float
    average_response_time_ms: float
    last_used_at: Optional[datetime]


class WebhookDeliveryStats(BaseModel):
    """Schema for webhook delivery statistics"""
    webhook_id: UUID
    event_type: str
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    success_rate: float
    average_response_time_ms: float
