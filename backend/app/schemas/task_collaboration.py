"""
Task Collaboration Schemas
Sprint 12: Advanced Task Management & Team Collaboration

Pydantic schemas for request validation and response serialization.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# Task Template Schemas
# ============================================================================

class TaskTemplateCreate(BaseModel):
    """Create a new task template"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = "custom"

    default_priority: str = "medium"
    estimated_hours: Optional[float] = Field(None, ge=0)

    checklist_items: List[Dict[str, Any]] = Field(default_factory=list)
    default_assignments: List[Dict[str, Any]] = Field(default_factory=list)
    dependency_rules: List[Dict[str, Any]] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)

    is_public: bool = False
    event_id: Optional[UUID] = None
    tags: List[str] = Field(default_factory=list)


class TaskTemplateUpdate(BaseModel):
    """Update an existing task template"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None

    default_priority: Optional[str] = None
    estimated_hours: Optional[float] = Field(None, ge=0)

    checklist_items: Optional[List[Dict[str, Any]]] = None
    default_assignments: Optional[List[Dict[str, Any]]] = None
    dependency_rules: Optional[List[Dict[str, Any]]] = None
    custom_fields: Optional[Dict[str, Any]] = None

    is_public: Optional[bool] = None
    tags: Optional[List[str]] = None


class TaskTemplateResponse(BaseModel):
    """Task template response"""
    id: UUID
    name: str
    description: Optional[str]
    category: str

    default_priority: str
    estimated_hours: Optional[float]

    checklist_items: List[Dict[str, Any]]
    default_assignments: List[Dict[str, Any]]
    dependency_rules: List[Dict[str, Any]]
    custom_fields: Dict[str, Any]

    is_public: bool
    is_system: bool
    use_count: int

    created_by: UUID
    event_id: Optional[UUID]
    tags: List[str]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Task Assignment Schemas
# ============================================================================

class TaskAssignmentCreate(BaseModel):
    """Create a new task assignment"""
    task_id: UUID
    user_id: UUID
    role: Optional[str] = None
    estimated_hours: Optional[float] = Field(None, ge=0)
    workload_percentage: int = Field(100, ge=0, le=100)
    assignment_note: Optional[str] = None
    notify_on_assign: bool = True
    notify_on_due: bool = True


class TaskAssignmentUpdate(BaseModel):
    """Update task assignment"""
    status: Optional[str] = None
    role: Optional[str] = None
    estimated_hours: Optional[float] = Field(None, ge=0)
    workload_percentage: Optional[int] = Field(None, ge=0, le=100)
    decline_reason: Optional[str] = None


class TaskAssignmentResponse(BaseModel):
    """Task assignment response"""
    id: UUID
    task_id: UUID
    user_id: UUID
    assigned_by: UUID

    status: str
    role: Optional[str]

    estimated_hours: Optional[float]
    actual_hours: float
    workload_percentage: int

    assigned_at: datetime
    accepted_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    declined_at: Optional[datetime]

    assignment_note: Optional[str]
    decline_reason: Optional[str]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Time Tracking Schemas
# ============================================================================

class TimeLogCreate(BaseModel):
    """Create a time log entry"""
    task_id: UUID
    assignment_id: Optional[UUID] = None
    type: str = "work"
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    is_manual: bool = False
    is_billable: bool = True
    location: Optional[str] = None

    @validator('ended_at')
    def validate_end_time(cls, v, values):
        if v and 'started_at' in values and v < values['started_at']:
            raise ValueError('ended_at must be after started_at')
        return v


class TimeLogUpdate(BaseModel):
    """Update time log entry"""
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    is_billable: Optional[bool] = None


class TimeLogResponse(BaseModel):
    """Time log response"""
    id: UUID
    task_id: UUID
    assignment_id: Optional[UUID]
    user_id: UUID

    type: str
    started_at: datetime
    ended_at: Optional[datetime]
    duration_minutes: Optional[int]

    description: Optional[str]
    is_manual: bool
    is_billable: bool
    location: Optional[str]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Task Checklist Schemas
# ============================================================================

class ChecklistItemCreate(BaseModel):
    """Create a checklist item"""
    task_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    assigned_to: Optional[UUID] = None
    order: int = 0
    depends_on_item_id: Optional[UUID] = None


class ChecklistItemUpdate(BaseModel):
    """Update checklist item"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    assigned_to: Optional[UUID] = None
    order: Optional[int] = None
    is_completed: Optional[bool] = None


class ChecklistItemResponse(BaseModel):
    """Checklist item response"""
    id: UUID
    task_id: UUID
    assigned_to: Optional[UUID]

    title: str
    description: Optional[str]
    order: int

    is_completed: bool
    completed_at: Optional[datetime]
    completed_by: Optional[UUID]

    depends_on_item_id: Optional[UUID]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Team Member Schemas
# ============================================================================

class TeamMemberCreate(BaseModel):
    """Add a team member"""
    event_id: UUID
    user_id: UUID
    role: str = "member"
    custom_role_name: Optional[str] = None

    permissions: Dict[str, bool] = Field(default_factory=lambda: {
        "can_create_tasks": True,
        "can_assign_tasks": False,
        "can_delete_tasks": False,
        "can_manage_team": False,
        "can_view_analytics": True,
        "can_manage_budget": False
    })

    max_hours_per_week: float = Field(40.0, ge=0)
    hourly_rate: Optional[float] = Field(None, ge=0)

    skills: List[str] = Field(default_factory=list)
    expertise_areas: List[str] = Field(default_factory=list)

    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None

    bio: Optional[str] = None
    notes: Optional[str] = None


class TeamMemberUpdate(BaseModel):
    """Update team member"""
    role: Optional[str] = None
    custom_role_name: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None

    max_hours_per_week: Optional[float] = Field(None, ge=0)
    hourly_rate: Optional[float] = Field(None, ge=0)

    skills: Optional[List[str]] = None
    expertise_areas: Optional[List[str]] = None

    is_active: Optional[bool] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None

    bio: Optional[str] = None
    notes: Optional[str] = None


class TeamMemberResponse(BaseModel):
    """Team member response"""
    id: UUID
    event_id: UUID
    user_id: UUID
    added_by: UUID

    role: str
    custom_role_name: Optional[str]
    permissions: Dict[str, bool]

    max_hours_per_week: float
    hourly_rate: Optional[float]

    skills: List[str]
    expertise_areas: List[str]

    is_active: bool
    available_from: Optional[datetime]
    available_until: Optional[datetime]

    bio: Optional[str]
    notes: Optional[str]

    joined_at: datetime
    removed_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Workload Schemas
# ============================================================================

class WorkloadSnapshotResponse(BaseModel):
    """Workload snapshot response"""
    id: UUID
    team_member_id: UUID
    event_id: UUID

    snapshot_date: datetime
    week_start_date: datetime
    week_end_date: datetime

    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int

    estimated_hours: float
    actual_hours: float
    remaining_hours: float

    available_hours: float
    utilization_percentage: float

    priority_breakdown: Dict[str, int]

    created_at: datetime

    class Config:
        from_attributes = True


class WorkloadQuery(BaseModel):
    """Query parameters for workload data"""
    event_id: Optional[UUID] = None
    team_member_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class TeamWorkloadSummary(BaseModel):
    """Summary of team workload"""
    team_member_id: UUID
    user_id: UUID
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    estimated_hours: float
    actual_hours: float
    remaining_hours: float
    utilization_percentage: float
    is_overloaded: bool
    is_underutilized: bool


# ============================================================================
# Task Board Schemas
# ============================================================================

class TaskBoardCreate(BaseModel):
    """Create a task board"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    type: str = "kanban"
    event_id: UUID

    columns: List[Dict[str, Any]] = Field(default_factory=lambda: [
        {"id": "todo", "name": "To Do", "order": 0},
        {"id": "in_progress", "name": "In Progress", "order": 1},
        {"id": "done", "name": "Done", "order": 2}
    ])

    default_filters: Dict[str, Any] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=lambda: {
        "show_completed": True,
        "group_by": None,
        "sort_by": "priority"
    })

    is_default: bool = False


class TaskBoardUpdate(BaseModel):
    """Update task board"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    columns: Optional[List[Dict[str, Any]]] = None
    default_filters: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    is_archived: Optional[bool] = None


class TaskBoardResponse(BaseModel):
    """Task board response"""
    id: UUID
    name: str
    description: Optional[str]
    type: str

    event_id: UUID
    created_by: UUID

    columns: List[Dict[str, Any]]
    default_filters: Dict[str, Any]
    settings: Dict[str, Any]

    is_default: bool
    is_archived: bool

    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Task Label Schemas
# ============================================================================

class TaskLabelCreate(BaseModel):
    """Create a task label"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    color: str = Field("#808080", regex="^#[0-9A-Fa-f]{6}$")
    board_id: Optional[UUID] = None
    event_id: Optional[UUID] = None
    parent_label_id: Optional[UUID] = None
    order: int = 0


class TaskLabelUpdate(BaseModel):
    """Update task label"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(None, regex="^#[0-9A-Fa-f]{6}$")
    order: Optional[int] = None
    is_active: Optional[bool] = None


class TaskLabelResponse(BaseModel):
    """Task label response"""
    id: UUID
    name: str
    description: Optional[str]
    color: str

    board_id: Optional[UUID]
    event_id: Optional[UUID]
    parent_label_id: Optional[UUID]

    order: int
    is_active: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Bulk Operations Schemas
# ============================================================================

class BulkAssignmentCreate(BaseModel):
    """Bulk assign tasks to users"""
    task_ids: List[UUID] = Field(..., min_items=1)
    user_ids: List[UUID] = Field(..., min_items=1)
    estimated_hours_per_task: Optional[float] = None
    notify: bool = True


class TaskFromTemplateCreate(BaseModel):
    """Create task from template"""
    template_id: UUID
    event_id: UUID
    title: Optional[str] = None  # Override template name
    due_date: Optional[datetime] = None
    assigned_to: Optional[UUID] = None
    phase: str


class BulkTaskUpdate(BaseModel):
    """Bulk update tasks"""
    task_ids: List[UUID] = Field(..., min_items=1)
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[datetime] = None


# ============================================================================
# Analytics Schemas
# ============================================================================

class TaskAnalytics(BaseModel):
    """Task analytics for an event"""
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    overdue_tasks: int
    completion_rate: float

    average_completion_time_hours: Optional[float]
    total_estimated_hours: float
    total_actual_hours: float

    tasks_by_priority: Dict[str, int]
    tasks_by_status: Dict[str, int]
    tasks_by_assignee: Dict[str, int]


class TeamProductivity(BaseModel):
    """Team productivity metrics"""
    team_member_id: UUID
    user_id: UUID
    completed_tasks: int
    total_hours_logged: float
    average_task_completion_time_hours: float
    on_time_completion_rate: float
    task_acceptance_rate: float
