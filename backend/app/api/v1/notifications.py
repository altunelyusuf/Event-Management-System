"""
CelebraTech Event Management System - Notification API
Sprint 8: Notification System
FR-008: Multi-channel Notification System
FastAPI endpoints for notification operations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import math

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_admin_user
from app.models.user import User
from app.services.notification_service import NotificationService
from app.schemas.notification import (
    NotificationCreate,
    NotificationBulkCreate,
    NotificationUpdate,
    NotificationResponse,
    NotificationListResponse,
    NotificationPreferenceCreate,
    NotificationPreferenceUpdate,
    NotificationPreferenceResponse,
    NotificationDeviceCreate,
    NotificationDeviceUpdate,
    NotificationDeviceResponse,
    MarkNotificationAsRead,
    MarkAllAsRead,
    NotificationStats,
    NotificationFilters,
    NotificationType,
    NotificationStatus,
    NotificationPriority
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ============================================================================
# Notification Endpoints
# ============================================================================

@router.post(
    "",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create notification",
    description="Create a notification (admin or system)"
)
async def create_notification(
    notification_data: NotificationCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a notification"""
    service = NotificationService(db)
    notification = await service.create_notification(notification_data, current_user)
    return NotificationResponse.from_orm(notification)


@router.post(
    "/bulk",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create bulk notifications",
    description="Create notifications for multiple users (admin only)"
)
async def create_bulk_notifications(
    bulk_data: NotificationBulkCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create bulk notifications"""
    service = NotificationService(db)
    result = await service.create_bulk_notifications(bulk_data, current_user)
    return result


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get notification",
    description="Get notification by ID"
)
async def get_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notification by ID"""
    service = NotificationService(db)
    notification = await service.get_notification(notification_id, current_user)
    return NotificationResponse.from_orm(notification)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark as read",
    description="Mark notification as read"
)
async def mark_notification_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark notification as read"""
    service = NotificationService(db)
    notification = await service.mark_as_read(notification_id, current_user)
    return NotificationResponse.from_orm(notification)


@router.post(
    "/read-all",
    response_model=dict,
    summary="Mark all as read",
    description="Mark all notifications as read"
)
async def mark_all_notifications_as_read(
    mark_data: MarkAllAsRead,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read"""
    service = NotificationService(db)
    result = await service.mark_all_as_read(mark_data, current_user)
    return result


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notification",
    description="Delete a notification"
)
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete notification"""
    service = NotificationService(db)
    await service.delete_notification(notification_id, current_user)
    return None


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List notifications",
    description="List user's notifications with filters"
)
async def list_notifications(
    type: Optional[str] = Query(None, description="Filter by type"),
    status: Optional[NotificationStatus] = Query(None, description="Filter by status"),
    priority: Optional[NotificationPriority] = Query(None, description="Filter by priority"),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    context_type: Optional[str] = Query(None, description="Filter by context type"),
    context_id: Optional[UUID] = Query(None, description="Filter by context ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List notifications with filtering

    Filters:
    - type: Notification type
    - status: Notification status
    - priority: Notification priority
    - is_read: Read status (true/false)
    - context_type: Context type (booking, event, etc.)
    - context_id: Context ID
    """
    service = NotificationService(db)

    filters = NotificationFilters(
        type=type,
        status=status,
        priority=priority,
        is_read=is_read,
        context_type=context_type,
        context_id=context_id
    )

    notifications, total = await service.list_notifications(
        current_user,
        filters,
        page,
        page_size
    )

    # Get unread count
    unread_count = await service.get_unread_count(current_user)

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return NotificationListResponse(
        notifications=[NotificationResponse.from_orm(n) for n in notifications],
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get(
    "/stats/me",
    response_model=NotificationStats,
    summary="Get notification statistics",
    description="Get user's notification statistics"
)
async def get_notification_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notification statistics"""
    service = NotificationService(db)
    stats = await service.get_stats(current_user)
    return NotificationStats(**stats)


@router.get(
    "/unread/count",
    response_model=dict,
    summary="Get unread count",
    description="Get unread notification count"
)
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get unread notification count"""
    service = NotificationService(db)
    count = await service.get_unread_count(current_user)
    return {"unread_count": count}


# ============================================================================
# Notification Preference Endpoints
# ============================================================================

@router.get(
    "/preferences",
    response_model=List[NotificationPreferenceResponse],
    summary="Get notification preferences",
    description="Get user's notification preferences"
)
async def get_notification_preferences(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notification preferences"""
    service = NotificationService(db)
    preferences = await service.get_preferences(current_user)
    return [NotificationPreferenceResponse.from_orm(p) for p in preferences]


@router.post(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create notification preference",
    description="Create notification preference"
)
async def create_notification_preference(
    preference_data: NotificationPreferenceCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create notification preference"""
    service = NotificationService(db)
    preference = await service.create_preference(preference_data, current_user)
    return NotificationPreferenceResponse.from_orm(preference)


@router.put(
    "/preferences/{preference_id}",
    response_model=NotificationPreferenceResponse,
    summary="Update notification preference",
    description="Update notification preference"
)
async def update_notification_preference(
    preference_id: UUID,
    preference_data: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update notification preference"""
    service = NotificationService(db)
    preference = await service.update_preference(preference_id, preference_data, current_user)
    return NotificationPreferenceResponse.from_orm(preference)


# ============================================================================
# Notification Device Endpoints
# ============================================================================

@router.get(
    "/devices",
    response_model=List[NotificationDeviceResponse],
    summary="Get notification devices",
    description="Get user's registered devices"
)
async def get_notification_devices(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notification devices"""
    service = NotificationService(db)
    devices = await service.get_devices(current_user)
    return [NotificationDeviceResponse.from_orm(d) for d in devices]


@router.post(
    "/devices",
    response_model=NotificationDeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register device",
    description="Register device for push notifications"
)
async def register_notification_device(
    device_data: NotificationDeviceCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Register device for push notifications"""
    service = NotificationService(db)
    device = await service.register_device(device_data, current_user)
    return NotificationDeviceResponse.from_orm(device)


@router.delete(
    "/devices/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate device",
    description="Deactivate a device"
)
async def deactivate_notification_device(
    device_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate device"""
    service = NotificationService(db)
    await service.deactivate_device(device_id, current_user)
    return None
