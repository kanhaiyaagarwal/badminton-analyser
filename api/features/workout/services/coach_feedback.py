"""Coach feedback engine — LLM-enhanced with template fallbacks."""

import asyncio
import logging
import random
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db_models.workout import ExerciseSet, Exercise, WorkoutSession, SessionStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Set Feedback
# ---------------------------------------------------------------------------

_TARGET_EXACT = [
    "Right on target.",
    "Nailed it. Exactly as planned.",
    "Perfect execution.",
]

_TARGET_OVER = [
    "{delta} more than planned. Strong.",
    "Exceeded target by {delta}. Nice push.",
    "{actual} reps — {delta} above target. Solid.",
]

_TARGET_UNDER = [
    "{actual} of {target} — still solid work.",
    "Short of target by {delta}, but every rep counts.",
    "{actual} reps today. We'll build from here.",
]

_PR_REPS = [
    "New PR! {reps} reps — personal best!",
    "Personal record! {reps} reps. You're leveling up.",
]

_PR_WEIGHT = [
    "New weight PR! {weight}kg. Stronger than ever.",
    "PR alert — {weight}kg is a new personal best!",
]

_VS_LAST_BETTER = [
    "Up from {last} last time.",
    "Improved from {last} reps last session.",
]

_VS_LAST_SAME = [
    "Matching your last session.",
    "Consistent with last time. Solid.",
]

_RPE_EASY = [
    "Felt easy? Consider adding weight next time.",
    "Low effort noted. Room to push harder.",
]

_RPE_HARD = [
    "Tough set. Rest well before the next one.",
    "Hard effort. Recovery matters — take your time.",
]

_RPE_MEDIUM = [
    "Good effort. Right in the sweet spot.",
    "Solid intensity. Keep it up.",
]


def generate_set_feedback(
    db: Session,
    user_id: int,
    exercise_id: int,
    actual_reps: int,
    target_reps: Optional[int],
    weight_kg: Optional[float],
    rpe: Optional[int],
) -> str:
    """Compare to target, last session, PRs. Return coach message."""
    parts = []

    # vs target
    if target_reps and actual_reps:
        delta = actual_reps - target_reps
        if delta == 0:
            parts.append(random.choice(_TARGET_EXACT))
        elif delta > 0:
            parts.append(random.choice(_TARGET_OVER).format(
                delta=delta, actual=actual_reps, target=target_reps
            ))
        else:
            parts.append(random.choice(_TARGET_UNDER).format(
                delta=abs(delta), actual=actual_reps, target=target_reps
            ))

    # Check PRs
    pr_reps = _get_pr_reps(db, user_id, exercise_id)
    pr_weight = _get_pr_weight(db, user_id, exercise_id)

    if actual_reps and pr_reps is not None and actual_reps > pr_reps:
        parts.append(random.choice(_PR_REPS).format(reps=actual_reps))
    elif weight_kg and pr_weight is not None and weight_kg > pr_weight:
        parts.append(random.choice(_PR_WEIGHT).format(weight=weight_kg))

    # vs last session
    last_reps = _get_last_session_reps(db, user_id, exercise_id)
    if last_reps is not None and actual_reps and not any("PR" in p for p in parts):
        if actual_reps > last_reps:
            parts.append(random.choice(_VS_LAST_BETTER).format(last=last_reps))
        elif actual_reps == last_reps:
            parts.append(random.choice(_VS_LAST_SAME))

    # RPE feedback
    if rpe is not None and not parts:  # only add RPE if no other feedback
        if rpe <= 3:
            parts.append(random.choice(_RPE_EASY))
        elif rpe >= 8:
            parts.append(random.choice(_RPE_HARD))
        else:
            parts.append(random.choice(_RPE_MEDIUM))

    if not parts:
        parts.append("Set logged. Keep going!")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Rest Tips
# ---------------------------------------------------------------------------

_REST_TIPS = [
    "Shake out your arms. Stay loose.",
    "Deep breaths. You've got this.",
    "Hydrate. Your muscles need it.",
    "Visualize the next set. Smooth, controlled reps.",
    "Roll your shoulders back. Posture matters even at rest.",
    "Quick stretch if anything feels tight.",
]


def generate_rest_tip(exercise_name: str, set_number: int, last_reps: Optional[int], rpe: Optional[int]) -> str:
    """Contextual rest period tip."""
    if rpe and rpe >= 8:
        return "Take your full rest. That was a tough set."
    if rpe and rpe <= 3:
        return "Consider increasing weight on the next set."
    return random.choice(_REST_TIPS)


# ---------------------------------------------------------------------------
# Session Summary
# ---------------------------------------------------------------------------

def generate_session_summary(db: Session, user_id: int, session: WorkoutSession) -> dict:
    """Compute highlights, PRs, coach summary text."""
    sets = db.query(ExerciseSet).filter(
        ExerciseSet.session_id == session.id,
        ExerciseSet.is_skipped == False,
    ).all()

    exercises_completed = len(set(s.exercise_id for s in sets))
    total_sets = len(sets)
    total_reps = sum(s.actual_reps or 0 for s in sets)
    total_volume = sum((s.actual_reps or 0) * (s.weight_kg or 0) for s in sets)

    # Duration
    duration_seconds = 0
    if session.started_at and session.ended_at:
        duration_seconds = int((session.ended_at - session.started_at).total_seconds())
    elif session.started_at:
        duration_seconds = int((datetime.utcnow() - session.started_at).total_seconds())

    duration_minutes = round(duration_seconds / 60)

    # Find PRs achieved this session
    prs = []
    exercise_ids = set(s.exercise_id for s in sets)
    for eid in exercise_ids:
        session_sets = [s for s in sets if s.exercise_id == eid]
        exercise = db.query(Exercise).filter(Exercise.id == eid).first()
        if not exercise:
            continue

        max_reps = max((s.actual_reps or 0) for s in session_sets)
        max_weight = max((s.weight_kg or 0) for s in session_sets)

        # Check if this is a PR
        prev_max_reps = db.query(func.max(ExerciseSet.actual_reps)).join(WorkoutSession).filter(
            WorkoutSession.user_id == user_id,
            ExerciseSet.exercise_id == eid,
            ExerciseSet.session_id != session.id,
        ).scalar() or 0

        prev_max_weight = db.query(func.max(ExerciseSet.weight_kg)).join(WorkoutSession).filter(
            WorkoutSession.user_id == user_id,
            ExerciseSet.exercise_id == eid,
            ExerciseSet.session_id != session.id,
        ).scalar() or 0

        if max_reps > prev_max_reps and max_reps > 0:
            prs.append({"exercise": exercise.name, "type": "reps", "value": max_reps})
        if max_weight > prev_max_weight and max_weight > 0:
            prs.append({"exercise": exercise.name, "type": "weight", "value": max_weight})

    # Highlights
    highlights = []
    if prs:
        highlights.append(f"{len(prs)} new PR{'s' if len(prs) > 1 else ''}!")
    if total_volume > 0:
        highlights.append(f"{round(total_volume, 1)}kg total volume")
    if total_reps > 0:
        highlights.append(f"{total_reps} total reps")

    # Streak
    from .workout_service import WorkoutService
    streak = WorkoutService._compute_streak(db, user_id)

    # Coach summary
    if prs:
        coach = f"Outstanding session! {len(prs)} personal record{'s' if len(prs) > 1 else ''}. Your hard work is paying off."
    elif exercises_completed >= 5:
        coach = "Massive session. You crushed every exercise. Recovery is your next workout."
    elif total_reps > 50:
        coach = f"{total_reps} reps — solid volume today. Consistency wins the game."
    else:
        coach = "Another workout in the books. Every session makes you stronger."

    return {
        "exercises_completed": exercises_completed,
        "total_sets": total_sets,
        "total_reps": total_reps,
        "total_volume_kg": round(total_volume, 1),
        "duration_minutes": duration_minutes,
        "duration_seconds": duration_seconds,
        "prs": prs,
        "highlights": highlights,
        "streak": streak,
        "coach_summary": coach,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_pr_reps(db: Session, user_id: int, exercise_id: int) -> Optional[int]:
    """Get the best reps for this exercise across all sessions."""
    return db.query(func.max(ExerciseSet.actual_reps)).join(WorkoutSession).filter(
        WorkoutSession.user_id == user_id,
        ExerciseSet.exercise_id == exercise_id,
    ).scalar()


def _get_pr_weight(db: Session, user_id: int, exercise_id: int) -> Optional[float]:
    """Get the best weight for this exercise across all sessions."""
    return db.query(func.max(ExerciseSet.weight_kg)).join(WorkoutSession).filter(
        WorkoutSession.user_id == user_id,
        ExerciseSet.exercise_id == exercise_id,
    ).scalar()


def _get_last_session_reps(db: Session, user_id: int, exercise_id: int) -> Optional[int]:
    """Get reps from the most recent completed set of this exercise."""
    last_set = db.query(ExerciseSet).join(WorkoutSession).filter(
        WorkoutSession.user_id == user_id,
        ExerciseSet.exercise_id == exercise_id,
        WorkoutSession.status == SessionStatus.COMPLETED,
    ).order_by(ExerciseSet.id.desc()).first()

    return last_set.actual_reps if last_set else None


def get_exercise_history(db: Session, user_id: int, exercise_id: int) -> dict:
    """Get exercise history for the intro screen: last session data and PRs."""
    pr_reps = _get_pr_reps(db, user_id, exercise_id)
    pr_weight = _get_pr_weight(db, user_id, exercise_id)

    # Last session data
    last_sets = db.query(ExerciseSet).join(WorkoutSession).filter(
        WorkoutSession.user_id == user_id,
        ExerciseSet.exercise_id == exercise_id,
        WorkoutSession.status == SessionStatus.COMPLETED,
    ).order_by(ExerciseSet.id.desc()).limit(10).all()

    last_session = None
    if last_sets:
        # Group by session_id to get the most recent session's sets
        latest_session_id = last_sets[0].session_id
        session_sets = [s for s in last_sets if s.session_id == latest_session_id]
        last_session = {
            "sets": len(session_sets),
            "best_reps": max((s.actual_reps or 0) for s in session_sets),
            "best_weight": max((s.weight_kg or 0) for s in session_sets),
            "avg_rpe": round(
                sum(s.rpe or 0 for s in session_sets if s.rpe) /
                max(1, sum(1 for s in session_sets if s.rpe)),
                1
            ) if any(s.rpe for s in session_sets) else None,
        }

    return {
        "pr_reps": pr_reps,
        "pr_weight": pr_weight,
        "last_session": last_session,
    }


# ---------------------------------------------------------------------------
# LLM-Enhanced Feedback (async, with template fallbacks)
# ---------------------------------------------------------------------------

_SET_FEEDBACK_PROMPT = """\
You are a concise strength coach. Given a user's set data, write 1-2 sentences of \
personalized feedback. Be encouraging but honest. Reference specific numbers. \
Keep it under 30 words.

Output JSON: {"feedback": "..."}
"""

_SUMMARY_PROMPT = """\
You are a strength coach reviewing a workout session. Write a 2-3 sentence personalized \
summary that mentions specific achievements, areas for improvement, and motivation \
for next session. Keep it under 50 words.

Output JSON: {"summary": "..."}
"""


async def generate_smart_set_feedback(
    db: Session,
    user_id: int,
    exercise_id: int,
    actual_reps: int,
    target_reps: Optional[int],
    weight_kg: Optional[float],
    rpe: Optional[int],
    form_score: Optional[int] = None,
) -> Optional[str]:
    """LLM-powered set feedback. Returns None if LLM unavailable."""
    try:
        from . import llm_service

        exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
        name = exercise.name if exercise else "Exercise"

        # Build context
        context = f"Exercise: {name}\n"
        context += f"Reps: {actual_reps}" + (f" / {target_reps} target" if target_reps else "") + "\n"
        if weight_kg:
            context += f"Weight: {weight_kg}kg\n"
        if rpe:
            context += f"RPE: {rpe}/10\n"
        if form_score:
            context += f"Form score: {form_score}/100\n"

        # Add history context
        pr_reps = _get_pr_reps(db, user_id, exercise_id)
        pr_weight = _get_pr_weight(db, user_id, exercise_id)
        last_reps = _get_last_session_reps(db, user_id, exercise_id)

        if pr_reps and actual_reps and actual_reps > pr_reps:
            context += f"NEW REP PR! Previous best: {pr_reps}\n"
        if pr_weight and weight_kg and weight_kg > pr_weight:
            context += f"NEW WEIGHT PR! Previous best: {pr_weight}kg\n"
        if last_reps:
            context += f"Last session reps: {last_reps}\n"

        result = await llm_service.chat(
            system_prompt=_SET_FEEDBACK_PROMPT,
            user_prompt=context,
            json_mode=True,
            temperature=0.8,
            max_tokens=150,
        )

        if result and result.get("feedback"):
            return result["feedback"]
    except Exception as e:
        logger.debug(f"LLM set feedback failed: {e}")

    return None


async def generate_smart_summary(
    db: Session,
    user_id: int,
    session: WorkoutSession,
    template_summary: dict,
) -> Optional[str]:
    """LLM-powered session summary. Returns None if LLM unavailable."""
    try:
        from . import llm_service

        context = f"Session stats:\n"
        context += f"- Exercises completed: {template_summary.get('exercises_completed', 0)}\n"
        context += f"- Total sets: {template_summary.get('total_sets', 0)}\n"
        context += f"- Total reps: {template_summary.get('total_reps', 0)}\n"
        context += f"- Duration: {template_summary.get('duration_minutes', 0)} minutes\n"
        if template_summary.get('total_volume_kg'):
            context += f"- Total volume: {template_summary['total_volume_kg']}kg\n"
        if template_summary.get('prs'):
            prs_text = ", ".join(f"{p['exercise']} ({p['type']}: {p['value']})" for p in template_summary['prs'])
            context += f"- PRs achieved: {prs_text}\n"
        if template_summary.get('streak'):
            context += f"- Current streak: {template_summary['streak']} days\n"

        result = await llm_service.chat(
            system_prompt=_SUMMARY_PROMPT,
            user_prompt=context,
            json_mode=True,
            temperature=0.8,
            max_tokens=200,
        )

        if result and result.get("summary"):
            return result["summary"]
    except Exception as e:
        logger.debug(f"LLM summary failed: {e}")

    return None


def try_smart_set_feedback(
    db: Session,
    user_id: int,
    exercise_id: int,
    actual_reps: int,
    target_reps: Optional[int],
    weight_kg: Optional[float],
    rpe: Optional[int],
    form_score: Optional[int] = None,
) -> str:
    """Sync wrapper: try LLM feedback, fall back to template."""
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            generate_smart_set_feedback(
                db, user_id, exercise_id, actual_reps, target_reps, weight_kg, rpe, form_score
            )
        )
        loop.close()
        if result:
            return result
    except Exception as e:
        logger.debug(f"Smart feedback unavailable: {e}")

    return generate_set_feedback(db, user_id, exercise_id, actual_reps, target_reps, weight_kg, rpe)


def try_smart_summary(db: Session, user_id: int, session: WorkoutSession, template_summary: dict) -> str:
    """Sync wrapper: try LLM summary, fall back to template."""
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            generate_smart_summary(db, user_id, session, template_summary)
        )
        loop.close()
        if result:
            return result
    except Exception as e:
        logger.debug(f"Smart summary unavailable: {e}")

    return template_summary.get("coach_summary", "Workout complete!")
