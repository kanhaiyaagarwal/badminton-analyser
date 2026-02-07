"""Analysis Pydantic models."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from .court import CourtBoundaryCreate


class AnalysisStart(BaseModel):
    """Schema for starting analysis."""
    court_boundary: CourtBoundaryCreate
    speed_preset: str = "balanced"  # fast, balanced, accurate, turbo
    frame_timestamp: float = 0.0  # Timestamp for background frame (the one user selected for court setup)
    save_frame_data: bool = False  # Save per-frame data for tuning dashboard


class ShotInfo(BaseModel):
    """Individual shot information."""
    time: float
    shot: str
    confidence: float


class RallyInfo(BaseModel):
    """Rally information."""
    rally_id: int
    duration: float
    shot_count: int
    shots: List[str]


class AnalysisSummary(BaseModel):
    """Analysis summary statistics."""
    total_shots: int
    total_rallies: int
    frames_processed: int
    player_detection_rate: float
    avg_confidence: float
    foot_positions_recorded: int


class AnalysisReport(BaseModel):
    """Full analysis report."""
    summary: AnalysisSummary
    shot_distribution: Dict[str, int]
    rallies: List[RallyInfo]
    shot_timeline: List[ShotInfo]
    court_settings: Dict[str, Any]
    heatmap_image_path: Optional[str] = None
    heatmap_data_path: Optional[str] = None


class AnalysisStatus(BaseModel):
    """Job status response."""
    job_id: int
    status: str
    progress: float
    status_message: Optional[str] = None
    error_message: Optional[str] = None
