"""SQLAlchemy models for the Mimic Challenge feature."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, Integer, String, Float, Enum, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship

from ....database import Base


class MimicProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class MimicSessionStatus(str, enum.Enum):
    READY = "ready"
    ACTIVE = "active"
    ENDED = "ended"


class MimicChallenge(Base):
    """A reference video that users mimic."""
    __tablename__ = "mimic_challenges"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    video_s3_key = Column(String(512), nullable=True)
    video_local_path = Column(String(512), nullable=True)
    video_duration = Column(Float, nullable=True)
    video_fps = Column(Float, nullable=True)

    thumbnail_s3_key = Column(String(512), nullable=True)
    thumbnail_local_path = Column(String(512), nullable=True)

    annotated_video_local_path = Column(String(512), nullable=True)
    annotated_video_s3_key = Column(String(512), nullable=True)

    pose_timeline = Column(JSON, nullable=True)
    total_frames = Column(Integer, default=0)
    processing_status = Column(
        Enum(MimicProcessingStatus), default=MimicProcessingStatus.PENDING
    )

    is_trending = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    play_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)


class MimicSession(Base):
    """One user attempt at a mimic challenge."""
    __tablename__ = "mimic_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    challenge_id = Column(Integer, ForeignKey("mimic_challenges.id"), nullable=False)

    source = Column(String(10), default="live")  # "live" or "upload"
    status = Column(Enum(MimicSessionStatus), default=MimicSessionStatus.READY)
    overall_score = Column(Float, default=0.0)
    duration_seconds = Column(Float, default=0.0)
    frames_compared = Column(Integer, default=0)

    score_breakdown = Column(JSON, nullable=True)
    frame_scores = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)


class MimicRecord(Base):
    """Personal best per user per challenge."""
    __tablename__ = "mimic_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    challenge_id = Column(Integer, ForeignKey("mimic_challenges.id"), nullable=False)
    best_score = Column(Float, default=0.0)
    attempt_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
