"""
CelebraTech Event Management System - Booking Models
Sprint 4: Booking & Quote System
FR-004: Booking & Quote Management
Database models for booking and quote system
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, Numeric, DateTime, Date, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


# ============================================================================
# Enumerations
# ============================================================================

class BookingRequestStatus(str, enum.Enum):
    """Status of booking request"""
    DRAFT = "DRAFT"  # Draft, not yet sent
    PENDING = "PENDING"  # Sent, awaiting vendor response
    QUOTED = "QUOTED"  # Vendor provided quote
    ACCEPTED = "ACCEPTED"  # Organizer accepted quote
    REJECTED = "REJECTED"  # Vendor rejected request
    EXPIRED = "EXPIRED"  # Request expired without response
    CANCELLED = "CANCELLED"  # Cancelled by organizer


class BookingStatus(str, enum.Enum):
    """Status of confirmed booking"""
    CONFIRMED = "CONFIRMED"  # Booking confirmed, awaiting event date
    IN_PROGRESS = "IN_PROGRESS"  # Event is happening
    COMPLETED = "COMPLETED"  # Event completed successfully
    CANCELLED = "CANCELLED"  # Booking cancelled


class PaymentStatus(str, enum.Enum):
    """Payment status"""
    PENDING = "PENDING"  # No payment yet
    DEPOSIT_PAID = "DEPOSIT_PAID"  # Deposit paid
    PARTIAL = "PARTIAL"  # Partial payment made
    PAID = "PAID"  # Fully paid
    REFUNDED = "REFUNDED"  # Refunded
    DISPUTED = "DISPUTED"  # Payment dispute


class CancellationInitiator(str, enum.Enum):
    """Who initiated cancellation"""
    ORGANIZER = "ORGANIZER"
    VENDOR = "VENDOR"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


class QuoteStatus(str, enum.Enum):
    """Quote status"""
    DRAFT = "DRAFT"  # Draft quote
    SENT = "SENT"  # Sent to organizer
    VIEWED = "VIEWED"  # Viewed by organizer
    ACCEPTED = "ACCEPTED"  # Accepted by organizer
    REJECTED = "REJECTED"  # Rejected by organizer
    EXPIRED = "EXPIRED"  # Expired
    REVISED = "REVISED"  # Revised by vendor


# ============================================================================
# Models
# ============================================================================

class BookingRequest(Base):
    """
    Booking request from event organizer to vendor
    Represents initial inquiry/request for services
    """
    __tablename__ = "booking_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    organizer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Request Details
    status = Column(SQLEnum(BookingRequestStatus), default=BookingRequestStatus.DRAFT, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # Event Information
    event_date = Column(DateTime(timezone=True), nullable=False)
    event_end_date = Column(DateTime(timezone=True))  # For multi-day events
    venue_name = Column(String(255))
    venue_address = Column(Text)
    guest_count = Column(Integer)

    # Service Requirements
    service_category = Column(String(100))
    specific_services = Column(JSONB)  # List of specific services needed
    special_requirements = Column(Text)

    # Budget
    budget_min = Column(Numeric(12, 2))
    budget_max = Column(Numeric(12, 2))
    currency = Column(String(3), default="TRY")

    # Timeline
    response_deadline = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))

    # Communication
    preferred_contact_method = Column(String(50))  # EMAIL, PHONE, WHATSAPP
    contact_notes = Column(Text)

    # Tracking
    viewed_by_vendor = Column(Boolean, default=False)
    viewed_at = Column(DateTime(timezone=True))
    responded_at = Column(DateTime(timezone=True))

    # Metadata
    metadata = Column(JSONB)  # Flexible data storage
    internal_notes = Column(Text)  # Private notes

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True))

    # Relationships
    event = relationship("Event", back_populates="booking_requests")
    vendor = relationship("Vendor", back_populates="booking_requests")
    organizer = relationship("User", foreign_keys=[organizer_id])
    quotes = relationship("Quote", back_populates="booking_request", cascade="all, delete-orphan")


class Quote(Base):
    """
    Vendor's quote in response to booking request
    Contains pricing, services, and terms
    """
    __tablename__ = "quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    booking_request_id = Column(UUID(as_uuid=True), ForeignKey("booking_requests.id"), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)

    # Quote Details
    status = Column(SQLEnum(QuoteStatus), default=QuoteStatus.DRAFT, nullable=False)
    quote_number = Column(String(50), unique=True, nullable=False)  # Q-2024-00001
    version = Column(Integer, default=1, nullable=False)  # For revisions

    # Pricing
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax_rate = Column(Numeric(5, 2), default=0)  # Tax percentage
    tax_amount = Column(Numeric(12, 2), default=0)
    discount_amount = Column(Numeric(12, 2), default=0)
    discount_reason = Column(String(255))
    total_amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="TRY")

    # Payment Terms
    deposit_percentage = Column(Numeric(5, 2), default=30)  # Default 30% deposit
    deposit_amount = Column(Numeric(12, 2))
    payment_terms = Column(Text)  # Payment schedule description

    # Service Details
    description = Column(Text)
    services_included = Column(JSONB)  # List of included services
    services_excluded = Column(JSONB)  # List of excluded services
    additional_notes = Column(Text)

    # Validity
    valid_until = Column(DateTime(timezone=True), nullable=False)

    # Terms & Conditions
    cancellation_policy = Column(Text)
    terms_and_conditions = Column(Text)

    # Customization Options
    is_customizable = Column(Boolean, default=True)
    customization_notes = Column(Text)

    # Tracking
    sent_at = Column(DateTime(timezone=True))
    viewed_at = Column(DateTime(timezone=True))
    accepted_at = Column(DateTime(timezone=True))
    rejected_at = Column(DateTime(timezone=True))

    # Rejection/Revision
    rejection_reason = Column(Text)
    revision_notes = Column(Text)
    previous_quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.id"))  # For revisions

    # Metadata
    metadata = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    booking_request = relationship("BookingRequest", back_populates="quotes")
    vendor = relationship("Vendor", back_populates="quotes")
    quote_items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan")
    booking = relationship("Booking", back_populates="quote", uselist=False)
    previous_quote = relationship("Quote", remote_side=[id], foreign_keys=[previous_quote_id])


class QuoteItem(Base):
    """
    Individual line item in a quote
    Represents a specific service or product
    """
    __tablename__ = "quote_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=False)
    vendor_service_id = Column(UUID(as_uuid=True), ForeignKey("vendor_services.id"))

    # Item Details
    item_name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))

    # Quantity & Pricing
    quantity = Column(Numeric(10, 2), default=1, nullable=False)
    unit = Column(String(50))  # PERSON, HOUR, DAY, ITEM
    unit_price = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)

    # Discount
    discount_percentage = Column(Numeric(5, 2), default=0)
    discount_amount = Column(Numeric(12, 2), default=0)
    total = Column(Numeric(12, 2), nullable=False)

    # Options
    is_optional = Column(Boolean, default=False)
    is_customizable = Column(Boolean, default=True)
    notes = Column(Text)

    # Display
    order_index = Column(Integer, default=0)

    # Metadata
    metadata = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    quote = relationship("Quote", back_populates="quote_items")
    vendor_service = relationship("VendorService")


class Booking(Base):
    """
    Confirmed booking between event organizer and vendor
    Created when quote is accepted
    """
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    booking_request_id = Column(UUID(as_uuid=True), ForeignKey("booking_requests.id"), nullable=False)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    organizer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Booking Details
    status = Column(SQLEnum(BookingStatus), default=BookingStatus.CONFIRMED, nullable=False)
    booking_number = Column(String(50), unique=True, nullable=False)  # B-2024-00001

    # Event Information (snapshot from request)
    event_date = Column(DateTime(timezone=True), nullable=False)
    event_end_date = Column(DateTime(timezone=True))
    venue_name = Column(String(255))
    venue_address = Column(Text)
    guest_count = Column(Integer)

    # Financial
    total_amount = Column(Numeric(12, 2), nullable=False)
    deposit_amount = Column(Numeric(12, 2), nullable=False)
    amount_paid = Column(Numeric(12, 2), default=0)
    amount_due = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="TRY")
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    # Commission (platform fee)
    commission_rate = Column(Numeric(5, 4), nullable=False)  # From vendor subscription
    commission_amount = Column(Numeric(12, 2), nullable=False)
    commission_paid = Column(Boolean, default=False)

    # Contract & Terms
    contract_signed = Column(Boolean, default=False)
    contract_signed_at = Column(DateTime(timezone=True))
    contract_url = Column(String(500))  # PDF contract document
    terms_accepted = Column(Boolean, default=False)
    terms_accepted_at = Column(DateTime(timezone=True))

    # Cancellation Policy
    cancellation_policy = Column(Text)
    is_refundable = Column(Boolean, default=True)
    refund_percentage = Column(Numeric(5, 2))  # % refundable based on timing

    # Service Delivery
    service_description = Column(Text)
    special_requirements = Column(Text)
    vendor_notes = Column(Text)  # Private vendor notes
    organizer_notes = Column(Text)  # Private organizer notes

    # Completion
    completed_at = Column(DateTime(timezone=True))
    completion_notes = Column(Text)

    # Review
    organizer_reviewed = Column(Boolean, default=False)
    vendor_reviewed = Column(Boolean, default=False)

    # Metadata
    metadata = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    cancelled_at = Column(DateTime(timezone=True))

    # Relationships
    booking_request = relationship("BookingRequest")
    quote = relationship("Quote", back_populates="booking")
    event = relationship("Event", back_populates="bookings")
    vendor = relationship("Vendor", back_populates="bookings")
    organizer = relationship("User", foreign_keys=[organizer_id])
    payments = relationship("BookingPayment", back_populates="booking", cascade="all, delete-orphan")
    cancellation = relationship("BookingCancellation", back_populates="booking", uselist=False, cascade="all, delete-orphan")


class BookingPayment(Base):
    """
    Payment record for a booking
    Tracks individual payments towards booking
    """
    __tablename__ = "booking_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # Who made payment

    # Payment Details
    payment_number = Column(String(50), unique=True, nullable=False)  # P-2024-00001
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="TRY")
    payment_method = Column(String(50))  # CREDIT_CARD, BANK_TRANSFER, CASH, etc.

    # Status
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    # Payment Gateway
    payment_gateway = Column(String(50))  # STRIPE, IYZICO, etc.
    gateway_transaction_id = Column(String(255))  # External transaction ID
    gateway_response = Column(JSONB)  # Full gateway response

    # Payment Type
    is_deposit = Column(Boolean, default=False)
    is_refund = Column(Boolean, default=False)
    refund_reason = Column(Text)
    original_payment_id = Column(UUID(as_uuid=True), ForeignKey("booking_payments.id"))  # For refunds

    # Dates
    payment_date = Column(DateTime(timezone=True))
    processed_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    refunded_at = Column(DateTime(timezone=True))

    # Failure Details
    failure_reason = Column(Text)
    failure_code = Column(String(50))

    # Notes
    notes = Column(Text)

    # Metadata
    metadata = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    booking = relationship("Booking", back_populates="payments")
    user = relationship("User")
    original_payment = relationship("BookingPayment", remote_side=[id], foreign_keys=[original_payment_id])


class BookingCancellation(Base):
    """
    Cancellation details for a booking
    Records who cancelled, why, and refund details
    """
    __tablename__ = "booking_cancellations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False, unique=True)
    cancelled_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Cancellation Details
    initiator = Column(SQLEnum(CancellationInitiator), nullable=False)
    reason = Column(Text, nullable=False)
    reason_category = Column(String(100))  # WEATHER, ILLNESS, VENDOR_ISSUE, etc.

    # Timing
    days_before_event = Column(Integer)  # How many days before event was cancelled
    cancellation_date = Column(DateTime(timezone=True), nullable=False)

    # Financial Impact
    refund_percentage = Column(Numeric(5, 2), nullable=False)
    refund_amount = Column(Numeric(12, 2), nullable=False)
    penalty_amount = Column(Numeric(12, 2), default=0)

    # Refund Processing
    refund_requested = Column(Boolean, default=False)
    refund_requested_at = Column(DateTime(timezone=True))
    refund_processed = Column(Boolean, default=False)
    refund_processed_at = Column(DateTime(timezone=True))
    refund_transaction_id = Column(String(255))

    # Mutual Agreement
    mutual_agreement = Column(Boolean, default=False)
    organizer_approved = Column(Boolean, default=False)
    vendor_approved = Column(Boolean, default=False)

    # Notes
    organizer_notes = Column(Text)
    vendor_notes = Column(Text)
    admin_notes = Column(Text)

    # Dispute
    disputed = Column(Boolean, default=False)
    dispute_reason = Column(Text)
    dispute_resolved = Column(Boolean, default=False)
    dispute_resolution = Column(Text)

    # Metadata
    metadata = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    booking = relationship("Booking", back_populates="cancellation")
    cancelled_by = relationship("User")


# Add indexes for better query performance
from sqlalchemy import Index

# BookingRequest indexes
Index('idx_booking_request_event', BookingRequest.event_id)
Index('idx_booking_request_vendor', BookingRequest.vendor_id)
Index('idx_booking_request_organizer', BookingRequest.organizer_id)
Index('idx_booking_request_status', BookingRequest.status)
Index('idx_booking_request_event_date', BookingRequest.event_date)

# Quote indexes
Index('idx_quote_request', Quote.booking_request_id)
Index('idx_quote_vendor', Quote.vendor_id)
Index('idx_quote_status', Quote.status)
Index('idx_quote_number', Quote.quote_number)

# Booking indexes
Index('idx_booking_event', Booking.event_id)
Index('idx_booking_vendor', Booking.vendor_id)
Index('idx_booking_organizer', Booking.organizer_id)
Index('idx_booking_status', Booking.status)
Index('idx_booking_payment_status', Booking.payment_status)
Index('idx_booking_event_date', Booking.event_date)
Index('idx_booking_number', Booking.booking_number)

# Payment indexes
Index('idx_payment_booking', BookingPayment.booking_id)
Index('idx_payment_user', BookingPayment.user_id)
Index('idx_payment_status', BookingPayment.status)
Index('idx_payment_number', BookingPayment.payment_number)
