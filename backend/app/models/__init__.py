"""
CelebraTech Event Management System - Database Models
Sprint 1: Infrastructure & Authentication
Sprint 2: Event Management Core
Sprint 3: Vendor Profile Foundation
Sprint 4: Booking & Quote System
Sprint 5: Payment Gateway Integration & Financial Management
Sprint 6: Review and Rating System
Sprint 7: Messaging System
Sprint 8: Notification System
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

from app.models.booking import (
    BookingRequest,
    Quote,
    QuoteItem,
    Booking,
    BookingPayment,
    BookingCancellation
)

from app.models.payment import (
    PaymentGatewayConfig,
    PaymentTransaction,
    PaymentRefund,
    PaymentDispute,
    VendorPayout,
    PayoutItem,
    Invoice,
    SavedPaymentMethod
)

from app.models.review import (
    Review,
    ReviewResponse,
    ReviewHelpfulness,
    ReviewReport,
    VendorRatingCache
)

from app.models.messaging import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageReadReceipt,
    MessageAttachment,
    TypingIndicator,
    MessageReaction
)

from app.models.notification import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationTemplate,
    NotificationDevice,
    NotificationBatch
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
    # Booking models
    "BookingRequest",
    "Quote",
    "QuoteItem",
    "Booking",
    "BookingPayment",
    "BookingCancellation",
    # Payment models
    "PaymentGatewayConfig",
    "PaymentTransaction",
    "PaymentRefund",
    "PaymentDispute",
    "VendorPayout",
    "PayoutItem",
    "Invoice",
    "SavedPaymentMethod",
    # Review models
    "Review",
    "ReviewResponse",
    "ReviewHelpfulness",
    "ReviewReport",
    "VendorRatingCache",
    # Messaging models
    "Conversation",
    "ConversationParticipant",
    "Message",
    "MessageReadReceipt",
    "MessageAttachment",
    "TypingIndicator",
    "MessageReaction",
    # Notification models
    "Notification",
    "NotificationDelivery",
    "NotificationPreference",
    "NotificationTemplate",
    "NotificationDevice",
    "NotificationBatch",
]
