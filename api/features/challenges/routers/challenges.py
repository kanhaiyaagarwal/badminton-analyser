"""Challenges REST endpoints — create, list, end, and recording."""

import cv2
import numpy as np
import logging
import shutil
import subprocess
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session, defer

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


def _anonymize_email(email: str) -> str:
    """Mask email for leaderboard display: show first 3 chars of local part."""
    local, domain = email.rsplit("@", 1)
    visible = min(3, len(local))
    return f"{local[:visible]}***@{domain}"


def _anonymize_username(name: str) -> str:
    """Mask username: show first 3 chars, hide the rest."""
    if len(name) <= 3:
        return name
    return f"{name[:3]}***"


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


def _build_response(session: ChallengeSession, personal_best=None, daily_rank=None) -> ChallengeResponse:
    return ChallengeResponse(
        id=session.id,
        challenge_type=session.challenge_type,
        status=session.status.value,
        score=session.score,
        duration_seconds=session.duration_seconds,
        personal_best=personal_best,
        daily_rank=daily_rank,
        has_recording=_has_recording(session),
        created_at=session.created_at,
        ended_at=session.ended_at,
    )


def _compute_daily_rank(db: Session, user_id: int, challenge_type: str) -> Optional[int]:
    """Compute the user's rank on today's leaderboard for a challenge type."""
    day_start = datetime.combine(date.today(), datetime.min.time())
    rows = (
        db.query(
            ChallengeSession.user_id,
            sa_func.max(ChallengeSession.score).label("best_score"),
        )
        .filter(
            ChallengeSession.status == ChallengeStatus.ENDED,
            ChallengeSession.challenge_type == challenge_type,
            ChallengeSession.created_at >= day_start,
            ChallengeSession.score > 0,
        )
        .group_by(ChallengeSession.user_id)
        .order_by(sa_func.max(ChallengeSession.score).desc())
        .all()
    )
    for idx, row in enumerate(rows, start=1):
        if row.user_id == user_id:
            return idx
    return None


def _save_recording(frames: list, session: ChallengeSession, user_id: int):
    """Encode recorded frames to H.264 MP4 and persist to S3 or local storage."""
    if not frames:
        return

    settings = get_settings()
    storage = get_storage_service()

    output_dir = settings.output_path / str(user_id) / f"challenge_{session.id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = str(output_dir / "recording_raw.mp4")
    video_path = str(output_dir / "recording.mp4")

    try:
        first_frame = cv2.imdecode(np.frombuffer(frames[0], np.uint8), cv2.IMREAD_COLOR)
        height, width = first_frame.shape[:2]

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 10
        out = cv2.VideoWriter(raw_path, fourcc, fps, (width, height))

        for frame_data in frames:
            frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                out.write(frame)
        out.release()

        # Re-encode to H.264 with faststart for browser/mobile playback
        if shutil.which("ffmpeg"):
            result = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", raw_path,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "28",
                    "-movflags", "+faststart",
                    "-pix_fmt", "yuv420p",
                    video_path,
                ],
                capture_output=True, timeout=120,
            )
            Path(raw_path).unlink(missing_ok=True)
            if result.returncode != 0:
                logger.warning(f"ffmpeg re-encode failed: {result.stderr[:500]}")
                # Fallback: use the raw mp4v file
                Path(raw_path).touch()  # may already be deleted
                if not Path(video_path).exists():
                    video_path = raw_path
        else:
            # No ffmpeg available — use raw mp4v file directly
            logger.warning("ffmpeg not found, saving raw mp4v recording")
            Path(raw_path).rename(video_path)

        if not Path(video_path).exists():
            logger.error("Recording file not produced")
            return

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
        # Clean up partial files
        Path(raw_path).unlink(missing_ok=True)


def _save_screenshots(screenshots: List[bytes], session: ChallengeSession, user_id: int):
    """Save per-second annotated screenshots to S3."""
    if not screenshots:
        return
    storage = get_storage_service()
    prefix = f"challenges/{user_id}/challenge_{session.id}/screenshots/"
    for i, jpg_bytes in enumerate(screenshots):
        key = f"{prefix}{i:04d}.jpg"
        storage.outputs.save(key, jpg_bytes, content_type="image/jpeg")
    session.screenshots_s3_prefix = prefix
    session.screenshot_count = len(screenshots)
    logger.info(f"Saved {len(screenshots)} screenshots for session {session.id}")


@router.get("/enabled")
def get_enabled_challenges(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Return challenge types available to this user based on FeatureAccess modes.

    - global: available to everyone
    - per_user: available only if in user.enabled_features
    - disabled: hidden from non-admins
    Admins see all challenge types regardless.
    """
    from ....db_models.feature_access import FeatureAccess

    if user.is_admin:
        return list(VALID_TYPES)

    rows = db.query(FeatureAccess).filter(
        FeatureAccess.feature_name.in_(VALID_TYPES)
    ).all()
    access_map = {r.feature_name: r.access_mode for r in rows}
    user_features = set(user.enabled_features or [])

    enabled = []
    for ct in VALID_TYPES:
        mode = access_map.get(ct, "per_user")
        if mode == "global":
            enabled.append(ct)
        elif mode == "per_user" and ct in user_features:
            enabled.append(ct)
    return enabled


@router.post("/sessions", response_model=ChallengeSessionStart)
def create_challenge_session(
    body: ChallengeCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a new challenge session and return a WebSocket URL."""
    from ....db_models.feature_access import FeatureAccess

    if body.challenge_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid challenge type. Must be one of: {VALID_TYPES}")

    # Check access via FeatureAccess
    if not user.is_admin:
        fa = db.query(FeatureAccess).filter(
            FeatureAccess.feature_name == body.challenge_type
        ).first()
        mode = fa.access_mode if fa else "per_user"

        if mode == "disabled":
            raise HTTPException(status_code=403, detail="This challenge type is not currently enabled")
        if mode == "per_user":
            user_features = user.enabled_features or []
            if body.challenge_type not in user_features:
                raise HTTPException(status_code=403, detail="This challenge type is not enabled for your account")

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

    # If already ended (e.g. by WebSocket disconnect handler), return existing data
    if session.status == ChallengeStatus.ENDED:
        record = db.query(ChallengeRecord).filter(
            ChallengeRecord.user_id == user.id,
            ChallengeRecord.challenge_type == session.challenge_type,
        ).first()
        daily_rank = _compute_daily_rank(db, user.id, session.challenge_type)
        return _build_response(session, record.best_score if record else session.score, daily_rank=daily_rank)

    gsm = get_generic_session_manager()
    analyzer = gsm.get_session(session_id)

    # Grab screenshots before ending session (end_session pops the analyzer)
    screenshots = []
    if analyzer:
        screenshots = analyzer.get_screenshots()

    # Auto-save recording if still active
    if analyzer and getattr(analyzer, 'is_recording', False):
        frames = analyzer.stop_recording()
        _save_recording(frames, session, user.id)
        session.is_recording = False

    report = gsm.end_session(session_id) or {}

    # Save per-second screenshots
    _save_screenshots(screenshots, session, user.id)

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

    daily_rank = _compute_daily_rank(db, user.id, session.challenge_type)
    return _build_response(session, personal_best, daily_rank=daily_rank)


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
    challenge_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """List completed challenge sessions for the current user."""
    q = (
        db.query(ChallengeSession)
        .options(defer(ChallengeSession.extra_data))
        .filter(
            ChallengeSession.user_id == user.id,
            ChallengeSession.status == ChallengeStatus.ENDED,
        )
    )
    if challenge_type and challenge_type in VALID_TYPES:
        q = q.filter(ChallengeSession.challenge_type == challenge_type)
    sessions = q.order_by(ChallengeSession.created_at.desc()).limit(50).all()

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


@router.get("/stats")
def get_challenge_stats(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Get aggregated stats per challenge type for the current user.

    Returns for each type:
    - personal_best: highest single-session score ever
    - weekly_total: sum of scores this week (Monday–Sunday)
    - daily_best: highest single-session score today
    """
    # Personal bests
    records = db.query(ChallengeRecord).filter(
        ChallengeRecord.user_id == user.id
    ).all()
    pb_map = {r.challenge_type: r.best_score for r in records}

    # Week start (Monday 00:00)
    today = date.today()
    monday = today - timedelta(days=today.weekday())  # weekday(): Mon=0
    week_start = datetime.combine(monday, datetime.min.time())

    # Day start (today 00:00)
    day_start = datetime.combine(today, datetime.min.time())

    # Weekly totals per type
    weekly_rows = (
        db.query(
            ChallengeSession.challenge_type,
            sa_func.sum(ChallengeSession.score).label("total"),
        )
        .filter(
            ChallengeSession.user_id == user.id,
            ChallengeSession.status == ChallengeStatus.ENDED,
            ChallengeSession.created_at >= week_start,
        )
        .group_by(ChallengeSession.challenge_type)
        .all()
    )
    weekly_map = {row.challenge_type: int(row.total or 0) for row in weekly_rows}

    # Daily best per type
    daily_rows = (
        db.query(
            ChallengeSession.challenge_type,
            sa_func.max(ChallengeSession.score).label("best"),
        )
        .filter(
            ChallengeSession.user_id == user.id,
            ChallengeSession.status == ChallengeStatus.ENDED,
            ChallengeSession.created_at >= day_start,
        )
        .group_by(ChallengeSession.challenge_type)
        .all()
    )
    daily_map = {row.challenge_type: int(row.best or 0) for row in daily_rows}

    result = {}
    for ctype in VALID_TYPES:
        result[ctype] = {
            "personal_best": pb_map.get(ctype, 0),
            "weekly_total": weekly_map.get(ctype, 0),
            "daily_best": daily_map.get(ctype, 0),
        }
    return result


@router.get("/leaderboard")
def get_leaderboard(
    challenge_type: str = Query("pushup"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Get daily and weekly leaderboards for a challenge type.

    Returns top 3 entries plus the current user's rank for both periods.
    Emails are anonymized for other users.
    """
    if challenge_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid challenge type. Must be one of: {VALID_TYPES}")

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    day_start = datetime.combine(today, datetime.min.time())
    week_start = datetime.combine(monday, datetime.min.time())

    def _build_board(since: datetime):
        """Build leaderboard entries and user rank for a time period."""
        # Subquery: best score per user in the period
        rows = (
            db.query(
                ChallengeSession.user_id,
                sa_func.max(ChallengeSession.score).label("best_score"),
            )
            .filter(
                ChallengeSession.status == ChallengeStatus.ENDED,
                ChallengeSession.challenge_type == challenge_type,
                ChallengeSession.created_at >= since,
                ChallengeSession.score > 0,
            )
            .group_by(ChallengeSession.user_id)
            .order_by(sa_func.max(ChallengeSession.score).desc())
            .all()
        )

        # Build ranked list
        ranked = []
        user_rank = None
        for idx, row in enumerate(rows, start=1):
            u = db.query(User).filter(User.id == row.user_id).first()
            if not u:
                continue
            is_self = u.id == user.id
            ranked.append({
                "rank": idx,
                "username": u.username if is_self else _anonymize_username(u.username),
                "email": u.email if is_self else _anonymize_email(u.email),
                "score": int(row.best_score),
                "is_self": is_self,
            })
            if is_self:
                user_rank = idx

        # Return top 3 entries
        top = ranked[:3]

        # If user is outside top 3, append their entry
        if user_rank and user_rank > 3:
            user_entry = next(e for e in ranked if e["is_self"])
            top.append(user_entry)

        return {"entries": top, "user_rank": user_rank}

    return {
        "challenge_type": challenge_type,
        "daily": _build_board(day_start),
        "weekly": _build_board(week_start),
    }


# ---------- Admin endpoints ----------


@router.get("/admin/sessions")
def admin_list_sessions(
    challenge_type: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """List all challenge sessions with pagination (admin only)."""
    q = db.query(ChallengeSession, User.username).options(
        defer(ChallengeSession.extra_data)
    ).join(
        User, User.id == ChallengeSession.user_id
    )
    if challenge_type:
        q = q.filter(ChallengeSession.challenge_type == challenge_type)
    if user_id:
        q = q.filter(ChallengeSession.user_id == user_id)

    total = q.count()
    rows = q.order_by(ChallengeSession.created_at.desc()).offset(skip).limit(limit).all()

    sessions = []
    for session, username in rows:
        extra = session.extra_data or {}
        sessions.append(AdminSessionResponse(
            id=session.id,
            user_id=session.user_id,
            username=username,
            challenge_type=session.challenge_type,
            status=session.status.value,
            score=session.score,
            duration_seconds=session.duration_seconds,
            has_pose_data=bool(extra.get("frame_timeline")),
            has_recording=_has_recording(session),
            has_screenshots=bool(session.screenshots_s3_prefix),
            screenshot_count=session.screenshot_count or 0,
            created_at=session.created_at,
            ended_at=session.ended_at,
        ))
    return {"sessions": sessions, "total": total, "skip": skip, "limit": limit}


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


@router.get("/admin/sessions/{session_id}/pose-data/refined")
def admin_get_refined_pose_data(
    session_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """
    Refined pose data: full frames for first 2 and last 3 reps,
    summary only for reps in between. Original data is untouched.
    """
    session = db.query(ChallengeSession).filter(
        ChallengeSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    extra = session.extra_data or {}
    timeline = extra.get("frame_timeline")
    if not timeline:
        raise HTTPException(status_code=404, detail="No pose data available for this session")

    # Group frames by rep number (reps field = cumulative count)
    # Rep boundaries: when reps field increments
    rep_groups = {}  # rep_number -> list of frames
    pre_rep_frames = []  # frames before first rep (setup/ready)
    for frame in timeline:
        rep_num = frame.get("reps", 0)
        if rep_num == 0:
            pre_rep_frames.append(frame)
        else:
            rep_groups.setdefault(rep_num, []).append(frame)

    total_reps = max(rep_groups.keys()) if rep_groups else 0
    first_n = 2
    last_n = 3

    # Determine which reps get full data vs summary
    if total_reps <= first_n + last_n:
        # Few enough reps — include all full
        full_rep_nums = set(rep_groups.keys())
        summary_rep_nums = set()
    else:
        full_rep_nums = set(range(1, first_n + 1)) | set(range(total_reps - last_n + 1, total_reps + 1))
        summary_rep_nums = set(rep_groups.keys()) - full_rep_nums

    refined = []

    # Pre-rep phase (setup — before first rep): include full frame data
    if pre_rep_frames:
        refined.append({
            "type": "full",
            "phase": "setup",
            "rep": 0,
            "frame_count": len(pre_rep_frames),
            "frames": pre_rep_frames,
        })

    for rep_num in sorted(rep_groups.keys()):
        frames = rep_groups[rep_num]
        if rep_num in full_rep_nums:
            # Full frame data with landmarks
            refined.append({
                "type": "full",
                "rep": rep_num,
                "frame_count": len(frames),
                "frames": frames,
            })
        else:
            # Summary only — no landmarks
            angles = [f["angle"] for f in frames if f.get("angle") is not None]
            states = [f.get("state") for f in frames]
            feedbacks = list({f["fb"] for f in frames if f.get("fb")})
            refined.append({
                "type": "summary",
                "rep": rep_num,
                "frame_count": len(frames),
                "time_range": [frames[0]["t"], frames[-1]["t"]],
                "angle_min": round(min(angles), 1) if angles else None,
                "angle_max": round(max(angles), 1) if angles else None,
                "states": list(dict.fromkeys(states)),  # unique, ordered
                "feedback_samples": feedbacks,
            })

    return JSONResponse(content={
        "session_id": session.id,
        "challenge_type": session.challenge_type,
        "score": session.score,
        "duration_seconds": session.duration_seconds,
        "total_reps": total_reps,
        "total_frames": len(timeline),
        "full_reps": sorted(full_rep_nums),
        "summary_reps": sorted(summary_rep_nums),
        "end_reason": extra.get("end_reason"),
        "refined_timeline": refined,
    })


@router.get("/admin/sessions/{session_id}/screenshots")
def admin_list_screenshots(
    session_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """List screenshot URLs for a session (admin only)."""
    session = db.query(ChallengeSession).filter(
        ChallengeSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.screenshots_s3_prefix or not session.screenshot_count:
        return {"count": 0, "urls": []}

    storage = get_storage_service()
    urls = []
    for i in range(session.screenshot_count):
        key = f"{session.screenshots_s3_prefix}{i:04d}.jpg"
        urls.append(storage.outputs.get_url(key))

    return {"count": session.screenshot_count, "urls": urls}


@router.get("/admin/sessions/{session_id}/screenshots/{index}")
def admin_get_screenshot(
    session_id: int,
    index: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Download a single screenshot by index (admin only)."""
    session = db.query(ChallengeSession).filter(
        ChallengeSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.screenshots_s3_prefix or not session.screenshot_count:
        raise HTTPException(status_code=404, detail="No screenshots available")

    if index < 0 or index >= session.screenshot_count:
        raise HTTPException(status_code=404, detail=f"Screenshot index out of range (0-{session.screenshot_count - 1})")

    storage = get_storage_service()
    key = f"{session.screenshots_s3_prefix}{index:04d}.jpg"
    try:
        data = storage.outputs.load(key)
    except Exception:
        raise HTTPException(status_code=404, detail="Screenshot not found in storage")

    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Content-Disposition": f'inline; filename="session_{session_id}_screenshot_{index:04d}.jpg"'},
    )


@router.get("/admin/sessions/{session_id}/detail")
def admin_get_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Get session result details the way the user sees them (admin only)."""
    session = db.query(ChallengeSession).filter(
        ChallengeSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    record = db.query(ChallengeRecord).filter(
        ChallengeRecord.user_id == session.user_id,
        ChallengeRecord.challenge_type == session.challenge_type,
    ).first()
    daily_rank = _compute_daily_rank(db, session.user_id, session.challenge_type)

    return _build_response(session, record.best_score if record else None, daily_rank)


@router.get("/admin/sessions/{session_id}/recording")
def admin_download_recording(
    session_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Download recording for any session (admin only)."""
    storage = get_storage_service()

    session = db.query(ChallengeSession).filter(
        ChallengeSession.id == session_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    filename = f"challenge_recording_{session_id}.mp4"

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

    if session.recording_local_path:
        video_path = Path(session.recording_local_path)
        if video_path.exists():
            return FileResponse(path=str(video_path), media_type="video/mp4", filename=filename)

    raise HTTPException(status_code=404, detail="No recording available for this session")


@router.get("/admin/config")
def admin_get_config(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Get all challenge configs (thresholds only)."""
    rows = db.query(ChallengeConfig).all()
    saved = {r.challenge_type: r for r in rows}

    result = {}
    for ctype, defaults in CHALLENGE_DEFAULTS.items():
        row = saved.get(ctype)
        result[ctype] = {
            "thresholds": row.thresholds if row else defaults,
            "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
            "is_custom": (row.thresholds != defaults) if row else False,
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
    """Reset thresholds to defaults, preserving the enabled flag (admin only)."""
    if challenge_type not in CHALLENGE_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"Invalid challenge type. Must be one of: {list(CHALLENGE_DEFAULTS.keys())}")

    row = db.query(ChallengeConfig).filter(
        ChallengeConfig.challenge_type == challenge_type
    ).first()
    if row:
        row.thresholds = CHALLENGE_DEFAULTS[challenge_type]
        db.commit()
        db.refresh(row)
    return {"challenge_type": challenge_type, "thresholds": CHALLENGE_DEFAULTS[challenge_type], "is_custom": False}


