"""Standing arm rep counter — counts reps via elbow angle for curls, raises, presses, rows, shrugs.

Works for any standing exercise where the shoulder-elbow-wrist angle cycles between
a "relaxed" (arm extended) and "contracted" (arm flexed/raised) state.

Covers: bicep curl, hammer curl, lateral raise, front raise, shoulder press,
        upright row, overhead tricep extension, tricep kickback, shrugs, reverse fly, etc.
"""

import logging
from typing import Dict

from ....core.streaming.pose_detector import PoseDetector
from .rep_counter import RepCounterAnalyzer

logger = logging.getLogger(__name__)

L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24

# Movement patterns determine which angle/metric to track
PATTERNS = {
    # Elbow flexion (arm bends at elbow): curls, tricep extensions
    "elbow_flex": {
        "description": "Elbow angle (shoulder-elbow-wrist)",
        "relaxed_angle": 155,   # arm nearly straight
        "contracted_angle": 60, # arm bent
    },
    # Shoulder abduction (arm raises to side): lateral raise, front raise
    "shoulder_raise": {
        "description": "Arm height relative to shoulder",
        "relaxed_angle": 155,   # arms at sides
        "contracted_angle": 80, # arms raised to shoulder height
    },
    # Overhead press (arms go overhead)
    "overhead_press": {
        "description": "Elbow angle for overhead press",
        "relaxed_angle": 90,    # elbows at 90 at shoulders
        "contracted_angle": 160, # arms extended overhead
    },
    # Shrug (shoulder elevation — small movement)
    "shrug": {
        "description": "Shoulder height relative to ears",
        "relaxed_angle": 155,
        "contracted_angle": 130,  # smaller range — shrugs are subtle
    },
    # Row (elbow behind torso)
    "row": {
        "description": "Elbow angle for rowing motion",
        "relaxed_angle": 155,
        "contracted_angle": 70,
    },
}

# Map exercise slugs to movement patterns
EXERCISE_PATTERNS = {
    # Elbow flexion
    "bicep-curl": "elbow_flex",
    "hammer-curl": "elbow_flex",
    "preacher-curl": "elbow_flex",
    "incline-dumbbell-curl": "elbow_flex",
    "concentration-curl": "elbow_flex",
    "cable-curl": "elbow_flex",
    "reverse-curl": "elbow_flex",
    "overhead-tricep-extension": "elbow_flex",
    "tricep-pushdown": "elbow_flex",
    "dumbbell-tricep-kickback": "elbow_flex",
    # Shoulder raise
    "lateral-raise": "shoulder_raise",
    "cable-lateral-raise": "shoulder_raise",
    "front-raise": "shoulder_raise",
    "reverse-fly": "shoulder_raise",
    # Overhead press
    "shoulder-press": "overhead_press",
    "arnold-press": "overhead_press",
    # Shrug
    "barbell-shrug": "shrug",
    "dumbbell-shrug": "shrug",
    # Row
    "upright-row": "row",
    "barbell-row": "row",
    "single-arm-dumbbell-row": "row",
    "t-bar-row": "row",
    "seated-cable-row": "row",
    "chest-supported-row": "row",
    "pendlay-row": "row",
}


class ArmRepAnalyzer(RepCounterAnalyzer):
    """
    Counts reps for standing arm exercises using elbow/shoulder angles.

    State machine: RELAXED -> CONTRACTED -> RELAXED counts as 1 rep.

    Adapts thresholds based on exercise pattern (curl vs raise vs press vs row).
    """

    def __init__(self, exercise_slug: str = "bicep-curl", config=None):
        super().__init__(challenge_type="arm_rep", config=config)
        self.exercise_slug = exercise_slug
        cfg = config or {}

        # Get pattern for this exercise
        pattern_name = EXERCISE_PATTERNS.get(exercise_slug, "elbow_flex")
        pattern = PATTERNS[pattern_name]
        self.pattern_name = pattern_name

        # Override pattern thresholds with config if provided
        self.relaxed_angle = cfg.get("relaxed_angle", pattern["relaxed_angle"])
        self.contracted_angle = cfg.get("contracted_angle", pattern["contracted_angle"])

        # For overhead press, the cycle is inverted: start low (90°), go high (160°)
        self.inverted = pattern_name == "overhead_press"

        self._state = "relaxed"
        self._ready = False
        self._ready_since = 0.0
        self._stood_still_frames = 0
        self._total_active_frames = 0
        self._form_good_frames = 0

    def _get_elbow_angle(self, landmarks):
        """Average shoulder-elbow-wrist angle (both arms)."""
        left = PoseDetector.angle_between(
            (landmarks[L_SHOULDER]["nx"], landmarks[L_SHOULDER]["ny"]),
            (landmarks[L_ELBOW]["nx"], landmarks[L_ELBOW]["ny"]),
            (landmarks[L_WRIST]["nx"], landmarks[L_WRIST]["ny"]),
        )
        right = PoseDetector.angle_between(
            (landmarks[R_SHOULDER]["nx"], landmarks[R_SHOULDER]["ny"]),
            (landmarks[R_ELBOW]["nx"], landmarks[R_ELBOW]["ny"]),
            (landmarks[R_WRIST]["nx"], landmarks[R_WRIST]["ny"]),
        )
        return (left + right) / 2

    def _get_arm_height(self, landmarks):
        """Wrist height relative to shoulder (for raises). Lower = arms raised."""
        shoulder_y = (landmarks[L_SHOULDER]["ny"] + landmarks[R_SHOULDER]["ny"]) / 2
        wrist_y = (landmarks[L_WRIST]["ny"] + landmarks[R_WRIST]["ny"]) / 2
        # Return as pseudo-angle: arms at sides ≈ 180, arms raised ≈ 90
        delta = wrist_y - shoulder_y  # positive = wrists below shoulders
        # Map to 0-180 range: 0.3 delta = ~180 (relaxed), 0.0 delta = ~90 (raised)
        return max(60, min(180, 90 + delta * 300))

    def _get_shoulder_height(self, landmarks):
        """Shoulder elevation for shrugs. Shoulder-to-hip distance."""
        shoulder_y = (landmarks[L_SHOULDER]["ny"] + landmarks[R_SHOULDER]["ny"]) / 2
        hip_y = (landmarks[L_HIP]["ny"] + landmarks[R_HIP]["ny"]) / 2
        gap = hip_y - shoulder_y  # larger = shoulders lower (relaxed)
        return max(100, min(180, 100 + gap * 400))

    def _get_angle(self, landmarks):
        """Get the appropriate angle metric based on pattern."""
        if self.pattern_name == "shoulder_raise":
            return self._get_arm_height(landmarks)
        elif self.pattern_name == "shrug":
            return self._get_shoulder_height(landmarks)
        else:
            return self._get_elbow_angle(landmarks)

    def _is_standing(self, landmarks):
        """Check if person is roughly upright (not lying down)."""
        shoulder_y = (landmarks[L_SHOULDER]["ny"] + landmarks[R_SHOULDER]["ny"]) / 2
        hip_y = (landmarks[L_HIP]["ny"] + landmarks[R_HIP]["ny"]) / 2
        return hip_y > shoulder_y + 0.05  # hips below shoulders

    def _upper_body_visible(self, landmarks):
        """Check if shoulders, elbows, wrists are visible."""
        min_vis = 0.4
        for idx in [L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST]:
            if landmarks[idx].get("visibility", 0) < min_vis:
                return False
        return True

    def _process_pose(self, landmarks: list, timestamp: float) -> Dict:
        angle = self._get_angle(landmarks)
        is_standing = self._is_standing(landmarks)
        visible = self._upper_body_visible(landmarks)

        # Ready gate
        if not self._ready:
            if not visible:
                self.form_feedback = "Step into frame — show upper body"
            elif not is_standing:
                self.form_feedback = "Stand upright to begin"
            else:
                self._ready = True
                self._ready_since = timestamp
                self.form_feedback = "Ready! Start your reps"
                self.mark_active(timestamp)
                logger.info(f"ArmRep ready: pattern={self.pattern_name}, slug={self.exercise_slug}")
            return {"angle": round(angle, 1), "state": self._state}

        self._total_active_frames += 1
        self.mark_active(timestamp)

        # Rep counting with state machine
        if self.inverted:
            # Overhead press: start at ~90° (relaxed), go to ~160° (contracted/locked out)
            if self._state == "relaxed" and angle > self.contracted_angle:
                self._state = "contracted"
                self.form_feedback = "Good! Lock out overhead"
            elif self._state == "contracted" and angle < self.relaxed_angle + 10:
                self._state = "relaxed"
                self.reps += 1
                self.form_feedback = f"Rep {self.reps}!"
                self._form_good_frames += 1
                logger.info(f"ArmRep rep {self.reps} ({self.exercise_slug}, angle={angle:.1f})")
            elif self._state == "relaxed":
                self.form_feedback = "Press up — extend your arms"
            else:
                self.form_feedback = "Lower the weight with control"
        else:
            # Normal: start high angle (relaxed ~155°), go to low angle (contracted ~60°)
            if self._state == "relaxed" and angle < self.contracted_angle:
                self._state = "contracted"
                self.form_feedback = "Good! Now return with control"
            elif self._state == "contracted" and angle > self.relaxed_angle - 15:
                self._state = "relaxed"
                self.reps += 1
                self.form_feedback = f"Rep {self.reps}!"
                self._form_good_frames += 1
                logger.info(f"ArmRep rep {self.reps} ({self.exercise_slug}, angle={angle:.1f})")
            elif self._state == "relaxed":
                self.form_feedback = "Start the movement"
            else:
                self.form_feedback = "Return to starting position"

        return {
            "angle": round(angle, 1),
            "state": self._state,
            "pattern": self.pattern_name,
        }

    def get_final_report(self) -> Dict:
        report = super().get_final_report()
        form_score = round(
            (self._form_good_frames / max(self._total_active_frames, 1)) * 100
        ) if self.reps > 0 else 0
        report["form_summary"] = {
            "good_reps": self.reps,
            "form_score": max(0, min(100, form_score)),
            "pattern": self.pattern_name,
            "exercise": self.exercise_slug,
        }
        return report
