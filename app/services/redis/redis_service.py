"""
Redis Connection and Basic Operations Service
"""

import redis
import json
from typing import Any, Optional, Dict, List, Union
from urllib.parse import urlparse
import logging

from app.core.config import settings

logger = logging.getLogger("ds")


class RedisService:
    """Redis connection and basic operations service."""

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None

    def get_client(self) -> redis.Redis:
        """Get Redis client instance."""
        if not self._client:
            try:
                # Parse Redis URL
                parsed_url = urlparse(settings.REDIS_URL)

                # Create connection pool
                self._pool = redis.ConnectionPool(
                    host=parsed_url.hostname or 'localhost',
                    port=parsed_url.port or 6379,
                    db=int(parsed_url.path.lstrip('/')) if parsed_url.path else 0,
                    password=settings.REDIS_PASSWORD or parsed_url.password,
                    decode_responses=True,
                    max_connections=20,
                    retry_on_timeout=True
                )

                # Create Redis client
                self._client = redis.Redis(connection_pool=self._pool)

                # Test connection
                self._client.ping()
                logger.info("Redis connection established")

            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

        return self._client

    async def health_check(self) -> Dict[str, Any]:
        """Check Redis connection health."""
        try:
            client = self.get_client()

            # Test basic operations
            client.ping()
            info = client.info()

            return {
                "status": "healthy",
                "version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses")
            }

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    # String operations
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a key-value pair with optional expiration."""
        try:
            client = self.get_client()

            # Serialize value if it's not a string
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)

            result = client.set(key, value, ex=ex)
            return bool(result)

        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        try:
            client = self.get_client()
            value = client.get(key)

            if value is None:
                return None

            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        try:
            client = self.get_client()
            return client.delete(*keys)

        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return 0

    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        try:
            client = self.get_client()
            return client.exists(*keys)

        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return 0

    async def expire(self, key: str, time: int) -> bool:
        """Set expiration time for a key."""
        try:
            client = self.get_client()
            return bool(client.expire(key, time))

        except Exception as e:
            logger.error(f"Redis expire error: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """Get time to live for a key."""
        try:
            client = self.get_client()
            return client.ttl(key)

        except Exception as e:
            logger.error(f"Redis ttl error: {e}")
            return -1

    # Hash operations
    async def hset(self, name: str, key: str, value: Any) -> int:
        """Set field in hash."""
        try:
            client = self.get_client()

            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)

            return client.hset(name, key, value)

        except Exception as e:
            logger.error(f"Redis hset error: {e}")
            return 0

    async def hget(self, name: str, key: str) -> Optional[Any]:
        """Get field from hash."""
        try:
            client = self.get_client()
            value = client.hget(name, key)

            if value is None:
                return None

            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"Redis hget error: {e}")
            return None

    async def hgetall(self, name: str) -> Dict[str, Any]:
        """Get all fields from hash."""
        try:
            client = self.get_client()
            result = client.hgetall(name)

            # Try to deserialize JSON values
            for key, value in result.items():
                try:
                    result[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass

            return result

        except Exception as e:
            logger.error(f"Redis hgetall error: {e}")
            return {}

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete fields from hash."""
        try:
            client = self.get_client()
            return client.hdel(name, *keys)

        except Exception as e:
            logger.error(f"Redis hdel error: {e}")
            return 0

    # List operations
    async def lpush(self, name: str, *values: Any) -> int:
        """Push values to the left of a list."""
        try:
            client = self.get_client()

            # Serialize non-string values
            serialized_values = []
            for value in values:
                if not isinstance(value, str):
                    value = json.dumps(value, ensure_ascii=False)
                serialized_values.append(value)

            return client.lpush(name, *serialized_values)

        except Exception as e:
            logger.error(f"Redis lpush error: {e}")
            return 0

    async def rpush(self, name: str, *values: Any) -> int:
        """Push values to the right of a list."""
        try:
            client = self.get_client()

            # Serialize non-string values
            serialized_values = []
            for value in values:
                if not isinstance(value, str):
                    value = json.dumps(value, ensure_ascii=False)
                serialized_values.append(value)

            return client.rpush(name, *serialized_values)

        except Exception as e:
            logger.error(f"Redis rpush error: {e}")
            return 0

    async def lpop(self, name: str) -> Optional[Any]:
        """Pop value from the left of a list."""
        try:
            client = self.get_client()
            value = client.lpop(name)

            if value is None:
                return None

            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"Redis lpop error: {e}")
            return None

    async def rpop(self, name: str) -> Optional[Any]:
        """Pop value from the right of a list."""
        try:
            client = self.get_client()
            value = client.rpop(name)

            if value is None:
                return None

            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"Redis rpop error: {e}")
            return None

    async def lrange(self, name: str, start: int, end: int) -> List[Any]:
        """Get a range of elements from a list."""
        try:
            client = self.get_client()
            values = client.lrange(name, start, end)

            # Try to deserialize JSON values
            result = []
            for value in values:
                try:
                    result.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    result.append(value)

            return result

        except Exception as e:
            logger.error(f"Redis lrange error: {e}")
            return []

    # Set operations
    async def sadd(self, name: str, *values: Any) -> int:
        """Add values to a set."""
        try:
            client = self.get_client()

            # Serialize non-string values
            serialized_values = []
            for value in values:
                if not isinstance(value, str):
                    value = json.dumps(value, ensure_ascii=False)
                serialized_values.append(value)

            return client.sadd(name, *serialized_values)

        except Exception as e:
            logger.error(f"Redis sadd error: {e}")
            return 0

    async def smembers(self, name: str) -> set:
        """Get all members of a set."""
        try:
            client = self.get_client()
            values = client.smembers(name)

            # Try to deserialize JSON values
            result = set()
            for value in values:
                try:
                    result.add(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    result.add(value)

            return result

        except Exception as e:
            logger.error(f"Redis smembers error: {e}")
            return set()

    # Utility operations
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        try:
            client = self.get_client()
            return client.keys(pattern)

        except Exception as e:
            logger.error(f"Redis keys error: {e}")
            return []

    async def flushdb(self) -> bool:
        """Clear current database."""
        try:
            client = self.get_client()
            return bool(client.flushdb())

        except Exception as e:
            logger.error(f"Redis flushdb error: {e}")
            return False

    async def info(self) -> Dict[str, Any]:
        """Get Redis server information."""
        try:
            client = self.get_client()
            return client.info()

        except Exception as e:
            logger.error(f"Redis info error: {e}")
            return {}


# Global instance
redis_service = RedisService()