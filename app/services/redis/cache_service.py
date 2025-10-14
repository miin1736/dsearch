"""
Caching Service using Redis
"""
from typing import Any, Optional, Callable
from functools import wraps

from .redis_service import redis_service

logger = logging.getLogger("ds")


class CacheService:
    """Redis를 사용한 고수준 캐싱 서비스 클래스."""

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl

    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값을 가져옵니다."""
        try:
            return await redis_service.get(key)
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값을 설정합니다."""
        ttl = ttl or self.default_ttl
        try:
            return await redis_service.set(key, value, ex=ttl)
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """캐시에서 키를 삭제합니다."""
        try:
            client = redis_service.get_client()
            return client.delete(key) > 0
        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """패턴에 맞는 키들을 삭제합니다."""
        try:
            client = redis_service.get_client()
            keys = client.keys(pattern)
            if keys:
                return client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern failed for {pattern}: {e}")
            return 0

# Global instance
cache_service = CacheService()