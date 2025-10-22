"""
CelebraTech Event Management System - Vendor Schemas
Sprint 3: Vendor Profile Foundation
FR-003: Vendor Marketplace & Discovery
Pydantic schemas for vendor data validation
"""
from pydantic import BaseModel, Field, EmailStr, HttpUrl, validator, root_validator
from typing import Optional, List
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID

from app.models.vendor import (
    VendorCategory,
    VendorStatus,
    BusinessType,
    SubscriptionTier,
    PriceUnit,
    MediaType,
    AvailabilityStatus
)


# ============================================================================
# Base Schemas
# ============================================================================

class VendorBase(BaseModel):
    """Base vendor schema with common fields"""
    business_name: str = Field(..., min_length=2, max_length=255)
    business_type: Optional[BusinessType] = None
    category: VendorCategory
    description: str = Field(..., min_length=10)
    short_description: Optional[str] = Field(None, max_length=500)

    # Contact Information
    website_url: Optional[HttpUrl] = None
    phone: str = Field(..., min_length=10, max_length=20)
    email: EmailStr

    # Location
    location_city: str = Field(..., min_length=2, max_length=100)
    location_district: Optional[str] = Field(None, max_length=100)
    location_address: Optional[str] = None
    location_lat: Optional[Decimal] = Field(None, ge=-90, le=90)
    location_lng: Optional[Decimal] = Field(None, ge=-180, le=180)
    service_radius_km: int = Field(50, ge=0, le=500)

    # Sustainability
    eco_certified: bool = False
    eco_score: Optional[Decimal] = Field(None, ge=0, le=100)


class VendorServiceBase(BaseModel):
    """Base vendor service schema"""
    service_name: str = Field(..., min_length=2, max_length=255)
    service_category: str = Field(..., max_length=100)
    description: Optional[str] = None

    # Pricing
    base_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    price_unit: Optional[PriceUnit] = None

    # Capacity
    min_capacity: Optional[int] = Field(None, ge=1)
    max_capacity: Optional[int] = Field(None, ge=1)
    duration_hours: Optional[Decimal] = Field(None, gt=0)

    # Options
    is_customizable: bool = True
    is_active: bool = True

    @validator('max_price')
    def validate_max_price(cls, v, values):
        if v and 'base_price' in values and values['base_price']:
            if v < values['base_price']:
                raise ValueError('max_price must be greater than or equal to base_price')
        return v

    @validator('max_capacity')
    def validate_max_capacity(cls, v, values):
        if v and 'min_capacity' in values and values['min_capacity']:
            if v < values['min_capacity']:
                raise ValueError('max_capacity must be greater than or equal to min_capacity')
        return v


class VendorPortfolioBase(BaseModel):
    """Base vendor portfolio schema"""
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    media_type: MediaType
    media_url: HttpUrl
    thumbnail_url: Optional[HttpUrl] = None
    width: Optional[int] = Field(None, gt=0)
    height: Optional[int] = Field(None, gt=0)
    file_size: Optional[int] = Field(None, gt=0)
    order_index: int = Field(0, ge=0)
    is_featured: bool = False
    event_type: Optional[str] = Field(None, max_length=50)


class VendorAvailabilityBase(BaseModel):
    """Base vendor availability schema"""
    date: date
    status: AvailabilityStatus
    notes: Optional[str] = None

    @validator('date')
    def validate_date(cls, v):
        if v < date.today():
            raise ValueError('Availability date cannot be in the past')
        return v


class VendorTeamMemberBase(BaseModel):
    """Base vendor team member schema"""
    name: str = Field(..., min_length=2, max_length=255)
    role: str = Field(..., min_length=2, max_length=100)
    bio: Optional[str] = None
    photo_url: Optional[HttpUrl] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    order_index: int = Field(0, ge=0)


class VendorCertificationBase(BaseModel):
    """Base vendor certification schema"""
    certification_name: str = Field(..., min_length=2, max_length=255)
    issuing_organization: str = Field(..., min_length=2, max_length=255)
    issue_date: date
    expiry_date: Optional[date] = None
    certificate_url: Optional[HttpUrl] = None

    @validator('expiry_date')
    def validate_expiry_date(cls, v, values):
        if v and 'issue_date' in values and v <= values['issue_date']:
            raise ValueError('expiry_date must be after issue_date')
        return v


class VendorWorkingHoursBase(BaseModel):
    """Base vendor working hours schema"""
    day_of_week: int = Field(..., ge=0, le=6)
    open_time: time
    close_time: time
    is_closed: bool = False

    @validator('close_time')
    def validate_close_time(cls, v, values):
        if not values.get('is_closed', False) and 'open_time' in values:
            if v <= values['open_time']:
                raise ValueError('close_time must be after open_time')
        return v


# ============================================================================
# Create Schemas
# ============================================================================

class VendorCreate(VendorBase):
    """Schema for creating a new vendor profile"""
    subcategories: List[str] = Field(default_factory=list, max_items=10)

    # Business Registration (optional at creation)
    business_registration_number: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=100)


class VendorServiceCreate(VendorServiceBase):
    """Schema for creating a vendor service"""
    pass


class VendorPortfolioCreate(VendorPortfolioBase):
    """Schema for creating a portfolio item"""
    pass


class VendorAvailabilityCreate(VendorAvailabilityBase):
    """Schema for creating availability entry"""
    pass


class VendorTeamMemberCreate(VendorTeamMemberBase):
    """Schema for adding a team member"""
    user_id: Optional[UUID] = None


class VendorCertificationCreate(VendorCertificationBase):
    """Schema for adding a certification"""
    pass


class VendorWorkingHoursCreate(VendorWorkingHoursBase):
    """Schema for setting working hours"""
    pass


# ============================================================================
# Update Schemas
# ============================================================================

class VendorUpdate(BaseModel):
    """Schema for updating vendor profile"""
    business_name: Optional[str] = Field(None, min_length=2, max_length=255)
    business_type: Optional[BusinessType] = None
    description: Optional[str] = Field(None, min_length=10)
    short_description: Optional[str] = Field(None, max_length=500)

    # Branding
    logo_url: Optional[HttpUrl] = None
    cover_image_url: Optional[HttpUrl] = None

    # Contact Information
    website_url: Optional[HttpUrl] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[EmailStr] = None

    # Location
    location_city: Optional[str] = Field(None, min_length=2, max_length=100)
    location_district: Optional[str] = Field(None, max_length=100)
    location_address: Optional[str] = None
    location_lat: Optional[Decimal] = Field(None, ge=-90, le=90)
    location_lng: Optional[Decimal] = Field(None, ge=-180, le=180)
    service_radius_km: Optional[int] = Field(None, ge=0, le=500)

    # Sustainability
    eco_certified: Optional[bool] = None
    eco_score: Optional[Decimal] = Field(None, ge=0, le=100)

    # Business Registration
    business_registration_number: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=100)


class VendorServiceUpdate(BaseModel):
    """Schema for updating vendor service"""
    service_name: Optional[str] = Field(None, min_length=2, max_length=255)
    service_category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    base_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    price_unit: Optional[PriceUnit] = None
    min_capacity: Optional[int] = Field(None, ge=1)
    max_capacity: Optional[int] = Field(None, ge=1)
    duration_hours: Optional[Decimal] = Field(None, gt=0)
    is_customizable: Optional[bool] = None
    is_active: Optional[bool] = None


class VendorPortfolioUpdate(BaseModel):
    """Schema for updating portfolio item"""
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    order_index: Optional[int] = Field(None, ge=0)
    is_featured: Optional[bool] = None
    event_type: Optional[str] = Field(None, max_length=50)


class VendorAvailabilityUpdate(BaseModel):
    """Schema for updating availability"""
    status: Optional[AvailabilityStatus] = None
    notes: Optional[str] = None


class VendorTeamMemberUpdate(BaseModel):
    """Schema for updating team member"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    role: Optional[str] = Field(None, min_length=2, max_length=100)
    bio: Optional[str] = None
    photo_url: Optional[HttpUrl] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    order_index: Optional[int] = Field(None, ge=0)


class VendorWorkingHoursUpdate(BaseModel):
    """Schema for updating working hours"""
    open_time: Optional[time] = None
    close_time: Optional[time] = None
    is_closed: Optional[bool] = None


# ============================================================================
# Response Schemas
# ============================================================================

class VendorSubcategoryResponse(BaseModel):
    """Response schema for vendor subcategory"""
    subcategory: str

    class Config:
        from_attributes = True


class VendorServiceResponse(VendorServiceBase):
    """Response schema for vendor service"""
    id: UUID
    vendor_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VendorPortfolioResponse(VendorPortfolioBase):
    """Response schema for portfolio item"""
    id: UUID
    vendor_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class VendorAvailabilityResponse(VendorAvailabilityBase):
    """Response schema for availability"""
    id: UUID
    vendor_id: UUID
    booking_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VendorTeamMemberResponse(VendorTeamMemberBase):
    """Response schema for team member"""
    id: UUID
    vendor_id: UUID
    user_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VendorCertificationResponse(VendorCertificationBase):
    """Response schema for certification"""
    id: UUID
    vendor_id: UUID
    verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class VendorWorkingHoursResponse(VendorWorkingHoursBase):
    """Response schema for working hours"""
    id: UUID
    vendor_id: UUID

    class Config:
        from_attributes = True


class VendorResponse(VendorBase):
    """Response schema for vendor profile"""
    id: UUID
    user_id: UUID

    # Branding
    logo_url: Optional[str] = None
    cover_image_url: Optional[str] = None

    # Verification
    verified: bool
    verification_date: Optional[datetime] = None

    # Ratings and Performance
    avg_rating: Decimal
    review_count: int
    booking_count: int
    completion_rate: Optional[Decimal] = None
    response_time_hours: Optional[Decimal] = None

    # Subscription
    subscription_tier: SubscriptionTier
    subscription_started_at: Optional[datetime] = None
    subscription_expires_at: Optional[datetime] = None
    zero_commission_until: Optional[datetime] = None
    commission_rate: Decimal

    # Status
    status: VendorStatus
    featured: bool
    featured_until: Optional[datetime] = None

    # Business Registration
    business_registration_number: Optional[str] = None
    tax_id: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VendorDetailResponse(VendorResponse):
    """Detailed vendor response with relationships"""
    subcategories: List[VendorSubcategoryResponse] = []
    services: List[VendorServiceResponse] = []
    portfolio: List[VendorPortfolioResponse] = []
    team_members: List[VendorTeamMemberResponse] = []
    certifications: List[VendorCertificationResponse] = []
    working_hours: List[VendorWorkingHoursResponse] = []

    class Config:
        from_attributes = True


# ============================================================================
# Search and Filter Schemas
# ============================================================================

class VendorSearchFilters(BaseModel):
    """Schema for vendor search and filtering"""
    # Text search
    query: Optional[str] = Field(None, min_length=2, max_length=200)

    # Category filtering
    category: Optional[VendorCategory] = None
    subcategories: Optional[List[str]] = Field(default=None, max_items=10)

    # Location filtering
    city: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    radius_km: Optional[int] = Field(None, ge=1, le=500)

    # Rating and verification
    min_rating: Optional[Decimal] = Field(None, ge=0, le=5)
    verified_only: bool = False
    eco_certified_only: bool = False

    # Pricing
    min_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)

    # Availability
    available_on: Optional[date] = None

    # Features
    featured_only: bool = False

    # Sorting
    sort_by: Optional[str] = Field(
        "relevance",
        regex="^(relevance|rating|price_low|price_high|newest|popular|distance)$"
    )

    @validator('max_price')
    def validate_max_price(cls, v, values):
        if v and 'min_price' in values and values['min_price']:
            if v < values['min_price']:
                raise ValueError('max_price must be greater than or equal to min_price')
        return v

    @root_validator
    def validate_location_search(cls, values):
        lat = values.get('latitude')
        lng = values.get('longitude')
        radius = values.get('radius_km')

        # If doing radius search, need both lat/lng and radius
        if any([lat, lng, radius]):
            if not all([lat, lng, radius]):
                raise ValueError(
                    'For location-based search, latitude, longitude, and radius_km are all required'
                )

        return values


class VendorListResponse(BaseModel):
    """Response schema for vendor list with pagination"""
    vendors: List[VendorResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# ============================================================================
# Verification and Admin Schemas
# ============================================================================

class VendorVerificationRequest(BaseModel):
    """Schema for vendor verification"""
    verification_notes: Optional[str] = None
    verified: bool


class VendorSubscriptionUpdate(BaseModel):
    """Schema for updating vendor subscription"""
    subscription_tier: SubscriptionTier
    subscription_started_at: Optional[datetime] = None
    subscription_expires_at: Optional[datetime] = None
    zero_commission_until: Optional[datetime] = None
    commission_rate: Optional[Decimal] = Field(None, ge=0, le=1)

    @validator('subscription_expires_at')
    def validate_expiry(cls, v, values):
        if v and 'subscription_started_at' in values and values['subscription_started_at']:
            if v <= values['subscription_started_at']:
                raise ValueError('subscription_expires_at must be after subscription_started_at')
        return v


class VendorStatusUpdate(BaseModel):
    """Schema for updating vendor status"""
    status: VendorStatus
    status_reason: Optional[str] = None


class VendorFeaturedUpdate(BaseModel):
    """Schema for featuring vendor"""
    featured: bool
    featured_until: Optional[datetime] = None

    @validator('featured_until')
    def validate_featured_until(cls, v, values):
        if v and v <= datetime.utcnow():
            raise ValueError('featured_until must be in the future')
        return v


# ============================================================================
# Statistics Schemas
# ============================================================================

class VendorStatistics(BaseModel):
    """Schema for vendor statistics"""
    total_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    completion_rate: Decimal
    avg_rating: Decimal
    review_count: int
    total_revenue: Decimal
    avg_response_time_hours: Decimal
    portfolio_count: int
    service_count: int

    # Monthly statistics
    bookings_this_month: int
    revenue_this_month: Decimal

    # Upcoming
    upcoming_bookings: int


# ============================================================================
# Bulk Operations Schemas
# ============================================================================

class BulkAvailabilityCreate(BaseModel):
    """Schema for bulk availability creation"""
    start_date: date
    end_date: date
    status: AvailabilityStatus
    notes: Optional[str] = None

    # Days of week (0 = Monday, 6 = Sunday)
    days_of_week: Optional[List[int]] = Field(None, min_items=1, max_items=7)

    @validator('days_of_week')
    def validate_days(cls, v):
        if v:
            for day in v:
                if day < 0 or day > 6:
                    raise ValueError('days_of_week must contain values between 0 and 6')
        return v

    @validator('end_date')
    def validate_end_date(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class BulkAvailabilityResponse(BaseModel):
    """Response schema for bulk availability operation"""
    created_count: int
    date_range: str
    status: AvailabilityStatus
