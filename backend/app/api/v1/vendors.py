"""
CelebraTech Event Management System - Vendor API
Sprint 3: Vendor Profile Foundation
FR-003: Vendor Marketplace & Discovery
FastAPI endpoints for vendor marketplace
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_admin_user
from app.models.user import User
from app.models.vendor import VendorCategory
from app.schemas.vendor import (
    VendorCreate,
    VendorUpdate,
    VendorResponse,
    VendorDetailResponse,
    VendorListResponse,
    VendorServiceCreate,
    VendorServiceUpdate,
    VendorServiceResponse,
    VendorPortfolioCreate,
    VendorPortfolioUpdate,
    VendorPortfolioResponse,
    VendorAvailabilityCreate,
    VendorAvailabilityUpdate,
    VendorAvailabilityResponse,
    VendorTeamMemberCreate,
    VendorTeamMemberUpdate,
    VendorTeamMemberResponse,
    VendorCertificationCreate,
    VendorCertificationResponse,
    VendorWorkingHoursCreate,
    VendorWorkingHoursUpdate,
    VendorWorkingHoursResponse,
    VendorSearchFilters,
    VendorStatistics,
    VendorVerificationRequest,
    VendorSubscriptionUpdate,
    VendorStatusUpdate,
    VendorFeaturedUpdate,
    BulkAvailabilityCreate,
    BulkAvailabilityResponse
)
from app.services.vendor_service import VendorService

router = APIRouter(prefix="/vendors", tags=["Vendors"])


# ============================================================================
# Vendor CRUD Endpoints
# ============================================================================

@router.post(
    "",
    response_model=VendorDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create vendor profile",
    description="Create a new vendor profile for current user"
)
async def create_vendor(
    vendor_data: VendorCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new vendor profile

    - **business_name**: Business name (required)
    - **category**: Main vendor category (required)
    - **description**: Detailed description (required)
    - **phone**: Contact phone (required)
    - **email**: Contact email (required)
    - **location_city**: City location (required)
    - **subcategories**: Additional service categories

    Returns created vendor profile with PENDING_VERIFICATION status
    """
    vendor_service = VendorService(db)
    vendor = await vendor_service.create_vendor(vendor_data, current_user)
    return VendorDetailResponse.from_orm(vendor)


@router.get(
    "/me",
    response_model=VendorDetailResponse,
    summary="Get my vendor profile",
    description="Get current user's vendor profile"
)
async def get_my_vendor(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's vendor profile

    Returns vendor profile with all related data
    """
    vendor_service = VendorService(db)
    vendor = await vendor_service.get_my_vendor(current_user)

    # Load relationships
    vendor = await vendor_service.get_vendor(
        str(vendor.id),
        current_user,
        load_relationships=True
    )

    return VendorDetailResponse.from_orm(vendor)


@router.get(
    "/search",
    response_model=VendorListResponse,
    summary="Search vendors",
    description="Search and filter vendors in marketplace"
)
async def search_vendors(
    query: Optional[str] = None,
    category: Optional[VendorCategory] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    verified_only: bool = False,
    eco_certified_only: bool = False,
    featured_only: bool = False,
    available_on: Optional[date] = None,
    latitude: Optional[float] = Query(None, ge=-90, le=90),
    longitude: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: Optional[int] = Query(None, ge=1, le=500),
    sort_by: str = Query("relevance", regex="^(relevance|rating|newest|popular)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Search vendors with filters

    Query parameters:
    - **query**: Text search in business name and description
    - **category**: Filter by vendor category
    - **city**: Filter by city
    - **district**: Filter by district
    - **min_rating**: Minimum average rating
    - **verified_only**: Show only verified vendors
    - **eco_certified_only**: Show only eco-certified vendors
    - **featured_only**: Show only featured vendors
    - **available_on**: Filter by availability date
    - **latitude/longitude/radius_km**: Location-based search
    - **sort_by**: Sort order (relevance, rating, newest, popular)
    - **page**: Page number
    - **page_size**: Items per page

    Returns paginated list of vendors
    """
    # Build filters
    filters = VendorSearchFilters(
        query=query,
        category=category,
        city=city,
        district=district,
        min_rating=min_rating,
        verified_only=verified_only,
        eco_certified_only=eco_certified_only,
        featured_only=featured_only,
        available_on=available_on,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        sort_by=sort_by
    )

    vendor_service = VendorService(db)
    vendors, total = await vendor_service.search_vendors(filters, page, page_size)

    return VendorListResponse(
        vendors=[VendorResponse.from_orm(v) for v in vendors],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.get(
    "/{vendor_id}",
    response_model=VendorDetailResponse,
    summary="Get vendor by ID",
    description="Get vendor details with full information"
)
async def get_vendor(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get vendor by ID

    Returns vendor with all related data (services, portfolio, team, etc.)
    Public endpoint - accessible without authentication
    """
    vendor_service = VendorService(db)
    vendor = await vendor_service.get_vendor(vendor_id, load_relationships=True)
    return VendorDetailResponse.from_orm(vendor)


@router.put(
    "/{vendor_id}",
    response_model=VendorResponse,
    summary="Update vendor profile",
    description="Update vendor profile details"
)
async def update_vendor(
    vendor_id: str,
    vendor_data: VendorUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update vendor profile

    Only the vendor owner can update the profile.
    All fields are optional - only provided fields will be updated.
    """
    vendor_service = VendorService(db)
    vendor = await vendor_service.update_vendor(vendor_id, vendor_data, current_user)
    return VendorResponse.from_orm(vendor)


@router.delete(
    "/{vendor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete vendor profile",
    description="Soft delete vendor profile"
)
async def delete_vendor(
    vendor_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete vendor profile

    Only the vendor owner can delete the profile.
    This is a soft delete - data is preserved but marked as deleted.
    """
    vendor_service = VendorService(db)
    await vendor_service.delete_vendor(vendor_id, current_user)
    return None


# ============================================================================
# Service Management Endpoints
# ============================================================================

@router.post(
    "/{vendor_id}/services",
    response_model=VendorServiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add service",
    description="Add a new service to vendor"
)
async def add_service(
    vendor_id: str,
    service_data: VendorServiceCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new service to vendor

    - **service_name**: Service name (required)
    - **service_category**: Service category (required)
    - **description**: Service description
    - **base_price/max_price**: Price range
    - **price_unit**: Pricing unit (PER_PERSON, PER_HOUR, etc.)
    - **min_capacity/max_capacity**: Capacity range
    - **duration_hours**: Service duration

    Returns created service
    """
    vendor_service = VendorService(db)
    service = await vendor_service.add_service(vendor_id, service_data, current_user)
    return VendorServiceResponse.from_orm(service)


@router.get(
    "/{vendor_id}/services",
    response_model=List[VendorServiceResponse],
    summary="Get vendor services",
    description="Get all services for a vendor"
)
async def get_services(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all services for a vendor"""
    vendor_service = VendorService(db)
    services = await vendor_service.get_services(vendor_id)
    return [VendorServiceResponse.from_orm(s) for s in services]


@router.put(
    "/{vendor_id}/services/{service_id}",
    response_model=VendorServiceResponse,
    summary="Update service",
    description="Update a vendor service"
)
async def update_service(
    vendor_id: str,
    service_id: str,
    service_data: VendorServiceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a vendor service

    All fields are optional - only provided fields will be updated.
    """
    vendor_service = VendorService(db)
    service = await vendor_service.update_service(
        vendor_id, service_id, service_data, current_user
    )
    return VendorServiceResponse.from_orm(service)


@router.delete(
    "/{vendor_id}/services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete service",
    description="Delete a vendor service"
)
async def delete_service(
    vendor_id: str,
    service_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a vendor service"""
    vendor_service = VendorService(db)
    await vendor_service.delete_service(vendor_id, service_id, current_user)
    return None


# ============================================================================
# Portfolio Management Endpoints
# ============================================================================

@router.post(
    "/{vendor_id}/portfolio",
    response_model=VendorPortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add portfolio item",
    description="Add a portfolio item (photo/video)"
)
async def add_portfolio_item(
    vendor_id: str,
    portfolio_data: VendorPortfolioCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a portfolio item

    - **title**: Item title (required)
    - **media_type**: IMAGE or VIDEO (required)
    - **media_url**: URL to media file (required)
    - **thumbnail_url**: Thumbnail URL
    - **is_featured**: Mark as featured
    - **event_type**: Related event type

    Returns created portfolio item
    """
    vendor_service = VendorService(db)
    portfolio = await vendor_service.add_portfolio_item(
        vendor_id, portfolio_data, current_user
    )
    return VendorPortfolioResponse.from_orm(portfolio)


@router.get(
    "/{vendor_id}/portfolio",
    response_model=List[VendorPortfolioResponse],
    summary="Get vendor portfolio",
    description="Get all portfolio items for a vendor"
)
async def get_portfolio(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all portfolio items for a vendor"""
    vendor_service = VendorService(db)
    portfolio = await vendor_service.get_portfolio(vendor_id)
    return [VendorPortfolioResponse.from_orm(p) for p in portfolio]


@router.put(
    "/{vendor_id}/portfolio/{portfolio_id}",
    response_model=VendorPortfolioResponse,
    summary="Update portfolio item",
    description="Update a portfolio item"
)
async def update_portfolio_item(
    vendor_id: str,
    portfolio_id: str,
    portfolio_data: VendorPortfolioUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a portfolio item

    All fields are optional - only provided fields will be updated.
    """
    vendor_service = VendorService(db)
    portfolio = await vendor_service.update_portfolio_item(
        vendor_id, portfolio_id, portfolio_data, current_user
    )
    return VendorPortfolioResponse.from_orm(portfolio)


@router.delete(
    "/{vendor_id}/portfolio/{portfolio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete portfolio item",
    description="Delete a portfolio item"
)
async def delete_portfolio_item(
    vendor_id: str,
    portfolio_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a portfolio item"""
    vendor_service = VendorService(db)
    await vendor_service.delete_portfolio_item(vendor_id, portfolio_id, current_user)
    return None


# ============================================================================
# Availability Management Endpoints
# ============================================================================

@router.post(
    "/{vendor_id}/availability",
    response_model=VendorAvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set availability",
    description="Set availability for a specific date"
)
async def set_availability(
    vendor_id: str,
    availability_data: VendorAvailabilityCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Set availability for a specific date

    - **date**: Date (required)
    - **status**: AVAILABLE, BOOKED, BLOCKED, or TENTATIVE (required)
    - **notes**: Optional notes

    Returns created/updated availability entry
    """
    vendor_service = VendorService(db)
    availability = await vendor_service.set_availability(
        vendor_id, availability_data, current_user
    )
    return VendorAvailabilityResponse.from_orm(availability)


@router.post(
    "/{vendor_id}/availability/bulk",
    response_model=BulkAvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk set availability",
    description="Set availability for multiple dates"
)
async def bulk_set_availability(
    vendor_id: str,
    bulk_data: BulkAvailabilityCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Set availability for multiple dates

    - **start_date**: Start date (required)
    - **end_date**: End date (required)
    - **status**: Availability status (required)
    - **days_of_week**: Optional list of weekdays (0=Mon, 6=Sun)
    - **notes**: Optional notes

    Returns count of dates updated
    """
    vendor_service = VendorService(db)
    count = await vendor_service.bulk_set_availability(
        vendor_id, bulk_data, current_user
    )

    date_range = f"{bulk_data.start_date} to {bulk_data.end_date}"

    return BulkAvailabilityResponse(
        created_count=count,
        date_range=date_range,
        status=bulk_data.status
    )


@router.get(
    "/{vendor_id}/availability",
    response_model=List[VendorAvailabilityResponse],
    summary="Get availability",
    description="Get availability for date range"
)
async def get_availability(
    vendor_id: str,
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    db: AsyncSession = Depends(get_db)
):
    """Get availability for date range"""
    vendor_service = VendorService(db)
    availability = await vendor_service.get_availability(
        vendor_id, start_date, end_date
    )
    return [VendorAvailabilityResponse.from_orm(a) for a in availability]


@router.get(
    "/{vendor_id}/availability/check",
    response_model=dict,
    summary="Check availability",
    description="Check if vendor is available on a specific date"
)
async def check_availability(
    vendor_id: str,
    check_date: date = Query(..., description="Date to check"),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if vendor is available on a specific date

    Returns:
    - **available**: Boolean indicating availability
    - **date**: The checked date
    """
    vendor_service = VendorService(db)
    is_available = await vendor_service.check_availability(vendor_id, check_date)

    return {
        "available": is_available,
        "date": check_date.isoformat()
    }


# ============================================================================
# Team Member Management Endpoints
# ============================================================================

@router.post(
    "/{vendor_id}/team",
    response_model=VendorTeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add team member",
    description="Add a team member to vendor"
)
async def add_team_member(
    vendor_id: str,
    member_data: VendorTeamMemberCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a team member

    - **name**: Member name (required)
    - **role**: Member role (required)
    - **bio**: Biography
    - **photo_url**: Photo URL
    - **email/phone**: Contact information

    Returns created team member
    """
    vendor_service = VendorService(db)
    member = await vendor_service.add_team_member(vendor_id, member_data, current_user)
    return VendorTeamMemberResponse.from_orm(member)


@router.put(
    "/{vendor_id}/team/{member_id}",
    response_model=VendorTeamMemberResponse,
    summary="Update team member",
    description="Update a team member"
)
async def update_team_member(
    vendor_id: str,
    member_id: str,
    member_data: VendorTeamMemberUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a team member

    All fields are optional - only provided fields will be updated.
    """
    vendor_service = VendorService(db)
    member = await vendor_service.update_team_member(
        vendor_id, member_id, member_data, current_user
    )
    return VendorTeamMemberResponse.from_orm(member)


@router.delete(
    "/{vendor_id}/team/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete team member",
    description="Delete a team member"
)
async def delete_team_member(
    vendor_id: str,
    member_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a team member"""
    vendor_service = VendorService(db)
    await vendor_service.delete_team_member(vendor_id, member_id, current_user)
    return None


# ============================================================================
# Certification Management Endpoints
# ============================================================================

@router.post(
    "/{vendor_id}/certifications",
    response_model=VendorCertificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add certification",
    description="Add a certification to vendor"
)
async def add_certification(
    vendor_id: str,
    cert_data: VendorCertificationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a certification

    - **certification_name**: Certification name (required)
    - **issuing_organization**: Organization that issued (required)
    - **issue_date**: Issue date (required)
    - **expiry_date**: Expiration date
    - **certificate_url**: Certificate document URL

    Returns created certification
    """
    vendor_service = VendorService(db)
    cert = await vendor_service.add_certification(vendor_id, cert_data, current_user)
    return VendorCertificationResponse.from_orm(cert)


@router.delete(
    "/{vendor_id}/certifications/{cert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete certification",
    description="Delete a certification"
)
async def delete_certification(
    vendor_id: str,
    cert_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a certification"""
    vendor_service = VendorService(db)
    await vendor_service.delete_certification(vendor_id, cert_id, current_user)
    return None


# ============================================================================
# Working Hours Management Endpoints
# ============================================================================

@router.post(
    "/{vendor_id}/working-hours",
    response_model=VendorWorkingHoursResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set working hours",
    description="Set working hours for a day of week"
)
async def set_working_hours(
    vendor_id: str,
    hours_data: VendorWorkingHoursCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Set working hours for a day of week

    - **day_of_week**: Day (0=Monday, 6=Sunday) (required)
    - **open_time**: Opening time (required)
    - **close_time**: Closing time (required)
    - **is_closed**: Mark as closed

    Returns created/updated working hours
    """
    vendor_service = VendorService(db)
    hours = await vendor_service.set_working_hours(vendor_id, hours_data, current_user)
    return VendorWorkingHoursResponse.from_orm(hours)


@router.get(
    "/{vendor_id}/working-hours",
    response_model=List[VendorWorkingHoursResponse],
    summary="Get working hours",
    description="Get all working hours for vendor"
)
async def get_working_hours(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all working hours for vendor"""
    vendor_service = VendorService(db)
    hours = await vendor_service.get_working_hours(vendor_id)
    return [VendorWorkingHoursResponse.from_orm(h) for h in hours]


# ============================================================================
# Statistics Endpoint
# ============================================================================

@router.get(
    "/{vendor_id}/statistics",
    response_model=VendorStatistics,
    summary="Get vendor statistics",
    description="Get comprehensive vendor statistics"
)
async def get_statistics(
    vendor_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get vendor statistics

    Returns:
    - Booking statistics
    - Revenue information
    - Performance metrics
    - Portfolio and service counts

    Requires vendor owner or admin access
    """
    vendor_service = VendorService(db)
    stats = await vendor_service.get_statistics(vendor_id, current_user)
    return VendorStatistics(**stats)


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.post(
    "/{vendor_id}/verify",
    response_model=VendorResponse,
    summary="Verify vendor",
    description="Verify or unverify a vendor (admin only)"
)
async def verify_vendor(
    vendor_id: str,
    verification_data: VendorVerificationRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify or unverify a vendor

    Admin only endpoint.

    - **verified**: Verification status (required)
    - **verification_notes**: Notes about verification

    Returns updated vendor
    """
    vendor_service = VendorService(db)
    vendor = await vendor_service.verify_vendor(
        vendor_id, verification_data, current_user
    )
    return VendorResponse.from_orm(vendor)


@router.put(
    "/{vendor_id}/status",
    response_model=VendorResponse,
    summary="Update vendor status",
    description="Update vendor status (admin only)"
)
async def update_vendor_status(
    vendor_id: str,
    status_data: VendorStatusUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update vendor status

    Admin only endpoint.

    - **status**: New status (PENDING_VERIFICATION, ACTIVE, SUSPENDED, INACTIVE, DELETED)
    - **status_reason**: Reason for status change

    Returns updated vendor
    """
    vendor_service = VendorService(db)
    vendor = await vendor_service.update_vendor_status(
        vendor_id, status_data, current_user
    )
    return VendorResponse.from_orm(vendor)


@router.put(
    "/{vendor_id}/subscription",
    response_model=VendorResponse,
    summary="Update vendor subscription",
    description="Update vendor subscription (admin only)"
)
async def update_subscription(
    vendor_id: str,
    subscription_data: VendorSubscriptionUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update vendor subscription

    Admin only endpoint.

    - **subscription_tier**: Subscription tier (BASIC, STANDARD, PREMIUM, ENTERPRISE)
    - **subscription_started_at**: Subscription start date
    - **subscription_expires_at**: Subscription expiration date
    - **zero_commission_until**: Zero commission period end date
    - **commission_rate**: Commission rate (0-1)

    Returns updated vendor
    """
    vendor_service = VendorService(db)
    vendor = await vendor_service.update_subscription(
        vendor_id, subscription_data, current_user
    )
    return VendorResponse.from_orm(vendor)


@router.put(
    "/{vendor_id}/featured",
    response_model=VendorResponse,
    summary="Set featured status",
    description="Set vendor featured status (admin only)"
)
async def set_featured(
    vendor_id: str,
    featured_data: VendorFeaturedUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Set vendor featured status

    Admin only endpoint.

    - **featured**: Featured status (required)
    - **featured_until**: Feature expiration date

    Returns updated vendor
    """
    vendor_service = VendorService(db)
    vendor = await vendor_service.set_featured(
        vendor_id, featured_data, current_user
    )
    return VendorResponse.from_orm(vendor)
