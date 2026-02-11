"""
WebSocket Stream Handler - Handles live streaming WebSocket connections.

This module manages WebSocket connections for live video streaming,
processing frames in real-time and broadcasting results.

Supports two modes:
- Basic: real-time pose analysis, instant results per frame
- Advanced: frames stored to disk, background processing, periodic results
"""

import json
import base64
import asyncio
from typing import Dict, List, Set, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import logging

from ..services.stream_service import (
    get_stream_session_manager, BasicStreamAnalyzer, AdvancedStreamAnalyzer,
)
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

        # Background tasks for advanced mode result broadcasting
        self._broadcast_tasks: Dict[int, asyncio.Task] = {}

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

        # Cancel broadcast task if any
        task = self._broadcast_tasks.pop(session_id, None)
        if task:
            task.cancel()

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

    # -------------------------------------------------------------------
    # Main stream handler (dispatches based on analyzer type)
    # -------------------------------------------------------------------

    async def handle_stream(self, websocket: WebSocket, session_id: int, analyzer):
        """
        Handle incoming stream frames from the streamer.

        Dispatches to basic or advanced handler based on analyzer type.
        """
        if isinstance(analyzer, AdvancedStreamAnalyzer):
            await self._handle_advanced_stream(websocket, session_id, analyzer)
        else:
            await self._handle_basic_stream(websocket, session_id, analyzer)

    # -------------------------------------------------------------------
    # Basic mode: real-time analysis per frame
    # -------------------------------------------------------------------

    async def _handle_basic_stream(
        self, websocket: WebSocket, session_id: int, analyzer: BasicStreamAnalyzer
    ):
        """Basic mode: analyze each frame in real-time, return results immediately."""
        try:
            while True:
                try:
                    raw_message = await asyncio.wait_for(
                        websocket.receive_text(), timeout=60.0
                    )
                except asyncio.TimeoutError:
                    try:
                        await websocket.send_json({"type": "ping"})
                        continue
                    except Exception:
                        break

                if raw_message == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue

                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError:
                    continue

                msg_type = message.get("type")

                if msg_type == "frame":
                    result = await self._process_basic_frame(analyzer, message)

                    if result.get('stats', {}).get('frames_processed', 0) % 30 == 0:
                        logger.info(f"Session {session_id}: Frame {result.get('stats', {}).get('frames_processed')}")

                    await websocket.send_json({"type": "analysis_result", **result})
                    await self.broadcast_to_viewers(session_id, {"type": "analysis_result", **result})

                elif msg_type == "start_recording":
                    analyzer.start_recording()
                    await websocket.send_json({"type": "recording_started"})

                elif msg_type == "stop_recording":
                    frames = analyzer.stop_recording()
                    await websocket.send_json({"type": "recording_stopped", "frame_count": len(frames)})

                elif msg_type == "end_stream":
                    await self._end_basic_stream(websocket, session_id, analyzer)
                    break

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            logger.info(f"Session {session_id}: WebSocket disconnected")
        except Exception as e:
            logger.error(f"Session {session_id}: Error in stream handler: {e}")
        finally:
            self.disconnect_streamer(session_id)

    async def _process_basic_frame(self, analyzer: BasicStreamAnalyzer, message: dict) -> dict:
        """Process a single frame for basic mode."""
        try:
            frame_b64 = message.get("data", "")
            timestamp = message.get("timestamp", 0.0)
            if not frame_b64:
                return {"error": "No frame data"}

            frame_data = base64.b64decode(frame_b64)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, analyzer.process_frame, frame_data, timestamp
            )
            return result
        except Exception as e:
            logger.error(f"Frame processing error: {e}", exc_info=True)
            return {"error": str(e)}

    async def _end_basic_stream(
        self, websocket: WebSocket, session_id: int, analyzer: BasicStreamAnalyzer
    ):
        """End a basic mode stream."""
        analyzer.release_raw_video_writer()
        report = analyzer.get_final_report()

        db = SessionLocal()
        try:
            session = db.query(StreamSession).filter(StreamSession.id == session_id).first()
            if session:
                session.status = StreamStatus.ENDED
                session.ended_at = datetime.utcnow()
                if report and 'summary' in report:
                    session.total_shots = report['summary'].get('total_shots', 0)
                if report and 'shot_distribution' in report:
                    session.shot_distribution = report['shot_distribution']
                if report and 'heatmap_data' in report:
                    session.foot_positions = report['heatmap_data']
                if report and 'shot_timeline' in report:
                    session.shot_timeline = report['shot_timeline']
                if analyzer.raw_video_path:
                    session.raw_video_local_path = analyzer.raw_video_path
                has_data = report.get('has_post_analysis_data', False)
                session.analysis_status = "pending" if has_data else "none"
                db.commit()
        except Exception as e:
            logger.error(f"Session {session_id}: Failed to save to DB: {e}")
            db.rollback()
        finally:
            db.close()

        await websocket.send_json({
            "type": "stream_ended",
            "report": report,
            "analysis_available": report.get('has_post_analysis_data', False),
        })
        await self.broadcast_to_viewers(session_id, {
            "type": "stream_ended",
            "report": report,
            "analysis_available": report.get('has_post_analysis_data', False),
        })
        logger.info(f"Session {session_id}: Basic stream ended")

    # -------------------------------------------------------------------
    # Advanced mode: buffer frames, background processing
    # -------------------------------------------------------------------

    async def _handle_advanced_stream(
        self, websocket: WebSocket, session_id: int, analyzer: AdvancedStreamAnalyzer
    ):
        """Advanced mode: store frames fast, background processor catches up."""

        # Start periodic result broadcaster
        self._broadcast_tasks[session_id] = asyncio.create_task(
            self._broadcast_advanced_results(websocket, session_id, analyzer)
        )

        try:
            while True:
                try:
                    raw_message = await asyncio.wait_for(
                        websocket.receive_text(), timeout=60.0
                    )
                except asyncio.TimeoutError:
                    try:
                        await websocket.send_json({"type": "ping"})
                        continue
                    except Exception:
                        break

                if raw_message == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue

                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError:
                    continue

                msg_type = message.get("type")

                if msg_type == "frame":
                    result = await self._process_advanced_frame(analyzer, message)

                    # Send lightweight buffer status back (~every 30 frames)
                    await websocket.send_json({"type": "frame_buffered", **result})

                elif msg_type == "end_stream":
                    await self._end_advanced_stream(websocket, session_id, analyzer)
                    break

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            logger.info(f"Session {session_id}: WebSocket disconnected")
        except Exception as e:
            logger.error(f"Session {session_id}: Error in advanced stream: {e}")
        finally:
            self.disconnect_streamer(session_id)

    async def _process_advanced_frame(
        self, analyzer: AdvancedStreamAnalyzer, message: dict
    ) -> dict:
        """Process a single frame for advanced mode (just store it)."""
        try:
            frame_b64 = message.get("data", "")
            timestamp = message.get("timestamp", 0.0)
            if not frame_b64:
                return {"error": "No frame data"}

            frame_data = base64.b64decode(frame_b64)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, analyzer.process_frame, frame_data, timestamp
            )
            return result
        except Exception as e:
            logger.error(f"Advanced frame error: {e}", exc_info=True)
            return {"error": str(e)}

    async def _broadcast_advanced_results(
        self, websocket: WebSocket, session_id: int, analyzer: AdvancedStreamAnalyzer
    ):
        """Periodically check for new classification results and push to client."""
        try:
            while True:
                await asyncio.sleep(2.0)

                if analyzer.has_new_results():
                    results = analyzer.get_accumulated_results()
                    status = analyzer._build_status()
                    msg = {
                        "type": "chunk_results",
                        "seconds_processed": status['seconds_processed'],
                        "seconds_buffered": status['seconds_buffered'],
                        "frames_processed": status['frames_processed'],
                        **results,
                    }
                    try:
                        await websocket.send_json(msg)
                        await self.broadcast_to_viewers(session_id, msg)
                    except Exception:
                        break
        except asyncio.CancelledError:
            pass

    async def _end_advanced_stream(
        self, websocket: WebSocket, session_id: int, analyzer: AdvancedStreamAnalyzer
    ):
        """End an advanced mode stream — finalize in background."""
        # Cancel result broadcaster
        task = self._broadcast_tasks.pop(session_id, None)
        if task:
            task.cancel()

        # Send preliminary report + "finalizing" status
        report = analyzer.get_final_report()
        await websocket.send_json({"type": "finalizing", "report": report})

        # Save basic info to DB
        db = SessionLocal()
        try:
            session = db.query(StreamSession).filter(StreamSession.id == session_id).first()
            if session:
                session.status = StreamStatus.ENDED
                session.ended_at = datetime.utcnow()
                if report and 'summary' in report:
                    session.total_shots = report['summary'].get('total_shots', 0)
                if report and 'shot_distribution' in report:
                    session.shot_distribution = report['shot_distribution']
                if analyzer.raw_video_path:
                    session.raw_video_local_path = analyzer.raw_video_path
                session.analysis_status = "running"
                db.commit()
        except Exception as e:
            logger.error(f"Session {session_id}: Failed to save to DB: {e}")
            db.rollback()
        finally:
            db.close()

        # Run finalize in executor (this takes a while — annotated video etc.)
        from ..config import get_settings
        settings = get_settings()
        output_dir = str(settings.output_path / str(session_id))

        loop = asyncio.get_event_loop()
        try:
            finalize_result = await loop.run_in_executor(
                None, analyzer.finalize, output_dir
            )
        except Exception as e:
            logger.error(f"Session {session_id}: Finalize failed: {e}", exc_info=True)
            finalize_result = {"error": str(e)}

        # Update DB with final results
        db = SessionLocal()
        try:
            session = db.query(StreamSession).filter(StreamSession.id == session_id).first()
            if session:
                if finalize_result and not finalize_result.get("error"):
                    session.analysis_status = "complete"
                    session.analysis_progress = 100
                    session.annotated_video_local_path = finalize_result.get("annotated_video_path")
                    session.frame_data_local_path = finalize_result.get("frame_data_path")
                    session.post_analysis_shots = finalize_result.get("total_shots")
                    session.post_analysis_distribution = finalize_result.get("shot_distribution")
                    session.post_analysis_rallies = finalize_result.get("total_rallies")
                    session.post_analysis_shuttle_hits = finalize_result.get("shuttle_hits")
                    # Update top-level totals so /results endpoint returns accurate data
                    session.total_shots = finalize_result.get("total_shots", session.total_shots)
                    session.shot_distribution = finalize_result.get("shot_distribution", session.shot_distribution)
                    # Save detailed data for results page
                    session.shot_timeline = finalize_result.get("shot_timeline")
                    session.foot_positions = finalize_result.get("foot_positions")
                    session.post_analysis_rally_data = finalize_result.get("rallies")
                else:
                    session.analysis_status = "failed"
                db.commit()
        except Exception as e:
            logger.error(f"Session {session_id}: Failed to save finalize to DB: {e}")
            db.rollback()
        finally:
            db.close()

        # Send final result
        success = bool(finalize_result and not finalize_result.get("error"))
        msg = {
            "type": "stream_ended",
            "report": finalize_result,
            "analysis_available": success,
            "analysis_status": "complete" if success else "failed",
        }
        await websocket.send_json(msg)
        await self.broadcast_to_viewers(session_id, msg)
        logger.info(f"Session {session_id}: Advanced stream ended and finalized")

    # -------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------

    def get_session_stats(self, session_id: int) -> Optional[dict]:
        """Get current stats for a session."""
        analyzer = self._session_manager.get_session(session_id)
        if analyzer and isinstance(analyzer, BasicStreamAnalyzer):
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
