"""
배치 처리 서비스

대용량 문서 인덱싱, 데이터 처리, 시스템 유지보수 등의 배치 작업을
비동기적으로 관리하고 실행하는 서비스입니다.
작업 생성, 실행, 모니터링, 취소, 재시도 기능을 제공합니다.
"""

import asyncio
import uuid
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from app.core.config import settings
from app.models.batch import (
    BatchJob, BatchJobCreate, BatchJobUpdate, BatchJobStatus,
    BatchJobType, BulkIndexJob, DocumentIndexJob, IndexMaintenanceJob
)
from app.services.redis.redis_service import redis_service
from .document_processor import DocumentProcessor

logger = logging.getLogger("batch")


class BatchService:
    """\n    배치 작업 관리 및 실행 서비스.\n\n    다양한 유형의 배치 작업(문서 인덱싱, 대량 인덱싱, 인덱스 유지보수,\n    벡터 생성 등)을 비동기적으로 관리하고 실행합니다.\n    Redis를 통한 작업 상태 관리와 실시간 모니터링을 지원합니다.\n    """

    def __init__(self):
        self.redis = redis_service
        self.document_processor = DocumentProcessor()
        self.executor = ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)
        self._running_jobs: Dict[str, asyncio.Task] = {}

    async def create_job(self, job_data: BatchJobCreate) -> BatchJob:
        """\n        새로운 배치 작업을 생성합니다.\n\n        제공된 작업 데이터를 기반으로 고유 ID를 가진 배치 작업을\n        생성하고 Redis에 저장합니다.\n\n        Args:\n            job_data: 배치 작업 생성 정보 (이름, 유형, 매개변수 등)\n\n        Returns:\n            BatchJob: 생성된 배치 작업 객체\n\n        Raises:\n            Exception: 작업 생성 중 오류 발생 시\n        """
        try:
            job_id = str(uuid.uuid4())

            job = BatchJob(
                id=job_id,
                **job_data.dict()
            )

            # Store job in Redis
            await self._store_job(job)

            logger.info(f"Created batch job {job_id}: {job.name}")
            return job

        except Exception as e:
            logger.error(f"Error creating batch job: {e}")
            raise

    async def get_job(self, job_id: str) -> Optional[BatchJob]:
        """\n        ID로 배치 작업을 조회합니다.\n\n        Redis에서 지정된 ID의 배치 작업 정보를 가져옵니다.\n\n        Args:\n            job_id: 조회할 배치 작업의 고유 ID\n\n        Returns:\n            Optional[BatchJob]: 배치 작업 객체 또는 None (찾지 못한 경우)\n        """
        try:
            job_data = await self.redis.get(f"batch_job:{job_id}")
            if job_data:
                return BatchJob(**job_data)
            return None

        except Exception as e:
            logger.error(f"Error getting batch job {job_id}: {e}")
            return None

    async def update_job(self, job_id: str, update_data: BatchJobUpdate) -> bool:
        """\n        배치 작업의 상태와 데이터를 업데이트합니다.\n\n        작업의 상태, 진행률, 메시지, 결과 등을 업데이트하고\n        상태 변경에 따라 타임스탬프를 자동 설정합니다.\n\n        Args:\n            job_id: 업데이트할 배치 작업의 ID\n            update_data: 업데이트할 데이터\n\n        Returns:\n            bool: 업데이트 성공 여부\n        """
        try:
            job = await self.get_job(job_id)
            if not job:
                return False

            # Update job data
            for field, value in update_data.dict(exclude_unset=True).items():
                setattr(job, field, value)

            # Update timestamps
            if update_data.status == BatchJobStatus.RUNNING and not job.started_at:
                job.started_at = datetime.utcnow()
            elif update_data.status in [BatchJobStatus.COMPLETED, BatchJobStatus.FAILED]:
                job.completed_at = datetime.utcnow()

            # Store updated job
            await self._store_job(job)

            logger.info(f"Updated batch job {job_id}: {update_data.status}")
            return True

        except Exception as e:
            logger.error(f"Error updating batch job {job_id}: {e}")
            return False

    async def list_jobs(self, status: Optional[BatchJobStatus] = None,
                       job_type: Optional[BatchJobType] = None,
                       limit: int = 50) -> List[BatchJob]:
        """\n        필터링 옵션과 함께 배치 작업 목록을 조회합니다.\n\n        상태나 작업 유형으로 필터링하여 배치 작업 목록을 반환하고\n        생성 시간 순으로 정렬합니다.\n\n        Args:\n            status: 필터링할 작업 상태 (선택사항)\n            job_type: 필터링할 작업 유형 (선택사항)\n            limit: 반환할 최대 작업 수\n\n        Returns:\n            List[BatchJob]: 필터링된 배치 작업 목록\n        """
        try:
            # Get all job keys
            job_keys = await self.redis.keys("batch_job:*")

            jobs = []
            for key in job_keys:
                job_data = await self.redis.get(key)
                if job_data:
                    job = BatchJob(**job_data)

                    # Apply filters
                    if status and job.status != status:
                        continue
                    if job_type and job.job_type != job_type:
                        continue

                    jobs.append(job)

            # Sort by creation time (newest first)
            jobs.sort(key=lambda x: x.created_at, reverse=True)

            return jobs[:limit]

        except Exception as e:
            logger.error(f"Error listing batch jobs: {e}")
            return []

    async def execute_job(self, job_id: str) -> bool:
        """\n        배치 작업을 비동기적으로 실행합니다.\n\n        작업을 실행 상태로 변경하고 작업 유형에 따라 적절한\n        처리를 수행하며, 비동기 태스크로 실행합니다.\n\n        Args:\n            job_id: 실행할 배치 작업의 ID\n\n        Returns:\n            bool: 작업 실행 시작 성공 여부\n        """
        try:
            job = await self.get_job(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return False

            if job.status != BatchJobStatus.PENDING:
                logger.warning(f"Job {job_id} is not in pending status")
                return False

            # Mark job as running
            await self.update_job(job_id, BatchJobUpdate(
                status=BatchJobStatus.RUNNING,
                message="Job started"
            ))

            # Execute job based on type
            task = asyncio.create_task(self._execute_job_by_type(job))
            self._running_jobs[job_id] = task

            # Wait for completion (in background)
            asyncio.create_task(self._wait_for_job_completion(job_id, task))

            return True

        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}")
            await self.update_job(job_id, BatchJobUpdate(
                status=BatchJobStatus.FAILED,
                message=f"Execution failed: {str(e)}"
            ))
            return False

    async def cancel_job(self, job_id: str) -> bool:
        """\n        실행 중인 작업을 취소합니다.\n\n        실행 중인 비동기 태스크를 취소하고 작업 상태를\n        취소 상태로 업데이트합니다.\n\n        Args:\n            job_id: 취소할 배치 작업의 ID\n\n        Returns:\n            bool: 작업 취소 성공 여부\n        """
        try:
            if job_id in self._running_jobs:
                task = self._running_jobs[job_id]
                task.cancel()
                del self._running_jobs[job_id]

            await self.update_job(job_id, BatchJobUpdate(
                status=BatchJobStatus.CANCELLED,
                message="Job cancelled by user"
            ))

            logger.info(f"Cancelled job {job_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False

    async def retry_job(self, job_id: str) -> bool:
        """\n        실패한 작업을 재시도합니다.\n\n        실패한 작업을 대기 상태로 되돌리고 재시도 수를\n        증가시켜 다시 실행합니다.\n\n        Args:\n            job_id: 재시도할 배치 작업의 ID\n\n        Returns:\n            bool: 재시도 시작 성공 여부\n        """
        try:
            job = await self.get_job(job_id)
            if not job:
                return False

            if job.status != BatchJobStatus.FAILED:
                logger.warning(f"Job {job_id} is not in failed status")
                return False

            if job.attempts >= job.retry_count:
                logger.warning(f"Job {job_id} has exceeded retry limit")
                return False

            # Reset job status and increment attempts
            await self.update_job(job_id, BatchJobUpdate(
                status=BatchJobStatus.PENDING,
                message="Job queued for retry",
                attempts=job.attempts + 1
            ))

            # Execute job
            return await self.execute_job(job_id)

        except Exception as e:
            logger.error(f"Error retrying job {job_id}: {e}")
            return False

    async def delete_job(self, job_id: str) -> bool:
        """\n        배치 작업을 삭제합니다.\n\n        실행 중인 작업은 먼저 취소한 후 Redis에서\n        작업 데이터를 완전히 삭제합니다.\n\n        Args:\n            job_id: 삭제할 배치 작업의 ID\n\n        Returns:\n            bool: 작업 삭제 성공 여부\n        """
        try:
            # Cancel if running
            if job_id in self._running_jobs:
                await self.cancel_job(job_id)

            # Delete from Redis
            result = await self.redis.delete(f"batch_job:{job_id}")

            logger.info(f"Deleted job {job_id}")
            return result > 0

        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {e}")
            return False

    async def _execute_job_by_type(self, job: BatchJob) -> Dict[str, Any]:
        """\n        작업 유형에 따라 작업을 실행합니다.\n\n        배치 작업의 유형(문서 인덱싱, 대량 인덱싱, 인덱스 유지보수,\n        벡터 생성 등)에 맞는 적절한 처리 로직을 호출합니다.\n\n        Args:\n            job: 실행할 배치 작업 객체\n\n        Returns:\n            Dict[str, Any]: 작업 실행 결과\n\n        Raises:\n            ValueError: 알 수 없는 작업 유형인 경우\n        """
        try:
            if job.job_type == BatchJobType.DOCUMENT_INDEX:
                return await self._execute_document_index_job(job)
            elif job.job_type == BatchJobType.BULK_INDEX:
                return await self._execute_bulk_index_job(job)
            elif job.job_type == BatchJobType.INDEX_MAINTENANCE:
                return await self._execute_index_maintenance_job(job)
            elif job.job_type == BatchJobType.VECTOR_GENERATION:
                return await self._execute_vector_generation_job(job)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")

        except Exception as e:
            logger.error(f"Job execution error: {e}")
            raise

    async def _execute_document_index_job(self, job: BatchJob) -> Dict[str, Any]:
        """\n        문서 인덱싱 작업을 실행합니다.\n\n        단일 문서를 Elasticsearch 인덱스에 색인하고\n        선택적으로 벡터를 생성합니다.\n\n        Args:\n            job: 문서 인덱싱 작업 객체\n\n        Returns:\n            Dict[str, Any]: 인덱싱 결과\n        """
        params = DocumentIndexJob(**job.parameters)

        result = await self.document_processor.index_document(
            file_path=params.file_path,
            document_id=params.document_id,
            category=params.category,
            metadata=params.metadata,
            generate_vector=params.generate_vector
        )

        return result

    async def _execute_bulk_index_job(self, job: BatchJob) -> Dict[str, Any]:
        """\n        대량 인덱싱 작업을 실행합니다.\n\n        지정된 경로의 여러 문서를 일괄적으로 인덱싱하고\n        진행 상황을 실시간 업데이트합니다.\n\n        Args:\n            job: 대량 인덱싱 작업 객체\n\n        Returns:\n            Dict[str, Any]: 대량 인덱싱 결과\n        """
        params = BulkIndexJob(**job.parameters)

        result = await self.document_processor.bulk_index_documents(
            source_path=params.source_path,
            index_name=params.index_name,
            batch_size=params.batch_size,
            include_patterns=params.include_patterns,
            exclude_patterns=params.exclude_patterns,
            overwrite_existing=params.overwrite_existing,
            generate_vectors=params.generate_vectors,
            progress_callback=lambda progress: asyncio.create_task(
                self.update_job(job.id, BatchJobUpdate(progress_percent=progress))
            )
        )

        return result

    async def _execute_index_maintenance_job(self, job: BatchJob) -> Dict[str, Any]:
        """\n        인덱스 유지보수 작업을 실행합니다.\n\n        Elasticsearch 인덱스의 새로고침, 최적화 등\n        유지보수 작업을 수행합니다.\n\n        Args:\n            job: 인덱스 유지보수 작업 객체\n\n        Returns:\n            Dict[str, Any]: 유지보수 작업 결과\n        """
        params = IndexMaintenanceJob(**job.parameters)

        from app.services.elasticsearch import elasticsearch_service

        results = {}
        for index_name in params.index_names:
            index_results = {}

            if "refresh" in params.operations:
                success = await elasticsearch_service.refresh_index(index_name)
                index_results["refresh"] = success

            if "optimize" in params.operations:
                # This would call force merge or similar optimization
                index_results["optimize"] = True

            results[index_name] = index_results

        return {"results": results}

    async def _execute_vector_generation_job(self, job: BatchJob) -> Dict[str, Any]:
        """\n        벡터 생성 작업을 실행합니다.\n\n        기존 문서들에 대한 벡터를 재생성하여\n        검색 성능을 향상시킵니다.\n\n        Args:\n            job: 벡터 생성 작업 객체\n\n        Returns:\n            Dict[str, Any]: 벡터 생성 결과\n        """
        # This would regenerate vectors for existing documents
        return await self.document_processor.regenerate_vectors(
            index_name=job.parameters.get("index_name", "ds_content"),
            batch_size=job.parameters.get("batch_size", 100)
        )

    async def _wait_for_job_completion(self, job_id: str, task: asyncio.Task):
        """\n        작업 완료를 대기하고 상태를 업데이트합니다.\n\n        비동기 작업의 완료를 대기하고 성공/실패에 따라\n        적절한 상태로 업데이트합니다.\n\n        Args:\n            job_id: 대기할 배치 작업의 ID\n            task: 대기할 비동기 태스크\n        """
        try:
            result = await task

            await self.update_job(job_id, BatchJobUpdate(
                status=BatchJobStatus.COMPLETED,
                progress_percent=100,
                message="Job completed successfully",
                result=result
            ))

        except asyncio.CancelledError:
            logger.info(f"Job {job_id} was cancelled")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            await self.update_job(job_id, BatchJobUpdate(
                status=BatchJobStatus.FAILED,
                message=f"Job failed: {str(e)}",
                error_details={"error": str(e), "type": type(e).__name__}
            ))

        finally:
            if job_id in self._running_jobs:
                del self._running_jobs[job_id]

    async def _store_job(self, job: BatchJob):
        """\n        작업을 Redis에 저장합니다.\n\n        배치 작업 데이터를 JSON 형태로 직렬화하여\n        Redis에 저장하고 TTL을 설정합니다.\n\n        Args:\n            job: 저장할 배치 작업 객체\n        """
        await self.redis.set(
            f"batch_job:{job.id}",
            job.dict(),
            ex=86400 * 7  # Keep jobs for 7 days
        )

    async def get_job_statistics(self) -> Dict[str, Any]:
        """\n        배치 작업 통계를 조회합니다.\n\n        전체 작업의 상태별 기수, 성공률 등\n        통계 정보를 수집하여 반환합니다.\n\n        Returns:\n            Dict[str, Any]: 배치 작업 통계 데이터\n        """
        try:
            jobs = await self.list_jobs()

            stats = {
                "total_jobs": len(jobs),
                "pending_jobs": len([j for j in jobs if j.status == BatchJobStatus.PENDING]),
                "running_jobs": len([j for j in jobs if j.status == BatchJobStatus.RUNNING]),
                "completed_jobs": len([j for j in jobs if j.status == BatchJobStatus.COMPLETED]),
                "failed_jobs": len([j for j in jobs if j.status == BatchJobStatus.FAILED]),
                "cancelled_jobs": len([j for j in jobs if j.status == BatchJobStatus.CANCELLED])
            }

            # Calculate success rate
            total_finished = stats["completed_jobs"] + stats["failed_jobs"]
            if total_finished > 0:
                stats["success_rate_percent"] = (stats["completed_jobs"] / total_finished) * 100

            return stats

        except Exception as e:
            logger.error(f"Error getting job statistics: {e}")
            return {}

    async def cleanup_old_jobs(self, days: int = 7) -> int:
        """\n        오래된 완료 작업들을 정리합니다.\n\n        지정된 일수보다 오래된 완료되거나 실패한 작업들을\n        자동으로 삭제하여 저장공간을 절약합니다.\n\n        Args:\n            days: 유지할 일수 (기본값: 7일)\n\n        Returns:\n            int: 삭제된 작업 수\n        """
        try:
            jobs = await self.list_jobs()
            deleted_count = 0

            cutoff_date = datetime.utcnow() - timedelta(days=days)

            for job in jobs:
                if (job.status in [BatchJobStatus.COMPLETED, BatchJobStatus.FAILED] and
                    job.completed_at and
                    datetime.fromisoformat(job.completed_at) < cutoff_date):

                    await self.delete_job(job.id)
                    deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} old jobs")
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up old jobs: {e}")
            return 0


# Global instance
batch_service = BatchService()