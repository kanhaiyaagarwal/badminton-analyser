"""Authentication router."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import UserCreate, UserResponse, UserLogin, Token
from ..services.user_service import UserService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


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


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """Create a new user account."""
    from ..config import get_settings
    from ..db_models.invite import InviteCode, WhitelistEmail, Waitlist
    settings = get_settings()

    # Check if email is whitelisted (bypass invite code)
    # Check both env-based and database whitelist
    is_whitelisted = user_data.email.lower() in settings.whitelist_emails_list
    if not is_whitelisted:
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

        # First check DB for invite code
        invite_code_record = db.query(InviteCode).filter(
            InviteCode.code == user_data.invite_code.upper(),
            InviteCode.is_active == True
        ).first()

        # If not in DB, check env config (fallback)
        if not invite_code_record:
            if user_data.invite_code.upper() not in settings.invite_codes_list:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid invite code"
                )
        else:
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

    # Create user
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

    return user


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token."""
    user = UserService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserService.create_tokens(user)


@router.post("/login/json", response_model=Token)
async def login_json(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login with JSON body (alternative to form)."""
    user = UserService.authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserService.create_tokens(user)


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


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    """Get current user information."""
    return current_user
