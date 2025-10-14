"""
Caching Service using RedisOperations Service
"""
from typing import Any, Optional, Callableimport redis
from functools import wrapsport Any, Optional, Dict, List, Union
arse import urlparse
from .redis_service import redis_service

logger = logging.getLogger("ds")config import settings


class CacheService:
    """Redis를 사용한 고수준 캐싱 서비스 클래스."""
class RedisService:
    def __init__(self, default_ttl: int = 3600):    """Redis 연결 및 기본 작업을 관리하는 서비스 클래스."""
        self.default_ttl = default_ttl

    async def get(self, key: str) -> Optional[Any]:        self._client: Optional[redis.Redis] = None
        """캐시에서 값을 가져옵니다."""
        try:
            return await redis_service.get(key)
        except Exception as e:        """Redis 클라이언트를 초기화합니다."""
            logger.error(f"Cache get failed for key {key}: {e}")
            return Noneings.REDIS_URL)
self._client = redis.Redis(
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값을 설정합니다."""
        ttl = ttl or self.default_ttl
        try:nt(url.path.lstrip('/')) if url.path else 0,
            return await redis_service.set(key, value, ex=ttl)
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return Falser(f"Redis client initialization failed: {e}")
            raise
    async def delete(self, key: str) -> bool:
        """캐시에서 키를 삭제합니다."""
        try: 반환합니다."""
            client = redis_service.get_client()        if self._client is None:
            return client.delete(key) > 0
        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            return Falsestr, Any]:
        """Redis 연결 상태를 확인합니다."""
    async def clear_pattern(self, pattern: str) -> int:
        """패턴에 맞는 키들을 삭제합니다."""
        try:lient.ping()
            client = redis_service.get_client()
            keys = client.keys(pattern)n as e:
            if keys:h check failed: {e}")
                return client.delete(*keys)            return {"status": "unhealthy", "error": str(e)}
            return 0
        except Exception as e:    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
            logger.error(f"Cache clear pattern failed for {pattern}: {e}")
            return 0
f.get_client()
# Global instance            return client.set(key, value, ex=ex)
cache_service = CacheService()