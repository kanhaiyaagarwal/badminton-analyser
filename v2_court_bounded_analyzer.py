"""
Badminton Shot Analyzer v2 - Court Bounded Analysis
====================================================
Focuses on half-court single player analysis with user-defined court boundaries.

Features:
- User defines court boundary coordinates at startup
- Only analyzes players within the defined court region
- Cleaner shot detection based on pose movement
- Optional court color for better visualization
"""

import cv2
import numpy as np
import mediapipe as mp
import json
import sys
import math
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import logging

# Output directory for all analysis results
OUTPUT_DIR = Path(__file__).parent / "analysis_output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(OUTPUT_DIR / 'badminton_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class CourtBoundary:
    """Defines the court region of interest"""
    top_left: Tuple[int, int]
    top_right: Tuple[int, int]
    bottom_left: Tuple[int, int]
    bottom_right: Tuple[int, int]
    court_color: str = "green"  # green, blue, wood, other

    def get_polygon(self) -> np.ndarray:
        """Get court boundary as polygon for cv2 operations"""
        return np.array([
            self.top_left,
            self.top_right,
            self.bottom_right,
            self.bottom_left
        ], dtype=np.int32)

    def get_bounding_rect(self) -> Tuple[int, int, int, int]:
        """Get bounding rectangle (x, y, width, height)"""
        all_x = [self.top_left[0], self.top_right[0], self.bottom_left[0], self.bottom_right[0]]
        all_y = [self.top_left[1], self.top_right[1], self.bottom_left[1], self.bottom_right[1]]

        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)

        return (x_min, y_min, x_max - x_min, y_max - y_min)

    def is_point_inside(self, point: Tuple[int, int]) -> bool:
        """Check if a point is inside the court boundary"""
        polygon = self.get_polygon()
        result = cv2.pointPolygonTest(polygon, point, False)
        return result >= 0

    def is_bbox_inside(self, bbox: Tuple[int, int, int, int], threshold: float = 0.5) -> bool:
        """Check if bounding box is sufficiently inside court (by threshold %)"""
        x1, y1, x2, y2 = bbox

        # Check corners and center
        points = [
            (x1, y1), (x2, y1),  # top corners
            (x1, y2), (x2, y2),  # bottom corners
            ((x1 + x2) // 2, (y1 + y2) // 2)  # center
        ]

        inside_count = sum(1 for p in points if self.is_point_inside(p))
        return (inside_count / len(points)) >= threshold

    def create_mask(self, frame_shape: Tuple[int, int]) -> np.ndarray:
        """Create a binary mask for the court region"""
        mask = np.zeros(frame_shape[:2], dtype=np.uint8)
        polygon = self.get_polygon()
        cv2.fillPoly(mask, [polygon], 255)
        return mask

    def to_dict(self) -> dict:
        """Convert to dictionary for saving"""
        return {
            'top_left': self.top_left,
            'top_right': self.top_right,
            'bottom_left': self.bottom_left,
            'bottom_right': self.bottom_right,
            'court_color': self.court_color
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CourtBoundary':
        """Create from dictionary"""
        return cls(
            top_left=tuple(data['top_left']),
            top_right=tuple(data['top_right']),
            bottom_left=tuple(data['bottom_left']),
            bottom_right=tuple(data['bottom_right']),
            court_color=data.get('court_color', 'green')
        )


@dataclass
class ShotData:
    """Data structure for storing shot information"""
    frame_number: int
    timestamp: float
    shot_type: str
    confidence: float
    player_bbox: Tuple[int, int, int, int]
    wrist_position: Optional[Tuple[int, int]] = None
    coaching_tip: str = ""
    movement_data: dict = field(default_factory=dict)


@dataclass
class RallyData:
    """Data structure for a rally (sequence of shots)"""
    rally_id: int
    start_frame: int
    end_frame: int
    start_time: float
    end_time: float
    shots: List[ShotData] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def shot_count(self) -> int:
        return len(self.shots)


class CourtBoundedAnalyzer:
    """Badminton analyzer that only processes within defined court boundaries"""

    def __init__(self, court_boundary: CourtBoundary, process_every_n_frames: int = 2,
                 processing_width: int = 640, model_complexity: int = 1,
                 skip_static_frames: bool = True):
        """
        Initialize analyzer with performance options.

        Args:
            court_boundary: Court region to analyze
            process_every_n_frames: Skip frames for pose detection (1=all, 2=every other, etc.)
            processing_width: Resize frame to this width for processing (smaller=faster)
            model_complexity: MediaPipe model complexity (0=fastest, 1=balanced, 2=accurate)
            skip_static_frames: Skip pose detection when no motion detected
        """
        self.court = court_boundary
        self.process_every_n_frames = process_every_n_frames
        self.processing_width = processing_width
        self.model_complexity = model_complexity
        self.skip_static_frames = skip_static_frames

        # For motion detection
        self.prev_gray = None
        self.motion_threshold = 1000  # Minimum pixels changed to consider motion

        self.setup_models()
        self.setup_coaching_database()
        self.reset_analysis_state()

    def setup_models(self):
        """Initialize pose detection model"""
        logger.info("Initializing Court Bounded Badminton Analyzer...")

        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=self.model_complexity,  # 0=fastest, 1=balanced, 2=accurate
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.4
        )
        self.mp_drawing = mp.solutions.drawing_utils

        logger.info(f"Pose model loaded (complexity={self.model_complexity})")
        logger.info(f"Processing width: {self.processing_width}px")
        logger.info(f"Frame skip: every {self.process_every_n_frames} frame(s)")
        logger.info(f"Skip static frames: {self.skip_static_frames}")
        logger.info(f"Court boundary: {self.court.get_bounding_rect()}")

    def setup_coaching_database(self):
        """Setup coaching tips for each shot type"""
        self.coaching_db = {
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

    def reset_analysis_state(self):
        """Reset all analysis state for new video"""
        self.shot_history: List[ShotData] = []
        self.rally_history: List[RallyData] = []
        self.session_stats = defaultdict(int)

        # Movement tracking
        self.pose_history = []
        self.movement_history = []
        self.foot_position_history: List[Tuple[int, int]] = []  # Full video tracking for heatmap
        self.foot_position_data: List[dict] = []  # Detailed tracking with timestamps and rally info

        # Rally tracking
        self.current_rally_shots = []
        self.rally_id_counter = 0
        self.frames_since_last_shot = 0
        self.rally_gap_threshold = 90  # frames (~3 seconds at 30fps) to consider rally ended

        # State tracking
        self.last_shot_frame = 0
        self.player_detected_frames = 0
        self.total_frames_processed = 0

    def get_coaching_tip(self, shot_type: str) -> str:
        """Get a coaching tip for the shot type"""
        if shot_type in self.coaching_db:
            tips = self.coaching_db[shot_type]['tips']
            tip_index = len(self.shot_history) % len(tips)
            return tips[tip_index]
        return ""

    def _accumulate_foot_position(self, pose_landmarks, frame_number: int = 0, timestamp: float = 0.0) -> None:
        """Accumulate foot position for heatmap generation"""
        if pose_landmarks is None or not hasattr(self, '_last_transform'):
            return

        landmarks = pose_landmarks.landmark
        left_ankle = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE]
        right_ankle = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE]

        # Check visibility
        if left_ankle.visibility < 0.5 and right_ankle.visibility < 0.5:
            return

        # Calculate foot midpoint in normalized coordinates
        if left_ankle.visibility >= 0.5 and right_ankle.visibility >= 0.5:
            mid_x = (left_ankle.x + right_ankle.x) / 2
            mid_y = (left_ankle.y + right_ankle.y) / 2
        elif left_ankle.visibility >= 0.5:
            mid_x, mid_y = left_ankle.x, left_ankle.y
        else:
            mid_x, mid_y = right_ankle.x, right_ankle.y

        # Convert to pixel coordinates using stored transform
        transform = self._last_transform
        pixel_x = int(mid_x * transform['court_w'] + transform['x1'])
        pixel_y = int(mid_y * transform['court_h'] + transform['y1'])

        # Only add if inside court boundary
        if self.court.is_point_inside((pixel_x, pixel_y)):
            self.foot_position_history.append((pixel_x, pixel_y))

            # Store detailed data for advanced visualizations
            # Rally ID: use current rally counter, or -1 if between rallies
            current_rally_id = self.rally_id_counter if self.current_rally_shots else -1

            self.foot_position_data.append({
                'x': pixel_x,
                'y': pixel_y,
                'frame': frame_number,
                'timestamp': timestamp,
                'rally_id': current_rally_id,
                'normalized_x': mid_x,
                'normalized_y': mid_y
            })

    def extract_court_region(self, frame: np.ndarray) -> np.ndarray:
        """Extract only the court region from frame"""
        mask = self.court.create_mask(frame.shape)

        # Apply mask
        masked_frame = cv2.bitwise_and(frame, frame, mask=mask)

        # Optionally crop to bounding rect for efficiency
        x, y, w, h = self.court.get_bounding_rect()
        cropped = masked_frame[y:y+h, x:x+w]

        return cropped, (x, y)  # Return crop offset for coordinate adjustment

    def detect_motion(self, frame: np.ndarray) -> bool:
        """Detect if there's significant motion in the court area"""
        # Get court region
        x, y, cw, ch = self.court.get_bounding_rect()
        court_region = frame[y:y+ch, x:x+cw]

        # Convert to grayscale
        gray = cv2.cvtColor(court_region, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_gray is None:
            self.prev_gray = gray
            return True  # Assume motion on first frame

        # Calculate frame difference
        frame_diff = cv2.absdiff(self.prev_gray, gray)
        _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)

        # Count changed pixels
        motion_pixels = cv2.countNonZero(thresh)

        self.prev_gray = gray

        return motion_pixels > self.motion_threshold

    def analyze_pose_in_court(self, frame: np.ndarray) -> Tuple[Optional[any], Optional[Tuple]]:
        """Detect pose only within court boundaries with optimizations"""
        h, w = frame.shape[:2]

        # Optimization 1: Crop to court region first
        x, y, cw, ch = self.court.get_bounding_rect()
        # Add some padding around court
        pad = 50
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(w, x + cw + pad)
        y2 = min(h, y + ch + pad)
        court_frame = frame[y1:y2, x1:x2]

        court_h, court_w = court_frame.shape[:2]

        # Optimization 2: Resize for faster processing
        if court_w > self.processing_width:
            scale = self.processing_width / court_w
            process_frame = cv2.resize(court_frame, (self.processing_width, int(court_h * scale)))
        else:
            scale = 1.0
            process_frame = court_frame

        # Convert to RGB for MediaPipe
        frame_rgb = cv2.cvtColor(process_frame, cv2.COLOR_BGR2RGB)

        # Run pose detection on smaller frame
        results = self.pose.process(frame_rgb)

        if not results.pose_landmarks:
            return None, None

        landmarks = results.pose_landmarks.landmark

        # Scale coordinates back to full frame
        # Landmarks are normalized (0-1) relative to the processed frame
        # We need to map them back to full frame coordinates

        # Get player center (hip midpoint) in full frame coordinates
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]

        # Convert from processed frame coords to full frame coords
        # processed_x * process_width / scale + x1 = full_frame_x
        center_x = int((left_hip.x + right_hip.x) / 2 * (court_w) + x1)
        center_y = int((left_hip.y + right_hip.y) / 2 * (court_h) + y1)

        # Check if player center is inside court
        if not self.court.is_point_inside((center_x, center_y)):
            return None, None  # Player outside court, ignore

        # Calculate player bounding box in full frame coordinates
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

        # Double check bbox is inside court
        if not self.court.is_bbox_inside(player_bbox, threshold=0.3):
            return None, None

        # Store the coordinate transformation info for drawing
        self._last_transform = {
            'x1': x1, 'y1': y1,
            'court_w': court_w, 'court_h': court_h,
            'scale': scale
        }

        return results.pose_landmarks, player_bbox

    def analyze_movement(self, pose_landmarks) -> dict:
        """Analyze player movement from pose landmarks"""
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

        # Current pose state (normalized coordinates 0-1, y increases downward)
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

        # Debug: Log positions occasionally to understand the data
        if len(self.pose_history) % 30 == 0:  # Every 30 frames
            logger.debug(f"Pose - Wrist Y: {right_wrist.y:.3f}, Shoulder Y: {right_shoulder.y:.3f}, "
                        f"Hip Y: {current_state['hip_center'][1]:.3f}")

        # Calculate velocities if we have history
        movement_data = {
            'wrist_velocity': 0.0,
            'body_velocity': 0.0,
            'wrist_direction': 'none',  # up, down, left, right
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
            movement_data['swing_type'] = self.classify_swing(
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

    def classify_swing(self, wrist_vel: float, wrist_dir: str,
                       pose_state: dict, wrist_dy: float) -> str:
        """Classify the type of swing based on movement"""

        # Threshold for significant movement - need meaningful motion to classify as a shot
        if wrist_vel < 0.03:
            return 'static'

        wrist_y = pose_state['wrist'][1]
        wrist_x = pose_state['wrist'][0]
        shoulder_y = pose_state['shoulder'][1]
        shoulder_x = pose_state['shoulder'][0]
        elbow_y = pose_state['elbow'][1]
        hip_y = pose_state['hip_center'][1]

        # Calculate arm extension (how far wrist is from shoulder)
        arm_extension = math.sqrt((wrist_x - shoulder_x)**2 + (wrist_y - shoulder_y)**2)

        # Overhead position (wrist clearly above shoulder)
        is_overhead = wrist_y < shoulder_y - 0.08

        # Wrist is very low (below hip level) - potential net shot position
        is_low_position = wrist_y > hip_y - 0.1

        # Arm is extended forward (wrist far from shoulder horizontally)
        is_arm_extended = arm_extension > 0.15

        # === OVERHEAD SHOTS (smash, clear, drop) ===
        # High velocity + upward movement + overhead position = power shot
        if wrist_vel > 0.06 and wrist_dir == 'up' and is_overhead:
            return 'power_overhead'

        # Moderate velocity + overhead position + upward or forward motion
        if wrist_vel > 0.04 and is_overhead and wrist_dir in ['up', 'left', 'right']:
            return 'gentle_overhead'

        # === DRIVE SHOTS ===
        # Fast horizontal movement at mid-body height
        if wrist_vel > 0.05 and wrist_dir in ['left', 'right']:
            # Wrist roughly between shoulder and hip
            if shoulder_y < wrist_y < hip_y:
                return 'drive'

        # === NET SHOTS ===
        # Must be: low position + arm extended + moderate forward/down movement
        # Net shots are gentle, controlled - not fast swings
        if is_low_position and is_arm_extended:
            if wrist_vel > 0.03 and wrist_vel < 0.12:  # Gentle movement, not a smash
                if wrist_dir in ['down', 'left', 'right']:  # Forward or slight down
                    return 'net_play'

        # === DEFENSIVE/LIFT SHOTS ===
        # Low position + upward movement = lifting the shuttle
        if is_low_position and wrist_dir == 'up' and wrist_vel > 0.04:
            return 'lift'

        # === PREPARATION/RECOVERY ===
        # Some movement but doesn't match shot patterns
        if wrist_vel > 0.025:
            return 'movement'

        return 'ready'

    def classify_shot(self, movement_data: dict, pose_landmarks) -> Tuple[str, float]:
        """Classify shot type from movement data"""

        swing_type = movement_data.get('swing_type', 'none')
        wrist_vel = movement_data.get('wrist_velocity', 0)

        # Map swing type to shot type
        if swing_type == 'power_overhead':
            # High velocity overhead = smash, lower velocity = clear
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
            # Defensive lift from low position
            return 'lift', min(0.7, 0.4 + wrist_vel * 4)

        elif swing_type == 'movement':
            return 'preparation', 0.4

        elif swing_type == 'ready':
            return 'ready_position', 0.5

        else:
            return 'static', 0.3

    def analyze_frame(self, frame: np.ndarray, frame_number: int,
                      timestamp: float) -> Tuple[Optional[ShotData], any]:
        """Analyze a single frame within court boundaries

        Returns: (shot_data, pose_landmarks)
        """

        self.total_frames_processed += 1

        # Detect pose within court
        pose_landmarks, player_bbox = self.analyze_pose_in_court(frame)

        if pose_landmarks is None:
            self.frames_since_last_shot += 1
            return None, None

        self.player_detected_frames += 1

        # Accumulate foot position for heatmap
        self._accumulate_foot_position(pose_landmarks, frame_number, timestamp)

        # Analyze movement
        movement_data = self.analyze_movement(pose_landmarks)

        # Classify shot
        shot_type, confidence = self.classify_shot(movement_data, pose_landmarks)

        # Get wrist position for visualization
        h, w = frame.shape[:2]
        wrist = pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        wrist_pos = (int(wrist.x * w), int(wrist.y * h))

        # Create shot data
        shot_data = ShotData(
            frame_number=frame_number,
            timestamp=timestamp,
            shot_type=shot_type,
            confidence=confidence,
            player_bbox=player_bbox,
            wrist_position=wrist_pos,
            coaching_tip=self.get_coaching_tip(shot_type) if shot_type not in ['static', 'ready_position', 'preparation'] else "",
            movement_data=movement_data
        )

        # Track actual shots (not static/ready/preparation positions)
        actual_shots = ['smash', 'clear', 'drop_shot', 'net_shot', 'drive', 'lift']
        if shot_type in actual_shots and confidence > 0.5:
            self.shot_history.append(shot_data)
            self.session_stats[shot_type] += 1
            self.last_shot_frame = frame_number
            self.frames_since_last_shot = 0

            # Rally tracking
            self.current_rally_shots.append(shot_data)

            logger.info(f"Frame {frame_number}: {shot_type} (confidence: {confidence:.2f})")
        else:
            self.frames_since_last_shot += 1

        # Check if rally ended (gap in shots)
        if (self.frames_since_last_shot > self.rally_gap_threshold and
            len(self.current_rally_shots) > 0):
            self.end_current_rally()

        return shot_data, pose_landmarks

    def end_current_rally(self):
        """End the current rally and save it"""
        if len(self.current_rally_shots) < 2:
            # Not enough shots for a rally
            self.current_rally_shots = []
            return

        self.rally_id_counter += 1

        rally = RallyData(
            rally_id=self.rally_id_counter,
            start_frame=self.current_rally_shots[0].frame_number,
            end_frame=self.current_rally_shots[-1].frame_number,
            start_time=self.current_rally_shots[0].timestamp,
            end_time=self.current_rally_shots[-1].timestamp,
            shots=self.current_rally_shots.copy()
        )

        self.rally_history.append(rally)
        logger.info(f"Rally {rally.rally_id} ended: {rally.shot_count} shots, {rally.duration:.1f}s")

        self.current_rally_shots = []

    def draw_court_boundary(self, frame: np.ndarray) -> np.ndarray:
        """Draw court boundary overlay"""
        polygon = self.court.get_polygon()

        # Draw filled semi-transparent overlay
        overlay = frame.copy()

        # Court color based on setting
        color_map = {
            'green': (0, 100, 0),
            'blue': (100, 50, 0),
            'wood': (50, 100, 150),
            'other': (100, 100, 100)
        }
        fill_color = color_map.get(self.court.court_color, (100, 100, 100))

        cv2.fillPoly(overlay, [polygon], fill_color)
        cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)

        # Draw boundary lines
        cv2.polylines(frame, [polygon], True, (0, 255, 255), 2)

        # Draw corner markers
        for corner in [self.court.top_left, self.court.top_right,
                       self.court.bottom_left, self.court.bottom_right]:
            cv2.circle(frame, corner, 8, (0, 255, 255), -1)
            cv2.circle(frame, corner, 10, (255, 255, 255), 2)

        return frame

    def draw_annotations(self, frame: np.ndarray, shot_data: Optional[ShotData],
                         pose_landmarks) -> np.ndarray:
        """Draw all annotations on frame"""

        # Draw court boundary
        frame = self.draw_court_boundary(frame)

        # Draw pose if detected
        if pose_landmarks:
            # Color based on shot type
            if shot_data:
                active_shots = ['smash', 'clear', 'drop_shot', 'net_shot', 'drive', 'lift']
                if shot_data.shot_type in active_shots:
                    pose_color = (0, 255, 0)  # Green for active shots
                elif shot_data.shot_type == 'ready_position':
                    pose_color = (0, 255, 255)  # Yellow for ready
                else:
                    pose_color = (128, 128, 128)  # Gray for static
            else:
                pose_color = (128, 128, 128)

            # Draw skeleton connections
            self.mp_drawing.draw_landmarks(
                frame, pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=pose_color, thickness=2, circle_radius=3),
                self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
            )

            # Draw body part labels
            self.draw_body_part_labels(frame, pose_landmarks)

        # Draw shot info
        if shot_data:
            self.draw_shot_info(frame, shot_data)

        # Draw stats panel
        self.draw_stats_panel(frame)

        return frame

    def draw_body_part_labels(self, frame: np.ndarray, pose_landmarks) -> None:
        """Draw labels for each detected body part"""
        h, w = frame.shape[:2]
        landmarks = pose_landmarks.landmark

        # Define which body parts to label with their MediaPipe indices
        # Using shorter labels to reduce clutter
        body_parts = {
            # Upper body - right side (dominant for badminton)
            self.mp_pose.PoseLandmark.RIGHT_WRIST: ("R.Wrist", (0, 255, 255)),      # Yellow
            self.mp_pose.PoseLandmark.RIGHT_ELBOW: ("R.Elbow", (0, 200, 255)),      # Orange
            self.mp_pose.PoseLandmark.RIGHT_SHOULDER: ("R.Shoulder", (0, 150, 255)), # Red-orange

            # Upper body - left side
            self.mp_pose.PoseLandmark.LEFT_WRIST: ("L.Wrist", (255, 255, 0)),       # Cyan
            self.mp_pose.PoseLandmark.LEFT_ELBOW: ("L.Elbow", (255, 200, 0)),       # Light blue
            self.mp_pose.PoseLandmark.LEFT_SHOULDER: ("L.Shoulder", (255, 150, 0)), # Blue

            # Core
            self.mp_pose.PoseLandmark.RIGHT_HIP: ("R.Hip", (0, 255, 0)),            # Green
            self.mp_pose.PoseLandmark.LEFT_HIP: ("L.Hip", (0, 255, 100)),           # Light green

            # Lower body
            self.mp_pose.PoseLandmark.RIGHT_KNEE: ("R.Knee", (255, 0, 255)),        # Magenta
            self.mp_pose.PoseLandmark.LEFT_KNEE: ("L.Knee", (255, 100, 255)),       # Pink
            self.mp_pose.PoseLandmark.RIGHT_ANKLE: ("R.Ankle", (128, 0, 255)),      # Purple
            self.mp_pose.PoseLandmark.LEFT_ANKLE: ("L.Ankle", (128, 100, 255)),     # Light purple

            # Head
            self.mp_pose.PoseLandmark.NOSE: ("Nose", (255, 255, 255)),              # White
        }

        for landmark_id, (label, color) in body_parts.items():
            landmark = landmarks[landmark_id]

            # Only draw if landmark is visible enough
            if landmark.visibility > 0.5:
                # Convert normalized coordinates to pixel coordinates
                x = int(landmark.x * w)
                y = int(landmark.y * h)

                # Draw a larger circle for the landmark
                cv2.circle(frame, (x, y), 6, color, -1)
                cv2.circle(frame, (x, y), 8, (255, 255, 255), 1)

                # Draw label with background for readability
                label_with_coords = f"{label}"
                font_scale = 0.4
                thickness = 1

                # Get text size for background
                (text_w, text_h), baseline = cv2.getTextSize(
                    label_with_coords, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
                )

                # Position label slightly offset from the point
                label_x = x + 10
                label_y = y - 5

                # Draw background rectangle
                cv2.rectangle(
                    frame,
                    (label_x - 2, label_y - text_h - 2),
                    (label_x + text_w + 2, label_y + 2),
                    (0, 0, 0),
                    -1
                )

                # Draw text
                cv2.putText(
                    frame, label_with_coords,
                    (label_x, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale, color, thickness
                )

        # Draw computed points (hip center, shoulder center)
        self.draw_computed_points(frame, landmarks, h, w)

    def draw_computed_points(self, frame: np.ndarray, landmarks, h: int, w: int) -> None:
        """Draw computed reference points used in shot classification"""

        # Get landmarks for computed points
        r_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        l_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        r_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]
        l_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]

        # Calculate centers
        shoulder_center_x = int((r_shoulder.x + l_shoulder.x) / 2 * w)
        shoulder_center_y = int((r_shoulder.y + l_shoulder.y) / 2 * h)
        hip_center_x = int((r_hip.x + l_hip.x) / 2 * w)
        hip_center_y = int((r_hip.y + l_hip.y) / 2 * h)

        # Draw shoulder center
        cv2.circle(frame, (shoulder_center_x, shoulder_center_y), 8, (0, 255, 255), 2)
        cv2.putText(frame, "ShoulderCenter", (shoulder_center_x + 10, shoulder_center_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

        # Draw hip center
        cv2.circle(frame, (hip_center_x, hip_center_y), 8, (0, 255, 0), 2)
        cv2.putText(frame, "HipCenter", (hip_center_x + 10, hip_center_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        # Draw vertical reference line (body axis)
        cv2.line(frame, (shoulder_center_x, shoulder_center_y),
                (hip_center_x, hip_center_y), (100, 100, 100), 1, cv2.LINE_AA)

        # Draw horizontal reference lines for shot classification zones
        # These help visualize the zones used in classify_swing()

        # Line at shoulder level (overhead zone above this)
        cv2.line(frame, (0, shoulder_center_y), (w, shoulder_center_y),
                (50, 50, 150), 1, cv2.LINE_AA)
        cv2.putText(frame, "Shoulder Line", (w - 100, shoulder_center_y - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.35, (50, 50, 150), 1)

        # Line at hip level (low zone below this)
        cv2.line(frame, (0, hip_center_y), (w, hip_center_y),
                (50, 150, 50), 1, cv2.LINE_AA)
        cv2.putText(frame, "Hip Line", (w - 70, hip_center_y - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.35, (50, 150, 50), 1)

        # Show wrist position relative to these lines
        r_wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        wrist_x = int(r_wrist.x * w)
        wrist_y = int(r_wrist.y * h)

        # Determine zone
        if wrist_y < shoulder_center_y - 20:
            zone = "OVERHEAD"
            zone_color = (0, 0, 255)  # Red
        elif wrist_y > hip_center_y - 10:
            zone = "LOW"
            zone_color = (255, 165, 0)  # Orange
        else:
            zone = "MID"
            zone_color = (0, 255, 0)  # Green

        # Draw zone indicator near wrist
        cv2.putText(frame, f"[{zone}]", (wrist_x + 15, wrist_y + 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, zone_color, 2)

    def draw_shot_info(self, frame: np.ndarray, shot_data: ShotData):
        """Draw shot information overlay"""
        h, w = frame.shape[:2]

        # Shot type display
        if shot_data.shot_type not in ['static', 'preparation']:
            # Background box
            text = f"{shot_data.shot_type.upper()} ({shot_data.confidence:.0%})"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]

            x, y = 10, 40
            cv2.rectangle(frame, (x-5, y-30), (x + text_size[0] + 5, y + 5), (0, 0, 0), -1)

            # Color based on shot type
            colors = {
                'smash': (0, 0, 255),       # Red
                'clear': (0, 255, 0),       # Green
                'drop_shot': (255, 165, 0), # Orange
                'net_shot': (255, 255, 0),  # Cyan
                'drive': (255, 0, 255),     # Magenta
                'lift': (255, 200, 100),    # Light blue
                'ready_position': (0, 255, 255)  # Yellow
            }
            color = colors.get(shot_data.shot_type, (255, 255, 255))

            cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

            # Coaching tip
            if shot_data.coaching_tip:
                tip_y = y + 35
                cv2.putText(frame, f"Tip: {shot_data.coaching_tip}", (x, tip_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Draw player bbox
        if shot_data.player_bbox:
            x1, y1, x2, y2 = shot_data.player_bbox
            bbox_color = (0, 255, 0) if shot_data.shot_type not in ['static', 'preparation'] else (128, 128, 128)
            cv2.rectangle(frame, (x1, y1), (x2, y2), bbox_color, 2)

        # Draw wrist position with movement vector
        if shot_data.wrist_position and shot_data.movement_data:
            wx, wy = shot_data.wrist_position
            wrist_vel = shot_data.movement_data.get('wrist_velocity', 0)

            # Circle size based on velocity
            radius = max(5, min(20, int(wrist_vel * 200)))
            cv2.circle(frame, (wx, wy), radius, (0, 255, 255), -1)

    def draw_stats_panel(self, frame: np.ndarray):
        """Draw statistics panel"""
        h, w = frame.shape[:2]

        # Panel position (bottom left)
        panel_x, panel_y = 10, h - 120
        panel_w, panel_h = 280, 110

        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, panel_y),
                     (panel_x + panel_w, panel_y + panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Border
        cv2.rectangle(frame, (panel_x, panel_y),
                     (panel_x + panel_w, panel_y + panel_h), (255, 255, 255), 1)

        # Title
        cv2.putText(frame, "SESSION STATS", (panel_x + 10, panel_y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Stats
        y_offset = panel_y + 50
        line_height = 18

        stats_text = [
            f"Shots: {len(self.shot_history)} | Rallies: {len(self.rally_history)}",
            f"Smash: {self.session_stats.get('smash', 0)} | Clear: {self.session_stats.get('clear', 0)}",
            f"Drop: {self.session_stats.get('drop_shot', 0)} | Drive: {self.session_stats.get('drive', 0)}",
            f"Net: {self.session_stats.get('net_shot', 0)} | Lift: {self.session_stats.get('lift', 0)}",
        ]

        for text in stats_text:
            cv2.putText(frame, text, (panel_x + 10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            y_offset += line_height

    def analyze_video(self, video_path: str, output_path: Optional[str] = None,
                      show_live: bool = False) -> dict:
        """Analyze video within court boundaries"""

        logger.info(f"Starting analysis: {video_path}")
        logger.info(f"Court boundary: {self.court.get_bounding_rect()}")
        logger.info(f"Processing every {self.process_every_n_frames} frame(s) for pose")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        # Video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(f"Video: {total_frames} frames, {fps} FPS, {width}x{height}")

        # Video writer
        out = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_number = 0
        last_shot_data = None
        last_pose_landmarks = None
        frames_skipped_motion = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                timestamp = frame_number / fps

                # Decide whether to process this frame
                should_process = False

                if frame_number % self.process_every_n_frames == 0:
                    # Check motion if skip_static_frames is enabled
                    if self.skip_static_frames:
                        if self.detect_motion(frame):
                            should_process = True
                        else:
                            frames_skipped_motion += 1
                    else:
                        should_process = True

                if should_process:
                    shot_data, pose_landmarks = self.analyze_frame(frame, frame_number, timestamp)
                    if shot_data:
                        last_shot_data = shot_data
                    if pose_landmarks:
                        last_pose_landmarks = pose_landmarks
                else:
                    # Use cached data for skipped frames
                    shot_data = last_shot_data
                    pose_landmarks = last_pose_landmarks

                # Draw annotations
                annotated_frame = self.draw_annotations(frame, shot_data, pose_landmarks)

                # Live display
                if show_live:
                    # Resize for display if too large
                    display_frame = annotated_frame
                    if width > 1280:
                        scale = 1280 / width
                        display_frame = cv2.resize(annotated_frame,
                                                   (int(width * scale), int(height * scale)))

                    cv2.imshow('Badminton Analysis - Press Q to quit', display_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        logger.info("User quit")
                        break

                # Save frame (always full resolution)
                if out:
                    out.write(annotated_frame)

                frame_number += 1

                # Progress update
                if frame_number % (fps * 3) == 0:
                    progress = (frame_number / total_frames) * 100
                    skip_info = f" | Static skipped: {frames_skipped_motion}" if self.skip_static_frames else ""
                    logger.info(f"Progress: {progress:.1f}% | Shots: {len(self.shot_history)}{skip_info}")

                    # Write progress to file for external monitoring
                    if hasattr(self, 'progress_file') and self.progress_file:
                        try:
                            with open(self.progress_file, 'w') as f:
                                json.dump({
                                    'progress': progress,
                                    'shots': len(self.shot_history),
                                    'frame': frame_number,
                                    'total_frames': total_frames,
                                    'message': f"Processing: {progress:.1f}% ({len(self.shot_history)} shots detected)"
                                }, f)
                        except Exception:
                            pass

        except KeyboardInterrupt:
            logger.info("Analysis interrupted")

        finally:
            # End any remaining rally
            if self.current_rally_shots:
                self.end_current_rally()

            cap.release()
            if out:
                out.release()
            if show_live:
                cv2.destroyAllWindows()

        # Generate movement heatmap
        video_name = Path(video_path).stem if video_path else None
        heatmap_result = self.generate_movement_heatmap(video_name)

        report = self.generate_report()
        if heatmap_result:
            report['heatmap_image_path'] = heatmap_result['image_path']
            report['heatmap_data_path'] = heatmap_result['data_path']

        return report

    def generate_report(self) -> dict:
        """Generate analysis report"""

        if not self.shot_history:
            return {
                'message': 'No shots detected',
                'frames_processed': self.total_frames_processed,
                'player_detected_frames': self.player_detected_frames
            }

        # Shot statistics
        shot_counts = dict(self.session_stats)
        total_shots = len(self.shot_history)

        # Rally statistics
        rally_stats = []
        for rally in self.rally_history:
            rally_stats.append({
                'rally_id': rally.rally_id,
                'duration': rally.duration,
                'shot_count': rally.shot_count,
                'shots': [s.shot_type for s in rally.shots]
            })

        # Timeline
        shot_timeline = [
            {'time': s.timestamp, 'shot': s.shot_type, 'confidence': s.confidence}
            for s in self.shot_history
        ]

        report = {
            'summary': {
                'total_shots': total_shots,
                'total_rallies': len(self.rally_history),
                'frames_processed': self.total_frames_processed,
                'player_detection_rate': self.player_detected_frames / self.total_frames_processed if self.total_frames_processed > 0 else 0,
                'avg_confidence': np.mean([s.confidence for s in self.shot_history]),
                'foot_positions_recorded': len(self.foot_position_history)
            },
            'shot_distribution': shot_counts,
            'rallies': rally_stats,
            'shot_timeline': shot_timeline,
            'court_settings': self.court.to_dict()
        }

        return report

    def save_report(self, report: dict, video_name: str = None) -> str:
        """Save report to JSON file in analysis_output folder"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if video_name:
            filename = OUTPUT_DIR / f"report_{video_name}_{timestamp}.json"
        else:
            filename = OUTPUT_DIR / f"report_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Report saved: {filename}")
        return str(filename)

    def generate_movement_heatmap(self, video_name: str = None) -> Optional[dict]:
        """Generate movement heatmap from accumulated foot positions

        Returns dict with 'image_path' and 'data_path' keys
        """
        if len(self.foot_position_history) < 10:
            logger.warning("Not enough foot positions recorded for heatmap generation")
            return None

        generator = MovementHeatmapGenerator(self.court)
        heatmap_image = generator.generate_heatmap(self.foot_position_history)

        if heatmap_image is None:
            return None

        # Save heatmap image and data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"heatmap_{video_name}_{timestamp}" if video_name else f"heatmap_{timestamp}"

        image_path = OUTPUT_DIR / f"{base_name}.png"
        data_path = OUTPUT_DIR / f"{base_name}_data.json"

        # Save image
        cv2.imwrite(str(image_path), heatmap_image)
        logger.info(f"Movement heatmap saved: {image_path}")

        # Save raw data for custom visualizations
        heatmap_data = {
            'metadata': {
                'video_name': video_name,
                'timestamp': timestamp,
                'total_positions': len(self.foot_position_data),
                'total_rallies': len(self.rally_history),
                'court_boundary': self.court.to_dict()
            },
            'positions': self.foot_position_data,
            'rallies': [
                {
                    'rally_id': r.rally_id,
                    'start_frame': r.start_frame,
                    'end_frame': r.end_frame,
                    'start_time': r.start_time,
                    'end_time': r.end_time,
                    'shot_count': r.shot_count
                }
                for r in self.rally_history
            ]
        }

        with open(data_path, 'w') as f:
            json.dump(heatmap_data, f, indent=2)
        logger.info(f"Movement data saved: {data_path}")

        return {
            'image_path': str(image_path),
            'data_path': str(data_path)
        }


@dataclass
class HeatmapConfig:
    """Configuration for heatmap generation"""
    output_width: int = 800
    output_height: int = 600
    grid_resolution: int = 50  # Number of bins in each dimension
    blur_sigma: float = 2.0  # Gaussian blur sigma for smoothing
    colormap: int = cv2.COLORMAP_HOT  # OpenCV colormap


class MovementHeatmapGenerator:
    """Generates movement heatmap from foot position data"""

    def __init__(self, court: CourtBoundary, config: HeatmapConfig = None):
        self.court = court
        self.config = config or HeatmapConfig()

    def _get_perspective_transform(self) -> np.ndarray:
        """Get perspective transform matrix to normalize court to rectangle"""
        # Source points: court corners (trapezoid shape from camera angle)
        src_points = np.array([
            self.court.top_left,
            self.court.top_right,
            self.court.bottom_right,
            self.court.bottom_left
        ], dtype=np.float32)

        # Destination: normalized rectangle
        dst_points = np.array([
            [0, 0],
            [self.config.grid_resolution - 1, 0],
            [self.config.grid_resolution - 1, self.config.grid_resolution - 1],
            [0, self.config.grid_resolution - 1]
        ], dtype=np.float32)

        return cv2.getPerspectiveTransform(src_points, dst_points)

    def _transform_points(self, points: List[Tuple[int, int]], transform: np.ndarray) -> np.ndarray:
        """Transform points using perspective matrix"""
        if not points:
            return np.array([])

        pts = np.array(points, dtype=np.float32).reshape(-1, 1, 2)
        transformed = cv2.perspectiveTransform(pts, transform)
        return transformed.reshape(-1, 2)

    def generate_heatmap(self, foot_positions: List[Tuple[int, int]]) -> Optional[np.ndarray]:
        """Generate heatmap image from foot positions"""
        if len(foot_positions) < 10:
            return None

        # Get perspective transform
        transform = self._get_perspective_transform()

        # Transform points to normalized court coordinates
        transformed_points = self._transform_points(foot_positions, transform)

        if len(transformed_points) == 0:
            return None

        # Create 2D histogram
        grid_res = self.config.grid_resolution
        heatmap, _, _ = np.histogram2d(
            transformed_points[:, 1],  # Y coordinates
            transformed_points[:, 0],  # X coordinates
            bins=[grid_res, grid_res],
            range=[[0, grid_res], [0, grid_res]]
        )

        # Apply Gaussian blur for smoothing
        if self.config.blur_sigma > 0:
            heatmap = cv2.GaussianBlur(
                heatmap.astype(np.float32),
                (0, 0),
                self.config.blur_sigma
            )

        # Normalize to 0-255
        if heatmap.max() > 0:
            heatmap_normalized = (heatmap / heatmap.max() * 255).astype(np.uint8)
        else:
            heatmap_normalized = heatmap.astype(np.uint8)

        # Apply colormap (COLORMAP_HOT: black -> red -> yellow -> white)
        heatmap_colored = cv2.applyColorMap(heatmap_normalized, self.config.colormap)

        # Resize to output dimensions
        heatmap_resized = cv2.resize(
            heatmap_colored,
            (self.config.output_width, self.config.output_height),
            interpolation=cv2.INTER_CUBIC
        )

        # Add court lines overlay
        heatmap_with_court = self._draw_court_lines(heatmap_resized)

        # Add legend and statistics
        final_image = self._add_legend_and_stats(heatmap_with_court, foot_positions, heatmap)

        return final_image

    def _draw_court_lines(self, image: np.ndarray) -> np.ndarray:
        """Draw court boundary lines on the heatmap"""
        h, w = image.shape[:2]

        # Court outline (rectangle since we've normalized the perspective)
        margin = 10
        court_rect = [
            (margin, margin),
            (w - margin, margin),
            (w - margin, h - margin),
            (margin, h - margin)
        ]

        # Draw court outline
        pts = np.array(court_rect, dtype=np.int32)
        cv2.polylines(image, [pts], True, (255, 255, 255), 2)

        # Draw center line (horizontal)
        cv2.line(image, (margin, h // 2), (w - margin, h // 2), (255, 255, 255), 1)

        # Draw service line (approximately 1/3 from front)
        service_y = h // 3
        cv2.line(image, (margin, service_y), (w - margin, service_y), (200, 200, 200), 1)

        # Draw center vertical line
        cv2.line(image, (w // 2, margin), (w // 2, h - margin), (200, 200, 200), 1)

        return image

    def _add_legend_and_stats(self, image: np.ndarray, positions: List[Tuple[int, int]],
                              histogram: np.ndarray) -> np.ndarray:
        """Add color legend and statistics to the heatmap"""
        h, w = image.shape[:2]

        # Create a larger canvas to accommodate legend
        canvas_height = h + 80
        canvas = np.zeros((canvas_height, w, 3), dtype=np.uint8)
        canvas[0:h, 0:w] = image

        # Draw title
        title = "Player Movement Heatmap"
        cv2.putText(canvas, title, (10, h + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Draw color legend bar
        legend_x = 10
        legend_y = h + 40
        legend_width = 200
        legend_height = 15

        # Create gradient for legend
        for i in range(legend_width):
            val = int(i / legend_width * 255)
            color = cv2.applyColorMap(np.array([[val]], dtype=np.uint8), self.config.colormap)[0, 0]
            cv2.line(canvas,
                    (legend_x + i, legend_y),
                    (legend_x + i, legend_y + legend_height),
                    color.tolist(), 1)

        # Legend labels
        cv2.putText(canvas, "Low", (legend_x, legend_y + legend_height + 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.putText(canvas, "High", (legend_x + legend_width - 25, legend_y + legend_height + 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        # Statistics
        stats_x = 250
        stats_text = f"Positions recorded: {len(positions)}"
        cv2.putText(canvas, stats_text, (stats_x, h + 55),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Peak zone info
        if histogram.max() > 0:
            peak_y, peak_x = np.unravel_index(histogram.argmax(), histogram.shape)
            zone_names = ["Front", "Mid", "Back"]
            zone_idx = min(2, peak_y * 3 // self.config.grid_resolution)
            zone_text = f"Most active zone: {zone_names[zone_idx]} court"
            cv2.putText(canvas, zone_text, (stats_x, h + 75),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        return canvas


class CourtSelector:
    """Interactive court boundary selector using mouse clicks"""

    def __init__(self, frame: np.ndarray, window_name: str = "Select Court Corners"):
        self.frame = frame.copy()
        self.original_frame = frame.copy()
        self.window_name = window_name
        self.points = []  # Store clicked points
        self.point_labels = ['Top-Left', 'Top-Right', 'Bottom-Right', 'Bottom-Left']
        self.colors = [(0, 255, 0), (0, 255, 255), (0, 165, 255), (0, 0, 255)]  # Different color per point
        self.done = False
        self.h, self.w = frame.shape[:2]

    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse click events"""
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.points) < 4:
                self.points.append((x, y))
                self.update_display()

                if len(self.points) == 4:
                    self.done = True

        elif event == cv2.EVENT_MOUSEMOVE:
            # Show crosshair and coordinates at cursor
            self.update_display(cursor_pos=(x, y))

    def update_display(self, cursor_pos: Optional[Tuple[int, int]] = None):
        """Update the display with current points and instructions"""
        self.frame = self.original_frame.copy()
        h, w = self.frame.shape[:2]

        # Draw instruction box at top
        cv2.rectangle(self.frame, (0, 0), (w, 60), (0, 0, 0), -1)

        if len(self.points) < 4:
            next_point = self.point_labels[len(self.points)]
            instruction = f"Click to select: {next_point} ({len(self.points)+1}/4)"
            color = self.colors[len(self.points)]
        else:
            instruction = "All points selected! Press ENTER to confirm, R to reset"
            color = (0, 255, 0)

        cv2.putText(self.frame, instruction, (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(self.frame, "Press ESC to cancel, R to reset points", (10, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Draw cursor position and crosshair
        if cursor_pos:
            cx, cy = cursor_pos
            # Crosshair
            cv2.line(self.frame, (cx, 60), (cx, h), (100, 100, 100), 1)
            cv2.line(self.frame, (0, cy), (w, cy), (100, 100, 100), 1)
            # Coordinate display
            coord_text = f"({cx}, {cy})"
            cv2.putText(self.frame, coord_text, (cx + 10, cy - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Draw clicked points
        for i, point in enumerate(self.points):
            # Circle
            cv2.circle(self.frame, point, 8, self.colors[i], -1)
            cv2.circle(self.frame, point, 10, (255, 255, 255), 2)
            # Label
            label = f"{self.point_labels[i]} ({point[0]}, {point[1]})"
            cv2.putText(self.frame, label, (point[0] + 15, point[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors[i], 2)

        # Draw lines connecting points
        if len(self.points) >= 2:
            for i in range(len(self.points)):
                if i < len(self.points) - 1:
                    cv2.line(self.frame, self.points[i], self.points[i+1], (0, 255, 255), 2)

            # Close the polygon if we have all 4 points
            if len(self.points) == 4:
                cv2.line(self.frame, self.points[3], self.points[0], (0, 255, 255), 2)

                # Fill with semi-transparent overlay
                overlay = self.frame.copy()
                polygon = np.array(self.points, dtype=np.int32)
                cv2.fillPoly(overlay, [polygon], (0, 255, 0))
                cv2.addWeighted(overlay, 0.3, self.frame, 0.7, 0, self.frame)

        cv2.imshow(self.window_name, self.frame)

    def select(self) -> Optional[List[Tuple[int, int]]]:
        """Run the interactive selection. Returns list of 4 points or None if cancelled."""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, min(1280, self.w), min(720, self.h))
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        self.update_display()

        while True:
            key = cv2.waitKey(1) & 0xFF

            if key == 27:  # ESC - cancel
                cv2.destroyWindow(self.window_name)
                return None

            elif key == ord('r') or key == ord('R'):  # Reset
                self.points = []
                self.done = False
                self.update_display()

            elif key == 13 or key == 10:  # Enter - confirm
                if len(self.points) == 4:
                    cv2.destroyWindow(self.window_name)
                    return self.points

        return None


def get_reference_frame(video_path: str) -> Tuple[np.ndarray, float]:
    """Let user select which frame to use for court selection"""

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    print(f"\nVideo duration: {duration:.1f} seconds ({total_frames} frames)")
    print(f"FPS: {fps:.1f}")

    # Ask user for timestamp
    print("\nSelect timestamp for reference frame:")
    print("  - Enter seconds (e.g., '5' or '10.5')")
    print("  - Press Enter for frame 0")
    print("  - Enter 'browse' to scrub through video\n")

    while True:
        user_input = input("Timestamp (seconds): ").strip().lower()

        if user_input == '' or user_input == '0':
            timestamp = 0
            break

        elif user_input == 'browse':
            # Interactive frame browser
            frame, timestamp = browse_video_frames(cap, fps, total_frames)
            if frame is not None:
                cap.release()
                return frame, timestamp
            continue

        else:
            try:
                timestamp = float(user_input)
                if 0 <= timestamp <= duration:
                    break
                else:
                    print(f"  Timestamp must be between 0 and {duration:.1f}")
            except ValueError:
                print("  Invalid input. Enter a number or 'browse'")

    # Seek to timestamp
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError(f"Could not read frame at {timestamp}s")

    print(f"Using frame at {timestamp:.1f}s")
    return frame, timestamp


def browse_video_frames(cap: cv2.VideoCapture, fps: float, total_frames: int) -> Tuple[Optional[np.ndarray], float]:
    """Interactive video browser with trackbar"""

    window_name = "Video Browser - Use trackbar or arrow keys"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    current_frame = 0

    def on_trackbar(val):
        nonlocal current_frame
        current_frame = val

    cv2.createTrackbar("Frame", window_name, 0, total_frames - 1, on_trackbar)

    print("\nVideo Browser Controls:")
    print("  - Drag trackbar to scrub through video")
    print("  - Left/Right arrows: -/+ 1 frame")
    print("  - Up/Down arrows: -/+ 1 second")
    print("  - Enter: Select current frame")
    print("  - ESC: Cancel\n")

    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap.read()

        if not ret:
            current_frame = max(0, current_frame - 1)
            continue

        # Draw frame info
        display_frame = frame.copy()
        timestamp = current_frame / fps
        info_text = f"Frame: {current_frame}/{total_frames} | Time: {timestamp:.2f}s"

        cv2.rectangle(display_frame, (0, 0), (400, 35), (0, 0, 0), -1)
        cv2.putText(display_frame, info_text, (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        h, w = frame.shape[:2]
        cv2.resizeWindow(window_name, min(1280, w), min(720, h))
        cv2.imshow(window_name, display_frame)

        key = cv2.waitKey(30) & 0xFF

        if key == 27:  # ESC
            cv2.destroyWindow(window_name)
            return None, 0

        elif key == 13 or key == 10:  # Enter
            cv2.destroyWindow(window_name)
            return frame, timestamp

        elif key == 81 or key == 2:  # Left arrow
            current_frame = max(0, current_frame - 1)
            cv2.setTrackbarPos("Frame", window_name, current_frame)

        elif key == 83 or key == 3:  # Right arrow
            current_frame = min(total_frames - 1, current_frame + 1)
            cv2.setTrackbarPos("Frame", window_name, current_frame)

        elif key == 82 or key == 0:  # Up arrow (+1 second)
            current_frame = min(total_frames - 1, current_frame + int(fps))
            cv2.setTrackbarPos("Frame", window_name, current_frame)

        elif key == 84 or key == 1:  # Down arrow (-1 second)
            current_frame = max(0, current_frame - int(fps))
            cv2.setTrackbarPos("Frame", window_name, current_frame)

    return None, 0


def get_court_coordinates_interactive(video_path: str) -> CourtBoundary:
    """Interactive court boundary selection with click-to-select"""

    print("\n" + "=" * 60)
    print("COURT BOUNDARY SETUP")
    print("=" * 60)

    # Step 1: Get reference frame
    print("\nStep 1: Select reference frame")
    print("-" * 40)
    frame, timestamp = get_reference_frame(video_path)

    h, w = frame.shape[:2]
    print(f"\nVideo dimensions: {w}x{h}")

    # Step 2: Click to select corners
    print("\nStep 2: Click to select court corners")
    print("-" * 40)
    print("\nA window will open. Click the 4 corners of the half-court")
    print("in this order: Top-Left → Top-Right → Bottom-Right → Bottom-Left")
    print("\nControls:")
    print("  - Click: Select corner point")
    print("  - R: Reset all points")
    print("  - Enter: Confirm selection")
    print("  - ESC: Cancel")

    input("\nPress Enter to open the selection window...")

    # Run interactive selector
    selector = CourtSelector(frame)
    points = selector.select()

    if points is None:
        print("\nSelection cancelled.")
        retry = input("Try again? (y/n): ").lower().startswith('y')
        if retry:
            return get_court_coordinates_interactive(video_path)
        else:
            raise ValueError("Court selection cancelled")

    top_left, top_right, bottom_right, bottom_left = points

    # Step 3: Court color (optional)
    print("\nStep 3: Court color (optional)")
    print("-" * 40)
    print("Options: green, blue, wood, other")
    court_color = input("Court color (default: green): ").strip().lower()
    if court_color not in ['green', 'blue', 'wood', 'other']:
        court_color = 'green'

    # Create court boundary
    court = CourtBoundary(
        top_left=top_left,
        top_right=top_right,
        bottom_left=bottom_left,
        bottom_right=bottom_right,
        court_color=court_color
    )

    # Final preview
    print("\nFinal preview...")
    preview_frame = frame.copy()

    # Draw boundary
    polygon = court.get_polygon()
    cv2.polylines(preview_frame, [polygon], True, (0, 255, 255), 3)

    # Fill with transparency
    overlay = preview_frame.copy()
    cv2.fillPoly(overlay, [polygon], (0, 255, 0))
    cv2.addWeighted(overlay, 0.3, preview_frame, 0.7, 0, preview_frame)

    # Draw corners with labels
    corners = [top_left, top_right, bottom_right, bottom_left]
    labels = ['TL', 'TR', 'BR', 'BL']
    for corner, label in zip(corners, labels):
        cv2.circle(preview_frame, corner, 10, (0, 0, 255), -1)
        cv2.putText(preview_frame, f"{label} {corner}", (corner[0]+15, corner[1]),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Show preview
    cv2.imshow('Court Boundary Preview - Press any key', preview_frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    confirm = input("\nConfirm this boundary? (y/n): ").lower().startswith('y')

    if not confirm:
        print("Let's try again...")
        return get_court_coordinates_interactive(video_path)

    # Option to save coordinates
    save_coords = input("Save coordinates for future use? (y/n): ").lower().startswith('y')
    if save_coords:
        coord_file = OUTPUT_DIR / f"{Path(video_path).stem}_court_coords.json"
        with open(coord_file, 'w') as f:
            json.dump(court.to_dict(), f, indent=2)
        print(f"Coordinates saved to: {coord_file}")

    return court


def load_court_coordinates(coord_file: Path) -> CourtBoundary:
    """Load court coordinates from file"""
    with open(coord_file, 'r') as f:
        data = json.load(f)
    return CourtBoundary.from_dict(data)


def main():
    """Main entry point"""

    print("\n" + "=" * 60)
    print("BADMINTON SHOT ANALYZER v2")
    print("Court Bounded Single Player Analysis")
    print("=" * 60)

    # Get video path
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        video_path = input("\nEnter video file path: ").strip().strip('"').strip("'")

    if not Path(video_path).exists():
        print(f"Error: Video file not found: {video_path}")
        return

    # Check for existing coordinates in output folder
    coord_file = OUTPUT_DIR / f"{Path(video_path).stem}_court_coords.json"

    if coord_file.exists():
        use_existing = input(f"\nFound existing coordinates ({coord_file}). Use them? (y/n): ")
        if use_existing.lower().startswith('y'):
            court = load_court_coordinates(coord_file)
            print(f"Loaded court boundary: {court.get_bounding_rect()}")
        else:
            court = get_court_coordinates_interactive(video_path)
    else:
        court = get_court_coordinates_interactive(video_path)

    # Analysis options
    print("\n" + "-" * 40)
    print("PERFORMANCE OPTIONS")
    print("-" * 40)

    print("\n1. Processing Speed Preset:")
    print("   [1] Fast     - Lower accuracy, ~4x speed")
    print("   [2] Balanced - Good accuracy, ~2x speed (recommended)")
    print("   [3] Accurate - Best accuracy, slower")

    speed_preset = input("Select preset [1/2/3, default=2]: ").strip()

    # Configure based on preset
    if speed_preset == '1':
        process_every_n = 3
        processing_width = 480
        model_complexity = 0
        skip_static = True
        print("   → Fast mode: skip 3 frames, 480px, model=0, skip static")
    elif speed_preset == '3':
        process_every_n = 1
        processing_width = 960
        model_complexity = 1
        skip_static = False
        print("   → Accurate mode: all frames, 960px, model=1, no skip")
    else:
        process_every_n = 2
        processing_width = 640
        model_complexity = 1
        skip_static = True
        print("   → Balanced mode: skip 2 frames, 640px, model=1, skip static")

    show_live = input("\nShow live analysis? (y/n): ").lower().startswith('y')
    save_video = input("Save annotated video? (y/n): ").lower().startswith('y')

    output_path = None
    if save_video:
        output_path = str(OUTPUT_DIR / f"analyzed_{Path(video_path).stem}.mp4")

    # Initialize analyzer with performance settings
    analyzer = CourtBoundedAnalyzer(
        court,
        process_every_n_frames=process_every_n,
        processing_width=processing_width,
        model_complexity=model_complexity,
        skip_static_frames=skip_static
    )

    # Run analysis
    print("\n" + "=" * 60)
    print("STARTING ANALYSIS")
    print("=" * 60)
    print("Press 'Q' in video window or Ctrl+C to stop\n")

    try:
        report = analyzer.analyze_video(video_path, output_path, show_live)

        # Display results
        print("\n" + "=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)

        if 'summary' in report:
            summary = report['summary']
            print(f"\nTotal Shots Detected: {summary['total_shots']}")
            print(f"Total Rallies: {summary['total_rallies']}")
            print(f"Player Detection Rate: {summary['player_detection_rate']:.1%}")
            print(f"Average Confidence: {summary['avg_confidence']:.2f}")

            print("\nShot Distribution:")
            for shot_type, count in report['shot_distribution'].items():
                pct = (count / summary['total_shots'] * 100) if summary['total_shots'] > 0 else 0
                print(f"  {shot_type}: {count} ({pct:.1f}%)")

            if report['rallies']:
                print(f"\nRally Summary:")
                for rally in report['rallies'][:5]:  # Show first 5 rallies
                    print(f"  Rally {rally['rally_id']}: {rally['shot_count']} shots, "
                          f"{rally['duration']:.1f}s - {', '.join(rally['shots'])}")
        else:
            print(f"\n{report.get('message', 'Analysis complete')}")

        # Save report
        video_name = Path(video_path).stem
        report_file = analyzer.save_report(report, video_name)
        print(f"\nDetailed report saved: {report_file}")

        if output_path:
            print(f"Annotated video saved: {output_path}")

    except KeyboardInterrupt:
        print("\n\nAnalysis cancelled by user")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
