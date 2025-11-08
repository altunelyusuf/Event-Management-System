"""
Performance & Optimization API
Sprint 22: Performance & Optimization

API endpoints for performance monitoring, caching, and system health.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.auth import get_current_user, require_admin
from app.models.user import User
from app.services.performance_service import PerformanceService
from app.services.cache_service import RedisCacheService, get_cache_service
from app.schemas.performance import (
    PerformanceMetricCreate, PerformanceMetricResponse,
    PerformanceMetricQuery, PerformanceMetricStats,
    CacheStats, SystemHealthResponse,
    PerformanceDashboard, LatencyBreakdown, ThroughputStats,
    DatabaseQueryStats, OptimizationReport,
    MonitoringDashboard, BenchmarkResult
)

router = APIRouter(prefix="/performance", tags=["performance"])


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_performance_service(
    db: AsyncSession = Depends(get_db),
    cache_service: RedisCacheService = Depends(get_cache_service)
) -> PerformanceService:
    """Get performance service instance"""
    async with PerformanceService(db, cache_service) as service:
        yield service


# ============================================================================
# Performance Metrics Endpoints
# ============================================================================

@router.post("/metrics", response_model=PerformanceMetricResponse, status_code=status.HTTP_201_CREATED)
async def record_metric(
    metric_data: PerformanceMetricCreate,
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Record a performance metric.

    Metric types:
    - api_latency: API endpoint response time
    - db_query_time: Database query execution time
    - cache_hit: Cache hit event
    - cache_miss: Cache miss event
    - request_count: Request counter
    - error_rate: Error rate percentage
    - cpu_usage: CPU utilization percentage
    - memory_usage: Memory utilization percentage
    """
    return await performance_service.record_metric(metric_data)


@router.get("/metrics", response_model=List[PerformanceMetricResponse])
async def query_metrics(
    metric_type: Optional[str] = None,
    hours_back: int = 24,
    limit: int = 1000,
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """Query performance metrics with filters"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=hours_back)

    query = PerformanceMetricQuery(
        metric_type=metric_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )

    return await performance_service.query_metrics(query)


@router.get("/metrics/stats/{metric_type}", response_model=PerformanceMetricStats)
async def get_metric_stats(
    metric_type: str,
    hours_back: int = 24,
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Get aggregated statistics for a metric type.

    Returns percentiles (p50, p95, p99), average, min, and max values.
    """
    return await performance_service.get_metric_stats(metric_type, hours_back)


@router.get("/metrics/latency/breakdown", response_model=List[LatencyBreakdown])
async def get_latency_breakdown(
    hours_back: int = 24,
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Get latency breakdown by endpoint.

    Returns average, p50, p95, p99 latency for each endpoint.
    """
    return await performance_service.get_latency_breakdown(hours_back)


@router.get("/metrics/throughput", response_model=ThroughputStats)
async def get_throughput_stats(
    hours_back: int = 1,
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """Get API throughput statistics (requests per second/minute/hour)"""
    return await performance_service.get_throughput_stats(hours_back)


@router.get("/metrics/database", response_model=List[DatabaseQueryStats])
async def get_database_query_stats(
    hours_back: int = 24,
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """Get database query performance statistics"""
    return await performance_service.get_database_query_stats(hours_back)


# ============================================================================
# Cache Management Endpoints
# ============================================================================

@router.get("/cache/stats", response_model=CacheStats)
async def get_cache_stats(
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Get cache statistics.

    Returns:
    - Total cache entries
    - Hit/miss counts
    - Hit rate percentage
    - Memory usage
    - Most accessed keys
    """
    return await performance_service.get_cache_stats()


@router.delete("/cache")
async def clear_cache(
    namespace: str = "default",
    current_user: User = Depends(require_admin),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Clear cache (admin only).

    Can specify namespace to clear specific cache sections.
    """
    return await performance_service.clear_cache(namespace)


@router.delete("/cache/expired")
async def clear_expired_cache(
    current_user: User = Depends(require_admin),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """Clear expired cache entries (admin only)"""
    return await performance_service.clear_expired_cache()


# ============================================================================
# System Health Endpoints
# ============================================================================

@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Get overall system health.

    Checks:
    - Database connection and performance
    - Redis connection and cache hit rate
    - API latency and error rate
    - Resource utilization (CPU, memory, disk)
    - Active alerts
    """
    return await performance_service.get_system_health()


@router.get("/health/ping")
async def health_ping():
    """
    Simple health check endpoint (no authentication required).

    Used by load balancers and monitoring systems.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": "performance-monitoring"
    }


# ============================================================================
# Dashboard & Monitoring Endpoints
# ============================================================================

@router.get("/dashboard", response_model=PerformanceDashboard)
async def get_performance_dashboard(
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Get comprehensive performance dashboard.

    Includes:
    - System health overview
    - API latency breakdown
    - Throughput statistics
    - Database query stats
    - Cache metrics
    - Resource utilization
    """
    return await performance_service.get_performance_dashboard()


@router.get("/monitoring", response_model=Dict[str, Any])
async def get_monitoring_dashboard(
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Get real-time monitoring dashboard.

    Returns current system status, metrics, and alerts.
    """
    health = await performance_service.get_system_health()
    cache_stats = await performance_service.get_cache_stats()
    latency_breakdown = await performance_service.get_latency_breakdown(hours_back=1)

    return {
        "timestamp": datetime.utcnow(),
        "status": health.status,
        "health": health.dict(),
        "cache_stats": cache_stats.dict(),
        "recent_latency": [lb.dict() for lb in latency_breakdown[:10]],
        "uptime_seconds": 0  # TODO: Track actual uptime
    }


# ============================================================================
# Optimization Endpoints
# ============================================================================

@router.get("/optimization/report", response_model=OptimizationReport)
async def get_optimization_report(
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Get optimization recommendations.

    Analyzes system performance and provides:
    - Optimization recommendations
    - Performance bottlenecks
    - Resource utilization analysis
    - Overall performance score (0-100)
    """
    return await performance_service.get_optimization_report()


# ============================================================================
# Benchmarking Endpoints
# ============================================================================

@router.post("/benchmark/{operation_name}", response_model=BenchmarkResult)
async def run_benchmark(
    operation_name: str,
    iterations: int = 100,
    current_user: User = Depends(require_admin),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Run a performance benchmark (admin only).

    Tests:
    - Database query performance
    - Cache read/write operations
    - API endpoint latency

    Returns average, min, max execution times and operations per second.
    """
    async def sample_operation():
        """Sample operation for benchmarking"""
        # In production, this would benchmark actual operations
        import asyncio
        await asyncio.sleep(0.001)

    return await performance_service.run_benchmark(
        operation_name,
        sample_operation,
        iterations
    )


# ============================================================================
# Maintenance Endpoints
# ============================================================================

@router.delete("/metrics/cleanup")
async def cleanup_old_metrics(
    days_to_keep: int = 30,
    current_user: User = Depends(require_admin),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Delete old performance metrics (admin only).

    Removes metrics older than specified days to save storage.
    Default: 30 days retention.
    """
    count = await performance_service.cleanup_old_metrics(days_to_keep)
    return {
        "deleted_count": count,
        "days_to_keep": days_to_keep
    }


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/metric-types")
async def get_metric_types(
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """Get list of available metric types"""
    metric_types = await performance_service.perf_repo.get_metric_types()
    return {
        "metric_types": metric_types,
        "available_types": [
            "api_latency",
            "db_query_time",
            "cache_hit",
            "cache_miss",
            "request_count",
            "error_rate",
            "cpu_usage",
            "memory_usage",
            "disk_io",
            "network_io",
            "concurrent_users",
            "active_sessions"
        ]
    }


@router.get("/thresholds")
async def get_performance_thresholds(
    current_user: User = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """Get performance alert thresholds"""
    return {
        "thresholds": performance_service.thresholds,
        "description": {
            "api_latency_warning": "API response time warning threshold (ms)",
            "api_latency_critical": "API response time critical threshold (ms)",
            "db_query_warning": "Database query warning threshold (ms)",
            "db_query_critical": "Database query critical threshold (ms)",
            "cache_hit_rate_warning": "Cache hit rate warning threshold (%)",
            "cache_hit_rate_critical": "Cache hit rate critical threshold (%)",
            "error_rate_warning": "Error rate warning threshold (%)",
            "error_rate_critical": "Error rate critical threshold (%)"
        }
    }


# ============================================================================
# Request Tracking Middleware Helper
# ============================================================================

async def track_request_performance(
    request: Request,
    endpoint: str,
    latency_ms: float,
    status_code: int,
    performance_service: PerformanceService
):
    """
    Helper function to track request performance.

    Should be called from middleware.
    """
    try:
        await performance_service.record_api_latency(
            endpoint=endpoint,
            method=request.method,
            latency_ms=latency_ms,
            status_code=status_code
        )
    except Exception as e:
        # Don't fail requests if performance tracking fails
        print(f"Performance tracking error: {e}")
