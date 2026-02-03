"""Job Pydantic models."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class JobCreate(BaseModel):
    """Schema for job creation (internal use)."""
    video_filename: str
    video_path: str


class JobResponse(BaseModel):
    """Schema for job response."""
    id: int
    video_filename: str
    status: str
    progress: float
    status_message: Optional[str] = None
    error_message: Optional[str] = None
    court_boundary: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    has_results: bool = False

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_results(cls, job) -> "JobResponse":
        """Create response with has_results flag."""
        return cls(
            id=job.id,
            video_filename=job.video_filename,
            status=job.status.value if hasattr(job.status, 'value') else job.status,
            progress=job.progress,
            status_message=job.status_message,
            error_message=job.error_message,
            court_boundary=job.court_boundary,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            has_results=job.report_path is not None
        )


class JobListResponse(BaseModel):
    """Schema for list of jobs."""
    jobs: List[JobResponse]
    total: int
