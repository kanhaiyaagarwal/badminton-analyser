"""Pydantic schemas for the Workout / AI Fitness Coach feature."""

from datetime import date, datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

class OnboardingRequest(BaseModel):
    # About You (step 2)
    fitness_level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    injuries: Optional[List[str]] = None

    # Goals (step 3)
    goals: List[str] = Field(..., min_length=1)

    # Schedule (step 4)
    preferred_days: List[str] = Field(..., min_length=1)
    session_duration_minutes: int = Field(45, ge=10, le=120)
    train_location: str = Field("gym", pattern="^(gym|home)$")
    available_equipment: Optional[List[str]] = None


class OnboardingResponse(BaseModel):
    success: bool
    plan_name: str
    split_type: str
    days_per_week: int
    message: str


# ---------------------------------------------------------------------------
# Exercises
# ---------------------------------------------------------------------------

class ExerciseResponse(BaseModel):
    id: int
    name: str
    slug: str
    category: str
    muscle_groups: List[str]
    primary_muscle: str
    equipment: List[str]
    tracking_mode: str
    difficulty: str
    form_cues: Optional[List[str]] = None
    common_mistakes: Optional[List[str]] = None
    demo_image_url: Optional[str] = None
    demo_video_url: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Quick Start
# ---------------------------------------------------------------------------

class QuickStartRequest(BaseModel):
    exercise_slugs: List[str] = Field(..., min_length=1, max_length=20)


# ---------------------------------------------------------------------------
# Today / Week Views
# ---------------------------------------------------------------------------

class TodayExercise(BaseModel):
    slug: str
    name: str
    sets: int
    reps: str  # e.g. "8-10" or "30s"
    equipment: List[str]


class TodayWorkoutResponse(BaseModel):
    has_plan: bool
    day_label: Optional[str] = None  # e.g. "Push Day"
    exercises: List[TodayExercise] = []
    estimated_minutes: int = 0
    streak: int = 0
    coach_message: str = ""
    session_id: Optional[int] = None


class WeekDay(BaseModel):
    day: str  # mon, tue, ...
    label: Optional[str] = None
    status: str  # planned, completed, skipped, rest, today


class WeekViewResponse(BaseModel):
    days: List[WeekDay]
    plan_name: Optional[str] = None
    week_number: int = 1


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------

class ProgressStatsResponse(BaseModel):
    total_workouts: int = 0
    current_streak: int = 0
    best_streak: int = 0
    total_volume_kg: float = 0.0
    workouts_this_week: int = 0
    recent_prs: List[dict] = []


# ---------------------------------------------------------------------------
# M1: Session Agent Schemas
# ---------------------------------------------------------------------------

class SessionActionRequest(BaseModel):
    action: str = Field(..., pattern="^(start|adjust_time|begin_workout|complete_set|skip_exercise|skip_rest|end_workout|modify_exercise)$")
    params: dict = Field(default_factory=dict)


class AgentResponse(BaseModel):
    view: str  # brief, exercise_intro, active_set, rest_timer, cooldown, summary
    data: dict
    coach_says: str = ""
    available_actions: List[str] = []
    progress: Optional[dict] = None
    audio_url: Optional[str] = None

    class Config:
        from_attributes = True


class SessionStartRequest(BaseModel):
    exercise_slugs: Optional[List[str]] = None
    time_budget_minutes: Optional[int] = None


class ExerciseHistoryResponse(BaseModel):
    pr_reps: Optional[int] = None
    pr_weight: Optional[float] = None
    last_session: Optional[dict] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Chat (Voice-First AI Coach Companion)
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = ""
    context: str = Field("onboarding", pattern="^(onboarding|pre_workout|post_set|rest|post_workout)$")
    session_id: Optional[Union[str, int]] = None
    conversation_id: Optional[str] = None


class SuggestedOption(BaseModel):
    label: str
    value: str


class ChatAction(BaseModel):
    type: str
    params: dict = Field(default_factory=dict)


class PlanUpdate(BaseModel):
    exercises: Optional[List[dict]] = None


class ChatResponse(BaseModel):
    response: str
    audio_url: Optional[str] = None
    actions: List[ChatAction] = []
    suggested_options: List[SuggestedOption] = []
    data_collected: Optional[dict] = None
    plan_update: Optional[PlanUpdate] = None
    onboarding_complete: bool = False
    conversation_id: Optional[str] = None
