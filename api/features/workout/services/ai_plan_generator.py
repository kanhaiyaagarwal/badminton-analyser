"""LLM-powered workout plan generation.

Falls back to template-based plan_generator.py if LLM call fails.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from ..db_models.workout import (
    Exercise, UserProfile, UserGoal, CoachPreferences, ExerciseSet,
    WorkoutSession, SessionStatus,
)
from . import llm_service
from .plan_generator import generate_template_plan

logger = logging.getLogger(__name__)

PLAN_SYSTEM_PROMPT = """\
You are an expert strength and conditioning coach. Generate a structured weekly \
workout plan in JSON format.

Rules:
- Only use exercises from the provided catalog (match by slug exactly).
- Respect the user's equipment, injuries, fitness level, and schedule.
- Each day should have 3-7 exercises depending on session duration.
- Compound movements first, isolation last.
- Balance push/pull/legs across the week.
- For bodyweight exercises, use "reps" or "30s" for holds.
- For weighted exercises, suggest conservative starting weights based on fitness level.

Output JSON schema:
{
  "name": "Plan Name — N Day",
  "split_type": "ppl" | "upper_lower" | "full_body",
  "days_per_week": <int>,
  "fitness_level": "<level>",
  "coach_reasoning": "<1-2 sentences explaining plan rationale>",
  "days": [
    {
      "day": "mon",
      "label": "Push Day",
      "exercises": [
        {
          "slug": "bench-press",
          "name": "Bench Press",
          "sets": 4,
          "reps": "8-10",
          "equipment": ["barbell", "bench"]
        }
      ],
      "estimated_minutes": 45
    }
  ]
}
"""


async def generate_plan(db: Session, user_id: int) -> Optional[dict]:
    """Generate an AI-powered workout plan.

    Returns plan_data dict on success, None on failure (caller uses template fallback).
    """
    # Gather user context
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    goals = db.query(UserGoal).filter(UserGoal.user_id == user_id).order_by(UserGoal.priority).all()
    prefs = db.query(CoachPreferences).filter(CoachPreferences.user_id == user_id).first()

    if not profile or not prefs:
        logger.debug("Missing profile or prefs for AI plan generation")
        return None

    # Build exercise catalog
    exercises = db.query(Exercise).all()
    catalog = [
        {
            "slug": e.slug,
            "name": e.name,
            "category": e.category,
            "muscle_groups": e.muscle_groups or [],
            "primary_muscle": e.primary_muscle,
            "equipment": e.equipment or ["none"],
            "tracking_mode": e.tracking_mode,
            "difficulty": e.difficulty,
        }
        for e in exercises
    ]

    # Get recent exercise history (last 4 weeks of sets)
    recent_sets = (
        db.query(ExerciseSet)
        .join(WorkoutSession)
        .filter(
            WorkoutSession.user_id == user_id,
            WorkoutSession.status == SessionStatus.COMPLETED,
        )
        .order_by(ExerciseSet.completed_at.desc())
        .limit(100)
        .all()
    )

    history_summary = []
    if recent_sets:
        # Group by exercise_id
        exercise_map = {}
        for s in recent_sets:
            if s.exercise_id not in exercise_map:
                exercise_map[s.exercise_id] = {
                    "exercise_id": s.exercise_id,
                    "sets_completed": 0,
                    "best_reps": 0,
                    "best_weight_kg": 0,
                }
            entry = exercise_map[s.exercise_id]
            entry["sets_completed"] += 1
            entry["best_reps"] = max(entry["best_reps"], s.actual_reps or 0)
            entry["best_weight_kg"] = max(entry["best_weight_kg"], s.weight_kg or 0)

        # Add exercise names
        for eid, entry in exercise_map.items():
            ex = db.query(Exercise).filter(Exercise.id == eid).first()
            if ex:
                entry["name"] = ex.name
                entry["slug"] = ex.slug
                history_summary.append(entry)

    # Build user prompt
    user_prompt = _build_user_prompt(profile, goals, prefs, catalog, history_summary)

    # Call LLM
    result = await llm_service.chat(
        system_prompt=PLAN_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        json_mode=True,
        temperature=0.7,
        max_tokens=3000,
    )

    if not result:
        return None

    # Validate required fields
    if not result.get("days") or not result.get("split_type"):
        logger.warning(f"AI plan missing required fields: {list(result.keys())}")
        return None

    # Validate all exercise slugs exist
    valid_slugs = {e.slug for e in exercises}
    for day in result.get("days", []):
        day["exercises"] = [
            ex for ex in day.get("exercises", [])
            if ex.get("slug") in valid_slugs
        ]

    # Ensure plan has exercises
    total_exercises = sum(len(d.get("exercises", [])) for d in result["days"])
    if total_exercises == 0:
        logger.warning("AI plan had no valid exercises after slug validation")
        return None

    logger.info(
        f"AI plan generated: {result.get('name')}, "
        f"{len(result['days'])} days, {total_exercises} exercises"
    )

    return result


def _build_user_prompt(
    profile: UserProfile,
    goals: list,
    prefs: CoachPreferences,
    catalog: list,
    history: list,
) -> str:
    """Build the user prompt with all context for plan generation."""
    parts = []

    # User profile
    parts.append("## User Profile")
    parts.append(f"- Fitness level: {profile.fitness_level}")
    if profile.age:
        parts.append(f"- Age: {profile.age}")
    if profile.gender:
        parts.append(f"- Gender: {profile.gender}")
    if profile.weight_kg:
        parts.append(f"- Weight: {profile.weight_kg}kg")
    if profile.injuries:
        parts.append(f"- Injuries/limitations: {', '.join(profile.injuries)}")

    # Goals
    if goals:
        parts.append("\n## Goals (in priority order)")
        for g in goals:
            parts.append(f"- {g.goal_type}")

    # Preferences
    parts.append("\n## Schedule & Equipment")
    parts.append(f"- Days per week: {prefs.days_per_week}")
    parts.append(f"- Preferred days: {', '.join(prefs.preferred_days or [])}")
    parts.append(f"- Session duration: {prefs.session_duration_minutes} minutes")
    parts.append(f"- Location: {prefs.train_location}")
    if prefs.available_equipment:
        parts.append(f"- Available equipment: {', '.join(prefs.available_equipment)}")
    else:
        parts.append("- Available equipment: none (bodyweight only)" if prefs.train_location == "home" else "- Available equipment: full gym")

    # Recent history
    if history:
        parts.append("\n## Recent Performance (last 4 weeks)")
        for h in history[:10]:
            parts.append(
                f"- {h.get('name', '?')}: {h['sets_completed']} sets, "
                f"best {h['best_reps']} reps @ {h['best_weight_kg']}kg"
            )

    # Exercise catalog
    parts.append("\n## Available Exercises (use these slugs exactly)")
    for ex in catalog:
        equip = ", ".join(ex["equipment"])
        parts.append(f"- {ex['slug']}: {ex['name']} ({ex['category']}, {ex['primary_muscle']}, equip: {equip})")

    parts.append("\nGenerate the workout plan JSON now.")

    return "\n".join(parts)
