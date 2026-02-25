"""Admin router for managing invite codes and waitlist."""

import secrets
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from ..database import get_db
from ..db_models.user import User
from ..db_models.invite import InviteCode, Waitlist, WhitelistEmail
from ..db_models.stream_session import StreamSession, StreamStatus
from .auth import get_current_user

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# --- Pydantic Models ---

class InviteCodeCreate(BaseModel):
    code: Optional[str] = None  # Auto-generate if not provided
    max_uses: int = 0  # 0 = unlimited
    note: Optional[str] = None


class InviteCodeResponse(BaseModel):
    id: int
    code: str
    max_uses: int
    times_used: int
    is_active: bool
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class WaitlistEntry(BaseModel):
    id: int
    email: str
    name: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class WaitlistJoin(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class WhitelistEmailCreate(BaseModel):
    email: EmailStr
    note: Optional[str] = None


class WhitelistEmailResponse(BaseModel):
    id: int
    email: str
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Dependencies ---

async def get_admin_user(current_user=Depends(get_current_user)):
    """Ensure current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# --- Invite Code Endpoints ---

@router.get("/invite-codes", response_model=List[InviteCodeResponse])
async def list_invite_codes(
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all invite codes."""
    codes = db.query(InviteCode).order_by(InviteCode.created_at.desc()).all()
    return codes


@router.post("/invite-codes", response_model=InviteCodeResponse)
async def create_invite_code(
    data: InviteCodeCreate,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new invite code."""
    # Generate code if not provided
    code = data.code or f"INV-{secrets.token_hex(4).upper()}"

    # Check if code already exists
    existing = db.query(InviteCode).filter(InviteCode.code == code.upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite code already exists"
        )

    invite_code = InviteCode(
        code=code.upper(),
        max_uses=data.max_uses,
        note=data.note,
        created_by=admin.id
    )
    db.add(invite_code)
    db.commit()
    db.refresh(invite_code)

    return invite_code


@router.delete("/invite-codes/{code_id}")
async def delete_invite_code(
    code_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete an invite code."""
    code = db.query(InviteCode).filter(InviteCode.id == code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Invite code not found")

    db.delete(code)
    db.commit()
    return {"status": "deleted"}


@router.patch("/invite-codes/{code_id}/toggle")
async def toggle_invite_code(
    code_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Toggle invite code active status."""
    code = db.query(InviteCode).filter(InviteCode.id == code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Invite code not found")

    code.is_active = not code.is_active
    db.commit()
    return {"status": "toggled", "is_active": code.is_active}


# --- Waitlist Endpoints ---

@router.get("/waitlist", response_model=List[WaitlistEntry])
async def list_waitlist(
    status_filter: Optional[str] = None,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List waitlist entries."""
    query = db.query(Waitlist)
    if status_filter:
        query = query.filter(Waitlist.status == status_filter)
    entries = query.order_by(Waitlist.created_at.desc()).all()
    return entries


@router.post("/waitlist/{entry_id}/approve")
async def approve_waitlist(
    entry_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Approve a waitlist entry and generate invite code."""
    entry = db.query(Waitlist).filter(Waitlist.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    if entry.status != "pending":
        raise HTTPException(status_code=400, detail="Entry already processed")

    # Create personal invite code
    code = f"WL-{secrets.token_hex(4).upper()}"
    invite_code = InviteCode(
        code=code,
        max_uses=1,
        note=f"Waitlist approval for {entry.email}",
        created_by=admin.id
    )
    db.add(invite_code)
    db.flush()

    # Update waitlist entry
    entry.status = "approved"
    entry.approved_at = datetime.utcnow()
    entry.approved_by = admin.id
    entry.invite_code_id = invite_code.id

    db.commit()

    return {
        "status": "approved",
        "email": entry.email,
        "invite_code": code
    }


@router.post("/waitlist/{entry_id}/reject")
async def reject_waitlist(
    entry_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Reject a waitlist entry."""
    entry = db.query(Waitlist).filter(Waitlist.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    entry.status = "rejected"
    db.commit()
    return {"status": "rejected"}


@router.delete("/waitlist/{entry_id}")
async def delete_waitlist_entry(
    entry_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a waitlist entry."""
    entry = db.query(Waitlist).filter(Waitlist.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    db.delete(entry)
    db.commit()
    return {"status": "deleted"}


# --- Public Waitlist Join (no auth required) ---

@router.post("/join-waitlist", status_code=status.HTTP_201_CREATED)
async def join_waitlist(
    data: WaitlistJoin,
    db: Session = Depends(get_db)
):
    """Join the waitlist (public endpoint)."""
    # Check if already on waitlist
    existing = db.query(Waitlist).filter(Waitlist.email == data.email.lower()).first()
    if existing:
        if existing.status == "approved":
            return {"status": "already_approved", "message": "You've already been approved! Check your email for the invite code."}
        return {"status": "already_waitlisted", "message": "You're already on the waitlist."}

    # Check if email is already registered
    existing_user = db.query(User).filter(User.email == data.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already has an account"
        )

    entry = Waitlist(
        email=data.email.lower(),
        name=data.name
    )
    db.add(entry)
    db.commit()

    return {"status": "joined", "message": "You've been added to the waitlist! We'll notify you when access is available."}


# --- User Management ---

@router.get("/users")
async def list_users(
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all users."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "username": u.username,
            "is_active": u.is_active,
            "is_admin": u.is_admin,
            "enabled_features": u.enabled_features or [],
            "created_at": u.created_at
        }
        for u in users
    ]


class FeatureAccessResponse(BaseModel):
    feature_name: str
    access_mode: str
    default_on_signup: bool
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FeatureAccessUpdate(BaseModel):
    access_mode: Optional[str] = None
    default_on_signup: Optional[bool] = None


# --- Feature Access Endpoints ---

@router.get("/feature-access", response_model=List[FeatureAccessResponse])
async def list_feature_access(
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all feature access settings."""
    from ..db_models.feature_access import FeatureAccess
    rows = db.query(FeatureAccess).order_by(FeatureAccess.feature_name).all()
    return rows


@router.patch("/feature-access/{feature_name}", response_model=FeatureAccessResponse)
async def update_feature_access(
    feature_name: str,
    body: FeatureAccessUpdate,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update access_mode and/or default_on_signup for a feature."""
    from ..db_models.feature_access import FeatureAccess
    from ..db_models.user import ALL_FEATURES

    if feature_name not in ALL_FEATURES:
        raise HTTPException(status_code=400, detail=f"Unknown feature: {feature_name}")

    row = db.query(FeatureAccess).filter(FeatureAccess.feature_name == feature_name).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Feature access row not found for {feature_name}")

    if body.access_mode is not None:
        if body.access_mode not in ("global", "disabled", "per_user"):
            raise HTTPException(status_code=400, detail="access_mode must be 'global', 'disabled', or 'per_user'")
        row.access_mode = body.access_mode

    if body.default_on_signup is not None:
        row.default_on_signup = body.default_on_signup

    db.commit()
    db.refresh(row)
    return row


class UpdateFeaturesRequest(BaseModel):
    enabled_features: List[str]


@router.patch("/users/{user_id}/features")
async def update_user_features(
    user_id: int,
    body: UpdateFeaturesRequest,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update enabled features for a user."""
    from ..db_models.user import ALL_FEATURES

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate feature names
    invalid = set(body.enabled_features) - set(ALL_FEATURES)
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid features: {invalid}. Must be from {ALL_FEATURES}")

    user.enabled_features = list(body.enabled_features)
    db.commit()
    return {"status": "updated", "enabled_features": user.enabled_features}


@router.patch("/users/{user_id}/toggle-admin")
async def toggle_user_admin(
    user_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Toggle user admin status."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own admin status")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_admin = not user.is_admin
    db.commit()
    return {"status": "toggled", "is_admin": user.is_admin}


# --- Whitelist Email Endpoints ---

@router.get("/whitelist", response_model=List[WhitelistEmailResponse])
async def list_whitelist(
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all whitelisted emails."""
    emails = db.query(WhitelistEmail).order_by(WhitelistEmail.created_at.desc()).all()
    return emails


@router.post("/whitelist", response_model=WhitelistEmailResponse)
async def add_whitelist_email(
    data: WhitelistEmailCreate,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Add an email to whitelist."""
    # Check if already whitelisted
    existing = db.query(WhitelistEmail).filter(
        WhitelistEmail.email == data.email.lower()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already whitelisted"
        )

    whitelist = WhitelistEmail(
        email=data.email.lower(),
        note=data.note,
        created_by=admin.id
    )
    db.add(whitelist)
    db.commit()
    db.refresh(whitelist)

    return whitelist


@router.delete("/whitelist/{email_id}")
async def remove_whitelist_email(
    email_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Remove an email from whitelist."""
    entry = db.query(WhitelistEmail).filter(WhitelistEmail.id == email_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Whitelist entry not found")

    db.delete(entry)
    db.commit()
    return {"status": "deleted"}


# --- Badminton Stream Sessions ---

@router.get("/stream-sessions")
async def admin_list_stream_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """List all badminton stream sessions with pagination (admin only)."""
    # Select only the columns needed — avoids loading huge JSON blobs
    # (foot_positions, shot_timeline, etc.) which cause MySQL OOM on sort.
    cols = (
        StreamSession.id,
        StreamSession.user_id,
        User.username,
        StreamSession.title,
        StreamSession.status,
        StreamSession.total_shots,
        StreamSession.shot_distribution,
        StreamSession.stream_mode,
        StreamSession.created_at,
        StreamSession.ended_at,
        StreamSession.recording_s3_key,
        StreamSession.recording_local_path,
        StreamSession.post_analysis_shots,
    )
    q = db.query(*cols).join(User, User.id == StreamSession.user_id)
    if status_filter:
        q = q.filter(StreamSession.status == status_filter)

    total = q.count()
    rows = q.order_by(StreamSession.created_at.desc()).offset(skip).limit(limit).all()

    sessions = []
    for row in rows:
        sessions.append({
            "id": row.id,
            "user_id": row.user_id,
            "username": row.username,
            "title": row.title,
            "status": row.status.value if row.status else "unknown",
            "total_shots": row.total_shots or 0,
            "shot_distribution": row.shot_distribution,
            "stream_mode": row.stream_mode or "basic",
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "ended_at": row.ended_at.isoformat() if row.ended_at else None,
            "has_recording": bool(row.recording_s3_key or row.recording_local_path),
            "post_analysis_shots": row.post_analysis_shots,
        })
    return {"sessions": sessions, "total": total, "skip": skip, "limit": limit}


@router.get("/stream-sessions/{session_id}/heatmaps")
async def admin_get_stream_heatmaps(
    session_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Get heatmap visualizations for a stream session (admin only)."""
    from pathlib import Path
    import json
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from heatmap_visualizer import HeatmapVisualizer

    session = db.query(StreamSession).filter(StreamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.foot_positions or len(session.foot_positions) < 5:
        return {"heatmaps": [], "message": "Not enough position data for heatmaps"}

    output_dir = Path(f"analysis_output/stream_{session_id}")
    if session.heatmap_paths and all(Path(p).exists() for p in session.heatmap_paths.values()):
        heatmaps = []
        for heatmap_type in session.heatmap_paths:
            heatmaps.append({
                "type": heatmap_type,
                "url": f"/api/v1/admin/stream-sessions/{session_id}/heatmap/{heatmap_type}",
            })
        return {"heatmaps": heatmaps}

    output_dir.mkdir(parents=True, exist_ok=True)
    temp_data = {
        "positions": session.foot_positions,
        "rallies": [],
        "metadata": {"court_boundary": session.court_boundary, "video_name": f"stream_{session_id}"},
    }
    temp_file = output_dir / "heatmap_data.json"
    with open(temp_file, "w") as f:
        json.dump(temp_data, f)

    try:
        visualizer = HeatmapVisualizer(str(temp_file))
        saved_paths = visualizer.save_all_visualizations(str(output_dir))
        session.heatmap_paths = saved_paths
        db.commit()
        return {"heatmaps": [{"type": t, "url": f"/api/v1/admin/stream-sessions/{session_id}/heatmap/{t}"} for t in saved_paths]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate heatmaps: {str(e)}")


@router.get("/stream-sessions/{session_id}/heatmap/{heatmap_type}")
async def admin_get_stream_heatmap_image(
    session_id: int,
    heatmap_type: str,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Get a specific heatmap image (admin only)."""
    from pathlib import Path
    from fastapi.responses import FileResponse

    session = db.query(StreamSession).filter(StreamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.heatmap_paths or heatmap_type not in session.heatmap_paths:
        raise HTTPException(status_code=404, detail="Heatmap not found")

    heatmap_path = Path(session.heatmap_paths[heatmap_type])
    if not heatmap_path.exists():
        raise HTTPException(status_code=404, detail="Heatmap file not found")

    return FileResponse(heatmap_path, media_type="image/png")


@router.get("/stream-sessions/{session_id}/results")
async def admin_get_stream_results(
    session_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Get full results for a stream session (admin only, no ownership check)."""
    from pathlib import Path

    session = db.query(StreamSession).filter(StreamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != StreamStatus.ENDED:
        raise HTTPException(status_code=400, detail="Session has not ended yet")

    duration = None
    if session.started_at and session.ended_at:
        duration = (session.ended_at - session.started_at).total_seconds()

    has_recording = bool(session.recording_s3_key) or (
        bool(session.recording_local_path) and Path(session.recording_local_path).exists()
    )
    has_annotated_video = bool(session.annotated_video_s3_key) or (
        bool(session.annotated_video_local_path) and Path(session.annotated_video_local_path).exists()
    )
    has_frame_data = bool(session.frame_data_s3_key) or (
        bool(session.frame_data_local_path) and Path(session.frame_data_local_path).exists()
    )

    return {
        "session_id": session.id,
        "title": session.title or f"Live Session #{session.id}",
        "summary": {
            "total_shots": session.total_shots,
            "session_duration": duration,
            "frame_rate": session.frame_rate,
            "quality": session.quality,
        },
        "shot_distribution": session.shot_distribution or {},
        "heatmap_paths": session.heatmap_paths,
        "foot_positions": session.foot_positions or [],
        "shot_timeline": session.shot_timeline or [],
        "court_boundary": session.court_boundary,
        "has_recording": has_recording,
        "analysis_status": session.analysis_status or "none",
        "analysis_progress": session.analysis_progress or 0,
        "has_annotated_video": has_annotated_video,
        "has_frame_data": has_frame_data,
        "post_analysis": {
            "shots": session.post_analysis_shots,
            "distribution": session.post_analysis_distribution,
            "rallies": session.post_analysis_rallies,
            "shuttle_hits": session.post_analysis_shuttle_hits,
            "rally_data": session.post_analysis_rally_data,
        } if session.analysis_status == "complete" else None,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
    }


@router.get("/stream-sessions/{session_id}/recording")
def admin_download_stream_recording(
    session_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Download recording for any stream session (admin only)."""
    from pathlib import Path
    from fastapi.responses import FileResponse, StreamingResponse
    from ..services.storage_service import get_storage_service

    storage = get_storage_service()
    session = db.query(StreamSession).filter(StreamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    filename = f"stream_recording_{session_id}.mp4"

    if session.recording_s3_key and storage.is_s3():
        try:
            video_data = storage.outputs.load(session.recording_s3_key)

            def iter_data():
                chunk_size = 1024 * 1024
                for i in range(0, len(video_data), chunk_size):
                    yield video_data[i:i + chunk_size]

            return StreamingResponse(
                iter_data(),
                media_type="video/mp4",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Length": str(len(video_data)),
                },
            )
        except Exception:
            pass

    if session.recording_local_path:
        video_path = Path(session.recording_local_path)
        if video_path.exists():
            return FileResponse(path=str(video_path), media_type="video/mp4", filename=filename)

    raise HTTPException(status_code=404, detail="No recording available for this session")


@router.get("/stream-sessions/{session_id}/annotated-video")
def admin_download_annotated_video(
    session_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Download annotated video for any stream session (admin only)."""
    import subprocess
    import logging
    from pathlib import Path
    from fastapi.responses import FileResponse

    logger = logging.getLogger(__name__)
    session = db.query(StreamSession).filter(StreamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.annotated_video_local_path:
        raise HTTPException(status_code=404, detail="Annotated video not available")

    video_path = Path(session.annotated_video_local_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Annotated video not available")

    h264_path = video_path.parent / f"{video_path.stem}_h264{video_path.suffix}"
    serve_path = video_path

    if h264_path.exists():
        serve_path = h264_path
    else:
        try:
            subprocess.run(
                [
                    'ffmpeg', '-y', '-i', str(video_path),
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                    '-c:a', 'aac', '-movflags', '+faststart',
                    str(h264_path),
                ],
                capture_output=True, text=True, timeout=300,
            )
            if h264_path.exists():
                serve_path = h264_path
                logger.info(f"Admin: Created H.264 annotated video for session {session_id}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"Admin: H.264 re-encode failed for session {session_id}: {e}")

    return FileResponse(
        path=str(serve_path),
        media_type="video/mp4",
        filename=f"annotated_stream_{session_id}.mp4",
    )
