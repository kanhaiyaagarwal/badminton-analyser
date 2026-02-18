"""Squat hold analyzer — tracks time held in a valid squat position.

Plank-like hold pattern: timer accumulates while in good squat form (knee angle
below threshold, torso upright). Pauses when standing up or leaning too far.
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


class SquatHoldAnalyzer(RepCounterAnalyzer):
    """
    Tracks time held in a valid squat position.

    Hold time accumulates when knee angle is below hold_angle_max and
    the torso isn't leaning excessively.

    Auto-end triggers:
    - max_duration (default 5 min)
    - Form break too long: out of squat form for > form_break_timeout
    - Left frame: key landmarks not visible for > left_frame_timeout (3s)
    """

    def __init__(self, config=None):
        super().__init__(challenge_type="squat_hold", config=config)
        cfg = config or {}
        from .rep_counter import CHALLENGE_DEFAULTS
        defaults = CHALLENGE_DEFAULTS.get("squat_hold", {})
        self.hold_angle_max = cfg.get("hold_angle_max", defaults.get("hold_angle_max", 130))
        self.good_angle_min = cfg.get("good_angle_min", defaults.get("good_angle_min", 90))
        self.lean_threshold = cfg.get("lean_threshold", defaults.get("lean_threshold", 30))
        self._first_rep_grace = cfg.get("first_rep_grace", defaults.get("first_rep_grace", 30.0))
        self.left_frame_timeout = cfg.get("left_frame_timeout", defaults.get("left_frame_timeout", 3.0))
        self.form_break_timeout = cfg.get("form_break_timeout", defaults.get("form_break_timeout", 5.0))
        self.form_break_grace = cfg.get("form_break_grace", defaults.get("form_break_grace", 3.0))

        self._ready = False
        self._ready_since = 0.0
        self._in_hold = False

        # Collapse detection timers
        self._form_break_since = 0.0
        self._left_frame_since = 0.0

        # Depth zone threshold: angle below this = full depth, above = half depth
        self.full_depth_angle = cfg.get("full_depth_angle", defaults.get("full_depth_angle", 100))

        # Form quality counters
        self._total_active_frames = 0
        self._good_form_frames = 0
        self._form_break_count = 0
        self._lean_frames = 0
        self._depth_lost_frames = 0
        self._prev_good_form = False
        self._prev_valid_angle = 170.0  # last trusted knee angle

        # Depth zone time tracking
        self._half_hold_seconds = 0.0   # hold_angle_max > angle >= full_depth_angle
        self._full_hold_seconds = 0.0   # angle < full_depth_angle

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
        # --- Knee angle ---
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
        lower_conf = self._lower_body_confidence(landmarks)
        if self._ankle_above_knee(landmarks) or lower_conf < 0.5:
            angle = self._prev_valid_angle
        else:
            angle = raw_angle
            self._prev_valid_angle = angle

        # --- Forward lean ---
        shoulder_y = (landmarks[L_SHOULDER]["ny"] + landmarks[R_SHOULDER]["ny"]) / 2
        shoulder_x = (landmarks[L_SHOULDER]["nx"] + landmarks[R_SHOULDER]["nx"]) / 2
        hip_y = (landmarks[L_HIP]["ny"] + landmarks[R_HIP]["ny"]) / 2
        hip_x = (landmarks[L_HIP]["nx"] + landmarks[R_HIP]["nx"]) / 2
        dx = shoulder_x - hip_x
        dy = shoulder_y - hip_y
        lean_angle = abs(math.degrees(math.atan2(dx, -dy))) if abs(dy) > 0.01 else 0
        leaning = lean_angle > self.lean_threshold

        # --- Left frame tracking ---
        hip_vis = max(landmarks[L_HIP].get("visibility", 0), landmarks[R_HIP].get("visibility", 0))
        knee_vis = max(landmarks[L_KNEE].get("visibility", 0), landmarks[R_KNEE].get("visibility", 0))
        ankle_vis = max(landmarks[L_ANKLE].get("visibility", 0), landmarks[R_ANKLE].get("visibility", 0))
        key_visible = hip_vis >= 0.4 and knee_vis >= 0.4 and ankle_vis >= 0.4

        if key_visible:
            self._left_frame_since = 0.0
        elif self._left_frame_since == 0.0:
            self._left_frame_since = timestamp

        # Good form = knees bent enough and not leaning excessively
        in_squat = angle < self.hold_angle_max
        good_form = in_squat and not leaning

        # --- Visibility gate before ready ---
        if not self._ready:
            for group_name, indices in VISIBILITY_GROUPS.items():
                best_vis = max(landmarks[i].get("visibility", 0) for i in indices)
                if best_vis < VISIBILITY_THRESHOLD:
                    self.form_feedback = VISIBILITY_MESSAGES[group_name]
                    return {"angle": round(angle, 1), "in_hold": False, "leaning": leaning}

        # --- Ready gate: must be standing upright first, then squat down ---
        if not self._ready:
            if angle > 150:  # standing
                self._ready = True
                self._ready_since = timestamp
                self.form_feedback = "Ready! Lower into squat position"
                self.mark_active(timestamp)
                logger.info(f"Squat hold ready at t={timestamp:.2f}s")
            else:
                self.form_feedback = "Stand upright facing the camera"
            return {"angle": round(angle, 1), "in_hold": False, "leaning": leaning}

        # --- Form quality tracking ---
        self._total_active_frames += 1
        if good_form:
            self._good_form_frames += 1
        if leaning and in_squat:
            self._lean_frames += 1
        if not in_squat and self._in_hold:
            self._depth_lost_frames += 1
        if self._prev_good_form and not good_form:
            self._form_break_count += 1
        self._prev_good_form = good_form

        # --- Hold time tracking ---
        is_full_depth = angle < self.full_depth_angle
        if good_form:
            if self._last_timestamp > 0:
                dt = timestamp - self._last_timestamp
                if 0 < dt < 1.0:
                    self.hold_seconds += dt
                    if is_full_depth:
                        self._full_hold_seconds += dt
                    else:
                        self._half_hold_seconds += dt
            self._in_hold = True
            self._form_break_since = 0.0
            self.mark_active(timestamp)

            if is_full_depth:
                self.form_feedback = "Great depth — hold it!"
            else:
                self.form_feedback = "Hold the squat — go deeper for full depth!"
        else:
            self._in_hold = False
            if self._form_break_since == 0.0:
                self._form_break_since = timestamp

            if not in_squat:
                self.form_feedback = "Don't stand up — hold it"
            elif leaning:
                self.form_feedback = "Keep your chest up — don't lean forward"

        # Score for hold is hold_seconds
        self.reps = int(self.hold_seconds)

        # --- Collapse / end-session detection ---
        grace_expired = (
            self.hold_seconds > 0
            or (self._ready and self._ready_since > 0
                and timestamp - self._ready_since >= self._first_rep_grace)
        )

        if grace_expired and not self._session_ended:
            # Signal 1: Form break too long
            if self._form_break_since > 0:
                break_dur = timestamp - self._form_break_since
                effective_limit = (
                    self.form_break_timeout if self.hold_seconds < 15
                    else self.form_break_grace
                )
                if break_dur >= effective_limit:
                    self._session_ended = True
                    self._end_reason = "form_break"
                    self.form_feedback = "Squat form lost — session over!"
                    logger.info(
                        f"Squat hold ended: form_break "
                        f"(hold={self.hold_seconds:.1f}s, t={timestamp:.1f}s)"
                    )

            # Signal 2: Left frame
            if (not self._session_ended
                    and self._left_frame_since > 0
                    and (timestamp - self._left_frame_since) > self.left_frame_timeout):
                self._session_ended = True
                self._end_reason = "left_frame"
                self.form_feedback = "Left frame — session over!"
                logger.info(
                    f"Squat hold ended: left_frame "
                    f"(hold={self.hold_seconds:.1f}s, t={timestamp:.1f}s)"
                )

        return {"angle": round(angle, 1), "in_hold": self._in_hold, "leaning": leaning}

    def get_final_report(self) -> Dict:
        report = super().get_final_report()
        # Override score to be hold_seconds (like plank)
        report["score"] = int(self.hold_seconds)
        duration = report.get("duration_seconds", 0)
        good_form_pct = round(self.hold_seconds / max(duration, 0.1) * 100, 1)
        total_hold = max(self.hold_seconds, 0.1)
        report["form_summary"] = {
            "good_form_pct": min(100.0, good_form_pct),
            "form_break_count": self._form_break_count,
            "lean_frames": self._lean_frames,
            "depth_lost_frames": self._depth_lost_frames,
            "form_score": max(0, min(100, round(good_form_pct))),
            "half_hold_seconds": round(self._half_hold_seconds, 1),
            "full_hold_seconds": round(self._full_hold_seconds, 1),
            "half_hold_pct": round(self._half_hold_seconds / total_hold * 100, 1),
            "full_hold_pct": round(self._full_hold_seconds / total_hold * 100, 1),
        }
        return report
