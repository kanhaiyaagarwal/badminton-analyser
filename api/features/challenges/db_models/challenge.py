"""SQLAlchemy models for the Challenges feature."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, Integer, String, Float, Enum, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from ....database import Base


class ChallengeStatus(str, enum.Enum):
    READY = "ready"
    ACTIVE = "active"
    ENDED = "ended"


class ChallengeSession(Base):
    __tablename__ = "challenge_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    challenge_type = Column(String(32), nullable=False)  # plank, squat, pushup
    status = Column(Enum(ChallengeStatus), default=ChallengeStatus.READY)
    score = Column(Integer, default=0)  # reps or hold-seconds
    duration_seconds = Column(Float, default=0.0)
    extra_data = Column(JSON, nullable=True)  # feature-specific payload
    recording_s3_key = Column(String(512), nullable=True)
    recording_local_path = Column(String(512), nullable=True)
    is_recording = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)


class ChallengeRecord(Base):
    """Personal best records per user per challenge type."""
    __tablename__ = "challenge_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    challenge_type = Column(String(32), nullable=False)
    best_score = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChallengeConfig(Base):
    """Admin-configurable angle thresholds per challenge type."""
    __tablename__ = "challenge_configs"

    id = Column(Integer, primary_key=True, index=True)
    challenge_type = Column(String(32), unique=True, nullable=False)
    thresholds = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
