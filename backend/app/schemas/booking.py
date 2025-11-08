"""
CelebraTech Event Management System - Booking Schemas
Sprint 4: Booking & Quote System
FR-004: Booking & Quote Management
Pydantic schemas for booking data validation
"""
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from app.models.booking import (
    BookingRequestStatus,
    BookingStatus,
    PaymentStatus,
    CancellationInitiator,
    QuoteStatus
)


# ============================================================================
# Booking Request Schemas
# ============================================================================

class BookingRequestBase(BaseModel):
    """Base booking request schema"""
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=20)
    event_date: datetime
    event_end_date: Optional[datetime] = None
    venue_name: Optional[str] = Field(None, max_length=255)
    venue_address: Optional[str] = None
    guest_count: Optional[int] = Field(None, gt=0)
    service_category: Optional[str] = Field(None, max_length=100)
    special_requirements: Optional[str] = None
    budget_min: Optional[Decimal] = Field(None, ge=0)
    budget_max: Optional[Decimal] = Field(None, ge=0)
    preferred_contact_method: Optional[str] = Field("EMAIL", max_length=50)
    contact_notes: Optional[str] = None

    @validator('event_date')
    def validate_event_date(cls, v):
        if v < datetime.utcnow():
            raise ValueError('Event date must be in the future')
        return v

    @validator('event_end_date')
    def validate_end_date(cls, v, values):
        if v and 'event_date' in values and v < values['event_date']:
            raise ValueError('End date must be after start date')
        return v

    @validator('budget_max')
    def validate_budget_range(cls, v, values):
        if v and 'budget_min' in values and values['budget_min']:
            if v < values['budget_min']:
                raise ValueError('Maximum budget must be greater than minimum')
        return v


class BookingRequestCreate(BookingRequestBase):
    """Schema for creating booking request"""
    vendor_id: UUID
    specific_services: Optional[List[str]] = Field(default_factory=list)
    response_deadline: Optional[datetime] = None


class BookingRequestUpdate(BaseModel):
    """Schema for updating booking request"""
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=20)
    event_date: Optional[datetime] = None
    event_end_date: Optional[datetime] = None
    venue_name: Optional[str] = Field(None, max_length=255)
    venue_address: Optional[str] = None
    guest_count: Optional[int] = Field(None, gt=0)
    special_requirements: Optional[str] = None
    budget_min: Optional[Decimal] = Field(None, ge=0)
    budget_max: Optional[Decimal] = Field(None, ge=0)


class BookingRequestResponse(BookingRequestBase):
    """Response schema for booking request"""
    id: UUID
    event_id: UUID
    vendor_id: UUID
    organizer_id: UUID
    status: BookingRequestStatus
    currency: str
    viewed_by_vendor: bool
    viewed_at: Optional[datetime]
    responded_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Quote Item Schemas
# ============================================================================

class QuoteItemBase(BaseModel):
    """Base quote item schema"""
    item_name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    quantity: Decimal = Field(..., gt=0)
    unit: Optional[str] = Field(None, max_length=50)
    unit_price: Decimal = Field(..., ge=0)
    discount_percentage: Decimal = Field(0, ge=0, le=100)
    is_optional: bool = False
    is_customizable: bool = True
    notes: Optional[str] = None


class QuoteItemCreate(QuoteItemBase):
    """Schema for creating quote item"""
    vendor_service_id: Optional[UUID] = None


class QuoteItemUpdate(BaseModel):
    """Schema for updating quote item"""
    item_name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    is_optional: Optional[bool] = None
    notes: Optional[str] = None


class QuoteItemResponse(QuoteItemBase):
    """Response schema for quote item"""
    id: UUID
    quote_id: UUID
    vendor_service_id: Optional[UUID]
    subtotal: Decimal
    discount_amount: Decimal
    total: Decimal
    order_index: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Quote Schemas
# ============================================================================

class QuoteBase(BaseModel):
    """Base quote schema"""
    description: Optional[str] = None
    deposit_percentage: Decimal = Field(30, ge=0, le=100)
    payment_terms: Optional[str] = None
    cancellation_policy: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    additional_notes: Optional[str] = None
    is_customizable: bool = True
    customization_notes: Optional[str] = None


class QuoteCreate(QuoteBase):
    """Schema for creating quote"""
    booking_request_id: UUID
    items: List[QuoteItemCreate] = Field(..., min_items=1)
    tax_rate: Decimal = Field(0, ge=0, le=100)
    discount_amount: Decimal = Field(0, ge=0)
    discount_reason: Optional[str] = Field(None, max_length=255)
    valid_days: int = Field(7, gt=0, le=90)


class QuoteUpdate(BaseModel):
    """Schema for updating quote (vendor can revise)"""
    description: Optional[str] = None
    tax_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    discount_reason: Optional[str] = Field(None, max_length=255)
    deposit_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    payment_terms: Optional[str] = None
    cancellation_policy: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    additional_notes: Optional[str] = None
    revision_notes: Optional[str] = None


class QuoteResponse(QuoteBase):
    """Response schema for quote"""
    id: UUID
    booking_request_id: UUID
    vendor_id: UUID
    status: QuoteStatus
    quote_number: str
    version: int
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    discount_reason: Optional[str]
    total_amount: Decimal
    currency: str
    deposit_amount: Decimal
    valid_until: datetime
    services_included: Optional[List]
    services_excluded: Optional[List]
    sent_at: Optional[datetime]
    viewed_at: Optional[datetime]
    accepted_at: Optional[datetime]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    previous_quote_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuoteDetailResponse(QuoteResponse):
    """Detailed quote response with items"""
    quote_items: List[QuoteItemResponse] = []

    class Config:
        from_attributes = True


class QuoteAccept(BaseModel):
    """Schema for accepting a quote"""
    terms_accepted: bool = Field(..., description="Must accept terms and conditions")
    payment_method: Optional[str] = Field(None, max_length=50)

    @validator('terms_accepted')
    def validate_acceptance(cls, v):
        if not v:
            raise ValueError('Terms and conditions must be accepted')
        return v


class QuoteReject(BaseModel):
    """Schema for rejecting a quote"""
    rejection_reason: str = Field(..., min_length=10)


# ============================================================================
# Booking Schemas
# ============================================================================

class BookingResponse(BaseModel):
    """Response schema for booking"""
    id: UUID
    booking_request_id: UUID
    quote_id: UUID
    event_id: UUID
    vendor_id: UUID
    organizer_id: UUID
    status: BookingStatus
    booking_number: str
    event_date: datetime
    event_end_date: Optional[datetime]
    venue_name: Optional[str]
    venue_address: Optional[str]
    guest_count: Optional[int]
    total_amount: Decimal
    deposit_amount: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    currency: str
    payment_status: PaymentStatus
    commission_rate: Decimal
    commission_amount: Decimal
    commission_paid: bool
    contract_signed: bool
    contract_signed_at: Optional[datetime]
    contract_url: Optional[str]
    terms_accepted: bool
    terms_accepted_at: Optional[datetime]
    cancellation_policy: Optional[str]
    is_refundable: bool
    refund_percentage: Optional[Decimal]
    service_description: Optional[str]
    special_requirements: Optional[str]
    completed_at: Optional[datetime]
    organizer_reviewed: bool
    vendor_reviewed: bool
    created_at: datetime
    updated_at: datetime
    cancelled_at: Optional[datetime]

    class Config:
        from_attributes = True


class BookingUpdate(BaseModel):
    """Schema for updating booking"""
    venue_name: Optional[str] = Field(None, max_length=255)
    venue_address: Optional[str] = None
    guest_count: Optional[int] = Field(None, gt=0)
    special_requirements: Optional[str] = None
    vendor_notes: Optional[str] = None
    organizer_notes: Optional[str] = None


class BookingComplete(BaseModel):
    """Schema for completing a booking"""
    completion_notes: Optional[str] = None


# ============================================================================
# Payment Schemas
# ============================================================================

class PaymentCreate(BaseModel):
    """Schema for creating payment"""
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field(..., max_length=50)
    is_deposit: bool = False
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    """Response schema for payment"""
    id: UUID
    booking_id: UUID
    user_id: UUID
    payment_number: str
    amount: Decimal
    currency: str
    payment_method: str
    status: PaymentStatus
    payment_gateway: Optional[str]
    gateway_transaction_id: Optional[str]
    is_deposit: bool
    is_refund: bool
    refund_reason: Optional[str]
    original_payment_id: Optional[UUID]
    payment_date: Optional[datetime]
    processed_at: Optional[datetime]
    failed_at: Optional[datetime]
    refunded_at: Optional[datetime]
    failure_reason: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Cancellation Schemas
# ============================================================================

class CancellationCreate(BaseModel):
    """Schema for cancelling booking"""
    reason: str = Field(..., min_length=20)
    reason_category: Optional[str] = Field(None, max_length=100)
    organizer_notes: Optional[str] = None
    vendor_notes: Optional[str] = None


class CancellationResponse(BaseModel):
    """Response schema for cancellation"""
    id: UUID
    booking_id: UUID
    cancelled_by_user_id: UUID
    initiator: CancellationInitiator
    reason: str
    reason_category: Optional[str]
    days_before_event: Optional[int]
    cancellation_date: datetime
    refund_percentage: Decimal
    refund_amount: Decimal
    penalty_amount: Decimal
    refund_requested: bool
    refund_requested_at: Optional[datetime]
    refund_processed: bool
    refund_processed_at: Optional[datetime]
    refund_transaction_id: Optional[str]
    mutual_agreement: bool
    organizer_approved: bool
    vendor_approved: bool
    organizer_notes: Optional[str]
    vendor_notes: Optional[str]
    admin_notes: Optional[str]
    disputed: bool
    dispute_reason: Optional[str]
    dispute_resolved: bool
    dispute_resolution: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CancellationApprove(BaseModel):
    """Schema for approving cancellation"""
    approved: bool
    notes: Optional[str] = None


# ============================================================================
# Search and Filter Schemas
# ============================================================================

class BookingRequestFilters(BaseModel):
    """Filters for booking request search"""
    status: Optional[BookingRequestStatus] = None
    event_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    viewed_only: Optional[bool] = None
    unviewed_only: Optional[bool] = None


class BookingFilters(BaseModel):
    """Filters for booking search"""
    status: Optional[BookingStatus] = None
    payment_status: Optional[PaymentStatus] = None
    event_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    completed_only: Optional[bool] = None
    cancelled_only: Optional[bool] = None


class BookingListResponse(BaseModel):
    """Response schema for booking list with pagination"""
    bookings: List[BookingResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class BookingRequestListResponse(BaseModel):
    """Response schema for booking request list with pagination"""
    booking_requests: List[BookingRequestResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class QuoteListResponse(BaseModel):
    """Response schema for quote list with pagination"""
    quotes: List[QuoteResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# ============================================================================
# Statistics Schemas
# ============================================================================

class BookingStatistics(BaseModel):
    """Schema for booking statistics"""
    total_bookings: int
    confirmed_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    total_revenue: Decimal
    revenue_pending: Decimal
    revenue_received: Decimal
    average_booking_value: Decimal
    completion_rate: Decimal
    cancellation_rate: Decimal

    # Time-based stats
    bookings_this_month: int
    revenue_this_month: Decimal
    bookings_this_year: int
    revenue_this_year: Decimal

    # Upcoming
    upcoming_bookings: int
    upcoming_revenue: Decimal


class VendorBookingStatistics(BookingStatistics):
    """Vendor-specific booking statistics"""
    pending_requests: int
    pending_quotes: int
    response_rate: Decimal
    average_response_time_hours: Decimal
    commission_total: Decimal
    commission_paid: Decimal
    commission_pending: Decimal


class OrganizerBookingStatistics(BookingStatistics):
    """Organizer-specific booking statistics"""
    active_requests: int
    pending_quotes: int
    events_with_bookings: int
    average_vendors_per_event: Decimal


# ============================================================================
# Dashboard Schemas
# ============================================================================

class BookingDashboard(BaseModel):
    """Dashboard overview for bookings"""
    statistics: BookingStatistics
    recent_bookings: List[BookingResponse]
    upcoming_events: List[BookingResponse]
    pending_actions: int
    notifications: int


# ============================================================================
# Notification Schemas
# ============================================================================

class BookingNotification(BaseModel):
    """Schema for booking-related notifications"""
    type: str  # NEW_REQUEST, QUOTE_RECEIVED, BOOKING_CONFIRMED, etc.
    booking_id: Optional[UUID]
    booking_request_id: Optional[UUID]
    quote_id: Optional[UUID]
    title: str
    message: str
    action_url: Optional[str]
    created_at: datetime
