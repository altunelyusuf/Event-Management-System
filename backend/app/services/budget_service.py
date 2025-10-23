"""
CelebraTech Event Management System - Budget Service
Sprint 15: Budget Management System
Business logic for budget and expense operations
"""
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from app.models.budget import (
    Budget,
    BudgetCategory,
    Expense,
    Invoice,
    PaymentSchedule,
    BudgetAlert,
    FinancialReport,
    BudgetTemplate,
    BudgetStatus,
    ExpenseStatus
)
from app.models.user import User
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    ExpenseCreate,
    ExpenseUpdate,
    InvoiceCreate
)
from app.repositories.budget_repository import BudgetRepository


class BudgetService:
    """Service for budget operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.budget_repo = BudgetRepository(db)

    # ========================================================================
    # Budget Operations
    # ========================================================================

    async def create_budget(
        self,
        budget_data: BudgetCreate,
        current_user: User
    ) -> Budget:
        """Create a new budget"""
        # TODO: Verify user has permission for this event
        budget = await self.budget_repo.create_budget(
            budget_data,
            current_user.id
        )

        await self.db.commit()
        return budget

    async def get_budget(
        self,
        budget_id: UUID,
        current_user: User
    ) -> Budget:
        """Get budget by ID with permission check"""
        budget = await self.budget_repo.get_budget_by_id(budget_id)

        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found"
            )

        # TODO: Check permission
        return budget

    async def get_event_budget(
        self,
        event_id: UUID,
        current_user: User
    ) -> Optional[Budget]:
        """Get budget for a specific event"""
        budget = await self.budget_repo.get_budget_by_event(event_id)
        # TODO: Check permission
        return budget

    async def update_budget(
        self,
        budget_id: UUID,
        budget_data: BudgetUpdate,
        current_user: User
    ) -> Budget:
        """Update a budget"""
        budget = await self.get_budget(budget_id, current_user)

        updated_budget = await self.budget_repo.update_budget(
            budget_id,
            budget_data
        )

        await self.db.commit()
        return updated_budget

    async def get_budget_summary(
        self,
        budget_id: UUID,
        current_user: User
    ) -> Dict[str, Any]:
        """Get budget summary with totals"""
        await self.get_budget(budget_id, current_user)

        summary = await self.budget_repo.get_budget_summary(budget_id)
        return summary

    # ========================================================================
    # Budget Category Operations
    # ========================================================================

    async def create_budget_category(
        self,
        budget_id: UUID,
        name: str,
        allocated_amount: Decimal,
        description: Optional[str],
        current_user: User
    ) -> BudgetCategory:
        """Create a budget category"""
        await self.get_budget(budget_id, current_user)

        category = await self.budget_repo.create_budget_category(
            budget_id,
            name,
            allocated_amount,
            description
        )

        await self.db.commit()
        return category

    async def get_budget_categories(
        self,
        budget_id: UUID,
        current_user: User
    ) -> List[BudgetCategory]:
        """Get all categories for a budget"""
        await self.get_budget(budget_id, current_user)

        categories = await self.budget_repo.get_budget_categories(budget_id)
        return categories

    # ========================================================================
    # Expense Operations
    # ========================================================================

    async def create_expense(
        self,
        expense_data: ExpenseCreate,
        current_user: User
    ) -> Expense:
        """Create a new expense"""
        await self.get_budget(expense_data.budget_id, current_user)

        expense = await self.budget_repo.create_expense(
            expense_data,
            current_user.id
        )

        # Check budget alerts
        await self.budget_repo.check_budget_thresholds(expense_data.budget_id)

        await self.db.commit()
        return expense

    async def get_expense(
        self,
        expense_id: UUID,
        current_user: User
    ) -> Expense:
        """Get expense by ID"""
        expense = await self.budget_repo.get_expense_by_id(expense_id)

        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found"
            )

        # Verify access to budget
        await self.get_budget(expense.budget_id, current_user)

        return expense

    async def get_budget_expenses(
        self,
        budget_id: UUID,
        current_user: User,
        status_filter: Optional[ExpenseStatus] = None,
        category_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[Expense], int]:
        """Get expenses for a budget with filters"""
        await self.get_budget(budget_id, current_user)

        offset = (page - 1) * page_size

        expenses, total = await self.budget_repo.get_budget_expenses(
            budget_id,
            status_filter,
            category_id,
            page_size,
            offset
        )

        return expenses, total

    async def update_expense(
        self,
        expense_id: UUID,
        expense_data: ExpenseUpdate,
        current_user: User
    ) -> Expense:
        """Update an expense"""
        expense = await self.get_expense(expense_id, current_user)

        updated_expense = await self.budget_repo.update_expense(
            expense_id,
            expense_data
        )

        await self.db.commit()
        return updated_expense

    async def approve_expense(
        self,
        expense_id: UUID,
        current_user: User
    ) -> Expense:
        """Approve an expense"""
        expense = await self.get_expense(expense_id, current_user)

        approved_expense = await self.budget_repo.approve_expense(
            expense_id,
            current_user.id
        )

        await self.db.commit()
        return approved_expense

    async def mark_expense_paid(
        self,
        expense_id: UUID,
        current_user: User
    ) -> Expense:
        """Mark expense as paid"""
        expense = await self.get_expense(expense_id, current_user)

        paid_expense = await self.budget_repo.mark_expense_paid(expense_id)

        await self.db.commit()
        return paid_expense

    # ========================================================================
    # Invoice Operations
    # ========================================================================

    async def create_invoice(
        self,
        invoice_data: InvoiceCreate,
        current_user: User
    ) -> Invoice:
        """Create a new invoice"""
        await self.get_budget(invoice_data.budget_id, current_user)

        invoice = await self.budget_repo.create_invoice(
            invoice_data,
            current_user.id
        )

        await self.db.commit()
        return invoice

    async def get_invoice(
        self,
        invoice_id: UUID,
        current_user: User
    ) -> Invoice:
        """Get invoice by ID"""
        invoice = await self.budget_repo.get_invoice_by_id(invoice_id)

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )

        await self.get_budget(invoice.budget_id, current_user)

        return invoice

    async def get_budget_invoices(
        self,
        budget_id: UUID,
        current_user: User
    ) -> List[Invoice]:
        """Get all invoices for a budget"""
        await self.get_budget(budget_id, current_user)

        invoices = await self.budget_repo.get_budget_invoices(budget_id)
        return invoices

    # ========================================================================
    # Payment Schedule Operations
    # ========================================================================

    async def create_payment_schedule(
        self,
        budget_id: UUID,
        vendor_id: UUID,
        amount: Decimal,
        due_date: datetime,
        description: Optional[str],
        current_user: User
    ) -> PaymentSchedule:
        """Create a payment schedule"""
        await self.get_budget(budget_id, current_user)

        schedule = await self.budget_repo.create_payment_schedule(
            budget_id,
            vendor_id,
            amount,
            due_date,
            description
        )

        await self.db.commit()
        return schedule

    async def get_upcoming_payments(
        self,
        budget_id: UUID,
        current_user: User,
        days_ahead: int = 30
    ) -> List[PaymentSchedule]:
        """Get upcoming payments"""
        await self.get_budget(budget_id, current_user)

        payments = await self.budget_repo.get_upcoming_payments(
            budget_id,
            days_ahead
        )

        return payments

    # ========================================================================
    # Budget Alert Operations
    # ========================================================================

    async def create_budget_alert(
        self,
        budget_id: UUID,
        alert_type: str,
        threshold_percentage: float,
        message: str,
        current_user: User
    ) -> BudgetAlert:
        """Create a budget alert"""
        await self.get_budget(budget_id, current_user)

        alert = await self.budget_repo.create_budget_alert(
            budget_id,
            alert_type,
            threshold_percentage,
            message
        )

        await self.db.commit()
        return alert

    async def check_budget_alerts(
        self,
        budget_id: UUID,
        current_user: User
    ) -> List[BudgetAlert]:
        """Check if any budget alerts are triggered"""
        await self.get_budget(budget_id, current_user)

        alerts = await self.budget_repo.check_budget_thresholds(budget_id)

        if alerts:
            await self.db.commit()

        return alerts

    # ========================================================================
    # Financial Report Operations
    # ========================================================================

    async def generate_financial_report(
        self,
        budget_id: UUID,
        report_type: str,
        current_user: User
    ) -> FinancialReport:
        """Generate a financial report"""
        await self.get_budget(budget_id, current_user)

        report = await self.budget_repo.generate_financial_report(
            budget_id,
            report_type,
            current_user.id
        )

        await self.db.commit()
        return report

    async def get_financial_reports(
        self,
        budget_id: UUID,
        current_user: User
    ) -> List[FinancialReport]:
        """Get all financial reports for a budget"""
        await self.get_budget(budget_id, current_user)

        reports = await self.budget_repo.get_financial_reports(budget_id)
        return reports

    # ========================================================================
    # Budget Template Operations
    # ========================================================================

    async def create_budget_template(
        self,
        name: str,
        event_type: str,
        template_data: Dict[str, Any],
        current_user: User
    ) -> BudgetTemplate:
        """Create a budget template"""
        template = await self.budget_repo.create_budget_template(
            name,
            event_type,
            template_data,
            current_user.id
        )

        await self.db.commit()
        return template

    async def get_budget_templates(
        self,
        event_type: Optional[str] = None
    ) -> List[BudgetTemplate]:
        """Get budget templates"""
        templates = await self.budget_repo.get_budget_templates(event_type)
        return templates
