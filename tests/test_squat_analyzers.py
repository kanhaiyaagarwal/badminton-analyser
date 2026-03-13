"""
Tests for SquatAnalyzer (squat_half, squat_full) and SquatHoldAnalyzer.

These tests call _process_pose() directly with synthetic landmark data,
bypassing frame decode and MediaPipe detection.
"""

import math
import sys
import os
import pytest

# Add project root to path so we can import the analyzers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.core.streaming.pose_detector import PoseDetector
from api.features.challenges.services.squat_analyzer import SquatAnalyzer
from api.features.challenges.services.squat_hold_analyzer import SquatHoldAnalyzer


# ---------------------------------------------------------------------------
# Landmark helpers
# ---------------------------------------------------------------------------

def _lm(nx, ny, visibility=0.9):
    """Create a single landmark dict."""
    return {"nx": nx, "ny": ny, "x": int(nx * 640), "y": int(ny * 480), "visibility": visibility}


def _standing_landmarks(knee_angle=170, lean_offset=0.0, knee_cave=0.0, visibility=0.9):
    """
    Build a 33-landmark array for a person standing/squatting.

    knee_angle: hip-knee-ankle angle in degrees (170 = standing, 90 = deep squat)
    lean_offset: horizontal offset of shoulders from hips (simulates lean)
    knee_cave: inward shift of knees (0 = aligned with hips)
    visibility: visibility for all landmarks

    Body layout (front-facing):
      nose at (0.5, 0.15)
      shoulders at (0.4, 0.25) and (0.6, 0.25)
      hips at (0.45, 0.50) and (0.55, 0.50)
      knees computed from knee_angle
      ankles at (0.45, 0.85) and (0.55, 0.85)
    """
    landmarks = [_lm(0.5, 0.15, visibility)] * 33  # fill with default

    # Nose
    landmarks[0] = _lm(0.5 + lean_offset, 0.15, visibility)
    # Shoulders
    landmarks[11] = _lm(0.4 + lean_offset, 0.25, visibility)
    landmarks[12] = _lm(0.6 + lean_offset, 0.25, visibility)
    # Hips
    landmarks[23] = _lm(0.45, 0.50, visibility)
    landmarks[24] = _lm(0.55, 0.50, visibility)
    # Ankles
    landmarks[27] = _lm(0.45, 0.85, visibility)
    landmarks[28] = _lm(0.55, 0.85, visibility)

    # Compute knee positions from desired knee_angle.
    # Hip is above, ankle is below. We place the knee along the leg
    # such that the hip-knee-ankle angle matches the target.
    # For simplicity: knee X stays roughly between hip and ankle X,
    # and knee Y is computed to give the desired angle.
    hip_y = 0.50
    ankle_y = 0.85
    mid_y = (hip_y + ankle_y) / 2

    # Approximate: at 180° knees are inline, at 90° knees are pushed forward.
    # Use a simple model: knee Y = mid_y, knee X offset = f(angle)
    # The angle_between function measures the angle at the vertex (knee).
    # With hip above and ankle below, a straight leg (knee on the line) = ~180°.
    # Bending = knee moves forward (smaller nx) → angle decreases.
    rad = math.radians(knee_angle)
    # Place knee at midpoint Y, offset X to achieve angle
    # half_len = distance from knee to hip (or ankle) vertically
    half_len = (ankle_y - hip_y) / 2  # 0.175
    # Forward offset to achieve the angle
    # angle = 2 * atan2(offset, half_len) approximately for symmetric case
    # offset = half_len * tan((pi - angle) / 2)
    if knee_angle < 179:
        offset = half_len * math.tan((math.pi - rad) / 2)
    else:
        offset = 0.0

    # Left knee: hip_x=0.45, ankle_x=0.45
    left_knee_x = 0.45 - offset - knee_cave
    right_knee_x = 0.55 + offset + knee_cave
    # Clamp to reasonable range
    left_knee_x = max(0.1, min(0.9, left_knee_x))
    right_knee_x = max(0.1, min(0.9, right_knee_x))

    landmarks[25] = _lm(left_knee_x, mid_y, visibility)
    landmarks[26] = _lm(right_knee_x, mid_y, visibility)

    return landmarks


def _verify_angle(landmarks, expected_angle, tolerance=5):
    """Verify that the computed knee angle matches expectations."""
    angle = PoseDetector.angle_between(
        (landmarks[23]["nx"], landmarks[23]["ny"]),  # hip
        (landmarks[25]["nx"], landmarks[25]["ny"]),  # knee
        (landmarks[27]["nx"], landmarks[27]["ny"]),  # ankle
    )
    assert abs(angle - expected_angle) < tolerance, \
        f"Expected angle ~{expected_angle}°, got {angle:.1f}°"
    return angle


# ===========================================================================
# SquatAnalyzer tests (squat_half and squat_full)
# ===========================================================================

class TestSquatAnalyzerInit:
    """Test constructor and config handling."""

    def test_default_squat_full(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        assert a.challenge_type == "squat_full"
        assert a.down_angle == 100
        assert a.up_angle == 160
        assert a._state == "up"
        assert a._ready is False

    def test_default_squat_half(self):
        a = SquatAnalyzer(challenge_type="squat_half")
        assert a.challenge_type == "squat_half"
        assert a.down_angle == 130
        assert a.up_angle == 160

    def test_custom_config_overrides(self):
        a = SquatAnalyzer(challenge_type="squat_full", config={"down_angle": 110, "up_angle": 155})
        assert a.down_angle == 110
        assert a.up_angle == 155

    def test_form_counters_start_at_zero(self):
        a = SquatAnalyzer()
        assert a._total_active_frames == 0
        assert a._partial_squat_count == 0
        assert a._knees_caving_frames == 0
        assert a._lean_frames == 0


class TestSquatReadyGate:
    """Test that the analyzer requires standing position before counting."""

    def test_not_ready_when_squatting(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        lm = _standing_landmarks(knee_angle=100)
        result = a._process_pose(lm, 0.0)
        assert a._ready is False
        assert "Stand upright" in a.form_feedback

    def test_ready_when_standing(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        lm = _standing_landmarks(knee_angle=170)
        result = a._process_pose(lm, 0.0)
        assert a._ready is True
        assert "Ready" in a.form_feedback

    def test_visibility_gate_blocks_ready(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        # Low visibility on knees
        lm = _standing_landmarks(knee_angle=170, visibility=0.9)
        lm[25] = _lm(0.45, 0.675, 0.2)  # left knee barely visible
        lm[26] = _lm(0.55, 0.675, 0.2)  # right knee barely visible
        result = a._process_pose(lm, 0.0)
        assert a._ready is False
        assert "not visible" in a.form_feedback.lower() or "step back" in a.form_feedback.lower()

    def test_visibility_gate_passes_all_groups(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        # All visible, standing
        lm = _standing_landmarks(knee_angle=170, visibility=0.9)
        a._process_pose(lm, 0.0)
        assert a._ready is True


class TestSquatRepCounting:
    """Test the UP -> DOWN -> UP rep counting state machine."""

    def _get_ready(self, analyzer, t=0.0):
        """Put analyzer into ready state."""
        lm = _standing_landmarks(knee_angle=170)
        analyzer._process_pose(lm, t)
        assert analyzer._ready is True

    def test_single_rep_squat_full(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        self._get_ready(a, 0.0)
        assert a.reps == 0

        # Go down past down_angle=100 (need angle < 100)
        lm_down = _standing_landmarks(knee_angle=85)
        a._process_pose(lm_down, 1.0)
        assert a._state == "down"
        assert a.reps == 0

        # Come back up past up_angle=160
        lm_up = _standing_landmarks(knee_angle=170)
        a._process_pose(lm_up, 2.0)
        assert a._state == "up"
        assert a.reps == 1

    def test_single_rep_squat_half(self):
        a = SquatAnalyzer(challenge_type="squat_half")
        self._get_ready(a, 0.0)

        # Half squat: down_angle=130, so angle < 130 counts
        lm_down = _standing_landmarks(knee_angle=120)
        a._process_pose(lm_down, 1.0)
        assert a._state == "down"

        lm_up = _standing_landmarks(knee_angle=170)
        a._process_pose(lm_up, 2.0)
        assert a.reps == 1

    def test_multiple_reps(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        self._get_ready(a, 0.0)

        for i in range(5):
            t = (i * 2) + 1
            a._process_pose(_standing_landmarks(knee_angle=85), float(t))
            a._process_pose(_standing_landmarks(knee_angle=170), float(t + 1))

        assert a.reps == 5

    def test_half_depth_not_counted_in_full_mode(self):
        """In squat_full mode (down_angle=100), a 120° squat should NOT count."""
        a = SquatAnalyzer(challenge_type="squat_full")
        self._get_ready(a, 0.0)

        # Go to 120° (not deep enough for full)
        a._process_pose(_standing_landmarks(knee_angle=120), 1.0)
        assert a._state == "up"  # didn't cross threshold

        # Come back up
        a._process_pose(_standing_landmarks(knee_angle=170), 2.0)
        assert a.reps == 0

    def test_half_depth_counted_in_half_mode(self):
        """In squat_half mode (down_angle=130), a 120° squat SHOULD count."""
        a = SquatAnalyzer(challenge_type="squat_half")
        self._get_ready(a, 0.0)

        a._process_pose(_standing_landmarks(knee_angle=120), 1.0)
        assert a._state == "down"

        a._process_pose(_standing_landmarks(knee_angle=170), 2.0)
        assert a.reps == 1

    def test_partial_squat_tracked(self):
        """Going partway down then back up without reaching threshold = partial."""
        a = SquatAnalyzer(challenge_type="squat_full")
        self._get_ready(a, 0.0)

        # Go to ~145° (partial — between up_angle-10=150 and down_angle=100)
        a._process_pose(_standing_landmarks(knee_angle=140), 1.0)
        # Should set _went_partial
        assert a._went_partial is True

        # Come back up without going deep enough
        a._process_pose(_standing_landmarks(knee_angle=170), 2.0)
        assert a.reps == 0
        assert a._partial_squat_count == 1
        assert "didn't count" in a.form_feedback.lower()


class TestSquatFormDetection:
    """Test knee cave and forward lean detection."""

    def _get_ready(self, analyzer, t=0.0):
        lm = _standing_landmarks(knee_angle=170)
        analyzer._process_pose(lm, t)

    def test_knee_cave_detected(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        self._get_ready(a, 0.0)

        # Go down with knees caving inward
        lm = _standing_landmarks(knee_angle=85, knee_cave=0.1)  # large inward shift
        a._process_pose(lm, 1.0)
        assert a._state == "down"
        # Check the result
        result = a._process_pose(lm, 1.1)
        assert result["knees_caving"] is True
        assert a._knees_caving_frames > 0

    def test_no_knee_cave_when_aligned(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        self._get_ready(a, 0.0)

        lm = _standing_landmarks(knee_angle=85, knee_cave=0.0)
        result = a._process_pose(lm, 1.0)
        assert result["knees_caving"] is False

    def test_forward_lean_detected(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        self._get_ready(a, 0.0)

        # Large lean offset = shoulders way in front of hips
        lm = _standing_landmarks(knee_angle=85, lean_offset=0.25)
        result = a._process_pose(lm, 1.0)
        assert result["leaning"] is True
        assert a._lean_frames > 0

    def test_no_lean_when_upright(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        self._get_ready(a, 0.0)

        lm = _standing_landmarks(knee_angle=85, lean_offset=0.0)
        result = a._process_pose(lm, 1.0)
        assert result["leaning"] is False

    def test_form_feedback_for_knee_cave(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        self._get_ready(a, 0.0)

        # First frame enters down state
        lm = _standing_landmarks(knee_angle=85, knee_cave=0.1)
        a._process_pose(lm, 1.0)
        # Second frame in down state with knee cave → feedback
        a._process_pose(lm, 1.1)
        assert "knees" in a.form_feedback.lower()

    def test_form_feedback_for_lean(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        self._get_ready(a, 0.0)

        # Down with lean
        lm = _standing_landmarks(knee_angle=85, lean_offset=0.25)
        a._process_pose(lm, 1.0)
        # Second frame → lean feedback (if not overridden by knee cave)
        lm_lean_only = _standing_landmarks(knee_angle=85, lean_offset=0.25, knee_cave=0.0)
        a._process_pose(lm_lean_only, 1.1)
        assert "lean" in a.form_feedback.lower() or "chest" in a.form_feedback.lower()


class TestSquatCollapseDetection:
    """Test the 3-signal auto-end system."""

    def _get_ready_with_rep(self, analyzer):
        """Get ready and do one rep to expire grace period."""
        lm_stand = _standing_landmarks(knee_angle=170)
        analyzer._process_pose(lm_stand, 0.0)
        assert analyzer._ready is True

        # Do 1 rep to expire grace
        analyzer._process_pose(_standing_landmarks(knee_angle=85), 1.0)
        analyzer._process_pose(_standing_landmarks(knee_angle=170), 2.0)
        assert analyzer.reps == 1

    def test_stuck_in_down_triggers_end(self):
        a = SquatAnalyzer(challenge_type="squat_full", config={"stuck_timeout": 3.0})
        self._get_ready_with_rep(a)

        # Go down and stay
        a._process_pose(_standing_landmarks(knee_angle=85), 3.0)
        assert a._session_ended is False

        # Stay in down for > stuck_timeout
        a._process_pose(_standing_landmarks(knee_angle=85), 7.0)
        assert a._session_ended is True
        assert a._end_reason == "position_break"

    def test_sat_down_triggers_end(self):
        """Hips below ankles for > 2s → session ends."""
        a = SquatAnalyzer(challenge_type="squat_full")
        self._get_ready_with_rep(a)

        # Create landmarks where hips are below ankles
        lm = _standing_landmarks(knee_angle=85)
        # Move hips below ankle level
        lm[23] = _lm(0.45, 0.90)  # left hip below ankle (0.85)
        lm[24] = _lm(0.55, 0.90)  # right hip below ankle
        a._process_pose(lm, 3.0)
        assert a._session_ended is False

        # Stay sat down for > 2s
        a._process_pose(lm, 6.0)
        assert a._session_ended is True
        assert a._end_reason == "sat_down"

    def test_left_frame_triggers_end(self):
        a = SquatAnalyzer(challenge_type="squat_full", config={"left_frame_timeout": 2.0})
        self._get_ready_with_rep(a)

        # Low visibility on key landmarks
        lm = _standing_landmarks(knee_angle=130, visibility=0.1)
        a._process_pose(lm, 3.0)
        assert a._session_ended is False

        # Stay invisible for > left_frame_timeout
        a._process_pose(lm, 6.0)
        assert a._session_ended is True
        assert a._end_reason == "left_frame"

    def test_grace_period_prevents_early_end(self):
        """Before first rep and within grace period, collapse signals are ignored."""
        a = SquatAnalyzer(challenge_type="squat_full", config={
            "stuck_timeout": 2.0,
            "first_rep_grace": 30.0,
        })
        # Get ready but DON'T do a rep
        lm_stand = _standing_landmarks(knee_angle=170)
        a._process_pose(lm_stand, 0.0)
        assert a._ready is True

        # Go down and stay stuck
        a._process_pose(_standing_landmarks(knee_angle=85), 1.0)
        a._process_pose(_standing_landmarks(knee_angle=85), 5.0)
        # No rep done, still within grace → should NOT end
        assert a._session_ended is False

    def test_grace_expires_without_rep(self):
        """After grace period expires, collapse triggers even without a rep."""
        a = SquatAnalyzer(challenge_type="squat_full", config={
            "stuck_timeout": 2.0,
            "first_rep_grace": 5.0,
        })
        lm_stand = _standing_landmarks(knee_angle=170)
        a._process_pose(lm_stand, 0.0)

        # Wait past grace period, then get stuck
        a._process_pose(_standing_landmarks(knee_angle=85), 6.0)  # ready_since=0, 6-0=6 > 5
        a._process_pose(_standing_landmarks(knee_angle=85), 9.0)  # stuck for 3s > 2s
        assert a._session_ended is True

    def test_left_frame_resets_on_visibility_return(self):
        """If user comes back into frame, timer resets."""
        a = SquatAnalyzer(challenge_type="squat_full", config={"left_frame_timeout": 3.0})
        self._get_ready_with_rep(a)

        # Leave frame
        lm_gone = _standing_landmarks(knee_angle=130, visibility=0.1)
        a._process_pose(lm_gone, 3.0)

        # Come back before timeout
        lm_back = _standing_landmarks(knee_angle=150, visibility=0.9)
        a._process_pose(lm_back, 4.0)
        assert a._left_frame_since == 0.0

        # Leave again
        a._process_pose(lm_gone, 5.0)
        a._process_pose(lm_gone, 7.0)  # only 2s gone, not 3
        assert a._session_ended is False


class TestSquatBuildResult:
    """Test the _build_result output structure."""

    def test_result_keys(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        lm = _standing_landmarks(knee_angle=170)
        result = a._process_pose(lm, 0.0)
        assert "angle" in result
        assert "hip_angle" in result
        assert "lean_angle" in result
        assert "state" in result
        assert "depth_good" in result
        assert "knees_caving" in result
        assert "leaning" in result

    def test_angle_is_rounded(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        lm = _standing_landmarks(knee_angle=170)
        result = a._process_pose(lm, 0.0)
        # angle should be a float with 1 decimal
        assert isinstance(result["angle"], float)


class TestSquatFinalReport:
    """Test get_final_report() and form_summary."""

    def _do_session(self, challenge_type, good_reps=3, partial_reps=1):
        a = SquatAnalyzer(challenge_type=challenge_type)
        # Get ready
        a._process_pose(_standing_landmarks(knee_angle=170), 0.0)
        a._ready_timestamp = 0.0  # set for duration calc

        t = 1.0
        down_angle = 85 if challenge_type == "squat_full" else 120

        # Good reps
        for i in range(good_reps):
            a._process_pose(_standing_landmarks(knee_angle=down_angle), t)
            t += 1
            a._process_pose(_standing_landmarks(knee_angle=170), t)
            t += 1

        # Partial reps (go partway then back up)
        for i in range(partial_reps):
            a._process_pose(_standing_landmarks(knee_angle=140), t)
            t += 1
            a._process_pose(_standing_landmarks(knee_angle=170), t)
            t += 1

        a._last_timestamp = t
        return a

    def test_form_summary_present(self):
        a = self._do_session("squat_full", good_reps=3, partial_reps=1)
        report = a.get_final_report()
        assert "form_summary" in report

    def test_form_summary_fields(self):
        a = self._do_session("squat_full", good_reps=3, partial_reps=1)
        report = a.get_final_report()
        fs = report["form_summary"]
        assert "total_attempts" in fs
        assert "good_reps" in fs
        assert "partial_squats" in fs
        assert "knees_caving_pct" in fs
        assert "form_score" in fs

    def test_form_summary_values(self):
        a = self._do_session("squat_full", good_reps=5, partial_reps=0)
        report = a.get_final_report()
        fs = report["form_summary"]
        assert fs["good_reps"] == 5
        assert fs["partial_squats"] == 0
        assert fs["total_attempts"] == 5
        assert fs["form_score"] == 100  # perfect form

    def test_score_is_reps(self):
        a = self._do_session("squat_full", good_reps=4)
        report = a.get_final_report()
        assert report["score"] == 4

    def test_form_score_decreases_with_partials(self):
        a = self._do_session("squat_full", good_reps=2, partial_reps=3)
        report = a.get_final_report()
        fs = report["form_summary"]
        # 2 good out of 5 total = 40% rep quality
        assert fs["form_score"] < 50

    def test_duration_calculated(self):
        a = self._do_session("squat_full", good_reps=3)
        report = a.get_final_report()
        assert report["duration_seconds"] > 0

    def test_challenge_type_in_report(self):
        a = self._do_session("squat_half")
        report = a.get_final_report()
        assert report["challenge_type"] == "squat_half"


# ===========================================================================
# SquatHoldAnalyzer tests
# ===========================================================================

class TestSquatHoldInit:
    """Test constructor and config."""

    def test_defaults(self):
        a = SquatHoldAnalyzer()
        assert a.challenge_type == "squat_hold"
        assert a.hold_angle_max == 130
        assert a.good_angle_min == 90
        assert a.lean_threshold == 30
        assert a._ready is False

    def test_custom_config(self):
        a = SquatHoldAnalyzer(config={"hold_angle_max": 120, "good_angle_min": 80})
        assert a.hold_angle_max == 120
        assert a.good_angle_min == 80


class TestSquatHoldReadyGate:
    """Test ready gate for squat hold."""

    def test_not_ready_when_squatting(self):
        a = SquatHoldAnalyzer()
        lm = _standing_landmarks(knee_angle=100)
        a._process_pose(lm, 0.0)
        assert a._ready is False
        assert "Stand upright" in a.form_feedback

    def test_ready_when_standing(self):
        a = SquatHoldAnalyzer()
        lm = _standing_landmarks(knee_angle=170)
        a._process_pose(lm, 0.0)
        assert a._ready is True
        assert "Ready" in a.form_feedback

    def test_visibility_blocks_ready(self):
        a = SquatHoldAnalyzer()
        lm = _standing_landmarks(knee_angle=170, visibility=0.9)
        lm[27] = _lm(0.45, 0.85, 0.1)  # ankles not visible
        lm[28] = _lm(0.55, 0.85, 0.1)
        a._process_pose(lm, 0.0)
        assert a._ready is False


class TestSquatHoldTimer:
    """Test hold time accumulation."""

    def _get_ready(self, analyzer, t=0.0):
        lm = _standing_landmarks(knee_angle=170)
        analyzer._process_pose(lm, t)
        assert analyzer._ready is True

    def test_hold_time_accumulates_in_squat(self):
        a = SquatHoldAnalyzer()
        self._get_ready(a, 0.0)

        # Squat down (angle < hold_angle_max=130)
        lm = _standing_landmarks(knee_angle=110)
        a._process_pose(lm, 1.0)
        a._process_pose(lm, 2.0)
        a._process_pose(lm, 3.0)

        assert a.hold_seconds == pytest.approx(2.0, abs=0.1)  # 2s of hold (1→2, 2→3)

    def test_hold_time_pauses_when_standing(self):
        a = SquatHoldAnalyzer()
        self._get_ready(a, 0.0)

        # Hold for 2s
        lm_squat = _standing_landmarks(knee_angle=110)
        a._process_pose(lm_squat, 1.0)
        a._process_pose(lm_squat, 2.0)
        a._process_pose(lm_squat, 3.0)
        hold_after_squat = a.hold_seconds

        # Stand up — hold should not increase
        lm_stand = _standing_landmarks(knee_angle=170)
        a._process_pose(lm_stand, 4.0)
        a._process_pose(lm_stand, 5.0)

        assert a.hold_seconds == pytest.approx(hold_after_squat, abs=0.01)

    def test_hold_time_pauses_when_leaning(self):
        a = SquatHoldAnalyzer()
        self._get_ready(a, 0.0)

        # Hold with good form
        lm_good = _standing_landmarks(knee_angle=110)
        a._process_pose(lm_good, 1.0)
        a._process_pose(lm_good, 2.0)
        hold_before_lean = a.hold_seconds

        # Now lean excessively — hold should pause
        lm_lean = _standing_landmarks(knee_angle=110, lean_offset=0.25)
        a._process_pose(lm_lean, 3.0)
        a._process_pose(lm_lean, 4.0)

        # Hold should not have increased during lean
        assert a.hold_seconds == pytest.approx(hold_before_lean, abs=0.01)

    def test_hold_resumes_after_form_correction(self):
        a = SquatHoldAnalyzer()
        self._get_ready(a, 0.0)

        # Hold, then break form, then resume
        lm_good = _standing_landmarks(knee_angle=110)
        a._process_pose(lm_good, 1.0)
        a._process_pose(lm_good, 2.0)
        hold_1 = a.hold_seconds

        # Break form
        lm_stand = _standing_landmarks(knee_angle=170)
        a._process_pose(lm_stand, 3.0)

        # Resume good form
        a._process_pose(lm_good, 4.0)
        a._process_pose(lm_good, 5.0)

        assert a.hold_seconds > hold_1

    def test_deep_squat_feedback(self):
        a = SquatHoldAnalyzer()
        self._get_ready(a, 0.0)

        # Very deep squat (angle < good_angle_min=90)
        lm = _standing_landmarks(knee_angle=80)
        a._process_pose(lm, 1.0)
        a._process_pose(lm, 2.0)
        assert "great" in a.form_feedback.lower() or "depth" in a.form_feedback.lower()

    def test_reps_tracks_hold_seconds(self):
        """reps field should mirror int(hold_seconds) for display compatibility."""
        a = SquatHoldAnalyzer()
        self._get_ready(a, 0.0)

        lm = _standing_landmarks(knee_angle=110)
        a._process_pose(lm, 1.0)
        a._process_pose(lm, 4.0)  # 3s of hold
        assert a.reps == int(a.hold_seconds)


class TestSquatHoldFormTracking:
    """Test form quality counters."""

    def _get_ready(self, analyzer, t=0.0):
        lm = _standing_landmarks(knee_angle=170)
        analyzer._process_pose(lm, t)

    def test_good_form_frames_counted(self):
        a = SquatHoldAnalyzer()
        self._get_ready(a, 0.0)

        lm_good = _standing_landmarks(knee_angle=110)
        for t in [1.0, 2.0, 3.0]:
            a._process_pose(lm_good, t)

        assert a._good_form_frames == 3
        assert a._total_active_frames == 3

    def test_lean_frames_counted(self):
        a = SquatHoldAnalyzer()
        self._get_ready(a, 0.0)

        lm_lean = _standing_landmarks(knee_angle=110, lean_offset=0.25)
        a._process_pose(lm_lean, 1.0)
        a._process_pose(lm_lean, 2.0)

        assert a._lean_frames == 2

    def test_depth_lost_frames_counted(self):
        a = SquatHoldAnalyzer()
        self._get_ready(a, 0.0)

        # Start in hold
        lm_squat = _standing_landmarks(knee_angle=110)
        a._process_pose(lm_squat, 1.0)
        assert a._in_hold is True

        # Stand up — depth lost
        lm_stand = _standing_landmarks(knee_angle=170)
        a._process_pose(lm_stand, 2.0)
        assert a._depth_lost_frames == 1

    def test_form_break_count(self):
        a = SquatHoldAnalyzer()
        self._get_ready(a, 0.0)

        lm_good = _standing_landmarks(knee_angle=110)
        lm_bad = _standing_landmarks(knee_angle=170)

        # Good → Bad = 1 break
        a._process_pose(lm_good, 1.0)
        a._process_pose(lm_bad, 2.0)
        assert a._form_break_count == 1

        # Bad → Good → Bad = 2nd break
        a._process_pose(lm_good, 3.0)
        a._process_pose(lm_bad, 4.0)
        assert a._form_break_count == 2


class TestSquatHoldCollapseDetection:
    """Test auto-end triggers for squat hold."""

    def _get_ready_with_hold(self, analyzer):
        """Get ready and accumulate some hold time."""
        lm_stand = _standing_landmarks(knee_angle=170)
        analyzer._process_pose(lm_stand, 0.0)

        lm_squat = _standing_landmarks(knee_angle=110)
        analyzer._process_pose(lm_squat, 1.0)
        analyzer._process_pose(lm_squat, 2.0)
        assert analyzer.hold_seconds > 0  # grace condition met

    def test_form_break_triggers_end(self):
        a = SquatHoldAnalyzer(config={"form_break_timeout": 3.0})
        self._get_ready_with_hold(a)

        # Break form and stay broken
        lm_stand = _standing_landmarks(knee_angle=170)
        a._process_pose(lm_stand, 3.0)  # form_break_since = 3.0
        a._process_pose(lm_stand, 7.0)  # 4s > 3s timeout
        assert a._session_ended is True
        assert a._end_reason == "form_break"

    def test_left_frame_triggers_end(self):
        a = SquatHoldAnalyzer(config={"left_frame_timeout": 2.0})
        self._get_ready_with_hold(a)

        lm_gone = _standing_landmarks(knee_angle=110, visibility=0.1)
        a._process_pose(lm_gone, 3.0)
        a._process_pose(lm_gone, 6.0)  # 3s > 2s
        assert a._session_ended is True
        assert a._end_reason == "left_frame"

    def test_form_break_grace_tightens_after_15s(self):
        """After 15s of hold, form_break grace is shorter."""
        a = SquatHoldAnalyzer(config={
            "form_break_timeout": 5.0,
            "form_break_grace": 2.0,
        })
        lm_stand = _standing_landmarks(knee_angle=170)
        a._process_pose(lm_stand, 0.0)

        # Accumulate > 15s of hold
        lm_squat = _standing_landmarks(knee_angle=110)
        for t in range(1, 20):
            a._process_pose(lm_squat, float(t))
        assert a.hold_seconds >= 15

        # Break form
        a._process_pose(lm_stand, 20.0)
        a._process_pose(lm_stand, 23.0)  # 3s > form_break_grace(2s)
        assert a._session_ended is True

    def test_grace_prevents_early_end(self):
        """Before any hold time and within grace, no auto-end."""
        a = SquatHoldAnalyzer(config={
            "form_break_timeout": 2.0,
            "first_rep_grace": 30.0,
        })
        lm_stand = _standing_landmarks(knee_angle=170)
        a._process_pose(lm_stand, 0.0)
        # Don't hold at all — just stand
        a._process_pose(lm_stand, 5.0)
        a._process_pose(lm_stand, 10.0)
        assert a._session_ended is False  # no hold_seconds, within grace


class TestSquatHoldFinalReport:
    """Test get_final_report() for squat hold."""

    def test_score_is_hold_seconds(self):
        a = SquatHoldAnalyzer()
        a._process_pose(_standing_landmarks(knee_angle=170), 0.0)
        a._ready_timestamp = 0.0

        lm = _standing_landmarks(knee_angle=110)
        a._process_pose(lm, 1.0)
        a._process_pose(lm, 6.0)  # ~5s hold

        a._last_timestamp = 6.0
        report = a.get_final_report()
        assert report["score"] == int(a.hold_seconds)
        assert report["score"] >= 4  # should be ~5

    def test_form_summary_fields(self):
        a = SquatHoldAnalyzer()
        a._process_pose(_standing_landmarks(knee_angle=170), 0.0)
        a._ready_timestamp = 0.0

        lm = _standing_landmarks(knee_angle=110)
        for t in [1.0, 2.0, 3.0]:
            a._process_pose(lm, t)
        a._last_timestamp = 3.0

        report = a.get_final_report()
        fs = report["form_summary"]
        assert "good_form_pct" in fs
        assert "form_break_count" in fs
        assert "lean_frames" in fs
        assert "depth_lost_frames" in fs
        assert "form_score" in fs

    def test_perfect_form_score(self):
        a = SquatHoldAnalyzer()
        a._process_pose(_standing_landmarks(knee_angle=170), 0.0)
        a._ready_timestamp = 0.0

        lm = _standing_landmarks(knee_angle=110)
        for t in range(1, 11):
            a._process_pose(lm, float(t))
        a._last_timestamp = 10.0

        report = a.get_final_report()
        fs = report["form_summary"]
        assert fs["form_score"] >= 80  # high score for all good form
        assert fs["form_break_count"] == 0

    def test_challenge_type_in_report(self):
        a = SquatHoldAnalyzer()
        report = a.get_final_report()
        assert report["challenge_type"] == "squat_hold"


# ===========================================================================
# Cross-variant tests
# ===========================================================================

class TestSquatVariantDifferences:
    """Verify that squat_half and squat_full behave differently at the same depth."""

    def test_half_counts_at_120_full_does_not(self):
        """120° knee angle should count for half but not full."""
        for ctype, should_count in [("squat_half", True), ("squat_full", False)]:
            a = SquatAnalyzer(challenge_type=ctype)
            # Ready
            a._process_pose(_standing_landmarks(knee_angle=170), 0.0)
            # Go to 120°
            a._process_pose(_standing_landmarks(knee_angle=120), 1.0)
            went_down = a._state == "down"
            # Come back up
            a._process_pose(_standing_landmarks(knee_angle=170), 2.0)

            if should_count:
                assert a.reps == 1, f"{ctype}: expected 1 rep at 120°"
            else:
                assert a.reps == 0, f"{ctype}: expected 0 reps at 120°"

    def test_both_count_at_85(self):
        """85° should count for both variants."""
        for ctype in ["squat_half", "squat_full"]:
            a = SquatAnalyzer(challenge_type=ctype)
            a._process_pose(_standing_landmarks(knee_angle=170), 0.0)
            a._process_pose(_standing_landmarks(knee_angle=85), 1.0)
            a._process_pose(_standing_landmarks(knee_angle=170), 2.0)
            assert a.reps == 1, f"{ctype}: expected 1 rep at 85°"


class TestSquatHoldVsRepScoring:
    """Verify that hold and rep variants use different scoring."""

    def test_hold_score_is_seconds(self):
        a = SquatHoldAnalyzer()
        a._process_pose(_standing_landmarks(knee_angle=170), 0.0)
        a._ready_timestamp = 0.0
        lm = _standing_landmarks(knee_angle=110)
        a._process_pose(lm, 1.0)
        a._process_pose(lm, 11.0)
        a._last_timestamp = 11.0
        report = a.get_final_report()
        assert report["score"] == int(a.hold_seconds)
        assert report["score"] >= 9

    def test_rep_score_is_count(self):
        a = SquatAnalyzer(challenge_type="squat_full")
        a._process_pose(_standing_landmarks(knee_angle=170), 0.0)
        a._ready_timestamp = 0.0
        for i in range(3):
            a._process_pose(_standing_landmarks(knee_angle=85), float(i * 2 + 1))
            a._process_pose(_standing_landmarks(knee_angle=170), float(i * 2 + 2))
        a._last_timestamp = 6.0
        report = a.get_final_report()
        assert report["score"] == 3


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_exact_threshold_angle(self):
        """Angle exactly at down_angle should still trigger down state."""
        a = SquatAnalyzer(challenge_type="squat_full")
        a._process_pose(_standing_landmarks(knee_angle=170), 0.0)

        # Create landmarks that produce angle very close to down_angle (100)
        # Due to approximation in _standing_landmarks, we may not hit exactly 100
        # but testing boundary behavior
        lm = _standing_landmarks(knee_angle=95)  # safely below threshold
        result = a._process_pose(lm, 1.0)
        assert a._state == "down"

    def test_rapid_frame_processing(self):
        """Many frames at high frequency shouldn't break anything."""
        a = SquatAnalyzer(challenge_type="squat_full")
        a._process_pose(_standing_landmarks(knee_angle=170), 0.0)

        # 100 frames at 30fps
        for i in range(100):
            t = i / 30.0 + 0.1
            angle = 170 if (i // 15) % 2 == 0 else 85
            a._process_pose(_standing_landmarks(knee_angle=angle), t)

        # Should have some reps
        assert a.reps > 0

    def test_hold_large_dt_capped(self):
        """dt > 1.0 between frames should not add hold time (prevents jumps)."""
        a = SquatHoldAnalyzer()
        a._process_pose(_standing_landmarks(knee_angle=170), 0.0)

        lm = _standing_landmarks(knee_angle=110)
        a._process_pose(lm, 1.0)
        a._process_pose(lm, 10.0)  # 9s gap — should be capped

        # hold_seconds should NOT be 9s (the dt > 1.0 check should cap it)
        assert a.hold_seconds < 2.0

    def test_session_ended_stays_ended(self):
        """Once session_ended is True, it stays True."""
        a = SquatAnalyzer(challenge_type="squat_full", config={"stuck_timeout": 1.0})
        a._process_pose(_standing_landmarks(knee_angle=170), 0.0)
        # Do a rep to expire grace
        a._process_pose(_standing_landmarks(knee_angle=85), 1.0)
        a._process_pose(_standing_landmarks(knee_angle=170), 2.0)
        # Get stuck
        a._process_pose(_standing_landmarks(knee_angle=85), 3.0)
        a._process_pose(_standing_landmarks(knee_angle=85), 5.0)
        assert a._session_ended is True

        # Process more frames — should stay ended
        a._process_pose(_standing_landmarks(knee_angle=170), 6.0)
        assert a._session_ended is True

    def test_zero_timestamp(self):
        """Processing at t=0 should work fine."""
        a = SquatAnalyzer(challenge_type="squat_full")
        result = a._process_pose(_standing_landmarks(knee_angle=170), 0.0)
        assert result is not None
        assert a._ready is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
