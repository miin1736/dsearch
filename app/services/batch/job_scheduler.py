"""
Job Scheduler Service using APScheduler
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
import logging

from app.core.config import settings
from app.models.batch import JobSchedule, BatchJobCreate, BatchJobType
from ..elasticsearch import ElasticsearchService
from .document_processor import DocumentProcessor
from .batch_service import batch_service

logger = logging.getLogger("ds")


class JobScheduler:
    """Service for scheduling and managing recurring batch jobs."""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.scheduled_jobs: Dict[str, JobSchedule] = {}

    async def initialize(self):
        """Initialize the job scheduler."""
        try:
            # Configure job stores
            jobstores = {
                'default': MemoryJobStore()
            }

            # Configure executors
            executors = {
                'default': AsyncIOExecutor(),
            }

            job_defaults = {
                'coalesce': False,
                'max_instances': 3,
                'misfire_grace_time': 3600  # 1 hour
            }

            # Create scheduler
            self.scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='Asia/Seoul'
            )

            # Start scheduler
            self.scheduler.start()

            logger.info("Job scheduler initialized and started")

        except Exception as e:
            logger.error(f"Failed to initialize job scheduler: {e}")
            raise

    async def shutdown(self):
        """Shutdown the job scheduler."""
        if self.scheduler:
            self.scheduler.shutdown(wait=True)
            logger.info("Job scheduler shutdown")

    async def schedule_job(self, job_schedule: JobSchedule) -> bool:
        """Schedule a recurring job."""
        try:
            if not self.scheduler:
                await self.initialize()

            # Parse cron expression
            cron_parts = job_schedule.cron_expression.split()
            if len(cron_parts) != 5:
                raise ValueError("Invalid cron expression. Expected 5 parts.")

            minute, hour, day, month, day_of_week = cron_parts

            # Add job to scheduler
            job = self.scheduler.add_job(
                func=self._execute_scheduled_job,
                trigger='cron',
                args=[job_schedule],
                id=f"scheduled_job_{job_schedule.name}",
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone=job_schedule.timezone,
                max_instances=job_schedule.max_instances,
                replace_existing=True
            )

            # Store job schedule configuration
            self.scheduled_jobs[job_schedule.name] = job_schedule

            logger.info(f"Scheduled job: {job_schedule.name} with cron: {job_schedule.cron_expression}")
            return True

        except Exception as e:
            logger.error(f"Error scheduling job {job_schedule.name}: {e}")
            return False

    async def unschedule_job(self, job_name: str) -> bool:
        """Remove a scheduled job."""
        try:
            if not self.scheduler:
                return False

            job_id = f"scheduled_job_{job_name}"
            self.scheduler.remove_job(job_id)

            # Remove from stored schedules
            if job_name in self.scheduled_jobs:
                del self.scheduled_jobs[job_name]

            logger.info(f"Unscheduled job: {job_name}")
            return True

        except Exception as e:
            logger.error(f"Error unscheduling job {job_name}: {e}")
            return False

    async def pause_job(self, job_name: str) -> bool:
        """Pause a scheduled job."""
        try:
            if not self.scheduler:
                return False

            job_id = f"scheduled_job_{job_name}"
            self.scheduler.pause_job(job_id)

            logger.info(f"Paused job: {job_name}")
            return True

        except Exception as e:
            logger.error(f"Error pausing job {job_name}: {e}")
            return False

    async def resume_job(self, job_name: str) -> bool:
        """Resume a paused job."""
        try:
            if not self.scheduler:
                return False

            job_id = f"scheduled_job_{job_name}"
            self.scheduler.resume_job(job_id)

            logger.info(f"Resumed job: {job_name}")
            return True

        except Exception as e:
            logger.error(f"Error resuming job {job_name}: {e}")
            return False

    async def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get list of all scheduled jobs."""
        try:
            if not self.scheduler:
                return []

            jobs = []
            for job in self.scheduler.get_jobs():
                job_info = {
                    "id": job.id,
                    "name": job.name or job.id,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                    "max_instances": job.max_instances,
                    "pending": len([j for j in self.scheduler.get_jobs() if j.id == job.id and j.next_run_time])
                }

                # Add schedule configuration if available
                job_name = job.id.replace("scheduled_job_", "")
                if job_name in self.scheduled_jobs:
                    schedule_config = self.scheduled_jobs[job_name]
                    job_info.update({
                        "job_type": schedule_config.job_type,
                        "parameters": schedule_config.parameters,
                        "enabled": schedule_config.enabled,
                        "cron_expression": schedule_config.cron_expression
                    })

                jobs.append(job_info)

            return jobs

        except Exception as e:
            logger.error(f"Error getting scheduled jobs: {e}")
            return []

    async def _execute_scheduled_job(self, job_schedule: JobSchedule):
        """Execute a scheduled job by creating a batch job."""
        try:
            logger.info(f"Executing scheduled job: {job_schedule.name}")

            # Check if job is enabled
            if not job_schedule.enabled:
                logger.info(f"Skipping disabled job: {job_schedule.name}")
                return

            # Create batch job
            batch_job_data = BatchJobCreate(
                job_type=job_schedule.job_type,
                name=f"{job_schedule.name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                description=f"Scheduled execution of {job_schedule.name}",
                parameters=job_schedule.parameters,
                priority="normal"
            )

            # Create and execute the job
            batch_job = await batch_service.create_job(batch_job_data)
            success = await batch_service.execute_job(batch_job.id)

            if success:
                logger.info(f"Scheduled job {job_schedule.name} started successfully as batch job {batch_job.id}")
            else:
                logger.error(f"Failed to start scheduled job {job_schedule.name}")

        except Exception as e:
            logger.error(f"Error executing scheduled job {job_schedule.name}: {e}")

    # Predefined job schedules
    async def setup_default_schedules(self):
        """Set up default scheduled jobs."""
        try:
            # Daily index maintenance at 2 AM
            index_maintenance_schedule = JobSchedule(
                job_type=BatchJobType.INDEX_MAINTENANCE,
                name="daily_index_maintenance",
                parameters={
                    "index_names": ["ds_content"],
                    "operations": ["refresh", "optimize"]
                },
                cron_expression="0 2 * * *",  # Daily at 2 AM
                enabled=True
            )

            await self.schedule_job(index_maintenance_schedule)

            # Weekly cleanup at 3 AM on Sunday
            cleanup_schedule = JobSchedule(
                job_type=BatchJobType.INDEX_MAINTENANCE,
                name="weekly_cleanup",
                parameters={
                    "cleanup_old_jobs": True,
                    "days_to_keep": 30
                },
                cron_expression="0 3 * * 0",  # Weekly on Sunday at 3 AM
                enabled=True
            )

            await self.schedule_job(cleanup_schedule)

            # Vector regeneration monthly at 4 AM on 1st day
            vector_regen_schedule = JobSchedule(
                job_type=BatchJobType.VECTOR_GENERATION,
                name="monthly_vector_regeneration",
                parameters={
                    "index_name": "ds_content",
                    "batch_size": 50
                },
                cron_expression="0 4 1 * *",  # Monthly on 1st day at 4 AM
                enabled=False  # Disabled by default as it's resource intensive
            )

            await self.schedule_job(vector_regen_schedule)

            logger.info("Default job schedules set up")

        except Exception as e:
            logger.error(f"Error setting up default schedules: {e}")

    async def run_job_immediately(self, job_schedule: JobSchedule) -> str:
        """Run a scheduled job immediately."""
        try:
            # Create batch job for immediate execution
            batch_job_data = BatchJobCreate(
                job_type=job_schedule.job_type,
                name=f"{job_schedule.name} - Manual Run - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                description=f"Manual execution of {job_schedule.name}",
                parameters=job_schedule.parameters,
                priority="high"
            )

            # Create and execute the job
            batch_job = await batch_service.create_job(batch_job_data)
            success = await batch_service.execute_job(batch_job.id)

            if success:
                logger.info(f"Manual run of {job_schedule.name} started as batch job {batch_job.id}")
                return batch_job.id
            else:
                raise Exception("Failed to start manual job execution")

        except Exception as e:
            logger.error(f"Error running job immediately {job_schedule.name}: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check scheduler health."""
        try:
            if not self.scheduler:
                return {"status": "unhealthy", "error": "Scheduler not initialized"}

            if not self.scheduler.running:
                return {"status": "unhealthy", "error": "Scheduler not running"}

            jobs = await self.get_scheduled_jobs()

            return {
                "status": "healthy",
                "scheduler_state": "running",
                "total_jobs": len(jobs),
                "enabled_jobs": len([j for j in jobs if j.get("enabled", True)]),
                "next_job": min([j["next_run"] for j in jobs if j["next_run"]], default=None)
            }

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Global instance
job_scheduler = JobScheduler()

"""
Services module initialization
"""
from ..elasticsearch import ElasticsearchService
from ..search.vector_service import VectorService
from ..search.search_service import SearchService
# 추가 서비스 import (필요 시)
# from .redis.redis_service import redis_service
# from .redis.cache_service import cache_service
# from .ml.openai_service import openai_service