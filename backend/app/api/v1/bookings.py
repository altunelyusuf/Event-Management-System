"""
CelebraTech Event Management System - Booking API
Sprint 4: Booking & Quote System
FR-004: Booking & Quote Management
FastAPI endpoints for booking and quote management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.booking import BookingRequestStatus, BookingStatus, PaymentStatus
from app.schemas.booking import (
    BookingRequestCreate,
    BookingRequestUpdate,
    BookingRequestResponse,
    BookingRequestListResponse,
    QuoteCreate,
    QuoteUpdate,
    QuoteResponse,
    QuoteDetailResponse,
    QuoteListResponse,
    QuoteAccept,
    QuoteReject,
    BookingResponse,
    BookingUpdate,
    BookingComplete,
    BookingListResponse,
    PaymentCreate,
    PaymentResponse,
    CancellationCreate,
    CancellationResponse,
    CancellationApprove,
    BookingRequestFilters,
    BookingFilters
)
from app.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


# ============================================================================
# Booking Request Endpoints
# ============================================================================

@router.post(
    "/requests",
    response_model=BookingRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create booking request",
    description="Create a new booking request to a vendor for an event"
)
async def create_booking_request(
    request_data: BookingRequestCreate,
    event_id: str = Query(..., description="Event ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new booking request

    - **event_id**: Event for which booking is requested
    - **vendor_id**: Vendor to send request to
    - **title**: Brief title of request
    - **description**: Detailed description
    - **event_date**: Event date
    - **guest_count**: Estimated guest count
    - **budget_min/budget_max**: Budget range

    Returns created booking request
    """
    booking_service = BookingService(db)
    booking_request = await booking_service.create_booking_request(
        event_id,
        request_data,
        current_user
    )
    return BookingRequestResponse.from_orm(booking_request)


@router.get(
    "/requests/{request_id}",
    response_model=BookingRequestResponse,
    summary="Get booking request",
    description="Get booking request by ID"
)
async def get_booking_request(
    request_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get booking request details"""
    booking_service = BookingService(db)
    booking_request = await booking_service.get_booking_request(request_id, current_user)
    return BookingRequestResponse.from_orm(booking_request)


@router.put(
    "/requests/{request_id}",
    response_model=BookingRequestResponse,
    summary="Update booking request",
    description="Update booking request details"
)
async def update_booking_request(
    request_id: str,
    request_data: BookingRequestUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update booking request

    Only the organizer can update the request.
    Can only update if status is DRAFT or PENDING.
    """
    booking_service = BookingService(db)
    booking_request = await booking_service.update_booking_request(
        request_id,
        request_data,
        current_user
    )
    return BookingRequestResponse.from_orm(booking_request)


@router.get(
    "/requests/event/{event_id}",
    response_model=List[BookingRequestResponse],
    summary="Get event booking requests",
    description="Get all booking requests for an event"
)
async def get_event_booking_requests(
    event_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all booking requests for an event"""
    booking_service = BookingService(db)
    booking_requests = await booking_service.get_booking_requests_for_event(
        event_id,
        current_user
    )
    return [BookingRequestResponse.from_orm(br) for br in booking_requests]


@router.get(
    "/requests/vendor/{vendor_id}",
    response_model=BookingRequestListResponse,
    summary="Get vendor booking requests",
    description="Get booking requests for vendor with filters"
)
async def get_vendor_booking_requests(
    vendor_id: str,
    status: Optional[BookingRequestStatus] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    viewed_only: Optional[bool] = None,
    unviewed_only: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get booking requests for vendor

    Query parameters:
    - **status**: Filter by status
    - **from_date**: Filter by event date from
    - **to_date**: Filter by event date to
    - **viewed_only**: Show only viewed requests
    - **unviewed_only**: Show only unviewed requests
    - **page**: Page number
    - **page_size**: Items per page

    Returns paginated list of booking requests
    """
    filters = BookingRequestFilters(
        status=status,
        from_date=from_date,
        to_date=to_date,
        viewed_only=viewed_only,
        unviewed_only=unviewed_only
    )

    booking_service = BookingService(db)
    booking_requests, total = await booking_service.get_booking_requests_for_vendor(
        vendor_id,
        filters,
        page,
        page_size,
        current_user
    )

    return BookingRequestListResponse(
        booking_requests=[BookingRequestResponse.from_orm(br) for br in booking_requests],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.post(
    "/requests/{request_id}/viewed",
    response_model=BookingRequestResponse,
    summary="Mark request as viewed",
    description="Mark booking request as viewed by vendor"
)
async def mark_request_viewed(
    request_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark booking request as viewed by vendor"""
    booking_service = BookingService(db)
    booking_request = await booking_service.mark_request_as_viewed(request_id, current_user)
    return BookingRequestResponse.from_orm(booking_request)


# ============================================================================
# Quote Endpoints
# ============================================================================

@router.post(
    "/quotes",
    response_model=QuoteDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create quote",
    description="Create a quote in response to booking request"
)
async def create_quote(
    quote_data: QuoteCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a quote

    - **booking_request_id**: Related booking request
    - **items**: List of quote items (services/products)
    - **tax_rate**: Tax percentage
    - **deposit_percentage**: Deposit percentage required
    - **payment_terms**: Payment terms description
    - **cancellation_policy**: Cancellation policy
    - **terms_and_conditions**: Terms and conditions
    - **valid_days**: Number of days quote is valid

    Returns created quote with all items
    """
    booking_service = BookingService(db)
    quote = await booking_service.create_quote(quote_data, current_user)
    quote_with_items = await booking_service.get_quote(str(quote.id), current_user, load_items=True)
    return QuoteDetailResponse.from_orm(quote_with_items)


@router.get(
    "/quotes/{quote_id}",
    response_model=QuoteDetailResponse,
    summary="Get quote",
    description="Get quote by ID with all items"
)
async def get_quote(
    quote_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get quote details with all items"""
    booking_service = BookingService(db)
    quote = await booking_service.get_quote(quote_id, current_user, load_items=True)
    return QuoteDetailResponse.from_orm(quote)


@router.post(
    "/quotes/{quote_id}/send",
    response_model=QuoteResponse,
    summary="Send quote",
    description="Send quote to organizer"
)
async def send_quote(
    quote_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send quote to organizer

    Marks quote as SENT and updates booking request status to QUOTED.
    Only vendor can send quote.
    """
    booking_service = BookingService(db)
    quote = await booking_service.send_quote(quote_id, current_user)
    return QuoteResponse.from_orm(quote)


@router.post(
    "/quotes/{quote_id}/accept",
    response_model=BookingResponse,
    summary="Accept quote",
    description="Accept quote and create booking"
)
async def accept_quote(
    quote_id: str,
    accept_data: QuoteAccept,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept quote and create booking

    - **terms_accepted**: Must be true
    - **payment_method**: Preferred payment method

    Only organizer can accept quote.
    Creates a confirmed booking and returns it.
    """
    booking_service = BookingService(db)
    booking = await booking_service.accept_quote(quote_id, accept_data, current_user)
    return BookingResponse.from_orm(booking)


@router.post(
    "/quotes/{quote_id}/reject",
    response_model=QuoteResponse,
    summary="Reject quote",
    description="Reject a quote"
)
async def reject_quote(
    quote_id: str,
    reject_data: QuoteReject,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reject a quote

    - **rejection_reason**: Reason for rejection (required)

    Only organizer can reject quote.
    """
    booking_service = BookingService(db)
    quote = await booking_service.reject_quote(quote_id, reject_data, current_user)
    return QuoteResponse.from_orm(quote)


@router.get(
    "/quotes/request/{booking_request_id}",
    response_model=List[QuoteResponse],
    summary="Get quotes for request",
    description="Get all quotes for a booking request"
)
async def get_quotes_for_request(
    booking_request_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all quotes for a booking request"""
    booking_service = BookingService(db)
    quotes = await booking_service.get_quotes_for_request(booking_request_id, current_user)
    return [QuoteResponse.from_orm(q) for q in quotes]


# ============================================================================
# Booking Endpoints
# ============================================================================

@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Get booking",
    description="Get booking by ID"
)
async def get_booking(
    booking_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get booking details"""
    booking_service = BookingService(db)
    booking = await booking_service.get_booking(booking_id, current_user, load_relationships=True)
    return BookingResponse.from_orm(booking)


@router.put(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Update booking",
    description="Update booking details"
)
async def update_booking(
    booking_id: str,
    booking_data: BookingUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update booking details

    Only organizer can update booking.
    Can update venue details, guest count, and special requirements.
    """
    booking_service = BookingService(db)
    booking = await booking_service.update_booking(booking_id, booking_data, current_user)
    return BookingResponse.from_orm(booking)


@router.post(
    "/{booking_id}/complete",
    response_model=BookingResponse,
    summary="Complete booking",
    description="Mark booking as completed"
)
async def complete_booking(
    booking_id: str,
    complete_data: BookingComplete,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Complete a booking

    - **completion_notes**: Optional notes about completion

    Only vendor or admin can complete booking.
    Event date must have passed.
    """
    booking_service = BookingService(db)
    booking = await booking_service.complete_booking(booking_id, complete_data, current_user)
    return BookingResponse.from_orm(booking)


@router.get(
    "/event/{event_id}",
    response_model=List[BookingResponse],
    summary="Get event bookings",
    description="Get all bookings for an event"
)
async def get_event_bookings(
    event_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all bookings for an event"""
    booking_service = BookingService(db)
    bookings = await booking_service.get_bookings_for_event(event_id, current_user)
    return [BookingResponse.from_orm(b) for b in bookings]


@router.get(
    "/vendor/{vendor_id}",
    response_model=BookingListResponse,
    summary="Get vendor bookings",
    description="Get bookings for vendor with filters"
)
async def get_vendor_bookings(
    vendor_id: str,
    status: Optional[BookingStatus] = None,
    payment_status: Optional[PaymentStatus] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    completed_only: Optional[bool] = None,
    cancelled_only: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get bookings for vendor

    Query parameters:
    - **status**: Filter by booking status
    - **payment_status**: Filter by payment status
    - **from_date**: Filter by event date from
    - **to_date**: Filter by event date to
    - **completed_only**: Show only completed bookings
    - **cancelled_only**: Show only cancelled bookings
    - **page**: Page number
    - **page_size**: Items per page

    Returns paginated list of bookings
    """
    filters = BookingFilters(
        status=status,
        payment_status=payment_status,
        from_date=from_date,
        to_date=to_date,
        completed_only=completed_only,
        cancelled_only=cancelled_only
    )

    booking_service = BookingService(db)
    bookings, total = await booking_service.get_bookings_for_vendor(
        vendor_id,
        filters,
        page,
        page_size,
        current_user
    )

    return BookingListResponse(
        bookings=[BookingResponse.from_orm(b) for b in bookings],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


# ============================================================================
# Payment Endpoints
# ============================================================================

@router.post(
    "/{booking_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create payment",
    description="Create a payment for booking"
)
async def create_payment(
    booking_id: str,
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a payment

    - **amount**: Payment amount
    - **payment_method**: Payment method (CREDIT_CARD, BANK_TRANSFER, etc.)
    - **is_deposit**: Whether this is deposit payment
    - **notes**: Optional payment notes

    Only organizer can make payments.
    Payment amount cannot exceed amount due.

    Note: This creates a payment record. Actual payment processing
    happens through payment gateway integration.
    """
    booking_service = BookingService(db)
    payment = await booking_service.create_payment(booking_id, payment_data, current_user)
    return PaymentResponse.from_orm(payment)


# ============================================================================
# Cancellation Endpoints
# ============================================================================

@router.post(
    "/{booking_id}/cancel",
    response_model=CancellationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cancel booking",
    description="Cancel a booking"
)
async def cancel_booking(
    booking_id: str,
    cancellation_data: CancellationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a booking

    - **reason**: Cancellation reason (required, min 20 characters)
    - **reason_category**: Category (optional)
    - **organizer_notes**: Private organizer notes
    - **vendor_notes**: Private vendor notes

    Both organizer and vendor can cancel bookings.
    Refund amount is calculated based on cancellation policy and timing.
    Cannot cancel already cancelled or completed bookings.
    """
    booking_service = BookingService(db)
    cancellation = await booking_service.cancel_booking(
        booking_id,
        cancellation_data,
        current_user
    )
    return CancellationResponse.from_orm(cancellation)


@router.get(
    "/{booking_id}/cancellation",
    response_model=CancellationResponse,
    summary="Get cancellation details",
    description="Get cancellation details for a booking"
)
async def get_cancellation(
    booking_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get cancellation details"""
    booking_service = BookingService(db)
    booking = await booking_service.get_booking(booking_id, current_user, load_relationships=True)

    if not booking.cancellation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cancellation found for this booking"
        )

    return CancellationResponse.from_orm(booking.cancellation)


# ============================================================================
# Search and List Endpoints
# ============================================================================

@router.get(
    "/my/requests",
    response_model=BookingRequestListResponse,
    summary="Get my booking requests",
    description="Get current user's booking requests"
)
async def get_my_booking_requests(
    status: Optional[BookingRequestStatus] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's booking requests

    Returns all booking requests created by the current user.
    """
    # This would require a new repository method
    # For now, return empty list as placeholder
    return BookingRequestListResponse(
        booking_requests=[],
        total=0,
        page=page,
        page_size=page_size,
        has_more=False
    )


@router.get(
    "/my/bookings",
    response_model=BookingListResponse,
    summary="Get my bookings",
    description="Get current user's bookings"
)
async def get_my_bookings(
    status: Optional[BookingStatus] = None,
    payment_status: Optional[PaymentStatus] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's bookings

    Returns all bookings where the current user is the organizer.
    """
    # This would require a new repository method
    # For now, return empty list as placeholder
    return BookingListResponse(
        bookings=[],
        total=0,
        page=page,
        page_size=page_size,
        has_more=False
    )
