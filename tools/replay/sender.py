"""Async WebSocket frame sender with concurrent receive."""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List

import websockets

from .config import ReplayConfig
from .protocols import get_protocol
from .client import AuthenticatedClient
from .video_reader import VideoFrameReader

logger = logging.getLogger(__name__)


class FrameSender:
    def __init__(self, config: ReplayConfig, client: AuthenticatedClient):
        self.config = config
        self.client = client
        self.protocol = get_protocol(config.feature)
        self.results: List[Dict[str, Any]] = []
        self.final_report: Dict[str, Any] = {}
        self.frames_sent = 0
        self.start_time = 0.0
        self.end_time = 0.0
        self._auto_ended = asyncio.Event()  # server signalled session over

    async def run(self, reader: VideoFrameReader):
        # REST setup
        session_id = self.protocol.setup_session(self.client, self.config, reader)

        # Build WS URL
        ws_url = (
            self.config.ws_base_url
            + self.protocol.WS_PATH_TEMPLATE.format(
                session_id=session_id, token=self.client.token
            )
        )
        logger.info(f"Connecting to {ws_url}")

        async with websockets.connect(ws_url) as ws:
            # Start receive loop in background
            receive_done = asyncio.Event()
            recv_task = asyncio.create_task(self._receive_loop(ws, receive_done))

            # Send frames
            self.start_time = time.monotonic()
            frame_gen = reader.frames(
                self.config.fps,
                max_frames=self.config.max_frames,
                start_frame=self.config.start_frame,
            )

            for b64, ts, w, h, idx in frame_gen:
                # Stop sending if server signalled auto-end (collapse, time limit, etc.)
                if self._auto_ended.is_set():
                    last = self.results[-1] if self.results else {}
                    reason = last.get("end_reason", "auto_end")
                    logger.info(f"Server auto-ended session: {reason} — stopping send loop")
                    break

                msg = self.protocol.make_frame_message(b64, ts, w, h)
                await ws.send(msg)
                self.frames_sent += 1

                log_interval = 10 if self.config.feature == "challenge" else 30
                if self.config.verbose and self.frames_sent % log_interval == 0:
                    pct = (
                        f"{idx / reader.total_frames * 100:.0f}%"
                        if reader.total_frames > 0
                        else "?"
                    )
                    stats = (
                        self.protocol.extract_stats(self.results[-1])
                        if self.results
                        else ""
                    )
                    logger.info(
                        f"  frame {self.frames_sent} (idx={idx}, {pct}) {stats}"
                    )

                # Rate limiting
                if self.config.playback_speed > 0:
                    delay = 1.0 / self.config.fps / self.config.playback_speed
                    await asyncio.sleep(delay)

            # REST end-session — saves recording (badminton) or persists score (challenges)
            rest_report = None
            should_end_rest = self.config.record or self.config.feature == "challenge"
            if should_end_rest:
                logger.info("Ending session via REST...")
                try:
                    rest_report = self.protocol.end_session(self.client, session_id)
                except Exception as e:
                    logger.warning(f"REST end-session failed: {e}")

            # Send WS end message
            logger.info("Sending WS end message...")
            await ws.send(self.protocol.END_MESSAGE)

            # Wait for end response (with timeout)
            try:
                await asyncio.wait_for(receive_done.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("Timed out waiting for end response")

            self.end_time = time.monotonic()
            recv_task.cancel()
            try:
                await recv_task
            except asyncio.CancelledError:
                pass

        # Merge REST report if WS didn't provide one
        if rest_report and not self.final_report:
            self.final_report = rest_report

    async def _receive_loop(self, ws, done_event: asyncio.Event):
        """Collect server responses until the end message arrives."""
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type", "")

                if msg_type in ("analysis_result", "challenge_update"):
                    self.results.append(msg)
                    # Check if challenge auto-ended (collapse, time limit, etc.)
                    if msg_type == "challenge_update" and msg.get("auto_end"):
                        reason = msg.get("end_reason", "unknown")
                        reps = msg.get("reps", 0)
                        logger.info(f"Challenge auto-ended: {reason} (reps={reps})")
                        self._auto_ended.set()
                elif msg_type == self.protocol.END_RESPONSE_TYPE:
                    self.final_report = msg.get("report", {})
                    done_event.set()
                    return
                elif msg_type in ("pong", "ping", "recording_started", "recording_stopped"):
                    pass
                else:
                    if self.config.verbose:
                        logger.debug(f"Received: {msg_type}")
        except websockets.ConnectionClosed:
            done_event.set()
        except asyncio.CancelledError:
            raise

    @property
    def elapsed(self) -> float:
        if self.end_time > 0:
            return self.end_time - self.start_time
        return time.monotonic() - self.start_time

    @property
    def effective_fps(self) -> float:
        e = self.elapsed
        return self.frames_sent / e if e > 0 else 0
