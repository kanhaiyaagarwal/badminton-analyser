"""REST endpoints for the Workout / AI Fitness Coach feature."""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ....database import get_db
from ....routers.auth import get_current_user
from ....db_models.user import User
from ..models.workout import (
    OnboardingRequest, OnboardingResponse,
    QuickStartRequest,
    ExerciseResponse,
    SessionActionRequest, AgentResponse,
    SessionStartRequest, ExerciseHistoryResponse,
)
from ..services.workout_service import WorkoutService
from ..services.session_agent import SessionAgent
from ..services.coach_feedback import get_exercise_history

router = APIRouter(prefix="/api/v1/workout", tags=["workout"])


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

@router.post("/onboarding", response_model=OnboardingResponse)
async def save_onboarding(
    data: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save onboarding data and generate workout plan."""
    result = WorkoutService.save_onboarding(db, current_user.id, data.model_dump())
    return result


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get onboarding / profile status."""
    return WorkoutService.get_profile(db, current_user.id)


@router.delete("/profile/reset")
async def reset_onboarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reset workout onboarding — clears profile, goals, preferences, plan, and progressions."""
    from ..db_models.workout import (
        UserProfile, UserGoal, CoachPreferences, WorkoutPlan,
        ExerciseProgression, WorkoutSession, ExerciseSet,
    )

    uid = current_user.id
    db.query(ExerciseSet).filter(
        ExerciseSet.session_id.in_(
            db.query(WorkoutSession.id).filter(WorkoutSession.user_id == uid)
        )
    ).delete(synchronize_session=False)
    db.query(WorkoutSession).filter(WorkoutSession.user_id == uid).delete()
    db.query(ExerciseProgression).filter(ExerciseProgression.user_id == uid).delete()
    db.query(WorkoutPlan).filter(WorkoutPlan.user_id == uid).delete()
    db.query(CoachPreferences).filter(CoachPreferences.user_id == uid).delete()
    db.query(UserGoal).filter(UserGoal.user_id == uid).delete()
    db.query(UserProfile).filter(UserProfile.user_id == uid).delete()
    db.commit()

    return {"status": "ok", "message": "Workout data reset. Please re-onboard."}


# ---------------------------------------------------------------------------
# Exercises
# ---------------------------------------------------------------------------

@router.get("/exercises", response_model=list[ExerciseResponse])
async def list_exercises(
    muscle_group: Optional[str] = Query(None),
    equipment: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List exercises with optional filters."""
    exercises, total = WorkoutService.get_exercises(
        db, muscle_group=muscle_group, equipment=equipment,
        search=search, category=category, limit=limit, offset=offset,
    )
    return exercises


@router.get("/exercises/{slug}", response_model=ExerciseResponse)
async def get_exercise(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single exercise by slug."""
    exercise = WorkoutService.get_exercise_by_slug(db, slug)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return exercise


# ---------------------------------------------------------------------------
# Today / Week / Progress
# ---------------------------------------------------------------------------

@router.get("/today")
async def get_today_workout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get today's planned workout."""
    return WorkoutService.get_today_workout(db, current_user.id)


@router.get("/week")
async def get_week_view(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the week view with day statuses."""
    return WorkoutService.get_week_view(db, current_user.id)


@router.get("/progress/stats")
async def get_progress_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get progress statistics."""
    return WorkoutService.get_progress_stats(db, current_user.id)


# ---------------------------------------------------------------------------
# Quick Start
# ---------------------------------------------------------------------------

@router.post("/quick-start")
async def create_quick_start(
    data: QuickStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a quick start session from selected exercises."""
    result = WorkoutService.create_quick_start_session(
        db, current_user.id, data.exercise_slugs,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# M1: Session Agent Endpoints
# ---------------------------------------------------------------------------

@router.post("/sessions/start", response_model=AgentResponse)
async def start_session(
    data: SessionStartRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create/load a workout session and return the brief view."""
    params = {}
    if data:
        if data.exercise_slugs:
            params["exercise_slugs"] = data.exercise_slugs
        if data.time_budget_minutes:
            params["time_budget_minutes"] = data.time_budget_minutes

    try:
        result = SessionAgent.process_action(db, current_user.id, None, "start", params)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/action", response_model=AgentResponse)
async def session_action(
    session_id: int,
    data: SessionActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unified agent action endpoint — dispatches to SessionAgent."""
    try:
        result = SessionAgent.process_action(
            db, current_user.id, session_id, data.action, data.params,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/start-tracking")
async def start_tracking_session(
    session_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a challenge session for camera-based form tracking during a workout set.

    Reuses the exact same challenge infrastructure (GenericSessionManager,
    analyzers, /ws/challenge/ endpoint) that powers standalone challenges.
    """
    exercise_slug = data.get("exercise_slug", "")

    from ..services.camera_tracking import get_analyzer_type, is_trackable
    if not is_trackable(exercise_slug):
        raise HTTPException(status_code=400, detail=f"Exercise '{exercise_slug}' not trackable")

    challenge_type = get_analyzer_type(exercise_slug)

    # Create a ChallengeSession row (reuse challenge infra)
    from ...challenges.db_models.challenge import ChallengeSession, ChallengeStatus, ChallengeConfig
    from ...challenges.services.pushup_analyzer import PushupAnalyzer
    from ...challenges.services.squat_analyzer import SquatAnalyzer
    from ...challenges.services.plank_analyzer import PlankAnalyzer
    from ...challenges.routers.challenges import ANALYZER_MAP, get_generic_session_manager

    if challenge_type not in ANALYZER_MAP:
        raise HTTPException(status_code=400, detail=f"No analyzer for type: {challenge_type}")

    session = ChallengeSession(
        user_id=current_user.id,
        challenge_type=challenge_type,
        status=ChallengeStatus.READY,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create analyzer with DB config (same as challenge flow)
    analyzer_cls = ANALYZER_MAP[challenge_type]
    config_row = db.query(ChallengeConfig).filter(
        ChallengeConfig.challenge_type == challenge_type
    ).first()
    config_val = config_row.thresholds if config_row else None
    if analyzer_cls is SquatAnalyzer:
        analyzer = analyzer_cls(challenge_type=challenge_type, config=config_val)
    else:
        analyzer = analyzer_cls(config=config_val)

    gsm = get_generic_session_manager()
    gsm.register_session(session.id, f"challenge_{challenge_type}", analyzer)

    return {
        "challenge_session_id": session.id,
        "challenge_type": challenge_type,
        "ws_url": f"/ws/challenge/{session.id}",
    }


@router.post("/sessions/{session_id}/sets/{set_number}/camera-result", response_model=AgentResponse)
async def submit_camera_result(
    session_id: int,
    set_number: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit camera tracking results for a set (reps, form_score)."""
    try:
        params = {
            "exercise_id": data.get("exercise_id"),
            "set_number": set_number,
            "reps": data.get("reps"),
            "form_score": data.get("form_score"),
            "duration_seconds": data.get("duration_seconds"),
        }
        result = SessionAgent.process_action(
            db, current_user.id, session_id, "complete_set", params,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/exercises/{slug}/history", response_model=ExerciseHistoryResponse)
async def exercise_history(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get exercise history for the intro screen (last session, PRs)."""
    from ..db_models.workout import Exercise
    exercise = db.query(Exercise).filter(Exercise.slug == slug).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    history = get_exercise_history(db, current_user.id, exercise.id)
    return history


# ---------------------------------------------------------------------------
# M3: TTS endpoint
# ---------------------------------------------------------------------------

@router.get("/tts/{cache_key}")
async def get_tts_audio(
    cache_key: str,
    text: str = Query(..., max_length=300),
):
    """Generate TTS audio on demand for dynamic coach messages."""
    from ..services.tts_service import generate_speech

    audio_bytes = await generate_speech(text)
    if not audio_bytes:
        raise HTTPException(status_code=503, detail="TTS unavailable")

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
