"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import init_db, get_db, SessionLocal
from .routers import auth_router, analysis_router, court_router, results_router, upload_router, stream_router
from .routers.admin import router as admin_router
from .websocket.progress_handler import get_ws_manager
from .websocket.stream_handler import get_stream_connection_manager
from .services.user_service import UserService
from .services.job_manager import JobManager
from .services.stream_service import get_stream_session_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


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

# Include routers
app.include_router(auth_router)
app.include_router(analysis_router)
app.include_router(court_router)
app.include_router(results_router)
app.include_router(upload_router)
app.include_router(stream_router)
app.include_router(admin_router)


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
    """Health check endpoint."""
    return {"status": "healthy"}


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
    finally:
        db.close()

    # Connect to stream manager
    stream_manager = get_stream_connection_manager()
    session_manager = get_stream_session_manager()

    # Get or create analyzer
    analyzer = session_manager.get_session(session_id)
    if not analyzer:
        analyzer = session_manager.create_session(session_id, court_boundary)

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
