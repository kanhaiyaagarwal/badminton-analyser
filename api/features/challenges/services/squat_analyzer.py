"""Squat rep counter — counts full squat reps via hip-knee angle."""

import logging
from typing import Dict

from ....core.streaming.pose_detector import PoseDetector
from .rep_counter import RepCounterAnalyzer

logger = logging.getLogger(__name__)

L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28


class SquatAnalyzer(RepCounterAnalyzer):
    """
    Counts squat reps using the hip-knee-ankle angle.

    State machine: STANDING → DOWN → STANDING counts as 1 rep.
    """

    def __init__(self, config=None):
        super().__init__(challenge_type="squat", config=config)
        cfg = config or {}
        self.down_angle = cfg.get("down_angle", 100)
        self.up_angle = cfg.get("up_angle", 160)
        self._state = "up"  # "up" | "down"

    def _process_pose(self, landmarks: list, timestamp: float) -> Dict:
        self.mark_active(timestamp)
        # Average both legs for robustness
        left_angle = PoseDetector.angle_between(
            (landmarks[L_HIP]["nx"], landmarks[L_HIP]["ny"]),
            (landmarks[L_KNEE]["nx"], landmarks[L_KNEE]["ny"]),
            (landmarks[L_ANKLE]["nx"], landmarks[L_ANKLE]["ny"]),
        )
        right_angle = PoseDetector.angle_between(
            (landmarks[R_HIP]["nx"], landmarks[R_HIP]["ny"]),
            (landmarks[R_KNEE]["nx"], landmarks[R_KNEE]["ny"]),
            (landmarks[R_ANKLE]["nx"], landmarks[R_ANKLE]["ny"]),
        )
        angle = (left_angle + right_angle) / 2

        # State machine
        if self._state == "up" and angle < self.down_angle:
            self._state = "down"
            self.form_feedback = "Good depth! Now stand up"
        elif self._state == "down" and angle > self.up_angle:
            self._state = "up"
            self.reps += 1
            self.form_feedback = f"Rep {self.reps}!"
        elif self._state == "up":
            self.form_feedback = "Squat down — bend your knees"
        else:
            self.form_feedback = "Push back up to standing"

        return {
            "angle": round(angle, 1),
            "state": self._state,
        }
