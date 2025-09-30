"""
Caching Service using Redis
"""

import hashlib
import pickle
from typing import Any, Optional, Callable
from functools import wraps
import logging

from .redis_service import redis_service

logger = logging.getLogger("ds")


class CacheService:
    """High-level caching service using Redis."""

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self.redis = redis_service

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        try:
            cached_value = await self.redis.get(f"cache:{key}")
            if cached_value is not None:
                # Try to unpickle if it's a complex object
                try:
                    return pickle.loads(cached_value.encode('latin1'))
                except:
                    return cached_value
            return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value with TTL."""
        try:
            ttl = ttl or self.default_ttl

            # Serialize complex objects
            if not isinstance(value, str):
                try:
                    value = pickle.dumps(value).decode('latin1')
                except:
                    value = str(value)

            return await self.redis.set(f"cache:{key}", value, ex=ttl)

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        try:
            result = await self.redis.delete(f"cache:{key}")
            return result > 0

        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all cache keys matching pattern."""
        try:
            keys = await self.redis.keys(f"cache:{pattern}")
            if keys:
                return await self.redis.delete(*keys)
            return 0

        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0

    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments."""
        # Create a string representation of arguments
        key_parts = [prefix]

        # Add positional arguments
        for arg in args:
            if hasattr(arg, '__dict__'):
                # For objects, use their dict representation
                key_parts.append(str(sorted(arg.__dict__.items())))
            else:
                key_parts.append(str(arg))

        # Add keyword arguments
        for k, v in sorted(kwargs.items()):
            if hasattr(v, '__dict__'):
                key_parts.append(f"{k}:{sorted(v.__dict__.items())}")
            else:
                key_parts.append(f"{k}:{v}")

        # Create hash of the combined key
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def cache_result(self, ttl: Optional[int] = None, key_prefix: str = "func"):
        """Decorator to cache function results."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self.generate_key(f"{key_prefix}:{func.__name__}", *args, **kwargs)

                # Try to get from cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                    return cached_result

                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl)

                logger.debug(f"Cache miss for {func.__name__}: {cache_key}")
                return result

            return wrapper
        return decorator

    # Search-specific caching methods
    async def cache_search_result(self, query_hash: str, result: Any, ttl: int = 300) -> bool:
        """Cache search results."""
        return await self.set(f"search:{query_hash}", result, ttl)

    async def get_cached_search_result(self, query_hash: str) -> Optional[Any]:
        """Get cached search results."""
        return await self.get(f"search:{query_hash}")

    async def cache_document(self, document_id: str, document: Any, ttl: int = 3600) -> bool:
        """Cache document data."""
        return await self.set(f"document:{document_id}", document, ttl)

    async def get_cached_document(self, document_id: str) -> Optional[Any]:
        """Get cached document data."""
        return await self.get(f"document:{document_id}")

    async def cache_user_session(self, session_id: str, session_data: Any, ttl: int = 86400) -> bool:
        """Cache user session data."""
        return await self.set(f"session:{session_id}", session_data, ttl)

    async def get_cached_user_session(self, session_id: str) -> Optional[Any]:
        """Get cached user session data."""
        return await self.get(f"session:{session_id}")

    async def cache_popular_queries(self, queries: list, ttl: int = 3600) -> bool:
        """Cache popular search queries."""
        return await self.set("popular_queries", queries, ttl)

    async def get_popular_queries(self) -> Optional[list]:
        """Get cached popular queries."""
        return await self.get("popular_queries")

    # Statistics caching
    async def increment_counter(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        try:
            client = self.redis.get_client()
            return client.incrby(f"counter:{key}", amount)

        except Exception as e:
            logger.error(f"Counter increment error: {e}")
            return 0

    async def get_counter(self, key: str) -> int:
        """Get counter value."""
        try:
            value = await self.redis.get(f"counter:{key}")
            return int(value) if value else 0

        except Exception as e:
            logger.error(f"Counter get error: {e}")
            return 0

    async def reset_counter(self, key: str) -> bool:
        """Reset counter to zero."""
        return await self.redis.delete(f"counter:{key}")

    # Health check
    async def health_check(self) -> dict:
        """Check cache service health."""
        try:
            # Test basic operations
            test_key = "health_check_test"
            test_value = "ok"

            # Set and get test value
            await self.set(test_key, test_value, ttl=10)
            retrieved_value = await self.get(test_key)
            await self.delete(test_key)

            if retrieved_value == test_value:
                return {"status": "healthy", "message": "Cache operations working"}
            else:
                return {"status": "unhealthy", "message": "Cache operations failed"}

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Global instance
cache_service = CacheService()