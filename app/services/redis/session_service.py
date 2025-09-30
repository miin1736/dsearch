"""
Session Management Service using Redis
"""

import uuid
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from .redis_service import redis_service

logger = logging.getLogger("ds")


class SessionService:
    """Session management service using Redis."""

    def __init__(self, default_ttl: int = 86400):  # 24 hours default
        self.default_ttl = default_ttl
        self.redis = redis_service

    async def create_session(self, user_id: str, user_data: Dict[str, Any],
                           ttl: Optional[int] = None) -> str:
        """Create a new session."""
        try:
            session_id = str(uuid.uuid4())
            ttl = ttl or self.default_ttl

            session_data = {
                "user_id": user_id,
                "user_data": user_data,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat()
            }

            success = await self.redis.set(
                f"session:{session_id}",
                session_data,
                ex=ttl
            )

            if success:
                # Also maintain user -> session mapping
                await self.redis.set(
                    f"user_session:{user_id}",
                    session_id,
                    ex=ttl
                )

                logger.info(f"Created session {session_id} for user {user_id}")
                return session_id
            else:
                raise Exception("Failed to create session")

        except Exception as e:
            logger.error(f"Session creation error: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        try:
            session_data = await self.redis.get(f"session:{session_id}")

            if session_data:
                # Update last activity
                session_data["last_activity"] = datetime.utcnow().isoformat()
                await self.redis.set(f"session:{session_id}", session_data)

                return session_data

            return None

        except Exception as e:
            logger.error(f"Session get error: {e}")
            return None

    async def update_session(self, session_id: str, update_data: Dict[str, Any],
                           extend_ttl: bool = True) -> bool:
        """Update session data."""
        try:
            session_data = await self.redis.get(f"session:{session_id}")

            if not session_data:
                return False

            # Update data
            session_data.update(update_data)
            session_data["last_activity"] = datetime.utcnow().isoformat()

            # Set with or without extending TTL
            if extend_ttl:
                success = await self.redis.set(
                    f"session:{session_id}",
                    session_data,
                    ex=self.default_ttl
                )
            else:
                current_ttl = await self.redis.ttl(f"session:{session_id}")
                success = await self.redis.set(
                    f"session:{session_id}",
                    session_data,
                    ex=max(current_ttl, 60)  # At least 1 minute
                )

            return success

        except Exception as e:
            logger.error(f"Session update error: {e}")
            return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        try:
            # Get session data to find user_id
            session_data = await self.redis.get(f"session:{session_id}")

            # Delete session
            result = await self.redis.delete(f"session:{session_id}")

            # Delete user session mapping
            if session_data and "user_id" in session_data:
                await self.redis.delete(f"user_session:{session_data['user_id']}")

            logger.info(f"Deleted session {session_id}")
            return result > 0

        except Exception as e:
            logger.error(f"Session deletion error: {e}")
            return False

    async def get_user_session(self, user_id: str) -> Optional[str]:
        """Get active session ID for a user."""
        try:
            session_id = await self.redis.get(f"user_session:{user_id}")
            return session_id

        except Exception as e:
            logger.error(f"User session get error: {e}")
            return None

    async def extend_session(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """Extend session TTL."""
        try:
            ttl = ttl or self.default_ttl
            return await self.redis.expire(f"session:{session_id}", ttl)

        except Exception as e:
            logger.error(f"Session extension error: {e}")
            return False

    async def get_session_ttl(self, session_id: str) -> int:
        """Get remaining TTL for a session."""
        try:
            return await self.redis.ttl(f"session:{session_id}")

        except Exception as e:
            logger.error(f"Session TTL get error: {e}")
            return -1

    # User activity tracking
    async def track_user_activity(self, session_id: str, activity: str,
                                details: Optional[Dict[str, Any]] = None) -> bool:
        """Track user activity in session."""
        try:
            activity_data = {
                "activity": activity,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details or {}
            }

            # Add to activity list (keep last 100 activities)
            activity_key = f"session_activity:{session_id}"

            await self.redis.lpush(activity_key, activity_data)

            # Keep only last 100 activities
            client = self.redis.get_client()
            client.ltrim(activity_key, 0, 99)

            # Set TTL for activity log
            await self.redis.expire(activity_key, self.default_ttl)

            return True

        except Exception as e:
            logger.error(f"Activity tracking error: {e}")
            return False

    async def get_user_activities(self, session_id: str, limit: int = 20) -> list:
        """Get recent user activities."""
        try:
            activities = await self.redis.lrange(f"session_activity:{session_id}", 0, limit - 1)
            return activities

        except Exception as e:
            logger.error(f"Get activities error: {e}")
            return []

    # Search history management
    async def add_search_to_history(self, session_id: str, query: str,
                                  results_count: int, search_type: str = "text") -> bool:
        """Add search query to user history."""
        try:
            search_data = {
                "query": query,
                "results_count": results_count,
                "search_type": search_type,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Add to search history (keep last 50 searches)
            history_key = f"search_history:{session_id}"

            await self.redis.lpush(history_key, search_data)

            # Keep only last 50 searches
            client = self.redis.get_client()
            client.ltrim(history_key, 0, 49)

            # Set TTL
            await self.redis.expire(history_key, self.default_ttl)

            return True

        except Exception as e:
            logger.error(f"Search history error: {e}")
            return False

    async def get_search_history(self, session_id: str, limit: int = 10) -> list:
        """Get user's search history."""
        try:
            history = await self.redis.lrange(f"search_history:{session_id}", 0, limit - 1)
            return history

        except Exception as e:
            logger.error(f"Get search history error: {e}")
            return []

    async def clear_search_history(self, session_id: str) -> bool:
        """Clear user's search history."""
        try:
            result = await self.redis.delete(f"search_history:{session_id}")
            return result > 0

        except Exception as e:
            logger.error(f"Clear search history error: {e}")
            return False

    # Session statistics
    async def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        try:
            keys = await self.redis.keys("session:*")
            return len(keys)

        except Exception as e:
            logger.error(f"Active sessions count error: {e}")
            return 0

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (manual cleanup)."""
        try:
            session_keys = await self.redis.keys("session:*")
            expired_count = 0

            for key in session_keys:
                ttl = await self.redis.ttl(key)
                if ttl <= 0:  # Expired or no expiration set
                    session_id = key.replace("session:", "")
                    await self.delete_session(session_id)
                    expired_count += 1

            logger.info(f"Cleaned up {expired_count} expired sessions")
            return expired_count

        except Exception as e:
            logger.error(f"Session cleanup error: {e}")
            return 0

    # Health check
    async def health_check(self) -> dict:
        """Check session service health."""
        try:
            # Test session operations
            test_user_id = "health_check_user"
            test_data = {"test": "data"}

            # Create test session
            session_id = await self.create_session(test_user_id, test_data, ttl=10)

            # Get session
            retrieved_data = await self.get_session(session_id)

            # Delete test session
            await self.delete_session(session_id)

            if retrieved_data and retrieved_data["user_id"] == test_user_id:
                return {"status": "healthy", "message": "Session operations working"}
            else:
                return {"status": "unhealthy", "message": "Session operations failed"}

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Global instance
session_service = SessionService()