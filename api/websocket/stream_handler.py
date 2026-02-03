"""
WebSocket Stream Handler - Handles live streaming WebSocket connections.

This module manages WebSocket connections for live video streaming,
processing frames in real-time and broadcasting results.
"""

import json
import base64
import asyncio
from typing import Dict, List, Set, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import logging

from ..services.stream_service import get_stream_session_manager, StreamAnalyzer
from ..database import SessionLocal
from ..db_models.stream_session import StreamSession, StreamStatus

logger = logging.getLogger(__name__)


class StreamConnectionManager:
    """
    Manages WebSocket connections for live streaming sessions.

    Handles:
    - Active stream connections (sending frames)
    - Viewer connections (receiving results only)
    - Broadcasting results to all connected clients
    """

    def __init__(self):
        # Active streaming connections (one per session - the streamer)
        self._stream_connections: Dict[int, WebSocket] = {}

        # Viewer connections (multiple per session - observers)
        self._viewer_connections: Dict[int, Set[WebSocket]] = {}

        # Session analyzers
        self._session_manager = get_stream_session_manager()

    async def connect_streamer(self, websocket: WebSocket, session_id: int) -> bool:
        """
        Connect a streamer (frame sender) to a session.

        Only one streamer per session is allowed.
        """
        if session_id in self._stream_connections:
            logger.warning(f"Session {session_id} already has a streamer")
            return False

        await websocket.accept()
        self._stream_connections[session_id] = websocket

        if session_id not in self._viewer_connections:
            self._viewer_connections[session_id] = set()

        logger.info(f"Streamer connected to session {session_id}")
        return True

    async def connect_viewer(self, websocket: WebSocket, session_id: int) -> bool:
        """
        Connect a viewer (results receiver) to a session.
        """
        if session_id not in self._viewer_connections:
            self._viewer_connections[session_id] = set()

        await websocket.accept()
        self._viewer_connections[session_id].add(websocket)

        logger.info(f"Viewer connected to session {session_id} "
                   f"(total viewers: {len(self._viewer_connections[session_id])})")
        return True

    def disconnect_streamer(self, session_id: int):
        """Disconnect streamer from session."""
        if session_id in self._stream_connections:
            del self._stream_connections[session_id]
            logger.info(f"Streamer disconnected from session {session_id}")

    def disconnect_viewer(self, websocket: WebSocket, session_id: int):
        """Disconnect viewer from session."""
        if session_id in self._viewer_connections:
            self._viewer_connections[session_id].discard(websocket)
            logger.info(f"Viewer disconnected from session {session_id}")

    async def broadcast_to_viewers(self, session_id: int, message: dict):
        """Broadcast message to all viewers of a session."""
        if session_id not in self._viewer_connections:
            return

        viewers = list(self._viewer_connections[session_id])
        dead_connections = []

        for viewer in viewers:
            try:
                await viewer.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to viewer: {e}")
                dead_connections.append(viewer)

        # Remove dead connections
        for conn in dead_connections:
            self._viewer_connections[session_id].discard(conn)

    async def handle_stream(self, websocket: WebSocket, session_id: int, analyzer: StreamAnalyzer):
        """
        Handle incoming stream frames from the streamer.

        Message protocol:
        - type: "frame" - Contains frame data to analyze
        - type: "start_recording" - Start recording frames
        - type: "stop_recording" - Stop recording frames
        - type: "end_stream" - End the streaming session
        - type: "ping" - Keep-alive ping
        """
        try:
            while True:
                # Receive message
                try:
                    raw_message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=60.0  # 60 second timeout
                    )
                except asyncio.TimeoutError:
                    # Send ping to check connection
                    try:
                        await websocket.send_json({"type": "ping"})
                        continue
                    except Exception:
                        logger.info(f"Session {session_id}: Connection timeout")
                        break

                # Handle ping
                if raw_message == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue

                # Parse message
                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError:
                    logger.warning(f"Session {session_id}: Invalid JSON received")
                    continue

                msg_type = message.get("type")

                if msg_type == "frame":
                    # Process frame
                    result = await self._process_frame(analyzer, message)

                    # Debug logging every 30 frames
                    if result.get('stats', {}).get('frames_processed', 0) % 30 == 0:
                        logger.info(f"Session {session_id}: Processed frame {result.get('stats', {}).get('frames_processed')}")

                    # Send result back to streamer
                    await websocket.send_json({
                        "type": "analysis_result",
                        **result
                    })

                    # Broadcast to viewers
                    await self.broadcast_to_viewers(session_id, {
                        "type": "analysis_result",
                        **result
                    })

                elif msg_type == "start_recording":
                    analyzer.start_recording()
                    await websocket.send_json({
                        "type": "recording_started"
                    })

                elif msg_type == "stop_recording":
                    frames = analyzer.stop_recording()
                    await websocket.send_json({
                        "type": "recording_stopped",
                        "frame_count": len(frames)
                    })

                elif msg_type == "end_stream":
                    # Generate final report
                    report = analyzer.get_final_report()

                    # Save to database
                    db = SessionLocal()
                    try:
                        session = db.query(StreamSession).filter(
                            StreamSession.id == session_id
                        ).first()
                        if session:
                            session.status = StreamStatus.ENDED
                            session.ended_at = datetime.utcnow()
                            if report and 'summary' in report:
                                session.total_shots = report['summary'].get('total_shots', 0)
                            if report and 'shot_distribution' in report:
                                session.shot_distribution = report['shot_distribution']
                            # Save heatmap data (foot positions with timestamps)
                            if report and 'heatmap_data' in report:
                                session.foot_positions = report['heatmap_data']
                            # Save shot timeline for trajectory visualization
                            if report and 'shot_timeline' in report:
                                session.shot_timeline = report['shot_timeline']
                            db.commit()
                            logger.info(f"Session {session_id}: Saved to DB - {session.total_shots} shots, {len(report.get('heatmap_data', []))} positions")
                    except Exception as e:
                        logger.error(f"Session {session_id}: Failed to save to DB: {e}")
                        db.rollback()
                    finally:
                        db.close()

                    await websocket.send_json({
                        "type": "stream_ended",
                        "report": report
                    })

                    # Notify viewers
                    await self.broadcast_to_viewers(session_id, {
                        "type": "stream_ended",
                        "report": report
                    })

                    logger.info(f"Session {session_id}: Stream ended by user")
                    break

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                else:
                    logger.warning(f"Session {session_id}: Unknown message type: {msg_type}")

        except WebSocketDisconnect:
            logger.info(f"Session {session_id}: WebSocket disconnected")
        except Exception as e:
            logger.error(f"Session {session_id}: Error in stream handler: {e}")
        finally:
            self.disconnect_streamer(session_id)

    async def _process_frame(self, analyzer: StreamAnalyzer, message: dict) -> dict:
        """Process a single frame message."""
        try:
            # Get frame data
            frame_b64 = message.get("data", "")
            timestamp = message.get("timestamp", 0.0)

            if not frame_b64:
                logger.warning("Received empty frame data")
                return {"error": "No frame data"}

            # Decode base64
            frame_data = base64.b64decode(frame_b64)

            # Log frame size periodically
            if analyzer.stats.frames_processed % 30 == 0:
                logger.debug(f"Processing frame, size: {len(frame_data)} bytes")

            # Process frame (run in executor to not block event loop)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                analyzer.process_frame,
                frame_data,
                timestamp
            )

            return result

        except Exception as e:
            logger.error(f"Frame processing error: {e}", exc_info=True)
            return {"error": str(e)}

    def get_session_stats(self, session_id: int) -> Optional[dict]:
        """Get current stats for a session."""
        analyzer = self._session_manager.get_session(session_id)
        if analyzer:
            return analyzer._get_stats_dict()
        return None

    def get_active_sessions(self) -> List[int]:
        """Get list of active session IDs."""
        return list(self._stream_connections.keys())


# Global connection manager
_connection_manager: Optional[StreamConnectionManager] = None


def get_stream_connection_manager() -> StreamConnectionManager:
    """Get the global stream connection manager."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = StreamConnectionManager()
    return _connection_manager
