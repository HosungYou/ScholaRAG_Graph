"""
Job Store - Persistent background job tracking.

Stores job status in PostgreSQL for reliability and recovery.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    # BUG-028: Added INTERRUPTED for jobs killed by server restart
    INTERRUPTED = "interrupted"


@dataclass
class Job:
    """Represents a background job."""
    id: str
    job_type: str  # e.g., "import", "embedding", "export"
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    message: str = ""
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "job_type": self.job_type,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        """Create Job from dictionary."""
        return cls(
            id=data["id"],
            job_type=data["job_type"],
            status=JobStatus(data["status"]),
            progress=data.get("progress", 0.0),
            message=data.get("message", ""),
            result=data.get("result"),
            error=data.get("error"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            metadata=data.get("metadata", {}),
        )


class JobStore:
    """
    Persistent job store using PostgreSQL.

    Falls back to in-memory storage if database is unavailable.
    """

    # SQL for creating jobs table
    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS jobs (
        id UUID PRIMARY KEY,
        job_type VARCHAR(50) NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        progress REAL DEFAULT 0.0,
        message TEXT,
        result JSONB,
        error TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        metadata JSONB DEFAULT '{}'::jsonb
    );

    CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
    CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type);
    CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
    """

    def __init__(self, db_connection=None):
        self.db = db_connection
        self._memory_store: dict[str, Job] = {}

    async def init_table(self) -> None:
        """Create jobs table if it doesn't exist."""
        if self.db:
            try:
                await self.db.execute(self.CREATE_TABLE_SQL)
                logger.info("Jobs table initialized")
            except Exception as e:
                logger.warning(f"Failed to create jobs table: {type(e).__name__}")

    async def create_job(
        self,
        job_type: str,
        metadata: dict = None,
    ) -> Job:
        """Create a new job."""
        job = Job(
            id=str(uuid4()),
            job_type=job_type,
            metadata=metadata or {},
        )

        if self.db:
            try:
                await self.db.execute(
                    """
                    INSERT INTO jobs (id, job_type, status, progress, message, metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    job.id,
                    job.job_type,
                    job.status.value,
                    job.progress,
                    job.message,
                    json.dumps(job.metadata),
                    job.created_at,
                    job.updated_at,
                )
            except Exception as e:
                logger.warning(f"Failed to persist job to DB: {type(e).__name__}")
                self._memory_store[job.id] = job
        else:
            self._memory_store[job.id] = job

        return job

    def _parse_json_field(self, value) -> Optional[dict]:
        """Parse a JSON field that might be a string or already a dict."""
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        if self.db:
            try:
                row = await self.db.fetchrow(
                    "SELECT * FROM jobs WHERE id = $1",
                    job_id,
                )
                if row:
                    return Job(
                        id=str(row["id"]),
                        job_type=row["job_type"],
                        status=JobStatus(row["status"]),
                        progress=row["progress"] or 0.0,
                        message=row["message"] or "",
                        result=self._parse_json_field(row["result"]),
                        error=row["error"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        started_at=row["started_at"],
                        completed_at=row["completed_at"],
                        metadata=self._parse_json_field(row["metadata"]) or {},
                    )
            except Exception as e:
                logger.warning(f"Failed to get job from DB: {type(e).__name__}")

        return self._memory_store.get(job_id)

    async def update_job(
        self,
        job_id: str,
        status: JobStatus = None,
        progress: float = None,
        message: str = None,
        result: dict = None,
        error: str = None,
        metadata: dict = None,
    ) -> Optional[Job]:
        """Update job status, progress, and metadata.

        BUG-028 Extension: Added metadata parameter to support checkpoint saving.
        When metadata is provided, it merges with existing metadata (not replace).
        """
        job = await self.get_job(job_id)
        if not job:
            return None

        # Update fields
        if status is not None:
            job.status = status
            if status == JobStatus.RUNNING and not job.started_at:
                job.started_at = datetime.now()
            elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                job.completed_at = datetime.now()

        if progress is not None:
            job.progress = progress
        if message is not None:
            job.message = message
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error

        # BUG-028 Extension: Merge metadata for checkpoint support
        if metadata is not None:
            job.metadata = {**job.metadata, **metadata}

        job.updated_at = datetime.now()

        # Persist
        if self.db:
            try:
                await self.db.execute(
                    """
                    UPDATE jobs
                    SET status = $2, progress = $3, message = $4, result = $5,
                        error = $6, updated_at = $7, started_at = $8, completed_at = $9,
                        metadata = $10
                    WHERE id = $1
                    """,
                    job_id,
                    job.status.value,
                    job.progress,
                    job.message,
                    json.dumps(job.result) if job.result else None,
                    job.error,
                    job.updated_at,
                    job.started_at,
                    job.completed_at,
                    json.dumps(job.metadata),
                )
            except Exception as e:
                logger.warning(f"Failed to update job in DB: {type(e).__name__}")
                self._memory_store[job_id] = job
        else:
            self._memory_store[job_id] = job

        return job

    async def list_jobs(
        self,
        job_type: str = None,
        status: JobStatus = None,
        limit: int = 50,
    ) -> list[Job]:
        """List jobs with optional filters."""
        jobs = []

        if self.db:
            try:
                query = "SELECT * FROM jobs WHERE 1=1"
                params = []
                param_idx = 1

                if job_type:
                    query += f" AND job_type = ${param_idx}"
                    params.append(job_type)
                    param_idx += 1

                if status:
                    query += f" AND status = ${param_idx}"
                    params.append(status.value)
                    param_idx += 1

                query += f" ORDER BY created_at DESC LIMIT ${param_idx}"
                params.append(limit)

                rows = await self.db.fetch(query, *params)
                for row in rows:
                    jobs.append(Job(
                        id=str(row["id"]),
                        job_type=row["job_type"],
                        status=JobStatus(row["status"]),
                        progress=row["progress"] or 0.0,
                        message=row["message"] or "",
                        result=self._parse_json_field(row["result"]),
                        error=row["error"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        started_at=row["started_at"],
                        completed_at=row["completed_at"],
                        metadata=self._parse_json_field(row["metadata"]) or {},
                    ))
                return jobs
            except Exception as e:
                logger.warning(f"Failed to list jobs from DB: {type(e).__name__}")

        # Fallback to memory store
        memory_jobs = list(self._memory_store.values())
        if job_type:
            memory_jobs = [j for j in memory_jobs if j.job_type == job_type]
        if status:
            memory_jobs = [j for j in memory_jobs if j.status == status]
        return sorted(memory_jobs, key=lambda j: j.created_at, reverse=True)[:limit]

    async def cleanup_old_jobs(self, days: int = 7) -> int:
        """Delete jobs older than specified days."""
        if self.db:
            try:
                # Use parameterized interval by calculating the cutoff timestamp
                result = await self.db.execute(
                    """
                    DELETE FROM jobs
                    WHERE created_at < NOW() - ($1 || ' days')::INTERVAL
                    AND status IN ('completed', 'failed', 'cancelled')
                    """,
                    str(days),
                )
                # Parse "DELETE N" to get count
                count = int(result.split()[-1]) if result else 0
                logger.info(f"Cleaned up {count} old jobs")
                return count
            except Exception as e:
                logger.warning(f"Failed to cleanup jobs: {type(e).__name__}: {e}")
                return 0
        return 0

    async def mark_running_as_interrupted(self) -> int:
        """
        BUG-028: Mark all RUNNING jobs as INTERRUPTED on server startup.

        When server restarts (e.g., Render auto-deploy), background tasks are killed.
        This marks orphaned jobs so users can see what happened and retry if needed.

        Returns:
            Number of jobs marked as interrupted
        """
        if self.db:
            try:
                # Find and update all RUNNING jobs
                result = await self.db.execute(
                    """
                    UPDATE jobs
                    SET status = 'interrupted',
                        error = 'Server restarted during job execution. Please retry.',
                        updated_at = NOW()
                    WHERE status = 'running'
                    """
                )
                # Parse "UPDATE N" to get count
                count = int(result.split()[-1]) if result else 0
                if count > 0:
                    logger.warning(f"BUG-028: Marked {count} running jobs as interrupted (server restart)")
                return count
            except Exception as e:
                logger.warning(f"Failed to mark running jobs as interrupted: {type(e).__name__}: {e}")
                return 0

        # Fallback for memory store
        count = 0
        for job_id, job in self._memory_store.items():
            if job.status == JobStatus.RUNNING:
                job.status = JobStatus.INTERRUPTED
                job.error = "Server restarted during job execution. Please retry."
                job.updated_at = datetime.now()
                count += 1
        return count
