"""
Analytics API Endpoints

REST API endpoints for analytics, reporting, metrics, and dashboards.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import date
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    ReportCreate, ReportResponse, ReportUpdate,
    MetricCreate, MetricResponse, MetricQuery,
    DashboardCreate, DashboardUpdate, DashboardResponse,
    AuditLogQuery, AuditLogResponse,
    EventAnalytics, VendorAnalytics, FinancialAnalytics, DashboardData
)


router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ============================================================================
# Analytics Endpoints
# ============================================================================

@router.get("/events/{event_id}", response_model=EventAnalytics)
async def get_event_analytics(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive analytics for an event.

    Includes completion rates, guest statistics, bookings, financial data,
    and reviews.
    """
    service = AnalyticsService(db)
    return await service.get_event_analytics(event_id, current_user)


@router.get("/vendors/{vendor_id}", response_model=VendorAnalytics)
async def get_vendor_analytics(
    vendor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get performance analytics for a vendor.

    Includes ratings, bookings, revenue, conversion rates, and completion stats.
    Vendors can view their own analytics.
    """
    service = AnalyticsService(db)
    return await service.get_vendor_analytics(vendor_id, current_user)


@router.get("/financial", response_model=FinancialAnalytics)
async def get_financial_analytics(
    start_date: Optional[date] = Query(None, description="Start date for analytics period"),
    end_date: Optional[date] = Query(None, description="End date for analytics period"),
    event_id: Optional[UUID] = Query(None, description="Filter by specific event"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get financial analytics for a time period.

    Includes revenue, expenses, profit, payment volume, refunds, and breakdowns
    by category and event type.
    """
    service = AnalyticsService(db)
    return await service.get_financial_analytics(
        start_date, end_date, event_id, current_user
    )


@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get dashboard data for the current user.

    Provides overview of events, financial summary, guest summary, bookings,
    and recent activity.
    """
    service = AnalyticsService(db)
    return await service.get_dashboard_data(current_user)


# ============================================================================
# Report Endpoints
# ============================================================================

@router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_data: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new report.

    Supports various report types:
    - event_summary: Event summary report
    - financial_report: Financial analysis
    - guest_report: Guest list and RSVP summary
    - vendor_performance: Vendor performance metrics
    - booking_analysis: Booking trends
    - review_analysis: Review analytics

    Reports can be generated in PDF, CSV, Excel, or JSON format.
    """
    service = AnalyticsService(db)
    return await service.create_report(report_data, current_user)


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a report by ID.

    Returns report details including status, data, and download information.
    """
    service = AnalyticsService(db)
    return await service.get_report(report_id, current_user)


@router.get("/reports", response_model=List[ReportResponse])
async def get_reports(
    event_id: Optional[UUID] = Query(None, description="Filter by event"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all reports for the current user.

    Supports filtering by event and status.
    Admins can see all reports.
    """
    service = AnalyticsService(db)
    return await service.get_reports(event_id, status, current_user, skip, limit)


@router.delete("/reports/{report_id}", status_code=status.HTTP_200_OK)
async def delete_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a report.

    Only the report creator or admins can delete reports.
    """
    service = AnalyticsService(db)
    return await service.delete_report(report_id, current_user)


# ============================================================================
# Metric Endpoints
# ============================================================================

@router.post("/metrics", response_model=MetricResponse, status_code=status.HTTP_201_CREATED)
async def create_metric(
    metric_data: MetricCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new metric (admin only).

    Used for tracking custom metrics over time.
    """
    service = AnalyticsService(db)
    return await service.create_metric(metric_data, current_user)


@router.post("/metrics/query", response_model=List[MetricResponse])
async def query_metrics(
    query: MetricQuery,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Query metrics with filters.

    Supports filtering by name, category, event, vendor, and date range.
    Returns time-series metric data.
    """
    service = AnalyticsService(db)
    return await service.get_metrics(query, current_user, limit)


# ============================================================================
# Dashboard Endpoints
# ============================================================================

@router.post("/dashboards", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    dashboard_data: DashboardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a custom dashboard.

    Dashboards allow users to configure custom layouts with selected widgets
    for analytics visualization.
    """
    service = AnalyticsService(db)
    return await service.create_dashboard(dashboard_data, current_user)


@router.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a dashboard by ID.

    Public dashboards can be viewed by anyone.
    Private dashboards require ownership or admin access.
    """
    service = AnalyticsService(db)
    return await service.get_dashboard(dashboard_id, current_user)


@router.get("/dashboards", response_model=List[DashboardResponse])
async def get_dashboards(
    event_id: Optional[UUID] = Query(None, description="Filter by event"),
    dashboard_type: Optional[str] = Query(None, description="Filter by dashboard type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all dashboards for the current user.

    Returns custom, event, and vendor dashboards.
    """
    service = AnalyticsService(db)
    return await service.get_dashboards(event_id, dashboard_type, current_user)


@router.patch("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: UUID,
    dashboard_data: DashboardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a dashboard.

    Update layout, widgets, or dashboard settings.
    """
    service = AnalyticsService(db)
    return await service.update_dashboard(dashboard_id, dashboard_data, current_user)


@router.delete("/dashboards/{dashboard_id}", status_code=status.HTTP_200_OK)
async def delete_dashboard(
    dashboard_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a dashboard.

    Only the dashboard creator or admins can delete dashboards.
    """
    service = AnalyticsService(db)
    return await service.delete_dashboard(dashboard_id, current_user)


# ============================================================================
# Audit Log Endpoints
# ============================================================================

@router.post("/audit-logs/query", response_model=List[AuditLogResponse])
async def query_audit_logs(
    query: AuditLogQuery,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Query audit logs (admin only).

    Returns system activity logs with filtering by action, category, user,
    resource type, date range, and success status.

    Useful for security auditing, compliance, and debugging.
    """
    service = AnalyticsService(db)
    return await service.get_audit_logs(query, current_user, skip, limit)


# ============================================================================
# Export Endpoints
# ============================================================================

@router.get("/export/events/{event_id}")
async def export_event_data(
    event_id: UUID,
    format: str = Query("csv", pattern="^(csv|excel|pdf)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export event data.

    Exports comprehensive event data including guests, bookings, payments,
    and tasks in the specified format.

    Supported formats: CSV, Excel, PDF
    """
    # TODO: Implement export functionality
    return {
        "message": "Export functionality coming soon",
        "event_id": event_id,
        "format": format
    }


@router.get("/export/guests/{event_id}")
async def export_guest_list(
    event_id: UUID,
    format: str = Query("csv", pattern="^(csv|excel)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export guest list with RSVP data.

    Includes guest contact information, RSVP status, dietary restrictions,
    seating assignments, and check-in status.

    Supported formats: CSV, Excel
    """
    # TODO: Implement export functionality
    return {
        "message": "Export functionality coming soon",
        "event_id": event_id,
        "format": format
    }


@router.get("/export/financial")
async def export_financial_data(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    format: str = Query("csv", pattern="^(csv|excel|pdf)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export financial data.

    Exports revenue, expenses, payments, and invoices for the specified period.

    Supported formats: CSV, Excel, PDF
    """
    # TODO: Implement export functionality
    return {
        "message": "Export functionality coming soon",
        "start_date": start_date,
        "end_date": end_date,
        "format": format
    }
