"""
유틸리티 API 엔드포인트

사용자 활동 로깅, 권한 체크, 벡터 인덱싱 등의 유틸리티 기능을 제공합니다.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import datetime

from app.core.security import get_current_user
from app.models.base import ResponseModel
from app.services.elasticsearch import elasticsearch_service
from app.services.search.vector_service import vector_service

logger = logging.getLogger("ds")

router = APIRouter()


@router.post("/log")
async def log_user_activity(
    request: Request,
    log_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    사용자 활동을 로깅합니다.

    사용자의 검색, 클릭, 다운로드 등의 활동을 Elasticsearch에 기록합니다.

    Args:
        request: FastAPI 요청 객체 (IP 주소 추출용)
        log_data: 로깅할 활동 데이터
            - action: 활동 유형 (search, view, download 등)
            - details: 활동 상세 정보
        current_user: 인증된 현재 사용자 정보

    Returns:
        ResponseModel: 로깅 성공 여부

    Raises:
        HTTPException: 로깅 실패 시 500 에러
    """
    try:
        # Get client IP
        client_ip = request.client.host
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()

        # Prepare log document
        log_document = {
            "@timestamp": datetime.utcnow().isoformat(),
            "userId": current_user.get("user_id", ""),
            "username": current_user.get("username", ""),
            "whereIp": client_ip,
            "whereChannel": request.headers.get("user-agent", ""),
            **log_data
        }

        # Index to Elasticsearch
        await elasticsearch_service.index_document(
            index="ds_log",
            doc_id=f"{current_user.get('user_id')}-{datetime.utcnow().timestamp()}",
            document=log_document
        )

        logger.info(f"User activity logged: {log_data.get('action', 'unknown')} by {current_user.get('username')}")

        return ResponseModel(
            success=True,
            message="활동이 기록되었습니다"
        )

    except Exception as e:
        logger.error(f"Log user activity error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"활동 기록 실패: {str(e)}"
        )


@router.post("/role-check")
async def check_user_role(
    user_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    사용자의 권한을 확인합니다.

    특정 사용자의 역할과 권한 정보를 조회합니다.

    Args:
        user_data: 사용자 확인 데이터
            - userId: 확인할 사용자 ID
        current_user: 인증된 현재 사용자 정보

    Returns:
        ResponseModel: 사용자 역할 및 권한 정보

    Raises:
        HTTPException: 권한 확인 실패 시 500 에러
    """
    try:
        user_id = user_data.get("userId", current_user.get("user_id"))

        # 기본값
        auth = False
        user_role = ["search"]

        logger.info(f"Role check for user {user_id}: role={user_role}, auth={auth}")

        return ResponseModel(
            success=True,
            message="권한 확인 완료",
            data={
                "userId": user_id,
                "auth": auth,
                "userRole": user_role
            }
        )

    except Exception as e:
        logger.error(f"Check user role error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"권한 확인 실패: {str(e)}"
        )


@router.post("/vector-indexing")
async def index_documents_to_vector(
    config: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    문서를 벡터 인덱스에 임베딩하여 저장합니다.

    기존 문서들을 읽어서 벡터로 변환하고 벡터 검색용 인덱스에 저장합니다.

    Args:
        config: 벡터 인덱싱 설정
            - model: 사용할 임베딩 모델
            - docType: 문서 타입 ("doc" 또는 "web")
            - targetIndex: 타겟 벡터 인덱스명
        current_user: 인증된 현재 사용자 정보

    Returns:
        ResponseModel: 벡터 인덱싱 작업 결과

    Raises:
        HTTPException: 벡터 인덱싱 실패 시 500 에러
    """
    try:
        doc_type = config.get("docType", "doc")
        target_index = config.get("targetIndex", "ds_content_vector")

        # Determine source index
        if doc_type == "doc":
            source_index = "ds_content"
        elif doc_type == "web":
            source_index = "ds_content_web"
        else:
            raise ValueError(f"Invalid docType: {doc_type}")

        # Vector indexing 작업 시작
        indexed_count = await vector_service.index_documents_for_vector_search(
            source_index=source_index,
            target_index=target_index
        )

        logger.info(f"Vector indexing completed: {indexed_count} documents indexed to {target_index}")

        return ResponseModel(
            success=True,
            message=f"벡터 인덱싱 완료: {indexed_count}개 문서 처리",
            data={
                "indexed_count": indexed_count,
                "target_index": target_index
            }
        )

    except Exception as e:
        logger.error(f"Vector indexing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"벡터 인덱싱 실패: {str(e)}"
        )