"""
Redis Connection and Basic Operations Service
"""

import logging  # 추가: logging 모듈 import 
import redis
from typing import Any, Optional, Dict, List, Union
from urllib.parse import urlparse

from app.core.config import settings

logger = logging.getLogger("ds")


class RedisService:
    """Redis 연결 및 기본 작업을 관리하는 서비스 클래스."""

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._initialize_client()

    def _initialize_client(self):
        """Redis 클라이언트를 초기화합니다."""
        try:
            url = urlparse(settings.REDIS_URL)
            self._client = redis.Redis(
                host=url.hostname,
                port=url.port,
                password=url.password,
                db=int(url.path.lstrip('/')) if url.path else 0,
                decode_responses=True
            )
        except Exception as e:
            logger.error(f"Redis client initialization failed: {e}")
            raise

    def get_client(self) -> redis.Redis:
        """Redis 클라이언트를 반환합니다."""
        if self._client is None:
            raise RuntimeError("Redis client not initialized")
        return self._client

    async def health_check(self) -> Dict[str, Any]:
        """Redis 연결 상태를 확인합니다."""
        try:
            client = self.get_client()
            pong = client.ping()
            return {"status": "healthy", "ping": pong}
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """키-값을 설정합니다."""
        try:
            client = self.get_client()
            return client.set(key, value, ex=ex)
        except Exception as e:
            logger.error(f"Redis set failed for key {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """키에 해당하는 값을 가져옵니다."""
        try:
            client = self.get_client()
            return client.get(key)
        except Exception as e:
            logger.error(f"Redis get failed for key {key}: {e}")
            return None

# Global instance
redis_service = RedisService()