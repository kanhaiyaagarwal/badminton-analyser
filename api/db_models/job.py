"""Job database model."""

import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class JobStatus(str, enum.Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    """Analysis job model."""

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Video info
    video_filename = Column(String(255), nullable=False)
    video_path = Column(String(512), nullable=False)

    # Storage type and S3 keys
    storage_type = Column(String(10), default="local")  # "local" or "s3"
    s3_video_key = Column(String(512), nullable=True)   # S3 key for source video
    s3_output_prefix = Column(String(512), nullable=True)  # S3 prefix for outputs

    # Court boundary (stored as JSON)
    court_boundary = Column(JSON, nullable=True)

    # Status tracking
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    progress = Column(Float, default=0.0)  # 0-100
    status_message = Column(String(255), nullable=True)
    error_message = Column(String(1024), nullable=True)

    # Results
    report_path = Column(String(512), nullable=True)
    annotated_video_path = Column(String(512), nullable=True)
    heatmap_paths = Column(JSON, nullable=True)  # Dict of heatmap type -> path
    background_frame_path = Column(String(512), nullable=True)  # Frame for heatmap backgrounds

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="jobs")

    def __repr__(self):
        return f"<Job(id={self.id}, status={self.status}, user_id={self.user_id})>"
