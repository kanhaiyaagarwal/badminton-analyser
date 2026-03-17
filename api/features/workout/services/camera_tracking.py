"""Map exercise slugs to camera analyzers for real-time form tracking.

Uses existing RepCounterAnalyzer subclasses from the challenge feature.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Map exercise slugs to challenge analyzer types.
#
# Analyzers detect reps by tracking joint angles through a state machine:
#   pushup     — elbow angle (horizontal push: down/up)
#   squat_full — knee angle (stand/squat, ~160°→100°)
#   squat_hold — knee angle (hold below threshold)
#   plank      — body alignment (isometric hold)
#
# Exercises are mapped to whichever analyzer matches their primary movement pattern.
# The analyzer doesn't care what exercise name it is — only the joint angles matter.

TRACKABLE_EXERCISES = {
    # === PUSHUP analyzer (elbow angle, horizontal push/extend) ===
    "push-up": "pushup",
    "diamond-push-up": "pushup",
    "wide-grip-push-up": "pushup",
    "burpee": "pushup",           # has a push-up in the movement

    # === SQUAT analyzer (knee angle, stand/squat cycle) ===
    "bodyweight-squat": "squat_full",
    "jump-squat": "squat_full",
    "sumo-squat": "squat_full",
    "front-squat": "squat_full",
    "barbell-squat": "squat_full",
    "hack-squat": "squat_full",
    "smith-machine-squat": "squat_full",
    "bulgarian-split-squat": "squat_full",  # single-leg but same knee pattern
    "lunges": "squat_full",                 # each lunge is a knee bend cycle
    "step-up": "squat_full",                # knee extension per step
    "box-jump": "squat_full",               # squat + jump
    "sissy-squat": "squat_full",
    "glute-bridge": "squat_full",           # hip extension cycle (knee angle changes)

    # === SQUAT HOLD analyzer (isometric knee bend) ===
    "squat-hold": "squat_hold",
    "wall-sit": "squat_hold",

    # === PLANK analyzer (isometric body hold) ===
    "plank": "plank",
    "side-plank": "plank",
    "hollow-body-hold": "plank",

    # === SQUAT analyzer — deadlift/hinge patterns (knee bends at bottom) ===
    "deadlift": "squat_full",
    "sumo-deadlift": "squat_full",
    "kettlebell-swing": "squat_full",       # hip hinge — knee angle changes
    "barbell-thruster": "squat_full",       # squat + press — knee cycle
    "hip-thrust": "squat_full",             # hip extension — knee angle shifts
    "nordic-curl": "squat_full",            # dramatic knee flexion/extension
    "leg-extension": "squat_full",          # seated knee extension
    "cable-pull-through": "squat_full",     # hip hinge with knee bend

    # === SQUAT analyzer — core exercises (hip/knee angle cycles) ===
    "crunch": "squat_full",
    "russian-twist": "squat_full",
    "bicycle-crunch": "squat_full",
    "hanging-leg-raise": "squat_full",      # hip angle cycle (legs up/down)
    "v-up": "squat_full",
    "dead-bug": "squat_full",
    "decline-sit-up": "squat_full",
    "cable-crunch": "squat_full",
    "ab-wheel-rollout": "squat_full",       # body extension/contraction
    "hyperextension": "squat_full",         # hip extension cycle
    "superman": "squat_full",               # back extension — hip angle

    # === SQUAT analyzer — glute/accessory (hip extension visible) ===
    "glute-bridge": "squat_full",
    "donkey-kick": "squat_full",
    "fire-hydrant": "squat_full",
    "calf-raise": "squat_full",
    "single-leg-calf-raise": "squat_full",

    # === PUSHUP analyzer — vertical push/pull (elbow angle cycle) ===
    "dips": "pushup",                       # vertical elbow bend/extend
    "tricep-dip-bench": "pushup",           # bench dip — same pattern
    "pull-up": "pushup",                    # elbow flex/extend (chin-up motion)
    "chin-up": "pushup",

    # === PUSHUP analyzer — pressing from horizontal (lying down) ===
    "bench-press": "pushup",                # lying elbow extension
    "incline-bench-press": "pushup",
    "decline-bench-press": "pushup",
    "incline-dumbbell-press": "pushup",
    "close-grip-bench-press": "pushup",
    "skull-crusher": "pushup",              # lying elbow extension
    "dumbbell-fly": "pushup",              # lying arm arc
    "incline-dumbbell-fly": "pushup",

    # === HOLD analyzers ===
    "hip-flexor-stretch": "plank",          # held position
    "pigeon-pose": "plank",
    "childs-pose": "plank",

    # === ARM REP analyzer (standing elbow/shoulder angle cycles) ===
    # Elbow flexion pattern (curls, tricep extensions)
    "bicep-curl": "arm_rep",
    "hammer-curl": "arm_rep",
    "preacher-curl": "arm_rep",
    "incline-dumbbell-curl": "arm_rep",
    "concentration-curl": "arm_rep",
    "cable-curl": "arm_rep",
    "reverse-curl": "arm_rep",
    "overhead-tricep-extension": "arm_rep",
    "tricep-pushdown": "arm_rep",
    "dumbbell-tricep-kickback": "arm_rep",
    # Shoulder raise pattern (lateral/front raises, reverse fly)
    "lateral-raise": "arm_rep",
    "cable-lateral-raise": "arm_rep",
    "front-raise": "arm_rep",
    "reverse-fly": "arm_rep",
    # Overhead press pattern
    "shoulder-press": "arm_rep",
    "arnold-press": "arm_rep",
    # Shrug pattern
    "barbell-shrug": "arm_rep",
    "dumbbell-shrug": "arm_rep",
    # Row pattern
    "upright-row": "arm_rep",
    "barbell-row": "arm_rep",
    "single-arm-dumbbell-row": "arm_rep",
    "t-bar-row": "arm_rep",
    "seated-cable-row": "arm_rep",
    "chest-supported-row": "arm_rep",
    "pendlay-row": "arm_rep",
    # Hinge pattern (hip angle with standing position)
    "good-morning": "arm_rep",
    "romanian-deadlift": "arm_rep",
    "stiff-leg-deadlift": "arm_rep",
    "face-pull": "arm_rep",
    "glute-kickback": "arm_rep",

    # === NOT TRACKABLE — documented reasons ===
    # Machine (obscures body): pec-deck, cable-fly, cable-crossover,
    #   lat-pulldown, seated-row-machine, chest-press-machine,
    #   adductor-machine, abductor-machine, leg-curl, seated-leg-curl,
    #   seated-calf-raise, donkey-calf-raise
    # Too fast/dynamic: mountain-climber, jump-rope, high-knees, jumping-jacks,
    #   battle-ropes, bear-crawl
    # Walking/no reps: farmers-walk, sled-push
    # Olympic (too complex): power-clean, dumbbell-snatch, turkish-get-up
    # Flexibility (passive): foam-roll, yoga-flow, zumba-dance, cat-cow-stretch,
    #   worlds-greatest-stretch, band-shoulder-dislocates, ankle-mobility-drill
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
        elif analyzer_type == "arm_rep":
            from ...challenges.services.arm_curl_analyzer import ArmRepAnalyzer
            return ArmRepAnalyzer(exercise_slug=exercise_slug, config=config)
        else:
            logger.warning(f"No analyzer for type: {analyzer_type}")
            return None
    except ImportError as e:
        logger.error(f"Failed to import analyzer for {analyzer_type}: {e}")
        return None
