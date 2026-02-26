"""Mimic Challenge REST endpoints."""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session, defer

from ....config import get_settings
from ....database import get_db
from ....routers.auth import get_current_user
from ....services.storage_service import get_storage_service
from ....core.streaming.session_manager import get_generic_session_manager
from ..db_models.mimic import (
    MimicChallenge, MimicSession, MimicRecord,
    MimicProcessingStatus, MimicSessionStatus,
)
from ..models.mimic import (
    MimicChallengeResponse, MimicSessionCreate, MimicSessionStart,
    MimicSessionResponse, MimicRecordResponse, MimicCompareStart,
)
from ..services.mimic_analyzer import MimicAnalyzer
from ..services.reference_processor import process_reference_video
from ..services.video_comparator import compare_video

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mimic", tags=["mimic"])

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def require_admin(user=Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def _build_challenge_response(ch: MimicChallenge) -> MimicChallengeResponse:
    return MimicChallengeResponse(
        id=ch.id,
        title=ch.title,
        description=ch.description,
        created_by=ch.created_by,
        video_duration=ch.video_duration,
        video_fps=ch.video_fps,
        total_frames=ch.total_frames or 0,
        processing_status=ch.processing_status.value,
        is_trending=ch.is_trending,
        is_public=ch.is_public,
        play_count=ch.play_count or 0,
        has_video=bool(ch.video_s3_key or ch.video_local_path),
        has_thumbnail=bool(ch.thumbnail_s3_key or ch.thumbnail_local_path),
        created_at=ch.created_at,
    )


# ---------- Challenge CRUD ----------


@router.post("/challenges", response_model=MimicChallengeResponse)
async def upload_challenge(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Upload a reference video and start background processing."""
    # Validate file extension
    ext = Path(video.filename or "").suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid video format. Allowed: {ALLOWED_VIDEO_EXTENSIONS}"
        )

    settings = get_settings()

    # Save video to local storage
    upload_dir = settings.output_path / str(user.id) / "mimic_challenges"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Create DB row first to get the ID
    challenge = MimicChallenge(
        title=title,
        description=description,
        created_by=user.id,
        processing_status=MimicProcessingStatus.PENDING,
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)

    video_filename = f"mimic_{challenge.id}{ext}"
    video_path = str(upload_dir / video_filename)

    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)

    challenge.video_local_path = video_path
    db.commit()

    # Kick off background processing
    process_reference_video(challenge.id)

    return _build_challenge_response(challenge)


@router.get("/challenges")
def list_challenges(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """List public challenges and user's own challenges."""
    q = db.query(MimicChallenge).options(
        defer(MimicChallenge.pose_timeline)
    ).filter(
        (MimicChallenge.is_public == True) | (MimicChallenge.created_by == user.id)
    )
    total = q.count()
    challenges = q.order_by(MimicChallenge.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "challenges": [_build_challenge_response(c) for c in challenges],
        "total": total,
    }


@router.get("/challenges/trending")
def list_trending_challenges(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """List admin-curated trending challenges."""
    challenges = db.query(MimicChallenge).options(
        defer(MimicChallenge.pose_timeline)
    ).filter(
        MimicChallenge.is_trending == True,
        MimicChallenge.processing_status == MimicProcessingStatus.READY,
    ).order_by(MimicChallenge.play_count.desc()).all()

    return [_build_challenge_response(c) for c in challenges]


@router.get("/challenges/{challenge_id}", response_model=MimicChallengeResponse)
def get_challenge(
    challenge_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get challenge details."""
    challenge = db.query(MimicChallenge).options(
        defer(MimicChallenge.pose_timeline)
    ).filter(
        MimicChallenge.id == challenge_id
    ).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return _build_challenge_response(challenge)


@router.get("/challenges/{challenge_id}/video")
def get_challenge_video(
    challenge_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Serve the reference video."""
    storage = get_storage_service()
    challenge = db.query(MimicChallenge).options(
        defer(MimicChallenge.pose_timeline)
    ).filter(
        MimicChallenge.id == challenge_id
    ).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    # Check S3 first
    if challenge.video_s3_key and storage.is_s3():
        try:
            video_data = storage.outputs.load(challenge.video_s3_key)
            return Response(
                content=video_data,
                media_type="video/mp4",
                headers={"Content-Disposition": f'inline; filename="mimic_{challenge_id}.mp4"'},
            )
        except Exception as e:
            logger.error(f"Failed to load mimic video from S3: {e}")

    # Check local
    if challenge.video_local_path and Path(challenge.video_local_path).exists():
        return FileResponse(
            path=challenge.video_local_path,
            media_type="video/mp4",
            filename=f"mimic_{challenge_id}.mp4",
        )

    raise HTTPException(status_code=404, detail="Video not available")


@router.post("/challenges/{challenge_id}/compare", response_model=MimicCompareStart)
async def compare_challenge(
    challenge_id: int,
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Upload a video to compare against a reference challenge offline."""
    challenge = db.query(MimicChallenge).options(
        defer(MimicChallenge.pose_timeline)
    ).filter(
        MimicChallenge.id == challenge_id
    ).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    if challenge.processing_status != MimicProcessingStatus.READY:
        raise HTTPException(
            status_code=400,
            detail=f"Challenge is not ready (status: {challenge.processing_status.value})"
        )

    # Validate file extension
    ext = Path(video.filename or "").suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid video format. Allowed: {ALLOWED_VIDEO_EXTENSIONS}"
        )

    # Create session
    session = MimicSession(
        user_id=user.id,
        challenge_id=challenge.id,
        source="upload",
        status=MimicSessionStatus.READY,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Increment play count
    challenge.play_count = (challenge.play_count or 0) + 1
    db.commit()

    # Save uploaded video
    settings = get_settings()
    upload_dir = settings.output_path / str(user.id) / "mimic_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    video_path = str(upload_dir / f"compare_{session.id}{ext}")

    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)

    # Kick off background comparison
    compare_video(challenge.id, video_path, session.id)

    return MimicCompareStart(session_id=session.id, status="processing")


@router.get("/challenges/{challenge_id}/thumbnail")
def get_challenge_thumbnail(
    challenge_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Serve the challenge thumbnail."""
    challenge = db.query(MimicChallenge).options(
        defer(MimicChallenge.pose_timeline)
    ).filter(
        MimicChallenge.id == challenge_id
    ).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    if challenge.thumbnail_local_path and Path(challenge.thumbnail_local_path).exists():
        return FileResponse(
            path=challenge.thumbnail_local_path,
            media_type="image/jpeg",
            filename=f"mimic_{challenge_id}_thumb.jpg",
        )

    raise HTTPException(status_code=404, detail="Thumbnail not available")


# ---------- Sessions ----------


@router.post("/sessions", response_model=MimicSessionStart)
def create_mimic_session(
    body: MimicSessionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a mimic session and register the analyzer."""
    challenge = db.query(MimicChallenge).filter(
        MimicChallenge.id == body.challenge_id
    ).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    if challenge.processing_status != MimicProcessingStatus.READY:
        raise HTTPException(
            status_code=400,
            detail=f"Challenge is not ready (status: {challenge.processing_status.value})"
        )

    session = MimicSession(
        user_id=user.id,
        challenge_id=challenge.id,
        status=MimicSessionStatus.READY,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Increment play count
    challenge.play_count = (challenge.play_count or 0) + 1
    db.commit()

    # Create analyzer with reference data
    analyzer = MimicAnalyzer(
        reference_timeline=challenge.pose_timeline or [],
        reference_fps=challenge.video_fps or 30.0,
        reference_duration=challenge.video_duration or 1.0,
    )

    gsm = get_generic_session_manager()
    gsm.register_session(session.id, "mimic", analyzer)

    return MimicSessionStart(
        session_id=session.id,
        challenge_id=challenge.id,
        ws_url=f"/ws/mimic/{session.id}",
        reference_duration=challenge.video_duration,
        reference_fps=challenge.video_fps,
    )


@router.post("/sessions/{session_id}/end")
def end_mimic_session(
    session_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """End a mimic session and persist scores."""
    session = db.query(MimicSession).filter(
        MimicSession.id == session_id,
        MimicSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == MimicSessionStatus.ENDED:
        record = db.query(MimicRecord).filter(
            MimicRecord.user_id == user.id,
            MimicRecord.challenge_id == session.challenge_id,
        ).first()
        return _build_session_response(session, record)

    gsm = get_generic_session_manager()
    report = gsm.end_session(session_id) or {}

    session.status = MimicSessionStatus.ENDED
    session.ended_at = datetime.utcnow()
    session.overall_score = report.get("overall_score", 0)
    session.duration_seconds = report.get("duration_seconds", 0)
    session.frames_compared = report.get("frames_compared", 0)
    session.score_breakdown = report.get("score_breakdown")
    session.frame_scores = report.get("frame_scores")

    # Update personal best
    record = db.query(MimicRecord).filter(
        MimicRecord.user_id == user.id,
        MimicRecord.challenge_id == session.challenge_id,
    ).first()

    if record:
        record.attempt_count += 1
        if session.overall_score > record.best_score:
            record.best_score = session.overall_score
    else:
        record = MimicRecord(
            user_id=user.id,
            challenge_id=session.challenge_id,
            best_score=session.overall_score,
            attempt_count=1,
        )
        db.add(record)

    db.commit()
    db.refresh(session)

    return _build_session_response(session, record)


@router.get("/sessions")
def list_mimic_sessions(
    challenge_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """List past mimic sessions for the current user."""
    q = db.query(MimicSession).filter(
        MimicSession.user_id == user.id,
        MimicSession.status == MimicSessionStatus.ENDED,
    )
    if challenge_id:
        q = q.filter(MimicSession.challenge_id == challenge_id)

    total = q.count()
    sessions = q.order_by(MimicSession.created_at.desc()).offset(offset).limit(limit).all()

    results = []
    for s in sessions:
        record = db.query(MimicRecord).filter(
            MimicRecord.user_id == user.id,
            MimicRecord.challenge_id == s.challenge_id,
        ).first()
        results.append(_build_session_response(s, record))

    return {"sessions": results, "total": total}


@router.get("/sessions/{session_id}")
def get_mimic_session(
    session_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get details for a specific mimic session."""
    session = db.query(MimicSession).filter(
        MimicSession.id == session_id,
        MimicSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    record = db.query(MimicRecord).filter(
        MimicRecord.user_id == user.id,
        MimicRecord.challenge_id == session.challenge_id,
    ).first()

    challenge = db.query(MimicChallenge).filter(
        MimicChallenge.id == session.challenge_id
    ).first()

    resp = _build_session_response(session, record)
    if challenge:
        resp["challenge_title"] = challenge.title

    return resp


@router.get("/records")
def get_mimic_records(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get personal best records for all mimic challenges."""
    records = db.query(MimicRecord).filter(
        MimicRecord.user_id == user.id
    ).all()

    return [
        {
            "challenge_id": r.challenge_id,
            "best_score": r.best_score,
            "attempt_count": r.attempt_count,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in records
    ]


# ---------- Admin endpoints ----------


@router.put("/admin/challenges/{challenge_id}/trending")
def toggle_trending(
    challenge_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Toggle trending status for a challenge (admin only)."""
    challenge = db.query(MimicChallenge).options(
        defer(MimicChallenge.pose_timeline)
    ).filter(
        MimicChallenge.id == challenge_id
    ).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    challenge.is_trending = not challenge.is_trending
    db.commit()

    return {"id": challenge.id, "is_trending": challenge.is_trending}


@router.get("/admin/challenges/{challenge_id}/annotated-video")
def get_annotated_video(
    challenge_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Download the annotated reference video with skeleton overlay (admin only)."""
    challenge = db.query(MimicChallenge).options(
        defer(MimicChallenge.pose_timeline)
    ).filter(
        MimicChallenge.id == challenge_id
    ).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    # Check S3 first
    if challenge.annotated_video_s3_key:
        storage = get_storage_service()
        if storage.is_s3():
            try:
                video_data = storage.outputs.load(challenge.annotated_video_s3_key)
                return Response(
                    content=video_data,
                    media_type="video/mp4",
                    headers={
                        "Content-Disposition": f'attachment; filename="mimic_{challenge_id}_annotated.mp4"'
                    },
                )
            except Exception as e:
                logger.error(f"Failed to load annotated video from S3: {e}")

    # Check local
    if challenge.annotated_video_local_path and Path(challenge.annotated_video_local_path).exists():
        return FileResponse(
            path=challenge.annotated_video_local_path,
            media_type="video/mp4",
            filename=f"mimic_{challenge_id}_annotated.mp4",
        )

    raise HTTPException(status_code=404, detail="Annotated video not available")


# ---------- Helpers ----------


def _build_session_response(session: MimicSession, record: Optional[MimicRecord] = None) -> dict:
    return {
        "id": session.id,
        "challenge_id": session.challenge_id,
        "status": session.status.value,
        "overall_score": session.overall_score or 0,
        "duration_seconds": session.duration_seconds or 0,
        "frames_compared": session.frames_compared or 0,
        "score_breakdown": session.score_breakdown,
        "frame_scores": session.frame_scores,
        "personal_best": record.best_score if record else None,
        "attempt_count": record.attempt_count if record else 0,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
    }
