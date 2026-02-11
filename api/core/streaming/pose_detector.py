"""
Shared pose detection wrapper around MediaPipe.

Extracted from FrameAnalyzer so that multiple features (badminton,
challenges, workout) can reuse the same pose detection pipeline
without duplicating MediaPipe initialization or coordinate transforms.
"""

import cv2
import numpy as np
import math
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Skeleton connections for frontend visualization
SKELETON_CONNECTIONS = [
    # Torso
    (11, 12),   # shoulders
    (11, 23),   # left shoulder → left hip
    (12, 24),   # right shoulder → right hip
    (23, 24),   # hips
    # Left arm
    (11, 13),   # shoulder → elbow
    (13, 15),   # elbow → wrist
    # Right arm
    (12, 14),   # shoulder → elbow
    (14, 16),   # elbow → wrist
    # Left leg
    (23, 25),   # hip → knee
    (25, 27),   # knee → ankle
    # Right leg
    (24, 26),   # hip → knee
    (26, 28),   # knee → ankle
]


@dataclass
class PoseResult:
    """Result of a single-frame pose detection."""
    landmarks: Optional[object] = None  # MediaPipe NormalizedLandmarkList
    player_detected: bool = False
    landmark_list: Optional[List[Dict]] = None  # [{x, y, visibility}, ...]
    frame_width: int = 0
    frame_height: int = 0


class PoseDetector:
    """
    Standalone MediaPipe Pose wrapper.

    Handles model initialisation, frame preprocessing, and coordinate
    normalisation.  Feature analyzers receive a `PoseResult` and use
    whichever landmarks they need without knowing about MediaPipe.
    """

    def __init__(
        self,
        model_complexity: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.4,
    ):
        import mediapipe as mp

        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            enable_segmentation=False,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    # ----- public API -----

    def detect(self, frame: np.ndarray) -> PoseResult:
        """
        Run pose detection on a BGR frame.

        Returns a PoseResult with raw MediaPipe landmarks and a
        serialisable landmark list (pixel coordinates).
        """
        h, w = frame.shape[:2]
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)

        if not results.pose_landmarks:
            return PoseResult(frame_width=w, frame_height=h)

        # Build serialisable list
        lm_list = []
        for lm in results.pose_landmarks.landmark:
            lm_list.append({
                "x": int(lm.x * w),
                "y": int(lm.y * h),
                "visibility": lm.visibility,
                "nx": lm.x,   # normalised 0-1
                "ny": lm.y,
            })

        return PoseResult(
            landmarks=results.pose_landmarks,
            player_detected=True,
            landmark_list=lm_list,
            frame_width=w,
            frame_height=h,
        )

    def extract_pose_data(self, pose_result: PoseResult) -> Optional[Dict]:
        """
        Convert PoseResult into a frontend-friendly dict with landmarks
        and skeleton connections.
        """
        if not pose_result.player_detected or not pose_result.landmark_list:
            return None

        return {
            "landmarks": pose_result.landmark_list,
            "connections": SKELETON_CONNECTIONS,
            "width": pose_result.frame_width,
            "height": pose_result.frame_height,
        }

    # ----- angle helpers (used by challenges) -----

    @staticmethod
    def angle_between(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
        """
        Compute the angle ABC (in degrees) where B is the vertex.

        Args:
            a, b, c: (x, y) tuples (pixel or normalised).

        Returns:
            Angle in degrees [0, 180].
        """
        ba = (a[0] - b[0], a[1] - b[1])
        bc = (c[0] - b[0], c[1] - b[1])
        dot = ba[0] * bc[0] + ba[1] * bc[1]
        mag_ba = math.sqrt(ba[0] ** 2 + ba[1] ** 2)
        mag_bc = math.sqrt(bc[0] ** 2 + bc[1] ** 2)
        if mag_ba * mag_bc == 0:
            return 0.0
        cos_angle = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
        return math.degrees(math.acos(cos_angle))

    def close(self):
        """Release MediaPipe resources."""
        if self.pose:
            self.pose.close()
