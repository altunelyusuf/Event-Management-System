"""
CelebraTech Event Management System - Vendor Service
Sprint 3: Vendor Profile Foundation
FR-003: Vendor Marketplace & Discovery
Business logic for vendor operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import Optional, List, Tuple
from datetime import date

from app.models.user import User, UserRole
from app.models.vendor import Vendor, VendorStatus
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
    VendorVerificationRequest,
    VendorSubscriptionUpdate,
    VendorStatusUpdate,
    VendorFeaturedUpdate,
    BulkAvailabilityCreate
)
from app.repositories.vendor_repository import VendorRepository


class VendorService:
    """Service for vendor business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = VendorRepository(db)

    # ========================================================================
    # Permission Helpers
    # ========================================================================

    def _is_vendor_owner(self, vendor: Vendor, user: User) -> bool:
        """Check if user owns the vendor profile"""
        return str(vendor.user_id) == str(user.id)

    def _is_admin(self, user: User) -> bool:
        """Check if user is admin"""
        return user.role == UserRole.ADMIN

    def _check_vendor_access(self, vendor: Vendor, user: User):
        """
        Check if user has access to vendor

        Raises:
            HTTPException: If user doesn't have access
        """
        if not (self._is_vendor_owner(vendor, user) or self._is_admin(user)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to access this vendor profile"
            )

    def _check_vendor_edit_permission(self, vendor: Vendor, user: User):
        """
        Check if user can edit vendor

        Raises:
            HTTPException: If user doesn't have permission
        """
        if not self._is_vendor_owner(vendor, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the vendor owner can edit this profile"
            )

    def _check_admin_permission(self, user: User):
        """
        Check if user is admin

        Raises:
            HTTPException: If user is not admin
        """
        if not self._is_admin(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required"
            )

    # ========================================================================
    # Vendor CRUD Operations
    # ========================================================================

    async def create_vendor(
        self,
        vendor_data: VendorCreate,
        current_user: User
    ) -> Vendor:
        """
        Create a new vendor profile

        Args:
            vendor_data: Vendor creation data
            current_user: Current user

        Returns:
            Created vendor

        Raises:
            HTTPException: If user already has a vendor profile
        """
        # Check if user already has a vendor profile
        existing_vendor = await self.repo.get_by_user_id(str(current_user.id))
        if existing_vendor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has a vendor profile"
            )

        # Create vendor
        vendor = await self.repo.create(str(current_user.id), vendor_data)
        return vendor

    async def get_vendor(
        self,
        vendor_id: str,
        current_user: Optional[User] = None,
        load_relationships: bool = False
    ) -> Vendor:
        """
        Get vendor by ID

        Args:
            vendor_id: Vendor ID
            current_user: Current user (optional for public access)
            load_relationships: Whether to load related data

        Returns:
            Vendor instance

        Raises:
            HTTPException: If vendor not found or access denied
        """
        vendor = await self.repo.get_by_id(vendor_id, load_relationships)
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

        # If vendor is not active and user is not owner/admin, deny access
        if vendor.status != VendorStatus.ACTIVE:
            if not current_user or not (
                self._is_vendor_owner(vendor, current_user) or self._is_admin(current_user)
            ):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Vendor not found"
                )

        return vendor

    async def get_my_vendor(self, current_user: User) -> Vendor:
        """
        Get current user's vendor profile

        Args:
            current_user: Current user

        Returns:
            Vendor instance

        Raises:
            HTTPException: If vendor not found
        """
        vendor = await self.repo.get_by_user_id(str(current_user.id))
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor profile not found"
            )

        return vendor

    async def update_vendor(
        self,
        vendor_id: str,
        vendor_data: VendorUpdate,
        current_user: User
    ) -> Vendor:
        """
        Update vendor profile

        Args:
            vendor_id: Vendor ID
            vendor_data: Update data
            current_user: Current user

        Returns:
            Updated vendor

        Raises:
            HTTPException: If vendor not found or access denied
        """
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        updated_vendor = await self.repo.update(vendor_id, vendor_data)
        if not updated_vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

        return updated_vendor

    async def delete_vendor(self, vendor_id: str, current_user: User):
        """
        Delete vendor profile

        Args:
            vendor_id: Vendor ID
            current_user: Current user

        Raises:
            HTTPException: If vendor not found or access denied
        """
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        success = await self.repo.delete(vendor_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

    # ========================================================================
    # Vendor Service Management
    # ========================================================================

    async def add_service(
        self,
        vendor_id: str,
        service_data: VendorServiceCreate,
        current_user: User
    ):
        """Add a service to vendor"""
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        return await self.repo.add_service(vendor_id, service_data)

    async def update_service(
        self,
        vendor_id: str,
        service_id: str,
        service_data: VendorServiceUpdate,
        current_user: User
    ):
        """Update a vendor service"""
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        service = await self.repo.update_service(service_id, service_data)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )

        return service

    async def delete_service(
        self,
        vendor_id: str,
        service_id: str,
        current_user: User
    ):
        """Delete a vendor service"""
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        success = await self.repo.delete_service(service_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )

    async def get_services(self, vendor_id: str):
        """Get all services for a vendor"""
        # Public access - no permission check needed
        await self.get_vendor(vendor_id)  # Just verify vendor exists
        return await self.repo.get_services(vendor_id)

    # ========================================================================
    # Portfolio Management
    # ========================================================================

    async def add_portfolio_item(
        self,
        vendor_id: str,
        portfolio_data: VendorPortfolioCreate,
        current_user: User
    ):
        """Add a portfolio item"""
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        return await self.repo.add_portfolio_item(vendor_id, portfolio_data)

    async def update_portfolio_item(
        self,
        vendor_id: str,
        portfolio_id: str,
        portfolio_data: VendorPortfolioUpdate,
        current_user: User
    ):
        """Update a portfolio item"""
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        portfolio = await self.repo.update_portfolio_item(portfolio_id, portfolio_data)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio item not found"
            )

        return portfolio

    async def delete_portfolio_item(
        self,
        vendor_id: str,
        portfolio_id: str,
        current_user: User
    ):
        """Delete a portfolio item"""
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        success = await self.repo.delete_portfolio_item(portfolio_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio item not found"
            )

    async def get_portfolio(self, vendor_id: str):
        """Get all portfolio items for a vendor"""
        # Public access
        await self.get_vendor(vendor_id)
        return await self.repo.get_portfolio(vendor_id)

    # ========================================================================
    # Availability Management
    # ========================================================================

    async def set_availability(
        self,
        vendor_id: str,
        availability_data: VendorAvailabilityCreate,
        current_user: User
    ):
        """Set availability for a specific date"""
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        return await self.repo.set_availability(vendor_id, availability_data)

    async def bulk_set_availability(
        self,
        vendor_id: str,
        bulk_data: BulkAvailabilityCreate,
        current_user: User
    ) -> int:
        """Set availability for multiple dates"""
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        return await self.repo.bulk_set_availability(vendor_id, bulk_data)

    async def get_availability(
        self,
        vendor_id: str,
        start_date: date,
        end_date: date
    ):
        """Get availability for date range"""
        # Public access
        await self.get_vendor(vendor_id)
        return await self.repo.get_availability(vendor_id, start_date, end_date)

    async def check_availability(self, vendor_id: str, check_date: date) -> bool:
        """Check if vendor is available on a specific date"""
        # Public access
        await self.get_vendor(vendor_id)
        return await self.repo.check_availability(vendor_id, check_date)

    # ========================================================================
    # Team Member Management
    # ========================================================================

    async def add_team_member(
        self,
        vendor_id: str,
        member_data: VendorTeamMemberCreate,
        current_user: User
    ):
        """Add a team member"""
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        return await self.repo.add_team_member(vendor_id, member_data)

    async def update_team_member(
        self,
        vendor_id: str,
        member_id: str,
        member_data: VendorTeamMemberUpdate,
        current_user: User
    ):
        """Update a team member"""
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        member = await self.repo.update_team_member(member_id, member_data)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found"
            )

        return member

    async def delete_team_member(
        self,
        vendor_id: str,
        member_id: str,
        current_user: User
    ):
        """Delete a team member"""
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        success = await self.repo.delete_team_member(member_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found"
            )

    # ========================================================================
    # Certification Management
    # ========================================================================

    async def add_certification(
        self,
        vendor_id: str,
        cert_data: VendorCertificationCreate,
        current_user: User
    ):
        """Add a certification"""
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        return await self.repo.add_certification(vendor_id, cert_data)

    async def delete_certification(
        self,
        vendor_id: str,
        cert_id: str,
        current_user: User
    ):
        """Delete a certification"""
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        success = await self.repo.delete_certification(cert_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certification not found"
            )

    # ========================================================================
    # Working Hours Management
    # ========================================================================

    async def set_working_hours(
        self,
        vendor_id: str,
        hours_data: VendorWorkingHoursCreate,
        current_user: User
    ):
        """Set working hours for a day"""
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_edit_permission(vendor, current_user)

        return await self.repo.set_working_hours(vendor_id, hours_data)

    async def get_working_hours(self, vendor_id: str):
        """Get all working hours for vendor"""
        # Public access
        await self.get_vendor(vendor_id)
        return await self.repo.get_working_hours(vendor_id)

    # ========================================================================
    # Search and Discovery
    # ========================================================================

    async def search_vendors(
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
        return await self.repo.search(filters, page, page_size)

    # ========================================================================
    # Statistics and Analytics
    # ========================================================================

    async def get_statistics(self, vendor_id: str, current_user: User) -> dict:
        """
        Get vendor statistics

        Args:
            vendor_id: Vendor ID
            current_user: Current user

        Returns:
            Statistics dictionary

        Raises:
            HTTPException: If vendor not found or access denied
        """
        vendor = await self.get_vendor(vendor_id, current_user)
        self._check_vendor_access(vendor, current_user)

        return await self.repo.get_statistics(vendor_id)

    # ========================================================================
    # Admin Operations
    # ========================================================================

    async def verify_vendor(
        self,
        vendor_id: str,
        verification_data: VendorVerificationRequest,
        current_user: User
    ) -> Vendor:
        """
        Verify or unverify a vendor

        Args:
            vendor_id: Vendor ID
            verification_data: Verification data
            current_user: Current user (must be admin)

        Returns:
            Updated vendor

        Raises:
            HTTPException: If not admin or vendor not found
        """
        self._check_admin_permission(current_user)

        vendor = await self.repo.verify_vendor(
            vendor_id,
            verification_data.verified,
            verification_data.verification_notes
        )

        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

        return vendor

    async def update_vendor_status(
        self,
        vendor_id: str,
        status_data: VendorStatusUpdate,
        current_user: User
    ) -> Vendor:
        """
        Update vendor status

        Args:
            vendor_id: Vendor ID
            status_data: Status update data
            current_user: Current user (must be admin)

        Returns:
            Updated vendor

        Raises:
            HTTPException: If not admin or vendor not found
        """
        self._check_admin_permission(current_user)

        vendor = await self.repo.update_status(vendor_id, status_data.status)
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

        return vendor

    async def update_subscription(
        self,
        vendor_id: str,
        subscription_data: VendorSubscriptionUpdate,
        current_user: User
    ) -> Vendor:
        """
        Update vendor subscription

        Args:
            vendor_id: Vendor ID
            subscription_data: Subscription data
            current_user: Current user (must be admin)

        Returns:
            Updated vendor

        Raises:
            HTTPException: If not admin or vendor not found
        """
        self._check_admin_permission(current_user)

        vendor = await self.get_vendor(vendor_id, current_user)

        # Update subscription fields
        vendor.subscription_tier = subscription_data.subscription_tier

        if subscription_data.subscription_started_at is not None:
            vendor.subscription_started_at = subscription_data.subscription_started_at

        if subscription_data.subscription_expires_at is not None:
            vendor.subscription_expires_at = subscription_data.subscription_expires_at

        if subscription_data.zero_commission_until is not None:
            vendor.zero_commission_until = subscription_data.zero_commission_until

        if subscription_data.commission_rate is not None:
            vendor.commission_rate = subscription_data.commission_rate

        await self.db.commit()
        await self.db.refresh(vendor)

        return vendor

    async def set_featured(
        self,
        vendor_id: str,
        featured_data: VendorFeaturedUpdate,
        current_user: User
    ) -> Vendor:
        """
        Set vendor featured status

        Args:
            vendor_id: Vendor ID
            featured_data: Featured data
            current_user: Current user (must be admin)

        Returns:
            Updated vendor

        Raises:
            HTTPException: If not admin or vendor not found
        """
        self._check_admin_permission(current_user)

        vendor = await self.repo.set_featured(
            vendor_id,
            featured_data.featured,
            featured_data.featured_until
        )

        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

        return vendor
