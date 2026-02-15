"""Pushup rep counter — counts pushup reps via elbow angle with leg form detection."""

import logging
from typing import Dict

from ....core.streaming.pose_detector import PoseDetector
from .rep_counter import RepCounterAnalyzer

logger = logging.getLogger(__name__)

L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
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


class PushupAnalyzer(RepCounterAnalyzer):
    """
    Counts pushup reps using the shoulder-elbow-wrist angle.

    State machine: UP → DOWN → UP counts as 1 rep.

    Form checks:
    - Legs straight (knee angle > threshold) — detects kneeling / legs on ground
    - Body aligned (shoulder-hip-ankle roughly straight)
    - Ready gate: won't count reps until person is in a horizontal pushup position

    Auto-end triggers:
    - max_duration (default 5 min)
    - inactivity_timeout: user leaves pushup position for 10s
    """

    def __init__(self, config=None):
        super().__init__(challenge_type="pushup", config=config)
        cfg = config or {}
        self.down_angle = cfg.get("down_angle", 90)
        self.up_angle = cfg.get("up_angle", 155)
        self.knee_threshold = cfg.get("knee_threshold", 150)
        self.body_spread_threshold = cfg.get("body_spread_threshold", 0.25)
        # Collapse detection: end session when player breaks position
        self.collapse_hold_time = cfg.get("collapse_hold_time", 5.0)  # max seconds in DOWN
        self.collapse_gap = cfg.get("collapse_gap", 0.03)  # min shoulder-wrist ny gap
        self.collapse_hip_gap = cfg.get("collapse_hip_gap", 0.06)  # min hip-wrist ny gap for collapse
        # Half-pushup detection: hips on ground = cobra pose, not a real pushup
        self.half_pushup_gap = cfg.get("half_pushup_gap", 0.05)  # min hip-wrist ny gap
        # Stood-up detection: person leaves pushup position
        self.stood_up_timeout = cfg.get("stood_up_timeout", 1.5)  # seconds non-horizontal before end
        self._first_rep_grace = cfg.get("first_rep_grace", 30.0)  # seconds to wait for first rep
        self.collapse_recovery_deg = cfg.get("collapse_recovery_deg", 20)  # degrees above min = recovering
        self._state = "up"
        self._ready = False  # override base: require pushup position
        self._ready_since = 0.0  # timestamp when ready was set
        self._down_since = 0.0  # timestamp when entered DOWN state
        self._down_min_angle = 180.0  # lowest angle seen during current down phase
        self._stood_up_since = 0.0  # timestamp when left horizontal position

    def _process_pose(self, landmarks: list, timestamp: float) -> Dict:
        # --- Elbow angle (primary rep metric) ---
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

        # --- Knee angle (hip→knee→ankle) — straight legs check ---
        left_knee = PoseDetector.angle_between(
            (landmarks[L_HIP]["nx"], landmarks[L_HIP]["ny"]),
            (landmarks[L_KNEE]["nx"], landmarks[L_KNEE]["ny"]),
            (landmarks[L_ANKLE]["nx"], landmarks[L_ANKLE]["ny"]),
        )
        right_knee = PoseDetector.angle_between(
            (landmarks[R_HIP]["nx"], landmarks[R_HIP]["ny"]),
            (landmarks[R_KNEE]["nx"], landmarks[R_KNEE]["ny"]),
            (landmarks[R_ANKLE]["nx"], landmarks[R_ANKLE]["ny"]),
        )
        knee_angle = (left_knee + right_knee) / 2
        legs_straight = knee_angle > self.knee_threshold

        # --- Body alignment (shoulder-hip-ankle angle) ---
        left_body = PoseDetector.angle_between(
            (landmarks[L_SHOULDER]["nx"], landmarks[L_SHOULDER]["ny"]),
            (landmarks[L_HIP]["nx"], landmarks[L_HIP]["ny"]),
            (landmarks[L_ANKLE]["nx"], landmarks[L_ANKLE]["ny"]),
        )
        right_body = PoseDetector.angle_between(
            (landmarks[R_SHOULDER]["nx"], landmarks[R_SHOULDER]["ny"]),
            (landmarks[R_HIP]["nx"], landmarks[R_HIP]["ny"]),
            (landmarks[R_ANKLE]["nx"], landmarks[R_ANKLE]["ny"]),
        )
        body_angle = (left_body + right_body) / 2

        # --- Horizontal check: vertical spread of shoulder/hip/ankle ---
        # Small spread = lying horizontal (pushup), large spread = standing
        shoulder_y = (landmarks[L_SHOULDER]["ny"] + landmarks[R_SHOULDER]["ny"]) / 2
        hip_y = (landmarks[L_HIP]["ny"] + landmarks[R_HIP]["ny"]) / 2
        ankle_y = (landmarks[L_ANKLE]["ny"] + landmarks[R_ANKLE]["ny"]) / 2
        y_spread = max(shoulder_y, hip_y, ankle_y) - min(shoulder_y, hip_y, ankle_y)
        is_horizontal = y_spread < self.body_spread_threshold

        # --- Visibility gate: all body parts must be visible ---
        if not self._ready:
            for group_name, indices in VISIBILITY_GROUPS.items():
                best_vis = max(landmarks[i].get("visibility", 0) for i in indices)
                if best_vis < VISIBILITY_THRESHOLD:
                    self.form_feedback = VISIBILITY_MESSAGES[group_name]
                    return {
                        "angle": round(angle, 1),
                        "knee_angle": round(knee_angle, 1),
                        "body_angle": round(body_angle, 1),
                        "state": self._state,
                        "legs_straight": legs_straight,
                        "is_horizontal": is_horizontal,
                    }

        # --- Ready gate: latch on once in pushup position ---
        if not self._ready:
            if is_horizontal:
                self._ready = True
                self._ready_since = timestamp
                self.form_feedback = "Ready! Start your pushups"
                self.mark_active(timestamp)
                logger.info(f"Pushup ready at t={timestamp:.2f}s (spread={y_spread:.3f})")
            else:
                self.form_feedback = "Get into pushup position"
            # Return early so "Ready!" feedback is not overwritten by rep logic
            return {
                "angle": round(angle, 1),
                "knee_angle": round(knee_angle, 1),
                "body_angle": round(body_angle, 1),
                "state": self._state,
                "legs_straight": legs_straight,
                "is_horizontal": is_horizontal,
            }

        # --- Activity tracking & stood-up detection ---
        if is_horizontal:
            self.mark_active(timestamp)
            self._stood_up_since = 0.0
        elif self._stood_up_since == 0.0:
            self._stood_up_since = timestamp

        # --- Ground reference & gap metrics ---
        wrist_ny = (landmarks[L_WRIST]["ny"] + landmarks[R_WRIST]["ny"]) / 2
        torso_gap = wrist_ny - shoulder_y  # positive = shoulders above wrists
        hip_ground_gap = wrist_ny - hip_y  # positive = hips above wrists (ground)
        # Half-pushup: hips on ground (gap tiny), only chest lifts = cobra pose
        is_half_pushup = hip_ground_gap < self.half_pushup_gap

        # --- Rep counting (only when ready) ---
        if self._state == "up" and angle < self.down_angle:
            self._state = "down"
            self._down_since = timestamp
            self._down_min_angle = angle
            self.form_feedback = "Good! Now push up"
        elif self._state == "down" and angle > self.up_angle:
            self._state = "up"
            self._down_since = 0.0
            self._down_min_angle = 180.0
            if is_half_pushup:
                # Don't count — hips on ground, only chest moved
                self.form_feedback = "Half pushup! Lift your hips off the ground"
            else:
                self.reps += 1
                self.form_feedback = f"Rep {self.reps}!"
                logger.info(f"Pushup rep {self.reps} detected (angle={angle:.1f}, t={timestamp:.2f}s)")
        elif is_half_pushup:
            self.form_feedback = "Hips on ground — lift into plank position"
        elif not legs_straight:
            self.form_feedback = "Straighten your legs"
        elif self._state == "up":
            self.form_feedback = "Lower your body — bend your elbows"
        else:
            self.form_feedback = "Push up — extend your arms"

        # --- Collapse detection (end session if position breaks) ---
        collapsed = False
        collapse_reason = ""

        # Track lowest angle during down phase
        if self._state == "down":
            self._down_min_angle = min(self._down_min_angle, angle)

        # Don't auto-end until first rep or grace period expires
        grace_expired = (self.reps > 0
                         or (self._ready and self._ready_since > 0
                             and timestamp - self._ready_since >= self._first_rep_grace))

        if grace_expired and self._state == "down" and self._down_since > 0:
            # Signal 1: Whole body on ground — BOTH shoulder AND hip gaps vanish
            # torso_gap alone is unreliable: in a proper pushup down, shoulders
            # naturally approach wrist height. True collapse = hips drop too.
            if torso_gap < self.collapse_gap and hip_ground_gap < self.collapse_hip_gap:
                collapsed = True
                collapse_reason = "torso_on_ground"

            # Signal 2: Stuck in DOWN too long — can't push back up
            # BUT if user is actively recovering (angle well above minimum),
            # they're pushing up — reset the timer instead of ending.
            elif (timestamp - self._down_since) > self.collapse_hold_time:
                recovering = (angle - self._down_min_angle) >= self.collapse_recovery_deg
                if recovering:
                    # User is actively pushing up, give them more time.
                    # Reset min angle so next window measures fresh recovery.
                    logger.info(
                        f"Collapse timer reset: user recovering "
                        f"(angle={angle:.1f}, min={self._down_min_angle:.1f}, "
                        f"recovery={angle - self._down_min_angle:.1f}°)"
                    )
                    self._down_since = timestamp
                    self._down_min_angle = angle
                else:
                    collapsed = True
                    collapse_reason = "position_break"

        # Signal 3: Stood up — left pushup position
        if (grace_expired
                and not collapsed
                and not is_horizontal
                and self._stood_up_since > 0
                and (timestamp - self._stood_up_since) >= self.stood_up_timeout):
            collapsed = True
            collapse_reason = "stood_up"

        if collapsed:
            self._session_ended = True
            self._end_reason = collapse_reason
            if collapse_reason == "torso_on_ground":
                self.form_feedback = "Body touched ground — session over!"
            elif collapse_reason == "stood_up":
                self.form_feedback = "Left pushup position — session over!"
            else:
                self.form_feedback = "Position break — couldn't push back up"
            logger.info(
                f"Pushup session ended: {collapse_reason} "
                f"(spread={y_spread:.3f}, gap={torso_gap:.3f}, reps={self.reps}, t={timestamp:.1f}s)"
            )

        return {
            "angle": round(angle, 1),
            "knee_angle": round(knee_angle, 1),
            "body_angle": round(body_angle, 1),
            "state": self._state,
            "legs_straight": legs_straight,
            "is_horizontal": is_horizontal,
            "torso_gap": round(torso_gap, 3),
            "hip_ground_gap": round(hip_ground_gap, 3),
            "is_half_pushup": is_half_pushup,
            "collapsed": collapsed,
        }
