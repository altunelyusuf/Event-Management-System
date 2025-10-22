"""
CelebraTech Event Management System - Database Models
Sprint 1: Infrastructure & Authentication
Sprint 2: Event Management Core
Sprint 3: Vendor Profile Foundation
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

from app.models.event import (
    Event,
    EventOrganizer,
    EventPhase,
    EventMilestone,
    EventCulturalElement
)

from app.models.task import (
    Task,
    TaskDependency,
    TaskComment,
    TaskAttachment
)

from app.models.vendor import (
    Vendor,
    VendorSubcategory,
    VendorService,
    VendorPortfolio,
    VendorAvailability,
    VendorTeamMember,
    VendorCertification,
    VendorWorkingHours
)

__all__ = [
    # User models
    "User",
    "UserSession",
    "EmailVerificationToken",
    "PasswordResetToken",
    "UserConsent",
    "OAuthConnection",
    # Event models
    "Event",
    "EventOrganizer",
    "EventPhase",
    "EventMilestone",
    "EventCulturalElement",
    # Task models
    "Task",
    "TaskDependency",
    "TaskComment",
    "TaskAttachment",
    # Vendor models
    "Vendor",
    "VendorSubcategory",
    "VendorService",
    "VendorPortfolio",
    "VendorAvailability",
    "VendorTeamMember",
    "VendorCertification",
    "VendorWorkingHours",
]
