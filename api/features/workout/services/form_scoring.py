"""Aggregate per-frame form quality into a 0-100 score.

Reads from the RepCounterAnalyzer frame_timeline format:
  { t, lm, angle, state, fb, reps, hold }
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def compute_form_score(frame_timeline: List[Dict]) -> int:
    """Compute an aggregate form score from the analyzer's frame timeline.

    Timeline fields (from rep_counter.py):
      - fb: str — form feedback text ("Good form", "Go deeper", etc.)
      - state: str/bool — exercise state (e.g. "up"/"down" for reps, True/False for plank)

    Scoring:
      - "Good form" frames = good
      - Any other non-empty feedback = bad
      - Empty / no feedback = neutral
      - Active frames (state is truthy) weighted 2x
    """
    if not frame_timeline:
        return 0

    good_points = 0
    total_points = 0

    for frame in frame_timeline:
        fb = frame.get("fb", "")
        state = frame.get("state")

        # Weight active frames 2x more than rest frames
        is_active = bool(state)
        weight = 2 if is_active else 1

        if not fb or fb == "Good form" or fb == "Good form!":
            good_points += weight
            total_points += weight
        else:
            # Non-good feedback means bad form on this frame
            total_points += weight

    if total_points == 0:
        return 0

    score = round((good_points / total_points) * 100)
    return max(0, min(100, score))


def extract_form_feedback(frame_timeline: List[Dict]) -> List[str]:
    """Extract the most common form corrections from the timeline."""
    if not frame_timeline:
        return []

    feedback_counts: Dict[str, int] = {}
    for frame in frame_timeline:
        fb = frame.get("fb", "")
        if fb and fb not in ("Good form", "Good form!", ""):
            feedback_counts[fb] = feedback_counts.get(fb, 0) + 1

    # Return top 3 most common corrections
    sorted_feedback = sorted(feedback_counts.items(), key=lambda x: -x[1])
    return [fb for fb, _ in sorted_feedback[:3]]
