"""Plank hold analyzer — tracks time in a valid plank position."""

import logging
from typing import Dict

from ....core.streaming.pose_detector import PoseDetector
from .rep_counter import RepCounterAnalyzer

logger = logging.getLogger(__name__)

# MediaPipe landmark indices
L_SHOULDER, R_SHOULDER = 11, 12
L_HIP, R_HIP = 23, 24
L_ANKLE, R_ANKLE = 27, 28


class PlankAnalyzer(RepCounterAnalyzer):
    """
    Detects a valid plank by checking shoulder-hip-ankle alignment.

    The angle formed by (shoulder, hip, ankle) should be close to 180
    degrees when in a proper plank.  If the angle drops below the
    threshold the hold timer pauses and form feedback is given.
    """

    def __init__(self, config=None):
        super().__init__(challenge_type="plank")
        cfg = config or {}
        self.good_angle_min = cfg.get("good_angle_min", 150)
        self.good_angle_max = cfg.get("good_angle_max", 195)
        self._in_plank = False

    def _process_pose(self, landmarks: list, timestamp: float) -> Dict:
        # Use the side with better visibility
        left_vis = min(
            landmarks[L_SHOULDER]["visibility"],
            landmarks[L_HIP]["visibility"],
            landmarks[L_ANKLE]["visibility"],
        )
        right_vis = min(
            landmarks[R_SHOULDER]["visibility"],
            landmarks[R_HIP]["visibility"],
            landmarks[R_ANKLE]["visibility"],
        )

        if left_vis >= right_vis:
            shoulder = (landmarks[L_SHOULDER]["nx"], landmarks[L_SHOULDER]["ny"])
            hip = (landmarks[L_HIP]["nx"], landmarks[L_HIP]["ny"])
            ankle = (landmarks[L_ANKLE]["nx"], landmarks[L_ANKLE]["ny"])
        else:
            shoulder = (landmarks[R_SHOULDER]["nx"], landmarks[R_SHOULDER]["ny"])
            hip = (landmarks[R_HIP]["nx"], landmarks[R_HIP]["ny"])
            ankle = (landmarks[R_ANKLE]["nx"], landmarks[R_ANKLE]["ny"])

        angle = PoseDetector.angle_between(shoulder, hip, ankle)

        good_form = self.good_angle_min <= angle <= self.good_angle_max

        if good_form:
            if self._last_timestamp > 0:
                dt = timestamp - self._last_timestamp
                if dt > 0 and dt < 1.0:  # guard against jumps
                    self.hold_seconds += dt
            self._in_plank = True
            self.form_feedback = "Good plank form!"
        else:
            self._in_plank = False
            if angle < self.good_angle_min:
                self.form_feedback = "Hips too high — straighten your body"
            else:
                self.form_feedback = "Hips sagging — engage your core"

        # Score for plank is hold_seconds
        self.reps = int(self.hold_seconds)

        return {
            "angle": round(angle, 1),
            "in_plank": self._in_plank,
        }
