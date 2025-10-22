"""
AI & Recommendation Engine Models
Sprint 17: AI & Recommendation Engine

Database models for AI-powered recommendations, user behavior tracking,
personalization, smart matching, and predictive analytics.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    Text, ForeignKey, JSON, Index, UniqueConstraint, ARRAY
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

class RecommendationType(str, enum.Enum):
    """Types of recommendations"""
    VENDOR = "vendor"
    EVENT_TEMPLATE = "event_template"
    SERVICE = "service"
    BUDGET_TEMPLATE = "budget_template"
    GUEST_GROUP = "guest_group"
    VENUE = "venue"
    TASK_TEMPLATE = "task_template"


class RecommendationAlgorithm(str, enum.Enum):
    """Recommendation algorithms"""
    CONTENT_BASED = "content_based"  # Based on item features
    COLLABORATIVE_FILTERING = "collaborative_filtering"  # Based on similar users
    HYBRID = "hybrid"  # Combination of multiple approaches
    POPULARITY = "popularity"  # Trending/popular items
    PERSONALIZED = "personalized"  # User-specific preferences
    CONTEXT_AWARE = "context_aware"  # Based on current context
    DEEP_LEARNING = "deep_learning"  # Neural network models


class InteractionType(str, enum.Enum):
    """User interaction types"""
    VIEW = "view"
    CLICK = "click"
    SEARCH = "search"
    BOOKMARK = "bookmark"
    SHARE = "share"
    INQUIRY = "inquiry"
    QUOTE_REQUEST = "quote_request"
    BOOKING = "booking"
    REVIEW = "review"
    DISMISS = "dismiss"  # Explicitly dismissed recommendation
    HIDE = "hide"  # Hide this type of recommendation


class FeedbackType(str, enum.Enum):
    """Feedback types"""
    EXPLICIT = "explicit"  # Direct rating/feedback
    IMPLICIT = "implicit"  # Inferred from behavior
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class ModelType(str, enum.Enum):
    """ML model types"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    RANKING = "ranking"
    EMBEDDING = "embedding"
    NEURAL_NETWORK = "neural_network"


class PredictionType(str, enum.Enum):
    """Types of predictions"""
    BUDGET_FORECAST = "budget_forecast"
    GUEST_COUNT = "guest_count"
    VENDOR_DEMAND = "vendor_demand"
    EVENT_SUCCESS = "event_success"
    BOOKING_LIKELIHOOD = "booking_likelihood"
    CHURN_RISK = "churn_risk"


# ============================================================================
# User Behavior Tracking Models
# ============================================================================

class UserBehavior(Base):
    """
    Track user interactions for learning preferences.

    Captures all user actions to build behavioral profiles
    and improve recommendations over time.
    """
    __tablename__ = "user_behaviors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Interaction details
    interaction_type = Column(String(50), nullable=False, index=True)  # InteractionType

    # Entity reference (polymorphic)
    entity_type = Column(String(50), nullable=False, index=True)  # vendor, event, service, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Context
    session_id = Column(String(255), nullable=True, index=True)
    source = Column(String(100), nullable=True)  # recommendation, search, browse, etc.

    # Interaction metadata
    duration_seconds = Column(Integer, nullable=True)  # Time spent
    interaction_data = Column(JSON, nullable=True)  # Additional context

    # Device and location
    device_type = Column(String(50), nullable=True)  # desktop, mobile, tablet
    platform = Column(String(50), nullable=True)  # ios, android, web
    location_data = Column(JSON, nullable=True)  # {city, country, coordinates}

    # Weighting
    weight = Column(Float, default=1.0)  # Importance weight (0-1)

    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_user_behaviors_user_occurred', 'user_id', 'occurred_at'),
        Index('ix_user_behaviors_entity', 'entity_type', 'entity_id'),
        Index('ix_user_behaviors_type_occurred', 'interaction_type', 'occurred_at'),
        Index('ix_user_behaviors_session', 'session_id'),
    )


class UserPreference(Base):
    """
    User preferences and settings for personalization.

    Explicit preferences and learned preferences from behavior.
    """
    __tablename__ = "user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Preference category
    category = Column(String(100), nullable=False, index=True)  # vendors, budget, style, etc.
    subcategory = Column(String(100), nullable=True)

    # Preference details
    preference_key = Column(String(200), nullable=False)
    preference_value = Column(JSON, nullable=False)  # Can be any type

    # Source
    source = Column(String(50), nullable=False, default="explicit")  # explicit, learned, inferred
    confidence = Column(Float, nullable=True)  # 0-1 confidence score for learned preferences

    # Priority
    weight = Column(Float, default=1.0)  # Importance weight

    # Metadata
    learned_at = Column(DateTime, nullable=True)  # When it was learned
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'category', 'preference_key', name='uq_user_preference'),
        Index('ix_user_preferences_user_category', 'user_id', 'category'),
    )


class UserProfile(Base):
    """
    Machine learning user profile with embeddings.

    Stores computed user embeddings and features for ML models.
    """
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # User embeddings (vector representations)
    embedding_vector = Column(ARRAY(Float), nullable=True)  # Dense embedding
    embedding_dimension = Column(Integer, nullable=True)
    embedding_model = Column(String(100), nullable=True)  # Model version used

    # Computed features
    features = Column(JSON, nullable=False, default={})  # {feature_name: value}

    # User segments
    segments = Column(ARRAY(String), nullable=True)  # [budget_conscious, luxury_seeker, etc.]
    persona = Column(String(100), nullable=True)  # Primary persona type

    # Preferences summary
    preferred_categories = Column(ARRAY(String), nullable=True)
    preferred_price_range = Column(JSON, nullable=True)  # {min, max, currency}
    preferred_locations = Column(ARRAY(String), nullable=True)
    preferred_vendors = Column(ARRAY(UUID(as_uuid=True)), nullable=True)

    # Behavior summary
    total_events = Column(Integer, default=0)
    total_bookings = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    average_event_budget = Column(Float, nullable=True)

    # Engagement metrics
    activity_score = Column(Float, default=0.0)  # Overall activity level
    engagement_level = Column(String(50), nullable=True)  # low, medium, high
    last_active_at = Column(DateTime, nullable=True)

    # Profile quality
    profile_completeness = Column(Float, default=0.0)  # 0-1 score
    data_quality_score = Column(Float, default=0.0)  # 0-1 score

    # Metadata
    profile_version = Column(Integer, default=1)
    last_computed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_user_profiles_user', 'user_id'),
        Index('ix_user_profiles_persona', 'persona'),
    )


# ============================================================================
# Recommendation Models
# ============================================================================

class Recommendation(Base):
    """
    Generated recommendations for users.

    Stores recommendations with explanations, scores, and tracking.
    """
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Recommendation type and target
    recommendation_type = Column(String(50), nullable=False, index=True)  # RecommendationType
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Context (optional)
    context_type = Column(String(50), nullable=True)  # event, search, browse
    context_id = Column(UUID(as_uuid=True), nullable=True)

    # Scoring
    score = Column(Float, nullable=False)  # Recommendation score (0-1)
    rank = Column(Integer, nullable=True)  # Rank in recommendation list

    # Algorithm used
    algorithm = Column(String(50), nullable=False)  # RecommendationAlgorithm
    model_version = Column(String(50), nullable=True)

    # Explanation
    explanation = Column(Text, nullable=True)  # Human-readable explanation
    reasoning = Column(JSON, nullable=True)  # Detailed reasoning factors
    features = Column(JSON, nullable=True)  # Features used for this recommendation

    # Personalization
    personalization_factors = Column(JSON, nullable=True)  # What made this personal
    diversity_factor = Column(Float, nullable=True)  # Diversity contribution

    # Tracking
    is_shown = Column(Boolean, default=False)
    is_clicked = Column(Boolean, default=False)
    is_converted = Column(Boolean, default=False)  # Led to desired action
    is_dismissed = Column(Boolean, default=False)

    shown_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    converted_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)

    # A/B Testing
    experiment_id = Column(String(100), nullable=True, index=True)
    variant = Column(String(50), nullable=True)

    # Metadata
    expires_at = Column(DateTime, nullable=True, index=True)  # Recommendation freshness
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_recommendations_user_type', 'user_id', 'recommendation_type'),
        Index('ix_recommendations_entity', 'entity_type', 'entity_id'),
        Index('ix_recommendations_user_created', 'user_id', 'created_at'),
        Index('ix_recommendations_score', 'score'),
        Index('ix_recommendations_experiment', 'experiment_id', 'variant'),
    )


class RecommendationFeedback(Base):
    """
    User feedback on recommendations.

    Captures explicit and implicit feedback to improve recommendations.
    """
    __tablename__ = "recommendation_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_id = Column(UUID(as_uuid=True), ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=True, index=True)

    # Feedback details
    feedback_type = Column(String(50), nullable=False)  # FeedbackType
    rating = Column(Integer, nullable=True)  # 1-5 stars (explicit feedback)
    sentiment = Column(String(50), nullable=True)  # positive, negative, neutral

    # Feedback content
    comment = Column(Text, nullable=True)
    reasons = Column(ARRAY(String), nullable=True)  # Why they gave this feedback

    # Inferred feedback (implicit)
    inferred_score = Column(Float, nullable=True)  # 0-1 inferred satisfaction
    signals = Column(JSON, nullable=True)  # Signals used for inference

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_recommendation_feedback_user', 'user_id'),
        Index('ix_recommendation_feedback_recommendation', 'recommendation_id'),
    )


# ============================================================================
# Smart Matching Models
# ============================================================================

class VendorMatchingProfile(Base):
    """
    ML profile for vendors to enable smart matching.

    Stores vendor embeddings and features for matching algorithms.
    """
    __tablename__ = "vendor_matching_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Vendor reference
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Vendor embeddings
    embedding_vector = Column(ARRAY(Float), nullable=True)
    embedding_dimension = Column(Integer, nullable=True)
    embedding_model = Column(String(100), nullable=True)

    # Extracted features
    features = Column(JSON, nullable=False, default={})

    # Service capabilities
    service_tags = Column(ARRAY(String), nullable=True)
    specializations = Column(ARRAY(String), nullable=True)
    target_segments = Column(ARRAY(String), nullable=True)

    # Performance metrics
    average_rating = Column(Float, nullable=True)
    total_bookings = Column(Integer, default=0)
    success_rate = Column(Float, nullable=True)
    response_time_hours = Column(Float, nullable=True)

    # Pricing
    price_range = Column(JSON, nullable=True)  # {min, max, currency}
    price_segment = Column(String(50), nullable=True)  # budget, mid-range, premium, luxury

    # Availability
    availability_score = Column(Float, nullable=True)  # 0-1 how often available
    capacity_utilization = Column(Float, nullable=True)

    # Quality indicators
    quality_score = Column(Float, nullable=True)  # 0-1 overall quality
    reliability_score = Column(Float, nullable=True)
    popularity_score = Column(Float, nullable=True)

    # Metadata
    profile_version = Column(Integer, default=1)
    last_computed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_vendor_matching_profiles_vendor', 'vendor_id'),
        Index('ix_vendor_matching_profiles_price_segment', 'price_segment'),
    )


class EventVendorMatch(Base):
    """
    Smart matching between events and vendors.

    AI-powered matching with scoring and explanations.
    """
    __tablename__ = "event_vendor_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)

    # Match scoring
    match_score = Column(Float, nullable=False)  # Overall match score (0-1)

    # Component scores
    service_match_score = Column(Float, nullable=True)  # Service fit
    budget_match_score = Column(Float, nullable=True)  # Budget fit
    style_match_score = Column(Float, nullable=True)  # Style compatibility
    availability_score = Column(Float, nullable=True)  # Availability fit
    location_score = Column(Float, nullable=True)  # Location proximity
    quality_score = Column(Float, nullable=True)  # Vendor quality

    # Confidence
    confidence = Column(Float, nullable=True)  # 0-1 confidence in match

    # Algorithm
    algorithm = Column(String(50), nullable=False)
    model_version = Column(String(50), nullable=True)

    # Explanation
    match_reasons = Column(ARRAY(String), nullable=True)  # Why this is a good match
    explanation = Column(Text, nullable=True)
    feature_contributions = Column(JSON, nullable=True)  # Feature importance

    # Status
    is_recommended = Column(Boolean, default=True)
    is_contacted = Column(Boolean, default=False)
    is_booked = Column(Boolean, default=False)

    # Metadata
    computed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint('event_id', 'vendor_id', name='uq_event_vendor_match'),
        Index('ix_event_vendor_matches_event', 'event_id'),
        Index('ix_event_vendor_matches_vendor', 'vendor_id'),
        Index('ix_event_vendor_matches_score', 'match_score'),
    )


# ============================================================================
# ML Models Management
# ============================================================================

class MLModel(Base):
    """
    Machine learning model registry.

    Tracks ML models, versions, performance, and metadata.
    """
    __tablename__ = "ml_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Model identity
    model_name = Column(String(200), nullable=False, index=True)
    model_type = Column(String(50), nullable=False)  # ModelType
    model_version = Column(String(50), nullable=False)

    # Purpose
    purpose = Column(String(200), nullable=False)  # What this model does
    description = Column(Text, nullable=True)

    # Model configuration
    algorithm = Column(String(100), nullable=False)
    hyperparameters = Column(JSON, nullable=True)
    features = Column(ARRAY(String), nullable=True)  # Feature names

    # Training info
    training_data_size = Column(Integer, nullable=True)
    training_date = Column(DateTime, nullable=True)
    training_duration_seconds = Column(Integer, nullable=True)

    # Performance metrics
    metrics = Column(JSON, nullable=True)  # {accuracy, precision, recall, etc.}

    # Model artifacts
    model_path = Column(String(500), nullable=True)  # Path to model file
    model_size_mb = Column(Float, nullable=True)

    # Deployment
    is_active = Column(Boolean, default=False, index=True)
    is_production = Column(Boolean, default=False)
    deployed_at = Column(DateTime, nullable=True)

    # A/B Testing
    traffic_percentage = Column(Float, default=0.0)  # 0-100 traffic split

    # Monitoring
    prediction_count = Column(Integer, default=0)
    average_latency_ms = Column(Float, nullable=True)
    error_rate = Column(Float, nullable=True)

    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint('model_name', 'model_version', name='uq_model_version'),
        Index('ix_ml_models_name_active', 'model_name', 'is_active'),
    )


class Prediction(Base):
    """
    ML model predictions for various use cases.

    Stores predictions for tracking, debugging, and improvement.
    """
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Model reference
    model_id = Column(UUID(as_uuid=True), ForeignKey("ml_models.id", ondelete="SET NULL"), nullable=True, index=True)
    model_name = Column(String(200), nullable=False, index=True)
    model_version = Column(String(50), nullable=False)

    # Prediction details
    prediction_type = Column(String(50), nullable=False, index=True)  # PredictionType

    # Target reference (polymorphic)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Input features
    input_features = Column(JSON, nullable=False)

    # Prediction output
    prediction_value = Column(JSON, nullable=False)  # Can be any type
    confidence = Column(Float, nullable=True)  # 0-1 confidence score
    probabilities = Column(JSON, nullable=True)  # Class probabilities

    # Explanation
    feature_importance = Column(JSON, nullable=True)
    explanation = Column(Text, nullable=True)

    # Ground truth (for evaluation)
    actual_value = Column(JSON, nullable=True)  # Actual outcome
    is_correct = Column(Boolean, nullable=True)
    error = Column(Float, nullable=True)  # Prediction error

    # Performance
    latency_ms = Column(Float, nullable=True)

    # Metadata
    predicted_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_predictions_type_predicted', 'prediction_type', 'predicted_at'),
        Index('ix_predictions_model_predicted', 'model_id', 'predicted_at'),
        Index('ix_predictions_entity', 'entity_type', 'entity_id'),
    )


# ============================================================================
# A/B Testing & Experiments
# ============================================================================

class Experiment(Base):
    """
    A/B testing experiments for recommendations and features.

    Manages experiments with variants and metrics tracking.
    """
    __tablename__ = "experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Experiment identity
    experiment_key = Column(String(200), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Experiment type
    experiment_type = Column(String(50), nullable=False)  # recommendation, feature, ui, etc.
    target = Column(String(100), nullable=True)  # What's being tested

    # Variants
    variants = Column(JSON, nullable=False)  # [{name, weight, config}]
    control_variant = Column(String(50), nullable=True)

    # Traffic allocation
    traffic_percentage = Column(Float, default=100.0)  # 0-100

    # Targeting
    target_segments = Column(ARRAY(String), nullable=True)
    target_criteria = Column(JSON, nullable=True)

    # Status
    status = Column(String(50), nullable=False, default="draft")  # draft, running, paused, completed

    # Timing
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Results
    results = Column(JSON, nullable=True)  # Experiment results
    winner_variant = Column(String(50), nullable=True)

    # Metrics
    primary_metric = Column(String(100), nullable=True)
    secondary_metrics = Column(ARRAY(String), nullable=True)

    # Sample size
    target_sample_size = Column(Integer, nullable=True)
    current_sample_size = Column(Integer, default=0)

    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('ix_experiments_status', 'status'),
        Index('ix_experiments_key', 'experiment_key'),
    )


class ExperimentAssignment(Base):
    """
    User assignments to experiment variants.

    Tracks which users are in which variant for consistency.
    """
    __tablename__ = "experiment_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)  # For anonymous users

    # Assignment
    variant = Column(String(50), nullable=False)

    # Tracking
    exposure_count = Column(Integer, default=0)
    first_exposure_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_exposure_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Conversion tracking
    has_converted = Column(Boolean, default=False)
    converted_at = Column(DateTime, nullable=True)
    conversion_value = Column(Float, nullable=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        Index('ix_experiment_assignments_experiment_user', 'experiment_id', 'user_id'),
        Index('ix_experiment_assignments_experiment_session', 'experiment_id', 'session_id'),
    )
