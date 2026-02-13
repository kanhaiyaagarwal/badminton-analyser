"""OTP service for generating and verifying email verification codes."""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from ..config import get_settings
from ..db_models.otp import EmailOTP
from ..db_models.user import User
from .email_service import get_email_service

settings = get_settings()


class OTPService:
    """Service for OTP generation, verification, and rate limiting."""

    @staticmethod
    def generate_otp_code() -> str:
        """Generate a secure 6-digit OTP code."""
        return "".join(secrets.choice("0123456789") for _ in range(6))

    @staticmethod
    def create_otp(db: Session, user: User, purpose: str = "verify") -> EmailOTP:
        """Create a new OTP for a user, invalidating any existing ones with the same purpose."""
        # Invalidate existing unverified OTPs for this user and purpose
        db.query(EmailOTP).filter(
            EmailOTP.user_id == user.id,
            EmailOTP.purpose == purpose,
            EmailOTP.verified_at.is_(None)
        ).delete()

        # Create new OTP
        otp = EmailOTP(
            user_id=user.id,
            code=OTPService.generate_otp_code(),
            purpose=purpose,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.otp_expire_minutes)
        )
        db.add(otp)
        db.commit()
        db.refresh(otp)
        return otp

    @staticmethod
    def send_otp(db: Session, user: User) -> bool:
        """Generate OTP and send via email. Returns True on success."""
        otp = OTPService.create_otp(db, user, purpose="verify")
        email_service = get_email_service()
        return email_service.send_otp_email(user.email, otp.code, user.username)

    @staticmethod
    def get_latest_otp(db: Session, user_id: int, purpose: str = "verify") -> Optional[EmailOTP]:
        """Get the latest unverified OTP for a user with the given purpose."""
        return db.query(EmailOTP).filter(
            EmailOTP.user_id == user_id,
            EmailOTP.purpose == purpose,
            EmailOTP.verified_at.is_(None)
        ).order_by(EmailOTP.created_at.desc()).first()

    @staticmethod
    def verify_otp(db: Session, user_id: int, code: str) -> Tuple[bool, str, Optional[int]]:
        """
        Verify an OTP code (email verification purpose).

        Returns:
            Tuple of (success, message, remaining_attempts or None)
        """
        otp = OTPService.get_latest_otp(db, user_id, purpose="verify")

        if not otp:
            return False, "No OTP found. Please request a new one.", None

        # Check if expired
        if datetime.utcnow() > otp.expires_at:
            return False, "OTP has expired. Please request a new one.", None

        # Check if max attempts exceeded
        if otp.attempts >= settings.otp_max_attempts:
            return False, "Maximum attempts exceeded. Please request a new OTP.", None

        # Verify code
        if otp.code != code:
            otp.attempts += 1
            db.commit()
            remaining = settings.otp_max_attempts - otp.attempts
            if remaining <= 0:
                return False, "Maximum attempts exceeded. Please request a new OTP.", 0
            return False, f"Invalid OTP code. {remaining} attempt(s) remaining.", remaining

        # Success - mark as verified
        otp.verified_at = datetime.utcnow()
        db.commit()

        # Mark user email as verified
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.email_verified = True
            user.email_verified_at = datetime.utcnow()
            db.commit()

        return True, "Email verified successfully.", None

    @staticmethod
    def can_resend_otp(db: Session, user_id: int, purpose: str = "verify") -> Tuple[bool, int]:
        """
        Check if user can request a new OTP.

        Returns:
            Tuple of (can_resend, seconds_until_can_resend)
        """
        otp = OTPService.get_latest_otp(db, user_id, purpose=purpose)

        if not otp:
            return True, 0

        # Calculate cooldown
        seconds_since_created = (datetime.utcnow() - otp.created_at).total_seconds()
        cooldown_remaining = settings.otp_resend_cooldown_seconds - int(seconds_since_created)

        if cooldown_remaining > 0:
            return False, cooldown_remaining

        return True, 0

    @staticmethod
    def resend_otp(db: Session, user: User) -> Tuple[bool, str, int]:
        """
        Resend OTP if cooldown has passed.

        Returns:
            Tuple of (success, message, cooldown_seconds)
        """
        can_resend, cooldown_remaining = OTPService.can_resend_otp(db, user.id)

        if not can_resend:
            return False, f"Please wait {cooldown_remaining} seconds before requesting a new code.", cooldown_remaining

        success = OTPService.send_otp(db, user)
        if success:
            return True, "A new verification code has been sent to your email.", 0
        return False, "Failed to send verification email. Please try again.", 0

    @staticmethod
    def send_password_reset_otp(db: Session, user: User) -> bool:
        """Generate password reset OTP and send via email. Returns True on success."""
        otp = OTPService.create_otp(db, user, purpose="reset")
        email_service = get_email_service()
        return email_service.send_password_reset_email(user.email, otp.code, user.username)

    @staticmethod
    def verify_password_reset_otp(db: Session, user_id: int, code: str) -> Tuple[bool, str, Optional[int]]:
        """
        Verify a password reset OTP code. Does NOT mark email as verified.

        Returns:
            Tuple of (success, message, remaining_attempts or None)
        """
        otp = OTPService.get_latest_otp(db, user_id, purpose="reset")

        if not otp:
            return False, "No reset code found. Please request a new one.", None

        if datetime.utcnow() > otp.expires_at:
            return False, "Reset code has expired. Please request a new one.", None

        if otp.attempts >= settings.otp_max_attempts:
            return False, "Maximum attempts exceeded. Please request a new reset code.", None

        if otp.code != code:
            otp.attempts += 1
            db.commit()
            remaining = settings.otp_max_attempts - otp.attempts
            if remaining <= 0:
                return False, "Maximum attempts exceeded. Please request a new reset code.", 0
            return False, f"Invalid reset code. {remaining} attempt(s) remaining.", remaining

        # Success - mark as verified (but don't touch email_verified)
        otp.verified_at = datetime.utcnow()
        db.commit()

        return True, "Code verified successfully.", None
