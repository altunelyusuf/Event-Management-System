"""
CelebraTech Event Management System - Task Schemas
Sprint 2: Event Management Core
Pydantic models for task request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.task import TaskPriority, TaskStatus, DependencyType


# Base schemas
class TaskBase(BaseModel):
    """Base task schema"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    phase: str = Field(..., max_length=50)


class TaskCreate(TaskBase):
    """Schema for task creation"""
    due_date: Optional[datetime] = None
    estimated_duration_hours: Optional[Decimal] = Field(None, ge=0)
    assigned_to: Optional[UUID] = None
    parent_task_id: Optional[UUID] = None
    is_milestone: bool = False
    is_critical: bool = False
    order_index: int = 0
    metadata: Dict[str, Any] = {}


class TaskUpdate(BaseModel):
    """Schema for updating task"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime] = None
    estimated_duration_hours: Optional[Decimal] = Field(None, ge=0)
    actual_duration_hours: Optional[Decimal] = Field(None, ge=0)
    assigned_to: Optional[UUID] = None
    is_critical: Optional[bool] = None
    order_index: Optional[int] = None


class TaskResponse(TaskBase):
    """Schema for task response"""
    id: UUID
    event_id: UUID
    status: TaskStatus
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_duration_hours: Optional[Decimal]
    actual_duration_hours: Optional[Decimal]
    assigned_to: Optional[UUID]
    is_milestone: bool
    is_critical: bool
    parent_task_id: Optional[UUID]
    order_index: int
    created_by: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TaskDetailResponse(TaskResponse):
    """Schema for detailed task response with relationships"""
    subtasks: List[TaskResponse] = []
    dependencies: List["TaskDependencyResponse"] = []
    comments: List["TaskCommentResponse"] = []
    attachments: List["TaskAttachmentResponse"] = []
    assignee_name: Optional[str] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Schema for paginated task list"""
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# Task Dependency schemas
class TaskDependencyCreate(BaseModel):
    """Schema for creating task dependency"""
    depends_on_task_id: UUID
    dependency_type: DependencyType = DependencyType.FINISH_TO_START
    lag_days: int = 0


class TaskDependencyResponse(BaseModel):
    """Schema for task dependency response"""
    task_id: UUID
    depends_on_task_id: UUID
    dependency_type: DependencyType
    lag_days: int

    class Config:
        from_attributes = True


# Task Comment schemas
class TaskCommentCreate(BaseModel):
    """Schema for creating task comment"""
    comment_text: str = Field(..., min_length=1)


class TaskCommentUpdate(BaseModel):
    """Schema for updating task comment"""
    comment_text: str = Field(..., min_length=1)


class TaskCommentResponse(BaseModel):
    """Schema for task comment response"""
    id: UUID
    task_id: UUID
    user_id: UUID
    comment_text: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Task Attachment schemas
class TaskAttachmentResponse(BaseModel):
    """Schema for task attachment response"""
    id: UUID
    task_id: UUID
    file_name: str
    file_url: str
    file_size: Optional[int]
    file_type: Optional[str]
    uploaded_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Task Statistics
class TaskStatistics(BaseModel):
    """Schema for task statistics"""
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    overdue_tasks: int
    completion_percentage: Decimal
    critical_tasks_pending: int
    tasks_by_priority: Dict[str, int]
    tasks_by_phase: Dict[str, int]


# Task by Phase
class TasksByPhase(BaseModel):
    """Schema for tasks grouped by phase"""
    phase: str
    phase_name: str
    tasks: List[TaskResponse]
    total: int
    completed: int
    completion_percentage: Decimal


# Bulk operations
class BulkTaskUpdate(BaseModel):
    """Schema for bulk task update"""
    task_ids: List[UUID]
    status: Optional[TaskStatus] = None
    assigned_to: Optional[UUID] = None
    priority: Optional[TaskPriority] = None


class BulkTaskResponse(BaseModel):
    """Schema for bulk task operation response"""
    updated_count: int
    failed_ids: List[UUID]
    errors: Dict[str, str]


# Task Templates
class TaskTemplateCreate(BaseModel):
    """Schema for creating task template"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    event_type: str
    phase: str
    tasks: List[TaskCreate]


class TaskTemplateResponse(BaseModel):
    """Schema for task template response"""
    id: UUID
    name: str
    description: Optional[str]
    event_type: str
    phase: str
    task_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# Forward references
TaskDetailResponse.update_forward_refs()
