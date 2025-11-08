"""
CelebraTech Event Management System - Budget API
Sprint 15: Budget Management System
FastAPI endpoints for budget and expense management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.budget import ExpenseStatus
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
    BudgetSummaryResponse,
    BudgetCategoryCreate,
    BudgetCategoryResponse,
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseListResponse,
    InvoiceCreate,
    InvoiceResponse,
    PaymentScheduleCreate,
    PaymentScheduleResponse,
    BudgetAlertCreate,
    BudgetAlertResponse,
    FinancialReportResponse,
    BudgetTemplateCreate,
    BudgetTemplateResponse
)
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/budget", tags=["Budget Management"])


# ============================================================================
# Budget Endpoints
# ============================================================================

@router.post(
    "/budgets",
    response_model=BudgetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create budget",
    description="Create a new budget for an event"
)
async def create_budget(
    budget_data: BudgetCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new budget for an event"""
    budget_service = BudgetService(db)
    budget = await budget_service.create_budget(budget_data, current_user)
    return BudgetResponse.from_orm(budget)


@router.get(
    "/budgets/{budget_id}",
    response_model=BudgetResponse,
    summary="Get budget",
    description="Get budget details by ID"
)
async def get_budget(
    budget_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get budget by ID"""
    budget_service = BudgetService(db)
    budget = await budget_service.get_budget(budget_id, current_user)
    return BudgetResponse.from_orm(budget)


@router.get(
    "/events/{event_id}/budget",
    response_model=BudgetResponse,
    summary="Get event budget",
    description="Get the budget for a specific event"
)
async def get_event_budget(
    event_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get budget for a specific event"""
    budget_service = BudgetService(db)
    budget = await budget_service.get_event_budget(event_id, current_user)

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found for this event"
        )

    return BudgetResponse.from_orm(budget)


@router.put(
    "/budgets/{budget_id}",
    response_model=BudgetResponse,
    summary="Update budget",
    description="Update budget properties"
)
async def update_budget(
    budget_id: UUID,
    budget_data: BudgetUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a budget"""
    budget_service = BudgetService(db)
    budget = await budget_service.update_budget(budget_id, budget_data, current_user)
    return BudgetResponse.from_orm(budget)


@router.get(
    "/budgets/{budget_id}/summary",
    response_model=BudgetSummaryResponse,
    summary="Get budget summary",
    description="Get budget summary with totals and percentages"
)
async def get_budget_summary(
    budget_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get budget summary"""
    budget_service = BudgetService(db)
    summary = await budget_service.get_budget_summary(budget_id, current_user)
    return summary


# ============================================================================
# Budget Category Endpoints
# ============================================================================

@router.post(
    "/budgets/{budget_id}/categories",
    response_model=BudgetCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create budget category",
    description="Create a new budget category"
)
async def create_budget_category(
    budget_id: UUID,
    category_data: BudgetCategoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a budget category"""
    budget_service = BudgetService(db)
    category = await budget_service.create_budget_category(
        budget_id,
        category_data.name,
        category_data.allocated_amount,
        category_data.description,
        current_user
    )
    return BudgetCategoryResponse.from_orm(category)


@router.get(
    "/budgets/{budget_id}/categories",
    response_model=List[BudgetCategoryResponse],
    summary="Get budget categories",
    description="Get all categories for a budget"
)
async def get_budget_categories(
    budget_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get budget categories"""
    budget_service = BudgetService(db)
    categories = await budget_service.get_budget_categories(budget_id, current_user)
    return [BudgetCategoryResponse.from_orm(c) for c in categories]


# ============================================================================
# Expense Endpoints
# ============================================================================

@router.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create expense",
    description="Create a new expense record"
)
async def create_expense(
    expense_data: ExpenseCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new expense"""
    budget_service = BudgetService(db)
    expense = await budget_service.create_expense(expense_data, current_user)
    return ExpenseResponse.from_orm(expense)


@router.get(
    "/expenses/{expense_id}",
    response_model=ExpenseResponse,
    summary="Get expense",
    description="Get expense details by ID"
)
async def get_expense(
    expense_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get expense by ID"""
    budget_service = BudgetService(db)
    expense = await budget_service.get_expense(expense_id, current_user)
    return ExpenseResponse.from_orm(expense)


@router.get(
    "/budgets/{budget_id}/expenses",
    response_model=ExpenseListResponse,
    summary="Get budget expenses",
    description="Get all expenses for a budget with filtering"
)
async def get_budget_expenses(
    budget_id: UUID,
    status_filter: Optional[ExpenseStatus] = Query(None, description="Filter by status"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get expenses for a budget"""
    budget_service = BudgetService(db)
    expenses, total = await budget_service.get_budget_expenses(
        budget_id,
        current_user,
        status_filter,
        category_id,
        page,
        page_size
    )

    return ExpenseListResponse(
        expenses=[ExpenseResponse.from_orm(e) for e in expenses],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.put(
    "/expenses/{expense_id}",
    response_model=ExpenseResponse,
    summary="Update expense",
    description="Update expense details"
)
async def update_expense(
    expense_id: UUID,
    expense_data: ExpenseUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an expense"""
    budget_service = BudgetService(db)
    expense = await budget_service.update_expense(expense_id, expense_data, current_user)
    return ExpenseResponse.from_orm(expense)


@router.post(
    "/expenses/{expense_id}/approve",
    response_model=ExpenseResponse,
    summary="Approve expense",
    description="Approve a pending expense"
)
async def approve_expense(
    expense_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve an expense"""
    budget_service = BudgetService(db)
    expense = await budget_service.approve_expense(expense_id, current_user)
    return ExpenseResponse.from_orm(expense)


@router.post(
    "/expenses/{expense_id}/mark-paid",
    response_model=ExpenseResponse,
    summary="Mark expense as paid",
    description="Mark an approved expense as paid"
)
async def mark_expense_paid(
    expense_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark expense as paid"""
    budget_service = BudgetService(db)
    expense = await budget_service.mark_expense_paid(expense_id, current_user)
    return ExpenseResponse.from_orm(expense)


# ============================================================================
# Invoice Endpoints
# ============================================================================

@router.post(
    "/invoices",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create invoice",
    description="Create a new invoice"
)
async def create_invoice(
    invoice_data: InvoiceCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new invoice"""
    budget_service = BudgetService(db)
    invoice = await budget_service.create_invoice(invoice_data, current_user)
    return InvoiceResponse.from_orm(invoice)


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get invoice",
    description="Get invoice details by ID"
)
async def get_invoice(
    invoice_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get invoice by ID"""
    budget_service = BudgetService(db)
    invoice = await budget_service.get_invoice(invoice_id, current_user)
    return InvoiceResponse.from_orm(invoice)


@router.get(
    "/budgets/{budget_id}/invoices",
    response_model=List[InvoiceResponse],
    summary="Get budget invoices",
    description="Get all invoices for a budget"
)
async def get_budget_invoices(
    budget_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get invoices for a budget"""
    budget_service = BudgetService(db)
    invoices = await budget_service.get_budget_invoices(budget_id, current_user)
    return [InvoiceResponse.from_orm(i) for i in invoices]


# ============================================================================
# Payment Schedule Endpoints
# ============================================================================

@router.post(
    "/budgets/{budget_id}/payment-schedules",
    response_model=PaymentScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create payment schedule",
    description="Create a new payment schedule"
)
async def create_payment_schedule(
    budget_id: UUID,
    schedule_data: PaymentScheduleCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a payment schedule"""
    budget_service = BudgetService(db)
    schedule = await budget_service.create_payment_schedule(
        budget_id,
        schedule_data.vendor_id,
        schedule_data.amount,
        schedule_data.due_date,
        schedule_data.description,
        current_user
    )
    return PaymentScheduleResponse.from_orm(schedule)


@router.get(
    "/budgets/{budget_id}/upcoming-payments",
    response_model=List[PaymentScheduleResponse],
    summary="Get upcoming payments",
    description="Get upcoming payment schedules"
)
async def get_upcoming_payments(
    budget_id: UUID,
    days_ahead: int = Query(30, ge=1, le=365, description="Days to look ahead"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get upcoming payments"""
    budget_service = BudgetService(db)
    payments = await budget_service.get_upcoming_payments(
        budget_id,
        current_user,
        days_ahead
    )
    return [PaymentScheduleResponse.from_orm(p) for p in payments]


# ============================================================================
# Budget Alert Endpoints
# ============================================================================

@router.post(
    "/budgets/{budget_id}/alerts",
    response_model=BudgetAlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create budget alert",
    description="Create a budget threshold alert"
)
async def create_budget_alert(
    budget_id: UUID,
    alert_data: BudgetAlertCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a budget alert"""
    budget_service = BudgetService(db)
    alert = await budget_service.create_budget_alert(
        budget_id,
        alert_data.alert_type,
        alert_data.threshold_percentage,
        alert_data.message,
        current_user
    )
    return BudgetAlertResponse.from_orm(alert)


@router.get(
    "/budgets/{budget_id}/check-alerts",
    response_model=List[BudgetAlertResponse],
    summary="Check budget alerts",
    description="Check if any budget alerts are triggered"
)
async def check_budget_alerts(
    budget_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Check budget alerts"""
    budget_service = BudgetService(db)
    alerts = await budget_service.check_budget_alerts(budget_id, current_user)
    return [BudgetAlertResponse.from_orm(a) for a in alerts]


# ============================================================================
# Financial Report Endpoints
# ============================================================================

@router.post(
    "/budgets/{budget_id}/reports",
    response_model=FinancialReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate financial report",
    description="Generate a financial report for the budget"
)
async def generate_financial_report(
    budget_id: UUID,
    report_type: str = Query(..., description="Report type (summary, detailed, forecast)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a financial report"""
    budget_service = BudgetService(db)
    report = await budget_service.generate_financial_report(
        budget_id,
        report_type,
        current_user
    )
    return FinancialReportResponse.from_orm(report)


@router.get(
    "/budgets/{budget_id}/reports",
    response_model=List[FinancialReportResponse],
    summary="Get financial reports",
    description="Get all financial reports for a budget"
)
async def get_financial_reports(
    budget_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get financial reports"""
    budget_service = BudgetService(db)
    reports = await budget_service.get_financial_reports(budget_id, current_user)
    return [FinancialReportResponse.from_orm(r) for r in reports]


# ============================================================================
# Budget Template Endpoints
# ============================================================================

@router.post(
    "/templates",
    response_model=BudgetTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create budget template",
    description="Create a reusable budget template"
)
async def create_budget_template(
    template_data: BudgetTemplateCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a budget template"""
    budget_service = BudgetService(db)
    template = await budget_service.create_budget_template(
        template_data.name,
        template_data.event_type,
        template_data.template_data,
        current_user
    )
    return BudgetTemplateResponse.from_orm(template)


@router.get(
    "/templates",
    response_model=List[BudgetTemplateResponse],
    summary="Get budget templates",
    description="Get all budget templates"
)
async def get_budget_templates(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: AsyncSession = Depends(get_db)
):
    """Get budget templates"""
    budget_service = BudgetService(db)
    templates = await budget_service.get_budget_templates(event_type)
    return [BudgetTemplateResponse.from_orm(t) for t in templates]
