"""
CelebraTech Event Management System - Review Schemas
Sprint 6: Review and Rating System
FR-006: Review and Rating Management
Pydantic schemas for review data validation
"""
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.review import (
    ReviewStatus,
    ReviewReportReason,
    ReportStatus
)


# ============================================================================
# Review Schemas
# ============================================================================

class ReviewBase(BaseModel):
    """Base review fields"""
    overall_rating: int = Field(..., ge=1, le=5, description="Overall rating (1-5 stars)")
    quality_rating: Optional[int] = Field(None, ge=1, le=5)
    professionalism_rating: Optional[int] = Field(None, ge=1, le=5)
    value_rating: Optional[int] = Field(None, ge=1, le=5)
    communication_rating: Optional[int] = Field(None, ge=1, le=5)
    timeliness_rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = Field(None, max_length=5000)
    photos: List[str] = Field(default_factory=list, max_items=10)
    pros: List[str] = Field(default_factory=list, max_items=5)
    cons: List[str] = Field(default_factory=list, max_items=5)


class ReviewCreate(ReviewBase):
    """Schema for creating a review"""
    booking_id: UUID

    @validator('comment')
    def validate_comment(cls, v, values):
        """Ensure review has either comment or ratings"""
        if not v and 'overall_rating' not in values:
            raise ValueError('Review must have at least overall rating')
        if v and len(v.strip()) < 10:
            raise ValueError('Comment must be at least 10 characters')
        return v

    @validator('photos')
    def validate_photos(cls, v):
        """Validate photo URLs"""
        for url in v:
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f'Invalid photo URL: {url}')
        return v

    @validator('pros', 'cons')
    def validate_lists(cls, v):
        """Validate pros/cons lists"""
        for item in v:
            if len(item.strip()) == 0:
                raise ValueError('Empty items not allowed')
            if len(item) > 200:
                raise ValueError('Items must be 200 characters or less')
        return v


class ReviewUpdate(BaseModel):
    """Schema for updating a review"""
    overall_rating: Optional[int] = Field(None, ge=1, le=5)
    quality_rating: Optional[int] = Field(None, ge=1, le=5)
    professionalism_rating: Optional[int] = Field(None, ge=1, le=5)
    value_rating: Optional[int] = Field(None, ge=1, le=5)
    communication_rating: Optional[int] = Field(None, ge=1, le=5)
    timeliness_rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = Field(None, max_length=5000)
    photos: Optional[List[str]] = Field(None, max_items=10)
    pros: Optional[List[str]] = Field(None, max_items=5)
    cons: Optional[List[str]] = Field(None, max_items=5)


class ReviewResponse(ReviewBase):
    """Response schema for review"""
    id: UUID
    booking_id: UUID
    vendor_id: UUID
    reviewer_id: UUID
    event_id: UUID
    status: str
    is_verified: bool
    event_date: datetime
    helpful_count: int
    not_helpful_count: int
    report_count: int
    has_response: bool
    is_featured: bool
    is_public: bool
    created_at: datetime
    updated_at: Optional[datetime]

    # Optional related data (loaded separately)
    reviewer_name: Optional[str] = None
    vendor_name: Optional[str] = None
    response: Optional['ReviewResponseResponse'] = None

    class Config:
        from_attributes = True


class ReviewSummary(BaseModel):
    """Summary schema for review (list view)"""
    id: UUID
    overall_rating: int
    title: Optional[str]
    comment: Optional[str]
    reviewer_name: str
    is_verified: bool
    event_date: datetime
    helpful_count: int
    has_response: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Review Response Schemas
# ============================================================================

class ReviewResponseCreate(BaseModel):
    """Schema for creating vendor response"""
    response_text: str = Field(..., min_length=10, max_length=2000)

    @validator('response_text')
    def validate_response(cls, v):
        """Validate response text"""
        if not v or len(v.strip()) < 10:
            raise ValueError('Response must be at least 10 characters')
        return v.strip()


class ReviewResponseUpdate(BaseModel):
    """Schema for updating vendor response"""
    response_text: str = Field(..., min_length=10, max_length=2000)


class ReviewResponseResponse(BaseModel):
    """Response schema for vendor response"""
    id: UUID
    review_id: UUID
    vendor_id: UUID
    responder_id: UUID
    response_text: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

    # Optional related data
    responder_name: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# Review Helpfulness Schemas
# ============================================================================

class ReviewHelpfulnessCreate(BaseModel):
    """Schema for voting on review helpfulness"""
    is_helpful: bool = Field(..., description="True if helpful, False if not helpful")


class ReviewHelpfulnessResponse(BaseModel):
    """Response schema for helpfulness vote"""
    id: UUID
    review_id: UUID
    user_id: UUID
    is_helpful: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Review Report Schemas
# ============================================================================

class ReviewReportCreate(BaseModel):
    """Schema for reporting a review"""
    reason: ReviewReportReason
    description: Optional[str] = Field(None, max_length=1000)

    @validator('description')
    def validate_description(cls, v, values):
        """Require description for 'other' reason"""
        if values.get('reason') == ReviewReportReason.OTHER and not v:
            raise ValueError('Description required when reason is "other"')
        return v


class ReviewReportUpdate(BaseModel):
    """Schema for updating report (admin only)"""
    status: ReportStatus
    investigation_notes: Optional[str] = None
    resolution: Optional[str] = None


class ReviewReportResponse(BaseModel):
    """Response schema for review report"""
    id: UUID
    review_id: UUID
    reporter_id: UUID
    reason: str
    description: Optional[str]
    status: str
    investigated_by: Optional[UUID]
    investigation_notes: Optional[str]
    resolution: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Rating Statistics Schemas
# ============================================================================

class VendorRatingStats(BaseModel):
    """Vendor rating statistics"""
    vendor_id: UUID
    total_reviews: int
    average_rating: Decimal
    one_star_count: int
    two_star_count: int
    three_star_count: int
    four_star_count: int
    five_star_count: int
    avg_quality_rating: Optional[Decimal]
    avg_professionalism_rating: Optional[Decimal]
    avg_value_rating: Optional[Decimal]
    avg_communication_rating: Optional[Decimal]
    avg_timeliness_rating: Optional[Decimal]
    total_helpful_votes: int
    response_rate: Decimal
    avg_response_time_hours: Optional[Decimal]
    recent_reviews_30d: int
    recent_average_30d: Optional[Decimal]
    last_calculated_at: datetime

    class Config:
        from_attributes = True


class ReviewDistribution(BaseModel):
    """Rating distribution breakdown"""
    five_stars: int = Field(..., description="Number of 5-star reviews")
    four_stars: int
    three_stars: int
    two_stars: int
    one_star: int
    total_reviews: int
    average_rating: Decimal


class CategoryRatings(BaseModel):
    """Category-specific rating averages"""
    quality: Optional[Decimal] = None
    professionalism: Optional[Decimal] = None
    value: Optional[Decimal] = None
    communication: Optional[Decimal] = None
    timeliness: Optional[Decimal] = None


# ============================================================================
# Filter and Query Schemas
# ============================================================================

class ReviewFilters(BaseModel):
    """Filters for review queries"""
    vendor_id: Optional[UUID] = None
    reviewer_id: Optional[UUID] = None
    min_rating: Optional[int] = Field(None, ge=1, le=5)
    max_rating: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[ReviewStatus] = None
    is_verified: Optional[bool] = None
    has_response: Optional[bool] = None
    is_featured: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @root_validator
    def validate_rating_range(cls, values):
        """Ensure min_rating <= max_rating"""
        min_r = values.get('min_rating')
        max_r = values.get('max_rating')
        if min_r and max_r and min_r > max_r:
            raise ValueError('min_rating cannot be greater than max_rating')
        return values

    @root_validator
    def validate_date_range(cls, values):
        """Ensure start_date <= end_date"""
        start = values.get('start_date')
        end = values.get('end_date')
        if start and end and start > end:
            raise ValueError('start_date cannot be after end_date')
        return values


class ReviewSortBy(str):
    """Sort options for reviews"""
    RECENT = "recent"  # Most recent first
    RATING_HIGH = "rating_high"  # Highest rating first
    RATING_LOW = "rating_low"  # Lowest rating first
    HELPFUL = "helpful"  # Most helpful first
    OLDEST = "oldest"  # Oldest first


# ============================================================================
# Pagination Schemas
# ============================================================================

class ReviewListResponse(BaseModel):
    """Paginated list of reviews"""
    reviews: List[ReviewResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ReviewSummaryListResponse(BaseModel):
    """Paginated list of review summaries"""
    reviews: List[ReviewSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# ============================================================================
# Moderation Schemas (Admin)
# ============================================================================

class ReviewModerationUpdate(BaseModel):
    """Schema for moderating a review (admin only)"""
    status: ReviewStatus
    moderation_notes: Optional[str] = Field(None, max_length=1000)
    is_featured: Optional[bool] = None


class ReviewBulkAction(BaseModel):
    """Schema for bulk review actions (admin only)"""
    review_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    action: str = Field(..., description="Action to perform: approve, reject, flag, hide")
    notes: Optional[str] = None

    @validator('action')
    def validate_action(cls, v):
        """Validate action"""
        allowed = ['approve', 'reject', 'flag', 'hide']
        if v not in allowed:
            raise ValueError(f'Action must be one of: {", ".join(allowed)}')
        return v


# Update forward references
ReviewResponse.model_rebuild()
