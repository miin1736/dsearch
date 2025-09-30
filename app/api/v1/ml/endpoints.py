"""
기계학습 및 AI API 엔드포인트

RAG (Retrieval-Augmented Generation) 기반 질문 답변, 문서 요약,
개인화 추천, 키워드 추출 등 AI 기능을 위한 API 엔드포인트들을 제공합니다.
스트리밍 응답과 실시간 추천 기능을 지원합니다.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
import json
import logging

from app.core.security import get_current_user
from app.models.base import ResponseModel
from app.models.search import SearchType, DocumentModel
from app.services.ml.rag_service import rag_service
from app.services.ml.recommendation_service import recommendation_service
from app.services.ml.openai_service import openai_service

logger = logging.getLogger("ds")

router = APIRouter()


@router.post("/ask")
async def ask_question(
    request: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    RAG (검색 증강 생성)를 사용하여 질문에 답변합니다.

    사용자의 질문에 대해 관련 문서를 검색하고 AI를 통해
    컨텍스트 기반의 정확한 답변을 생성합니다.

    Args:
        request: 질문 요청 데이터
            - question: 사용자의 질문
            - search_type: 검색 유형 (기본값: hybrid)
            - max_documents: 검색할 최대 문서 수 (기본값: 5)
        current_user: 인증된 현재 사용자 정보

    Returns:
        ResponseModel: 질문에 대한 답변과 참조 문서

    Raises:
        HTTPException: 질문이 없는 경우 400 에러,
                      답변 생성 실패 시 500 에러
    """
    try:
        question = request.get("question")
        if not question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question is required"
            )

        search_type = SearchType(request.get("search_type", "hybrid"))
        max_documents = request.get("max_documents", 5)

        result = await rag_service.ask_question(
            question=question,
            search_type=search_type,
            max_documents=max_documents
        )

        logger.info(f"User {current_user.get('username')} asked: {question}")

        return ResponseModel(
            success=result["success"],
            data=result,
            message=result.get("error") if not result["success"] else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ask question error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Question answering failed: {str(e)}"
        )


@router.post("/ask/stream")
async def ask_question_streaming(
    request: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    RAG를 사용하여 스트리밍 응답으로 질문에 답변합니다.

    실시간으로 답변을 생성하면서 부분적인 결과를 스트리밍으로
    전송하여 사용자에게 빠른 반응성을 제공합니다.

    Args:
        request: 질문 요청 데이터
            - question: 사용자의 질문
            - search_type: 검색 유형 (기본값: hybrid)
            - max_documents: 검색할 최대 문서 수 (기본값: 5)
        current_user: 인증된 현재 사용자 정보

    Returns:
        StreamingResponse: 실시간 답변 스트림

    Raises:
        HTTPException: 질문이 없는 경우 400 에러,
                      스트리밍 실패 시 500 에러
    """
    try:
        question = request.get("question")
        if not question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question is required"
            )

        search_type = SearchType(request.get("search_type", "hybrid"))
        max_documents = request.get("max_documents", 5)

        async def generate_stream():
            try:
                async for chunk in rag_service.ask_question_streaming(
                    question=question,
                    search_type=search_type,
                    max_documents=max_documents
                ):
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'data': str(e)}, ensure_ascii=False)}\n\n"

        logger.info(f"User {current_user.get('username')} asked (streaming): {question}")

        return StreamingResponse(
            generate_stream(),
            media_type="text/stream-events",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ask question streaming error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming question answering failed: {str(e)}"
        )


@router.post("/summarize")
async def summarize_documents(
    request: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    여러 문서를 요약합니다.

    지정된 문서들의 내용을 분석하여 핵심 내용을 추출하고
    지정된 요약 유형에 따라 통합된 요약을 생성합니다.

    Args:
        request: 요약 요청 데이터
            - document_ids: 요약할 문서들의 ID 목록
            - summary_type: 요약 유형 (기본값: comprehensive)
        current_user: 인증된 현재 사용자 정보

    Returns:
        ResponseModel: 문서들의 통합 요약 결과

    Raises:
        HTTPException: 문서 ID가 없는 경우 400 에러,
                      요약 생성 실패 시 500 에러
    """
    try:
        document_ids = request.get("document_ids", [])
        if not document_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document IDs are required"
            )

        summary_type = request.get("summary_type", "comprehensive")

        result = await rag_service.summarize_documents(
            document_ids=document_ids,
            summary_type=summary_type
        )

        logger.info(f"User {current_user.get('username')} summarized {len(document_ids)} documents")

        return ResponseModel(
            success=result["success"],
            data=result,
            message=result.get("error") if not result["success"] else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summarize documents error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document summarization failed: {str(e)}"
        )


@router.get("/recommendations")
async def get_recommendations(
    user_id: str = None,
    document_id: str = None,
    session_id: str = None,
    k: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    문서 추천을 조회합니다.

    사용자의 행동 패턴, 관심사, 최근 활동을 기반으로
    개인화된 문서 추천을 제공합니다.

    Args:
        user_id: 사용자 ID (선택사항, 기본값: 현재 사용자)
        document_id: 기준 문서 ID (선택사항)
        session_id: 세션 ID (선택사항)
        k: 추천할 문서 수 (기본값: 10)
        current_user: 인증된 현재 사용자 정보

    Returns:
        ResponseModel: 개인화된 문서 추천 목록

    Raises:
        HTTPException: 추천 생성 실패 시 500 에러
    """
    try:
        recommendations = await recommendation_service.recommend_mixed(
            user_id=user_id or current_user.get("user_id"),
            document_id=document_id,
            session_id=session_id,
            k=k
        )

        return ResponseModel(
            success=True,
            data=recommendations
        )

    except Exception as e:
        logger.error(f"Get recommendations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting recommendations failed: {str(e)}"
        )


@router.get("/recommendations/similar/{document_id}")
async def get_similar_recommendations(
    document_id: str,
    k: int = 5,
    threshold: float = 0.6,
    current_user: dict = Depends(get_current_user)
):
    """
    유사한 문서 추천을 조회합니다.

    지정된 문서와 내용적으로 유사한 문서들을 찾아
    유사도 임계값을 기준으로 추천 목록을 제공합니다.

    Args:
        document_id: 기준이 되는 문서의 ID
        k: 추천할 유사 문서 수 (기본값: 5)
        threshold: 유사도 임계값 (기본값: 0.6)
        current_user: 인증된 현재 사용자 정보

    Returns:
        ResponseModel: 유사한 문서들의 추천 목록

    Raises:
        HTTPException: 유사 문서 조회 실패 시 500 에러
    """
    try:
        recommendations = await recommendation_service.recommend_similar_documents(
            document_id=document_id,
            k=k,
            threshold=threshold
        )

        return ResponseModel(
            success=True,
            data={"recommendations": recommendations}
        )

    except Exception as e:
        logger.error(f"Get similar recommendations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting similar recommendations failed: {str(e)}"
        )


@router.get("/recommendations/trending")
async def get_trending_recommendations(
    k: int = 10,
    time_window_hours: int = 24,
    current_user: dict = Depends(get_current_user)
):
    """
    인기 급상승 문서 추천을 조회합니다.

    지정된 시간 윈도우 내에서 가장 많이 조회되고 관심받는
    문서들을 트렌드 기반으로 추천합니다.

    Args:
        k: 추천할 인기 문서 수 (기본값: 10)
        time_window_hours: 트렌드 분석 시간 윈도우 (기본값: 24시간)
        current_user: 인증된 현재 사용자 정보

    Returns:
        ResponseModel: 인기 급상승 문서 추천 목록

    Raises:
        HTTPException: 트렌드 문서 조회 실패 시 500 에러
    """
    try:
        recommendations = await recommendation_service.recommend_trending_documents(
            k=k,
            time_window_hours=time_window_hours
        )

        return ResponseModel(
            success=True,
            data={"recommendations": recommendations}
        )

    except Exception as e:
        logger.error(f"Get trending recommendations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting trending recommendations failed: {str(e)}"
        )


@router.post("/extract/keywords")
async def extract_keywords(
    request: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    AI를 사용하여 텍스트에서 키워드를 추출합니다.

    주어진 텍스트에서 핵심적인 키워드와 구문을 AI 기반으로
    추출하고, 중요도 순으로 정렬하여 반환합니다.

    Args:
        request: 키워드 추출 요청 데이터
            - text: 분석할 텍스트
            - max_keywords: 추출할 최대 키워드 수 (기본값: 10)
        current_user: 인증된 현재 사용자 정보

    Returns:
        ResponseModel: 추출된 키워드 목록 (중요도 순)

    Raises:
        HTTPException: 텍스트가 없는 경우 400 에러,
                      키워드 추출 실패 시 500 에러
    """
    try:
        text = request.get("text")
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text is required"
            )

        max_keywords = request.get("max_keywords", 10)

        if await openai_service.is_available():
            keywords = await openai_service.extract_keywords(text, max_keywords)
        else:
            # Fall back to simpler extraction
            from app.services.search.text_analyzer import text_analyzer
            keywords = await text_analyzer.extract_keywords(text, max_keywords)

        return ResponseModel(
            success=True,
            data={"keywords": keywords}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Extract keywords error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Keyword extraction failed: {str(e)}"
        )


@router.get("/health")
async def ml_health_check(current_user: dict = Depends(get_current_user)):
    """
    ML/AI 서비스들의 상태를 확인합니다.

    RAG 서비스, 추천 서비스, OpenAI 서비스 등 모든 AI 관련
    서비스들의 연결 상태와 동작 상태를 점검합니다.

    Args:
        current_user: 인증된 현재 사용자 정보

    Returns:
        ResponseModel: 각 AI 서비스별 상태 정보

    Raises:
        HTTPException: 헬스 체크 실행 중 오류 발생 시 500 에러
    """
    try:
        health_status = {
            "rag_service": await rag_service.health_check(),
            "recommendation_service": await recommendation_service.health_check(),
            "openai_service": await openai_service.health_check()
        }

        overall_status = "healthy"
        for service, status_info in health_status.items():
            if status_info.get("status") not in ["healthy", "available"]:
                overall_status = "degraded"
                break

        return ResponseModel(
            success=True,
            data={
                "overall_status": overall_status,
                "services": health_status
            }
        )

    except Exception as e:
        logger.error(f"ML health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML health check failed: {str(e)}"
        )