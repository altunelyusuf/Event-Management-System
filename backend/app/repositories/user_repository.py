"""
CelebraTech Event Management System - User Repository
Sprint 1: Infrastructure & Authentication
Data access layer for user operations
"""
from typing import Optional, List
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import secrets

from app.models.user import (
    User,
    UserSession,
    EmailVerificationToken,
    PasswordResetToken,
    UserConsent,
    OAuthConnection,
    UserStatus
)
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


class UserRepository:
    """Repository for user database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_data: UserCreate) -> User:
        """
        Create a new user

        Args:
            user_data: User creation data

        Returns:
            Created user object
        """
        password_hash = get_password_hash(user_data.password)

        user = User(
            email=user_data.email,
            phone=user_data.phone,
            password_hash=password_hash,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role,
            language_preference=user_data.language_preference,
            currency_preference=user_data.currency_preference,
            status=UserStatus.ACTIVE
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID

        Args:
            user_id: User UUID

        Returns:
            User object or None
        """
        result = await self.db.execute(
            select(User).where(
                and_(
                    User.id == user_id,
                    User.deleted_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email

        Args:
            email: User email address

        Returns:
            User object or None
        """
        result = await self.db.execute(
            select(User).where(
                and_(
                    User.email == email,
                    User.deleted_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        """
        Get user by phone number

        Args:
            phone: User phone number

        Returns:
            User object or None
        """
        result = await self.db.execute(
            select(User).where(
                and_(
                    User.phone == phone,
                    User.deleted_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    async def update(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """
        Update user profile

        Args:
            user_id: User UUID
            user_data: Update data

        Returns:
            Updated user object or None
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user_id: str) -> bool:
        """
        Soft delete user

        Args:
            user_id: User UUID

        Returns:
            True if deleted, False otherwise
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.deleted_at = datetime.utcnow()
        user.status = UserStatus.DELETED
        await self.db.commit()
        return True

    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp"""
        user = await self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            await self.db.commit()

    async def verify_email(self, user_id: str) -> bool:
        """Mark user email as verified"""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.email_verified = True
        user.email_verified_at = datetime.utcnow()
        await self.db.commit()
        return True

    async def verify_phone(self, user_id: str) -> bool:
        """Mark user phone as verified"""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.phone_verified = True
        user.phone_verified_at = datetime.utcnow()
        await self.db.commit()
        return True

    async def enable_two_factor(self, user_id: str, secret: str) -> bool:
        """Enable two-factor authentication"""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.two_factor_enabled = True
        user.two_factor_secret = secret
        await self.db.commit()
        return True

    async def disable_two_factor(self, user_id: str) -> bool:
        """Disable two-factor authentication"""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.two_factor_enabled = False
        user.two_factor_secret = None
        await self.db.commit()
        return True

    # Session management
    async def create_session(
        self,
        user_id: str,
        refresh_token: str,
        expires_at: datetime,
        ip_address: str = None,
        user_agent: str = None
    ) -> UserSession:
        """Create a new user session"""
        session = UserSession(
            user_id=user_id,
            refresh_token=refresh_token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session_by_token(self, refresh_token: str) -> Optional[UserSession]:
        """Get session by refresh token"""
        result = await self.db.execute(
            select(UserSession).where(
                and_(
                    UserSession.refresh_token == refresh_token,
                    UserSession.revoked_at.is_(None),
                    UserSession.expires_at > datetime.utcnow()
                )
            )
        )
        return result.scalar_one_or_none()

    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a user session"""
        result = await self.db.execute(
            select(UserSession).where(UserSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return False

        session.revoked_at = datetime.utcnow()
        await self.db.commit()
        return True

    async def revoke_all_sessions(self, user_id: str) -> int:
        """Revoke all user sessions"""
        result = await self.db.execute(
            select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.revoked_at.is_(None)
                )
            )
        )
        sessions = result.scalars().all()

        count = 0
        for session in sessions:
            session.revoked_at = datetime.utcnow()
            count += 1

        await self.db.commit()
        return count

    # Email verification tokens
    async def create_email_verification_token(self, user_id: str) -> EmailVerificationToken:
        """Create email verification token"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)

        verification = EmailVerificationToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        self.db.add(verification)
        await self.db.commit()
        await self.db.refresh(verification)
        return verification

    async def verify_email_token(self, token: str) -> Optional[str]:
        """
        Verify email token and return user_id

        Returns:
            user_id if valid, None otherwise
        """
        result = await self.db.execute(
            select(EmailVerificationToken).where(
                and_(
                    EmailVerificationToken.token == token,
                    EmailVerificationToken.used_at.is_(None),
                    EmailVerificationToken.expires_at > datetime.utcnow()
                )
            )
        )
        verification = result.scalar_one_or_none()
        if not verification:
            return None

        verification.used_at = datetime.utcnow()
        await self.db.commit()
        return str(verification.user_id)

    # Password reset tokens
    async def create_password_reset_token(self, user_id: str) -> PasswordResetToken:
        """Create password reset token"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        reset = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        self.db.add(reset)
        await self.db.commit()
        await self.db.refresh(reset)
        return reset

    async def verify_password_reset_token(self, token: str) -> Optional[str]:
        """
        Verify password reset token and return user_id

        Returns:
            user_id if valid, None otherwise
        """
        result = await self.db.execute(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.token == token,
                    PasswordResetToken.used_at.is_(None),
                    PasswordResetToken.expires_at > datetime.utcnow()
                )
            )
        )
        reset = result.scalar_one_or_none()
        if not reset:
            return None

        reset.used_at = datetime.utcnow()
        await self.db.commit()
        return str(reset.user_id)

    async def update_password(self, user_id: str, new_password: str) -> bool:
        """Update user password"""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        user.password_hash = get_password_hash(new_password)
        await self.db.commit()
        return True

    # Consent management
    async def create_consent(
        self,
        user_id: str,
        consent_type: str,
        consent_version: str,
        granted: bool,
        ip_address: str,
        user_agent: str
    ) -> UserConsent:
        """Create user consent record"""
        consent = UserConsent(
            user_id=user_id,
            consent_type=consent_type,
            consent_version=consent_version,
            granted=granted,
            granted_at=datetime.utcnow() if granted else None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(consent)
        await self.db.commit()
        await self.db.refresh(consent)
        return consent

    async def get_user_consents(self, user_id: str) -> List[UserConsent]:
        """Get all consents for a user"""
        result = await self.db.execute(
            select(UserConsent).where(UserConsent.user_id == user_id)
        )
        return result.scalars().all()

    # OAuth connections
    async def create_oauth_connection(
        self,
        user_id: str,
        provider: str,
        provider_user_id: str,
        access_token: str = None,
        refresh_token: str = None
    ) -> OAuthConnection:
        """Create OAuth connection"""
        connection = OAuthConnection(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            access_token=access_token,
            refresh_token=refresh_token
        )
        self.db.add(connection)
        await self.db.commit()
        await self.db.refresh(connection)
        return connection

    async def get_oauth_connection(
        self,
        provider: str,
        provider_user_id: str
    ) -> Optional[OAuthConnection]:
        """Get OAuth connection by provider and provider user ID"""
        result = await self.db.execute(
            select(OAuthConnection).where(
                and_(
                    OAuthConnection.provider == provider,
                    OAuthConnection.provider_user_id == provider_user_id
                )
            )
        )
        return result.scalar_one_or_none()
