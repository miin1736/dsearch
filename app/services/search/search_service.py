"""
Main Search Service
"""
from typing import List, Dict, Any, Optional, Tuple
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q, A

from app.core.config import settings
from app.models.search import SearchQuery, SearchResult, DocumentModel, FacetAggregation, FacetItem
from app.services.elasticsearch import elasticsearch_service
from .text_analyzer import TextAnalyzer
from .highlighter import HighlightService

logger = logging.getLogger("ds")


class SearchService:
    """텍스트 및 하이브리드 검색을 처리하는 메인 검색 서비스 클래스."""

    def __init__(self):
        self.text_analyzer = TextAnalyzer()
        self.highlighter = HighlightService()

    async def search(self, query: SearchQuery) -> SearchResult:
        """검색 쿼리를 실행합니다."""
        try:
            # 검색 로직 구현 (예시: Elasticsearch 쿼리 구성)
            es_client = elasticsearch_service.get_client()
            search = Search(using=es_client, index=query.index_name)
            # 쿼리 구성 및 실행 (구체적 구현 생략)
            results = search.execute()
            return SearchResult(results=results.hits, total=results.total)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return SearchResult(results=[], total=0)

# Global instance
search_service = SearchService()