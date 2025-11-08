"""
CelebraTech Event Management System - Booking Service
Sprint 4: Booking & Quote System
FR-004: Booking & Quote Management
Business logic for booking operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import Optional, List, Tuple
from datetime import datetime

from app.models.user import User, UserRole
from app.models.booking import (
    BookingRequest,
    Quote,
    Booking,
    BookingPayment,
    BookingCancellation,
    BookingRequestStatus,
    QuoteStatus,
    BookingStatus,
    CancellationInitiator
)
from app.models.vendor import Vendor
from app.models.event import Event
from app.schemas.booking import (
    BookingRequestCreate,
    BookingRequestUpdate,
    QuoteCreate,
    QuoteUpdate,
    QuoteAccept,
    QuoteReject,
    BookingUpdate,
    BookingComplete,
    PaymentCreate,
    CancellationCreate,
    CancellationApprove,
    BookingRequestFilters,
    BookingFilters
)
from app.repositories.booking_repository import BookingRepository
from app.repositories.event_repository import EventRepository
from app.repositories.vendor_repository import VendorRepository


class BookingService:
    """Service for booking business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BookingRepository(db)
        self.event_repo = EventRepository(db)
        self.vendor_repo = VendorRepository(db)

    # ========================================================================
    # Permission Helpers
    # ========================================================================

    async def _check_event_access(self, event_id: str, user: User):
        """Check if user has access to event"""
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        # Check if user is event creator or organizer
        has_access = await self.event_repo.user_has_permission(event_id, str(user.id), "view")
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to access this event"
            )

        return event

    async def _check_vendor_access(self, vendor_id: str, user: User):
        """Check if user owns vendor"""
        vendor = await self.vendor_repo.get_by_id(vendor_id)
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

        if str(vendor.user_id) != str(user.id) and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to access this vendor"
            )

        return vendor

    def _check_booking_request_access(
        self,
        booking_request: BookingRequest,
        user: User
    ) -> bool:
        """Check if user can access booking request"""
        # Organizer or vendor owner or admin
        return (
            str(booking_request.organizer_id) == str(user.id) or
            user.role == UserRole.ADMIN
        )

    async def _check_booking_access(
        self,
        booking: Booking,
        user: User
    ) -> bool:
        """Check if user can access booking"""
        # Check if user is organizer
        if str(booking.organizer_id) == str(user.id):
            return True

        # Check if user is vendor owner
        vendor = await self.vendor_repo.get_by_id(str(booking.vendor_id))
        if vendor and str(vendor.user_id) == str(user.id):
            return True

        # Check if admin
        if user.role == UserRole.ADMIN:
            return True

        return False

    # ========================================================================
    # Booking Request Operations
    # ========================================================================

    async def create_booking_request(
        self,
        event_id: str,
        request_data: BookingRequestCreate,
        current_user: User
    ) -> BookingRequest:
        """Create a new booking request"""
        # Verify event access
        await self._check_event_access(event_id, current_user)

        # Verify vendor exists and is active
        vendor = await self.vendor_repo.get_by_id(str(request_data.vendor_id))
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

        if vendor.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vendor is not currently accepting bookings"
            )

        # Create booking request
        booking_request = await self.repo.create_booking_request(
            event_id,
            str(current_user.id),
            request_data
        )

        return booking_request

    async def get_booking_request(
        self,
        request_id: str,
        current_user: User
    ) -> BookingRequest:
        """Get booking request by ID"""
        booking_request = await self.repo.get_booking_request_by_id(request_id)
        if not booking_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking request not found"
            )

        # Check permission
        if not self._check_booking_request_access(booking_request, current_user):
            # Also check if user owns the vendor
            vendor = await self.vendor_repo.get_by_id(str(booking_request.vendor_id))
            if not vendor or str(vendor.user_id) != str(current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No permission to access this booking request"
                )

        return booking_request

    async def update_booking_request(
        self,
        request_id: str,
        request_data: BookingRequestUpdate,
        current_user: User
    ) -> BookingRequest:
        """Update booking request"""
        booking_request = await self.get_booking_request(request_id, current_user)

        # Only organizer can update
        if str(booking_request.organizer_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the organizer can update the booking request"
            )

        # Can only update if still pending or draft
        if booking_request.status not in [BookingRequestStatus.DRAFT, BookingRequestStatus.PENDING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update booking request in current status"
            )

        updated_request = await self.repo.update_booking_request(request_id, request_data)
        return updated_request

    async def get_booking_requests_for_event(
        self,
        event_id: str,
        current_user: User
    ) -> List[BookingRequest]:
        """Get all booking requests for an event"""
        await self._check_event_access(event_id, current_user)
        return await self.repo.get_booking_requests_for_event(event_id)

    async def get_booking_requests_for_vendor(
        self,
        vendor_id: str,
        filters: Optional[BookingRequestFilters],
        page: int,
        page_size: int,
        current_user: User
    ) -> Tuple[List[BookingRequest], int]:
        """Get booking requests for vendor"""
        await self._check_vendor_access(vendor_id, current_user)
        return await self.repo.get_booking_requests_for_vendor(
            vendor_id, filters, page, page_size
        )

    async def mark_request_as_viewed(
        self,
        request_id: str,
        current_user: User
    ) -> BookingRequest:
        """Mark booking request as viewed by vendor"""
        booking_request = await self.get_booking_request(request_id, current_user)

        # Must be vendor owner
        vendor = await self._check_vendor_access(str(booking_request.vendor_id), current_user)

        await self.repo.mark_as_viewed(request_id)
        return await self.get_booking_request(request_id, current_user)

    # ========================================================================
    # Quote Operations
    # ========================================================================

    async def create_quote(
        self,
        quote_data: QuoteCreate,
        current_user: User
    ) -> Quote:
        """Create a quote for booking request"""
        # Get booking request
        booking_request = await self.repo.get_booking_request_by_id(
            str(quote_data.booking_request_id)
        )
        if not booking_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking request not found"
            )

        # Must be vendor owner
        vendor = await self._check_vendor_access(str(booking_request.vendor_id), current_user)

        # Booking request must be in pending status
        if booking_request.status not in [BookingRequestStatus.PENDING, BookingRequestStatus.QUOTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create quote for this booking request"
            )

        # Create quote
        quote = await self.repo.create_quote(str(vendor.id), quote_data)
        return quote

    async def get_quote(
        self,
        quote_id: str,
        current_user: User,
        load_items: bool = False
    ) -> Quote:
        """Get quote by ID"""
        quote = await self.repo.get_quote_by_id(quote_id, load_items)
        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quote not found"
            )

        # Check permission
        booking_request = await self.repo.get_booking_request_by_id(str(quote.booking_request_id))
        if not booking_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related booking request not found"
            )

        # Must be organizer or vendor owner
        is_organizer = str(booking_request.organizer_id) == str(current_user.id)
        vendor = await self.vendor_repo.get_by_id(str(booking_request.vendor_id))
        is_vendor = vendor and str(vendor.user_id) == str(current_user.id)

        if not (is_organizer or is_vendor or current_user.role == UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to access this quote"
            )

        return quote

    async def send_quote(
        self,
        quote_id: str,
        current_user: User
    ) -> Quote:
        """Send quote to organizer"""
        quote = await self.get_quote(quote_id, current_user)

        # Must be vendor owner
        vendor = await self.vendor_repo.get_by_id(str(quote.vendor_id))
        if not vendor or str(vendor.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only vendor can send quote"
            )

        # Quote must be in draft status
        if quote.status != QuoteStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quote has already been sent"
            )

        return await self.repo.send_quote(quote_id)

    async def accept_quote(
        self,
        quote_id: str,
        accept_data: QuoteAccept,
        current_user: User
    ) -> Booking:
        """Accept quote and create booking"""
        quote = await self.get_quote(quote_id, current_user, load_items=True)

        # Get booking request
        booking_request = await self.repo.get_booking_request_by_id(str(quote.booking_request_id))

        # Must be organizer
        if str(booking_request.organizer_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organizer can accept quote"
            )

        # Quote must be sent or viewed
        if quote.status not in [QuoteStatus.SENT, QuoteStatus.VIEWED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quote is not available for acceptance"
            )

        # Check if quote is still valid
        if quote.valid_until < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quote has expired"
            )

        # Accept quote
        await self.repo.accept_quote(quote_id)

        # Create booking
        booking = await self.repo.create_booking(quote, booking_request)

        return booking

    async def reject_quote(
        self,
        quote_id: str,
        reject_data: QuoteReject,
        current_user: User
    ) -> Quote:
        """Reject a quote"""
        quote = await self.get_quote(quote_id, current_user)

        # Get booking request
        booking_request = await self.repo.get_booking_request_by_id(str(quote.booking_request_id))

        # Must be organizer
        if str(booking_request.organizer_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organizer can reject quote"
            )

        return await self.repo.reject_quote(quote_id, reject_data.rejection_reason)

    async def get_quotes_for_request(
        self,
        booking_request_id: str,
        current_user: User
    ) -> List[Quote]:
        """Get all quotes for a booking request"""
        booking_request = await self.get_booking_request(booking_request_id, current_user)
        return await self.repo.get_quotes_for_request(booking_request_id)

    # ========================================================================
    # Booking Operations
    # ========================================================================

    async def get_booking(
        self,
        booking_id: str,
        current_user: User,
        load_relationships: bool = False
    ) -> Booking:
        """Get booking by ID"""
        booking = await self.repo.get_booking_by_id(booking_id, load_relationships)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )

        # Check permission
        has_access = await self._check_booking_access(booking, current_user)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to access this booking"
            )

        return booking

    async def update_booking(
        self,
        booking_id: str,
        booking_data: BookingUpdate,
        current_user: User
    ) -> Booking:
        """Update booking"""
        booking = await self.get_booking(booking_id, current_user)

        # Only organizer can update booking details
        if str(booking.organizer_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organizer can update booking"
            )

        return await self.repo.update_booking(booking_id, booking_data)

    async def complete_booking(
        self,
        booking_id: str,
        complete_data: BookingComplete,
        current_user: User
    ) -> Booking:
        """Mark booking as completed"""
        booking = await self.get_booking(booking_id, current_user)

        # Vendor can mark as completed
        vendor = await self.vendor_repo.get_by_id(str(booking.vendor_id))
        if not vendor or str(vendor.user_id) != str(current_user.id):
            if current_user.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only vendor or admin can complete booking"
                )

        # Booking must be confirmed
        if booking.status != BookingStatus.CONFIRMED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only complete confirmed bookings"
            )

        # Event date must have passed
        if booking.event_date > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot complete booking before event date"
            )

        return await self.repo.complete_booking(booking_id, complete_data.completion_notes)

    async def get_bookings_for_event(
        self,
        event_id: str,
        current_user: User
    ) -> List[Booking]:
        """Get all bookings for an event"""
        await self._check_event_access(event_id, current_user)
        return await self.repo.get_bookings_for_event(event_id)

    async def get_bookings_for_vendor(
        self,
        vendor_id: str,
        filters: Optional[BookingFilters],
        page: int,
        page_size: int,
        current_user: User
    ) -> Tuple[List[Booking], int]:
        """Get bookings for vendor"""
        await self._check_vendor_access(vendor_id, current_user)
        return await self.repo.get_bookings_for_vendor(vendor_id, filters, page, page_size)

    # ========================================================================
    # Payment Operations
    # ========================================================================

    async def create_payment(
        self,
        booking_id: str,
        payment_data: PaymentCreate,
        current_user: User
    ) -> BookingPayment:
        """Create a payment"""
        booking = await self.get_booking(booking_id, current_user)

        # Only organizer can make payments
        if str(booking.organizer_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organizer can make payments"
            )

        # Booking must not be cancelled
        if booking.status == BookingStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot make payment for cancelled booking"
            )

        # Validate payment amount
        if payment_data.amount > booking.amount_due:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment amount exceeds amount due"
            )

        return await self.repo.create_payment(
            booking_id,
            str(current_user.id),
            payment_data
        )

    # ========================================================================
    # Cancellation Operations
    # ========================================================================

    async def cancel_booking(
        self,
        booking_id: str,
        cancellation_data: CancellationCreate,
        current_user: User
    ) -> BookingCancellation:
        """Cancel a booking"""
        booking = await self.get_booking(booking_id, current_user)

        # Cannot cancel already cancelled booking
        if booking.status == BookingStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking is already cancelled"
            )

        # Cannot cancel completed booking
        if booking.status == BookingStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel completed booking"
            )

        # Determine initiator
        if str(booking.organizer_id) == str(current_user.id):
            initiator = CancellationInitiator.ORGANIZER
        elif current_user.role == UserRole.ADMIN:
            initiator = CancellationInitiator.ADMIN
        else:
            # Check if vendor owner
            vendor = await self.vendor_repo.get_by_id(str(booking.vendor_id))
            if vendor and str(vendor.user_id) == str(current_user.id):
                initiator = CancellationInitiator.VENDOR
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No permission to cancel this booking"
                )

        return await self.repo.create_cancellation(
            booking_id,
            str(current_user.id),
            initiator,
            cancellation_data
        )
