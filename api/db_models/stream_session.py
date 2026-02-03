"""Stream session database model for live streaming."""

import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class StreamStatus(str, enum.Enum):
    """Stream session status enumeration."""
    SETUP = "setup"          # Court setup phase
    READY = "ready"          # Ready to start streaming
    STREAMING = "streaming"  # Active streaming
    PAUSED = "paused"        # Temporarily paused
    ENDED = "ended"          # Session ended


class StreamSession(Base):
    """Live streaming session model."""

    __tablename__ = "stream_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Session name/title (optional)
    title = Column(String(255), nullable=True)

    # Court setup (required before streaming)
    court_boundary = Column(JSON, nullable=True)

    # Session state
    status = Column(Enum(StreamStatus), default=StreamStatus.SETUP)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Recording settings
    is_recording = Column(Boolean, default=False)
    recording_s3_key = Column(String(512), nullable=True)
    recording_local_path = Column(String(512), nullable=True)

    # Live stats (updated during stream)
    total_shots = Column(Integer, default=0)
    current_rally = Column(Integer, default=0)
    shot_distribution = Column(JSON, nullable=True)  # Dict of shot_type -> count

    # Stream settings
    frame_rate = Column(Integer, default=10)  # FPS setting chosen by user
    quality = Column(String(20), default="medium")  # low, medium, high, max

    # Results (saved when session ends)
    final_report_path = Column(String(512), nullable=True)
    heatmap_paths = Column(JSON, nullable=True)

    # Heatmap and trajectory data
    foot_positions = Column(JSON, nullable=True)  # List of {x, y, timestamp} for heatmap
    shot_timeline = Column(JSON, nullable=True)   # List of {time, shot_type, confidence} for trajectory

    # Storage type
    storage_type = Column(String(10), default="local")  # "local" or "s3"
    s3_output_prefix = Column(String(512), nullable=True)

    # Relationships
    user = relationship("User", back_populates="stream_sessions")

    def __repr__(self):
        return f"<StreamSession(id={self.id}, status={self.status}, user_id={self.user_id})>"
