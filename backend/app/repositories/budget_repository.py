"""
CelebraTech Event Management System - Budget Repository
Sprint 15: Budget Management System
Data access layer for budget and expense operations
"""
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from app.models.budget import (
    Budget,
    BudgetCategory,
    BudgetItem,
    BudgetAllocation,
    Expense,
    ExpenseCategory,
    PaymentSchedule,
    Invoice,
    InvoiceItem,
    CostEstimate,
    BudgetAlert,
    FinancialReport,
    BudgetTemplate,
    BudgetStatus,
    ExpenseStatus
)
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    ExpenseCreate,
    ExpenseUpdate,
    InvoiceCreate
)


class BudgetRepository:
    """Repository for budget database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Budget CRUD Operations
    # ========================================================================

    async def create_budget(
        self,
        budget_data: BudgetCreate,
        user_id: UUID
    ) -> Budget:
        """Create a new budget"""
        budget = Budget(
            event_id=budget_data.event_id,
            name=budget_data.name,
            description=budget_data.description,
            total_amount=budget_data.total_amount,
            currency=budget_data.currency,
            buffer_percentage=budget_data.buffer_percentage,
            notes=budget_data.notes,
            status=BudgetStatus.DRAFT,
            created_by=user_id
        )

        self.db.add(budget)
        await self.db.flush()
        await self.db.refresh(budget)

        return budget

    async def get_budget_by_id(self, budget_id: UUID) -> Optional[Budget]:
        """Get budget by ID"""
        query = select(Budget).where(Budget.id == budget_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_budget_by_event(self, event_id: UUID) -> Optional[Budget]:
        """Get budget for a specific event"""
        query = select(Budget).where(Budget.event_id == event_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_budget(
        self,
        budget_id: UUID,
        budget_data: BudgetUpdate
    ) -> Optional[Budget]:
        """Update a budget"""
        budget = await self.get_budget_by_id(budget_id)
        if not budget:
            return None

        update_data = budget_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(budget, field, value)

        budget.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(budget)

        return budget

    async def get_budget_summary(self, budget_id: UUID) -> Dict[str, Any]:
        """Get budget summary with totals"""
        budget = await self.get_budget_by_id(budget_id)
        if not budget:
            return {}

        # Get total expenses
        expense_query = select(func.sum(Expense.amount)).where(
            and_(
                Expense.budget_id == budget_id,
                Expense.status.in_([ExpenseStatus.APPROVED, ExpenseStatus.PAID])
            )
        )
        expense_result = await self.db.execute(expense_query)
        total_spent = expense_result.scalar() or Decimal(0)

        # Get budget categories
        category_query = select(BudgetCategory).where(
            BudgetCategory.budget_id == budget_id
        )
        category_result = await self.db.execute(category_query)
        categories = category_result.scalars().all()

        remaining = budget.total_amount - total_spent
        percentage_used = (float(total_spent) / float(budget.total_amount) * 100) if budget.total_amount > 0 else 0

        return {
            "budget_id": str(budget.id),
            "total_amount": float(budget.total_amount),
            "total_spent": float(total_spent),
            "remaining": float(remaining),
            "percentage_used": percentage_used,
            "currency": budget.currency,
            "status": budget.status,
            "categories_count": len(categories)
        }

    # ========================================================================
    # Budget Category Operations
    # ========================================================================

    async def create_budget_category(
        self,
        budget_id: UUID,
        name: str,
        allocated_amount: Decimal,
        description: Optional[str] = None
    ) -> BudgetCategory:
        """Create a budget category"""
        category = BudgetCategory(
            budget_id=budget_id,
            name=name,
            description=description,
            allocated_amount=allocated_amount,
            spent_amount=Decimal(0)
        )

        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)

        return category

    async def get_budget_categories(self, budget_id: UUID) -> List[BudgetCategory]:
        """Get all categories for a budget"""
        query = select(BudgetCategory).where(
            BudgetCategory.budget_id == budget_id
        ).order_by(BudgetCategory.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Expense CRUD Operations
    # ========================================================================

    async def create_expense(
        self,
        expense_data: ExpenseCreate,
        user_id: UUID
    ) -> Expense:
        """Create a new expense"""
        expense = Expense(
            budget_id=expense_data.budget_id,
            category_id=expense_data.category_id,
            vendor_id=expense_data.vendor_id,
            booking_id=expense_data.booking_id,
            title=expense_data.title,
            description=expense_data.description,
            amount=expense_data.amount,
            expense_type=expense_data.expense_type,
            expense_date=expense_data.expense_date or datetime.utcnow(),
            payment_method=expense_data.payment_method,
            receipt_url=expense_data.receipt_url,
            notes=expense_data.notes,
            metadata=expense_data.metadata,
            status=ExpenseStatus.PENDING,
            created_by=user_id
        )

        self.db.add(expense)
        await self.db.flush()
        await self.db.refresh(expense)

        return expense

    async def get_expense_by_id(self, expense_id: UUID) -> Optional[Expense]:
        """Get expense by ID"""
        query = select(Expense).where(Expense.id == expense_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_budget_expenses(
        self,
        budget_id: UUID,
        status: Optional[ExpenseStatus] = None,
        category_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Expense], int]:
        """Get expenses for a budget with filters"""
        query = select(Expense).where(Expense.budget_id == budget_id)

        if status:
            query = query.where(Expense.status == status)
        if category_id:
            query = query.where(Expense.category_id == category_id)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get paginated results
        query = query.order_by(Expense.expense_date.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        expenses = list(result.scalars().all())

        return expenses, total

    async def update_expense(
        self,
        expense_id: UUID,
        expense_data: ExpenseUpdate
    ) -> Optional[Expense]:
        """Update an expense"""
        expense = await self.get_expense_by_id(expense_id)
        if not expense:
            return None

        update_data = expense_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(expense, field, value)

        expense.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(expense)

        return expense

    async def approve_expense(self, expense_id: UUID, approved_by: UUID) -> Optional[Expense]:
        """Approve an expense"""
        expense = await self.get_expense_by_id(expense_id)
        if not expense:
            return None

        expense.status = ExpenseStatus.APPROVED
        expense.approved_by = approved_by
        expense.approved_at = datetime.utcnow()
        expense.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(expense)

        return expense

    async def mark_expense_paid(self, expense_id: UUID) -> Optional[Expense]:
        """Mark expense as paid"""
        expense = await self.get_expense_by_id(expense_id)
        if not expense:
            return None

        expense.status = ExpenseStatus.PAID
        expense.paid_at = datetime.utcnow()
        expense.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(expense)

        return expense

    # ========================================================================
    # Invoice Operations
    # ========================================================================

    async def create_invoice(
        self,
        invoice_data: InvoiceCreate,
        user_id: UUID
    ) -> Invoice:
        """Create a new invoice"""
        invoice = Invoice(
            budget_id=invoice_data.budget_id,
            vendor_id=invoice_data.vendor_id,
            invoice_number=invoice_data.invoice_number,
            invoice_date=invoice_data.invoice_date,
            due_date=invoice_data.due_date,
            subtotal=invoice_data.subtotal,
            tax_amount=invoice_data.tax_amount,
            total_amount=invoice_data.total_amount,
            currency=invoice_data.currency,
            notes=invoice_data.notes,
            status="pending",
            created_by=user_id
        )

        self.db.add(invoice)
        await self.db.flush()

        # Create invoice items if provided
        if invoice_data.items:
            for item_data in invoice_data.items:
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=item_data.description,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    amount=item_data.amount
                )
                self.db.add(invoice_item)

        await self.db.flush()
        await self.db.refresh(invoice)

        return invoice

    async def get_invoice_by_id(self, invoice_id: UUID) -> Optional[Invoice]:
        """Get invoice by ID"""
        query = select(Invoice).where(Invoice.id == invoice_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_budget_invoices(self, budget_id: UUID) -> List[Invoice]:
        """Get all invoices for a budget"""
        query = select(Invoice).where(
            Invoice.budget_id == budget_id
        ).order_by(Invoice.invoice_date.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Payment Schedule Operations
    # ========================================================================

    async def create_payment_schedule(
        self,
        budget_id: UUID,
        vendor_id: UUID,
        amount: Decimal,
        due_date: datetime,
        description: Optional[str] = None
    ) -> PaymentSchedule:
        """Create a payment schedule"""
        schedule = PaymentSchedule(
            budget_id=budget_id,
            vendor_id=vendor_id,
            amount=amount,
            due_date=due_date,
            description=description,
            status="pending"
        )

        self.db.add(schedule)
        await self.db.flush()
        await self.db.refresh(schedule)

        return schedule

    async def get_upcoming_payments(
        self,
        budget_id: UUID,
        days_ahead: int = 30
    ) -> List[PaymentSchedule]:
        """Get upcoming payments"""
        future_date = datetime.utcnow() + timedelta(days=days_ahead)

        query = select(PaymentSchedule).where(
            and_(
                PaymentSchedule.budget_id == budget_id,
                PaymentSchedule.status == "pending",
                PaymentSchedule.due_date <= future_date
            )
        ).order_by(PaymentSchedule.due_date)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Budget Alert Operations
    # ========================================================================

    async def create_budget_alert(
        self,
        budget_id: UUID,
        alert_type: str,
        threshold_percentage: float,
        message: str
    ) -> BudgetAlert:
        """Create a budget alert"""
        alert = BudgetAlert(
            budget_id=budget_id,
            alert_type=alert_type,
            threshold_percentage=threshold_percentage,
            message=message,
            is_triggered=False
        )

        self.db.add(alert)
        await self.db.flush()
        await self.db.refresh(alert)

        return alert

    async def check_budget_thresholds(self, budget_id: UUID) -> List[BudgetAlert]:
        """Check if any budget thresholds are exceeded"""
        budget_summary = await self.get_budget_summary(budget_id)
        percentage_used = budget_summary.get("percentage_used", 0)

        query = select(BudgetAlert).where(
            and_(
                BudgetAlert.budget_id == budget_id,
                BudgetAlert.is_triggered == False,
                BudgetAlert.threshold_percentage <= percentage_used
            )
        )

        result = await self.db.execute(query)
        alerts = result.scalars().all()

        # Mark alerts as triggered
        for alert in alerts:
            alert.is_triggered = True
            alert.triggered_at = datetime.utcnow()

        await self.db.flush()

        return list(alerts)

    # ========================================================================
    # Financial Report Operations
    # ========================================================================

    async def generate_financial_report(
        self,
        budget_id: UUID,
        report_type: str,
        user_id: UUID
    ) -> FinancialReport:
        """Generate a financial report"""
        budget_summary = await self.get_budget_summary(budget_id)
        categories = await self.get_budget_categories(budget_id)

        category_breakdown = []
        for category in categories:
            category_breakdown.append({
                "name": category.name,
                "allocated": float(category.allocated_amount),
                "spent": float(category.spent_amount),
                "remaining": float(category.allocated_amount - category.spent_amount)
            })

        report_data = {
            "summary": budget_summary,
            "categories": category_breakdown,
            "generated_at": datetime.utcnow().isoformat()
        }

        report = FinancialReport(
            budget_id=budget_id,
            report_type=report_type,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
            report_data=report_data,
            generated_by=user_id
        )

        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)

        return report

    async def get_financial_reports(self, budget_id: UUID) -> List[FinancialReport]:
        """Get all financial reports for a budget"""
        query = select(FinancialReport).where(
            FinancialReport.budget_id == budget_id
        ).order_by(FinancialReport.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Budget Template Operations
    # ========================================================================

    async def create_budget_template(
        self,
        name: str,
        event_type: str,
        template_data: Dict[str, Any],
        user_id: UUID
    ) -> BudgetTemplate:
        """Create a budget template"""
        template = BudgetTemplate(
            name=name,
            event_type=event_type,
            template_data=template_data,
            created_by=user_id
        )

        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)

        return template

    async def get_budget_templates(
        self,
        event_type: Optional[str] = None
    ) -> List[BudgetTemplate]:
        """Get budget templates"""
        query = select(BudgetTemplate)

        if event_type:
            query = query.where(BudgetTemplate.event_type == event_type)

        query = query.order_by(BudgetTemplate.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())
