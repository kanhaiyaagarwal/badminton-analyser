import cv2
import numpy as np
import mediapipe as mp
from ultralytics import YOLO
import torch
import json
import time
import sys
import math
from pathlib import Path
from collections import defaultdict, Counter
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('badminton_shot_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ShotData:
    """Data structure for storing shot information"""
    frame_number: int
    timestamp: float
    shot_type: str
    confidence: float
    pose_landmarks: List
    player_bbox: Tuple
    shuttlecock_pos: Optional[Tuple]
    coaching_advice: str
    player_id: str = "unknown"

class BadmintonShotAnalyzer:
    def __init__(self):
        self.setup_models()
        self.setup_coaching_database()
        self.shot_history = []
        self.session_stats = defaultdict(int)
        # Static object filtering
        self.static_objects = {}  # Track objects that remain stationary
        self.static_threshold = 10  # pixels movement threshold
        self.static_frame_count = 15  # frames to confirm static object
        
        # Person-centric analysis
        self.pose_velocity_history = []  # Track pose velocities over time
        self.body_momentum_history = []  # Track body momentum changes
        self.swing_detection_history = []  # Track swing patterns
        self.stance_history = []  # Track player stance changes
        
        # Player tracking consistency
        self.player_positions = {}  # Track player 1 (left) vs player 2 (right)
        self.player_ids = {}  # Consistent player identification
        self.court_center_x = None
        
        # Last shot tracking for static display - per player
        self.last_shot_by_player = {}  # Store last actual shot for each player for static display
        
    def setup_models(self):
        """Initialize pose detection and object detection models"""
        logger.info("🏸 Initializing Enhanced Badminton Shot Analyzer...")
        
        # MediaPipe Pose Detection
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            enable_segmentation=False,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # YOLO for shuttlecock detection
        try:
            self.yolo_model = YOLO('yolov8n.pt')
            logger.info("✅ YOLO model loaded successfully")
        except Exception as e:
            logger.warning(f"⚠️ YOLO model not available: {e}")
            self.yolo_model = None
        
        logger.info("✅ Models initialized successfully")
    
    def setup_coaching_database(self):
        """Setup coaching advice database"""
        self.coaching_db = {
            'smash': {
                'tips': ["Keep elbow high and rotate torso for power", "Hit at highest point", "Follow through completely"],
                'mistakes': ["Hitting too low", "Not rotating torso", "Rushing the shot"],
                'priority': 'High'
            },
            'clear': {
                'tips': ["Use high-to-low swing path", "Generate power from legs", "Aim for back tramlines"],
                'mistakes': ["Not getting under shuttle", "Using only arm power", "Poor timing"],
                'priority': 'High'
            },
            'drop_shot': {
                'tips': ["Use deceptive action", "Gentle wrist at contact", "Aim just over net"],
                'mistakes': ["Telegraphing shot", "Hitting too hard", "Poor placement"],
                'priority': 'Medium'
            },
            'net_shot': {
                'tips': ["Keep racket head up", "Step forward", "Keep shuttle close to net"],
                'mistakes': ["Hitting into net", "Standing upright", "Moving too slowly"],
                'priority': 'Medium'
            },
            'drive': {
                'tips': ["Keep racket head up", "Flat fast swing", "Step into shot"],
                'mistakes': ["Swinging too low", "Poor positioning", "Lack of power"],
                'priority': 'Low'
            }
        }
    
    def detect_shuttlecock(self, frame, frame_number=0):
        """Enhanced multi-method shuttlecock detection with static object filtering"""
        candidates = []
        
        # Method 1: YOLO Detection
        if self.yolo_model is not None:
            try:
                results = self.yolo_model(frame, verbose=False)
                for result in results:
                    if result.boxes is not None:
                        for box in result.boxes:
                            class_id = int(box.cls[0])
                            conf = float(box.conf[0])
                            
                            # Sports ball, frisbee, or tennis ball might be shuttlecock
                            if class_id in [32, 33, 38] and conf > 0.15:
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                center_x = int((x1 + x2) / 2)
                                center_y = int((y1 + y2) / 2)
                                
                                candidates.append({
                                    'position': (center_x, center_y),
                                    'confidence': conf,
                                    'bbox': (int(x1), int(y1), int(x2), int(y2)),
                                    'method': 'YOLO',
                                    'size': (x2-x1) * (y2-y1)
                                })
            except Exception as e:
                logger.debug(f"YOLO detection failed: {e}")
        
        # Method 2: Optical Flow Detection (Best for fast moving objects)
        optical_flow_candidate = self.detect_by_optical_flow(frame)
        if optical_flow_candidate:
            candidates.append(optical_flow_candidate)
        
        # Method 3: Background Subtraction
        bg_sub_candidate = self.detect_by_background_subtraction(frame)
        if bg_sub_candidate:
            candidates.append(bg_sub_candidate)
        
        # Method 4: Motion Detection (fallback)
        motion_candidate = self.detect_by_motion(frame)
        if motion_candidate:
            candidates.append({
                'position': motion_candidate,
                'confidence': 0.4,  # Lower confidence as fallback
                'bbox': None,
                'method': 'Motion',
                'size': 100
            })
        
        # Method 5: Color Detection (lowest priority)
        color_candidate = self.detect_by_color(frame)
        if color_candidate:
            color_candidate['confidence'] *= 0.7  # Reduce confidence for color-only detection
            candidates.append(color_candidate)
        
        # Filter out static objects
        candidates = self.filter_static_objects(candidates, frame_number)
        
        # Validate temporal consistency
        candidates = self.validate_temporal_consistency(candidates)
        
        # Select best candidate
        if candidates:
            best = self.select_best_candidate(candidates)
            if best:
                self.track_shuttlecock(best['position'])
                return best
        
        return None
    
    def detect_by_motion(self, frame):
        """Motion-based shuttlecock detection"""
        if not hasattr(self, 'prev_frame'):
            self.prev_frame = frame
            return None
        
        gray_current = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_prev = cv2.cvtColor(self.prev_frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate motion
        frame_diff = cv2.absdiff(gray_current, gray_prev)
        _, motion_mask = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if 50 < area < 500:
                x, y, w, h = cv2.boundingRect(contour)
                center_x, center_y = x + w//2, y + h//2
                
                aspect_ratio = w / h if h > 0 else 1
                if 0.5 < aspect_ratio < 2.0:
                    self.prev_frame = frame
                    return (center_x, center_y)
        
        self.prev_frame = frame
        return None
    
    def detect_by_color(self, frame):
        """Color-based shuttlecock detection (white objects)"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # White object detection
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Clean up mask
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if 20 < area < 800:
                x, y, w, h = cv2.boundingRect(contour)
                center_x, center_y = x + w//2, y + h//2
                
                aspect_ratio = w / h if h > 0 else 1
                if 0.3 < aspect_ratio < 3.0:
                    # Calculate circularity
                    perimeter = cv2.arcLength(contour, True)
                    circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                    confidence = min(0.8, 0.3 + circularity * 0.5)
                    
                    return {
                        'position': (center_x, center_y),
                        'confidence': confidence,
                        'bbox': (x, y, x+w, y+h),
                        'method': 'Color',
                        'size': area
                    }
        
        return None
    
    def detect_by_optical_flow(self, frame):
        """Enhanced shuttlecock detection using optical flow"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.prev_gray is None:
            self.prev_gray = gray
            return None
        
        # Initialize background subtractor if needed
        if self.background_subtractor is None:
            self.background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=False)
        
        # Background subtraction for motion detection
        fg_mask = self.background_subtractor.apply(frame)
        
        # Find good features to track (potential shuttlecock points)
        corners = cv2.goodFeaturesToTrack(self.prev_gray, mask=None, **self.optical_flow_params)
        
        if corners is not None and len(corners) > 0:
            # Calculate optical flow
            next_corners, status, error = cv2.calcOpticalFlowPyrLK(
                self.prev_gray, gray, corners, None, **self.lk_params)
            
            # Select good points with high velocity (shuttlecock moves fast)
            good_new = next_corners[status==1]
            good_old = corners[status==1]
            
            for i, (new, old) in enumerate(zip(good_new, good_old)):
                a, b = new.ravel().astype(int)
                c, d = old.ravel().astype(int)
                
                # Calculate velocity
                velocity = math.sqrt((a-c)**2 + (b-d)**2)
                
                # High velocity suggests shuttlecock
                if velocity > 5:  # Minimum velocity threshold
                    # Check if point is in foreground (moving object)
                    if a < fg_mask.shape[1] and b < fg_mask.shape[0] and fg_mask[b, a] > 0:
                        # Validate size and shape in the area
                        roi_size = 20
                        x1, y1 = max(0, a-roi_size), max(0, b-roi_size)
                        x2, y2 = min(frame.shape[1], a+roi_size), min(frame.shape[0], b+roi_size)
                        
                        roi = frame[y1:y2, x1:x2]
                        if roi.size > 0:
                            # Check for white/bright object in ROI
                            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                            bright_pixels = np.sum(roi_gray > 180)
                            
                            if bright_pixels > 10:  # Has bright pixels
                                confidence = min(0.8, velocity / 20 * 0.5 + bright_pixels / 100 * 0.3)
                                self.prev_gray = gray
                                
                                return {
                                    'position': (a, b),
                                    'confidence': confidence,
                                    'bbox': (x1, y1, x2, y2),
                                    'method': 'OpticalFlow',
                                    'size': roi_size * roi_size,
                                    'velocity': velocity
                                }
        
        self.prev_gray = gray
        return None
    
    def detect_by_background_subtraction(self, frame):
        """Background subtraction based detection"""
        if self.background_subtractor is None:
            self.background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=False)
        
        # Apply background subtraction
        fg_mask = self.background_subtractor.apply(frame)
        
        # Clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours of moving objects
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if 10 < area < 200:  # Small moving object
                x, y, w, h = cv2.boundingRect(contour)
                center_x, center_y = x + w//2, y + h//2
                
                # Check aspect ratio (shuttlecock is roughly circular)
                aspect_ratio = w / h if h > 0 else 1
                if 0.5 < aspect_ratio < 2.0:
                    # Check if object is bright (white shuttlecock)
                    roi = frame[y:y+h, x:x+w]
                    if roi.size > 0:
                        roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                        avg_brightness = np.mean(roi_gray)
                        
                        if avg_brightness > 120:  # Bright object
                            confidence = min(0.7, area / 100 * 0.3 + avg_brightness / 255 * 0.4)
                            return {
                                'position': (center_x, center_y),
                                'confidence': confidence,
                                'bbox': (x, y, x+w, y+h),
                                'method': 'BackgroundSub',
                                'size': area
                            }
        
        return None
    
    def filter_static_objects(self, candidates, frame_number):
        """Filter out static objects that have remained stationary"""
        if not candidates:
            return candidates
        
        filtered_candidates = []
        
        for candidate in candidates:
            pos = candidate['position']
            object_key = f"{pos[0]//20}_{pos[1]//20}"  # Grid-based grouping
            
            if object_key in self.static_objects:
                static_data = self.static_objects[object_key]
                
                # Calculate movement from last known position
                last_pos = static_data['last_position']
                movement = math.sqrt((pos[0] - last_pos[0])**2 + (pos[1] - last_pos[1])**2)
                
                if movement < self.static_threshold:
                    # Object hasn't moved much
                    static_data['static_count'] += 1
                    static_data['last_frame'] = frame_number
                    
                    # If object has been static for too long, mark as static
                    if static_data['static_count'] >= self.static_frame_count:
                        static_data['is_static'] = True
                        continue  # Skip this candidate
                else:
                    # Object moved significantly, reset static counter
                    static_data['static_count'] = 0
                    static_data['is_static'] = False
                    static_data['last_position'] = pos
                    static_data['last_frame'] = frame_number
                    
            else:
                # New object, start tracking
                self.static_objects[object_key] = {
                    'last_position': pos,
                    'last_frame': frame_number,
                    'static_count': 0,
                    'is_static': False,
                    'first_seen': frame_number
                }
            
            # Add penalty for objects that are becoming static
            if object_key in self.static_objects:
                static_count = self.static_objects[object_key]['static_count']
                if static_count > 5:  # Starting to look static
                    candidate['confidence'] *= (1.0 - static_count / self.static_frame_count * 0.5)
            
            filtered_candidates.append(candidate)
        
        # Clean up old static object entries (older than 100 frames)
        current_frame = frame_number
        keys_to_remove = []
        for key, data in self.static_objects.items():
            if current_frame - data['last_frame'] > 100:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.static_objects[key]
        
        return filtered_candidates
    
    def validate_temporal_consistency(self, candidates):
        """Validate candidates against recent shuttlecock history"""
        if not candidates or not hasattr(self, 'shuttle_history') or len(self.shuttle_history) < 3:
            return candidates
        
        validated_candidates = []
        recent_positions = self.shuttle_history[-5:]  # Last 5 positions
        
        for candidate in candidates:
            pos = candidate['position']
            
            # Calculate average distance to recent positions
            distances = []
            for hist_pos in recent_positions:
                dist = math.sqrt((pos[0] - hist_pos[0])**2 + (pos[1] - hist_pos[1])**2)
                distances.append(dist)
            
            avg_distance = sum(distances) / len(distances)
            
            # Reasonable distance threshold (shuttlecock can move fast but not teleport)
            if avg_distance < 200:  # Reasonable movement range
                # Boost confidence for consistent trajectory
                consistency_bonus = max(0, (200 - avg_distance) / 200 * 0.3)
                candidate['confidence'] += consistency_bonus
                validated_candidates.append(candidate)
            elif avg_distance < 400:  # Still possible but reduce confidence
                candidate['confidence'] *= 0.5
                validated_candidates.append(candidate)
            # If avg_distance > 400, likely false positive, exclude it
        
        return validated_candidates if validated_candidates else candidates
    
    def identify_player(self, pose_landmarks, frame_number):
        """Identify and consistently track player 1 (left) vs player 2 (right)"""
        if not pose_landmarks:
            return "unknown"
        
        landmarks = pose_landmarks.landmark
        
        # Get player center position
        shoulder_left = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        shoulder_right = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        center_x = (shoulder_left.x + shoulder_right.x) / 2
        
        # Initialize court center on first few frames
        if self.court_center_x is None:
            if len(self.player_positions) < 10:  # Collect positions for first 10 detections
                self.player_positions[frame_number] = center_x
            elif len(self.player_positions) == 10:
                # Calculate court center as midpoint between detected players
                positions = list(self.player_positions.values())
                self.court_center_x = (min(positions) + max(positions)) / 2
                logger.info(f"Court center established at x={self.court_center_x:.3f}")
        
        # Assign player based on court position
        if self.court_center_x is not None:
            if center_x < self.court_center_x:
                player_id = "player_1_left"
            else:
                player_id = "player_2_right"
            
            # Store consistent tracking
            if player_id not in self.player_ids:
                self.player_ids[player_id] = {
                    'first_seen': frame_number,
                    'total_detections': 0,
                    'avg_position': center_x
                }
            
            # Update tracking stats
            self.player_ids[player_id]['total_detections'] += 1
            self.player_ids[player_id]['avg_position'] = (
                self.player_ids[player_id]['avg_position'] * 0.9 + center_x * 0.1
            )
            
            return player_id
        
        return "unknown"
    
    def analyze_body_movement(self, pose_landmarks):
        """Advanced body movement analysis for shot detection"""
        if not pose_landmarks:
            return None
        
        landmarks = pose_landmarks.landmark
        
        # Key body points for movement analysis
        key_points = {
            'right_shoulder': landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER],
            'left_shoulder': landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER], 
            'right_elbow': landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW],
            'right_wrist': landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST],
            'right_hip': landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP],
            'left_hip': landmarks[self.mp_pose.PoseLandmark.LEFT_HIP],
            'right_knee': landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE],
            'left_knee': landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE]
        }
        
        # Calculate current pose state
        pose_state = {
            'shoulder_center': ((key_points['right_shoulder'].x + key_points['left_shoulder'].x) / 2,
                               (key_points['right_shoulder'].y + key_points['left_shoulder'].y) / 2),
            'hip_center': ((key_points['right_hip'].x + key_points['left_hip'].x) / 2,
                          (key_points['right_hip'].y + key_points['left_hip'].y) / 2),
            'wrist_pos': (key_points['right_wrist'].x, key_points['right_wrist'].y),
            'elbow_pos': (key_points['right_elbow'].x, key_points['right_elbow'].y),
            'knee_spread': abs(key_points['right_knee'].x - key_points['left_knee'].x),
            'body_tilt': key_points['right_shoulder'].x - key_points['left_shoulder'].x
        }
        
        # Track pose velocity if we have history
        if len(self.pose_velocity_history) > 0:
            prev_pose = self.pose_velocity_history[-1]
            
            # Calculate velocities
            wrist_velocity = math.sqrt(
                (pose_state['wrist_pos'][0] - prev_pose['wrist_pos'][0])**2 +
                (pose_state['wrist_pos'][1] - prev_pose['wrist_pos'][1])**2
            )
            
            body_velocity = math.sqrt(
                (pose_state['shoulder_center'][0] - prev_pose['shoulder_center'][0])**2 +
                (pose_state['shoulder_center'][1] - prev_pose['shoulder_center'][1])**2
            )
            
            pose_state['wrist_velocity'] = wrist_velocity
            pose_state['body_velocity'] = body_velocity
            
            # Detect swing patterns
            swing_pattern = self.detect_swing_pattern(pose_state, prev_pose)
            pose_state['swing_pattern'] = swing_pattern
        else:
            pose_state['wrist_velocity'] = 0.0
            pose_state['body_velocity'] = 0.0
            pose_state['swing_pattern'] = 'none'
        
        # Store in history (keep last 10 frames)
        self.pose_velocity_history.append(pose_state)
        if len(self.pose_velocity_history) > 10:
            self.pose_velocity_history.pop(0)
        
        return pose_state
    
    def detect_swing_pattern(self, current_pose, prev_pose):
        """Detect swing patterns from pose movement"""
        wrist_vel = current_pose.get('wrist_velocity', 0)
        body_vel = current_pose.get('body_velocity', 0)
        
        # Wrist movement analysis
        wrist_dx = current_pose['wrist_pos'][0] - prev_pose['wrist_pos'][0]
        wrist_dy = current_pose['wrist_pos'][1] - prev_pose['wrist_pos'][1]
        
        # High wrist velocity suggests active swing
        if wrist_vel > 0.05:  # Significant wrist movement
            if wrist_dy < -0.03:  # Upward movement (overhead shot)
                if wrist_vel > 0.08:
                    return 'power_overhead'  # Smash/Clear
                else:
                    return 'gentle_overhead'  # Drop shot
            elif wrist_dy > 0.03:  # Downward movement
                return 'net_shot'
            elif abs(wrist_dx) > 0.05:  # Horizontal movement
                return 'drive_shot'
        elif body_vel > 0.02:  # Body movement without wrist
            return 'preparation'
        
        return 'static'
    
    def classify_shot_from_movement(self, movement_data):
        """Classify shot based on movement patterns instead of static pose"""
        if not movement_data:
            return "unknown", 0.0
        
        swing_pattern = movement_data.get('swing_pattern', 'none')
        wrist_velocity = movement_data.get('wrist_velocity', 0)
        body_velocity = movement_data.get('body_velocity', 0)
        
        # Movement-based classification
        if swing_pattern == 'power_overhead':
            confidence = min(0.9, wrist_velocity * 10)
            if wrist_velocity > 0.1:
                return "smash", confidence
            else:
                return "clear", confidence * 0.8
        elif swing_pattern == 'gentle_overhead':
            return "drop_shot", min(0.8, wrist_velocity * 12)
        elif swing_pattern == 'net_shot':
            return "net_shot", min(0.75, wrist_velocity * 8)
        elif swing_pattern == 'drive_shot':
            return "drive", min(0.7, wrist_velocity * 6)
        elif swing_pattern == 'preparation':
            return "ready_position", min(0.6, body_velocity * 15)
        else:
            return "static", 0.4
    
    def select_best_candidate(self, candidates):
        """Select best shuttlecock candidate with enhanced scoring"""
        if not candidates:
            return None
        
        # Multi-factor scoring system
        for candidate in candidates:
            pos = candidate['position']
            
            # Factor 1: Base confidence from detection method
            score = candidate['confidence']
            
            # Factor 2: Trajectory prediction bonus
            if hasattr(self, 'shuttle_history') and len(self.shuttle_history) >= 2:
                predicted = self.predict_position()
                if predicted:
                    distance = math.sqrt((pos[0] - predicted[0])**2 + (pos[1] - predicted[1])**2)
                    if distance < 50:
                        score += 0.3 * (1 - distance/50)
                    elif distance > 100:
                        score *= 0.6
            
            # Factor 3: Size preference (shuttlecock is small)
            size = candidate.get('size', 100)
            if 20 < size < 300:  # Ideal shuttlecock size range
                score += 0.1
            elif size > 800:  # Too large, likely not shuttlecock
                score *= 0.3
            
            # Factor 4: Detection method reliability
            method = candidate.get('method', 'Unknown')
            if method == 'OpticalFlow':
                score *= 1.4  # Optical flow is excellent for fast moving objects
            elif method == 'BackgroundSub':
                score *= 1.3  # Background subtraction is very reliable
            elif method == 'YOLO':
                score *= 1.2  # YOLO is good for object recognition
            elif method == 'Motion':
                score *= 0.9  # Basic motion detection
            elif method == 'Color':
                score *= 0.7  # Color can be very noisy
            
            # Factor 5: Position reasonableness (avoid extreme edges)
            frame_height, frame_width = 720, 1280  # Typical video dimensions
            if hasattr(self, 'frame_shape'):
                frame_height, frame_width = self.frame_shape[:2]
            
            margin = 50
            if (pos[0] < margin or pos[0] > frame_width - margin or 
                pos[1] < margin or pos[1] > frame_height - margin):
                score *= 0.7  # Penalize edge detections
            
            candidate['final_score'] = score
        
        # Return candidate with highest final score
        best = max(candidates, key=lambda x: x['final_score'])
        return best if best['final_score'] > 0.2 else None
    
    def predict_position(self):
        """Predict next shuttlecock position"""
        if not hasattr(self, 'shuttle_history') or len(self.shuttle_history) < 3:
            return None
        
        recent = self.shuttle_history[-3:]
        
        # Calculate velocity
        dx = recent[-1][0] - recent[-2][0]
        dy = recent[-1][1] - recent[-2][1]
        
        # Calculate acceleration
        prev_dx = recent[-2][0] - recent[-3][0]
        prev_dy = recent[-2][1] - recent[-3][1]
        
        ax = dx - prev_dx
        ay = dy - prev_dy
        
        # Predict with physics (including gravity)
        next_x = recent[-1][0] + dx + ax
        next_y = recent[-1][1] + dy + ay + 2  # Gravity effect
        
        return (int(next_x), int(next_y))
    
    def track_shuttlecock(self, position):
        """Track shuttlecock movement with analytics"""
        if not hasattr(self, 'shuttle_history'):
            self.shuttle_history = []
            self.shuttle_speed = 0.0
            self.shuttle_direction = 0.0
            self.shuttle_acceleration = 0.0
        
        # Add to history (keep last 20 positions)
        self.shuttle_history.append(position)
        if len(self.shuttle_history) > 20:
            self.shuttle_history.pop(0)
        
        # Calculate analytics
        if len(self.shuttle_history) >= 2:
            prev_pos = self.shuttle_history[-2]
            curr_pos = self.shuttle_history[-1]
            
            dx = curr_pos[0] - prev_pos[0]
            dy = curr_pos[1] - prev_pos[1]
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Update speed with smoothing
            self.shuttle_speed = 0.7 * self.shuttle_speed + 0.3 * distance
            
            # Calculate direction
            if dx != 0:
                angle = math.atan2(dy, dx) * 180 / math.pi
                self.shuttle_direction = angle
            
            # Calculate acceleration
            if len(self.shuttle_history) >= 3:
                prev_prev = self.shuttle_history[-3]
                prev_dx = prev_pos[0] - prev_prev[0]
                prev_dy = prev_pos[1] - prev_prev[1]
                prev_distance = math.sqrt(prev_dx*prev_dx + prev_dy*prev_dy)
                
                acceleration = distance - prev_distance
                self.shuttle_acceleration = 0.8 * self.shuttle_acceleration + 0.2 * acceleration
    
    def detect_game_state(self, frame, pose_landmarks, shuttle_data, frame_number):
        """Enhanced game state detection"""
        if not pose_landmarks:
            return "no_player", 0.0
        
        landmarks = pose_landmarks.landmark
        
        # Key points
        left_wrist = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST]
        right_wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_ankle = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE]
        right_ankle = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE]
        
        # Store pose for movement analysis
        current_pose = {
            'left_wrist': (left_wrist.x, left_wrist.y),
            'right_wrist': (right_wrist.x, right_wrist.y),
            'left_shoulder': (left_shoulder.x, left_shoulder.y),
            'right_shoulder': (right_shoulder.x, right_shoulder.y),
            'left_ankle': (left_ankle.x, left_ankle.y),
            'right_ankle': (right_ankle.x, right_ankle.y),
        }
        
        # Initialize tracking variables
        if not hasattr(self, 'pose_history'):
            self.pose_history = []
            self.movement_threshold = 0.03
            self.static_count = 0
            self.active_count = 0
        
        # Update pose history
        self.pose_history.append(current_pose)
        if len(self.pose_history) > 15:
            self.pose_history.pop(0)
        
        if len(self.pose_history) < 5:
            return "analyzing", 0.5
        
        # Calculate movement
        recent_movement = self.calculate_movement()
        
        # Analyze racket position
        dominant_wrist = right_wrist  # Assume right-handed
        dominant_shoulder = right_shoulder
        
        arm_angle = abs(math.atan2(
            dominant_wrist.y - dominant_shoulder.y,
            dominant_wrist.x - dominant_shoulder.x
        ) * 180 / math.pi)
        
        racket_active = (dominant_wrist.y < dominant_shoulder.y or 
                        arm_angle > 45 or 
                        abs(dominant_wrist.x - dominant_shoulder.x) > 0.15)
        
        # Enhanced state detection logic
        confidence = 0.0
        
        # Priority 1: Fast moving shuttlecock = active play
        if (shuttle_data and hasattr(self, 'shuttle_speed') and self.shuttle_speed > 10):
            game_state = "active_play"
            confidence = 0.95
            self.active_count += 1
            self.static_count = 0
            
        # Priority 2: High movement + active racket = active play
        elif (recent_movement > self.movement_threshold * 2 and racket_active):
            game_state = "active_play"
            confidence = 0.85
            self.active_count += 1
            self.static_count = 0
            
        # Priority 3: Movement + shuttlecock = active play
        elif (recent_movement > self.movement_threshold and shuttle_data):
            game_state = "active_play"
            confidence = 0.8
            self.active_count += 1
            self.static_count = 0
            
        # Priority 4: Racket active but low movement = ready
        elif (racket_active and recent_movement > self.movement_threshold * 0.5):
            game_state = "ready_position"
            confidence = 0.7
            self.static_count = 0
            
        # Priority 5: Very low movement = static
        elif (recent_movement < self.movement_threshold * 0.3 and not racket_active):
            self.static_count += 1
            if self.static_count > 5:
                game_state = "static"
                confidence = 0.85
            else:
                game_state = "ready_position"
                confidence = 0.6
            self.active_count = 0
            
        else:
            game_state = "ready_position"
            confidence = 0.5
        
        # Boost confidence for consistent activity
        if self.active_count > 3 and game_state == "active_play":
            confidence = min(0.95, confidence + 0.1)
        
        return game_state, confidence
    
    def calculate_movement(self):
        """Calculate pose movement over recent frames"""
        if len(self.pose_history) < 2:
            return 0.0
        
        total_movement = 0.0
        recent_poses = self.pose_history[-5:]  # Last 5 frames
        
        for i in range(1, len(recent_poses)):
            frame_movement = 0.0
            current = recent_poses[i]
            previous = recent_poses[i-1]
            
            for point_name in current.keys():
                curr_x, curr_y = current[point_name]
                prev_x, prev_y = previous[point_name]
                
                point_movement = math.sqrt((curr_x - prev_x)**2 + (curr_y - prev_y)**2)
                frame_movement += point_movement
            
            total_movement += frame_movement
        
        return total_movement / (len(recent_poses) - 1) if len(recent_poses) > 1 else 0.0
    
    def classify_shot(self, pose_landmarks, has_recent_movement=True):
        """Classify badminton shot from pose - only called during active play"""
        if not pose_landmarks:
            return "unknown", 0.0
        
        landmarks = pose_landmarks.landmark
        
        # Key points
        right_wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        right_elbow = landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW]
        
        # Calculate positions and angles
        wrist_height = 1 - right_wrist.y
        shoulder_height = 1 - right_shoulder.y
        
        arm_angle = math.atan2(
            right_wrist.y - right_shoulder.y,
            right_wrist.x - right_shoulder.x
        ) * 180 / math.pi
        
        # Calculate elbow angle
        shoulder_to_elbow = np.array([right_shoulder.x - right_elbow.x, right_shoulder.y - right_elbow.y])
        elbow_to_wrist = np.array([right_wrist.x - right_elbow.x, right_wrist.y - right_elbow.y])
        
        cosine_angle = np.dot(shoulder_to_elbow, elbow_to_wrist) / (
            np.linalg.norm(shoulder_to_elbow) * np.linalg.norm(elbow_to_wrist)
        )
        elbow_angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0)) * 180 / math.pi
        
        # Classification rules - more restrictive to avoid false positives
        if (wrist_height > shoulder_height + 0.15 and -45 < arm_angle < 45 and elbow_angle > 100):
            return "smash", 0.8
        elif (wrist_height > shoulder_height + 0.08 and -30 < arm_angle < 60 and elbow_angle > 90):
            return "clear", 0.75
        elif (wrist_height < shoulder_height - 0.25 and abs(arm_angle) < 45):
            return "net_shot", 0.7
        elif (abs(wrist_height - shoulder_height) < 0.08 and abs(arm_angle) > 75 and 
              has_recent_movement and elbow_angle < 160):  # Only classify drive with movement
            return "drive", 0.65
        elif (wrist_height > shoulder_height - 0.03 and -15 < arm_angle < 30 and elbow_angle > 85):
            return "drop_shot", 0.6
        else:
            return "unknown", 0.3
    
    def get_coaching_advice(self, shot_type):
        """Get coaching advice for shot type"""
        if shot_type in self.coaching_db:
            tips = self.coaching_db[shot_type]['tips']
            tip_index = len(self.shot_history) % len(tips)
            return tips[tip_index]
        return "Keep practicing! Focus on footwork and timing."
    
    def analyze_frame(self, frame, frame_number, timestamp):
        """Analyze single frame with enhanced detection - support multiple players"""
        # Store frame dimensions for position validation
        self.frame_shape = frame.shape
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]
        
        all_shot_data = []
        pose_results = None
        
        # Try to detect players using frame splitting approach
        # Split frame into left and right halves and analyze separately
        left_half = frame_rgb[:, :w//2]
        right_half = frame_rgb[:, w//2:]
        
        # Analyze left half
        left_results = self.pose.process(left_half)
        if left_results.pose_landmarks:
            # Adjust landmarks to full frame coordinates
            adjusted_landmarks = self.adjust_landmarks_to_full_frame(left_results.pose_landmarks, 'left', w)
            left_shot_data = self.process_single_player(adjusted_landmarks, frame, frame_number, timestamp, force_player_id="player_1_left")
            if left_shot_data:
                all_shot_data.append(left_shot_data)
                if not pose_results:  # Use first detected pose for drawing
                    pose_results = left_results
        
        # Analyze right half
        right_results = self.pose.process(right_half)
        if right_results.pose_landmarks:
            # Adjust landmarks to full frame coordinates
            adjusted_landmarks = self.adjust_landmarks_to_full_frame(right_results.pose_landmarks, 'right', w)
            right_shot_data = self.process_single_player(adjusted_landmarks, frame, frame_number, timestamp, force_player_id="player_2_right")
            if right_shot_data:
                all_shot_data.append(right_shot_data)
                if not pose_results:  # Use first detected pose for drawing
                    pose_results = right_results
        
        # Fallback: try full frame analysis if no players detected
        if not all_shot_data:
            full_results = self.pose.process(frame_rgb)
            if full_results.pose_landmarks:
                shot_data = self.process_single_player(full_results.pose_landmarks, frame, frame_number, timestamp)
                if shot_data:
                    all_shot_data.append(shot_data)
                    pose_results = full_results
        
        return all_shot_data, pose_results
    
    def adjust_landmarks_to_full_frame(self, landmarks, side, full_width):
        """Adjust landmarks from half-frame to full-frame coordinates"""
        if side == 'right':
            # Shift right half landmarks by half width
            for landmark in landmarks.landmark:
                landmark.x = (landmark.x / 2) + 0.5  # Scale to half and shift right
        else:  # left
            # Scale left half landmarks to fit left half of full frame
            for landmark in landmarks.landmark:
                landmark.x = landmark.x / 2  # Scale to fit left half
        
        return landmarks
    
    def process_single_player(self, pose_landmarks, frame, frame_number, timestamp, force_player_id=None):
        """Process a single player's pose data"""
        if not pose_landmarks:
            return None
        
        # Identify player consistently
        if force_player_id:
            player_id = force_player_id
        else:
            player_id = self.identify_player(pose_landmarks, frame_number)
        
        # Advanced movement analysis (person-centric)
        movement_data = self.analyze_body_movement(pose_landmarks)
        
        # Movement-based shot classification (primary method)
        shot_type, confidence = self.classify_shot_from_movement(movement_data)
        
        # Optional: Still detect shuttlecock but don't rely on it heavily
        shuttle_data = None  # Disable for now to focus on person
        
        # Determine game state from movement patterns
        if shot_type in ["smash", "clear", "drop_shot", "net_shot", "drive"]:
            game_state = "active_play"
            state_confidence = confidence
        elif shot_type == "ready_position":
            game_state = "ready_position" 
            state_confidence = confidence
        else:
            game_state = "static"
            state_confidence = confidence
        
        # Player bounding box
        landmarks = pose_landmarks.landmark
        h, w = frame.shape[:2]
        
        x_coords = [lm.x * w for lm in landmarks if lm.visibility > 0.5]
        y_coords = [lm.y * h for lm in landmarks if lm.visibility > 0.5]
        
        if x_coords and y_coords:
            player_bbox = (int(min(x_coords)), int(min(y_coords)), 
                         int(max(x_coords)), int(max(y_coords)))
        else:
            player_bbox = (0, 0, w, h)
        
        # Coaching advice
        if shot_type in ["smash", "clear", "drop_shot", "net_shot", "drive"]:
            coaching_advice = self.get_coaching_advice(shot_type)
        elif shot_type == "ready_position":
            coaching_advice = "Good ready position! Stay alert."
        else:
            coaching_advice = "Player in static position"
        
        # Create shot data
        shot_data = ShotData(
            frame_number=frame_number,
            timestamp=timestamp,
            shot_type=shot_type,
            confidence=confidence,
            pose_landmarks=pose_landmarks,
            player_bbox=player_bbox,
            shuttlecock_pos=shuttle_data['position'] if shuttle_data else None,
            coaching_advice=coaching_advice,
            player_id=player_id
        )
        
        # Store movement data for enhanced visualization
        if movement_data:
            shot_data.movement_data = movement_data
        
        # Store shuttle data for enhanced visualization (if available)
        if shuttle_data:
            shot_data.shuttlecock_data = shuttle_data
        
        return shot_data
    
    def draw_annotations(self, frame, all_shot_data, pose_results):
        """Draw enhanced annotations for multiple players simultaneously"""
        # Calculate dynamic text parameters
        text_params = self.calculate_dynamic_text_params(frame)
        
        # Draw pose landmarks for all detected players
        if pose_results and pose_results.pose_landmarks:
            # Draw basic pose for any detected pose
            pose_color = (0, 255, 0)
            connection_color = (255, 0, 0)
            self.mp_drawing.draw_landmarks(
                frame, pose_results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=pose_color, thickness=2),
                self.mp_drawing.DrawingSpec(color=connection_color, thickness=2)
            )
        
        # Draw individual player data and bounding boxes
        for shot_data in all_shot_data:
            if shot_data:
                # Player bounding box
                x1, y1, x2, y2 = shot_data.player_bbox
                
                if shot_data.shot_type == "static":
                    bbox_color = (128, 128, 128)
                elif shot_data.shot_type == "ready_position":
                    bbox_color = (0, 255, 255)
                else:
                    bbox_color = (0, 255, 0)
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), bbox_color, 2)
                
                # Draw movement vectors if available
                if hasattr(shot_data, 'movement_data') and shot_data.movement_data and shot_data.pose_landmarks:
                    landmarks = shot_data.pose_landmarks.landmark
                    h, w = frame.shape[:2]
                    
                    # Draw wrist velocity vector
                    wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]
                    wrist_x, wrist_y = int(wrist.x * w), int(wrist.y * h)
                    wrist_vel = shot_data.movement_data.get('wrist_velocity', 0)
                    
                    if wrist_vel > 0.02:  # Show vector if significant movement
                        vector_length = int(wrist_vel * 300)  # Scale for visibility
                        cv2.arrowedLine(frame, (wrist_x, wrist_y), 
                                      (wrist_x + vector_length, wrist_y - vector_length//2),
                                      (255, 255, 0), 2, tipLength=0.3)
        
        # Draw shuttlecock if any player has it
        for shot_data in all_shot_data:
            if hasattr(shot_data, 'shuttlecock_data') and shot_data.shuttlecock_data:
                self.draw_enhanced_shuttlecock(frame, shot_data.shuttlecock_data)
                break  # Only draw one shuttlecock
            elif shot_data.shuttlecock_pos:
                cx, cy = shot_data.shuttlecock_pos
                cv2.circle(frame, (cx, cy), 8, (0, 255, 255), -1)
                break
        
        # Draw dual player display at the top
        self.draw_dual_player_display(frame, all_shot_data, text_params)
        
        # Game state indicators on the right
        self.draw_dual_game_state_indicators(frame, all_shot_data, text_params)
        
        # Shuttlecock analytics
        if hasattr(self, 'shuttle_speed'):
            self.draw_shuttlecock_analytics(frame)
        
        return frame
    
    def draw_dual_player_display(self, frame, all_shot_data, text_params):
        """Draw both players' information at the top of the frame"""
        # Organize players by left/right
        player_data = {"player_1_left": None, "player_2_right": None}
        
        for shot_data in all_shot_data:
            if shot_data and shot_data.player_id in player_data:
                player_data[shot_data.player_id] = shot_data
        
        # Calculate positions for dual display
        left_x = text_params['margin']
        right_x = text_params['frame_width'] // 2 + text_params['margin']
        y_pos = text_params['line_height']
        
        # Draw Player 1 (Left)
        self.draw_single_player_info(frame, player_data["player_1_left"], 
                                   left_x, y_pos, text_params, "Player 1 (Left)")
        
        # Draw Player 2 (Right)
        self.draw_single_player_info(frame, player_data["player_2_right"], 
                                   right_x, y_pos, text_params, "Player 2 (Right)")
    
    def draw_single_player_info(self, frame, shot_data, x_pos, y_pos, text_params, player_label):
        """Draw individual player information - focused on what player is doing"""
        if not shot_data:
            # No player detected
            cv2.putText(frame, f"{player_label}: Not Detected", 
                       (x_pos, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 
                       text_params['main_font_scale'], (128, 128, 128), text_params['main_thickness'])
            return
        
        # Color based on state
        if shot_data.shot_type == "static":
            text_color = (128, 128, 128)
        elif shot_data.shot_type == "ready_position":
            text_color = (0, 255, 255)
        else:
            text_color = (255, 255, 255)
        
        # Main info line - focus on what player is doing
        player_last_shot = self.last_shot_by_player.get(shot_data.player_id)
        if shot_data.shot_type == "static" and player_last_shot:
            info_text = f"{player_label}: Static (Last: {player_last_shot.shot_type})"
        elif shot_data.shot_type == "ready_position":
            info_text = f"{player_label}: Ready Position"
        elif shot_data.shot_type in ["smash", "clear", "drop_shot", "net_shot", "drive"]:
            info_text = f"{player_label}: Playing {shot_data.shot_type.replace('_', ' ').title()} ({shot_data.confidence:.2f})"
        else:
            info_text = f"{player_label}: {shot_data.shot_type.replace('_', ' ').title()}"
        
        # Truncate if needed (half screen width)
        max_chars = int(text_params['max_text_width'] / 2 / (text_params['main_font_scale'] * 12))
        if len(info_text) > max_chars:
            info_text = info_text[:max_chars-3] + "..."
        
        # Draw main info only - no coaching tips
        cv2.putText(frame, info_text, (x_pos, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, text_params['main_font_scale'], 
                   text_color, text_params['main_thickness'])
    
    def draw_dual_game_state_indicators(self, frame, all_shot_data, text_params):
        """Draw game state indicators for both players on the right side"""
        frame_width = text_params['frame_width']
        
        # Organize players
        player_data = {"player_1_left": None, "player_2_right": None}
        for shot_data in all_shot_data:
            if shot_data and shot_data.player_id in player_data:
                player_data[shot_data.player_id] = shot_data
        
        # State colors
        state_colors = {
            "static": (128, 128, 128),
            "ready_position": (0, 255, 255),
            "active_play": (0, 255, 0)
        }
        
        # Draw Player 1 state indicator
        if player_data["player_1_left"]:
            state = player_data["player_1_left"].shot_type
            if state in ["smash", "clear", "drop_shot", "net_shot", "drive"]:
                state = "active_play"
            color = state_colors.get(state, (255, 255, 255))
            cv2.circle(frame, (frame_width - 80, 50), 15, color, -1)
            cv2.putText(frame, "P1", (frame_width - 90, 55), 
                       cv2.FONT_HERSHEY_SIMPLEX, text_params['state_font_scale'], 
                       (255, 255, 255), text_params['state_thickness'])
        
        # Draw Player 2 state indicator
        if player_data["player_2_right"]:
            state = player_data["player_2_right"].shot_type
            if state in ["smash", "clear", "drop_shot", "net_shot", "drive"]:
                state = "active_play"
            color = state_colors.get(state, (255, 255, 255))
            cv2.circle(frame, (frame_width - 80, 90), 15, color, -1)
            cv2.putText(frame, "P2", (frame_width - 90, 95), 
                       cv2.FONT_HERSHEY_SIMPLEX, text_params['state_font_scale'], 
                       (255, 255, 255), text_params['state_thickness'])
    
    def calculate_dynamic_text_params(self, frame):
        """Calculate dynamic text parameters based on video resolution"""
        frame_height, frame_width = frame.shape[:2]
        
        # Base scaling factor (1.0 for 1280x720, scale accordingly)
        base_width, base_height = 1280, 720
        width_scale = frame_width / base_width
        height_scale = frame_height / base_height
        scale_factor = min(width_scale, height_scale)  # Use smaller scale to ensure fit
        
        # Text parameters scaled by resolution
        params = {
            'main_font_scale': max(0.6, 1.0 * scale_factor),  # Main shot text
            'tip_font_scale': max(0.5, 0.7 * scale_factor),   # Coaching tip text
            'state_font_scale': max(0.4, 0.5 * scale_factor), # Small state indicator
            'main_thickness': max(1, int(2 * scale_factor)),  # Main text thickness
            'tip_thickness': max(1, int(2 * scale_factor)),   # Tip text thickness
            'state_thickness': max(1, int(1 * scale_factor)), # State text thickness
            'margin': int(10 * scale_factor),                 # Text margins
            'line_height': int(40 * scale_factor),            # Space between lines
            'max_text_width': int(frame_width * 0.8),         # Maximum text width
            'frame_width': frame_width,
            'frame_height': frame_height
        }
        
        return params
    
    def draw_enhanced_shuttlecock(self, frame, shuttle_data):
        """Draw enhanced shuttlecock with trajectory and analytics"""
        cx, cy = shuttle_data['position']
        confidence = shuttle_data['confidence']
        method = shuttle_data.get('method', 'Unknown')
        
        # Main shuttlecock indicator - size and color based on confidence
        if confidence > 0.8:
            shuttle_color = (0, 255, 255)  # Bright yellow
            radius = 15
            thickness = -1
        elif confidence > 0.5:
            shuttle_color = (0, 200, 255)  # Orange
            radius = 12
            thickness = -1
        else:
            shuttle_color = (0, 100, 255)  # Red
            radius = 10
            thickness = 2
        
        # Draw main circle
        cv2.circle(frame, (cx, cy), radius, shuttle_color, thickness)
        cv2.circle(frame, (cx, cy), radius + 3, shuttle_color, 2)
        
        # Detection method indicator
        method_colors = {'YOLO': (255, 0, 255), 'Motion': (255, 255, 0), 'Color': (0, 255, 0)}
        method_color = method_colors.get(method, (255, 255, 255))
        cv2.circle(frame, (cx, cy), radius + 6, method_color, 1)
        
        # Bounding box if available
        if shuttle_data.get('bbox'):
            bx1, by1, bx2, by2 = shuttle_data['bbox']
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), shuttle_color, 1)
        
        # Trajectory trail
        if hasattr(self, 'shuttle_history') and len(self.shuttle_history) > 1:
            self.draw_shuttlecock_trail(frame, shuttle_color)
        
        # Predicted position
        if hasattr(self, 'shuttle_history') and len(self.shuttle_history) >= 3:
            predicted = self.predict_position()
            if predicted:
                px, py = predicted
                cv2.circle(frame, (px, py), 8, (255, 255, 255), 2)
                cv2.putText(frame, "PRED", (px-15, py-15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                cv2.line(frame, (cx, cy), (px, py), (255, 255, 255), 1, cv2.LINE_AA)
        
        # Information label
        label = f"Shuttle ({confidence:.2f}) [{method}]"
        label_pos = (max(10, cx - 60), max(25, cy - 25))
        
        # Background for label
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        cv2.rectangle(frame, 
                     (label_pos[0] - 2, label_pos[1] - label_size[1] - 2),
                     (label_pos[0] + label_size[0] + 2, label_pos[1] + 2),
                     (0, 0, 0), -1)
        
        cv2.putText(frame, label, label_pos, 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, shuttle_color, 1)
        
        # Velocity vector
        if hasattr(self, 'shuttle_speed') and self.shuttle_speed > 5:
            if hasattr(self, 'shuttle_direction'):
                vector_length = min(50, self.shuttle_speed * 2)
                angle_rad = self.shuttle_direction * math.pi / 180
                
                end_x = int(cx + vector_length * math.cos(angle_rad))
                end_y = int(cy + vector_length * math.sin(angle_rad))
                
                cv2.arrowedLine(frame, (cx, cy), (end_x, end_y), 
                               (255, 0, 255), 2, tipLength=0.3)
        
        # Speed indicator ring
        if hasattr(self, 'shuttle_speed'):
            speed_radius = int(radius + 10 + min(20, self.shuttle_speed / 2))
            speed_intensity = min(255, int(self.shuttle_speed * 10))
            speed_color = (0, speed_intensity, 255)
            cv2.circle(frame, (cx, cy), speed_radius, speed_color, 1)
    
    def draw_shuttlecock_trail(self, frame, shuttle_color):
        """Draw shuttlecock trail with fading effect"""
        if len(self.shuttle_history) < 2:
            return
        
        trail_length = min(15, len(self.shuttle_history))
        trail_points = self.shuttle_history[-trail_length:]
        
        for i in range(1, len(trail_points)):
            fade_factor = i / len(trail_points)
            faded_color = tuple(int(c * fade_factor) for c in shuttle_color)
            
            pt1 = trail_points[i-1]
            pt2 = trail_points[i]
            
            thickness = max(1, int(3 * fade_factor))
            cv2.line(frame, pt1, pt2, faded_color, thickness, cv2.LINE_AA)
            
            if i % 2 == 0:
                radius = max(1, int(3 * fade_factor))
                cv2.circle(frame, pt2, radius, faded_color, -1)
    
    def draw_game_state_indicator(self, frame, game_state):
        """Draw game state indicator in corner"""
        colors = {
            "static": (128, 128, 128),
            "ready_position": (0, 255, 255),
            "active_play": (0, 255, 0)
        }
        
        state_color = colors.get(game_state, (255, 255, 255))
        frame_height, frame_width = frame.shape[:2]
        
        # State indicator circle
        cv2.circle(frame, (frame_width - 50, 50), 20, state_color, -1)
        cv2.circle(frame, (frame_width - 50, 50), 22, (255, 255, 255), 2)
        
        # State text
        labels = {
            "static": "STATIC",
            "ready_position": "READY",
            "active_play": "ACTIVE"
        }
        
        label = labels.get(game_state, "UNKNOWN")
        cv2.putText(frame, label, (frame_width - 120, 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, state_color, 2)
    
    def draw_shuttlecock_analytics(self, frame):
        """Draw shuttlecock analytics panel"""
        frame_height, frame_width = frame.shape[:2]
        
        # Analytics panel
        panel_x, panel_y = 10, frame_height - 120
        panel_width, panel_height = 250, 110
        
        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, panel_y), 
                     (panel_x + panel_width, panel_y + panel_height), 
                     (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Panel border
        cv2.rectangle(frame, (panel_x, panel_y), 
                     (panel_x + panel_width, panel_y + panel_height), 
                     (255, 255, 255), 1)
        
        # Title
        cv2.putText(frame, "SHUTTLECOCK ANALYTICS", 
                   (panel_x + 5, panel_y + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # Speed
        speed_text = f"Speed: {self.shuttle_speed:.1f} px/frame"
        cv2.putText(frame, speed_text, (panel_x + 5, panel_y + 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Direction
        if hasattr(self, 'shuttle_direction'):
            direction_text = f"Direction: {self.shuttle_direction:.1f}°"
            cv2.putText(frame, direction_text, (panel_x + 5, panel_y + 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Acceleration
        if hasattr(self, 'shuttle_acceleration'):
            accel_text = f"Acceleration: {self.shuttle_acceleration:.1f}"
            cv2.putText(frame, accel_text, (panel_x + 5, panel_y + 80), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Detection count
        detection_count = len(self.shuttle_history) if hasattr(self, 'shuttle_history') else 0
        count_text = f"Detections: {detection_count}"
        cv2.putText(frame, count_text, (panel_x + 5, panel_y + 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    def analyze_video(self, video_path, output_path=None, show_live=False):
        """Analyze video with enhanced shuttlecock tracking"""
        logger.info(f"🏸 Starting enhanced video analysis: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        # Video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"📊 Video: {total_frames} frames, {fps} FPS, {width}x{height}")
        logger.info(f"⚠️ Press Ctrl+C anytime to stop and get partial results")
        logger.info(f"👥 Dual-player analysis enabled!")
        
        # Video writer setup
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_number = 0
        self.shot_history = []
        interrupted = False
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                timestamp = frame_number / fps
                
                # Analyze frame - now returns list of shot data for multiple players
                all_shot_data, pose_results = self.analyze_frame(frame, frame_number, timestamp)
                
                # Store actual shots only
                for shot_data in all_shot_data:
                    if (shot_data and 
                        shot_data.shot_type not in ["static", "ready_position", "unknown"] and 
                        shot_data.confidence > 0.5):
                        
                        self.shot_history.append(shot_data)
                        self.session_stats[shot_data.shot_type] += 1
                        # Store last shot per player for static display
                        self.last_shot_by_player[shot_data.player_id] = shot_data
                        
                        logger.info(f"Frame {frame_number}: {shot_data.player_id} - {shot_data.shot_type} "
                                   f"(confidence: {shot_data.confidence:.2f})")
                
                # Log static/ready states less frequently
                if frame_number % (fps * 2) == 0:
                    for shot_data in all_shot_data:
                        if (shot_data and 
                            shot_data.shot_type in ["static", "ready_position"]):
                            
                            logger.info(f"Frame {frame_number}: {shot_data.player_id} - {shot_data.shot_type} "
                                       f"(confidence: {shot_data.confidence:.2f})")
                
                # Draw enhanced annotations - pass all shot data
                annotated_frame = self.draw_annotations(frame, all_shot_data, pose_results)
                
                # Live view
                if show_live:
                    cv2.imshow('Enhanced Badminton Analysis - Press Q to quit, Ctrl+C for results', 
                              annotated_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        logger.info("🛑 User quit via 'Q' key")
                        interrupted = True
                        break
                
                # Save annotated video
                if output_path:
                    out.write(annotated_frame)
                
                frame_number += 1
                
                # Enhanced progress updates
                if frame_number % (fps * 3) == 0:  # Every 3 seconds
                    progress = (frame_number / total_frames) * 100
                    shots_so_far = len(self.shot_history)
                    
                    # Check for shuttlecock in any player data
                    shuttle_status = "❌"
                    for shot_data in all_shot_data:
                        if shot_data and hasattr(shot_data, 'shuttlecock_data'):
                            shuttle_status = "✅"
                            break
                    
                    # Show states of both players
                    player_states = []
                    for shot_data in all_shot_data:
                        if shot_data:
                            player_id = shot_data.player_id.replace("player_", "P").replace("_left", "L").replace("_right", "R")
                            player_states.append(f"{player_id}:{shot_data.shot_type}")
                    
                    states_str = " | ".join(player_states) if player_states else "no players"
                    
                    logger.info(f"Progress: {progress:.1f}% | Shots: {shots_so_far} | "
                               f"Shuttle: {shuttle_status} | Players: {states_str}")
                
        except KeyboardInterrupt:
            logger.info(f"\n🛑 Analysis interrupted at frame {frame_number}")
            logger.info(f"📊 Processed {frame_number}/{total_frames} frames ({(frame_number/total_frames)*100:.1f}%)")
            interrupted = True
        
        finally:
            cap.release()
            if output_path:
                out.release()
            if show_live:
                cv2.destroyAllWindows()
        
        # Generate results
        shots_detected = len(self.shot_history)
        if shots_detected > 0:
            logger.info(f"✅ Analysis {'interrupted' if interrupted else 'complete'}! "
                       f"Detected {shots_detected} shots")
            
            if hasattr(self, 'shuttle_history'):
                shuttle_detections = len(self.shuttle_history)
                logger.info(f"🎾 Shuttlecock tracked in {shuttle_detections} frames")
            
            return self.generate_report(interrupted, frame_number, total_frames)
        else:
            logger.warning("⚠️ No shots detected")
            return {
                "message": "No shots detected", 
                "interrupted": interrupted,
                "frames_processed": frame_number,
                "total_frames": total_frames
            }
    
    def generate_report(self, interrupted=False, frames_processed=None, total_frames=None):
        """Generate comprehensive analysis report"""
        if not self.shot_history:
            return {
                "message": "No shots detected",
                "interrupted": interrupted,
                "frames_processed": frames_processed or 0,
                "total_frames": total_frames or 0
            }
        
        # Basic statistics
        total_shots = len(self.shot_history)
        shot_distribution = dict(self.session_stats)
        
        # Timeline and confidence
        shot_timeline = [(shot.timestamp, shot.shot_type) for shot in self.shot_history]
        avg_confidence = np.mean([shot.confidence for shot in self.shot_history])
        
        # Performance insights
        unique_shots = len(set([shot.shot_type for shot in self.shot_history]))
        low_confidence_shots = len([shot for shot in self.shot_history if shot.confidence < 0.6])
        
        insights = []
        if unique_shots < 4:
            insights.append({
                "category": "Shot Variety",
                "level": "improvement_needed",
                "message": f"Only {unique_shots} shot types detected. Expand your repertoire."
            })
        
        if low_confidence_shots > total_shots * 0.3:
            insights.append({
                "category": "Technique Consistency", 
                "level": "improvement_needed",
                "message": "Many low-confidence shots. Focus on consistent technique."
            })
        
        # Calculate coverage
        max_timestamp = max([shot.timestamp for shot in self.shot_history]) if self.shot_history else 0
        
        report = {
            "analysis_info": {
                "interrupted": interrupted,
                "completion_status": "Partial (interrupted)" if interrupted else "Complete",
                "frames_processed": frames_processed or "Complete",
                "total_frames": total_frames or "Unknown",
                "analysis_coverage": f"{(frames_processed/total_frames)*100:.1f}%" if (frames_processed and total_frames) else "100%"
            },
            "session_summary": {
                "total_shots": total_shots,
                "video_duration_analyzed": max_timestamp,
                "avg_confidence": avg_confidence,
                "shots_per_minute": total_shots / (max_timestamp / 60) if max_timestamp > 0 else 0,
                "unique_shot_types": unique_shots
            },
            "shot_distribution": shot_distribution,
            "shot_timeline": shot_timeline,
            "performance_insights": insights,
            "shuttlecock_stats": {
                "total_detections": len(self.shuttle_history) if hasattr(self, 'shuttle_history') else 0,
                "avg_speed": getattr(self, 'shuttle_speed', 0),
                "tracking_enabled": True
            }
        }
        
        return report
    
    def save_report(self, report, filename=None):
        """Save analysis report"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"enhanced_badminton_analysis_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📄 Report saved: {filename}")
        return filename

def main():
    """Main function"""
    print("🏸 Enhanced Badminton Dual-Player Shot Analysis 🏸")
    print("=" * 80)
    
    # Get video input
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        video_path = input("Enter video file path: ").strip().strip('"').strip("'")
    
    if not Path(video_path).exists():
        print(f"❌ Video file not found: {video_path}")
        return
    
    # Initialize analyzer
    analyzer = BadmintonShotAnalyzer()
    
    print(f"\n🎬 Analyzing video: {Path(video_path).name}")
    
    # User preferences
    show_live = input("Show live analysis with dual-player display? (y/n): ").lower().startswith('y')
    save_annotated = input("Save annotated video with dual-player overlays? (y/n): ").lower().startswith('y')
    
    output_path = None
    if save_annotated:
        output_path = f"enhanced_{Path(video_path).stem}.mp4"
    
    try:
        report = analyzer.analyze_video(video_path, output_path, show_live)
        
        # Display results
        print("\n" + "=" * 80)
        if report.get("interrupted"):
            print("🛑 PARTIAL ANALYSIS RESULTS (INTERRUPTED)")
        else:
            print("🏆 ENHANCED ANALYSIS COMPLETE")
        print("=" * 80)
        
        # Analysis info
        if report.get("analysis_info"):
            info = report["analysis_info"]
            print(f"📊 Status: {info['completion_status']}")
            if info.get("analysis_coverage"):
                print(f"📈 Coverage: {info['analysis_coverage']}")
        
        # Session summary
        if "session_summary" in report:
            summary = report["session_summary"]
            print(f"🎯 Total Shots: {summary['total_shots']}")
            print(f"⏱️ Duration Analyzed: {summary['video_duration_analyzed']:.1f}s")
            print(f"📊 Avg Confidence: {summary['avg_confidence']:.2f}")
            print(f"🏸 Shots/Minute: {summary['shots_per_minute']:.1f}")
            print(f"🎪 Unique Shot Types: {summary['unique_shot_types']}")
            
            # Shot distribution
            print(f"\n📋 Shot Distribution:")
            for shot_type, count in report["shot_distribution"].items():
                percentage = (count / summary['total_shots']) * 100
                print(f"   {shot_type}: {count} ({percentage:.1f}%)")
            
            # Shuttlecock stats
            if "shuttlecock_stats" in report:
                shuttle_stats = report["shuttlecock_stats"]
                print(f"\n🎾 Shuttlecock Tracking:")
                print(f"   Total Detections: {shuttle_stats['total_detections']}")
                print(f"   Average Speed: {shuttle_stats['avg_speed']:.1f} px/frame")
            
            # Performance insights
            print(f"\n💡 Performance Insights:")
            for insight in report["performance_insights"]:
                level_emoji = "⚠️" if insight["level"] == "improvement_needed" else "✅"
                print(f"   {level_emoji} {insight['category']}: {insight['message']}")
        else:
            print(f"ℹ️ {report.get('message', 'No results available')}")
        
        # Save report
        report_file = analyzer.save_report(report)
        print(f"\n📄 Detailed report: {report_file}")
        
        if output_path:
            print(f"🎥 Enhanced video: {output_path}")
            print(f"   ✨ Includes dual-player display, pose tracking, and shot analysis!")
        
        # Success message
        if report.get("interrupted"):
            print(f"\n💡 Analysis stopped early but results are valid!")
        else:
            print(f"\n🎉 Dual-player analysis complete!")
            
    except KeyboardInterrupt:
        print(f"\n🛑 Analysis cancelled by user!")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"\n❌ Analysis failed: {e}")

if __name__ == "__main__":
    main()