"""
검색 관련 데이터 모델
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum

# ResponseModel import 추가
from .base import ResponseModel


class SearchType(str, Enum):
    """검색 타입 열거형"""
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    VECTOR = "vector"
    HYBRID = "hybrid"
    AI = "ai"
    INTEGRATION = "integration"


class SortType(str, Enum):
    """정렬 타입 열거형"""
    RELEVANCE = "relevance"
    DATE_DESC = "date_desc"
    DATE_ASC = "date_asc"
    TITLE = "title"
    SCORE = "score"


class SearchFilter(BaseModel):
    """검색 필터 모델"""
    categories: Optional[List[str]] = Field(default=None, description="카테고리 필터")
    tags: Optional[List[str]] = Field(default=None, description="태그 필터")
    date_range: Optional[Dict[str, str]] = Field(default=None, description="날짜 범위 필터")
    file_types: Optional[List[str]] = Field(default=None, description="파일 타입 필터")
    authors: Optional[List[str]] = Field(default=None, description="작성자 필터")
    
    @validator('date_range')
    def validate_date_range(cls, v):
        """날짜 범위 검증"""
        if v and ('start' in v or 'end' in v):
            if 'start' in v:
                datetime.fromisoformat(v['start'].replace('Z', '+00:00'))
            if 'end' in v:
                datetime.fromisoformat(v['end'].replace('Z', '+00:00'))
        return v


class SearchQuery(BaseModel):
    """검색 쿼리 모델"""
    query: str = Field(..., min_length=1, max_length=500, description="검색 쿼리")
    search_type: SearchType = Field(default=SearchType.INTEGRATION, description="검색 타입")
    size: int = Field(default=10, ge=1, le=100, description="결과 수")
    from_: int = Field(default=0, ge=0, alias="from", description="오프셋")
    sort: SortType = Field(default=SortType.RELEVANCE, description="정렬 방식")
    filters: Optional[SearchFilter] = Field(default=None, description="검색 필터")
    
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "query": "FastAPI 개발 방법",
                "search_type": "integration",
                "size": 10,
                "from": 0,
                "sort": "relevance"
            }
        }
    }


class DocumentModel(BaseModel):
    """문서 모델"""
    id: str = Field(..., description="문서 ID")
    score: float = Field(..., description="검색 점수")
    source: Dict[str, Any] = Field(..., description="문서 소스 데이터")
    highlight: Optional[Dict[str, List[str]]] = Field(default=None, description="하이라이트 정보")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "doc_12345",
                "score": 0.95,
                "source": {
                    "title": "FastAPI 개발 가이드",
                    "content": "FastAPI는 Python으로 API를 구축하기 위한...",
                    "category": "tech"
                }
            }
        }
    }


class SearchResult(ResponseModel):
    """검색 결과 모델"""
    took: int = Field(..., description="검색 소요 시간(ms)")
    total: Dict[str, Union[int, str]] = Field(..., description="총 결과 수 정보")
    hits: List[DocumentModel] = Field(..., description="검색 결과")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "검색 완료",
                "took": 45,
                "total": {"value": 1500, "relation": "eq"},
                "hits": []
            }
        }
    }


class AutoCompleteAddRequest(BaseModel):
    """자동완성 키워드 추가 요청 모델"""
    keyword: str = Field(..., min_length=1, max_length=100, description="추가할 키워드")
    use_yn: str = Field(default="Y", pattern="^(Y|N)$", description="활성화 상태")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "keyword": "힐스테이트",
                "use_yn": "Y"
            }
        }
    }


class AutoCompleteAddResponse(ResponseModel):
    """자동완성 키워드 추가 응답 모델"""
    keyword: str = Field(..., description="추가된 키워드")
    document_id: str = Field(..., description="생성된 문서 ID")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "키워드가 성공적으로 추가되었습니다",
                "keyword": "힐스테이트",
                "document_id": "6YhJ1pkBZykI2mC0P21x"
            }
        }
    }


class TypoCorrectionQuery(BaseModel):
    """오타 교정 쿼리 모델"""
    text: str = Field(..., min_length=1, max_length=200, description="교정할 텍스트")
    size: int = Field(default=10, ge=1, le=50, description="반환할 제안 개수")
    max_edits: int = Field(default=2, ge=1, le=2, description="최대 편집 거리")
    min_word_length: int = Field(default=8, ge=1, le=20, description="제안할 최소 단어 길이")
    prefix_length: int = Field(default=2, ge=0, le=10, description="일치해야 하는 접두사 길이")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "밤죄도시",
                "size": 10,
                "max_edits": 2,
                "min_word_length": 8,
                "prefix_length": 2
            }
        }
    }


class TypoSuggestion(BaseModel):
    """오타 교정 제안 모델"""
    text: str = Field(..., description="교정된 텍스트")
    score: float = Field(..., description="제안 점수")
    freq: int = Field(..., description="빈도수")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "범죄도시",
                "score": 0.8,
                "freq": 100
            }
        }
    }


class TypoCorrectionResult(ResponseModel):
    """오타 교정 결과 모델"""
    original_text: str = Field(..., description="원본 텍스트")
    suggestions: List[TypoSuggestion] = Field(..., description="교정 제안 리스트")
    took_ms: int = Field(..., description="처리 시간(ms)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "오타 교정 완료",
                "original_text": "밤죄도시",
                "suggestions": [
                    {
                        "text": "범죄도시",
                        "score": 0.8,
                        "freq": 100
                    }
                ],
                "took_ms": 12
            }
        }
    }


class TypoCorrectionAddRequest(BaseModel):
    """오타 교정 키워드 추가 요청 모델"""
    keyword: str = Field(..., min_length=1, max_length=100, description="추가할 키워드")
    category: Optional[str] = Field(default=None, max_length=50, description="카테고리")
    category_id: Optional[str] = Field(default=None, max_length=50, description="카테고리 ID")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "keyword": "범죄도시",
                "category": "영화",
                "category_id": "movie_001"
            }
        }
    }


class TypoCorrectionAddResponse(ResponseModel):
    """오타 교정 키워드 추가 응답 모델"""
    keyword: str = Field(..., description="추가된 키워드")
    document_id: str = Field(..., description="생성된 문서 ID")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "오타 교정 키워드가 성공적으로 추가되었습니다",
                "keyword": "범죄도시",
                "document_id": "abc123xyz"
            }
        }
    }


class VectorSearchRequest(BaseModel):
    """벡터 검색 요청 모델"""
    query: str = Field(..., min_length=1, max_length=1000, description="검색 쿼리")
    model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        description="임베딩 모델"
    )
    size: int = Field(default=10, ge=1, le=100, description="결과 수")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="유사도 임계값")
    include_score: bool = Field(default=True, description="유사도 점수 포함 여부")


class AutocompleteRequest(BaseModel):
    """자동완성 요청 모델"""
    query: str = Field(..., min_length=1, max_length=100, description="자동완성 쿼리")
    size: int = Field(default=10, ge=1, le=50, description="제안 수")
    field: str = Field(default="title", description="대상 필드")


class AutocompleteResponse(ResponseModel):
    """자동완성 응답 모델"""
    suggestions: List[str] = Field(..., description="자동완성 제안 목록")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "자동완성 완료",
                "suggestions": [
                    "FastAPI tutorial",
                    "FastAPI authentication",
                    "FastAPI database"
                ]
            }
        }
    }


class SearchSuggestionsResponse(ResponseModel):
    """검색 제안 응답 모델"""
    suggestions: List[str] = Field(..., description="검색 제안 목록")
    query: str = Field(..., description="원본 쿼리")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "검색 제안 완료",
                "suggestions": [
                    "FastAPI tutorial",
                    "FastAPI authentication",
                    "FastAPI database integration"
                ],
                "query": "FastAPI"
            }
        }
    }


class DocumentDetail(BaseModel):
    """문서 상세 정보 모델"""
    id: str = Field(..., description="문서 ID")
    title: str = Field(..., description="문서 제목")
    content: Optional[str] = Field(default=None, description="문서 내용")
    summary: Optional[str] = Field(default=None, description="문서 요약")
    category: Optional[str] = Field(default=None, description="카테고리")
    tags: Optional[List[str]] = Field(default=None, description="태그")
    author: Optional[str] = Field(default=None, description="작성자")
    created_at: Optional[datetime] = Field(default=None, description="생성일시")
    updated_at: Optional[datetime] = Field(default=None, description="수정일시")
    view_count: int = Field(default=0, description="조회수")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="메타데이터")


class DocumentResponse(ResponseModel):
    """문서 조회 응답 모델"""
    document: DocumentDetail = Field(..., description="문서 상세 정보")


class SimilarDocumentsRequest(BaseModel):
    """유사 문서 요청 모델"""
    document_id: str = Field(..., description="기준 문서 ID")
    size: int = Field(default=5, ge=1, le=20, description="유사 문서 수")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="유사도 임계값")
    exclude_self: bool = Field(default=True, description="자기 자신 제외 여부")


class SimilarDocumentsResponse(ResponseModel):
    """유사 문서 응답 모델"""
    similar_documents: List[DocumentModel] = Field(..., description="유사 문서 목록")
    base_document_id: str = Field(..., description="기준 문서 ID")


class CategoryInfo(BaseModel):
    """카테고리 정보 모델"""
    name: str = Field(..., description="카테고리 이름")
    display_name: str = Field(..., description="카테고리 표시명")
    description: Optional[str] = Field(default=None, description="카테고리 설명")
    document_count: int = Field(..., description="문서 수")
    subcategories: Optional[List['CategoryInfo']] = Field(default=None, description="하위 카테고리")

# Forward reference 해결
CategoryInfo.model_rebuild()


class CategoriesResponse(ResponseModel):
    """카테고리 목록 응답 모델"""
    categories: List[CategoryInfo] = Field(..., description="카테고리 목록")
    total_categories: int = Field(..., description="총 카테고리 수")


class DocumentDownloadInfo(BaseModel):
    """문서 다운로드 정보 모델"""
    document_id: str = Field(..., description="문서 ID")
    filename: str = Field(..., description="파일명")
    file_size: int = Field(..., description="파일 크기(bytes)")
    content_type: str = Field(..., description="콘텐츠 타입")
    download_url: str = Field(..., description="다운로드 URL")
    expires_at: Optional[datetime] = Field(default=None, description="만료 시간")


class ExportRequest(BaseModel):
    """검색 결과 내보내기 요청 모델"""
    query: str = Field(..., description="검색 쿼리")
    format: str = Field(default="json", pattern="^(json|csv|excel)$", description="내보내기 형식")
    max_results: int = Field(default=1000, ge=1, le=10000, description="최대 결과 수")
    include_content: bool = Field(default=False, description="전체 내용 포함 여부")
    filters: Optional[SearchFilter] = Field(default=None, description="검색 필터")


class SearchStatsResponse(ResponseModel):
    """검색 통계 응답 모델"""
    total_documents: int = Field(..., description="전체 문서 수")
    total_searches: int = Field(..., description="총 검색 횟수")
    popular_queries: List[Dict[str, Any]] = Field(..., description="인기 검색어")
    categories_distribution: Dict[str, int] = Field(..., description="카테고리별 분포")


class AISearchRequest(BaseModel):
    """AI 검색 요청 모델"""
    query: str = Field(..., min_length=1, max_length=1000, description="AI 검색 쿼리")
    context_size: int = Field(default=5, ge=1, le=20, description="컨텍스트 크기")
    model: str = Field(default="gpt-3.5-turbo", description="AI 모델")
    include_sources: bool = Field(default=True, description="소스 정보 포함 여부")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="AI 모델 temperature")
    max_tokens: int = Field(default=1000, ge=100, le=4000, description="최대 토큰 수")


class AISearchResponse(ResponseModel):
    """AI 검색 응답 모델"""
    ai_response: str = Field(..., description="AI 생성 응답")
    sources: List[Dict[str, Any]] = Field(..., description="참조 소스")
    tokens_used: int = Field(..., description="사용된 토큰 수")
    ai_model_used: str = Field(..., description="사용된 AI 모델")  # model_used → ai_model_used로 변경
    
    model_config = {
        "protected_namespaces": (),  # 보호 네임스페이스 비활성화
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "AI 검색 완료",
                "ai_response": "FastAPI로 REST API를 만드는 방법은...",
                "sources": [
                    {
                        "title": "FastAPI 공식 문서",
                        "url": "https://fastapi.tiangolo.com",
                        "relevance": 0.95
                    }
                ],
                "tokens_used": 1250,
                "ai_model_used": "gpt-3.5-turbo"
            }
        }
    }


class HybridSearchRequest(BaseModel):
    """하이브리드 검색 요청 모델"""
    query: str = Field(..., min_length=1, max_length=500, description="검색 쿼리")
    keyword_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="키워드 검색 가중치")
    vector_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="벡터 검색 가중치")
    size: int = Field(default=10, ge=1, le=100, description="결과 수")
    filters: Optional[SearchFilter] = Field(default=None, description="검색 필터")
    
    @validator('vector_weight')
    def validate_weights_sum(cls, v, values):
        """가중치 합계 검증"""
        if 'keyword_weight' in values:
            if abs((values['keyword_weight'] + v) - 1.0) > 0.001:
                raise ValueError("키워드 가중치와 벡터 가중치의 합은 1.0이어야 합니다")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "FastAPI 웹 개발",
                "keyword_weight": 0.7,
                "vector_weight": 0.3,
                "size": 10
            }
        }
    }


class SearchPerformanceMetrics(BaseModel):
    """검색 성능 지표 모델"""
    total_documents_indexed: int = Field(..., description="인덱싱된 총 문서 수")
    index_size_mb: float = Field(..., description="인덱스 크기(MB)")
    avg_search_time_ms: float = Field(..., description="평균 검색 시간(ms)")
    searches_per_second: float = Field(..., description="초당 검색 수")
    cache_hit_rate: float = Field(..., description="캐시 적중률")


class SearchAnalytics(BaseModel):
    """검색 분석 정보 모델"""
    query_performance: Dict[str, float] = Field(..., description="쿼리 성능 지표")
    popular_terms: List[Dict[str, Any]] = Field(..., description="인기 검색어")
    search_trends: List[Dict[str, Any]] = Field(..., description="검색 트렌드")
    category_distribution: Dict[str, int] = Field(..., description="카테고리별 검색 분포")


class EnhancedSearchStatsResponse(ResponseModel):
    """향상된 검색 통계 응답 모델"""
    performance_metrics: SearchPerformanceMetrics = Field(..., description="성능 지표")
    analytics: SearchAnalytics = Field(..., description="분석 정보") 
    last_updated: datetime = Field(..., description="마지막 업데이트 시간")


class FacetItem(BaseModel):
    """패싯 아이템 모델"""
    key: str = Field(..., description="패싯 키")
    doc_count: int = Field(..., description="문서 수")
    selected: bool = Field(default=False, description="선택 여부")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "key": "technology",
                "doc_count": 15000,
                "selected": False
            }
        }
    }


class FacetAggregation(BaseModel):
    """패싯 집계 모델"""
    field_name: str = Field(..., description="필드명")
    display_name: str = Field(..., description="표시명")
    buckets: List[FacetItem] = Field(..., description="패싯 버킷")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "field_name": "category",
                "display_name": "카테고리",
                "buckets": [
                    {
                        "key": "technology",
                        "doc_count": 15000,
                        "selected": False
                    },
                    {
                        "key": "business", 
                        "doc_count": 12000,
                        "selected": True
                    }
                ]
            }
        }
    }


class SearchFacets(BaseModel):
    """검색 패싯 정보 모델"""
    categories: List[FacetItem] = Field(..., description="카테고리 패싯")
    authors: List[FacetItem] = Field(..., description="작성자 패싯")
    dates: List[FacetItem] = Field(..., description="날짜 패싯")
    file_types: List[FacetItem] = Field(..., description="파일 타입 패싯")
    languages: List[FacetItem] = Field(..., description="언어 패싯")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "categories": [
                    {"key": "tech", "doc_count": 15000, "selected": False},
                    {"key": "business", "doc_count": 12000, "selected": True}
                ],
                "authors": [
                    {"key": "김개발", "doc_count": 500, "selected": False}
                ],
                "dates": [
                    {"key": "2023", "doc_count": 25000, "selected": False}
                ],
                "file_types": [
                    {"key": "pdf", "doc_count": 8000, "selected": False},
                    {"key": "docx", "doc_count": 6000, "selected": False}
                ],
                "languages": [
                    {"key": "ko", "doc_count": 20000, "selected": False},
                    {"key": "en", "doc_count": 15000, "selected": False}
                ]
            }
        }
    }


class AdvancedSearchFilter(SearchFilter):
    """고급 검색 필터 모델"""
    language: Optional[List[str]] = Field(default=None, description="언어 필터")
    content_length: Optional[Dict[str, int]] = Field(default=None, description="내용 길이 필터")
    popularity_score: Optional[Dict[str, float]] = Field(default=None, description="인기도 점수 필터")
    last_modified: Optional[Dict[str, str]] = Field(default=None, description="수정일 필터")
    
    @validator('content_length')
    def validate_content_length(cls, v):
        """내용 길이 필터 검증"""
        if v:
            if 'min' in v and 'max' in v and v['min'] > v['max']:
                raise ValueError("최소값이 최대값보다 클 수 없습니다")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "categories": ["tech", "programming"],
                "language": ["ko", "en"],
                "content_length": {"min": 1000, "max": 50000},
                "popularity_score": {"min": 0.7},
                "date_range": {
                    "start": "2023-01-01",
                    "end": "2023-12-31"
                }
            }
        }
    }


class AdvancedSearchRequest(SearchQuery):
    """고급 검색 요청 모델"""
    filters: Optional[AdvancedSearchFilter] = Field(default=None, description="고급 검색 필터")
    include_facets: bool = Field(default=True, description="패싯 정보 포함 여부")
    facet_size: int = Field(default=10, ge=1, le=100, description="패싯 버킷 수")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "FastAPI 웹 개발",
                "search_type": "integration",
                "size": 20,
                "include_facets": True,
                "facet_size": 10,
                "filters": {
                    "categories": ["tech"],
                    "language": ["ko"],
                    "date_range": {
                        "start": "2023-01-01",
                        "end": "2023-12-31"
                    }
                }
            }
        }
    }


class AdvancedSearchResponse(SearchResult):
    """고급 검색 응답 모델"""
    facets: Optional[SearchFacets] = Field(default=None, description="패싯 정보")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "고급 검색 완료",
                "took": 85,
                "total": {"value": 2500, "relation": "eq"},
                "hits": [],
                "facets": {
                    "categories": [
                        {"key": "tech", "doc_count": 1500, "selected": True}
                    ]
                }
            }
        }
    }


# SearchResult 모델도 업데이트 (facets 필드 추가)
class SearchResponse(SearchResult):
    """검색 응답 모델 (SearchResult의 별칭)"""
    facets: Optional[SearchFacets] = Field(default=None, description="패싯 정보")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "검색 완료",
                "took": 45,
                "total": {"value": 1500, "relation": "eq"},
                "hits": [],
                "facets": None
            }
        }
    }