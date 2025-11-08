"""
CelebraTech Event Management System - User Schemas
Sprint 1: Infrastructure & Authentication
Pydantic models for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.user import UserRole, UserStatus


# Base schemas
class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=12, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role: UserRole = UserRole.ORGANIZER
    language_preference: str = Field("tr", max_length=5)
    currency_preference: str = Field("TRY", max_length=3)

    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in v):
            raise ValueError("Password must contain at least one special character")

        return v


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    profile_image_url: Optional[str] = None
    language_preference: Optional[str] = None
    currency_preference: Optional[str] = None
    timezone: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: UUID
    role: UserRole
    status: UserStatus
    phone: Optional[str]
    email_verified: bool
    phone_verified: bool
    two_factor_enabled: bool
    profile_image_url: Optional[str]
    language_preference: str
    currency_preference: str
    timezone: str
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """Schema for user in database (includes password hash)"""
    password_hash: str

    class Config:
        from_attributes = True


# Authentication schemas
class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr
    password: str
    two_factor_code: Optional[str] = Field(None, min_length=6, max_length=6)


class LoginResponse(BaseModel):
    """Schema for login response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    """Schema for changing password"""
    current_password: str
    new_password: str = Field(..., min_length=12, max_length=100)

    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in v):
            raise ValueError("Password must contain at least one special character")

        return v


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Schema for reset password request"""
    token: str
    new_password: str = Field(..., min_length=12, max_length=100)


class VerifyEmailRequest(BaseModel):
    """Schema for email verification request"""
    token: str


class TwoFactorEnableRequest(BaseModel):
    """Schema for enabling two-factor authentication"""
    password: str


class TwoFactorVerifyRequest(BaseModel):
    """Schema for verifying two-factor authentication"""
    code: str = Field(..., min_length=6, max_length=6)


class TwoFactorDisableRequest(BaseModel):
    """Schema for disabling two-factor authentication"""
    password: str
    code: str = Field(..., min_length=6, max_length=6)


# OAuth schemas
class OAuthCallbackRequest(BaseModel):
    """Schema for OAuth callback"""
    code: str
    provider: str = Field(..., pattern="^(GOOGLE|APPLE|FACEBOOK)$")


class OAuthLinkRequest(BaseModel):
    """Schema for linking OAuth account"""
    code: str
    provider: str = Field(..., pattern="^(GOOGLE|APPLE|FACEBOOK)$")


# Consent schemas
class ConsentCreate(BaseModel):
    """Schema for creating consent"""
    consent_type: str
    consent_version: str
    granted: bool


class ConsentResponse(BaseModel):
    """Schema for consent response"""
    id: UUID
    user_id: UUID
    consent_type: str
    consent_version: str
    granted: bool
    granted_at: Optional[datetime]
    revoked_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# Error responses
class ErrorResponse(BaseModel):
    """Schema for error response"""
    detail: str


class ValidationErrorResponse(BaseModel):
    """Schema for validation error response"""
    detail: list[dict]
