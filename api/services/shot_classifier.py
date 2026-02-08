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

    def __init__(
        self,
        velocity_thresholds: Optional[Dict[str, float]] = None,
        position_thresholds: Optional[Dict[str, float]] = None,
        shot_cooldown_seconds: float = 0.4,
        effective_fps: float = 30.0,
        rally_gap_seconds: float = 3.0,
        shuttle_gap_frames: int = 90,
        shuttle_gap_miss_pct: float = 80.0,
    ):
        self.T = {**self.DEFAULT_VELOCITY_THRESHOLDS, **(velocity_thresholds or {})}
        self.P = {**self.DEFAULT_POSITION_THRESHOLDS, **(position_thresholds or {})}
        self.shot_cooldown_seconds = shot_cooldown_seconds
        self.effective_fps = effective_fps
        self.rally_gap_seconds = rally_gap_seconds
        self.shuttle_gap_frames = shuttle_gap_frames
        self.shuttle_gap_miss_pct = shuttle_gap_miss_pct

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

        # Phase 2: Classify each frame (swing -> shot)
        shots = []
        last_shot_timestamp = -999.0
        session_stats: Dict[str, int] = {}

        for i, frame in enumerate(raw_frame_data):
            if not frame.get("player_detected"):
                continue

            vel_info = velocity_data[i] if i < len(velocity_data) else {}
            if not vel_info:
                continue

            pose_state = frame.get("pose_state")
            if not pose_state:
                continue

            # Classify swing type
            swing_type = self._classify_swing(
                vel_info["wrist_velocity"],
                vel_info["wrist_direction"],
                pose_state,
                vel_info.get("wrist_dy_per_sec", 0),
                vel_info.get("pose_history_window", []),
            )

            # Classify shot from swing
            shot_type, confidence = self._classify_shot(swing_type, vel_info["wrist_velocity"])

            # Apply cooldown
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

        # Phase 3: Detect shuttle hits (arc direction changes)
        shuttle_hits = self._detect_shuttle_hits(raw_frame_data, fps)

        # Phase 4: Match shots with shuttle hits
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

        # Phase 7: Enrich shuttle rallies with shot data
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

        summary = {
            "total_shots": len(enriched_shots),
            "total_rallies": len(rallies),
            "frames_processed": total_frames,
            "player_detection_rate": (
                player_detected_frames / total_frames if total_frames > 0 else 0
            ),
            "avg_confidence": (
                sum(s["confidence"] for s in enriched_shots) / len(enriched_shots)
                if enriched_shots else 0
            ),
            "shuttle_detection_rate": (
                shuttle_detected_frames / total_frames if total_frames > 0 and has_shuttle else None
            ),
            "shuttle_hits_detected": len(shuttle_hits),
        }

        return {
            "shots": enriched_shots,
            "rallies": rallies,
            "gap_zones": gap_zones,
            "shuttle_hits": shuttle_hits,
            "shot_timeline": shot_timeline,
            "shot_distribution": session_stats,
            "summary": summary,
        }

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
        """Detect shuttle hit points from direction changes in shuttle trajectory.

        A "hit" is detected when the shuttle's horizontal or vertical velocity
        reverses direction with significant magnitude.
        """
        hits: List[dict] = []
        prev_visible_frame = None
        prev_dx = None
        prev_dy = None

        min_speed_for_hit = 50.0  # minimum px/sec to consider a direction change as a hit

        for frame in raw_frames:
            shuttle = frame.get("shuttle")
            if not shuttle or not shuttle.get("visible"):
                continue

            if prev_visible_frame is None:
                prev_visible_frame = frame
                continue

            prev_shuttle = prev_visible_frame["shuttle"]
            dt = frame["timestamp"] - prev_visible_frame["timestamp"]
            if dt <= 0:
                prev_visible_frame = frame
                continue

            dx = (shuttle["x"] - prev_shuttle["x"]) / dt  # px/sec
            dy = (shuttle["y"] - prev_shuttle["y"]) / dt

            if prev_dx is not None:
                # Check horizontal direction reversal
                h_reversal = (prev_dx * dx < 0) and (abs(dx) > min_speed_for_hit or abs(prev_dx) > min_speed_for_hit)
                # Check vertical direction reversal with significant magnitude
                v_reversal = (prev_dy * dy < 0) and (abs(dy) > min_speed_for_hit * 1.5)

                if h_reversal or v_reversal:
                    speed_after = self._compute_shuttle_speed(raw_frames, frame["frame_number"], fps)
                    hits.append({
                        "frame": frame["frame_number"],
                        "timestamp": frame["timestamp"],
                        "hit_position": {"x": shuttle["x"], "y": shuttle["y"]},
                        "speed_px_per_sec": round(speed_after, 1) if speed_after else None,
                        "direction_before": {"dx": round(prev_dx, 1), "dy": round(prev_dy, 1)},
                        "direction_after": {"dx": round(dx, 1), "dy": round(dy, 1)},
                    })

            prev_dx = dx
            prev_dy = dy
            prev_visible_frame = frame

        return hits

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
