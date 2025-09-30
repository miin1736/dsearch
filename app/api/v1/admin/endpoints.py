"""
관리자 API 엔드포인트

시스템 관리와 모니터링을 위한 관리자 전용 API 엔드포인트들을 제공합니다.
시스템 상태 확인, 서비스 헬스 체크, 시스템 정보 조회 기능을 포함합니다.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
import logging

from app.core.security import get_super_user
from app.models.base import ResponseModel
from app.services.elasticsearch import elasticsearch_service
from app.services.redis.redis_service import redis_service

logger = logging.getLogger("ds")

router = APIRouter()


@router.get("/health")
async def health_check(current_user: dict = Depends(get_super_user)):
    """
    관리자를 위한 시스템 헬스 체크 엔드포인트.

    모든 핵심 서비스(Elasticsearch, Redis)의 상태를 확인하고
    전체 시스템의 건강 상태를 반환합니다.

    Args:
        current_user: 슈퍼유저 권한이 확인된 현재 사용자 정보

    Returns:
        ResponseModel: 시스템 전체 상태와 각 서비스별 상태 정보

    Raises:
        HTTPException: 헬스 체크 실행 중 오류 발생 시 500 에러
    """
    try:
        # Check all services
        health_status = {
            "elasticsearch": await elasticsearch_service.health_check(),
            "redis": await redis_service.health_check()
        }

        # Determine overall status
        overall_status = "healthy"
        for service, status_info in health_status.items():
            if status_info.get("status") != "healthy":
                overall_status = "unhealthy"
                break

        return ResponseModel(
            success=overall_status == "healthy",
            data={
                "overall_status": overall_status,
                "services": health_status
            }
        )

    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/system/info")
async def get_system_info(current_user: dict = Depends(get_super_user)):
    """
    시스템 정보와 통계를 조회합니다.

    Elasticsearch와 Redis의 상세한 상태 정보 및 통계를 수집하여
    시스템 모니터링과 관리를 지원합니다.

    Args:
        current_user: 슈퍼유저 권한이 확인된 현재 사용자 정보

    Returns:
        ResponseModel: 시스템 정보와 통계 데이터
            - elasticsearch: 문서 수, 인덱스 크기 등
            - redis: 메모리 사용량, 연결된 클라이언트 수 등

    Raises:
        HTTPException: 시스템 정보 조회 중 오류 발생 시 500 에러
    """
    try:
        # Get Elasticsearch info
        es_stats = await elasticsearch_service.get_index_stats("ds_content")

        # Get Redis info
        redis_info = await redis_service.info()

        return ResponseModel(
            success=True,
            data={
                "elasticsearch": {
                    "document_count": es_stats.get("document_count", 0) if es_stats else 0,
                    "index_size": es_stats.get("store_size_bytes", 0) if es_stats else 0
                },
                "redis": {
                    "used_memory": redis_info.get("used_memory_human", "Unknown"),
                    "connected_clients": redis_info.get("connected_clients", 0)
                }
            }
        )

    except Exception as e:
        logger.error(f"System info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting system info failed: {str(e)}"
        )