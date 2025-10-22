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
Sprint 9: Guest Management System
Sprint 10: Analytics & Reporting System
Sprint 11: Document Management System
Sprint 12: Advanced Task Management & Team Collaboration
Sprint 13: Search & Discovery System
Sprint 14: Calendar & Scheduling System
Sprint 15: Budget Management System
Sprint 16: Collaboration & Sharing System
Sprint 17: AI & Recommendation Engine
Sprint 18: Mobile App Foundation
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

from app.models.guest import (
    Guest,
    GuestGroup,
    GuestInvitation,
    RSVPResponse,
    SeatingArrangement,
    GuestCheckIn,
    DietaryRestriction
)

from app.models.analytics import (
    AnalyticsSnapshot,
    Report,
    Metric,
    Dashboard,
    AuditLog,
    EventCompletionRate
)

from app.models.document import (
    Document,
    DocumentFolder,
    DocumentShare,
    DocumentComment,
    DocumentSignature,
    DocumentTemplate,
    DocumentActivity
)

from app.models.task_collaboration import (
    TaskTemplate,
    TaskAssignment,
    TaskTimeLog,
    TaskChecklist,
    TeamMember,
    WorkloadSnapshot,
    TaskBoard,
    TaskLabel
)

from app.models.search import (
    SavedSearch,
    SearchAnalytics,
    SearchSuggestion,
    SearchFilterPreset,
    VendorMatchingScore,
    SearchIndexStatus
)

from app.models.calendar import (
    Calendar,
    CalendarEvent,
    RecurringEventRule,
    VendorAvailability,
    BookingConflict,
    CalendarSync,
    CalendarShare
)

from app.models.budget import (
    Budget,
    BudgetCategory,
    Expense,
    BudgetTemplate,
    BudgetAlert,
    BudgetSnapshot,
    CostForecast,
    CurrencyExchangeRate
)

from app.models.collaboration import (
    EventCollaborator,
    EventTeam,
    TeamMember,
    EventInvitation,
    ActivityLog,
    Comment,
    Mention,
    ShareLink,
    ResourceLock,
    CollaborationPresence
)

from app.models.recommendation import (
    UserBehavior,
    UserPreference,
    UserProfile,
    Recommendation,
    RecommendationFeedback,
    VendorMatchingProfile,
    EventVendorMatch,
    MLModel,
    Prediction,
    Experiment,
    ExperimentAssignment
)

from app.models.mobile import (
    MobileDevice,
    MobileSession,
    PushNotification,
    DeepLink,
    DeepLinkClick,
    OfflineSyncQueue,
    AppVersion,
    MobileFeatureFlag,
    MobileFeatureFlagAssignment,
    MobileAnalyticsEvent,
    MobileScreenView
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
    # Guest models
    "Guest",
    "GuestGroup",
    "GuestInvitation",
    "RSVPResponse",
    "SeatingArrangement",
    "GuestCheckIn",
    "DietaryRestriction",
    # Analytics models
    "AnalyticsSnapshot",
    "Report",
    "Metric",
    "Dashboard",
    "AuditLog",
    "EventCompletionRate",
    # Document models
    "Document",
    "DocumentFolder",
    "DocumentShare",
    "DocumentComment",
    "DocumentSignature",
    "DocumentTemplate",
    "DocumentActivity",
    # Task Collaboration models
    "TaskTemplate",
    "TaskAssignment",
    "TaskTimeLog",
    "TaskChecklist",
    "TeamMember",
    "WorkloadSnapshot",
    "TaskBoard",
    "TaskLabel",
    # Search & Discovery models
    "SavedSearch",
    "SearchAnalytics",
    "SearchSuggestion",
    "SearchFilterPreset",
    "VendorMatchingScore",
    "SearchIndexStatus",
    # Calendar & Scheduling models
    "Calendar",
    "CalendarEvent",
    "RecurringEventRule",
    "VendorAvailability",
    "BookingConflict",
    "CalendarSync",
    "CalendarShare",
    # Budget Management models
    "Budget",
    "BudgetCategory",
    "Expense",
    "BudgetTemplate",
    "BudgetAlert",
    "BudgetSnapshot",
    "CostForecast",
    "CurrencyExchangeRate",
    # Collaboration & Sharing models
    "EventCollaborator",
    "EventTeam",
    "TeamMember",
    "EventInvitation",
    "ActivityLog",
    "Comment",
    "Mention",
    "ShareLink",
    "ResourceLock",
    "CollaborationPresence",
    # AI & Recommendation Engine models
    "UserBehavior",
    "UserPreference",
    "UserProfile",
    "Recommendation",
    "RecommendationFeedback",
    "VendorMatchingProfile",
    "EventVendorMatch",
    "MLModel",
    "Prediction",
    "Experiment",
    "ExperimentAssignment",
    # Mobile App Foundation models
    "MobileDevice",
    "MobileSession",
    "PushNotification",
    "DeepLink",
    "DeepLinkClick",
    "OfflineSyncQueue",
    "AppVersion",
    "MobileFeatureFlag",
    "MobileFeatureFlagAssignment",
    "MobileAnalyticsEvent",
    "MobileScreenView",
]
