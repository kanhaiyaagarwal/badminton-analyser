"""Map exercise slugs to camera analyzers for real-time form tracking.

Uses existing RepCounterAnalyzer subclasses from the challenge feature.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Map exercise slugs to challenge analyzer types
TRACKABLE_EXERCISES = {
    "push-up": "pushup",
    "bodyweight-squat": "squat_full",
    "plank": "plank",
    "squat-hold": "squat_hold",
    "jump-squat": "squat_full",
    "burpee": "pushup",
    # Not yet supported — analyzer doesn't exist
    "lunges": None,
    "mountain-climber": None,
}


def is_trackable(exercise_slug: str) -> bool:
    """Check if an exercise supports camera-based form tracking."""
    return TRACKABLE_EXERCISES.get(exercise_slug) is not None


def get_analyzer_type(exercise_slug: str) -> Optional[str]:
    """Get the challenge analyzer type for an exercise slug."""
    return TRACKABLE_EXERCISES.get(exercise_slug)


def create_workout_analyzer(exercise_slug: str, config: dict = None):
    """Create a RepCounterAnalyzer instance for a workout exercise.

    Returns None if the exercise is not trackable.
    """
    analyzer_type = get_analyzer_type(exercise_slug)
    if not analyzer_type:
        return None

    try:
        if analyzer_type == "pushup":
            from ...challenges.services.pushup_analyzer import PushupAnalyzer
            return PushupAnalyzer(config=config)
        elif analyzer_type in ("squat_full", "squat_half"):
            from ...challenges.services.squat_analyzer import SquatAnalyzer
            return SquatAnalyzer(challenge_type=analyzer_type, config=config)
        elif analyzer_type == "squat_hold":
            from ...challenges.services.squat_analyzer import SquatAnalyzer
            return SquatAnalyzer(challenge_type="squat_hold", config=config)
        elif analyzer_type == "plank":
            from ...challenges.services.plank_analyzer import PlankAnalyzer
            return PlankAnalyzer(config=config)
        else:
            logger.warning(f"No analyzer for type: {analyzer_type}")
            return None
    except ImportError as e:
        logger.error(f"Failed to import analyzer for {analyzer_type}: {e}")
        return None
