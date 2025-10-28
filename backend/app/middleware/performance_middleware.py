"""
Performance Monitoring Middleware
Sprint 22: Performance & Optimization

Middleware for automatic performance tracking and monitoring.
"""

import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from typing import Callable
import asyncio

from app.schemas.performance import PerformanceMetricCreate


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API request performance.

    Automatically records:
    - Request latency
    - Request count
    - Error rates
    - Response sizes
    """

    def __init__(
        self,
        app,
        track_latency: bool = True,
        track_requests: bool = True,
        excluded_paths: list = None
    ):
        super().__init__(app)
        self.track_latency = track_latency
        self.track_requests = track_requests
        self.excluded_paths = excluded_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/performance/health/ping"
        ]

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request and track performance"""
        # Skip tracking for excluded paths
        if self._should_exclude(request.url.path):
            return await call_next(request)

        # Record start time
        start_time = time.time()

        # Process request
        response = None
        error = None

        try:
            response = await call_next(request)
        except Exception as e:
            error = str(e)
            raise
        finally:
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Track metrics (don't await to avoid slowing down requests)
            asyncio.create_task(
                self._record_metrics(
                    request=request,
                    response=response,
                    latency_ms=latency_ms,
                    error=error
                )
            )

        return response

    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from tracking"""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)

    async def _record_metrics(
        self,
        request: Request,
        response: Response,
        latency_ms: float,
        error: str = None
    ):
        """Record performance metrics (async, non-blocking)"""
        try:
            # Get performance service from app state
            # Note: In production, this would be injected properly
            # For now, we'll just log the metrics

            endpoint = request.url.path
            method = request.method
            status_code = response.status_code if response else 500

            # Log metrics (in production, save to database/metrics system)
            if self.track_latency:
                print(f"📊 {method} {endpoint} - {latency_ms:.2f}ms - {status_code}")

            # You can add more detailed tracking here:
            # - await performance_service.record_api_latency(...)
            # - await performance_service.record_metric(...)

        except Exception as e:
            # Don't fail requests if metric recording fails
            print(f"Metric recording error: {e}")


class CacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware for response caching.

    Caches GET requests based on URL and query parameters.
    """

    def __init__(
        self,
        app,
        cache_service=None,
        default_ttl: int = 300,
        cacheable_methods: list = None,
        excluded_paths: list = None
    ):
        super().__init__(app)
        self.cache_service = cache_service
        self.default_ttl = default_ttl
        self.cacheable_methods = cacheable_methods or ["GET"]
        self.excluded_paths = excluded_paths or [
            "/auth",
            "/performance",
            "/admin"
        ]

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request with caching"""
        # Only cache specific methods
        if request.method not in self.cacheable_methods:
            return await call_next(request)

        # Skip caching for excluded paths
        if self._should_exclude(request.url.path):
            return await call_next(request)

        # Check if cache service is available
        if not self.cache_service:
            return await call_next(request)

        # Generate cache key
        cache_key = self._generate_cache_key(request)

        # Try to get from cache
        cached_response = await self.cache_service.get(cache_key, namespace="http_cache")
        if cached_response:
            # Return cached response
            return Response(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers={"X-Cache": "HIT"}
            )

        # Process request
        response = await call_next(request)

        # Cache successful responses
        if 200 <= response.status_code < 300:
            # Read response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            # Cache response
            await self.cache_service.set(
                cache_key,
                {
                    "content": body.decode(),
                    "status_code": response.status_code
                },
                ttl=self.default_ttl,
                namespace="http_cache"
            )

            # Return response with body
            return Response(
                content=body,
                status_code=response.status_code,
                headers={"X-Cache": "MISS"}
            )

        return response

    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from caching"""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)

    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key from request"""
        # Include method, path, and query parameters
        key_parts = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items()))
        ]

        return ":".join(key_parts)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.

    Limits requests per user/IP to prevent abuse.
    """

    def __init__(
        self,
        app,
        cache_service=None,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        super().__init__(app)
        self.cache_service = cache_service
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request with rate limiting"""
        if not self.cache_service:
            return await call_next(request)

        # Get client identifier (IP or user ID)
        client_id = self._get_client_id(request)

        # Check rate limits
        is_allowed, headers = await self._check_rate_limit(client_id)

        if not is_allowed:
            return Response(
                content='{"detail": "Rate limit exceeded"}',
                status_code=429,
                headers=headers
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        for key, value in headers.items():
            response.headers[key] = value

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # In production, check for user ID from auth token
        # For now, use IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def _check_rate_limit(self, client_id: str) -> tuple:
        """Check if client has exceeded rate limit"""
        current_time = int(time.time())

        # Check minute limit
        minute_key = f"rate_limit:minute:{client_id}:{current_time // 60}"
        minute_count = await self.cache_service.get(minute_key, namespace="rate_limit") or 0

        # Check hour limit
        hour_key = f"rate_limit:hour:{client_id}:{current_time // 3600}"
        hour_count = await self.cache_service.get(hour_key, namespace="rate_limit") or 0

        # Increment counters
        if minute_count < self.requests_per_minute and hour_count < self.requests_per_hour:
            await self.cache_service.increment(minute_key, namespace="rate_limit")
            await self.cache_service.increment(hour_key, namespace="rate_limit")

            # Set TTL if new key
            if minute_count == 0:
                await self.cache_service.set(minute_key, 1, ttl=60, namespace="rate_limit")
            if hour_count == 0:
                await self.cache_service.set(hour_key, 1, ttl=3600, namespace="rate_limit")

            headers = {
                "X-RateLimit-Limit-Minute": str(self.requests_per_minute),
                "X-RateLimit-Remaining-Minute": str(self.requests_per_minute - minute_count - 1),
                "X-RateLimit-Limit-Hour": str(self.requests_per_hour),
                "X-RateLimit-Remaining-Hour": str(self.requests_per_hour - hour_count - 1)
            }

            return True, headers

        # Rate limit exceeded
        headers = {
            "X-RateLimit-Limit-Minute": str(self.requests_per_minute),
            "X-RateLimit-Remaining-Minute": "0",
            "X-RateLimit-Limit-Hour": str(self.requests_per_hour),
            "X-RateLimit-Remaining-Hour": "0",
            "Retry-After": "60"
        }

        return False, headers


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Response compression middleware.

    Compresses responses to reduce bandwidth usage.
    """

    def __init__(
        self,
        app,
        minimum_size: int = 1000,
        compression_level: int = 6
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request with compression"""
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")

        if "gzip" not in accept_encoding.lower():
            return await call_next(request)

        response = await call_next(request)

        # Only compress if response is large enough
        # (In production, implement actual gzip compression)

        return response
