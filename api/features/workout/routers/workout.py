"""REST endpoints for the Workout / AI Fitness Coach feature."""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
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
    ChatRequest, ChatResponse, SuggestedOption, ChatAction,
)
from ..services.workout_service import WorkoutService
from ..services.session_agent import SessionAgent
from ..services.coach_feedback import get_exercise_history
from ..services import onboarding_agent, chat_agent

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
    """Reset workout onboarding — soft-deletes sessions/chat, hard-deletes profile/plan/prefs."""
    from ..db_models.workout import (
        UserProfile, UserGoal, CoachPreferences, WorkoutPlan,
        ExerciseProgression, WorkoutSession, ExerciseSet,
        ChatConversation, ChatMessage,
    )
    from datetime import datetime

    uid = current_user.id
    now = datetime.utcnow()

    # Soft-delete: mark chat conversations as closed (keeps messages for debugging)
    db.query(ChatConversation).filter(
        ChatConversation.user_id == uid,
    ).update({"status": "reset", "closed_at": now}, synchronize_session=False)

    # Soft-delete: mark workout sessions as archived, detach from plan (FK)
    db.query(WorkoutSession).filter(
        WorkoutSession.user_id == uid,
    ).update({"status": "skipped", "plan_id": None}, synchronize_session=False)

    # Hard-delete: profile, goals, preferences, plan, progressions (re-created on onboarding)
    db.query(ExerciseProgression).filter(ExerciseProgression.user_id == uid).delete()
    db.query(WorkoutPlan).filter(WorkoutPlan.user_id == uid).delete()
    db.query(CoachPreferences).filter(CoachPreferences.user_id == uid).delete()
    db.query(UserGoal).filter(UserGoal.user_id == uid).delete()
    db.query(UserProfile).filter(UserProfile.user_id == uid).delete()
    db.commit()

    return {"status": "ok", "message": "Workout data reset. Please re-onboard."}


# ---------------------------------------------------------------------------
# Chat (Voice-First AI Coach Companion)
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def workout_chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unified chat endpoint. Routes to OnboardingAgent or WorkoutChatAgent based on context."""
    if body.context == "onboarding":
        result = await onboarding_agent.process_turn(
            conversation_id=body.conversation_id,
            user_message=body.message,
        )
        return ChatResponse(
            response=result["response"],
            suggested_options=[SuggestedOption(**o) for o in result.get("suggested_options", [])],
            data_collected=result.get("data_collected"),
            onboarding_complete=result.get("onboarding_complete", False),
            conversation_id=result.get("conversation_id"),
        )

    # All other contexts: pre_workout, post_set, rest, post_workout
    sid_int = None
    try:
        sid_int = int(body.session_id) if body.session_id else None
    except (ValueError, TypeError):
        pass

    session_data = _build_chat_session_data(db, body.session_id, current_user)
    user_context = {"name": current_user.username or ""}

    result = await chat_agent.process_chat(
        user_message=body.message,
        context=body.context,
        session_data=session_data,
        user_context=user_context,
        db=db,
        session_id=sid_int,
        user_id=current_user.id,
        conversation_id=body.conversation_id,
    )

    return ChatResponse(
        response=result.get("response", ""),
        actions=[ChatAction(**a) for a in result.get("actions", [])],
        suggested_options=[SuggestedOption(**o) for o in result.get("suggested_options", [])],
        conversation_id=result.get("conversation_id") or body.conversation_id,
    )


def _build_chat_session_data(db: Session, session_id: Optional[str], user) -> dict:
    """Build session context for chat agent from a real session if available."""
    if not session_id:
        return {"exercises": [], "day_label": "Today's workout", "estimated_minutes": 45}

    try:
        from ..db_models.workout import WorkoutSession, Exercise
        sid = int(session_id)
        session = db.query(WorkoutSession).filter(
            WorkoutSession.id == sid,
            WorkoutSession.user_id == user.id,
        ).first()
        if session and session.planned_exercises:
            planned = session.planned_exercises
            plan_slugs = {e.get("slug") for e in planned}

            # Fetch all exercises to enrich planned with primary_muscle and find alternatives
            all_exercises = db.query(Exercise).all()
            slug_to_ex = {ex.slug: ex for ex in all_exercises}

            # Enrich planned exercises with primary_muscle
            plan_muscles = set()
            for ex in planned:
                db_ex = slug_to_ex.get(ex.get("slug"))
                if db_ex:
                    ex["primary_muscle"] = db_ex.primary_muscle
                    plan_muscles.add(db_ex.primary_muscle)

            # Find alternative exercises (same muscle groups, not already in plan)
            alternatives = []
            for ex in all_exercises:
                if ex.slug in plan_slugs:
                    continue
                if ex.primary_muscle in plan_muscles:
                    alternatives.append({
                        "slug": ex.slug,
                        "name": ex.name,
                        "primary_muscle": ex.primary_muscle,
                    })

            # Build text summary for LLM
            alt_lines = []
            for a in alternatives[:20]:
                alt_lines.append(f"- {a['name']} (slug: {a['slug']}, muscle: {a['primary_muscle']})")

            return {
                "exercises": planned,
                "day_label": "Today's workout",
                "estimated_minutes": len(planned) * 5,
                "alternatives": alternatives,
                "alternatives_text": "\n".join(alt_lines) if alt_lines else "No alternatives available.",
            }
    except (ValueError, TypeError):
        pass

    return {"exercises": [], "day_label": "Today's workout", "estimated_minutes": 45}


# ---------------------------------------------------------------------------
# Exercises
# ---------------------------------------------------------------------------

@router.get("/exercises", response_model=list[ExerciseResponse])
async def list_exercises(
    muscle_group: Optional[str] = Query(None),
    equipment: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
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
    """Get today's planned workout with personalized greeting and coach insight."""
    result = WorkoutService.get_today_workout(db, current_user.id)

    # Layer on personalized greeting + insight
    username = current_user.username or (current_user.email or "").split("@")[0]
    greeting_data = WorkoutService.get_personalized_greeting(
        db, current_user.id, username,
    )
    result["greeting"] = greeting_data["greeting"]
    result["insight"] = greeting_data["insight"]
    result["insight_type"] = greeting_data["insight_type"]

    return result


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


@router.get("/history")
async def get_workout_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get completed workout sessions history."""
    return WorkoutService.get_workout_history(db, current_user.id, limit, offset)


@router.put("/profile/measurements")
async def update_measurements(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update body measurements (weight_kg, height_cm, age)."""
    try:
        return WorkoutService.update_measurements(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/goals")
async def get_goals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user goals."""
    return WorkoutService.get_goals(db, current_user.id)


@router.get("/equipment")
async def get_equipment(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user's saved equipment and master equipment list."""
    return WorkoutService.get_equipment(db, current_user.id)


@router.put("/equipment")
async def update_equipment(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user's available equipment list."""
    return WorkoutService.update_equipment(db, current_user.id, data.get("equipment", []), data.get("train_location"))


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
    from ...challenges.services.arm_curl_analyzer import ArmRepAnalyzer
    if analyzer_cls is SquatAnalyzer:
        analyzer = analyzer_cls(challenge_type=challenge_type, config=config_val)
    elif analyzer_cls is ArmRepAnalyzer:
        analyzer = analyzer_cls(exercise_slug=data.get("exercise_slug", "bicep-curl"), config=config_val)
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


# ---------------------------------------------------------------------------
# STT endpoint (Whisper fallback for browsers without Web Speech API)
# ---------------------------------------------------------------------------

@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Transcribe uploaded audio using OpenAI Whisper API."""
    from ..services.stt_service import transcribe_audio

    audio_bytes = await audio.read()
    if not audio_bytes or len(audio_bytes) < 100:
        raise HTTPException(status_code=400, detail="No audio data")

    if len(audio_bytes) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=400, detail="Audio too large (max 5MB)")

    text = await transcribe_audio(audio_bytes, audio.content_type or "audio/webm")
    if text is None:
        raise HTTPException(status_code=503, detail="STT unavailable")

    return {"text": text}


# ---------------------------------------------------------------------------
# Admin: Workout Sessions
# ---------------------------------------------------------------------------

@router.get("/admin/sessions")
async def admin_list_workout_sessions(
    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin=Depends(get_current_user),
):
    """List workout sessions with summary data (admin only)."""
    if not getattr(admin, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin only")

    from ..db_models.workout import WorkoutSession, ExerciseSet
    from ....db_models.user import User

    q = db.query(WorkoutSession, User.username, User.email).join(
        User, User.id == WorkoutSession.user_id
    )
    if user_id:
        q = q.filter(WorkoutSession.user_id == user_id)
    if status:
        q = q.filter(WorkoutSession.status == status)

    total = q.count()
    rows = q.order_by(WorkoutSession.created_at.desc()).offset(skip).limit(limit).all()

    sessions = []
    for ws, username, email in rows:
        # Count sets and get challenge_session_ids for screenshot links
        sets = db.query(ExerciseSet).filter(ExerciseSet.session_id == ws.id).all()
        challenge_ids = [s.challenge_session_id for s in sets if s.challenge_session_id]

        summary = ws.summary or {}
        sessions.append({
            "id": ws.id,
            "user_id": ws.user_id,
            "username": username,
            "email": email,
            "status": ws.status.value if ws.status else "unknown",
            "session_type": ws.session_type.value if ws.session_type else "coached",
            "started_at": ws.started_at,
            "ended_at": ws.ended_at,
            "duration_seconds": ws.duration_seconds,
            "created_at": ws.created_at,
            "exercises_completed": summary.get("exercises_completed", 0),
            "total_sets": summary.get("total_sets", 0),
            "total_reps": summary.get("total_reps", 0),
            "total_volume_kg": summary.get("total_volume_kg", 0),
            "prs": summary.get("prs", []),
            "coach_summary": summary.get("coach_summary", ""),
            "planned_exercises": ws.planned_exercises or [],
            "set_count": len(sets),
            "challenge_session_ids": challenge_ids,
            "sets": [
                {
                    "id": s.id,
                    "exercise_id": s.exercise_id,
                    "set_number": s.set_number,
                    "actual_reps": s.actual_reps,
                    "target_reps": s.target_reps,
                    "weight_kg": s.weight_kg,
                    "rpe": s.rpe,
                    "form_score": s.form_score,
                    "challenge_session_id": s.challenge_session_id,
                    "duration_seconds": s.duration_seconds,
                    "completed_at": s.completed_at,
                }
                for s in sets
            ],
        })

    return {"sessions": sessions, "total": total, "skip": skip, "limit": limit}
