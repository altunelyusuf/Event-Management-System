"""
CelebraTech Event Management System - Notification Schemas
Sprint 8: Notification System
FR-008: Multi-channel Notification System
Pydantic schemas for notification data validation
"""
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from app.models.notification import (
    NotificationType,
    NotificationPriority,
    NotificationStatus,
    NotificationChannel,
    DeliveryStatus
)


# ============================================================================
# Notification Schemas
# ============================================================================

class NotificationBase(BaseModel):
    """Base notification fields"""
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=5000)
    data: Dict[str, Any] = Field(default_factory=dict)
    action_url: Optional[str] = Field(None, max_length=500)
    action_text: Optional[str] = Field(None, max_length=100)


class NotificationCreate(NotificationBase):
    """Schema for creating a notification"""
    user_id: UUID
    type: NotificationType
    priority: NotificationPriority = Field(NotificationPriority.NORMAL)
    channels: List[NotificationChannel] = Field(default_factory=lambda: [NotificationChannel.IN_APP])
    context_type: Optional[str] = Field(None, max_length=50)
    context_id: Optional[UUID] = None
    actor_id: Optional[UUID] = None
    group_key: Optional[str] = Field(None, max_length=100)
    expires_at: Optional[datetime] = None

    @validator('channels')
    def validate_channels(cls, v):
        """Ensure at least one channel"""
        if not v or len(v) == 0:
            raise ValueError('At least one notification channel required')
        return v


class NotificationBulkCreate(BaseModel):
    """Schema for creating notifications for multiple users"""
    user_ids: List[UUID] = Field(..., min_items=1, max_items=1000)
    type: NotificationType
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=5000)
    priority: NotificationPriority = Field(NotificationPriority.NORMAL)
    channels: List[NotificationChannel] = Field(default_factory=lambda: [NotificationChannel.IN_APP])
    data: Dict[str, Any] = Field(default_factory=dict)
    action_url: Optional[str] = None
    context_type: Optional[str] = None
    context_id: Optional[UUID] = None


class NotificationUpdate(BaseModel):
    """Schema for updating notification (admin)"""
    status: Optional[NotificationStatus] = None
    expires_at: Optional[datetime] = None


class NotificationResponse(BaseModel):
    """Response schema for notification"""
    id: UUID
    user_id: UUID
    type: str
    priority: str
    status: str
    title: str
    message: str
    data: Dict[str, Any]
    action_url: Optional[str]
    action_text: Optional[str]
    context_type: Optional[str]
    context_id: Optional[UUID]
    actor_id: Optional[UUID]
    channels: List[str]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    read_at: Optional[datetime]
    expires_at: Optional[datetime]
    group_key: Optional[str]
    created_at: datetime

    # Actor info (loaded separately)
    actor_name: Optional[str] = None
    actor_avatar: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationSummary(BaseModel):
    """Summary schema for notification list"""
    id: UUID
    type: str
    title: str
    message: str
    status: str
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Notification Preference Schemas
# ============================================================================

class NotificationPreferenceBase(BaseModel):
    """Base notification preference fields"""
    in_app_enabled: bool = Field(True)
    email_enabled: bool = Field(True)
    push_enabled: bool = Field(True)
    sms_enabled: bool = Field(False)
    frequency: str = Field("immediate")
    quiet_hours_enabled: bool = Field(False)
    quiet_hours_start: Optional[str] = Field(None, regex=r'^([01]\d|2[0-3]):([0-5]\d)$')
    quiet_hours_end: Optional[str] = Field(None, regex=r'^([01]\d|2[0-3]):([0-5]\d)$')


class NotificationPreferenceCreate(NotificationPreferenceBase):
    """Schema for creating notification preference"""
    notification_type: str = Field(..., max_length=50)

    @root_validator
    def validate_quiet_hours(cls, values):
        """Validate quiet hours consistency"""
        enabled = values.get('quiet_hours_enabled')
        start = values.get('quiet_hours_start')
        end = values.get('quiet_hours_end')

        if enabled and (not start or not end):
            raise ValueError('Quiet hours start and end times required when enabled')

        return values


class NotificationPreferenceUpdate(NotificationPreferenceBase):
    """Schema for updating notification preference"""
    in_app_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    frequency: Optional[str] = None
    quiet_hours_enabled: Optional[bool] = None


class NotificationPreferenceResponse(BaseModel):
    """Response schema for notification preference"""
    id: UUID
    user_id: UUID
    notification_type: str
    in_app_enabled: bool
    email_enabled: bool
    push_enabled: bool
    sms_enabled: bool
    frequency: str
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[str]
    quiet_hours_end: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Notification Device Schemas
# ============================================================================

class NotificationDeviceCreate(BaseModel):
    """Schema for registering a device"""
    device_token: str = Field(..., max_length=500)
    device_type: str = Field(..., max_length=20)
    device_name: Optional[str] = Field(None, max_length=200)
    platform: str = Field(..., max_length=20)
    app_version: Optional[str] = Field(None, max_length=50)
    os_version: Optional[str] = Field(None, max_length=50)

    @validator('device_type')
    def validate_device_type(cls, v):
        """Validate device type"""
        allowed = ['ios', 'android', 'web']
        if v not in allowed:
            raise ValueError(f'Device type must be one of: {", ".join(allowed)}')
        return v

    @validator('platform')
    def validate_platform(cls, v):
        """Validate platform"""
        allowed = ['fcm', 'apns']
        if v not in allowed:
            raise ValueError(f'Platform must be one of: {", ".join(allowed)}')
        return v


class NotificationDeviceUpdate(BaseModel):
    """Schema for updating a device"""
    device_name: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class NotificationDeviceResponse(BaseModel):
    """Response schema for notification device"""
    id: UUID
    user_id: UUID
    device_token: str
    device_type: str
    device_name: Optional[str]
    platform: str
    app_version: Optional[str]
    os_version: Optional[str]
    is_active: bool
    last_used_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Notification Template Schemas
# ============================================================================

class NotificationTemplateCreate(BaseModel):
    """Schema for creating notification template (admin)"""
    notification_type: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    in_app_title: Optional[str] = Field(None, max_length=200)
    in_app_message: Optional[str] = None
    email_subject: Optional[str] = Field(None, max_length=200)
    email_body_html: Optional[str] = None
    email_body_text: Optional[str] = None
    push_title: Optional[str] = Field(None, max_length=100)
    push_body: Optional[str] = Field(None, max_length=200)
    sms_message: Optional[str] = Field(None, max_length=160)
    variables: Dict[str, Any] = Field(default_factory=dict)
    default_channels: List[str] = Field(default_factory=list)
    default_priority: str = Field("normal")


class NotificationTemplateUpdate(BaseModel):
    """Schema for updating notification template (admin)"""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    in_app_title: Optional[str] = None
    in_app_message: Optional[str] = None
    email_subject: Optional[str] = None
    email_body_html: Optional[str] = None
    email_body_text: Optional[str] = None
    push_title: Optional[str] = None
    push_body: Optional[str] = None
    sms_message: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    default_channels: Optional[List[str]] = None
    default_priority: Optional[str] = None
    is_active: Optional[bool] = None


class NotificationTemplateResponse(BaseModel):
    """Response schema for notification template"""
    id: UUID
    notification_type: str
    name: str
    description: Optional[str]
    in_app_title: Optional[str]
    in_app_message: Optional[str]
    email_subject: Optional[str]
    email_body_html: Optional[str]
    email_body_text: Optional[str]
    push_title: Optional[str]
    push_body: Optional[str]
    sms_message: Optional[str]
    variables: Dict[str, Any]
    default_channels: List[str]
    default_priority: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Notification Batch Schemas
# ============================================================================

class NotificationBatchCreate(BaseModel):
    """Schema for creating notification batch (admin)"""
    name: str = Field(..., max_length=200)
    notification_type: str = Field(..., max_length=50)
    target_users: Optional[List[UUID]] = Field(None, max_items=10000)
    target_criteria: Optional[Dict[str, Any]] = None
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=5000)
    data: Dict[str, Any] = Field(default_factory=dict)
    channels: List[str] = Field(default_factory=list)
    scheduled_at: Optional[datetime] = None

    @root_validator
    def validate_targets(cls, values):
        """Ensure either target_users or target_criteria provided"""
        users = values.get('target_users')
        criteria = values.get('target_criteria')

        if not users and not criteria:
            raise ValueError('Either target_users or target_criteria must be provided')

        return values


class NotificationBatchResponse(BaseModel):
    """Response schema for notification batch"""
    id: UUID
    name: str
    notification_type: str
    status: str
    total_count: int
    sent_count: int
    failed_count: int
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Mark as Read Schemas
# ============================================================================

class MarkNotificationAsRead(BaseModel):
    """Schema for marking notification as read"""
    notification_id: UUID


class MarkAllAsRead(BaseModel):
    """Schema for marking all notifications as read"""
    before_date: Optional[datetime] = None


# ============================================================================
# Notification Statistics Schemas
# ============================================================================

class NotificationStats(BaseModel):
    """Notification statistics"""
    total_notifications: int
    unread_count: int
    read_count: int
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_priority: Dict[str, int] = Field(default_factory=dict)


class NotificationDeliveryStats(BaseModel):
    """Delivery statistics"""
    total_deliveries: int
    by_channel: Dict[str, int]
    by_status: Dict[str, int]
    success_rate: float


# ============================================================================
# Filter and Query Schemas
# ============================================================================

class NotificationFilters(BaseModel):
    """Filters for notification queries"""
    type: Optional[str] = None
    status: Optional[NotificationStatus] = None
    priority: Optional[NotificationPriority] = None
    is_read: Optional[bool] = None
    context_type: Optional[str] = None
    context_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @root_validator
    def validate_date_range(cls, values):
        """Ensure start_date <= end_date"""
        start = values.get('start_date')
        end = values.get('end_date')
        if start and end and start > end:
            raise ValueError('start_date cannot be after end_date')
        return values


# ============================================================================
# Pagination Schemas
# ============================================================================

class NotificationListResponse(BaseModel):
    """Paginated list of notifications"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# ============================================================================
# Test Notification Schemas
# ============================================================================

class TestNotificationCreate(BaseModel):
    """Schema for sending test notification (admin)"""
    user_id: UUID
    channel: NotificationChannel
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=5000)
