"""Authentication router."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import (
    UserCreate, UserResponse, UserLogin, Token,
    SignupResponse, VerifyEmailRequest, VerifyEmailResponse,
    ResendOTPRequest, ResendOTPResponse,
    ForgotPasswordRequest, ForgotPasswordResponse,
    ResetPasswordRequest, ResetPasswordResponse
)
from ..services.user_service import UserService
from ..services.otp_service import OTPService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

MAX_FAILED_ATTEMPTS = 10
LOCKOUT_DURATION_HOURS = 5


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Dependency to get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = UserService.decode_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    user = UserService.get_user_by_id(db, token_data.user_id)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


def _check_lockout(user):
    """Check if user account is locked. Raises HTTPException if locked."""
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = user.locked_until - datetime.utcnow()
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        if hours > 0:
            time_str = f"{hours}h {minutes}m"
        else:
            time_str = f"{minutes}m"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked due to too many failed attempts. Reset your password or try again in {time_str}.",
            headers={"X-Locked-Until": user.locked_until.isoformat()}
        )


def _handle_failed_login(db: Session, user):
    """Increment failed login attempts and lock if threshold reached."""
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.utcnow() + timedelta(hours=LOCKOUT_DURATION_HOURS)
    db.commit()


def _handle_successful_login(db: Session, user):
    """Reset failed login counter on successful authentication."""
    if user.failed_login_attempts:
        user.failed_login_attempts = 0
        db.commit()


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """Create a new user account and send OTP for email verification."""
    from ..config import get_settings
    from ..db_models.invite import InviteCode, WhitelistEmail, Waitlist
    from datetime import datetime

    settings = get_settings()

    # Check if email is whitelisted in database (bypass invite code)
    db_whitelist = db.query(WhitelistEmail).filter(
        WhitelistEmail.email == user_data.email.lower()
    ).first()
    is_whitelisted = db_whitelist is not None

    invite_code_record = None

    if not is_whitelisted:
        if not user_data.invite_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite code required"
            )

        # Check DB for invite code
        invite_code_record = db.query(InviteCode).filter(
            InviteCode.code == user_data.invite_code.upper(),
            InviteCode.is_active == True
        ).first()

        if not invite_code_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid invite code"
            )

        # Check if code has reached max uses
        if invite_code_record.max_uses > 0 and invite_code_record.times_used >= invite_code_record.max_uses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite code has reached maximum uses"
            )

    # Check if email already exists
    if UserService.get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    if UserService.get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Create user (email_verified=False by default)
    user = UserService.create_user(db, user_data)

    # Increment invite code usage if from DB
    if invite_code_record:
        invite_code_record.times_used += 1

        # Update waitlist entry status if this code came from waitlist approval
        waitlist_entry = db.query(Waitlist).filter(
            Waitlist.invite_code_id == invite_code_record.id,
            Waitlist.status == "approved"
        ).first()
        if waitlist_entry:
            waitlist_entry.status = "registered"

        db.commit()

    # Check if email verification is required
    if settings.require_email_verification:
        # Send OTP email
        OTPService.send_otp(db, user)
        return SignupResponse(
            user_id=user.id,
            email=user.email,
            message="Account created. Please check your email for the verification code.",
            requires_verification=True
        )
    else:
        # Auto-verify user when email verification is disabled
        user.email_verified = True
        user.email_verified_at = datetime.utcnow()
        db.commit()
        return SignupResponse(
            user_id=user.id,
            email=user.email,
            message="Account created successfully. You can now login.",
            requires_verification=False
        )


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token."""
    from ..config import get_settings
    settings = get_settings()

    # Look up user first to check lockout before password verification
    user = UserService.get_user_by_email(db, form_data.username)
    if user:
        _check_lockout(user)

    authenticated_user = UserService.authenticate_user(db, form_data.username, form_data.password)
    if not authenticated_user:
        # Increment failed attempts only if user exists (wrong password, not wrong email)
        if user:
            _handle_failed_login(db, user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _handle_successful_login(db, authenticated_user)

    if settings.require_email_verification and not authenticated_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email before logging in."
        )

    return UserService.create_tokens(authenticated_user)


@router.post("/login/json", response_model=Token)
async def login_json(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login with JSON body (alternative to form)."""
    from ..config import get_settings
    settings = get_settings()

    # Look up user first to check lockout before password verification
    user = UserService.get_user_by_email(db, credentials.email)
    if user:
        _check_lockout(user)

    authenticated_user = UserService.authenticate_user(db, credentials.email, credentials.password)
    if not authenticated_user:
        if user:
            _handle_failed_login(db, user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _handle_successful_login(db, authenticated_user)

    if settings.require_email_verification and not authenticated_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email before logging in."
        )

    return UserService.create_tokens(authenticated_user)


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    token_data = UserService.verify_refresh_token(refresh_token)
    if token_data is None or token_data.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = UserService.get_user_by_id(db, token_data.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return UserService.create_tokens(user)


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email with OTP code."""
    user = UserService.get_user_by_id(db, request.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.email_verified:
        return VerifyEmailResponse(
            success=True,
            message="Email already verified."
        )

    success, message, remaining = OTPService.verify_otp(db, request.user_id, request.code)

    return VerifyEmailResponse(
        success=success,
        message=message,
        remaining_attempts=remaining
    )


@router.post("/resend-otp", response_model=ResendOTPResponse)
async def resend_otp(request: ResendOTPRequest, db: Session = Depends(get_db)):
    """Resend OTP verification code."""
    user = UserService.get_user_by_id(db, request.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.email_verified:
        return ResendOTPResponse(
            success=False,
            message="Email already verified.",
            cooldown_seconds=0
        )

    success, message, cooldown = OTPService.resend_otp(db, user)

    return ResendOTPResponse(
        success=success,
        message=message,
        cooldown_seconds=cooldown
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send password reset OTP to email."""
    user = UserService.get_user_by_email(db, request.email)

    if not user:
        # Don't leak whether email exists
        return ForgotPasswordResponse(
            success=True,
            message="If an account with that email exists, a reset code has been sent."
        )

    # Check resend cooldown
    can_resend, cooldown_remaining = OTPService.can_resend_otp(db, user.id, purpose="reset")
    if not can_resend:
        return ForgotPasswordResponse(
            success=False,
            message=f"Please wait {cooldown_remaining} seconds before requesting a new code."
        )

    OTPService.send_password_reset_otp(db, user)

    return ForgotPasswordResponse(
        success=True,
        message="If an account with that email exists, a reset code has been sent."
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Verify OTP and set new password. Clears account lockout."""
    user = UserService.get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    success, message, remaining = OTPService.verify_password_reset_otp(db, user.id, request.code)
    if not success:
        return ResetPasswordResponse(success=False, message=message)

    # Update password and clear lockout
    user.hashed_password = UserService.hash_password(request.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    return ResetPasswordResponse(
        success=True,
        message="Password reset successfully. You can now login with your new password."
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    """Get current user information."""
    return current_user
