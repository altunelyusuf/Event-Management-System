"""
Search API Endpoints
Sprint 13: Search & Discovery System

REST API endpoints for search functionality:
- General search
- Autocomplete
- Saved searches
- Search suggestions
- Filter presets
- Analytics
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user, get_optional_user
from app.models.user import User
from app.services.search_service import SearchService
from app.schemas.search import (
    SearchRequest, SearchResponse,
    VendorSearchRequest, EventSearchRequest, ServiceSearchRequest,
    AutocompleteRequest, AutocompleteResponse,
    SavedSearchCreate, SavedSearchResponse, SavedSearchUpdate,
    SearchSuggestionCreate, SearchSuggestionResponse, SearchSuggestionUpdate,
    FilterPresetCreate, FilterPresetResponse, FilterPresetUpdate,
    SearchAnalyticsSummary, SearchTrendingQuery,
    VendorMatchingRequest, VendorMatchingScoreResponse
)


router = APIRouter(prefix="/search", tags=["Search & Discovery"])


# ============================================================================
# Main Search Endpoints
# ============================================================================

@router.post("/", response_model=SearchResponse)
async def search(
    search_request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Perform a general search.

    Supports:
    - Full-text search across multiple fields
    - Faceted filtering (category, price, rating, location)
    - Location-based search (geospatial)
    - Multiple sort options
    - Pagination

    Returns results with highlights, facets, and suggestions.
    """
    service = SearchService(db)
    return await service.search(search_request, current_user)


@router.post("/vendors", response_model=SearchResponse)
async def search_vendors(
    search_request: VendorSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Search for vendors with vendor-specific filters.

    Additional filters:
    - Service types
    - Languages
    - Portfolio keywords
    - Verification status
    - Featured vendors
    """
    service = SearchService(db)
    return await service.search_vendors(search_request, current_user)


@router.post("/events", response_model=SearchResponse)
async def search_events(
    search_request: EventSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Search for events with event-specific filters.

    Additional filters:
    - Event type
    - Event status
    - Organizer
    - Date range
    """
    service = SearchService(db)
    return await service.search_events(search_request, current_user)


@router.post("/services", response_model=SearchResponse)
async def search_services(
    search_request: ServiceSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Search for services with service-specific filters.

    Additional filters:
    - Vendor
    - Service category
    - Price range
    - Availability
    """
    service = SearchService(db)
    return await service.search_services(search_request, current_user)


# ============================================================================
# Autocomplete Endpoints
# ============================================================================

@router.get("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete(
    prefix: str = Query(..., min_length=1, max_length=100, description="Search prefix"),
    search_type: Optional[str] = Query(None, description="Filter by search type"),
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """
    Get autocomplete suggestions for search input.

    Uses a combination of:
    - Database search suggestions
    - Elasticsearch completion suggester
    - Popular search queries

    Returns relevant suggestions based on prefix.
    """
    service = SearchService(db)
    suggestions = await service.autocomplete(prefix, search_type, limit)

    return AutocompleteResponse(
        suggestions=suggestions,
        count=len(suggestions)
    )


# ============================================================================
# Saved Search Endpoints
# ============================================================================

@router.post("/saved", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED)
async def create_saved_search(
    search_data: SavedSearchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save a search for quick access and notifications.

    Saved searches allow users to:
    - Quickly re-run favorite searches
    - Receive notifications when new matching results appear
    - Track search history
    """
    service = SearchService(db)
    return await service.create_saved_search(search_data, current_user)


@router.get("/saved/{search_id}", response_model=SavedSearchResponse)
async def get_saved_search(
    search_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a saved search by ID"""
    service = SearchService(db)
    return await service.get_saved_search(search_id, current_user)


@router.get("/saved/user/{user_id}", response_model=List[SavedSearchResponse])
async def get_user_saved_searches(
    user_id: UUID,
    search_type: Optional[str] = Query(None, description="Filter by search type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all saved searches for a user.

    Users can only view their own saved searches unless admin.
    """
    service = SearchService(db)
    return await service.get_user_saved_searches(user_id, search_type, current_user)


@router.patch("/saved/{search_id}", response_model=SavedSearchResponse)
async def update_saved_search(
    search_id: UUID,
    search_data: SavedSearchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a saved search"""
    service = SearchService(db)
    return await service.update_saved_search(search_id, search_data, current_user)


@router.delete("/saved/{search_id}", status_code=status.HTTP_200_OK)
async def delete_saved_search(
    search_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a saved search"""
    service = SearchService(db)
    return await service.delete_saved_search(search_id, current_user)


@router.post("/saved/{search_id}/execute", response_model=SearchResponse)
async def execute_saved_search(
    search_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Execute a saved search.

    Runs the saved search with its stored parameters
    and updates usage statistics.
    """
    service = SearchService(db)
    return await service.execute_saved_search(search_id, current_user)


# ============================================================================
# Search Suggestion Endpoints
# ============================================================================

@router.post("/suggestions", response_model=SearchSuggestionResponse, status_code=status.HTTP_201_CREATED)
async def create_suggestion(
    suggestion_data: SearchSuggestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a search suggestion (admin only).

    Curated suggestions appear in autocomplete
    and trending searches.
    """
    service = SearchService(db)
    return await service.create_suggestion(suggestion_data, current_user)


@router.get("/suggestions/trending", response_model=List[SearchSuggestionResponse])
async def get_trending_suggestions(
    search_type: Optional[str] = Query(None, description="Filter by search type"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Get trending search suggestions.

    Returns popular and trending searches
    based on recent user activity.
    """
    service = SearchService(db)
    return await service.get_trending_suggestions(search_type, limit)


@router.patch("/suggestions/{suggestion_id}", response_model=SearchSuggestionResponse)
async def update_suggestion(
    suggestion_id: UUID,
    suggestion_data: SearchSuggestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a search suggestion (admin only)"""
    service = SearchService(db)
    return await service.update_suggestion(suggestion_id, suggestion_data, current_user)


# ============================================================================
# Filter Preset Endpoints
# ============================================================================

@router.post("/filters/presets", response_model=FilterPresetResponse, status_code=status.HTTP_201_CREATED)
async def create_filter_preset(
    preset_data: FilterPresetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a filter preset (admin only).

    Filter presets are curated filter combinations like:
    - "Budget-Friendly Vendors"
    - "Premium Services"
    - "Top-Rated Venues"
    """
    service = SearchService(db)
    return await service.create_filter_preset(preset_data, current_user)


@router.get("/filters/presets", response_model=List[FilterPresetResponse])
async def get_filter_presets(
    search_type: Optional[str] = Query(None, description="Filter by search type"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get filter presets.

    Returns curated filter combinations
    for quick search refinement.
    """
    service = SearchService(db)
    return await service.get_filter_presets(search_type)


@router.patch("/filters/presets/{preset_id}", response_model=FilterPresetResponse)
async def update_filter_preset(
    preset_id: UUID,
    preset_data: FilterPresetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a filter preset (admin only)"""
    service = SearchService(db)
    return await service.update_filter_preset(preset_id, preset_data, current_user)


@router.delete("/filters/presets/{preset_id}", status_code=status.HTTP_200_OK)
async def delete_filter_preset(
    preset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a filter preset (admin only)"""
    service = SearchService(db)
    return await service.delete_filter_preset(preset_id, current_user)


# ============================================================================
# Analytics Endpoints
# ============================================================================

@router.get("/analytics/trending", response_model=List[SearchTrendingQuery])
async def get_trending_queries(
    search_type: Optional[str] = Query(None, description="Filter by search type"),
    days: int = Query(7, ge=1, le=30, description="Time period in days"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get trending search queries.

    Returns most popular search queries
    within the specified time period.

    Requires authentication.
    """
    service = SearchService(db)
    queries = await service.get_trending_queries(search_type, days, limit)

    return [
        SearchTrendingQuery(
            query=q["query"],
            search_count=q["count"],
            trend_percentage=0.0  # TODO: Calculate trend
        )
        for q in queries
    ]


@router.get("/analytics/summary", response_model=SearchAnalyticsSummary)
async def get_analytics_summary(
    start_date: Optional[datetime] = Query(None, description="Start date (defaults to 7 days ago)"),
    end_date: Optional[datetime] = Query(None, description="End date (defaults to now)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get search analytics summary.

    Provides overview of search activity including:
    - Total searches
    - Unique users
    - Average results
    - Average duration
    - Top queries
    - Trending queries

    Requires authentication (admin recommended).
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=7)
    if not end_date:
        end_date = datetime.utcnow()

    service = SearchService(db)
    return await service.get_analytics_summary(start_date, end_date)


# ============================================================================
# Vendor Matching Endpoints
# ============================================================================

@router.post("/match-vendors", response_model=List[VendorMatchingScoreResponse])
async def match_vendors_for_event(
    match_request: VendorMatchingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Match vendors to event requirements using AI algorithm.

    Calculates matching scores based on:
    - Category match
    - Location proximity
    - Budget compatibility
    - Availability
    - Rating and experience
    - Cultural fit
    - Style preferences

    Returns ranked list of best-matching vendors.
    """
    service = SearchService(db)
    return await service.match_vendors_for_event(
        event_id=match_request.event_id,
        category=match_request.category,
        max_results=match_request.max_results,
        min_score=match_request.min_score
    )
