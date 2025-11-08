"""
Task Collaboration Models
Sprint 12: Advanced Task Management & Team Collaboration

Extends the basic task system with advanced features:
- Task templates for reusability
- Enhanced task assignments with workload tracking
- Time logging and tracking
- Task checklists
- Team management with roles
- Workload snapshots
- Task boards (Kanban/Scrum)
- Task labels and organization
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    Text, ForeignKey, JSON, UniqueConstraint, Index, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import enum

from app.core.database import Base


# ============================================================================
# Enums
# ============================================================================

class TaskPriorityLevel(str, enum.Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskAssignmentStatus(str, enum.Enum):
    """Assignment status"""
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DECLINED = "declined"


class TeamMemberRole(str, enum.Enum):
    """Team member roles"""
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


class TaskBoardType(str, enum.Enum):
    """Task board types"""
    KANBAN = "kanban"
    SCRUM = "scrum"
    LIST = "list"
    TIMELINE = "timeline"
    CALENDAR = "calendar"


class TimeLogType(str, enum.Enum):
    """Time log entry types"""
    WORK = "work"
    BREAK = "break"
    MEETING = "meeting"
    RESEARCH = "research"
    REVIEW = "review"
    OTHER = "other"


class TemplateCategory(str, enum.Enum):
    """Task template categories"""
    EVENT_PLANNING = "event_planning"
    VENDOR_MANAGEMENT = "vendor_management"
    GUEST_MANAGEMENT = "guest_management"
    FINANCIAL = "financial"
    MARKETING = "marketing"
    LOGISTICS = "logistics"
    CUSTOM = "custom"


# ============================================================================
# Task Template Models
# ============================================================================

class TaskTemplate(Base):
    """
    Reusable task templates for common workflows.

    Templates can include predefined:
    - Task structure
    - Checklists
    - Estimated duration
    - Default assignments
    - Dependencies
    """
    __tablename__ = "task_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic info
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), default=TemplateCategory.CUSTOM.value)

    # Template content
    default_priority = Column(String(20), default=TaskPriorityLevel.MEDIUM.value)
    estimated_hours = Column(Float, nullable=True)

    # Template structure (JSON)
    checklist_items = Column(JSON, default=list)  # [{title, description, order}]
    default_assignments = Column(JSON, default=list)  # [{role, estimated_hours}]
    dependency_rules = Column(JSON, default=list)  # [{depends_on_template_id, type}]
    custom_fields = Column(JSON, default={})

    # Metadata
    is_public = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)  # System templates (cannot be deleted)
    use_count = Column(Integer, default=0)

    # Ownership
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True)  # Event-specific template

    # Tags and organization
    tags = Column(ARRAY(String(50)), default=list)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    event = relationship("Event", foreign_keys=[event_id])

    # Indexes
    __table_args__ = (
        Index('idx_task_template_category', 'category'),
        Index('idx_task_template_created_by', 'created_by'),
        Index('idx_task_template_is_public', 'is_public'),
    )


# ============================================================================
# Enhanced Task Assignment
# ============================================================================

class TaskAssignment(Base):
    """
    Enhanced task assignments with detailed tracking.

    Extends basic task assignment with:
    - Assignment status workflow
    - Time estimates vs actual
    - Workload calculation
    - Assignment history
    """
    __tablename__ = "task_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Assignment details
    status = Column(String(20), default=TaskAssignmentStatus.ASSIGNED.value)
    role = Column(String(100), nullable=True)  # e.g., "Designer", "Coordinator"

    # Time tracking
    estimated_hours = Column(Float, nullable=True)
    actual_hours = Column(Float, default=0.0)

    # Workload percentage (0-100)
    workload_percentage = Column(Integer, default=100)  # % of task this person is responsible for

    # Status timestamps
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    declined_at = Column(DateTime, nullable=True)

    # Notes
    assignment_note = Column(Text, nullable=True)
    decline_reason = Column(Text, nullable=True)

    # Notifications
    notify_on_assign = Column(Boolean, default=True)
    notify_on_due = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    task = relationship("Task", back_populates="assignments")
    assignee = relationship("User", foreign_keys=[user_id], backref="task_assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])
    time_logs = relationship("TaskTimeLog", back_populates="assignment", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_task_assignment_task', 'task_id'),
        Index('idx_task_assignment_user', 'user_id'),
        Index('idx_task_assignment_status', 'status'),
        UniqueConstraint('task_id', 'user_id', name='uq_task_user_assignment'),
    )


# ============================================================================
# Time Tracking
# ============================================================================

class TaskTimeLog(Base):
    """
    Time logging for task assignments.

    Tracks:
    - Work sessions
    - Time spent on tasks
    - Breaks and interruptions
    - Automatic vs manual entries
    """
    __tablename__ = "task_time_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("task_assignments.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Time tracking
    type = Column(String(20), default=TimeLogType.WORK.value)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)  # Calculated or manual

    # Entry details
    description = Column(Text, nullable=True)
    is_manual = Column(Boolean, default=False)
    is_billable = Column(Boolean, default=True)

    # Location (if tracked)
    location = Column(String(200), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    task = relationship("Task", backref="time_logs")
    assignment = relationship("TaskAssignment", back_populates="time_logs")
    user = relationship("User", backref="time_logs")

    # Indexes
    __table_args__ = (
        Index('idx_task_time_log_task', 'task_id'),
        Index('idx_task_time_log_user', 'user_id'),
        Index('idx_task_time_log_started', 'started_at'),
    )


# ============================================================================
# Task Checklist
# ============================================================================

class TaskChecklist(Base):
    """
    Checklist items within tasks.

    Allows breaking down tasks into smaller steps:
    - Ordered checklist items
    - Completion tracking
    - Assignment to specific users
    - Dependencies between items
    """
    __tablename__ = "task_checklists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Item details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, default=0)

    # Status
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Dependencies
    depends_on_item_id = Column(UUID(as_uuid=True), ForeignKey("task_checklists.id"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    task = relationship("Task", backref="checklist_items")
    assignee = relationship("User", foreign_keys=[assigned_to])
    completer = relationship("User", foreign_keys=[completed_by])
    depends_on = relationship("TaskChecklist", remote_side=[id], backref="dependent_items")

    # Indexes
    __table_args__ = (
        Index('idx_task_checklist_task', 'task_id'),
        Index('idx_task_checklist_order', 'task_id', 'order'),
    )


# ============================================================================
# Team Management
# ============================================================================

class TeamMember(Base):
    """
    Team members for event collaboration.

    Manages:
    - Team roles and permissions
    - Workload capacity
    - Availability
    - Skills and expertise
    """
    __tablename__ = "team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Role and permissions
    role = Column(String(20), default=TeamMemberRole.MEMBER.value)
    custom_role_name = Column(String(100), nullable=True)

    # Permissions (JSON)
    permissions = Column(JSON, default={
        "can_create_tasks": True,
        "can_assign_tasks": False,
        "can_delete_tasks": False,
        "can_manage_team": False,
        "can_view_analytics": True,
        "can_manage_budget": False
    })

    # Workload settings
    max_hours_per_week = Column(Float, default=40.0)
    hourly_rate = Column(Float, nullable=True)  # For cost calculation

    # Skills and expertise
    skills = Column(ARRAY(String(50)), default=list)
    expertise_areas = Column(ARRAY(String(50)), default=list)

    # Availability
    is_active = Column(Boolean, default=True)
    available_from = Column(DateTime, nullable=True)
    available_until = Column(DateTime, nullable=True)

    # Notes
    bio = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    removed_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    event = relationship("Event", backref="team_members")
    user = relationship("User", foreign_keys=[user_id], backref="team_memberships")
    added_by_user = relationship("User", foreign_keys=[added_by])
    workload_snapshots = relationship("WorkloadSnapshot", back_populates="team_member", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_team_member_event', 'event_id'),
        Index('idx_team_member_user', 'user_id'),
        Index('idx_team_member_role', 'role'),
        UniqueConstraint('event_id', 'user_id', name='uq_event_team_member'),
    )


# ============================================================================
# Workload Tracking
# ============================================================================

class WorkloadSnapshot(Base):
    """
    Periodic snapshots of team member workload.

    Tracks:
    - Current task assignments
    - Estimated vs actual hours
    - Capacity utilization
    - Burndown data
    """
    __tablename__ = "workload_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    team_member_id = Column(UUID(as_uuid=True), ForeignKey("team_members.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)

    # Snapshot timing
    snapshot_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    week_start_date = Column(DateTime, nullable=False)
    week_end_date = Column(DateTime, nullable=False)

    # Workload metrics
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    in_progress_tasks = Column(Integer, default=0)

    # Hours
    estimated_hours = Column(Float, default=0.0)
    actual_hours = Column(Float, default=0.0)
    remaining_hours = Column(Float, default=0.0)

    # Capacity
    available_hours = Column(Float, default=0.0)
    utilization_percentage = Column(Float, default=0.0)  # actual / available

    # Task breakdown by priority (JSON)
    priority_breakdown = Column(JSON, default={
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0
    })

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    team_member = relationship("TeamMember", back_populates="workload_snapshots")
    event = relationship("Event")

    # Indexes
    __table_args__ = (
        Index('idx_workload_snapshot_team_member', 'team_member_id'),
        Index('idx_workload_snapshot_date', 'snapshot_date'),
        Index('idx_workload_snapshot_week', 'week_start_date', 'week_end_date'),
    )


# ============================================================================
# Task Board Management
# ============================================================================

class TaskBoard(Base):
    """
    Task boards for organizing tasks (Kanban, Scrum, etc.).

    Features:
    - Multiple board types
    - Custom columns/statuses
    - Board sharing
    - Filters and views
    """
    __tablename__ = "task_boards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic info
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(20), default=TaskBoardType.KANBAN.value)

    # Ownership
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Board configuration (JSON)
    columns = Column(JSON, default=[
        {"id": "todo", "name": "To Do", "order": 0},
        {"id": "in_progress", "name": "In Progress", "order": 1},
        {"id": "done", "name": "Done", "order": 2}
    ])

    # Filters and settings (JSON)
    default_filters = Column(JSON, default={})
    settings = Column(JSON, default={
        "show_completed": True,
        "group_by": None,
        "sort_by": "priority"
    })

    # Visibility
    is_default = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    archived_at = Column(DateTime, nullable=True)

    # Relationships
    event = relationship("Event", backref="task_boards")
    creator = relationship("User")
    labels = relationship("TaskLabel", back_populates="board", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_task_board_event', 'event_id'),
        Index('idx_task_board_type', 'type'),
    )


# ============================================================================
# Task Labels
# ============================================================================

class TaskLabel(Base):
    """
    Labels/tags for task organization.

    Features:
    - Color coding
    - Board-specific or global
    - Hierarchical labels
    """
    __tablename__ = "task_labels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Label details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#808080")  # Hex color code

    # Scope
    board_id = Column(UUID(as_uuid=True), ForeignKey("task_boards.id", ondelete="CASCADE"), nullable=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=True)

    # Hierarchy
    parent_label_id = Column(UUID(as_uuid=True), ForeignKey("task_labels.id"), nullable=True)

    # Metadata
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    board = relationship("TaskBoard", back_populates="labels")
    event = relationship("Event")
    parent_label = relationship("TaskLabel", remote_side=[id], backref="child_labels")

    # Indexes
    __table_args__ = (
        Index('idx_task_label_board', 'board_id'),
        Index('idx_task_label_event', 'event_id'),
    )
