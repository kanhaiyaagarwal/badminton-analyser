"""Protocol definitions for badminton and challenge WebSocket sessions."""

import json
import logging
from typing import Any, Dict

from .client import AuthenticatedClient
from .config import ReplayConfig
from .video_reader import VideoFrameReader

logger = logging.getLogger(__name__)


class BadmintonProtocol:
    WS_PATH_TEMPLATE = "/ws/stream/{session_id}?token={token}"
    END_MESSAGE = json.dumps({"type": "end_stream"})
    END_RESPONSE_TYPE = "stream_ended"

    @staticmethod
    def make_frame_message(b64: str, timestamp: float, w: int, h: int) -> str:
        return json.dumps({
            "type": "frame",
            "data": b64,
            "timestamp": timestamp,
            "width": w,
            "height": h,
        })

    @staticmethod
    def setup_session(
        client: AuthenticatedClient,
        config: ReplayConfig,
        reader: VideoFrameReader,
    ) -> int:
        """Run REST setup sequence; return session_id."""
        session_id = client.create_stream_session()

        # Load or generate court boundary
        if config.court_boundary_file:
            with open(config.court_boundary_file) as f:
                court = json.load(f)
            # Normalize {"x":..,"y":..} dicts → [x, y] arrays if needed
            for key in ("top_left", "top_right", "bottom_left", "bottom_right"):
                pt = court.get(key)
                if isinstance(pt, dict):
                    court[key] = [pt["x"], pt["y"]]
        elif config.use_full_frame:
            court = reader.get_full_frame_court()
        else:
            raise ValueError(
                "Badminton mode requires --court-file or --full-frame"
            )

        client.setup_court(session_id, court)
        client.start_stream(session_id)
        if config.record and config.stream_mode != "advanced":
            # Advanced mode always records to raw_stream.mp4 automatically
            client.start_recording(session_id)
        return session_id

    @staticmethod
    def end_session(client: AuthenticatedClient, session_id: int) -> dict:
        """POST end-stream REST call — saves recording to disk."""
        return client.end_stream(session_id)

    @staticmethod
    def extract_stats(result: Dict[str, Any]) -> str:
        """Pull key metrics from an analysis_result for progress logging."""
        stats = result.get("stats", {})
        shots = stats.get("total_shots", "?")
        rally = stats.get("current_rally", "?")
        return f"shots={shots} rally={rally}"


class ChallengeProtocol:
    WS_PATH_TEMPLATE = "/ws/challenge/{session_id}?token={token}"
    END_MESSAGE = json.dumps({"type": "end_session"})
    END_RESPONSE_TYPE = "session_ended"

    @staticmethod
    def make_frame_message(b64: str, timestamp: float, w: int, h: int) -> str:
        return json.dumps({
            "type": "frame",
            "data": b64,
            "timestamp": timestamp,
        })

    @staticmethod
    def setup_session(
        client: AuthenticatedClient,
        config: ReplayConfig,
        reader: VideoFrameReader,
    ) -> int:
        """Create challenge session via REST; return session_id."""
        session_id = client.create_challenge_session()
        if config.record:
            client.start_challenge_recording(session_id)
        return session_id

    @staticmethod
    def end_session(client: AuthenticatedClient, session_id: int) -> dict:
        """POST end-session REST call — persists score + personal best."""
        return client.end_challenge_session(session_id)

    @staticmethod
    def extract_stats(result: Dict[str, Any]) -> str:
        """Pull key metrics from a challenge_update for progress logging."""
        reps = result.get("reps", result.get("rep_count", "?"))
        hold = result.get("hold_seconds", "?")
        detected = result.get("player_detected", False)
        ready = result.get("ready", False)
        feedback = result.get("form_feedback", "")
        ex = result.get("exercise", {})
        angle = ex.get("angle", "?")
        state = ex.get("state", ex.get("in_plank", "?"))

        parts = [f"reps={reps}"]
        if hold and hold != "?" and float(hold) > 0:
            parts.append(f"hold={hold}s")
        parts.append(f"pose={'Y' if detected else 'N'}")
        parts.append(f"ready={'Y' if ready else 'N'}")
        if angle != "?":
            parts.append(f"angle={angle}")
        if state != "?":
            parts.append(f"state={state}")
        if feedback:
            parts.append(f"fb=\"{feedback}\"")
        return " ".join(parts)


def get_protocol(feature: str):
    if feature == "badminton":
        return BadmintonProtocol
    elif feature == "challenge":
        return ChallengeProtocol
    else:
        raise ValueError(f"Unknown feature: {feature}")
