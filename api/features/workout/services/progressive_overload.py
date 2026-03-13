"""Progressive overload engine — auto-adjusts weight/reps each week.

Rules:
- Compound: +2.5kg when all sets completed at RPE <= 7
- Isolation: +1-2 reps before weight increase
- Bodyweight: +1-2 reps when form score > 80
- Holds: +5-10 seconds
- Deload: after 4 weeks same weight OR RPE consistently > 8
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db_models.workout import (
    Exercise, ExerciseSet, ExerciseProgression,
    WorkoutSession, SessionStatus,
)

logger = logging.getLogger(__name__)


class ProgressiveOverloadEngine:

    @staticmethod
    def compute_next_targets(
        db: Session,
        user_id: int,
        exercise_id: int,
    ) -> dict:
        """Compute next session's targets for an exercise.

        Returns: {
            next_weight_kg, next_reps, rationale,
            progression_type: "increase" | "maintain" | "deload"
        }
        """
        exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
        if not exercise:
            return {"progression_type": "maintain", "rationale": "Exercise not found"}

        # Get or create progression record
        progression = db.query(ExerciseProgression).filter(
            ExerciseProgression.user_id == user_id,
            ExerciseProgression.exercise_id == exercise_id,
        ).first()

        # Get recent sets (last 2 sessions)
        recent_sets = (
            db.query(ExerciseSet)
            .join(WorkoutSession)
            .filter(
                WorkoutSession.user_id == user_id,
                ExerciseSet.exercise_id == exercise_id,
                ExerciseSet.is_skipped == False,
                WorkoutSession.status == SessionStatus.COMPLETED,
            )
            .order_by(ExerciseSet.completed_at.desc())
            .limit(20)
            .all()
        )

        if not recent_sets:
            return {
                "progression_type": "maintain",
                "rationale": "No history yet — start with current targets.",
            }

        # Analyze last session's performance
        last_session_id = recent_sets[0].session_id
        last_session_sets = [s for s in recent_sets if s.session_id == last_session_id]

        avg_rpe = _avg([s.rpe for s in last_session_sets if s.rpe])
        all_completed = all(
            (s.actual_reps or 0) >= (s.target_reps or 0)
            for s in last_session_sets
            if s.target_reps
        )
        current_weight = max((s.weight_kg or 0) for s in last_session_sets)
        current_reps = max((s.actual_reps or 0) for s in last_session_sets)

        # Determine progression based on exercise category
        category = exercise.category

        if category == "compound":
            result = _compound_progression(
                current_weight, current_reps, avg_rpe, all_completed, progression
            )
        elif category == "isolation":
            result = _isolation_progression(
                current_weight, current_reps, avg_rpe, all_completed, progression
            )
        elif category == "bodyweight":
            form_score = _avg([s.form_score for s in last_session_sets if hasattr(s, 'form_score') and s.form_score])
            result = _bodyweight_progression(
                current_reps, avg_rpe, form_score, exercise.tracking_mode, progression
            )
        else:
            result = {
                "next_weight_kg": current_weight,
                "next_reps": current_reps,
                "progression_type": "maintain",
                "rationale": "Maintain current targets.",
            }

        # Update progression record
        _update_progression(db, user_id, exercise_id, result, progression)

        return result

    @staticmethod
    def get_targets_for_exercise(
        db: Session,
        user_id: int,
        exercise_id: int,
    ) -> Optional[dict]:
        """Get stored progression targets for display."""
        prog = db.query(ExerciseProgression).filter(
            ExerciseProgression.user_id == user_id,
            ExerciseProgression.exercise_id == exercise_id,
        ).first()

        if not prog:
            return None

        return {
            "weight_kg": prog.current_weight_kg,
            "reps": prog.current_reps,
            "weeks_at_current": prog.weeks_at_current,
        }


def _compound_progression(
    weight: float, reps: int, avg_rpe: Optional[float],
    all_completed: bool, progression: Optional[ExerciseProgression],
) -> dict:
    """Compound: +2.5kg when all sets completed at RPE <= 7."""
    weeks = progression.weeks_at_current if progression else 0

    # Deload check
    if weeks >= 4 or (avg_rpe and avg_rpe > 8.5):
        deload_weight = round(weight * 0.9, 1)
        return {
            "next_weight_kg": max(0, deload_weight),
            "next_reps": reps,
            "progression_type": "deload",
            "rationale": f"Deload week: dropping to {deload_weight}kg. Recovery helps growth.",
        }

    if all_completed and avg_rpe and avg_rpe <= 7:
        new_weight = weight + 2.5
        return {
            "next_weight_kg": new_weight,
            "next_reps": reps,
            "progression_type": "increase",
            "rationale": f"All sets completed at RPE {avg_rpe:.0f}. Moving up to {new_weight}kg.",
        }

    return {
        "next_weight_kg": weight,
        "next_reps": reps,
        "progression_type": "maintain",
        "rationale": "Keep working at current weight until all sets feel controlled.",
    }


def _isolation_progression(
    weight: float, reps: int, avg_rpe: Optional[float],
    all_completed: bool, progression: Optional[ExerciseProgression],
) -> dict:
    """Isolation: +1-2 reps before weight increase."""
    weeks = progression.weeks_at_current if progression else 0

    if weeks >= 4 or (avg_rpe and avg_rpe > 8.5):
        return {
            "next_weight_kg": max(0, round(weight * 0.9, 1)),
            "next_reps": reps,
            "progression_type": "deload",
            "rationale": "Time for a deload. Lighter weight, focus on form.",
        }

    if all_completed and avg_rpe and avg_rpe <= 7:
        if reps < 12:
            # Add reps first
            return {
                "next_weight_kg": weight,
                "next_reps": reps + 1,
                "progression_type": "increase",
                "rationale": f"Adding 1 rep — working up to 12 before increasing weight.",
            }
        else:
            # At 12 reps — bump weight, reset reps
            new_weight = weight + 1.25 if weight < 10 else weight + 2.5
            return {
                "next_weight_kg": new_weight,
                "next_reps": 8,
                "progression_type": "increase",
                "rationale": f"Hit 12 reps! Moving up to {new_weight}kg for 8 reps.",
            }

    return {
        "next_weight_kg": weight,
        "next_reps": reps,
        "progression_type": "maintain",
        "rationale": "Maintain current targets — focus on full range of motion.",
    }


def _bodyweight_progression(
    reps: int, avg_rpe: Optional[float], form_score: Optional[float],
    tracking_mode: str, progression: Optional[ExerciseProgression],
) -> dict:
    """Bodyweight: +1-2 reps when form is good, or +5-10s for holds."""
    if tracking_mode == "hold":
        # Timed exercises (plank, holds): +5-10 seconds
        current_seconds = reps or 30
        if avg_rpe and avg_rpe <= 6:
            new_seconds = current_seconds + 10
            return {
                "next_weight_kg": 0,
                "next_reps": new_seconds,
                "progression_type": "increase",
                "rationale": f"Good hold! Try {new_seconds} seconds next time.",
            }
        elif avg_rpe and avg_rpe <= 7:
            new_seconds = current_seconds + 5
            return {
                "next_weight_kg": 0,
                "next_reps": new_seconds,
                "progression_type": "increase",
                "rationale": f"Solid effort. Adding 5 seconds to {new_seconds}s.",
            }
        return {
            "next_weight_kg": 0,
            "next_reps": current_seconds,
            "progression_type": "maintain",
            "rationale": "Maintain hold duration. Focus on staying tight.",
        }

    # Rep-based bodyweight
    good_form = form_score and form_score > 80

    if good_form and avg_rpe and avg_rpe <= 7:
        return {
            "next_weight_kg": 0,
            "next_reps": reps + 2,
            "progression_type": "increase",
            "rationale": f"Great form ({form_score:.0f}/100)! Adding 2 reps.",
        }
    elif avg_rpe and avg_rpe <= 7:
        return {
            "next_weight_kg": 0,
            "next_reps": reps + 1,
            "progression_type": "increase",
            "rationale": "Adding 1 rep. Focus on form quality.",
        }

    return {
        "next_weight_kg": 0,
        "next_reps": reps,
        "progression_type": "maintain",
        "rationale": "Maintain reps. Nail the form before adding more.",
    }


def _update_progression(
    db: Session,
    user_id: int,
    exercise_id: int,
    result: dict,
    existing: Optional[ExerciseProgression],
):
    """Update or create the ExerciseProgression record."""
    if not existing:
        existing = ExerciseProgression(
            user_id=user_id,
            exercise_id=exercise_id,
        )
        db.add(existing)

    old_weight = existing.current_weight_kg
    old_reps = existing.current_reps

    existing.current_weight_kg = result.get("next_weight_kg", old_weight)
    existing.current_reps = result.get("next_reps", old_reps)

    if result["progression_type"] == "increase" or result["progression_type"] == "deload":
        existing.weeks_at_current = 0
        existing.last_progression_date = datetime.utcnow()
    else:
        existing.weeks_at_current = (existing.weeks_at_current or 0) + 1

    # Append to history
    history = existing.progression_history or []
    history.append({
        "date": datetime.utcnow().isoformat(),
        "type": result["progression_type"],
        "weight_kg": result.get("next_weight_kg"),
        "reps": result.get("next_reps"),
        "rationale": result.get("rationale"),
    })
    # Keep last 20 entries
    existing.progression_history = history[-20:]

    db.flush()


def _avg(values: list) -> Optional[float]:
    """Safe average of non-None values."""
    valid = [v for v in values if v is not None]
    return sum(valid) / len(valid) if valid else None
