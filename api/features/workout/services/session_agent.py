"""Coach agent — processes user actions during a workout session.

The single entry point is `SessionAgent.process_action()`, which dispatches
to handler functions based on the action name.  Each handler returns an
AgentResponse that tells the frontend what to render and what the coach says.
"""

import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db_models.workout import (
    Exercise, ExerciseSet, WorkoutSession, WorkoutPlan,
    SessionStatus, SessionType, PlanStatus,
)
from .coach_feedback import (
    generate_set_feedback, generate_rest_tip,
    generate_session_summary, get_exercise_history,
    try_smart_set_feedback, try_smart_summary,
)
from .progressive_overload import ProgressiveOverloadEngine
from .tts_service import get_audio_url_for_coach
from .plan_generator import VOLUME_SCHEMES

logger = logging.getLogger(__name__)

# Default rest duration by exercise category (seconds)
REST_DURATIONS = {
    "compound": 120,
    "isolation": 60,
    "bodyweight": 60,
    "cardio": 30,
}


# ---------------------------------------------------------------------------
# AgentResponse (dict-based to avoid import cycles with Pydantic models)
# ---------------------------------------------------------------------------

def _enrich_exercise(exercise_dict: dict, db_exercise) -> dict:
    """Add DB-only fields (demo_video_url, description) to exercise dict for frontend."""
    enriched = dict(exercise_dict)
    if db_exercise:
        if db_exercise.demo_video_url:
            enriched["demo_video_url"] = db_exercise.demo_video_url
        if db_exercise.demo_image_url:
            enriched["demo_image_url"] = db_exercise.demo_image_url
    return enriched


def _agent_response(
    view: str,
    data: dict,
    coach_says: str = "",
    available_actions: list = None,
    progress: dict = None,
    audio_url: str = None,
) -> dict:
    # Auto-resolve audio URL from coach text if not provided
    if not audio_url and coach_says:
        audio_url = get_audio_url_for_coach(coach_says)

    resp = {
        "view": view,
        "data": data,
        "coach_says": coach_says,
        "available_actions": available_actions or [],
        "progress": progress,
    }
    if audio_url:
        resp["audio_url"] = audio_url
    return resp


# ---------------------------------------------------------------------------
# Session Agent
# ---------------------------------------------------------------------------

class SessionAgent:
    """Processes user actions during a workout session."""

    HANDLERS = {
        "start",
        "adjust_time",
        "begin_workout",
        "complete_set",
        "skip_exercise",
        "skip_rest",
        "end_workout",
        "modify_exercise",
        "update_plan",
    }

    @staticmethod
    def process_action(
        db: Session,
        user_id: int,
        session_id: Optional[int],
        action: str,
        params: dict,
    ) -> dict:
        if action not in SessionAgent.HANDLERS:
            raise ValueError(f"Unknown action: {action}")

        handler = {
            "start": _handle_start,
            "adjust_time": _handle_adjust_time,
            "begin_workout": _handle_begin_workout,
            "complete_set": _handle_complete_set,
            "skip_exercise": _handle_skip_exercise,
            "skip_rest": _handle_skip_rest,
            "end_workout": _handle_end_workout,
            "modify_exercise": _handle_modify_exercise,
            "update_plan": _handle_update_plan,
        }[action]

        return handler(db, user_id, session_id, params)


# ---------------------------------------------------------------------------
# Action Handlers
# ---------------------------------------------------------------------------

def _handle_start(db: Session, user_id: int, session_id: Optional[int], params: dict) -> dict:
    """Initialize a workout session. Loads exercises from plan or slugs."""
    exercise_slugs = params.get("exercise_slugs")
    time_budget = params.get("time_budget_minutes")

    session = None

    if session_id:
        # Resume existing session
        session = db.query(WorkoutSession).filter(
            WorkoutSession.id == session_id,
            WorkoutSession.user_id == user_id,
        ).first()

    if not session and exercise_slugs:
        # Quick-start path: create session from slugs
        session = WorkoutSession(
            user_id=user_id,
            session_type=SessionType.QUICK_START,
            status=SessionStatus.PLANNED,
            scheduled_date=date.today(),
            time_budget_minutes=time_budget,
        )
        db.add(session)
        db.flush()

        exercises = db.query(Exercise).filter(Exercise.slug.in_(exercise_slugs)).all()
        # Maintain the order provided by the user
        slug_order = {s: i for i, s in enumerate(exercise_slugs)}
        exercises.sort(key=lambda e: slug_order.get(e.slug, 999))

        planned = _build_planned_exercises(exercises, "intermediate", time_budget_minutes=time_budget or 0)
        session.planned_exercises = planned
        db.commit()

    elif not session:
        # Coached path: find today's session or create from plan
        session = db.query(WorkoutSession).filter(
            WorkoutSession.user_id == user_id,
            WorkoutSession.scheduled_date == date.today(),
            WorkoutSession.status.in_([SessionStatus.PLANNED, SessionStatus.IN_PROGRESS]),
        ).order_by(WorkoutSession.id.desc()).first()

        if session and not session.planned_exercises:
            # Load exercises from plan
            _populate_session_from_plan(db, user_id, session)

        if not session:
            # No session exists — create ad-hoc
            session = WorkoutSession(
                user_id=user_id,
                session_type=SessionType.COACHED,
                status=SessionStatus.PLANNED,
                scheduled_date=date.today(),
                time_budget_minutes=time_budget,
            )
            db.add(session)
            db.flush()
            _populate_session_from_plan(db, user_id, session)

    if time_budget:
        session.time_budget_minutes = time_budget

    db.commit()

    planned = session.planned_exercises or []
    # Apply trimming if time budget set
    if time_budget and time_budget > 0:
        planned = _trim_exercises(planned, time_budget)

    # Build day label
    day_label = _get_day_label(db, user_id, session)

    return _agent_response(
        view="brief",
        data={
            "session_id": session.id,
            "day_label": day_label,
            "exercises": planned,
            "time_budget_minutes": session.time_budget_minutes,
            "estimated_minutes": _estimate_total_minutes(planned),
        },
        coach_says=_brief_coach_message(planned),
        available_actions=["adjust_time", "begin_workout", "end_workout"],
    )


def _handle_adjust_time(db: Session, user_id: int, session_id: Optional[int], params: dict) -> dict:
    """Re-trim the exercise list for a new time budget."""
    minutes = params.get("minutes", 45)

    session = _get_session(db, user_id, session_id)
    session.time_budget_minutes = minutes
    db.commit()

    planned = session.planned_exercises or []
    trimmed = _trim_exercises(planned, minutes)

    day_label = _get_day_label(db, user_id, session)

    return _agent_response(
        view="brief",
        data={
            "session_id": session.id,
            "day_label": day_label,
            "exercises": trimmed,
            "time_budget_minutes": minutes,
            "estimated_minutes": _estimate_total_minutes(trimmed),
        },
        coach_says=f"Got it — trimmed to fit {minutes} minutes.",
        available_actions=["adjust_time", "begin_workout", "end_workout"],
    )


def _handle_begin_workout(db: Session, user_id: int, session_id: Optional[int], params: dict) -> dict:
    """Lock in the plan and transition to the first exercise."""
    session = _get_session(db, user_id, session_id)
    session.status = SessionStatus.IN_PROGRESS
    session.started_at = datetime.utcnow()
    db.commit()

    planned = _get_active_exercises(session)
    if not planned:
        return _handle_end_workout(db, user_id, session_id, {})

    first = planned[0]
    exercise = db.query(Exercise).filter(Exercise.id == first["exercise_id"]).first()
    history = get_exercise_history(db, user_id, first["exercise_id"]) if exercise else {}

    return _agent_response(
        view="exercise_intro",
        data={
            "session_id": session.id,
            "exercise": _enrich_exercise(first, exercise),
            "form_cues": (exercise.form_cues or [])[:3] if exercise else [],
            "history": history,
        },
        coach_says=f"Let's start with {first['name']}. {(exercise.form_cues or [''])[0] if exercise and exercise.form_cues else 'Focus on form.'}",
        available_actions=["complete_set", "skip_exercise", "end_workout"],
        progress=_build_progress(planned, 0, 1),
    )


def _handle_complete_set(db: Session, user_id: int, session_id: Optional[int], params: dict) -> dict:
    """Log a completed set and determine the next phase."""
    session = _get_session(db, user_id, session_id)
    planned = _get_active_exercises(session)

    exercise_id = params.get("exercise_id")
    set_number = params.get("set_number", 1)
    actual_reps = params.get("reps")
    weight_kg = params.get("weight_kg")
    rpe = params.get("rpe")
    duration_seconds = params.get("duration_seconds")

    # Find the exercise in planned list
    ex_info = None
    ex_index = 0
    for i, ex in enumerate(planned):
        if ex["exercise_id"] == exercise_id:
            ex_info = ex
            ex_index = i
            break

    if not ex_info:
        raise ValueError(f"Exercise {exercise_id} not in session plan")

    # Determine target reps
    target_reps = _parse_target_reps(ex_info.get("reps", "10"))

    # Insert ExerciseSet row
    exercise_set = ExerciseSet(
        session_id=session.id,
        exercise_id=exercise_id,
        set_number=set_number,
        target_reps=target_reps,
        actual_reps=actual_reps,
        weight_kg=weight_kg,
        duration_seconds=duration_seconds,
        rpe=rpe,
        form_score=params.get("form_score"),
        challenge_session_id=params.get("challenge_session_id"),
        exercise_order=ex_info.get("order", ex_index),
        completed_at=datetime.utcnow(),
    )
    db.add(exercise_set)
    db.commit()

    # Generate coach feedback (LLM-enhanced)
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    form_score = params.get("form_score")
    feedback = try_smart_set_feedback(
        db, user_id, exercise_id, actual_reps or 0, target_reps, weight_kg, rpe, form_score
    )

    total_sets = ex_info.get("sets", 3)
    sets_remaining = total_sets - set_number

    if sets_remaining > 0:
        # More sets for this exercise → rest timer
        rest_sec = REST_DURATIONS.get(
            exercise.category if exercise else "compound", 90
        )
        tip = generate_rest_tip(
            ex_info["name"], set_number, actual_reps, rpe
        )

        return _agent_response(
            view="rest_timer",
            data={
                "session_id": session.id,
                "rest_duration_sec": rest_sec,
                "next_set": {
                    "exercise_id": exercise_id,
                    "name": ex_info["name"],
                    "set_number": set_number + 1,
                    "sets_total": total_sets,
                    "target_reps": target_reps,
                },
                "feedback": feedback,
            },
            coach_says=feedback + " " + tip,
            available_actions=["skip_rest", "end_workout"],
            progress=_build_progress(planned, ex_index, set_number + 1),
        )

    # This exercise is done — check if more exercises
    next_index = ex_index + 1
    if next_index < len(planned):
        next_ex = planned[next_index]
        next_exercise = db.query(Exercise).filter(Exercise.id == next_ex["exercise_id"]).first()
        history = get_exercise_history(db, user_id, next_ex["exercise_id"]) if next_exercise else {}

        return _agent_response(
            view="exercise_intro",
            data={
                "session_id": session.id,
                "exercise": _enrich_exercise(next_ex, next_exercise),
                "form_cues": (next_exercise.form_cues or [])[:3] if next_exercise else [],
                "history": history,
                "prev_feedback": feedback,
            },
            coach_says=f"{feedback} Moving on to {next_ex['name']}.",
            available_actions=["complete_set", "skip_exercise", "end_workout"],
            progress=_build_progress(planned, next_index, 1),
        )

    # All exercises done → cooldown
    return _agent_response(
        view="cooldown",
        data={
            "session_id": session.id,
            "feedback": feedback,
            "stretches": [
                "Chest stretch — hold 20 seconds each side",
                "Quad stretch — hold 20 seconds each leg",
                "Shoulder cross-body stretch — 15 seconds each",
            ],
        },
        coach_says=f"{feedback} All exercises done! Take a minute to cool down.",
        available_actions=["end_workout"],
        progress=_build_progress(planned, len(planned) - 1, total_sets),
    )


def _handle_skip_exercise(db: Session, user_id: int, session_id: Optional[int], params: dict) -> dict:
    """Skip the current exercise and advance to the next one."""
    session = _get_session(db, user_id, session_id)
    planned = _get_active_exercises(session)

    exercise_id = params.get("exercise_id")

    # Find current exercise index
    ex_index = 0
    for i, ex in enumerate(planned):
        if ex["exercise_id"] == exercise_id:
            ex_index = i
            break

    # Mark as skipped by inserting a skipped set record
    skip_set = ExerciseSet(
        session_id=session.id,
        exercise_id=exercise_id,
        set_number=0,
        exercise_order=planned[ex_index].get("order", ex_index) if ex_index < len(planned) else ex_index,
        is_skipped=True,
        completed_at=datetime.utcnow(),
    )
    db.add(skip_set)
    db.commit()

    # Advance to next exercise
    next_index = ex_index + 1
    if next_index < len(planned):
        next_ex = planned[next_index]
        exercise = db.query(Exercise).filter(Exercise.id == next_ex["exercise_id"]).first()
        history = get_exercise_history(db, user_id, next_ex["exercise_id"]) if exercise else {}

        return _agent_response(
            view="exercise_intro",
            data={
                "session_id": session.id,
                "exercise": _enrich_exercise(next_ex, exercise),
                "form_cues": (exercise.form_cues or [])[:3] if exercise else [],
                "history": history,
            },
            coach_says=f"Skipped. Next up: {next_ex['name']}.",
            available_actions=["complete_set", "skip_exercise", "end_workout"],
            progress=_build_progress(planned, next_index, 1),
        )

    # No more exercises → cooldown
    return _agent_response(
        view="cooldown",
        data={
            "session_id": session.id,
            "stretches": [
                "Chest stretch — hold 20 seconds each side",
                "Quad stretch — hold 20 seconds each leg",
                "Shoulder cross-body stretch — 15 seconds each",
            ],
        },
        coach_says="That was the last exercise. Let's cool down.",
        available_actions=["end_workout"],
    )


def _handle_skip_rest(db: Session, user_id: int, session_id: Optional[int], params: dict) -> dict:
    """Skip rest timer, go to the next set."""
    session = _get_session(db, user_id, session_id)
    planned = _get_active_exercises(session)

    # The frontend should pass exercise_id and next set_number
    exercise_id = params.get("exercise_id")
    set_number = params.get("set_number", 1)

    ex_info = None
    ex_index = 0
    for i, ex in enumerate(planned):
        if ex["exercise_id"] == exercise_id:
            ex_info = ex
            ex_index = i
            break

    if not ex_info:
        raise ValueError(f"Exercise {exercise_id} not in session plan")

    target_reps = _parse_target_reps(ex_info.get("reps", "10"))

    # Check if this exercise supports camera tracking
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    tracking_mode = exercise.tracking_mode if exercise else "reps"

    # Get progression targets
    progression = ProgressiveOverloadEngine.get_targets_for_exercise(db, user_id, exercise_id)

    active_data = {
        "session_id": session.id,
        "exercise": ex_info,
        "set_number": set_number,
        "sets_total": ex_info.get("sets", 3),
        "target_reps": target_reps,
        "tracking_mode": tracking_mode,
    }
    if progression:
        active_data["progression"] = progression

    return _agent_response(
        view="active_set",
        data=active_data,
        coach_says=f"Set {set_number} of {ex_info.get('sets', 3)}. Let's go.",
        available_actions=["complete_set", "skip_exercise", "end_workout"],
        progress=_build_progress(planned, ex_index, set_number),
    )


def _handle_modify_exercise(db: Session, user_id: int, session_id: Optional[int], params: dict) -> dict:
    """Modify sets/reps for an exercise in the current plan."""
    session = _get_session(db, user_id, session_id)
    planned = session.planned_exercises or []

    exercise_id = params.get("exercise_id")
    new_sets = params.get("sets")
    new_reps = params.get("reps")

    updated = []
    target_ex = None
    for ex in planned:
        if ex.get("exercise_id") == exercise_id or ex.get("slug") == str(exercise_id):
            new_ex = {**ex}
            if new_sets is not None:
                new_ex["sets"] = int(new_sets)
            if new_reps is not None:
                new_ex["reps"] = str(new_reps)
            updated.append(new_ex)
            target_ex = new_ex
        else:
            updated.append(ex)

    if not target_ex:
        raise ValueError(f"Exercise {exercise_id} not in session plan")

    session.planned_exercises = updated
    db.commit()

    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    history = get_exercise_history(db, user_id, exercise_id) if exercise else {}

    return _agent_response(
        view="exercise_intro",
        data={
            "session_id": session.id,
            "exercise": _enrich_exercise(target_ex, exercise),
            "form_cues": (exercise.form_cues or [])[:3] if exercise else [],
            "history": history,
        },
        coach_says=f"Updated to {target_ex.get('sets', 3)} sets x {target_ex.get('reps', '10')}.",
        available_actions=["complete_set", "skip_exercise", "end_workout"],
        progress=_build_progress(updated, updated.index(target_ex), 1),
    )


def _handle_update_plan(db: Session, user_id: int, session_id: Optional[int], params: dict) -> dict:
    """Bulk update the exercise plan: reorder, edit sets/reps, delete exercises.

    params.exercises: list of {exercise_id, slug, name, sets, reps, ...} in desired order.
    Only exercises present in the list are kept (deletions = omitted exercises).
    """
    session = _get_session(db, user_id, session_id)

    new_exercises = params.get("exercises", [])
    if not new_exercises:
        raise ValueError("Cannot have an empty exercise plan")

    # Rebuild planned_exercises preserving all original fields, updating sets/reps/order
    old_by_id = {}
    for ex in (session.planned_exercises or []):
        key = ex.get("exercise_id") or ex.get("slug")
        old_by_id[key] = ex

    updated = []
    for i, incoming in enumerate(new_exercises):
        key = incoming.get("exercise_id") or incoming.get("slug")
        base = old_by_id.get(key, incoming)
        merged = {**base}
        if "sets" in incoming:
            merged["sets"] = int(incoming["sets"])
        if "reps" in incoming:
            merged["reps"] = str(incoming["reps"])
        merged["order"] = i
        updated.append(merged)

    session.planned_exercises = updated
    db.commit()

    day_label = _get_day_label(db, user_id, session)

    return _agent_response(
        view="brief",
        data={
            "session_id": session.id,
            "day_label": day_label,
            "exercises": updated,
            "estimated_minutes": len(updated) * 5,
        },
        coach_says=f"Plan updated — {len(updated)} exercises. Ready when you are!",
        available_actions=["adjust_time", "begin_workout", "end_workout"],
    )


def _handle_end_workout(db: Session, user_id: int, session_id: Optional[int], params: dict) -> dict:
    """Finalize the session — compute summary stats."""
    session = _get_session(db, user_id, session_id)
    session.status = SessionStatus.COMPLETED
    session.ended_at = datetime.utcnow()

    if session.started_at:
        session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())

    db.commit()

    summary = generate_session_summary(db, user_id, session)

    # Try LLM-enhanced summary
    smart_coach = try_smart_summary(db, user_id, session, summary)
    summary["coach_summary"] = smart_coach

    # Compute progressive overload targets for next session
    planned = session.planned_exercises or []
    progression_updates = []
    for ex in planned:
        eid = ex.get("exercise_id")
        if eid:
            targets = ProgressiveOverloadEngine.compute_next_targets(db, user_id, eid)
            if targets.get("progression_type") != "maintain":
                progression_updates.append({
                    "exercise": ex.get("name"),
                    "type": targets["progression_type"],
                    "rationale": targets.get("rationale"),
                })

    summary["progression_updates"] = progression_updates

    session.summary = summary
    db.commit()

    return _agent_response(
        view="summary",
        data={
            "session_id": session.id,
            **summary,
        },
        coach_says=smart_coach,
        available_actions=[],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_session(db: Session, user_id: int, session_id: Optional[int]) -> WorkoutSession:
    """Fetch session or raise."""
    if not session_id:
        raise ValueError("session_id is required")
    session = db.query(WorkoutSession).filter(
        WorkoutSession.id == session_id,
        WorkoutSession.user_id == user_id,
    ).first()
    if not session:
        raise ValueError(f"Session {session_id} not found")
    return session


def _get_active_exercises(session: WorkoutSession) -> list:
    """Get the planned exercises, applying time budget trimming if needed."""
    planned = session.planned_exercises or []
    if session.time_budget_minutes and session.time_budget_minutes > 0:
        return _trim_exercises(planned, session.time_budget_minutes)
    return planned


def _populate_session_from_plan(db: Session, user_id: int, session: WorkoutSession):
    """Load exercises into the session from the user's active plan."""
    plan = db.query(WorkoutPlan).filter(
        WorkoutPlan.user_id == user_id,
        WorkoutPlan.status == PlanStatus.ACTIVE,
    ).first()

    if not plan or not plan.plan_data:
        return

    today_day_name = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][date.today().weekday()]

    today_day = None
    for day in plan.plan_data.get("days", []):
        if day.get("day") == today_day_name:
            today_day = day
            break

    if not today_day:
        # Fallback: use the first day in the plan
        days = plan.plan_data.get("days", [])
        if days:
            today_day = days[0]

    if not today_day:
        return

    plan_exercises = today_day.get("exercises", [])

    # Resolve exercise IDs
    slugs = [ex["slug"] for ex in plan_exercises]
    db_exercises = db.query(Exercise).filter(Exercise.slug.in_(slugs)).all()
    slug_to_id = {e.slug: e.id for e in db_exercises}

    planned = []
    for i, ex in enumerate(plan_exercises):
        eid = slug_to_id.get(ex["slug"])
        if not eid:
            continue
        planned.append({
            "exercise_id": eid,
            "slug": ex["slug"],
            "name": ex["name"],
            "sets": ex.get("sets", 3),
            "reps": ex.get("reps", "10"),
            "equipment": ex.get("equipment", ["none"]),
            "order": i,
        })

    session.planned_exercises = planned
    if plan.id:
        session.plan_id = plan.id


def _build_planned_exercises(exercises: list, fitness_level: str = "intermediate", time_budget_minutes: int = 0) -> list:
    """Build planned_exercises JSON from a list of Exercise ORM objects."""
    volume = VOLUME_SCHEMES.get(fitness_level, VOLUME_SCHEMES["intermediate"])
    sets = volume.get("sets", volume.get("base_sets", 3))

    # Adjust sets based on time budget vs exercise count
    if time_budget_minutes > 0 and len(exercises) > 0:
        from .plan_generator import _plan_for_duration
        _, sets = _plan_for_duration(time_budget_minutes, volume.get("base_sets", 3))

    return [
        {
            "exercise_id": ex.id,
            "slug": ex.slug,
            "name": ex.name,
            "sets": sets,
            "reps": volume["reps"] if ex.tracking_mode == "reps" else "30s",
            "equipment": ex.equipment or ["none"],
            "order": i,
        }
        for i, ex in enumerate(exercises)
    ]


def _trim_exercises(planned: list, time_budget_minutes: int) -> list:
    """Trim exercises to fit within time budget. ~7 min per exercise."""
    max_exercises = max(1, time_budget_minutes // 7)
    return planned[:max_exercises]


def _estimate_total_minutes(planned: list) -> int:
    """Estimate total workout time from planned exercises."""
    total = 0
    for ex in planned:
        sets = ex.get("sets", 3)
        # ~40s work + ~75s rest per set
        total += sets * (40 + 75)
    return max(10, round(total / 60))


def _get_day_label(db: Session, user_id: int, session: WorkoutSession) -> str:
    """Get a human-readable day label for the session."""
    if session.plan_id:
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == session.plan_id).first()
        if plan and plan.plan_data:
            today_day_name = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][date.today().weekday()]
            for day in plan.plan_data.get("days", []):
                if day.get("day") == today_day_name:
                    return day.get("label", "Workout")
    return "Quick Workout" if session.session_type == SessionType.QUICK_START else "Workout"


def _build_progress(planned: list, exercise_index: int, set_number: int) -> dict:
    """Build progress dict for the response."""
    current_ex = planned[exercise_index] if exercise_index < len(planned) else None
    return {
        "exercise_index": exercise_index,
        "exercise_total": len(planned),
        "set_number": set_number,
        "sets_total": current_ex.get("sets", 3) if current_ex else 0,
    }


def _parse_target_reps(reps_str) -> Optional[int]:
    """Parse a reps string like '8-10' or '30s' into a target integer."""
    if isinstance(reps_str, int):
        return reps_str
    if not reps_str:
        return None
    reps_str = str(reps_str).strip()
    if reps_str.endswith("s"):
        return None  # timed exercise
    if "-" in reps_str:
        # Take the upper end of the range
        parts = reps_str.split("-")
        try:
            return int(parts[-1])
        except ValueError:
            return None
    try:
        return int(reps_str)
    except ValueError:
        return None


def _brief_coach_message(planned: list) -> str:
    """Generate a coach message for the brief screen."""
    count = len(planned)
    if count == 0:
        return "No exercises loaded. Try a quick start!"
    minutes = _estimate_total_minutes(planned)
    return f"{count} exercises, ~{minutes} minutes. Ready when you are."


# ---------------------------------------------------------------------------
# Plan Modification Helpers (called by chat_agent)
# ---------------------------------------------------------------------------

def swap_exercise_in_plan(
    planned_exercises: list[dict],
    old_slug: str,
    new_slug: str,
    new_name: Optional[str] = None,
) -> list[dict]:
    """Swap an exercise in the plan. Returns updated exercise list."""
    updated = []
    swapped = False
    for ex in planned_exercises:
        if ex.get("slug") == old_slug and not swapped:
            new_ex = {**ex, "slug": new_slug, "name": new_name or new_slug.replace("-", " ").title()}
            updated.append(new_ex)
            swapped = True
            logger.info("Swapped exercise %s -> %s", old_slug, new_slug)
        else:
            updated.append(ex)
    return updated


def adjust_exercise_targets(
    planned_exercises: list[dict],
    exercise_id,
    weight_kg: Optional[float] = None,
    reps: Optional[int] = None,
) -> list[dict]:
    """Adjust weight/reps for an exercise. Returns updated list."""
    updated = []
    for ex in planned_exercises:
        if ex.get("exercise_id") == exercise_id or ex.get("slug") == str(exercise_id):
            new_ex = {**ex}
            if weight_kg is not None:
                new_ex["weight_kg"] = weight_kg
            if reps is not None:
                new_ex["reps"] = str(reps)
            updated.append(new_ex)
        else:
            updated.append(ex)
    return updated


def add_exercise_to_plan(
    planned_exercises: list[dict],
    slug: str,
    position: Optional[int] = None,
    name: Optional[str] = None,
    sets: int = 3,
    reps: str = "10",
) -> list[dict]:
    """Insert an exercise into the plan. Returns updated list."""
    new_ex = {
        "slug": slug,
        "name": name or slug.replace("-", " ").title(),
        "sets": sets,
        "reps": reps,
        "order": position if position is not None else len(planned_exercises),
    }
    updated = list(planned_exercises)
    if position is not None and 0 <= position <= len(updated):
        updated.insert(position, new_ex)
    else:
        updated.append(new_ex)
    return updated


def remove_exercise_from_plan(
    planned_exercises: list[dict],
    exercise_id,
) -> list[dict]:
    """Remove an exercise from the plan. Returns updated list."""
    return [
        ex for ex in planned_exercises
        if ex.get("exercise_id") != exercise_id and ex.get("slug") != str(exercise_id)
    ]
