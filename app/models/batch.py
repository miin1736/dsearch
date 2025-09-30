"""
Batch Processing Models
"""

from typing import Optional, Dict, Any, List
from pydantic import Field
from enum import Enum
from datetime import datetime

from .base import BaseModel, TimestampMixin


class BatchJobType(str, Enum):
    """Batch job type enumeration."""
    DOCUMENT_INDEX = "document_index"
    DOCUMENT_UPDATE = "document_update"
    DOCUMENT_DELETE = "document_delete"
    BULK_INDEX = "bulk_index"
    INDEX_MAINTENANCE = "index_maintenance"
    VECTOR_GENERATION = "vector_generation"
    DATA_MIGRATION = "data_migration"


class BatchJobStatus(str, Enum):
    """Batch job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class BatchJobPriority(str, Enum):
    """Batch job priority enumeration."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class BatchJobCreate(BaseModel):
    """Batch job creation model."""

    job_type: BatchJobType
    name: str = Field(..., max_length=200)
    description: Optional[str] = Field(default=None, max_length=500)
    parameters: Optional[Dict[str, Any]] = None
    priority: BatchJobPriority = Field(default=BatchJobPriority.NORMAL)
    scheduled_at: Optional[datetime] = None
    retry_count: int = Field(default=0, ge=0, le=5)
    timeout_seconds: int = Field(default=3600, gt=0)


class BatchJobUpdate(BaseModel):
    """Batch job update model."""

    status: Optional[BatchJobStatus] = None
    progress_percent: Optional[int] = Field(default=None, ge=0, le=100)
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None


class BatchJob(BatchJobCreate, TimestampMixin):
    """Full batch job model."""

    id: str
    status: BatchJobStatus = Field(default=BatchJobStatus.PENDING)
    progress_percent: int = Field(default=0, ge=0, le=100)
    message: Optional[str] = None

    # Results and errors
    result: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Processing info
    worker_id: Optional[str] = None
    attempts: int = Field(default=0)

    class Config:
        orm_mode = True


class BatchJobStats(BaseModel):
    """Batch job statistics."""

    total_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    cancelled_jobs: int

    avg_processing_time_seconds: Optional[float] = None
    success_rate_percent: Optional[float] = None


class BulkIndexJob(BaseModel):
    """Bulk index job parameters."""

    source_path: str
    index_name: str
    document_type: str
    batch_size: int = Field(default=100, gt=0)
    include_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    overwrite_existing: bool = Field(default=False)
    generate_vectors: bool = Field(default=True)


class DocumentIndexJob(BaseModel):
    """Document index job parameters."""

    file_path: str
    document_id: Optional[str] = None
    category: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    generate_vector: bool = Field(default=True)
    extract_text: bool = Field(default=True)


class IndexMaintenanceJob(BaseModel):
    """Index maintenance job parameters."""

    index_names: List[str]
    operations: List[str] = Field(
        default=["optimize", "refresh"],
        description="Operations to perform: optimize, refresh, flush, etc."
    )
    force_merge_max_segments: Optional[int] = None


class JobSchedule(BaseModel):
    """Job scheduling configuration."""

    job_type: BatchJobType
    name: str
    parameters: Dict[str, Any]
    cron_expression: str = Field(
        ...,
        description="Cron expression for scheduling (e.g., '0 2 * * *' for daily at 2 AM)"
    )
    enabled: bool = Field(default=True)
    timezone: str = Field(default="Asia/Seoul")
    max_instances: int = Field(default=1, ge=1)

    class Config:
        orm_mode = True