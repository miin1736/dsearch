"""
검색 API 엔드포인트 모듈
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
import logging

from app.core.security import get_current_user
from app.models.search import (
    SearchQuery, SearchResult, VectorSearchQuery, SimilarDocumentQuery,
    AutoCompleteQuery, AutoCompleteResult, DocumentModel
)
from app.models.base import ResponseModel, PaginatedResponse
from app.services.search import SearchService, VectorService
from app.services.search.text_analyzer import TextAnalyzer
from app.utils.file_handler import FileHandler

logger = logging.getLogger("ds")

router = APIRouter()

# Initialize services
search_service = SearchService()
vector_service = VectorService()
text_analyzer = TextAnalyzer()
file_handler = FileHandler()


@router.post("/", response_model=SearchResult)
async def search_documents(
    query: SearchQuery,
    current_user: dict = Depends(get_current_user)
):
    """
    문서 검색을 수행합니다.

    다양한 검색 유형을 지원합니다:
    - text: BM25를 사용한 전통적인 텍스트 검색
    - vector: 의미적 벡터 검색
    - hybrid: 텍스트와 벡터 검색의 조합
    - fuzzy: 유사 문자열 매칭 검색

    Args:
        query (SearchQuery): 검색 쿼리 매개변수
        current_user (dict): 현재 인증된 사용자 정보

    Returns:
        SearchResult: 검색 결과

    Raises:
        HTTPException: 검색 실행 중 오류 발생 시
    """
    try:
        result = await search_service.search(query)

        # Log user activity
        logger.info(f"User {current_user.get('username')} searched: {query.query}")

        return result

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/vector", response_model=SearchResult)
async def vector_search(
    query: VectorSearchQuery,
    current_user: dict = Depends(get_current_user)
):
    """
    벡터 기반 의미적 검색을 수행합니다.

    텍스트를 벡터로 변환하여 의미적 유사성을 기반으로 문서를 검색합니다.

    Args:
        query (VectorSearchQuery): 벡터 검색 쿼리 매개변수
        current_user (dict): 현재 인증된 사용자 정보

    Returns:
        SearchResult: 벡터 검색 결과

    Raises:
        HTTPException: 벡터 검색 실행 중 오류 발생 시
    """
    try:
        # Convert to SearchQuery
        search_query = SearchQuery(
            query=query.query,
            search_type="vector",
            size=query.k,
            vector_threshold=query.threshold
        )

        result = await vector_service.vector_search(search_query)
        return result

    except Exception as e:
        logger.error(f"Vector search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search failed: {str(e)}"
        )


@router.get("/similar/{document_id}", response_model=List[DocumentModel])
async def find_similar_documents(
    document_id: str = Path(..., description="Document ID to find similar documents for"),
    k: int = Query(default=10, ge=1, le=50, description="Number of similar documents"),
    threshold: float = Query(default=0.7, ge=0.0, le=1.0, description="Similarity threshold"),
    current_user: dict = Depends(get_current_user)
):
    """
    벡터 유사도를 사용하여 주어진 문서와 유사한 문서들을 찾습니다.

    Args:
        document_id (str): 기준 문서 ID
        k (int): 반환할 유사 문서 개수 (1-50, 기본값: 10)
        threshold (float): 유사도 임계값 (0.0-1.0, 기본값: 0.7)
        current_user (dict): 현재 인증된 사용자 정보

    Returns:
        List[DocumentModel]: 유사한 문서들의 리스트

    Raises:
        HTTPException: 유사 문서 검색 중 오류 발생 시
    """
    try:
        similar_docs = await vector_service.find_similar_documents(
            document_id=document_id,
            k=k,
            threshold=threshold
        )

        logger.info(f"User {current_user.get('username')} found {len(similar_docs)} similar documents for {document_id}")

        return similar_docs

    except Exception as e:
        logger.error(f"Similar documents error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Finding similar documents failed: {str(e)}"
        )


@router.post("/autocomplete", response_model=AutoCompleteResult)
async def get_autocomplete_suggestions(
    query: AutoCompleteQuery,
    current_user: dict = Depends(get_current_user)
):
    """
    검색 쿼리에 대한 자동완성 제안을 가져옵니다.

    입력된 접두사를 기반으로 가능한 검색어 후보들을 제공합니다.

    Args:
        query (AutoCompleteQuery): 자동완성 쿼리 매개변수
        current_user (dict): 현재 인증된 사용자 정보

    Returns:
        AutoCompleteResult: 자동완성 제안 결과

    Raises:
        HTTPException: 자동완성 처리 중 오류 발생 시
    """
    try:
        import time
        start_time = time.time()

        suggestions = await text_analyzer.get_auto_completions(
            prefix=query.prefix,
            field=query.field,
            size=query.size
        )

        took_ms = int((time.time() - start_time) * 1000)

        result = AutoCompleteResult(
            suggestions=suggestions,
            took_ms=took_ms
        )

        return result

    except Exception as e:
        logger.error(f"Autocomplete error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Autocomplete failed: {str(e)}"
        )


@router.get("/suggestions/{query}")
async def get_search_suggestions(
    query: str = Path(..., description="Query to get suggestions for"),
    current_user: dict = Depends(get_current_user)
):
    """
    검색 제안 및 오타 교정을 제공합니다.

    입력된 쿼리의 오타를 교정하고 더 나은 검색어를 제안합니다.

    Args:
        query (str): 교정할 검색 쿼리
        current_user (dict): 현재 인증된 사용자 정보

    Returns:
        ResponseModel: 교정된 검색 제안 결과

    Raises:
        HTTPException: 제안 생성 중 오류 발생 시
    """
    try:
        suggestions = await text_analyzer.suggest_corrections(query)

        return ResponseModel(
            success=True,
            data={
                "query": query,
                "suggestions": suggestions
            }
        )

    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting suggestions failed: {str(e)}"
        )


@router.get("/document/{document_id}")
async def get_document(
    document_id: str = Path(..., description="Document ID"),
    highlight: Optional[str] = Query(default=None, description="Keywords to highlight"),
    current_user: dict = Depends(get_current_user)
):
    """
    ID로 문서 내용을 가져오며 선택적으로 키워드 하이라이트를 적용합니다.

    Args:
        document_id (str): 문서 ID
        highlight (Optional[str]): 하이라이트할 키워드들 (쉼표로 구분)
        current_user (dict): 현재 인증된 사용자 정보

    Returns:
        DocumentModel: 문서 내용 (하이라이트 적용됨)

    Raises:
        HTTPException: 문서를 찾을 수 없거나 처리 중 오류 발생 시
    """
    try:
        document = await search_service.get_document_by_id(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Apply highlighting if requested
        if highlight:
            keywords = highlight.split(',')
            keywords = [kw.strip() for kw in keywords if kw.strip()]

            if document.html_content and keywords:
                from app.services.search.highlighter import highlight_service
                document.html_content = highlight_service.highlight_document_view(
                    document.html_content, keywords
                )

        logger.info(f"User {current_user.get('username')} viewed document {document_id}")

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting document failed: {str(e)}"
        )


@router.get("/document/{document_id}/download")
async def download_document(
    document_id: str = Path(..., description="Document ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    문서 파일을 다운로드합니다.

    Args:
        document_id (str): 다운로드할 문서 ID
        current_user (dict): 현재 인증된 사용자 정보

    Returns:
        FileResponse: 다운로드할 파일 응답

    Raises:
        HTTPException: 파일을 찾을 수 없거나 다운로드 중 오류 발생 시
    """
    try:
        document = await search_service.get_document_by_id(document_id)

        if not document or not document.file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document or file not found"
            )

        file_path = file_handler.get_full_path(document.file_path)

        if not file_handler.file_exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on server"
            )

        logger.info(f"User {current_user.get('username')} downloaded document {document_id}")

        return FileResponse(
            path=file_path,
            filename=document.filename,
            media_type='application/octet-stream'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download document error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Downloading document failed: {str(e)}"
        )


@router.get("/categories")
async def get_categories(
    current_user: dict = Depends(get_current_user)
):
    """
    필터링을 위한 사용 가능한 문서 카테고리를 가져옵니다.

    Args:
        current_user (dict): 현재 인증된 사용자 정보

    Returns:
        ResponseModel: 사용 가능한 카테고리 목록

    Raises:
        HTTPException: 카테고리 조회 중 오류 발생 시
    """
    try:
        categories = await search_service.get_categories()

        return ResponseModel(
            success=True,
            data={"categories": categories}
        )

    except Exception as e:
        logger.error(f"Get categories error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting categories failed: {str(e)}"
        )


@router.get("/stats")
async def get_search_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    검색 통계 및 분석 데이터를 가져옵니다.

    Args:
        current_user (dict): 현재 인증된 사용자 정보

    Returns:
        ResponseModel: 검색 통계 데이터

    Raises:
        HTTPException: 통계 조회 중 오류 발생 시
    """
    try:
        stats = await search_service.get_search_stats()

        return ResponseModel(
            success=True,
            data=stats
        )

    except Exception as e:
        logger.error(f"Get search stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting search stats failed: {str(e)}"
        )


@router.post("/export")
async def export_search_results(
    query: SearchQuery,
    format: str = Query(default="csv", regex="^(csv|xlsx|json)$"),
    current_user: dict = Depends(get_current_user)
):
    """
    검색 결과를 다양한 형식으로 내보냅니다.

    지원 형식: CSV, Excel (XLSX), JSON

    Args:
        query (SearchQuery): 내보낼 검색 쿼리
        format (str): 내보내기 형식 (csv, xlsx, json)
        current_user (dict): 현재 인증된 사용자 정보

    Returns:
        StreamingResponse: 내보낸 파일의 스트리밍 응답

    Raises:
        HTTPException: 내보내기 처리 중 오류 발생 시
    """
    try:
        # Perform search to get results
        result = await search_service.search(query)

        # Export results
        export_data = await search_service.export_results(result.documents, format)

        logger.info(f"User {current_user.get('username')} exported search results in {format} format")

        # Return as streaming response
        if format == "csv":
            media_type = "text/csv"
            filename = f"search_results.csv"
        elif format == "xlsx":
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"search_results.xlsx"
        else:  # json
            media_type = "application/json"
            filename = f"search_results.json"

        return StreamingResponse(
            iter([export_data]),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        logger.error(f"Export search results error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Exporting search results failed: {str(e)}"
        )