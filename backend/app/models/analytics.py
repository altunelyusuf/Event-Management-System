"""
Analytics and Reporting Models

This module defines the database models for analytics, reporting, and metrics
tracking across the CelebraTech Event Management System.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Numeric, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


# Enums
class ReportType(str, enum.Enum):
    """Report type enumeration"""
    EVENT_SUMMARY = "event_summary"
    FINANCIAL_REPORT = "financial_report"
    GUEST_REPORT = "guest_report"
    VENDOR_PERFORMANCE = "vendor_performance"
    BOOKING_ANALYSIS = "booking_analysis"
    REVIEW_ANALYSIS = "review_analysis"
    CUSTOM = "custom"


class ReportStatus(str, enum.Enum):
    """Report generation status"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportFormat(str, enum.Enum):
    """Report output format"""
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"


class MetricType(str, enum.Enum):
    """Metric type enumeration"""
    COUNTER = "counter"  # Simple count
    GAUGE = "gauge"  # Current value
    HISTOGRAM = "histogram"  # Distribution
    RATE = "rate"  # Rate over time


class AnalyticsSnapshot(Base):
    """
    Analytics snapshot model for capturing point-in-time metrics

    Stores aggregated metrics for events, vendors, and platform-wide statistics
    """
    __tablename__ = "analytics_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Snapshot metadata
    snapshot_date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    snapshot_type = Column(String(50), nullable=False)  # daily, weekly, monthly, event_completion

    # Scope
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True, index=True)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    # Event Metrics
    event_metrics = Column(JSON, default={})
    # {
    #     "total_events": 0,
    #     "active_events": 0,
    #     "completed_events": 0,
    #     "cancelled_events": 0,
    #     "avg_completion_rate": 0.0,
    #     "events_by_type": {},
    #     "events_by_phase": {}
    # }

    # Financial Metrics
    financial_metrics = Column(JSON, default={})
    # {
    #     "total_revenue": 0.0,
    #     "total_expenses": 0.0,
    #     "net_profit": 0.0,
    #     "avg_event_budget": 0.0,
    #     "payment_volume": 0.0,
    #     "pending_payments": 0.0,
    #     "refund_rate": 0.0
    # }

    # Guest Metrics
    guest_metrics = Column(JSON, default={})
    # {
    #     "total_guests": 0,
    #     "confirmed_guests": 0,
    #     "rsvp_response_rate": 0.0,
    #     "avg_guests_per_event": 0.0,
    #     "checkin_rate": 0.0,
    #     "dietary_breakdown": {}
    # }

    # Vendor Metrics
    vendor_metrics = Column(JSON, default={})
    # {
    #     "total_vendors": 0,
    #     "active_vendors": 0,
    #     "avg_rating": 0.0,
    #     "total_bookings": 0,
    #     "booking_conversion_rate": 0.0,
    #     "vendors_by_category": {}
    # }

    # Booking Metrics
    booking_metrics = Column(JSON, default={})
    # {
    #     "total_bookings": 0,
    #     "confirmed_bookings": 0,
    #     "cancelled_bookings": 0,
    #     "avg_booking_value": 0.0,
    #     "quote_to_booking_rate": 0.0
    # }

    # Review Metrics
    review_metrics = Column(JSON, default={})
    # {
    #     "total_reviews": 0,
    #     "avg_rating": 0.0,
    #     "review_response_rate": 0.0,
    #     "rating_distribution": {}
    # }

    # Platform Metrics
    platform_metrics = Column(JSON, default={})
    # {
    #     "total_users": 0,
    #     "active_users": 0,
    #     "new_signups": 0,
    #     "user_retention_rate": 0.0
    # }

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    event = relationship("Event", foreign_keys=[event_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    user = relationship("User", foreign_keys=[user_id])
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        Index("idx_snapshot_date", "snapshot_date"),
        Index("idx_snapshot_type", "snapshot_type"),
        Index("idx_snapshot_event", "event_id"),
        Index("idx_snapshot_vendor", "vendor_id"),
    )

    def __repr__(self):
        return f"<AnalyticsSnapshot {self.snapshot_type} - {self.snapshot_date}>"


class Report(Base):
    """
    Report model for generated reports

    Stores generated reports with parameters and output
    """
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Report details
    type = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Report parameters
    parameters = Column(JSON, default={})
    # {
    #     "event_id": "uuid",
    #     "start_date": "2024-01-01",
    #     "end_date": "2024-12-31",
    #     "filters": {}
    # }

    # Report scope
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True, index=True)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True, index=True)

    # Status and format
    status = Column(String(20), default=ReportStatus.PENDING.value, index=True)
    format = Column(String(20), default=ReportFormat.PDF.value)

    # Output
    data = Column(JSON, default={})  # Report data
    file_path = Column(String(500), nullable=True)  # Path to generated file
    file_size = Column(Integer, nullable=True)  # File size in bytes

    # Generation tracking
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Access tracking
    download_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime, nullable=True)

    # Expiration
    expires_at = Column(DateTime, nullable=True)  # Auto-delete after expiration

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    event = relationship("Event", foreign_keys=[event_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        Index("idx_report_type", "type"),
        Index("idx_report_status", "status"),
        Index("idx_report_event", "event_id"),
        Index("idx_report_created", "created_at"),
        Index("idx_report_expires", "expires_at"),
    )

    def __repr__(self):
        return f"<Report {self.title} ({self.type})>"


class Metric(Base):
    """
    Metric model for tracking individual metrics over time

    Stores time-series data for various metrics
    """
    __tablename__ = "metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Metric identification
    name = Column(String(100), nullable=False, index=True)
    type = Column(String(20), default=MetricType.COUNTER.value)
    category = Column(String(50), nullable=False, index=True)  # event, financial, guest, vendor, etc.

    # Metric value
    value = Column(Numeric(20, 4), nullable=False)
    value_previous = Column(Numeric(20, 4), nullable=True)  # Previous value for comparison

    # Scope
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True, index=True)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    # Additional data
    metadata = Column(JSON, default={})
    tags = Column(ARRAY(String(50)), default=list)

    # Timestamp
    measured_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    event = relationship("Event", foreign_keys=[event_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    user = relationship("User", foreign_keys=[user_id])

    # Indexes
    __table_args__ = (
        Index("idx_metric_name", "name"),
        Index("idx_metric_category", "category"),
        Index("idx_metric_measured", "measured_at"),
        Index("idx_metric_event", "event_id"),
        Index("idx_metric_name_measured", "name", "measured_at"),
    )

    def __repr__(self):
        return f"<Metric {self.name}: {self.value}>"


class Dashboard(Base):
    """
    Dashboard model for custom dashboard configurations

    Allows users to create custom dashboards with selected widgets
    """
    __tablename__ = "dashboards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Dashboard details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Dashboard type
    dashboard_type = Column(String(50), default="custom")  # custom, event, vendor, admin

    # Scope
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)

    # Configuration
    layout = Column(JSON, default={})
    # {
    #     "widgets": [
    #         {
    #             "id": "widget-1",
    #             "type": "metric_card",
    #             "metric": "total_revenue",
    #             "position": {"x": 0, "y": 0, "w": 3, "h": 2}
    #         }
    #     ]
    # }

    # Widget configuration
    widgets = Column(JSON, default=[])
    # [
    #     {
    #         "id": "widget-1",
    #         "type": "chart",
    #         "data_source": "revenue_over_time",
    #         "settings": {}
    #     }
    # ]

    # Sharing
    is_public = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    event = relationship("Event", foreign_keys=[event_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        Index("idx_dashboard_type", "dashboard_type"),
        Index("idx_dashboard_event", "event_id"),
        Index("idx_dashboard_vendor", "vendor_id"),
        Index("idx_dashboard_creator", "created_by"),
    )

    def __repr__(self):
        return f"<Dashboard {self.name}>"


class AuditLog(Base):
    """
    Audit log model for tracking important system actions

    Used for compliance, security, and analytics
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Action details
    action = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # auth, event, booking, payment, etc.
    severity = Column(String(20), default="info")  # info, warning, error, critical

    # Actor
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Target
    resource_type = Column(String(50), nullable=True)  # event, booking, payment, etc.
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Details
    description = Column(Text, nullable=True)
    changes = Column(JSON, default={})  # Before/after for updates
    # {
    #     "before": {"status": "pending"},
    #     "after": {"status": "confirmed"}
    # }

    # Additional context
    metadata = Column(JSON, default={})
    tags = Column(ARRAY(String(50)), default=list)

    # Status
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    # Indexes
    __table_args__ = (
        Index("idx_audit_action", "action"),
        Index("idx_audit_category", "category"),
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_created", "created_at"),
        Index("idx_audit_severity", "severity"),
    )

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_id}>"


class EventCompletionRate(Base):
    """
    Event completion rate tracking

    Tracks completion percentage of events through phases
    """
    __tablename__ = "event_completion_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)

    # Completion metrics
    overall_completion = Column(Numeric(5, 2), default=0.0)  # 0-100%
    phases_completed = Column(Integer, default=0)
    total_phases = Column(Integer, default=11)

    # Task completion
    tasks_completed = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    task_completion_rate = Column(Numeric(5, 2), default=0.0)

    # Booking completion
    bookings_confirmed = Column(Integer, default=0)
    bookings_needed = Column(Integer, default=0)
    booking_completion_rate = Column(Numeric(5, 2), default=0.0)

    # Guest management completion
    invitations_sent = Column(Integer, default=0)
    rsvps_received = Column(Integer, default=0)
    rsvp_completion_rate = Column(Numeric(5, 2), default=0.0)

    # Budget utilization
    budget_spent = Column(Numeric(15, 2), default=0.0)
    budget_allocated = Column(Numeric(15, 2), default=0.0)
    budget_utilization_rate = Column(Numeric(5, 2), default=0.0)

    # Calculated at
    calculated_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    event = relationship("Event", foreign_keys=[event_id])

    # Indexes
    __table_args__ = (
        Index("idx_completion_event", "event_id"),
        Index("idx_completion_calculated", "calculated_at"),
        Index("idx_completion_overall", "overall_completion"),
    )

    def __repr__(self):
        return f"<EventCompletionRate {self.event_id}: {self.overall_completion}%>"
