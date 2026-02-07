"""
Tuning Service - Fast re-classification of shots using cached frame data.

This service enables instant threshold tuning without re-running pose detection:
1. Video analysis runs once, caching per-frame metrics (velocities, positions)
2. When user adjusts thresholds, this service re-applies classification logic
3. Results update in ~100ms vs minutes for full reprocessing
"""

import json
import math
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Shot types
ACTUAL_SHOTS = ['smash', 'clear', 'drop_shot', 'net_shot', 'drive', 'lift']
NON_SHOT_STATES = ['static', 'ready_position', 'preparation', 'follow_through']


def detect_overhead_arc_from_frames(
    current_frame_idx: int,
    frames: List[Dict[str, Any]],
    current_velocity: float,
    current_direction: str,
    thresholds: Dict[str, float],
    position_thresholds: Optional[Dict[str, float]] = None
) -> Optional[str]:
    """
    Detect if we're at the contact point of an overhead motion arc.
    Pattern: UP phase (preparation) → DOWN phase (hit)

    This version works with cached frame data for tuning service re-classification.

    Args:
        current_frame_idx: Index of current frame in frames list
        frames: List of all cached frame data
        current_velocity: Current wrist velocity
        current_direction: Current wrist direction
        thresholds: Velocity thresholds dict
        position_thresholds: Position thresholds dict

    Returns:
        'smash_arc', 'clear_arc', 'drop_arc', or None
    """
    # Need at least 3 previous frames for arc detection
    if current_frame_idx < 3:
        return None

    T = thresholds
    P = position_thresholds or {'overhead_offset': 0.08}

    # Get the last 3 frames before current
    recent_indices = range(max(0, current_frame_idx - 3), current_frame_idx)
    recent_frames = [frames[i] for i in recent_indices if frames[i].get('player_detected', False)]

    if len(recent_frames) < 2:
        return None

    # Check 1: Was recently moving UP? (at least 2 of last 3 frames)
    up_frames = sum(1 for f in recent_frames if f.get('wrist_direction') == 'up')
    had_upward_motion = up_frames >= 2

    # Check 2: Currently moving DOWN?
    moving_down = current_direction == 'down'

    # Check 3: Was overhead at peak? (wrist above shoulder in recent frames)
    overhead_offset = P.get('overhead_offset', 0.08)
    was_overhead = any(
        (f.get('wrist_y') is not None and
         f.get('shoulder_y') is not None and
         f.get('wrist_y') < f.get('shoulder_y') - overhead_offset)
        for f in recent_frames
    )

    # Check 4: Time window (arc within 0.5 seconds)
    current_ts = frames[current_frame_idx].get('timestamp', 0)
    earliest_ts = recent_frames[0].get('timestamp', 0) if recent_frames else 0
    time_span = current_ts - earliest_ts
    within_window = time_span < 0.5

    # Must satisfy arc pattern first
    if not (had_upward_motion and moving_down and was_overhead and within_window):
        return None

    # Check 5: Classify based on descent velocity
    if current_velocity > T.get('smash_vs_clear', 2.4):
        return 'smash_arc'
    elif current_velocity > T.get('gentle_overhead', 1.5):
        return 'clear_arc'
    elif current_velocity > T.get('drop_min', 0.8):
        return 'drop_arc'

    return None  # Too slow to be an overhead shot


@dataclass
class FrameClassification:
    """Classification result for a single frame."""
    frame_number: int
    timestamp: float
    shot_type: str
    confidence: float
    swing_type: str
    cooldown_active: bool


def classify_swing(
    wrist_velocity: float,
    wrist_direction: str,
    wrist_y: float,
    shoulder_y: float,
    hip_y: float,
    arm_extension: float,
    thresholds: Dict[str, float],
    position_thresholds: Optional[Dict[str, float]] = None,
    frame_idx: Optional[int] = None,
    frames: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Classify swing type based on movement data and thresholds.

    Args:
        wrist_velocity: Wrist velocity in normalized distance per second
        wrist_direction: Direction of wrist movement ('up', 'down', 'left', 'right')
        wrist_y: Y position of wrist (normalized, 0=top)
        shoulder_y: Y position of shoulder (normalized)
        hip_y: Y position of hip center (normalized)
        arm_extension: Distance from wrist to shoulder (normalized)
        thresholds: Velocity threshold dictionary
        position_thresholds: Optional position threshold dictionary
        frame_idx: Optional current frame index (for arc detection)
        frames: Optional list of all frames (for arc detection)

    Returns:
        Swing type string
    """
    T = thresholds

    # Default position thresholds
    P = position_thresholds or {
        'overhead_offset': 0.08,
        'low_position_offset': 0.1,
        'arm_extension_min': 0.15
    }

    # Static - no significant movement
    if wrist_velocity < T.get('static', 0.9):
        return 'static'

    # Check for overhead arc pattern (smash/clear/drop) if frame context available
    if frame_idx is not None and frames is not None:
        overhead_arc = detect_overhead_arc_from_frames(
            frame_idx, frames, wrist_velocity, wrist_direction, T, P
        )
        if overhead_arc:
            return overhead_arc  # 'smash_arc', 'clear_arc', or 'drop_arc'

    # Handle missing position data - can't do position-based classification
    if wrist_y is None or shoulder_y is None or hip_y is None:
        # Fall back to velocity-only classification
        if wrist_velocity > T.get('power_overhead', 1.8) and wrist_direction == 'up':
            return 'power_overhead'
        if wrist_velocity > T.get('gentle_overhead', 1.2) and wrist_direction in ['up', 'left', 'right']:
            return 'gentle_overhead'
        if wrist_velocity > T.get('drive', 1.5) and wrist_direction in ['left', 'right']:
            return 'drive'
        if wrist_velocity > T.get('movement', 0.75):
            return 'movement'
        return 'ready'

    # Position checks using tunable thresholds
    is_overhead = wrist_y < shoulder_y - P.get('overhead_offset', 0.08)
    is_low_position = wrist_y > hip_y - P.get('low_position_offset', 0.1)
    is_arm_extended = (arm_extension or 0) > P.get('arm_extension_min', 0.15)

    # Overhead shots (power overhead = smash potential) - legacy single-frame detection
    if wrist_velocity > T.get('power_overhead', 1.8) and wrist_direction == 'up' and is_overhead:
        return 'power_overhead'

    # Gentle overhead (clear/drop potential) - legacy single-frame detection
    if wrist_velocity > T.get('gentle_overhead', 1.2) and is_overhead and wrist_direction in ['up', 'left', 'right']:
        return 'gentle_overhead'

    # Drive shots (horizontal at mid-body)
    if wrist_velocity > T.get('drive', 1.5) and wrist_direction in ['left', 'right']:
        if shoulder_y < wrist_y < hip_y:
            return 'drive'

    # Net shots (low position, arm extended, controlled movement)
    net_min = T.get('net_min', 0.9)
    net_max = T.get('net_max', 3.6)
    if is_low_position and is_arm_extended:
        if net_min < wrist_velocity < net_max:
            if wrist_direction in ['down', 'left', 'right']:
                return 'net_play'

    # Lift shots (low position, upward movement)
    if is_low_position and wrist_direction == 'up' and wrist_velocity > T.get('lift', 1.2):
        return 'lift'

    # Movement/preparation
    if wrist_velocity > T.get('movement', 0.75):
        return 'movement'

    return 'ready'


def classify_shot(
    swing_type: str,
    wrist_velocity: float,
    thresholds: Dict[str, float]
) -> Tuple[str, float]:
    """
    Convert swing type to final shot classification with confidence.

    Args:
        swing_type: Classified swing type from classify_swing()
        wrist_velocity: Wrist velocity for confidence calculation
        thresholds: Velocity threshold dictionary

    Returns:
        Tuple of (shot_type, confidence)
    """
    T = thresholds

    # Arc-detected overhead shots (high confidence - detected at contact point)
    if swing_type == 'smash_arc':
        confidence = min(0.95, 0.7 + (wrist_velocity - T.get('smash_vs_clear', 2.4)) * 0.1)
        return 'smash', confidence

    elif swing_type == 'clear_arc':
        confidence = min(0.90, 0.6 + (wrist_velocity - T.get('gentle_overhead', 1.5)) * 0.15)
        return 'clear', confidence

    elif swing_type == 'drop_arc':
        confidence = min(0.85, 0.5 + wrist_velocity * 0.2)
        return 'drop_shot', confidence

    # Legacy single-frame detection
    if swing_type == 'power_overhead':
        smash_threshold = T.get('smash_vs_clear', 2.4)
        if wrist_velocity > smash_threshold:
            confidence = min(0.9, 0.6 + (wrist_velocity - smash_threshold) * 0.1)
            return 'smash', confidence
        else:
            confidence = min(0.85, 0.5 + (wrist_velocity - T.get('gentle_overhead', 1.2)) * 0.15)
            return 'clear', confidence

    elif swing_type == 'gentle_overhead':
        confidence = min(0.8, 0.5 + (wrist_velocity - T.get('gentle_overhead', 1.2)) * 0.2)
        return 'drop_shot', confidence

    elif swing_type == 'net_play':
        confidence = min(0.75, 0.5 + (wrist_velocity - T.get('net_min', 0.9)) * 0.1)
        return 'net_shot', confidence

    elif swing_type == 'drive':
        confidence = min(0.75, 0.5 + (wrist_velocity - T.get('drive', 1.5)) * 0.15)
        return 'drive', confidence

    elif swing_type == 'lift':
        confidence = min(0.7, 0.4 + (wrist_velocity - T.get('lift', 1.2)) * 0.2)
        return 'lift', confidence

    elif swing_type == 'movement':
        return 'preparation', 0.4

    elif swing_type == 'ready':
        return 'ready_position', 0.5

    else:
        return 'static', 0.3


def reclassify_shots(
    frame_data: Dict[str, Any],
    new_thresholds: Dict[str, float],
    new_cooldown: float = 0.4,
    position_thresholds: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Re-classify all shots in frame data using new thresholds.

    This is the core fast re-classification function. It takes cached
    movement data (velocities, positions) and re-applies the classification
    logic with new threshold values.

    Args:
        frame_data: Cached frame analysis data with per-frame metrics
        new_thresholds: New velocity thresholds to apply
        new_cooldown: New shot cooldown in seconds
        position_thresholds: Optional position thresholds (overhead_offset, low_position_offset, arm_extension_min)

    Returns:
        Dictionary with:
        - results: List of per-frame classification results
        - shot_distribution_before: Original shot counts
        - shot_distribution_after: New shot counts
        - frames_changed: Number of frames with different classification
        - comparison: List of before/after for changed frames
    """
    frames = frame_data.get("frames", [])
    original_thresholds = frame_data.get("thresholds_used", {})
    original_cooldown = frame_data.get("cooldown_seconds", 0.4)

    results = []
    comparison = []
    last_shot_ts = -999.0

    # Count distributions
    dist_before = {}
    dist_after = {}
    frames_changed = 0

    for frame_idx, frame in enumerate(frames):
        frame_num = frame.get("frame_number", 0)
        timestamp = frame.get("timestamp", 0)
        player_detected = frame.get("player_detected", False)

        # Get original classification
        original_shot = frame.get("shot_type")
        original_conf = frame.get("confidence", 0)

        if not player_detected:
            results.append({
                "frame_number": frame_num,
                "timestamp": timestamp,
                "player_detected": False,
                "original_shot_type": original_shot,
                "original_confidence": original_conf,
                "new_shot_type": None,
                "new_confidence": None,
                "changed": False
            })
            continue

        # Get movement data for re-classification
        # Use 'or' to handle both missing keys and None values
        wrist_velocity = frame.get("wrist_velocity") or 0
        wrist_direction = frame.get("wrist_direction") or "none"
        wrist_y = frame.get("wrist_y")  # Keep as None if missing - classify_swing handles it
        shoulder_y = frame.get("shoulder_y")
        hip_y = frame.get("hip_y")
        arm_extension = frame.get("arm_extension")

        # Re-classify swing type (with frame context for arc detection)
        swing_type = classify_swing(
            wrist_velocity=wrist_velocity,
            wrist_direction=wrist_direction,
            wrist_y=wrist_y,
            shoulder_y=shoulder_y,
            hip_y=hip_y,
            arm_extension=arm_extension,
            thresholds=new_thresholds,
            position_thresholds=position_thresholds,
            frame_idx=frame_idx,
            frames=frames
        )

        # Re-classify shot
        new_shot, new_conf = classify_shot(swing_type, wrist_velocity, new_thresholds)

        # Apply cooldown
        cooldown_active = False
        if new_shot in ACTUAL_SHOTS and new_conf > 0.5:
            if timestamp - last_shot_ts < new_cooldown:
                # In cooldown - classify as follow-through
                new_shot = 'follow_through'
                new_conf = 0.3
                cooldown_active = True
            else:
                last_shot_ts = timestamp

        # Track changes
        changed = original_shot != new_shot
        if changed:
            frames_changed += 1
            comparison.append({
                "frame_number": frame_num,
                "timestamp": timestamp,
                "before_shot": original_shot,
                "before_confidence": original_conf,
                "after_shot": new_shot,
                "after_confidence": new_conf
            })

        # Update distributions (only count actual shots)
        if original_shot in ACTUAL_SHOTS:
            dist_before[original_shot] = dist_before.get(original_shot, 0) + 1
        if new_shot in ACTUAL_SHOTS:
            dist_after[new_shot] = dist_after.get(new_shot, 0) + 1

        results.append({
            "frame_number": frame_num,
            "timestamp": timestamp,
            "player_detected": True,
            "original_shot_type": original_shot,
            "original_confidence": original_conf,
            "new_shot_type": new_shot,
            "new_confidence": new_conf,
            "swing_type": swing_type,
            "cooldown_active": cooldown_active,
            "changed": changed
        })

    return {
        "total_frames": len(frames),
        "frames_changed": frames_changed,
        "results": results,
        "comparison": comparison,
        "shot_distribution_before": dist_before,
        "shot_distribution_after": dist_after,
        "thresholds_applied": new_thresholds,
        "position_thresholds_applied": position_thresholds,
        "cooldown_applied": new_cooldown
    }


def load_frame_data(frame_data_path: str) -> Optional[Dict[str, Any]]:
    """Load cached frame data from JSON file."""
    try:
        path = Path(frame_data_path)
        if not path.exists():
            logger.error(f"Frame data file not found: {frame_data_path}")
            return None

        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading frame data: {e}")
        return None


def save_frame_data(frame_data: Dict[str, Any], output_path: str) -> bool:
    """Save frame data to JSON file."""
    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(frame_data, f, indent=2)

        logger.info(f"Frame data saved: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving frame data: {e}")
        return False


def extract_velocity_thresholds(thresholds: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract flat velocity threshold values from nested preset format.

    Converts from:
    {"velocity": {"static": {"value": 0.9, ...}, ...}}

    To:
    {"static": 0.9, ...}
    """
    result = {}

    # Handle velocity thresholds
    velocity = thresholds.get("velocity", {})
    for key, val in velocity.items():
        if isinstance(val, dict):
            result[key] = val.get("value", 0)
        else:
            result[key] = val

    # Handle cooldown (extract as regular threshold for convenience)
    cooldown = thresholds.get("cooldown", {})
    for key, val in cooldown.items():
        if isinstance(val, dict):
            result[key] = val.get("value", 0)
        else:
            result[key] = val

    return result


def extract_position_thresholds(thresholds: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract position threshold values from nested preset format.

    Converts from:
    {"position": {"overhead_offset": {"value": 0.08, ...}, ...}}

    To:
    {"overhead_offset": 0.08, "low_position_offset": 0.1, "arm_extension_min": 0.15}
    """
    result = {}
    position = thresholds.get("position", {})

    for key, val in position.items():
        if isinstance(val, dict):
            result[key] = val.get("value", 0)
        else:
            result[key] = val

    # Ensure defaults are present
    if "overhead_offset" not in result:
        result["overhead_offset"] = 0.08
    if "low_position_offset" not in result:
        result["low_position_offset"] = 0.1
    if "arm_extension_min" not in result:
        result["arm_extension_min"] = 0.15

    return result


def get_overhead_offset(thresholds: Dict[str, Any]) -> float:
    """Extract overhead offset from position thresholds (for backward compatibility)."""
    position = thresholds.get("position", {})
    overhead = position.get("overhead_offset", {})
    if isinstance(overhead, dict):
        return overhead.get("value", 0.08)
    return overhead if isinstance(overhead, (int, float)) else 0.08


class TuningService:
    """Service class for tuning operations."""

    @staticmethod
    def reclassify_from_file(
        frame_data_path: str,
        new_thresholds: Dict[str, Any],
        new_cooldown: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load frame data from file and re-classify with new thresholds.

        Args:
            frame_data_path: Path to cached frame data JSON
            new_thresholds: New threshold configuration (nested or flat format)
            new_cooldown: New cooldown seconds (if None, extract from thresholds)

        Returns:
            Re-classification results or None on error
        """
        # Load frame data
        frame_data = load_frame_data(frame_data_path)
        if not frame_data:
            return None

        # Extract flat thresholds
        velocity_thresholds = extract_velocity_thresholds(new_thresholds)

        # Extract position thresholds
        position_thresholds = extract_position_thresholds(new_thresholds)

        # Get cooldown
        if new_cooldown is None:
            cooldown = new_thresholds.get("cooldown", {})
            shot_cd = cooldown.get("shot_cooldown_seconds", {})
            if isinstance(shot_cd, dict):
                new_cooldown = shot_cd.get("value", 0.4)
            else:
                new_cooldown = float(shot_cd) if shot_cd else 0.4

        # Re-classify
        return reclassify_shots(
            frame_data=frame_data,
            new_thresholds=velocity_thresholds,
            new_cooldown=new_cooldown,
            position_thresholds=position_thresholds
        )

    @staticmethod
    def compare_presets(
        frame_data_path: str,
        preset_a_thresholds: Dict[str, Any],
        preset_b_thresholds: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Compare classification results between two presets.

        Returns analysis of how shot detection differs between presets.
        """
        frame_data = load_frame_data(frame_data_path)
        if not frame_data:
            return None

        # Extract cooldown values
        def get_cooldown(preset):
            cd = preset.get("cooldown", {}).get("shot_cooldown_seconds", {})
            return cd.get("value", 0.4) if isinstance(cd, dict) else cd

        # Run classification with each preset
        result_a = reclassify_shots(
            frame_data,
            extract_velocity_thresholds(preset_a_thresholds),
            get_cooldown(preset_a_thresholds),
            extract_position_thresholds(preset_a_thresholds)
        )

        result_b = reclassify_shots(
            frame_data,
            extract_velocity_thresholds(preset_b_thresholds),
            get_cooldown(preset_b_thresholds),
            extract_position_thresholds(preset_b_thresholds)
        )

        # Compare results
        differences = []
        for ra, rb in zip(result_a["results"], result_b["results"]):
            if ra["new_shot_type"] != rb["new_shot_type"]:
                differences.append({
                    "frame_number": ra["frame_number"],
                    "timestamp": ra["timestamp"],
                    "preset_a_shot": ra["new_shot_type"],
                    "preset_a_confidence": ra["new_confidence"],
                    "preset_b_shot": rb["new_shot_type"],
                    "preset_b_confidence": rb["new_confidence"]
                })

        return {
            "total_frames": result_a["total_frames"],
            "frames_different": len(differences),
            "differences": differences,
            "preset_a_distribution": result_a["shot_distribution_after"],
            "preset_b_distribution": result_b["shot_distribution_after"]
        }
