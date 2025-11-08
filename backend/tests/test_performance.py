"""
Performance & Optimization Tests
Sprint 24: Testing & Documentation

Tests for Sprint 22 performance monitoring and caching features.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cache_service import RedisCacheService
from app.schemas.performance import PerformanceMetricCreate


@pytest.mark.asyncio
@pytest.mark.unit
class TestPerformanceMetrics:
    """Test performance metrics recording and querying"""

    async def test_record_metric(self, client: AsyncClient, auth_headers: dict):
        """Test recording a performance metric"""
        response = await client.post(
            "/api/v1/performance/metrics",
            headers=auth_headers,
            json={
                "metric_type": "api_latency",
                "metric_value": 150.5,
                "tags": {
                    "endpoint": "/api/v1/events",
                    "method": "GET"
                }
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["metric_type"] == "api_latency"
        assert data["metric_value"] == 150.5

    async def test_query_metrics(self, client: AsyncClient, auth_headers: dict):
        """Test querying performance metrics"""
        # First, record some metrics
        for i in range(5):
            await client.post(
                "/api/v1/performance/metrics",
                headers=auth_headers,
                json={
                    "metric_type": "api_latency",
                    "metric_value": 100.0 + i * 10,
                    "tags": {}
                }
            )

        # Then query them
        response = await client.get(
            "/api/v1/performance/metrics?metric_type=api_latency&limit=10",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5

    async def test_get_metric_stats(self, client: AsyncClient, auth_headers: dict):
        """Test getting metric statistics"""
        # Record metrics
        for value in [100, 150, 200, 250, 300]:
            await client.post(
                "/api/v1/performance/metrics",
                headers=auth_headers,
                json={
                    "metric_type": "db_query_time",
                    "metric_value": float(value),
                    "tags": {}
                }
            )

        # Get stats
        response = await client.get(
            "/api/v1/performance/metrics/stats/db_query_time",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "avg" in data
        assert "min" in data
        assert "max" in data
        assert "p50" in data
        assert "p95" in data
        assert "p99" in data


@pytest.mark.asyncio
@pytest.mark.unit
class TestCacheService:
    """Test caching service"""

    async def test_cache_set_and_get(self):
        """Test setting and getting cache values"""
        cache = RedisCacheService()

        # Set value
        await cache.set("test_key", {"data": "test_value"}, ttl=60)

        # Get value
        result = await cache.get("test_key")

        assert result is not None
        assert result["data"] == "test_value"

    async def test_cache_miss(self):
        """Test cache miss"""
        cache = RedisCacheService()

        result = await cache.get("nonexistent_key")

        assert result is None

    async def test_cache_delete(self):
        """Test deleting cache entry"""
        cache = RedisCacheService()

        # Set and then delete
        await cache.set("delete_key", "value")
        await cache.delete("delete_key")

        result = await cache.get("delete_key")
        assert result is None

    async def test_cache_statistics(self):
        """Test cache statistics"""
        cache = RedisCacheService()

        # Perform some cache operations
        await cache.set("key1", "value1")
        await cache.get("key1")  # Hit
        await cache.get("key2")  # Miss

        stats = cache.get_stats()

        assert "l1_hits" in stats
        assert "l1_misses" in stats
        assert "combined_hit_rate" in stats


@pytest.mark.asyncio
@pytest.mark.unit
class TestSystemHealth:
    """Test system health monitoring"""

    async def test_health_check(self, client: AsyncClient, auth_headers: dict):
        """Test system health check"""
        response = await client.get(
            "/api/v1/performance/health",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "metrics" in data

    async def test_health_ping(self, client: AsyncClient):
        """Test simple health ping (no auth required)"""
        response = await client.get("/api/v1/performance/health/ping")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
@pytest.mark.unit
class TestPerformanceDashboard:
    """Test performance dashboard"""

    async def test_get_dashboard(self, client: AsyncClient, auth_headers: dict):
        """Test getting performance dashboard"""
        response = await client.get(
            "/api/v1/performance/dashboard",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "system_health" in data
        assert "api_metrics" in data
        assert "cache_metrics" in data

    async def test_latency_breakdown(self, client: AsyncClient, auth_headers: dict):
        """Test latency breakdown"""
        response = await client.get(
            "/api/v1/performance/metrics/latency/breakdown",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceBenchmark:
    """Performance benchmark tests"""

    async def test_api_response_time(self, client: AsyncClient, auth_headers: dict, performance_timer):
        """Test API response time is within acceptable limits"""
        performance_timer.start()

        response = await client.get(
            "/api/v1/performance/health/ping"
        )

        performance_timer.stop()

        assert response.status_code == 200
        assert performance_timer.elapsed_ms() < 200  # Should respond in < 200ms

    async def test_cache_hit_performance(self):
        """Test cache hit performance"""
        cache = RedisCacheService()

        # Warm up cache
        await cache.set("perf_test", {"large": "data" * 100})

        # Measure cache hit time
        import time
        start = time.time()

        for _ in range(100):
            await cache.get("perf_test")

        elapsed = (time.time() - start) * 1000

        # 100 cache hits should complete in < 100ms
        assert elapsed < 100

    async def test_concurrent_requests(self, client: AsyncClient, auth_headers: dict):
        """Test handling concurrent requests"""
        import asyncio

        async def make_request():
            return await client.get(
                "/api/v1/performance/health/ping"
            )

        # Make 50 concurrent requests
        tasks = [make_request() for _ in range(50)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)


@pytest.mark.asyncio
@pytest.mark.unit
class TestOptimizationReport:
    """Test optimization recommendations"""

    async def test_get_optimization_report(self, client: AsyncClient, auth_headers: dict):
        """Test getting optimization report"""
        response = await client.get(
            "/api/v1/performance/optimization/report",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data
        assert "recommendations" in data
        assert 0 <= data["overall_score"] <= 100
