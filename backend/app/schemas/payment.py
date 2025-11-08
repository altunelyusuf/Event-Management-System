"""
CelebraTech Event Management System - Payment Schemas
Sprint 5: Payment Gateway Integration & Financial Management
FR-005: Payment Processing & Financial Management
Pydantic schemas for payment data validation
"""
from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List, Dict
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from app.models.payment import (
    PaymentGatewayType,
    TransactionType,
    TransactionStatus,
    RefundStatus,
    PayoutStatus,
    InvoiceStatus,
    PaymentMethodType
)


# ============================================================================
# Payment Processing Schemas
# ============================================================================

class PaymentIntentCreate(BaseModel):
    """Schema for creating payment intent"""
    booking_id: UUID
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("TRY", max_length=3)
    payment_method_id: Optional[str] = None  # Saved payment method
    save_payment_method: bool = False
    return_url: Optional[str] = None


class PaymentConfirm(BaseModel):
    """Schema for confirming payment"""
    payment_intent_id: str


class TransactionResponse(BaseModel):
    """Response schema for transaction"""
    id: UUID
    transaction_number: str
    booking_id: UUID
    transaction_type: TransactionType
    status: TransactionStatus
    amount: Decimal
    currency: str
    platform_fee: Decimal
    gateway_fee: Decimal
    net_amount: Decimal
    gateway_type: PaymentGatewayType
    payment_method_type: Optional[PaymentMethodType]
    payment_method_last4: Optional[str]
    payment_method_brand: Optional[str]
    three_d_secure_used: bool
    created_at: datetime
    captured_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Refund Schemas
# ============================================================================

class RefundCreate(BaseModel):
    """Schema for creating refund"""
    transaction_id: UUID
    amount: Decimal = Field(..., gt=0)
    reason: str = Field(..., max_length=50)
    description: Optional[str] = None
    refund_gateway_fee: bool = False


class RefundResponse(BaseModel):
    """Response schema for refund"""
    id: UUID
    refund_number: str
    transaction_id: UUID
    booking_id: UUID
    status: RefundStatus
    amount: Decimal
    currency: str
    gateway_fee_refunded: Decimal
    reason: str
    description: Optional[str]
    requested_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Invoice Schemas
# ============================================================================

class InvoiceLineItem(BaseModel):
    """Invoice line item"""
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal


class InvoiceGenerate(BaseModel):
    """Schema for generating invoice"""
    booking_id: UUID
    due_days: int = Field(30, ge=1, le=90)
    payment_terms: Optional[str] = None
    notes: Optional[str] = None


class InvoiceResponse(BaseModel):
    """Response schema for invoice"""
    id: UUID
    invoice_number: str
    booking_id: UUID
    status: InvoiceStatus
    issue_date: date
    due_date: date
    paid_date: Optional[date]
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    currency: str
    customer_name: str
    vendor_name: str
    pdf_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Payout Schemas
# ============================================================================

class PayoutCreate(BaseModel):
    """Schema for creating payout"""
    vendor_id: UUID
    period_start: date
    period_end: date


class PayoutResponse(BaseModel):
    """Response schema for payout"""
    id: UUID
    payout_number: str
    vendor_id: UUID
    status: PayoutStatus
    gross_amount: Decimal
    commission_amount: Decimal
    net_amount: Decimal
    currency: str
    period_start: date
    period_end: date
    booking_count: int
    scheduled_at: Optional[datetime]
    processed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Saved Payment Method Schemas
# ============================================================================

class PaymentMethodSave(BaseModel):
    """Schema for saving payment method"""
    gateway_payment_method_id: str
    gateway_type: PaymentGatewayType
    set_as_default: bool = False


class PaymentMethodResponse(BaseModel):
    """Response schema for saved payment method"""
    id: UUID
    method_type: PaymentMethodType
    is_default: bool
    card_last4: Optional[str]
    card_brand: Optional[str]
    card_exp_month: Optional[int]
    card_exp_year: Optional[int]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Gateway Configuration Schemas
# ============================================================================

class GatewayConfigCreate(BaseModel):
    """Schema for creating gateway config"""
    gateway_type: PaymentGatewayType
    api_key: str
    secret_key: str
    webhook_secret: Optional[str] = None
    is_test_mode: bool = True
    payout_enabled: bool = False


class GatewayConfigResponse(BaseModel):
    """Response schema for gateway config"""
    id: UUID
    vendor_id: UUID
    gateway_type: PaymentGatewayType
    is_active: bool
    is_test_mode: bool
    payout_enabled: bool
    created_at: datetime
    verified_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Statistics Schemas
# ============================================================================

class PaymentStatistics(BaseModel):
    """Payment statistics"""
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    total_revenue: Decimal
    total_refunded: Decimal
    platform_fees: Decimal
    gateway_fees: Decimal
    success_rate: Decimal


class VendorPayoutStatistics(BaseModel):
    """Vendor payout statistics"""
    total_payouts: int
    total_paid: Decimal
    total_pending: Decimal
    average_payout: Decimal
    last_payout_date: Optional[date]
