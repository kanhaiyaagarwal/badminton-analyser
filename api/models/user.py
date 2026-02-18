"""User Pydantic models for request/response."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    invite_code: str = Field(default="", max_length=50)


class GoogleAuthRequest(BaseModel):
    """Schema for Google OAuth login/signup."""
    credential: str
    invite_code: str = Field(default="", max_length=50)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    mobile: Optional[str] = Field(None, max_length=20)


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    email: str
    username: str
    mobile: Optional[str] = None
    is_active: bool
    is_admin: bool = False
    enabled_features: list = []
    auth_provider: str = "local"
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for decoded token data."""
    user_id: Optional[int] = None
    email: Optional[str] = None


class SignupResponse(BaseModel):
    """Schema for signup response (before email verification)."""
    user_id: int
    email: str
    message: str
    requires_verification: bool = True


class VerifyEmailRequest(BaseModel):
    """Schema for email verification request."""
    user_id: int
    code: str = Field(..., min_length=6, max_length=6)


class VerifyEmailResponse(BaseModel):
    """Schema for email verification response."""
    success: bool
    message: str
    remaining_attempts: Optional[int] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None


class ResendOTPRequest(BaseModel):
    """Schema for resend OTP request."""
    user_id: int


class ResendOTPResponse(BaseModel):
    """Schema for resend OTP response."""
    success: bool
    message: str
    cooldown_seconds: int = 0


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request."""
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Schema for forgot password response."""
    success: bool
    message: str


class ResetPasswordRequest(BaseModel):
    """Schema for reset password request."""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=100)


class ResetPasswordResponse(BaseModel):
    """Schema for reset password response."""
    success: bool
    message: str
