"""
CelebraTech Event Management System - Recommendation API
Sprint 17: AI & Recommendation Engine
FastAPI endpoints for AI-powered recommendations and predictions
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.recommendation import (
    RecommendationType,
    RecommendationAlgorithm,
    InteractionType,
    FeedbackType,
    PredictionType
)
from app.schemas.recommendation import (
    UserBehaviorCreate,
    UserBehaviorResponse,
    UserPreferenceCreate,
    UserPreferenceResponse,
    RecommendationResponse,
    RecommendationFeedbackCreate,
    RecommendationFeedbackResponse,
    VendorMatchResponse,
    PredictionCreate,
    PredictionResponse,
    MLModelCreate,
    MLModelResponse,
    ExperimentCreate,
    ExperimentResponse
)
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["AI & Recommendations"])


# ============================================================================
# User Behavior Tracking Endpoints
# ============================================================================

@router.post(
    "/behavior",
    response_model=UserBehaviorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Track user interaction",
    description="Track user interaction for learning preferences"
)
async def track_interaction(
    behavior_data: UserBehaviorCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Track user interaction behavior"""
    rec_service = RecommendationService(db)
    behavior = await rec_service.track_interaction(
        current_user.id,
        behavior_data.interaction_type,
        behavior_data.entity_type,
        behavior_data.entity_id,
        current_user,
        behavior_data.metadata
    )
    return UserBehaviorResponse.from_orm(behavior)


@router.get(
    "/behavior/history",
    response_model=List[UserBehaviorResponse],
    summary="Get behavior history",
    description="Get user's interaction history"
)
async def get_behavior_history(
    interaction_type: Optional[InteractionType] = Query(None, description="Filter by interaction type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    days_back: int = Query(30, ge=1, le=365, description="Days to look back"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get behavior history"""
    rec_service = RecommendationService(db)
    behaviors = await rec_service.get_user_behavior_history(
        current_user.id,
        current_user,
        interaction_type,
        entity_type,
        days_back
    )
    return [UserBehaviorResponse.from_orm(b) for b in behaviors]


# ============================================================================
# User Preferences Endpoints
# ============================================================================

@router.post(
    "/preferences",
    response_model=UserPreferenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save user preference",
    description="Save or update user preference"
)
async def save_preference(
    preference_data: UserPreferenceCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Save user preference"""
    rec_service = RecommendationService(db)
    preference = await rec_service.save_preference(
        preference_data.preference_key,
        preference_data.preference_value,
        current_user,
        preference_data.preference_type
    )
    return UserPreferenceResponse.from_orm(preference)


@router.get(
    "/preferences",
    response_model=List[UserPreferenceResponse],
    summary="Get user preferences",
    description="Get all user preferences"
)
async def get_preferences(
    preference_type: Optional[str] = Query(None, description="Filter by preference type"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user preferences"""
    rec_service = RecommendationService(db)
    preferences = await rec_service.get_user_preferences(current_user, preference_type)
    return [UserPreferenceResponse.from_orm(p) for p in preferences]


# ============================================================================
# Recommendation Endpoints
# ============================================================================

@router.post(
    "/vendors/generate",
    response_model=List[RecommendationResponse],
    summary="Generate vendor recommendations",
    description="Generate personalized vendor recommendations"
)
async def generate_vendor_recommendations(
    event_id: Optional[UUID] = Query(None, description="Event context"),
    limit: int = Query(10, ge=1, le=50),
    algorithm: RecommendationAlgorithm = Query(RecommendationAlgorithm.HYBRID),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate vendor recommendations"""
    rec_service = RecommendationService(db)
    recommendations = await rec_service.generate_vendor_recommendations(
        current_user,
        event_id,
        limit,
        algorithm
    )
    return [RecommendationResponse.from_orm(r) for r in recommendations]


@router.get(
    "/",
    response_model=List[RecommendationResponse],
    summary="Get recommendations",
    description="Get user's recommendations"
)
async def get_recommendations(
    recommendation_type: Optional[RecommendationType] = Query(None, description="Filter by type"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recommendations"""
    rec_service = RecommendationService(db)
    recommendations = await rec_service.get_recommendations(
        current_user,
        recommendation_type,
        limit
    )
    return [RecommendationResponse.from_orm(r) for r in recommendations]


@router.post(
    "/{recommendation_id}/shown",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark recommendation shown",
    description="Mark recommendation as shown to user"
)
async def mark_recommendation_shown(
    recommendation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark recommendation as shown"""
    rec_service = RecommendationService(db)
    await rec_service.mark_recommendation_shown(recommendation_id, current_user)


@router.post(
    "/{recommendation_id}/clicked",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark recommendation clicked",
    description="Mark recommendation as clicked"
)
async def mark_recommendation_clicked(
    recommendation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark recommendation as clicked"""
    rec_service = RecommendationService(db)
    await rec_service.mark_recommendation_clicked(recommendation_id, current_user)


@router.post(
    "/{recommendation_id}/feedback",
    response_model=RecommendationFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provide recommendation feedback",
    description="Provide feedback on a recommendation"
)
async def provide_feedback(
    recommendation_id: UUID,
    feedback_data: RecommendationFeedbackCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Provide recommendation feedback"""
    rec_service = RecommendationService(db)
    feedback = await rec_service.provide_feedback(
        recommendation_id,
        feedback_data.feedback_type,
        current_user,
        feedback_data.rating,
        feedback_data.comment
    )
    return RecommendationFeedbackResponse.from_orm(feedback)


# ============================================================================
# Vendor Matching Endpoints
# ============================================================================

@router.post(
    "/events/{event_id}/match-vendors",
    response_model=List[VendorMatchResponse],
    summary="Match vendors to event",
    description="Generate smart vendor matches for an event"
)
async def match_vendors(
    event_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Match vendors to event"""
    rec_service = RecommendationService(db)
    matches = await rec_service.match_vendors_for_event(event_id, current_user, limit)
    return [VendorMatchResponse.from_orm(m) for m in matches]


@router.get(
    "/events/{event_id}/vendor-matches",
    response_model=List[VendorMatchResponse],
    summary="Get vendor matches",
    description="Get vendor matches for an event"
)
async def get_vendor_matches(
    event_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get vendor matches"""
    rec_service = RecommendationService(db)
    matches = await rec_service.get_event_vendor_matches(event_id, current_user, limit)
    return [VendorMatchResponse.from_orm(m) for m in matches]


# ============================================================================
# Prediction Endpoints
# ============================================================================

@router.post(
    "/predict/budget",
    response_model=PredictionResponse,
    summary="Predict event budget",
    description="Predict budget for an event based on features"
)
async def predict_budget(
    prediction_data: PredictionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Predict event budget"""
    rec_service = RecommendationService(db)
    prediction = await rec_service.predict_budget(
        prediction_data.entity_id,
        current_user,
        prediction_data.features
    )
    return PredictionResponse.from_orm(prediction)


@router.post(
    "/predict/guest-count",
    response_model=PredictionResponse,
    summary="Predict guest count",
    description="Predict guest count for an event"
)
async def predict_guest_count(
    prediction_data: PredictionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Predict guest count"""
    rec_service = RecommendationService(db)
    prediction = await rec_service.predict_guest_count(
        prediction_data.entity_id,
        current_user,
        prediction_data.features
    )
    return PredictionResponse.from_orm(prediction)


@router.get(
    "/predictions",
    response_model=List[PredictionResponse],
    summary="Get user predictions",
    description="Get all predictions for current user"
)
async def get_predictions(
    prediction_type: Optional[PredictionType] = Query(None, description="Filter by type"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user predictions"""
    rec_service = RecommendationService(db)
    predictions = await rec_service.get_user_predictions(
        current_user,
        prediction_type,
        limit
    )
    return [PredictionResponse.from_orm(p) for p in predictions]


# ============================================================================
# ML Model Management Endpoints (Admin)
# ============================================================================

@router.post(
    "/models",
    response_model=MLModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register ML model",
    description="Register a new ML model (admin only)"
)
async def register_model(
    model_data: MLModelCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Register ML model"""
    rec_service = RecommendationService(db)
    model = await rec_service.register_model(
        model_data.model_type,
        model_data.model_name,
        model_data.version,
        model_data.hyperparameters,
        model_data.metrics,
        current_user,
        model_data.artifact_path
    )
    return MLModelResponse.from_orm(model)


@router.post(
    "/models/{model_id}/activate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Activate ML model",
    description="Activate an ML model (admin only)"
)
async def activate_model(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Activate ML model"""
    rec_service = RecommendationService(db)
    await rec_service.activate_model(model_id, current_user)


# ============================================================================
# A/B Testing / Experiment Endpoints
# ============================================================================

@router.post(
    "/experiments",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create experiment",
    description="Create A/B test experiment (admin only)"
)
async def create_experiment(
    experiment_data: ExperimentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create A/B test experiment"""
    rec_service = RecommendationService(db)
    experiment = await rec_service.create_experiment(
        experiment_data.experiment_name,
        experiment_data.description,
        experiment_data.control_group,
        experiment_data.treatment_groups,
        experiment_data.start_date,
        experiment_data.end_date,
        experiment_data.success_metrics,
        current_user
    )
    return ExperimentResponse.from_orm(experiment)


@router.get(
    "/experiments/{experiment_name}/variant",
    response_model=dict,
    summary="Get experiment variant",
    description="Get user's assigned variant for an experiment"
)
async def get_experiment_variant(
    experiment_name: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's experiment variant"""
    rec_service = RecommendationService(db)
    variant = await rec_service.get_user_experiment_variant(experiment_name, current_user)
    return {"experiment_name": experiment_name, "variant": variant}


@router.get(
    "/experiments/active",
    response_model=List[ExperimentResponse],
    summary="Get active experiments",
    description="Get all active A/B test experiments"
)
async def get_active_experiments(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get active experiments"""
    rec_service = RecommendationService(db)
    experiments = await rec_service.get_active_experiments()
    return [ExperimentResponse.from_orm(e) for e in experiments]
