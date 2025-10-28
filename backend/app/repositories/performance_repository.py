"""
Performance & Optimization Repository
Sprint 22: Performance & Optimization

Repository layer for performance metrics, caching, and monitoring.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_, or_, desc
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import statistics

from app.models.performance import PerformanceMetric, CacheEntry
from app.schemas.performance import (
    PerformanceMetricCreate, PerformanceMetricQuery,
    CacheEntryCreate
)


class PerformanceRepository:
    """Repository for performance operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Performance Metric Operations
    # ========================================================================

    async def record_metric(
        self,
        metric_data: PerformanceMetricCreate
    ) -> PerformanceMetric:
        """Record a performance metric"""
        metric = PerformanceMetric(
            metric_type=metric_data.metric_type,
            metric_value=metric_data.metric_value,
            tags=metric_data.tags,
            recorded_at=datetime.utcnow()
        )

        self.db.add(metric)
        await self.db.flush()
        return metric

    async def get_metric_by_id(
        self,
        metric_id: UUID
    ) -> Optional[PerformanceMetric]:
        """Get metric by ID"""
        stmt = select(PerformanceMetric).where(PerformanceMetric.id == metric_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def query_metrics(
        self,
        query: PerformanceMetricQuery
    ) -> List[PerformanceMetric]:
        """Query performance metrics with filters"""
        stmt = select(PerformanceMetric)

        # Apply filters
        filters = []
        if query.metric_type:
            filters.append(PerformanceMetric.metric_type == query.metric_type)
        if query.start_date:
            filters.append(PerformanceMetric.recorded_at >= query.start_date)
        if query.end_date:
            filters.append(PerformanceMetric.recorded_at <= query.end_date)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Order by recorded_at descending
        stmt = stmt.order_by(desc(PerformanceMetric.recorded_at))

        # Apply limit
        stmt = stmt.limit(query.limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_metric_stats(
        self,
        metric_type: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get aggregated statistics for a metric type"""
        stmt = select(PerformanceMetric).where(
            and_(
                PerformanceMetric.metric_type == metric_type,
                PerformanceMetric.recorded_at >= start_date,
                PerformanceMetric.recorded_at <= end_date
            )
        )

        result = await self.db.execute(stmt)
        metrics = result.scalars().all()

        if not metrics:
            return {
                "count": 0,
                "avg": 0,
                "min": 0,
                "max": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0
            }

        values = [m.metric_value for m in metrics]
        values_sorted = sorted(values)

        return {
            "count": len(values),
            "avg": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "p50": self._percentile(values_sorted, 50),
            "p95": self._percentile(values_sorted, 95),
            "p99": self._percentile(values_sorted, 99)
        }

    async def get_metric_types(self) -> List[str]:
        """Get all unique metric types"""
        stmt = select(PerformanceMetric.metric_type).distinct()
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]

    async def delete_old_metrics(
        self,
        days_to_keep: int = 30
    ) -> int:
        """Delete metrics older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        stmt = delete(PerformanceMetric).where(
            PerformanceMetric.recorded_at < cutoff_date
        )

        result = await self.db.execute(stmt)
        return result.rowcount

    async def get_recent_metrics_by_type(
        self,
        metric_type: str,
        hours_back: int = 24,
        limit: int = 1000
    ) -> List[PerformanceMetric]:
        """Get recent metrics for a specific type"""
        since_date = datetime.utcnow() - timedelta(hours=hours_back)

        stmt = select(PerformanceMetric).where(
            and_(
                PerformanceMetric.metric_type == metric_type,
                PerformanceMetric.recorded_at >= since_date
            )
        ).order_by(desc(PerformanceMetric.recorded_at)).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ========================================================================
    # Cache Entry Operations
    # ========================================================================

    async def create_cache_entry(
        self,
        cache_data: CacheEntryCreate
    ) -> CacheEntry:
        """Create a cache entry in database"""
        expires_at = datetime.utcnow() + timedelta(seconds=cache_data.ttl)

        cache_entry = CacheEntry(
            cache_key=cache_data.cache_key,
            cache_value=cache_data.cache_value,
            ttl=cache_data.ttl,
            hit_count=0,
            created_at=datetime.utcnow(),
            expires_at=expires_at
        )

        self.db.add(cache_entry)
        await self.db.flush()
        return cache_entry

    async def get_cache_entry(
        self,
        cache_key: str
    ) -> Optional[CacheEntry]:
        """Get cache entry by key"""
        stmt = select(CacheEntry).where(
            and_(
                CacheEntry.cache_key == cache_key,
                CacheEntry.expires_at > datetime.utcnow()
            )
        )

        result = await self.db.execute(stmt)
        entry = result.scalar_one_or_none()

        # Increment hit count
        if entry:
            entry.hit_count += 1

        return entry

    async def delete_cache_entry(
        self,
        cache_key: str
    ) -> bool:
        """Delete cache entry by key"""
        stmt = delete(CacheEntry).where(CacheEntry.cache_key == cache_key)
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def clear_all_cache(self) -> int:
        """Clear all cache entries"""
        stmt = delete(CacheEntry)
        result = await self.db.execute(stmt)
        return result.rowcount

    async def clear_expired_cache(self) -> int:
        """Clear expired cache entries"""
        stmt = delete(CacheEntry).where(
            CacheEntry.expires_at <= datetime.utcnow()
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        # Total entries
        total_stmt = select(func.count()).select_from(CacheEntry).where(
            CacheEntry.expires_at > datetime.utcnow()
        )
        total_result = await self.db.execute(total_stmt)
        total_entries = total_result.scalar() or 0

        # Expired entries
        expired_stmt = select(func.count()).select_from(CacheEntry).where(
            CacheEntry.expires_at <= datetime.utcnow()
        )
        expired_result = await self.db.execute(expired_stmt)
        expired_entries = expired_result.scalar() or 0

        # Total hits
        hits_stmt = select(func.sum(CacheEntry.hit_count)).select_from(CacheEntry)
        hits_result = await self.db.execute(hits_stmt)
        total_hits = hits_result.scalar() or 0

        # Most accessed keys
        most_accessed_stmt = select(
            CacheEntry.cache_key,
            CacheEntry.hit_count
        ).where(
            CacheEntry.expires_at > datetime.utcnow()
        ).order_by(desc(CacheEntry.hit_count)).limit(10)

        most_accessed_result = await self.db.execute(most_accessed_stmt)
        most_accessed_keys = [
            {"key": row[0], "hits": row[1]}
            for row in most_accessed_result.all()
        ]

        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "total_hits": total_hits,
            "most_accessed_keys": most_accessed_keys
        }

    async def get_cache_keys_by_pattern(
        self,
        pattern: str
    ) -> List[str]:
        """Get cache keys matching a pattern"""
        # Convert pattern to SQL LIKE pattern
        sql_pattern = pattern.replace('*', '%')

        stmt = select(CacheEntry.cache_key).where(
            and_(
                CacheEntry.cache_key.like(sql_pattern),
                CacheEntry.expires_at > datetime.utcnow()
            )
        )

        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]

    # ========================================================================
    # Analytics & Aggregations
    # ========================================================================

    async def get_latency_by_endpoint(
        self,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """Get latency breakdown by endpoint"""
        since_date = datetime.utcnow() - timedelta(hours=hours_back)

        stmt = select(PerformanceMetric).where(
            and_(
                PerformanceMetric.metric_type == 'api_latency',
                PerformanceMetric.recorded_at >= since_date
            )
        )

        result = await self.db.execute(stmt)
        metrics = result.scalars().all()

        # Group by endpoint
        endpoint_data = {}
        for metric in metrics:
            if not metric.tags or 'endpoint' not in metric.tags:
                continue

            endpoint = metric.tags['endpoint']
            method = metric.tags.get('method', 'GET')
            key = f"{method} {endpoint}"

            if key not in endpoint_data:
                endpoint_data[key] = {
                    "endpoint": endpoint,
                    "method": method,
                    "values": [],
                    "errors": 0
                }

            endpoint_data[key]["values"].append(metric.metric_value)
            if metric.tags.get('error'):
                endpoint_data[key]["errors"] += 1

        # Calculate statistics for each endpoint
        results = []
        for key, data in endpoint_data.items():
            values = sorted(data["values"])
            request_count = len(values)
            error_count = data["errors"]

            results.append({
                "endpoint": data["endpoint"],
                "method": data["method"],
                "avg_latency_ms": statistics.mean(values),
                "p50_latency_ms": self._percentile(values, 50),
                "p95_latency_ms": self._percentile(values, 95),
                "p99_latency_ms": self._percentile(values, 99),
                "request_count": request_count,
                "error_count": error_count,
                "error_rate": (error_count / request_count * 100) if request_count > 0 else 0
            })

        return sorted(results, key=lambda x: x["avg_latency_ms"], reverse=True)

    async def get_throughput_stats(
        self,
        hours_back: int = 1
    ) -> Dict[str, Any]:
        """Get throughput statistics"""
        since_date = datetime.utcnow() - timedelta(hours=hours_back)

        stmt = select(PerformanceMetric).where(
            and_(
                PerformanceMetric.metric_type == 'request_count',
                PerformanceMetric.recorded_at >= since_date
            )
        )

        result = await self.db.execute(stmt)
        metrics = result.scalars().all()

        total_requests = sum(m.metric_value for m in metrics)
        duration_hours = hours_back

        return {
            "timestamp": datetime.utcnow(),
            "requests_per_second": total_requests / (duration_hours * 3600) if duration_hours > 0 else 0,
            "requests_per_minute": total_requests / (duration_hours * 60) if duration_hours > 0 else 0,
            "requests_per_hour": total_requests / duration_hours if duration_hours > 0 else 0,
            "total_requests": total_requests
        }

    async def get_database_query_stats(
        self,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """Get database query statistics"""
        since_date = datetime.utcnow() - timedelta(hours=hours_back)

        stmt = select(PerformanceMetric).where(
            and_(
                PerformanceMetric.metric_type == 'db_query_time',
                PerformanceMetric.recorded_at >= since_date
            )
        )

        result = await self.db.execute(stmt)
        metrics = result.scalars().all()

        # Group by query type and table
        query_data = {}
        for metric in metrics:
            if not metric.tags or 'table' not in metric.tags:
                continue

            table = metric.tags['table']
            query_type = metric.tags.get('type', 'SELECT')
            key = f"{query_type}:{table}"

            if key not in query_data:
                query_data[key] = {
                    "query_type": query_type,
                    "table_name": table,
                    "values": []
                }

            query_data[key]["values"].append(metric.metric_value)

        # Calculate statistics
        results = []
        for key, data in query_data.items():
            values = data["values"]
            slow_threshold = 50  # ms

            results.append({
                "query_type": data["query_type"],
                "table_name": data["table_name"],
                "avg_execution_time_ms": statistics.mean(values),
                "min_execution_time_ms": min(values),
                "max_execution_time_ms": max(values),
                "total_executions": len(values),
                "slow_query_count": sum(1 for v in values if v > slow_threshold)
            })

        return sorted(results, key=lambda x: x["avg_execution_time_ms"], reverse=True)

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values"""
        if not sorted_values:
            return 0.0

        index = (len(sorted_values) - 1) * percentile / 100
        floor = int(index)
        ceil = floor + 1

        if ceil >= len(sorted_values):
            return sorted_values[floor]

        # Linear interpolation
        fraction = index - floor
        return sorted_values[floor] + (sorted_values[ceil] - sorted_values[floor]) * fraction

    async def get_metric_count_by_type(
        self,
        hours_back: int = 24
    ) -> Dict[str, int]:
        """Get count of metrics by type"""
        since_date = datetime.utcnow() - timedelta(hours=hours_back)

        stmt = select(
            PerformanceMetric.metric_type,
            func.count(PerformanceMetric.id)
        ).where(
            PerformanceMetric.recorded_at >= since_date
        ).group_by(PerformanceMetric.metric_type)

        result = await self.db.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
