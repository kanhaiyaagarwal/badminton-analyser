"""Pydantic schemas for the Mimic Challenge feature."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class MimicChallengeCreate(BaseModel):
    title: str
    description: Optional[str] = None


class MimicChallengeResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    created_by: int
    video_duration: Optional[float] = None
    video_fps: Optional[float] = None
    total_frames: int = 0
    processing_status: str
    is_trending: bool = False
    is_public: bool = True
    play_count: int = 0
    has_video: bool = False
    has_thumbnail: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class MimicSessionCreate(BaseModel):
    challenge_id: int


class MimicSessionStart(BaseModel):
    session_id: int
    challenge_id: int
    ws_url: str
    reference_duration: Optional[float] = None
    reference_fps: Optional[float] = None


class MimicSessionResponse(BaseModel):
    id: int
    challenge_id: int
    status: str
    overall_score: float = 0.0
    duration_seconds: float = 0.0
    frames_compared: int = 0
    score_breakdown: Optional[dict] = None
    personal_best: Optional[float] = None
    challenge_title: Optional[str] = None
    created_at: datetime
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MimicCompareStart(BaseModel):
    session_id: int
    status: str


class MimicRecordResponse(BaseModel):
    challenge_id: int
    best_score: float
    attempt_count: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
