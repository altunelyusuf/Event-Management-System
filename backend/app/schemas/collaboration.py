"""
Collaboration & Sharing Schemas
Sprint 16: Collaboration & Sharing System

Pydantic schemas for collaboration, sharing, permissions,
activity tracking, and real-time collaboration features.
"""

from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# EventCollaborator Schemas
# ============================================================================

class EventCollaboratorBase(BaseModel):
    """Base schema for event collaborators"""
    role: str = Field("viewer", description="Collaborator role")
    can_view: bool = Field(True)
    can_edit: bool = Field(False)
    can_delete: bool = Field(False)
    can_share: bool = Field(False)
    can_manage_collaborators: bool = Field(False)
    can_manage_budget: bool = Field(False)
    can_manage_guests: bool = Field(False)
    can_manage_vendors: bool = Field(False)
    notes: Optional[str] = None


class EventCollaboratorCreate(EventCollaboratorBase):
    """Schema for creating event collaborator"""
    event_id: UUID
    user_id: UUID
    access_expires_at: Optional[datetime] = None
    notification_preferences: Optional[Dict[str, Any]] = Field(
        default={"email": True, "push": True, "frequency": "instant"}
    )


class EventCollaboratorUpdate(BaseModel):
    """Schema for updating event collaborator"""
    role: Optional[str] = None
    can_view: Optional[bool] = None
    can_edit: Optional[bool] = None
    can_delete: Optional[bool] = None
    can_share: Optional[bool] = None
    can_manage_collaborators: Optional[bool] = None
    can_manage_budget: Optional[bool] = None
    can_manage_guests: Optional[bool] = None
    can_manage_vendors: Optional[bool] = None
    access_expires_at: Optional[datetime] = None
    notification_preferences: Optional[Dict[str, Any]] = None
    is_favorite: Optional[bool] = None
    is_pinned: Optional[bool] = None
    notes: Optional[str] = None


class EventCollaboratorResponse(EventCollaboratorBase):
    """Schema for event collaborator response"""
    id: UUID
    event_id: UUID
    user_id: UUID
    invited_by: Optional[UUID]
    access_granted_at: datetime
    access_expires_at: Optional[datetime]
    last_accessed_at: Optional[datetime]
    access_count: int
    is_favorite: bool
    is_pinned: bool
    notification_preferences: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollaboratorWithUser(EventCollaboratorResponse):
    """Collaborator with user details"""
    user: Optional[Dict[str, Any]] = None  # User info from join


class CollaboratorPermissionCheck(BaseModel):
    """Schema for checking collaborator permissions"""
    user_id: UUID
    event_id: UUID
    permission: str = Field(..., description="Permission to check (can_view, can_edit, etc)")


# ============================================================================
# EventTeam Schemas
# ============================================================================

class EventTeamBase(BaseModel):
    """Base schema for event teams"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    color: Optional[str] = Field(None, regex="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = None
    default_role: str = Field("viewer")
    is_public: bool = Field(False)
    requires_approval: bool = Field(True)


class EventTeamCreate(EventTeamBase):
    """Schema for creating event team"""
    event_id: UUID
    team_lead_id: Optional[UUID] = None


class EventTeamUpdate(BaseModel):
    """Schema for updating event team"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    color: Optional[str] = Field(None, regex="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = None
    default_role: Optional[str] = None
    is_public: Optional[bool] = None
    requires_approval: Optional[bool] = None
    team_lead_id: Optional[UUID] = None


class EventTeamResponse(EventTeamBase):
    """Schema for event team response"""
    id: UUID
    event_id: UUID
    team_lead_id: Optional[UUID]
    member_count: int
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventTeamWithMembers(EventTeamResponse):
    """Team with member details"""
    members: Optional[List[Dict[str, Any]]] = []


# ============================================================================
# TeamMember Schemas
# ============================================================================

class TeamMemberBase(BaseModel):
    """Base schema for team members"""
    role: str = Field("member")
    notification_enabled: bool = Field(True)


class TeamMemberCreate(TeamMemberBase):
    """Schema for adding team member"""
    team_id: UUID
    user_id: UUID


class TeamMemberUpdate(BaseModel):
    """Schema for updating team member"""
    role: Optional[str] = None
    notification_enabled: Optional[bool] = None
    is_active: Optional[bool] = None


class TeamMemberResponse(TeamMemberBase):
    """Schema for team member response"""
    id: UUID
    team_id: UUID
    user_id: UUID
    joined_at: datetime
    invited_by: Optional[UUID]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# EventInvitation Schemas
# ============================================================================

class EventInvitationBase(BaseModel):
    """Base schema for event invitations"""
    email: EmailStr
    role: str = Field("viewer")
    message: Optional[str] = Field(None, max_length=1000)


class EventInvitationCreate(EventInvitationBase):
    """Schema for creating event invitation"""
    event_id: UUID
    expires_in_hours: int = Field(168, gt=0, le=720)  # Default 7 days, max 30 days


class EventInvitationBulkCreate(BaseModel):
    """Schema for bulk invitations"""
    event_id: UUID
    invitations: List[EventInvitationBase]
    expires_in_hours: int = Field(168, gt=0, le=720)


class EventInvitationUpdate(BaseModel):
    """Schema for updating invitation"""
    status: Optional[str] = None
    response_message: Optional[str] = None


class EventInvitationResponse(EventInvitationBase):
    """Schema for invitation response"""
    id: UUID
    event_id: UUID
    invited_user_id: Optional[UUID]
    invited_by: Optional[UUID]
    token: str
    status: str
    expires_at: datetime
    sent_at: datetime
    responded_at: Optional[datetime]
    response_message: Optional[str]
    email_sent: bool
    reminder_sent: bool
    reminder_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvitationAcceptRequest(BaseModel):
    """Schema for accepting invitation"""
    token: str
    response_message: Optional[str] = None


class InvitationDeclineRequest(BaseModel):
    """Schema for declining invitation"""
    token: str
    response_message: Optional[str] = Field(None, max_length=500)


# ============================================================================
# ActivityLog Schemas
# ============================================================================

class ActivityLogBase(BaseModel):
    """Base schema for activity logs"""
    activity_type: str
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    changes: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_public: bool = Field(True)


class ActivityLogCreate(ActivityLogBase):
    """Schema for creating activity log"""
    event_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    group_key: Optional[str] = None
    parent_activity_id: Optional[UUID] = None


class ActivityLogResponse(ActivityLogBase):
    """Schema for activity log response"""
    id: UUID
    event_id: Optional[UUID]
    user_id: Optional[UUID]
    is_system: bool
    group_key: Optional[str]
    parent_activity_id: Optional[UUID]
    ip_address: Optional[str]
    occurred_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityLogWithUser(ActivityLogResponse):
    """Activity log with user details"""
    user: Optional[Dict[str, Any]] = None


class ActivityFeedRequest(BaseModel):
    """Schema for activity feed request"""
    event_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    activity_types: Optional[List[str]] = None
    entity_type: Optional[str] = None
    is_public: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(50, gt=0, le=200)
    offset: int = Field(0, ge=0)


class ActivityFeedResponse(BaseModel):
    """Schema for activity feed response"""
    activities: List[ActivityLogWithUser]
    total: int
    limit: int
    offset: int


# ============================================================================
# Comment Schemas
# ============================================================================

class CommentBase(BaseModel):
    """Base schema for comments"""
    content: str = Field(..., min_length=1, max_length=5000)
    mentions: Optional[List[UUID]] = []


class CommentCreate(CommentBase):
    """Schema for creating comment"""
    commentable_type: str
    commentable_id: UUID
    event_id: Optional[UUID] = None
    parent_comment_id: Optional[UUID] = None
    attachments: Optional[List[Dict[str, Any]]] = []


class CommentUpdate(BaseModel):
    """Schema for updating comment"""
    content: Optional[str] = Field(None, min_length=1, max_length=5000)
    is_pinned: Optional[bool] = None
    is_resolved: Optional[bool] = None


class CommentResponse(CommentBase):
    """Schema for comment response"""
    id: UUID
    commentable_type: str
    commentable_id: UUID
    event_id: Optional[UUID]
    user_id: Optional[UUID]
    parent_comment_id: Optional[UUID]
    thread_id: Optional[UUID]
    depth: int
    content_html: Optional[str]
    attachments: Optional[List[Dict[str, Any]]]
    is_edited: bool
    is_deleted: bool
    is_pinned: bool
    is_resolved: bool
    reaction_counts: Optional[Dict[str, int]]
    reply_count: int
    edited_at: Optional[datetime]
    resolved_at: Optional[datetime]
    resolved_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommentWithUser(CommentResponse):
    """Comment with user details"""
    user: Optional[Dict[str, Any]] = None
    replies: Optional[List['CommentWithUser']] = []


class CommentReactionRequest(BaseModel):
    """Schema for adding/removing reaction"""
    reaction_type: str = Field(..., regex="^[a-z_]+$")


class CommentThreadResponse(BaseModel):
    """Schema for comment thread"""
    root_comment: CommentWithUser
    replies: List[CommentWithUser]
    total_replies: int


# ============================================================================
# Mention Schemas
# ============================================================================

class MentionCreate(BaseModel):
    """Schema for creating mention"""
    mentioned_user_id: UUID
    source_type: str
    source_id: UUID
    event_id: Optional[UUID] = None
    context: Optional[str] = None


class MentionResponse(BaseModel):
    """Schema for mention response"""
    id: UUID
    mentioned_user_id: UUID
    mentioned_by: Optional[UUID]
    source_type: str
    source_id: UUID
    event_id: Optional[UUID]
    context: Optional[str]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class MentionWithDetails(MentionResponse):
    """Mention with user and source details"""
    mentioned_by_user: Optional[Dict[str, Any]] = None
    source: Optional[Dict[str, Any]] = None


class MentionMarkReadRequest(BaseModel):
    """Schema for marking mentions as read"""
    mention_ids: List[UUID]


# ============================================================================
# ShareLink Schemas
# ============================================================================

class ShareLinkBase(BaseModel):
    """Base schema for share links"""
    resource_type: str
    resource_id: UUID
    access_level: str = Field("view")
    password: Optional[str] = Field(None, min_length=4, max_length=100)
    allowed_emails: Optional[List[EmailStr]] = None
    allowed_domains: Optional[List[str]] = None
    is_public: bool = Field(False)
    allow_download: bool = Field(True)
    allow_comments: bool = Field(False)
    max_views: Optional[int] = Field(None, gt=0)
    max_downloads: Optional[int] = Field(None, gt=0)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None


class ShareLinkCreate(ShareLinkBase):
    """Schema for creating share link"""
    event_id: Optional[UUID] = None
    expires_in_hours: Optional[int] = Field(None, gt=0, le=8760)  # Max 1 year


class ShareLinkUpdate(BaseModel):
    """Schema for updating share link"""
    access_level: Optional[str] = None
    password: Optional[str] = Field(None, min_length=4, max_length=100)
    allowed_emails: Optional[List[EmailStr]] = None
    allowed_domains: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    allow_download: Optional[bool] = None
    allow_comments: Optional[bool] = None
    max_views: Optional[int] = Field(None, gt=0)
    max_downloads: Optional[int] = Field(None, gt=0)
    expires_at: Optional[datetime] = None
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None


class ShareLinkResponse(BaseModel):
    """Schema for share link response"""
    id: UUID
    created_by: Optional[UUID]
    resource_type: str
    resource_id: UUID
    event_id: Optional[UUID]
    token: str
    short_code: Optional[str]
    access_level: str
    password_protected: bool = Field(False)
    allowed_emails: Optional[List[str]]
    allowed_domains: Optional[List[str]]
    is_active: bool
    is_public: bool
    allow_download: bool
    allow_comments: bool
    max_views: Optional[int]
    max_downloads: Optional[int]
    expires_at: Optional[datetime]
    view_count: int
    download_count: int
    last_accessed_at: Optional[datetime]
    title: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @validator('password_protected', pre=True, always=True)
    def check_password_protected(cls, v, values):
        # Will be set based on whether password_hash exists
        return v


class ShareLinkAccessRequest(BaseModel):
    """Schema for accessing share link"""
    token: str
    password: Optional[str] = None
    email: Optional[EmailStr] = None


class ShareLinkAccessResponse(BaseModel):
    """Schema for share link access response"""
    resource_type: str
    resource_id: UUID
    access_level: str
    resource: Optional[Dict[str, Any]] = None
    can_download: bool
    can_comment: bool


# ============================================================================
# ResourceLock Schemas
# ============================================================================

class ResourceLockCreate(BaseModel):
    """Schema for acquiring resource lock"""
    resource_type: str
    resource_id: UUID
    lock_reason: Optional[str] = Field(None, max_length=500)
    timeout_seconds: int = Field(300, gt=0, le=3600)  # Default 5 min, max 1 hour


class ResourceLockResponse(BaseModel):
    """Schema for resource lock response"""
    id: UUID
    resource_type: str
    resource_id: UUID
    locked_by: UUID
    lock_token: str
    lock_reason: Optional[str]
    locked_at: datetime
    expires_at: datetime
    last_heartbeat_at: datetime
    is_active: bool
    released_at: Optional[datetime]

    class Config:
        from_attributes = True


class ResourceLockHeartbeat(BaseModel):
    """Schema for lock heartbeat/keep-alive"""
    lock_token: str


class ResourceLockRelease(BaseModel):
    """Schema for releasing lock"""
    lock_token: str


class ResourceLockCheck(BaseModel):
    """Schema for checking lock status"""
    resource_type: str
    resource_id: UUID


class ResourceLockStatus(BaseModel):
    """Schema for lock status response"""
    is_locked: bool
    locked_by: Optional[UUID] = None
    locked_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    can_override: bool = False


# ============================================================================
# CollaborationPresence Schemas
# ============================================================================

class CollaborationPresenceCreate(BaseModel):
    """Schema for creating presence"""
    resource_type: str
    resource_id: UUID
    event_id: Optional[UUID] = None
    status: str = Field("viewing")
    cursor_position: Optional[Dict[str, Any]] = None
    selection: Optional[Dict[str, Any]] = None


class CollaborationPresenceUpdate(BaseModel):
    """Schema for updating presence"""
    status: Optional[str] = None
    cursor_position: Optional[Dict[str, Any]] = None
    selection: Optional[Dict[str, Any]] = None


class CollaborationPresenceResponse(BaseModel):
    """Schema for presence response"""
    id: UUID
    user_id: UUID
    session_id: str
    resource_type: str
    resource_id: UUID
    event_id: Optional[UUID]
    status: str
    cursor_position: Optional[Dict[str, Any]]
    selection: Optional[Dict[str, Any]]
    joined_at: datetime
    last_seen_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class CollaborationPresenceWithUser(CollaborationPresenceResponse):
    """Presence with user details"""
    user: Optional[Dict[str, Any]] = None


class PresenceListRequest(BaseModel):
    """Schema for getting presence list"""
    resource_type: str
    resource_id: UUID


class PresenceListResponse(BaseModel):
    """Schema for presence list response"""
    active_users: List[CollaborationPresenceWithUser]
    total_active: int


# ============================================================================
# Bulk and Analytics Schemas
# ============================================================================

class BulkCollaboratorAdd(BaseModel):
    """Schema for bulk adding collaborators"""
    event_id: UUID
    collaborators: List[Dict[str, Any]]  # [{user_id, role, permissions}]


class BulkCollaboratorRemove(BaseModel):
    """Schema for bulk removing collaborators"""
    event_id: UUID
    user_ids: List[UUID]


class CollaboratorAnalytics(BaseModel):
    """Schema for collaborator analytics"""
    event_id: UUID
    total_collaborators: int
    active_collaborators: int
    role_distribution: Dict[str, int]
    recent_activity: List[ActivityLogResponse]
    top_contributors: List[Dict[str, Any]]


class EventShareSettings(BaseModel):
    """Schema for event sharing settings"""
    event_id: UUID
    is_public: bool = Field(False)
    allow_collaboration_requests: bool = Field(False)
    default_collaborator_role: str = Field("viewer")
    require_approval: bool = Field(True)
    allowed_domains: Optional[List[str]] = None


class EventShareSettingsResponse(EventShareSettings):
    """Schema for event share settings response"""
    id: UUID
    updated_at: datetime
    updated_by: Optional[UUID]

    class Config:
        from_attributes = True
