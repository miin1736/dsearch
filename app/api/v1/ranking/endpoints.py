"""
Ranking API Endpoints - 인기검색어, 최근검색어, 인기문서
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from app.models.ranking import (
    RankingSearchRequest,
    RankingDocumentRequest,
    RecentSearchRequest,
    RankingSearchResponse,
    RankingDocumentResponse,
    RecentSearchResponse
)
from app.services.ranking_service import ranking_service
from app.core.security import get_current_user_optional

logger = logging.getLogger("ds")

router = APIRouter()


@router.post("/search", response_model=RankingSearchResponse)
async def get_search_ranking(
    ds_request: RankingSearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_optional)
):
    """
    인기 검색어 조회

    - **howRequestDays**: 조회할 일수 (기본: 7일)
    - **howRequestTopN**: 상위 N개 검색어 (기본: 10개)

    Returns:
        인기 검색어 목록 (label, value)
    """
    try:
        ranking_items = await ranking_service.get_search_ranking(ds_request)
        return RankingSearchResponse(ds_response=ranking_items)

    except Exception as e:
        logger.error(f"Error getting search ranking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인기 검색어 조회 실패: {str(e)}"
        )


@router.post("/document", response_model=RankingDocumentResponse)
async def get_document_ranking(
    ds_request: RankingDocumentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_optional)
):
    """
    인기 문서 조회

    - **howRequestDays**: 조회할 일수 (기본: 7일)
    - **howRequestTopN**: 상위 N개 문서 (기본: 10개)

    Returns:
        인기 문서 목록 (순위, 제목, 조회수, ID)
    """
    try:
        ranking_items = await ranking_service.get_document_ranking(ds_request)
        return RankingDocumentResponse(ds_response=ranking_items)

    except Exception as e:
        logger.error(f"Error getting document ranking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인기 문서 조회 실패: {str(e)}"
        )


@router.post("/recent", response_model=RecentSearchResponse)
async def get_recent_searches(
    ds_request: RecentSearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_optional)
):
    """
    최근 검색어 조회

    - **whoUserId**: 사용자 ID (선택사항, 없으면 전체)
    - **whoUserName**: 사용자 이름/팀 (선택사항)
    - **howRequestRecentText**: 최근 검색어 개수 (기본: 10개)
    - **whenCreated**: 조회할 일수 (기본: 7일)

    Returns:
        최근 검색어 목록 (label, value)
    """
    try:
        recent_items = await ranking_service.get_recent_searches(ds_request)
        return RecentSearchResponse(ds_response=recent_items)

    except Exception as e:
        logger.error(f"Error getting recent searches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"최근 검색어 조회 실패: {str(e)}"
        )