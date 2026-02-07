"""Tuning preset database models."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class TuningPreset(Base):
    """
    Tuning preset model for storing shot detection thresholds.

    Designed for extensibility - thresholds are stored as JSON to support
    any activity type (badminton, tennis, basketball, etc.) without schema changes.
    """

    __tablename__ = "tuning_presets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)

    # Activity type for future extensibility (badminton, tennis, basketball, etc.)
    activity_type = Column(String(50), default="badminton", nullable=False)

    # Generic thresholds stored as JSON - schema depends on activity_type
    # Allows any sport to define its own threshold parameters
    # Example for badminton:
    # {
    #   "velocity": {
    #     "static": {"value": 0.9, "min": 0.1, "max": 2.0, "step": 0.1, "label": "Static threshold"},
    #     "power_overhead": {"value": 1.8, "min": 0.5, "max": 4.0, "step": 0.1, "label": "Power overhead"},
    #     ...
    #   },
    #   "cooldown": {
    #     "shot_cooldown_seconds": {"value": 0.4, "min": 0.1, "max": 2.0, "step": 0.05, "label": "Shot cooldown"}
    #   },
    #   "position": {
    #     "overhead_offset": {"value": 0.08, "min": 0.01, "max": 0.2, "step": 0.01, "label": "Overhead position offset"}
    #   }
    # }
    thresholds = Column(JSON, nullable=False)

    # Whether this preset is currently active for new analyses
    is_active = Column(Boolean, default=False, nullable=False)

    # System default preset (non-deletable)
    is_default = Column(Boolean, default=False, nullable=False)

    # Who created this preset
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    creator = relationship("User", backref="tuning_presets")

    # Unique constraint: name must be unique per activity type
    __table_args__ = (
        UniqueConstraint('name', 'activity_type', name='uq_preset_name_activity'),
    )

    def __repr__(self):
        return f"<TuningPreset(id={self.id}, name='{self.name}', activity='{self.activity_type}', active={self.is_active})>"

    def get_velocity_thresholds(self) -> dict:
        """Extract velocity threshold values for use in analysis."""
        velocity = self.thresholds.get("velocity", {})
        return {key: val.get("value", 0) for key, val in velocity.items()}

    def get_cooldown_seconds(self) -> float:
        """Extract shot cooldown value."""
        cooldown = self.thresholds.get("cooldown", {})
        shot_cooldown = cooldown.get("shot_cooldown_seconds", {})
        return shot_cooldown.get("value", 0.4)


class ActivityThresholdSchema(Base):
    """
    Defines what thresholds are available for each activity type.

    This allows dynamic UI generation - frontend reads schema from API
    and renders appropriate slider controls without hardcoding.
    """

    __tablename__ = "activity_threshold_schemas"

    id = Column(Integer, primary_key=True, index=True)

    # Activity type identifier (must be unique)
    activity_type = Column(String(50), unique=True, nullable=False)

    # Human-readable name
    display_name = Column(String(100), nullable=False)

    # Description of the activity
    description = Column(String(500), nullable=True)

    # Threshold schema definition
    # Defines categories, threshold names, ranges, defaults, labels
    # Example:
    # {
    #   "categories": [
    #     {
    #       "key": "velocity",
    #       "label": "Velocity Thresholds",
    #       "description": "Thresholds for movement velocity classification",
    #       "thresholds": [
    #         {"key": "static", "label": "Static", "min": 0.1, "max": 2.0, "step": 0.1, "default": 0.9, "unit": "m/s"},
    #         {"key": "power_overhead", "label": "Power Overhead", "min": 0.5, "max": 4.0, "step": 0.1, "default": 1.8},
    #         ...
    #       ]
    #     },
    #     {
    #       "key": "cooldown",
    #       "label": "Cooldown Settings",
    #       "thresholds": [
    #         {"key": "shot_cooldown_seconds", "label": "Shot Cooldown", "min": 0.1, "max": 2.0, "step": 0.05, "default": 0.4, "unit": "s"}
    #       ]
    #     }
    #   ]
    # }
    schema = Column(JSON, nullable=False)

    # Python module path for the classifier (for future use)
    # e.g., "api.classifiers.badminton" or "api.classifiers.tennis"
    classifier_module = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<ActivityThresholdSchema(activity='{self.activity_type}', display='{self.display_name}')>"


class TuningSession(Base):
    """
    Tuning session for video-based threshold tuning.

    Stores the analyzed video, cached frame data, and current threshold settings.
    Allows instant re-classification without re-running pose detection.
    """

    __tablename__ = "tuning_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Reference to the source job (video analysis)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)

    # User who owns this session
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Session name/description
    name = Column(String(100), nullable=True)

    # Activity type
    activity_type = Column(String(50), default="badminton", nullable=False)

    # Path to cached frame data JSON
    frame_data_path = Column(String(512), nullable=True)

    # Current thresholds being tested (may differ from any saved preset)
    current_thresholds = Column(JSON, nullable=True)

    # Video info for the frame viewer
    video_info = Column(JSON, nullable=True)  # {fps, duration, frame_count, width, height}

    # Status
    status = Column(String(20), default="created")  # created, analyzing, ready, failed

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="tuning_sessions")
    job = relationship("Job", backref="tuning_sessions")

    def __repr__(self):
        return f"<TuningSession(id={self.id}, status='{self.status}', job_id={self.job_id})>"
