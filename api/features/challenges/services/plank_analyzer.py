"""Plank hold analyzer — tracks time in a valid plank position."""

import logging
from typing import Dict

from ....core.streaming.pose_detector import PoseDetector
from .rep_counter import RepCounterAnalyzer

logger = logging.getLogger(__name__)

# MediaPipe landmark indices
L_SHOULDER, R_SHOULDER = 11, 12
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28

VISIBILITY_GROUPS = {
    "head": [0],                          # nose
    "shoulders": [L_SHOULDER, R_SHOULDER],
    "torso": [L_HIP, R_HIP],
    "legs": [L_KNEE, R_KNEE, L_ANKLE, R_ANKLE],
}
VISIBILITY_THRESHOLD = 0.5
VISIBILITY_MESSAGES = {
    "head": "Can't see your head — adjust camera",
    "shoulders": "Shoulders not visible — step into frame",
    "torso": "Torso not visible — show full body",
    "legs": "Legs not visible — step back so full body is in frame",
}


class PlankAnalyzer(RepCounterAnalyzer):
    """
    Detects a valid plank by checking shoulder-hip-ankle alignment.

    The angle formed by (shoulder, hip, ankle) should be close to 180
    degrees when in a proper plank.  If the angle drops below the
    threshold the hold timer pauses and form feedback is given.

    Auto-end triggers:
    - max_duration (default 5 min)
    - inactivity_timeout: user breaks plank form for 10s
    - collapse: body on ground, form lost too long, or stood up
    """

    def __init__(self, config=None):
        super().__init__(challenge_type="plank", config=config)
        cfg = config or {}
        self.good_angle_min = cfg.get("good_angle_min", 150)
        self.good_angle_max = cfg.get("good_angle_max", 195)
        self._in_plank = False
        self._ready = False  # require user to get into plank first

        # Safety / auto-end config
        self._ready_since = 0.0
        self._stood_up_since = 0.0
        self._form_break_since = 0.0
        self._first_rep_grace = cfg.get("first_rep_grace", 30.0)
        self.stood_up_timeout = cfg.get("stood_up_timeout", 1.5)
        self.stood_up_early_timeout = cfg.get("stood_up_early_timeout", 10.0)
        self.recovery_window = cfg.get("recovery_window", 15.0)
        self.form_break_grace = cfg.get("form_break_grace", 3.0)
        self.form_break_timeout = cfg.get("form_break_timeout", 8.0)
        self.collapse_gap = cfg.get("collapse_gap", 0.03)
        self.collapse_hip_gap = cfg.get("collapse_hip_gap", 0.06)

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

        # Horizontal check (same concept as pushup)
        shoulder_y = (landmarks[L_SHOULDER]["ny"] + landmarks[R_SHOULDER]["ny"]) / 2
        hip_y = (landmarks[L_HIP]["ny"] + landmarks[R_HIP]["ny"]) / 2
        ankle_y = (landmarks[L_ANKLE]["ny"] + landmarks[R_ANKLE]["ny"]) / 2
        y_spread = max(shoulder_y, hip_y, ankle_y) - min(shoulder_y, hip_y, ankle_y)
        is_horizontal = y_spread < 0.25

        good_form = self.good_angle_min <= angle <= self.good_angle_max

        # --- Visibility gate: all body parts must be visible before ready ---
        if not self._ready:
            for group_name, indices in VISIBILITY_GROUPS.items():
                best_vis = max(landmarks[i].get("visibility", 0) for i in indices)
                if best_vis < VISIBILITY_THRESHOLD:
                    self.form_feedback = VISIBILITY_MESSAGES[group_name]
                    return {
                        "angle": round(angle, 1),
                        "in_plank": False,
                    }

        # Ready gate: latch on once user gets into plank
        if not self._ready:
            if is_horizontal and good_form:
                self._ready = True
                self._ready_since = timestamp
                self.form_feedback = "Plank detected — hold it!"
                self.mark_active(timestamp)
            else:
                self.form_feedback = "Get into plank position"
                return {
                    "angle": round(angle, 1),
                    "in_plank": False,
                }

        # --- Stood-up tracking ---
        if is_horizontal:
            self._stood_up_since = 0.0
            self.mark_active(timestamp)
        elif self._stood_up_since == 0.0:
            self._stood_up_since = timestamp

        # Hold time tracking
        if good_form:
            if self._last_timestamp > 0:
                dt = timestamp - self._last_timestamp
                if dt > 0 and dt < 1.0:  # guard against jumps
                    self.hold_seconds += dt
            self._in_plank = True
            self.form_feedback = "Good plank form!"
            self._form_break_since = 0.0
        else:
            self._in_plank = False
            if self._form_break_since == 0.0:
                self._form_break_since = timestamp
            break_dur = timestamp - self._form_break_since
            in_recovery = self.hold_seconds < self.recovery_window
            if in_recovery and break_dur < self.form_break_grace:
                # Early in session + brief break — just corrective feedback
                if angle < self.good_angle_min:
                    self.form_feedback = "Hips too high — straighten your body"
                else:
                    self.form_feedback = "Hips sagging — engage your core"
            elif in_recovery:
                # Early in session + past grace — countdown to end
                remaining = max(0, self.form_break_timeout - break_dur)
                self.form_feedback = f"Get back in position! ({int(remaining)}s)"
            else:
                # Past recovery window — just show what's wrong, session ends quickly
                if angle < self.good_angle_min:
                    self.form_feedback = "Hips too high — straighten your body"
                else:
                    self.form_feedback = "Hips sagging — engage your core"

        # --- Collapse / end-session detection ---
        grace_expired = (
            self.hold_seconds > 0
            or (self._ready and self._ready_since > 0
                and timestamp - self._ready_since >= self._first_rep_grace)
        )

        if grace_expired and not self._session_ended:
            # Wrist Y for ground-level reference
            wrist_ny = (landmarks[L_WRIST]["ny"] + landmarks[R_WRIST]["ny"]) / 2

            # Signal 1: Body on ground — shoulders AND hips near wrist (ground) level
            if (wrist_ny - shoulder_y < self.collapse_gap
                    and wrist_ny - hip_y < self.collapse_hip_gap):
                self._session_ended = True
                self._end_reason = "torso_on_ground"
                self.form_feedback = "Body on ground — session over!"
                logger.info(
                    f"Plank session ended: torso_on_ground "
                    f"(hold={self.hold_seconds:.1f}s, t={timestamp:.1f}s)"
                )

            # Signal 2: Form break too long
            # During recovery window (first 15s): full grace + countdown
            # After recovery window: end after 1.5s of bad form
            elif self._form_break_since > 0:
                break_dur = timestamp - self._form_break_since
                in_recovery = self.hold_seconds < self.recovery_window
                effective_limit = self.form_break_timeout if in_recovery else 1.5
                if break_dur >= effective_limit:
                    self._session_ended = True
                    self._end_reason = "form_break"
                    self.form_feedback = "Plank form lost — session over!"
                    logger.info(
                        f"Plank session ended: form_break "
                        f"(hold={self.hold_seconds:.1f}s, t={timestamp:.1f}s)"
                    )

            # Signal 3: Stood up — left plank position
            else:
                effective_timeout = (
                    self.stood_up_early_timeout if self.hold_seconds < 5
                    else self.stood_up_timeout
                )
                if (not is_horizontal
                        and self._stood_up_since > 0
                        and (timestamp - self._stood_up_since) >= effective_timeout):
                    self._session_ended = True
                    self._end_reason = "stood_up"
                    self.form_feedback = "Left plank position — session over!"
                    logger.info(
                        f"Plank session ended: stood_up "
                        f"(hold={self.hold_seconds:.1f}s, t={timestamp:.1f}s)"
                    )

        # Score for plank is hold_seconds
        self.reps = int(self.hold_seconds)

        return {
            "angle": round(angle, 1),
            "in_plank": self._in_plank,
        }
