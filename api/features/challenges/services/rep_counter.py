"""
Base rep-counter analyzer for fitness challenges.

Subclassed by plank, squat, and pushup analyzers which each define
their own angle logic and rep/hold detection.
"""

import cv2
import numpy as np
import logging
from abc import abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from ....core.streaming.base_analyzer import BaseStreamAnalyzer
from ....core.streaming.pose_detector import PoseDetector, SKELETON_CONNECTIONS

logger = logging.getLogger(__name__)

CHALLENGE_DEFAULTS = {
    "squat":  {"down_angle": 100, "up_angle": 160},
    "pushup": {"down_angle": 90, "up_angle": 155},
    "plank":  {"good_angle_min": 150, "good_angle_max": 195},
}


class RepCounterAnalyzer(BaseStreamAnalyzer):
    """
    Abstract rep/hold counter built on the shared PoseDetector.

    Subclasses implement `_process_pose()` to define exercise-specific
    logic (angle thresholds, state machines, etc.).
    """

    def __init__(self, challenge_type: str):
        self.challenge_type = challenge_type
        self.detector = PoseDetector(model_complexity=1)
        self.reps = 0
        self.hold_seconds = 0.0
        self.form_feedback = ""
        self._frame_counter = 0
        self._start_time = datetime.now()
        self._last_timestamp = 0.0
        self.frame_timeline: List[Dict] = []

        # Recording state
        self.is_recording = False
        self.recorded_frames: List[bytes] = []

    def process_frame(self, frame_data: bytes, timestamp: float) -> Dict:
        self._frame_counter += 1

        # Decode JPEG
        try:
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return self._empty_result()
        except Exception as e:
            logger.error(f"Frame decode error: {e}")
            return self._empty_result()

        # Detect pose
        pose_result = self.detector.detect(frame)
        pose_data = self.detector.extract_pose_data(pose_result)

        # Exercise-specific logic
        exercise_data = {}
        if pose_result.player_detected and pose_result.landmark_list:
            exercise_data = self._process_pose(pose_result.landmark_list, timestamp)
            self.frame_timeline.append({
                "t": round(timestamp, 3),
                "lm": [[round(l["nx"], 4), round(l["ny"], 4), round(l.get("visibility", 0), 2)] for l in pose_result.landmark_list],
                "angle": exercise_data.get("angle"),
                "state": exercise_data.get("state") or exercise_data.get("in_plank"),
                "fb": self.form_feedback,
                "reps": self.reps,
                "hold": round(self.hold_seconds, 1),
            })

        # Record annotated frame if recording
        if self.is_recording:
            annotated = self._draw_annotations(frame, pose_result, timestamp)
            _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
            self.recorded_frames.append(buf.tobytes())

        self._last_timestamp = timestamp

        return {
            "type": "challenge_update",
            "challenge_type": self.challenge_type,
            "reps": self.reps,
            "hold_seconds": round(self.hold_seconds, 1),
            "form_feedback": self.form_feedback,
            "pose": pose_data,
            "exercise": exercise_data,
            "frames_processed": self._frame_counter,
            "player_detected": pose_result.player_detected,
        }

    @abstractmethod
    def _process_pose(self, landmarks: list, timestamp: float) -> Dict:
        """
        Exercise-specific pose processing.

        Args:
            landmarks: List of dicts with x, y, visibility, nx, ny.
            timestamp: Current frame timestamp.

        Returns:
            Dict with exercise-specific data (angles, state, etc.).
        """

    def get_final_report(self) -> Dict:
        duration = (datetime.now() - self._start_time).total_seconds()
        return {
            "challenge_type": self.challenge_type,
            "score": self.reps if self.challenge_type != "plank" else int(self.hold_seconds),
            "reps": self.reps,
            "hold_seconds": round(self.hold_seconds, 1),
            "duration_seconds": round(duration, 1),
            "frames_processed": self._frame_counter,
            "frame_timeline": self.frame_timeline,
        }

    def reset(self):
        self.reps = 0
        self.hold_seconds = 0.0
        self.form_feedback = ""
        self._frame_counter = 0
        self._start_time = datetime.now()
        self._last_timestamp = 0.0
        self.frame_timeline = []

    def close(self):
        self.detector.close()

    def _empty_result(self) -> Dict:
        return {
            "type": "challenge_update",
            "challenge_type": self.challenge_type,
            "reps": self.reps,
            "hold_seconds": round(self.hold_seconds, 1),
            "form_feedback": self.form_feedback,
            "pose": None,
            "exercise": {},
            "frames_processed": self._frame_counter,
            "player_detected": False,
        }

    # ---------- Recording ----------

    def start_recording(self):
        self.is_recording = True
        self.recorded_frames = []
        logger.info(f"Recording started for {self.challenge_type} challenge")

    def stop_recording(self) -> List[bytes]:
        self.is_recording = False
        frames = self.recorded_frames
        self.recorded_frames = []
        logger.info(f"Recording stopped: {len(frames)} frames captured")
        return frames

    def _draw_annotations(self, frame: np.ndarray, pose_result, timestamp: float) -> np.ndarray:
        """Draw skeleton overlay and HUD onto the frame."""
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        # Draw skeleton if pose detected
        if pose_result.player_detected and pose_result.landmark_list:
            landmarks = pose_result.landmark_list
            good_form = self.form_feedback.lower().startswith("good") if self.form_feedback else False
            joint_color = (0, 200, 0) if good_form else (0, 220, 220)  # green or yellow (BGR)
            line_color = (0, 220, 220)  # yellow

            # Draw connections
            for (a, b) in SKELETON_CONNECTIONS:
                if a >= len(landmarks) or b >= len(landmarks):
                    continue
                la, lb = landmarks[a], landmarks[b]
                if la.get("visibility", 0) < 0.3 or lb.get("visibility", 0) < 0.3:
                    continue
                cv2.line(annotated, (la["x"], la["y"]), (lb["x"], lb["y"]), line_color, 2)

            # Draw joints
            for lm in landmarks:
                if lm.get("visibility", 0) < 0.3:
                    continue
                cv2.circle(annotated, (lm["x"], lm["y"]), 4, joint_color, -1)

        # HUD background strip at top
        overlay = annotated.copy()
        cv2.rectangle(overlay, (0, 0), (w, 50), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, annotated, 0.4, 0, annotated)

        # Challenge type label
        label = self.challenge_type.upper()
        cv2.putText(annotated, label, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (78, 204, 163), 2)

        # Score
        if self.challenge_type == "plank":
            score_text = f"{self.hold_seconds:.1f}s"
        else:
            score_text = f"{self.reps} reps"
        cv2.putText(annotated, score_text, (w // 2 - 40, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Elapsed time
        elapsed = timestamp
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        time_text = f"{mins}:{secs:02d}"
        cv2.putText(annotated, time_text, (w - 80, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

        # Form feedback at bottom
        if self.form_feedback:
            fb = self.form_feedback
            good = fb.lower().startswith("good")
            fb_color = (0, 200, 0) if good else (0, 100, 230)  # green or orange-red (BGR)
            text_size = cv2.getTextSize(fb, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            tx = (w - text_size[0]) // 2
            # Background pill
            cv2.rectangle(annotated, (tx - 10, h - 40), (tx + text_size[0] + 10, h - 10), (0, 0, 0), -1)
            cv2.putText(annotated, fb, (tx, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, fb_color, 2)

        return annotated
