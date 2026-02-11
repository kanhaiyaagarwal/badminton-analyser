"""Pydantic schemas for the Challenges feature."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ChallengeCreate(BaseModel):
    challenge_type: str  # "plank", "squat", "pushup"


class ChallengeResponse(BaseModel):
    id: int
    challenge_type: str
    status: str
    score: int
    duration_seconds: float
    personal_best: Optional[int] = None
    has_recording: bool = False
    created_at: datetime
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChallengeSessionStart(BaseModel):
    """Returned when a challenge session is started."""
    session_id: int
    challenge_type: str
    ws_url: str  # WebSocket URL the frontend should connect to


class ChallengeConfigResponse(BaseModel):
    challenge_type: str
    thresholds: dict
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChallengeConfigUpdate(BaseModel):
    thresholds: dict


class AdminSessionResponse(BaseModel):
    id: int
    user_id: int
    username: str
    challenge_type: str
    status: str
    score: int
    duration_seconds: float
    has_pose_data: bool
    has_recording: bool
    created_at: datetime
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True
