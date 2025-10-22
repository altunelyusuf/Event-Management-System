"""
CelebraTech Event Management System - Payment Models
Sprint 5: Payment Gateway Integration & Financial Management
FR-005: Payment Processing & Financial Management
Database models for payment gateway integration
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

class PaymentGatewayType(str, enum.Enum):
    """Payment gateway types"""
    STRIPE = "STRIPE"
    IYZICO = "IYZICO"
    PAYPAL = "PAYPAL"
    BANK_TRANSFER = "BANK_TRANSFER"
    CASH = "CASH"


class TransactionType(str, enum.Enum):
    """Transaction types"""
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
    PAYOUT = "PAYOUT"
    COMMISSION = "COMMISSION"
    ADJUSTMENT = "ADJUSTMENT"


class TransactionStatus(str, enum.Enum):
    """Transaction status"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class RefundStatus(str, enum.Enum):
    """Refund status"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DisputeStatus(str, enum.Enum):
    """Payment dispute status"""
    OPENED = "OPENED"
    UNDER_REVIEW = "UNDER_REVIEW"
    EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"
    WON = "WON"
    LOST = "LOST"
    CLOSED = "CLOSED"


class PayoutStatus(str, enum.Enum):
    """Payout status for vendors"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class InvoiceStatus(str, enum.Enum):
    """Invoice status"""
    DRAFT = "DRAFT"
    SENT = "SENT"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentMethodType(str, enum.Enum):
    """Saved payment method types"""
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    BANK_ACCOUNT = "BANK_ACCOUNT"


# ============================================================================
# Models
# ============================================================================

class PaymentGatewayConfig(Base):
    """
    Payment gateway configuration for vendors
    Stores API keys and settings for each gateway
    """
    __tablename__ = "payment_gateway_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)

    # Gateway Details
    gateway_type = Column(SQLEnum(PaymentGatewayType), nullable=False)
    is_active = Column(Boolean, default=False)
    is_test_mode = Column(Boolean, default=True)

    # Credentials (encrypted)
    api_key = Column(Text)  # Encrypted
    secret_key = Column(Text)  # Encrypted
    webhook_secret = Column(Text)  # Encrypted
    merchant_id = Column(String(255))

    # Configuration
    config = Column(JSONB)  # Additional gateway-specific settings

    # Payout Settings
    payout_enabled = Column(Boolean, default=False)
    payout_schedule = Column(String(50))  # DAILY, WEEKLY, MONTHLY
    minimum_payout_amount = Column(Numeric(12, 2), default=100)

    # Metadata
    metadata = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    verified_at = Column(DateTime(timezone=True))

    # Relationships
    vendor = relationship("Vendor")


class PaymentTransaction(Base):
    """
    Payment transaction record
    More detailed than BookingPayment - tracks gateway-specific details
    """
    __tablename__ = "payment_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    booking_payment_id = Column(UUID(as_uuid=True), ForeignKey("booking_payments.id"))
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)

    # Transaction Details
    transaction_type = Column(SQLEnum(TransactionType), default=TransactionType.PAYMENT, nullable=False)
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)
    transaction_number = Column(String(50), unique=True, nullable=False)  # TXN-2024-00001

    # Amount
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="TRY")

    # Fee Breakdown
    platform_fee = Column(Numeric(12, 2), default=0)
    gateway_fee = Column(Numeric(12, 2), default=0)
    net_amount = Column(Numeric(12, 2), nullable=False)  # Amount - fees

    # Gateway Information
    gateway_type = Column(SQLEnum(PaymentGatewayType), nullable=False)
    gateway_transaction_id = Column(String(255))
    gateway_payment_intent_id = Column(String(255))
    gateway_customer_id = Column(String(255))
    gateway_response = Column(JSONB)

    # Payment Method
    payment_method_type = Column(SQLEnum(PaymentMethodType))
    payment_method_last4 = Column(String(4))
    payment_method_brand = Column(String(50))  # VISA, MASTERCARD, etc.
    payment_method_country = Column(String(2))

    # 3D Secure
    three_d_secure_used = Column(Boolean, default=False)
    three_d_secure_result = Column(String(50))

    # Dates
    initiated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    authorized_at = Column(DateTime(timezone=True))
    captured_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    refunded_at = Column(DateTime(timezone=True))

    # Failure Details
    failure_code = Column(String(100))
    failure_message = Column(Text)
    decline_reason = Column(String(255))

    # Risk Assessment
    risk_score = Column(Numeric(5, 2))
    risk_level = Column(String(20))  # LOW, MEDIUM, HIGH
    fraud_detected = Column(Boolean, default=False)

    # Customer Information
    customer_ip = Column(String(45))
    customer_email = Column(String(255))
    customer_phone = Column(String(20))

    # Billing Address
    billing_address = Column(JSONB)

    # Metadata
    metadata = Column(JSONB)
    internal_notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    booking_payment = relationship("BookingPayment")
    booking = relationship("Booking")
    user = relationship("User", foreign_keys=[user_id])
    vendor = relationship("Vendor")
    refunds = relationship("PaymentRefund", back_populates="transaction", cascade="all, delete-orphan")


class PaymentRefund(Base):
    """
    Payment refund record
    Tracks refunds issued for payments
    """
    __tablename__ = "payment_refunds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("payment_transactions.id"), nullable=False)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    cancellation_id = Column(UUID(as_uuid=True), ForeignKey("booking_cancellations.id"))

    # Refund Details
    status = Column(SQLEnum(RefundStatus), default=RefundStatus.PENDING, nullable=False)
    refund_number = Column(String(50), unique=True, nullable=False)  # RFD-2024-00001

    # Amount
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="TRY")

    # Fee Handling
    refund_gateway_fee = Column(Boolean, default=False)
    gateway_fee_refunded = Column(Numeric(12, 2), default=0)

    # Gateway Information
    gateway_type = Column(SQLEnum(PaymentGatewayType), nullable=False)
    gateway_refund_id = Column(String(255))
    gateway_response = Column(JSONB)

    # Reason
    reason = Column(String(50))  # REQUESTED_BY_CUSTOMER, DUPLICATE, FRAUDULENT
    description = Column(Text)

    # Processing
    requested_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    processed_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))

    # Failure Details
    failure_reason = Column(Text)

    # Metadata
    metadata = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    transaction = relationship("PaymentTransaction", back_populates="refunds")
    booking = relationship("Booking")
    cancellation = relationship("BookingCancellation")


class PaymentDispute(Base):
    """
    Payment dispute/chargeback record
    Tracks disputes raised by customers
    """
    __tablename__ = "payment_disputes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("payment_transactions.id"), nullable=False)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)

    # Dispute Details
    status = Column(SQLEnum(DisputeStatus), default=DisputeStatus.OPENED, nullable=False)
    dispute_number = Column(String(50), unique=True, nullable=False)  # DSP-2024-00001

    # Amount
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="TRY")

    # Gateway Information
    gateway_type = Column(SQLEnum(PaymentGatewayType), nullable=False)
    gateway_dispute_id = Column(String(255))
    gateway_response = Column(JSONB)

    # Dispute Reason
    reason = Column(String(100))  # FRAUDULENT, UNRECOGNIZED, DUPLICATE, etc.
    customer_message = Column(Text)

    # Evidence
    evidence_submitted = Column(Boolean, default=False)
    evidence_due_by = Column(DateTime(timezone=True))
    evidence_details = Column(JSONB)  # Documents, shipping info, etc.

    # Resolution
    resolution = Column(String(50))  # WON, LOST, ACCEPTED
    resolution_reason = Column(Text)
    resolved_at = Column(DateTime(timezone=True))

    # Dates
    opened_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    responded_at = Column(DateTime(timezone=True))

    # Metadata
    metadata = Column(JSONB)
    internal_notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    transaction = relationship("PaymentTransaction")
    booking = relationship("Booking")


class VendorPayout(Base):
    """
    Vendor payout record
    Tracks payments made to vendors
    """
    __tablename__ = "vendor_payouts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)

    # Payout Details
    status = Column(SQLEnum(PayoutStatus), default=PayoutStatus.PENDING, nullable=False)
    payout_number = Column(String(50), unique=True, nullable=False)  # PO-2024-00001

    # Amount
    gross_amount = Column(Numeric(12, 2), nullable=False)  # Total bookings amount
    commission_amount = Column(Numeric(12, 2), nullable=False)  # Platform commission
    net_amount = Column(Numeric(12, 2), nullable=False)  # Amount paid to vendor
    currency = Column(String(3), default="TRY")

    # Gateway Information
    gateway_type = Column(SQLEnum(PaymentGatewayType))
    gateway_payout_id = Column(String(255))
    gateway_response = Column(JSONB)

    # Period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Booking Count
    booking_count = Column(Integer, default=0)

    # Bank Details (snapshot at payout time)
    bank_account_info = Column(JSONB)  # Encrypted

    # Processing
    scheduled_at = Column(DateTime(timezone=True))
    processed_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))

    # Failure Details
    failure_reason = Column(Text)

    # Metadata
    metadata = Column(JSONB)
    internal_notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    vendor = relationship("Vendor")
    payout_items = relationship("PayoutItem", back_populates="payout", cascade="all, delete-orphan")


class PayoutItem(Base):
    """
    Individual booking in a payout
    Links bookings to vendor payouts
    """
    __tablename__ = "payout_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    payout_id = Column(UUID(as_uuid=True), ForeignKey("vendor_payouts.id"), nullable=False)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)

    # Amount
    booking_amount = Column(Numeric(12, 2), nullable=False)
    commission_amount = Column(Numeric(12, 2), nullable=False)
    net_amount = Column(Numeric(12, 2), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    payout = relationship("VendorPayout", back_populates="payout_items")
    booking = relationship("Booking")


class Invoice(Base):
    """
    Invoice for bookings
    Generated for customer records
    """
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)

    # Invoice Details
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    invoice_number = Column(String(50), unique=True, nullable=False)  # INV-2024-00001

    # Dates
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date)

    # Amounts
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0)
    discount_amount = Column(Numeric(12, 2), default=0)
    total_amount = Column(Numeric(12, 2), nullable=False)
    amount_paid = Column(Numeric(12, 2), default=0)
    amount_due = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="TRY")

    # Tax Details
    tax_rate = Column(Numeric(5, 2))
    tax_id = Column(String(50))  # Vendor tax ID

    # Line Items
    line_items = Column(JSONB)  # Array of invoice line items

    # Customer Details (snapshot)
    customer_name = Column(String(255))
    customer_email = Column(String(255))
    customer_phone = Column(String(20))
    customer_address = Column(JSONB)

    # Vendor Details (snapshot)
    vendor_name = Column(String(255))
    vendor_email = Column(String(255))
    vendor_phone = Column(String(20))
    vendor_address = Column(JSONB)
    vendor_tax_id = Column(String(50))

    # Payment Terms
    payment_terms = Column(Text)
    notes = Column(Text)

    # PDF
    pdf_url = Column(String(500))
    pdf_generated_at = Column(DateTime(timezone=True))

    # Metadata
    metadata = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime(timezone=True))

    # Relationships
    booking = relationship("Booking")
    user = relationship("User", foreign_keys=[user_id])
    vendor = relationship("Vendor")


class SavedPaymentMethod(Base):
    """
    Saved payment method for users
    Tokenized payment methods for faster checkout
    """
    __tablename__ = "saved_payment_methods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Payment Method Details
    method_type = Column(SQLEnum(PaymentMethodType), nullable=False)
    is_default = Column(Boolean, default=False)

    # Gateway Information
    gateway_type = Column(SQLEnum(PaymentGatewayType), nullable=False)
    gateway_customer_id = Column(String(255))
    gateway_payment_method_id = Column(String(255), nullable=False)

    # Card Details (for display only, not for processing)
    card_last4 = Column(String(4))
    card_brand = Column(String(50))  # VISA, MASTERCARD
    card_exp_month = Column(Integer)
    card_exp_year = Column(Integer)
    card_country = Column(String(2))

    # Bank Account Details (for display only)
    bank_name = Column(String(255))
    account_last4 = Column(String(4))

    # Billing Address
    billing_address = Column(JSONB)

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Metadata
    metadata = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User")


# Add indexes for better query performance
from sqlalchemy import Index

# PaymentTransaction indexes
Index('idx_payment_txn_booking', PaymentTransaction.booking_id)
Index('idx_payment_txn_user', PaymentTransaction.user_id)
Index('idx_payment_txn_vendor', PaymentTransaction.vendor_id)
Index('idx_payment_txn_status', PaymentTransaction.status)
Index('idx_payment_txn_number', PaymentTransaction.transaction_number)
Index('idx_payment_txn_gateway_id', PaymentTransaction.gateway_transaction_id)

# PaymentRefund indexes
Index('idx_refund_transaction', PaymentRefund.transaction_id)
Index('idx_refund_booking', PaymentRefund.booking_id)
Index('idx_refund_status', PaymentRefund.status)
Index('idx_refund_number', PaymentRefund.refund_number)

# VendorPayout indexes
Index('idx_payout_vendor', VendorPayout.vendor_id)
Index('idx_payout_status', VendorPayout.status)
Index('idx_payout_number', VendorPayout.payout_number)
Index('idx_payout_period', VendorPayout.period_start, VendorPayout.period_end)

# Invoice indexes
Index('idx_invoice_booking', Invoice.booking_id)
Index('idx_invoice_user', Invoice.user_id)
Index('idx_invoice_vendor', Invoice.vendor_id)
Index('idx_invoice_status', Invoice.status)
Index('idx_invoice_number', Invoice.invoice_number)
Index('idx_invoice_due_date', Invoice.due_date)
