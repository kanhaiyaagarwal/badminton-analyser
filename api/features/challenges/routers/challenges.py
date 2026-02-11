"""Challenges REST endpoints — create, list, end, and recording."""

import cv2
import numpy as np
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy.orm import Session

from ....config import get_settings
from ....database import get_db
from ....db_models.user import User
from ....routers.auth import get_current_user
from ....services.storage_service import get_storage_service
from ..db_models.challenge import ChallengeSession, ChallengeRecord, ChallengeStatus, ChallengeConfig
from ..models.challenge import (
    ChallengeCreate, ChallengeResponse, ChallengeSessionStart,
    ChallengeConfigResponse, ChallengeConfigUpdate, AdminSessionResponse,
)
from ..services.rep_counter import CHALLENGE_DEFAULTS
from ..services.plank_analyzer import PlankAnalyzer
from ..services.squat_analyzer import SquatAnalyzer
from ..services.pushup_analyzer import PushupAnalyzer
from ....core.streaming.session_manager import get_generic_session_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/challenges", tags=["challenges"])

VALID_TYPES = {"plank", "squat", "pushup"}

ANALYZER_MAP = {
    "plank": PlankAnalyzer,
    "squat": SquatAnalyzer,
    "pushup": PushupAnalyzer,
}


def require_admin(user=Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def _has_recording(session: ChallengeSession) -> bool:
    return bool(session.recording_s3_key or session.recording_local_path)


def _build_response(session: ChallengeSession, personal_best=None) -> ChallengeResponse:
    return ChallengeResponse(
        id=session.id,
        challenge_type=session.challenge_type,
        status=session.status.value,
        score=session.score,
        duration_seconds=session.duration_seconds,
        personal_best=personal_best,
        has_recording=_has_recording(session),
        created_at=session.created_at,
        ended_at=session.ended_at,
    )


def _save_recording(frames: list, session: ChallengeSession, user_id: int):
    """Encode recorded frames to MP4 and persist to S3 or local storage."""
    if not frames:
        return

    settings = get_settings()
    storage = get_storage_service()

    output_dir = settings.output_path / str(user_id) / f"challenge_{session.id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    video_path = str(output_dir / "recording.mp4")

    try:
        first_frame = cv2.imdecode(np.frombuffer(frames[0], np.uint8), cv2.IMREAD_COLOR)
        height, width = first_frame.shape[:2]

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 10
        out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

        for frame_data in frames:
            frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                out.write(frame)
        out.release()

        if storage.is_s3():
            try:
                s3_key = f"challenges/{user_id}/challenge_{session.id}/recording.mp4"
                with open(video_path, 'rb') as f:
                    storage.outputs.save(s3_key, f, content_type='video/mp4')
                session.recording_s3_key = s3_key
                Path(video_path).unlink(missing_ok=True)
            except Exception as e:
                logger.error(f"Failed to upload challenge recording to S3: {e}")
                session.recording_local_path = video_path
        else:
            session.recording_local_path = video_path

    except Exception as e:
        logger.error(f"Failed to create challenge recording: {e}")


@router.post("/sessions", response_model=ChallengeSessionStart)
def create_challenge_session(
    body: ChallengeCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a new challenge session and return a WebSocket URL."""
    if body.challenge_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid challenge type. Must be one of: {VALID_TYPES}")

    session = ChallengeSession(
        user_id=user.id,
        challenge_type=body.challenge_type,
        status=ChallengeStatus.READY,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create analyzer and register with generic session manager
    analyzer_cls = ANALYZER_MAP[body.challenge_type]
    config_row = db.query(ChallengeConfig).filter(
        ChallengeConfig.challenge_type == body.challenge_type
    ).first()
    analyzer = analyzer_cls(config=config_row.thresholds if config_row else None)
    gsm = get_generic_session_manager()
    gsm.register_session(session.id, f"challenge_{body.challenge_type}", analyzer)

    return ChallengeSessionStart(
        session_id=session.id,
        challenge_type=body.challenge_type,
        ws_url=f"/ws/challenge/{session.id}",
    )


@router.post("/sessions/{session_id}/end", response_model=ChallengeResponse)
def end_challenge_session(
    session_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """End a challenge session and persist the results."""
    session = db.query(ChallengeSession).filter(
        ChallengeSession.id == session_id,
        ChallengeSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    gsm = get_generic_session_manager()

    # Auto-save recording if still active
    analyzer = gsm.get_session(session_id)
    if analyzer and getattr(analyzer, 'is_recording', False):
        frames = analyzer.stop_recording()
        _save_recording(frames, session, user.id)
        session.is_recording = False

    report = gsm.end_session(session_id) or {}

    session.status = ChallengeStatus.ENDED
    session.ended_at = datetime.utcnow()
    session.score = report.get("score", 0)
    session.duration_seconds = report.get("duration_seconds", 0.0)
    session.extra_data = report

    # Update personal best
    record = db.query(ChallengeRecord).filter(
        ChallengeRecord.user_id == user.id,
        ChallengeRecord.challenge_type == session.challenge_type,
    ).first()

    personal_best = None
    if record:
        if session.score > record.best_score:
            record.best_score = session.score
        personal_best = record.best_score
    else:
        record = ChallengeRecord(
            user_id=user.id,
            challenge_type=session.challenge_type,
            best_score=session.score,
        )
        db.add(record)
        personal_best = session.score

    db.commit()
    db.refresh(session)

    return _build_response(session, personal_best)


# ---------- Recording endpoints ----------


@router.post("/sessions/{session_id}/recording/start")
def start_recording(
    session_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Start recording the challenge session."""
    session = db.query(ChallengeSession).filter(
        ChallengeSession.id == session_id,
        ChallengeSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    gsm = get_generic_session_manager()
    analyzer = gsm.get_session(session_id)
    if not analyzer:
        raise HTTPException(status_code=400, detail="Session analyzer not found")

    analyzer.start_recording()
    session.is_recording = True
    db.commit()

    return {"recording": True, "message": "Recording started"}


@router.post("/sessions/{session_id}/recording/stop")
def stop_recording(
    session_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Stop recording and save the video."""
    session = db.query(ChallengeSession).filter(
        ChallengeSession.id == session_id,
        ChallengeSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    gsm = get_generic_session_manager()
    analyzer = gsm.get_session(session_id)

    if not analyzer:
        if _has_recording(session):
            return {"recording": False, "message": "Recording already saved", "has_video": True}
        raise HTTPException(status_code=400, detail="Session not active")

    frames = analyzer.stop_recording()
    session.is_recording = False

    _save_recording(frames, session, user.id)

    db.commit()

    return {
        "recording": False,
        "message": "Recording stopped and saved" if _has_recording(session) else "Recording stopped",
        "frame_count": len(frames),
        "has_video": _has_recording(session),
    }


@router.get("/sessions/{session_id}/recording")
def download_recording(
    session_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Download the recorded video for a challenge session."""
    storage = get_storage_service()

    session = db.query(ChallengeSession).filter(
        ChallengeSession.id == session_id,
        ChallengeSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    filename = f"challenge_recording_{session_id}.mp4"

    # Check S3 first
    if session.recording_s3_key and storage.is_s3():
        try:
            video_data = storage.outputs.load(session.recording_s3_key)
            return Response(
                content=video_data,
                media_type="video/mp4",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except Exception as e:
            logger.error(f"Failed to load challenge recording from S3: {e}")

    # Check local file
    if session.recording_local_path:
        video_path = Path(session.recording_local_path)
        if video_path.exists():
            return FileResponse(path=str(video_path), media_type="video/mp4", filename=filename)

    raise HTTPException(status_code=404, detail="No recording available for this session")


@router.get("/sessions", response_model=List[ChallengeResponse])
def list_challenge_sessions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """List all challenge sessions for the current user."""
    sessions = (
        db.query(ChallengeSession)
        .filter(ChallengeSession.user_id == user.id)
        .order_by(ChallengeSession.created_at.desc())
        .limit(50)
        .all()
    )

    results = []
    for s in sessions:
        # Look up personal best
        record = db.query(ChallengeRecord).filter(
            ChallengeRecord.user_id == user.id,
            ChallengeRecord.challenge_type == s.challenge_type,
        ).first()

        results.append(_build_response(s, record.best_score if record else None))

    return results


@router.get("/records")
def get_personal_records(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get personal best records for all challenge types."""
    records = db.query(ChallengeRecord).filter(
        ChallengeRecord.user_id == user.id
    ).all()

    return {r.challenge_type: r.best_score for r in records}


# ---------- Admin endpoints ----------


@router.get("/admin/sessions", response_model=List[AdminSessionResponse])
def admin_list_sessions(
    challenge_type: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """List all challenge sessions (admin only)."""
    q = db.query(ChallengeSession, User.username).join(
        User, User.id == ChallengeSession.user_id
    )
    if challenge_type:
        q = q.filter(ChallengeSession.challenge_type == challenge_type)
    if user_id:
        q = q.filter(ChallengeSession.user_id == user_id)
    rows = q.order_by(ChallengeSession.created_at.desc()).limit(200).all()

    results = []
    for session, username in rows:
        extra = session.extra_data or {}
        results.append(AdminSessionResponse(
            id=session.id,
            user_id=session.user_id,
            username=username,
            challenge_type=session.challenge_type,
            status=session.status.value,
            score=session.score,
            duration_seconds=session.duration_seconds,
            has_pose_data=bool(extra.get("frame_timeline")),
            has_recording=_has_recording(session),
            created_at=session.created_at,
            ended_at=session.ended_at,
        ))
    return results


@router.get("/admin/sessions/{session_id}/pose-data")
def admin_get_pose_data(
    session_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Download per-frame pose data for a session (admin only)."""
    session = db.query(ChallengeSession).filter(
        ChallengeSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    extra = session.extra_data or {}
    timeline = extra.get("frame_timeline")
    if not timeline:
        raise HTTPException(status_code=404, detail="No pose data available for this session")

    return JSONResponse(content={
        "session_id": session.id,
        "challenge_type": session.challenge_type,
        "score": session.score,
        "duration_seconds": session.duration_seconds,
        "frame_count": len(timeline),
        "frame_timeline": timeline,
    })


@router.get("/admin/config")
def admin_get_config(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Get all challenge configs, filling in defaults for missing types."""
    rows = db.query(ChallengeConfig).all()
    saved = {r.challenge_type: r for r in rows}

    result = {}
    for ctype, defaults in CHALLENGE_DEFAULTS.items():
        if ctype in saved:
            row = saved[ctype]
            result[ctype] = {
                "thresholds": row.thresholds,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "is_custom": True,
            }
        else:
            result[ctype] = {
                "thresholds": defaults,
                "updated_at": None,
                "is_custom": False,
            }
    return result


@router.put("/admin/config/{challenge_type}")
def admin_update_config(
    challenge_type: str,
    body: ChallengeConfigUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Upsert thresholds for a challenge type (admin only)."""
    if challenge_type not in CHALLENGE_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"Invalid challenge type. Must be one of: {list(CHALLENGE_DEFAULTS.keys())}")

    row = db.query(ChallengeConfig).filter(
        ChallengeConfig.challenge_type == challenge_type
    ).first()
    if row:
        row.thresholds = body.thresholds
    else:
        row = ChallengeConfig(
            challenge_type=challenge_type,
            thresholds=body.thresholds,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return {"challenge_type": row.challenge_type, "thresholds": row.thresholds, "updated_at": row.updated_at.isoformat()}


@router.post("/admin/config/{challenge_type}/reset")
def admin_reset_config(
    challenge_type: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Delete config row to revert to defaults (admin only)."""
    if challenge_type not in CHALLENGE_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"Invalid challenge type. Must be one of: {list(CHALLENGE_DEFAULTS.keys())}")

    row = db.query(ChallengeConfig).filter(
        ChallengeConfig.challenge_type == challenge_type
    ).first()
    if row:
        db.delete(row)
        db.commit()
    return {"challenge_type": challenge_type, "thresholds": CHALLENGE_DEFAULTS[challenge_type], "is_custom": False}
