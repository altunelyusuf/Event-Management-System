"""
Search & Discovery Schemas
Sprint 13: Search & Discovery System

Pydantic schemas for search functionality.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# Search Request Schemas
# ============================================================================

class SearchRequest(BaseModel):
    """General search request"""
    query: Optional[str] = Field(None, max_length=500, description="Search query text")
    search_type: str = Field("vendor", description="Type: vendor, event, service, venue, all")

    # Filters
    category: Optional[str] = None
    subcategory: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # Price range
    price_min: Optional[float] = Field(None, ge=0)
    price_max: Optional[float] = Field(None, ge=0)

    # Rating filter
    rating_min: Optional[float] = Field(None, ge=0, le=5)

    # Location-based search
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius_km: Optional[float] = Field(None, ge=0, le=1000)
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = Field("TR", description="Country code")

    # Boolean filters
    verified_only: bool = False
    featured_only: bool = False
    available_only: bool = False
    instant_booking: bool = False

    # Date filters
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None

    # Sorting
    sort_by: str = Field("relevance", description="relevance, rating, price_low, price_high, distance, popularity, newest")

    # Pagination
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)

    # Advanced
    filters: Dict[str, Any] = Field(default_factory=dict)

    @validator('price_max')
    def validate_price_range(cls, v, values):
        if v and 'price_min' in values and values['price_min']:
            if v < values['price_min']:
                raise ValueError('price_max must be greater than price_min')
        return v


class VendorSearchRequest(SearchRequest):
    """Vendor-specific search"""
    search_type: str = Field("vendor", const=True)
    service_types: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    portfolio_keywords: List[str] = Field(default_factory=list)


class EventSearchRequest(SearchRequest):
    """Event-specific search"""
    search_type: str = Field("event", const=True)
    event_type: Optional[str] = None
    event_status: Optional[str] = None
    organizer_id: Optional[UUID] = None


class ServiceSearchRequest(SearchRequest):
    """Service-specific search"""
    search_type: str = Field("service", const=True)
    vendor_id: Optional[UUID] = None
    service_category: Optional[str] = None


# ============================================================================
# Search Response Schemas
# ============================================================================

class SearchHighlight(BaseModel):
    """Search result highlights"""
    field: str
    fragments: List[str]


class SearchResultBase(BaseModel):
    """Base search result"""
    id: UUID
    type: str
    title: str
    description: Optional[str]
    score: float
    highlights: List[SearchHighlight] = Field(default_factory=list)


class VendorSearchResult(SearchResultBase):
    """Vendor search result"""
    type: str = Field("vendor", const=True)
    business_name: str
    category: str
    subcategories: List[str]
    rating: Optional[float]
    review_count: int
    verified: bool
    featured: bool
    city: Optional[str]
    region: Optional[str]
    distance_km: Optional[float]
    price_range: Optional[str]
    availability_status: str
    image_url: Optional[str]

    class Config:
        from_attributes = True


class EventSearchResult(SearchResultBase):
    """Event search result"""
    type: str = Field("event", const=True)
    event_type: str
    event_date: Optional[datetime]
    location: Optional[str]
    status: str
    organizer_name: Optional[str]
    guest_count: Optional[int]

    class Config:
        from_attributes = True


class ServiceSearchResult(SearchResultBase):
    """Service search result"""
    type: str = Field("service", const=True)
    vendor_name: str
    vendor_id: UUID
    service_name: str
    category: str
    price: Optional[float]
    duration: Optional[str]

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Search response with results"""
    query: Optional[str]
    search_type: str
    total_results: int
    results_shown: int
    page: int
    total_pages: int
    search_duration_ms: int

    results: List[Any]  # Mix of VendorSearchResult, EventSearchResult, etc.

    # Facets for filtering
    facets: Dict[str, Any] = Field(default_factory=dict)

    # Suggestions
    suggestions: List[str] = Field(default_factory=list)
    did_you_mean: Optional[str] = None


# ============================================================================
# Saved Search Schemas
# ============================================================================

class SavedSearchCreate(BaseModel):
    """Create a saved search"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    search_type: str = "vendor"

    query_params: Dict[str, Any] = Field(default_factory=dict)

    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius_km: Optional[float] = Field(None, ge=0, le=1000)

    notify_on_new_results: bool = True
    notification_frequency: str = Field("daily", description="immediate, daily, weekly")


class SavedSearchUpdate(BaseModel):
    """Update a saved search"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    query_params: Optional[Dict[str, Any]] = None

    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius_km: Optional[float] = Field(None, ge=0, le=1000)

    notify_on_new_results: Optional[bool] = None
    notification_frequency: Optional[str] = None
    is_active: Optional[bool] = None


class SavedSearchResponse(BaseModel):
    """Saved search response"""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    search_type: str
    query_params: Dict[str, Any]

    latitude: Optional[float]
    longitude: Optional[float]
    radius_km: Optional[float]

    notify_on_new_results: bool
    notification_frequency: str

    use_count: int
    last_used_at: Optional[datetime]
    result_count_last_run: Optional[int]

    is_active: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Search Analytics Schemas
# ============================================================================

class SearchAnalyticsCreate(BaseModel):
    """Record search analytics"""
    search_type: str
    query_text: Optional[str] = None

    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    sort_by: Optional[str] = None

    search_latitude: Optional[float] = None
    search_longitude: Optional[float] = None
    search_radius_km: Optional[float] = None

    results_count: int = 0
    results_shown: int = 0
    results_clicked: List[UUID] = Field(default_factory=list)

    search_duration_ms: Optional[int] = None
    elasticsearch_used: bool = False

    clicked_position: Optional[int] = None
    session_id: Optional[str] = None

    page: Optional[str] = None
    device_type: Optional[str] = None


class SearchAnalyticsResponse(BaseModel):
    """Search analytics response"""
    id: UUID
    user_id: Optional[UUID]
    search_type: str
    query_text: Optional[str]

    filters_applied: Dict[str, Any]
    sort_by: Optional[str]

    results_count: int
    results_shown: int

    search_duration_ms: Optional[int]

    searched_at: datetime

    class Config:
        from_attributes = True


class SearchTrendingQuery(BaseModel):
    """Trending search query"""
    query: str
    search_count: int
    trend_percentage: float  # % change from previous period


class SearchAnalyticsSummary(BaseModel):
    """Search analytics summary"""
    total_searches: int
    unique_users: int
    average_results: float
    average_duration_ms: float

    top_queries: List[str]
    trending_queries: List[SearchTrendingQuery]

    searches_by_type: Dict[str, int]
    searches_by_device: Dict[str, int]

    period_start: datetime
    period_end: datetime


# ============================================================================
# Search Suggestion Schemas
# ============================================================================

class SearchSuggestionCreate(BaseModel):
    """Create a search suggestion"""
    suggestion_text: str = Field(..., min_length=1, max_length=200)
    suggestion_type: str = "vendor"

    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    is_featured: bool = False
    is_curated: bool = False
    seasonal: bool = False
    region: Optional[str] = None
    language: str = "en"

    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchSuggestionUpdate(BaseModel):
    """Update a search suggestion"""
    suggestion_text: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = None
    tags: Optional[List[str]] = None

    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None


class SearchSuggestionResponse(BaseModel):
    """Search suggestion response"""
    id: UUID
    suggestion_text: str
    suggestion_type: str

    category: Optional[str]
    tags: List[str]

    search_count: int
    click_through_rate: float
    conversion_rate: float

    relevance_score: float
    is_trending: bool
    is_featured: bool

    is_active: bool
    is_curated: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AutocompleteRequest(BaseModel):
    """Autocomplete request"""
    prefix: str = Field(..., min_length=1, max_length=100)
    search_type: Optional[str] = None
    limit: int = Field(10, ge=1, le=20)


class AutocompleteResponse(BaseModel):
    """Autocomplete response"""
    suggestions: List[str]
    count: int


# ============================================================================
# Filter Preset Schemas
# ============================================================================

class FilterPresetCreate(BaseModel):
    """Create a filter preset"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    icon: Optional[str] = None

    search_type: str = "vendor"
    filters: Dict[str, Any] = Field(default_factory=dict)

    display_order: int = 0
    is_featured: bool = False
    color: Optional[str] = Field(None, regex="^#[0-9A-Fa-f]{6}$")


class FilterPresetUpdate(BaseModel):
    """Update a filter preset"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    icon: Optional[str] = None

    filters: Optional[Dict[str, Any]] = None

    display_order: Optional[int] = None
    is_featured: Optional[bool] = None
    color: Optional[str] = Field(None, regex="^#[0-9A-Fa-f]{6}$")
    is_active: Optional[bool] = None


class FilterPresetResponse(BaseModel):
    """Filter preset response"""
    id: UUID
    name: str
    description: Optional[str]
    icon: Optional[str]

    search_type: str
    filters: Dict[str, Any]

    display_order: int
    is_featured: bool
    color: Optional[str]

    use_count: int
    is_active: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Vendor Matching Schemas
# ============================================================================

class VendorMatchingRequest(BaseModel):
    """Request vendor matching for an event"""
    event_id: UUID
    category: Optional[str] = None
    max_results: int = Field(20, ge=1, le=100)
    min_score: float = Field(0.0, ge=0, le=100)


class VendorMatchingScoreResponse(BaseModel):
    """Vendor matching score response"""
    id: UUID
    vendor_id: UUID
    event_id: UUID

    overall_score: float

    category_match_score: float
    location_score: float
    budget_score: float
    availability_score: float
    rating_score: float
    experience_score: float

    cultural_fit_score: float
    style_match_score: float

    match_details: Dict[str, Any]

    rank_position: Optional[int]

    calculated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Index Status Schemas
# ============================================================================

class SearchIndexStatusResponse(BaseModel):
    """Search index status"""
    id: UUID
    index_name: str
    entity_type: str

    is_healthy: bool
    last_sync_at: Optional[datetime]
    last_full_reindex_at: Optional[datetime]

    total_documents: int
    indexed_documents: int
    failed_documents: int

    sync_in_progress: bool
    last_error: Optional[str]

    updated_at: datetime

    class Config:
        from_attributes = True


class ReindexRequest(BaseModel):
    """Request to reindex"""
    index_name: str
    full_reindex: bool = False
    batch_size: int = Field(1000, ge=100, le=10000)
