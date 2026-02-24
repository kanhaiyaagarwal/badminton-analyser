"""FastAPI application entry point."""

import os
import json
import base64
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Datadog APM — auto-instruments FastAPI when ddtrace is installed + DD agent is running
if os.environ.get("DD_TRACE_ENABLED", "").lower() in ("1", "true"):
    try:
        from ddtrace import patch_all
        patch_all()
        logging.getLogger(__name__).info("Datadog APM tracing enabled")
    except ImportError:
        logging.getLogger(__name__).info("ddtrace not installed — skipping APM")

from .config import get_settings
from sqlalchemy import text
from .database import init_db, get_db, SessionLocal
from .routers import auth_router, analysis_router, court_router, results_router, upload_router, stream_router
from .routers.admin import router as admin_router
from .routers.tuning import router as tuning_router
from .websocket.progress_handler import get_ws_manager
from .websocket.stream_handler import get_stream_connection_manager
from .services.user_service import UserService
from .services.job_manager import JobManager
from .services.stream_service import get_stream_session_manager
from .features.registry import build_registry
from .core.streaming.session_manager import get_generic_session_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Build feature registry (import-time — no side effects beyond logging)
feature_registry = build_registry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Badminton Analyzer API...")
    init_db()

    # Ensure directories exist
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Upload directory: {settings.upload_path}")
    logger.info(f"Output directory: {settings.output_path}")

    yield

    # Shutdown
    logger.info("Shutting down...")
    JobManager.get_instance().shutdown()
    get_stream_session_manager().close_all()
    get_generic_session_manager().close_all()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="API for badminton video analysis with shot detection and movement tracking",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include existing routers (badminton — stays hardcoded for now)
app.include_router(auth_router)
app.include_router(analysis_router)
app.include_router(court_router)
app.include_router(results_router)
app.include_router(upload_router)
app.include_router(stream_router)
app.include_router(admin_router)
app.include_router(tuning_router)

# Include feature-registered routers (challenges, etc.)
feature_registry.install_routers(app)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint — verifies DB connectivity."""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy", "db": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "db": "disconnected", "error": str(e)},
        )


@app.get("/api/v1/features")
async def list_features():
    """Return available platform features."""
    return feature_registry.list_features()


# ---------------------------------------------------------------------------
# WebSocket: job progress (unchanged)
# ---------------------------------------------------------------------------

@app.websocket("/ws/progress/{job_id}")
async def websocket_progress(
    websocket: WebSocket,
    job_id: int,
    token: str = Query(...)
):
    """WebSocket endpoint for real-time progress updates."""
    # Validate token
    token_data = UserService.decode_token(token)
    if token_data is None or token_data.user_id is None:
        await websocket.accept()
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Verify job belongs to user
    db = SessionLocal()
    try:
        from .db_models.job import Job
        job = db.query(Job).filter(
            Job.id == job_id,
            Job.user_id == token_data.user_id
        ).first()

        if not job:
            await websocket.accept()
            await websocket.close(code=4004, reason="Job not found")
            return
    finally:
        db.close()

    # Connect to WebSocket manager
    ws_manager = get_ws_manager()
    await ws_manager.connect(websocket, job_id)

    try:
        # Keep connection alive
        while True:
            # Wait for messages (ping/pong)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, job_id)
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
        await ws_manager.disconnect(websocket, job_id)


# ---------------------------------------------------------------------------
# WebSocket: badminton live stream (unchanged)
# ---------------------------------------------------------------------------

@app.websocket("/ws/stream/{session_id}")
async def websocket_stream(
    websocket: WebSocket,
    session_id: int,
    token: str = Query(...)
):
    """WebSocket endpoint for live streaming."""
    # Validate token
    token_data = UserService.decode_token(token)
    if token_data is None or token_data.user_id is None:
        # Must accept before closing to avoid 403 HTTP error
        await websocket.accept()
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Verify session belongs to user
    db = SessionLocal()
    try:
        from .db_models.stream_session import StreamSession, StreamStatus
        session = db.query(StreamSession).filter(
            StreamSession.id == session_id,
            StreamSession.user_id == token_data.user_id
        ).first()

        if not session:
            await websocket.accept()
            await websocket.close(code=4004, reason="Session not found")
            return

        if session.status not in [StreamStatus.READY, StreamStatus.STREAMING]:
            await websocket.accept()
            await websocket.close(code=4000, reason="Session not ready for streaming")
            return

        court_boundary = session.court_boundary
        stream_mode = session.stream_mode or "basic"
        frame_rate = float(session.frame_rate or 30)
        enable_tuning_data = bool(session.enable_tuning_data)
        enable_shuttle_tracking = bool(session.enable_shuttle_tracking)
        chunk_duration = session.chunk_duration or 60
    finally:
        db.close()

    # Connect to stream manager
    stream_manager = get_stream_connection_manager()
    session_manager = get_stream_session_manager()

    # Get or create analyzer
    analyzer = session_manager.get_session(session_id)
    if not analyzer:
        from .config import get_settings
        settings = get_settings()
        output_dir = str(settings.output_path / str(token_data.user_id) / f"stream_{session_id}")
        analyzer = session_manager.create_session(
            session_id, court_boundary,
            frame_rate=frame_rate,
            enable_tuning_data=enable_tuning_data,
            enable_shuttle_tracking=enable_shuttle_tracking,
            output_dir=output_dir,
            stream_mode=stream_mode,
            chunk_duration=chunk_duration,
        )

    # Connect as streamer (this accepts the websocket internally)
    if not await stream_manager.connect_streamer(websocket, session_id):
        # connect_streamer doesn't accept if it fails, so we need to accept first
        try:
            await websocket.accept()
        except Exception:
            pass  # Already accepted in some cases
        await websocket.close(code=4002, reason="Session already has a streamer")
        return

    # Update session status
    db = SessionLocal()
    try:
        session = db.query(StreamSession).filter(StreamSession.id == session_id).first()
        if session:
            session.status = StreamStatus.STREAMING
            db.commit()
    finally:
        db.close()

    # Handle stream
    await stream_manager.handle_stream(websocket, session_id, analyzer)


@app.websocket("/ws/stream/{session_id}/view")
async def websocket_stream_viewer(
    websocket: WebSocket,
    session_id: int,
    token: str = Query(...)
):
    """WebSocket endpoint for viewing live stream results (read-only)."""
    # Validate token
    token_data = UserService.decode_token(token)
    if token_data is None or token_data.user_id is None:
        await websocket.accept()
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Connect as viewer
    stream_manager = get_stream_connection_manager()
    await stream_manager.connect_viewer(websocket, session_id)

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        stream_manager.disconnect_viewer(websocket, session_id)
    except Exception as e:
        logger.error(f"Viewer WebSocket error for session {session_id}: {e}")
        stream_manager.disconnect_viewer(websocket, session_id)


# ---------------------------------------------------------------------------
# WebSocket: challenge sessions (new — feature-aware)
# ---------------------------------------------------------------------------

@app.websocket("/ws/challenge/{session_id}")
async def websocket_challenge(
    websocket: WebSocket,
    session_id: int,
    token: str = Query(...)
):
    """
    WebSocket for challenge sessions (plank/squat/pushup).

    Protocol (same as badminton stream):
      Client sends: { "type": "frame", "data": "<base64 jpeg>", "timestamp": <float> }
      Server replies: { "type": "challenge_update", ... }
      Client sends: { "type": "end_session" } to finish.
    """
    # Validate token
    token_data = UserService.decode_token(token)
    if token_data is None or token_data.user_id is None:
        await websocket.accept()
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Verify session belongs to user
    db = SessionLocal()
    try:
        from .features.challenges.db_models.challenge import ChallengeSession, ChallengeStatus
        session = db.query(ChallengeSession).filter(
            ChallengeSession.id == session_id,
            ChallengeSession.user_id == token_data.user_id,
        ).first()

        if not session:
            await websocket.accept()
            await websocket.close(code=4004, reason="Session not found")
            return

        if session.status == ChallengeStatus.ENDED:
            await websocket.accept()
            await websocket.close(code=4000, reason="Session already ended")
            return
    finally:
        db.close()

    # Get analyzer from generic session manager
    gsm = get_generic_session_manager()
    analyzer = gsm.get_session(session_id)

    if not analyzer:
        await websocket.accept()
        await websocket.close(code=4004, reason="No analyzer for this session — create session first via REST")
        return

    await websocket.accept()

    # Mark session as active
    db = SessionLocal()
    try:
        from .features.challenges.db_models.challenge import ChallengeSession, ChallengeStatus
        session = db.query(ChallengeSession).filter(ChallengeSession.id == session_id).first()
        if session:
            session.status = ChallengeStatus.ACTIVE
            db.commit()
    finally:
        db.close()

    try:
        while True:
            try:
                raw_message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0,
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
                frame_b64 = message.get("data", "")
                timestamp = message.get("timestamp", 0.0)
                if not frame_b64:
                    continue

                frame_data = base64.b64decode(frame_b64)

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, analyzer.process_frame, frame_data, timestamp
                )
                await websocket.send_json(result)

            elif msg_type == "end_session":
                report = analyzer.get_final_report()
                await websocket.send_json({"type": "session_ended", "report": report})
                break

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"Challenge session {session_id}: WebSocket disconnected")
    except Exception as e:
        logger.error(f"Challenge session {session_id}: Error: {e}")

    # ---- Cleanup: end session if still active (e.g. user pressed back) ----
    try:
        from .features.challenges.db_models.challenge import (
            ChallengeSession as CS, ChallengeStatus, ChallengeRecord,
        )
        from .features.challenges.routers.challenges import _save_recording, _save_screenshots

        db2 = SessionLocal()
        try:
            sess = db2.query(CS).filter(CS.id == session_id).first()
            if sess and sess.status != ChallengeStatus.ENDED:
                # Save recording if active
                if analyzer and getattr(analyzer, 'is_recording', False):
                    frames = analyzer.stop_recording()
                    _save_recording(frames, sess, sess.user_id)
                    sess.is_recording = False

                # Save screenshots
                screenshots = analyzer.get_screenshots() if analyzer else []

                report = gsm.end_session(session_id) or {}

                _save_screenshots(screenshots, sess, sess.user_id)

                sess.status = ChallengeStatus.ENDED
                sess.ended_at = datetime.utcnow()
                sess.score = report.get("score", 0)
                sess.duration_seconds = report.get("duration_seconds", 0.0)
                sess.extra_data = report
                sess.form_summary = report.get("form_summary")

                # Update personal best
                record = db2.query(ChallengeRecord).filter(
                    ChallengeRecord.user_id == sess.user_id,
                    ChallengeRecord.challenge_type == sess.challenge_type,
                ).first()
                if record:
                    if sess.score > record.best_score:
                        record.best_score = sess.score
                else:
                    db2.add(ChallengeRecord(
                        user_id=sess.user_id,
                        challenge_type=sess.challenge_type,
                        best_score=sess.score,
                    ))

                db2.commit()
                logger.info(f"Challenge session {session_id}: auto-ended on disconnect (score={sess.score})")
        finally:
            db2.close()
    except Exception as cleanup_err:
        logger.error(f"Challenge session {session_id}: cleanup error: {cleanup_err}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
