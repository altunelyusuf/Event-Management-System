"""
CelebraTech Event Management System - Booking Repository
Sprint 4: Booking & Quote System
FR-004: Booking & Quote Management
Data access layer for booking operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from app.models.booking import (
    BookingRequest,
    Quote,
    QuoteItem,
    Booking,
    BookingPayment,
    BookingCancellation,
    BookingRequestStatus,
    BookingStatus,
    PaymentStatus,
    QuoteStatus,
    CancellationInitiator
)
from app.models.vendor import Vendor
from app.schemas.booking import (
    BookingRequestCreate,
    BookingRequestUpdate,
    QuoteCreate,
    QuoteUpdate,
    QuoteItemCreate,
    BookingUpdate,
    PaymentCreate,
    CancellationCreate,
    BookingRequestFilters,
    BookingFilters
)


class BookingRepository:
    """Repository for booking data access"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Booking Request Operations
    # ========================================================================

    async def create_booking_request(
        self,
        event_id: str,
        organizer_id: str,
        request_data: BookingRequestCreate
    ) -> BookingRequest:
        """Create a new booking request"""
        # Calculate expiration date (default 30 days)
        expires_at = datetime.utcnow() + timedelta(days=30)

        booking_request = BookingRequest(
            event_id=UUID(event_id),
            vendor_id=request_data.vendor_id,
            organizer_id=UUID(organizer_id),
            title=request_data.title,
            description=request_data.description,
            event_date=request_data.event_date,
            event_end_date=request_data.event_end_date,
            venue_name=request_data.venue_name,
            venue_address=request_data.venue_address,
            guest_count=request_data.guest_count,
            service_category=request_data.service_category,
            specific_services=request_data.specific_services,
            special_requirements=request_data.special_requirements,
            budget_min=request_data.budget_min,
            budget_max=request_data.budget_max,
            response_deadline=request_data.response_deadline,
            expires_at=expires_at,
            preferred_contact_method=request_data.preferred_contact_method,
            contact_notes=request_data.contact_notes,
            status=BookingRequestStatus.PENDING
        )

        self.db.add(booking_request)
        await self.db.commit()
        await self.db.refresh(booking_request)

        return booking_request

    async def get_booking_request_by_id(
        self,
        request_id: str
    ) -> Optional[BookingRequest]:
        """Get booking request by ID"""
        query = select(BookingRequest).where(
            and_(
                BookingRequest.id == UUID(request_id),
                BookingRequest.deleted_at.is_(None)
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_booking_request(
        self,
        request_id: str,
        request_data: BookingRequestUpdate
    ) -> Optional[BookingRequest]:
        """Update booking request"""
        booking_request = await self.get_booking_request_by_id(request_id)
        if not booking_request:
            return None

        update_data = request_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(booking_request, field, value)

        await self.db.commit()
        await self.db.refresh(booking_request)

        return booking_request

    async def mark_as_viewed(self, request_id: str) -> bool:
        """Mark booking request as viewed by vendor"""
        booking_request = await self.get_booking_request_by_id(request_id)
        if not booking_request:
            return False

        booking_request.viewed_by_vendor = True
        booking_request.viewed_at = datetime.utcnow()

        await self.db.commit()
        return True

    async def get_booking_requests_for_event(
        self,
        event_id: str
    ) -> List[BookingRequest]:
        """Get all booking requests for an event"""
        query = select(BookingRequest).where(
            and_(
                BookingRequest.event_id == UUID(event_id),
                BookingRequest.deleted_at.is_(None)
            )
        ).order_by(BookingRequest.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_booking_requests_for_vendor(
        self,
        vendor_id: str,
        filters: Optional[BookingRequestFilters] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[BookingRequest], int]:
        """Get booking requests for vendor with filters"""
        query = select(BookingRequest).where(
            and_(
                BookingRequest.vendor_id == UUID(vendor_id),
                BookingRequest.deleted_at.is_(None)
            )
        )

        # Apply filters
        if filters:
            if filters.status:
                query = query.where(BookingRequest.status == filters.status)

            if filters.from_date:
                query = query.where(BookingRequest.event_date >= filters.from_date)

            if filters.to_date:
                query = query.where(BookingRequest.event_date <= filters.to_date)

            if filters.viewed_only:
                query = query.where(BookingRequest.viewed_by_vendor == True)

            if filters.unviewed_only:
                query = query.where(BookingRequest.viewed_by_vendor == False)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Pagination
        query = query.order_by(BookingRequest.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        requests = list(result.scalars().all())

        return requests, total

    # ========================================================================
    # Quote Operations
    # ========================================================================

    async def create_quote(
        self,
        vendor_id: str,
        quote_data: QuoteCreate
    ) -> Quote:
        """Create a new quote"""
        # Generate quote number
        quote_number = await self._generate_quote_number()

        # Calculate totals from items
        subtotal = sum(
            item.quantity * item.unit_price * (1 - item.discount_percentage / 100)
            for item in quote_data.items
        )

        tax_amount = subtotal * (quote_data.tax_rate / 100)
        total_amount = subtotal + tax_amount - quote_data.discount_amount
        deposit_amount = total_amount * (quote_data.deposit_percentage / 100)

        # Calculate validity
        valid_until = datetime.utcnow() + timedelta(days=quote_data.valid_days)

        quote = Quote(
            booking_request_id=quote_data.booking_request_id,
            vendor_id=UUID(vendor_id),
            quote_number=quote_number,
            subtotal=subtotal,
            tax_rate=quote_data.tax_rate,
            tax_amount=tax_amount,
            discount_amount=quote_data.discount_amount,
            discount_reason=quote_data.discount_reason,
            total_amount=total_amount,
            deposit_percentage=quote_data.deposit_percentage,
            deposit_amount=deposit_amount,
            description=quote_data.description,
            payment_terms=quote_data.payment_terms,
            cancellation_policy=quote_data.cancellation_policy,
            terms_and_conditions=quote_data.terms_and_conditions,
            additional_notes=quote_data.additional_notes,
            is_customizable=quote_data.is_customizable,
            customization_notes=quote_data.customization_notes,
            valid_until=valid_until,
            status=QuoteStatus.DRAFT
        )

        self.db.add(quote)
        await self.db.flush()

        # Add quote items
        for idx, item_data in enumerate(quote_data.items):
            subtotal = item_data.quantity * item_data.unit_price
            discount_amount = subtotal * (item_data.discount_percentage / 100)
            total = subtotal - discount_amount

            item = QuoteItem(
                quote_id=quote.id,
                vendor_service_id=item_data.vendor_service_id,
                item_name=item_data.item_name,
                description=item_data.description,
                category=item_data.category,
                quantity=item_data.quantity,
                unit=item_data.unit,
                unit_price=item_data.unit_price,
                subtotal=subtotal,
                discount_percentage=item_data.discount_percentage,
                discount_amount=discount_amount,
                total=total,
                is_optional=item_data.is_optional,
                is_customizable=item_data.is_customizable,
                notes=item_data.notes,
                order_index=idx
            )
            self.db.add(item)

        await self.db.commit()
        await self.db.refresh(quote)

        return quote

    async def get_quote_by_id(
        self,
        quote_id: str,
        load_items: bool = False
    ) -> Optional[Quote]:
        """Get quote by ID"""
        query = select(Quote).where(Quote.id == UUID(quote_id))

        if load_items:
            query = query.options(selectinload(Quote.quote_items))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def send_quote(self, quote_id: str) -> Optional[Quote]:
        """Mark quote as sent"""
        quote = await self.get_quote_by_id(quote_id)
        if not quote:
            return None

        quote.status = QuoteStatus.SENT
        quote.sent_at = datetime.utcnow()

        # Update booking request status
        booking_request = await self.get_booking_request_by_id(str(quote.booking_request_id))
        if booking_request:
            booking_request.status = BookingRequestStatus.QUOTED
            booking_request.responded_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(quote)

        return quote

    async def mark_quote_as_viewed(self, quote_id: str) -> bool:
        """Mark quote as viewed by organizer"""
        quote = await self.get_quote_by_id(quote_id)
        if not quote:
            return False

        if quote.status == QuoteStatus.SENT:
            quote.status = QuoteStatus.VIEWED

        quote.viewed_at = datetime.utcnow()

        await self.db.commit()
        return True

    async def accept_quote(self, quote_id: str) -> Optional[Quote]:
        """Accept a quote"""
        quote = await self.get_quote_by_id(quote_id)
        if not quote:
            return None

        quote.status = QuoteStatus.ACCEPTED
        quote.accepted_at = datetime.utcnow()

        # Update booking request
        booking_request = await self.get_booking_request_by_id(str(quote.booking_request_id))
        if booking_request:
            booking_request.status = BookingRequestStatus.ACCEPTED

        await self.db.commit()
        await self.db.refresh(quote)

        return quote

    async def reject_quote(
        self,
        quote_id: str,
        rejection_reason: str
    ) -> Optional[Quote]:
        """Reject a quote"""
        quote = await self.get_quote_by_id(quote_id)
        if not quote:
            return None

        quote.status = QuoteStatus.REJECTED
        quote.rejected_at = datetime.utcnow()
        quote.rejection_reason = rejection_reason

        await self.db.commit()
        await self.db.refresh(quote)

        return quote

    async def get_quotes_for_request(
        self,
        booking_request_id: str
    ) -> List[Quote]:
        """Get all quotes for a booking request"""
        query = select(Quote).where(
            Quote.booking_request_id == UUID(booking_request_id)
        ).order_by(Quote.version.desc(), Quote.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # Booking Operations
    # ========================================================================

    async def create_booking(
        self,
        quote: Quote,
        booking_request: BookingRequest
    ) -> Booking:
        """Create booking from accepted quote"""
        # Get vendor commission rate
        vendor_query = select(Vendor).where(Vendor.id == quote.vendor_id)
        vendor_result = await self.db.execute(vendor_query)
        vendor = vendor_result.scalar_one()

        # Generate booking number
        booking_number = await self._generate_booking_number()

        # Calculate commission
        commission_amount = quote.total_amount * vendor.commission_rate

        booking = Booking(
            booking_request_id=booking_request.id,
            quote_id=quote.id,
            event_id=booking_request.event_id,
            vendor_id=booking_request.vendor_id,
            organizer_id=booking_request.organizer_id,
            booking_number=booking_number,
            status=BookingStatus.CONFIRMED,
            event_date=booking_request.event_date,
            event_end_date=booking_request.event_end_date,
            venue_name=booking_request.venue_name,
            venue_address=booking_request.venue_address,
            guest_count=booking_request.guest_count,
            total_amount=quote.total_amount,
            deposit_amount=quote.deposit_amount,
            amount_paid=Decimal('0'),
            amount_due=quote.total_amount,
            payment_status=PaymentStatus.PENDING,
            commission_rate=vendor.commission_rate,
            commission_amount=commission_amount,
            commission_paid=False,
            contract_signed=False,
            terms_accepted=True,
            terms_accepted_at=datetime.utcnow(),
            cancellation_policy=quote.cancellation_policy,
            is_refundable=True,
            service_description=quote.description,
            special_requirements=booking_request.special_requirements
        )

        self.db.add(booking)
        await self.db.commit()
        await self.db.refresh(booking)

        return booking

    async def get_booking_by_id(
        self,
        booking_id: str,
        load_relationships: bool = False
    ) -> Optional[Booking]:
        """Get booking by ID"""
        query = select(Booking).where(Booking.id == UUID(booking_id))

        if load_relationships:
            query = query.options(
                selectinload(Booking.payments),
                selectinload(Booking.cancellation)
            )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_booking_by_number(self, booking_number: str) -> Optional[Booking]:
        """Get booking by booking number"""
        query = select(Booking).where(Booking.booking_number == booking_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_booking(
        self,
        booking_id: str,
        booking_data: BookingUpdate
    ) -> Optional[Booking]:
        """Update booking"""
        booking = await self.get_booking_by_id(booking_id)
        if not booking:
            return None

        update_data = booking_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(booking, field, value)

        await self.db.commit()
        await self.db.refresh(booking)

        return booking

    async def complete_booking(
        self,
        booking_id: str,
        completion_notes: Optional[str] = None
    ) -> Optional[Booking]:
        """Mark booking as completed"""
        booking = await self.get_booking_by_id(booking_id)
        if not booking:
            return None

        booking.status = BookingStatus.COMPLETED
        booking.completed_at = datetime.utcnow()
        booking.completion_notes = completion_notes

        # Update vendor statistics
        await self._update_vendor_completion_stats(str(booking.vendor_id))

        await self.db.commit()
        await self.db.refresh(booking)

        return booking

    async def get_bookings_for_event(
        self,
        event_id: str
    ) -> List[Booking]:
        """Get all bookings for an event"""
        query = select(Booking).where(
            Booking.event_id == UUID(event_id)
        ).order_by(Booking.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_bookings_for_vendor(
        self,
        vendor_id: str,
        filters: Optional[BookingFilters] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Booking], int]:
        """Get bookings for vendor with filters"""
        query = select(Booking).where(Booking.vendor_id == UUID(vendor_id))

        # Apply filters
        if filters:
            if filters.status:
                query = query.where(Booking.status == filters.status)

            if filters.payment_status:
                query = query.where(Booking.payment_status == filters.payment_status)

            if filters.from_date:
                query = query.where(Booking.event_date >= filters.from_date)

            if filters.to_date:
                query = query.where(Booking.event_date <= filters.to_date)

            if filters.completed_only:
                query = query.where(Booking.status == BookingStatus.COMPLETED)

            if filters.cancelled_only:
                query = query.where(Booking.status == BookingStatus.CANCELLED)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Pagination
        query = query.order_by(Booking.event_date.asc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        bookings = list(result.scalars().all())

        return bookings, total

    # ========================================================================
    # Payment Operations
    # ========================================================================

    async def create_payment(
        self,
        booking_id: str,
        user_id: str,
        payment_data: PaymentCreate
    ) -> BookingPayment:
        """Create a payment record"""
        payment_number = await self._generate_payment_number()

        payment = BookingPayment(
            booking_id=UUID(booking_id),
            user_id=UUID(user_id),
            payment_number=payment_number,
            amount=payment_data.amount,
            payment_method=payment_data.payment_method,
            is_deposit=payment_data.is_deposit,
            notes=payment_data.notes,
            status=PaymentStatus.PENDING
        )

        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)

        return payment

    async def process_payment(
        self,
        payment_id: str,
        gateway_transaction_id: str,
        gateway: str
    ) -> Optional[BookingPayment]:
        """Mark payment as processed"""
        query = select(BookingPayment).where(BookingPayment.id == UUID(payment_id))
        result = await self.db.execute(query)
        payment = result.scalar_one_or_none()

        if not payment:
            return None

        payment.status = PaymentStatus.PAID
        payment.payment_date = datetime.utcnow()
        payment.processed_at = datetime.utcnow()
        payment.payment_gateway = gateway
        payment.gateway_transaction_id = gateway_transaction_id

        # Update booking payment status
        booking = await self.get_booking_by_id(str(payment.booking_id))
        if booking:
            booking.amount_paid += payment.amount
            booking.amount_due = booking.total_amount - booking.amount_paid

            if payment.is_deposit:
                booking.payment_status = PaymentStatus.DEPOSIT_PAID
            elif booking.amount_paid >= booking.total_amount:
                booking.payment_status = PaymentStatus.PAID
            else:
                booking.payment_status = PaymentStatus.PARTIAL

        await self.db.commit()
        await self.db.refresh(payment)

        return payment

    # ========================================================================
    # Cancellation Operations
    # ========================================================================

    async def create_cancellation(
        self,
        booking_id: str,
        user_id: str,
        initiator: CancellationInitiator,
        cancellation_data: CancellationCreate
    ) -> BookingCancellation:
        """Create a cancellation record"""
        booking = await self.get_booking_by_id(booking_id)
        if not booking:
            raise ValueError("Booking not found")

        # Calculate days before event
        days_before = (booking.event_date - datetime.utcnow()).days

        # Calculate refund based on cancellation policy (simplified logic)
        refund_percentage = self._calculate_refund_percentage(days_before)
        refund_amount = booking.amount_paid * (refund_percentage / 100)
        penalty_amount = booking.amount_paid - refund_amount

        cancellation = BookingCancellation(
            booking_id=UUID(booking_id),
            cancelled_by_user_id=UUID(user_id),
            initiator=initiator,
            reason=cancellation_data.reason,
            reason_category=cancellation_data.reason_category,
            days_before_event=days_before,
            cancellation_date=datetime.utcnow(),
            refund_percentage=refund_percentage,
            refund_amount=refund_amount,
            penalty_amount=penalty_amount,
            organizer_notes=cancellation_data.organizer_notes,
            vendor_notes=cancellation_data.vendor_notes
        )

        self.db.add(cancellation)

        # Update booking status
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(cancellation)

        return cancellation

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _generate_quote_number(self) -> str:
        """Generate unique quote number"""
        year = datetime.utcnow().year
        query = select(func.count()).select_from(Quote).where(
            func.extract('year', Quote.created_at) == year
        )
        result = await self.db.execute(query)
        count = result.scalar() + 1
        return f"Q-{year}-{count:05d}"

    async def _generate_booking_number(self) -> str:
        """Generate unique booking number"""
        year = datetime.utcnow().year
        query = select(func.count()).select_from(Booking).where(
            func.extract('year', Booking.created_at) == year
        )
        result = await self.db.execute(query)
        count = result.scalar() + 1
        return f"B-{year}-{count:05d}"

    async def _generate_payment_number(self) -> str:
        """Generate unique payment number"""
        year = datetime.utcnow().year
        query = select(func.count()).select_from(BookingPayment).where(
            func.extract('year', BookingPayment.created_at) == year
        )
        result = await self.db.execute(query)
        count = result.scalar() + 1
        return f"P-{year}-{count:05d}"

    def _calculate_refund_percentage(self, days_before: int) -> Decimal:
        """Calculate refund percentage based on cancellation timing"""
        if days_before >= 60:
            return Decimal('100')
        elif days_before >= 30:
            return Decimal('75')
        elif days_before >= 14:
            return Decimal('50')
        elif days_before >= 7:
            return Decimal('25')
        else:
            return Decimal('0')

    async def _update_vendor_completion_stats(self, vendor_id: str):
        """Update vendor completion statistics"""
        # Get completed and total bookings
        completed_query = select(func.count()).select_from(Booking).where(
            and_(
                Booking.vendor_id == UUID(vendor_id),
                Booking.status == BookingStatus.COMPLETED
            )
        )
        completed_result = await self.db.execute(completed_query)
        completed = completed_result.scalar()

        total_query = select(func.count()).select_from(Booking).where(
            Booking.vendor_id == UUID(vendor_id)
        )
        total_result = await self.db.execute(total_query)
        total = total_result.scalar()

        # Calculate completion rate
        completion_rate = (completed / total * 100) if total > 0 else 0

        # Update vendor
        vendor_update = (
            update(Vendor)
            .where(Vendor.id == UUID(vendor_id))
            .values(
                booking_count=total,
                completion_rate=Decimal(str(completion_rate))
            )
        )
        await self.db.execute(vendor_update)
