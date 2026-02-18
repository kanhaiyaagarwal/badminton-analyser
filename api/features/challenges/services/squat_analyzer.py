"""Squat rep counter — counts squat reps via knee angle with form quality tracking.

Used by both squat_half and squat_full challenge types (different down_angle thresholds).
"""

import math
import logging
from typing import Dict

from ....core.streaming.pose_detector import PoseDetector
from .rep_counter import RepCounterAnalyzer

logger = logging.getLogger(__name__)

# MediaPipe landmark indices
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28

VISIBILITY_GROUPS = {
    "head": [NOSE],
    "shoulders": [L_SHOULDER, R_SHOULDER],
    "hips": [L_HIP, R_HIP],
    "knees": [L_KNEE, R_KNEE],
    "ankles": [L_ANKLE, R_ANKLE],
}
VISIBILITY_THRESHOLD = 0.5
VISIBILITY_MESSAGES = {
    "head": "Can't see your head — adjust camera",
    "shoulders": "Shoulders not visible — step into frame",
    "hips": "Hips not visible — show full body",
    "knees": "Knees not visible — step back so full body is in frame",
    "ankles": "Ankles not visible — step back so feet are in frame",
}


class SquatAnalyzer(RepCounterAnalyzer):
    """
    Counts squat reps using the hip-knee-ankle angle.

    State machine: UP -> DOWN -> UP counts as 1 rep.

    Form checks:
    - Knee cave detection (knees collapsing inward)
    - Forward lean detection (excessive torso lean)
    - Partial squat detection (went partway down but not enough)
    - Ready gate: must be standing upright facing camera

    Auto-end triggers:
    - max_duration (default 5 min)
    - Sat down: hips below ankle level for > 2s
    - Stuck in DOWN: > stuck_timeout (5s)
    - Left frame: key landmarks not visible for > left_frame_timeout (3s)
    """

    def __init__(self, challenge_type="squat_full", config=None):
        super().__init__(challenge_type=challenge_type, config=config)
        cfg = config or {}
        from .rep_counter import CHALLENGE_DEFAULTS
        defaults = CHALLENGE_DEFAULTS.get(challenge_type, {})
        self.down_angle = cfg.get("down_angle", defaults.get("down_angle", 100))
        self.up_angle = cfg.get("up_angle", defaults.get("up_angle", 160))
        self.stuck_timeout = cfg.get("stuck_timeout", defaults.get("stuck_timeout", 5.0))
        self.left_frame_timeout = cfg.get("left_frame_timeout", defaults.get("left_frame_timeout", 3.0))
        self._first_rep_grace = cfg.get("first_rep_grace", defaults.get("first_rep_grace", 30.0))
        self.lean_threshold = cfg.get("lean_threshold", defaults.get("lean_threshold", 30))
        self.knee_cave_ratio = cfg.get("knee_cave_ratio", defaults.get("knee_cave_ratio", 0.85))

        self._state = "up"  # "up" | "down"
        self._ready = False  # require standing position
        self._ready_since = 0.0

        # Collapse detection timers
        self._down_since = 0.0
        self._sat_down_since = 0.0
        self._left_frame_since = 0.0

        # Form quality counters
        self._total_active_frames = 0
        self._partial_squat_count = 0
        self._knees_caving_frames = 0
        self._lean_frames = 0
        self._went_partial = False  # tracking partial descent
        self._prev_valid_angle = 170.0  # last trusted knee angle

    def _ankle_above_knee(self, landmarks):
        """True if either ankle is above its knee (impossible geometry)."""
        return (landmarks[L_ANKLE]["ny"] < landmarks[L_KNEE]["ny"] - 0.02
                or landmarks[R_ANKLE]["ny"] < landmarks[R_KNEE]["ny"] - 0.02)

    def _lower_body_confidence(self, landmarks):
        """Min visibility across hips, knees, ankles."""
        return min(
            max(landmarks[L_HIP].get("visibility", 0), landmarks[R_HIP].get("visibility", 0)),
            max(landmarks[L_KNEE].get("visibility", 0), landmarks[R_KNEE].get("visibility", 0)),
            max(landmarks[L_ANKLE].get("visibility", 0), landmarks[R_ANKLE].get("visibility", 0)),
        )

    def _process_pose(self, landmarks: list, timestamp: float) -> Dict:
        # --- Knee angle (primary rep metric) ---
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
        raw_angle = (left_angle + right_angle) / 2

        # --- Guard: reject garbage angles from bad landmarks ---
        # If ankle is above knee (physically impossible) or confidence
        # is too low, hold the previous valid angle to prevent false reps.
        lower_conf = self._lower_body_confidence(landmarks)
        if self._ankle_above_knee(landmarks) or lower_conf < 0.5:
            angle = self._prev_valid_angle
        else:
            angle = raw_angle
            self._prev_valid_angle = angle

        # --- Hip angle (shoulder-hip-knee) for lean detection ---
        left_hip_angle = PoseDetector.angle_between(
            (landmarks[L_SHOULDER]["nx"], landmarks[L_SHOULDER]["ny"]),
            (landmarks[L_HIP]["nx"], landmarks[L_HIP]["ny"]),
            (landmarks[L_KNEE]["nx"], landmarks[L_KNEE]["ny"]),
        )
        right_hip_angle = PoseDetector.angle_between(
            (landmarks[R_SHOULDER]["nx"], landmarks[R_SHOULDER]["ny"]),
            (landmarks[R_HIP]["nx"], landmarks[R_HIP]["ny"]),
            (landmarks[R_KNEE]["nx"], landmarks[R_KNEE]["ny"]),
        )
        hip_angle = (left_hip_angle + right_hip_angle) / 2

        # --- Forward lean: angle of shoulder-hip line from vertical ---
        shoulder_y = (landmarks[L_SHOULDER]["ny"] + landmarks[R_SHOULDER]["ny"]) / 2
        shoulder_x = (landmarks[L_SHOULDER]["nx"] + landmarks[R_SHOULDER]["nx"]) / 2
        hip_y = (landmarks[L_HIP]["ny"] + landmarks[R_HIP]["ny"]) / 2
        hip_x = (landmarks[L_HIP]["nx"] + landmarks[R_HIP]["nx"]) / 2
        dx = shoulder_x - hip_x
        dy = shoulder_y - hip_y
        lean_angle = abs(math.degrees(math.atan2(dx, -dy))) if abs(dy) > 0.01 else 0
        leaning = lean_angle > self.lean_threshold

        # --- Knee cave detection ---
        left_knee_x = landmarks[L_KNEE]["nx"]
        right_knee_x = landmarks[R_KNEE]["nx"]
        left_hip_x = landmarks[L_HIP]["nx"]
        right_hip_x = landmarks[R_HIP]["nx"]
        knee_spread = abs(left_knee_x - right_knee_x)
        hip_spread = abs(left_hip_x - right_hip_x)
        knees_caving = knee_spread < hip_spread * self.knee_cave_ratio if hip_spread > 0.01 else False

        # --- Sat-down detection: hips below ankle level ---
        ankle_y = (landmarks[L_ANKLE]["ny"] + landmarks[R_ANKLE]["ny"]) / 2
        hips_below_ankles = hip_y > ankle_y + 0.02

        # --- Left frame tracking ---
        hip_vis = max(landmarks[L_HIP].get("visibility", 0), landmarks[R_HIP].get("visibility", 0))
        knee_vis = max(landmarks[L_KNEE].get("visibility", 0), landmarks[R_KNEE].get("visibility", 0))
        ankle_vis = max(landmarks[L_ANKLE].get("visibility", 0), landmarks[R_ANKLE].get("visibility", 0))
        key_visible = hip_vis >= 0.4 and knee_vis >= 0.4 and ankle_vis >= 0.4

        if key_visible:
            self._left_frame_since = 0.0
        elif self._left_frame_since == 0.0:
            self._left_frame_since = timestamp

        depth_good = angle < self.down_angle

        # --- Visibility gate before ready ---
        if not self._ready:
            for group_name, indices in VISIBILITY_GROUPS.items():
                best_vis = max(landmarks[i].get("visibility", 0) for i in indices)
                if best_vis < VISIBILITY_THRESHOLD:
                    self.form_feedback = VISIBILITY_MESSAGES[group_name]
                    return self._build_result(angle, hip_angle, lean_angle, depth_good, knees_caving, leaning)

        # --- Ready gate: must be standing upright ---
        if not self._ready:
            if angle > self.up_angle:
                self._ready = True
                self._ready_since = timestamp
                self.form_feedback = "Ready! Start squatting"
                self.mark_active(timestamp)
                logger.info(f"Squat ready at t={timestamp:.2f}s (angle={angle:.1f})")
            else:
                self.form_feedback = "Stand upright facing the camera"
            return self._build_result(angle, hip_angle, lean_angle, depth_good, knees_caving, leaning)

        # --- Form quality tracking ---
        self._total_active_frames += 1
        if knees_caving and self._state == "down":
            self._knees_caving_frames += 1
        if leaning:
            self._lean_frames += 1

        self.mark_active(timestamp)

        # --- Sat-down tracking ---
        if hips_below_ankles:
            if self._sat_down_since == 0.0:
                self._sat_down_since = timestamp
        else:
            self._sat_down_since = 0.0

        # --- Rep counting ---
        if self._state == "up" and angle < self.down_angle:
            self._state = "down"
            self._down_since = timestamp
            self._went_partial = False
            self.form_feedback = "Good depth! Now stand up"
        elif self._state == "up" and angle < self.up_angle - 10:
            # Going down but haven't reached threshold
            self._went_partial = True
        elif self._state == "down" and angle > self.up_angle:
            self._state = "up"
            self._down_since = 0.0
            self.reps += 1
            self.form_feedback = f"Rep {self.reps}!"
            logger.info(f"Squat rep {self.reps} (angle={angle:.1f}, t={timestamp:.2f}s)")
        elif self._state == "up" and self._went_partial and angle > self.up_angle:
            # Came back up without reaching depth
            self._partial_squat_count += 1
            self._went_partial = False
            self.form_feedback = "Go lower! That didn't count"
        elif knees_caving and self._state == "down":
            self.form_feedback = "Push your knees out!"
        elif leaning and self._state == "down":
            self.form_feedback = "Keep your chest up — don't lean forward"
        elif self._state == "up":
            self.form_feedback = "Squat down — bend your knees"
        else:
            self.form_feedback = "Push back up to standing"

        # --- Collapse detection ---
        grace_expired = (
            self.reps > 0
            or (self._ready and self._ready_since > 0
                and timestamp - self._ready_since >= self._first_rep_grace)
        )

        if grace_expired and not self._session_ended:
            # Signal 1: Sat down — hips below ankles for > 2s
            if (self._sat_down_since > 0
                    and (timestamp - self._sat_down_since) > 2.0):
                self._session_ended = True
                self._end_reason = "sat_down"
                self.form_feedback = "Sat down — session over!"
                logger.info(f"Squat session ended: sat_down (reps={self.reps}, t={timestamp:.1f}s)")

            # Signal 2: Stuck in DOWN too long
            elif (self._state == "down" and self._down_since > 0
                  and (timestamp - self._down_since) > self.stuck_timeout):
                self._session_ended = True
                self._end_reason = "position_break"
                self.form_feedback = "Stuck at bottom — session over!"
                logger.info(f"Squat session ended: stuck_down (reps={self.reps}, t={timestamp:.1f}s)")

            # Signal 3: Left frame
            elif (self._left_frame_since > 0
                  and (timestamp - self._left_frame_since) > self.left_frame_timeout):
                self._session_ended = True
                self._end_reason = "left_frame"
                self.form_feedback = "Left frame — session over!"
                logger.info(f"Squat session ended: left_frame (reps={self.reps}, t={timestamp:.1f}s)")

        return self._build_result(angle, hip_angle, lean_angle, depth_good, knees_caving, leaning)

    def _build_result(self, angle, hip_angle, lean_angle, depth_good, knees_caving, leaning):
        return {
            "angle": round(angle, 1),
            "hip_angle": round(hip_angle, 1),
            "lean_angle": round(lean_angle, 1),
            "state": self._state,
            "depth_good": depth_good,
            "knees_caving": knees_caving,
            "leaning": leaning,
        }

    def get_final_report(self) -> Dict:
        report = super().get_final_report()
        total_attempts = self.reps + self._partial_squat_count
        knees_caving_pct = round(
            self._knees_caving_frames / max(self._total_active_frames, 1) * 100, 1
        )
        rep_quality = (self.reps / max(total_attempts, 1)) * 100
        knee_quality = 100 - knees_caving_pct
        form_score = round(rep_quality * 0.9 + knee_quality * 0.1)
        report["form_summary"] = {
            "total_attempts": total_attempts,
            "good_reps": self.reps,
            "partial_squats": self._partial_squat_count,
            "knees_caving_pct": knees_caving_pct,
            "form_score": max(0, min(100, form_score)),
        }
        return report
