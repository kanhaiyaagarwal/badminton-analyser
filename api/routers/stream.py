"""Stream router for live streaming sessions."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models.stream_session import StreamSession, StreamStatus
from ..services.stream_service import get_stream_session_manager
from ..services.storage_service import get_storage_service
from ..websocket.stream_handler import get_stream_connection_manager
from .auth import get_current_user

router = APIRouter(prefix="/api/v1/stream", tags=["stream"])


# Request/Response models
class CreateStreamRequest(BaseModel):
    """Request to create a new stream session."""
    title: Optional[str] = None
    frame_rate: int = 10
    quality: str = "medium"


class CreateStreamResponse(BaseModel):
    """Response with new stream session info."""
    session_id: int
    status: str
    ws_url: str


class SetupCourtRequest(BaseModel):
    """Request to set up court boundary."""
    court_boundary: dict


class StreamSessionResponse(BaseModel):
    """Stream session info response."""
    id: int
    title: Optional[str]
    status: str
    is_recording: bool
    total_shots: int
    current_rally: int
    created_at: datetime
    started_at: Optional[datetime]


class StartRecordingResponse(BaseModel):
    """Response for recording start."""
    recording: bool
    message: str


@router.post("/create", response_model=CreateStreamResponse)
async def create_stream_session(
    request: CreateStreamRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new streaming session."""
    # Validate frame rate
    if request.frame_rate not in [5, 10, 15, 30]:
        raise HTTPException(status_code=400, detail="Invalid frame rate. Use 5, 10, 15, or 30")

    if request.quality not in ["low", "medium", "high", "max"]:
        raise HTTPException(status_code=400, detail="Invalid quality. Use low, medium, high, or max")

    # Create session in database
    session = StreamSession(
        user_id=current_user.id,
        title=request.title,
        status=StreamStatus.SETUP,
        frame_rate=request.frame_rate,
        quality=request.quality,
        storage_type=get_storage_service().storage_type
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return CreateStreamResponse(
        session_id=session.id,
        status=session.status.value,
        ws_url=f"/ws/stream/{session.id}"
    )


@router.post("/{session_id}/setup-court")
async def setup_court(
    session_id: int,
    request: SetupCourtRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set court boundary for the stream session."""
    session = db.query(StreamSession).filter(
        StreamSession.id == session_id,
        StreamSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status not in [StreamStatus.SETUP, StreamStatus.READY]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot setup court in {session.status.value} state"
        )

    # Validate court boundary
    required_keys = ['top_left', 'top_right', 'bottom_left', 'bottom_right']
    for key in required_keys:
        if key not in request.court_boundary:
            raise HTTPException(
                status_code=400,
                detail=f"Missing court boundary key: {key}"
            )

    session.court_boundary = request.court_boundary
    session.status = StreamStatus.READY
    db.commit()

    return {
        "status": "success",
        "message": "Court boundary set. Ready to start streaming.",
        "session_status": session.status.value
    }


@router.post("/{session_id}/start")
async def start_stream(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark session as streaming (actual streaming via WebSocket)."""
    session = db.query(StreamSession).filter(
        StreamSession.id == session_id,
        StreamSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != StreamStatus.READY:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start stream in {session.status.value} state. Set up court first."
        )

    if not session.court_boundary:
        raise HTTPException(
            status_code=400,
            detail="Court boundary not set"
        )

    # Create analyzer for this session
    session_manager = get_stream_session_manager()
    session_manager.create_session(session_id, session.court_boundary)

    session.status = StreamStatus.STREAMING
    session.started_at = datetime.utcnow()
    db.commit()

    return {
        "status": "success",
        "message": "Stream started. Connect to WebSocket to send frames.",
        "ws_url": f"/ws/stream/{session_id}"
    }


@router.post("/{session_id}/end")
async def end_stream(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """End the streaming session and get final report."""
    from pathlib import Path
    from ..config import get_settings
    from ..services.storage_service import get_storage_service
    import cv2
    import numpy as np
    import logging

    logger = logging.getLogger(__name__)
    settings = get_settings()
    storage = get_storage_service()

    session = db.query(StreamSession).filter(
        StreamSession.id == session_id,
        StreamSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == StreamStatus.ENDED:
        raise HTTPException(status_code=400, detail="Session already ended")

    # Get analyzer before ending session
    session_manager = get_stream_session_manager()
    analyzer = session_manager.get_session(session_id)

    # If recording was active, save it before ending
    if analyzer and session.is_recording:
        logger.info(f"Auto-saving recording for session {session_id} before ending")
        frames = analyzer.stop_recording()
        session.is_recording = False

        if frames:
            try:
                # Create output directory
                output_dir = settings.output_path / str(current_user.id) / f"stream_{session_id}"
                output_dir.mkdir(parents=True, exist_ok=True)
                video_path = str(output_dir / "recording.mp4")

                # Decode first frame to get dimensions
                first_frame = cv2.imdecode(np.frombuffer(frames[0], np.uint8), cv2.IMREAD_COLOR)
                height, width = first_frame.shape[:2]

                # Create video writer
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                fps = session.frame_rate or 10
                out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

                # Write all frames
                for frame_data in frames:
                    frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        out.write(frame)
                out.release()

                # Upload to S3 if enabled
                if storage.is_s3():
                    try:
                        s3_key = f"streams/{current_user.id}/stream_{session_id}/recording.mp4"
                        with open(video_path, 'rb') as f:
                            storage.outputs.save(s3_key, f, content_type='video/mp4')
                        session.recording_s3_key = s3_key
                        logger.info(f"Uploaded stream recording to S3: {s3_key}")
                        Path(video_path).unlink(missing_ok=True)
                    except Exception as e:
                        logger.error(f"Failed to upload recording to S3: {e}")
                        session.recording_local_path = video_path
                else:
                    session.recording_local_path = video_path

                logger.info(f"Auto-saved recording with {len(frames)} frames for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to auto-save recording: {e}")

    # Get final report from analyzer
    report = session_manager.end_session(session_id)

    # Update session in database
    session.status = StreamStatus.ENDED
    session.ended_at = datetime.utcnow()

    if report:
        # Save summary stats
        if 'summary' in report:
            session.total_shots = report['summary'].get('total_shots', 0)

        # Save shot distribution
        if 'shot_distribution' in report:
            session.shot_distribution = report['shot_distribution']

    db.commit()

    return {
        "status": "success",
        "message": "Stream ended",
        "report": report
    }


@router.get("/{session_id}/status", response_model=StreamSessionResponse)
async def get_stream_status(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current stream session status."""
    session = db.query(StreamSession).filter(
        StreamSession.id == session_id,
        StreamSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get live stats if streaming
    if session.status == StreamStatus.STREAMING:
        session_manager = get_stream_session_manager()
        analyzer = session_manager.get_session(session_id)
        if analyzer:
            session.total_shots = analyzer.stats.total_shots
            session.current_rally = analyzer.stats.current_rally

    return StreamSessionResponse(
        id=session.id,
        title=session.title,
        status=session.status.value,
        is_recording=session.is_recording,
        total_shots=session.total_shots,
        current_rally=session.current_rally,
        created_at=session.created_at,
        started_at=session.started_at
    )


@router.post("/{session_id}/recording/start", response_model=StartRecordingResponse)
async def start_recording(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start recording the stream."""
    session = db.query(StreamSession).filter(
        StreamSession.id == session_id,
        StreamSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != StreamStatus.STREAMING:
        raise HTTPException(status_code=400, detail="Session is not streaming")

    session_manager = get_stream_session_manager()
    analyzer = session_manager.get_session(session_id)

    if not analyzer:
        raise HTTPException(status_code=400, detail="Analyzer not found")

    analyzer.start_recording()
    session.is_recording = True
    db.commit()

    return StartRecordingResponse(
        recording=True,
        message="Recording started"
    )


@router.post("/{session_id}/recording/stop")
async def stop_recording(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stop recording the stream."""
    from pathlib import Path
    from ..config import get_settings
    from ..services.storage_service import get_storage_service
    import cv2
    import numpy as np
    import logging

    logger = logging.getLogger(__name__)
    settings = get_settings()
    storage = get_storage_service()

    session = db.query(StreamSession).filter(
        StreamSession.id == session_id,
        StreamSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_manager = get_stream_session_manager()
    analyzer = session_manager.get_session(session_id)

    if not analyzer:
        # Check if session already has a recording (auto-saved on end)
        if session.recording_s3_key or session.recording_local_path:
            return {
                "recording": False,
                "message": "Recording already saved when session ended",
                "frame_count": 0,
                "has_video": True
            }
        logger.warning(f"Analyzer not found for session {session_id} - session may have ended")
        raise HTTPException(status_code=400, detail="Stream session not active. Recording may have been auto-saved when session ended.")

    frames = analyzer.stop_recording()
    session.is_recording = False

    video_path = None
    s3_key = None
    if frames:
        # Create output directory for local processing
        output_dir = settings.output_path / str(current_user.id) / f"stream_{session_id}"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save frames as video locally first (needed for encoding)
        video_path = str(output_dir / "recording.mp4")

        try:
            # Decode first frame to get dimensions
            first_frame = cv2.imdecode(np.frombuffer(frames[0], np.uint8), cv2.IMREAD_COLOR)
            height, width = first_frame.shape[:2]

            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = session.frame_rate or 10
            out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

            # Write all frames
            for frame_data in frames:
                frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    out.write(frame)

            out.release()

            # Upload to S3 if enabled
            if storage.is_s3():
                try:
                    s3_key = f"streams/{current_user.id}/stream_{session_id}/recording.mp4"
                    with open(video_path, 'rb') as f:
                        storage.outputs.save(s3_key, f, content_type='video/mp4')
                    session.recording_s3_key = s3_key
                    logger.info(f"Uploaded stream recording to S3: {s3_key}")

                    # Clean up local file after successful S3 upload
                    Path(video_path).unlink(missing_ok=True)
                    video_path = None
                except Exception as e:
                    logger.error(f"Failed to upload recording to S3: {e}")
                    # Keep local path as fallback
                    session.recording_local_path = video_path
            else:
                session.recording_local_path = video_path

        except Exception as e:
            logger.error(f"Failed to create recording: {e}")
            video_path = None
            # Log error but don't fail the request

    db.commit()

    return {
        "recording": False,
        "message": "Recording stopped and saved" if (video_path or s3_key) else "Recording stopped",
        "frame_count": len(frames),
        "has_video": (video_path is not None) or (s3_key is not None)
    }


@router.get("/{session_id}/recording")
async def download_recording(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download the recorded video for a session."""
    from fastapi.responses import FileResponse, Response
    from pathlib import Path
    from ..services.storage_service import get_storage_service
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Download recording request for session {session_id} by user {current_user.id}")

    storage = get_storage_service()

    session = db.query(StreamSession).filter(
        StreamSession.id == session_id,
        StreamSession.user_id == current_user.id
    ).first()

    if not session:
        logger.warning(f"Session {session_id} not found for user {current_user.id}")
        raise HTTPException(status_code=404, detail="Session not found")

    logger.info(f"Session found: s3_key={session.recording_s3_key}, local_path={session.recording_local_path}")
    filename = f"stream_recording_{session_id}.mp4"

    # Check S3 first
    if session.recording_s3_key and storage.is_s3():
        try:
            logger.info(f"Loading recording from S3: {session.recording_s3_key}")
            video_data = storage.outputs.load(session.recording_s3_key)
            logger.info(f"S3 recording loaded, size: {len(video_data)} bytes")
            return Response(
                content=video_data,
                media_type="video/mp4",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
        except Exception as e:
            logger.error(f"Failed to load from S3: {e}")
            # Fall through to local check

    # Check local file
    if session.recording_local_path:
        video_path = Path(session.recording_local_path)
        logger.info(f"Checking local path: {video_path}, exists: {video_path.exists()}")
        if video_path.exists():
            return FileResponse(
                path=str(video_path),
                media_type="video/mp4",
                filename=filename
            )

    logger.warning(f"No recording available for session {session_id}")
    raise HTTPException(status_code=404, detail="No recording available for this session")


@router.get("/{session_id}/stats")
async def get_live_stats(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get live statistics for streaming session."""
    session = db.query(StreamSession).filter(
        StreamSession.id == session_id,
        StreamSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != StreamStatus.STREAMING:
        return {
            "status": session.status.value,
            "message": "Session is not streaming"
        }

    connection_manager = get_stream_connection_manager()
    stats = connection_manager.get_session_stats(session_id)

    if not stats:
        return {
            "status": session.status.value,
            "message": "No stats available"
        }

    return stats


@router.get("/active")
async def list_active_sessions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's active streaming sessions."""
    sessions = db.query(StreamSession).filter(
        StreamSession.user_id == current_user.id,
        StreamSession.status.in_([StreamStatus.SETUP, StreamStatus.READY, StreamStatus.STREAMING])
    ).all()

    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "status": s.status.value,
                "created_at": s.created_at.isoformat() if s.created_at else None
            }
            for s in sessions
        ]
    }


@router.get("/sessions")
async def list_all_sessions(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all user's stream sessions (for dashboard)."""
    from pathlib import Path

    query = db.query(StreamSession).filter(StreamSession.user_id == current_user.id)

    if status_filter:
        try:
            status_enum = StreamStatus(status_filter)
            query = query.filter(StreamSession.status == status_enum)
        except ValueError:
            pass

    total = query.count()
    sessions = query.order_by(StreamSession.created_at.desc()).offset(skip).limit(limit).all()

    def has_recording(s):
        # Check S3 first
        if s.recording_s3_key:
            return True
        # Check local file
        if s.recording_local_path:
            return Path(s.recording_local_path).exists()
        return False

    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title or f"Live Session #{s.id}",
                "status": s.status.value,
                "total_shots": s.total_shots,
                "shot_distribution": s.shot_distribution,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "has_results": s.status == StreamStatus.ENDED and s.total_shots > 0,
                "has_recording": has_recording(s),
                "type": "stream"
            }
            for s in sessions
        ],
        "total": total
    }


@router.get("/{session_id}/results")
async def get_session_results(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full results for an ended stream session."""
    from pathlib import Path
    import logging

    logger = logging.getLogger(__name__)

    session = db.query(StreamSession).filter(
        StreamSession.id == session_id,
        StreamSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != StreamStatus.ENDED:
        raise HTTPException(status_code=400, detail="Session has not ended yet")

    # Calculate duration if we have timestamps
    duration = None
    if session.started_at and session.ended_at:
        duration = (session.ended_at - session.started_at).total_seconds()

    # Check if recording exists (S3 or local)
    has_recording = False
    if session.recording_s3_key:
        has_recording = True
        logger.info(f"Session {session_id} has S3 recording: {session.recording_s3_key}")
    elif session.recording_local_path:
        has_recording = Path(session.recording_local_path).exists()
        logger.info(f"Session {session_id} local recording: {session.recording_local_path}, exists: {has_recording}")

    return {
        "session_id": session.id,
        "title": session.title or f"Live Session #{session.id}",
        "summary": {
            "total_shots": session.total_shots,
            "session_duration": duration,
            "frame_rate": session.frame_rate,
            "quality": session.quality
        },
        "shot_distribution": session.shot_distribution or {},
        "heatmap_paths": session.heatmap_paths,
        "foot_positions": session.foot_positions or [],
        "shot_timeline": session.shot_timeline or [],
        "court_boundary": session.court_boundary,
        "has_recording": has_recording,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None
    }


@router.get("/{session_id}/heatmaps")
async def get_session_heatmaps(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get heatmap visualizations for a stream session."""
    from pathlib import Path
    import json
    import tempfile
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from heatmap_visualizer import HeatmapVisualizer, VisualizerConfig

    session = db.query(StreamSession).filter(
        StreamSession.id == session_id,
        StreamSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.foot_positions or len(session.foot_positions) < 5:
        return {"heatmaps": [], "message": "Not enough position data for heatmaps"}

    # Check if heatmaps already generated
    output_dir = Path(f"analysis_output/stream_{session_id}")
    if session.heatmap_paths and all(Path(p).exists() for p in session.heatmap_paths.values()):
        # Return existing heatmaps
        heatmaps = []
        for heatmap_type, path in session.heatmap_paths.items():
            heatmaps.append({
                "type": heatmap_type,
                "url": f"/api/v1/stream/{session_id}/heatmap/{heatmap_type}"
            })
        return {"heatmaps": heatmaps}

    # Generate heatmaps
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create temp data file for visualizer
    temp_data = {
        "positions": session.foot_positions,
        "rallies": [],
        "metadata": {
            "court_boundary": session.court_boundary,
            "video_name": f"stream_{session_id}"
        }
    }

    temp_file = output_dir / "heatmap_data.json"
    with open(temp_file, 'w') as f:
        json.dump(temp_data, f)

    try:
        visualizer = HeatmapVisualizer(str(temp_file))
        saved_paths = visualizer.save_all_visualizations(str(output_dir))

        # Update session with heatmap paths
        session.heatmap_paths = saved_paths
        db.commit()

        heatmaps = []
        for heatmap_type in saved_paths.keys():
            heatmaps.append({
                "type": heatmap_type,
                "url": f"/api/v1/stream/{session_id}/heatmap/{heatmap_type}"
            })

        return {"heatmaps": heatmaps}
    except Exception as e:
        logger.error(f"Failed to generate heatmaps for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate heatmaps: {str(e)}")


@router.get("/{session_id}/heatmap/{heatmap_type}")
async def get_session_heatmap_image(
    session_id: int,
    heatmap_type: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific heatmap image for a stream session."""
    from pathlib import Path
    from fastapi.responses import FileResponse

    session = db.query(StreamSession).filter(
        StreamSession.id == session_id,
        StreamSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.heatmap_paths or heatmap_type not in session.heatmap_paths:
        raise HTTPException(status_code=404, detail="Heatmap not found")

    heatmap_path = Path(session.heatmap_paths[heatmap_type])
    if not heatmap_path.exists():
        raise HTTPException(status_code=404, detail="Heatmap file not found")

    return FileResponse(heatmap_path, media_type="image/png")


@router.delete("/{session_id}")
async def delete_session(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a stream session."""
    session = db.query(StreamSession).filter(
        StreamSession.id == session_id,
        StreamSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Don't allow deleting active sessions
    if session.status == StreamStatus.STREAMING:
        raise HTTPException(status_code=400, detail="Cannot delete an active streaming session. End it first.")

    # Clean up any stored files
    # TODO: Delete recording files if they exist

    db.delete(session)
    db.commit()

    return {"status": "deleted", "message": "Session deleted successfully"}


# WebSocket endpoints are added to main.py
