"""
검색 서비스
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# 올바른 모델 import
from app.models.search import (
    SearchQuery, 
    SearchResult, 
    SearchResponse,  # SearchResult 대신 SearchResponse 사용
    DocumentModel, 
    FacetAggregation, 
    FacetItem,
    SearchFacets,
    AdvancedSearchRequest,
    AdvancedSearchResponse
)

logger = logging.getLogger("ds")


class SearchService:
    """검색 서비스 클래스"""
    
    def __init__(self):
        self.elasticsearch_host = "https://cruxdata.co.kr"
        self.ports = [10323, 10423, 10523]
    
    async def search(self, query: SearchQuery) -> SearchResponse:
        """
        통합 검색 수행
        
        Args:
            query: 검색 쿼리
            
        Returns:
            SearchResponse: 검색 결과
        """
        try:
            logger.info(f"검색 수행 - 쿼리: {query.query}, 타입: {query.search_type}")
            
            # TODO: 실제 Elasticsearch 검색 구현
            
            # 임시 Mock 데이터
            mock_hits = [
                DocumentModel(
                    id="doc_12345",
                    score=0.95,
                    source={
                        "title": "FastAPI 개발 가이드",
                        "content": "FastAPI는 Python으로 API를 구축하기 위한...",
                        "category": "tech",
                        "created_at": datetime.now().isoformat()
                    },
                    highlight={
                        "title": ["<em>FastAPI</em> 개발 가이드"],
                        "content": ["<em>FastAPI</em>는 Python으로..."]
                    }
                )
            ]
            
            return SearchResponse(
                success=True,
                message="검색 완료",
                took=45,
                total={"value": 1500, "relation": "eq"},
                hits=mock_hits[:query.size]
            )
            
        except Exception as e:
            logger.error(f"검색 오류: {e}")
            raise
    
    async def advanced_search(self, query: AdvancedSearchRequest) -> AdvancedSearchResponse:
        """
        고급 검색 수행
        
        Args:
            query: 고급 검색 쿼리
            
        Returns:
            AdvancedSearchResponse: 고급 검색 결과
        """
        try:
            logger.info(f"고급 검색 수행 - 쿼리: {query.query}")
            
            # 기본 검색 수행
            basic_result = await self.search(query)
            
            # 패싯 정보 생성 (query.include_facets가 True인 경우)
            facets = None
            if query.include_facets:
                facets = SearchFacets(
                    categories=[
                        FacetItem(key="tech", doc_count=1500, selected=True),
                        FacetItem(key="business", doc_count=800, selected=False)
                    ],
                    authors=[
                        FacetItem(key="김개발", doc_count=200, selected=False),
                        FacetItem(key="박프로그래머", doc_count=150, selected=False)
                    ],
                    dates=[
                        FacetItem(key="2023", doc_count=1200, selected=False),
                        FacetItem(key="2022", doc_count=300, selected=False)
                    ],
                    file_types=[
                        FacetItem(key="pdf", doc_count=900, selected=False),
                        FacetItem(key="docx", doc_count=600, selected=False)
                    ],
                    languages=[
                        FacetItem(key="ko", doc_count=1300, selected=False),
                        FacetItem(key="en", doc_count=200, selected=False)
                    ]
                )
            
            return AdvancedSearchResponse(
                success=True,
                message="고급 검색 완료",
                took=basic_result.took,
                total=basic_result.total,
                hits=basic_result.hits,
                facets=facets
            )
            
        except Exception as e:
            logger.error(f"고급 검색 오류: {e}")
            raise


# 전역 인스턴스 생성
search_service = SearchService()