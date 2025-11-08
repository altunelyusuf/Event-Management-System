"""
CelebraTech Event Management System - Authentication API
Sprint 1: Infrastructure & Authentication
FR-001: User Authentication & Authorization
FastAPI endpoints for authentication
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    TwoFactorEnableRequest,
    TwoFactorVerifyRequest,
    TwoFactorDisableRequest,
    ErrorResponse
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        422: {"description": "Validation Error"}
    },
    summary="Register a new user",
    description="Create a new user account with email and password. Requires KVKK consent."
)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account

    - **email**: Valid email address (must be unique)
    - **password**: Strong password (min 12 chars, uppercase, lowercase, digit, special char)
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **phone**: Optional phone number (must be unique if provided)
    - **role**: User role (ORGANIZER, VENDOR, GUEST)

    Returns access token, refresh token, and user profile
    """
    auth_service = AuthService(db)

    # Get client info
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "")

    # Register user
    user, tokens = await auth_service.register(user_data, ip_address, user_agent)

    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        user=UserResponse.from_orm(user)
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"}
    },
    summary="Login user",
    description="Authenticate user with email and password"
)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and generate tokens

    - **email**: User's email address
    - **password**: User's password
    - **two_factor_code**: Optional 6-digit 2FA code (required if 2FA is enabled)

    Returns access token, refresh token, and user profile
    """
    auth_service = AuthService(db)

    # Get client info
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "")

    # Login user
    user, tokens = await auth_service.login(login_data, ip_address, user_agent)

    if not tokens:
        # 2FA required
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Two-factor authentication required",
            headers={"X-2FA-Required": "true"}
        )

    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        user=UserResponse.from_orm(user)
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"}
    },
    summary="Refresh access token",
    description="Get a new access token using refresh token"
)
async def refresh_token(
    token_data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token

    - **refresh_token**: Valid refresh token

    Returns new access token and refresh token
    """
    auth_service = AuthService(db)

    # Get client info
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "")

    # Refresh tokens
    tokens = await auth_service.refresh_token(
        token_data.refresh_token,
        ip_address,
        user_agent
    )

    return tokens


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
    description="Logout user from current device"
)
async def logout(
    token_data: RefreshTokenRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user from current device

    Requires authentication. Revokes the provided refresh token.
    """
    auth_service = AuthService(db)
    await auth_service.logout(current_user, token_data.refresh_token)
    return None


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout from all devices",
    description="Logout user from all devices"
)
async def logout_all(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user from all devices

    Requires authentication. Revokes all refresh tokens for the user.
    """
    auth_service = AuthService(db)
    await auth_service.logout_all(current_user)
    return None


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get current authenticated user profile"
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user profile

    Requires authentication.
    """
    return UserResponse.from_orm(current_user)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"}
    },
    summary="Change password",
    description="Change user password"
)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password

    - **current_password**: Current password
    - **new_password**: New password (must meet strength requirements)

    Requires authentication. Logs out user from all devices after password change.
    """
    auth_service = AuthService(db)
    await auth_service.change_password(
        current_user,
        password_data.current_password,
        password_data.new_password
    )
    return None


@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Forgot password",
    description="Request password reset email"
)
async def forgot_password(
    forgot_data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset

    - **email**: User's email address

    Sends password reset email if email exists. Always returns success for security.
    """
    auth_service = AuthService(db)
    await auth_service.forgot_password(forgot_data.email)
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"}
    },
    summary="Reset password",
    description="Reset password using token"
)
async def reset_password(
    reset_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password using token

    - **token**: Password reset token from email
    - **new_password**: New password (must meet strength requirements)

    Logs out user from all devices after password reset.
    """
    auth_service = AuthService(db)
    await auth_service.reset_password(reset_data.token, reset_data.new_password)
    return None


@router.post(
    "/verify-email",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"}
    },
    summary="Verify email",
    description="Verify email address using token"
)
async def verify_email(
    verify_data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify email address

    - **token**: Email verification token from email
    """
    auth_service = AuthService(db)
    await auth_service.verify_email(verify_data.token)
    return None


@router.post(
    "/resend-verification",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Resend verification email",
    description="Resend email verification link"
)
async def resend_verification(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resend verification email

    Requires authentication.
    """
    auth_service = AuthService(db)
    await auth_service.resend_verification_email(current_user)
    return {"message": "Verification email sent"}


@router.post(
    "/2fa/enable",
    response_model=dict,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"}
    },
    summary="Enable two-factor authentication",
    description="Enable 2FA and get QR code secret"
)
async def enable_two_factor(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Enable two-factor authentication

    Returns TOTP secret for QR code generation.
    User should scan QR code with authenticator app and verify with code.
    """
    auth_service = AuthService(db)
    secret = await auth_service.enable_two_factor(current_user)

    # Generate QR code URI
    import pyotp
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="CelebraTech"
    )

    return {
        "secret": secret,
        "qr_code_uri": provisioning_uri,
        "message": "Scan QR code with authenticator app and verify with code"
    }


@router.post(
    "/2fa/verify",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"}
    },
    summary="Verify two-factor authentication",
    description="Verify 2FA code"
)
async def verify_two_factor(
    verify_data: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify two-factor authentication code

    - **code**: 6-digit TOTP code from authenticator app
    """
    auth_service = AuthService(db)
    await auth_service.verify_two_factor(current_user, verify_data.code)
    return None


@router.post(
    "/2fa/disable",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"}
    },
    summary="Disable two-factor authentication",
    description="Disable 2FA"
)
async def disable_two_factor(
    disable_data: TwoFactorDisableRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disable two-factor authentication

    - **password**: User's password (for security)
    - **code**: 6-digit TOTP code from authenticator app (for verification)
    """
    auth_service = AuthService(db)

    # Verify password
    from app.core.security import verify_password
    if not verify_password(disable_data.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )

    # Disable 2FA
    await auth_service.disable_two_factor(current_user, disable_data.code)
    return None
