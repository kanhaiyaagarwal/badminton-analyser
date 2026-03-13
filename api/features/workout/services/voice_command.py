"""Parse voice commands into workout session actions.

Maps recognized speech text to (action_name, params) tuples that can be
dispatched to SessionAgent.process_action().
"""

import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Static command mappings
STATIC_COMMANDS = {
    "done": ("complete_set", {}),
    "complete": ("complete_set", {}),
    "finished": ("complete_set", {}),
    "skip": ("skip_exercise", {}),
    "skip exercise": ("skip_exercise", {}),
    "skip rest": ("skip_rest", {}),
    "next": ("skip_rest", {}),
    "pause": ("pause", {}),
    "stop": ("end_workout", {}),
    "end workout": ("end_workout", {}),
    "end": ("end_workout", {}),
}

# Number word mapping
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}

# Patterns for parameterized commands
# e.g., "12 reps", "twelve reps"
REP_PATTERN = re.compile(r'^(\d+|' + '|'.join(NUMBER_WORDS.keys()) + r')\s+reps?$', re.I)

# e.g., "12 at 50", "10 reps at 60 kg"
REPS_AT_WEIGHT_PATTERN = re.compile(
    r'^(\d+)\s+(?:reps?\s+)?at\s+(\d+(?:\.\d+)?)\s*(?:kg|kilos?)?$', re.I
)

# e.g., "RPE 7", "effort 8"
RPE_PATTERN = re.compile(r'^(?:rpe|effort)\s+(\d+)$', re.I)


def _parse_number(text: str) -> Optional[int]:
    """Parse a number from text (digit or word)."""
    text = text.strip().lower()
    if text.isdigit():
        return int(text)
    return NUMBER_WORDS.get(text)


def parse_voice_command(
    text: str,
    context: dict = None,
) -> Optional[Tuple[str, dict]]:
    """Parse recognized text into (action, params).

    Args:
        text: Recognized speech text
        context: Current session context with exercise_id, set_number, etc.

    Returns:
        (action_name, params) tuple or None if not understood.
    """
    if not text:
        return None

    text = text.strip().lower()
    context = context or {}

    # Check static commands first
    if text in STATIC_COMMANDS:
        action, params = STATIC_COMMANDS[text]
        # Merge context into params for skip_rest and complete_set
        if action in ("complete_set", "skip_rest", "skip_exercise"):
            params = {**params, **_context_params(context)}
        return action, params

    # Check rep count pattern: "12 reps"
    match = REP_PATTERN.match(text)
    if match:
        reps = _parse_number(match.group(1))
        if reps is not None:
            params = {"reps": reps, **_context_params(context)}
            return "complete_set", params

    # Check reps at weight pattern: "10 at 60"
    match = REPS_AT_WEIGHT_PATTERN.match(text)
    if match:
        reps = int(match.group(1))
        weight = float(match.group(2))
        params = {"reps": reps, "weight_kg": weight, **_context_params(context)}
        return "complete_set", params

    # Check RPE: "RPE 7"
    match = RPE_PATTERN.match(text)
    if match:
        rpe_val = int(match.group(1))
        if 1 <= rpe_val <= 10:
            # RPE alone doesn't complete a set; store for later
            return "set_rpe", {"rpe": rpe_val}

    # Fuzzy: if text contains "done" or "finished" somewhere
    if "done" in text or "finished" in text:
        params = _context_params(context)
        return "complete_set", params

    if "skip" in text and "rest" in text:
        return "skip_rest", _context_params(context)

    logger.debug(f"Voice command not understood: '{text}'")
    return None


def _context_params(context: dict) -> dict:
    """Extract exercise_id and set_number from context."""
    params = {}
    if context.get("exercise_id"):
        params["exercise_id"] = context["exercise_id"]
    if context.get("set_number"):
        params["set_number"] = context["set_number"]
    return params
