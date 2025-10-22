"""
CelebraTech Event Management System - Database Models
Sprint 1: Infrastructure & Authentication
"""

# This file makes the models directory a Python package
# Import all models to ensure they're registered with SQLAlchemy

from app.models.user import (
    User,
    UserSession,
    EmailVerificationToken,
    PasswordResetToken,
    UserConsent,
    OAuthConnection
)

__all__ = [
    "User",
    "UserSession",
    "EmailVerificationToken",
    "PasswordResetToken",
    "UserConsent",
    "OAuthConnection",
]
