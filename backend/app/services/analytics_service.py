"""
Analytics Service

Business logic layer for analytics, reporting, and metrics.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta, date
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.analytics import Report, Metric, Dashboard, AuditLog, ReportStatus, ReportFormat
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    ReportCreate, ReportResponse, ReportUpdate,
    MetricCreate, MetricResponse, MetricQuery,
    DashboardCreate, DashboardUpdate, DashboardResponse,
    AuditLogCreate, AuditLogResponse, AuditLogQuery,
    EventAnalytics, VendorAnalytics, FinancialAnalytics, DashboardData
)


class AnalyticsService:
    """Service for analytics and reporting business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AnalyticsRepository(db)

    # ========================================================================
    # Event Analytics
    # ========================================================================

    async def get_event_analytics(
        self,
        event_id: UUID,
        current_user: User
    ) -> EventAnalytics:
        """Get comprehensive analytics for an event"""
        # TODO: Check event access
        analytics_data = await self.repo.calculate_event_analytics(event_id)

        if not analytics_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        return EventAnalytics(**analytics_data)

    async def get_vendor_analytics(
        self,
        vendor_id: UUID,
        current_user: User
    ) -> VendorAnalytics:
        """Get analytics for a vendor"""
        # Vendors can view their own analytics, admins can view all
        # TODO: Add proper authorization check

        analytics_data = await self.repo.calculate_vendor_analytics(vendor_id)

        if not analytics_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

        return VendorAnalytics(**analytics_data)

    async def get_financial_analytics(
        self,
        start_date: Optional[date],
        end_date: Optional[date],
        event_id: Optional[UUID],
        current_user: User
    ) -> FinancialAnalytics:
        """Get financial analytics"""
        # TODO: Check authorization

        analytics_data = await self.repo.calculate_financial_analytics(
            start_date=start_date,
            end_date=end_date,
            event_id=event_id
        )

        return FinancialAnalytics(**analytics_data)

    async def get_dashboard_data(
        self,
        current_user: User
    ) -> DashboardData:
        """Get dashboard data for current user"""
        dashboard_data = await self.repo.get_dashboard_data(current_user.id)
        return DashboardData(**dashboard_data)

    # ========================================================================
    # Report Operations
    # ========================================================================

    async def create_report(
        self,
        report_data: ReportCreate,
        current_user: User
    ) -> ReportResponse:
        """Create a new report"""
        # Set expiration
        expires_at = datetime.utcnow() + timedelta(days=report_data.expires_in_days)

        report = Report(
            type=report_data.type,
            title=report_data.title,
            description=report_data.description,
            parameters=report_data.parameters,
            event_id=report_data.event_id,
            vendor_id=report_data.vendor_id,
            format=report_data.format.value,
            status=ReportStatus.PENDING.value,
            expires_at=expires_at,
            created_by=current_user.id
        )

        # Add date parameters
        if report_data.start_date:
            report.parameters["start_date"] = report_data.start_date.isoformat()
        if report_data.end_date:
            report.parameters["end_date"] = report_data.end_date.isoformat()

        created_report = await self.repo.create_report(report)

        # TODO: Trigger background job to generate report
        # For now, just mark as generating
        await self.repo.update_report_status(created_report.id, ReportStatus.GENERATING.value)

        await self.db.commit()
        return ReportResponse.model_validate(created_report)

    async def get_report(
        self,
        report_id: UUID,
        current_user: User
    ) -> ReportResponse:
        """Get a report by ID"""
        report = await self.repo.get_report(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )

        # Check ownership
        if report.created_by != current_user.id and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this report"
            )

        return ReportResponse.model_validate(report)

    async def get_reports(
        self,
        event_id: Optional[UUID],
        status: Optional[str],
        current_user: User,
        skip: int = 0,
        limit: int = 50
    ) -> List[ReportResponse]:
        """Get reports for current user"""
        # Users can only see their own reports unless admin
        user_id = None if current_user.role == UserRole.ADMIN.value else current_user.id

        reports = await self.repo.get_reports(
            user_id=user_id,
            event_id=event_id,
            status=status,
            skip=skip,
            limit=limit
        )

        return [ReportResponse.model_validate(r) for r in reports]

    async def delete_report(
        self,
        report_id: UUID,
        current_user: User
    ) -> dict:
        """Delete a report"""
        report = await self.repo.get_report(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )

        # Check ownership
        if report.created_by != current_user.id and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this report"
            )

        await self.db.delete(report)
        await self.db.commit()
        return {"message": "Report deleted successfully"}

    # ========================================================================
    # Metric Operations
    # ========================================================================

    async def create_metric(
        self,
        metric_data: MetricCreate,
        current_user: User
    ) -> MetricResponse:
        """Create a new metric (admin only)"""
        if current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        metric = Metric(**metric_data.model_dump())
        created_metric = await self.repo.create_metric(metric)
        await self.db.commit()
        return MetricResponse.model_validate(created_metric)

    async def get_metrics(
        self,
        query: MetricQuery,
        current_user: User,
        limit: int = 100
    ) -> List[MetricResponse]:
        """Get metrics with filters"""
        # TODO: Add authorization check

        metrics = await self.repo.get_metrics(
            name=query.name,
            category=query.category,
            event_id=query.event_id,
            start_date=query.start_date,
            end_date=query.end_date,
            limit=limit
        )

        return [MetricResponse.model_validate(m) for m in metrics]

    # ========================================================================
    # Dashboard Operations
    # ========================================================================

    async def create_dashboard(
        self,
        dashboard_data: DashboardCreate,
        current_user: User
    ) -> DashboardResponse:
        """Create a new dashboard"""
        dashboard = Dashboard(
            **dashboard_data.model_dump(exclude={"widgets"}),
            widgets=[w.model_dump() for w in dashboard_data.widgets],
            created_by=current_user.id
        )

        created_dashboard = await self.repo.create_dashboard(dashboard)
        await self.db.commit()
        return DashboardResponse.model_validate(created_dashboard)

    async def get_dashboard(
        self,
        dashboard_id: UUID,
        current_user: User
    ) -> DashboardResponse:
        """Get a dashboard by ID"""
        dashboard = await self.repo.get_dashboard(dashboard_id)
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found"
            )

        # Check access
        if not dashboard.is_public:
            if dashboard.created_by != current_user.id and current_user.role != UserRole.ADMIN.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this dashboard"
                )

        return DashboardResponse.model_validate(dashboard)

    async def get_dashboards(
        self,
        event_id: Optional[UUID],
        dashboard_type: Optional[str],
        current_user: User
    ) -> List[DashboardResponse]:
        """Get dashboards for current user"""
        dashboards = await self.repo.get_dashboards(
            user_id=current_user.id,
            event_id=event_id,
            dashboard_type=dashboard_type
        )

        return [DashboardResponse.model_validate(d) for d in dashboards]

    async def update_dashboard(
        self,
        dashboard_id: UUID,
        dashboard_data: DashboardUpdate,
        current_user: User
    ) -> DashboardResponse:
        """Update a dashboard"""
        dashboard = await self.repo.get_dashboard(dashboard_id)
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found"
            )

        # Check ownership
        if dashboard.created_by != current_user.id and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this dashboard"
            )

        update_data = dashboard_data.model_dump(exclude_unset=True)

        # Convert widgets if provided
        if "widgets" in update_data and update_data["widgets"]:
            update_data["widgets"] = [w.model_dump() if hasattr(w, 'model_dump') else w for w in update_data["widgets"]]

        updated_dashboard = await self.repo.update_dashboard(dashboard_id, update_data)
        await self.db.commit()
        return DashboardResponse.model_validate(updated_dashboard)

    async def delete_dashboard(
        self,
        dashboard_id: UUID,
        current_user: User
    ) -> dict:
        """Delete a dashboard"""
        dashboard = await self.repo.get_dashboard(dashboard_id)
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found"
            )

        # Check ownership
        if dashboard.created_by != current_user.id and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this dashboard"
            )

        success = await self.repo.delete_dashboard(dashboard_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete dashboard"
            )

        await self.db.commit()
        return {"message": "Dashboard deleted successfully"}

    # ========================================================================
    # Audit Log Operations
    # ========================================================================

    async def create_audit_log(
        self,
        audit_log_data: AuditLogCreate
    ) -> AuditLogResponse:
        """Create an audit log entry (internal use)"""
        audit_log = AuditLog(**audit_log_data.model_dump())
        created_log = await self.repo.create_audit_log(audit_log)
        await self.db.commit()
        return AuditLogResponse.model_validate(created_log)

    async def get_audit_logs(
        self,
        query: AuditLogQuery,
        current_user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLogResponse]:
        """Get audit logs (admin only)"""
        if current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        logs = await self.repo.get_audit_logs(
            user_id=query.user_id,
            action=query.action,
            category=query.category,
            resource_type=query.resource_type,
            resource_id=query.resource_id,
            start_date=query.start_date,
            end_date=query.end_date,
            skip=skip,
            limit=limit
        )

        return [AuditLogResponse.model_validate(log) for log in logs]

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def log_action(
        self,
        action: str,
        category: str,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        description: Optional[str] = None,
        changes: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        success: bool = True,
        severity: str = "info"
    ):
        """Helper method to log actions"""
        audit_log_data = AuditLogCreate(
            action=action,
            category=category,
            severity=severity,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            changes=changes or {},
            metadata=metadata or {},
            success=success
        )

        await self.create_audit_log(audit_log_data)
