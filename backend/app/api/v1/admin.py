"""
CelebraTech Event Management System - Admin API
Sprint 21: Admin & Moderation System
FastAPI endpoints for admin and moderation operations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.admin import (
    AdminActionResponse,
    AdminActionListResponse,
    AdminStatsResponse,
    UserSuspendRequest,
    UserDeleteRequest,
    VendorApprovalRequest,
    VendorRejectionRequest,
    VendorListResponse,
    ModerationQueueResponse,
    ModerationQueueListResponse,
    ModerationReviewRequest,
    ModerationStatsResponse,
    SystemConfigCreate,
    SystemConfigUpdate,
    SystemConfigResponse,
    DashboardStatsResponse
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin & Moderation"])


# ============================================================================
# Admin Action Log Endpoints
# ============================================================================

@router.get(
    "/actions",
    response_model=AdminActionListResponse,
    summary="Get admin actions",
    description="Get admin action log (admin only)"
)
async def get_admin_actions(
    admin_id: Optional[UUID] = Query(None, description="Filter by admin ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    days_back: int = Query(30, ge=1, le=365, description="Days to look back"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get admin action log"""
    admin_service = AdminService(db)
    actions, total = await admin_service.get_admin_actions(
        current_user,
        admin_id,
        action_type,
        target_type,
        days_back,
        page,
        page_size
    )

    return AdminActionListResponse(
        actions=[AdminActionResponse.from_orm(a) for a in actions],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.get(
    "/actions/stats",
    response_model=AdminStatsResponse,
    summary="Get admin statistics",
    description="Get admin action statistics (admin only)"
)
async def get_admin_stats(
    days_back: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get admin statistics"""
    admin_service = AdminService(db)
    stats = await admin_service.get_admin_stats(current_user, days_back)
    return stats


# ============================================================================
# User Management Endpoints
# ============================================================================

@router.post(
    "/users/{user_id}/suspend",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Suspend user",
    description="Suspend a user account (admin only)"
)
async def suspend_user(
    user_id: UUID,
    suspend_data: UserSuspendRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Suspend a user"""
    admin_service = AdminService(db)
    success = await admin_service.suspend_user(
        user_id,
        suspend_data.reason,
        current_user,
        suspend_data.duration_days,
        request
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.post(
    "/users/{user_id}/unsuspend",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unsuspend user",
    description="Unsuspend a user account (admin only)"
)
async def unsuspend_user(
    user_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Unsuspend a user"""
    admin_service = AdminService(db)
    success = await admin_service.unsuspend_user(user_id, current_user, request)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete a user account (admin only)"
)
async def delete_user(
    user_id: UUID,
    delete_data: UserDeleteRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user"""
    admin_service = AdminService(db)
    success = await admin_service.delete_user(
        user_id,
        delete_data.reason,
        current_user,
        request
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


# ============================================================================
# Vendor Management Endpoints
# ============================================================================

@router.get(
    "/vendors/pending",
    response_model=VendorListResponse,
    summary="Get pending vendors",
    description="Get vendors pending approval (admin only)"
)
async def get_pending_vendors(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get pending vendor approvals"""
    admin_service = AdminService(db)
    vendors, total = await admin_service.get_pending_vendors(
        current_user,
        page,
        page_size
    )

    return VendorListResponse(
        vendors=vendors,  # Using Vendor model directly
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.post(
    "/vendors/{vendor_id}/approve",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Approve vendor",
    description="Approve a vendor (admin only)"
)
async def approve_vendor(
    vendor_id: UUID,
    approval_data: VendorApprovalRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve a vendor"""
    admin_service = AdminService(db)
    success = await admin_service.approve_vendor(
        vendor_id,
        current_user,
        approval_data.notes,
        request
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )


@router.post(
    "/vendors/{vendor_id}/reject",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reject vendor",
    description="Reject a vendor (admin only)"
)
async def reject_vendor(
    vendor_id: UUID,
    rejection_data: VendorRejectionRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Reject a vendor"""
    admin_service = AdminService(db)
    success = await admin_service.reject_vendor(
        vendor_id,
        rejection_data.reason,
        current_user,
        request
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )


@router.post(
    "/vendors/{vendor_id}/suspend",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Suspend vendor",
    description="Suspend a vendor (admin only)"
)
async def suspend_vendor(
    vendor_id: UUID,
    suspension_data: VendorRejectionRequest,  # Reusing rejection schema
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Suspend a vendor"""
    admin_service = AdminService(db)
    success = await admin_service.suspend_vendor(
        vendor_id,
        suspension_data.reason,
        current_user,
        request
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )


# ============================================================================
# Moderation Queue Endpoints
# ============================================================================

@router.get(
    "/moderation-queue",
    response_model=ModerationQueueListResponse,
    summary="Get moderation queue",
    description="Get moderation queue items (admin only)"
)
async def get_moderation_queue(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get moderation queue"""
    admin_service = AdminService(db)
    items, total = await admin_service.get_moderation_queue(
        current_user,
        status_filter,
        content_type,
        page,
        page_size
    )

    return ModerationQueueListResponse(
        items=[ModerationQueueResponse.from_orm(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.put(
    "/moderation-queue/{item_id}",
    response_model=ModerationQueueResponse,
    summary="Review moderation item",
    description="Review a moderation queue item (admin only)"
)
async def review_moderation_item(
    item_id: UUID,
    review_data: ModerationReviewRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Review moderation item"""
    admin_service = AdminService(db)
    item = await admin_service.review_moderation_item(
        item_id,
        review_data.decision,
        current_user,
        review_data.notes,
        request
    )
    return ModerationQueueResponse.from_orm(item)


@router.get(
    "/moderation-queue/stats",
    response_model=ModerationStatsResponse,
    summary="Get moderation statistics",
    description="Get moderation queue statistics (admin only)"
)
async def get_moderation_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get moderation statistics"""
    admin_service = AdminService(db)
    stats = await admin_service.get_moderation_stats(current_user)
    return stats


# ============================================================================
# System Configuration Endpoints
# ============================================================================

@router.get(
    "/config",
    response_model=List[SystemConfigResponse],
    summary="Get system configurations",
    description="Get all system configurations (admin only)"
)
async def get_all_configs(
    category: Optional[str] = Query(None, description="Filter by category"),
    include_sensitive: bool = Query(False, description="Include sensitive configs"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all system configurations"""
    admin_service = AdminService(db)
    configs = await admin_service.get_all_configs(
        current_user,
        category,
        include_sensitive
    )
    return [SystemConfigResponse.from_orm(c) for c in configs]


@router.get(
    "/config/{config_key}",
    response_model=SystemConfigResponse,
    summary="Get system configuration",
    description="Get a specific system configuration (admin only)"
)
async def get_config(
    config_key: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get system configuration"""
    admin_service = AdminService(db)
    config = await admin_service.get_config(config_key, current_user)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    return SystemConfigResponse.from_orm(config)


@router.post(
    "/config",
    response_model=SystemConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create/update system configuration",
    description="Create or update system configuration (admin only)"
)
async def set_config(
    config_data: SystemConfigCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Set system configuration"""
    admin_service = AdminService(db)
    config = await admin_service.set_config(
        config_data.config_key,
        config_data.config_value,
        config_data.category,
        current_user,
        config_data.is_sensitive,
        request
    )
    return SystemConfigResponse.from_orm(config)


@router.put(
    "/config/{config_key}",
    response_model=SystemConfigResponse,
    summary="Update system configuration",
    description="Update a system configuration (admin only)"
)
async def update_config(
    config_key: str,
    config_data: SystemConfigUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update system configuration"""
    admin_service = AdminService(db)
    config = await admin_service.set_config(
        config_key,
        config_data.config_value,
        config_data.category,
        current_user,
        config_data.is_sensitive,
        request
    )
    return SystemConfigResponse.from_orm(config)


@router.delete(
    "/config/{config_key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete system configuration",
    description="Delete a system configuration (admin only)"
)
async def delete_config(
    config_key: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete system configuration"""
    admin_service = AdminService(db)
    success = await admin_service.delete_config(config_key, current_user, request)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )


# ============================================================================
# Dashboard Endpoints
# ============================================================================

@router.get(
    "/dashboard",
    response_model=DashboardStatsResponse,
    summary="Get dashboard statistics",
    description="Get admin dashboard statistics (admin only)"
)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get admin dashboard statistics"""
    admin_service = AdminService(db)
    stats = await admin_service.get_dashboard_stats(current_user)
    return stats
