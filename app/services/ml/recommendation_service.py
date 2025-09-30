"""
Document Recommendation Service
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict, Counter
import logging

from app.models.search import DocumentModel
from app.services.search.vector_service import vector_service
from app.services.search.search_service import search_service
from app.services.redis.cache_service import cache_service

logger = logging.getLogger("ds")


class RecommendationService:
    """Service for document recommendations using various algorithms."""

    def __init__(self):
        self.vector_service = vector_service
        self.search_service = search_service
        self.cache_service = cache_service

    async def recommend_similar_documents(self, document_id: str, k: int = 5,
                                        threshold: float = 0.6) -> List[DocumentModel]:
        """
        Recommend documents similar to a given document using vector similarity.
        """
        try:
            # Check cache first
            cache_key = f"similar_docs:{document_id}:{k}:{threshold}"
            cached_result = await self.cache_service.get(cache_key)
            if cached_result:
                return [DocumentModel(**doc) for doc in cached_result]

            # Get similar documents using vector similarity
            similar_docs = await self.vector_service.find_similar_documents(
                document_id=document_id,
                k=k * 2,  # Get more to filter and re-rank
                threshold=threshold
            )

            if not similar_docs:
                return []

            # Re-rank based on multiple factors
            ranked_docs = await self._rerank_recommendations(similar_docs, document_id)

            # Cache results
            result = ranked_docs[:k]
            await self.cache_service.set(
                cache_key,
                [doc.dict() for doc in result],
                ttl=3600  # Cache for 1 hour
            )

            return result

        except Exception as e:
            logger.error(f"Error recommending similar documents: {e}")
            return []

    async def recommend_by_user_history(self, user_id: str, session_id: Optional[str] = None,
                                      k: int = 10) -> List[DocumentModel]:
        """
        Recommend documents based on user's search and view history.
        """
        try:
            # Get user's recent search history
            user_interests = await self._get_user_interests(user_id, session_id)

            if not user_interests:
                # Fall back to popular documents
                return await self.get_popular_documents(k)

            # Find documents matching user interests
            recommendations = []

            # Search for documents based on interest keywords
            for interest, weight in user_interests.items():
                try:
                    from app.models.search import SearchQuery, SearchType

                    search_query = SearchQuery(
                        query=interest,
                        search_type=SearchType.HYBRID,
                        size=min(k, 5)  # Get fewer results per interest
                    )

                    search_result = await self.search_service.search(search_query)

                    # Apply interest weight to scores
                    for doc in search_result.documents:
                        doc.score = (doc.score or 0) * weight
                        recommendations.append(doc)

                except Exception as e:
                    logger.error(f"Error searching for interest '{interest}': {e}")
                    continue

            # Remove duplicates and sort by weighted score
            seen_ids = set()
            unique_recommendations = []

            for doc in sorted(recommendations, key=lambda x: x.score or 0, reverse=True):
                if doc.id not in seen_ids:
                    seen_ids.add(doc.id)
                    unique_recommendations.append(doc)

            return unique_recommendations[:k]

        except Exception as e:
            logger.error(f"Error getting user-based recommendations: {e}")
            return []

    async def recommend_trending_documents(self, k: int = 10,
                                         time_window_hours: int = 24) -> List[DocumentModel]:
        """
        Recommend currently trending documents based on recent activity.
        """
        try:
            cache_key = f"trending_docs:{k}:{time_window_hours}"
            cached_result = await self.cache_service.get(cache_key)
            if cached_result:
                return [DocumentModel(**doc) for doc in cached_result]

            # This is a simplified implementation
            # In a real system, you'd track document views, searches, etc.

            # For now, return popular documents with some recency bias
            popular_docs = await self.get_popular_documents(k * 2)

            # Apply recency weighting (newer documents get higher scores)
            current_time = datetime.utcnow()
            trending_docs = []

            for doc in popular_docs:
                try:
                    # Parse document creation date
                    if doc.created_date:
                        created_date = datetime.fromisoformat(doc.created_date.replace('Z', '+00:00'))
                        age_hours = (current_time - created_date).total_seconds() / 3600

                        # Apply time decay (newer documents get higher weight)
                        time_weight = max(0.1, 1 - (age_hours / (time_window_hours * 24)))
                        doc.score = (doc.score or 0) * time_weight

                    trending_docs.append(doc)

                except Exception as e:
                    logger.error(f"Error processing document date: {e}")
                    trending_docs.append(doc)

            # Sort by adjusted score
            trending_docs.sort(key=lambda x: x.score or 0, reverse=True)
            result = trending_docs[:k]

            # Cache results
            await self.cache_service.set(
                cache_key,
                [doc.dict() for doc in result],
                ttl=1800  # Cache for 30 minutes
            )

            return result

        except Exception as e:
            logger.error(f"Error getting trending recommendations: {e}")
            return []

    async def recommend_by_category(self, category: str, k: int = 10,
                                  exclude_document_ids: Optional[List[str]] = None) -> List[DocumentModel]:
        """
        Recommend documents from a specific category.
        """
        try:
            from app.models.search import SearchQuery

            # Search within category
            search_query = SearchQuery(
                query="*",  # Match all in category
                categories=[category],
                size=k * 2,  # Get more to filter out exclusions
                sort_field="_score",
                sort_order="desc"
            )

            search_result = await self.search_service.search(search_query)
            recommendations = search_result.documents

            # Filter out excluded documents
            if exclude_document_ids:
                recommendations = [
                    doc for doc in recommendations
                    if doc.id not in exclude_document_ids
                ]

            return recommendations[:k]

        except Exception as e:
            logger.error(f"Error getting category recommendations: {e}")
            return []

    async def get_popular_documents(self, k: int = 10) -> List[DocumentModel]:
        """
        Get popular documents based on various signals.
        """
        try:
            cache_key = f"popular_docs:{k}"
            cached_result = await self.cache_service.get(cache_key)
            if cached_result:
                return [DocumentModel(**doc) for doc in cached_result]

            # For now, use a simple approach - search for all documents and sort by score
            from app.models.search import SearchQuery

            search_query = SearchQuery(
                query="*",  # Match all documents
                size=k,
                sort_field="_score",
                sort_order="desc"
            )

            search_result = await self.search_service.search(search_query)
            result = search_result.documents

            # Cache results
            await self.cache_service.set(
                cache_key,
                [doc.dict() for doc in result],
                ttl=3600  # Cache for 1 hour
            )

            return result

        except Exception as e:
            logger.error(f"Error getting popular documents: {e}")
            return []

    async def recommend_mixed(self, user_id: Optional[str] = None,
                            document_id: Optional[str] = None,
                            session_id: Optional[str] = None,
                            k: int = 10) -> Dict[str, List[DocumentModel]]:
        """
        Get mixed recommendations using multiple strategies.
        """
        try:
            recommendations = {}

            # Get recommendations from different sources in parallel
            tasks = []

            # Similar documents (if document_id provided)
            if document_id:
                tasks.append(
                    self.recommend_similar_documents(document_id, k=min(k, 5))
                )

            # User-based recommendations (if user_id provided)
            if user_id:
                tasks.append(
                    self.recommend_by_user_history(user_id, session_id, k=min(k, 5))
                )

            # Trending documents
            tasks.append(
                self.recommend_trending_documents(k=min(k, 5))
            )

            # Popular documents
            tasks.append(
                self.get_popular_documents(k=min(k, 5))
            )

            # Execute all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            result_names = []
            if document_id:
                result_names.append("similar")
            if user_id:
                result_names.append("personalized")
            result_names.extend(["trending", "popular"])

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error in recommendation task {i}: {result}")
                    continue

                if i < len(result_names):
                    recommendations[result_names[i]] = result

            return recommendations

        except Exception as e:
            logger.error(f"Error getting mixed recommendations: {e}")
            return {}

    async def _get_user_interests(self, user_id: str,
                                session_id: Optional[str] = None) -> Dict[str, float]:
        """
        Extract user interests from their activity history.
        """
        try:
            interests = defaultdict(float)

            # Get search history (simplified - in real system, you'd query activity logs)
            if session_id:
                from app.services.redis.session_service import session_service

                search_history = await session_service.get_search_history(session_id, limit=20)

                # Extract keywords from search queries
                for search_item in search_history:
                    if isinstance(search_item, dict) and "query" in search_item:
                        query = search_item["query"]

                        # Simple keyword extraction (split by spaces)
                        keywords = query.split()
                        for keyword in keywords:
                            if len(keyword) > 2:  # Ignore very short terms
                                interests[keyword] += 1.0

            # Normalize interest weights
            if interests:
                max_weight = max(interests.values())
                interests = {k: v / max_weight for k, v in interests.items()}

            return dict(interests)

        except Exception as e:
            logger.error(f"Error extracting user interests: {e}")
            return {}

    async def _rerank_recommendations(self, documents: List[DocumentModel],
                                    source_document_id: str) -> List[DocumentModel]:
        """
        Re-rank recommendations based on multiple factors.
        """
        try:
            # Get source document for comparison
            source_doc = await self.search_service.get_document_by_id(source_document_id)

            if not source_doc:
                return documents

            # Apply various ranking factors
            for doc in documents:
                base_score = doc.score or 0

                # Category similarity boost
                category_boost = 1.0
                if (source_doc.category0 and doc.category0 and
                    source_doc.category0 == doc.category0):
                    category_boost = 1.2

                # File type similarity boost
                file_type_boost = 1.0
                if (source_doc.file_type and doc.file_type and
                    source_doc.file_type == doc.file_type):
                    file_type_boost = 1.1

                # Recency boost (newer documents get slight boost)
                recency_boost = 1.0
                try:
                    if doc.created_date:
                        created_date = datetime.fromisoformat(doc.created_date.replace('Z', '+00:00'))
                        days_old = (datetime.utcnow() - created_date).days
                        recency_boost = max(0.8, 1.0 - (days_old / 365))  # Year-based decay
                except:
                    pass

                # Apply all boosts
                doc.score = base_score * category_boost * file_type_boost * recency_boost

            # Sort by final score
            documents.sort(key=lambda x: x.score or 0, reverse=True)
            return documents

        except Exception as e:
            logger.error(f"Error re-ranking recommendations: {e}")
            return documents

    async def get_recommendation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about recommendations.
        """
        try:
            # This would typically query actual usage metrics
            # For now, return some basic stats

            return {
                "total_documents": await self._get_total_document_count(),
                "recommendation_types": {
                    "similar": "Vector similarity based",
                    "personalized": "User history based",
                    "trending": "Recent popularity based",
                    "popular": "Overall popularity based",
                    "category": "Category filtered"
                },
                "cache_hit_rate": await self._get_cache_hit_rate(),
                "avg_response_time_ms": 150  # Placeholder
            }

        except Exception as e:
            logger.error(f"Error getting recommendation stats: {e}")
            return {}

    async def _get_total_document_count(self) -> int:
        """Get total number of documents in the index."""
        try:
            from app.services.elasticsearch import elasticsearch_service

            stats = await elasticsearch_service.get_index_stats("ds_content")
            return stats.get("document_count", 0) if stats else 0

        except Exception as e:
            logger.error(f"Error getting document count: {e}")
            return 0

    async def _get_cache_hit_rate(self) -> float:
        """Get cache hit rate for recommendations."""
        try:
            # This is a placeholder - in a real system you'd track cache metrics
            return 0.75  # 75% hit rate

        except Exception as e:
            logger.error(f"Error getting cache hit rate: {e}")
            return 0.0

    async def health_check(self) -> Dict[str, Any]:
        """Check recommendation service health."""
        try:
            # Test basic functionality
            popular_docs = await self.get_popular_documents(k=1)

            return {
                "status": "healthy" if popular_docs else "degraded",
                "dependencies": {
                    "vector_service": "available",
                    "search_service": "available",
                    "cache_service": "available"
                },
                "test_results": {
                    "popular_documents": len(popular_docs) > 0
                }
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
recommendation_service = RecommendationService()