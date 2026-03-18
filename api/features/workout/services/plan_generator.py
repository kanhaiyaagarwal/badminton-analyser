"""Template-based workout plan generation (no LLM).

Exercise prioritization:
1. Compound exercises first (bench press before cable fly)
2. Match user's difficulty level (beginner gets beginner exercises)
3. Respect equipment constraints (home = bodyweight/dumbbells only)
4. Variety — don't repeat the same exercise across days
"""

import random
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Split Templates
# ---------------------------------------------------------------------------

SPLIT_TEMPLATES = {
    "ppl": {
        "name": "Push Pull Legs",
        "min_days": 3,
        "max_days": 6,
        "day_labels": [
            "Push — Chest & Shoulders",
            "Pull — Back & Biceps",
            "Legs — Quads & Glutes",
            "Push — Shoulders & Triceps",
            "Pull — Back & Rear Delts",
            "Legs — Hamstrings & Calves",
        ],
        "muscle_map": {
            "Push — Chest & Shoulders": ["chest", "shoulders", "triceps"],
            "Push — Shoulders & Triceps": ["shoulders", "triceps", "chest"],
            "Pull — Back & Biceps": ["back", "biceps", "rear delts"],
            "Pull — Back & Rear Delts": ["back", "rear delts", "biceps"],
            "Legs — Quads & Glutes": ["quads", "glutes", "hamstrings", "calves"],
            "Legs — Hamstrings & Calves": ["hamstrings", "calves", "glutes", "quads"],
        },
    },
    "upper_lower": {
        "name": "Upper / Lower",
        "min_days": 2,
        "max_days": 4,
        "day_labels": [
            "Upper — Chest & Back",
            "Lower — Quads & Glutes",
            "Upper — Shoulders & Arms",
            "Lower — Hamstrings & Core",
        ],
        "muscle_map": {
            "Upper — Chest & Back": ["chest", "back", "triceps"],
            "Upper — Shoulders & Arms": ["shoulders", "biceps", "triceps"],
            "Lower — Quads & Glutes": ["quads", "glutes", "calves"],
            "Lower — Hamstrings & Core": ["hamstrings", "core", "glutes"],
        },
    },
    "full_body": {
        "name": "Full Body",
        "min_days": 2,
        "max_days": 3,
        "day_labels": ["Full Body — Push Focus", "Full Body — Pull Focus", "Full Body — Legs Focus"],
        "muscle_map": {
            "Full Body — Push Focus": ["chest", "shoulders", "triceps", "quads", "core"],
            "Full Body — Pull Focus": ["back", "biceps", "hamstrings", "rear delts", "core"],
            "Full Body — Legs Focus": ["quads", "glutes", "calves", "shoulders", "back"],
        },
    },
}

# Volume schemes by experience level (sets adjusted dynamically by session duration)
VOLUME_SCHEMES = {
    "beginner": {"base_sets": 3, "reps": "10-12", "rest_sec": 90},
    "intermediate": {"base_sets": 3, "reps": "8-10", "rest_sec": 75},
    "advanced": {"base_sets": 4, "reps": "6-8", "rest_sec": 60},
}

# Category priority: compounds first, then bodyweight, then isolation, then cardio
CATEGORY_PRIORITY = {
    "compound": 0,
    "bodyweight": 1,
    "isolation": 2,
    "cardio": 3,
}

# Difficulty ranking for matching user level
DIFFICULTY_RANK = {
    "beginner": 0,
    "intermediate": 1,
    "advanced": 2,
}


# Similarity groups — exercises within a group are too similar to appear together
# When one is picked, others in the same group are excluded for that day
SIMILARITY_GROUPS = [
    {"deadlift", "romanian-deadlift", "sumo-deadlift", "stiff-leg-deadlift"},
    {"barbell-squat", "front-squat", "hack-squat", "smith-machine-squat"},
    {"bench-press", "close-grip-bench-press", "decline-bench-press"},
    {"incline-bench-press", "incline-dumbbell-press"},
    {"dumbbell-fly", "incline-dumbbell-fly"},
    {"bicep-curl", "hammer-curl", "preacher-curl", "incline-dumbbell-curl", "concentration-curl", "cable-curl", "reverse-curl"},
    {"overhead-tricep-extension", "tricep-pushdown", "dumbbell-tricep-kickback", "skull-crusher"},
    {"lateral-raise", "cable-lateral-raise"},
    {"barbell-row", "pendlay-row", "t-bar-row"},
    {"single-arm-dumbbell-row", "chest-supported-row", "seated-cable-row"},
    {"shoulder-press", "arnold-press"},
    {"barbell-shrug", "dumbbell-shrug"},
    {"crunch", "decline-sit-up", "cable-crunch"},
    {"plank", "side-plank"},
    {"bodyweight-squat", "jump-squat", "sumo-squat", "sissy-squat"},
    {"lunges", "bulgarian-split-squat", "step-up"},
    {"calf-raise", "single-leg-calf-raise"},
    {"push-up", "diamond-push-up", "wide-grip-push-up"},
    {"pull-up", "chin-up"},
    {"glute-bridge", "hip-thrust"},
    {"good-morning", "hyperextension"},
]

# Build a slug → group index lookup
_SLUG_TO_GROUP = {}
for _i, _group in enumerate(SIMILARITY_GROUPS):
    for _slug in _group:
        _SLUG_TO_GROUP[_slug] = _i


def _pick_split(days_per_week: int) -> str:
    """Choose best split for the given training frequency."""
    if days_per_week >= 5:
        return "ppl"
    elif days_per_week >= 4:
        return "upper_lower"
    else:
        return "full_body"


# Muscles where we want isolation exercises (not compounds that happen to hit them)
_ISOLATION_PREFERRED = {"biceps", "triceps", "calves", "core", "rear delts"}


def _score_exercise(ex: dict, target_muscle: str, user_level: str) -> float:
    """Score an exercise for selection priority. Lower = better.

    Priorities:
    1. Primary muscle match (exact primary_muscle match scores best)
    2. For small muscles (biceps, triceps, etc.): prefer isolation targeting them
       For large muscles (chest, back, etc.): prefer compounds
    3. Difficulty matches user level (exact match best, ±1 ok, ±2 worst)
    4. Small random factor for variety across regenerations
    """
    score = 0.0

    # Primary muscle match: 0 if primary matches, 5 if only in muscle_groups
    is_primary = ex.get("primary_muscle") == target_muscle
    if is_primary:
        score += 0
    else:
        score += 5

    # Category priority — but for isolation-preferred muscles, flip the preference
    if target_muscle in _ISOLATION_PREFERRED and is_primary:
        # For biceps/triceps/etc: isolation with primary match is best
        cat_scores = {"isolation": 0, "bodyweight": 1, "compound": 2, "cardio": 3}
    else:
        cat_scores = CATEGORY_PRIORITY
    score += cat_scores.get(ex.get("category", "cardio"), 3) * 10

    # Difficulty match
    user_rank = DIFFICULTY_RANK.get(user_level, 0)
    ex_rank = DIFFICULTY_RANK.get(ex.get("difficulty", "beginner"), 0)
    diff_gap = abs(user_rank - ex_rank)
    if diff_gap == 0:
        score += 0
    elif diff_gap == 1:
        score += 3
    else:
        score += 8  # advanced exercise for beginner or vice versa

    # Skip flexibility/recovery exercises for main workout slots
    if ex.get("tracking_mode") == "hold" and ex.get("category") == "cardio":
        score += 50

    # Small random factor for variety (different plans each time)
    score += random.random() * 2

    return score


def _equipment_available(ex: dict, available_equipment: Optional[List[str]], is_home: bool) -> bool:
    """Check if user has the equipment for this exercise."""
    ex_equip = set(ex.get("equipment", ["none"]))
    if ex_equip == {"none"}:
        return True  # bodyweight — always available
    if not is_home:
        return True  # gym — assume all equipment available
    # Home: must have the equipment
    user_equip = set(available_equipment or [])
    return ex_equip.issubset(user_equip | {"none"})


def _exercises_for_muscles(
    target_muscles: List[str],
    exercises: List[dict],
    available_equipment: Optional[List[str]],
    is_home: bool,
    user_level: str,
    max_exercises: int = 5,
    used_slugs: set = None,
) -> List[dict]:
    """Select exercises that hit the target muscles, with smart prioritization.

    For each target muscle:
    1. Filter to exercises that hit this muscle AND user has equipment for
    2. Score and sort by priority (compound first, difficulty match, variety)
    3. Pick the best available exercise not already used
    """
    if used_slugs is None:
        used_slugs = set()
    selected = []
    selected_slugs = set()
    used_groups = set()  # similarity groups already picked for this day

    for muscle in target_muscles:
        if len(selected) >= max_exercises:
            break

        # Find all candidate exercises for this muscle
        candidates = []
        for ex in exercises:
            slug = ex["slug"]
            if slug in used_slugs or slug in selected_slugs:
                continue
            if muscle not in ex.get("muscle_groups", []):
                continue
            if not _equipment_available(ex, available_equipment, is_home):
                continue
            # Skip if a similar exercise is already selected for this day
            group_id = _SLUG_TO_GROUP.get(slug)
            if group_id is not None and group_id in used_groups:
                continue
            candidates.append(ex)

        if not candidates:
            continue

        # Score and sort
        candidates.sort(key=lambda ex: _score_exercise(ex, muscle, user_level))

        # Pick the best one
        best = candidates[0]
        selected.append(best)
        selected_slugs.add(best["slug"])
        group_id = _SLUG_TO_GROUP.get(best["slug"])
        if group_id is not None:
            used_groups.add(group_id)

    # If we have room, add more exercises for under-represented muscles
    if len(selected) < max_exercises:
        all_candidates = []
        for ex in exercises:
            slug = ex["slug"]
            if slug in used_slugs or slug in selected_slugs:
                continue
            if not any(m in ex.get("muscle_groups", []) for m in target_muscles):
                continue
            if not _equipment_available(ex, available_equipment, is_home):
                continue
            # Skip similar exercises
            group_id = _SLUG_TO_GROUP.get(slug)
            if group_id is not None and group_id in used_groups:
                continue
            all_candidates.append(ex)

        # Sort remaining by how well they complement what we already have
        all_candidates.sort(key=lambda ex: _score_exercise(ex, target_muscles[0], user_level))

        for ex in all_candidates:
            if len(selected) >= max_exercises:
                break
            selected.append(ex)
            selected_slugs.add(ex["slug"])
            group_id = _SLUG_TO_GROUP.get(ex["slug"])
            if group_id is not None:
                used_groups.add(group_id)

    return selected


def _plan_for_duration(session_minutes: int, base_sets: int) -> tuple:
    """Return (max_exercises, sets_per_exercise) for a given session duration.

    Strategy: shorter sessions → fewer exercises with same sets.
    Longer sessions → more exercises, bump to 4 sets when time allows.
    ~7 min per exercise @ 3 sets, ~9 min per exercise @ 4 sets.
    """
    if session_minutes <= 15:
        return 2, min(base_sets, 3)
    elif session_minutes <= 20:
        return 3, 3
    elif session_minutes <= 25:
        return 3, min(base_sets, 3)
    elif session_minutes <= 30:
        return 4, 3
    elif session_minutes <= 40:
        return 4, min(base_sets + 1, 4)
    elif session_minutes <= 45:
        return 5, 3
    elif session_minutes <= 50:
        return 5, min(base_sets + 1, 4)
    elif session_minutes <= 55:
        return 6, 3
    else:
        return 6, min(base_sets + 1, 4)


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

    # Realistic exercise/set planning based on session duration
    # ~7 min per exercise @ 3 sets, ~9 min per exercise @ 4 sets
    # (45s work + rest per set + transition time)
    max_per_session, sets_per_exercise = _plan_for_duration(
        session_duration_minutes, volume["base_sets"]
    )
    rest_sec = volume["rest_sec"]

    # Track used slugs across days for variety (especially for repeated day types like PPL)
    global_used = set()

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
            target_muscles, exercises, available_equipment, is_home,
            fitness_level, max_per_session, used_slugs=global_used,
        )

        # Add selected slugs to global used (for variety on next day with same muscle group)
        for ex in day_exercises:
            global_used.add(ex["slug"])

        day_data = {
            "day": day_name,
            "label": label,
            "exercises": [
                {
                    "slug": ex["slug"],
                    "name": ex["name"],
                    "sets": sets_per_exercise,
                    "reps": volume["reps"] if ex.get("tracking_mode") == "reps" else (
                        "30s" if ex.get("tracking_mode") == "hold" else "30s"
                    ),
                    "equipment": ex.get("equipment", ["none"]),
                }
                for ex in day_exercises
            ],
            "estimated_minutes": _estimate_duration(
                len(day_exercises), sets_per_exercise, rest_sec
            ),
        }
        days.append(day_data)

    plan_name = f"{template['name']} — {days_per_week} Day"

    return {
        "name": plan_name,
        "split_type": split_type,
        "days_per_week": days_per_week,
        "fitness_level": fitness_level,
        "volume": {**volume, "sets": sets_per_exercise},
        "days": days,
    }
