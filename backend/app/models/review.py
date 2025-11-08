"""
CelebraTech Event Management System - Review Models
Sprint 6: Review and Rating System
FR-006: Review and Rating Management
SQLAlchemy models for vendor reviews and ratings
"""
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, Numeric,
    DateTime, ForeignKey, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
import enum

from app.core.database import Base


# ============================================================================
# Enumerations
# ============================================================================

class ReviewRating(enum.IntEnum):
    """Review rating values (1-5 stars)"""
    ONE_STAR = 1
    TWO_STARS = 2
    THREE_STARS = 3
    FOUR_STARS = 4
    FIVE_STARS = 5


class ReviewStatus(str, enum.Enum):
    """Review moderation status"""
    PENDING = "pending"  # Awaiting moderation
    APPROVED = "approved"  # Visible to public
    REJECTED = "rejected"  # Violates guidelines
    FLAGGED = "flagged"  # Flagged for review
    HIDDEN = "hidden"  # Hidden by admin


class ReviewReportReason(str, enum.Enum):
    """Reasons for reporting a review"""
    INAPPROPRIATE = "inappropriate"  # Offensive content
    SPAM = "spam"  # Spam or promotional
    FAKE = "fake"  # Suspected fake review
    OFF_TOPIC = "off_topic"  # Not relevant
    PERSONAL_INFO = "personal_info"  # Contains personal information
    OTHER = "other"  # Other reason


class ReportStatus(str, enum.Enum):
    """Review report status"""
    PENDING = "pending"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# ============================================================================
# Models
# ============================================================================

class Review(Base):
    """
    Vendor review by customer

    Created after booking completion. Includes multi-category ratings,
    text review, photos, and verification status.
    """
    __tablename__ = "reviews"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True  # One review per booking
    )
    vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    reviewer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False
    )

    # Overall Rating (1-5 stars, required)
    overall_rating = Column(Integer, nullable=False)

    # Category Ratings (1-5 stars, optional)
    quality_rating = Column(Integer, nullable=True)  # Service/product quality
    professionalism_rating = Column(Integer, nullable=True)  # Vendor professionalism
    value_rating = Column(Integer, nullable=True)  # Value for money
    communication_rating = Column(Integer, nullable=True)  # Communication quality
    timeliness_rating = Column(Integer, nullable=True)  # On-time delivery

    # Review Content
    title = Column(String(200), nullable=True)  # Review title/headline
    comment = Column(Text, nullable=True)  # Detailed review text

    # Photos (array of URLs)
    photos = Column(ARRAY(String(500)), default=list)

    # Pros and Cons
    pros = Column(ARRAY(String(200)), default=list)  # What was good
    cons = Column(ARRAY(String(200)), default=list)  # What could improve

    # Verification
    is_verified = Column(Boolean, default=True)  # Verified booking completion
    event_date = Column(DateTime, nullable=False)  # When event occurred

    # Moderation
    status = Column(String(20), default=ReviewStatus.APPROVED.value)  # Review status
    moderation_notes = Column(Text, nullable=True)  # Admin notes
    moderated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    moderated_at = Column(DateTime, nullable=True)

    # Engagement Metrics
    helpful_count = Column(Integer, default=0)  # Number of helpful votes
    not_helpful_count = Column(Integer, default=0)  # Number of not helpful votes
    report_count = Column(Integer, default=0)  # Number of times reported

    # Response
    has_response = Column(Boolean, default=False)  # Vendor responded

    # Visibility
    is_featured = Column(Boolean, default=False)  # Featured by admin
    is_public = Column(Boolean, default=True)  # Visible to public

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete

    # Relationships
    booking = relationship("Booking", back_populates="review")
    vendor = relationship("Vendor", back_populates="reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="reviews_given")
    event = relationship("Event", back_populates="reviews")
    moderator = relationship("User", foreign_keys=[moderated_by])

    response = relationship(
        "ReviewResponse",
        back_populates="review",
        uselist=False,
        cascade="all, delete-orphan"
    )
    helpfulness_votes = relationship(
        "ReviewHelpfulness",
        back_populates="review",
        cascade="all, delete-orphan"
    )
    reports = relationship(
        "ReviewReport",
        back_populates="review",
        cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint('overall_rating >= 1 AND overall_rating <= 5', name='check_overall_rating'),
        CheckConstraint('quality_rating IS NULL OR (quality_rating >= 1 AND quality_rating <= 5)', name='check_quality_rating'),
        CheckConstraint('professionalism_rating IS NULL OR (professionalism_rating >= 1 AND professionalism_rating <= 5)', name='check_professionalism_rating'),
        CheckConstraint('value_rating IS NULL OR (value_rating >= 1 AND value_rating <= 5)', name='check_value_rating'),
        CheckConstraint('communication_rating IS NULL OR (communication_rating >= 1 AND communication_rating <= 5)', name='check_communication_rating'),
        CheckConstraint('timeliness_rating IS NULL OR (timeliness_rating >= 1 AND timeliness_rating <= 5)', name='check_timeliness_rating'),
        CheckConstraint('helpful_count >= 0', name='check_helpful_count'),
        CheckConstraint('not_helpful_count >= 0', name='check_not_helpful_count'),
        CheckConstraint('report_count >= 0', name='check_report_count'),
        Index('idx_reviews_vendor_status', 'vendor_id', 'status'),
        Index('idx_reviews_vendor_rating', 'vendor_id', 'overall_rating'),
        Index('idx_reviews_created', 'created_at'),
        Index('idx_reviews_featured', 'is_featured', 'status'),
    )

    def __repr__(self):
        return f"<Review {self.id}: {self.overall_rating}★ by {self.reviewer_id} for {self.vendor_id}>"


class ReviewResponse(Base):
    """
    Vendor response to a review

    Allows vendors to respond to customer reviews professionally.
    """
    __tablename__ = "review_responses"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    review_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        unique=True  # One response per review
    )
    vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False
    )
    responder_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Response Content
    response_text = Column(Text, nullable=False)

    # Moderation
    status = Column(String(20), default=ReviewStatus.APPROVED.value)
    moderation_notes = Column(Text, nullable=True)
    moderated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    moderated_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    review = relationship("Review", back_populates="response")
    vendor = relationship("Vendor")
    responder = relationship("User", foreign_keys=[responder_id])
    moderator = relationship("User", foreign_keys=[moderated_by])

    # Indexes
    __table_args__ = (
        Index('idx_review_responses_review', 'review_id'),
        Index('idx_review_responses_vendor', 'vendor_id'),
    )

    def __repr__(self):
        return f"<ReviewResponse {self.id} to review {self.review_id}>"


class ReviewHelpfulness(Base):
    """
    User votes on review helpfulness

    Users can mark reviews as helpful or not helpful.
    """
    __tablename__ = "review_helpfulness"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    review_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Vote
    is_helpful = Column(Boolean, nullable=False)  # True = helpful, False = not helpful

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    review = relationship("Review", back_populates="helpfulness_votes")
    user = relationship("User")

    # Constraints - One vote per user per review
    __table_args__ = (
        UniqueConstraint('review_id', 'user_id', name='unique_review_user_vote'),
        Index('idx_helpfulness_review', 'review_id'),
        Index('idx_helpfulness_user', 'user_id'),
    )

    def __repr__(self):
        return f"<ReviewHelpfulness {self.id}: {'Helpful' if self.is_helpful else 'Not Helpful'}>"


class ReviewReport(Base):
    """
    Reports of inappropriate reviews

    Users can report reviews that violate guidelines.
    """
    __tablename__ = "review_reports"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    review_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    reporter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Report Details
    reason = Column(String(50), nullable=False)  # ReviewReportReason
    description = Column(Text, nullable=True)  # Additional details

    # Investigation
    status = Column(String(20), default=ReportStatus.PENDING.value)
    investigated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    investigation_notes = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)  # Action taken
    resolved_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    review = relationship("Review", back_populates="reports")
    reporter = relationship("User", foreign_keys=[reporter_id])
    investigator = relationship("User", foreign_keys=[investigated_by])

    # Constraints
    __table_args__ = (
        Index('idx_review_reports_review', 'review_id'),
        Index('idx_review_reports_status', 'status'),
        Index('idx_review_reports_created', 'created_at'),
    )

    def __repr__(self):
        return f"<ReviewReport {self.id}: {self.reason} on review {self.review_id}>"


class VendorRatingCache(Base):
    """
    Cached vendor rating statistics

    Denormalized table for fast rating queries. Updated periodically
    or when reviews change.
    """
    __tablename__ = "vendor_rating_cache"

    # Primary Key (vendor_id is the PK)
    vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        primary_key=True
    )

    # Overall Statistics
    total_reviews = Column(Integer, default=0, nullable=False)
    average_rating = Column(Numeric(3, 2), default=0, nullable=False)  # e.g., 4.65

    # Rating Distribution
    one_star_count = Column(Integer, default=0)
    two_star_count = Column(Integer, default=0)
    three_star_count = Column(Integer, default=0)
    four_star_count = Column(Integer, default=0)
    five_star_count = Column(Integer, default=0)

    # Category Averages
    avg_quality_rating = Column(Numeric(3, 2), nullable=True)
    avg_professionalism_rating = Column(Numeric(3, 2), nullable=True)
    avg_value_rating = Column(Numeric(3, 2), nullable=True)
    avg_communication_rating = Column(Numeric(3, 2), nullable=True)
    avg_timeliness_rating = Column(Numeric(3, 2), nullable=True)

    # Engagement
    total_helpful_votes = Column(Integer, default=0)
    response_rate = Column(Numeric(5, 2), default=0)  # Percentage of reviews with responses
    avg_response_time_hours = Column(Numeric(8, 2), nullable=True)  # Average hours to respond

    # Recent Activity
    recent_reviews_30d = Column(Integer, default=0)  # Reviews in last 30 days
    recent_average_30d = Column(Numeric(3, 2), nullable=True)  # Average rating last 30 days

    # Metadata
    last_calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    vendor = relationship("Vendor", back_populates="rating_cache")

    # Constraints
    __table_args__ = (
        CheckConstraint('total_reviews >= 0', name='check_total_reviews'),
        CheckConstraint('average_rating >= 0 AND average_rating <= 5', name='check_average_rating'),
        CheckConstraint('response_rate >= 0 AND response_rate <= 100', name='check_response_rate'),
        Index('idx_vendor_rating_cache_rating', 'average_rating'),
    )

    def __repr__(self):
        return f"<VendorRatingCache {self.vendor_id}: {self.average_rating}★ ({self.total_reviews} reviews)>"
