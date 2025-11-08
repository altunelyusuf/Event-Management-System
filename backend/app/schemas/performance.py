"""
Performance & Optimization Schemas
Sprint 22: Performance & Optimization

Pydantic schemas for performance metrics, caching, and monitoring.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# Performance Metric Schemas
# ============================================================================

class PerformanceMetricCreate(BaseModel):
    """Schema for creating a performance metric"""
    metric_type: str = Field(..., description="Type of metric (api_latency, db_query, cache_hit, etc.)")
    metric_value: float = Field(..., description="Metric value")
    tags: Optional[Dict[str, Any]] = Field(None, description="Additional metadata tags")

    @validator('metric_type')
    def validate_metric_type(cls, v):
        """Validate metric type"""
        allowed_types = [
            'api_latency', 'db_query_time', 'cache_hit', 'cache_miss',
            'request_count', 'error_rate', 'cpu_usage', 'memory_usage',
            'disk_io', 'network_io', 'concurrent_users', 'active_sessions'
        ]
        if v not in allowed_types:
            raise ValueError(f'Invalid metric type. Allowed: {allowed_types}')
        return v


class PerformanceMetricResponse(BaseModel):
    """Schema for performance metric response"""
    id: UUID
    metric_type: str
    metric_value: float
    tags: Optional[Dict[str, Any]]
    recorded_at: datetime

    class Config:
        from_attributes = True


class PerformanceMetricQuery(BaseModel):
    """Schema for querying performance metrics"""
    metric_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    tags: Optional[Dict[str, Any]] = None
    limit: int = Field(1000, ge=1, le=10000)


class PerformanceMetricStats(BaseModel):
    """Schema for aggregated performance stats"""
    metric_type: str
    count: int
    avg: float
    min: float
    max: float
    p50: float
    p95: float
    p99: float
    period_start: datetime
    period_end: datetime


# ============================================================================
# Cache Schemas
# ============================================================================

class CacheEntryCreate(BaseModel):
    """Schema for creating a cache entry"""
    cache_key: str = Field(..., max_length=500)
    cache_value: Dict[str, Any] = Field(...)
    ttl: int = Field(..., ge=1, le=86400, description="Time to live in seconds")


class CacheEntryResponse(BaseModel):
    """Schema for cache entry response"""
    id: UUID
    cache_key: str
    cache_value: Dict[str, Any]
    ttl: int
    hit_count: int
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


class CacheStats(BaseModel):
    """Schema for cache statistics"""
    total_entries: int
    total_hits: int
    total_misses: int
    hit_rate: float
    memory_usage_mb: float
    expired_entries: int
    most_accessed_keys: List[Dict[str, Any]]


class CacheKeyPattern(BaseModel):
    """Schema for cache key pattern"""
    pattern: str = Field(..., description="Pattern to match cache keys (supports wildcards)")


# ============================================================================
# System Health Schemas
# ============================================================================

class SystemHealthResponse(BaseModel):
    """Schema for system health check"""
    status: str = Field(..., description="Overall system status (healthy, degraded, unhealthy)")
    timestamp: datetime
    components: Dict[str, Any]
    metrics: Dict[str, float]
    alerts: List[str]


class DatabaseHealth(BaseModel):
    """Schema for database health"""
    status: str
    connection_pool_size: int
    active_connections: int
    idle_connections: int
    avg_query_time_ms: float
    slow_queries: int


class RedisHealth(BaseModel):
    """Schema for Redis health"""
    status: str
    connected: bool
    memory_usage_mb: float
    total_keys: int
    hit_rate: float
    avg_latency_ms: float


class APIHealth(BaseModel):
    """Schema for API health"""
    status: str
    total_requests: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    error_rate: float
    active_requests: int


# ============================================================================
# Performance Dashboard Schemas
# ============================================================================

class PerformanceDashboard(BaseModel):
    """Schema for performance dashboard"""
    timestamp: datetime
    system_health: SystemHealthResponse
    api_metrics: Dict[str, Any]
    database_metrics: Dict[str, Any]
    cache_metrics: Dict[str, Any]
    resource_usage: Dict[str, Any]


class LatencyBreakdown(BaseModel):
    """Schema for latency breakdown by endpoint"""
    endpoint: str
    method: str
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    request_count: int
    error_count: int
    error_rate: float


class ThroughputStats(BaseModel):
    """Schema for throughput statistics"""
    timestamp: datetime
    requests_per_second: float
    requests_per_minute: float
    requests_per_hour: float
    peak_rps: float
    avg_rps: float


# ============================================================================
# Database Performance Schemas
# ============================================================================

class DatabaseQueryStats(BaseModel):
    """Schema for database query statistics"""
    query_type: str
    table_name: str
    avg_execution_time_ms: float
    min_execution_time_ms: float
    max_execution_time_ms: float
    total_executions: int
    slow_query_count: int


class DatabaseIndexStats(BaseModel):
    """Schema for database index statistics"""
    table_name: str
    index_name: str
    index_size_mb: float
    index_scans: int
    tuples_read: int
    tuples_fetched: int
    is_unique: bool


class DatabaseConnectionStats(BaseModel):
    """Schema for database connection statistics"""
    total_connections: int
    active_connections: int
    idle_connections: int
    waiting_connections: int
    max_connections: int
    connection_utilization: float


# ============================================================================
# Load Testing Schemas
# ============================================================================

class LoadTestRequest(BaseModel):
    """Schema for load test request"""
    test_name: str
    target_endpoint: str
    concurrent_users: int = Field(..., ge=1, le=10000)
    duration_seconds: int = Field(..., ge=1, le=3600)
    ramp_up_seconds: int = Field(0, ge=0, le=300)
    request_rate: Optional[int] = Field(None, description="Requests per second (optional)")


class LoadTestResponse(BaseModel):
    """Schema for load test response"""
    test_id: UUID
    test_name: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[float]
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    requests_per_second: float
    errors: List[Dict[str, Any]]


# ============================================================================
# Optimization Schemas
# ============================================================================

class OptimizationRecommendation(BaseModel):
    """Schema for optimization recommendation"""
    category: str = Field(..., description="Category (database, cache, api, etc.)")
    severity: str = Field(..., description="Severity (low, medium, high, critical)")
    title: str
    description: str
    impact: str
    suggested_fix: str
    estimated_improvement: Optional[str] = None


class OptimizationReport(BaseModel):
    """Schema for optimization report"""
    generated_at: datetime
    overall_score: float = Field(..., ge=0, le=100)
    recommendations: List[OptimizationRecommendation]
    bottlenecks: List[Dict[str, Any]]
    resource_utilization: Dict[str, float]


# ============================================================================
# Alert Schemas
# ============================================================================

class PerformanceAlert(BaseModel):
    """Schema for performance alert"""
    alert_type: str = Field(..., description="Type of alert")
    severity: str = Field(..., description="Severity level")
    message: str
    metric_type: str
    current_value: float
    threshold_value: float
    triggered_at: datetime


class AlertRule(BaseModel):
    """Schema for alert rule"""
    name: str
    metric_type: str
    operator: str = Field(..., regex="^(gt|gte|lt|lte|eq)$")
    threshold: float
    duration_seconds: int = Field(60, description="Alert after threshold exceeded for this duration")
    enabled: bool = True


class AlertRuleResponse(BaseModel):
    """Schema for alert rule response"""
    id: UUID
    name: str
    metric_type: str
    operator: str
    threshold: float
    duration_seconds: int
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Resource Monitoring Schemas
# ============================================================================

class ResourceUsage(BaseModel):
    """Schema for resource usage"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent_mb: float
    network_recv_mb: float
    active_connections: int


class ResourceThresholds(BaseModel):
    """Schema for resource thresholds"""
    cpu_percent: float = Field(80.0, ge=0, le=100)
    memory_percent: float = Field(80.0, ge=0, le=100)
    disk_percent: float = Field(85.0, ge=0, le=100)
    connection_count: int = Field(1000, ge=1)


# ============================================================================
# Monitoring Dashboard Schemas
# ============================================================================

class MonitoringDashboard(BaseModel):
    """Schema for comprehensive monitoring dashboard"""
    timestamp: datetime
    status: str
    uptime_seconds: float
    api_stats: Dict[str, Any]
    database_stats: Dict[str, Any]
    cache_stats: Dict[str, Any]
    resource_stats: Dict[str, Any]
    active_alerts: List[PerformanceAlert]
    recent_errors: List[Dict[str, Any]]


# ============================================================================
# Benchmark Schemas
# ============================================================================

class BenchmarkResult(BaseModel):
    """Schema for benchmark result"""
    benchmark_name: str
    operation: str
    iterations: int
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    ops_per_second: float
    timestamp: datetime


class BenchmarkComparison(BaseModel):
    """Schema for benchmark comparison"""
    operation: str
    baseline_ops_per_second: float
    current_ops_per_second: float
    improvement_percent: float
    is_improved: bool
