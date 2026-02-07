"""Tuning Pydantic models for request/response schemas."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# Threshold Schema Models (for dynamic UI generation)
# ============================================================================

class ThresholdDefinition(BaseModel):
    """Definition of a single threshold parameter."""
    key: str
    label: str
    min: float
    max: float
    step: float
    default: float
    unit: Optional[str] = None
    description: Optional[str] = None


class ThresholdCategory(BaseModel):
    """A category of related thresholds."""
    key: str
    label: str
    description: Optional[str] = None
    thresholds: List[ThresholdDefinition]


class ActivitySchema(BaseModel):
    """Full schema for an activity type."""
    activity_type: str
    display_name: str
    description: Optional[str] = None
    categories: List[ThresholdCategory]


# ============================================================================
# Threshold Value Models (for actual threshold data)
# ============================================================================

class ThresholdValue(BaseModel):
    """A threshold value with metadata."""
    value: float
    min: float
    max: float
    step: float
    label: str
    unit: Optional[str] = None


class ThresholdSet(BaseModel):
    """Complete set of thresholds for an activity."""
    velocity: Dict[str, ThresholdValue]
    cooldown: Dict[str, ThresholdValue]
    position: Optional[Dict[str, ThresholdValue]] = None


# ============================================================================
# Tuning Preset Models
# ============================================================================

class TuningPresetCreate(BaseModel):
    """Schema for creating a new tuning preset."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    activity_type: str = "badminton"
    thresholds: Dict[str, Any]  # Flexible JSON structure


class TuningPresetUpdate(BaseModel):
    """Schema for updating a tuning preset."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    thresholds: Optional[Dict[str, Any]] = None


class TuningPresetResponse(BaseModel):
    """Response schema for tuning preset."""
    id: int
    name: str
    description: Optional[str]
    activity_type: str
    thresholds: Dict[str, Any]
    is_active: bool
    is_default: bool
    created_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TuningPresetListResponse(BaseModel):
    """Response for listing presets."""
    presets: List[TuningPresetResponse]
    active_preset_id: Optional[int] = None


# ============================================================================
# Frame Data Models (for caching and re-classification)
# ============================================================================

class FrameMetrics(BaseModel):
    """Metrics for a single analyzed frame."""
    frame_number: int
    timestamp: float
    player_detected: bool
    wrist_velocity: Optional[float] = None
    body_velocity: Optional[float] = None
    wrist_direction: Optional[str] = None
    wrist_position: Optional[List[int]] = None  # [x, y]
    swing_type: Optional[str] = None
    shot_type: Optional[str] = None
    confidence: Optional[float] = None
    cooldown_active: bool = False
    # Raw pose data for re-classification
    wrist_y: Optional[float] = None
    shoulder_y: Optional[float] = None
    hip_y: Optional[float] = None
    is_overhead: Optional[bool] = None
    is_low_position: Optional[bool] = None
    arm_extension: Optional[float] = None


class VideoInfo(BaseModel):
    """Video metadata."""
    fps: float
    duration: float
    frame_count: int
    width: Optional[int] = None
    height: Optional[int] = None


class FrameDataExport(BaseModel):
    """Complete frame data export for a tuning session."""
    video_info: VideoInfo
    thresholds_used: Dict[str, float]
    cooldown_seconds: float
    frames: List[FrameMetrics]


# ============================================================================
# Re-classification Models
# ============================================================================

class ReclassifyRequest(BaseModel):
    """Request to re-classify shots with new thresholds."""
    velocity_thresholds: Dict[str, float]
    position_thresholds: Optional[Dict[str, float]] = None
    shot_cooldown_seconds: float = 0.4


class ClassificationResult(BaseModel):
    """Result for a single frame after re-classification."""
    frame_number: int
    timestamp: float
    original_shot_type: Optional[str]
    original_confidence: Optional[float]
    new_shot_type: Optional[str]
    new_confidence: Optional[float]
    changed: bool


class ReclassifyResponse(BaseModel):
    """Response from re-classification."""
    total_frames: int
    frames_changed: int
    results: List[ClassificationResult]
    # Summary of changes
    shot_distribution_before: Dict[str, int]
    shot_distribution_after: Dict[str, int]


# ============================================================================
# Tuning Session Models
# ============================================================================

class TuningSessionCreate(BaseModel):
    """Create a new tuning session from a job."""
    job_id: Optional[int] = None
    name: Optional[str] = None
    activity_type: str = "badminton"


class TuningSessionResponse(BaseModel):
    """Response for tuning session."""
    id: int
    job_id: Optional[int]
    user_id: int
    name: Optional[str]
    activity_type: str
    status: str
    video_info: Optional[Dict[str, Any]]
    current_thresholds: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TuningSessionFrameResponse(BaseModel):
    """Response for getting frame data from a session."""
    session_id: int
    video_info: VideoInfo
    thresholds_used: Dict[str, float]
    frame_count: int


# ============================================================================
# Comparison Models
# ============================================================================

class ShotComparisonEntry(BaseModel):
    """Single entry in shot comparison table."""
    frame_number: int
    timestamp: float
    before_shot: Optional[str]
    before_confidence: Optional[float]
    after_shot: Optional[str]
    after_confidence: Optional[float]
    changed: bool


class ThresholdComparisonResponse(BaseModel):
    """Response comparing before/after classifications."""
    comparisons: List[ShotComparisonEntry]
    summary: Dict[str, Any]


# ============================================================================
# Default Badminton Thresholds
# ============================================================================

def get_default_badminton_thresholds() -> Dict[str, Any]:
    """Get default badminton threshold configuration."""
    return {
        "velocity": {
            "static": {
                "value": 0.9,
                "min": 0.1,
                "max": 2.0,
                "step": 0.1,
                "label": "Static Threshold",
                "description": "Below this velocity, player is considered static"
            },
            "movement": {
                "value": 0.75,
                "min": 0.1,
                "max": 2.0,
                "step": 0.1,
                "label": "Movement Threshold",
                "description": "Threshold for preparation/movement detection"
            },
            "power_overhead": {
                "value": 1.8,
                "min": 0.5,
                "max": 4.0,
                "step": 0.1,
                "label": "Power Overhead",
                "description": "Velocity for power overhead shots (smash)"
            },
            "gentle_overhead": {
                "value": 1.2,
                "min": 0.3,
                "max": 3.0,
                "step": 0.1,
                "label": "Gentle Overhead",
                "description": "Velocity for gentle overhead shots (clear/drop)"
            },
            "drive": {
                "value": 1.5,
                "min": 0.5,
                "max": 3.5,
                "step": 0.1,
                "label": "Drive",
                "description": "Velocity for horizontal drive shots"
            },
            "net_min": {
                "value": 0.9,
                "min": 0.1,
                "max": 2.0,
                "step": 0.1,
                "label": "Net Shot Min",
                "description": "Minimum velocity for net shots"
            },
            "net_max": {
                "value": 3.6,
                "min": 1.5,
                "max": 6.0,
                "step": 0.1,
                "label": "Net Shot Max",
                "description": "Maximum velocity for net shots"
            },
            "lift": {
                "value": 1.2,
                "min": 0.3,
                "max": 3.0,
                "step": 0.1,
                "label": "Lift",
                "description": "Velocity for defensive lift shots"
            },
            "smash_vs_clear": {
                "value": 2.4,
                "min": 1.0,
                "max": 5.0,
                "step": 0.1,
                "label": "Smash vs Clear",
                "description": "Threshold to distinguish smash from clear"
            }
        },
        "cooldown": {
            "shot_cooldown_seconds": {
                "value": 0.4,
                "min": 0.1,
                "max": 2.0,
                "step": 0.05,
                "label": "Shot Cooldown",
                "unit": "seconds",
                "description": "Time after a shot before detecting another"
            }
        },
        "position": {
            "overhead_offset": {
                "value": 0.08,
                "min": 0.01,
                "max": 0.2,
                "step": 0.01,
                "label": "Overhead Offset",
                "description": "How far above shoulder for overhead detection"
            },
            "low_position_offset": {
                "value": 0.1,
                "min": 0.01,
                "max": 0.25,
                "step": 0.01,
                "label": "Low Position Offset",
                "description": "How far below hip for low position detection (net/lift shots)"
            },
            "arm_extension_min": {
                "value": 0.15,
                "min": 0.05,
                "max": 0.3,
                "step": 0.01,
                "label": "Arm Extension Min",
                "description": "Minimum arm extension for net shot detection"
            }
        },
        "rally": {
            "stillness_frames": {
                "value": 4,
                "min": 2,
                "max": 10,
                "step": 1,
                "label": "Stillness Frames",
                "description": "Number of consecutive still frames to detect rally end"
            },
            "stillness_threshold": {
                "value": 0.02,
                "min": 0.005,
                "max": 0.1,
                "step": 0.005,
                "label": "Stillness Threshold",
                "description": "Max movement (as fraction) to be considered still"
            }
        }
    }


def get_badminton_activity_schema() -> Dict[str, Any]:
    """Get the badminton activity threshold schema for UI generation."""
    return {
        "activity_type": "badminton",
        "display_name": "Badminton",
        "description": "Shot detection for badminton including smash, clear, drop, net shots, drives, and lifts",
        "categories": [
            {
                "key": "velocity",
                "label": "Velocity Thresholds",
                "description": "Thresholds for movement velocity classification (normalized distance per second)",
                "thresholds": [
                    {"key": "static", "label": "Static", "min": 0.1, "max": 2.0, "step": 0.1, "default": 0.9},
                    {"key": "movement", "label": "Movement", "min": 0.1, "max": 2.0, "step": 0.1, "default": 0.75},
                    {"key": "power_overhead", "label": "Power Overhead", "min": 0.5, "max": 4.0, "step": 0.1, "default": 1.8},
                    {"key": "gentle_overhead", "label": "Gentle Overhead", "min": 0.3, "max": 3.0, "step": 0.1, "default": 1.2},
                    {"key": "drive", "label": "Drive", "min": 0.5, "max": 3.5, "step": 0.1, "default": 1.5},
                    {"key": "net_min", "label": "Net Min", "min": 0.1, "max": 2.0, "step": 0.1, "default": 0.9},
                    {"key": "net_max", "label": "Net Max", "min": 1.5, "max": 6.0, "step": 0.1, "default": 3.6},
                    {"key": "lift", "label": "Lift", "min": 0.3, "max": 3.0, "step": 0.1, "default": 1.2},
                    {"key": "smash_vs_clear", "label": "Smash vs Clear", "min": 1.0, "max": 5.0, "step": 0.1, "default": 2.4}
                ]
            },
            {
                "key": "cooldown",
                "label": "Cooldown Settings",
                "description": "Timing settings to prevent duplicate detections",
                "thresholds": [
                    {"key": "shot_cooldown_seconds", "label": "Shot Cooldown", "min": 0.1, "max": 2.0, "step": 0.05, "default": 0.4, "unit": "s"}
                ]
            },
            {
                "key": "position",
                "label": "Position Thresholds",
                "description": "Thresholds for body position classification",
                "thresholds": [
                    {"key": "overhead_offset", "label": "Overhead Offset", "min": 0.01, "max": 0.2, "step": 0.01, "default": 0.08, "description": "How far above shoulder for overhead detection"},
                    {"key": "low_position_offset", "label": "Low Position Offset", "min": 0.01, "max": 0.25, "step": 0.01, "default": 0.1, "description": "How far below hip for low position detection"},
                    {"key": "arm_extension_min", "label": "Arm Extension Min", "min": 0.05, "max": 0.3, "step": 0.01, "default": 0.15, "description": "Minimum arm extension for net shots"}
                ]
            },
            {
                "key": "rally",
                "label": "Rally Detection",
                "description": "Settings for detecting rally boundaries",
                "thresholds": [
                    {"key": "stillness_frames", "label": "Stillness Frames", "min": 2, "max": 10, "step": 1, "default": 4, "description": "Consecutive still frames to detect rally end"},
                    {"key": "stillness_threshold", "label": "Stillness Threshold", "min": 0.005, "max": 0.1, "step": 0.005, "default": 0.02, "description": "Max movement (fraction) to be still"}
                ]
            }
        ]
    }
