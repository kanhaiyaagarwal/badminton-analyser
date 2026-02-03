"""Invite code, waitlist, and whitelist database models."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func

from ..database import Base


class WhitelistEmail(Base):
    """Whitelisted emails that can signup without invite code."""

    __tablename__ = "whitelist_emails"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    note = Column(String(255), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InviteCode(Base):
    """Invite codes for signup."""

    __tablename__ = "invite_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)

    # Usage tracking
    max_uses = Column(Integer, default=0)  # 0 = unlimited
    times_used = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    note = Column(String(255), nullable=True)  # Optional description


class Waitlist(Base):
    """Waitlist for users who want access."""

    __tablename__ = "waitlist"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, approved, rejected

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # If approved, the invite code sent
    invite_code_id = Column(Integer, ForeignKey("invite_codes.id"), nullable=True)
