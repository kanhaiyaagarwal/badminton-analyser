"""Template-based workout plan generation (no LLM)."""

from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Split Templates
# ---------------------------------------------------------------------------

SPLIT_TEMPLATES = {
    "ppl": {
        "name": "Push Pull Legs",
        "min_days": 3,
        "max_days": 6,
        "day_labels": ["Push", "Pull", "Legs", "Push", "Pull", "Legs"],
        "muscle_map": {
            "Push": ["chest", "shoulders", "triceps"],
            "Pull": ["back", "biceps", "rear delts"],
            "Legs": ["quads", "hamstrings", "glutes", "calves"],
        },
    },
    "upper_lower": {
        "name": "Upper / Lower",
        "min_days": 2,
        "max_days": 4,
        "day_labels": ["Upper", "Lower", "Upper", "Lower"],
        "muscle_map": {
            "Upper": ["chest", "back", "shoulders", "biceps", "triceps"],
            "Lower": ["quads", "hamstrings", "glutes", "calves", "core"],
        },
    },
    "full_body": {
        "name": "Full Body",
        "min_days": 2,
        "max_days": 3,
        "day_labels": ["Full Body A", "Full Body B", "Full Body C"],
        "muscle_map": {
            "Full Body A": ["chest", "back", "quads", "shoulders", "core"],
            "Full Body B": ["chest", "hamstrings", "back", "biceps", "triceps"],
            "Full Body C": ["quads", "glutes", "shoulders", "back", "core"],
        },
    },
}

# Volume schemes by experience level
VOLUME_SCHEMES = {
    "beginner": {"sets": 3, "reps": "10-12", "rest_sec": 90},
    "intermediate": {"sets": 4, "reps": "8-10", "rest_sec": 75},
    "advanced": {"sets": 5, "reps": "6-8", "rest_sec": 60},
}

# Bodyweight substitutions when no gym equipment
BODYWEIGHT_SUBS = {
    "bench-press": "push-up",
    "shoulder-press": "push-up",  # pike push-up variant
    "barbell-squat": "bodyweight-squat",
    "leg-press": "bodyweight-squat",
    "barbell-row": "push-up",  # inverted row approximation
    "cable-fly": "push-up",
    "tricep-pushdown": "push-up",  # diamond push-up variant
    "leg-curl": "bodyweight-squat",
}


def _pick_split(days_per_week: int) -> str:
    """Choose best split for the given training frequency."""
    if days_per_week >= 5:
        return "ppl"
    elif days_per_week >= 4:
        return "upper_lower"
    else:
        return "full_body"


def _exercises_for_muscles(
    target_muscles: List[str],
    exercises: List[dict],
    available_equipment: Optional[List[str]],
    is_home: bool,
    max_exercises: int = 5,
) -> List[dict]:
    """Select exercises that hit the target muscles, respecting equipment constraints."""
    selected = []
    used_slugs = set()

    for muscle in target_muscles:
        for ex in exercises:
            if ex["slug"] in used_slugs:
                continue
            if muscle not in ex.get("muscle_groups", []):
                continue

            # Equipment check for home workouts
            if is_home and ex.get("equipment", ["none"]) != ["none"]:
                # Check if user has this equipment at home
                ex_equip = set(ex.get("equipment", []))
                user_equip = set(available_equipment or [])
                if ex_equip - {"none"} and not ex_equip.issubset(user_equip):
                    continue

            selected.append(ex)
            used_slugs.add(ex["slug"])

            if len(selected) >= max_exercises:
                return selected

    return selected


def _estimate_duration(num_exercises: int, sets: int, rest_sec: int) -> int:
    """Rough estimate of workout duration in minutes."""
    set_time_sec = 40 + rest_sec  # ~40s of work per set + rest
    total_sec = num_exercises * sets * set_time_sec
    return max(15, round(total_sec / 60))


def generate_template_plan(
    preferred_days: List[str],
    session_duration_minutes: int,
    fitness_level: str,
    train_location: str,
    available_equipment: Optional[List[str]],
    exercises: List[dict],
) -> dict:
    """
    Generate a template-based workout plan.

    Returns a plan_data dict with day assignments and exercise selections.
    """
    days_per_week = len(preferred_days)
    split_type = _pick_split(days_per_week)
    template = SPLIT_TEMPLATES[split_type]
    volume = VOLUME_SCHEMES.get(fitness_level, VOLUME_SCHEMES["beginner"])
    is_home = train_location == "home"

    # Max exercises per session based on duration
    if session_duration_minutes <= 20:
        max_per_session = 3
    elif session_duration_minutes <= 30:
        max_per_session = 4
    elif session_duration_minutes <= 45:
        max_per_session = 5
    else:
        max_per_session = 7

    # Build day assignments
    days = []
    day_labels = template["day_labels"]
    for i, day_name in enumerate(preferred_days):
        label = day_labels[i % len(day_labels)]
        target_muscles = template["muscle_map"].get(label, [])

        # For variants like "Full Body A", "Full Body B" — look up without suffix
        if not target_muscles:
            for key in template["muscle_map"]:
                if label.startswith(key.split()[0]):
                    target_muscles = template["muscle_map"][key]
                    break

        day_exercises = _exercises_for_muscles(
            target_muscles, exercises, available_equipment, is_home, max_per_session
        )

        day_data = {
            "day": day_name,
            "label": label,
            "exercises": [
                {
                    "slug": ex["slug"],
                    "name": ex["name"],
                    "sets": volume["sets"],
                    "reps": volume["reps"] if ex.get("tracking_mode") == "reps" else (
                        "30s" if ex.get("tracking_mode") == "hold" else "30s"
                    ),
                    "equipment": ex.get("equipment", ["none"]),
                }
                for ex in day_exercises
            ],
            "estimated_minutes": _estimate_duration(
                len(day_exercises), volume["sets"], volume["rest_sec"]
            ),
        }
        days.append(day_data)

    plan_name = f"{template['name']} — {days_per_week} Day"

    return {
        "name": plan_name,
        "split_type": split_type,
        "days_per_week": days_per_week,
        "fitness_level": fitness_level,
        "volume": volume,
        "days": days,
    }
