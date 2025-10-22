"""
Search & Discovery Models
Sprint 13: Search & Discovery System

Database models for search functionality:
- Saved searches
- Search analytics
- Search suggestions
- Search filters
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    Text, ForeignKey, JSON, Index, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


# ============================================================================
# Enums
# ============================================================================

class SearchType(str, enum.Enum):
    """Search type enumeration"""
    VENDOR = "vendor"
    EVENT = "event"
    SERVICE = "service"
    VENUE = "venue"
    ALL = "all"


class SearchSortBy(str, enum.Enum):
    """Search sorting options"""
    RELEVANCE = "relevance"
    RATING = "rating"
    PRICE_LOW = "price_low"
    PRICE_HIGH = "price_high"
    DISTANCE = "distance"
    POPULARITY = "popularity"
    NEWEST = "newest"


class SearchFilterType(str, enum.Enum):
    """Search filter types"""
    CATEGORY = "category"
    PRICE_RANGE = "price_range"
    LOCATION = "location"
    RATING = "rating"
    AVAILABILITY = "availability"
    VERIFIED = "verified"
    FEATURED = "featured"


# ============================================================================
# Saved Search Models
# ============================================================================

class SavedSearch(Base):
    """
    User's saved searches for quick access.

    Allows users to save frequently used search queries
    and receive notifications when new matching results appear.
    """
    __tablename__ = "saved_searches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Search details
    name = Column(String(200), nullable=False)  # User-defined name
    description = Column(Text, nullable=True)
    search_type = Column(String(20), default=SearchType.VENDOR.value, index=True)

    # Search query (JSON)
    query_params = Column(JSON, default={
        "keywords": None,
        "category": None,
        "location": None,
        "price_range": None,
        "rating_min": None,
        "filters": {}
    })

    # Geospatial search
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    radius_km = Column(Float, nullable=True)

    # Notification settings
    notify_on_new_results = Column(Boolean, default=True)
    notification_frequency = Column(String(20), default="daily")  # immediate, daily, weekly

    # Usage tracking
    use_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    result_count_last_run = Column(Integer, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="saved_searches")

    # Indexes
    __table_args__ = (
        Index('idx_saved_search_user_type', 'user_id', 'search_type'),
        Index('idx_saved_search_active', 'is_active'),
        Index('idx_saved_search_location', 'latitude', 'longitude'),
    )


# ============================================================================
# Search Analytics Models
# ============================================================================

class SearchAnalytics(Base):
    """
    Search query analytics for tracking and optimization.

    Records all search queries to understand user behavior,
    improve search relevance, and identify trends.
    """
    __tablename__ = "search_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User reference (nullable for anonymous searches)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Search details
    search_type = Column(String(20), default=SearchType.VENDOR.value, index=True)
    query_text = Column(Text, nullable=True, index=True)  # Raw search query

    # Search parameters (JSON)
    filters_applied = Column(JSON, default={})
    sort_by = Column(String(20), nullable=True)

    # Geospatial
    search_latitude = Column(Float, nullable=True)
    search_longitude = Column(Float, nullable=True)
    search_radius_km = Column(Float, nullable=True)

    # Results
    results_count = Column(Integer, default=0)
    results_shown = Column(Integer, default=0)  # With pagination
    results_clicked = Column(ARRAY(UUID(as_uuid=True)), default=list)  # IDs clicked

    # Performance metrics
    search_duration_ms = Column(Integer, nullable=True)
    elasticsearch_used = Column(Boolean, default=False)

    # User interaction
    clicked_position = Column(Integer, nullable=True)  # Position of first click
    session_id = Column(String(100), nullable=True, index=True)

    # Context
    page = Column(String(100), nullable=True)  # Where search was performed
    device_type = Column(String(20), nullable=True)  # mobile, tablet, desktop

    # Timestamps
    searched_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", backref="search_history")

    # Indexes
    __table_args__ = (
        Index('idx_search_analytics_query', 'query_text'),
        Index('idx_search_analytics_type', 'search_type'),
        Index('idx_search_analytics_date', 'searched_at'),
        Index('idx_search_analytics_results', 'results_count'),
    )


# ============================================================================
# Search Suggestion Models
# ============================================================================

class SearchSuggestion(Base):
    """
    Search suggestions and autocomplete.

    Stores popular search terms, trending searches,
    and curated suggestions for better user experience.
    """
    __tablename__ = "search_suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Suggestion details
    suggestion_text = Column(String(200), nullable=False, unique=True, index=True)
    suggestion_type = Column(String(20), default=SearchType.VENDOR.value)

    # Categorization
    category = Column(String(100), nullable=True, index=True)
    tags = Column(ARRAY(String(50)), default=list)

    # Popularity metrics
    search_count = Column(Integer, default=0, index=True)  # How many times searched
    click_through_rate = Column(Float, default=0.0)  # CTR
    conversion_rate = Column(Float, default=0.0)  # Booking rate after search

    # Relevance
    relevance_score = Column(Float, default=0.0)  # Calculated relevance
    is_trending = Column(Boolean, default=False, index=True)
    is_featured = Column(Boolean, default=False)  # Manually featured

    # Context
    seasonal = Column(Boolean, default=False)  # Seasonal suggestions
    region = Column(String(100), nullable=True)  # Region-specific
    language = Column(String(10), default="en")

    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_curated = Column(Boolean, default=False)  # Manually curated vs auto-generated

    # Metadata
    metadata = Column(JSON, default={})

    # Timestamps
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_searched_at = Column(DateTime, nullable=True)
    trending_since = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_search_suggestion_text', 'suggestion_text'),
        Index('idx_search_suggestion_trending', 'is_trending', 'search_count'),
        Index('idx_search_suggestion_category', 'category'),
    )


# ============================================================================
# Search Filter Preset Models
# ============================================================================

class SearchFilterPreset(Base):
    """
    Predefined search filter combinations.

    Allows admins to create curated filter presets
    like "Budget-Friendly Vendors", "Premium Services", etc.
    """
    __tablename__ = "search_filter_presets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Preset details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Icon identifier

    # Target search type
    search_type = Column(String(20), default=SearchType.VENDOR.value)

    # Filter configuration (JSON)
    filters = Column(JSON, default={})

    # Display
    display_order = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    color = Column(String(7), nullable=True)  # Hex color for UI

    # Usage tracking
    use_count = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_filter_preset_type', 'search_type'),
        Index('idx_filter_preset_order', 'display_order'),
    )


# ============================================================================
# Vendor Matching Score Models
# ============================================================================

class VendorMatchingScore(Base):
    """
    Vendor matching scores for event requirements.

    Stores calculated matching scores between vendors
    and specific event requirements for faster retrieval.
    """
    __tablename__ = "vendor_matching_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)

    # Matching scores (0-100)
    overall_score = Column(Float, nullable=False, index=True)

    # Component scores
    category_match_score = Column(Float, default=0.0)
    location_score = Column(Float, default=0.0)
    budget_score = Column(Float, default=0.0)
    availability_score = Column(Float, default=0.0)
    rating_score = Column(Float, default=0.0)
    experience_score = Column(Float, default=0.0)

    # AI-based scores
    cultural_fit_score = Column(Float, default=0.0)
    style_match_score = Column(Float, default=0.0)

    # Match details (JSON)
    match_details = Column(JSON, default={
        "strengths": [],
        "weaknesses": [],
        "recommendations": []
    })

    # Ranking
    rank_position = Column(Integer, nullable=True)

    # Timestamps
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)  # Cache expiration

    # Relationships
    vendor = relationship("Vendor", backref="matching_scores")
    event = relationship("Event", backref="vendor_matches")

    # Indexes
    __table_args__ = (
        Index('idx_matching_score_vendor', 'vendor_id'),
        Index('idx_matching_score_event', 'event_id'),
        Index('idx_matching_score_overall', 'overall_score'),
        Index('idx_matching_score_calculated', 'calculated_at'),
    )


# ============================================================================
# Search Index Status Models
# ============================================================================

class SearchIndexStatus(Base):
    """
    Track Elasticsearch indexing status.

    Monitors the sync status between PostgreSQL and Elasticsearch
    to ensure search index is up to date.
    """
    __tablename__ = "search_index_status"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Index details
    index_name = Column(String(100), nullable=False, unique=True)
    entity_type = Column(String(50), nullable=False)  # vendors, events, services

    # Status
    is_healthy = Column(Boolean, default=True)
    last_sync_at = Column(DateTime, nullable=True)
    last_full_reindex_at = Column(DateTime, nullable=True)

    # Metrics
    total_documents = Column(Integer, default=0)
    indexed_documents = Column(Integer, default=0)
    failed_documents = Column(Integer, default=0)

    # Sync details
    sync_in_progress = Column(Boolean, default=False)
    last_error = Column(Text, nullable=True)

    # Configuration (JSON)
    index_settings = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_index_status_name', 'index_name'),
        Index('idx_index_status_entity', 'entity_type'),
        Index('idx_index_status_health', 'is_healthy'),
    )
