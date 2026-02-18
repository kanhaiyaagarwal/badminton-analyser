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
        self.form_hysteresis = cfg.get("form_hysteresis", 10)
        self.sag_threshold = cfg.get("sag_threshold", 0.02)
        self.horizontal_threshold = cfg.get("horizontal_threshold", 0.35)
        self.flat_threshold = cfg.get("flat_threshold", 0.03)
        self.knee_angle_min = cfg.get("knee_angle_min", 150)
        self._in_plank = False
        self._in_good_form = False  # hysteresis state
        self._ready = False  # require user to get into plank first
        # Form quality counters
        self._form_break_count = 0
        self._sag_frames = 0
        self._pike_frames = 0
        self._total_active_frames = 0
        self._prev_good_form = False

        # Safety / auto-end config
        self._ready_since = 0.0
        self._stood_up_since = 0.0
        self._form_break_since = 0.0
        self._first_rep_grace = cfg.get("first_rep_grace", 30.0)
        self.stood_up_timeout = cfg.get("stood_up_timeout", 1.5)
        self.stood_up_early_timeout = cfg.get("stood_up_early_timeout", 8.0)
        self.recovery_window = cfg.get("recovery_window", 15.0)
        self.form_break_grace = cfg.get("form_break_grace", 3.0)
        self.form_break_timeout = cfg.get("form_break_timeout", 5.0)
        self.form_break_post_recovery = cfg.get("form_break_post_recovery", 2.0)
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

        best_vis = max(left_vis, right_vis)

        if left_vis >= right_vis:
            shoulder = (landmarks[L_SHOULDER]["nx"], landmarks[L_SHOULDER]["ny"])
            hip = (landmarks[L_HIP]["nx"], landmarks[L_HIP]["ny"])
            knee = (landmarks[L_KNEE]["nx"], landmarks[L_KNEE]["ny"])
            ankle = (landmarks[L_ANKLE]["nx"], landmarks[L_ANKLE]["ny"])
            knee_vis = min(landmarks[L_HIP]["visibility"], landmarks[L_KNEE]["visibility"], landmarks[L_ANKLE]["visibility"])
        else:
            shoulder = (landmarks[R_SHOULDER]["nx"], landmarks[R_SHOULDER]["ny"])
            hip = (landmarks[R_HIP]["nx"], landmarks[R_HIP]["ny"])
            knee = (landmarks[R_KNEE]["nx"], landmarks[R_KNEE]["ny"])
            ankle = (landmarks[R_ANKLE]["nx"], landmarks[R_ANKLE]["ny"])
            knee_vis = min(landmarks[R_HIP]["visibility"], landmarks[R_KNEE]["visibility"], landmarks[R_ANKLE]["visibility"])

        angle = PoseDetector.angle_between(shoulder, hip, ankle)

        # Knee straightness check: hip-knee-ankle angle must be near 180°.
        # Dropping to knees keeps shoulder-hip-ankle ~174° but bends knee to ~90-120°.
        knee_angle = PoseDetector.angle_between(hip, knee, ankle)
        knees_straight = knee_vis < 0.3 or knee_angle >= self.knee_angle_min

        # Horizontal check (same concept as pushup)
        shoulder_y = (landmarks[L_SHOULDER]["ny"] + landmarks[R_SHOULDER]["ny"]) / 2
        hip_y = (landmarks[L_HIP]["ny"] + landmarks[R_HIP]["ny"]) / 2
        ankle_y = (landmarks[L_ANKLE]["ny"] + landmarks[R_ANKLE]["ny"]) / 2
        y_spread = max(shoulder_y, hip_y, ankle_y) - min(shoulder_y, hip_y, ankle_y)
        is_horizontal = y_spread < self.horizontal_threshold

        # Flat-on-ground check: if y_spread is near zero, the person is lying
        # flat (not planking). A valid plank requires some elevation.
        not_flat = y_spread >= self.flat_threshold

        # Landmark visibility gate: if key landmarks (shoulder/hip/ankle) are
        # not visible, angle is unreliable (MediaPipe hallucinates off-screen
        # positions in a straight line, giving fake ~174° angles)
        landmarks_visible = best_vis >= 0.3

        # Hysteresis: once in good form, angle must drop further to exit
        if self._in_good_form:
            good_form = landmarks_visible and knees_straight and not_flat and angle >= (self.good_angle_min - self.form_hysteresis)
        else:
            good_form = landmarks_visible and knees_straight and not_flat and angle >= self.good_angle_min

        # --- Front-facing camera detection ---
        shoulder_x_gap = abs(landmarks[L_SHOULDER]["nx"] - landmarks[R_SHOULDER]["nx"])
        hip_x_gap = abs(landmarks[L_HIP]["nx"] - landmarks[R_HIP]["nx"])
        if not self._ready and shoulder_x_gap > 0.15 and hip_x_gap > 0.15:
            self.form_feedback = "Place your camera to the side for best results"
            return {"angle": round(angle, 1), "in_plank": False}

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
        # Reset stood_up timer if horizontal OR in good form (full hand plank
        # has high shoulder_y, failing is_horizontal even though form is valid)
        if is_horizontal or good_form:
            self._stood_up_since = 0.0
            self.mark_active(timestamp)
        elif self._stood_up_since == 0.0:
            self._stood_up_since = timestamp

        # Position-based sag/pike detection
        mid_y = (shoulder_y + ankle_y) / 2
        hips_sagging = hip_y > mid_y + self.sag_threshold

        # --- Form quality tracking ---
        self._total_active_frames += 1
        if self._prev_good_form and not good_form:
            self._form_break_count += 1
        if not good_form:
            if hips_sagging:
                self._sag_frames += 1
            else:
                self._pike_frames += 1
        self._prev_good_form = good_form

        # Hold time tracking
        if good_form:
            if self._last_timestamp > 0:
                dt = timestamp - self._last_timestamp
                if dt > 0 and dt < 1.0:  # guard against jumps
                    self.hold_seconds += dt
            self._in_plank = True
            self._in_good_form = True
            self.form_feedback = "Good plank form!"
            self._form_break_since = 0.0
            self.mark_active(timestamp)
        else:
            self._in_plank = False
            self._in_good_form = False
            if self._form_break_since == 0.0:
                self._form_break_since = timestamp
            break_dur = timestamp - self._form_break_since
            in_recovery = self.hold_seconds < self.recovery_window
            if hips_sagging:
                form_hint = "Hips sagging — engage your core"
            else:
                form_hint = "Hips too high — straighten your body"
            if in_recovery and break_dur < self.form_break_grace:
                # Early in session + brief break — just corrective feedback
                self.form_feedback = form_hint
            elif in_recovery:
                # Early in session + past grace — countdown to end
                remaining = max(0, self.form_break_timeout - break_dur)
                self.form_feedback = f"Get back in position! ({int(remaining)}s)"
            else:
                # Past recovery window — show what's wrong
                self.form_feedback = form_hint

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
                effective_limit = self.form_break_timeout if in_recovery else self.form_break_post_recovery
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

    def get_final_report(self) -> Dict:
        report = super().get_final_report()
        duration = report.get("duration_seconds", 0)
        good_form_pct = round(self.hold_seconds / max(duration, 0.1) * 100, 1)
        report["form_summary"] = {
            "good_form_pct": min(100.0, good_form_pct),
            "form_break_count": self._form_break_count,
            "sag_frames": self._sag_frames,
            "pike_frames": self._pike_frames,
            "form_score": max(0, min(100, round(good_form_pct))),
        }
        return report
