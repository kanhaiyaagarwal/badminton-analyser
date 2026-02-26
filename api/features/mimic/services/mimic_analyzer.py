"""
MimicAnalyzer — real-time pose comparison for mimic challenges.

Extends BaseStreamAnalyzer: receives user camera frames via WebSocket,
compares against a pre-extracted reference pose timeline, and returns
similarity scores per frame.
"""

import cv2
import numpy as np
import logging
from typing import Dict, List, Optional

from ....core.streaming.base_analyzer import BaseStreamAnalyzer
from ....core.streaming.pose_detector import PoseDetector, SKELETON_CONNECTIONS
from .pose_similarity import compute_all_similarities, generate_feedback

logger = logging.getLogger(__name__)


class MimicAnalyzer(BaseStreamAnalyzer):
    """Real-time analyzer that compares user poses against a reference timeline."""

    def __init__(
        self,
        reference_timeline: List[dict],
        reference_fps: float,
        reference_duration: float,
    ):
        self.ref_timeline = reference_timeline
        self.ref_fps = reference_fps or 30.0
        self.ref_duration = reference_duration or 1.0

        self.detector = PoseDetector(
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.4,
        )

        # Session state
        self.frame_scores: List[dict] = []
        self.start_time: Optional[float] = None
        self.frames_processed = 0

    def process_frame(self, frame_data: bytes, timestamp: float) -> Dict:
        """Process a single camera frame and return similarity scores."""
        if self.start_time is None:
            self.start_time = timestamp

        elapsed = timestamp - self.start_time

        # Decode frame
        frame = cv2.imdecode(
            np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR
        )
        if frame is None:
            return {"type": "mimic_update", "error": "invalid_frame"}

        # Detect user pose
        pose_result = self.detector.detect(frame)
        self.frames_processed += 1

        # Time alignment: wrap around if session is longer than reference
        ref_time = elapsed % self.ref_duration if self.ref_duration > 0 else 0
        ref_frame_idx = self._find_closest_ref_frame(ref_time)
        ref_entry = self.ref_timeline[ref_frame_idx] if ref_frame_idx is not None else None

        # Build response
        response: Dict = {
            "type": "mimic_update",
            "player_detected": pose_result.player_detected,
            "ref_time": round(ref_time, 3),
            "elapsed": round(elapsed, 3),
        }

        # Add user pose data for frontend skeleton overlay
        if pose_result.player_detected and pose_result.landmark_list:
            response["pose"] = {
                "landmarks": pose_result.landmark_list,
                "connections": SKELETON_CONNECTIONS,
            }

        # Add reference landmarks for overlay
        if ref_entry and ref_entry.get("lm"):
            ref_lm_dicts = [
                {"nx": lm[0], "ny": lm[1], "visibility": lm[2]}
                for lm in ref_entry["lm"]
            ]
            response["ref_landmarks"] = ref_entry["lm"]
        else:
            ref_lm_dicts = None

        # Compute similarity scores
        if (
            pose_result.player_detected
            and pose_result.landmark_list
            and ref_lm_dicts
        ):
            scores = compute_all_similarities(pose_result.landmark_list, ref_lm_dicts)
            feedback = generate_feedback(pose_result.landmark_list, ref_lm_dicts)

            response["scores"] = scores
            response["feedback"] = feedback

            self.frame_scores.append({
                "t": round(elapsed, 3),
                "ref_t": round(ref_time, 3),
                **scores,
            })
        elif not pose_result.player_detected:
            response["scores"] = {
                "cosine_raw": 0, "cosine_normalized": 0, "angle_score": 0,
                "upper_body": 0, "lower_body": 0,
            }
            response["feedback"] = "Step into frame"
        else:
            response["scores"] = {
                "cosine_raw": 0, "cosine_normalized": 0, "angle_score": 0,
                "upper_body": 0, "lower_body": 0,
            }
            response["feedback"] = "Reference pose not available"

        return response

    def get_final_report(self) -> Dict:
        """Generate summary report when the session ends."""
        if not self.frame_scores:
            return {
                "overall_score": 0,
                "duration_seconds": 0,
                "frames_compared": 0,
                "score_breakdown": {},
                "frame_scores": [],
            }

        # Average scores across all methods
        n = len(self.frame_scores)
        avg = {
            "cosine_raw": round(sum(f["cosine_raw"] for f in self.frame_scores) / n, 1),
            "cosine_normalized": round(sum(f["cosine_normalized"] for f in self.frame_scores) / n, 1),
            "angle_score": round(sum(f["angle_score"] for f in self.frame_scores) / n, 1),
            "upper_body": round(sum(f["upper_body"] for f in self.frame_scores) / n, 1),
            "lower_body": round(sum(f["lower_body"] for f in self.frame_scores) / n, 1),
        }

        # Section scores (5-second chunks)
        section_scores = self._compute_section_scores(chunk_seconds=5.0)

        # Use angle_score as primary overall score
        overall = avg["angle_score"]

        duration = 0.0
        if self.frame_scores:
            duration = self.frame_scores[-1]["t"]

        return {
            "overall_score": round(overall, 1),
            "duration_seconds": round(duration, 1),
            "frames_compared": n,
            "score_breakdown": avg,
            "section_scores": section_scores,
            "frame_scores": self.frame_scores,
        }

    def _compute_section_scores(self, chunk_seconds: float = 5.0) -> List[dict]:
        """Break frame scores into time chunks and average each."""
        if not self.frame_scores:
            return []

        max_t = self.frame_scores[-1]["t"]
        sections = []
        start = 0.0

        while start < max_t:
            end = start + chunk_seconds
            chunk = [f for f in self.frame_scores if start <= f["t"] < end]
            if chunk:
                cn = len(chunk)
                sections.append({
                    "start": round(start, 1),
                    "end": round(min(end, max_t), 1),
                    "cosine_raw": round(sum(f["cosine_raw"] for f in chunk) / cn, 1),
                    "cosine_normalized": round(sum(f["cosine_normalized"] for f in chunk) / cn, 1),
                    "angle_score": round(sum(f["angle_score"] for f in chunk) / cn, 1),
                })
            start = end

        return sections

    def _find_closest_ref_frame(self, ref_time: float) -> Optional[int]:
        """Find the timeline frame closest to the given reference time."""
        if not self.ref_timeline:
            return None

        best_idx = 0
        best_diff = abs(self.ref_timeline[0].get("t", 0) - ref_time)

        for i, entry in enumerate(self.ref_timeline):
            diff = abs(entry.get("t", 0) - ref_time)
            if diff < best_diff:
                best_diff = diff
                best_idx = i
            elif diff > best_diff:
                # Timeline is sorted — once diff increases, stop
                break

        return best_idx

    def reset(self):
        """Reset state for a new session."""
        self.frame_scores = []
        self.start_time = None
        self.frames_processed = 0

    def close(self):
        """Release resources."""
        if self.detector:
            self.detector.close()
