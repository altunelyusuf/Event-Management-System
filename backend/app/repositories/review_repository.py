"""
CelebraTech Event Management System - Review Repository
Sprint 6: Review and Rating System
FR-006: Review and Rating Management
Data access layer for reviews
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, update, delete
from sqlalchemy.orm import joinedload, selectinload
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from app.models.review import (
    Review,
    ReviewResponse,
    ReviewHelpfulness,
    ReviewReport,
    VendorRatingCache,
    ReviewStatus,
    ReportStatus
)
from app.models.booking import Booking
from app.models.vendor import Vendor
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewUpdate, ReviewFilters


class ReviewRepository:
    """Repository for review data access"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Review CRUD Operations
    # ========================================================================

    async def create_review(
        self,
        review_data: ReviewCreate,
        reviewer_id: UUID,
        vendor_id: UUID,
        event_id: UUID,
        event_date: datetime
    ) -> Review:
        """Create a new review"""
        review = Review(
            booking_id=review_data.booking_id,
            vendor_id=vendor_id,
            reviewer_id=reviewer_id,
            event_id=event_id,
            overall_rating=review_data.overall_rating,
            quality_rating=review_data.quality_rating,
            professionalism_rating=review_data.professionalism_rating,
            value_rating=review_data.value_rating,
            communication_rating=review_data.communication_rating,
            timeliness_rating=review_data.timeliness_rating,
            title=review_data.title,
            comment=review_data.comment,
            photos=review_data.photos,
            pros=review_data.pros,
            cons=review_data.cons,
            event_date=event_date,
            is_verified=True,  # Always verified if from booking
            status=ReviewStatus.APPROVED.value  # Auto-approve for now
        )

        self.db.add(review)
        await self.db.flush()
        await self.db.refresh(review)

        # Update vendor rating cache
        await self._update_vendor_rating_cache(vendor_id)

        return review

    async def get_review_by_id(
        self,
        review_id: UUID,
        load_relations: bool = False
    ) -> Optional[Review]:
        """Get review by ID"""
        query = select(Review).where(
            and_(
                Review.id == review_id,
                Review.deleted_at.is_(None)
            )
        )

        if load_relations:
            query = query.options(
                joinedload(Review.reviewer),
                joinedload(Review.vendor),
                joinedload(Review.response),
                selectinload(Review.helpfulness_votes)
            )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_review_by_booking(self, booking_id: UUID) -> Optional[Review]:
        """Get review by booking ID"""
        query = select(Review).where(
            and_(
                Review.booking_id == booking_id,
                Review.deleted_at.is_(None)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_review(
        self,
        review_id: UUID,
        review_data: ReviewUpdate
    ) -> Optional[Review]:
        """Update a review"""
        review = await self.get_review_by_id(review_id)
        if not review:
            return None

        # Update fields
        update_data = review_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(review, field, value)

        review.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(review)

        # Update vendor rating cache
        await self._update_vendor_rating_cache(review.vendor_id)

        return review

    async def delete_review(self, review_id: UUID) -> bool:
        """Soft delete a review"""
        review = await self.get_review_by_id(review_id)
        if not review:
            return False

        review.deleted_at = datetime.utcnow()
        await self.db.flush()

        # Update vendor rating cache
        await self._update_vendor_rating_cache(review.vendor_id)

        return True

    # ========================================================================
    # Review Queries
    # ========================================================================

    async def list_reviews(
        self,
        filters: Optional[ReviewFilters] = None,
        sort_by: str = "recent",
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Review], int]:
        """List reviews with filters and pagination"""
        # Base query
        query = select(Review).where(Review.deleted_at.is_(None))

        # Apply filters
        if filters:
            if filters.vendor_id:
                query = query.where(Review.vendor_id == filters.vendor_id)
            if filters.reviewer_id:
                query = query.where(Review.reviewer_id == filters.reviewer_id)
            if filters.min_rating:
                query = query.where(Review.overall_rating >= filters.min_rating)
            if filters.max_rating:
                query = query.where(Review.overall_rating <= filters.max_rating)
            if filters.status:
                query = query.where(Review.status == filters.status.value)
            if filters.is_verified is not None:
                query = query.where(Review.is_verified == filters.is_verified)
            if filters.has_response is not None:
                query = query.where(Review.has_response == filters.has_response)
            if filters.is_featured is not None:
                query = query.where(Review.is_featured == filters.is_featured)
            if filters.start_date:
                query = query.where(Review.created_at >= filters.start_date)
            if filters.end_date:
                query = query.where(Review.created_at <= filters.end_date)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Apply sorting
        if sort_by == "recent":
            query = query.order_by(desc(Review.created_at))
        elif sort_by == "rating_high":
            query = query.order_by(desc(Review.overall_rating), desc(Review.created_at))
        elif sort_by == "rating_low":
            query = query.order_by(asc(Review.overall_rating), desc(Review.created_at))
        elif sort_by == "helpful":
            query = query.order_by(desc(Review.helpful_count), desc(Review.created_at))
        elif sort_by == "oldest":
            query = query.order_by(asc(Review.created_at))
        else:
            query = query.order_by(desc(Review.created_at))

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Load relations
        query = query.options(
            joinedload(Review.reviewer),
            joinedload(Review.vendor),
            joinedload(Review.response)
        )

        result = await self.db.execute(query)
        reviews = result.scalars().unique().all()

        return list(reviews), total

    async def get_vendor_reviews(
        self,
        vendor_id: UUID,
        status: Optional[str] = ReviewStatus.APPROVED.value,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Review], int]:
        """Get all reviews for a vendor"""
        filters = ReviewFilters(vendor_id=vendor_id, status=status)
        return await self.list_reviews(filters, page=page, page_size=page_size)

    async def get_user_reviews(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Review], int]:
        """Get all reviews by a user"""
        filters = ReviewFilters(reviewer_id=user_id)
        return await self.list_reviews(filters, page=page, page_size=page_size)

    async def get_featured_reviews(
        self,
        vendor_id: Optional[UUID] = None,
        limit: int = 10
    ) -> List[Review]:
        """Get featured reviews"""
        query = select(Review).where(
            and_(
                Review.is_featured == True,
                Review.status == ReviewStatus.APPROVED.value,
                Review.is_public == True,
                Review.deleted_at.is_(None)
            )
        )

        if vendor_id:
            query = query.where(Review.vendor_id == vendor_id)

        query = query.order_by(desc(Review.created_at)).limit(limit)
        query = query.options(joinedload(Review.reviewer), joinedload(Review.vendor))

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    # ========================================================================
    # Review Response Operations
    # ========================================================================

    async def create_review_response(
        self,
        review_id: UUID,
        vendor_id: UUID,
        responder_id: UUID,
        response_text: str
    ) -> ReviewResponse:
        """Create vendor response to review"""
        response = ReviewResponse(
            review_id=review_id,
            vendor_id=vendor_id,
            responder_id=responder_id,
            response_text=response_text,
            status=ReviewStatus.APPROVED.value
        )

        self.db.add(response)

        # Update review
        await self.db.execute(
            update(Review)
            .where(Review.id == review_id)
            .values(has_response=True, updated_at=datetime.utcnow())
        )

        await self.db.flush()
        await self.db.refresh(response)

        # Update response rate in cache
        await self._update_vendor_rating_cache(vendor_id)

        return response

    async def get_review_response(self, review_id: UUID) -> Optional[ReviewResponse]:
        """Get response for a review"""
        query = select(ReviewResponse).where(
            and_(
                ReviewResponse.review_id == review_id,
                ReviewResponse.deleted_at.is_(None)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_review_response(
        self,
        response_id: UUID,
        response_text: str
    ) -> Optional[ReviewResponse]:
        """Update vendor response"""
        response = await self.db.get(ReviewResponse, response_id)
        if not response or response.deleted_at:
            return None

        response.response_text = response_text
        response.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(response)

        return response

    async def delete_review_response(self, response_id: UUID) -> bool:
        """Soft delete a review response"""
        response = await self.db.get(ReviewResponse, response_id)
        if not response or response.deleted_at:
            return False

        response.deleted_at = datetime.utcnow()

        # Update review
        await self.db.execute(
            update(Review)
            .where(Review.id == response.review_id)
            .values(has_response=False, updated_at=datetime.utcnow())
        )

        await self.db.flush()

        # Update response rate in cache
        await self._update_vendor_rating_cache(response.vendor_id)

        return True

    # ========================================================================
    # Review Helpfulness Operations
    # ========================================================================

    async def vote_helpfulness(
        self,
        review_id: UUID,
        user_id: UUID,
        is_helpful: bool
    ) -> ReviewHelpfulness:
        """Vote on review helpfulness"""
        # Check if vote exists
        query = select(ReviewHelpfulness).where(
            and_(
                ReviewHelpfulness.review_id == review_id,
                ReviewHelpfulness.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        existing_vote = result.scalar_one_or_none()

        if existing_vote:
            # Update existing vote
            old_value = existing_vote.is_helpful
            existing_vote.is_helpful = is_helpful

            # Update counts
            if old_value != is_helpful:
                await self._update_helpful_counts(review_id, old_value, is_helpful)

            await self.db.flush()
            await self.db.refresh(existing_vote)
            return existing_vote
        else:
            # Create new vote
            vote = ReviewHelpfulness(
                review_id=review_id,
                user_id=user_id,
                is_helpful=is_helpful
            )
            self.db.add(vote)

            # Update counts
            await self._update_helpful_counts(review_id, None, is_helpful)

            await self.db.flush()
            await self.db.refresh(vote)
            return vote

    async def get_user_helpfulness_vote(
        self,
        review_id: UUID,
        user_id: UUID
    ) -> Optional[ReviewHelpfulness]:
        """Get user's helpfulness vote for a review"""
        query = select(ReviewHelpfulness).where(
            and_(
                ReviewHelpfulness.review_id == review_id,
                ReviewHelpfulness.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _update_helpful_counts(
        self,
        review_id: UUID,
        old_value: Optional[bool],
        new_value: bool
    ):
        """Update helpful/not helpful counts"""
        review = await self.db.get(Review, review_id)
        if not review:
            return

        if old_value is None:
            # New vote
            if new_value:
                review.helpful_count += 1
            else:
                review.not_helpful_count += 1
        elif old_value != new_value:
            # Changed vote
            if new_value:
                review.helpful_count += 1
                review.not_helpful_count -= 1
            else:
                review.helpful_count -= 1
                review.not_helpful_count += 1

        await self.db.flush()

    # ========================================================================
    # Review Report Operations
    # ========================================================================

    async def create_review_report(
        self,
        review_id: UUID,
        reporter_id: UUID,
        reason: str,
        description: Optional[str] = None
    ) -> ReviewReport:
        """Create a review report"""
        report = ReviewReport(
            review_id=review_id,
            reporter_id=reporter_id,
            reason=reason,
            description=description,
            status=ReportStatus.PENDING.value
        )

        self.db.add(report)

        # Increment report count on review
        await self.db.execute(
            update(Review)
            .where(Review.id == review_id)
            .values(report_count=Review.report_count + 1)
        )

        # Auto-flag if many reports
        query = select(func.count()).select_from(ReviewReport).where(
            and_(
                ReviewReport.review_id == review_id,
                ReviewReport.status == ReportStatus.PENDING.value
            )
        )
        result = await self.db.execute(query)
        report_count = result.scalar()

        if report_count >= 3:  # Flag after 3 reports
            await self.db.execute(
                update(Review)
                .where(Review.id == review_id)
                .values(status=ReviewStatus.FLAGGED.value)
            )

        await self.db.flush()
        await self.db.refresh(report)

        return report

    async def get_review_reports(
        self,
        review_id: Optional[UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ReviewReport], int]:
        """Get review reports"""
        query = select(ReviewReport)

        if review_id:
            query = query.where(ReviewReport.review_id == review_id)
        if status:
            query = query.where(ReviewReport.status == status)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Pagination
        query = query.order_by(desc(ReviewReport.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        reports = result.scalars().all()

        return list(reports), total

    async def update_review_report(
        self,
        report_id: UUID,
        status: str,
        investigator_id: UUID,
        investigation_notes: Optional[str] = None,
        resolution: Optional[str] = None
    ) -> Optional[ReviewReport]:
        """Update review report (admin)"""
        report = await self.db.get(ReviewReport, report_id)
        if not report:
            return None

        report.status = status
        report.investigated_by = investigator_id
        report.investigation_notes = investigation_notes
        report.resolution = resolution
        report.updated_at = datetime.utcnow()

        if status == ReportStatus.RESOLVED.value:
            report.resolved_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(report)

        return report

    # ========================================================================
    # Vendor Rating Cache Operations
    # ========================================================================

    async def get_vendor_rating_stats(self, vendor_id: UUID) -> Optional[VendorRatingCache]:
        """Get cached vendor rating statistics"""
        return await self.db.get(VendorRatingCache, vendor_id)

    async def _update_vendor_rating_cache(self, vendor_id: UUID):
        """Update vendor rating cache"""
        # Calculate statistics
        query = select(
            func.count(Review.id).label('total_reviews'),
            func.avg(Review.overall_rating).label('avg_rating'),
            func.sum(func.case((Review.overall_rating == 1, 1), else_=0)).label('one_star'),
            func.sum(func.case((Review.overall_rating == 2, 1), else_=0)).label('two_star'),
            func.sum(func.case((Review.overall_rating == 3, 1), else_=0)).label('three_star'),
            func.sum(func.case((Review.overall_rating == 4, 1), else_=0)).label('four_star'),
            func.sum(func.case((Review.overall_rating == 5, 1), else_=0)).label('five_star'),
            func.avg(Review.quality_rating).label('avg_quality'),
            func.avg(Review.professionalism_rating).label('avg_professionalism'),
            func.avg(Review.value_rating).label('avg_value'),
            func.avg(Review.communication_rating).label('avg_communication'),
            func.avg(Review.timeliness_rating).label('avg_timeliness'),
            func.sum(Review.helpful_count).label('total_helpful')
        ).where(
            and_(
                Review.vendor_id == vendor_id,
                Review.status == ReviewStatus.APPROVED.value,
                Review.deleted_at.is_(None)
            )
        )

        result = await self.db.execute(query)
        stats = result.one()

        # Calculate response rate
        total_reviews = stats.total_reviews or 0
        if total_reviews > 0:
            response_query = select(func.count()).select_from(Review).where(
                and_(
                    Review.vendor_id == vendor_id,
                    Review.has_response == True,
                    Review.status == ReviewStatus.APPROVED.value,
                    Review.deleted_at.is_(None)
                )
            )
            response_result = await self.db.execute(response_query)
            response_count = response_result.scalar()
            response_rate = Decimal(response_count) / Decimal(total_reviews) * 100
        else:
            response_rate = Decimal(0)

        # Recent reviews (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_query = select(
            func.count(Review.id).label('recent_count'),
            func.avg(Review.overall_rating).label('recent_avg')
        ).where(
            and_(
                Review.vendor_id == vendor_id,
                Review.status == ReviewStatus.APPROVED.value,
                Review.created_at >= thirty_days_ago,
                Review.deleted_at.is_(None)
            )
        )
        recent_result = await self.db.execute(recent_query)
        recent_stats = recent_result.one()

        # Upsert cache
        cache = await self.db.get(VendorRatingCache, vendor_id)
        if cache:
            # Update existing
            cache.total_reviews = total_reviews
            cache.average_rating = stats.avg_rating or Decimal(0)
            cache.one_star_count = stats.one_star or 0
            cache.two_star_count = stats.two_star or 0
            cache.three_star_count = stats.three_star or 0
            cache.four_star_count = stats.four_star or 0
            cache.five_star_count = stats.five_star or 0
            cache.avg_quality_rating = stats.avg_quality
            cache.avg_professionalism_rating = stats.avg_professionalism
            cache.avg_value_rating = stats.avg_value
            cache.avg_communication_rating = stats.avg_communication
            cache.avg_timeliness_rating = stats.avg_timeliness
            cache.total_helpful_votes = stats.total_helpful or 0
            cache.response_rate = response_rate
            cache.recent_reviews_30d = recent_stats.recent_count or 0
            cache.recent_average_30d = recent_stats.recent_avg
            cache.last_calculated_at = datetime.utcnow()
            cache.updated_at = datetime.utcnow()
        else:
            # Create new
            cache = VendorRatingCache(
                vendor_id=vendor_id,
                total_reviews=total_reviews,
                average_rating=stats.avg_rating or Decimal(0),
                one_star_count=stats.one_star or 0,
                two_star_count=stats.two_star or 0,
                three_star_count=stats.three_star or 0,
                four_star_count=stats.four_star or 0,
                five_star_count=stats.five_star or 0,
                avg_quality_rating=stats.avg_quality,
                avg_professionalism_rating=stats.avg_professionalism,
                avg_value_rating=stats.avg_value,
                avg_communication_rating=stats.avg_communication,
                avg_timeliness_rating=stats.avg_timeliness,
                total_helpful_votes=stats.total_helpful or 0,
                response_rate=response_rate,
                recent_reviews_30d=recent_stats.recent_count or 0,
                recent_average_30d=recent_stats.recent_avg,
                last_calculated_at=datetime.utcnow()
            )
            self.db.add(cache)

        await self.db.flush()

    # ========================================================================
    # Moderation Operations (Admin)
    # ========================================================================

    async def moderate_review(
        self,
        review_id: UUID,
        status: str,
        moderator_id: UUID,
        moderation_notes: Optional[str] = None,
        is_featured: Optional[bool] = None
    ) -> Optional[Review]:
        """Moderate a review (admin only)"""
        review = await self.get_review_by_id(review_id)
        if not review:
            return None

        review.status = status
        review.moderated_by = moderator_id
        review.moderated_at = datetime.utcnow()
        review.moderation_notes = moderation_notes
        if is_featured is not None:
            review.is_featured = is_featured

        await self.db.flush()
        await self.db.refresh(review)

        # Update cache if status changed
        if status in [ReviewStatus.APPROVED.value, ReviewStatus.REJECTED.value]:
            await self._update_vendor_rating_cache(review.vendor_id)

        return review

    async def bulk_moderate_reviews(
        self,
        review_ids: List[UUID],
        action: str,
        moderator_id: UUID,
        notes: Optional[str] = None
    ) -> int:
        """Bulk moderate reviews (admin only)"""
        status_map = {
            'approve': ReviewStatus.APPROVED.value,
            'reject': ReviewStatus.REJECTED.value,
            'flag': ReviewStatus.FLAGGED.value,
            'hide': ReviewStatus.HIDDEN.value
        }

        status = status_map.get(action)
        if not status:
            return 0

        result = await self.db.execute(
            update(Review)
            .where(Review.id.in_(review_ids))
            .values(
                status=status,
                moderated_by=moderator_id,
                moderated_at=datetime.utcnow(),
                moderation_notes=notes
            )
        )

        await self.db.flush()

        # Update caches for affected vendors
        query = select(Review.vendor_id).where(Review.id.in_(review_ids)).distinct()
        vendor_result = await self.db.execute(query)
        vendor_ids = vendor_result.scalars().all()

        for vendor_id in vendor_ids:
            await self._update_vendor_rating_cache(vendor_id)

        return result.rowcount
