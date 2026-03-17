"""SQLAlchemy models for the Workout / AI Fitness Coach feature."""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Integer, String, Float, Enum, DateTime,
    ForeignKey, JSON, Date, Text,
)

from ....database import Base


# ---------------------------------------------------------------------------
# Exercises (seed data — read-only for users)
# ---------------------------------------------------------------------------

class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    slug = Column(String(128), unique=True, nullable=False, index=True)
    category = Column(String(32), nullable=False)  # compound, bodyweight, isolation, cardio
    muscle_groups = Column(JSON, nullable=False)  # ["chest", "triceps"]
    primary_muscle = Column(String(64), nullable=False)
    equipment = Column(JSON, nullable=False)  # ["barbell", "bench"] or ["none"]
    tracking_mode = Column(String(16), nullable=False, default="reps")  # reps, hold, timed
    difficulty = Column(String(16), nullable=False, default="intermediate")
    form_cues = Column(JSON, nullable=True)  # ["Keep elbows at 45°", ...]
    common_mistakes = Column(JSON, nullable=True)
    demo_image_url = Column(String(512), nullable=True)
    demo_video_url = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# User Profile (from onboarding)
# ---------------------------------------------------------------------------

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(16), nullable=True)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    fitness_level = Column(String(16), nullable=False, default="beginner")
    injuries = Column(JSON, nullable=True)  # ["lower back", ...]
    onboarding_completed = Column(Boolean, default=False)
    onboarding_completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# User Goals (multiple per user)
# ---------------------------------------------------------------------------

class UserGoal(Base):
    __tablename__ = "user_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goal_type = Column(String(32), nullable=False)  # build_muscle, lose_fat, get_stronger, stay_active
    priority = Column(Integer, default=0)


# ---------------------------------------------------------------------------
# Coach Preferences (from onboarding schedule screen)
# ---------------------------------------------------------------------------

class CoachPreferences(Base):
    __tablename__ = "coach_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    days_per_week = Column(Integer, default=3)
    preferred_days = Column(JSON, nullable=True)  # ["mon", "tue", "wed", ...]
    session_duration_minutes = Column(Integer, default=45)
    workout_split = Column(String(32), nullable=True)  # ppl, upper_lower, full_body
    available_equipment = Column(JSON, nullable=True)  # ["barbell", "dumbbells", ...]
    train_location = Column(String(16), default="gym")  # gym, home
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Workout Plans (template-generated)
# ---------------------------------------------------------------------------

class PlanStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(128), nullable=False)
    split_type = Column(String(32), nullable=False)  # ppl, upper_lower, full_body
    week_number = Column(Integer, default=1)
    status = Column(Enum(PlanStatus), default=PlanStatus.ACTIVE)
    plan_data = Column(JSON, nullable=False)  # full plan structure
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Workout Sessions
# ---------------------------------------------------------------------------

class SessionStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class SessionType(str, enum.Enum):
    COACHED = "coached"
    QUICK_START = "quick_start"
    FLEX = "flex"


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("workout_plans.id"), nullable=True)
    session_type = Column(Enum(SessionType), default=SessionType.COACHED)
    status = Column(Enum(SessionStatus), default=SessionStatus.PLANNED)
    scheduled_date = Column(Date, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    summary = Column(JSON, nullable=True)  # { exercises_completed, total_volume, ... }
    planned_exercises = Column(JSON, nullable=True)  # [{slug, name, sets, reps, exercise_id, order}, ...]
    time_budget_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Exercise Sets (individual set logs)
# ---------------------------------------------------------------------------

class ExerciseSet(Base):
    __tablename__ = "exercise_sets"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("workout_sessions.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    set_number = Column(Integer, nullable=False)
    target_reps = Column(Integer, nullable=True)
    actual_reps = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    rpe = Column(Integer, nullable=True)  # rate of perceived exertion 1-10
    form_score = Column(Integer, nullable=True)  # 0-100 from camera tracking
    is_warmup = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    exercise_order = Column(Integer, nullable=True)  # position in session
    is_skipped = Column(Boolean, default=False)


# ---------------------------------------------------------------------------
# Exercise Progression (progressive overload tracking)
# ---------------------------------------------------------------------------

class ExerciseProgression(Base):
    __tablename__ = "exercise_progressions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    current_weight_kg = Column(Float, nullable=True, default=0)
    current_reps = Column(Integer, nullable=True, default=0)
    weeks_at_current = Column(Integer, default=0)
    last_progression_date = Column(DateTime, nullable=True)
    progression_history = Column(JSON, nullable=True)  # [{date, type, weight_kg, reps, rationale}]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
