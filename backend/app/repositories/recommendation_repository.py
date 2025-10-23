"""
CelebraTech Event Management System - Recommendation Repository
Sprint 17: AI & Recommendation Engine
Data access layer for AI/ML recommendations and predictions
"""
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from uuid import UUID
import json

from app.models.recommendation import (
    UserBehavior,
    UserPreference,
    UserProfile,
    Recommendation,
    RecommendationFeedback,
    VendorMatchingProfile,
    EventVendorMatch,
    MLModel,
    Prediction,
    Experiment,
    ExperimentAssignment,
    RecommendationType,
    RecommendationAlgorithm,
    InteractionType,
    FeedbackType,
    PredictionType
)


class RecommendationRepository:
    """Repository for recommendation and ML operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # User Behavior Tracking
    # ========================================================================

    async def track_behavior(
        self,
        user_id: UUID,
        interaction_type: InteractionType,
        entity_type: str,
        entity_id: UUID,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UserBehavior:
        """Track user interaction behavior"""
        behavior = UserBehavior(
            user_id=user_id,
            interaction_type=interaction_type,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {},
            interaction_time=datetime.utcnow()
        )

        self.db.add(behavior)
        await self.db.flush()
        await self.db.refresh(behavior)

        return behavior

    async def get_user_behaviors(
        self,
        user_id: UUID,
        interaction_type: Optional[InteractionType] = None,
        entity_type: Optional[str] = None,
        days_back: int = 30,
        limit: int = 100
    ) -> List[UserBehavior]:
        """Get user behavior history"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        query = select(UserBehavior).where(
            and_(
                UserBehavior.user_id == user_id,
                UserBehavior.interaction_time >= cutoff_date
            )
        )

        if interaction_type:
            query = query.where(UserBehavior.interaction_type == interaction_type)
        if entity_type:
            query = query.where(UserBehavior.entity_type == entity_type)

        query = query.order_by(UserBehavior.interaction_time.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_popular_entities(
        self,
        entity_type: str,
        interaction_type: Optional[InteractionType] = None,
        days_back: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most popular entities based on interactions"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        query = select(
            UserBehavior.entity_id,
            func.count(UserBehavior.id).label('interaction_count')
        ).where(
            and_(
                UserBehavior.entity_type == entity_type,
                UserBehavior.interaction_time >= cutoff_date
            )
        )

        if interaction_type:
            query = query.where(UserBehavior.interaction_type == interaction_type)

        query = query.group_by(UserBehavior.entity_id).order_by(
            desc('interaction_count')
        ).limit(limit)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {"entity_id": str(row.entity_id), "interaction_count": row.interaction_count}
            for row in rows
        ]

    # ========================================================================
    # User Preferences
    # ========================================================================

    async def save_user_preference(
        self,
        user_id: UUID,
        preference_key: str,
        preference_value: Any,
        preference_type: str = "general"
    ) -> UserPreference:
        """Save or update user preference"""
        # Check if preference exists
        query = select(UserPreference).where(
            and_(
                UserPreference.user_id == user_id,
                UserPreference.preference_key == preference_key
            )
        )
        result = await self.db.execute(query)
        preference = result.scalar_one_or_none()

        if preference:
            preference.preference_value = preference_value
            preference.updated_at = datetime.utcnow()
        else:
            preference = UserPreference(
                user_id=user_id,
                preference_key=preference_key,
                preference_value=preference_value,
                preference_type=preference_type
            )
            self.db.add(preference)

        await self.db.flush()
        await self.db.refresh(preference)

        return preference

    async def get_user_preferences(
        self,
        user_id: UUID,
        preference_type: Optional[str] = None
    ) -> List[UserPreference]:
        """Get all user preferences"""
        query = select(UserPreference).where(UserPreference.user_id == user_id)

        if preference_type:
            query = query.where(UserPreference.preference_type == preference_type)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # User Profile (ML Features)
    # ========================================================================

    async def create_or_update_user_profile(
        self,
        user_id: UUID,
        embedding_vector: Optional[List[float]] = None,
        features: Optional[Dict[str, Any]] = None,
        segments: Optional[List[str]] = None,
        persona: Optional[str] = None
    ) -> UserProfile:
        """Create or update ML user profile"""
        query = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await self.db.execute(query)
        profile = result.scalar_one_or_none()

        if profile:
            if embedding_vector:
                profile.embedding_vector = embedding_vector
                profile.embedding_dimension = len(embedding_vector)
            if features:
                profile.features = features
            if segments:
                profile.segments = segments
            if persona:
                profile.persona = persona
            profile.updated_at = datetime.utcnow()
        else:
            profile = UserProfile(
                user_id=user_id,
                embedding_vector=embedding_vector,
                embedding_dimension=len(embedding_vector) if embedding_vector else None,
                features=features or {},
                segments=segments or [],
                persona=persona
            )
            self.db.add(profile)

        await self.db.flush()
        await self.db.refresh(profile)

        return profile

    async def get_user_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Get user ML profile"""
        query = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # ========================================================================
    # Recommendations
    # ========================================================================

    async def create_recommendation(
        self,
        user_id: UUID,
        recommendation_type: RecommendationType,
        entity_id: UUID,
        score: float,
        algorithm: RecommendationAlgorithm,
        explanation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> Recommendation:
        """Create a recommendation"""
        recommendation = Recommendation(
            user_id=user_id,
            recommendation_type=recommendation_type,
            entity_id=entity_id,
            score=score,
            algorithm=algorithm,
            explanation=explanation,
            metadata=metadata or {},
            expires_at=expires_at,
            is_shown=False,
            is_clicked=False,
            is_dismissed=False
        )

        self.db.add(recommendation)
        await self.db.flush()
        await self.db.refresh(recommendation)

        return recommendation

    async def get_user_recommendations(
        self,
        user_id: UUID,
        recommendation_type: Optional[RecommendationType] = None,
        limit: int = 10,
        exclude_shown: bool = False
    ) -> List[Recommendation]:
        """Get recommendations for a user"""
        query = select(Recommendation).where(
            and_(
                Recommendation.user_id == user_id,
                or_(
                    Recommendation.expires_at.is_(None),
                    Recommendation.expires_at > datetime.utcnow()
                )
            )
        )

        if recommendation_type:
            query = query.where(Recommendation.recommendation_type == recommendation_type)

        if exclude_shown:
            query = query.where(Recommendation.is_shown == False)

        query = query.order_by(Recommendation.score.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_recommendation_shown(self, recommendation_id: UUID) -> bool:
        """Mark recommendation as shown"""
        query = select(Recommendation).where(Recommendation.id == recommendation_id)
        result = await self.db.execute(query)
        recommendation = result.scalar_one_or_none()

        if not recommendation:
            return False

        recommendation.is_shown = True
        recommendation.shown_at = datetime.utcnow()
        await self.db.flush()

        return True

    async def mark_recommendation_clicked(self, recommendation_id: UUID) -> bool:
        """Mark recommendation as clicked"""
        query = select(Recommendation).where(Recommendation.id == recommendation_id)
        result = await self.db.execute(query)
        recommendation = result.scalar_one_or_none()

        if not recommendation:
            return False

        recommendation.is_clicked = True
        recommendation.clicked_at = datetime.utcnow()
        await self.db.flush()

        return True

    # ========================================================================
    # Recommendation Feedback
    # ========================================================================

    async def create_feedback(
        self,
        recommendation_id: UUID,
        user_id: UUID,
        feedback_type: FeedbackType,
        rating: Optional[int] = None,
        comment: Optional[str] = None
    ) -> RecommendationFeedback:
        """Create recommendation feedback"""
        feedback = RecommendationFeedback(
            recommendation_id=recommendation_id,
            user_id=user_id,
            feedback_type=feedback_type,
            rating=rating,
            comment=comment
        )

        self.db.add(feedback)
        await self.db.flush()
        await self.db.refresh(feedback)

        return feedback

    # ========================================================================
    # Vendor Matching
    # ========================================================================

    async def create_vendor_matching_profile(
        self,
        vendor_id: UUID,
        embedding_vector: Optional[List[float]] = None,
        features: Optional[Dict[str, Any]] = None,
        categories: Optional[List[str]] = None,
        quality_score: float = 0.0
    ) -> VendorMatchingProfile:
        """Create vendor matching profile"""
        profile = VendorMatchingProfile(
            vendor_id=vendor_id,
            embedding_vector=embedding_vector,
            embedding_dimension=len(embedding_vector) if embedding_vector else None,
            features=features or {},
            categories=categories or [],
            quality_score=quality_score
        )

        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)

        return profile

    async def create_vendor_match(
        self,
        event_id: UUID,
        vendor_id: UUID,
        match_score: float,
        algorithm: RecommendationAlgorithm,
        factors: Optional[Dict[str, Any]] = None,
        is_recommended: bool = True
    ) -> EventVendorMatch:
        """Create event-vendor match"""
        match = EventVendorMatch(
            event_id=event_id,
            vendor_id=vendor_id,
            match_score=match_score,
            algorithm=algorithm,
            match_factors=factors or {},
            is_recommended=is_recommended
        )

        self.db.add(match)
        await self.db.flush()
        await self.db.refresh(match)

        return match

    async def get_vendor_matches(
        self,
        event_id: UUID,
        limit: int = 10
    ) -> List[EventVendorMatch]:
        """Get top vendor matches for an event"""
        query = select(EventVendorMatch).where(
            and_(
                EventVendorMatch.event_id == event_id,
                EventVendorMatch.is_recommended == True
            )
        ).order_by(EventVendorMatch.match_score.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # ML Models
    # ========================================================================

    async def register_ml_model(
        self,
        model_type: str,
        model_name: str,
        version: str,
        hyperparameters: Dict[str, Any],
        metrics: Dict[str, Any],
        artifact_path: Optional[str] = None
    ) -> MLModel:
        """Register ML model"""
        model = MLModel(
            model_type=model_type,
            model_name=model_name,
            version=version,
            hyperparameters=hyperparameters,
            metrics=metrics,
            artifact_path=artifact_path,
            is_active=False
        )

        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)

        return model

    async def get_active_model(self, model_name: str) -> Optional[MLModel]:
        """Get active ML model by name"""
        query = select(MLModel).where(
            and_(
                MLModel.model_name == model_name,
                MLModel.is_active == True
            )
        ).order_by(MLModel.created_at.desc())

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def activate_model(self, model_id: UUID) -> bool:
        """Activate an ML model and deactivate others"""
        query = select(MLModel).where(MLModel.id == model_id)
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if not model:
            return False

        # Deactivate all models with same name
        deactivate_query = select(MLModel).where(
            and_(
                MLModel.model_name == model.model_name,
                MLModel.is_active == True
            )
        )
        deactivate_result = await self.db.execute(deactivate_query)
        for old_model in deactivate_result.scalars().all():
            old_model.is_active = False

        # Activate new model
        model.is_active = True
        model.activated_at = datetime.utcnow()

        await self.db.flush()

        return True

    # ========================================================================
    # Predictions
    # ========================================================================

    async def create_prediction(
        self,
        user_id: UUID,
        prediction_type: PredictionType,
        entity_id: Optional[UUID],
        predicted_value: float,
        confidence: float,
        model_id: Optional[UUID] = None,
        features: Optional[Dict[str, Any]] = None
    ) -> Prediction:
        """Create a prediction"""
        prediction = Prediction(
            user_id=user_id,
            prediction_type=prediction_type,
            entity_id=entity_id,
            predicted_value=predicted_value,
            confidence=confidence,
            model_id=model_id,
            features_used=features or {}
        )

        self.db.add(prediction)
        await self.db.flush()
        await self.db.refresh(prediction)

        return prediction

    async def get_user_predictions(
        self,
        user_id: UUID,
        prediction_type: Optional[PredictionType] = None,
        limit: int = 10
    ) -> List[Prediction]:
        """Get predictions for a user"""
        query = select(Prediction).where(Prediction.user_id == user_id)

        if prediction_type:
            query = query.where(Prediction.prediction_type == prediction_type)

        query = query.order_by(Prediction.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # A/B Testing / Experiments
    # ========================================================================

    async def create_experiment(
        self,
        experiment_name: str,
        description: str,
        control_group: str,
        treatment_groups: List[str],
        start_date: datetime,
        end_date: datetime,
        success_metrics: List[str]
    ) -> Experiment:
        """Create an A/B test experiment"""
        experiment = Experiment(
            experiment_name=experiment_name,
            description=description,
            control_group=control_group,
            treatment_groups=treatment_groups,
            start_date=start_date,
            end_date=end_date,
            success_metrics=success_metrics,
            is_active=True
        )

        self.db.add(experiment)
        await self.db.flush()
        await self.db.refresh(experiment)

        return experiment

    async def assign_user_to_experiment(
        self,
        experiment_id: UUID,
        user_id: UUID,
        variant: str
    ) -> ExperimentAssignment:
        """Assign user to experiment variant"""
        assignment = ExperimentAssignment(
            experiment_id=experiment_id,
            user_id=user_id,
            variant=variant
        )

        self.db.add(assignment)
        await self.db.flush()
        await self.db.refresh(assignment)

        return assignment

    async def get_user_experiment_assignment(
        self,
        experiment_id: UUID,
        user_id: UUID
    ) -> Optional[ExperimentAssignment]:
        """Get user's experiment assignment"""
        query = select(ExperimentAssignment).where(
            and_(
                ExperimentAssignment.experiment_id == experiment_id,
                ExperimentAssignment.user_id == user_id
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_experiments(self) -> List[Experiment]:
        """Get all active experiments"""
        now = datetime.utcnow()

        query = select(Experiment).where(
            and_(
                Experiment.is_active == True,
                Experiment.start_date <= now,
                Experiment.end_date >= now
            )
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())
