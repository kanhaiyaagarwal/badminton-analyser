"""
Stream Service - Real-time frame analysis for live streaming.

This service manages live streaming sessions and uses FrameAnalyzer
for real-time shot detection and movement tracking.
"""

import cv2
import numpy as np
import base64
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from collections import defaultdict
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


class StreamAnalyzer:
    """
    Real-time stream analyzer for live badminton analysis.

    Processes individual frames from a live stream and emits events
    for shot detection, position updates, and statistics.
    """

    def __init__(self, court_boundary: dict, session_id: int = 0):
        """
        Initialize stream analyzer.

        Args:
            court_boundary: Court boundary as dict (from database)
            session_id: Stream session ID for logging
        """
        self.session_id = session_id
        self.court = CourtBoundary.from_dict(court_boundary)

        # Initialize frame analyzer
        self.frame_analyzer = FrameAnalyzer(
            court_boundary=self.court,
            processing_width=640,
            model_complexity=1
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

        # Recording
        self.is_recording = False
        self.recorded_frames: List[bytes] = []

        self._frame_counter = 0
        self._start_time = datetime.now()

        logger.info(f"StreamAnalyzer initialized for session {session_id}")

    def process_frame(self, frame_data: bytes, timestamp: float) -> Dict:
        """
        Process a single frame from the stream.

        Args:
            frame_data: JPEG encoded frame data
            timestamp: Frame timestamp in seconds

        Returns:
            Dict with shot, position, and stats events
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

        # Record frame if recording is enabled
        if self.is_recording:
            self.recorded_frames.append(frame_data)

        # Analyze frame
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
            'stats': None
        }

        # Handle player detection and pose landmarks
        if result.player_detected:
            self.stats.player_detected_frames += 1

            # Extract pose landmarks for frontend visualization
            if result.pose_landmarks:
                h, w = frame.shape[:2]
                pose_data = self._extract_pose_data(result.pose_landmarks, w, h)
                if pose_data:
                    response['pose'] = pose_data
                    # Log occasionally
                    if self._frame_counter % 60 == 0:
                        logger.info(f"Session {self.session_id}: Pose extracted with {len(pose_data['landmarks'])} landmarks")

        # Handle position update
        if result.foot_position:
            response['position'] = StreamPositionEvent(
                x=result.foot_position[0],
                y=result.foot_position[1],
                timestamp=timestamp
            ).__dict__

            # Store for heatmap
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

            # Check if rally ended
            if (self.frames_since_last_shot > self.rally_gap_threshold and
                len(self.current_rally_shots) > 0):
                self._end_current_rally()

        # Include stats update
        response['stats'] = self._get_stats_dict()

        return response

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
        # Get coordinate transform from frame analyzer
        transform = self.frame_analyzer._last_transform
        if not transform:
            return None

        x1 = transform['x1']
        y1 = transform['y1']
        court_w = transform['court_w']
        court_h = transform['court_h']

        # Convert landmarks to full frame coordinates
        landmarks = []
        for i, lm in enumerate(pose_landmarks.landmark):
            # Transform from normalized cropped coords to full frame coords
            full_x = int(lm.x * court_w + x1)
            full_y = int(lm.y * court_h + y1)
            landmarks.append({
                'x': full_x,
                'y': full_y,
                'visibility': lm.visibility
            })

        # Define skeleton connections (pairs of landmark indices)
        connections = [
            # Torso
            (11, 12),  # shoulders
            (11, 23),  # left shoulder to left hip
            (12, 24),  # right shoulder to right hip
            (23, 24),  # hips
            # Left arm
            (11, 13),  # shoulder to elbow
            (13, 15),  # elbow to wrist
            # Right arm
            (12, 14),  # shoulder to elbow
            (14, 16),  # elbow to wrist
            # Left leg
            (23, 25),  # hip to knee
            (25, 27),  # knee to ankle
            # Right leg
            (24, 26),  # hip to knee
            (26, 28),  # knee to ankle
            # Face (optional - can be noisy)
            # (0, 1), (1, 2), (2, 3), (3, 7),
            # (0, 4), (4, 5), (5, 6), (6, 8),
        ]

        return {
            'landmarks': landmarks,
            'connections': connections,
            'width': frame_width,
            'height': frame_height
        }

    def _empty_result(self) -> Dict:
        """Return empty result for failed frame processing."""
        return {
            'shot': None,
            'position': None,
            'pose': None,
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
        # End any ongoing rally
        if self.current_rally_shots:
            self._end_current_rally()

        if not self.shot_history:
            return {
                'message': 'No shots detected',
                'frames_processed': self.stats.frames_processed,
                'player_detected_frames': self.stats.player_detected_frames
            }

        # Calculate average confidence
        avg_confidence = (
            sum(s.confidence for s in self.shot_history) / len(self.shot_history)
            if self.shot_history else 0
        )

        # Shot timeline
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
            'heatmap_data': self.foot_positions
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

    def close(self):
        """Release resources."""
        self.frame_analyzer.close()


class StreamSessionManager:
    """
    Manages multiple active streaming sessions.

    Thread-safe manager for concurrent streaming sessions.
    """

    def __init__(self):
        self._sessions: Dict[int, StreamAnalyzer] = {}

    def create_session(self, session_id: int, court_boundary: dict) -> StreamAnalyzer:
        """Create a new streaming session."""
        if session_id in self._sessions:
            self._sessions[session_id].close()

        analyzer = StreamAnalyzer(court_boundary, session_id)
        self._sessions[session_id] = analyzer
        return analyzer

    def get_session(self, session_id: int) -> Optional[StreamAnalyzer]:
        """Get an existing session."""
        return self._sessions.get(session_id)

    def end_session(self, session_id: int) -> Optional[Dict]:
        """End a session and return final report."""
        analyzer = self._sessions.pop(session_id, None)
        if analyzer:
            report = analyzer.get_final_report()
            analyzer.close()
            return report
        return None

    def get_active_sessions(self) -> List[int]:
        """Get list of active session IDs."""
        return list(self._sessions.keys())

    def close_all(self):
        """Close all sessions."""
        for session_id in list(self._sessions.keys()):
            self.end_session(session_id)


# Global session manager
_session_manager: Optional[StreamSessionManager] = None


def get_stream_session_manager() -> StreamSessionManager:
    """Get the global stream session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = StreamSessionManager()
    return _session_manager
