"""
Analytics Repository

Data access layer for analytics, reporting, and metrics.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, between, desc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from uuid import UUID

from app.models.analytics import (
    AnalyticsSnapshot, Report, Metric, Dashboard, AuditLog,
    EventCompletionRate, ReportStatus
)
from app.models.event import Event, EventStatus, EventPhase, PhaseStatus
from app.models.booking import Booking, BookingRequest
from app.models.payment import PaymentTransaction
from app.models.guest import Guest, RSVPStatus
from app.models.review import Review
from app.models.vendor import Vendor
from app.models.user import User


class AnalyticsRepository:
    """Repository for analytics and reporting operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Event Analytics
    # ========================================================================

    async def calculate_event_analytics(self, event_id: UUID) -> Dict[str, Any]:
        """Calculate comprehensive analytics for an event"""
        # Get event
        event_query = select(Event).where(Event.id == event_id)
        event_result = await self.db.execute(event_query)
        event = event_result.scalar_one_or_none()

        if not event:
            return {}

        # Phase completion
        phases_query = select(func.count(EventPhase.id)).where(
            and_(
                EventPhase.event_id == event_id,
                EventPhase.status == PhaseStatus.COMPLETED.value
            )
        )
        phases_completed = (await self.db.execute(phases_query)).scalar_one()

        total_phases_query = select(func.count(EventPhase.id)).where(EventPhase.event_id == event_id)
        total_phases = (await self.db.execute(total_phases_query)).scalar_one()

        overall_completion = (phases_completed / total_phases * 100) if total_phases > 0 else 0.0

        # Guest analytics
        total_guests_query = select(func.count(Guest.id)).where(Guest.event_id == event_id)
        total_guests = (await self.db.execute(total_guests_query)).scalar_one()

        confirmed_guests_query = select(func.count(Guest.id)).where(
            and_(Guest.event_id == event_id, Guest.rsvp_status == RSVPStatus.ATTENDING.value)
        )
        confirmed_guests = (await self.db.execute(confirmed_guests_query)).scalar_one()

        checkedin_guests_query = select(func.count(Guest.id)).where(
            and_(Guest.event_id == event_id, Guest.checked_in == True)
        )
        checked_in_guests = (await self.db.execute(checkedin_guests_query)).scalar_one()

        rsvp_response_rate = 0.0
        checkin_rate = 0.0

        if total_guests > 0:
            responded = await self.db.execute(
                select(func.count(Guest.id)).where(
                    and_(
                        Guest.event_id == event_id,
                        Guest.rsvp_status.in_([RSVPStatus.ATTENDING.value, RSVPStatus.NOT_ATTENDING.value])
                    )
                )
            )
            rsvp_response_rate = (responded.scalar_one() / total_guests * 100)

        if confirmed_guests > 0:
            checkin_rate = (checked_in_guests / confirmed_guests * 100)

        # Booking analytics
        total_bookings_query = select(func.count(Booking.id)).where(Booking.event_id == event_id)
        total_bookings = (await self.db.execute(total_bookings_query)).scalar_one()

        confirmed_bookings_query = select(func.count(Booking.id)).where(
            and_(Booking.event_id == event_id, Booking.status == "confirmed")
        )
        confirmed_bookings = (await self.db.execute(confirmed_bookings_query)).scalar_one()

        # Financial analytics
        budget_allocated = float(event.budget_amount or 0)
        budget_spent = float(event.spent_amount or 0)
        budget_utilization = (budget_spent / budget_allocated * 100) if budget_allocated > 0 else 0.0

        # Revenue from bookings
        revenue_query = select(func.sum(Booking.final_amount)).where(
            and_(Booking.event_id == event_id, Booking.status == "confirmed")
        )
        total_revenue = float((await self.db.execute(revenue_query)).scalar_one() or 0)

        # Reviews
        reviews_query = select(func.count(Review.id), func.avg(Review.rating)).where(
            Review.event_id == event_id
        )
        review_result = await self.db.execute(reviews_query)
        review_data = review_result.one()
        total_reviews = review_data[0] or 0
        avg_rating = float(review_data[1] or 0.0)

        return {
            "event_id": event_id,
            "event_name": event.name,
            "event_type": event.type.value,
            "event_date": event.event_date,
            "overall_completion": round(overall_completion, 2),
            "phases_completed": phases_completed,
            "total_phases": total_phases,
            "total_guests": total_guests,
            "confirmed_guests": confirmed_guests,
            "rsvp_response_rate": round(rsvp_response_rate, 2),
            "checkin_rate": round(checkin_rate, 2),
            "total_bookings": total_bookings,
            "confirmed_bookings": confirmed_bookings,
            "budget_allocated": budget_allocated,
            "budget_spent": budget_spent,
            "budget_utilization": round(budget_utilization, 2),
            "total_revenue": total_revenue,
            "total_expenses": budget_spent,
            "net_profit": total_revenue - budget_spent,
            "avg_rating": round(avg_rating, 2),
            "total_reviews": total_reviews,
            "calculated_at": datetime.utcnow()
        }

    async def calculate_vendor_analytics(self, vendor_id: UUID) -> Dict[str, Any]:
        """Calculate analytics for a vendor"""
        # Get vendor
        vendor_query = select(Vendor).where(Vendor.id == vendor_id)
        vendor_result = await self.db.execute(vendor_query)
        vendor = vendor_result.scalar_one_or_none()

        if not vendor:
            return {}

        # Review analytics
        reviews_query = select(func.count(Review.id), func.avg(Review.rating)).where(
            Review.vendor_id == vendor_id
        )
        review_result = await self.db.execute(reviews_query)
        review_data = review_result.one()
        total_reviews = review_data[0] or 0
        avg_rating = float(review_data[1] or 0.0)

        # Booking analytics
        total_bookings_query = select(func.count(Booking.id)).where(Booking.vendor_id == vendor_id)
        total_bookings = (await self.db.execute(total_bookings_query)).scalar_one()

        confirmed_bookings_query = select(func.count(Booking.id)).where(
            and_(Booking.vendor_id == vendor_id, Booking.status == "confirmed")
        )
        confirmed_bookings = (await self.db.execute(confirmed_bookings_query)).scalar_one()

        cancelled_bookings_query = select(func.count(Booking.id)).where(
            and_(Booking.vendor_id == vendor_id, Booking.status == "cancelled")
        )
        cancelled_bookings = (await self.db.execute(cancelled_bookings_query)).scalar_one()

        # Revenue
        revenue_query = select(func.sum(Booking.final_amount)).where(
            and_(Booking.vendor_id == vendor_id, Booking.status == "confirmed")
        )
        total_revenue = float((await self.db.execute(revenue_query)).scalar_one() or 0)

        avg_booking_value = (total_revenue / confirmed_bookings) if confirmed_bookings > 0 else 0.0

        # Quote conversion
        total_quotes_query = select(func.count(BookingRequest.id)).where(
            BookingRequest.vendor_id == vendor_id
        )
        total_quotes = (await self.db.execute(total_quotes_query)).scalar_one()

        booking_conversion_rate = (confirmed_bookings / total_quotes * 100) if total_quotes > 0 else 0.0

        return {
            "vendor_id": vendor_id,
            "vendor_name": vendor.business_name,
            "category": vendor.category,
            "avg_rating": round(avg_rating, 2),
            "total_reviews": total_reviews,
            "rating_trend": 0.0,  # TODO: Calculate trend
            "total_bookings": total_bookings,
            "confirmed_bookings": confirmed_bookings,
            "cancelled_bookings": cancelled_bookings,
            "booking_conversion_rate": round(booking_conversion_rate, 2),
            "total_revenue": total_revenue,
            "avg_booking_value": round(avg_booking_value, 2),
            "on_time_completion_rate": 0.0,  # TODO: Track completion
            "calculated_at": datetime.utcnow()
        }

    async def calculate_financial_analytics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        event_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Calculate financial analytics for a period"""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Base query conditions
        date_conditions = and_(
            PaymentTransaction.created_at >= start_date,
            PaymentTransaction.created_at <= end_date
        )

        if event_id:
            # TODO: Join with bookings to filter by event
            pass

        # Revenue
        revenue_query = select(func.sum(PaymentTransaction.amount)).where(
            and_(
                date_conditions,
                PaymentTransaction.status == "completed",
                PaymentTransaction.transaction_type == "charge"
            )
        )
        total_revenue = float((await self.db.execute(revenue_query)).scalar_one() or 0)

        # Refunds
        refund_query = select(func.sum(PaymentTransaction.amount)).where(
            and_(
                date_conditions,
                PaymentTransaction.status == "completed",
                PaymentTransaction.transaction_type == "refund"
            )
        )
        total_refunds = float((await self.db.execute(refund_query)).scalar_one() or 0)

        # Pending payments
        pending_query = select(func.sum(PaymentTransaction.amount)).where(
            and_(
                date_conditions,
                PaymentTransaction.status == "pending"
            )
        )
        pending_payments = float((await self.db.execute(pending_query)).scalar_one() or 0)

        # Failed payments
        failed_query = select(func.sum(PaymentTransaction.amount)).where(
            and_(
                date_conditions,
                PaymentTransaction.status == "failed"
            )
        )
        failed_payments = float((await self.db.execute(failed_query)).scalar_one() or 0)

        payment_volume = total_revenue + pending_payments
        refund_rate = (total_refunds / total_revenue * 100) if total_revenue > 0 else 0.0

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_revenue": total_revenue,
            "revenue_by_month": {},  # TODO: Group by month
            "revenue_by_event_type": {},  # TODO: Group by event type
            "total_expenses": 0.0,  # TODO: Calculate from event budgets
            "expenses_by_category": {},
            "net_profit": total_revenue - total_refunds,
            "profit_margin": 0.0,
            "payment_volume": payment_volume,
            "pending_payments": pending_payments,
            "completed_payments": total_revenue,
            "failed_payments": failed_payments,
            "total_refunds": total_refunds,
            "refund_rate": round(refund_rate, 2),
            "avg_event_budget": 0.0,  # TODO: Calculate
            "avg_booking_value": 0.0,  # TODO: Calculate
            "currency": "TRY"
        }

    # ========================================================================
    # Dashboard Data
    # ========================================================================

    async def get_dashboard_data(self, user_id: UUID) -> Dict[str, Any]:
        """Get dashboard data for a user (organizer)"""
        # Total events for user
        total_events_query = select(func.count(Event.id)).where(Event.created_by == user_id)
        total_events = (await self.db.execute(total_events_query)).scalar_one()

        # Active events
        active_events_query = select(func.count(Event.id)).where(
            and_(Event.created_by == user_id, Event.status == EventStatus.ACTIVE.value)
        )
        active_events = (await self.db.execute(active_events_query)).scalar_one()

        # Upcoming events
        upcoming_events_query = select(func.count(Event.id)).where(
            and_(
                Event.created_by == user_id,
                Event.event_date > datetime.utcnow()
            )
        )
        upcoming_events = (await self.db.execute(upcoming_events_query)).scalar_one()

        # Financial summary (for user's events)
        user_events_subquery = select(Event.id).where(Event.created_by == user_id).scalar_subquery()

        revenue_query = select(func.sum(Booking.final_amount)).where(
            and_(
                Booking.event_id.in_(user_events_subquery),
                Booking.status == "confirmed"
            )
        )
        total_revenue = float((await self.db.execute(revenue_query)).scalar_one() or 0)

        expenses_query = select(func.sum(Event.spent_amount)).where(Event.created_by == user_id)
        total_expenses = float((await self.db.execute(expenses_query)).scalar_one() or 0)

        # Guest summary
        guests_query = select(func.count(Guest.id)).where(Guest.event_id.in_(user_events_subquery))
        total_guests = (await self.db.execute(guests_query)).scalar_one()

        confirmed_guests_query = select(func.count(Guest.id)).where(
            and_(
                Guest.event_id.in_(user_events_subquery),
                Guest.rsvp_status == RSVPStatus.ATTENDING.value
            )
        )
        confirmed_guests = (await self.db.execute(confirmed_guests_query)).scalar_one()

        pending_rsvps_query = select(func.count(Guest.id)).where(
            and_(
                Guest.event_id.in_(user_events_subquery),
                Guest.rsvp_status == RSVPStatus.PENDING.value
            )
        )
        pending_rsvps = (await self.db.execute(pending_rsvps_query)).scalar_one()

        # Booking summary
        bookings_query = select(func.count(Booking.id)).where(Booking.event_id.in_(user_events_subquery))
        total_bookings = (await self.db.execute(bookings_query)).scalar_one()

        confirmed_bookings_query = select(func.count(Booking.id)).where(
            and_(
                Booking.event_id.in_(user_events_subquery),
                Booking.status == "confirmed"
            )
        )
        confirmed_bookings = (await self.db.execute(confirmed_bookings_query)).scalar_one()

        return {
            "total_events": total_events,
            "active_events": active_events,
            "upcoming_events": upcoming_events,
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "pending_payments": 0.0,  # TODO: Calculate
            "total_guests": total_guests,
            "confirmed_guests": confirmed_guests,
            "pending_rsvps": pending_rsvps,
            "total_bookings": total_bookings,
            "confirmed_bookings": confirmed_bookings,
            "pending_quotes": 0,  # TODO: Calculate
            "recent_bookings": 0,
            "recent_payments": 0,
            "recent_reviews": 0,
            "events_trend": 0.0,
            "revenue_trend": 0.0,
            "guest_trend": 0.0,
            "booking_trend": 0.0
        }

    # ========================================================================
    # Report Operations
    # ========================================================================

    async def create_report(self, report: Report) -> Report:
        """Create a new report"""
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def get_report(self, report_id: UUID) -> Optional[Report]:
        """Get a report by ID"""
        query = select(Report).where(Report.id == report_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_reports(
        self,
        user_id: Optional[UUID] = None,
        event_id: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Report]:
        """Get reports with filters"""
        query = select(Report)

        if user_id:
            query = query.where(Report.created_by == user_id)
        if event_id:
            query = query.where(Report.event_id == event_id)
        if status:
            query = query.where(Report.status == status)

        query = query.order_by(desc(Report.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_report_status(
        self,
        report_id: UUID,
        status: str,
        data: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> Optional[Report]:
        """Update report status"""
        report = await self.get_report(report_id)
        if not report:
            return None

        report.status = status
        if status == ReportStatus.GENERATING.value:
            report.started_at = datetime.utcnow()
        elif status == ReportStatus.COMPLETED.value:
            report.completed_at = datetime.utcnow()
            if data:
                report.data = data
        elif status == ReportStatus.FAILED.value:
            report.failed_at = datetime.utcnow()
            report.error_message = error

        report.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(report)
        return report

    # ========================================================================
    # Metric Operations
    # ========================================================================

    async def create_metric(self, metric: Metric) -> Metric:
        """Create a new metric"""
        self.db.add(metric)
        await self.db.flush()
        await self.db.refresh(metric)
        return metric

    async def get_metrics(
        self,
        name: Optional[str] = None,
        category: Optional[str] = None,
        event_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Metric]:
        """Get metrics with filters"""
        query = select(Metric)

        if name:
            query = query.where(Metric.name == name)
        if category:
            query = query.where(Metric.category == category)
        if event_id:
            query = query.where(Metric.event_id == event_id)
        if start_date:
            query = query.where(Metric.measured_at >= start_date)
        if end_date:
            query = query.where(Metric.measured_at <= end_date)

        query = query.order_by(desc(Metric.measured_at)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Dashboard Operations
    # ========================================================================

    async def create_dashboard(self, dashboard: Dashboard) -> Dashboard:
        """Create a new dashboard"""
        self.db.add(dashboard)
        await self.db.flush()
        await self.db.refresh(dashboard)
        return dashboard

    async def get_dashboard(self, dashboard_id: UUID) -> Optional[Dashboard]:
        """Get a dashboard by ID"""
        query = select(Dashboard).where(Dashboard.id == dashboard_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_dashboards(
        self,
        user_id: Optional[UUID] = None,
        event_id: Optional[UUID] = None,
        dashboard_type: Optional[str] = None
    ) -> List[Dashboard]:
        """Get dashboards with filters"""
        query = select(Dashboard)

        if user_id:
            query = query.where(Dashboard.created_by == user_id)
        if event_id:
            query = query.where(Dashboard.event_id == event_id)
        if dashboard_type:
            query = query.where(Dashboard.dashboard_type == dashboard_type)

        query = query.order_by(desc(Dashboard.created_at))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_dashboard(self, dashboard_id: UUID, update_data: Dict) -> Optional[Dashboard]:
        """Update a dashboard"""
        dashboard = await self.get_dashboard(dashboard_id)
        if not dashboard:
            return None

        for key, value in update_data.items():
            if hasattr(dashboard, key):
                setattr(dashboard, key, value)

        dashboard.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(dashboard)
        return dashboard

    async def delete_dashboard(self, dashboard_id: UUID) -> bool:
        """Delete a dashboard"""
        dashboard = await self.get_dashboard(dashboard_id)
        if not dashboard:
            return False

        await self.db.delete(dashboard)
        await self.db.flush()
        return True

    # ========================================================================
    # Audit Log Operations
    # ========================================================================

    async def create_audit_log(self, audit_log: AuditLog) -> AuditLog:
        """Create an audit log entry"""
        self.db.add(audit_log)
        await self.db.flush()
        await self.db.refresh(audit_log)
        return audit_log

    async def get_audit_logs(
        self,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
        category: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs with filters"""
        query = select(AuditLog)

        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if category:
            query = query.where(AuditLog.category == category)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)

        query = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
