"""
CelebraTech Event Management System - Review Service
Sprint 6: Review and Rating System
FR-006: Review and Rating Management
Business logic for review operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List, Optional, Tuple
from datetime import datetime
from uuid import UUID

from app.repositories.review_repository import ReviewRepository
from app.models.user import User, UserRole
from app.models.review import ReviewStatus, ReportStatus
from app.models.booking import Booking, BookingStatus
from app.models.vendor import Vendor
from app.schemas.review import (
    ReviewCreate,
    ReviewUpdate,
    ReviewFilters,
    ReviewResponseCreate,
    ReviewResponseUpdate,
    ReviewHelpfulnessCreate,
    ReviewReportCreate,
    ReviewReportUpdate,
    ReviewModerationUpdate,
    ReviewBulkAction
)


class ReviewService:
    """Service for review business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ReviewRepository(db)

    # ========================================================================
    # Review Operations
    # ========================================================================

    async def create_review(
        self,
        review_data: ReviewCreate,
        current_user: User
    ):
        """
        Create a new review

        Business rules:
        - User must have completed booking
        - One review per booking
        - Booking must be in COMPLETED status
        - Event must have occurred
        """
        # Get booking
        booking = await self.db.get(Booking, review_data.booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )

        # Check if user is the organizer
        from sqlalchemy import select
        from app.models.event import Event
        event_query = select(Event).where(Event.id == booking.event_id)
        event_result = await self.db.execute(event_query)
        event = event_result.scalar_one_or_none()

        if not event or str(event.organizer_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the event organizer can review this booking"
            )

        # Check booking status
        if booking.status != BookingStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only review completed bookings"
            )

        # Check if event has occurred
        if event.event_date > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot review booking before event occurs"
            )

        # Check if review already exists
        existing_review = await self.repo.get_review_by_booking(review_data.booking_id)
        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Review already exists for this booking"
            )

        # Create review
        review = await self.repo.create_review(
            review_data=review_data,
            reviewer_id=current_user.id,
            vendor_id=booking.vendor_id,
            event_id=booking.event_id,
            event_date=event.event_date
        )

        await self.db.commit()

        return review

    async def get_review(
        self,
        review_id: UUID,
        current_user: Optional[User] = None
    ):
        """Get review by ID"""
        review = await self.repo.get_review_by_id(review_id, load_relations=True)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )

        # Check visibility
        if not review.is_public and review.status != ReviewStatus.APPROVED.value:
            # Only allow access to reviewer, vendor, or admin
            if current_user:
                is_reviewer = str(review.reviewer_id) == str(current_user.id)
                is_vendor = False
                if current_user.role == UserRole.VENDOR.value:
                    # Check if user owns vendor
                    vendor = await self.db.get(Vendor, review.vendor_id)
                    is_vendor = vendor and str(vendor.user_id) == str(current_user.id)
                is_admin = current_user.role == UserRole.ADMIN.value

                if not (is_reviewer or is_vendor or is_admin):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not authorized to view this review"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view this review"
                )

        return review

    async def update_review(
        self,
        review_id: UUID,
        review_data: ReviewUpdate,
        current_user: User
    ):
        """
        Update a review

        Business rules:
        - Only reviewer can update
        - Cannot update after vendor response
        - Can update within 30 days of creation
        """
        review = await self.repo.get_review_by_id(review_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )

        # Check if user is reviewer
        if str(review.reviewer_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only reviewer can update review"
            )

        # Check if vendor has responded
        if review.has_response:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update review after vendor response"
            )

        # Check time limit (30 days)
        days_since_creation = (datetime.utcnow() - review.created_at).days
        if days_since_creation > 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update review after 30 days"
            )

        # Update review
        updated_review = await self.repo.update_review(review_id, review_data)
        await self.db.commit()

        return updated_review

    async def delete_review(
        self,
        review_id: UUID,
        current_user: User
    ):
        """
        Delete a review

        Business rules:
        - Only reviewer or admin can delete
        - Cannot delete after vendor response (unless admin)
        """
        review = await self.repo.get_review_by_id(review_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )

        # Check permissions
        is_reviewer = str(review.reviewer_id) == str(current_user.id)
        is_admin = current_user.role == UserRole.ADMIN.value

        if not (is_reviewer or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this review"
            )

        # Check if vendor has responded (non-admin)
        if review.has_response and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete review after vendor response. Contact support."
            )

        # Delete review
        success = await self.repo.delete_review(review_id)
        await self.db.commit()

        return success

    async def list_reviews(
        self,
        filters: Optional[ReviewFilters] = None,
        sort_by: str = "recent",
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List, int]:
        """List reviews with filters"""
        return await self.repo.list_reviews(filters, sort_by, page, page_size)

    async def get_vendor_reviews(
        self,
        vendor_id: UUID,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List, int]:
        """Get all reviews for a vendor"""
        return await self.repo.get_vendor_reviews(vendor_id, page=page, page_size=page_size)

    async def get_user_reviews(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List, int]:
        """Get all reviews by a user"""
        return await self.repo.get_user_reviews(user_id, page=page, page_size=page_size)

    # ========================================================================
    # Review Response Operations
    # ========================================================================

    async def create_review_response(
        self,
        review_id: UUID,
        response_data: ReviewResponseCreate,
        current_user: User
    ):
        """
        Create vendor response to review

        Business rules:
        - Only vendor can respond
        - One response per review
        - Can only respond to approved reviews
        """
        # Get review
        review = await self.repo.get_review_by_id(review_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )

        # Check if review is approved
        if review.status != ReviewStatus.APPROVED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only respond to approved reviews"
            )

        # Check if user owns vendor
        vendor = await self.db.get(Vendor, review.vendor_id)
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

        if str(vendor.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only vendor can respond to reviews"
            )

        # Check if response already exists
        existing_response = await self.repo.get_review_response(review_id)
        if existing_response:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Response already exists for this review"
            )

        # Create response
        response = await self.repo.create_review_response(
            review_id=review_id,
            vendor_id=review.vendor_id,
            responder_id=current_user.id,
            response_text=response_data.response_text
        )

        await self.db.commit()

        return response

    async def update_review_response(
        self,
        response_id: UUID,
        response_data: ReviewResponseUpdate,
        current_user: User
    ):
        """
        Update vendor response

        Business rules:
        - Only responder can update
        - Can update within 7 days
        """
        from app.models.review import ReviewResponse
        response = await self.db.get(ReviewResponse, response_id)
        if not response or response.deleted_at:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Response not found"
            )

        # Check if user is responder
        if str(response.responder_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only responder can update response"
            )

        # Check time limit (7 days)
        days_since_creation = (datetime.utcnow() - response.created_at).days
        if days_since_creation > 7:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update response after 7 days"
            )

        # Update response
        updated_response = await self.repo.update_review_response(
            response_id,
            response_data.response_text
        )

        await self.db.commit()

        return updated_response

    async def delete_review_response(
        self,
        response_id: UUID,
        current_user: User
    ):
        """Delete vendor response"""
        from app.models.review import ReviewResponse
        response = await self.db.get(ReviewResponse, response_id)
        if not response or response.deleted_at:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Response not found"
            )

        # Check permissions
        is_responder = str(response.responder_id) == str(current_user.id)
        is_admin = current_user.role == UserRole.ADMIN.value

        if not (is_responder or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this response"
            )

        # Delete response
        success = await self.repo.delete_review_response(response_id)
        await self.db.commit()

        return success

    # ========================================================================
    # Review Helpfulness Operations
    # ========================================================================

    async def vote_helpfulness(
        self,
        review_id: UUID,
        vote_data: ReviewHelpfulnessCreate,
        current_user: User
    ):
        """Vote on review helpfulness"""
        # Check if review exists
        review = await self.repo.get_review_by_id(review_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )

        # Cannot vote on own review
        if str(review.reviewer_id) == str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot vote on your own review"
            )

        # Vote
        vote = await self.repo.vote_helpfulness(
            review_id,
            current_user.id,
            vote_data.is_helpful
        )

        await self.db.commit()

        return vote

    async def get_user_vote(
        self,
        review_id: UUID,
        current_user: User
    ):
        """Get user's vote for a review"""
        return await self.repo.get_user_helpfulness_vote(review_id, current_user.id)

    # ========================================================================
    # Review Report Operations
    # ========================================================================

    async def report_review(
        self,
        review_id: UUID,
        report_data: ReviewReportCreate,
        current_user: User
    ):
        """Report a review"""
        # Check if review exists
        review = await self.repo.get_review_by_id(review_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )

        # Cannot report own review
        if str(review.reviewer_id) == str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot report your own review"
            )

        # Create report
        report = await self.repo.create_review_report(
            review_id=review_id,
            reporter_id=current_user.id,
            reason=report_data.reason.value,
            description=report_data.description
        )

        await self.db.commit()

        return report

    async def get_review_reports(
        self,
        review_id: Optional[UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        current_user: Optional[User] = None
    ):
        """Get review reports (admin only)"""
        if current_user and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        return await self.repo.get_review_reports(review_id, status, page, page_size)

    async def update_review_report(
        self,
        report_id: UUID,
        report_data: ReviewReportUpdate,
        current_user: User
    ):
        """Update review report (admin only)"""
        if current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        report = await self.repo.update_review_report(
            report_id=report_id,
            status=report_data.status.value,
            investigator_id=current_user.id,
            investigation_notes=report_data.investigation_notes,
            resolution=report_data.resolution
        )

        await self.db.commit()

        return report

    # ========================================================================
    # Rating Statistics Operations
    # ========================================================================

    async def get_vendor_rating_stats(self, vendor_id: UUID):
        """Get vendor rating statistics"""
        stats = await self.repo.get_vendor_rating_stats(vendor_id)
        if not stats:
            # Return empty stats if vendor has no reviews
            from app.models.review import VendorRatingCache
            from decimal import Decimal
            stats = VendorRatingCache(
                vendor_id=vendor_id,
                total_reviews=0,
                average_rating=Decimal(0),
                one_star_count=0,
                two_star_count=0,
                three_star_count=0,
                four_star_count=0,
                five_star_count=0,
                total_helpful_votes=0,
                response_rate=Decimal(0),
                recent_reviews_30d=0,
                last_calculated_at=datetime.utcnow()
            )

        return stats

    # ========================================================================
    # Moderation Operations (Admin)
    # ========================================================================

    async def moderate_review(
        self,
        review_id: UUID,
        moderation_data: ReviewModerationUpdate,
        current_user: User
    ):
        """Moderate a review (admin only)"""
        if current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        review = await self.repo.moderate_review(
            review_id=review_id,
            status=moderation_data.status.value,
            moderator_id=current_user.id,
            moderation_notes=moderation_data.moderation_notes,
            is_featured=moderation_data.is_featured
        )

        await self.db.commit()

        return review

    async def bulk_moderate_reviews(
        self,
        bulk_action: ReviewBulkAction,
        current_user: User
    ):
        """Bulk moderate reviews (admin only)"""
        if current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        count = await self.repo.bulk_moderate_reviews(
            review_ids=bulk_action.review_ids,
            action=bulk_action.action,
            moderator_id=current_user.id,
            notes=bulk_action.notes
        )

        await self.db.commit()

        return {"moderated_count": count}
