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
from ..db_models.stream_session import StreamSession
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
    q = db.query(StreamSession, User.username).join(
        User, User.id == StreamSession.user_id
    )
    if status_filter:
        q = q.filter(StreamSession.status == status_filter)

    total = q.count()
    rows = q.order_by(StreamSession.created_at.desc()).offset(skip).limit(limit).all()

    sessions = []
    for s, username in rows:
        sessions.append({
            "id": s.id,
            "user_id": s.user_id,
            "username": username,
            "title": s.title,
            "status": s.status.value if s.status else "unknown",
            "total_shots": s.total_shots or 0,
            "shot_distribution": s.shot_distribution,
            "stream_mode": s.stream_mode or "basic",
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "has_recording": bool(s.recording_s3_key or s.recording_local_path),
            "post_analysis_shots": s.post_analysis_shots,
        })
    return {"sessions": sessions, "total": total, "skip": skip, "limit": limit}
