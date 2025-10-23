"""
CelebraTech Event Management System - Recommendation Service
Sprint 17: AI & Recommendation Engine
Business logic for AI-powered recommendations and predictions
"""
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from uuid import UUID
import random
import hashlib

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
from app.models.user import User
from app.repositories.recommendation_repository import RecommendationRepository


class RecommendationService:
    """Service for recommendation and ML operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.rec_repo = RecommendationRepository(db)

    # ========================================================================
    # User Behavior Tracking
    # ========================================================================

    async def track_interaction(
        self,
        user_id: UUID,
        interaction_type: InteractionType,
        entity_type: str,
        entity_id: UUID,
        current_user: User,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UserBehavior:
        """Track user interaction"""
        behavior = await self.rec_repo.track_behavior(
            user_id,
            interaction_type,
            entity_type,
            entity_id,
            metadata
        )

        await self.db.commit()
        return behavior

    async def get_user_behavior_history(
        self,
        user_id: UUID,
        current_user: User,
        interaction_type: Optional[InteractionType] = None,
        entity_type: Optional[str] = None,
        days_back: int = 30
    ) -> List[UserBehavior]:
        """Get user behavior history"""
        # TODO: Verify permission
        behaviors = await self.rec_repo.get_user_behaviors(
            user_id,
            interaction_type,
            entity_type,
            days_back
        )

        return behaviors

    # ========================================================================
    # User Preferences
    # ========================================================================

    async def save_preference(
        self,
        preference_key: str,
        preference_value: Any,
        current_user: User,
        preference_type: str = "general"
    ) -> UserPreference:
        """Save user preference"""
        preference = await self.rec_repo.save_user_preference(
            current_user.id,
            preference_key,
            preference_value,
            preference_type
        )

        await self.db.commit()
        return preference

    async def get_user_preferences(
        self,
        current_user: User,
        preference_type: Optional[str] = None
    ) -> List[UserPreference]:
        """Get user preferences"""
        preferences = await self.rec_repo.get_user_preferences(
            current_user.id,
            preference_type
        )

        return preferences

    # ========================================================================
    # Recommendations
    # ========================================================================

    async def generate_vendor_recommendations(
        self,
        current_user: User,
        event_id: Optional[UUID] = None,
        limit: int = 10,
        algorithm: RecommendationAlgorithm = RecommendationAlgorithm.HYBRID
    ) -> List[Recommendation]:
        """
        Generate vendor recommendations for user

        This is a simplified implementation. In production, this would:
        - Use collaborative filtering based on similar users
        - Use content-based filtering on vendor features
        - Consider user's past interactions and preferences
        - Apply ML models for scoring
        """
        # Get user's past behavior
        behaviors = await self.rec_repo.get_user_behaviors(
            current_user.id,
            entity_type="vendor",
            days_back=90
        )

        # Get popular vendors (simple popularity-based recommendation)
        popular_vendors = await self.rec_repo.get_popular_entities(
            entity_type="vendor",
            interaction_type=InteractionType.BOOKING,
            days_back=30,
            limit=limit * 2
        )

        # Filter out vendors user has already interacted with
        interacted_vendor_ids = {str(b.entity_id) for b in behaviors}
        candidate_vendors = [
            v for v in popular_vendors
            if v["entity_id"] not in interacted_vendor_ids
        ][:limit]

        # Create recommendations
        recommendations = []
        for i, vendor in enumerate(candidate_vendors):
            # Simple scoring: higher for more popular vendors
            score = (limit - i) / limit * 100  # Score from 0-100

            rec = await self.rec_repo.create_recommendation(
                user_id=current_user.id,
                recommendation_type=RecommendationType.VENDOR,
                entity_id=UUID(vendor["entity_id"]),
                score=score,
                algorithm=algorithm,
                explanation=f"Popular vendor with {vendor['interaction_count']} bookings",
                metadata={"popularity_rank": i + 1},
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            recommendations.append(rec)

        await self.db.commit()
        return recommendations

    async def get_recommendations(
        self,
        current_user: User,
        recommendation_type: Optional[RecommendationType] = None,
        limit: int = 10
    ) -> List[Recommendation]:
        """Get recommendations for user"""
        recommendations = await self.rec_repo.get_user_recommendations(
            current_user.id,
            recommendation_type,
            limit
        )

        return recommendations

    async def mark_recommendation_shown(
        self,
        recommendation_id: UUID,
        current_user: User
    ) -> bool:
        """Mark recommendation as shown to user"""
        success = await self.rec_repo.mark_recommendation_shown(recommendation_id)

        if success:
            await self.db.commit()

        return success

    async def mark_recommendation_clicked(
        self,
        recommendation_id: UUID,
        current_user: User
    ) -> bool:
        """Mark recommendation as clicked"""
        success = await self.rec_repo.mark_recommendation_clicked(recommendation_id)

        if success:
            await self.db.commit()

            # Track as behavior
            # TODO: Get recommendation details and track interaction

        return success

    async def provide_feedback(
        self,
        recommendation_id: UUID,
        feedback_type: FeedbackType,
        current_user: User,
        rating: Optional[int] = None,
        comment: Optional[str] = None
    ) -> RecommendationFeedback:
        """Provide feedback on recommendation"""
        feedback = await self.rec_repo.create_feedback(
            recommendation_id,
            current_user.id,
            feedback_type,
            rating,
            comment
        )

        await self.db.commit()
        return feedback

    # ========================================================================
    # Vendor Matching
    # ========================================================================

    async def match_vendors_for_event(
        self,
        event_id: UUID,
        current_user: User,
        limit: int = 10
    ) -> List[EventVendorMatch]:
        """
        Match vendors to event requirements

        Simplified implementation. In production would:
        - Analyze event requirements (budget, guest count, type, date)
        - Find vendors matching criteria
        - Score based on:
          - Availability on event date
          - Price range match
          - Past performance ratings
          - Category relevance
          - Geographic proximity
        - Use ML models for scoring
        """
        # For now, just get popular vendors and create matches
        popular_vendors = await self.rec_repo.get_popular_entities(
            entity_type="vendor",
            days_back=30,
            limit=limit
        )

        matches = []
        for i, vendor in enumerate(popular_vendors):
            # Simple scoring based on popularity
            match_score = (limit - i) / limit * 100

            match = await self.rec_repo.create_vendor_match(
                event_id=event_id,
                vendor_id=UUID(vendor["entity_id"]),
                match_score=match_score,
                algorithm=RecommendationAlgorithm.HYBRID,
                factors={
                    "popularity": vendor["interaction_count"],
                    "rank": i + 1
                }
            )
            matches.append(match)

        await self.db.commit()
        return matches

    async def get_event_vendor_matches(
        self,
        event_id: UUID,
        current_user: User,
        limit: int = 10
    ) -> List[EventVendorMatch]:
        """Get vendor matches for an event"""
        # TODO: Verify user has access to event

        matches = await self.rec_repo.get_vendor_matches(event_id, limit)
        return matches

    # ========================================================================
    # Predictions
    # ========================================================================

    async def predict_budget(
        self,
        event_id: UUID,
        current_user: User,
        event_features: Dict[str, Any]
    ) -> Prediction:
        """
        Predict event budget

        Simplified implementation. In production would:
        - Use trained regression model
        - Feature engineering from event attributes
        - Consider historical data from similar events
        - Account for seasonal variations, location, etc.
        """
        # Simple rule-based prediction for demonstration
        guest_count = event_features.get("guest_count", 100)
        event_type = event_features.get("event_type", "general")

        # Base cost per guest varies by event type
        base_costs = {
            "wedding": 150,
            "corporate": 100,
            "birthday": 80,
            "general": 100
        }

        cost_per_guest = base_costs.get(event_type, 100)
        predicted_budget = guest_count * cost_per_guest

        # Confidence based on how many similar events we have
        confidence = 0.75  # 75% confidence

        prediction = await self.rec_repo.create_prediction(
            user_id=current_user.id,
            prediction_type=PredictionType.BUDGET_FORECAST,
            entity_id=event_id,
            predicted_value=predicted_budget,
            confidence=confidence,
            features=event_features
        )

        await self.db.commit()
        return prediction

    async def predict_guest_count(
        self,
        event_id: UUID,
        current_user: User,
        event_features: Dict[str, Any]
    ) -> Prediction:
        """Predict guest count for event"""
        # Simple prediction based on event type
        event_type = event_features.get("event_type", "general")

        average_guests = {
            "wedding": 150,
            "corporate": 100,
            "birthday": 50,
            "general": 75
        }

        predicted_count = average_guests.get(event_type, 75)
        confidence = 0.70

        prediction = await self.rec_repo.create_prediction(
            user_id=current_user.id,
            prediction_type=PredictionType.GUEST_COUNT,
            entity_id=event_id,
            predicted_value=predicted_count,
            confidence=confidence,
            features=event_features
        )

        await self.db.commit()
        return prediction

    async def get_user_predictions(
        self,
        current_user: User,
        prediction_type: Optional[PredictionType] = None,
        limit: int = 10
    ) -> List[Prediction]:
        """Get user's predictions"""
        predictions = await self.rec_repo.get_user_predictions(
            current_user.id,
            prediction_type,
            limit
        )

        return predictions

    # ========================================================================
    # ML Model Management
    # ========================================================================

    async def register_model(
        self,
        model_type: str,
        model_name: str,
        version: str,
        hyperparameters: Dict[str, Any],
        metrics: Dict[str, Any],
        current_user: User,
        artifact_path: Optional[str] = None
    ) -> MLModel:
        """Register a new ML model"""
        # TODO: Verify user is admin

        model = await self.rec_repo.register_ml_model(
            model_type,
            model_name,
            version,
            hyperparameters,
            metrics,
            artifact_path
        )

        await self.db.commit()
        return model

    async def activate_model(
        self,
        model_id: UUID,
        current_user: User
    ) -> bool:
        """Activate an ML model"""
        # TODO: Verify user is admin

        success = await self.rec_repo.activate_model(model_id)

        if success:
            await self.db.commit()

        return success

    async def get_active_model(self, model_name: str) -> Optional[MLModel]:
        """Get active model by name"""
        model = await self.rec_repo.get_active_model(model_name)
        return model

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
        success_metrics: List[str],
        current_user: User
    ) -> Experiment:
        """Create A/B test experiment"""
        # TODO: Verify user is admin

        experiment = await self.rec_repo.create_experiment(
            experiment_name,
            description,
            control_group,
            treatment_groups,
            start_date,
            end_date,
            success_metrics
        )

        await self.db.commit()
        return experiment

    async def get_user_experiment_variant(
        self,
        experiment_name: str,
        current_user: User
    ) -> Optional[str]:
        """
        Get user's experiment variant (A/B test assignment)

        Uses consistent hashing to ensure same user always gets same variant
        """
        # Get active experiments
        experiments = await self.rec_repo.get_active_experiments()

        target_experiment = None
        for exp in experiments:
            if exp.experiment_name == experiment_name:
                target_experiment = exp
                break

        if not target_experiment:
            return None

        # Check if user already assigned
        assignment = await self.rec_repo.get_user_experiment_assignment(
            target_experiment.id,
            current_user.id
        )

        if assignment:
            return assignment.variant

        # Assign user to variant using consistent hashing
        all_variants = [target_experiment.control_group] + target_experiment.treatment_groups

        # Hash user ID to get consistent variant
        hash_input = f"{current_user.id}{experiment_name}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        variant_index = hash_value % len(all_variants)
        variant = all_variants[variant_index]

        # Save assignment
        await self.rec_repo.assign_user_to_experiment(
            target_experiment.id,
            current_user.id,
            variant
        )

        await self.db.commit()
        return variant

    async def get_active_experiments(self) -> List[Experiment]:
        """Get all active experiments"""
        experiments = await self.rec_repo.get_active_experiments()
        return experiments
