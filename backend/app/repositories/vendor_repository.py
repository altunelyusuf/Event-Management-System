"""
CelebraTech Event Management System - Vendor Repository
Sprint 3: Vendor Profile Foundation
FR-003: Vendor Marketplace & Discovery
Data access layer for vendor operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case, cast, Float
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID

from app.models.vendor import (
    Vendor,
    VendorSubcategory,
    VendorService,
    VendorPortfolio,
    VendorAvailability,
    VendorTeamMember,
    VendorCertification,
    VendorWorkingHours,
    VendorCategory,
    VendorStatus,
    AvailabilityStatus
)
from app.schemas.vendor import (
    VendorCreate,
    VendorUpdate,
    VendorServiceCreate,
    VendorServiceUpdate,
    VendorPortfolioCreate,
    VendorPortfolioUpdate,
    VendorAvailabilityCreate,
    VendorAvailabilityUpdate,
    VendorTeamMemberCreate,
    VendorTeamMemberUpdate,
    VendorCertificationCreate,
    VendorWorkingHoursCreate,
    VendorWorkingHoursUpdate,
    VendorSearchFilters,
    BulkAvailabilityCreate
)


class VendorRepository:
    """Repository for vendor data access"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Vendor CRUD Operations
    # ========================================================================

    async def create(self, user_id: str, vendor_data: VendorCreate) -> Vendor:
        """
        Create a new vendor profile

        Args:
            user_id: User ID creating the vendor profile
            vendor_data: Vendor creation data

        Returns:
            Created vendor instance
        """
        # Create vendor
        vendor = Vendor(
            user_id=UUID(user_id),
            business_name=vendor_data.business_name,
            business_type=vendor_data.business_type,
            category=vendor_data.category,
            description=vendor_data.description,
            short_description=vendor_data.short_description,
            website_url=str(vendor_data.website_url) if vendor_data.website_url else None,
            phone=vendor_data.phone,
            email=vendor_data.email,
            location_city=vendor_data.location_city,
            location_district=vendor_data.location_district,
            location_address=vendor_data.location_address,
            location_lat=vendor_data.location_lat,
            location_lng=vendor_data.location_lng,
            service_radius_km=vendor_data.service_radius_km,
            eco_certified=vendor_data.eco_certified,
            eco_score=vendor_data.eco_score,
            business_registration_number=vendor_data.business_registration_number,
            tax_id=vendor_data.tax_id,
            status=VendorStatus.PENDING_VERIFICATION
        )

        self.db.add(vendor)
        await self.db.flush()

        # Add subcategories
        if vendor_data.subcategories:
            for subcategory in vendor_data.subcategories:
                subcat = VendorSubcategory(
                    vendor_id=vendor.id,
                    subcategory=subcategory
                )
                self.db.add(subcat)

        await self.db.commit()
        await self.db.refresh(vendor)

        return vendor

    async def get_by_id(
        self,
        vendor_id: str,
        load_relationships: bool = False
    ) -> Optional[Vendor]:
        """
        Get vendor by ID

        Args:
            vendor_id: Vendor ID
            load_relationships: Whether to load related data

        Returns:
            Vendor instance or None
        """
        query = select(Vendor).where(
            and_(
                Vendor.id == UUID(vendor_id),
                Vendor.deleted_at.is_(None)
            )
        )

        if load_relationships:
            query = query.options(
                selectinload(Vendor.subcategories),
                selectinload(Vendor.services),
                selectinload(Vendor.portfolio),
                selectinload(Vendor.team_members),
                selectinload(Vendor.certifications),
                selectinload(Vendor.working_hours)
            )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: str) -> Optional[Vendor]:
        """
        Get vendor profile by user ID

        Args:
            user_id: User ID

        Returns:
            Vendor instance or None
        """
        query = select(Vendor).where(
            and_(
                Vendor.user_id == UUID(user_id),
                Vendor.deleted_at.is_(None)
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update(self, vendor_id: str, vendor_data: VendorUpdate) -> Optional[Vendor]:
        """
        Update vendor profile

        Args:
            vendor_id: Vendor ID
            vendor_data: Update data

        Returns:
            Updated vendor instance or None
        """
        vendor = await self.get_by_id(vendor_id)
        if not vendor:
            return None

        # Update fields
        update_data = vendor_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(vendor, field):
                if field in ['website_url', 'logo_url', 'cover_image_url'] and value:
                    value = str(value)
                setattr(vendor, field, value)

        await self.db.commit()
        await self.db.refresh(vendor)

        return vendor

    async def delete(self, vendor_id: str) -> bool:
        """
        Soft delete vendor

        Args:
            vendor_id: Vendor ID

        Returns:
            True if deleted, False if not found
        """
        vendor = await self.get_by_id(vendor_id)
        if not vendor:
            return False

        vendor.deleted_at = datetime.utcnow()
        vendor.status = VendorStatus.DELETED

        await self.db.commit()
        return True

    # ========================================================================
    # Vendor Service Management
    # ========================================================================

    async def add_service(
        self,
        vendor_id: str,
        service_data: VendorServiceCreate
    ) -> VendorService:
        """
        Add a service to vendor

        Args:
            vendor_id: Vendor ID
            service_data: Service data

        Returns:
            Created service instance
        """
        service = VendorService(
            vendor_id=UUID(vendor_id),
            **service_data.dict()
        )

        self.db.add(service)
        await self.db.commit()
        await self.db.refresh(service)

        return service

    async def update_service(
        self,
        service_id: str,
        service_data: VendorServiceUpdate
    ) -> Optional[VendorService]:
        """
        Update a vendor service

        Args:
            service_id: Service ID
            service_data: Update data

        Returns:
            Updated service or None
        """
        query = select(VendorService).where(VendorService.id == UUID(service_id))
        result = await self.db.execute(query)
        service = result.scalar_one_or_none()

        if not service:
            return None

        update_data = service_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(service, field, value)

        await self.db.commit()
        await self.db.refresh(service)

        return service

    async def delete_service(self, service_id: str) -> bool:
        """
        Delete a vendor service

        Args:
            service_id: Service ID

        Returns:
            True if deleted, False if not found
        """
        query = select(VendorService).where(VendorService.id == UUID(service_id))
        result = await self.db.execute(query)
        service = result.scalar_one_or_none()

        if not service:
            return False

        await self.db.delete(service)
        await self.db.commit()

        return True

    async def get_services(self, vendor_id: str) -> List[VendorService]:
        """
        Get all services for a vendor

        Args:
            vendor_id: Vendor ID

        Returns:
            List of services
        """
        query = select(VendorService).where(
            VendorService.vendor_id == UUID(vendor_id)
        ).order_by(VendorService.created_at)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Portfolio Management
    # ========================================================================

    async def add_portfolio_item(
        self,
        vendor_id: str,
        portfolio_data: VendorPortfolioCreate
    ) -> VendorPortfolio:
        """
        Add a portfolio item

        Args:
            vendor_id: Vendor ID
            portfolio_data: Portfolio data

        Returns:
            Created portfolio item
        """
        portfolio = VendorPortfolio(
            vendor_id=UUID(vendor_id),
            title=portfolio_data.title,
            description=portfolio_data.description,
            media_type=portfolio_data.media_type,
            media_url=str(portfolio_data.media_url),
            thumbnail_url=str(portfolio_data.thumbnail_url) if portfolio_data.thumbnail_url else None,
            width=portfolio_data.width,
            height=portfolio_data.height,
            file_size=portfolio_data.file_size,
            order_index=portfolio_data.order_index,
            is_featured=portfolio_data.is_featured,
            event_type=portfolio_data.event_type
        )

        self.db.add(portfolio)
        await self.db.commit()
        await self.db.refresh(portfolio)

        return portfolio

    async def update_portfolio_item(
        self,
        portfolio_id: str,
        portfolio_data: VendorPortfolioUpdate
    ) -> Optional[VendorPortfolio]:
        """
        Update a portfolio item

        Args:
            portfolio_id: Portfolio ID
            portfolio_data: Update data

        Returns:
            Updated portfolio item or None
        """
        query = select(VendorPortfolio).where(VendorPortfolio.id == UUID(portfolio_id))
        result = await self.db.execute(query)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            return None

        update_data = portfolio_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(portfolio, field, value)

        await self.db.commit()
        await self.db.refresh(portfolio)

        return portfolio

    async def delete_portfolio_item(self, portfolio_id: str) -> bool:
        """
        Delete a portfolio item

        Args:
            portfolio_id: Portfolio ID

        Returns:
            True if deleted, False if not found
        """
        query = select(VendorPortfolio).where(VendorPortfolio.id == UUID(portfolio_id))
        result = await self.db.execute(query)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            return False

        await self.db.delete(portfolio)
        await self.db.commit()

        return True

    async def get_portfolio(self, vendor_id: str) -> List[VendorPortfolio]:
        """
        Get all portfolio items for a vendor

        Args:
            vendor_id: Vendor ID

        Returns:
            List of portfolio items
        """
        query = select(VendorPortfolio).where(
            VendorPortfolio.vendor_id == UUID(vendor_id)
        ).order_by(VendorPortfolio.order_index, VendorPortfolio.created_at)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Availability Management
    # ========================================================================

    async def set_availability(
        self,
        vendor_id: str,
        availability_data: VendorAvailabilityCreate
    ) -> VendorAvailability:
        """
        Set availability for a specific date

        Args:
            vendor_id: Vendor ID
            availability_data: Availability data

        Returns:
            Created/updated availability
        """
        # Check if availability already exists for this date
        query = select(VendorAvailability).where(
            and_(
                VendorAvailability.vendor_id == UUID(vendor_id),
                VendorAvailability.date == availability_data.date
            )
        )
        result = await self.db.execute(query)
        availability = result.scalar_one_or_none()

        if availability:
            # Update existing
            availability.status = availability_data.status
            availability.notes = availability_data.notes
        else:
            # Create new
            availability = VendorAvailability(
                vendor_id=UUID(vendor_id),
                date=availability_data.date,
                status=availability_data.status,
                notes=availability_data.notes
            )
            self.db.add(availability)

        await self.db.commit()
        await self.db.refresh(availability)

        return availability

    async def bulk_set_availability(
        self,
        vendor_id: str,
        bulk_data: BulkAvailabilityCreate
    ) -> int:
        """
        Set availability for multiple dates

        Args:
            vendor_id: Vendor ID
            bulk_data: Bulk availability data

        Returns:
            Number of dates updated
        """
        current_date = bulk_data.start_date
        count = 0

        while current_date <= bulk_data.end_date:
            # Check if we should process this day
            if bulk_data.days_of_week:
                if current_date.weekday() not in bulk_data.days_of_week:
                    current_date += timedelta(days=1)
                    continue

            # Set availability
            query = select(VendorAvailability).where(
                and_(
                    VendorAvailability.vendor_id == UUID(vendor_id),
                    VendorAvailability.date == current_date
                )
            )
            result = await self.db.execute(query)
            availability = result.scalar_one_or_none()

            if availability:
                availability.status = bulk_data.status
                availability.notes = bulk_data.notes
            else:
                availability = VendorAvailability(
                    vendor_id=UUID(vendor_id),
                    date=current_date,
                    status=bulk_data.status,
                    notes=bulk_data.notes
                )
                self.db.add(availability)

            count += 1
            current_date += timedelta(days=1)

        await self.db.commit()
        return count

    async def get_availability(
        self,
        vendor_id: str,
        start_date: date,
        end_date: date
    ) -> List[VendorAvailability]:
        """
        Get availability for date range

        Args:
            vendor_id: Vendor ID
            start_date: Start date
            end_date: End date

        Returns:
            List of availability entries
        """
        query = select(VendorAvailability).where(
            and_(
                VendorAvailability.vendor_id == UUID(vendor_id),
                VendorAvailability.date >= start_date,
                VendorAvailability.date <= end_date
            )
        ).order_by(VendorAvailability.date)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def check_availability(self, vendor_id: str, check_date: date) -> bool:
        """
        Check if vendor is available on a specific date

        Args:
            vendor_id: Vendor ID
            check_date: Date to check

        Returns:
            True if available, False otherwise
        """
        query = select(VendorAvailability).where(
            and_(
                VendorAvailability.vendor_id == UUID(vendor_id),
                VendorAvailability.date == check_date,
                VendorAvailability.status == AvailabilityStatus.AVAILABLE
            )
        )

        result = await self.db.execute(query)
        availability = result.scalar_one_or_none()

        return availability is not None

    # ========================================================================
    # Team Member Management
    # ========================================================================

    async def add_team_member(
        self,
        vendor_id: str,
        member_data: VendorTeamMemberCreate
    ) -> VendorTeamMember:
        """Add a team member"""
        member = VendorTeamMember(
            vendor_id=UUID(vendor_id),
            user_id=member_data.user_id,
            name=member_data.name,
            role=member_data.role,
            bio=member_data.bio,
            photo_url=str(member_data.photo_url) if member_data.photo_url else None,
            email=member_data.email,
            phone=member_data.phone,
            order_index=member_data.order_index
        )

        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)

        return member

    async def update_team_member(
        self,
        member_id: str,
        member_data: VendorTeamMemberUpdate
    ) -> Optional[VendorTeamMember]:
        """Update a team member"""
        query = select(VendorTeamMember).where(VendorTeamMember.id == UUID(member_id))
        result = await self.db.execute(query)
        member = result.scalar_one_or_none()

        if not member:
            return None

        update_data = member_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == 'photo_url' and value:
                value = str(value)
            setattr(member, field, value)

        await self.db.commit()
        await self.db.refresh(member)

        return member

    async def delete_team_member(self, member_id: str) -> bool:
        """Delete a team member"""
        query = select(VendorTeamMember).where(VendorTeamMember.id == UUID(member_id))
        result = await self.db.execute(query)
        member = result.scalar_one_or_none()

        if not member:
            return False

        await self.db.delete(member)
        await self.db.commit()

        return True

    # ========================================================================
    # Certification Management
    # ========================================================================

    async def add_certification(
        self,
        vendor_id: str,
        cert_data: VendorCertificationCreate
    ) -> VendorCertification:
        """Add a certification"""
        cert = VendorCertification(
            vendor_id=UUID(vendor_id),
            certification_name=cert_data.certification_name,
            issuing_organization=cert_data.issuing_organization,
            issue_date=cert_data.issue_date,
            expiry_date=cert_data.expiry_date,
            certificate_url=str(cert_data.certificate_url) if cert_data.certificate_url else None
        )

        self.db.add(cert)
        await self.db.commit()
        await self.db.refresh(cert)

        return cert

    async def delete_certification(self, cert_id: str) -> bool:
        """Delete a certification"""
        query = select(VendorCertification).where(VendorCertification.id == UUID(cert_id))
        result = await self.db.execute(query)
        cert = result.scalar_one_or_none()

        if not cert:
            return False

        await self.db.delete(cert)
        await self.db.commit()

        return True

    # ========================================================================
    # Working Hours Management
    # ========================================================================

    async def set_working_hours(
        self,
        vendor_id: str,
        hours_data: VendorWorkingHoursCreate
    ) -> VendorWorkingHours:
        """Set working hours for a day"""
        # Check if hours already exist for this day
        query = select(VendorWorkingHours).where(
            and_(
                VendorWorkingHours.vendor_id == UUID(vendor_id),
                VendorWorkingHours.day_of_week == hours_data.day_of_week
            )
        )
        result = await self.db.execute(query)
        hours = result.scalar_one_or_none()

        if hours:
            # Update existing
            hours.open_time = hours_data.open_time
            hours.close_time = hours_data.close_time
            hours.is_closed = hours_data.is_closed
        else:
            # Create new
            hours = VendorWorkingHours(
                vendor_id=UUID(vendor_id),
                day_of_week=hours_data.day_of_week,
                open_time=hours_data.open_time,
                close_time=hours_data.close_time,
                is_closed=hours_data.is_closed
            )
            self.db.add(hours)

        await self.db.commit()
        await self.db.refresh(hours)

        return hours

    async def get_working_hours(self, vendor_id: str) -> List[VendorWorkingHours]:
        """Get all working hours for vendor"""
        query = select(VendorWorkingHours).where(
            VendorWorkingHours.vendor_id == UUID(vendor_id)
        ).order_by(VendorWorkingHours.day_of_week)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Search and Discovery
    # ========================================================================

    async def search(
        self,
        filters: VendorSearchFilters,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Vendor], int]:
        """
        Search vendors with filters

        Args:
            filters: Search filters
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (vendors list, total count)
        """
        # Base query
        query = select(Vendor).where(
            and_(
                Vendor.deleted_at.is_(None),
                Vendor.status == VendorStatus.ACTIVE
            )
        )

        # Category filter
        if filters.category:
            query = query.where(Vendor.category == filters.category)

        # Location filters
        if filters.city:
            query = query.where(Vendor.location_city.ilike(f"%{filters.city}%"))

        if filters.district:
            query = query.where(Vendor.location_district.ilike(f"%{filters.district}%"))

        # Rating filter
        if filters.min_rating:
            query = query.where(Vendor.avg_rating >= filters.min_rating)

        # Verification filters
        if filters.verified_only:
            query = query.where(Vendor.verified == True)

        if filters.eco_certified_only:
            query = query.where(Vendor.eco_certified == True)

        # Featured filter
        if filters.featured_only:
            query = query.where(
                and_(
                    Vendor.featured == True,
                    or_(
                        Vendor.featured_until.is_(None),
                        Vendor.featured_until > datetime.utcnow()
                    )
                )
            )

        # Text search
        if filters.query:
            search_term = f"%{filters.query}%"
            query = query.where(
                or_(
                    Vendor.business_name.ilike(search_term),
                    Vendor.description.ilike(search_term),
                    Vendor.short_description.ilike(search_term)
                )
            )

        # Location-based search (radius)
        if filters.latitude and filters.longitude and filters.radius_km:
            # Using Haversine formula for distance calculation
            lat1 = filters.latitude
            lon1 = filters.longitude
            radius = filters.radius_km

            # This is a simplified version - in production, use PostGIS
            query = query.where(
                and_(
                    Vendor.location_lat.isnot(None),
                    Vendor.location_lng.isnot(None)
                )
            )

        # Availability filter
        if filters.available_on:
            # Subquery for vendors available on the specified date
            avail_subquery = select(VendorAvailability.vendor_id).where(
                and_(
                    VendorAvailability.date == filters.available_on,
                    VendorAvailability.status == AvailabilityStatus.AVAILABLE
                )
            )
            query = query.where(Vendor.id.in_(avail_subquery))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Sorting
        if filters.sort_by == "rating":
            query = query.order_by(Vendor.avg_rating.desc())
        elif filters.sort_by == "newest":
            query = query.order_by(Vendor.created_at.desc())
        elif filters.sort_by == "popular":
            query = query.order_by(Vendor.booking_count.desc())
        else:  # relevance (default)
            query = query.order_by(Vendor.featured.desc(), Vendor.avg_rating.desc())

        # Pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute
        result = await self.db.execute(query)
        vendors = list(result.scalars().all())

        return vendors, total

    # ========================================================================
    # Statistics and Analytics
    # ========================================================================

    async def get_statistics(self, vendor_id: str) -> dict:
        """
        Get vendor statistics

        Args:
            vendor_id: Vendor ID

        Returns:
            Statistics dictionary
        """
        vendor = await self.get_by_id(vendor_id)
        if not vendor:
            return {}

        # Count portfolio items
        portfolio_query = select(func.count()).select_from(VendorPortfolio).where(
            VendorPortfolio.vendor_id == UUID(vendor_id)
        )
        portfolio_result = await self.db.execute(portfolio_query)
        portfolio_count = portfolio_result.scalar()

        # Count services
        service_query = select(func.count()).select_from(VendorService).where(
            and_(
                VendorService.vendor_id == UUID(vendor_id),
                VendorService.is_active == True
            )
        )
        service_result = await self.db.execute(service_query)
        service_count = service_result.scalar()

        # Build statistics
        stats = {
            "total_bookings": vendor.booking_count,
            "completed_bookings": 0,  # Will be calculated from bookings in later sprint
            "cancelled_bookings": 0,
            "completion_rate": vendor.completion_rate or Decimal("0"),
            "avg_rating": vendor.avg_rating,
            "review_count": vendor.review_count,
            "total_revenue": Decimal("0"),  # Will be calculated from bookings
            "avg_response_time_hours": vendor.response_time_hours or Decimal("0"),
            "portfolio_count": portfolio_count,
            "service_count": service_count,
            "bookings_this_month": 0,
            "revenue_this_month": Decimal("0"),
            "upcoming_bookings": 0
        }

        return stats

    # ========================================================================
    # Admin Operations
    # ========================================================================

    async def verify_vendor(
        self,
        vendor_id: str,
        verified: bool,
        notes: Optional[str] = None
    ) -> Optional[Vendor]:
        """
        Verify or unverify a vendor

        Args:
            vendor_id: Vendor ID
            verified: Verification status
            notes: Verification notes

        Returns:
            Updated vendor or None
        """
        vendor = await self.get_by_id(vendor_id)
        if not vendor:
            return None

        vendor.verified = verified
        vendor.verification_date = datetime.utcnow() if verified else None
        vendor.verification_notes = notes

        if verified:
            vendor.status = VendorStatus.ACTIVE

        await self.db.commit()
        await self.db.refresh(vendor)

        return vendor

    async def update_status(
        self,
        vendor_id: str,
        new_status: VendorStatus
    ) -> Optional[Vendor]:
        """
        Update vendor status

        Args:
            vendor_id: Vendor ID
            new_status: New status

        Returns:
            Updated vendor or None
        """
        vendor = await self.get_by_id(vendor_id)
        if not vendor:
            return None

        vendor.status = new_status

        await self.db.commit()
        await self.db.refresh(vendor)

        return vendor

    async def set_featured(
        self,
        vendor_id: str,
        featured: bool,
        featured_until: Optional[datetime] = None
    ) -> Optional[Vendor]:
        """
        Set vendor featured status

        Args:
            vendor_id: Vendor ID
            featured: Featured status
            featured_until: Feature expiration date

        Returns:
            Updated vendor or None
        """
        vendor = await self.get_by_id(vendor_id)
        if not vendor:
            return None

        vendor.featured = featured
        vendor.featured_until = featured_until

        await self.db.commit()
        await self.db.refresh(vendor)

        return vendor
