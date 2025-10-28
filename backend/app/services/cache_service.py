"""
Redis Caching Service
Sprint 22: Performance & Optimization

Multi-tier caching service with Redis integration.
"""

import json
import hashlib
from typing import Optional, Any, Dict, List
from datetime import timedelta
import asyncio
from functools import wraps

# Note: In production, use redis.asyncio
# For now, we'll create a mock Redis client that can be swapped out
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisCacheService:
    """
    Redis caching service with multi-tier strategy.

    Caching Tiers:
    - L1: Application cache (LRU, in-memory, 1000 items)
    - L2: Redis cache (distributed, 10GB)
    - L3: CDN cache (handled by CDN provider)
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_ttl: int = 3600,
        l1_max_size: int = 1000
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.l1_max_size = l1_max_size

        # L1 Cache: In-memory LRU cache
        self.l1_cache: Dict[str, Any] = {}
        self.l1_access_order: List[str] = []

        # Redis client (L2 Cache)
        self.redis_client: Optional[Any] = None

        # Cache statistics
        self.stats = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "total_gets": 0,
            "total_sets": 0
        }

    async def connect(self):
        """Connect to Redis"""
        if REDIS_AVAILABLE:
            try:
                self.redis_client = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis_client.ping()
                print("✅ Connected to Redis")
            except Exception as e:
                print(f"⚠️ Redis connection failed: {e}. Using L1 cache only.")
                self.redis_client = None
        else:
            print("⚠️ Redis not available. Using L1 cache only.")

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            print("✅ Disconnected from Redis")

    async def get(
        self,
        key: str,
        namespace: str = "default"
    ) -> Optional[Any]:
        """
        Get value from cache (L1 → L2).

        Args:
            key: Cache key
            namespace: Cache namespace for key isolation

        Returns:
            Cached value or None if not found
        """
        self.stats["total_gets"] += 1
        full_key = self._make_key(key, namespace)

        # L1 Cache lookup
        if full_key in self.l1_cache:
            self._update_l1_access(full_key)
            self.stats["l1_hits"] += 1
            return self.l1_cache[full_key]

        self.stats["l1_misses"] += 1

        # L2 Cache lookup (Redis)
        if self.redis_client:
            try:
                value = await self.redis_client.get(full_key)
                if value is not None:
                    self.stats["l2_hits"] += 1
                    # Deserialize and populate L1 cache
                    deserialized_value = self._deserialize(value)
                    self._set_l1(full_key, deserialized_value)
                    return deserialized_value
                else:
                    self.stats["l2_misses"] += 1
            except Exception as e:
                print(f"Redis GET error: {e}")
                self.stats["l2_misses"] += 1

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "default"
    ) -> bool:
        """
        Set value in cache (L1 + L2).

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: self.default_ttl)
            namespace: Cache namespace for key isolation

        Returns:
            True if successful
        """
        self.stats["total_sets"] += 1
        full_key = self._make_key(key, namespace)
        ttl = ttl or self.default_ttl

        # Set in L1 cache
        self._set_l1(full_key, value)

        # Set in L2 cache (Redis)
        if self.redis_client:
            try:
                serialized_value = self._serialize(value)
                await self.redis_client.setex(
                    full_key,
                    ttl,
                    serialized_value
                )
                return True
            except Exception as e:
                print(f"Redis SET error: {e}")
                return False

        return True  # L1 cache succeeded

    async def delete(
        self,
        key: str,
        namespace: str = "default"
    ) -> bool:
        """
        Delete value from cache (L1 + L2).

        Args:
            key: Cache key
            namespace: Cache namespace

        Returns:
            True if deleted
        """
        full_key = self._make_key(key, namespace)

        # Delete from L1
        if full_key in self.l1_cache:
            del self.l1_cache[full_key]
            if full_key in self.l1_access_order:
                self.l1_access_order.remove(full_key)

        # Delete from L2 (Redis)
        if self.redis_client:
            try:
                await self.redis_client.delete(full_key)
                return True
            except Exception as e:
                print(f"Redis DELETE error: {e}")
                return False

        return True

    async def clear(self, namespace: str = "default") -> bool:
        """
        Clear all cache entries in namespace.

        Args:
            namespace: Cache namespace to clear

        Returns:
            True if successful
        """
        # Clear L1 cache for namespace
        keys_to_delete = [k for k in self.l1_cache.keys() if k.startswith(f"{namespace}:")]
        for key in keys_to_delete:
            del self.l1_cache[key]
            if key in self.l1_access_order:
                self.l1_access_order.remove(key)

        # Clear L2 cache (Redis) for namespace
        if self.redis_client:
            try:
                pattern = f"{namespace}:*"
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                return True
            except Exception as e:
                print(f"Redis CLEAR error: {e}")
                return False

        return True

    async def exists(
        self,
        key: str,
        namespace: str = "default"
    ) -> bool:
        """Check if key exists in cache"""
        full_key = self._make_key(key, namespace)

        # Check L1
        if full_key in self.l1_cache:
            return True

        # Check L2 (Redis)
        if self.redis_client:
            try:
                exists = await self.redis_client.exists(full_key)
                return bool(exists)
            except Exception as e:
                print(f"Redis EXISTS error: {e}")
                return False

        return False

    async def get_many(
        self,
        keys: List[str],
        namespace: str = "default"
    ) -> Dict[str, Any]:
        """Get multiple values from cache"""
        result = {}

        for key in keys:
            value = await self.get(key, namespace)
            if value is not None:
                result[key] = value

        return result

    async def set_many(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None,
        namespace: str = "default"
    ) -> bool:
        """Set multiple values in cache"""
        for key, value in items.items():
            await self.set(key, value, ttl, namespace)
        return True

    async def increment(
        self,
        key: str,
        amount: int = 1,
        namespace: str = "default"
    ) -> int:
        """Increment a counter in cache"""
        full_key = self._make_key(key, namespace)

        if self.redis_client:
            try:
                return await self.redis_client.incrby(full_key, amount)
            except Exception as e:
                print(f"Redis INCR error: {e}")

        # Fallback to L1 cache
        current = self.l1_cache.get(full_key, 0)
        new_value = int(current) + amount
        self._set_l1(full_key, new_value)
        return new_value

    async def decrement(
        self,
        key: str,
        amount: int = 1,
        namespace: str = "default"
    ) -> int:
        """Decrement a counter in cache"""
        return await self.increment(key, -amount, namespace)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats["total_gets"]
        l1_hit_rate = (
            self.stats["l1_hits"] / total_requests * 100
            if total_requests > 0 else 0
        )
        l2_hit_rate = (
            self.stats["l2_hits"] / total_requests * 100
            if total_requests > 0 else 0
        )
        combined_hit_rate = (
            (self.stats["l1_hits"] + self.stats["l2_hits"]) / total_requests * 100
            if total_requests > 0 else 0
        )

        return {
            "l1_size": len(self.l1_cache),
            "l1_max_size": self.l1_max_size,
            "l1_hits": self.stats["l1_hits"],
            "l1_misses": self.stats["l1_misses"],
            "l1_hit_rate": l1_hit_rate,
            "l2_hits": self.stats["l2_hits"],
            "l2_misses": self.stats["l2_misses"],
            "l2_hit_rate": l2_hit_rate,
            "combined_hit_rate": combined_hit_rate,
            "total_gets": self.stats["total_gets"],
            "total_sets": self.stats["total_sets"],
            "redis_connected": self.redis_client is not None
        }

    def reset_stats(self):
        """Reset cache statistics"""
        self.stats = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "total_gets": 0,
            "total_sets": 0
        }

    # ========================================================================
    # L1 Cache Management (LRU)
    # ========================================================================

    def _set_l1(self, key: str, value: Any):
        """Set value in L1 cache with LRU eviction"""
        # Add to cache
        self.l1_cache[key] = value

        # Update access order
        if key in self.l1_access_order:
            self.l1_access_order.remove(key)
        self.l1_access_order.append(key)

        # Evict LRU item if cache is full
        if len(self.l1_cache) > self.l1_max_size:
            lru_key = self.l1_access_order.pop(0)
            del self.l1_cache[lru_key]

    def _update_l1_access(self, key: str):
        """Update L1 access order (move to end)"""
        if key in self.l1_access_order:
            self.l1_access_order.remove(key)
            self.l1_access_order.append(key)

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _make_key(self, key: str, namespace: str) -> str:
        """Create namespaced cache key"""
        return f"{namespace}:{key}"

    def _serialize(self, value: Any) -> str:
        """Serialize value for storage"""
        return json.dumps(value)

    def _deserialize(self, value: str) -> Any:
        """Deserialize value from storage"""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """
        Generate cache key from arguments.

        Useful for function result caching.
        """
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_string = ":".join(key_parts)

        # Hash long keys
        if len(key_string) > 200:
            return hashlib.md5(key_string.encode()).hexdigest()

        return key_string


# ============================================================================
# Cache Decorators
# ============================================================================

def cached(
    ttl: int = 3600,
    namespace: str = "default",
    key_prefix: str = ""
):
    """
    Decorator for caching function results.

    Usage:
        @cached(ttl=300, namespace="api", key_prefix="user")
        async def get_user(user_id: str):
            # Expensive operation
            return user_data
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache service from first argument (usually self)
            cache_service = None
            if args and hasattr(args[0], 'cache_service'):
                cache_service = args[0].cache_service

            if not cache_service:
                # No cache service available, execute function
                return await func(*args, **kwargs)

            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{RedisCacheService.generate_key(*args[1:], **kwargs)}"

            # Try to get from cache
            cached_result = await cache_service.get(cache_key, namespace)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, ttl, namespace)

            return result

        return wrapper
    return decorator


# ============================================================================
# Global Cache Service Instance
# ============================================================================

# This will be initialized during application startup
cache_service: Optional[RedisCacheService] = None


async def get_cache_service() -> RedisCacheService:
    """Dependency injection for cache service"""
    global cache_service

    if cache_service is None:
        cache_service = RedisCacheService()
        await cache_service.connect()

    return cache_service


async def init_cache_service(redis_url: str = "redis://localhost:6379"):
    """Initialize global cache service"""
    global cache_service

    cache_service = RedisCacheService(redis_url=redis_url)
    await cache_service.connect()

    return cache_service


async def close_cache_service():
    """Close global cache service"""
    global cache_service

    if cache_service:
        await cache_service.disconnect()
        cache_service = None
