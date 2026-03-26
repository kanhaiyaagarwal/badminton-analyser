"""
Shot classification engine.

Consumes raw per-frame data (pose history + shuttle history) and produces
classified results: shots, rallies, shuttle hits, timeline.

This is the classification layer — separate from the detection models
(MediaPipe Pose, TrackNetV2) which only produce raw data.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def detect_shuttle_hits_windowed(
    raw_frames: List[dict],
    fps: float,
    disp_window: int = 15,
    speed_window: int = 8,
    break_window: int = 12,
    hit_threshold: float = 0.15,
    cooldown_frames: int = 25,
    norm_percentile: int = 90,
    gate_min: float = 0.03,
    wrist_bonus: float = 0.10,
    wrist_window: int = 8,
    # Legacy params accepted but ignored for backwards compatibility
    window: int = 30,
    direction_pct: float = 80.0,
    min_speed: float = 80.0,
) -> List[dict]:
    """Detect shuttle hits using multi-signal trajectory analysis.

    Combines three shuttle trajectory signals with optional wrist velocity
    bonus:
      A) Large-window displacement cosine (trajectory reversal)  — weight 0.30
      B) Speed ratio (abrupt speed change)                       — weight 0.40
      C) Trajectory break (prediction error from fitted path)    — weight 0.30
      D) Wrist velocity bonus (when pose data available)

    Signal gating: frames where fewer than 2 of the 3 shuttle signals
    are active (above gate_min) are suppressed to reduce false positives.

    Args:
        raw_frames: Per-frame data with shuttle x/y/visible and optional
            wrist_velocity.
        fps: Video FPS.
        disp_window: Frame window for displacement cosine signal.
        speed_window: Frame window for speed ratio signal.
        break_window: Frame window for trajectory break signal.
        hit_threshold: Combined score threshold.
        cooldown_frames: NMS cooldown between hits (frames).
        norm_percentile: Percentile for signal normalization (e.g. 90 or 95).
        gate_min: Minimum normalized signal value to count as "active"
            for the ≥2-signal gating rule. 0 disables gating.
        wrist_bonus: Weight for wrist velocity bonus signal. 0 disables.
        wrist_window: Half-window for wrist velocity max pooling (frames).

    Returns:
        List of hit dicts compatible with _match_shots_with_shuttle_hits().
    """
    import numpy as np

    n = len(raw_frames)
    if n == 0:
        return []

    # --- Step 0: Build clean position arrays ---
    raw_x = np.full(n, np.nan)
    raw_y = np.full(n, np.nan)
    has_pos = np.zeros(n, dtype=bool)

    for i, frame in enumerate(raw_frames):
        shuttle = frame.get("shuttle")
        if shuttle and shuttle.get("visible") and shuttle.get("x") is not None:
            raw_x[i] = shuttle["x"]
            raw_y[i] = shuttle["y"]
            has_pos[i] = True

    # Interpolate gaps up to 5 frames
    interp_x = raw_x.copy()
    interp_y = raw_y.copy()
    valid = has_pos.copy()
    MAX_GAP = 5
    gap_start = -1
    for i in range(n):
        if has_pos[i]:
            if gap_start >= 0 and gap_start > 0 and has_pos[gap_start - 1]:
                gap_len = i - gap_start
                if gap_len <= MAX_GAP:
                    prev_i = gap_start - 1
                    for g in range(gap_start, i):
                        t = (g - prev_i) / (i - prev_i)
                        interp_x[g] = raw_x[prev_i] + t * (raw_x[i] - raw_x[prev_i])
                        interp_y[g] = raw_y[prev_i] + t * (raw_y[i] - raw_y[prev_i])
                        valid[g] = True
            gap_start = -1
        else:
            if gap_start < 0:
                gap_start = i

    # Median-smooth with window=3
    smooth_x = np.full(n, np.nan)
    smooth_y = np.full(n, np.nan)
    for i in range(n):
        if not valid[i]:
            continue
        x_vals = []
        y_vals = []
        for d in range(-1, 2):
            j = i + d
            if 0 <= j < n and valid[j]:
                x_vals.append(interp_x[j])
                y_vals.append(interp_y[j])
        x_vals.sort()
        y_vals.sort()
        mid = len(x_vals) // 2
        smooth_x[i] = x_vals[mid]
        smooth_y[i] = y_vals[mid]

    # Compute velocity: v[i] = (pos[i] - pos[i-2]) / 2
    vx = np.zeros(n)
    vy = np.zeros(n)
    speed = np.zeros(n)
    for i in range(2, n):
        if not valid[i] or not valid[i - 2]:
            continue
        vx[i] = (smooth_x[i] - smooth_x[i - 2]) / 2.0
        vy[i] = (smooth_y[i] - smooth_y[i - 2]) / 2.0
        speed[i] = math.sqrt(vx[i] ** 2 + vy[i] ** 2)

    # --- Step 1: Signal A — Large-window net displacement cosine ---
    signal_a = np.zeros(n)
    min_span = max(1, disp_window // 3)
    for i in range(n):
        # Before window: first/last valid in [i-disp_window, i]
        b_first = b_last = -1
        for j in range(max(0, i - disp_window), i + 1):
            if valid[j]:
                if b_first < 0:
                    b_first = j
                b_last = j
        # After window: first/last valid in [i, i+disp_window]
        a_first = a_last = -1
        for j in range(i, min(n, i + disp_window + 1)):
            if valid[j]:
                if a_first < 0:
                    a_first = j
                a_last = j

        if b_first < 0 or a_first < 0:
            continue
        if (b_last - b_first) < min_span or (a_last - a_first) < min_span:
            continue

        b_dx = smooth_x[b_last] - smooth_x[b_first]
        b_dy = smooth_y[b_last] - smooth_y[b_first]
        a_dx = smooth_x[a_last] - smooth_x[a_first]
        a_dy = smooth_y[a_last] - smooth_y[a_first]

        b_mag = math.sqrt(b_dx ** 2 + b_dy ** 2)
        a_mag = math.sqrt(a_dx ** 2 + a_dy ** 2)
        if b_mag < 1e-6 or a_mag < 1e-6:
            continue

        cos_sim = (b_dx * a_dx + b_dy * a_dy) / (b_mag * a_mag)
        signal_a[i] = max(0.0, -cos_sim)

    # --- Step 2: Signal B — Speed ratio ---
    signal_b = np.zeros(n)
    for i in range(n):
        before_sum = before_cnt = 0.0
        for j in range(max(0, i - speed_window), i + 1):
            if speed[j] > 0:
                before_sum += speed[j]
                before_cnt += 1
        after_sum = after_cnt = 0.0
        for j in range(i + 1, min(n, i + speed_window + 1)):
            if speed[j] > 0:
                after_sum += speed[j]
                after_cnt += 1
        if before_cnt == 0 or after_cnt == 0:
            continue
        before_avg = before_sum / before_cnt
        after_avg = after_sum / after_cnt
        if before_avg < 1e-6 or after_avg < 1e-6:
            continue
        ratio = max(after_avg / before_avg, before_avg / after_avg)
        signal_b[i] = ratio - 1.0

    # --- Step 3: Signal C — Trajectory break / prediction error ---
    signal_c = np.zeros(n)
    K = 5  # prediction horizon
    for i in range(break_window, n - K):
        # Collect positions in [i-break_window, i]
        ts = []
        xs = []
        ys = []
        for j in range(i - break_window, i + 1):
            if valid[j]:
                ts.append(float(j))
                xs.append(smooth_x[j])
                ys.append(smooth_y[j])
        if len(ts) < 3:
            continue

        t_arr = np.array(ts)
        x_arr = np.array(xs)
        y_arr = np.array(ys)

        # Fit linear x(t): x = a*t + b
        try:
            x_coeffs = np.polyfit(t_arr, x_arr, 1)  # [a, b]
        except (np.linalg.LinAlgError, ValueError):
            continue

        # Fit quadratic y(t): y = a*t^2 + b*t + c
        try:
            y_coeffs = np.polyfit(t_arr, y_arr, 2)  # [a, b, c]
        except (np.linalg.LinAlgError, ValueError):
            continue

        # Predict positions at [i+1 ... i+K] and compute avg error
        err_sum = 0.0
        err_cnt = 0
        for k in range(1, K + 1):
            t = float(i + k)
            if i + k >= n or not valid[i + k]:
                continue
            pred_x = x_coeffs[0] * t + x_coeffs[1]
            pred_y = y_coeffs[0] * t * t + y_coeffs[1] * t + y_coeffs[2]
            dx = smooth_x[i + k] - pred_x
            dy = smooth_y[i + k] - pred_y
            err_sum += math.sqrt(dx ** 2 + dy ** 2)
            err_cnt += 1
        if err_cnt > 0:
            signal_c[i] = err_sum / err_cnt

    # --- Step 4: Normalize and combine ---
    def _normalize(arr: np.ndarray, pct: int) -> np.ndarray:
        pos = arr[arr > 0]
        if len(pos) == 0:
            return np.zeros_like(arr)
        pval = float(np.percentile(pos, pct))
        if pval < 1e-12:
            return np.zeros_like(arr)
        return np.clip(arr / pval, 0.0, 1.0)

    norm_a = _normalize(signal_a, norm_percentile)
    norm_b = _normalize(signal_b, norm_percentile)
    norm_c = _normalize(signal_c, norm_percentile)

    combined = 0.30 * norm_a + 0.40 * norm_b + 0.30 * norm_c

    # Signal gating: require ≥2 of 3 shuttle signals to be active
    if gate_min > 0:
        for i in range(n):
            active = (
                (1 if norm_a[i] > gate_min else 0) +
                (1 if norm_b[i] > gate_min else 0) +
                (1 if norm_c[i] > gate_min else 0)
            )
            if active < 2:
                combined[i] = 0.0

    # Wrist velocity bonus: boost combined score near wrist spikes
    if wrist_bonus > 0:
        wrist_vel = np.zeros(n)
        for i, frame in enumerate(raw_frames):
            wv = frame.get("wrist_velocity")
            if wv is not None and wv > 0:
                wrist_vel[i] = wv
        if np.any(wrist_vel > 0):
            norm_wv = _normalize(wrist_vel, 95)
            # Max-pool over ±wrist_window to account for timing offset
            wv_pooled = np.zeros(n)
            for i in range(n):
                lo = max(0, i - wrist_window)
                hi = min(n, i + wrist_window + 1)
                wv_pooled[i] = norm_wv[lo:hi].max()
            combined = combined + wrist_bonus * wv_pooled

    # --- Step 5: Peak detection with NMS ---
    candidates = []
    for i in range(n):
        if combined[i] >= hit_threshold:
            candidates.append((i, float(combined[i])))
    # Sort by score descending
    candidates.sort(key=lambda c: -c[1])

    suppressed = set()
    hits_indices: List[Tuple[int, float]] = []
    for idx, score in candidates:
        if idx in suppressed:
            continue
        hits_indices.append((idx, score))
        for j in range(max(0, idx - cooldown_frames), min(n, idx + cooldown_frames + 1)):
            suppressed.add(j)

    # Build output in frame order
    hits_indices.sort(key=lambda h: h[0])

    result: List[dict] = []
    for idx, score in hits_indices:
        frame = raw_frames[idx]
        shuttle = frame.get("shuttle") or {}
        speed_after = _compute_shuttle_speed_from_frames(
            raw_frames, frame.get("frame_number", idx), fps
        )
        result.append({
            "frame": frame.get("frame_number", idx),
            "timestamp": frame.get("timestamp", 0),
            "hit_position": {
                "x": shuttle.get("x"),
                "y": shuttle.get("y"),
            },
            "speed_px_per_sec": round(speed_after, 1) if speed_after else None,
            "direction_before": None,
            "direction_after": None,
            "confidence": round(score, 3),
            "reversal_type": "multi_signal",
        })

    return result


def _compute_shuttle_speed_from_frames(
    raw_frames: List[dict], hit_frame: int, fps: float, n_frames: int = 10
) -> Optional[float]:
    """Compute avg shuttle speed (px/sec) over next n detected frames after a hit."""
    after_hit = [
        f for f in raw_frames
        if f.get("frame_number", 0) > hit_frame
        and f.get("shuttle") and f["shuttle"].get("visible")
    ][:n_frames]

    if len(after_hit) < 2:
        return None

    speeds = []
    for i in range(1, len(after_hit)):
        dt = after_hit[i]["timestamp"] - after_hit[i - 1]["timestamp"]
        if dt <= 0:
            continue
        dx = after_hit[i]["shuttle"]["x"] - after_hit[i - 1]["shuttle"]["x"]
        dy = after_hit[i]["shuttle"]["y"] - after_hit[i - 1]["shuttle"]["y"]
        speed = math.sqrt(dx ** 2 + dy ** 2) / dt
        speeds.append(speed)

    return sum(speeds) / len(speeds) if speeds else None


def detect_shuttle_hits_windowed_tuning(
    frames: List[dict],
    fps: float,
    disp_window: int = 15,
    speed_window: int = 8,
    break_window: int = 12,
    hit_threshold: float = 0.15,
    cooldown_frames: int = 25,
    norm_percentile: int = 90,
    gate_min: float = 0.03,
    wrist_bonus: float = 0.10,
    wrist_window: int = 8,
    # Legacy params accepted for backwards compatibility
    window: int = 30,
    direction_pct: float = 80.0,
    min_speed: float = 80.0,
) -> List[dict]:
    """Multi-signal hit detection for tuning-format frames (flat shuttle_x/y/visible).

    Converts flat frame format to raw_frames format and delegates to
    detect_shuttle_hits_windowed().
    """
    raw_frames = []
    for f in frames:
        visible = f.get("shuttle_visible", False)
        entry: dict = {
            "frame_number": f.get("frame_number", 0),
            "timestamp": f.get("timestamp", 0),
            "shuttle": {
                "x": f.get("shuttle_x"),
                "y": f.get("shuttle_y"),
                "visible": visible,
            } if visible and f.get("shuttle_x") is not None else None,
        }
        # Pass through wrist velocity for co-detection bonus
        wv = f.get("wrist_velocity")
        if wv is not None:
            entry["wrist_velocity"] = wv
        raw_frames.append(entry)

    return detect_shuttle_hits_windowed(
        raw_frames, fps,
        disp_window=disp_window,
        speed_window=speed_window,
        break_window=break_window,
        hit_threshold=hit_threshold,
        cooldown_frames=cooldown_frames,
        norm_percentile=norm_percentile,
        gate_min=gate_min,
        wrist_bonus=wrist_bonus,
        wrist_window=wrist_window,
    )


class ShotClassifier:
    """Classifies shots using accumulated pose + shuttle raw data."""

    ACTUAL_SHOTS = ['smash', 'clear', 'drop_shot', 'net_shot', 'drive', 'lift']
    NON_SHOT_STATES = ['static', 'ready_position', 'preparation', 'follow_through']

    DEFAULT_VELOCITY_THRESHOLDS = {
        'static': 0.9,
        'movement': 0.75,
        'power_overhead': 1.8,
        'gentle_overhead': 1.2,
        'drive': 1.5,
        'net_min': 0.9,
        'net_max': 3.6,
        'lift': 1.2,
        'smash_vs_clear': 2.4,
        'drop_min': 0.8,
    }

    DEFAULT_POSITION_THRESHOLDS = {
        'overhead_offset': 0.08,
        'low_position_offset': 0.1,
        'arm_extension_min': 0.15,
    }

    DEFAULT_WINDOW_THRESHOLDS = {
        'overhead_offset_window': 0.03,  # wrist-above-shoulder offset for window
        'overhead_pct_min': 0.15,        # min % overhead frames for smash/clear/drop
        'net_height_max': 0.18,          # max avg_wrist_y for net shot
        'net_body_max': 0.25,            # max avg_hip_y for net shot (body low = lunging)
        'lift_hip_min': 0.42,            # avg_hip_y above this → lift (deep crouch)
        'lift_hip_secondary': 0.35,      # secondary hip threshold (with gap + wrist checks)
        'lift_gap_max': 0.08,            # max wrist-hip gap for secondary lift
        'lift_wrist_min': 0.28,          # min avg_wrist_y for secondary lift
    }

    def __init__(
        self,
        velocity_thresholds: Optional[Dict[str, float]] = None,
        position_thresholds: Optional[Dict[str, float]] = None,
        window_thresholds: Optional[Dict[str, float]] = None,
        shot_cooldown_seconds: float = 0.4,
        effective_fps: float = 30.0,
        rally_gap_seconds: float = 3.0,
        shuttle_gap_frames: int = 45,
        shuttle_gap_miss_pct: float = 80.0,
        hit_disp_window: int = 15,
        hit_speed_window: int = 8,
        hit_break_window: int = 12,
        hit_threshold: float = 0.15,
        hit_cooldown: int = 25,
        hit_norm_percentile: int = 90,
        hit_gate_min: float = 0.03,
        hit_wrist_bonus: float = 0.10,
        hit_wrist_window: int = 8,
        # Hit-centric: how many frames to look back from each hit
        attribution_window: int = 15,
        # Legacy params accepted for backwards compatibility
        shuttle_hit_window: int = 30,
        shuttle_hit_direction_pct: float = 80.0,
        shuttle_hit_cooldown: int = 15,
        shuttle_hit_min_speed: float = 80.0,
        court_center: Optional[List[int]] = None,
    ):
        self.T = {**self.DEFAULT_VELOCITY_THRESHOLDS, **(velocity_thresholds or {})}
        self.P = {**self.DEFAULT_POSITION_THRESHOLDS, **(position_thresholds or {})}
        self.W = {**self.DEFAULT_WINDOW_THRESHOLDS, **(window_thresholds or {})}
        self.court_center = court_center
        self.shot_cooldown_seconds = shot_cooldown_seconds
        self.effective_fps = effective_fps
        self.rally_gap_seconds = rally_gap_seconds
        self.shuttle_gap_frames = shuttle_gap_frames
        self.shuttle_gap_miss_pct = shuttle_gap_miss_pct
        self.hit_disp_window = hit_disp_window
        self.hit_speed_window = hit_speed_window
        self.hit_break_window = hit_break_window
        self.hit_threshold = hit_threshold
        self.hit_cooldown = hit_cooldown
        self.hit_norm_percentile = hit_norm_percentile
        self.hit_gate_min = hit_gate_min
        self.hit_wrist_bonus = hit_wrist_bonus
        self.hit_wrist_window = hit_wrist_window
        # Hit-centric lookback
        self.attribution_window = attribution_window

    def classify_all(self, raw_frame_data: List[dict], fps: float) -> dict:
        """
        Process all raw frame data and produce classified results.

        Input: list of per-frame raw data dicts:
            {
                frame_number, timestamp,
                pose_landmarks (not stored — already consumed into pose_state),
                pose_state: {wrist, elbow, shoulder, shoulder_center, hip_center},
                shuttle: {x, y, confidence, visible},
                player_detected, player_bbox, foot_position
            }

        Output: {
            shots, rallies, shuttle_hits, shot_timeline, summary,
            shot_distribution
        }
        """
        # Phase 1: Compute velocities from pose state history
        velocity_data = self._compute_velocities(raw_frame_data)

        # Inject wrist_velocity into raw frames for shuttle hit co-detection
        for i, frame in enumerate(raw_frame_data):
            vel_info = velocity_data[i] if i < len(velocity_data) else {}
            if vel_info and "wrist_velocity" in vel_info:
                frame["wrist_velocity"] = vel_info["wrist_velocity"]

        # Phase 2: Detect shuttle hits (arc direction changes)
        shuttle_hits = self._detect_shuttle_hits(raw_frame_data, fps)

        # Phase 3: Choose classification path
        has_shuttle = len(shuttle_hits) > 0

        if has_shuttle:
            # Hit-centric: for each shuttle hit, look back at player movement
            enriched_shots = self._classify_hits_centric(
                raw_frame_data, shuttle_hits, velocity_data, fps
            )
            session_stats: Dict[str, int] = {}
            player_stats: Dict[str, int] = {}
            opponent_count = 0
            for s in enriched_shots:
                st = s["shot_type"]
                if s.get("hit_by") == "opponent":
                    opponent_count += 1
                elif st in self.ACTUAL_SHOTS:
                    session_stats[st] = session_stats.get(st, 0) + 1
                    player_stats[st] = player_stats.get(st, 0) + 1
            session_stats["opponent"] = opponent_count
        else:
            # Legacy: per-frame classify + match
            shots = []
            last_shot_timestamp = -999.0
            session_stats = {}

            for i, frame in enumerate(raw_frame_data):
                if not frame.get("player_detected"):
                    continue

                vel_info = velocity_data[i] if i < len(velocity_data) else {}
                if not vel_info:
                    continue

                pose_state = frame.get("pose_state")
                if not pose_state:
                    continue

                swing_type = self._classify_swing(
                    vel_info["wrist_velocity"],
                    vel_info["wrist_direction"],
                    pose_state,
                    vel_info.get("wrist_dy_per_sec", 0),
                    vel_info.get("pose_history_window", []),
                )

                shot_type, confidence = self._classify_shot(swing_type, vel_info["wrist_velocity"])

                timestamp = frame["timestamp"]
                if shot_type in self.ACTUAL_SHOTS and confidence > 0.5:
                    if timestamp - last_shot_timestamp < self.shot_cooldown_seconds:
                        shot_type = 'follow_through'
                        confidence = 0.3
                    else:
                        last_shot_timestamp = timestamp

                if shot_type in self.ACTUAL_SHOTS and confidence > 0.5:
                    session_stats[shot_type] = session_stats.get(shot_type, 0) + 1
                    shots.append({
                        "frame": frame["frame_number"],
                        "timestamp": timestamp,
                        "shot_type": shot_type,
                        "confidence": round(confidence, 3),
                        "swing_type": swing_type,
                        "wrist_velocity": round(vel_info["wrist_velocity"], 3),
                    })

            enriched_shots = self._match_shots_with_shuttle_hits(shots, shuttle_hits)

        # Phase 5: Build rallies
        # Use shuttle-based rally detection when shuttle data is available,
        # fall back to pose-based (shot time gaps) otherwise.
        has_shuttle = any(f.get("shuttle") is not None for f in raw_frame_data)
        pose_rallies = self._build_rallies(enriched_shots, fps)
        gap_zones: List[dict] = []

        if has_shuttle:
            shuttle_result = self._build_shuttle_rallies(raw_frame_data, fps)
            rallies = shuttle_result["rallies"]
            gap_zones = shuttle_result["gap_zones"]
        else:
            rallies = pose_rallies

        # Phase 6: Suppress shots that fall inside gap zones
        if gap_zones:
            gap_frame_set = set()
            for gz in gap_zones:
                for idx in range(gz["start_idx"], gz["end_idx"] + 1):
                    if idx < len(raw_frame_data):
                        gap_frame_set.add(raw_frame_data[idx].get("frame_number"))
            enriched_shots = [
                s for s in enriched_shots
                if s["frame"] not in gap_frame_set
            ]

        # Phase 7: Enrich shuttle rallies with shot + hit data
        if has_shuttle and rallies:
            for rally in rallies:
                r_start = rally["start_time"]
                r_end = rally["end_time"]
                rally_shots = [
                    s["shot_type"] for s in enriched_shots
                    if r_start <= s["timestamp"] <= r_end
                ]
                rally["shots"] = rally_shots
                rally["shot_count"] = len(rally_shots)
                # Associate shuttle hits (actual exchanges) with rally
                rally_hits = [
                    h for h in shuttle_hits
                    if r_start <= h["timestamp"] <= r_end
                ]
                rally["hit_count"] = len(rally_hits)
                # Tighter duration based on first-to-last hit
                if len(rally_hits) >= 2:
                    rally["rally_duration"] = round(
                        rally_hits[-1]["timestamp"] - rally_hits[0]["timestamp"], 2
                    )
                elif len(rally_hits) == 1:
                    rally["rally_duration"] = 0.0
                else:
                    rally["rally_duration"] = rally["duration"]

        # Build timeline
        shot_timeline = []
        for s in enriched_shots:
            entry = {
                "time": s["timestamp"],
                "shot": s["shot_type"],
                "confidence": s["confidence"],
            }
            if s.get("shuttle_speed_px_per_sec") is not None:
                entry["shuttle_speed_px_per_sec"] = s["shuttle_speed_px_per_sec"]
            if s.get("shuttle_hit_matched"):
                entry["shuttle_hit_matched"] = True
            shot_timeline.append(entry)

        # Summary
        total_frames = len(raw_frame_data)
        player_detected_frames = sum(1 for f in raw_frame_data if f.get("player_detected"))
        shuttle_detected_frames = sum(
            1 for f in raw_frame_data
            if f.get("shuttle") and f["shuttle"].get("visible")
        )

        # Per-player shot counts
        player_shots = [s for s in enriched_shots if s.get("hit_by") == "player"]
        opponent_shots = [s for s in enriched_shots if s.get("hit_by") == "opponent"]
        forehand_shots = sum(1 for s in enriched_shots if s.get("stroke_side") == "forehand")
        backhand_shots = sum(1 for s in enriched_shots if s.get("stroke_side") == "backhand")

        summary = {
            "total_shots": len(enriched_shots),
            "player_shots": len(player_shots),
            "opponent_shots": len(opponent_shots),
            "forehand_shots": forehand_shots,
            "backhand_shots": backhand_shots,
            "total_rallies": len(rallies),
            "frames_processed": total_frames,
            "player_detection_rate": (
                player_detected_frames / total_frames if total_frames > 0 else 0
            ),
            "avg_confidence": (
                sum(s["confidence"] for s in player_shots) / len(player_shots)
                if player_shots else 0
            ),
            "shuttle_detection_rate": (
                shuttle_detected_frames / total_frames if total_frames > 0 and has_shuttle else None
            ),
            "shuttle_hits_detected": len(shuttle_hits),
        }

        # Compute center recovery metrics if court center was provided
        recovery = {}
        if self.court_center is not None:
            recovery = self._compute_recovery(raw_frame_data, enriched_shots, fps)

        result = {
            "shots": enriched_shots,
            "rallies": rallies,
            "gap_zones": gap_zones,
            "shuttle_hits": shuttle_hits,
            "shot_timeline": shot_timeline,
            "shot_distribution": session_stats,
            "summary": summary,
        }
        if recovery:
            result["recovery"] = recovery
        return result

    # ------------------------------------------------------------------
    # Velocity computation
    # ------------------------------------------------------------------

    def _compute_velocities(self, raw_frames: List[dict]) -> List[dict]:
        """Compute per-frame velocity data from pose state history.

        Mirrors the logic from CourtBoundedAnalyzer.analyze_movement().
        """
        results: List[dict] = []
        pose_history: List[dict] = []  # sliding window of last 10

        for frame in raw_frames:
            pose_state = frame.get("pose_state")
            if not pose_state or not frame.get("player_detected"):
                results.append({})
                continue

            vel_data = {
                "wrist_velocity": 0.0,
                "body_velocity": 0.0,
                "wrist_direction": "none",
                "wrist_dy_per_sec": 0.0,
                "time_delta": 0.0,
                "pose_history_window": list(pose_history[-3:]),  # for arc detection
            }

            if pose_history:
                prev = pose_history[-1]
                time_delta = frame["timestamp"] - prev.get("timestamp", frame["timestamp"])
                if time_delta <= 0:
                    time_delta = 1.0 / self.effective_fps

                vel_data["time_delta"] = time_delta

                # Wrist velocity
                wrist_dx = pose_state["wrist"][0] - prev["wrist"][0]
                wrist_dy = pose_state["wrist"][1] - prev["wrist"][1]
                distance = math.sqrt(wrist_dx ** 2 + wrist_dy ** 2)
                vel_data["wrist_velocity"] = distance / time_delta

                # Wrist direction
                if abs(wrist_dy) > abs(wrist_dx):
                    vel_data["wrist_direction"] = "up" if wrist_dy < 0 else "down"
                else:
                    vel_data["wrist_direction"] = "right" if wrist_dx > 0 else "left"

                vel_data["wrist_dy_per_sec"] = wrist_dy / time_delta

                # Body velocity
                body_dx = pose_state["shoulder_center"][0] - prev["shoulder_center"][0]
                body_dy = pose_state["shoulder_center"][1] - prev["shoulder_center"][1]
                vel_data["body_velocity"] = math.sqrt(body_dx ** 2 + body_dy ** 2) / time_delta

            # Store wrist_direction into pose_state for arc detection in next frames
            pose_state_with_dir = {**pose_state, "wrist_direction": vel_data["wrist_direction"]}

            pose_history.append(pose_state_with_dir)
            if len(pose_history) > 10:
                pose_history.pop(0)

            results.append(vel_data)

        return results

    # ------------------------------------------------------------------
    # Overhead arc detection
    # ------------------------------------------------------------------

    def _detect_overhead_arcs(
        self, current_velocity: float, current_direction: str,
        pose_history_window: List[dict],
    ) -> Optional[str]:
        """Detect overhead arc at contact point (UP→DOWN transition).

        Returns 'smash_arc', 'clear_arc', 'drop_arc', or None.
        """
        if len(pose_history_window) < 3:
            return None

        recent = pose_history_window[-3:]
        T = self.T
        P = self.P

        up_frames = sum(1 for p in recent if p.get("wrist_direction") == "up")
        had_upward = up_frames >= 2
        moving_down = current_direction == "down"

        was_overhead = any(
            p.get("wrist", (0, 1))[1] < p.get("shoulder", (0, 0))[1] - P.get("overhead_offset", 0.08)
            for p in recent
        )

        time_span = recent[-1].get("timestamp", 0) - recent[0].get("timestamp", 0)
        within_window = time_span < 0.5

        if not (had_upward and moving_down and was_overhead and within_window):
            return None

        if current_velocity > T.get("smash_vs_clear", 2.4):
            return "smash_arc"
        elif current_velocity > T.get("gentle_overhead", 1.5):
            return "clear_arc"
        elif current_velocity > T.get("drop_min", 0.8):
            return "drop_arc"

        return None

    # ------------------------------------------------------------------
    # Swing classification
    # ------------------------------------------------------------------

    def _classify_swing(
        self, wrist_vel: float, wrist_dir: str, pose_state: dict,
        wrist_dy: float, pose_history_window: List[dict],
    ) -> str:
        """Classify swing type from velocity + body position."""
        T = self.T
        P = self.P

        if wrist_vel < T["static"]:
            return "static"

        # Arc detection
        arc = self._detect_overhead_arcs(wrist_vel, wrist_dir, pose_history_window)
        if arc:
            return arc

        wrist_y = pose_state["wrist"][1]
        wrist_x = pose_state["wrist"][0]
        shoulder_y = pose_state["shoulder"][1]
        shoulder_x = pose_state["shoulder"][0]
        hip_y = pose_state["hip_center"][1]

        arm_extension = math.sqrt((wrist_x - shoulder_x) ** 2 + (wrist_y - shoulder_y) ** 2)

        is_overhead = wrist_y < shoulder_y - P["overhead_offset"]
        is_low_position = wrist_y > hip_y - P["low_position_offset"]
        is_arm_extended = arm_extension > P["arm_extension_min"]

        if wrist_vel > T["power_overhead"] and wrist_dir == "up" and is_overhead:
            return "power_overhead"

        if wrist_vel > T["gentle_overhead"] and is_overhead and wrist_dir in ("up", "left", "right"):
            return "gentle_overhead"

        if wrist_vel > T["drive"] and wrist_dir in ("left", "right"):
            if shoulder_y < wrist_y < hip_y:
                return "drive"

        if is_low_position and is_arm_extended:
            if T["net_min"] < wrist_vel < T["net_max"]:
                if wrist_dir in ("down", "left", "right"):
                    return "net_play"

        if is_low_position and wrist_dir == "up" and wrist_vel > T["lift"]:
            return "lift"

        if wrist_vel > T["movement"]:
            return "movement"

        return "ready"

    # ------------------------------------------------------------------
    # Shot classification
    # ------------------------------------------------------------------

    def _classify_shot(self, swing_type: str, wrist_vel: float) -> Tuple[str, float]:
        """Map swing type to shot type with confidence."""
        T = self.T

        if swing_type == "smash_arc":
            return "smash", min(0.95, 0.7 + (wrist_vel - T.get("smash_vs_clear", 2.4)) * 0.1)

        if swing_type == "clear_arc":
            return "clear", min(0.90, 0.6 + (wrist_vel - T.get("gentle_overhead", 1.5)) * 0.15)

        if swing_type == "drop_arc":
            return "drop_shot", min(0.85, 0.5 + wrist_vel * 0.2)

        if swing_type == "power_overhead":
            if wrist_vel > T["smash_vs_clear"]:
                return "smash", min(0.9, 0.6 + (wrist_vel - T["smash_vs_clear"]) * 0.1)
            return "clear", min(0.85, 0.5 + (wrist_vel - T["gentle_overhead"]) * 0.15)

        if swing_type == "gentle_overhead":
            return "drop_shot", min(0.8, 0.5 + (wrist_vel - T["gentle_overhead"]) * 0.2)

        if swing_type == "net_play":
            return "net_shot", min(0.75, 0.5 + (wrist_vel - T["net_min"]) * 0.1)

        if swing_type == "drive":
            return "drive", min(0.75, 0.5 + (wrist_vel - T["drive"]) * 0.15)

        if swing_type == "lift":
            return "lift", min(0.7, 0.4 + (wrist_vel - T["lift"]) * 0.2)

        if swing_type == "movement":
            return "preparation", 0.4

        if swing_type == "ready":
            return "ready_position", 0.5

        return "static", 0.3

    # ------------------------------------------------------------------
    # Shuttle hit detection (arc direction changes)
    # ------------------------------------------------------------------

    def _detect_shuttle_hits(self, raw_frames: List[dict], fps: float) -> List[dict]:
        """Detect shuttle hit points using multi-signal trajectory analysis.

        Combines displacement cosine, speed ratio, and trajectory break signals
        with optional wrist velocity bonus to identify frames where the shuttle
        was hit.
        """
        return detect_shuttle_hits_windowed(
            raw_frames, fps,
            disp_window=self.hit_disp_window,
            speed_window=self.hit_speed_window,
            break_window=self.hit_break_window,
            hit_threshold=self.hit_threshold,
            cooldown_frames=self.hit_cooldown,
            norm_percentile=self.hit_norm_percentile,
            gate_min=self.hit_gate_min,
            wrist_bonus=self.hit_wrist_bonus,
            wrist_window=self.hit_wrist_window,
        )

    def _compute_shuttle_speed(
        self, raw_frames: List[dict], hit_frame: int, fps: float, n_frames: int = 10
    ) -> Optional[float]:
        """Compute avg shuttle speed (px/sec) over next n detected frames after a hit."""
        # Find frames after the hit
        after_hit = [
            f for f in raw_frames
            if f["frame_number"] > hit_frame
            and f.get("shuttle") and f["shuttle"].get("visible")
        ][:n_frames]

        if len(after_hit) < 2:
            return None

        speeds = []
        for i in range(1, len(after_hit)):
            dt = after_hit[i]["timestamp"] - after_hit[i - 1]["timestamp"]
            if dt <= 0:
                continue
            dx = after_hit[i]["shuttle"]["x"] - after_hit[i - 1]["shuttle"]["x"]
            dy = after_hit[i]["shuttle"]["y"] - after_hit[i - 1]["shuttle"]["y"]
            speed = math.sqrt(dx ** 2 + dy ** 2) / dt
            speeds.append(speed)

        return sum(speeds) / len(speeds) if speeds else None

    # ------------------------------------------------------------------
    # Shot-shuttle matching
    # ------------------------------------------------------------------

    def _match_shots_with_shuttle_hits(
        self, shots: List[dict], shuttle_hits: List[dict], tolerance: float = 0.3
    ) -> List[dict]:
        """Match each shot to nearest shuttle hit within tolerance seconds."""
        enriched = []
        used_hits = set()

        for shot in shots:
            best_hit = None
            best_delta = tolerance + 1

            for i, hit in enumerate(shuttle_hits):
                if i in used_hits:
                    continue
                delta = abs(shot["timestamp"] - hit["timestamp"])
                if delta < best_delta:
                    best_delta = delta
                    best_hit = (i, hit)

            enriched_shot = dict(shot)
            if best_hit and best_delta <= tolerance:
                idx, hit = best_hit
                used_hits.add(idx)
                enriched_shot["shuttle_speed_px_per_sec"] = hit.get("speed_px_per_sec")
                enriched_shot["shuttle_hit_matched"] = True
            else:
                enriched_shot["shuttle_speed_px_per_sec"] = None
                enriched_shot["shuttle_hit_matched"] = False

            enriched.append(enriched_shot)

        return enriched

    # ------------------------------------------------------------------
    # Hit-centric shot classification
    # ------------------------------------------------------------------

    def _classify_hits_centric(
        self,
        raw_frame_data: List[dict],
        shuttle_hits: List[dict],
        velocity_data: List[dict],
        fps: float,
    ) -> List[dict]:
        """Hit-centric shot classification using sliding window features.

        For each shuttle hit, collect pose data over the preceding
        ``attribution_window`` frames and compute aggregate features
        (avg wrist/shoulder/hip positions, overhead %, peak velocity).
        Classification uses these window-level features rather than a
        single peak-velocity frame, which is more robust to frame-to-frame
        noise.

        Decision order: net_shot → smash → clear → drop → lift → drive.

        Returns list of shot dicts compatible with existing format.
        """
        # Build frame_number → index lookup
        frame_lookup: Dict[int, int] = {}
        for i, fd in enumerate(raw_frame_data):
            frame_lookup[fd.get("frame_number", i)] = i

        lookback = self.attribution_window
        T = self.T
        W = self.W  # window classification thresholds
        shots: List[dict] = []

        for hit in shuttle_hits:
            hit_frame = hit["frame"]
            hit_ts = hit["timestamp"]
            hit_idx = frame_lookup.get(hit_frame)
            if hit_idx is None:
                continue

            lo = max(0, hit_idx - lookback)

            # Collect window features from pose data
            wrist_ys: List[float] = []
            wrist_xs: List[float] = []
            shoulder_ys: List[float] = []
            shoulder_xs: List[float] = []
            hip_ys: List[float] = []
            velocities: List[float] = []

            for i in range(lo, hit_idx + 1):
                fd = raw_frame_data[i]
                vel_info = velocity_data[i] if i < len(velocity_data) else {}
                velocities.append(vel_info.get("wrist_velocity", 0.0))

                if fd.get("player_detected") and fd.get("pose_state"):
                    ps = fd["pose_state"]
                    wrist_ys.append(ps["wrist"][1])
                    wrist_xs.append(ps["wrist"][0])
                    shoulder_ys.append(ps["shoulder"][1])
                    shoulder_xs.append(ps["shoulder_center"][0] if "shoulder_center" in ps else ps["shoulder"][0])
                    hip_ys.append(ps["hip_center"][1])

            n_pose = len(wrist_ys)
            max_vel = max(velocities) if velocities else 0.0

            # --- Player attribution ---
            # Signal 1: Wrist velocity (was the player swinging?)
            wrist_active = max_vel >= T["movement"]

            # Signal 2: Shuttle direction relative to player
            # After the hit, is the shuttle moving TOWARD or AWAY from our player?
            shuttle_direction_score = 0.0  # positive = toward player (opponent), negative = away (player)
            shuttle_dir_computed = False

            # Get player position in pixel space at hit frame
            hit_fd = raw_frame_data[hit_idx]
            ct = hit_fd.get("court_transform")
            ps_at_hit = hit_fd.get("pose_state")
            if ct and ps_at_hit and ps_at_hit.get("wrist"):
                player_px_x = ps_at_hit["wrist"][0] * ct["court_w"] + ct["x1"]
                player_px_y = ps_at_hit["wrist"][1] * ct["court_h"] + ct["y1"]

                # Compute shuttle velocity vector after hit (next 10 visible frames)
                shuttle_after = []
                for j in range(hit_idx + 1, min(hit_idx + 30, len(raw_frame_data))):
                    s = raw_frame_data[j].get("shuttle")
                    if s and s.get("visible") and s.get("x") is not None:
                        shuttle_after.append((s["x"], s["y"], raw_frame_data[j].get("timestamp", 0)))
                        if len(shuttle_after) >= 5:
                            break

                if len(shuttle_after) >= 2:
                    # Average shuttle velocity vector
                    total_dx = shuttle_after[-1][0] - shuttle_after[0][0]
                    total_dy = shuttle_after[-1][1] - shuttle_after[0][1]

                    # Shuttle position at hit
                    hit_shuttle = hit.get("hit_position", {})
                    sx = hit_shuttle.get("x")
                    sy = hit_shuttle.get("y")
                    if sx is not None and sy is not None:
                        # Vector from shuttle to player
                        to_player_x = player_px_x - sx
                        to_player_y = player_px_y - sy

                        # Dot product: positive = shuttle moving toward player
                        dot = total_dx * to_player_x + total_dy * to_player_y
                        # Normalize by magnitudes to get cosine similarity
                        mag_vel = math.sqrt(total_dx**2 + total_dy**2)
                        mag_dir = math.sqrt(to_player_x**2 + to_player_y**2)
                        if mag_vel > 0 and mag_dir > 0:
                            shuttle_direction_score = dot / (mag_vel * mag_dir)
                            shuttle_dir_computed = True

            # Combine signals for attribution
            # Shuttle direction is the primary signal (physics-based):
            #   Positive = toward player = opponent hit
            #   Negative = away from player = player hit
            if shuttle_dir_computed:
                is_opponent = shuttle_direction_score > 0
            else:
                # Only wrist velocity available — fall back to original logic
                is_opponent = not wrist_active

            if is_opponent:
                shots.append({
                    "frame": hit_frame,
                    "timestamp": hit_ts,
                    "shot_type": "opponent",
                    "confidence": round(1.0 - max_vel / T["movement"], 3) if max_vel < T["movement"] else 0.5,
                    "swing_type": "opponent_hit",
                    "wrist_velocity": round(max_vel, 3),
                    "shuttle_direction_score": round(shuttle_direction_score, 3) if shuttle_dir_computed else None,
                    "shuttle_speed_px_per_sec": hit.get("speed_px_per_sec"),
                    "shuttle_hit_matched": True,
                    "hit_by": "opponent",
                })
                continue

            if n_pose == 0:
                # No pose data in window — default to drive
                shots.append({
                    "frame": hit_frame,
                    "timestamp": hit_ts,
                    "shot_type": "drive",
                    "confidence": 0.3,
                    "swing_type": "window_no_pose",
                    "wrist_velocity": round(max_vel, 3),
                    "shuttle_speed_px_per_sec": hit.get("speed_px_per_sec"),
                    "shuttle_hit_matched": True,
                    "hit_by": "player",
                })
                continue

            avg_wy = sum(wrist_ys) / n_pose
            avg_sy = sum(shoulder_ys) / n_pose
            avg_hy = sum(hip_ys) / n_pose

            # Overhead: % of frames with wrist above shoulder (small offset)
            overhead_off = W["overhead_offset_window"]
            pct_overhead = sum(
                1 for wy, sy in zip(wrist_ys, shoulder_ys)
                if wy < sy - overhead_off
            ) / n_pose

            # Wrist-hip gap (positive = wrist above hip)
            wrist_hip_gap = avg_hy - avg_wy

            # --- Classification (order matters) ---

            # 1. NET SHOT: wrist very high on screen AND body low (lunging)
            if avg_wy < W["net_height_max"] and avg_hy < W["net_body_max"]:
                shot_type = "net_shot"
                confidence = min(0.80, 0.5 + max_vel * 0.05)

            # 2. SMASH: overhead + high velocity
            elif pct_overhead > W["overhead_pct_min"] and max_vel > T["smash_vs_clear"]:
                shot_type = "smash"
                confidence = min(0.95, 0.7 + (max_vel - T["smash_vs_clear"]) * 0.05)

            # 3. CLEAR: overhead + moderate velocity
            elif pct_overhead > W["overhead_pct_min"] and max_vel > T["gentle_overhead"]:
                shot_type = "clear"
                confidence = min(0.85, 0.6 + (max_vel - T["gentle_overhead"]) * 0.1)

            # 4. DROP: overhead + low velocity
            elif pct_overhead > W["overhead_pct_min"] and max_vel > T.get("drop_min", 0.8):
                shot_type = "drop_shot"
                confidence = min(0.80, 0.5 + max_vel * 0.1)

            # 5. LIFT: body low (crouching) OR wrist near hip level
            elif (
                avg_hy > W["lift_hip_min"]
                or (
                    avg_hy > W["lift_hip_secondary"]
                    and wrist_hip_gap < W["lift_gap_max"]
                    and avg_wy > W["lift_wrist_min"]
                )
            ):
                shot_type = "lift"
                confidence = min(0.75, 0.4 + max_vel * 0.08) if max_vel > 0.8 else 0.4

            # 6. DRIVE: default mid-court shot
            else:
                shot_type = "drive"
                confidence = (
                    min(0.75, 0.5 + (max_vel - T["drive"]) * 0.1)
                    if max_vel > T["drive"]
                    else 0.4
                )

            # Compute wrist-shoulder X offset for forehand/backhand detection
            stroke_diff = None
            if wrist_xs and shoulder_xs:
                diffs = [wx - sx for wx, sx in zip(wrist_xs, shoulder_xs)]
                stroke_diff = max(diffs, key=abs)

            shots.append({
                "frame": hit_frame,
                "timestamp": hit_ts,
                "shot_type": shot_type,
                "confidence": round(confidence, 3),
                "swing_type": f"window_{shot_type}",
                "wrist_velocity": round(max_vel, 3),
                "shuttle_direction_score": round(shuttle_direction_score, 3) if shuttle_dir_computed else None,
                "shuttle_speed_px_per_sec": hit.get("speed_px_per_sec"),
                "shuttle_hit_matched": True,
                "hit_by": "player",
                "stroke_diff": round(stroke_diff, 4) if stroke_diff is not None else None,
            })

        # Post-processing: enforce hit alternation within rallies.
        # In badminton, hits must alternate player/opponent. When consecutive
        # hits are attributed to the same side, flip the one with weaker evidence.
        shots = self._enforce_alternation(shots)

        # After alternation, detect dominant side and label forehand/backhand.
        # Only for player shots — opponent shots get stroke_side=None.
        player_diffs = [s["stroke_diff"] for s in shots
                        if s.get("hit_by") == "player" and s.get("stroke_diff") is not None]
        if player_diffs:
            positive_count = sum(1 for d in player_diffs if d > 0.02)
            negative_count = sum(1 for d in player_diffs if d < -0.02)
            forehand_is_positive = positive_count >= negative_count

            for s in shots:
                if s.get("hit_by") == "player" and s.get("stroke_diff") is not None:
                    diff = s["stroke_diff"]
                    if abs(diff) > 0.02:
                        s["stroke_side"] = ("forehand" if diff > 0 else "backhand") if forehand_is_positive else ("backhand" if diff > 0 else "forehand")
                    else:
                        s["stroke_side"] = None
                else:
                    s["stroke_side"] = None

        return shots

    @staticmethod
    def _enforce_alternation(shots: List[dict]) -> List[dict]:
        """Enforce player/opponent alternation — flip weaker-evidence duplicates.

        Uses shuttle direction as primary tiebreaker (physics-based), falls
        back to wrist velocity when direction is unavailable.
        """
        if len(shots) < 2:
            return shots

        def _attribution_strength(shot):
            """Score how confident we are in this shot's attribution.
            Positive = confident player, Negative = confident opponent.
            """
            hb = shot.get("hit_by", "player")
            sign = 1 if hb == "player" else -1

            # Shuttle direction is the strongest signal
            dir_score = shot.get("shuttle_direction_score")
            if dir_score is not None:
                # dir < 0 = away from player (player hit), dir > 0 = toward (opponent)
                # Flip sign so positive = player evidence
                return -dir_score * sign

            # Fall back to velocity
            vel = shot.get("wrist_velocity", 0)
            return vel * sign

        # Multiple passes until stable
        for _ in range(5):
            flipped = False
            for i in range(1, len(shots)):
                prev_hb = shots[i - 1].get("hit_by")
                curr_hb = shots[i].get("hit_by")

                if not prev_hb or not curr_hb:
                    continue
                if prev_hb not in ("player", "opponent") or curr_hb not in ("player", "opponent"):
                    continue
                if prev_hb != curr_hb:
                    continue

                # Same side — flip the one with weaker evidence
                prev_str = abs(_attribution_strength(shots[i - 1]))
                curr_str = abs(_attribution_strength(shots[i]))

                flip_idx = i if curr_str < prev_str else i - 1

                new_hb = "opponent" if shots[flip_idx]["hit_by"] == "player" else "player"
                shots[flip_idx]["hit_by"] = new_hb
                if new_hb == "opponent":
                    shots[flip_idx]["shot_type"] = "opponent"
                flipped = True

            if not flipped:
                break

        return shots

    # ------------------------------------------------------------------
    # Rally building
    # ------------------------------------------------------------------

    def _build_rallies(self, shots: List[dict], fps: float) -> List[dict]:
        """Group shots into rallies based on time gaps."""
        if not shots:
            return []

        rally_gap_frames = int(self.rally_gap_seconds * fps) if fps > 0 else 90

        rallies = []
        current_rally_shots = [shots[0]]
        rally_id = 1

        for i in range(1, len(shots)):
            gap_seconds = shots[i]["timestamp"] - shots[i - 1]["timestamp"]
            if gap_seconds > self.rally_gap_seconds:
                # End current rally
                if len(current_rally_shots) >= 2:
                    rallies.append({
                        "rally_id": rally_id,
                        "duration": round(
                            current_rally_shots[-1]["timestamp"] - current_rally_shots[0]["timestamp"], 2
                        ),
                        "shot_count": len(current_rally_shots),
                        "shots": [s["shot_type"] for s in current_rally_shots],
                        "hit_by": [s.get("hit_by", "player") for s in current_rally_shots],
                        "player_shots": sum(1 for s in current_rally_shots if s.get("hit_by") == "player"),
                        "opponent_shots": sum(1 for s in current_rally_shots if s.get("hit_by") == "opponent"),
                    })
                    rally_id += 1
                current_rally_shots = [shots[i]]
            else:
                current_rally_shots.append(shots[i])

        # Final rally
        if len(current_rally_shots) >= 2:
            rallies.append({
                "rally_id": rally_id,
                "duration": round(
                    current_rally_shots[-1]["timestamp"] - current_rally_shots[0]["timestamp"], 2
                ),
                "shot_count": len(current_rally_shots),
                "shots": [s["shot_type"] for s in current_rally_shots],
                "hit_by": [s.get("hit_by", "player") for s in current_rally_shots],
                "player_shots": sum(1 for s in current_rally_shots if s.get("hit_by") == "player"),
                "opponent_shots": sum(1 for s in current_rally_shots if s.get("hit_by") == "opponent"),
            })

        return rallies

    # ------------------------------------------------------------------
    # Shuttle-based rally detection
    # ------------------------------------------------------------------

    def _build_shuttle_rallies(
        self, raw_frame_data: List[dict], fps: float
    ) -> dict:
        """Detect rallies and gap zones from shuttle visibility.

        Step 1: Mark every frame as "in_gap" if ANY window of
                shuttle_gap_frames starting at or covering that frame has
                >= miss_pct% missing detections.  This produces continuous
                gap zones with no duplicate break markers.
        Step 2: Rallies = non-gap stretches that contain visible shuttle frames.
        Step 3: Return gap zones so shots inside them can be suppressed.
        """
        window = max(1, self.shuttle_gap_frames)
        threshold = self.shuttle_gap_miss_pct / 100.0

        visibility = []
        for f in raw_frame_data:
            shuttle = f.get("shuttle")
            visibility.append(bool(shuttle and shuttle.get("visible")))

        n = len(visibility)
        if not any(visibility):
            return {"rallies": [], "gap_zones": []}

        # Step 1: Build per-frame gap mask.
        # A frame is "in gap" if the window starting at that frame has
        # >= threshold% missing.  Then extend the mark to cover the
        # whole window so overlapping detections merge into one zone.
        in_gap = [False] * n
        for i in range(n):
            end = min(i + window, n)
            actual = end - i
            if actual <= 0:
                continue
            miss = sum(1 for v in visibility[i:end] if not v)
            if miss / actual >= threshold:
                for j in range(i, end):
                    in_gap[j] = True

        # Step 2: Extract gap zones and rallies from the mask
        gap_zones: List[dict] = []
        rallies: List[dict] = []
        rally_id = 1
        i = 0

        while i < n:
            if in_gap[i]:
                # Gap zone
                gap_start = i
                while i < n and in_gap[i]:
                    i += 1
                gap_end = i - 1
                gap_zones.append({
                    "start_idx": gap_start,
                    "end_idx": gap_end,
                    "start_frame": raw_frame_data[gap_start].get("frame_number", gap_start),
                    "end_frame": raw_frame_data[gap_end].get("frame_number", gap_end),
                    "start_time": round(raw_frame_data[gap_start].get("timestamp", 0), 2),
                    "end_time": round(raw_frame_data[gap_end].get("timestamp", 0), 2),
                })
            else:
                # Rally zone
                rally_start = i
                while i < n and not in_gap[i]:
                    i += 1
                rally_end = i - 1

                # Only count if shuttle was actually visible somewhere in this range
                has_visible = any(visibility[rally_start:rally_end + 1])
                if has_visible:
                    start_ts = raw_frame_data[rally_start].get("timestamp", 0)
                    end_ts = raw_frame_data[rally_end].get("timestamp", 0)
                    duration = round(end_ts - start_ts, 2)
                    if duration > 0:
                        rallies.append({
                            "rally_id": rally_id,
                            "start_frame": raw_frame_data[rally_start].get("frame_number", rally_start),
                            "end_frame": raw_frame_data[rally_end].get("frame_number", rally_end),
                            "start_time": round(start_ts, 2),
                            "end_time": round(end_ts, 2),
                            "duration": duration,
                        })
                        rally_id += 1

        return {"rallies": rallies, "gap_zones": gap_zones}

    # ------------------------------------------------------------------
    # Center recovery analysis
    # ------------------------------------------------------------------

    def _compute_recovery(
        self, raw_frame_data: List[dict], enriched_shots: List[dict], fps: float
    ) -> dict:
        """Compute center recovery metrics between consecutive player shots.

        Measures how well the player returns to the court center (base position)
        between shots, tracking recovery rate, time, speed, and fatigue trends.
        """
        if not self.court_center or not enriched_shots:
            return {}

        # Find a frame with court_transform to convert pixel center to normalized coords
        ct = None
        for f in raw_frame_data:
            ct = f.get("court_transform")
            if ct and ct.get("court_w") and ct.get("court_h"):
                break
        if not ct:
            return {}

        # Convert court center from pixel coords to normalized (0-1) court coords
        norm_cx = (self.court_center[0] - ct["x1"]) / ct["court_w"]
        norm_cy = (self.court_center[1] - ct["y1"]) / ct["court_h"]

        # Recovery zone: 5% of court diagonal in normalized space
        # Normalized court is ~1.0 x 1.0, diagonal = sqrt(2) ≈ 1.414
        recovery_radius = 0.05 * math.sqrt(2)

        # Filter to player shots only, sorted by frame
        player_shots = sorted(
            [s for s in enriched_shots if s.get("hit_by") == "player"],
            key=lambda s: s["frame"],
        )

        if len(player_shots) < 2:
            return {}

        # Build frame index for fast lookup
        frame_map = {}
        for f in raw_frame_data:
            frame_map[f.get("frame_number", 0)] = f

        # Analyze recovery windows between consecutive player shots
        windows = []
        min_window_sec = 0.3  # Skip windows shorter than 0.3s

        for i in range(len(player_shots) - 1):
            shot_a = player_shots[i]
            shot_b = player_shots[i + 1]
            window_duration = shot_b["timestamp"] - shot_a["timestamp"]

            if window_duration < min_window_sec:
                continue

            # Collect foot positions in the recovery window
            start_frame = shot_a["frame"]
            end_frame = shot_b["frame"]

            positions = []  # (timestamp, distance_to_center)
            for fn in range(start_frame, end_frame + 1):
                fd = frame_map.get(fn)
                if not fd or not fd.get("foot_position"):
                    continue
                fp = fd["foot_position"]
                dist = math.sqrt((fp[0] - norm_cx) ** 2 + (fp[1] - norm_cy) ** 2)
                positions.append((fd.get("timestamp", 0), dist))

            if not positions:
                continue

            start_dist = positions[0][1]
            min_dist = min(p[1] for p in positions)
            recovered = min_dist <= recovery_radius

            # Time to first entry into recovery zone
            recovery_time = None
            for ts, dist in positions:
                if dist <= recovery_radius:
                    recovery_time = ts - positions[0][0]
                    break

            # Recovery completeness: how much of the distance was covered
            completeness = 0.0
            if start_dist > 0.001:
                completeness = max(0.0, min(1.0, (start_dist - min_dist) / start_dist))

            # Recovery speed: distance covered toward center / time
            time_to_min = 0.0
            for ts, dist in positions:
                if dist == min_dist:
                    time_to_min = ts - positions[0][0]
                    break
            recovery_speed = (start_dist - min_dist) / time_to_min if time_to_min > 0.01 else 0.0

            windows.append({
                "from_shot_frame": start_frame,
                "to_shot_frame": end_frame,
                "from_shot_time": round(shot_a["timestamp"], 2),
                "to_shot_time": round(shot_b["timestamp"], 2),
                "window_duration": round(window_duration, 2),
                "recovered": recovered,
                "recovery_time_sec": round(recovery_time, 2) if recovery_time is not None else None,
                "min_distance": round(min_dist, 4),
                "recovery_completeness": round(completeness, 3),
                "recovery_speed": round(recovery_speed, 3),
            })

        if not windows:
            return {}

        # Aggregate summary
        total = len(windows)
        recovered_count = sum(1 for w in windows if w["recovered"])
        recovery_times = [w["recovery_time_sec"] for w in windows if w["recovery_time_sec"] is not None]
        speeds = [w["recovery_speed"] for w in windows if w["recovery_speed"] > 0]

        # Percentile helper (linear interpolation)
        def _percentile(sorted_vals, pct):
            if not sorted_vals:
                return None
            k = (len(sorted_vals) - 1) * (pct / 100.0)
            f = int(k)
            c = min(f + 1, len(sorted_vals) - 1)
            d = k - f
            return round(sorted_vals[f] + d * (sorted_vals[c] - sorted_vals[f]), 2)

        sorted_times = sorted(recovery_times)

        summary = {
            "total_windows": total,
            "recovery_rate": round(recovered_count / total, 3) if total > 0 else 0,
            "avg_recovery_time": round(sum(recovery_times) / len(recovery_times), 2) if recovery_times else None,
            "fastest_recovery_time": round(min(recovery_times), 2) if recovery_times else None,
            "slowest_recovery_time": round(max(recovery_times), 2) if recovery_times else None,
            "p50_recovery_time": _percentile(sorted_times, 50),
            "p95_recovery_time": _percentile(sorted_times, 95),
            "p99_recovery_time": _percentile(sorted_times, 99),
            "avg_recovery_completeness": round(
                sum(w["recovery_completeness"] for w in windows) / total, 3
            ) if total > 0 else 0,
            "avg_min_distance": round(
                sum(w["min_distance"] for w in windows) / total, 4
            ) if total > 0 else 0,
            "fastest_sprint_speed": round(max(speeds), 3) if speeds else None,
            "avg_recovery_speed": round(sum(speeds) / len(speeds), 3) if speeds else None,
        }

        return {
            "court_center_normalized": [round(norm_cx, 4), round(norm_cy, 4)],
            "recovery_zone_radius": round(recovery_radius, 4),
            "windows": windows,
            "summary": summary,
        }
