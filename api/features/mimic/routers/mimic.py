"""Mimic Challenge REST endpoints."""

import io
import logging
import shutil
import zipfile
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
from ..services.pose_similarity import generate_summary_feedback
from ..services.video_comparator import compare_video

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mimic", tags=["mimic"])

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def require_admin(user=Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def _build_challenge_response(
    ch: MimicChallenge, creator_username: str = None, creator_email: str = None
) -> MimicChallengeResponse:
    return MimicChallengeResponse(
        id=ch.id,
        title=ch.title,
        description=ch.description,
        created_by=ch.created_by,
        creator_username=creator_username,
        creator_email=creator_email,
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

    # Check file size (100MB limit)
    contents = await video.read()
    if len(contents) > 100 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Video file too large. Maximum size is 100MB."
        )
    await video.seek(0)

    # Check per-user challenge limit
    user_count = db.query(MimicChallenge).filter(
        MimicChallenge.created_by == user.id
    ).count()
    if user_count >= 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 challenges per user. Delete an existing challenge to upload a new one."
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
    from ....db_models.user import User

    q = db.query(MimicChallenge, User.username, User.email).options(
        defer(MimicChallenge.pose_timeline)
    ).outerjoin(User, MimicChallenge.created_by == User.id).filter(
        (MimicChallenge.is_public == True) | (MimicChallenge.created_by == user.id)
    )
    total = q.count()
    rows = q.order_by(MimicChallenge.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "challenges": [
            _build_challenge_response(ch, creator_username=uname, creator_email=email)
            for ch, uname, email in rows
        ],
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

    session.uploaded_video_path = video_path
    db.commit()

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
    storage = get_storage_service()
    challenge = db.query(MimicChallenge).options(
        defer(MimicChallenge.pose_timeline)
    ).filter(
        MimicChallenge.id == challenge_id
    ).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    # Check S3 first
    if challenge.thumbnail_s3_key and storage.is_s3():
        try:
            thumb_data = storage.outputs.load(challenge.thumbnail_s3_key)
            return Response(
                content=thumb_data,
                media_type="image/jpeg",
                headers={"Content-Disposition": f'inline; filename="mimic_{challenge_id}_thumb.jpg"'},
            )
        except Exception as e:
            logger.error(f"Failed to load mimic thumbnail from S3: {e}")

    # Check local
    if challenge.thumbnail_local_path and Path(challenge.thumbnail_local_path).exists():
        return FileResponse(
            path=challenge.thumbnail_local_path,
            media_type="image/jpeg",
            filename=f"mimic_{challenge_id}_thumb.jpg",
        )

    raise HTTPException(status_code=404, detail="Thumbnail not available")


@router.delete("/challenges/{challenge_id}")
def user_delete_challenge(
    challenge_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Delete a challenge owned by the current user."""
    challenge = db.query(MimicChallenge).filter(
        MimicChallenge.id == challenge_id,
        MimicChallenge.created_by == user.id,
    ).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found or not owned by you")

    _cleanup_challenge_files(challenge, db)

    # Delete associated sessions and records
    db.query(MimicSession).filter(MimicSession.challenge_id == challenge_id).delete()
    db.query(MimicRecord).filter(MimicRecord.challenge_id == challenge_id).delete()

    db.delete(challenge)
    db.commit()

    return {"detail": f"Challenge {challenge_id} deleted"}


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

    # Grab screenshots before ending session (which destroys the analyzer)
    screenshots = []
    analyzer_ref = gsm.get_session(session_id)
    if analyzer_ref and hasattr(analyzer_ref, 'get_screenshots'):
        screenshots = analyzer_ref.get_screenshots()

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

    # Save screenshots
    _save_mimic_screenshots(screenshots, session, user.id)

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
    # Defer frame_scores — it's huge JSON and causes MySQL sort buffer OOM
    q = db.query(MimicSession).options(
        defer(MimicSession.frame_scores)
    ).filter(
        MimicSession.user_id == user.id,
        MimicSession.status == MimicSessionStatus.ENDED,
    )
    if challenge_id:
        q = q.filter(MimicSession.challenge_id == challenge_id)

    total = q.count()
    sessions = q.order_by(MimicSession.created_at.desc()).offset(offset).limit(limit).all()

    # Batch-fetch challenge titles for display
    challenge_ids = {s.challenge_id for s in sessions}
    titles = {}
    if challenge_ids:
        for ch in db.query(
            MimicChallenge.id, MimicChallenge.title
        ).filter(MimicChallenge.id.in_(challenge_ids)).all():
            titles[ch.id] = ch.title

    results = []
    for s in sessions:
        record = db.query(MimicRecord).filter(
            MimicRecord.user_id == user.id,
            MimicRecord.challenge_id == s.challenge_id,
        ).first()
        resp = _build_session_response(s, record, include_frames=False)
        resp["challenge_title"] = titles.get(s.challenge_id)
        results.append(resp)

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


@router.post("/sessions/{session_id}/force-compare")
def force_compare(
    session_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Force comparison despite audio mismatch, using offset=0."""
    session = db.query(MimicSession).filter(
        MimicSession.id == session_id,
        MimicSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != MimicSessionStatus.AUDIO_MISMATCH:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not in audio_mismatch state (status: {session.status.value})"
        )

    if not session.uploaded_video_path:
        raise HTTPException(status_code=400, detail="No uploaded video found for this session")

    # Re-kick background comparison (will detect AUDIO_MISMATCH status and use offset=0)
    compare_video(session.challenge_id, session.uploaded_video_path, session.id)

    return {"session_id": session.id, "status": "processing"}


@router.get("/sessions/{session_id}/comparison-video")
def get_comparison_video(
    session_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Serve the side-by-side comparison video for an upload-to-compare session."""
    session = db.query(MimicSession).filter(
        MimicSession.id == session_id,
        MimicSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if (
        not session.comparison_video_path
        or not Path(session.comparison_video_path).exists()
    ):
        raise HTTPException(status_code=404, detail="Comparison video not available")

    return FileResponse(
        path=session.comparison_video_path,
        media_type="video/mp4",
        filename=f"comparison_{session_id}.mp4",
    )


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


@router.get("/admin/challenges")
def admin_list_challenges(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """List all challenges with creator info (admin only)."""
    from ....db_models.user import User

    q = db.query(MimicChallenge, User.username, User.email).options(
        defer(MimicChallenge.pose_timeline)
    ).outerjoin(User, MimicChallenge.created_by == User.id)

    total = q.count()
    rows = q.order_by(MimicChallenge.created_at.desc()).offset(offset).limit(limit).all()

    results = [
        _build_challenge_response(ch, creator_username=username, creator_email=email)
        for ch, username, email in rows
    ]

    return {"challenges": results, "total": total}


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


@router.put("/admin/challenges/{challenge_id}/public")
def toggle_public(
    challenge_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Toggle public visibility for a challenge (admin only)."""
    challenge = db.query(MimicChallenge).options(
        defer(MimicChallenge.pose_timeline)
    ).filter(
        MimicChallenge.id == challenge_id
    ).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    challenge.is_public = not challenge.is_public
    db.commit()

    return {"id": challenge.id, "is_public": challenge.is_public}


@router.delete("/admin/challenges/{challenge_id}")
def delete_challenge(
    challenge_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Delete a challenge and all associated sessions/records/files (admin only)."""
    challenge = db.query(MimicChallenge).filter(
        MimicChallenge.id == challenge_id
    ).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    _cleanup_challenge_files(challenge, db)

    # Delete associated sessions and records
    db.query(MimicSession).filter(MimicSession.challenge_id == challenge_id).delete()
    db.query(MimicRecord).filter(MimicRecord.challenge_id == challenge_id).delete()

    db.delete(challenge)
    db.commit()

    return {"detail": f"Challenge {challenge_id} deleted"}


@router.get("/admin/sessions")
def admin_list_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """List all mimic sessions with user info (admin only)."""
    from ....db_models.user import User

    q = db.query(MimicSession, User.username, User.email).options(
        defer(MimicSession.frame_scores)
    ).outerjoin(User, MimicSession.user_id == User.id)

    total = q.count()
    rows = q.order_by(MimicSession.created_at.desc()).offset(offset).limit(limit).all()

    # Batch-fetch challenge titles
    challenge_ids = {s.challenge_id for s, _, _ in rows}
    titles = {}
    if challenge_ids:
        for ch in db.query(
            MimicChallenge.id, MimicChallenge.title
        ).filter(MimicChallenge.id.in_(challenge_ids)).all():
            titles[ch.id] = ch.title

    results = []
    for sess, username, email in rows:
        results.append({
            "id": sess.id,
            "user_id": sess.user_id,
            "username": username,
            "email": email,
            "challenge_id": sess.challenge_id,
            "challenge_title": titles.get(sess.challenge_id),
            "source": sess.source or "live",
            "status": sess.status.value,
            "overall_score": sess.overall_score or 0,
            "duration_seconds": sess.duration_seconds or 0,
            "frames_compared": sess.frames_compared or 0,
            "has_screenshots": bool(sess.screenshots_s3_prefix),
            "screenshot_count": sess.screenshot_count or 0,
            "has_comparison_video": bool(
                sess.comparison_video_path and Path(sess.comparison_video_path).exists()
            ),
            "has_uploaded_video": bool(
                sess.uploaded_video_path and Path(sess.uploaded_video_path).exists()
            ),
            "created_at": (sess.created_at.isoformat() + "Z") if sess.created_at else None,
            "ended_at": (sess.ended_at.isoformat() + "Z") if sess.ended_at else None,
        })

    return {"sessions": results, "total": total}


@router.get("/admin/sessions/{session_id}/screenshots")
def admin_list_session_screenshots(
    session_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """List screenshot URLs for a mimic session (admin only)."""
    session = db.query(MimicSession).filter(MimicSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.screenshots_s3_prefix or not session.screenshot_count:
        return {"count": 0, "urls": []}

    urls = []
    for i in range(session.screenshot_count):
        urls.append(f"/api/v1/mimic/admin/sessions/{session_id}/screenshots/{i}")

    return {"count": session.screenshot_count, "urls": urls}


@router.get("/admin/sessions/{session_id}/screenshots/download")
def admin_download_session_screenshots(
    session_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Download all screenshots for a mimic session as a ZIP (admin only)."""
    session = db.query(MimicSession).filter(MimicSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.screenshots_s3_prefix or not session.screenshot_count:
        raise HTTPException(status_code=404, detail="No screenshots available")

    storage = get_storage_service()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for i in range(session.screenshot_count):
            key = f"{session.screenshots_s3_prefix}{i:04d}.jpg"
            try:
                data = storage.outputs.load(key)
                zf.writestr(f"screenshot_{i:04d}.jpg", data)
            except Exception as e:
                logger.warning(f"Missing screenshot {key}: {e}")

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="mimic_session_{session_id}_screenshots.zip"'
        },
    )


@router.get("/admin/sessions/{session_id}/screenshots/{index}")
def admin_get_session_screenshot(
    session_id: int,
    index: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Get a single screenshot by index for a mimic session (admin only)."""
    session = db.query(MimicSession).filter(MimicSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.screenshots_s3_prefix or index < 0 or index >= (session.screenshot_count or 0):
        raise HTTPException(status_code=404, detail="Screenshot not found")

    storage = get_storage_service()
    key = f"{session.screenshots_s3_prefix}{index:04d}.jpg"
    try:
        data = storage.outputs.load(key)
    except Exception:
        raise HTTPException(status_code=404, detail="Screenshot file not found")

    return Response(
        content=data,
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f'inline; filename="mimic_session_{session_id}_screenshot_{index:04d}.jpg"'
        },
    )


@router.get("/admin/sessions/{session_id}/comparison-video")
def admin_get_comparison_video(
    session_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Serve the comparison video for a mimic session (admin only)."""
    session = db.query(MimicSession).filter(MimicSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if (
        not session.comparison_video_path
        or not Path(session.comparison_video_path).exists()
    ):
        raise HTTPException(status_code=404, detail="Comparison video not available")

    return FileResponse(
        path=session.comparison_video_path,
        media_type="video/mp4",
        filename=f"comparison_{session_id}.mp4",
    )


@router.get("/admin/sessions/{session_id}/uploaded-video")
def admin_get_uploaded_video(
    session_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Serve the original uploaded video for a mimic session (admin only)."""
    session = db.query(MimicSession).filter(MimicSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if (
        not session.uploaded_video_path
        or not Path(session.uploaded_video_path).exists()
    ):
        raise HTTPException(status_code=404, detail="Uploaded video not available")

    return FileResponse(
        path=session.uploaded_video_path,
        media_type="video/mp4",
        filename=f"upload_{session_id}.mp4",
    )


@router.get("/admin/sessions/{session_id}/details")
def admin_get_session_details(
    session_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Get detailed scoring data for a mimic session (admin only)."""
    session = db.query(MimicSession).options(
        defer(MimicSession.frame_scores)
    ).filter(MimicSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    feedback = generate_summary_feedback(session.score_breakdown) if session.score_breakdown else None

    return {
        "id": session.id,
        "score_breakdown": session.score_breakdown,
        "overall_score": session.overall_score or 0,
        "feedback": feedback,
        "duration_seconds": session.duration_seconds or 0,
        "frames_compared": session.frames_compared or 0,
        "source": session.source or "live",
        "has_comparison_video": bool(
            session.comparison_video_path and Path(session.comparison_video_path).exists()
        ),
        "created_at": (session.created_at.isoformat() + "Z") if session.created_at else None,
        "ended_at": (session.ended_at.isoformat() + "Z") if session.ended_at else None,
    }


@router.get("/admin/sessions/{session_id}/frame-scores")
def admin_get_frame_scores(
    session_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Download per-frame scoring data for a mimic session (admin only)."""
    session = db.query(MimicSession).filter(
        MimicSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.frame_scores:
        raise HTTPException(status_code=404, detail="No frame score data available")

    return {
        "session_id": session.id,
        "overall_score": session.overall_score or 0,
        "frames_compared": session.frames_compared or 0,
        "duration_seconds": session.duration_seconds or 0,
        "frame_scores": session.frame_scores,
    }


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


def _save_mimic_screenshots(screenshots: list, session: MimicSession, user_id: int):
    """Save per-second annotated screenshots to storage."""
    if not screenshots:
        return
    storage = get_storage_service()
    prefix = f"mimic/{user_id}/session_{session.id}/screenshots/"
    for i, jpg_bytes in enumerate(screenshots):
        key = f"{prefix}{i:04d}.jpg"
        storage.outputs.save(key, jpg_bytes, content_type="image/jpeg")
    session.screenshots_s3_prefix = prefix
    session.screenshot_count = len(screenshots)
    logger.info(f"Saved {len(screenshots)} mimic screenshots for session {session.id}")


def _cleanup_challenge_files(challenge: MimicChallenge, db: Session):
    """Clean up local + S3 files for a challenge and its sessions."""
    storage = get_storage_service()

    # Clean up local files
    for path in (
        challenge.video_local_path,
        challenge.thumbnail_local_path,
        challenge.annotated_video_local_path,
    ):
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass

    # Clean up S3 challenge files
    if storage.is_s3():
        for key in (
            challenge.video_s3_key,
            challenge.thumbnail_s3_key,
            challenge.annotated_video_s3_key,
        ):
            if key:
                try:
                    storage.outputs.delete(key)
                except Exception as e:
                    logger.warning(f"Failed to delete S3 key {key}: {e}")

    # Clean up session screenshots from S3
    sessions = db.query(MimicSession).filter(
        MimicSession.challenge_id == challenge.id
    ).all()
    for sess in sessions:
        if sess.screenshots_s3_prefix and storage.is_s3():
            for i in range(sess.screenshot_count or 0):
                key = f"{sess.screenshots_s3_prefix}{i:04d}.jpg"
                try:
                    storage.outputs.delete(key)
                except Exception:
                    pass


def _build_session_response(
    session: MimicSession,
    record: Optional[MimicRecord] = None,
    include_frames: bool = True,
) -> dict:
    feedback = generate_summary_feedback(session.score_breakdown) if session.score_breakdown else None
    resp = {
        "id": session.id,
        "challenge_id": session.challenge_id,
        "source": session.source or "live",
        "status": session.status.value,
        "overall_score": session.overall_score or 0,
        "duration_seconds": session.duration_seconds or 0,
        "frames_compared": session.frames_compared or 0,
        "score_breakdown": session.score_breakdown,
        "frame_scores": session.frame_scores if include_frames else None,
        "feedback": feedback,
        "has_comparison_video": bool(
            session.comparison_video_path
            and Path(session.comparison_video_path).exists()
        ),
        "personal_best": record.best_score if record else None,
        "attempt_count": record.attempt_count if record else 0,
        "created_at": (session.created_at.isoformat() + "Z") if session.created_at else None,
        "ended_at": (session.ended_at.isoformat() + "Z") if session.ended_at else None,
    }
    if session.audio_confidence is not None:
        resp["audio_confidence"] = session.audio_confidence
    if session.audio_offset is not None:
        resp["audio_offset"] = session.audio_offset
    return resp
