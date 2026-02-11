"""CLI entry point: python -m tools.replay"""

import argparse
import asyncio
import logging
import sys

from .config import ReplayConfig
from .client import AuthenticatedClient
from .video_reader import VideoFrameReader
from .sender import FrameSender
from .reporter import ResultReporter


def parse_args() -> ReplayConfig:
    p = argparse.ArgumentParser(
        prog="python -m tools.replay",
        description="Replay a recorded video through the livestream WebSocket pipeline.",
    )

    # Connection
    conn = p.add_argument_group("connection")
    conn.add_argument("--url", default="http://localhost:8000", help="Base API URL")
    conn.add_argument("--email", required=True, help="Login email")
    conn.add_argument("--password", required=True, help="Login password")

    # Video
    vid = p.add_argument_group("video")
    vid.add_argument("--video", required=True, help="Path to video file")
    vid.add_argument("--fps", type=int, default=10, choices=[5, 10, 15, 30], help="Target FPS")
    vid.add_argument("--jpeg-quality", type=int, default=80, help="JPEG quality 0-100")

    # Feature
    feat = p.add_argument_group("feature")
    feat.add_argument(
        "--feature", default="badminton", choices=["badminton", "challenge"],
        help="Which pipeline to test",
    )
    feat.add_argument(
        "--challenge-type", default="squat", choices=["squat", "plank", "pushup"],
        help="Challenge type (only for --feature challenge)",
    )

    # Court boundary
    court = p.add_argument_group("court (badminton only)")
    court.add_argument("--court-file", help="Path to court boundary JSON file")
    court.add_argument(
        "--full-frame", action="store_true", default=True,
        help="Use entire video frame as court boundary (default if no --court-file)",
    )

    # Badminton options
    bopt = p.add_argument_group("badminton options")
    bopt.add_argument(
        "--mode", default="basic", choices=["basic", "advanced"],
        help="Stream mode: basic (real-time) or advanced (buffered post-analysis)",
    )
    bopt.add_argument(
        "--record", action="store_true",
        help="Enable server-side recording",
    )
    bopt.add_argument(
        "--tuning", action="store_true",
        help="Enable tuning data (serialized landmarks + per-frame metrics)",
    )
    bopt.add_argument(
        "--shuttle", action="store_true",
        help="Enable shuttle tracking (requires weights/track.pt)",
    )

    # Streaming
    stream = p.add_argument_group("streaming")
    stream.add_argument("--max-frames", type=int, default=0, help="Max frames to send (0=all)")
    stream.add_argument("--start-frame", type=int, default=0, help="Frame index to start from")
    stream.add_argument(
        "--speed", type=float, default=1.0,
        help="Playback speed multiplier (0=max throughput)",
    )

    # Output
    out = p.add_argument_group("output")
    out.add_argument("--output", "-o", help="Save results JSON to this path")
    out.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = p.parse_args()

    is_advanced = args.mode == "advanced"

    return ReplayConfig(
        base_url=args.url,
        email=args.email,
        password=args.password,
        video_path=args.video,
        fps=args.fps,
        jpeg_quality=args.jpeg_quality,
        feature=args.feature,
        challenge_type=args.challenge_type,
        court_boundary_file=args.court_file,
        use_full_frame=args.full_frame,
        stream_mode=args.mode,
        record=args.record or is_advanced,  # advanced always records
        enable_tuning=args.tuning or is_advanced,  # advanced always enables tuning
        enable_shuttle=args.shuttle or is_advanced,  # advanced always enables shuttle
        max_frames=args.max_frames,
        start_frame=args.start_frame,
        playback_speed=args.speed,
        output_file=args.output,
        verbose=args.verbose,
    )


def main():
    config = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if config.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Open video
    reader = VideoFrameReader(config.video_path, config.jpeg_quality)
    print(
        f"Video: {config.video_path} "
        f"({reader.width}x{reader.height}, "
        f"{reader.native_fps:.1f}fps, "
        f"{reader.total_frames} frames)"
    )

    # Login
    client = AuthenticatedClient(config)
    client.login()

    # Send frames
    sender = FrameSender(config, client)
    asyncio.run(sender.run(reader))
    reader.close()

    # Report
    reporter = ResultReporter(sender)
    reporter.print_summary()
    if config.output_file:
        reporter.save_json(config.output_file)


if __name__ == "__main__":
    main()
