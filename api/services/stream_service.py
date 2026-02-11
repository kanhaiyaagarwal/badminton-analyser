"""
Stream Service - Real-time frame analysis for live streaming.

This service manages live streaming sessions and uses FrameAnalyzer
for real-time shot detection and movement tracking.

Post-analysis: After a stream ends, the collected raw_frame_data can
be fed through the ShotClassifier pipeline (hit detection, hit-centric
classification, rally building) and an annotated video + frame_data.json
written for the FrameViewer.
"""

import cv2
import numpy as np
import base64
import json
import math
import os
import tempfile
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

from .frame_analyzer import FrameAnalyzer, CourtBoundary, ShotData

logger = logging.getLogger(__name__)


@dataclass
class StreamStats:
    """Real-time streaming statistics."""
    total_shots: int = 0
    current_rally: int = 0
    shot_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_shot_type: Optional[str] = None
    last_shot_confidence: float = 0.0
    last_shot_timestamp: float = 0.0
    frames_processed: int = 0
    player_detected_frames: int = 0


@dataclass
class StreamShotEvent:
    """Event emitted when a shot is detected."""
    shot_type: str
    confidence: float
    timestamp: float
    rally_id: int
    coaching_tip: str = ""


@dataclass
class StreamPositionEvent:
    """Event emitted for position updates."""
    x: int
    y: int
    timestamp: float


class BasicStreamAnalyzer:
    """
    Real-time stream analyzer for live badminton analysis.

    Processes individual frames from a live stream and emits events
    for shot detection, position updates, and statistics.

    When enable_post_analysis=True, also collects raw_frame_data and
    writes raw video to disk for post-stream detailed analysis.
    """

    # Skeleton connections for drawing from serialized landmarks
    SKELETON_CONNECTIONS = [
        # Torso
        (11, 12), (11, 23), (12, 24), (23, 24),
        # Left arm
        (11, 13), (13, 15),
        # Right arm
        (12, 14), (14, 16),
        # Left leg
        (23, 25), (25, 27),
        # Right leg
        (24, 26), (26, 28),
    ]

    # Color palette for shuttle trail segments between hits
    HIT_TRAIL_COLORS = [
        (0, 255, 0),     # Green
        (0, 165, 255),   # Orange
        (255, 0, 255),   # Magenta
        (255, 255, 0),   # Cyan
        (0, 0, 255),     # Red
        (255, 0, 0),     # Blue
        (0, 255, 255),   # Yellow
        (255, 100, 255), # Pink
    ]

    ACTUAL_SHOTS = ['smash', 'clear', 'drop_shot', 'net_shot', 'drive', 'lift']

    def __init__(
        self,
        court_boundary: dict,
        session_id: int = 0,
        frame_rate: float = 30.0,
        velocity_thresholds: Optional[Dict[str, float]] = None,
        position_thresholds: Optional[Dict[str, float]] = None,
        shot_cooldown_seconds: float = 0.4,
        enable_post_analysis: bool = True,
        enable_tuning_data: bool = False,
        enable_shuttle_tracking: bool = True,
        output_dir: Optional[str] = None,
    ):
        self.session_id = session_id
        self.court = CourtBoundary.from_dict(court_boundary)
        self._court_boundary_dict = court_boundary
        self._velocity_thresholds = velocity_thresholds
        self._position_thresholds = position_thresholds
        self._shot_cooldown_seconds = shot_cooldown_seconds
        self.frame_rate = frame_rate

        # Post-analysis options
        self.enable_post_analysis = enable_post_analysis
        self.enable_tuning_data = enable_tuning_data
        self.enable_shuttle_tracking = enable_shuttle_tracking

        # Initialize frame analyzer
        use_static_mode = frame_rate <= 15
        self.frame_analyzer = FrameAnalyzer(
            court_boundary=self.court,
            processing_width=640,
            model_complexity=1,
            min_detection_confidence=0.3,
            min_tracking_confidence=0.3,
            effective_fps=frame_rate,
            velocity_thresholds=velocity_thresholds,
            position_thresholds=position_thresholds,
            shot_cooldown_seconds=shot_cooldown_seconds,
            static_image_mode=use_static_mode
        )

        # Streaming state
        self.stats = StreamStats()
        self.shot_history: List[ShotData] = []
        self.foot_positions: List[Dict] = []

        # Rally tracking
        self.current_rally_shots: List[ShotData] = []
        self.rally_id_counter = 0
        self.frames_since_last_shot = 0
        self.rally_gap_threshold = 90  # frames (~3 seconds at 30fps)

        # Recording (annotated recording)
        self.is_recording = False
        self.recorded_frames: List[bytes] = []

        self._frame_counter = 0
        self._start_time = datetime.now()
        self._frame_width = 0
        self._frame_height = 0

        # --- Post-analysis data collection ---
        self.raw_frame_data: List[dict] = []
        self.serialized_landmarks: List[Optional[List[dict]]] = []
        self._raw_video_writer: Optional[cv2.VideoWriter] = None
        self.raw_video_path: Optional[str] = None
        self._output_dir = output_dir

        # Shuttle tracking
        self._shuttle_tracker = None
        self._shuttle_frame_buffer: List[np.ndarray] = []
        if enable_shuttle_tracking and enable_post_analysis:
            self._init_shuttle_tracker()

        logger.info(
            f"StreamAnalyzer initialized for session {session_id} "
            f"(post_analysis={enable_post_analysis}, tuning={enable_tuning_data}, "
            f"shuttle={enable_shuttle_tracking})"
        )

    def _init_shuttle_tracker(self):
        """Initialize shuttle tracker if available."""
        try:
            from .shuttle_service import ShuttleService
            if ShuttleService.is_available():
                self._shuttle_tracker = ShuttleService.create_tracker()
                if self._shuttle_tracker:
                    logger.info(f"Session {self.session_id}: Shuttle tracker initialized")
                else:
                    logger.warning(f"Session {self.session_id}: Shuttle tracker creation failed")
            else:
                logger.info(f"Session {self.session_id}: Shuttle tracking unavailable (no weights)")
        except Exception as e:
            logger.warning(f"Session {self.session_id}: Shuttle tracker init failed: {e}")

    def _open_raw_video_writer(self, width: int, height: int):
        """Open raw video writer on first frame."""
        if self._raw_video_writer is not None:
            return

        if self._output_dir:
            raw_dir = Path(self._output_dir) / "stream_raw" / str(self.session_id)
        else:
            raw_dir = Path(tempfile.gettempdir()) / "badminton_streams" / str(self.session_id)
        raw_dir.mkdir(parents=True, exist_ok=True)

        self.raw_video_path = str(raw_dir / "raw_stream.mp4")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = max(1, int(self.frame_rate))
        self._raw_video_writer = cv2.VideoWriter(
            self.raw_video_path, fourcc, fps, (width, height)
        )
        logger.info(f"Session {self.session_id}: Raw video writer opened at {self.raw_video_path}")

    def process_frame(self, frame_data: bytes, timestamp: float) -> Dict:
        """
        Process a single frame from the stream.

        Args:
            frame_data: JPEG encoded frame data
            timestamp: Frame timestamp in seconds

        Returns:
            Dict with shot, position, shuttle, pose, and stats events
        """
        self._frame_counter += 1
        self.stats.frames_processed += 1

        # Decode frame
        try:
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                logger.warning(f"Failed to decode frame {self._frame_counter}")
                return self._empty_result()
        except Exception as e:
            logger.error(f"Frame decode error: {e}")
            return self._empty_result()

        h, w = frame.shape[:2]
        self._frame_width = w
        self._frame_height = h

        # Write raw frame to disk for post-analysis
        if self.enable_post_analysis:
            self._open_raw_video_writer(w, h)
            if self._raw_video_writer:
                self._raw_video_writer.write(frame)

        # Run shuttle tracking
        shuttle_result = None
        if self._shuttle_tracker is not None:
            shuttle_result = self._track_shuttle(frame)

        # Analyze frame (pose detection + real-time classification)
        result = self.frame_analyzer.analyze_frame(
            frame=frame,
            frame_number=self._frame_counter,
            timestamp=timestamp,
            shot_count=self.stats.total_shots
        )

        # Build response
        response = {
            'shot': None,
            'position': None,
            'pose': None,
            'shuttle': None,
            'stats': None
        }

        # Handle player detection and pose landmarks
        if result.player_detected:
            self.stats.player_detected_frames += 1
            if result.pose_landmarks:
                pose_data = self._extract_pose_data(result.pose_landmarks, w, h)
                if pose_data:
                    response['pose'] = pose_data
                    if self._frame_counter % 60 == 0:
                        logger.info(f"Session {self.session_id}: Pose extracted with {len(pose_data['landmarks'])} landmarks")

        # Handle position update
        if result.foot_position:
            response['position'] = StreamPositionEvent(
                x=result.foot_position[0],
                y=result.foot_position[1],
                timestamp=timestamp
            ).__dict__
            self.foot_positions.append({
                'x': result.foot_position[0],
                'y': result.foot_position[1],
                'timestamp': timestamp,
                'frame': self._frame_counter,
                'rally_id': self.rally_id_counter if self.current_rally_shots else -1
            })

        # Handle shot detection
        if result.is_actual_shot and result.shot_data:
            shot = result.shot_data
            self._handle_shot(shot, timestamp)
            response['shot'] = StreamShotEvent(
                shot_type=shot.shot_type,
                confidence=shot.confidence,
                timestamp=timestamp,
                rally_id=self.rally_id_counter,
                coaching_tip=shot.coaching_tip
            ).__dict__
        else:
            self.frames_since_last_shot += 1
            if (self.frames_since_last_shot > self.rally_gap_threshold and
                len(self.current_rally_shots) > 0):
                self._end_current_rally()

        # Include shuttle in response
        if shuttle_result and shuttle_result.get("visible"):
            response['shuttle'] = {
                'x': shuttle_result['x'],
                'y': shuttle_result['y'],
                'confidence': shuttle_result.get('confidence', 0),
            }

        # Record annotated frame if recording is enabled
        if self.is_recording:
            annotated = self._draw_annotations(
                frame, result.pose_landmarks, result.shot_data if result.is_actual_shot else None
            )
            _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
            self.recorded_frames.append(buf.tobytes())

        # Collect raw_frame_data for post-analysis
        if self.enable_post_analysis:
            self._collect_frame_data(frame, result, timestamp, shuttle_result)

        response['stats'] = self._get_stats_dict()
        return response

    def _track_shuttle(self, frame: np.ndarray) -> Optional[dict]:
        """Run shuttle detection on frame using 3-frame sliding window."""
        self._shuttle_frame_buffer.append(frame)
        if len(self._shuttle_frame_buffer) > 3:
            self._shuttle_frame_buffer.pop(0)

        if len(self._shuttle_frame_buffer) < 3:
            return None

        try:
            visible, x, y, confidence = self._shuttle_tracker.detect_in_frame(self._shuttle_frame_buffer)
            return {
                'visible': visible,
                'x': int(x),
                'y': int(y),
                'confidence': float(confidence),
            }
        except Exception as e:
            if self._frame_counter % 60 == 0:
                logger.warning(f"Session {self.session_id}: Shuttle detection error: {e}")
            return None

    def _collect_frame_data(self, frame: np.ndarray, result, timestamp: float, shuttle_result: Optional[dict]):
        """Collect one raw_frame_data entry per frame (same format as ShotClassifier)."""
        # Get pose state from frame analyzer history
        pose_state = None
        if self.frame_analyzer.pose_history:
            last = self.frame_analyzer.pose_history[-1]
            pose_state = {
                'wrist': last.get('wrist'),
                'elbow': last.get('elbow'),
                'shoulder': last.get('shoulder'),
                'shoulder_center': last.get('shoulder_center'),
                'hip_center': last.get('hip_center'),
            }

        # Court transform
        court_transform = None
        transform = self.frame_analyzer._last_transform
        if transform:
            court_transform = {
                'x1': transform['x1'],
                'y1': transform['y1'],
                'court_w': transform['court_w'],
                'court_h': transform['court_h'],
            }

        # Player bbox
        player_bbox = None
        if result.shot_data and result.shot_data.player_bbox:
            player_bbox = list(result.shot_data.player_bbox)

        entry = {
            'frame_number': self._frame_counter,
            'timestamp': timestamp,
            'player_detected': result.player_detected,
            'pose_state': pose_state,
            'shuttle': shuttle_result,
            'court_transform': court_transform,
            'player_bbox': player_bbox,
            'foot_position': list(result.foot_position) if result.foot_position else None,
        }

        self.raw_frame_data.append(entry)

        # Serialize all 33 landmarks if tuning data is enabled
        if self.enable_tuning_data and result.pose_landmarks:
            lm_list = []
            for lm in result.pose_landmarks.landmark:
                lm_list.append({
                    'x': lm.x,
                    'y': lm.y,
                    'z': lm.z,
                    'visibility': lm.visibility,
                })
            self.serialized_landmarks.append(lm_list)
        elif self.enable_tuning_data:
            self.serialized_landmarks.append(None)

    # ------------------------------------------------------------------
    # Post-analysis pipeline
    # ------------------------------------------------------------------

    def run_post_analysis(self, output_dir: str, progress_callback=None) -> dict:
        """
        Run full post-analysis pipeline on collected raw_frame_data.

        1) Release raw video writer
        2) Phase 2: ShotClassifier.classify_all()
        3) Phase 3: Write annotated video
        4) Extract tuning data (if enabled)

        Returns dict with paths and classified summary.
        """
        # Release raw video writer
        if self._raw_video_writer:
            self._raw_video_writer.release()
            self._raw_video_writer = None

        if not self.raw_frame_data:
            return {"error": "No frame data collected"}

        fps = max(1, int(self.frame_rate))
        w = self._frame_width
        h = self._frame_height

        if progress_callback:
            progress_callback(5, "Starting classification")

        # Phase 2: Classify
        try:
            from .shot_classifier import ShotClassifier
            sc = ShotClassifier(
                velocity_thresholds=self._velocity_thresholds,
                position_thresholds=self._position_thresholds,
                shot_cooldown_seconds=self._shot_cooldown_seconds or 0.4,
                effective_fps=self.frame_rate,
            )
            classified = sc.classify_all(self.raw_frame_data, fps)
        except Exception as e:
            logger.error(f"Session {self.session_id}: Classification failed: {e}", exc_info=True)
            return {"error": f"Classification failed: {e}"}

        if progress_callback:
            progress_callback(40, "Classification complete, writing annotated video")

        # Phase 3: Write annotated video
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        annotated_path = str(out_dir / "annotated_stream.mp4")

        if self.raw_video_path and Path(self.raw_video_path).exists():
            try:
                self._write_annotated_video(
                    self.raw_video_path, annotated_path,
                    self.raw_frame_data, classified, fps, w, h
                )
            except Exception as e:
                logger.error(f"Session {self.session_id}: Annotated video failed: {e}", exc_info=True)
                annotated_path = None
        else:
            logger.warning(f"Session {self.session_id}: No raw video found for annotation")
            annotated_path = None

        if progress_callback:
            progress_callback(75, "Annotated video complete, extracting tuning data")

        # Phase 4: Extract tuning data
        frame_data_path = None
        if self.enable_tuning_data:
            try:
                tuning = self._extract_tuning_data(self.raw_frame_data, classified)
                frame_data_path = str(out_dir / "frame_data.json")
                with open(frame_data_path, 'w') as f:
                    json.dump(tuning, f)
                logger.info(f"Session {self.session_id}: Tuning data written ({len(tuning)} frames)")
            except Exception as e:
                logger.error(f"Session {self.session_id}: Tuning data extraction failed: {e}", exc_info=True)
                frame_data_path = None

        if progress_callback:
            progress_callback(100, "Post-analysis complete")

        summary = classified.get("summary", {})
        return {
            "annotated_video_path": annotated_path,
            "raw_video_path": self.raw_video_path,
            "frame_data_path": frame_data_path,
            "summary": summary,
            "shot_distribution": classified.get("shot_distribution", {}),
            "total_shots": summary.get("total_shots", 0),
            "total_rallies": summary.get("total_rallies", 0),
            "shuttle_hits": summary.get("shuttle_hits_detected", 0),
            "shot_timeline": classified.get("shot_timeline", []),
            "rallies": classified.get("rallies", []),
            "shuttle_hits_detail": classified.get("shuttle_hits", []),
            "foot_positions": self.foot_positions,
        }

    def _write_annotated_video(
        self, video_path: str, output_path: str,
        raw_frame_data: List[dict], classified: dict,
        fps: int, width: int, height: int
    ):
        """Phase 3: Read raw video + raw data + classified -> annotate -> write."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Cannot reopen video for annotation: {video_path}")
            return

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # Build lookups
        shot_by_frame = {}
        for shot in classified.get("shots", []):
            shot_by_frame[shot["frame"]] = shot

        hit_by_frame = {}
        for hit in classified.get("shuttle_hits", []):
            hit_by_frame[hit["frame"]] = hit

        # Display state
        current_shot_display = None
        shot_display_frames = 0
        max_display_frames = fps  # ~1 second

        # Rolling shuttle trajectory (2-second window)
        trajectory_window = int(fps * 2)
        shuttle_trail = deque(maxlen=trajectory_window)
        max_jump_per_frame = math.hypot(width, height) * 0.2
        last_trail_frame = None
        hit_color_idx = 0

        frame_number = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_data = raw_frame_data[frame_number] if frame_number < len(raw_frame_data) else {}

                # Draw court boundary
                self._draw_court_boundary(frame)

                # Draw skeleton from serialized landmarks
                if self.enable_tuning_data and frame_number < len(self.serialized_landmarks):
                    landmarks = self.serialized_landmarks[frame_number]
                else:
                    landmarks = None

                ct = frame_data.get("court_transform")
                if landmarks and ct:
                    pose_color = (128, 128, 128)
                    if frame_number in shot_by_frame:
                        current_shot_display = shot_by_frame[frame_number]
                        shot_display_frames = 0
                        pose_color = (0, 255, 0)
                    elif current_shot_display and shot_display_frames < max_display_frames:
                        pose_color = (0, 255, 0)
                    self._draw_serialized_skeleton(frame, landmarks, ct, pose_color)

                # Shuttle trail
                shuttle_data = frame_data.get("shuttle")
                if shuttle_data and shuttle_data.get("visible"):
                    sx, sy = shuttle_data["x"], shuttle_data["y"]

                    # Outlier filter
                    if shuttle_trail and last_trail_frame is not None:
                        gap = max(1, frame_number - last_trail_frame)
                        if math.hypot(sx - shuttle_trail[-1][0], sy - shuttle_trail[-1][1]) > max_jump_per_frame * gap:
                            shuttle_trail.clear()

                    if frame_number in hit_by_frame:
                        hit_color_idx += 1

                    shuttle_trail.append((sx, sy, hit_color_idx, None))
                    last_trail_frame = frame_number

                # Draw shuttle marker
                self._draw_shuttle_marker(frame, shuttle_data)

                # Draw shuttle trail
                self._draw_shuttle_trail(frame, shuttle_trail)

                # Draw shot label (persists ~1 second)
                if current_shot_display and shot_display_frames < max_display_frames:
                    shot_text = f"{current_shot_display['shot_type'].upper()} ({current_shot_display['confidence']:.0%})"
                    speed = current_shot_display.get("shuttle_speed_px_per_sec")
                    if speed is not None:
                        shot_text += f" | {speed:.0f} px/s"
                    text_size = cv2.getTextSize(shot_text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
                    cv2.rectangle(frame, (5, 10), (15 + text_size[0], 50), (0, 0, 0), -1)
                    colors = {
                        'smash': (0, 0, 255), 'clear': (0, 255, 0),
                        'drop_shot': (255, 165, 0), 'net_shot': (255, 255, 0),
                        'drive': (255, 0, 255), 'lift': (255, 200, 100),
                    }
                    color = colors.get(current_shot_display["shot_type"], (255, 255, 255))
                    cv2.putText(frame, shot_text, (10, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
                    shot_display_frames += 1

                # Draw shuttle hit marker
                if frame_number in hit_by_frame:
                    hit = hit_by_frame[frame_number]
                    hx, hy = hit["hit_position"]["x"], hit["hit_position"]["y"]
                    cv2.circle(frame, (hx, hy), 15, (0, 0, 255), 3)
                    cv2.putText(frame, "HIT", (hx + 18, hy - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                # Draw stats panel
                self._draw_classified_stats(frame, classified)

                # Draw player bbox
                bbox = frame_data.get("player_bbox")
                if bbox and landmarks:
                    x1, y1, x2, y2 = bbox
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                out.write(frame)
                frame_number += 1

        finally:
            cap.release()
            out.release()

        logger.info(f"Annotated video written: {output_path} ({frame_number} frames)")

    def _draw_court_boundary(self, frame: np.ndarray):
        """Draw court boundary overlay on frame."""
        polygon = self.court.get_polygon()
        overlay = frame.copy()
        cv2.fillPoly(overlay, [polygon], (0, 100, 0))
        cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
        cv2.polylines(frame, [polygon], True, (0, 255, 255), 2)

    def _draw_serialized_skeleton(
        self, frame: np.ndarray, landmarks: List[dict],
        court_transform: dict, pose_color: tuple
    ):
        """Draw skeleton from serialized landmarks [{x, y, visibility}, ...] + court_transform."""
        ct_x1 = court_transform.get("x1", 0)
        ct_y1 = court_transform.get("y1", 0)
        ct_w = court_transform.get("court_w", 1)
        ct_h = court_transform.get("court_h", 1)

        def to_px(lm):
            if lm.get("visibility", 0) < 0.5:
                return None
            x = int(lm["x"] * ct_w + ct_x1)
            y = int(lm["y"] * ct_h + ct_y1)
            return (x, y)

        # Draw connections
        for i, j in self.SKELETON_CONNECTIONS:
            if i < len(landmarks) and j < len(landmarks):
                p1 = to_px(landmarks[i])
                p2 = to_px(landmarks[j])
                if p1 and p2:
                    cv2.line(frame, p1, p2, (255, 0, 0), 2)

        # Draw landmark points
        for lm in landmarks:
            pt = to_px(lm)
            if pt:
                cv2.circle(frame, pt, 3, pose_color, -1)

    def _draw_shuttle_marker(self, frame: np.ndarray, shuttle_data: Optional[dict]):
        """Draw shuttle position marker."""
        if not shuttle_data or not shuttle_data.get("visible"):
            return
        x, y = shuttle_data["x"], shuttle_data["y"]
        confidence = shuttle_data.get("confidence", 0)
        cv2.circle(frame, (x, y), 4, (0, 255, 255), -1)
        cv2.line(frame, (x - 12, y), (x + 12, y), (0, 255, 255), 1)
        cv2.line(frame, (x, y - 12), (x, y + 12), (0, 255, 255), 1)
        cv2.putText(frame, f"Shuttle ({confidence:.2f})", (x + 10, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    def _draw_shuttle_trail(self, frame: np.ndarray, shuttle_trail: deque):
        """Draw rolling shuttle trajectory with color cycling between hits."""
        if len(shuttle_trail) < 2:
            return
        points = list(shuttle_trail)
        for i in range(1, len(points)):
            x1, y1 = points[i - 1][0], points[i - 1][1]
            x2, y2 = points[i][0], points[i][1]
            alpha = 0.3 + 0.7 * (i / len(points))
            color_idx = points[i][2]
            base_color = self.HIT_TRAIL_COLORS[color_idx % len(self.HIT_TRAIL_COLORS)]
            color = tuple(int(c * alpha) for c in base_color)
            thickness = max(1, int(2 * alpha))
            cv2.line(frame, (x1, y1), (x2, y2), color, thickness)

    def _draw_classified_stats(self, frame: np.ndarray, classified: dict):
        """Draw stats panel from classified results."""
        h, w = frame.shape[:2]
        summary = classified.get("summary", {})
        dist = classified.get("shot_distribution", {})

        panel_x, panel_y = 10, h - 140
        panel_w, panel_h = 280, 130

        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, panel_y),
                     (panel_x + panel_w, panel_y + panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        cv2.rectangle(frame, (panel_x, panel_y),
                     (panel_x + panel_w, panel_y + panel_h), (255, 255, 255), 1)

        cv2.putText(frame, "SESSION STATS", (panel_x + 10, panel_y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        y_offset = panel_y + 50
        stats_text = [
            f"Shots: {summary.get('total_shots', 0)} | Rallies: {summary.get('total_rallies', 0)}",
            f"Smash: {dist.get('smash', 0)} | Clear: {dist.get('clear', 0)}",
            f"Drop: {dist.get('drop_shot', 0)} | Drive: {dist.get('drive', 0)}",
            f"Net: {dist.get('net_shot', 0)} | Lift: {dist.get('lift', 0)}",
        ]
        shuttle_rate = summary.get("shuttle_detection_rate")
        if shuttle_rate is not None:
            stats_text.append(f"Shuttle: {shuttle_rate:.0%} | Hits: {summary.get('shuttle_hits_detected', 0)}")

        for text in stats_text:
            cv2.putText(frame, text, (panel_x + 10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            y_offset += 18

    def _extract_tuning_data(self, raw_frame_data: List[dict], classified: dict) -> List[dict]:
        """Extract tuning-compatible per-frame metrics for FrameViewer.

        Adapted from v2_court_bounded_analyzer._extract_tuning_data().
        """
        from .shot_classifier import ShotClassifier

        V = self.frame_analyzer.VELOCITY_THRESHOLDS
        P = self.frame_analyzer.POSITION_THRESHOLDS

        sc = ShotClassifier(
            velocity_thresholds=V,
            position_thresholds=P,
            shot_cooldown_seconds=self._shot_cooldown_seconds or 0.4,
            effective_fps=self.frame_rate,
        )
        velocity_data = sc._compute_velocities(raw_frame_data)

        # Per-frame classification
        per_frame_classification = {}
        last_shot_ts = -999.0
        for i, fd in enumerate(raw_frame_data):
            if not fd.get("player_detected") or not fd.get("pose_state"):
                continue
            vel = velocity_data[i] if i < len(velocity_data) else {}
            if not vel:
                continue
            ps = fd["pose_state"]
            swing = sc._classify_swing(
                vel["wrist_velocity"], vel["wrist_direction"],
                ps, vel.get("wrist_dy_per_sec", 0),
                vel.get("pose_history_window", []),
            )
            shot_type, confidence = sc._classify_shot(swing, vel["wrist_velocity"])
            ts = fd["timestamp"]
            cooldown_active = False
            if shot_type in sc.ACTUAL_SHOTS and confidence > 0.5:
                if ts - last_shot_ts < sc.shot_cooldown_seconds:
                    shot_type = 'follow_through'
                    confidence = 0.3
                    cooldown_active = True
                else:
                    last_shot_ts = ts
            per_frame_classification[fd["frame_number"]] = {
                "swing_type": swing,
                "shot_type": shot_type,
                "confidence": confidence,
                "cooldown_active": cooldown_active,
            }

        # Replace with hit-centric results when available
        hit_centric_shots = classified.get("shots", [])
        if any(s.get("shuttle_hit_matched") for s in hit_centric_shots):
            per_frame_classification = {}
            for shot in hit_centric_shots:
                fn = shot["frame"]
                per_frame_classification[fn] = {
                    "swing_type": shot.get("swing_type", "none"),
                    "shot_type": shot["shot_type"],
                    "confidence": shot["confidence"],
                    "cooldown_active": False,
                }

        tuning = []
        for i, fd in enumerate(raw_frame_data):
            if not fd.get("player_detected"):
                tuning.append({
                    "frame_number": fd["frame_number"],
                    "timestamp": fd["timestamp"],
                    "player_detected": False,
                })
                continue

            ps = fd.get("pose_state", {})
            wrist_x = ps.get("wrist", (None, None))[0] if ps.get("wrist") else None
            wrist_y = ps.get("wrist", (None, None))[1] if ps.get("wrist") else None
            shoulder_x = ps.get("shoulder", (None, None))[0] if ps.get("shoulder") else None
            shoulder_y = ps.get("shoulder", (None, None))[1] if ps.get("shoulder") else None
            elbow_x = ps.get("elbow", (None, None))[0] if ps.get("elbow") else None
            elbow_y = ps.get("elbow", (None, None))[1] if ps.get("elbow") else None
            hip_x = ps.get("hip_center", (None, None))[0] if ps.get("hip_center") else None
            hip_y = ps.get("hip_center", (None, None))[1] if ps.get("hip_center") else None

            arm_extension = None
            is_overhead = is_low_position = is_arm_extended = is_wrist_between = None
            if wrist_x is not None and shoulder_x is not None:
                arm_extension = math.sqrt((wrist_x - shoulder_x)**2 + (wrist_y - shoulder_y)**2)
                is_overhead = wrist_y < shoulder_y - P['overhead_offset']
                is_arm_extended = arm_extension > P['arm_extension_min']
            if wrist_y is not None and hip_y is not None:
                is_low_position = wrist_y > hip_y - P['low_position_offset']
            if wrist_y is not None and shoulder_y is not None and hip_y is not None:
                is_wrist_between = shoulder_y < wrist_y < hip_y

            vel = velocity_data[i] if i < len(velocity_data) else {}
            cls = per_frame_classification.get(fd["frame_number"], {})

            entry = {
                "frame_number": fd["frame_number"],
                "timestamp": fd["timestamp"],
                "player_detected": True,
                "wrist_x": wrist_x,
                "wrist_y": wrist_y,
                "shoulder_x": shoulder_x,
                "shoulder_y": shoulder_y,
                "elbow_x": elbow_x,
                "elbow_y": elbow_y,
                "hip_x": hip_x,
                "hip_y": hip_y,
                "wrist_velocity": vel.get("wrist_velocity", 0.0),
                "body_velocity": vel.get("body_velocity", 0.0),
                "wrist_direction": vel.get("wrist_direction", "none"),
                "arm_extension": arm_extension,
                "is_overhead": is_overhead,
                "is_low_position": is_low_position,
                "is_arm_extended": is_arm_extended,
                "is_wrist_between_shoulder_hip": is_wrist_between,
                "swing_type": cls.get("swing_type", "none"),
                "shot_type": cls.get("shot_type", "static"),
                "confidence": cls.get("confidence", 0.3),
                "cooldown_active": cls.get("cooldown_active", False),
                "is_actual_shot": cls.get("shot_type", "static") in self.ACTUAL_SHOTS,
            }

            # Shuttle position
            shuttle = fd.get("shuttle")
            if shuttle:
                visible = shuttle.get("visible", False)
                entry["shuttle_x"] = shuttle.get("x") if visible else None
                entry["shuttle_y"] = shuttle.get("y") if visible else None
                entry["shuttle_confidence"] = shuttle.get("confidence")
                entry["shuttle_visible"] = visible

            # Court transform
            ct = fd.get("court_transform")
            if ct:
                entry["court_transform_x1"] = ct.get("x1")
                entry["court_transform_y1"] = ct.get("y1")
                entry["court_transform_w"] = ct.get("court_w")
                entry["court_transform_h"] = ct.get("court_h")

            # Player bbox
            bbox = fd.get("player_bbox")
            if bbox:
                entry["player_bbox_x1"] = bbox[0]
                entry["player_bbox_y1"] = bbox[1]
                entry["player_bbox_x2"] = bbox[2]
                entry["player_bbox_y2"] = bbox[3]

            tuning.append(entry)

        # Post-pass: shuttle velocity/direction and hit flags
        hit_frames = set()
        for hit in classified.get("shuttle_hits", []):
            hit_frames.add(hit.get("frame"))

        prev_shuttle_frame = None
        for entry in tuning:
            if not entry.get("shuttle_visible"):
                entry.setdefault("shuttle_speed", None)
                entry.setdefault("shuttle_dx", None)
                entry.setdefault("shuttle_dy", None)
                entry.setdefault("shuttle_direction", None)
                entry.setdefault("shuttle_is_hit", False)
                continue

            ts = entry.get("timestamp", 0)
            sx = entry.get("shuttle_x")
            sdx = sdy = speed = direction = None
            if prev_shuttle_frame is not None and sx is not None:
                dt = ts - prev_shuttle_frame.get("timestamp", 0)
                if dt > 0:
                    px = prev_shuttle_frame.get("shuttle_x")
                    py = prev_shuttle_frame.get("shuttle_y")
                    sdx = (sx - px) / dt
                    sdy = (entry.get("shuttle_y") - py) / dt
                    speed = round(math.sqrt(sdx * sdx + sdy * sdy), 1)
                    if abs(sdy) > abs(sdx):
                        direction = "up" if sdy < 0 else "down"
                    else:
                        direction = "right" if sdx > 0 else "left"

            entry["shuttle_speed"] = speed
            entry["shuttle_dx"] = round(sdx, 1) if sdx is not None else None
            entry["shuttle_dy"] = round(sdy, 1) if sdy is not None else None
            entry["shuttle_direction"] = direction
            entry["shuttle_is_hit"] = entry.get("frame_number") in hit_frames
            if entry.get("shuttle_visible"):
                prev_shuttle_frame = entry

        return tuning

    # ------------------------------------------------------------------
    # Existing methods (unchanged)
    # ------------------------------------------------------------------

    def _handle_shot(self, shot: ShotData, timestamp: float):
        """Handle detected shot."""
        self.shot_history.append(shot)
        self.current_rally_shots.append(shot)
        self.stats.total_shots += 1
        self.stats.shot_distribution[shot.shot_type] += 1
        self.stats.last_shot_type = shot.shot_type
        self.stats.last_shot_confidence = shot.confidence
        self.stats.last_shot_timestamp = timestamp
        self.frames_since_last_shot = 0
        logger.info(f"Session {self.session_id}: {shot.shot_type} (conf: {shot.confidence:.2f})")

    def _end_current_rally(self):
        """End the current rally."""
        if len(self.current_rally_shots) >= 2:
            self.rally_id_counter += 1
            self.stats.current_rally = self.rally_id_counter
            logger.info(f"Session {self.session_id}: Rally {self.rally_id_counter} ended "
                       f"with {len(self.current_rally_shots)} shots")
        self.current_rally_shots = []

    def _get_stats_dict(self) -> Dict:
        """Get current stats as dict."""
        return {
            'total_shots': self.stats.total_shots,
            'current_rally': self.stats.current_rally,
            'shot_distribution': dict(self.stats.shot_distribution),
            'last_shot_type': self.stats.last_shot_type,
            'last_shot_confidence': self.stats.last_shot_confidence,
            'frames_processed': self.stats.frames_processed,
            'player_detection_rate': (
                self.stats.player_detected_frames / self.stats.frames_processed
                if self.stats.frames_processed > 0 else 0
            )
        }

    def _extract_pose_data(self, pose_landmarks, frame_width: int, frame_height: int) -> Dict:
        """Extract pose landmarks as serializable data for frontend."""
        transform = self.frame_analyzer._last_transform
        if not transform:
            return None

        x1 = transform['x1']
        y1 = transform['y1']
        court_w = transform['court_w']
        court_h = transform['court_h']

        landmarks = []
        for i, lm in enumerate(pose_landmarks.landmark):
            full_x = int(lm.x * court_w + x1)
            full_y = int(lm.y * court_h + y1)
            landmarks.append({
                'x': full_x,
                'y': full_y,
                'visibility': lm.visibility
            })

        connections = [
            (11, 12), (11, 23), (12, 24), (23, 24),
            (11, 13), (13, 15),
            (12, 14), (14, 16),
            (23, 25), (25, 27),
            (24, 26), (26, 28),
        ]

        return {
            'landmarks': landmarks,
            'connections': connections,
            'width': frame_width,
            'height': frame_height
        }

    def _draw_annotations(self, frame: np.ndarray, pose_landmarks, shot_data) -> np.ndarray:
        """Draw skeleton and shot info onto frame for annotated recording."""
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        if pose_landmarks is not None:
            transform = self.frame_analyzer._last_transform
            if transform:
                court_w = transform['court_w']
                court_h = transform['court_h']
                ox = transform['x1']
                oy = transform['y1']
            else:
                court_w, court_h = w, h
                ox, oy = 0, 0

            landmarks = pose_landmarks.landmark

            def to_px(lm):
                if lm.visibility < 0.5:
                    return None
                return (int(lm.x * court_w + ox), int(lm.y * court_h + oy))

            connections = [
                (11, 12), (11, 23), (12, 24), (23, 24),
                (11, 13), (13, 15),
                (12, 14), (14, 16),
                (23, 25), (25, 27),
                (24, 26), (26, 28),
            ]

            if shot_data and shot_data.shot_type in self.frame_analyzer.ACTUAL_SHOTS:
                color = (0, 255, 0)
            else:
                color = (0, 255, 255)

            for i, j in connections:
                p1 = to_px(landmarks[i])
                p2 = to_px(landmarks[j])
                if p1 and p2:
                    cv2.line(annotated, p1, p2, (255, 0, 0), 2)

            for lm in landmarks:
                pt = to_px(lm)
                if pt:
                    cv2.circle(annotated, pt, 3, color, -1)

        if shot_data and shot_data.shot_type in self.frame_analyzer.ACTUAL_SHOTS:
            label = f"{shot_data.shot_type.replace('_', ' ').upper()} ({shot_data.confidence:.0%})"
            cv2.putText(annotated, label, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        stats_text = f"Shots: {self.stats.total_shots}  Rally: {self.stats.current_rally}"
        cv2.putText(annotated, stats_text, (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        return annotated

    def _empty_result(self) -> Dict:
        """Return empty result for failed frame processing."""
        return {
            'shot': None,
            'position': None,
            'pose': None,
            'shuttle': None,
            'stats': self._get_stats_dict()
        }

    def start_recording(self):
        """Start recording frames."""
        self.is_recording = True
        self.recorded_frames = []
        logger.info(f"Session {self.session_id}: Recording started")

    def stop_recording(self) -> List[bytes]:
        """Stop recording and return recorded frames."""
        self.is_recording = False
        frames = self.recorded_frames
        self.recorded_frames = []
        logger.info(f"Session {self.session_id}: Recording stopped ({len(frames)} frames)")
        return frames

    def get_final_report(self) -> Dict:
        """Generate final report when stream ends."""
        if self.current_rally_shots:
            self._end_current_rally()

        if not self.shot_history:
            return {
                'message': 'No shots detected',
                'frames_processed': self.stats.frames_processed,
                'player_detected_frames': self.stats.player_detected_frames,
                'has_post_analysis_data': self.enable_post_analysis and len(self.raw_frame_data) > 0,
            }

        avg_confidence = (
            sum(s.confidence for s in self.shot_history) / len(self.shot_history)
            if self.shot_history else 0
        )

        shot_timeline = [
            {
                'time': s.timestamp,
                'shot': s.shot_type,
                'confidence': s.confidence
            }
            for s in self.shot_history
        ]

        return {
            'summary': {
                'total_shots': self.stats.total_shots,
                'total_rallies': self.rally_id_counter,
                'frames_processed': self.stats.frames_processed,
                'player_detection_rate': (
                    self.stats.player_detected_frames / self.stats.frames_processed
                    if self.stats.frames_processed > 0 else 0
                ),
                'avg_confidence': avg_confidence,
                'session_duration': (datetime.now() - self._start_time).total_seconds(),
                'foot_positions_recorded': len(self.foot_positions)
            },
            'shot_distribution': dict(self.stats.shot_distribution),
            'shot_timeline': shot_timeline,
            'court_settings': self.court.to_dict(),
            'heatmap_data': self.foot_positions,
            'has_post_analysis_data': self.enable_post_analysis and len(self.raw_frame_data) > 0,
        }

    def get_heatmap_data(self) -> List[Tuple[int, int]]:
        """Get foot positions for heatmap generation."""
        return [(p['x'], p['y']) for p in self.foot_positions]

    def reset(self):
        """Reset analyzer for new session."""
        self.frame_analyzer.reset()
        self.stats = StreamStats()
        self.shot_history = []
        self.foot_positions = []
        self.current_rally_shots = []
        self.rally_id_counter = 0
        self.frames_since_last_shot = 0
        self._frame_counter = 0
        self._start_time = datetime.now()
        self.raw_frame_data = []
        self.serialized_landmarks = []

    def update_thresholds(
        self,
        velocity_thresholds: Optional[Dict[str, float]] = None,
        position_thresholds: Optional[Dict[str, float]] = None,
        shot_cooldown_seconds: Optional[float] = None
    ):
        if velocity_thresholds:
            self._velocity_thresholds = velocity_thresholds
            self.frame_analyzer.VELOCITY_THRESHOLDS.update(velocity_thresholds)
            logger.info(f"Session {self.session_id}: Updated velocity thresholds")

        if position_thresholds:
            self._position_thresholds = position_thresholds
            self.frame_analyzer.POSITION_THRESHOLDS.update(position_thresholds)
            logger.info(f"Session {self.session_id}: Updated position thresholds")

        if shot_cooldown_seconds is not None:
            self._shot_cooldown_seconds = shot_cooldown_seconds
            self.frame_analyzer.shot_cooldown_seconds = shot_cooldown_seconds
            logger.info(f"Session {self.session_id}: Updated cooldown to {shot_cooldown_seconds}s")

    def get_current_thresholds(self) -> Dict:
        """Get current threshold settings."""
        return {
            'velocity_thresholds': self.frame_analyzer.get_velocity_thresholds(),
            'position_thresholds': self.frame_analyzer.get_position_thresholds(),
            'shot_cooldown_seconds': self.frame_analyzer.get_cooldown_seconds()
        }

    def release_raw_video_writer(self):
        """Release the raw video writer (call before post-analysis)."""
        if self._raw_video_writer:
            self._raw_video_writer.release()
            self._raw_video_writer = None

    def close(self):
        """Release resources."""
        self.release_raw_video_writer()
        self.frame_analyzer.close()


# ---------------------------------------------------------------------------
# Advanced mode: continuous background processing
# ---------------------------------------------------------------------------

class FrameStore:
    """
    Append-only JPEG frame store backed by a single binary file.

    Main thread appends JPEG bytes (fast disk write).
    Background thread reads frames by index (seek + read, no locking needed
    because written data is immutable once written).

    File format: [4-byte length][jpeg_bytes][4-byte length][jpeg_bytes]...
    """

    def __init__(self, path: str):
        self._path = path
        self._write_file = open(path, 'wb')
        self._index: List[Tuple[int, int]] = []  # (offset, length)
        self._lock = threading.Lock()

    def append(self, jpeg_bytes: bytes):
        """Append a JPEG frame. Called from main thread."""
        length = len(jpeg_bytes)
        with self._lock:
            offset = self._write_file.tell()
            self._write_file.write(length.to_bytes(4, 'big'))
            self._write_file.write(jpeg_bytes)
            self._write_file.flush()
            self._index.append((offset + 4, length))

    def read_frame(self, index: int) -> np.ndarray:
        """Read and decode a frame by index. Called from background thread."""
        with self._lock:
            if index >= len(self._index):
                return None
            offset, length = self._index[index]
        # Read without lock — data at this offset is immutable
        with open(self._path, 'rb') as f:
            f.seek(offset)
            jpeg_bytes = f.read(length)
        return cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)

    def count(self) -> int:
        with self._lock:
            return len(self._index)

    def close(self):
        if self._write_file:
            self._write_file.close()
            self._write_file = None



class BackgroundProcessor(threading.Thread):
    """
    Daemon thread that continuously processes frames from a FrameStore.

    Reads frames one at a time, runs pose + shuttle detection, appends
    to raw_frame_data.  Every ``classify_interval`` processed frames it
    runs classify_all on ALL accumulated data and stores the result so
    the WebSocket layer can push it to the frontend.
    """

    def __init__(
        self,
        frame_store: FrameStore,
        court_boundary: dict,
        frame_rate: float,
        velocity_thresholds: Optional[Dict[str, float]] = None,
        position_thresholds: Optional[Dict[str, float]] = None,
        shot_cooldown_seconds: float = 0.4,
        enable_tuning_data: bool = False,
        classify_interval: int = 300,  # frames (~10s at 30fps)
    ):
        super().__init__(daemon=True)
        self._frame_store = frame_store
        self._court_boundary = court_boundary
        self._frame_rate = frame_rate
        self._velocity_thresholds = velocity_thresholds
        self._position_thresholds = position_thresholds
        self._shot_cooldown_seconds = shot_cooldown_seconds
        self._enable_tuning_data = enable_tuning_data
        self._classify_interval = classify_interval

        self._stop_event = threading.Event()
        self._drain_event = threading.Event()  # set when we should drain remaining frames
        self._done_event = threading.Event()   # set when processing is complete

        # Persistent analyzers (created lazily in run())
        self._frame_analyzer = None
        self._shuttle_tracker = None
        self._shuttle_buffer: List[np.ndarray] = []

        # Shared state (read by main thread)
        self._lock = threading.Lock()
        self.processed_count = 0
        self.raw_frame_data: List[dict] = []
        self.serialized_landmarks: List = []
        self._latest_results: Optional[dict] = None
        self._results_version = 0  # incremented on each classify

        # Timing instrumentation
        self._timing_shuttle_total = 0.0
        self._timing_pose_total = 0.0
        self._timing_build_total = 0.0
        self._timing_classify_total = 0.0
        self._timing_log_interval = 100  # log every N frames

    def _ensure_analyzers(self):
        """Lazy-init frame analyzer and shuttle tracker."""
        if self._frame_analyzer is None:
            from .frame_analyzer import FrameAnalyzer, CourtBoundary
            court = CourtBoundary.from_dict(self._court_boundary)
            use_static = self._frame_rate <= 15
            self._frame_analyzer = FrameAnalyzer(
                court_boundary=court,
                processing_width=640,
                model_complexity=1,
                min_detection_confidence=0.3,
                min_tracking_confidence=0.3,
                effective_fps=self._frame_rate,
                velocity_thresholds=self._velocity_thresholds,
                position_thresholds=self._position_thresholds,
                shot_cooldown_seconds=self._shot_cooldown_seconds,
                static_image_mode=use_static,
            )

        if self._shuttle_tracker is None:
            try:
                from .shuttle_service import ShuttleService
                if ShuttleService.is_available():
                    self._shuttle_tracker = ShuttleService.create_tracker()
            except Exception as e:
                logger.warning(f"BackgroundProcessor: shuttle tracker init failed: {e}")

    def run(self):
        """Main processing loop — runs in daemon thread."""
        import time
        self._ensure_analyzers()
        frames_since_classify = 0

        while not self._stop_event.is_set():
            available = self._frame_store.count()
            if self.processed_count >= available:
                if self._drain_event.is_set():
                    # No more frames coming, we're done
                    break
                time.sleep(0.01)
                continue

            # Read and process one frame
            frame = self._frame_store.read_frame(self.processed_count)
            if frame is None:
                time.sleep(0.01)
                continue

            frame_number = self.processed_count + 1  # 1-indexed
            timestamp = frame_number / self._frame_rate

            try:
                self._process_one_frame(frame, frame_number, timestamp)
            except Exception as e:
                logger.error(f"BackgroundProcessor: frame {frame_number} error: {e}")

            with self._lock:
                self.processed_count += 1

            frames_since_classify += 1
            if frames_since_classify >= self._classify_interval:
                self._run_classification()
                frames_since_classify = 0

        # Final classification after draining
        if self.processed_count > 0:
            self._run_classification()

        if self._frame_analyzer:
            self._frame_analyzer.close()

        self._done_event.set()

    def _process_one_frame(self, frame: np.ndarray, frame_number: int, timestamp: float):
        """Run pose + shuttle detection on a single frame."""
        import time as _time

        # Shuttle tracking
        t0 = _time.monotonic()
        shuttle_result = None
        if self._shuttle_tracker is not None:
            self._shuttle_buffer.append(frame)
            if len(self._shuttle_buffer) > 3:
                self._shuttle_buffer.pop(0)
            if len(self._shuttle_buffer) >= 3:
                try:
                    visible, x, y, conf = self._shuttle_tracker.detect_in_frame(self._shuttle_buffer)
                    shuttle_result = {
                        'visible': visible,
                        'x': int(x), 'y': int(y),
                        'confidence': float(conf),
                    }
                except Exception:
                    pass
        t1 = _time.monotonic()
        self._timing_shuttle_total += (t1 - t0)

        # Pose detection
        result = self._frame_analyzer.analyze_frame(
            frame=frame,
            frame_number=frame_number,
            timestamp=timestamp,
            shot_count=0,
        )
        t2 = _time.monotonic()
        self._timing_pose_total += (t2 - t1)

        # Build raw_frame_data entry
        pose_state = None
        if result.player_detected and self._frame_analyzer.pose_history:
            last = self._frame_analyzer.pose_history[-1]
            pose_state = {
                'wrist': last.get('wrist'),
                'elbow': last.get('elbow'),
                'shoulder': last.get('shoulder'),
                'shoulder_center': last.get('shoulder_center'),
                'hip_center': last.get('hip_center'),
                'timestamp': timestamp,
            }

        court_transform = None
        transform = self._frame_analyzer._last_transform
        if transform:
            court_transform = {
                'x1': transform['x1'], 'y1': transform['y1'],
                'court_w': transform['court_w'], 'court_h': transform['court_h'],
            }

        player_bbox = None
        if result.shot_data and result.shot_data.player_bbox:
            player_bbox = list(result.shot_data.player_bbox)

        entry = {
            'frame_number': frame_number,
            'timestamp': timestamp,
            'player_detected': result.player_detected,
            'pose_state': pose_state,
            'shuttle': shuttle_result,
            'court_transform': court_transform,
            'player_bbox': player_bbox,
            'foot_position': list(result.foot_position) if result.foot_position else None,
        }
        self.raw_frame_data.append(entry)

        # Serialize landmarks if tuning enabled
        if self._enable_tuning_data and result.pose_landmarks:
            lm_list = []
            for lm in result.pose_landmarks.landmark:
                lm_list.append({
                    'x': lm.x, 'y': lm.y, 'z': lm.z,
                    'visibility': lm.visibility,
                })
            self.serialized_landmarks.append(lm_list)
        elif self._enable_tuning_data:
            self.serialized_landmarks.append(None)

        t3 = _time.monotonic()
        self._timing_build_total += (t3 - t2)

        # Periodic timing log
        if frame_number % self._timing_log_interval == 0:
            n = frame_number
            avg_shuttle = self._timing_shuttle_total / n * 1000
            avg_pose = self._timing_pose_total / n * 1000
            avg_build = self._timing_build_total / n * 1000
            avg_total = (self._timing_shuttle_total + self._timing_pose_total + self._timing_build_total) / n * 1000
            logger.info(
                f"BackgroundProcessor timing [{n} frames]: "
                f"shuttle={avg_shuttle:.1f}ms  pose={avg_pose:.1f}ms  "
                f"build={avg_build:.1f}ms  total={avg_total:.1f}ms/frame  "
                f"classify={self._timing_classify_total:.1f}s total"
            )

    def _run_classification(self):
        """Run classify_all on all accumulated raw_frame_data."""
        import time as _time
        t0 = _time.monotonic()
        try:
            from .shot_classifier import ShotClassifier
            sc = ShotClassifier(
                velocity_thresholds=self._velocity_thresholds,
                position_thresholds=self._position_thresholds,
                shot_cooldown_seconds=self._shot_cooldown_seconds,
                effective_fps=self._frame_rate,
            )
            classified = sc.classify_all(
                self.raw_frame_data, max(1, int(self._frame_rate))
            )
        except Exception as e:
            logger.error(f"BackgroundProcessor: classification failed: {e}", exc_info=True)
            classified = {}
        elapsed = _time.monotonic() - t0
        self._timing_classify_total += elapsed

        with self._lock:
            self._latest_results = classified
            self._results_version += 1

        summary = classified.get("summary", {})
        logger.info(
            f"BackgroundProcessor: classified {self.processed_count} frames in {elapsed:.2f}s — "
            f"shots={summary.get('total_shots', 0)}, "
            f"rallies={summary.get('total_rallies', 0)}"
        )

    def get_latest_results(self) -> Optional[dict]:
        """Thread-safe read of latest classification results."""
        with self._lock:
            return self._latest_results

    def get_results_version(self) -> int:
        with self._lock:
            return self._results_version

    def request_drain(self):
        """Signal that no more frames will be added — process remaining and stop."""
        self._drain_event.set()

    def wait_until_done(self, timeout: float = 600):
        """Block until all frames are processed."""
        self._done_event.wait(timeout=timeout)

    def stop(self):
        """Hard stop."""
        self._stop_event.set()


class AdvancedStreamAnalyzer:
    """
    Advanced stream analyzer: FrameStore + BackgroundProcessor.

    - process_frame(): appends JPEG to FrameStore (~0.1ms), returns buffer status
    - BackgroundProcessor daemon thread reads frames, runs pose + shuttle + classify
    - finalize(): drains processor, writes annotated video
    """

    ACTUAL_SHOTS = ['smash', 'clear', 'drop_shot', 'net_shot', 'drive', 'lift']
    SKELETON_CONNECTIONS = BasicStreamAnalyzer.SKELETON_CONNECTIONS
    HIT_TRAIL_COLORS = BasicStreamAnalyzer.HIT_TRAIL_COLORS

    def __init__(
        self,
        court_boundary: dict,
        session_id: int = 0,
        frame_rate: float = 30.0,
        velocity_thresholds: Optional[Dict[str, float]] = None,
        position_thresholds: Optional[Dict[str, float]] = None,
        shot_cooldown_seconds: float = 0.4,
        enable_tuning_data: bool = False,
        output_dir: Optional[str] = None,
        chunk_duration_seconds: float = 60.0,
    ):
        self.session_id = session_id
        self.frame_rate = frame_rate
        self.enable_tuning_data = enable_tuning_data
        self._court_boundary_dict = court_boundary
        self._velocity_thresholds = velocity_thresholds
        self._position_thresholds = position_thresholds
        self._shot_cooldown_seconds = shot_cooldown_seconds
        self._output_dir = output_dir
        self.mode = 'advanced'

        # Frame dimensions (set on first frame)
        self._frame_counter = 0
        self._frame_width = 0
        self._frame_height = 0

        # Build storage dir
        if output_dir:
            raw_dir = Path(output_dir) / "stream_raw" / str(session_id)
        else:
            raw_dir = Path(tempfile.gettempdir()) / "badminton_streams" / str(session_id)
        raw_dir.mkdir(parents=True, exist_ok=True)

        self.raw_video_path = str(raw_dir / "raw_stream.mp4")
        self._raw_video_writer: Optional[cv2.VideoWriter] = None

        # FrameStore: append-only JPEG file
        self._frame_store = FrameStore(str(raw_dir / "frames.bin"))

        # Classify interval: ~10 seconds worth of frames
        classify_interval = max(30, int(10 * frame_rate))

        # BackgroundProcessor: daemon thread
        self._processor = BackgroundProcessor(
            frame_store=self._frame_store,
            court_boundary=court_boundary,
            frame_rate=frame_rate,
            velocity_thresholds=velocity_thresholds,
            position_thresholds=position_thresholds,
            shot_cooldown_seconds=shot_cooldown_seconds,
            enable_tuning_data=enable_tuning_data,
            classify_interval=classify_interval,
        )
        self._processor.start()

        # For annotation pass
        from .frame_analyzer import CourtBoundary
        self.court = CourtBoundary.from_dict(court_boundary)

        self._start_time = datetime.now()
        self._last_results_version = 0

        logger.info(
            f"AdvancedStreamAnalyzer initialized for session {session_id} "
            f"(classify every {classify_interval} frames)"
        )

    def process_frame(self, frame_data: bytes, timestamp: float) -> Dict:
        """
        Append JPEG bytes to FrameStore. Near-instant (~0.1ms).
        Returns buffer/processing status for the frontend.
        """
        self._frame_counter += 1

        # Store the raw JPEG bytes directly (no decode needed here)
        self._frame_store.append(frame_data)

        # Lazily open video writer for the final raw video (decode once)
        if self._raw_video_writer is None or self._frame_width == 0:
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is not None:
                h, w = frame.shape[:2]
                self._frame_width = w
                self._frame_height = h
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                fps = max(1, int(self.frame_rate))
                self._raw_video_writer = cv2.VideoWriter(
                    self.raw_video_path, fourcc, fps, (w, h)
                )
                self._raw_video_writer.write(frame)
        else:
            # Decode and write to raw video for annotation pass
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is not None and self._raw_video_writer:
                self._raw_video_writer.write(frame)

        return self._build_status()

    def _build_status(self) -> Dict:
        """Build status dict for WebSocket response."""
        processed = self._processor.processed_count
        return {
            'mode': 'advanced',
            'frames_buffered': self._frame_counter,
            'seconds_buffered': round(self._frame_counter / self.frame_rate, 1),
            'frames_processed': processed,
            'seconds_processed': round(processed / self.frame_rate, 1),
            'is_processing': processed < self._frame_counter,
        }

    def has_new_results(self) -> bool:
        """Check if BackgroundProcessor has new classification results."""
        v = self._processor.get_results_version()
        if v > self._last_results_version:
            self._last_results_version = v
            return True
        return False

    def get_accumulated_results(self) -> dict:
        """Get latest classification results from processor."""
        classified = self._processor.get_latest_results()
        if not classified:
            return {
                'shots': [], 'rallies': [],
                'shot_distribution': {}, 'shuttle_hits': [],
                'summary': {},
            }
        return {
            'shots': classified.get('shots', []),
            'rallies': classified.get('rallies', []),
            'shot_distribution': classified.get('shot_distribution', {}),
            'shuttle_hits': classified.get('shuttle_hits', []),
            'summary': classified.get('summary', {}),
        }

    def finalize(self, output_dir: str, progress_callback=None) -> dict:
        """
        Finalize: drain processor, final classify, write annotated video.
        """
        import time as _time
        finalize_start = _time.monotonic()

        # 1. Close raw video writer
        if self._raw_video_writer:
            self._raw_video_writer.release()
            self._raw_video_writer = None

        if progress_callback:
            progress_callback(5, "Waiting for background processing to complete")

        # 2. Signal processor to drain and wait
        t0 = _time.monotonic()
        self._processor.request_drain()
        self._processor.wait_until_done(timeout=600)

        # Close frame store (no more writes)
        self._frame_store.close()
        drain_time = _time.monotonic() - t0
        logger.info(f"Session {self.session_id} finalize: drain took {drain_time:.2f}s "
                     f"({self._processor.processed_count} frames)")

        # Log per-frame timing summary from processor
        proc = self._processor
        n = proc.processed_count or 1
        logger.info(
            f"Session {self.session_id} per-frame averages: "
            f"shuttle={proc._timing_shuttle_total/n*1000:.1f}ms  "
            f"pose={proc._timing_pose_total/n*1000:.1f}ms  "
            f"build={proc._timing_build_total/n*1000:.1f}ms  "
            f"total={( proc._timing_shuttle_total+proc._timing_pose_total+proc._timing_build_total)/n*1000:.1f}ms/frame  "
            f"classify={proc._timing_classify_total:.2f}s total"
        )

        if progress_callback:
            progress_callback(30, "Running final classification")

        # 3. Final classify_all
        t0 = _time.monotonic()
        fps = max(1, int(self.frame_rate))
        raw_frame_data = self._processor.raw_frame_data
        try:
            from .shot_classifier import ShotClassifier
            sc = ShotClassifier(
                velocity_thresholds=self._velocity_thresholds,
                position_thresholds=self._position_thresholds,
                shot_cooldown_seconds=self._shot_cooldown_seconds or 0.4,
                effective_fps=self.frame_rate,
            )
            classified = sc.classify_all(raw_frame_data, fps)
        except Exception as e:
            logger.error(f"Session {self.session_id}: Final classification failed: {e}", exc_info=True)
            classified = {}
        classify_time = _time.monotonic() - t0
        logger.info(f"Session {self.session_id} finalize: final classify took {classify_time:.2f}s")

        if progress_callback:
            progress_callback(50, "Writing annotated video")

        # 4. Annotated video
        t0 = _time.monotonic()
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        annotated_path = str(out_dir / "annotated_stream.mp4")

        if self.raw_video_path and Path(self.raw_video_path).exists():
            try:
                self._write_annotated_video(
                    self.raw_video_path, annotated_path,
                    raw_frame_data, classified,
                    fps, self._frame_width, self._frame_height
                )
            except Exception as e:
                logger.error(f"Session {self.session_id}: Annotated video failed: {e}", exc_info=True)
                annotated_path = None
        else:
            annotated_path = None
        annotate_time = _time.monotonic() - t0
        logger.info(f"Session {self.session_id} finalize: annotated video took {annotate_time:.2f}s")

        if progress_callback:
            progress_callback(80, "Extracting tuning data")

        # 5. Tuning data
        t0 = _time.monotonic()
        frame_data_path = None
        if self.enable_tuning_data and classified:
            try:
                tuning = self._extract_tuning_data(raw_frame_data, classified)
                frame_data_path = str(out_dir / "frame_data.json")
                with open(frame_data_path, 'w') as f:
                    json.dump(tuning, f)
            except Exception as e:
                logger.error(f"Session {self.session_id}: Tuning data failed: {e}", exc_info=True)
        tuning_time = _time.monotonic() - t0

        total_time = _time.monotonic() - finalize_start
        logger.info(
            f"Session {self.session_id} finalize complete in {total_time:.2f}s: "
            f"drain={drain_time:.2f}s  classify={classify_time:.2f}s  "
            f"annotate={annotate_time:.2f}s  tuning={tuning_time:.2f}s"
        )

        if progress_callback:
            progress_callback(100, "Finalization complete")

        # Extract foot positions from raw_frame_data for heatmaps
        # Build rally time ranges for rally_id assignment
        rallies = classified.get("rallies", [])
        rally_ranges = []
        for r in rallies:
            rally_ranges.append((r.get("start_time", 0), r.get("end_time", 0), r.get("rally_id", 0)))

        foot_positions = []
        for fd in raw_frame_data:
            fp = fd.get("foot_position")
            if fp and len(fp) >= 2:
                ts = fd.get("timestamp", 0)
                # Find which rally this frame belongs to
                rid = -1
                for r_start, r_end, r_id in rally_ranges:
                    if r_start <= ts <= r_end:
                        rid = r_id
                        break
                foot_positions.append({
                    "x": int(fp[0]), "y": int(fp[1]),
                    "timestamp": ts,
                    "frame": fd.get("frame_number", 0),
                    "rally_id": rid,
                })

        summary = classified.get("summary", {})
        return {
            "annotated_video_path": annotated_path,
            "raw_video_path": self.raw_video_path,
            "frame_data_path": frame_data_path,
            "summary": summary,
            "shot_distribution": classified.get("shot_distribution", {}),
            "total_shots": summary.get("total_shots", 0),
            "total_rallies": summary.get("total_rallies", 0),
            "shuttle_hits": summary.get("shuttle_hits_detected", 0),
            "shot_timeline": classified.get("shot_timeline", []),
            "rallies": classified.get("rallies", []),
            "shuttle_hits_detail": classified.get("shuttle_hits", []),
            "foot_positions": foot_positions,
        }

    # -- Annotated video (reuses BasicStreamAnalyzer pattern) ---------------

    def _write_annotated_video(
        self, video_path: str, output_path: str,
        raw_frame_data: List[dict], classified: dict,
        fps: int, width: int, height: int
    ):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        shot_by_frame = {s["frame"]: s for s in classified.get("shots", [])}
        hit_by_frame = {h["frame"]: h for h in classified.get("shuttle_hits", [])}

        current_shot_display = None
        shot_display_frames = 0
        max_display_frames = fps
        trajectory_window = int(fps * 2)
        shuttle_trail = deque(maxlen=trajectory_window)
        max_jump = math.hypot(width, height) * 0.2
        last_trail_frame = None
        hit_color_idx = 0

        serialized_landmarks = self._processor.serialized_landmarks

        frame_number = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                fd = raw_frame_data[frame_number] if frame_number < len(raw_frame_data) else {}

                # Court boundary
                polygon = self.court.get_polygon()
                overlay = frame.copy()
                cv2.fillPoly(overlay, [polygon], (0, 100, 0))
                cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
                cv2.polylines(frame, [polygon], True, (0, 255, 255), 2)

                # Skeleton
                landmarks = None
                if self.enable_tuning_data and frame_number < len(serialized_landmarks):
                    landmarks = serialized_landmarks[frame_number]
                ct = fd.get("court_transform")
                if landmarks and ct:
                    pose_color = (128, 128, 128)
                    if frame_number in shot_by_frame:
                        current_shot_display = shot_by_frame[frame_number]
                        shot_display_frames = 0
                        pose_color = (0, 255, 0)
                    elif current_shot_display and shot_display_frames < max_display_frames:
                        pose_color = (0, 255, 0)
                    self._draw_serialized_skeleton(frame, landmarks, ct, pose_color)

                # Shuttle trail
                shuttle_data = fd.get("shuttle")
                if shuttle_data and shuttle_data.get("visible"):
                    sx, sy = shuttle_data["x"], shuttle_data["y"]
                    if shuttle_trail and last_trail_frame is not None:
                        gap = max(1, frame_number - last_trail_frame)
                        if math.hypot(sx - shuttle_trail[-1][0], sy - shuttle_trail[-1][1]) > max_jump * gap:
                            shuttle_trail.clear()
                    if frame_number in hit_by_frame:
                        hit_color_idx += 1
                    shuttle_trail.append((sx, sy, hit_color_idx, None))
                    last_trail_frame = frame_number
                    cv2.circle(frame, (sx, sy), 4, (0, 255, 255), -1)
                    cv2.line(frame, (sx - 12, sy), (sx + 12, sy), (0, 255, 255), 1)
                    cv2.line(frame, (sx, sy - 12), (sx, sy + 12), (0, 255, 255), 1)

                if len(shuttle_trail) >= 2:
                    points = list(shuttle_trail)
                    for i in range(1, len(points)):
                        x1, y1 = points[i - 1][0], points[i - 1][1]
                        x2, y2 = points[i][0], points[i][1]
                        alpha = 0.3 + 0.7 * (i / len(points))
                        cidx = points[i][2]
                        base_color = self.HIT_TRAIL_COLORS[cidx % len(self.HIT_TRAIL_COLORS)]
                        color = tuple(int(c * alpha) for c in base_color)
                        cv2.line(frame, (x1, y1), (x2, y2), color, max(1, int(2 * alpha)))

                # Shot label
                if frame_number in shot_by_frame:
                    current_shot_display = shot_by_frame[frame_number]
                    shot_display_frames = 0
                if current_shot_display and shot_display_frames < max_display_frames:
                    shot_text = f"{current_shot_display['shot_type'].upper()} ({current_shot_display['confidence']:.0%})"
                    ts = cv2.getTextSize(shot_text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
                    cv2.rectangle(frame, (5, 10), (15 + ts[0], 50), (0, 0, 0), -1)
                    shot_colors = {
                        'smash': (0, 0, 255), 'clear': (0, 255, 0),
                        'drop_shot': (255, 165, 0), 'net_shot': (255, 255, 0),
                        'drive': (255, 0, 255), 'lift': (255, 200, 100),
                    }
                    cv2.putText(frame, shot_text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                                shot_colors.get(current_shot_display["shot_type"], (255, 255, 255)), 2)
                    shot_display_frames += 1

                # Hit marker
                if frame_number in hit_by_frame:
                    hit = hit_by_frame[frame_number]
                    hx, hy = hit["hit_position"]["x"], hit["hit_position"]["y"]
                    cv2.circle(frame, (hx, hy), 15, (0, 0, 255), 3)
                    cv2.putText(frame, "HIT", (hx + 18, hy - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                # Stats panel
                summary = classified.get("summary", {})
                dist = classified.get("shot_distribution", {})
                px, py = 10, height - 140
                pw, ph = 280, 130
                ov = frame.copy()
                cv2.rectangle(ov, (px, py), (px + pw, py + ph), (0, 0, 0), -1)
                cv2.addWeighted(ov, 0.7, frame, 0.3, 0, frame)
                cv2.rectangle(frame, (px, py), (px + pw, py + ph), (255, 255, 255), 1)
                cv2.putText(frame, "SESSION STATS", (px + 10, py + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                y_off = py + 50
                for txt in [
                    f"Shots: {summary.get('total_shots', 0)} | Rallies: {summary.get('total_rallies', 0)}",
                    f"Smash: {dist.get('smash', 0)} | Clear: {dist.get('clear', 0)}",
                    f"Drop: {dist.get('drop_shot', 0)} | Drive: {dist.get('drive', 0)}",
                    f"Net: {dist.get('net_shot', 0)} | Lift: {dist.get('lift', 0)}",
                ]:
                    cv2.putText(frame, txt, (px + 10, y_off),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
                    y_off += 18

                bbox = fd.get("player_bbox")
                if bbox and landmarks:
                    bx1, by1, bx2, by2 = bbox
                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 255, 0), 2)

                out.write(frame)
                frame_number += 1
        finally:
            cap.release()
            out.release()

        logger.info(f"Annotated video written: {output_path} ({frame_number} frames)")

    def _draw_serialized_skeleton(self, frame, landmarks, court_transform, pose_color):
        ct_x1, ct_y1 = court_transform.get("x1", 0), court_transform.get("y1", 0)
        ct_w, ct_h = court_transform.get("court_w", 1), court_transform.get("court_h", 1)

        def to_px(lm):
            if lm.get("visibility", 0) < 0.5:
                return None
            return (int(lm["x"] * ct_w + ct_x1), int(lm["y"] * ct_h + ct_y1))

        for i, j in self.SKELETON_CONNECTIONS:
            if i < len(landmarks) and j < len(landmarks):
                p1, p2 = to_px(landmarks[i]), to_px(landmarks[j])
                if p1 and p2:
                    cv2.line(frame, p1, p2, (255, 0, 0), 2)
        for lm in landmarks:
            pt = to_px(lm)
            if pt:
                cv2.circle(frame, pt, 3, pose_color, -1)

    # -- Tuning data extraction (reuses BasicStreamAnalyzer pattern) --------

    def _extract_tuning_data(self, raw_frame_data: List[dict], classified: dict) -> List[dict]:
        """Delegates to BasicStreamAnalyzer._extract_tuning_data logic."""
        from .frame_analyzer import FrameAnalyzer, CourtBoundary
        from .shot_classifier import ShotClassifier

        court = CourtBoundary.from_dict(self._court_boundary_dict)
        fa = FrameAnalyzer(
            court_boundary=court, processing_width=640,
            effective_fps=self.frame_rate,
            velocity_thresholds=self._velocity_thresholds,
            position_thresholds=self._position_thresholds,
        )
        V, P = fa.VELOCITY_THRESHOLDS, fa.POSITION_THRESHOLDS
        fa.close()

        sc = ShotClassifier(
            velocity_thresholds=V, position_thresholds=P,
            shot_cooldown_seconds=self._shot_cooldown_seconds or 0.4,
            effective_fps=self.frame_rate,
        )
        velocity_data = sc._compute_velocities(raw_frame_data)

        per_frame = {}
        last_shot_ts = -999.0
        for i, fd in enumerate(raw_frame_data):
            if not fd.get("player_detected") or not fd.get("pose_state"):
                continue
            vel = velocity_data[i] if i < len(velocity_data) else {}
            if not vel:
                continue
            ps = fd["pose_state"]
            swing = sc._classify_swing(
                vel["wrist_velocity"], vel["wrist_direction"],
                ps, vel.get("wrist_dy_per_sec", 0),
                vel.get("pose_history_window", []),
            )
            shot_type, confidence = sc._classify_shot(swing, vel["wrist_velocity"])
            ts = fd["timestamp"]
            cooldown_active = False
            if shot_type in sc.ACTUAL_SHOTS and confidence > 0.5:
                if ts - last_shot_ts < sc.shot_cooldown_seconds:
                    shot_type, confidence, cooldown_active = 'follow_through', 0.3, True
                else:
                    last_shot_ts = ts
            per_frame[fd["frame_number"]] = {
                "swing_type": swing, "shot_type": shot_type,
                "confidence": confidence, "cooldown_active": cooldown_active,
            }

        hit_centric = classified.get("shots", [])
        if any(s.get("shuttle_hit_matched") for s in hit_centric):
            per_frame = {
                s["frame"]: {
                    "swing_type": s.get("swing_type", "none"),
                    "shot_type": s["shot_type"],
                    "confidence": s["confidence"],
                    "cooldown_active": False,
                }
                for s in hit_centric
            }

        tuning = []
        for i, fd in enumerate(raw_frame_data):
            if not fd.get("player_detected"):
                tuning.append({"frame_number": fd["frame_number"], "timestamp": fd["timestamp"], "player_detected": False})
                continue

            ps = fd.get("pose_state") or {}
            wrist = ps.get("wrist")
            shoulder = ps.get("shoulder")
            elbow = ps.get("elbow")
            hip = ps.get("hip_center")
            wrist_x = wrist[0] if wrist else None
            wrist_y = wrist[1] if wrist else None
            shoulder_x = shoulder[0] if shoulder else None
            shoulder_y = shoulder[1] if shoulder else None
            elbow_x = elbow[0] if elbow else None
            elbow_y = elbow[1] if elbow else None
            hip_x = hip[0] if hip else None
            hip_y = hip[1] if hip else None

            arm_extension = is_overhead = is_low_position = is_arm_extended = is_wrist_between = None
            if wrist_x is not None and shoulder_x is not None:
                arm_extension = math.sqrt((wrist_x - shoulder_x)**2 + (wrist_y - shoulder_y)**2)
                is_overhead = wrist_y < shoulder_y - P['overhead_offset']
                is_arm_extended = arm_extension > P['arm_extension_min']
            if wrist_y is not None and hip_y is not None:
                is_low_position = wrist_y > hip_y - P['low_position_offset']
            if wrist_y is not None and shoulder_y is not None and hip_y is not None:
                is_wrist_between = shoulder_y < wrist_y < hip_y

            vel = velocity_data[i] if i < len(velocity_data) else {}
            cls = per_frame.get(fd["frame_number"], {})

            entry = {
                "frame_number": fd["frame_number"], "timestamp": fd["timestamp"], "player_detected": True,
                "wrist_x": wrist_x, "wrist_y": wrist_y,
                "shoulder_x": shoulder_x, "shoulder_y": shoulder_y,
                "elbow_x": elbow_x, "elbow_y": elbow_y,
                "hip_x": hip_x, "hip_y": hip_y,
                "wrist_velocity": vel.get("wrist_velocity", 0.0),
                "body_velocity": vel.get("body_velocity", 0.0),
                "wrist_direction": vel.get("wrist_direction", "none"),
                "arm_extension": arm_extension,
                "is_overhead": is_overhead, "is_low_position": is_low_position,
                "is_arm_extended": is_arm_extended,
                "is_wrist_between_shoulder_hip": is_wrist_between,
                "swing_type": cls.get("swing_type", "none"),
                "shot_type": cls.get("shot_type", "static"),
                "confidence": cls.get("confidence", 0.3),
                "cooldown_active": cls.get("cooldown_active", False),
                "is_actual_shot": cls.get("shot_type", "static") in self.ACTUAL_SHOTS,
            }

            shuttle = fd.get("shuttle")
            if shuttle:
                visible = shuttle.get("visible", False)
                entry.update({"shuttle_x": shuttle.get("x") if visible else None,
                              "shuttle_y": shuttle.get("y") if visible else None,
                              "shuttle_confidence": shuttle.get("confidence"),
                              "shuttle_visible": visible})
            ct = fd.get("court_transform")
            if ct:
                entry.update({"court_transform_x1": ct.get("x1"), "court_transform_y1": ct.get("y1"),
                              "court_transform_w": ct.get("court_w"), "court_transform_h": ct.get("court_h")})
            bbox = fd.get("player_bbox")
            if bbox:
                entry.update({"player_bbox_x1": bbox[0], "player_bbox_y1": bbox[1],
                              "player_bbox_x2": bbox[2], "player_bbox_y2": bbox[3]})
            tuning.append(entry)

        # Post-pass: shuttle velocity/direction and hit flags
        hit_frames = {h.get("frame") for h in classified.get("shuttle_hits", [])}
        prev = None
        for entry in tuning:
            if not entry.get("shuttle_visible"):
                for k in ("shuttle_speed", "shuttle_dx", "shuttle_dy", "shuttle_direction"):
                    entry.setdefault(k, None)
                entry.setdefault("shuttle_is_hit", False)
                continue
            ts, sx = entry.get("timestamp", 0), entry.get("shuttle_x")
            sdx = sdy = speed = direction = None
            if prev and sx is not None:
                dt = ts - prev.get("timestamp", 0)
                if dt > 0:
                    sdx = (sx - prev.get("shuttle_x")) / dt
                    sdy = (entry.get("shuttle_y") - prev.get("shuttle_y")) / dt
                    speed = round(math.sqrt(sdx*sdx + sdy*sdy), 1)
                    direction = ("up" if sdy < 0 else "down") if abs(sdy) > abs(sdx) else ("right" if sdx > 0 else "left")
            entry["shuttle_speed"] = speed
            entry["shuttle_dx"] = round(sdx, 1) if sdx is not None else None
            entry["shuttle_dy"] = round(sdy, 1) if sdy is not None else None
            entry["shuttle_direction"] = direction
            entry["shuttle_is_hit"] = entry.get("frame_number") in hit_frames
            if entry.get("shuttle_visible"):
                prev = entry

        return tuning

    # -- Public interface ---------------------------------------------------

    def get_final_report(self) -> Dict:
        results = self.get_accumulated_results()
        summary = results.get('summary', {})
        return {
            'summary': {
                'total_shots': summary.get('total_shots', 0),
                'total_rallies': summary.get('total_rallies', 0),
                'frames_processed': self._processor.processed_count,
                'session_duration': (datetime.now() - self._start_time).total_seconds(),
                'shuttle_hits_detected': summary.get('shuttle_hits_detected', 0),
            },
            'shot_distribution': results.get('shot_distribution', {}),
            'has_post_analysis_data': True,
        }

    def release_raw_video_writer(self):
        if self._raw_video_writer:
            self._raw_video_writer.release()
            self._raw_video_writer = None

    def close(self):
        self.release_raw_video_writer()
        self._processor.stop()
        self._frame_store.close()


class StreamSessionManager:
    """
    Manages multiple active streaming sessions.

    Thread-safe manager for concurrent streaming sessions.
    """

    def __init__(self):
        self._sessions: Dict[int, 'BasicStreamAnalyzer'] = {}

    def create_session(
        self,
        session_id: int,
        court_boundary: dict,
        frame_rate: float = 30.0,
        velocity_thresholds: Optional[Dict[str, float]] = None,
        position_thresholds: Optional[Dict[str, float]] = None,
        shot_cooldown_seconds: float = 0.4,
        enable_post_analysis: bool = True,
        enable_tuning_data: bool = False,
        enable_shuttle_tracking: bool = True,
        output_dir: Optional[str] = None,
        stream_mode: str = "basic",
        chunk_duration: int = 60,
    ) -> 'BasicStreamAnalyzer':
        """Create a new streaming session."""
        if session_id in self._sessions:
            self._sessions[session_id].close()

        if stream_mode == "advanced":
            analyzer = AdvancedStreamAnalyzer(
                court_boundary=court_boundary,
                session_id=session_id,
                frame_rate=frame_rate,
                velocity_thresholds=velocity_thresholds,
                position_thresholds=position_thresholds,
                shot_cooldown_seconds=shot_cooldown_seconds,
                enable_tuning_data=enable_tuning_data,
                output_dir=output_dir,
                chunk_duration_seconds=float(chunk_duration),
            )
            self._sessions[session_id] = analyzer
            return analyzer

        analyzer = BasicStreamAnalyzer(
            court_boundary=court_boundary,
            session_id=session_id,
            frame_rate=frame_rate,
            velocity_thresholds=velocity_thresholds,
            position_thresholds=position_thresholds,
            shot_cooldown_seconds=shot_cooldown_seconds,
            enable_post_analysis=enable_post_analysis,
            enable_tuning_data=enable_tuning_data,
            enable_shuttle_tracking=enable_shuttle_tracking,
            output_dir=output_dir,
        )
        self._sessions[session_id] = analyzer
        return analyzer

    def update_session_thresholds(
        self,
        session_id: int,
        velocity_thresholds: Optional[Dict[str, float]] = None,
        position_thresholds: Optional[Dict[str, float]] = None,
        shot_cooldown_seconds: Optional[float] = None
    ) -> bool:
        """Update thresholds for an active session."""
        analyzer = self._sessions.get(session_id)
        if analyzer:
            analyzer.update_thresholds(velocity_thresholds, position_thresholds, shot_cooldown_seconds)
            return True
        return False

    def get_session(self, session_id: int) -> Optional['BasicStreamAnalyzer']:
        """Get an existing session."""
        return self._sessions.get(session_id)

    def get_report(self, session_id: int) -> Optional[Dict]:
        """Get final report without destroying the analyzer."""
        analyzer = self._sessions.get(session_id)
        if analyzer:
            return analyzer.get_final_report()
        return None

    def end_session(self, session_id: int) -> Optional[Dict]:
        """End a session: get report but keep analyzer alive for post-analysis."""
        analyzer = self._sessions.get(session_id)
        if analyzer:
            analyzer.release_raw_video_writer()
            return analyzer.get_final_report()
        return None

    def run_post_analysis(self, session_id: int, output_dir: str, progress_callback=None) -> Optional[dict]:
        """Run post-analysis on a session's collected data."""
        analyzer = self._sessions.get(session_id)
        if not analyzer:
            return None
        if isinstance(analyzer, AdvancedStreamAnalyzer):
            return analyzer.finalize(output_dir, progress_callback)
        return analyzer.run_post_analysis(output_dir, progress_callback)

    def cleanup_session(self, session_id: int):
        """Final cleanup: close and remove the analyzer."""
        analyzer = self._sessions.pop(session_id, None)
        if analyzer:
            analyzer.close()

    def get_active_sessions(self) -> List[int]:
        """Get list of active session IDs."""
        return list(self._sessions.keys())

    def close_all(self):
        """Close all sessions."""
        for session_id in list(self._sessions.keys()):
            self.cleanup_session(session_id)


# Global session manager
_session_manager: Optional[StreamSessionManager] = None


def get_stream_session_manager() -> StreamSessionManager:
    """Get the global stream session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = StreamSessionManager()
    return _session_manager
