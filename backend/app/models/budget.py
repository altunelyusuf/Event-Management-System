"""
Budget Management Models
Sprint 15: Budget Management System

Database models for budget planning, expense tracking,
cost forecasting, and financial management.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    Text, ForeignKey, JSON, Index, UniqueConstraint, ARRAY, Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


# ============================================================================
# Enums
# ============================================================================

class BudgetStatus(str, enum.Enum):
    """Budget status"""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXCEEDED = "exceeded"
    CANCELLED = "cancelled"


class ExpenseStatus(str, enum.Enum):
    """Expense status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"
    CANCELLED = "cancelled"


class ExpenseType(str, enum.Enum):
    """Expense types"""
    VENDOR_PAYMENT = "vendor_payment"
    VENUE = "venue"
    CATERING = "catering"
    DECORATION = "decoration"
    ENTERTAINMENT = "entertainment"
    PHOTOGRAPHY = "photography"
    TRANSPORTATION = "transportation"
    ACCOMMODATION = "accommodation"
    MARKETING = "marketing"
    STAFF = "staff"
    EQUIPMENT = "equipment"
    SUPPLIES = "supplies"
    MISC = "misc"
    OTHER = "other"


class BudgetAlertType(str, enum.Enum):
    """Budget alert types"""
    THRESHOLD_WARNING = "threshold_warning"
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    CATEGORY_EXCEEDED = "category_exceeded"
    FORECAST_OVERRUN = "forecast_overrun"
    PAYMENT_DUE = "payment_due"


class CurrencyCode(str, enum.Enum):
    """Supported currency codes"""
    TRY = "TRY"  # Turkish Lira
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound


# ============================================================================
# Budget Models
# ============================================================================

class Budget(Base):
    """
    Event budget with planning and tracking.

    Manages overall event budget with categories,
    allocation, and actual expense tracking.
    """
    __tablename__ = "budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Event reference
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)

    # Budget details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Amounts
    total_budget = Column(Numeric(12, 2), nullable=False)
    allocated_amount = Column(Numeric(12, 2), default=0)
    spent_amount = Column(Numeric(12, 2), default=0)
    pending_amount = Column(Numeric(12, 2), default=0)
    remaining_amount = Column(Numeric(12, 2), nullable=True)

    # Currency
    currency = Column(String(3), default=CurrencyCode.TRY.value)

    # Status
    status = Column(String(20), default=BudgetStatus.DRAFT.value, index=True)

    # Thresholds (percentage)
    warning_threshold = Column(Integer, default=80)  # Warn at 80%
    critical_threshold = Column(Integer, default=95)  # Critical at 95%

    # Settings (JSON)
    settings = Column(JSON, default={
        "allow_overspending": False,
        "require_approval": True,
        "auto_allocate": False,
        "track_deposits": True
    })

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    event = relationship("Event", backref="budget")
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    categories = relationship("BudgetCategory", back_populates="budget", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="budget", cascade="all, delete-orphan")
    alerts = relationship("BudgetAlert", back_populates="budget", cascade="all, delete-orphan")
    snapshots = relationship("BudgetSnapshot", back_populates="budget", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_budget_event', 'event_id'),
        Index('idx_budget_status', 'status'),
    )


# ============================================================================
# Budget Category Models
# ============================================================================

class BudgetCategory(Base):
    """
    Budget categories for expense organization.

    Breaks down total budget into manageable categories
    with individual allocations and tracking.
    """
    __tablename__ = "budget_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Budget reference
    budget_id = Column(UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False, index=True)

    # Category details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    category_type = Column(String(30), default=ExpenseType.OTHER.value, index=True)

    # Amounts
    allocated_amount = Column(Numeric(12, 2), nullable=False)
    spent_amount = Column(Numeric(12, 2), default=0)
    pending_amount = Column(Numeric(12, 2), default=0)
    remaining_amount = Column(Numeric(12, 2), nullable=True)

    # Percentage of total budget
    percentage = Column(Float, nullable=True)

    # Priority
    priority = Column(Integer, default=0)
    is_essential = Column(Boolean, default=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    budget = relationship("Budget", back_populates="categories")
    expenses = relationship("Expense", back_populates="category")

    # Indexes
    __table_args__ = (
        Index('idx_budget_category_budget', 'budget_id'),
        Index('idx_budget_category_type', 'category_type'),
    )


# ============================================================================
# Expense Models
# ============================================================================

class Expense(Base):
    """
    Individual expenses and payments.

    Tracks all expenses against budget with approval workflow,
    payment status, and vendor references.
    """
    __tablename__ = "expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    budget_id = Column(UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("budget_categories.id"), nullable=True, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)

    # Vendor/payee reference
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True)
    payee_name = Column(String(200), nullable=True)

    # Expense details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    expense_type = Column(String(30), default=ExpenseType.OTHER.value, index=True)

    # Amounts
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default=CurrencyCode.TRY.value)
    tax_amount = Column(Numeric(12, 2), default=0)
    total_amount = Column(Numeric(12, 2), nullable=False)

    # Payment details
    payment_method = Column(String(50), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    payment_transaction_id = Column(UUID(as_uuid=True), ForeignKey("payment_transactions.id"), nullable=True)

    # Status and dates
    status = Column(String(20), default=ExpenseStatus.PENDING.value, index=True)
    expense_date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    due_date = Column(DateTime, nullable=True)
    paid_date = Column(DateTime, nullable=True)

    # Approval workflow
    requires_approval = Column(Boolean, default=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Attachments and receipts
    receipts = Column(JSON, default=[])  # [{url, filename, upload_date}]
    invoices = Column(JSON, default=[])  # [{url, invoice_number, date}]

    # Notes
    notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)

    # Recurring expense
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String(50), nullable=True)  # monthly, quarterly, etc.

    # Metadata
    metadata = Column(JSON, default={})

    # Timestamps
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    budget = relationship("Budget", back_populates="expenses")
    category = relationship("BudgetCategory", back_populates="expenses")
    event = relationship("Event")
    vendor = relationship("Vendor")
    booking = relationship("Booking")
    payment_transaction = relationship("PaymentTransaction")
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])

    # Indexes
    __table_args__ = (
        Index('idx_expense_budget', 'budget_id'),
        Index('idx_expense_category', 'category_id'),
        Index('idx_expense_status', 'status'),
        Index('idx_expense_date', 'expense_date'),
        Index('idx_expense_vendor', 'vendor_id'),
    )


# ============================================================================
# Budget Template Models
# ============================================================================

class BudgetTemplate(Base):
    """
    Reusable budget templates.

    Predefined budget structures with category allocations
    for different event types and sizes.
    """
    __tablename__ = "budget_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Template details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(50), nullable=True)  # wedding, corporate, birthday
    guest_count_range = Column(String(50), nullable=True)  # 50-100, 100-200

    # Template data (JSON)
    categories = Column(JSON, default=[])  # [{name, percentage, is_essential}]
    default_currency = Column(String(3), default=CurrencyCode.TRY.value)

    # Usage
    is_public = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)
    use_count = Column(Integer, default=0)

    # Metadata
    tags = Column(ARRAY(String(50)), default=list)
    metadata = Column(JSON, default={})

    # Timestamps
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = relationship("User")

    # Indexes
    __table_args__ = (
        Index('idx_budget_template_type', 'event_type'),
        Index('idx_budget_template_public', 'is_public'),
    )


# ============================================================================
# Budget Alert Models
# ============================================================================

class BudgetAlert(Base):
    """
    Budget alerts and notifications.

    Triggers when budget thresholds are reached,
    categories exceed limits, or payments are due.
    """
    __tablename__ = "budget_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Budget reference
    budget_id = Column(UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("budget_categories.id"), nullable=True)

    # Alert details
    alert_type = Column(String(30), nullable=False, index=True)
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    # Threshold details
    threshold_percentage = Column(Integer, nullable=True)
    current_percentage = Column(Float, nullable=True)
    amount_exceeded = Column(Numeric(12, 2), nullable=True)

    # Status
    is_read = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Notification sent
    notification_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime, nullable=True)

    # Timestamps
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    budget = relationship("Budget", back_populates="alerts")
    category = relationship("BudgetCategory")
    resolver = relationship("User")

    # Indexes
    __table_args__ = (
        Index('idx_budget_alert_budget', 'budget_id'),
        Index('idx_budget_alert_type', 'alert_type'),
        Index('idx_budget_alert_resolved', 'is_resolved'),
    )


# ============================================================================
# Budget Snapshot Models
# ============================================================================

class BudgetSnapshot(Base):
    """
    Periodic snapshots of budget status.

    Captures budget state at specific points in time
    for trend analysis and historical tracking.
    """
    __tablename__ = "budget_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Budget reference
    budget_id = Column(UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False, index=True)

    # Snapshot timing
    snapshot_date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    snapshot_type = Column(String(20), default="automatic")  # automatic, manual, milestone

    # Budget state
    total_budget = Column(Numeric(12, 2), nullable=False)
    allocated_amount = Column(Numeric(12, 2), nullable=False)
    spent_amount = Column(Numeric(12, 2), nullable=False)
    pending_amount = Column(Numeric(12, 2), nullable=False)
    remaining_amount = Column(Numeric(12, 2), nullable=False)

    # Percentages
    spent_percentage = Column(Float, nullable=False)
    allocated_percentage = Column(Float, nullable=False)

    # Category breakdown (JSON)
    category_breakdown = Column(JSON, default={})  # {category_id: {allocated, spent, remaining}}

    # Forecast data (JSON)
    forecast_data = Column(JSON, default={})

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    budget = relationship("Budget", back_populates="snapshots")

    # Indexes
    __table_args__ = (
        Index('idx_budget_snapshot_budget', 'budget_id'),
        Index('idx_budget_snapshot_date', 'snapshot_date'),
    )


# ============================================================================
# Cost Forecast Models
# ============================================================================

class CostForecast(Base):
    """
    Budget forecasting and projections.

    Predicts future costs based on current spending trends,
    committed expenses, and historical data.
    """
    __tablename__ = "cost_forecasts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Budget reference
    budget_id = Column(UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False, index=True)

    # Forecast details
    forecast_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    forecast_period_start = Column(DateTime, nullable=False)
    forecast_period_end = Column(DateTime, nullable=False)

    # Projected amounts
    projected_total = Column(Numeric(12, 2), nullable=False)
    projected_spent = Column(Numeric(12, 2), nullable=False)
    projected_remaining = Column(Numeric(12, 2), nullable=False)

    # Confidence and variance
    confidence_level = Column(Float, nullable=True)  # 0-100%
    variance_amount = Column(Numeric(12, 2), nullable=True)
    variance_percentage = Column(Float, nullable=True)

    # Forecast method
    forecast_method = Column(String(50), default="linear")  # linear, historical_average, ml_model

    # Category forecasts (JSON)
    category_forecasts = Column(JSON, default={})

    # Risk factors (JSON)
    risk_factors = Column(JSON, default=[])  # [{factor, impact, probability}]

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    budget = relationship("Budget", backref="forecasts")
    creator = relationship("User")

    # Indexes
    __table_args__ = (
        Index('idx_cost_forecast_budget', 'budget_id'),
        Index('idx_cost_forecast_date', 'forecast_date'),
    )


# ============================================================================
# Currency Exchange Rate Models
# ============================================================================

class CurrencyExchangeRate(Base):
    """
    Currency exchange rates for multi-currency budgets.

    Stores historical exchange rates for accurate
    currency conversion and reporting.
    """
    __tablename__ = "currency_exchange_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Currency pair
    from_currency = Column(String(3), nullable=False, index=True)
    to_currency = Column(String(3), nullable=False, index=True)

    # Rate
    exchange_rate = Column(Numeric(10, 6), nullable=False)

    # Validity
    effective_date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    source = Column(String(50), default="manual")  # manual, api, central_bank

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_exchange_rate_pair', 'from_currency', 'to_currency'),
        Index('idx_exchange_rate_date', 'effective_date'),
        UniqueConstraint('from_currency', 'to_currency', 'effective_date', name='uq_exchange_rate'),
    )
