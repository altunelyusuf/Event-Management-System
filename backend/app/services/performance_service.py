"""
Performance & Optimization Service
Sprint 22: Performance & Optimization

Service layer for performance metrics, monitoring, and optimization.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import asyncio
import psutil
import time

from app.repositories.performance_repository import PerformanceRepository
from app.services.cache_service import RedisCacheService
from app.schemas.performance import (
    PerformanceMetricCreate, PerformanceMetricResponse,
    PerformanceMetricQuery, PerformanceMetricStats,
    CacheEntryCreate, CacheEntryResponse, CacheStats,
    SystemHealthResponse, DatabaseHealth, RedisHealth, APIHealth,
    PerformanceDashboard, LatencyBreakdown, ThroughputStats,
    DatabaseQueryStats, OptimizationRecommendation, OptimizationReport,
    PerformanceAlert, ResourceUsage, MonitoringDashboard,
    BenchmarkResult
)


class PerformanceService:
    """Service for performance monitoring and optimization"""

    def __init__(
        self,
        db: AsyncSession,
        cache_service: Optional[RedisCacheService] = None
    ):
        self.db = db
        self.perf_repo = PerformanceRepository(db)
        self.cache_service = cache_service

        # Performance thresholds
        self.thresholds = {
            "api_latency_warning": 200,  # ms
            "api_latency_critical": 500,  # ms
            "db_query_warning": 50,  # ms
            "db_query_critical": 100,  # ms
            "cache_hit_rate_warning": 70,  # %
            "cache_hit_rate_critical": 50,  # %
            "error_rate_warning": 1,  # %
            "error_rate_critical": 5,  # %
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db.close()

    # ========================================================================
    # Metric Recording
    # ========================================================================

    async def record_metric(
        self,
        metric_data: PerformanceMetricCreate
    ) -> PerformanceMetricResponse:
        """Record a performance metric"""
        metric = await self.perf_repo.record_metric(metric_data)
        await self.db.commit()

        # Check for alerts
        await self._check_metric_thresholds(metric_data)

        return PerformanceMetricResponse.from_orm(metric)

    async def record_api_latency(
        self,
        endpoint: str,
        method: str,
        latency_ms: float,
        status_code: int,
        error: Optional[str] = None
    ):
        """Record API endpoint latency"""
        metric_data = PerformanceMetricCreate(
            metric_type="api_latency",
            metric_value=latency_ms,
            tags={
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "error": error
            }
        )
        await self.record_metric(metric_data)

    async def record_db_query_time(
        self,
        table: str,
        query_type: str,
        execution_time_ms: float
    ):
        """Record database query execution time"""
        metric_data = PerformanceMetricCreate(
            metric_type="db_query_time",
            metric_value=execution_time_ms,
            tags={
                "table": table,
                "type": query_type
            }
        )
        await self.record_metric(metric_data)

    async def record_cache_hit(self):
        """Record a cache hit"""
        metric_data = PerformanceMetricCreate(
            metric_type="cache_hit",
            metric_value=1
        )
        await self.record_metric(metric_data)

    async def record_cache_miss(self):
        """Record a cache miss"""
        metric_data = PerformanceMetricCreate(
            metric_type="cache_miss",
            metric_value=1
        )
        await self.record_metric(metric_data)

    # ========================================================================
    # Metric Queries
    # ========================================================================

    async def query_metrics(
        self,
        query: PerformanceMetricQuery
    ) -> List[PerformanceMetricResponse]:
        """Query performance metrics"""
        metrics = await self.perf_repo.query_metrics(query)
        return [PerformanceMetricResponse.from_orm(m) for m in metrics]

    async def get_metric_stats(
        self,
        metric_type: str,
        hours_back: int = 24
    ) -> PerformanceMetricStats:
        """Get aggregated statistics for a metric type"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=hours_back)

        stats = await self.perf_repo.get_metric_stats(
            metric_type,
            start_date,
            end_date
        )

        return PerformanceMetricStats(
            metric_type=metric_type,
            count=stats["count"],
            avg=stats["avg"],
            min=stats["min"],
            max=stats["max"],
            p50=stats["p50"],
            p95=stats["p95"],
            p99=stats["p99"],
            period_start=start_date,
            period_end=end_date
        )

    # ========================================================================
    # Cache Management
    # ========================================================================

    async def get_cache_stats(self) -> CacheStats:
        """Get cache statistics"""
        if self.cache_service:
            service_stats = self.cache_service.get_stats()
            return CacheStats(
                total_entries=service_stats["l1_size"],
                total_hits=service_stats["l1_hits"] + service_stats["l2_hits"],
                total_misses=service_stats["l1_misses"] + service_stats["l2_misses"],
                hit_rate=service_stats["combined_hit_rate"],
                memory_usage_mb=0,  # TODO: Calculate actual memory usage
                expired_entries=0,
                most_accessed_keys=[]
            )

        # Fallback to database cache stats
        db_stats = await self.perf_repo.get_cache_stats()
        total_hits = db_stats["total_hits"]
        total_misses = db_stats.get("total_misses", 0)
        total_requests = total_hits + total_misses
        hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0

        return CacheStats(
            total_entries=db_stats["total_entries"],
            total_hits=total_hits,
            total_misses=total_misses,
            hit_rate=hit_rate,
            memory_usage_mb=0,
            expired_entries=db_stats["expired_entries"],
            most_accessed_keys=db_stats["most_accessed_keys"]
        )

    async def clear_cache(self, namespace: str = "default") -> Dict[str, Any]:
        """Clear cache"""
        if self.cache_service:
            await self.cache_service.clear(namespace)
            return {"cleared": True, "namespace": namespace}

        # Clear database cache
        count = await self.perf_repo.clear_all_cache()
        await self.db.commit()
        return {"cleared": True, "entries_deleted": count}

    async def clear_expired_cache(self) -> Dict[str, Any]:
        """Clear expired cache entries"""
        count = await self.perf_repo.clear_expired_cache()
        await self.db.commit()
        return {"entries_deleted": count}

    # ========================================================================
    # System Health
    # ========================================================================

    async def get_system_health(self) -> SystemHealthResponse:
        """Get overall system health"""
        # Get component health
        db_health = await self._get_database_health()
        redis_health = await self._get_redis_health()
        api_health = await self._get_api_health()

        # Determine overall status
        components = {
            "database": db_health.dict(),
            "redis": redis_health.dict(),
            "api": api_health.dict()
        }

        all_healthy = all(
            comp.get("status") == "healthy"
            for comp in components.values()
        )

        status = "healthy" if all_healthy else "degraded"

        # Get resource metrics
        resource_usage = self._get_resource_usage()

        # Check for alerts
        alerts = await self._generate_alerts()

        return SystemHealthResponse(
            status=status,
            timestamp=datetime.utcnow(),
            components=components,
            metrics={
                "cpu_percent": resource_usage["cpu_percent"],
                "memory_percent": resource_usage["memory_percent"],
                "disk_percent": resource_usage["disk_percent"]
            },
            alerts=alerts
        )

    async def _get_database_health(self) -> DatabaseHealth:
        """Get database health metrics"""
        # In production, query actual database pool stats
        return DatabaseHealth(
            status="healthy",
            connection_pool_size=10,
            active_connections=2,
            idle_connections=8,
            avg_query_time_ms=15.5,
            slow_queries=0
        )

    async def _get_redis_health(self) -> RedisHealth:
        """Get Redis health metrics"""
        if not self.cache_service or not self.cache_service.redis_client:
            return RedisHealth(
                status="unavailable",
                connected=False,
                memory_usage_mb=0,
                total_keys=0,
                hit_rate=0,
                avg_latency_ms=0
            )

        stats = self.cache_service.get_stats()

        return RedisHealth(
            status="healthy",
            connected=True,
            memory_usage_mb=0,  # TODO: Query from Redis
            total_keys=stats["l1_size"],
            hit_rate=stats["l2_hit_rate"],
            avg_latency_ms=0.5
        )

    async def _get_api_health(self) -> APIHealth:
        """Get API health metrics"""
        # Get recent API metrics
        latency_stats = await self.get_metric_stats("api_latency", hours_back=1)

        return APIHealth(
            status="healthy",
            total_requests=latency_stats.count,
            avg_response_time_ms=latency_stats.avg,
            p95_response_time_ms=latency_stats.p95,
            error_rate=0.5,  # TODO: Calculate from actual error metrics
            active_requests=0
        )

    # ========================================================================
    # Performance Dashboard
    # ========================================================================

    async def get_performance_dashboard(self) -> PerformanceDashboard:
        """Get comprehensive performance dashboard"""
        system_health = await self.get_system_health()

        # Get API metrics
        api_latency_breakdown = await self.get_latency_breakdown(hours_back=24)
        throughput_stats = await self.get_throughput_stats(hours_back=1)

        # Get database metrics
        db_query_stats = await self.get_database_query_stats(hours_back=24)

        # Get cache metrics
        cache_stats = await self.get_cache_stats()

        # Get resource usage
        resource_usage = self._get_resource_usage()

        return PerformanceDashboard(
            timestamp=datetime.utcnow(),
            system_health=system_health,
            api_metrics={
                "latency_breakdown": [lb.dict() for lb in api_latency_breakdown],
                "throughput": throughput_stats.dict()
            },
            database_metrics={
                "query_stats": [qs.dict() for qs in db_query_stats]
            },
            cache_metrics=cache_stats.dict(),
            resource_usage=resource_usage
        )

    async def get_latency_breakdown(
        self,
        hours_back: int = 24
    ) -> List[LatencyBreakdown]:
        """Get latency breakdown by endpoint"""
        data = await self.perf_repo.get_latency_by_endpoint(hours_back)

        return [
            LatencyBreakdown(
                endpoint=item["endpoint"],
                method=item["method"],
                avg_latency_ms=item["avg_latency_ms"],
                p50_latency_ms=item["p50_latency_ms"],
                p95_latency_ms=item["p95_latency_ms"],
                p99_latency_ms=item["p99_latency_ms"],
                request_count=item["request_count"],
                error_count=item["error_count"],
                error_rate=item["error_rate"]
            )
            for item in data
        ]

    async def get_throughput_stats(
        self,
        hours_back: int = 1
    ) -> ThroughputStats:
        """Get throughput statistics"""
        data = await self.perf_repo.get_throughput_stats(hours_back)

        return ThroughputStats(
            timestamp=data["timestamp"],
            requests_per_second=data["requests_per_second"],
            requests_per_minute=data["requests_per_minute"],
            requests_per_hour=data["requests_per_hour"],
            peak_rps=data["requests_per_second"],  # TODO: Track actual peak
            avg_rps=data["requests_per_second"]
        )

    async def get_database_query_stats(
        self,
        hours_back: int = 24
    ) -> List[DatabaseQueryStats]:
        """Get database query statistics"""
        data = await self.perf_repo.get_database_query_stats(hours_back)

        return [
            DatabaseQueryStats(
                query_type=item["query_type"],
                table_name=item["table_name"],
                avg_execution_time_ms=item["avg_execution_time_ms"],
                min_execution_time_ms=item["min_execution_time_ms"],
                max_execution_time_ms=item["max_execution_time_ms"],
                total_executions=item["total_executions"],
                slow_query_count=item["slow_query_count"]
            )
            for item in data
        ]

    # ========================================================================
    # Optimization
    # ========================================================================

    async def get_optimization_report(self) -> OptimizationReport:
        """Generate optimization recommendations"""
        recommendations = []

        # Check API latency
        api_stats = await self.get_metric_stats("api_latency", hours_back=24)
        if api_stats.p95 > self.thresholds["api_latency_warning"]:
            recommendations.append(
                OptimizationRecommendation(
                    category="api",
                    severity="high" if api_stats.p95 > self.thresholds["api_latency_critical"] else "medium",
                    title="High API Latency Detected",
                    description=f"P95 latency is {api_stats.p95:.2f}ms (threshold: {self.thresholds['api_latency_warning']}ms)",
                    impact="User experience degradation, potential timeouts",
                    suggested_fix="Enable caching, optimize database queries, add indexes",
                    estimated_improvement="30-50% latency reduction"
                )
            )

        # Check cache hit rate
        cache_stats = await self.get_cache_stats()
        if cache_stats.hit_rate < self.thresholds["cache_hit_rate_warning"]:
            recommendations.append(
                OptimizationRecommendation(
                    category="cache",
                    severity="medium",
                    title="Low Cache Hit Rate",
                    description=f"Cache hit rate is {cache_stats.hit_rate:.2f}% (threshold: {self.thresholds['cache_hit_rate_warning']}%)",
                    impact="Increased database load, slower response times",
                    suggested_fix="Review cache TTL settings, increase cache size, add more cacheable endpoints",
                    estimated_improvement="20-40% faster response times"
                )
            )

        # Check database query performance
        db_stats = await self.get_database_query_stats(hours_back=24)
        slow_queries = [q for q in db_stats if q.avg_execution_time_ms > self.thresholds["db_query_warning"]]
        if slow_queries:
            recommendations.append(
                OptimizationRecommendation(
                    category="database",
                    severity="high",
                    title="Slow Database Queries Detected",
                    description=f"{len(slow_queries)} queries exceed {self.thresholds['db_query_warning']}ms threshold",
                    impact="Database bottleneck, increased resource usage",
                    suggested_fix="Add indexes, optimize queries, denormalize data if needed",
                    estimated_improvement="50-80% query time reduction"
                )
            )

        # Calculate overall score
        overall_score = 100.0
        if api_stats.p95 > self.thresholds["api_latency_warning"]:
            overall_score -= 20
        if cache_stats.hit_rate < self.thresholds["cache_hit_rate_warning"]:
            overall_score -= 15
        if slow_queries:
            overall_score -= 25

        return OptimizationReport(
            generated_at=datetime.utcnow(),
            overall_score=max(0, overall_score),
            recommendations=recommendations,
            bottlenecks=[
                {"type": "api_latency", "value": api_stats.p95},
                {"type": "cache_hit_rate", "value": cache_stats.hit_rate}
            ],
            resource_utilization=self._get_resource_usage()
        )

    # ========================================================================
    # Monitoring & Alerts
    # ========================================================================

    async def _check_metric_thresholds(self, metric: PerformanceMetricCreate):
        """Check if metric exceeds thresholds and generate alerts"""
        # This would trigger alert notifications in production
        if metric.metric_type == "api_latency":
            if metric.metric_value > self.thresholds["api_latency_critical"]:
                print(f"⚠️ CRITICAL: API latency {metric.metric_value}ms exceeds threshold")

    async def _generate_alerts(self) -> List[str]:
        """Generate current system alerts"""
        alerts = []

        # Check API latency
        api_stats = await self.get_metric_stats("api_latency", hours_back=1)
        if api_stats.p95 > self.thresholds["api_latency_critical"]:
            alerts.append(f"Critical API latency: {api_stats.p95:.2f}ms")

        # Check cache hit rate
        cache_stats = await self.get_cache_stats()
        if cache_stats.hit_rate < self.thresholds["cache_hit_rate_critical"]:
            alerts.append(f"Low cache hit rate: {cache_stats.hit_rate:.2f}%")

        return alerts

    def _get_resource_usage(self) -> Dict[str, float]:
        """Get current resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "disk_used_gb": disk.used / (1024 * 1024 * 1024)
            }
        except Exception as e:
            print(f"Error getting resource usage: {e}")
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_percent": 0,
                "memory_used_mb": 0,
                "disk_used_gb": 0
            }

    # ========================================================================
    # Benchmarking
    # ========================================================================

    async def run_benchmark(
        self,
        operation_name: str,
        operation_func,
        iterations: int = 100
    ) -> BenchmarkResult:
        """Run a benchmark on an operation"""
        times = []

        for _ in range(iterations):
            start_time = time.time()
            await operation_func()
            end_time = time.time()
            times.append((end_time - start_time) * 1000)  # Convert to ms

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        ops_per_second = 1000 / avg_time if avg_time > 0 else 0

        return BenchmarkResult(
            benchmark_name=f"benchmark_{operation_name}",
            operation=operation_name,
            iterations=iterations,
            avg_time_ms=avg_time,
            min_time_ms=min_time,
            max_time_ms=max_time,
            ops_per_second=ops_per_second,
            timestamp=datetime.utcnow()
        )

    # ========================================================================
    # Cleanup
    # ========================================================================

    async def cleanup_old_metrics(self, days_to_keep: int = 30) -> int:
        """Delete old performance metrics"""
        count = await self.perf_repo.delete_old_metrics(days_to_keep)
        await self.db.commit()
        return count
