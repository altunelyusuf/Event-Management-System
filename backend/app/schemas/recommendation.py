"""
AI & Recommendation Engine Schemas
Sprint 17: AI & Recommendation Engine

Pydantic schemas for AI-powered recommendations, user behavior tracking,
personalization, smart matching, and predictive analytics.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# User Behavior Schemas
# ============================================================================

class UserBehaviorBase(BaseModel):
    """Base schema for user behavior"""
    interaction_type: str
    entity_type: str
    entity_id: UUID
    session_id: Optional[str] = None
    source: Optional[str] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    interaction_data: Optional[Dict[str, Any]] = None
    device_type: Optional[str] = None
    platform: Optional[str] = None
    location_data: Optional[Dict[str, Any]] = None
    weight: float = Field(1.0, ge=0.0, le=1.0)


class UserBehaviorCreate(UserBehaviorBase):
    """Schema for creating user behavior"""
    user_id: Optional[UUID] = None  # Optional for anonymous tracking


class UserBehaviorResponse(UserBehaviorBase):
    """Schema for user behavior response"""
    id: UUID
    user_id: UUID
    ip_address: Optional[str]
    occurred_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class UserBehaviorAnalytics(BaseModel):
    """Schema for user behavior analytics"""
    user_id: UUID
    total_interactions: int
    interaction_breakdown: Dict[str, int]
    top_entities: List[Dict[str, Any]]
    average_session_duration: Optional[float]
    most_active_times: List[str]
    device_distribution: Dict[str, int]
    engagement_score: float


# ============================================================================
# User Preference Schemas
# ============================================================================

class UserPreferenceBase(BaseModel):
    """Base schema for user preferences"""
    category: str = Field(..., max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    preference_key: str = Field(..., max_length=200)
    preference_value: Any
    source: str = Field("explicit")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight: float = Field(1.0, ge=0.0)


class UserPreferenceCreate(UserPreferenceBase):
    """Schema for creating user preference"""
    user_id: UUID


class UserPreferenceUpdate(BaseModel):
    """Schema for updating user preference"""
    preference_value: Optional[Any] = None
    source: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight: Optional[float] = Field(None, ge=0.0)


class UserPreferenceResponse(UserPreferenceBase):
    """Schema for user preference response"""
    id: UUID
    user_id: UUID
    learned_at: Optional[datetime]
    updated_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class UserPreferenceSummary(BaseModel):
    """Schema for user preference summary"""
    user_id: UUID
    preferences_by_category: Dict[str, List[Dict[str, Any]]]
    total_preferences: int
    explicit_count: int
    learned_count: int


# ============================================================================
# User Profile Schemas
# ============================================================================

class UserProfileBase(BaseModel):
    """Base schema for user profiles"""
    embedding_dimension: Optional[int] = None
    embedding_model: Optional[str] = None
    features: Dict[str, Any] = Field(default_factory=dict)
    segments: Optional[List[str]] = None
    persona: Optional[str] = None
    preferred_categories: Optional[List[str]] = None
    preferred_price_range: Optional[Dict[str, Any]] = None
    preferred_locations: Optional[List[str]] = None


class UserProfileUpdate(UserProfileBase):
    """Schema for updating user profile"""
    embedding_vector: Optional[List[float]] = None


class UserProfileResponse(UserProfileBase):
    """Schema for user profile response"""
    id: UUID
    user_id: UUID
    total_events: int
    total_bookings: int
    total_spent: float
    average_event_budget: Optional[float]
    activity_score: float
    engagement_level: Optional[str]
    last_active_at: Optional[datetime]
    profile_completeness: float
    data_quality_score: float
    profile_version: int
    last_computed_at: Optional[datetime]
    updated_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileWithRecommendations(UserProfileResponse):
    """User profile with recommendations"""
    recommendations: Optional[List[Dict[str, Any]]] = []


# ============================================================================
# Recommendation Schemas
# ============================================================================

class RecommendationRequest(BaseModel):
    """Schema for requesting recommendations"""
    user_id: UUID
    recommendation_type: str
    context_type: Optional[str] = None
    context_id: Optional[UUID] = None
    limit: int = Field(10, gt=0, le=50)
    algorithm: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    diversity: float = Field(0.5, ge=0.0, le=1.0)


class RecommendationResponse(BaseModel):
    """Schema for recommendation response"""
    id: UUID
    user_id: UUID
    recommendation_type: str
    entity_type: str
    entity_id: UUID
    context_type: Optional[str]
    context_id: Optional[UUID]
    score: float
    rank: Optional[int]
    algorithm: str
    model_version: Optional[str]
    explanation: Optional[str]
    reasoning: Optional[Dict[str, Any]]
    features: Optional[Dict[str, Any]]
    personalization_factors: Optional[Dict[str, Any]]
    diversity_factor: Optional[float]
    is_shown: bool
    is_clicked: bool
    is_converted: bool
    is_dismissed: bool
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class RecommendationWithEntity(RecommendationResponse):
    """Recommendation with entity details"""
    entity: Optional[Dict[str, Any]] = None


class RecommendationListResponse(BaseModel):
    """Schema for recommendation list response"""
    recommendations: List[RecommendationWithEntity]
    total: int
    algorithm: str
    computed_at: datetime


class RecommendationInteraction(BaseModel):
    """Schema for tracking recommendation interaction"""
    recommendation_id: UUID
    interaction_type: str = Field(..., regex="^(shown|clicked|converted|dismissed)$")
    metadata: Optional[Dict[str, Any]] = None


class RecommendationFeedbackCreate(BaseModel):
    """Schema for creating recommendation feedback"""
    user_id: UUID
    recommendation_id: Optional[UUID] = None
    feedback_type: str
    rating: Optional[int] = Field(None, ge=1, le=5)
    sentiment: Optional[str] = None
    comment: Optional[str] = Field(None, max_length=1000)
    reasons: Optional[List[str]] = None


class RecommendationFeedbackResponse(BaseModel):
    """Schema for recommendation feedback response"""
    id: UUID
    user_id: UUID
    recommendation_id: Optional[UUID]
    feedback_type: str
    rating: Optional[int]
    sentiment: Optional[str]
    comment: Optional[str]
    reasons: Optional[List[str]]
    inferred_score: Optional[float]
    signals: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Smart Matching Schemas
# ============================================================================

class VendorMatchingProfileBase(BaseModel):
    """Base schema for vendor matching profiles"""
    embedding_dimension: Optional[int] = None
    embedding_model: Optional[str] = None
    features: Dict[str, Any] = Field(default_factory=dict)
    service_tags: Optional[List[str]] = None
    specializations: Optional[List[str]] = None
    target_segments: Optional[List[str]] = None
    price_range: Optional[Dict[str, Any]] = None
    price_segment: Optional[str] = None


class VendorMatchingProfileUpdate(VendorMatchingProfileBase):
    """Schema for updating vendor matching profile"""
    embedding_vector: Optional[List[float]] = None
    average_rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    success_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    response_time_hours: Optional[float] = Field(None, ge=0.0)
    availability_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class VendorMatchingProfileResponse(VendorMatchingProfileBase):
    """Schema for vendor matching profile response"""
    id: UUID
    vendor_id: UUID
    average_rating: Optional[float]
    total_bookings: int
    success_rate: Optional[float]
    response_time_hours: Optional[float]
    availability_score: Optional[float]
    capacity_utilization: Optional[float]
    quality_score: Optional[float]
    reliability_score: Optional[float]
    popularity_score: Optional[float]
    profile_version: int
    last_computed_at: Optional[datetime]
    updated_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class EventVendorMatchRequest(BaseModel):
    """Schema for requesting event-vendor matches"""
    event_id: UUID
    limit: int = Field(10, gt=0, le=50)
    algorithm: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    min_score: float = Field(0.5, ge=0.0, le=1.0)


class EventVendorMatchResponse(BaseModel):
    """Schema for event-vendor match response"""
    id: UUID
    event_id: UUID
    vendor_id: UUID
    match_score: float
    service_match_score: Optional[float]
    budget_match_score: Optional[float]
    style_match_score: Optional[float]
    availability_score: Optional[float]
    location_score: Optional[float]
    quality_score: Optional[float]
    confidence: Optional[float]
    algorithm: str
    model_version: Optional[str]
    match_reasons: Optional[List[str]]
    explanation: Optional[str]
    feature_contributions: Optional[Dict[str, Any]]
    is_recommended: bool
    is_contacted: bool
    is_booked: bool
    computed_at: datetime
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class EventVendorMatchWithVendor(EventVendorMatchResponse):
    """Event-vendor match with vendor details"""
    vendor: Optional[Dict[str, Any]] = None


class EventVendorMatchListResponse(BaseModel):
    """Schema for event-vendor match list response"""
    matches: List[EventVendorMatchWithVendor]
    total: int
    algorithm: str
    computed_at: datetime


# ============================================================================
# ML Model Schemas
# ============================================================================

class MLModelBase(BaseModel):
    """Base schema for ML models"""
    model_name: str = Field(..., max_length=200)
    model_type: str
    model_version: str = Field(..., max_length=50)
    purpose: str = Field(..., max_length=200)
    description: Optional[str] = None
    algorithm: str = Field(..., max_length=100)
    hyperparameters: Optional[Dict[str, Any]] = None
    features: Optional[List[str]] = None


class MLModelCreate(MLModelBase):
    """Schema for creating ML model"""
    training_data_size: Optional[int] = Field(None, gt=0)
    training_date: Optional[datetime] = None
    training_duration_seconds: Optional[int] = Field(None, ge=0)
    metrics: Optional[Dict[str, Any]] = None
    model_path: Optional[str] = Field(None, max_length=500)
    model_size_mb: Optional[float] = Field(None, gt=0)


class MLModelUpdate(BaseModel):
    """Schema for updating ML model"""
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_production: Optional[bool] = None
    traffic_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    metrics: Optional[Dict[str, Any]] = None


class MLModelResponse(MLModelBase):
    """Schema for ML model response"""
    id: UUID
    training_data_size: Optional[int]
    training_date: Optional[datetime]
    training_duration_seconds: Optional[int]
    metrics: Optional[Dict[str, Any]]
    model_path: Optional[str]
    model_size_mb: Optional[float]
    is_active: bool
    is_production: bool
    deployed_at: Optional[datetime]
    traffic_percentage: float
    prediction_count: int
    average_latency_ms: Optional[float]
    error_rate: Optional[float]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MLModelPerformance(BaseModel):
    """Schema for ML model performance metrics"""
    model_id: UUID
    model_name: str
    model_version: str
    metrics: Dict[str, Any]
    prediction_count: int
    average_latency_ms: float
    error_rate: float
    last_updated: datetime


# ============================================================================
# Prediction Schemas
# ============================================================================

class PredictionRequest(BaseModel):
    """Schema for requesting prediction"""
    model_name: str
    prediction_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    input_features: Dict[str, Any]


class PredictionResponse(BaseModel):
    """Schema for prediction response"""
    id: UUID
    model_id: Optional[UUID]
    model_name: str
    model_version: str
    prediction_type: str
    entity_type: Optional[str]
    entity_id: Optional[UUID]
    input_features: Dict[str, Any]
    prediction_value: Any
    confidence: Optional[float]
    probabilities: Optional[Dict[str, Any]]
    feature_importance: Optional[Dict[str, Any]]
    explanation: Optional[str]
    latency_ms: Optional[float]
    predicted_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class PredictionFeedback(BaseModel):
    """Schema for prediction feedback (ground truth)"""
    prediction_id: UUID
    actual_value: Any
    feedback: Optional[str] = None


class BudgetPredictionRequest(BaseModel):
    """Schema for budget prediction request"""
    event_type: str
    guest_count: int = Field(..., gt=0)
    location: Optional[str] = None
    date: Optional[datetime] = None
    services: Optional[List[str]] = None
    user_preferences: Optional[Dict[str, Any]] = None


class BudgetPredictionResponse(BaseModel):
    """Schema for budget prediction response"""
    predicted_budget: float
    confidence: float
    budget_range: Dict[str, float]  # {min, max}
    breakdown_by_category: Dict[str, float]
    factors_considered: List[str]
    recommendations: List[str]


class GuestCountPredictionRequest(BaseModel):
    """Schema for guest count prediction"""
    event_type: str
    venue_capacity: Optional[int] = None
    historical_data: Optional[Dict[str, Any]] = None


class GuestCountPredictionResponse(BaseModel):
    """Schema for guest count prediction response"""
    predicted_count: int
    confidence: float
    count_range: Dict[str, int]  # {min, max}
    factors: List[str]


# ============================================================================
# Experiment Schemas
# ============================================================================

class ExperimentBase(BaseModel):
    """Base schema for experiments"""
    experiment_key: str = Field(..., max_length=200)
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    experiment_type: str = Field(..., max_length=50)
    target: Optional[str] = Field(None, max_length=100)
    variants: List[Dict[str, Any]]
    control_variant: Optional[str] = None
    traffic_percentage: float = Field(100.0, ge=0.0, le=100.0)
    target_segments: Optional[List[str]] = None
    target_criteria: Optional[Dict[str, Any]] = None


class ExperimentCreate(ExperimentBase):
    """Schema for creating experiment"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    primary_metric: Optional[str] = None
    secondary_metrics: Optional[List[str]] = None
    target_sample_size: Optional[int] = Field(None, gt=0)


class ExperimentUpdate(BaseModel):
    """Schema for updating experiment"""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None
    traffic_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None
    winner_variant: Optional[str] = None


class ExperimentResponse(ExperimentBase):
    """Schema for experiment response"""
    id: UUID
    status: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    results: Optional[Dict[str, Any]]
    winner_variant: Optional[str]
    primary_metric: Optional[str]
    secondary_metrics: Optional[List[str]]
    target_sample_size: Optional[int]
    current_sample_size: int
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExperimentAssignmentRequest(BaseModel):
    """Schema for experiment assignment request"""
    experiment_key: str
    user_id: Optional[UUID] = None
    session_id: Optional[str] = None


class ExperimentAssignmentResponse(BaseModel):
    """Schema for experiment assignment response"""
    experiment_key: str
    variant: str
    config: Dict[str, Any]


class ExperimentConversion(BaseModel):
    """Schema for experiment conversion"""
    experiment_id: UUID
    user_id: Optional[UUID] = None
    session_id: Optional[str] = None
    conversion_value: Optional[float] = None


class ExperimentResults(BaseModel):
    """Schema for experiment results"""
    experiment_id: UUID
    experiment_key: str
    status: str
    variant_results: List[Dict[str, Any]]
    winner_variant: Optional[str]
    statistical_significance: float
    recommendation: str


# ============================================================================
# Analytics & Insights Schemas
# ============================================================================

class RecommendationMetrics(BaseModel):
    """Schema for recommendation metrics"""
    total_recommendations: int
    shown_count: int
    click_count: int
    conversion_count: int
    dismiss_count: int
    click_through_rate: float
    conversion_rate: float
    average_score: float
    algorithm_breakdown: Dict[str, int]


class PersonalizationInsights(BaseModel):
    """Schema for personalization insights"""
    user_id: UUID
    profile_completeness: float
    engagement_level: str
    top_preferences: List[Dict[str, Any]]
    recommended_actions: List[str]
    personalization_quality: float


class ModelPerformanceReport(BaseModel):
    """Schema for model performance report"""
    model_name: str
    model_version: str
    time_period: Dict[str, datetime]
    total_predictions: int
    accuracy_metrics: Dict[str, float]
    latency_metrics: Dict[str, float]
    error_rate: float
    recommendations: List[str]


class SmartMatchingReport(BaseModel):
    """Schema for smart matching report"""
    event_id: UUID
    total_matches: int
    high_confidence_matches: int
    average_match_score: float
    top_matches: List[EventVendorMatchWithVendor]
    matching_quality: float
    recommendations: List[str]


# ============================================================================
# Bulk Operations Schemas
# ============================================================================

class BulkRecommendationRequest(BaseModel):
    """Schema for bulk recommendation request"""
    user_ids: List[UUID] = Field(..., max_items=100)
    recommendation_type: str
    limit_per_user: int = Field(10, gt=0, le=50)


class BulkRecommendationResponse(BaseModel):
    """Schema for bulk recommendation response"""
    results: Dict[str, List[RecommendationWithEntity]]
    total_users: int
    total_recommendations: int
    computed_at: datetime


class BulkProfileUpdate(BaseModel):
    """Schema for bulk profile update"""
    user_ids: List[UUID]
    recompute_embeddings: bool = False
    update_features: bool = True


class BulkMatchingRequest(BaseModel):
    """Schema for bulk matching request"""
    event_ids: List[UUID] = Field(..., max_items=50)
    vendor_filters: Optional[Dict[str, Any]] = None
    limit_per_event: int = Field(10, gt=0, le=50)


# ============================================================================
# Configuration Schemas
# ============================================================================

class RecommendationConfig(BaseModel):
    """Schema for recommendation configuration"""
    algorithm: str
    model_version: Optional[str] = None
    diversity_weight: float = Field(0.3, ge=0.0, le=1.0)
    freshness_weight: float = Field(0.2, ge=0.0, le=1.0)
    popularity_weight: float = Field(0.2, ge=0.0, le=1.0)
    personalization_weight: float = Field(0.3, ge=0.0, le=1.0)
    min_score_threshold: float = Field(0.5, ge=0.0, le=1.0)
    max_age_hours: Optional[int] = Field(24, gt=0)


class PersonalizationSettings(BaseModel):
    """Schema for personalization settings"""
    user_id: UUID
    enable_personalization: bool = True
    enable_behavioral_tracking: bool = True
    enable_predictions: bool = True
    privacy_level: str = Field("standard", regex="^(minimal|standard|enhanced)$")
    data_retention_days: int = Field(365, gt=0, le=1095)


class AISettings(BaseModel):
    """Schema for AI system settings"""
    enable_recommendations: bool = True
    enable_smart_matching: bool = True
    enable_predictions: bool = True
    enable_experiments: bool = True
    default_algorithm: str = "hybrid"
    update_frequency_hours: int = Field(24, gt=0)
    min_data_quality_score: float = Field(0.7, ge=0.0, le=1.0)
