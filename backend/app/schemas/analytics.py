"""
Analytics and Reporting Schemas

Pydantic schemas for analytics, reporting, and metrics tracking.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID

from app.models.analytics import ReportType, ReportStatus, ReportFormat, MetricType


# ============================================================================
# Analytics Snapshot Schemas
# ============================================================================

class EventMetrics(BaseModel):
    """Event metrics schema"""
    total_events: int = 0
    active_events: int = 0
    completed_events: int = 0
    cancelled_events: int = 0
    avg_completion_rate: float = 0.0
    events_by_type: Dict[str, int] = Field(default_factory=dict)
    events_by_phase: Dict[str, int] = Field(default_factory=dict)


class FinancialMetrics(BaseModel):
    """Financial metrics schema"""
    total_revenue: float = 0.0
    total_expenses: float = 0.0
    net_profit: float = 0.0
    avg_event_budget: float = 0.0
    payment_volume: float = 0.0
    pending_payments: float = 0.0
    refund_rate: float = 0.0
    currency: str = "TRY"


class GuestMetrics(BaseModel):
    """Guest metrics schema"""
    total_guests: int = 0
    confirmed_guests: int = 0
    declined_guests: int = 0
    pending_guests: int = 0
    rsvp_response_rate: float = 0.0
    avg_guests_per_event: float = 0.0
    checkin_rate: float = 0.0
    dietary_breakdown: Dict[str, int] = Field(default_factory=dict)


class VendorMetrics(BaseModel):
    """Vendor metrics schema"""
    total_vendors: int = 0
    active_vendors: int = 0
    verified_vendors: int = 0
    avg_rating: float = 0.0
    total_bookings: int = 0
    booking_conversion_rate: float = 0.0
    vendors_by_category: Dict[str, int] = Field(default_factory=dict)


class BookingMetrics(BaseModel):
    """Booking metrics schema"""
    total_bookings: int = 0
    confirmed_bookings: int = 0
    pending_bookings: int = 0
    cancelled_bookings: int = 0
    avg_booking_value: float = 0.0
    quote_to_booking_rate: float = 0.0


class ReviewMetrics(BaseModel):
    """Review metrics schema"""
    total_reviews: int = 0
    avg_rating: float = 0.0
    review_response_rate: float = 0.0
    rating_distribution: Dict[str, int] = Field(default_factory=dict)


class PlatformMetrics(BaseModel):
    """Platform-wide metrics schema"""
    total_users: int = 0
    active_users: int = 0
    new_signups: int = 0
    user_retention_rate: float = 0.0
    organizer_count: int = 0
    vendor_count: int = 0


class AnalyticsSnapshotResponse(BaseModel):
    """Analytics snapshot response schema"""
    id: UUID
    snapshot_date: datetime
    snapshot_type: str

    event_id: Optional[UUID]
    vendor_id: Optional[UUID]
    user_id: Optional[UUID]

    event_metrics: Dict[str, Any]
    financial_metrics: Dict[str, Any]
    guest_metrics: Dict[str, Any]
    vendor_metrics: Dict[str, Any]
    booking_metrics: Dict[str, Any]
    review_metrics: Dict[str, Any]
    platform_metrics: Dict[str, Any]

    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Report Schemas
# ============================================================================

class ReportCreate(BaseModel):
    """Schema for creating a report"""
    type: str = Field(..., description="Report type")
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None

    # Report parameters
    event_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

    # Output format
    format: ReportFormat = Field(ReportFormat.PDF)

    # Expiration (days)
    expires_in_days: int = Field(30, ge=1, le=365)


class ReportUpdate(BaseModel):
    """Schema for updating a report"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[ReportStatus] = None


class ReportResponse(BaseModel):
    """Schema for report response"""
    id: UUID
    type: str
    title: str
    description: Optional[str]

    parameters: Dict[str, Any]
    event_id: Optional[UUID]
    vendor_id: Optional[UUID]

    status: str
    format: str

    data: Dict[str, Any]
    file_path: Optional[str]
    file_size: Optional[int]

    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    failed_at: Optional[datetime]
    error_message: Optional[str]

    download_count: int
    last_downloaded_at: Optional[datetime]

    expires_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True


# ============================================================================
# Metric Schemas
# ============================================================================

class MetricCreate(BaseModel):
    """Schema for creating a metric"""
    name: str = Field(..., min_length=1, max_length=100)
    type: MetricType = Field(MetricType.COUNTER)
    category: str = Field(..., max_length=50)

    value: float
    value_previous: Optional[float] = None

    event_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    user_id: Optional[UUID] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    measured_at: datetime = Field(default_factory=datetime.utcnow)


class MetricResponse(BaseModel):
    """Schema for metric response"""
    id: UUID
    name: str
    type: str
    category: str

    value: float
    value_previous: Optional[float]

    event_id: Optional[UUID]
    vendor_id: Optional[UUID]
    user_id: Optional[UUID]

    metadata: Dict[str, Any]
    tags: List[str]

    measured_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class MetricQuery(BaseModel):
    """Schema for querying metrics"""
    name: Optional[str] = None
    category: Optional[str] = None
    event_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)


# ============================================================================
# Dashboard Schemas
# ============================================================================

class WidgetConfig(BaseModel):
    """Widget configuration schema"""
    id: str
    type: str  # metric_card, chart, table, etc.
    title: Optional[str] = None
    data_source: str
    settings: Dict[str, Any] = Field(default_factory=dict)
    position: Dict[str, int] = Field(default_factory=dict)  # x, y, w, h


class DashboardCreate(BaseModel):
    """Schema for creating a dashboard"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None

    dashboard_type: str = Field("custom")

    event_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None

    layout: Dict[str, Any] = Field(default_factory=dict)
    widgets: List[WidgetConfig] = Field(default_factory=list)

    is_public: bool = Field(False)
    is_default: bool = Field(False)


class DashboardUpdate(BaseModel):
    """Schema for updating a dashboard"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None

    layout: Optional[Dict[str, Any]] = None
    widgets: Optional[List[WidgetConfig]] = None

    is_public: Optional[bool] = None
    is_default: Optional[bool] = None


class DashboardResponse(BaseModel):
    """Schema for dashboard response"""
    id: UUID
    name: str
    description: Optional[str]

    dashboard_type: str

    event_id: Optional[UUID]
    vendor_id: Optional[UUID]

    layout: Dict[str, Any]
    widgets: List[Dict[str, Any]]

    is_public: bool
    is_default: bool

    created_at: datetime
    updated_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True


# ============================================================================
# Audit Log Schemas
# ============================================================================

class AuditLogCreate(BaseModel):
    """Schema for creating an audit log"""
    action: str = Field(..., max_length=100)
    category: str = Field(..., max_length=50)
    severity: str = Field("info", pattern="^(info|warning|error|critical)$")

    user_id: Optional[UUID] = None
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = Field(None, max_length=500)

    resource_type: Optional[str] = Field(None, max_length=50)
    resource_id: Optional[UUID] = None

    description: Optional[str] = None
    changes: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    success: bool = Field(True)
    error_message: Optional[str] = None


class AuditLogResponse(BaseModel):
    """Schema for audit log response"""
    id: UUID
    action: str
    category: str
    severity: str

    user_id: Optional[UUID]
    ip_address: Optional[str]
    user_agent: Optional[str]

    resource_type: Optional[str]
    resource_id: Optional[UUID]

    description: Optional[str]
    changes: Dict[str, Any]
    metadata: Dict[str, Any]
    tags: List[str]

    success: bool
    error_message: Optional[str]

    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogQuery(BaseModel):
    """Schema for querying audit logs"""
    action: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    user_id: Optional[UUID] = None
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    success: Optional[bool] = None


# ============================================================================
# Event Analytics Schemas
# ============================================================================

class EventAnalytics(BaseModel):
    """Comprehensive event analytics"""
    event_id: UUID
    event_name: str
    event_type: str
    event_date: datetime

    # Completion
    overall_completion: float
    phases_completed: int
    total_phases: int

    # Tasks
    tasks_completed: int
    total_tasks: int
    task_completion_rate: float

    # Bookings
    bookings_confirmed: int
    bookings_pending: int
    bookings_cancelled: int
    total_bookings: int

    # Guests
    total_guests: int
    confirmed_guests: int
    rsvp_response_rate: float
    checkin_rate: float

    # Financial
    budget_allocated: float
    budget_spent: float
    budget_utilization: float
    total_revenue: float
    total_expenses: float
    net_profit: float

    # Reviews
    avg_rating: Optional[float] = None
    total_reviews: int = 0

    # Calculated at
    calculated_at: datetime


class VendorAnalytics(BaseModel):
    """Vendor performance analytics"""
    vendor_id: UUID
    vendor_name: str
    category: str

    # Ratings
    avg_rating: float
    total_reviews: int
    rating_trend: float  # Positive/negative trend

    # Bookings
    total_bookings: int
    confirmed_bookings: int
    cancelled_bookings: int
    booking_conversion_rate: float

    # Revenue
    total_revenue: float
    avg_booking_value: float

    # Response time
    avg_quote_response_time: Optional[float] = None  # In hours

    # Completion
    on_time_completion_rate: float = 0.0

    # Calculated at
    calculated_at: datetime


class FinancialAnalytics(BaseModel):
    """Financial analytics"""
    # Time period
    start_date: date
    end_date: date

    # Revenue
    total_revenue: float
    revenue_by_month: Dict[str, float]
    revenue_by_event_type: Dict[str, float]

    # Expenses
    total_expenses: float
    expenses_by_category: Dict[str, float]

    # Profit
    net_profit: float
    profit_margin: float

    # Payments
    payment_volume: float
    pending_payments: float
    completed_payments: float
    failed_payments: float

    # Refunds
    total_refunds: float
    refund_rate: float

    # Average values
    avg_event_budget: float
    avg_booking_value: float

    currency: str = "TRY"


# ============================================================================
# Dashboard Data Schemas
# ============================================================================

class DashboardData(BaseModel):
    """Dashboard data for organizer/admin"""
    # Overview
    total_events: int
    active_events: int
    upcoming_events: int

    # Financial summary
    total_revenue: float
    total_expenses: float
    pending_payments: float

    # Guest summary
    total_guests: int
    confirmed_guests: int
    pending_rsvps: int

    # Booking summary
    total_bookings: int
    confirmed_bookings: int
    pending_quotes: int

    # Recent activity
    recent_bookings: int = 0
    recent_payments: int = 0
    recent_reviews: int = 0

    # Trends (percentage change)
    events_trend: float = 0.0
    revenue_trend: float = 0.0
    guest_trend: float = 0.0
    booking_trend: float = 0.0


# ============================================================================
# Export Schemas
# ============================================================================

class ExportRequest(BaseModel):
    """Schema for export requests"""
    export_type: str = Field(..., description="Type of data to export")
    format: ReportFormat = Field(ReportFormat.CSV)

    # Filters
    event_id: Optional[UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    filters: Dict[str, Any] = Field(default_factory=dict)

    # Fields to include
    fields: List[str] = Field(default_factory=list)
