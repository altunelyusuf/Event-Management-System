"""
CelebraTech Event Management System - Review API
Sprint 6: Review and Rating System
FR-006: Review and Rating Management
FastAPI endpoints for review operations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import math

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_admin_user
from app.models.user import User
from app.services.review_service import ReviewService
from app.schemas.review import (
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse as ReviewResponseSchema,
    ReviewSummary,
    ReviewListResponse,
    ReviewSummaryListResponse,
    ReviewResponseCreate,
    ReviewResponseUpdate,
    ReviewResponseResponse,
    ReviewHelpfulnessCreate,
    ReviewHelpfulnessResponse,
    ReviewReportCreate,
    ReviewReportUpdate,
    ReviewReportResponse,
    VendorRatingStats,
    ReviewModerationUpdate,
    ReviewBulkAction,
    ReviewFilters,
    ReviewStatus
)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


# ============================================================================
# Review Endpoints
# ============================================================================

@router.post(
    "",
    response_model=ReviewResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create review",
    description="Create a review for a completed booking"
)
async def create_review(
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a review for a completed booking

    Business rules:
    - Must have completed booking
    - One review per booking
    - Event must have occurred
    - Only event organizer can review
    """
    service = ReviewService(db)
    review = await service.create_review(review_data, current_user)
    return ReviewResponseSchema.from_orm(review)


@router.get(
    "/{review_id}",
    response_model=ReviewResponseSchema,
    summary="Get review",
    description="Get review by ID"
)
async def get_review(
    review_id: UUID,
    current_user: Optional[User] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get review by ID"""
    service = ReviewService(db)
    review = await service.get_review(review_id, current_user)
    return ReviewResponseSchema.from_orm(review)


@router.put(
    "/{review_id}",
    response_model=ReviewResponseSchema,
    summary="Update review",
    description="Update a review"
)
async def update_review(
    review_id: UUID,
    review_data: ReviewUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a review

    Business rules:
    - Only reviewer can update
    - Cannot update after vendor response
    - Can update within 30 days
    """
    service = ReviewService(db)
    review = await service.update_review(review_id, review_data, current_user)
    return ReviewResponseSchema.from_orm(review)


@router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete review",
    description="Delete a review"
)
async def delete_review(
    review_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a review

    Business rules:
    - Only reviewer or admin can delete
    - Cannot delete after vendor response (unless admin)
    """
    service = ReviewService(db)
    await service.delete_review(review_id, current_user)
    return None


@router.get(
    "",
    response_model=ReviewListResponse,
    summary="List reviews",
    description="List reviews with filters and pagination"
)
async def list_reviews(
    vendor_id: Optional[UUID] = Query(None, description="Filter by vendor"),
    reviewer_id: Optional[UUID] = Query(None, description="Filter by reviewer"),
    min_rating: Optional[int] = Query(None, ge=1, le=5, description="Minimum rating"),
    max_rating: Optional[int] = Query(None, ge=1, le=5, description="Maximum rating"),
    status: Optional[ReviewStatus] = Query(None, description="Filter by status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification"),
    has_response: Optional[bool] = Query(None, description="Filter by response"),
    is_featured: Optional[bool] = Query(None, description="Filter by featured"),
    sort_by: str = Query("recent", description="Sort: recent, rating_high, rating_low, helpful, oldest"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """
    List reviews with comprehensive filtering

    Sort options:
    - recent: Most recent first
    - rating_high: Highest rating first
    - rating_low: Lowest rating first
    - helpful: Most helpful first
    - oldest: Oldest first
    """
    service = ReviewService(db)

    filters = ReviewFilters(
        vendor_id=vendor_id,
        reviewer_id=reviewer_id,
        min_rating=min_rating,
        max_rating=max_rating,
        status=status,
        is_verified=is_verified,
        has_response=has_response,
        is_featured=is_featured
    )

    reviews, total = await service.list_reviews(filters, sort_by, page, page_size)

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return ReviewListResponse(
        reviews=[ReviewResponseSchema.from_orm(r) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


# ============================================================================
# Vendor Review Endpoints
# ============================================================================

@router.get(
    "/vendor/{vendor_id}",
    response_model=ReviewListResponse,
    summary="Get vendor reviews",
    description="Get all reviews for a vendor"
)
async def get_vendor_reviews(
    vendor_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get all reviews for a vendor"""
    service = ReviewService(db)
    reviews, total = await service.get_vendor_reviews(vendor_id, page, page_size)

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return ReviewListResponse(
        reviews=[ReviewResponseSchema.from_orm(r) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


@router.get(
    "/vendor/{vendor_id}/stats",
    response_model=VendorRatingStats,
    summary="Get vendor rating statistics",
    description="Get comprehensive rating statistics for a vendor"
)
async def get_vendor_rating_stats(
    vendor_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get vendor rating statistics

    Includes:
    - Total reviews and average rating
    - Rating distribution (1-5 stars)
    - Category averages
    - Response rate
    - Recent activity
    """
    service = ReviewService(db)
    stats = await service.get_vendor_rating_stats(vendor_id)
    return VendorRatingStats.from_orm(stats)


# ============================================================================
# User Review Endpoints
# ============================================================================

@router.get(
    "/user/{user_id}",
    response_model=ReviewListResponse,
    summary="Get user reviews",
    description="Get all reviews written by a user"
)
async def get_user_reviews(
    user_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all reviews by a user"""
    # Users can only view their own reviews unless admin
    if str(user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view own reviews"
        )

    service = ReviewService(db)
    reviews, total = await service.get_user_reviews(user_id, page, page_size)

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return ReviewListResponse(
        reviews=[ReviewResponseSchema.from_orm(r) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


# ============================================================================
# Review Response Endpoints
# ============================================================================

@router.post(
    "/{review_id}/response",
    response_model=ReviewResponseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create vendor response",
    description="Create a vendor response to a review"
)
async def create_review_response(
    review_id: UUID,
    response_data: ReviewResponseCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create vendor response to review

    Business rules:
    - Only vendor can respond
    - One response per review
    - Can only respond to approved reviews
    """
    service = ReviewService(db)
    response = await service.create_review_response(review_id, response_data, current_user)
    return ReviewResponseResponse.from_orm(response)


@router.put(
    "/responses/{response_id}",
    response_model=ReviewResponseResponse,
    summary="Update vendor response",
    description="Update a vendor response"
)
async def update_review_response(
    response_id: UUID,
    response_data: ReviewResponseUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update vendor response

    Business rules:
    - Only responder can update
    - Can update within 7 days
    """
    service = ReviewService(db)
    response = await service.update_review_response(response_id, response_data, current_user)
    return ReviewResponseResponse.from_orm(response)


@router.delete(
    "/responses/{response_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete vendor response",
    description="Delete a vendor response"
)
async def delete_review_response(
    response_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete vendor response"""
    service = ReviewService(db)
    await service.delete_review_response(response_id, current_user)
    return None


# ============================================================================
# Review Helpfulness Endpoints
# ============================================================================

@router.post(
    "/{review_id}/vote",
    response_model=ReviewHelpfulnessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Vote on review helpfulness",
    description="Mark review as helpful or not helpful"
)
async def vote_review_helpfulness(
    review_id: UUID,
    vote_data: ReviewHelpfulnessCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Vote on review helpfulness

    Business rules:
    - One vote per user per review
    - Cannot vote on own review
    - Can change vote
    """
    service = ReviewService(db)
    vote = await service.vote_helpfulness(review_id, vote_data, current_user)
    return ReviewHelpfulnessResponse.from_orm(vote)


@router.get(
    "/{review_id}/vote/me",
    response_model=Optional[ReviewHelpfulnessResponse],
    summary="Get my vote",
    description="Get current user's vote for a review"
)
async def get_my_vote(
    review_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's vote for a review"""
    service = ReviewService(db)
    vote = await service.get_user_vote(review_id, current_user)
    if vote:
        return ReviewHelpfulnessResponse.from_orm(vote)
    return None


# ============================================================================
# Review Report Endpoints
# ============================================================================

@router.post(
    "/{review_id}/report",
    response_model=ReviewReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report review",
    description="Report a review for violating guidelines"
)
async def report_review(
    review_id: UUID,
    report_data: ReviewReportCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Report a review

    Reasons:
    - inappropriate: Offensive content
    - spam: Spam or promotional
    - fake: Suspected fake review
    - off_topic: Not relevant
    - personal_info: Contains personal information
    - other: Other reason (requires description)
    """
    service = ReviewService(db)
    report = await service.report_review(review_id, report_data, current_user)
    return ReviewReportResponse.from_orm(report)


@router.get(
    "/reports",
    response_model=List[ReviewReportResponse],
    summary="List review reports",
    description="List review reports (admin only)"
)
async def list_review_reports(
    review_id: Optional[UUID] = Query(None, description="Filter by review"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List review reports (admin only)"""
    service = ReviewService(db)
    reports, total = await service.get_review_reports(
        review_id, status, page, page_size, current_user
    )
    return [ReviewReportResponse.from_orm(r) for r in reports]


@router.put(
    "/reports/{report_id}",
    response_model=ReviewReportResponse,
    summary="Update review report",
    description="Update review report investigation (admin only)"
)
async def update_review_report(
    report_id: UUID,
    report_data: ReviewReportUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update review report (admin only)"""
    service = ReviewService(db)
    report = await service.update_review_report(report_id, report_data, current_user)
    return ReviewReportResponse.from_orm(report)


# ============================================================================
# Moderation Endpoints (Admin)
# ============================================================================

@router.put(
    "/{review_id}/moderate",
    response_model=ReviewResponseSchema,
    summary="Moderate review",
    description="Moderate a review (admin only)"
)
async def moderate_review(
    review_id: UUID,
    moderation_data: ReviewModerationUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Moderate a review (admin only)

    Actions:
    - Approve review
    - Reject review
    - Flag for review
    - Hide review
    - Mark as featured
    """
    service = ReviewService(db)
    review = await service.moderate_review(review_id, moderation_data, current_user)
    return ReviewResponseSchema.from_orm(review)


@router.post(
    "/moderate/bulk",
    response_model=dict,
    summary="Bulk moderate reviews",
    description="Moderate multiple reviews at once (admin only)"
)
async def bulk_moderate_reviews(
    bulk_action: ReviewBulkAction,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk moderate reviews (admin only)

    Actions:
    - approve: Approve all reviews
    - reject: Reject all reviews
    - flag: Flag all reviews
    - hide: Hide all reviews
    """
    service = ReviewService(db)
    result = await service.bulk_moderate_reviews(bulk_action, current_user)
    return result


# ============================================================================
# Featured Reviews Endpoint
# ============================================================================

@router.get(
    "/featured",
    response_model=List[ReviewResponseSchema],
    summary="Get featured reviews",
    description="Get featured reviews across all vendors"
)
async def get_featured_reviews(
    vendor_id: Optional[UUID] = Query(None, description="Filter by vendor"),
    limit: int = Query(10, ge=1, le=50, description="Number of reviews"),
    db: AsyncSession = Depends(get_db)
):
    """Get featured reviews"""
    from app.repositories.review_repository import ReviewRepository
    repo = ReviewRepository(db)
    reviews = await repo.get_featured_reviews(vendor_id, limit)
    return [ReviewResponseSchema.from_orm(r) for r in reviews]
