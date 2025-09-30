"""
배치 처리 API 엔드포인트

대용량 문서 처리, 데이터 인덱싱, 시스템 유지보수 등을 위한
배치 작업 관리 API 엔드포인트들을 제공합니다.
작업 생성, 실행, 모니터링, 취소 기능을 포함합니다.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
import logging

from app.core.security import get_current_user, get_super_user
from app.models.batch import BatchJob, BatchJobCreate, BatchJobUpdate, BatchJobStatus, BatchJobType
from app.models.base import ResponseModel
from app.services.batch.batch_service import batch_service

logger = logging.getLogger("ds")

router = APIRouter()


@router.post("/jobs", response_model=BatchJob)
async def create_batch_job(
    job_data: BatchJobCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    새로운 배치 작업을 생성합니다.

    제공된 작업 데이터를 기반으로 새로운 배치 작업을 생성하고
    작업 큐에 추가합니다.

    Args:
        job_data: 배치 작업 생성 데이터 (작업 유형, 매개변수 등)
        current_user: 인증된 현재 사용자 정보

    Returns:
        BatchJob: 생성된 배치 작업 정보

    Raises:
        HTTPException: 배치 작업 생성 중 오류 발생 시 500 에러
    """
    try:
        job = await batch_service.create_job(job_data)
        logger.info(f"User {current_user.get('username')} created batch job {job.id}")
        return job

    except Exception as e:
        logger.error(f"Create batch job error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Creating batch job failed: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=BatchJob)
async def get_batch_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    ID로 배치 작업을 조회합니다.

    지정된 ID의 배치 작업 정보와 현재 상태를 반환합니다.

    Args:
        job_id: 조회할 배치 작업의 고유 ID
        current_user: 인증된 현재 사용자 정보

    Returns:
        BatchJob: 배치 작업 정보 및 상태

    Raises:
        HTTPException: 작업을 찾을 수 없는 경우 404 에러,
                      기타 오류 발생 시 500 에러
    """
    try:
        job = await batch_service.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Batch job not found"
            )

        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get batch job error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting batch job failed: {str(e)}"
        )


@router.get("/jobs", response_model=List[BatchJob])
async def list_batch_jobs(
    status_filter: Optional[BatchJobStatus] = None,
    job_type: Optional[BatchJobType] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """
    필터링 옵션과 함께 배치 작업 목록을 조회합니다.

    상태, 작업 유형 등의 필터를 적용하여 배치 작업 목록을 조회하고
    페이지네이션을 지원합니다.

    Args:
        status_filter: 상태별 필터링 (선택사항)
        job_type: 작업 유형별 필터링 (선택사항)
        limit: 반환할 최대 작업 수 (기본값: 50)
        current_user: 인증된 현재 사용자 정보

    Returns:
        List[BatchJob]: 필터링된 배치 작업 목록

    Raises:
        HTTPException: 작업 목록 조회 중 오류 발생 시 500 에러
    """
    try:
        jobs = await batch_service.list_jobs(
            status=status_filter,
            job_type=job_type,
            limit=limit
        )

        return jobs

    except Exception as e:
        logger.error(f"List batch jobs error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Listing batch jobs failed: {str(e)}"
        )


@router.post("/jobs/{job_id}/execute")
async def execute_batch_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    배치 작업을 실행합니다.

    지정된 배치 작업을 큐에서 실행 상태로 변경하고
    실제 처리를 시작합니다.

    Args:
        job_id: 실행할 배치 작업의 고유 ID
        current_user: 인증된 현재 사용자 정보

    Returns:
        ResponseModel: 작업 실행 시작 결과

    Raises:
        HTTPException: 작업 실행 실패 시 400 에러,
                      기타 오류 발생 시 500 에러
    """
    try:
        success = await batch_service.execute_job(job_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to execute job"
            )

        logger.info(f"User {current_user.get('username')} executed batch job {job_id}")

        return ResponseModel(
            success=True,
            message="Job execution started",
            data={"job_id": job_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Execute batch job error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Executing batch job failed: {str(e)}"
        )


@router.post("/jobs/{job_id}/cancel")
async def cancel_batch_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    실행 중인 배치 작업을 취소합니다.

    진행 중이거나 대기 중인 배치 작업을 안전하게 취소하고
    관련 리소스를 정리합니다.

    Args:
        job_id: 취소할 배치 작업의 고유 ID
        current_user: 인증된 현재 사용자 정보

    Returns:
        ResponseModel: 작업 취소 결과

    Raises:
        HTTPException: 작업 취소 실패 시 400 에러,
                      기타 오류 발생 시 500 에러
    """
    try:
        success = await batch_service.cancel_job(job_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel job"
            )

        logger.info(f"User {current_user.get('username')} cancelled batch job {job_id}")

        return ResponseModel(
            success=True,
            message="Job cancelled",
            data={"job_id": job_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel batch job error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cancelling batch job failed: {str(e)}"
        )


@router.get("/stats")
async def get_batch_statistics(
    current_user: dict = Depends(get_super_user)
):
    """
    배치 작업 통계를 조회합니다 (관리자 전용).

    전체 배치 작업의 상태별 통계, 성공률, 평균 실행 시간 등
    시스템 모니터링에 필요한 통계 정보를 제공합니다.

    Args:
        current_user: 슈퍼유저 권한이 확인된 현재 사용자 정보

    Returns:
        ResponseModel: 배치 작업 통계 데이터

    Raises:
        HTTPException: 통계 조회 중 오류 발생 시 500 에러
    """
    try:
        stats = await batch_service.get_job_statistics()

        return ResponseModel(
            success=True,
            data=stats
        )

    except Exception as e:
        logger.error(f"Get batch statistics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Getting batch statistics failed: {str(e)}"
        )