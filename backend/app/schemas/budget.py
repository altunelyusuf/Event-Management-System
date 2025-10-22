"""
Budget Management Schemas
Sprint 15: Budget Management System

Pydantic schemas for budget functionality.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal


# ============================================================================
# Budget Schemas
# ============================================================================

class BudgetCreate(BaseModel):
    """Create a budget"""
    event_id: UUID
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None

    total_budget: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field("TRY", regex="^[A-Z]{3}$")

    warning_threshold: int = Field(80, ge=0, le=100)
    critical_threshold: int = Field(95, ge=0, le=100)

    settings: Dict[str, Any] = Field(default_factory=lambda: {
        "allow_overspending": False,
        "require_approval": True,
        "auto_allocate": False,
        "track_deposits": True
    })

    notes: Optional[str] = None


class BudgetUpdate(BaseModel):
    """Update a budget"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    total_budget: Optional[Decimal] = Field(None, gt=0)
    warning_threshold: Optional[int] = Field(None, ge=0, le=100)
    critical_threshold: Optional[int] = Field(None, ge=0, le=100)
    settings: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class BudgetResponse(BaseModel):
    """Budget response"""
    id: UUID
    event_id: UUID

    name: str
    description: Optional[str]

    total_budget: Decimal
    allocated_amount: Decimal
    spent_amount: Decimal
    pending_amount: Decimal
    remaining_amount: Optional[Decimal]

    currency: str
    status: str

    warning_threshold: int
    critical_threshold: int

    settings: Dict[str, Any]
    notes: Optional[str]

    created_by: UUID
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]
    approved_by: Optional[UUID]

    class Config:
        from_attributes = True


# ============================================================================
# Budget Category Schemas
# ============================================================================

class BudgetCategoryCreate(BaseModel):
    """Create a budget category"""
    budget_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    category_type: str = "other"

    allocated_amount: Decimal = Field(..., ge=0)
    priority: int = Field(0, ge=0)
    is_essential: bool = True

    notes: Optional[str] = None


class BudgetCategoryUpdate(BaseModel):
    """Update a budget category"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    allocated_amount: Optional[Decimal] = Field(None, ge=0)
    priority: Optional[int] = None
    is_essential: Optional[bool] = None
    notes: Optional[str] = None


class BudgetCategoryResponse(BaseModel):
    """Budget category response"""
    id: UUID
    budget_id: UUID

    name: str
    description: Optional[str]
    category_type: str

    allocated_amount: Decimal
    spent_amount: Decimal
    pending_amount: Decimal
    remaining_amount: Optional[Decimal]

    percentage: Optional[float]
    priority: int
    is_essential: bool

    notes: Optional[str]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Expense Schemas
# ============================================================================

class ExpenseCreate(BaseModel):
    """Create an expense"""
    budget_id: UUID
    category_id: Optional[UUID] = None
    event_id: UUID

    vendor_id: Optional[UUID] = None
    booking_id: Optional[UUID] = None
    payee_name: Optional[str] = None

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    expense_type: str = "other"

    amount: Decimal = Field(..., gt=0)
    currency: str = Field("TRY", regex="^[A-Z]{3}$")
    tax_amount: Decimal = Field(0, ge=0)

    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None

    expense_date: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None

    receipts: List[Dict[str, Any]] = Field(default_factory=list)
    invoices: List[Dict[str, Any]] = Field(default_factory=list)

    notes: Optional[str] = None
    internal_notes: Optional[str] = None

    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None


class ExpenseUpdate(BaseModel):
    """Update an expense"""
    category_id: Optional[UUID] = None
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ExpenseResponse(BaseModel):
    """Expense response"""
    id: UUID
    budget_id: UUID
    category_id: Optional[UUID]
    event_id: UUID

    vendor_id: Optional[UUID]
    booking_id: Optional[UUID]
    payee_name: Optional[str]

    title: str
    description: Optional[str]
    expense_type: str

    amount: Decimal
    currency: str
    tax_amount: Decimal
    total_amount: Decimal

    payment_method: Optional[str]
    payment_reference: Optional[str]

    status: str
    expense_date: datetime
    due_date: Optional[datetime]
    paid_date: Optional[datetime]

    requires_approval: bool
    approved_at: Optional[datetime]
    approved_by: Optional[UUID]
    rejection_reason: Optional[str]

    receipts: List[Dict[str, Any]]
    invoices: List[Dict[str, Any]]

    notes: Optional[str]

    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Budget Template Schemas
# ============================================================================

class BudgetTemplateCreate(BaseModel):
    """Create a budget template"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    event_type: Optional[str] = None
    guest_count_range: Optional[str] = None

    categories: List[Dict[str, Any]] = Field(..., min_items=1)
    default_currency: str = Field("TRY", regex="^[A-Z]{3}$")

    is_public: bool = False
    tags: List[str] = Field(default_factory=list)


class BudgetTemplateResponse(BaseModel):
    """Budget template response"""
    id: UUID
    name: str
    description: Optional[str]
    event_type: Optional[str]
    guest_count_range: Optional[str]

    categories: List[Dict[str, Any]]
    default_currency: str

    is_public: bool
    is_system: bool
    use_count: int

    tags: List[str]

    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Budget Analytics Schemas
# ============================================================================

class BudgetSummary(BaseModel):
    """Budget summary with key metrics"""
    budget_id: UUID
    total_budget: Decimal
    allocated_amount: Decimal
    spent_amount: Decimal
    pending_amount: Decimal
    remaining_amount: Decimal

    spent_percentage: float
    allocated_percentage: float
    remaining_percentage: float

    categories_count: int
    expenses_count: int
    pending_expenses_count: int

    is_over_budget: bool
    variance_amount: Decimal


class CategoryBreakdown(BaseModel):
    """Category spending breakdown"""
    category_id: UUID
    category_name: str
    allocated_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    percentage_of_total: float
    percentage_spent: float


class ExpenseTrend(BaseModel):
    """Expense trends over time"""
    period: str
    total_expenses: Decimal
    expense_count: int
    average_expense: Decimal


class BudgetAnalytics(BaseModel):
    """Comprehensive budget analytics"""
    summary: BudgetSummary
    category_breakdown: List[CategoryBreakdown]
    expense_trends: List[ExpenseTrend]
    top_expenses: List[ExpenseResponse]


# ============================================================================
# Forecast Schemas
# ============================================================================

class CostForecastCreate(BaseModel):
    """Create a cost forecast"""
    budget_id: UUID
    forecast_period_start: datetime
    forecast_period_end: datetime
    forecast_method: str = "linear"
    notes: Optional[str] = None


class CostForecastResponse(BaseModel):
    """Cost forecast response"""
    id: UUID
    budget_id: UUID

    forecast_date: datetime
    forecast_period_start: datetime
    forecast_period_end: datetime

    projected_total: Decimal
    projected_spent: Decimal
    projected_remaining: Decimal

    confidence_level: Optional[float]
    variance_amount: Optional[Decimal]
    variance_percentage: Optional[float]

    forecast_method: str
    category_forecasts: Dict[str, Any]
    risk_factors: List[Dict[str, Any]]

    notes: Optional[str]

    created_by: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Alert Schemas
# ============================================================================

class BudgetAlertResponse(BaseModel):
    """Budget alert response"""
    id: UUID
    budget_id: UUID
    category_id: Optional[UUID]

    alert_type: str
    severity: str
    title: str
    message: str

    threshold_percentage: Optional[int]
    current_percentage: Optional[float]
    amount_exceeded: Optional[Decimal]

    is_read: bool
    is_resolved: bool
    resolved_at: Optional[datetime]

    notification_sent: bool
    triggered_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Bulk Operations Schemas
# ============================================================================

class BulkCategoryCreate(BaseModel):
    """Bulk create budget categories"""
    budget_id: UUID
    categories: List[BudgetCategoryCreate] = Field(..., min_items=1)


class BulkExpenseCreate(BaseModel):
    """Bulk create expenses"""
    budget_id: UUID
    expenses: List[ExpenseCreate] = Field(..., min_items=1)


class BudgetFromTemplateCreate(BaseModel):
    """Create budget from template"""
    template_id: UUID
    event_id: UUID
    total_budget: Decimal = Field(..., gt=0)
    currency: str = Field("TRY", regex="^[A-Z]{3}$")
    name: Optional[str] = None


# ============================================================================
# Currency Exchange Schemas
# ============================================================================

class CurrencyExchangeRateCreate(BaseModel):
    """Create currency exchange rate"""
    from_currency: str = Field(..., regex="^[A-Z]{3}$")
    to_currency: str = Field(..., regex="^[A-Z]{3}$")
    exchange_rate: Decimal = Field(..., gt=0, decimal_places=6)
    effective_date: datetime = Field(default_factory=datetime.utcnow)
    source: str = "manual"


class CurrencyExchangeRateResponse(BaseModel):
    """Currency exchange rate response"""
    id: UUID
    from_currency: str
    to_currency: str
    exchange_rate: Decimal
    effective_date: datetime
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class CurrencyConversionRequest(BaseModel):
    """Currency conversion request"""
    amount: Decimal = Field(..., gt=0)
    from_currency: str = Field(..., regex="^[A-Z]{3}$")
    to_currency: str = Field(..., regex="^[A-Z]{3}$")
    conversion_date: Optional[datetime] = None


class CurrencyConversionResponse(BaseModel):
    """Currency conversion response"""
    original_amount: Decimal
    from_currency: str
    converted_amount: Decimal
    to_currency: str
    exchange_rate: Decimal
    conversion_date: datetime


# ============================================================================
# Report Schemas
# ============================================================================

class BudgetReportRequest(BaseModel):
    """Budget report request"""
    budget_id: UUID
    report_type: str = "summary"  # summary, detailed, variance, forecast
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_categories: bool = True
    include_expenses: bool = True
    format: str = "json"  # json, pdf, excel


class BudgetComparisonRequest(BaseModel):
    """Compare multiple budgets"""
    budget_ids: List[UUID] = Field(..., min_items=2, max_items=10)
    comparison_metrics: List[str] = Field(default_factory=lambda: ["spent", "remaining", "variance"])
