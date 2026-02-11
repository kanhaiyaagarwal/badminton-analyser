"""Pushup rep counter — counts pushup reps via elbow angle."""

import logging
from typing import Dict

from ....core.streaming.pose_detector import PoseDetector
from .rep_counter import RepCounterAnalyzer

logger = logging.getLogger(__name__)

L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16


class PushupAnalyzer(RepCounterAnalyzer):
    """
    Counts pushup reps using the shoulder-elbow-wrist angle.

    State machine: UP → DOWN → UP counts as 1 rep.
    """

    def __init__(self, config=None):
        super().__init__(challenge_type="pushup")
        cfg = config or {}
        self.down_angle = cfg.get("down_angle", 90)
        self.up_angle = cfg.get("up_angle", 155)
        self._state = "up"

    def _process_pose(self, landmarks: list, timestamp: float) -> Dict:
        left_angle = PoseDetector.angle_between(
            (landmarks[L_SHOULDER]["nx"], landmarks[L_SHOULDER]["ny"]),
            (landmarks[L_ELBOW]["nx"], landmarks[L_ELBOW]["ny"]),
            (landmarks[L_WRIST]["nx"], landmarks[L_WRIST]["ny"]),
        )
        right_angle = PoseDetector.angle_between(
            (landmarks[R_SHOULDER]["nx"], landmarks[R_SHOULDER]["ny"]),
            (landmarks[R_ELBOW]["nx"], landmarks[R_ELBOW]["ny"]),
            (landmarks[R_WRIST]["nx"], landmarks[R_WRIST]["ny"]),
        )
        angle = (left_angle + right_angle) / 2

        if self._state == "up" and angle < self.down_angle:
            self._state = "down"
            self.form_feedback = "Good! Now push up"
        elif self._state == "down" and angle > self.up_angle:
            self._state = "up"
            self.reps += 1
            self.form_feedback = f"Rep {self.reps}!"
        elif self._state == "up":
            self.form_feedback = "Lower your body — bend your elbows"
        else:
            self.form_feedback = "Push up — extend your arms"

        return {
            "angle": round(angle, 1),
            "state": self._state,
        }
