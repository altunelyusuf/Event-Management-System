"""
CelebraTech Event Management System - Authentication Service
Sprint 1: Infrastructure & Authentication
FR-001: User Authentication & Authorization
Business logic for authentication operations
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import secrets
import pyotp

from app.models.user import User
from app.schemas.user import (
    UserCreate,
    LoginRequest,
    TokenResponse,
    ConsentCreate
)
from app.repositories.user_repository import UserRepository
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.core.config import settings


class AuthService:
    """Service for authentication operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(
        self,
        user_data: UserCreate,
        ip_address: str,
        user_agent: str
    ) -> Tuple[User, TokenResponse]:
        """
        Register a new user

        Args:
            user_data: User registration data
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Tuple of (User, TokenResponse)

        Raises:
            HTTPException: If email or phone already exists
        """
        # Check if email already exists
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Check if phone already exists
        if user_data.phone:
            existing_phone = await self.user_repo.get_by_phone(user_data.phone)
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered"
                )

        # Create user
        user = await self.user_repo.create(user_data)

        # Create KVKK consent
        await self.user_repo.create_consent(
            user_id=str(user.id),
            consent_type="KVKK_EXPLICIT",
            consent_version="1.0",
            granted=True,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Generate tokens
        tokens = await self._generate_tokens(user, ip_address, user_agent)

        # Send verification email (async task)
        await self._send_verification_email(user)

        return user, tokens

    async def login(
        self,
        login_data: LoginRequest,
        ip_address: str,
        user_agent: str
    ) -> Tuple[User, Optional[TokenResponse]]:
        """
        Authenticate user and generate tokens

        Args:
            login_data: Login credentials
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Tuple of (User, TokenResponse or None)
            TokenResponse is None if 2FA is required

        Raises:
            HTTPException: If credentials are invalid
        """
        # Get user by email
        user = await self.user_repo.get_by_email(login_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Verify password
        if not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Check if account is active
        if user.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )

        # Check if 2FA is enabled
        if user.two_factor_enabled:
            if not login_data.two_factor_code:
                # Return user but no tokens - frontend should prompt for 2FA
                return user, None

            # Verify 2FA code
            if not self._verify_totp(user.two_factor_secret, login_data.two_factor_code):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid two-factor authentication code"
                )

        # Update last login
        await self.user_repo.update_last_login(str(user.id))

        # Generate tokens
        tokens = await self._generate_tokens(user, ip_address, user_agent)

        return user, tokens

    async def refresh_token(
        self,
        refresh_token: str,
        ip_address: str,
        user_agent: str
    ) -> TokenResponse:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Refresh token string
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            New token pair

        Raises:
            HTTPException: If refresh token is invalid
        """
        # Verify refresh token
        session = await self.user_repo.get_session_by_token(refresh_token)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Get user
        user = await self.user_repo.get_by_id(str(session.user_id))
        if not user or user.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user"
            )

        # Revoke old session
        await self.user_repo.revoke_session(str(session.id))

        # Generate new tokens
        tokens = await self._generate_tokens(user, ip_address, user_agent)

        return tokens

    async def logout(self, user: User, refresh_token: str) -> bool:
        """
        Logout user by revoking refresh token

        Args:
            user: Current user
            refresh_token: Refresh token to revoke

        Returns:
            True if successful
        """
        session = await self.user_repo.get_session_by_token(refresh_token)
        if session and str(session.user_id) == str(user.id):
            await self.user_repo.revoke_session(str(session.id))
        return True

    async def logout_all(self, user: User) -> int:
        """
        Logout user from all devices

        Args:
            user: Current user

        Returns:
            Number of sessions revoked
        """
        count = await self.user_repo.revoke_all_sessions(str(user.id))
        return count

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password

        Args:
            user: Current user
            current_password: Current password
            new_password: New password

        Returns:
            True if successful

        Raises:
            HTTPException: If current password is incorrect
        """
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )

        # Update password
        await self.user_repo.update_password(str(user.id), new_password)

        # Revoke all sessions except current
        await self.user_repo.revoke_all_sessions(str(user.id))

        return True

    async def forgot_password(self, email: str) -> bool:
        """
        Initiate password reset process

        Args:
            email: User email

        Returns:
            Always returns True (security - don't reveal if email exists)
        """
        user = await self.user_repo.get_by_email(email)
        if user:
            # Create password reset token
            token = await self.user_repo.create_password_reset_token(str(user.id))

            # Send password reset email (async task)
            await self._send_password_reset_email(user, token.token)

        # Always return True to not reveal if email exists
        return True

    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password using token

        Args:
            token: Password reset token
            new_password: New password

        Returns:
            True if successful

        Raises:
            HTTPException: If token is invalid or expired
        """
        # Verify token
        user_id = await self.user_repo.verify_password_reset_token(token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token"
            )

        # Update password
        await self.user_repo.update_password(user_id, new_password)

        # Revoke all sessions
        await self.user_repo.revoke_all_sessions(user_id)

        return True

    async def verify_email(self, token: str) -> bool:
        """
        Verify user email using token

        Args:
            token: Email verification token

        Returns:
            True if successful

        Raises:
            HTTPException: If token is invalid or expired
        """
        user_id = await self.user_repo.verify_email_token(token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token"
            )

        await self.user_repo.verify_email(user_id)
        return True

    async def resend_verification_email(self, user: User) -> bool:
        """
        Resend verification email

        Args:
            user: Current user

        Returns:
            True if sent
        """
        if user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )

        await self._send_verification_email(user)
        return True

    async def enable_two_factor(self, user: User) -> str:
        """
        Enable two-factor authentication

        Args:
            user: Current user

        Returns:
            TOTP secret for QR code generation
        """
        if user.two_factor_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Two-factor authentication already enabled"
            )

        # Generate TOTP secret
        secret = pyotp.random_base32()
        await self.user_repo.enable_two_factor(str(user.id), secret)

        return secret

    async def verify_two_factor(self, user: User, code: str) -> bool:
        """
        Verify two-factor authentication code

        Args:
            user: Current user
            code: TOTP code

        Returns:
            True if valid

        Raises:
            HTTPException: If code is invalid
        """
        if not user.two_factor_enabled or not user.two_factor_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Two-factor authentication not enabled"
            )

        if not self._verify_totp(user.two_factor_secret, code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication code"
            )

        return True

    async def disable_two_factor(self, user: User, code: str) -> bool:
        """
        Disable two-factor authentication

        Args:
            user: Current user
            code: TOTP code for verification

        Returns:
            True if successful

        Raises:
            HTTPException: If code is invalid
        """
        if not user.two_factor_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Two-factor authentication not enabled"
            )

        # Verify code before disabling
        if not self._verify_totp(user.two_factor_secret, code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication code"
            )

        await self.user_repo.disable_two_factor(str(user.id))
        return True

    # Private helper methods
    async def _generate_tokens(
        self,
        user: User,
        ip_address: str,
        user_agent: str
    ) -> TokenResponse:
        """Generate access and refresh tokens"""
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        # Store refresh token in database
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.user_repo.create_session(
            user_id=str(user.id),
            refresh_token=refresh_token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    def _verify_totp(self, secret: str, code: str) -> bool:
        """Verify TOTP code"""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    async def _send_verification_email(self, user: User) -> None:
        """Send email verification (async task)"""
        # Create verification token
        token = await self.user_repo.create_email_verification_token(str(user.id))

        # TODO: Send email via Celery task
        # For now, just log the token
        print(f"Email verification token for {user.email}: {token.token}")

    async def _send_password_reset_email(self, user: User, token: str) -> None:
        """Send password reset email (async task)"""
        # TODO: Send email via Celery task
        # For now, just log the token
        print(f"Password reset token for {user.email}: {token}")
