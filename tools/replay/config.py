"""Replay configuration dataclass."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ReplayConfig:
    # Connection
    base_url: str = "http://localhost:8000"
    email: str = ""
    password: str = ""

    # Video
    video_path: str = ""
    fps: int = 10
    jpeg_quality: int = 80

    # Feature
    feature: str = "badminton"  # "badminton" or "challenge"
    challenge_type: str = "squat"  # "squat", "plank", "pushup"

    # Court boundary
    court_boundary_file: Optional[str] = None
    use_full_frame: bool = True

    # Badminton options
    stream_mode: str = "basic"  # "basic" or "advanced"
    enable_tuning: bool = False
    enable_shuttle: bool = False

    # Recording (badminton only)
    record: bool = False

    # Streaming
    max_frames: int = 0  # 0 = all
    start_frame: int = 0
    playback_speed: float = 1.0  # 0 = max throughput

    # Output
    output_file: Optional[str] = None
    verbose: bool = False

    @property
    def ws_base_url(self) -> str:
        return self.base_url.replace("http://", "ws://").replace("https://", "wss://")
