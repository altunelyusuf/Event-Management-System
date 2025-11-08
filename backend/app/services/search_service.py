"""
Search Service
Sprint 13: Search & Discovery System

Business logic for search operations, Elasticsearch queries,
and vendor matching algorithms.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import time

from app.repositories.search_repository import SearchRepository
from app.models.user import User
from app.schemas.search import (
    SearchRequest, VendorSearchRequest, EventSearchRequest, ServiceSearchRequest,
    SavedSearchCreate, SavedSearchUpdate,
    SearchSuggestionCreate, SearchSuggestionUpdate,
    FilterPresetCreate, FilterPresetUpdate
)
from app.core.elasticsearch import INDEX_VENDORS, INDEX_EVENTS, INDEX_SERVICES


class SearchService:
    """Service for search operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SearchRepository(db)

    # ========================================================================
    # Main Search Methods
    # ========================================================================

    async def search(
        self,
        search_request: SearchRequest,
        current_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """Perform a search across specified index"""
        start_time = time.time()

        # Build Elasticsearch query
        es_query = self._build_search_query(search_request)

        # Determine index
        index = self._get_index_for_search_type(search_request.search_type)

        # Execute search
        es_response = await self.repo.search_elasticsearch(
            index=index,
            query=es_query,
            from_=search_request.skip,
            size=search_request.limit
        )

        # Calculate search duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Parse results
        results = self._parse_search_results(es_response, search_request.search_type)

        # Get total results
        total_results = es_response.get("hits", {}).get("total", {}).get("value", 0)

        # Build response
        response = {
            "query": search_request.query,
            "search_type": search_request.search_type,
            "total_results": total_results,
            "results_shown": len(results),
            "page": search_request.skip // search_request.limit + 1,
            "total_pages": (total_results + search_request.limit - 1) // search_request.limit,
            "search_duration_ms": duration_ms,
            "results": results,
            "facets": self._extract_facets(es_response),
            "suggestions": [],
            "did_you_mean": None
        }

        # Record analytics
        await self._record_search_analytics(
            search_request=search_request,
            results_count=total_results,
            duration_ms=duration_ms,
            user_id=current_user.id if current_user else None
        )

        return response

    async def search_vendors(
        self,
        search_request: VendorSearchRequest,
        current_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """Search for vendors"""
        return await self.search(search_request, current_user)

    async def search_events(
        self,
        search_request: EventSearchRequest,
        current_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """Search for events"""
        return await self.search(search_request, current_user)

    async def search_services(
        self,
        search_request: ServiceSearchRequest,
        current_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """Search for services"""
        return await self.search(search_request, current_user)

    # ========================================================================
    # Autocomplete
    # ========================================================================

    async def autocomplete(
        self,
        prefix: str,
        search_type: Optional[str] = None,
        limit: int = 10
    ) -> List[str]:
        """Get autocomplete suggestions"""
        # First, try database suggestions
        suggestions = await self.repo.get_suggestions_by_prefix(
            prefix=prefix,
            search_type=search_type,
            limit=limit
        )

        # If we have database suggestions, return them
        if suggestions:
            return [s.suggestion_text for s in suggestions]

        # Otherwise, try Elasticsearch completion suggester
        index = self._get_index_for_search_type(search_type or "vendor")
        field = self._get_name_field_for_index(index)

        es_suggestions = await self.repo.autocomplete_search(
            index=index,
            field=field,
            prefix=prefix,
            size=limit
        )

        return es_suggestions

    # ========================================================================
    # Saved Search Methods
    # ========================================================================

    async def create_saved_search(
        self,
        search_data: SavedSearchCreate,
        current_user: User
    ):
        """Create a saved search"""
        data = search_data.model_dump()
        data['user_id'] = current_user.id
        return await self.repo.create_saved_search(data)

    async def get_saved_search(
        self,
        search_id: UUID,
        current_user: User
    ):
        """Get a saved search"""
        saved_search = await self.repo.get_saved_search(search_id)
        if not saved_search:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved search not found"
            )

        # Check ownership
        if saved_search.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        return saved_search

    async def get_user_saved_searches(
        self,
        user_id: UUID,
        search_type: Optional[str] = None,
        current_user: Optional[User] = None
    ):
        """Get user's saved searches"""
        # Users can only see their own saved searches unless admin
        if current_user and user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        return await self.repo.get_user_saved_searches(user_id, search_type)

    async def update_saved_search(
        self,
        search_id: UUID,
        search_data: SavedSearchUpdate,
        current_user: User
    ):
        """Update a saved search"""
        saved_search = await self.get_saved_search(search_id, current_user)

        data = search_data.model_dump(exclude_unset=True)
        return await self.repo.update_saved_search(search_id, data)

    async def delete_saved_search(
        self,
        search_id: UUID,
        current_user: User
    ):
        """Delete a saved search"""
        saved_search = await self.get_saved_search(search_id, current_user)

        success = await self.repo.delete_saved_search(search_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete saved search"
            )

        return {"message": "Saved search deleted successfully"}

    async def execute_saved_search(
        self,
        search_id: UUID,
        current_user: User
    ):
        """Execute a saved search"""
        saved_search = await self.get_saved_search(search_id, current_user)

        # Increment usage count
        await self.repo.increment_saved_search_usage(search_id)

        # Build search request from saved search
        search_request = SearchRequest(
            **saved_search.query_params,
            latitude=saved_search.latitude,
            longitude=saved_search.longitude,
            radius_km=saved_search.radius_km,
            search_type=saved_search.search_type
        )

        # Execute search
        results = await self.search(search_request, current_user)

        # Update result count
        await self.repo.update_saved_search(
            search_id,
            {"result_count_last_run": results["total_results"]}
        )

        return results

    # ========================================================================
    # Search Suggestion Methods
    # ========================================================================

    async def create_suggestion(
        self,
        suggestion_data: SearchSuggestionCreate,
        current_user: User
    ):
        """Create a search suggestion (admin only)"""
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        data = suggestion_data.model_dump()
        return await self.repo.create_search_suggestion(data)

    async def get_trending_suggestions(
        self,
        search_type: Optional[str] = None,
        limit: int = 10
    ):
        """Get trending suggestions"""
        return await self.repo.get_trending_suggestions(search_type, limit)

    async def update_suggestion(
        self,
        suggestion_id: UUID,
        suggestion_data: SearchSuggestionUpdate,
        current_user: User
    ):
        """Update a search suggestion (admin only)"""
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        data = suggestion_data.model_dump(exclude_unset=True)
        return await self.repo.update_search_suggestion(suggestion_id, data)

    # ========================================================================
    # Filter Preset Methods
    # ========================================================================

    async def create_filter_preset(
        self,
        preset_data: FilterPresetCreate,
        current_user: User
    ):
        """Create a filter preset (admin only)"""
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        data = preset_data.model_dump()
        return await self.repo.create_filter_preset(data)

    async def get_filter_presets(
        self,
        search_type: Optional[str] = None
    ):
        """Get filter presets"""
        return await self.repo.get_filter_presets(search_type)

    async def update_filter_preset(
        self,
        preset_id: UUID,
        preset_data: FilterPresetUpdate,
        current_user: User
    ):
        """Update a filter preset (admin only)"""
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        data = preset_data.model_dump(exclude_unset=True)
        return await self.repo.update_filter_preset(preset_id, data)

    async def delete_filter_preset(
        self,
        preset_id: UUID,
        current_user: User
    ):
        """Delete a filter preset (admin only)"""
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        success = await self.repo.delete_filter_preset(preset_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete filter preset"
            )

        return {"message": "Filter preset deleted successfully"}

    # ========================================================================
    # Analytics Methods
    # ========================================================================

    async def get_trending_queries(
        self,
        search_type: Optional[str] = None,
        days: int = 7,
        limit: int = 10
    ):
        """Get trending search queries"""
        return await self.repo.get_trending_queries(search_type, days, limit)

    async def get_analytics_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ):
        """Get search analytics summary"""
        summary = await self.repo.get_search_analytics_summary(start_date, end_date)

        # Get trending queries
        trending = await self.repo.get_trending_queries(days=7, limit=10)

        summary["top_queries"] = [t["query"] for t in trending[:5]]
        summary["trending_queries"] = [
            {"query": t["query"], "search_count": t["count"], "trend_percentage": 0.0}
            for t in trending
        ]
        summary["period_start"] = start_date
        summary["period_end"] = end_date
        summary["searches_by_type"] = {}
        summary["searches_by_device"] = {}

        return summary

    # ========================================================================
    # Vendor Matching Methods
    # ========================================================================

    async def match_vendors_for_event(
        self,
        event_id: UUID,
        category: Optional[str] = None,
        max_results: int = 20,
        min_score: float = 0.0
    ):
        """Match vendors to event requirements"""
        # TODO: Implement actual matching algorithm
        # For now, return existing matches from database
        matches = await self.repo.get_vendor_matches(event_id, min_score, max_results)
        return matches

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _build_search_query(self, search_request: SearchRequest) -> Dict[str, Any]:
        """Build Elasticsearch query from search request"""
        must = []
        should = []
        filters = []

        # Text query
        if search_request.query:
            must.append({
                "multi_match": {
                    "query": search_request.query,
                    "fields": self._get_search_fields(search_request.search_type),
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            })

        # Category filter
        if search_request.category:
            filters.append({"term": {"category": search_request.category}})

        # Price range filter
        if search_request.price_min is not None or search_request.price_max is not None:
            price_filter = {"range": {"price": {}}}
            if search_request.price_min is not None:
                price_filter["range"]["price"]["gte"] = search_request.price_min
            if search_request.price_max is not None:
                price_filter["range"]["price"]["lte"] = search_request.price_max
            filters.append(price_filter)

        # Rating filter
        if search_request.rating_min is not None:
            filters.append({
                "range": {"rating": {"gte": search_request.rating_min}}
            })

        # Location-based search
        if search_request.latitude and search_request.longitude:
            filters.append({
                "geo_distance": {
                    "distance": f"{search_request.radius_km or 50}km",
                    "location": {
                        "lat": search_request.latitude,
                        "lon": search_request.longitude
                    }
                }
            })

        # Boolean filters
        if search_request.verified_only:
            filters.append({"term": {"verified": True}})
        if search_request.featured_only:
            filters.append({"term": {"featured": True}})
        if search_request.available_only:
            filters.append({"term": {"is_available": True}})

        # Build the complete query
        query = {
            "bool": {
                "must": must if must else [{"match_all": {}}],
                "filter": filters
            }
        }

        # Add sorting
        sort = self._build_sort(search_request)

        # Add aggregations for facets
        aggs = self._build_aggregations(search_request.search_type)

        # Add highlighting
        highlight = {
            "fields": {
                field: {}
                for field in self._get_search_fields(search_request.search_type)
            }
        }

        return {
            "query": query,
            "sort": sort,
            "aggs": aggs,
            "highlight": highlight
        }

    def _get_index_for_search_type(self, search_type: str) -> str:
        """Get Elasticsearch index name for search type"""
        mapping = {
            "vendor": INDEX_VENDORS,
            "event": INDEX_EVENTS,
            "service": INDEX_SERVICES,
            "all": f"{INDEX_VENDORS},{INDEX_EVENTS},{INDEX_SERVICES}"
        }
        return mapping.get(search_type, INDEX_VENDORS)

    def _get_search_fields(self, search_type: str) -> List[str]:
        """Get search fields for search type"""
        if search_type == "vendor":
            return ["business_name^3", "description^2", "tags", "services.name"]
        elif search_type == "event":
            return ["name^3", "description^2", "tags", "venue_name"]
        elif search_type == "service":
            return ["service_name^3", "description^2", "vendor_name", "tags"]
        return ["name^3", "description^2", "tags"]

    def _get_name_field_for_index(self, index: str) -> str:
        """Get name field for autocomplete"""
        if index == INDEX_VENDORS:
            return "business_name"
        elif index == INDEX_EVENTS:
            return "name"
        elif index == INDEX_SERVICES:
            return "service_name"
        return "name"

    def _build_sort(self, search_request: SearchRequest) -> List[Dict[str, Any]]:
        """Build sort clause"""
        sort_mapping = {
            "relevance": ["_score"],
            "rating": [{"rating": {"order": "desc"}}, "_score"],
            "price_low": [{"price": {"order": "asc"}}, "_score"],
            "price_high": [{"price": {"order": "desc"}}, "_score"],
            "popularity": [{"review_count": {"order": "desc"}}, "_score"],
            "newest": [{"created_at": {"order": "desc"}}, "_score"]
        }

        # Distance sorting (if location provided)
        if search_request.latitude and search_request.longitude:
            if search_request.sort_by == "distance":
                return [
                    {
                        "_geo_distance": {
                            "location": {
                                "lat": search_request.latitude,
                                "lon": search_request.longitude
                            },
                            "order": "asc",
                            "unit": "km"
                        }
                    },
                    "_score"
                ]

        return sort_mapping.get(search_request.sort_by, ["_score"])

    def _build_aggregations(self, search_type: str) -> Dict[str, Any]:
        """Build aggregations for facets"""
        aggs = {
            "categories": {"terms": {"field": "category", "size": 20}},
            "price_ranges": {
                "range": {
                    "field": "price",
                    "ranges": [
                        {"to": 1000},
                        {"from": 1000, "to": 5000},
                        {"from": 5000, "to": 10000},
                        {"from": 10000}
                    ]
                }
            },
            "ratings": {
                "range": {
                    "field": "rating",
                    "ranges": [
                        {"from": 4.5},
                        {"from": 4.0, "to": 4.5},
                        {"from": 3.0, "to": 4.0}
                    ]
                }
            }
        }

        if search_type == "vendor":
            aggs["verified"] = {"terms": {"field": "verified"}}
            aggs["featured"] = {"terms": {"field": "featured"}}

        return aggs

    def _parse_search_results(
        self,
        es_response: Dict[str, Any],
        search_type: str
    ) -> List[Dict[str, Any]]:
        """Parse Elasticsearch response to search results"""
        results = []

        for hit in es_response.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            score = hit.get("_score", 0.0)

            # Extract highlights
            highlights = []
            if "highlight" in hit:
                for field, fragments in hit["highlight"].items():
                    highlights.append({
                        "field": field,
                        "fragments": fragments
                    })

            result = {
                "id": source.get("id"),
                "type": search_type,
                "score": score,
                "highlights": highlights,
                **source
            }

            results.append(result)

        return results

    def _extract_facets(self, es_response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract facets from aggregations"""
        facets = {}
        aggs = es_response.get("aggregations", {})

        for key, value in aggs.items():
            if "buckets" in value:
                facets[key] = [
                    {"key": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in value["buckets"]
                ]

        return facets

    async def _record_search_analytics(
        self,
        search_request: SearchRequest,
        results_count: int,
        duration_ms: int,
        user_id: Optional[UUID] = None
    ):
        """Record search analytics"""
        analytics_data = {
            "user_id": user_id,
            "search_type": search_request.search_type,
            "query_text": search_request.query,
            "filters_applied": {
                "category": search_request.category,
                "price_min": search_request.price_min,
                "price_max": search_request.price_max,
                "rating_min": search_request.rating_min
            },
            "sort_by": search_request.sort_by,
            "search_latitude": search_request.latitude,
            "search_longitude": search_request.longitude,
            "search_radius_km": search_request.radius_km,
            "results_count": results_count,
            "results_shown": search_request.limit,
            "search_duration_ms": duration_ms,
            "elasticsearch_used": True
        }

        try:
            await self.repo.create_search_analytics(analytics_data)
        except Exception as e:
            # Don't fail the search if analytics recording fails
            print(f"Failed to record search analytics: {str(e)}")
