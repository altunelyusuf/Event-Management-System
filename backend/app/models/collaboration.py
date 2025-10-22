"""
Collaboration & Sharing Models
Sprint 16: Collaboration & Sharing System

Database models for team collaboration, sharing, permissions,
activity tracking, and real-time collaboration features.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    Text, ForeignKey, JSON, Index, UniqueConstraint, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


# ============================================================================
# Enums
# ============================================================================

class CollaboratorRole(str, enum.Enum):
    """Collaborator roles with increasing permissions"""
    VIEWER = "viewer"  # Can view only
    COMMENTER = "commenter"  # Can view and comment
    EDITOR = "editor"  # Can view, comment, and edit
    ADMIN = "admin"  # Can manage collaborators and settings
    OWNER = "owner"  # Full control


class InvitationStatus(str, enum.Enum):
    """Invitation status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ActivityType(str, enum.Enum):
    """Activity types for activity feed"""
    # Event activities
    EVENT_CREATED = "event_created"
    EVENT_UPDATED = "event_updated"
    EVENT_DELETED = "event_deleted"
    EVENT_PUBLISHED = "event_published"

    # Collaboration activities
    COLLABORATOR_ADDED = "collaborator_added"
    COLLABORATOR_REMOVED = "collaborator_removed"
    COLLABORATOR_ROLE_CHANGED = "collaborator_role_changed"

    # Task activities
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    TASK_ASSIGNED = "task_assigned"

    # Document activities
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_SHARED = "document_shared"
    DOCUMENT_DELETED = "document_deleted"

    # Comment activities
    COMMENT_ADDED = "comment_added"
    COMMENT_EDITED = "comment_edited"
    COMMENT_DELETED = "comment_deleted"

    # Booking activities
    BOOKING_CREATED = "booking_created"
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"

    # Budget activities
    EXPENSE_ADDED = "expense_added"
    EXPENSE_APPROVED = "expense_approved"
    BUDGET_EXCEEDED = "budget_exceeded"


class CommentableType(str, enum.Enum):
    """Types of entities that can be commented on"""
    EVENT = "event"
    TASK = "task"
    DOCUMENT = "document"
    BOOKING = "booking"
    EXPENSE = "expense"
    GUEST = "guest"


class ShareLinkType(str, enum.Enum):
    """Types of sharing links"""
    EVENT = "event"
    DOCUMENT = "document"
    CALENDAR = "calendar"
    GUEST_LIST = "guest_list"


class ShareLinkAccess(str, enum.Enum):
    """Access levels for sharing links"""
    VIEW = "view"
    EDIT = "edit"
    FULL = "full"


class ResourceLockType(str, enum.Enum):
    """Types of resources that can be locked"""
    EVENT = "event"
    TASK = "task"
    DOCUMENT = "document"
    BUDGET = "budget"


# ============================================================================
# Collaboration Models
# ============================================================================

class EventCollaborator(Base):
    """
    Event collaborators with role-based permissions.

    Manages access control for events, allowing multiple
    users to collaborate with different permission levels.
    """
    __tablename__ = "event_collaborators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Role and permissions
    role = Column(String(50), nullable=False, default="viewer")  # CollaboratorRole

    # Custom permissions (overrides role defaults)
    can_view = Column(Boolean, default=True)
    can_edit = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_share = Column(Boolean, default=False)
    can_manage_collaborators = Column(Boolean, default=False)
    can_manage_budget = Column(Boolean, default=False)
    can_manage_guests = Column(Boolean, default=False)
    can_manage_vendors = Column(Boolean, default=False)

    # Access details
    access_granted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    access_expires_at = Column(DateTime, nullable=True)  # Optional expiration
    last_accessed_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0)

    # Settings
    notification_preferences = Column(JSON, nullable=True)  # {email: true, push: true, frequency: 'instant'}
    is_favorite = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)

    # Metadata
    notes = Column(Text, nullable=True)  # Internal notes about this collaborator
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint('event_id', 'user_id', name='uq_event_collaborator'),
        Index('ix_event_collaborators_role', 'role'),
        Index('ix_event_collaborators_event_user', 'event_id', 'user_id'),
    )


class EventTeam(Base):
    """
    Teams for organizing event collaborators.

    Groups of users that can be assigned to events together,
    with shared roles and permissions.
    """
    __tablename__ = "event_teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Event reference
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)

    # Team details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color for UI
    icon = Column(String(50), nullable=True)  # Icon identifier

    # Team settings
    default_role = Column(String(50), nullable=False, default="viewer")  # Default role for members
    is_public = Column(Boolean, default=False)  # Can anyone join?
    requires_approval = Column(Boolean, default=True)  # Require admin approval to join

    # Team lead
    team_lead_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Metadata
    member_count = Column(Integer, default=0)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('ix_event_teams_event', 'event_id'),
    )


class TeamMember(Base):
    """
    Members of event teams.

    Links users to teams with individual roles and settings.
    """
    __tablename__ = "team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    team_id = Column(UUID(as_uuid=True), ForeignKey("event_teams.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Role in team
    role = Column(String(50), nullable=False, default="member")  # member, lead, admin

    # Membership details
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True)

    # Settings
    notification_enabled = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint('team_id', 'user_id', name='uq_team_member'),
        Index('ix_team_members_team_user', 'team_id', 'user_id'),
    )


class EventInvitation(Base):
    """
    Invitations to collaborate on events.

    Manages pending invitations with expiration and tracking.
    """
    __tablename__ = "event_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    invited_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)  # Null for email invites
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Invitation details
    email = Column(String(255), nullable=False, index=True)  # Email of invitee
    role = Column(String(50), nullable=False, default="viewer")  # Proposed role
    message = Column(Text, nullable=True)  # Personal message

    # Invitation token
    token = Column(String(255), unique=True, nullable=False, index=True)

    # Status
    status = Column(String(50), nullable=False, default="pending", index=True)  # InvitationStatus

    # Timing
    expires_at = Column(DateTime, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)

    # Response
    response_message = Column(Text, nullable=True)

    # Tracking
    email_sent = Column(Boolean, default=False)
    reminder_sent = Column(Boolean, default=False)
    reminder_count = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('ix_event_invitations_status_expires', 'status', 'expires_at'),
        Index('ix_event_invitations_token', 'token'),
    )


class ActivityLog(Base):
    """
    Activity feed for events and collaboration.

    Tracks all activities and changes for activity feeds,
    audit trails, and notifications.
    """
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)  # Actor

    # Activity details
    activity_type = Column(String(50), nullable=False, index=True)  # ActivityType
    title = Column(String(500), nullable=False)  # Human-readable title
    description = Column(Text, nullable=True)  # Detailed description

    # Entity references (polymorphic)
    entity_type = Column(String(50), nullable=True, index=True)  # Type of entity affected
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # ID of entity affected

    # Changes tracking
    changes = Column(JSON, nullable=True)  # {field: {old: value, new: value}}
    metadata = Column(JSON, nullable=True)  # Additional context

    # Visibility
    is_public = Column(Boolean, default=True)  # Show in public activity feed?
    is_system = Column(Boolean, default=False)  # System-generated activity?

    # Grouping (for collapsing similar activities)
    group_key = Column(String(255), nullable=True, index=True)  # For grouping similar activities
    parent_activity_id = Column(UUID(as_uuid=True), ForeignKey("activity_logs.id", ondelete="SET NULL"), nullable=True)

    # Metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_activity_logs_event_occurred', 'event_id', 'occurred_at'),
        Index('ix_activity_logs_user_occurred', 'user_id', 'occurred_at'),
        Index('ix_activity_logs_entity', 'entity_type', 'entity_id'),
        Index('ix_activity_logs_type_occurred', 'activity_type', 'occurred_at'),
    )


class Comment(Base):
    """
    Comments on events, tasks, documents, etc.

    Supports threaded discussions with mentions, reactions,
    and rich formatting.
    """
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Polymorphic entity reference
    commentable_type = Column(String(50), nullable=False, index=True)  # CommentableType
    commentable_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Event reference (for filtering)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True)

    # Author
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Threading
    parent_comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True)
    thread_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Root comment ID
    depth = Column(Integer, default=0)  # Nesting level

    # Content
    content = Column(Text, nullable=False)
    content_html = Column(Text, nullable=True)  # Rendered HTML
    mentions = Column(ARRAY(UUID(as_uuid=True)), nullable=True)  # User IDs mentioned

    # Attachments
    attachments = Column(JSON, nullable=True)  # [{url, filename, type, size}]

    # Status
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)  # For comment threads that are resolved

    # Engagement
    reaction_counts = Column(JSON, nullable=True)  # {thumbs_up: 5, heart: 3}
    reply_count = Column(Integer, default=0)

    # Metadata
    edited_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('ix_comments_commentable', 'commentable_type', 'commentable_id'),
        Index('ix_comments_thread', 'thread_id', 'created_at'),
        Index('ix_comments_parent', 'parent_comment_id'),
        Index('ix_comments_event_created', 'event_id', 'created_at'),
    )


class Mention(Base):
    """
    User mentions in comments and descriptions.

    Tracks @mentions for notifications and navigation.
    """
    __tablename__ = "mentions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    mentioned_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    mentioned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Source (where the mention occurred)
    source_type = Column(String(50), nullable=False, index=True)  # comment, description, note
    source_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Event reference (for filtering)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True)

    # Context
    context = Column(Text, nullable=True)  # Snippet of text around mention

    # Status
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('ix_mentions_user_read', 'mentioned_user_id', 'is_read'),
        Index('ix_mentions_source', 'source_type', 'source_id'),
    )


class ShareLink(Base):
    """
    Public/private sharing links for resources.

    Token-based access links with expiration, passwords,
    and access tracking.
    """
    __tablename__ = "share_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Creator
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Shared resource (polymorphic)
    resource_type = Column(String(50), nullable=False, index=True)  # ShareLinkType
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Event reference (for filtering)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True)

    # Link details
    token = Column(String(255), unique=True, nullable=False, index=True)
    short_code = Column(String(20), unique=True, nullable=True, index=True)  # Short URL code

    # Access control
    access_level = Column(String(50), nullable=False, default="view")  # ShareLinkAccess
    password_hash = Column(String(255), nullable=True)  # Optional password protection
    allowed_emails = Column(ARRAY(String), nullable=True)  # Restrict to specific emails
    allowed_domains = Column(ARRAY(String), nullable=True)  # Restrict to specific domains

    # Settings
    is_active = Column(Boolean, default=True, index=True)
    is_public = Column(Boolean, default=False)  # Listed publicly?
    allow_download = Column(Boolean, default=True)
    allow_comments = Column(Boolean, default=False)

    # Limits
    max_views = Column(Integer, nullable=True)  # Max number of views
    max_downloads = Column(Integer, nullable=True)  # Max number of downloads

    # Expiration
    expires_at = Column(DateTime, nullable=True, index=True)

    # Tracking
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)
    last_accessed_by = Column(String(255), nullable=True)  # Email or IP

    # Metadata
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('ix_share_links_resource', 'resource_type', 'resource_id'),
        Index('ix_share_links_token', 'token'),
        Index('ix_share_links_active_expires', 'is_active', 'expires_at'),
    )


class ResourceLock(Base):
    """
    Resource locks for collaborative editing.

    Prevents concurrent editing conflicts by locking
    resources while they're being edited.
    """
    __tablename__ = "resource_locks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Locked resource (polymorphic)
    resource_type = Column(String(50), nullable=False, index=True)  # ResourceLockType
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Lock owner
    locked_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Lock details
    lock_token = Column(String(255), unique=True, nullable=False)
    lock_reason = Column(String(500), nullable=True)

    # Timing
    locked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)  # Auto-release after timeout
    last_heartbeat_at = Column(DateTime, nullable=False, default=datetime.utcnow)  # Keep-alive

    # Status
    is_active = Column(Boolean, default=True, index=True)
    released_at = Column(DateTime, nullable=True)

    # Metadata
    session_id = Column(String(255), nullable=True)  # Browser session
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint('resource_type', 'resource_id', 'is_active', name='uq_active_resource_lock'),
        Index('ix_resource_locks_resource', 'resource_type', 'resource_id'),
        Index('ix_resource_locks_user', 'locked_by'),
        Index('ix_resource_locks_active_expires', 'is_active', 'expires_at'),
    )


class CollaborationPresence(Base):
    """
    Real-time presence tracking for collaborators.

    Tracks who is currently viewing/editing resources
    for real-time collaboration awareness.
    """
    __tablename__ = "collaboration_presence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User and session
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)

    # Presence location (polymorphic)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Event reference (for filtering)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True)

    # Presence state
    status = Column(String(50), nullable=False, default="viewing")  # viewing, editing, idle
    cursor_position = Column(JSON, nullable=True)  # For real-time cursor tracking
    selection = Column(JSON, nullable=True)  # Current selection

    # Timing
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    is_active = Column(Boolean, default=True, index=True)

    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'session_id', 'resource_type', 'resource_id', name='uq_presence'),
        Index('ix_presence_resource_active', 'resource_type', 'resource_id', 'is_active'),
        Index('ix_presence_user_active', 'user_id', 'is_active'),
        Index('ix_presence_last_seen', 'last_seen_at'),
    )
