"""
Frame Analyzer - Core pose detection and shot classification logic.

This module extracts the shared frame analysis functionality from CourtBoundedAnalyzer
so it can be used by both:
1. Video analysis (batch processing)
2. Live streaming (real-time processing)
"""

import cv2
import numpy as np
import mediapipe as mp
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CourtBoundary:
    """Defines the court region of interest."""
    top_left: Tuple[int, int]
    top_right: Tuple[int, int]
    bottom_left: Tuple[int, int]
    bottom_right: Tuple[int, int]
    court_color: str = "green"

    def get_polygon(self) -> np.ndarray:
        """Get court boundary as polygon for cv2 operations."""
        return np.array([
            self.top_left,
            self.top_right,
            self.bottom_right,
            self.bottom_left
        ], dtype=np.int32)

    def get_bounding_rect(self) -> Tuple[int, int, int, int]:
        """Get bounding rectangle (x, y, width, height)."""
        all_x = [self.top_left[0], self.top_right[0], self.bottom_left[0], self.bottom_right[0]]
        all_y = [self.top_left[1], self.top_right[1], self.bottom_left[1], self.bottom_right[1]]
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)
        return (x_min, y_min, x_max - x_min, y_max - y_min)

    def is_point_inside(self, point: Tuple[int, int]) -> bool:
        """Check if a point is inside the court boundary."""
        polygon = self.get_polygon()
        result = cv2.pointPolygonTest(polygon, point, False)
        return result >= 0

    def is_bbox_inside(self, bbox: Tuple[int, int, int, int], threshold: float = 0.5) -> bool:
        """Check if bounding box is sufficiently inside court."""
        x1, y1, x2, y2 = bbox
        points = [
            (x1, y1), (x2, y1),
            (x1, y2), (x2, y2),
            ((x1 + x2) // 2, (y1 + y2) // 2)
        ]
        inside_count = sum(1 for p in points if self.is_point_inside(p))
        return (inside_count / len(points)) >= threshold

    def create_mask(self, frame_shape: Tuple[int, int]) -> np.ndarray:
        """Create a binary mask for the court region."""
        mask = np.zeros(frame_shape[:2], dtype=np.uint8)
        polygon = self.get_polygon()
        cv2.fillPoly(mask, [polygon], 255)
        return mask

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'top_left': list(self.top_left),
            'top_right': list(self.top_right),
            'bottom_left': list(self.bottom_left),
            'bottom_right': list(self.bottom_right),
            'court_color': self.court_color
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CourtBoundary':
        """Create from dictionary."""
        return cls(
            top_left=tuple(data['top_left']),
            top_right=tuple(data['top_right']),
            bottom_left=tuple(data['bottom_left']),
            bottom_right=tuple(data['bottom_right']),
            court_color=data.get('court_color', 'green')
        )


@dataclass
class ShotData:
    """Data structure for storing shot information."""
    frame_number: int
    timestamp: float
    shot_type: str
    confidence: float
    player_bbox: Optional[Tuple[int, int, int, int]] = None
    wrist_position: Optional[Tuple[int, int]] = None
    coaching_tip: str = ""
    movement_data: dict = field(default_factory=dict)


@dataclass
class FrameAnalysisResult:
    """Result of analyzing a single frame."""
    shot_data: Optional[ShotData] = None
    pose_landmarks: Optional[any] = None
    player_detected: bool = False
    foot_position: Optional[Tuple[int, int]] = None
    is_actual_shot: bool = False  # True if this is a real shot (smash, clear, etc.)


class FrameAnalyzer:
    """
    Core frame analysis logic for badminton shot detection.

    This class handles:
    - Pose detection within court boundaries
    - Movement analysis
    - Shot classification
    - Foot position tracking

    Can be used for both video processing and live streaming.
    """

    ACTUAL_SHOTS = ['smash', 'clear', 'drop_shot', 'net_shot', 'drive', 'lift']

    def __init__(
        self,
        court_boundary: CourtBoundary,
        processing_width: int = 640,
        model_complexity: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.4
    ):
        """
        Initialize frame analyzer.

        Args:
            court_boundary: Court region to analyze
            processing_width: Resize frame width for processing (smaller=faster)
            model_complexity: MediaPipe model complexity (0=fastest, 1=balanced, 2=accurate)
            min_detection_confidence: Minimum confidence for pose detection
            min_tracking_confidence: Minimum confidence for pose tracking
        """
        self.court = court_boundary
        self.processing_width = processing_width
        self.model_complexity = model_complexity

        # Initialize MediaPipe pose
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            enable_segmentation=False,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.mp_drawing = mp.solutions.drawing_utils

        # Movement tracking history
        self.pose_history: List[dict] = []
        self._last_transform: Optional[dict] = None

        # Coaching tips database
        self.coaching_db = self._setup_coaching_database()

        logger.info(f"FrameAnalyzer initialized: width={processing_width}, complexity={model_complexity}")

    def _setup_coaching_database(self) -> dict:
        """Setup coaching tips for each shot type."""
        return {
            'smash': {
                'tips': [
                    "Keep elbow high and rotate torso for power",
                    "Hit at the highest point of contact",
                    "Follow through completely towards target"
                ],
                'priority': 'high'
            },
            'clear': {
                'tips': [
                    "Use high-to-low swing path",
                    "Generate power from legs and core",
                    "Aim for deep back court"
                ],
                'priority': 'high'
            },
            'drop_shot': {
                'tips': [
                    "Use deceptive preparation (same as smash)",
                    "Gentle wrist action at contact",
                    "Aim just over the net"
                ],
                'priority': 'medium'
            },
            'net_shot': {
                'tips': [
                    "Keep racket head up early",
                    "Step forward into the shot",
                    "Keep shuttle tight to the net"
                ],
                'priority': 'medium'
            },
            'drive': {
                'tips': [
                    "Keep racket flat and fast",
                    "Step into the shot",
                    "Quick compact swing"
                ],
                'priority': 'low'
            },
            'lift': {
                'tips': [
                    "Get low and under the shuttle",
                    "Use legs to generate power",
                    "Aim high and deep to back court"
                ],
                'priority': 'medium'
            }
        }

    def get_coaching_tip(self, shot_type: str, shot_count: int = 0) -> str:
        """Get a coaching tip for the shot type."""
        if shot_type in self.coaching_db:
            tips = self.coaching_db[shot_type]['tips']
            tip_index = shot_count % len(tips)
            return tips[tip_index]
        return ""

    def analyze_frame(
        self,
        frame: np.ndarray,
        frame_number: int,
        timestamp: float,
        shot_count: int = 0
    ) -> FrameAnalysisResult:
        """
        Analyze a single frame for shot detection.

        Args:
            frame: BGR image frame
            frame_number: Frame number in video/stream
            timestamp: Timestamp in seconds
            shot_count: Current shot count (for cycling coaching tips)

        Returns:
            FrameAnalysisResult with shot data and pose landmarks
        """
        result = FrameAnalysisResult()

        # Detect pose within court
        pose_landmarks, player_bbox = self._analyze_pose_in_court(frame)

        if pose_landmarks is None:
            return result

        result.player_detected = True
        result.pose_landmarks = pose_landmarks

        # Get foot position for heatmap
        foot_pos = self._get_foot_position(pose_landmarks)
        if foot_pos:
            result.foot_position = foot_pos

        # Analyze movement
        movement_data = self._analyze_movement(pose_landmarks)

        # Classify shot
        shot_type, confidence = self._classify_shot(movement_data, pose_landmarks)

        # Get wrist position
        h, w = frame.shape[:2]
        wrist = pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        wrist_pos = (int(wrist.x * w), int(wrist.y * h))

        # Get coaching tip for actual shots
        coaching_tip = ""
        if shot_type in self.ACTUAL_SHOTS:
            coaching_tip = self.get_coaching_tip(shot_type, shot_count)

        # Create shot data
        shot_data = ShotData(
            frame_number=frame_number,
            timestamp=timestamp,
            shot_type=shot_type,
            confidence=confidence,
            player_bbox=player_bbox,
            wrist_position=wrist_pos,
            coaching_tip=coaching_tip,
            movement_data=movement_data
        )

        result.shot_data = shot_data
        result.is_actual_shot = shot_type in self.ACTUAL_SHOTS and confidence > 0.5

        return result

    def _analyze_pose_in_court(self, frame: np.ndarray) -> Tuple[Optional[any], Optional[Tuple]]:
        """Detect pose only within court boundaries."""
        h, w = frame.shape[:2]

        # Crop to court region with padding
        x, y, cw, ch = self.court.get_bounding_rect()
        pad = 50
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(w, x + cw + pad)
        y2 = min(h, y + ch + pad)
        court_frame = frame[y1:y2, x1:x2]

        court_h, court_w = court_frame.shape[:2]

        # Resize for faster processing
        if court_w > self.processing_width:
            scale = self.processing_width / court_w
            process_frame = cv2.resize(court_frame, (self.processing_width, int(court_h * scale)))
        else:
            scale = 1.0
            process_frame = court_frame

        # Convert to RGB for MediaPipe
        frame_rgb = cv2.cvtColor(process_frame, cv2.COLOR_BGR2RGB)

        # Run pose detection
        results = self.pose.process(frame_rgb)

        if not results.pose_landmarks:
            return None, None

        landmarks = results.pose_landmarks.landmark

        # Get player center (hip midpoint) in full frame coordinates
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]

        center_x = int((left_hip.x + right_hip.x) / 2 * court_w + x1)
        center_y = int((left_hip.y + right_hip.y) / 2 * court_h + y1)

        # Check if player center is inside court
        if not self.court.is_point_inside((center_x, center_y)):
            return None, None

        # Calculate player bounding box
        x_coords = [lm.x * court_w + x1 for lm in landmarks if lm.visibility > 0.5]
        y_coords = [lm.y * court_h + y1 for lm in landmarks if lm.visibility > 0.5]

        if not x_coords or not y_coords:
            return None, None

        player_bbox = (
            int(min(x_coords)),
            int(min(y_coords)),
            int(max(x_coords)),
            int(max(y_coords))
        )

        # Verify bbox is inside court
        if not self.court.is_bbox_inside(player_bbox, threshold=0.3):
            return None, None

        # Store transform info for coordinate mapping
        self._last_transform = {
            'x1': x1, 'y1': y1,
            'court_w': court_w, 'court_h': court_h,
            'scale': scale
        }

        return results.pose_landmarks, player_bbox

    def _get_foot_position(self, pose_landmarks) -> Optional[Tuple[int, int]]:
        """Get foot midpoint position for heatmap."""
        if pose_landmarks is None or self._last_transform is None:
            return None

        landmarks = pose_landmarks.landmark
        left_ankle = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE]
        right_ankle = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE]

        # Lower visibility threshold for better coverage
        if left_ankle.visibility < 0.3 and right_ankle.visibility < 0.3:
            return None

        # Calculate foot midpoint
        if left_ankle.visibility >= 0.3 and right_ankle.visibility >= 0.3:
            mid_x = (left_ankle.x + right_ankle.x) / 2
            mid_y = (left_ankle.y + right_ankle.y) / 2
        elif left_ankle.visibility >= 0.3:
            mid_x, mid_y = left_ankle.x, left_ankle.y
        else:
            mid_x, mid_y = right_ankle.x, right_ankle.y

        # Convert to pixel coordinates
        transform = self._last_transform
        pixel_x = int(mid_x * transform['court_w'] + transform['x1'])
        pixel_y = int(mid_y * transform['court_h'] + transform['y1'])

        # Return position even if slightly outside court (for better heatmap coverage)
        # The court boundary check was too strict
        return (pixel_x, pixel_y)

    def _analyze_movement(self, pose_landmarks) -> dict:
        """Analyze player movement from pose landmarks."""
        if not pose_landmarks:
            return {}

        landmarks = pose_landmarks.landmark

        # Key points
        right_wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        right_elbow = landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]

        current_state = {
            'wrist': (right_wrist.x, right_wrist.y),
            'elbow': (right_elbow.x, right_elbow.y),
            'shoulder': (right_shoulder.x, right_shoulder.y),
            'shoulder_center': (
                (right_shoulder.x + left_shoulder.x) / 2,
                (right_shoulder.y + left_shoulder.y) / 2
            ),
            'hip_center': (
                (right_hip.x + left_hip.x) / 2,
                (right_hip.y + left_hip.y) / 2
            )
        }

        movement_data = {
            'wrist_velocity': 0.0,
            'body_velocity': 0.0,
            'wrist_direction': 'none',
            'swing_type': 'none'
        }

        if len(self.pose_history) > 0:
            prev_state = self.pose_history[-1]

            # Wrist velocity
            wrist_dx = current_state['wrist'][0] - prev_state['wrist'][0]
            wrist_dy = current_state['wrist'][1] - prev_state['wrist'][1]
            movement_data['wrist_velocity'] = math.sqrt(wrist_dx**2 + wrist_dy**2)

            # Wrist direction
            if abs(wrist_dy) > abs(wrist_dx):
                movement_data['wrist_direction'] = 'up' if wrist_dy < 0 else 'down'
            else:
                movement_data['wrist_direction'] = 'right' if wrist_dx > 0 else 'left'

            # Body velocity
            body_dx = current_state['shoulder_center'][0] - prev_state['shoulder_center'][0]
            body_dy = current_state['shoulder_center'][1] - prev_state['shoulder_center'][1]
            movement_data['body_velocity'] = math.sqrt(body_dx**2 + body_dy**2)

            # Classify swing type
            movement_data['swing_type'] = self._classify_swing(
                movement_data['wrist_velocity'],
                movement_data['wrist_direction'],
                current_state,
                wrist_dy
            )

        # Store in history (keep last 10 frames)
        self.pose_history.append(current_state)
        if len(self.pose_history) > 10:
            self.pose_history.pop(0)

        return movement_data

    def _classify_swing(self, wrist_vel: float, wrist_dir: str,
                        pose_state: dict, wrist_dy: float) -> str:
        """Classify the type of swing based on movement."""
        if wrist_vel < 0.03:
            return 'static'

        wrist_y = pose_state['wrist'][1]
        wrist_x = pose_state['wrist'][0]
        shoulder_y = pose_state['shoulder'][1]
        shoulder_x = pose_state['shoulder'][0]
        elbow_y = pose_state['elbow'][1]
        hip_y = pose_state['hip_center'][1]

        arm_extension = math.sqrt((wrist_x - shoulder_x)**2 + (wrist_y - shoulder_y)**2)
        is_overhead = wrist_y < shoulder_y - 0.08
        is_low_position = wrist_y > hip_y - 0.1
        is_arm_extended = arm_extension > 0.15

        # Overhead shots
        if wrist_vel > 0.06 and wrist_dir == 'up' and is_overhead:
            return 'power_overhead'

        if wrist_vel > 0.04 and is_overhead and wrist_dir in ['up', 'left', 'right']:
            return 'gentle_overhead'

        # Drive shots
        if wrist_vel > 0.05 and wrist_dir in ['left', 'right']:
            if shoulder_y < pose_state['wrist'][1] < hip_y:
                return 'drive'

        # Net shots
        if is_low_position and is_arm_extended:
            if 0.03 < wrist_vel < 0.12:
                if wrist_dir in ['down', 'left', 'right']:
                    return 'net_play'

        # Lift shots
        if is_low_position and wrist_dir == 'up' and wrist_vel > 0.04:
            return 'lift'

        # Movement/preparation
        if wrist_vel > 0.025:
            return 'movement'

        return 'ready'

    def _classify_shot(self, movement_data: dict, pose_landmarks) -> Tuple[str, float]:
        """Classify shot type from movement data."""
        swing_type = movement_data.get('swing_type', 'none')
        wrist_vel = movement_data.get('wrist_velocity', 0)

        if swing_type == 'power_overhead':
            if wrist_vel > 0.08:
                return 'smash', min(0.9, 0.6 + wrist_vel * 3)
            else:
                return 'clear', min(0.85, 0.5 + wrist_vel * 4)

        elif swing_type == 'gentle_overhead':
            return 'drop_shot', min(0.8, 0.5 + wrist_vel * 5)

        elif swing_type == 'net_play':
            return 'net_shot', min(0.75, 0.5 + wrist_vel * 3)

        elif swing_type == 'drive':
            return 'drive', min(0.75, 0.5 + wrist_vel * 4)

        elif swing_type == 'lift':
            return 'lift', min(0.7, 0.4 + wrist_vel * 4)

        elif swing_type == 'movement':
            return 'preparation', 0.4

        elif swing_type == 'ready':
            return 'ready_position', 0.5

        else:
            return 'static', 0.3

    def reset(self):
        """Reset analyzer state for new video/stream."""
        self.pose_history = []
        self._last_transform = None

    def close(self):
        """Release resources."""
        if self.pose:
            self.pose.close()
