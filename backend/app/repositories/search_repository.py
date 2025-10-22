"""
Search Repository
Sprint 13: Search & Discovery System

Data access layer for search operations and Elasticsearch integration.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, delete, desc
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from elasticsearch import AsyncElasticsearch

from app.models.search import (
    SavedSearch, SearchAnalytics, SearchSuggestion,
    SearchFilterPreset, VendorMatchingScore, SearchIndexStatus
)
from app.core.elasticsearch import (
    ElasticsearchClient, INDEX_VENDORS, INDEX_EVENTS, INDEX_SERVICES
)


class SearchRepository:
    """Repository for search operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.es_client = ElasticsearchClient.get_client()

    # ========================================================================
    # Saved Search Operations
    # ========================================================================

    async def create_saved_search(self, search_data: Dict[str, Any]) -> SavedSearch:
        """Create a saved search"""
        saved_search = SavedSearch(**search_data)
        self.db.add(saved_search)
        await self.db.commit()
        await self.db.refresh(saved_search)
        return saved_search

    async def get_saved_search(self, search_id: UUID) -> Optional[SavedSearch]:
        """Get a saved search by ID"""
        result = await self.db.execute(
            select(SavedSearch).where(SavedSearch.id == search_id)
        )
        return result.scalar_one_or_none()

    async def get_user_saved_searches(
        self,
        user_id: UUID,
        search_type: Optional[str] = None,
        is_active: bool = True
    ) -> List[SavedSearch]:
        """Get all saved searches for a user"""
        query = select(SavedSearch)

        filters = [SavedSearch.user_id == user_id]
        if search_type:
            filters.append(SavedSearch.search_type == search_type)
        if is_active:
            filters.append(SavedSearch.is_active == True)

        query = query.where(and_(*filters))
        query = query.order_by(SavedSearch.use_count.desc(), SavedSearch.created_at.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_saved_search(self, search_id: UUID, search_data: Dict[str, Any]) -> Optional[SavedSearch]:
        """Update a saved search"""
        await self.db.execute(
            update(SavedSearch)
            .where(SavedSearch.id == search_id)
            .values(**search_data)
        )
        await self.db.commit()
        return await self.get_saved_search(search_id)

    async def delete_saved_search(self, search_id: UUID) -> bool:
        """Delete a saved search"""
        result = await self.db.execute(
            delete(SavedSearch).where(SavedSearch.id == search_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def increment_saved_search_usage(self, search_id: UUID):
        """Increment use count for a saved search"""
        await self.db.execute(
            update(SavedSearch)
            .where(SavedSearch.id == search_id)
            .values(
                use_count=SavedSearch.use_count + 1,
                last_used_at=datetime.utcnow()
            )
        )
        await self.db.commit()

    # ========================================================================
    # Search Analytics Operations
    # ========================================================================

    async def create_search_analytics(self, analytics_data: Dict[str, Any]) -> SearchAnalytics:
        """Record search analytics"""
        analytics = SearchAnalytics(**analytics_data)
        self.db.add(analytics)
        await self.db.commit()
        await self.db.refresh(analytics)
        return analytics

    async def get_trending_queries(
        self,
        search_type: Optional[str] = None,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get trending search queries"""
        since = datetime.utcnow() - timedelta(days=days)

        query = select(
            SearchAnalytics.query_text,
            func.count(SearchAnalytics.id).label('search_count')
        ).where(
            and_(
                SearchAnalytics.searched_at >= since,
                SearchAnalytics.query_text.isnot(None),
                SearchAnalytics.query_text != ''
            )
        )

        if search_type:
            query = query.where(SearchAnalytics.search_type == search_type)

        query = query.group_by(SearchAnalytics.query_text)
        query = query.order_by(desc('search_count'))
        query = query.limit(limit)

        result = await self.db.execute(query)
        return [
            {"query": row.query_text, "count": row.search_count}
            for row in result
        ]

    async def get_search_analytics_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get search analytics summary"""
        # Total searches
        total_result = await self.db.execute(
            select(func.count(SearchAnalytics.id))
            .where(
                and_(
                    SearchAnalytics.searched_at >= start_date,
                    SearchAnalytics.searched_at <= end_date
                )
            )
        )
        total_searches = total_result.scalar_one()

        # Unique users
        unique_users_result = await self.db.execute(
            select(func.count(func.distinct(SearchAnalytics.user_id)))
            .where(
                and_(
                    SearchAnalytics.searched_at >= start_date,
                    SearchAnalytics.searched_at <= end_date,
                    SearchAnalytics.user_id.isnot(None)
                )
            )
        )
        unique_users = unique_users_result.scalar_one()

        # Average results
        avg_results_result = await self.db.execute(
            select(func.avg(SearchAnalytics.results_count))
            .where(
                and_(
                    SearchAnalytics.searched_at >= start_date,
                    SearchAnalytics.searched_at <= end_date
                )
            )
        )
        avg_results = avg_results_result.scalar_one() or 0.0

        # Average duration
        avg_duration_result = await self.db.execute(
            select(func.avg(SearchAnalytics.search_duration_ms))
            .where(
                and_(
                    SearchAnalytics.searched_at >= start_date,
                    SearchAnalytics.searched_at <= end_date,
                    SearchAnalytics.search_duration_ms.isnot(None)
                )
            )
        )
        avg_duration = avg_duration_result.scalar_one() or 0.0

        return {
            "total_searches": total_searches,
            "unique_users": unique_users,
            "average_results": round(avg_results, 2),
            "average_duration_ms": round(avg_duration, 2)
        }

    # ========================================================================
    # Search Suggestion Operations
    # ========================================================================

    async def create_search_suggestion(self, suggestion_data: Dict[str, Any]) -> SearchSuggestion:
        """Create a search suggestion"""
        suggestion = SearchSuggestion(**suggestion_data)
        self.db.add(suggestion)
        await self.db.commit()
        await self.db.refresh(suggestion)
        return suggestion

    async def get_search_suggestion(self, suggestion_id: UUID) -> Optional[SearchSuggestion]:
        """Get a search suggestion by ID"""
        result = await self.db.execute(
            select(SearchSuggestion).where(SearchSuggestion.id == suggestion_id)
        )
        return result.scalar_one_or_none()

    async def get_suggestions_by_prefix(
        self,
        prefix: str,
        search_type: Optional[str] = None,
        limit: int = 10
    ) -> List[SearchSuggestion]:
        """Get suggestions by prefix for autocomplete"""
        query = select(SearchSuggestion).where(
            and_(
                SearchSuggestion.suggestion_text.ilike(f"{prefix}%"),
                SearchSuggestion.is_active == True
            )
        )

        if search_type:
            query = query.where(SearchSuggestion.suggestion_type == search_type)

        query = query.order_by(
            SearchSuggestion.relevance_score.desc(),
            SearchSuggestion.search_count.desc()
        )
        query = query.limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_trending_suggestions(
        self,
        search_type: Optional[str] = None,
        limit: int = 10
    ) -> List[SearchSuggestion]:
        """Get trending suggestions"""
        query = select(SearchSuggestion).where(
            and_(
                SearchSuggestion.is_trending == True,
                SearchSuggestion.is_active == True
            )
        )

        if search_type:
            query = query.where(SearchSuggestion.suggestion_type == search_type)

        query = query.order_by(SearchSuggestion.search_count.desc())
        query = query.limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_search_suggestion(self, suggestion_id: UUID, suggestion_data: Dict[str, Any]) -> Optional[SearchSuggestion]:
        """Update a search suggestion"""
        await self.db.execute(
            update(SearchSuggestion)
            .where(SearchSuggestion.id == suggestion_id)
            .values(**suggestion_data)
        )
        await self.db.commit()
        return await self.get_search_suggestion(suggestion_id)

    async def increment_suggestion_usage(self, suggestion_id: UUID):
        """Increment search count for a suggestion"""
        await self.db.execute(
            update(SearchSuggestion)
            .where(SearchSuggestion.id == suggestion_id)
            .values(
                search_count=SearchSuggestion.search_count + 1,
                last_searched_at=datetime.utcnow()
            )
        )
        await self.db.commit()

    # ========================================================================
    # Filter Preset Operations
    # ========================================================================

    async def create_filter_preset(self, preset_data: Dict[str, Any]) -> SearchFilterPreset:
        """Create a filter preset"""
        preset = SearchFilterPreset(**preset_data)
        self.db.add(preset)
        await self.db.commit()
        await self.db.refresh(preset)
        return preset

    async def get_filter_preset(self, preset_id: UUID) -> Optional[SearchFilterPreset]:
        """Get a filter preset by ID"""
        result = await self.db.execute(
            select(SearchFilterPreset).where(SearchFilterPreset.id == preset_id)
        )
        return result.scalar_one_or_none()

    async def get_filter_presets(
        self,
        search_type: Optional[str] = None,
        is_featured: Optional[bool] = None
    ) -> List[SearchFilterPreset]:
        """Get filter presets"""
        query = select(SearchFilterPreset).where(SearchFilterPreset.is_active == True)

        if search_type:
            query = query.where(SearchFilterPreset.search_type == search_type)
        if is_featured is not None:
            query = query.where(SearchFilterPreset.is_featured == is_featured)

        query = query.order_by(SearchFilterPreset.display_order, SearchFilterPreset.created_at)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_filter_preset(self, preset_id: UUID, preset_data: Dict[str, Any]) -> Optional[SearchFilterPreset]:
        """Update a filter preset"""
        await self.db.execute(
            update(SearchFilterPreset)
            .where(SearchFilterPreset.id == preset_id)
            .values(**preset_data)
        )
        await self.db.commit()
        return await self.get_filter_preset(preset_id)

    async def delete_filter_preset(self, preset_id: UUID) -> bool:
        """Delete a filter preset"""
        result = await self.db.execute(
            delete(SearchFilterPreset).where(SearchFilterPreset.id == preset_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    # ========================================================================
    # Vendor Matching Operations
    # ========================================================================

    async def create_matching_score(self, score_data: Dict[str, Any]) -> VendorMatchingScore:
        """Create a vendor matching score"""
        score = VendorMatchingScore(**score_data)
        self.db.add(score)
        await self.db.commit()
        await self.db.refresh(score)
        return score

    async def get_vendor_matches(
        self,
        event_id: UUID,
        min_score: float = 0.0,
        limit: int = 20
    ) -> List[VendorMatchingScore]:
        """Get vendor matches for an event"""
        query = select(VendorMatchingScore).where(
            and_(
                VendorMatchingScore.event_id == event_id,
                VendorMatchingScore.overall_score >= min_score
            )
        )

        query = query.order_by(VendorMatchingScore.overall_score.desc())
        query = query.limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete_expired_matches(self):
        """Delete expired matching scores"""
        now = datetime.utcnow()
        result = await self.db.execute(
            delete(VendorMatchingScore).where(
                and_(
                    VendorMatchingScore.expires_at.isnot(None),
                    VendorMatchingScore.expires_at < now
                )
            )
        )
        await self.db.commit()
        return result.rowcount

    # ========================================================================
    # Search Index Status Operations
    # ========================================================================

    async def create_or_update_index_status(self, status_data: Dict[str, Any]) -> SearchIndexStatus:
        """Create or update index status"""
        # Check if exists
        result = await self.db.execute(
            select(SearchIndexStatus).where(
                SearchIndexStatus.index_name == status_data['index_name']
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update
            await self.db.execute(
                update(SearchIndexStatus)
                .where(SearchIndexStatus.id == existing.id)
                .values(**status_data)
            )
            await self.db.commit()
            return await self.get_index_status(status_data['index_name'])
        else:
            # Create
            status = SearchIndexStatus(**status_data)
            self.db.add(status)
            await self.db.commit()
            await self.db.refresh(status)
            return status

    async def get_index_status(self, index_name: str) -> Optional[SearchIndexStatus]:
        """Get index status by name"""
        result = await self.db.execute(
            select(SearchIndexStatus).where(SearchIndexStatus.index_name == index_name)
        )
        return result.scalar_one_or_none()

    async def get_all_index_statuses(self) -> List[SearchIndexStatus]:
        """Get all index statuses"""
        result = await self.db.execute(
            select(SearchIndexStatus).order_by(SearchIndexStatus.entity_type)
        )
        return result.scalars().all()

    # ========================================================================
    # Elasticsearch Operations
    # ========================================================================

    async def search_elasticsearch(
        self,
        index: str,
        query: Dict[str, Any],
        from_: int = 0,
        size: int = 20
    ) -> Dict[str, Any]:
        """Perform Elasticsearch search"""
        try:
            response = await self.es_client.search(
                index=index,
                body=query,
                from_=from_,
                size=size
            )
            return response
        except Exception as e:
            print(f"Elasticsearch search error: {str(e)}")
            return {"hits": {"total": {"value": 0}, "hits": []}}

    async def index_document(
        self,
        index: str,
        doc_id: str,
        document: Dict[str, Any]
    ) -> bool:
        """Index a single document"""
        try:
            await self.es_client.index(
                index=index,
                id=doc_id,
                body=document
            )
            return True
        except Exception as e:
            print(f"Elasticsearch index error: {str(e)}")
            return False

    async def bulk_index_documents(
        self,
        index: str,
        documents: List[Dict[str, Any]]
    ) -> int:
        """Bulk index documents"""
        try:
            from elasticsearch.helpers import async_bulk

            actions = [
                {
                    "_index": index,
                    "_id": doc.get("id"),
                    "_source": doc
                }
                for doc in documents
            ]

            success, failed = await async_bulk(self.es_client, actions)
            return success
        except Exception as e:
            print(f"Elasticsearch bulk index error: {str(e)}")
            return 0

    async def delete_document(self, index: str, doc_id: str) -> bool:
        """Delete a document from index"""
        try:
            await self.es_client.delete(index=index, id=doc_id)
            return True
        except Exception as e:
            print(f"Elasticsearch delete error: {str(e)}")
            return False

    async def autocomplete_search(
        self,
        index: str,
        field: str,
        prefix: str,
        size: int = 10
    ) -> List[str]:
        """Autocomplete search using completion suggester"""
        try:
            response = await self.es_client.search(
                index=index,
                body={
                    "suggest": {
                        "autocomplete": {
                            "prefix": prefix,
                            "completion": {
                                "field": f"{field}.suggest",
                                "size": size,
                                "skip_duplicates": True
                            }
                        }
                    }
                }
            )

            suggestions = []
            if "suggest" in response and "autocomplete" in response["suggest"]:
                for option in response["suggest"]["autocomplete"][0]["options"]:
                    suggestions.append(option["text"])

            return suggestions
        except Exception as e:
            print(f"Elasticsearch autocomplete error: {str(e)}")
            return []
