"""
Pose similarity scoring for Mimic challenges.

Three scoring methods computed per frame:
  A) Weighted cosine similarity (raw)
  B) Normalized cosine similarity (body-relative)
  C) Joint angle comparison

All functions are pure — no DB or session dependencies.
Landmarks are expected as lists of dicts with keys: nx, ny, visibility
(normalized 0-1 coordinates from MediaPipe).
"""

import math
from typing import Dict, List, Optional, Tuple

from ....core.streaming.pose_detector import PoseDetector

# MediaPipe landmark indices for body regions
UPPER_INDICES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
LOWER_INDICES = [23, 24, 25, 26, 27, 28, 29, 30, 31, 32]

# Joint angle definitions: (point_a, vertex, point_c) using landmark indices
# Each tuple defines the angle at the vertex point.
ANGLE_DEFINITIONS = [
    ("L_elbow", 11, 13, 15),    # left elbow: shoulder-elbow-wrist
    ("R_elbow", 12, 14, 16),    # right elbow
    ("L_shoulder", 13, 11, 23),  # left shoulder: elbow-shoulder-hip
    ("R_shoulder", 14, 12, 24),  # right shoulder
    ("L_knee", 23, 25, 27),      # left knee: hip-knee-ankle
    ("R_knee", 24, 26, 28),      # right knee
    ("L_hip", 11, 23, 25),       # left hip: shoulder-hip-knee
    ("R_hip", 12, 24, 26),       # right hip
]

# Feedback joint names for user-facing messages
JOINT_NAMES = {
    "L_elbow": "left elbow",
    "R_elbow": "right elbow",
    "L_shoulder": "left shoulder",
    "R_shoulder": "right shoulder",
    "L_knee": "left knee",
    "R_knee": "right knee",
    "L_hip": "left hip",
    "R_hip": "right hip",
}


def _lm_to_xy(lm: Dict) -> Tuple[float, float]:
    """Extract normalized (x, y) from a landmark dict."""
    return (lm.get("nx", lm.get("x", 0.0)), lm.get("ny", lm.get("y", 0.0)))


def _visibility(lm: Dict) -> float:
    return lm.get("visibility", 0.0)


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _magnitude(v: List[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def weighted_cosine_score(user_lm: List[Dict], ref_lm: List[Dict]) -> float:
    """
    Method A: Weighted cosine similarity on raw landmark positions.

    Flattens landmarks to [x1,y1,x2,y2,...] vectors, weights each pair
    by min(user_vis, ref_vis). Returns score 0-100.
    """
    if not user_lm or not ref_lm:
        return 0.0

    n = min(len(user_lm), len(ref_lm))
    u_vec = []
    r_vec = []

    for i in range(n):
        ux, uy = _lm_to_xy(user_lm[i])
        rx, ry = _lm_to_xy(ref_lm[i])
        w = min(_visibility(user_lm[i]), _visibility(ref_lm[i]))
        u_vec.extend([ux * w, uy * w])
        r_vec.extend([rx * w, ry * w])

    mag_u = _magnitude(u_vec)
    mag_r = _magnitude(r_vec)
    if mag_u == 0 or mag_r == 0:
        return 0.0

    cos_sim = _dot(u_vec, r_vec) / (mag_u * mag_r)
    # Map from ~[0.5, 1.0] → [0, 100]
    return max(0.0, min(100.0, (cos_sim - 0.5) / 0.5 * 100.0))


def normalized_cosine_score(user_lm: List[Dict], ref_lm: List[Dict]) -> float:
    """
    Method B: Normalized cosine similarity.

    Before cosine, translates both poses so mid-hip = origin
    and scales so shoulder width = 1.0. This removes body-structure
    baseline for better dynamic range.
    """
    if not user_lm or not ref_lm:
        return 0.0

    n = min(len(user_lm), len(ref_lm))
    if n < 25:
        return weighted_cosine_score(user_lm, ref_lm)

    def _normalize(lm_list):
        # Mid-hip = average of landmarks 23 and 24
        lh = _lm_to_xy(lm_list[23])
        rh = _lm_to_xy(lm_list[24])
        cx = (lh[0] + rh[0]) / 2
        cy = (lh[1] + rh[1]) / 2

        # Shoulder width = distance between landmarks 11 and 12
        ls = _lm_to_xy(lm_list[11])
        rs = _lm_to_xy(lm_list[12])
        sw = math.sqrt((ls[0] - rs[0]) ** 2 + (ls[1] - rs[1]) ** 2)
        if sw < 1e-6:
            sw = 1.0

        normalized = []
        for i in range(len(lm_list)):
            x, y = _lm_to_xy(lm_list[i])
            normalized.append({
                "nx": (x - cx) / sw,
                "ny": (y - cy) / sw,
                "visibility": _visibility(lm_list[i]),
            })
        return normalized

    try:
        u_norm = _normalize(user_lm)
        r_norm = _normalize(ref_lm)
    except (IndexError, ZeroDivisionError):
        return weighted_cosine_score(user_lm, ref_lm)

    return weighted_cosine_score(u_norm, r_norm)


def angle_comparison_score(user_lm: List[Dict], ref_lm: List[Dict]) -> float:
    """
    Method C: Joint angle comparison.

    Computes key joint angles for both poses and scores based on
    angular difference. Each angle contributes max(0, 1 - |diff|/45) * 100.
    """
    if not user_lm or not ref_lm:
        return 0.0

    n = min(len(user_lm), len(ref_lm))
    if n < 29:
        return 0.0

    scores = []
    for name, a_idx, b_idx, c_idx in ANGLE_DEFINITIONS:
        if a_idx >= n or b_idx >= n or c_idx >= n:
            continue

        # Check visibility — skip if any joint is too low confidence
        min_vis = min(
            _visibility(user_lm[a_idx]), _visibility(user_lm[b_idx]), _visibility(user_lm[c_idx]),
            _visibility(ref_lm[a_idx]), _visibility(ref_lm[b_idx]), _visibility(ref_lm[c_idx]),
        )
        if min_vis < 0.3:
            continue

        u_angle = PoseDetector.angle_between(
            _lm_to_xy(user_lm[a_idx]), _lm_to_xy(user_lm[b_idx]), _lm_to_xy(user_lm[c_idx])
        )
        r_angle = PoseDetector.angle_between(
            _lm_to_xy(ref_lm[a_idx]), _lm_to_xy(ref_lm[b_idx]), _lm_to_xy(ref_lm[c_idx])
        )

        diff = abs(u_angle - r_angle)
        angle_score = max(0.0, 1.0 - diff / 45.0) * 100.0
        scores.append(angle_score)

    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def region_score(
    user_lm: List[Dict], ref_lm: List[Dict], indices: List[int]
) -> float:
    """Score a subset of landmarks using normalized cosine similarity."""
    if not user_lm or not ref_lm:
        return 0.0

    n = min(len(user_lm), len(ref_lm))
    valid_indices = [i for i in indices if i < n]
    if not valid_indices:
        return 0.0

    sub_user = [user_lm[i] for i in valid_indices]
    sub_ref = [ref_lm[i] for i in valid_indices]

    return weighted_cosine_score(sub_user, sub_ref)


def compute_all_similarities(
    user_lm: List[Dict], ref_lm: List[Dict]
) -> Dict:
    """
    Compute all similarity metrics for a single frame.

    Returns dict with all scores (0-100) and region breakdowns.
    """
    return {
        "cosine_raw": round(weighted_cosine_score(user_lm, ref_lm), 1),
        "cosine_normalized": round(normalized_cosine_score(user_lm, ref_lm), 1),
        "angle_score": round(angle_comparison_score(user_lm, ref_lm), 1),
        "upper_body": round(region_score(user_lm, ref_lm, UPPER_INDICES), 1),
        "lower_body": round(region_score(user_lm, ref_lm, LOWER_INDICES), 1),
    }


def generate_feedback(user_lm: List[Dict], ref_lm: List[Dict]) -> str:
    """
    Generate actionable feedback by finding the joint with the largest
    angle difference between user and reference poses.
    """
    if not user_lm or not ref_lm:
        return "Step into frame"

    n = min(len(user_lm), len(ref_lm))
    if n < 29:
        return ""

    worst_name = ""
    worst_diff = 0.0
    worst_user_angle = 0.0
    worst_ref_angle = 0.0

    for name, a_idx, b_idx, c_idx in ANGLE_DEFINITIONS:
        if a_idx >= n or b_idx >= n or c_idx >= n:
            continue

        min_vis = min(
            _visibility(user_lm[a_idx]), _visibility(user_lm[b_idx]), _visibility(user_lm[c_idx]),
            _visibility(ref_lm[a_idx]), _visibility(ref_lm[b_idx]), _visibility(ref_lm[c_idx]),
        )
        if min_vis < 0.3:
            continue

        u_angle = PoseDetector.angle_between(
            _lm_to_xy(user_lm[a_idx]), _lm_to_xy(user_lm[b_idx]), _lm_to_xy(user_lm[c_idx])
        )
        r_angle = PoseDetector.angle_between(
            _lm_to_xy(ref_lm[a_idx]), _lm_to_xy(ref_lm[b_idx]), _lm_to_xy(ref_lm[c_idx])
        )

        diff = abs(u_angle - r_angle)
        if diff > worst_diff:
            worst_diff = diff
            worst_name = name
            worst_user_angle = u_angle
            worst_ref_angle = r_angle

    if worst_diff < 15:
        return "Great form!"

    joint = JOINT_NAMES.get(worst_name, worst_name)
    if worst_user_angle > worst_ref_angle:
        action = "Bend" if "knee" in joint or "elbow" in joint else "Lower"
    else:
        action = "Straighten" if "knee" in joint or "elbow" in joint else "Raise"

    return f"{action} your {joint} more"
