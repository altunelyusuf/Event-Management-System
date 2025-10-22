"""
Task Collaboration API Endpoints
Sprint 12: Advanced Task Management & Team Collaboration

REST API endpoints for advanced task features:
- Task templates
- Enhanced task assignments
- Time tracking
- Checklists
- Team management
- Workload tracking
- Task boards
- Labels
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.task_collaboration_service import TaskCollaborationService
from app.schemas.task_collaboration import (
    TaskTemplateCreate, TaskTemplateResponse, TaskTemplateUpdate,
    TaskAssignmentCreate, TaskAssignmentResponse, TaskAssignmentUpdate,
    TimeLogCreate, TimeLogResponse, TimeLogUpdate,
    ChecklistItemCreate, ChecklistItemResponse, ChecklistItemUpdate,
    TeamMemberCreate, TeamMemberResponse, TeamMemberUpdate,
    WorkloadSnapshotResponse, TeamWorkloadSummary,
    TaskBoardCreate, TaskBoardResponse, TaskBoardUpdate,
    TaskLabelCreate, TaskLabelResponse, TaskLabelUpdate,
    BulkAssignmentCreate, TaskFromTemplateCreate, BulkTaskUpdate
)


router = APIRouter(prefix="/task-collaboration", tags=["Task Collaboration"])


# ============================================================================
# Task Template Endpoints
# ============================================================================

@router.post("/templates", response_model=TaskTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_task_template(
    template_data: TaskTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new task template.

    Templates can be used to quickly create tasks with predefined:
    - Structure and checklists
    - Estimated duration
    - Default assignments
    - Dependencies
    """
    service = TaskCollaborationService(db)
    return await service.create_template(template_data, current_user)


@router.get("/templates/{template_id}", response_model=TaskTemplateResponse)
async def get_task_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a task template by ID.

    Public templates can be viewed by anyone.
    Private templates require ownership or admin access.
    """
    service = TaskCollaborationService(db)
    return await service.get_template(template_id, current_user)


@router.get("/templates", response_model=List[TaskTemplateResponse])
async def get_task_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get task templates with optional filters.

    Returns public templates and user's private templates.
    Sorted by popularity (use_count) and recency.
    """
    service = TaskCollaborationService(db)
    return await service.get_templates(category, is_public, current_user, skip, limit)


@router.patch("/templates/{template_id}", response_model=TaskTemplateResponse)
async def update_task_template(
    template_id: UUID,
    template_data: TaskTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a task template.

    Only the template creator or admins can update.
    System templates cannot be modified.
    """
    service = TaskCollaborationService(db)
    return await service.update_template(template_id, template_data, current_user)


@router.delete("/templates/{template_id}", status_code=status.HTTP_200_OK)
async def delete_task_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a task template.

    Only the template creator or admins can delete.
    System templates cannot be deleted.
    """
    service = TaskCollaborationService(db)
    return await service.delete_template(template_id, current_user)


@router.post("/templates/{template_id}/use")
async def create_task_from_template(
    template_id: UUID,
    task_data: TaskFromTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a task from a template.

    Generates task structure, checklist items, and assignments
    based on the template configuration.
    """
    task_data.template_id = template_id
    service = TaskCollaborationService(db)
    return await service.create_task_from_template(task_data, current_user)


# ============================================================================
# Task Assignment Endpoints
# ============================================================================

@router.post("/assignments", response_model=TaskAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_task_assignment(
    assignment_data: TaskAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assign a task to a user.

    Creates an enhanced assignment with:
    - Estimated hours and workload percentage
    - Assignment status tracking
    - Notification preferences
    """
    service = TaskCollaborationService(db)
    return await service.create_assignment(assignment_data, current_user)


@router.get("/assignments/{assignment_id}", response_model=TaskAssignmentResponse)
async def get_task_assignment(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a task assignment by ID"""
    service = TaskCollaborationService(db)
    return await service.get_assignment(assignment_id, current_user)


@router.get("/assignments/user/{user_id}", response_model=List[TaskAssignmentResponse])
async def get_user_task_assignments(
    user_id: UUID,
    status: Optional[str] = Query(None, description="Filter by assignment status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all task assignments for a user.

    Users can only view their own assignments unless admin.
    Can be filtered by assignment status.
    """
    service = TaskCollaborationService(db)
    return await service.get_user_assignments(user_id, status, current_user, skip, limit)


@router.patch("/assignments/{assignment_id}", response_model=TaskAssignmentResponse)
async def update_task_assignment(
    assignment_id: UUID,
    assignment_data: TaskAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a task assignment.

    Assignees can update their assignment status (accept, decline, complete).
    Assigners can update other fields like estimated hours.
    """
    service = TaskCollaborationService(db)
    return await service.update_assignment(assignment_id, assignment_data, current_user)


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_200_OK)
async def delete_task_assignment(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a task assignment.

    Only the person who created the assignment or admins can delete.
    """
    service = TaskCollaborationService(db)
    return await service.delete_assignment(assignment_id, current_user)


@router.post("/assignments/bulk", response_model=List[TaskAssignmentResponse])
async def bulk_assign_tasks(
    bulk_data: BulkAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Bulk assign multiple tasks to multiple users.

    Creates all combinations of task-user assignments.
    Skips assignments that already exist.
    """
    service = TaskCollaborationService(db)
    return await service.bulk_assign_tasks(bulk_data, current_user)


# ============================================================================
# Time Tracking Endpoints
# ============================================================================

@router.post("/time-logs", response_model=TimeLogResponse, status_code=status.HTTP_201_CREATED)
async def create_time_log(
    log_data: TimeLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a time log entry.

    Tracks time spent on tasks with:
    - Start and end times
    - Duration calculation
    - Work type categorization
    - Billable status
    """
    service = TaskCollaborationService(db)
    return await service.create_time_log(log_data, current_user)


@router.get("/time-logs/{log_id}", response_model=TimeLogResponse)
async def get_time_log(
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a time log entry by ID.

    Users can only view their own time logs unless admin.
    """
    service = TaskCollaborationService(db)
    return await service.get_time_log(log_id, current_user)


@router.get("/time-logs/user/{user_id}", response_model=List[TimeLogResponse])
async def get_user_time_logs(
    user_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get time logs for a user with optional date range filter.

    Users can only view their own time logs unless admin.
    Useful for timesheet generation and productivity tracking.
    """
    service = TaskCollaborationService(db)
    return await service.get_user_time_logs(user_id, start_date, end_date, current_user, skip, limit)


@router.patch("/time-logs/{log_id}", response_model=TimeLogResponse)
async def update_time_log(
    log_id: UUID,
    log_data: TimeLogUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a time log entry.

    Only the user who created the log can update it.
    Duration is recalculated if end time is updated.
    """
    service = TaskCollaborationService(db)
    return await service.update_time_log(log_id, log_data, current_user)


@router.delete("/time-logs/{log_id}", status_code=status.HTTP_200_OK)
async def delete_time_log(
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a time log entry.

    Only the user who created the log or admins can delete.
    """
    service = TaskCollaborationService(db)
    return await service.delete_time_log(log_id, current_user)


# ============================================================================
# Checklist Endpoints
# ============================================================================

@router.post("/checklists", response_model=ChecklistItemResponse, status_code=status.HTTP_201_CREATED)
async def create_checklist_item(
    item_data: ChecklistItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a checklist item for a task.

    Break down tasks into smaller, trackable steps.
    Items can be assigned to specific users and have dependencies.
    """
    service = TaskCollaborationService(db)
    return await service.create_checklist_item(item_data, current_user)


@router.patch("/checklists/{item_id}", response_model=ChecklistItemResponse)
async def update_checklist_item(
    item_id: UUID,
    item_data: ChecklistItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a checklist item.

    Mark items as completed, update assignment, or change order.
    Completion timestamp and user are tracked automatically.
    """
    service = TaskCollaborationService(db)
    return await service.update_checklist_item(item_id, item_data, current_user)


@router.delete("/checklists/{item_id}", status_code=status.HTTP_200_OK)
async def delete_checklist_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a checklist item"""
    service = TaskCollaborationService(db)
    return await service.delete_checklist_item(item_id, current_user)


# ============================================================================
# Team Management Endpoints
# ============================================================================

@router.post("/team-members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_team_member(
    member_data: TeamMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a team member to an event.

    Configure role, permissions, workload capacity, and skills.
    Team members can be assigned tasks and tracked for productivity.
    """
    service = TaskCollaborationService(db)
    return await service.add_team_member(member_data, current_user)


@router.get("/team-members/{member_id}", response_model=TeamMemberResponse)
async def get_team_member(
    member_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a team member by ID"""
    service = TaskCollaborationService(db)
    return await service.get_team_member(member_id, current_user)


@router.get("/team-members/event/{event_id}", response_model=List[TeamMemberResponse])
async def get_event_team(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all team members for an event.

    Returns active team members with their roles and permissions.
    """
    service = TaskCollaborationService(db)
    return await service.get_event_team(event_id, current_user)


@router.patch("/team-members/{member_id}", response_model=TeamMemberResponse)
async def update_team_member(
    member_id: UUID,
    member_data: TeamMemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update team member details.

    Update role, permissions, workload capacity, or skills.
    """
    service = TaskCollaborationService(db)
    return await service.update_team_member(member_id, member_data, current_user)


@router.delete("/team-members/{member_id}", status_code=status.HTTP_200_OK)
async def remove_team_member(
    member_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a team member from an event.

    Deactivates the member instead of deleting to preserve history.
    """
    service = TaskCollaborationService(db)
    return await service.remove_team_member(member_id, current_user)


@router.get("/team-members/{member_id}/workload", response_model=TeamWorkloadSummary)
async def get_team_member_workload(
    member_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current workload for a team member.

    Returns task counts, hours, and utilization percentage.
    Indicates if member is overloaded (>100%) or underutilized (<50%).
    """
    service = TaskCollaborationService(db)
    return await service.get_team_member_workload(member_id, current_user)


# ============================================================================
# Task Board Endpoints
# ============================================================================

@router.post("/boards", response_model=TaskBoardResponse, status_code=status.HTTP_201_CREATED)
async def create_task_board(
    board_data: TaskBoardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a task board.

    Boards organize tasks in different views:
    - Kanban: Column-based workflow
    - Scrum: Sprint-based planning
    - List: Simple list view
    - Timeline: Gantt-style timeline
    - Calendar: Calendar view
    """
    service = TaskCollaborationService(db)
    return await service.create_board(board_data, current_user)


@router.get("/boards/{board_id}", response_model=TaskBoardResponse)
async def get_task_board(
    board_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a task board by ID with its configuration"""
    service = TaskCollaborationService(db)
    return await service.get_board(board_id, current_user)


@router.get("/boards/event/{event_id}", response_model=List[TaskBoardResponse])
async def get_event_boards(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all task boards for an event.

    Returns active boards sorted by default board first.
    """
    service = TaskCollaborationService(db)
    return await service.get_event_boards(event_id, current_user)


@router.patch("/boards/{board_id}", response_model=TaskBoardResponse)
async def update_task_board(
    board_id: UUID,
    board_data: TaskBoardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update task board configuration.

    Update columns, filters, settings, or archive the board.
    """
    service = TaskCollaborationService(db)
    return await service.update_board(board_id, board_data, current_user)


@router.delete("/boards/{board_id}", status_code=status.HTTP_200_OK)
async def delete_task_board(
    board_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a task board.

    Default boards are archived instead of deleted.
    """
    service = TaskCollaborationService(db)
    return await service.delete_board(board_id, current_user)


# ============================================================================
# Task Label Endpoints
# ============================================================================

@router.post("/labels", response_model=TaskLabelResponse, status_code=status.HTTP_201_CREATED)
async def create_task_label(
    label_data: TaskLabelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a task label.

    Labels help organize and categorize tasks with color coding.
    Can be board-specific or event-wide.
    """
    service = TaskCollaborationService(db)
    return await service.create_label(label_data, current_user)


@router.get("/labels/{label_id}", response_model=TaskLabelResponse)
async def get_task_label(
    label_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a task label by ID"""
    service = TaskCollaborationService(db)
    return await service.get_label(label_id, current_user)


@router.patch("/labels/{label_id}", response_model=TaskLabelResponse)
async def update_task_label(
    label_id: UUID,
    label_data: TaskLabelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a task label.

    Update name, color, or display order.
    """
    service = TaskCollaborationService(db)
    return await service.update_label(label_id, label_data, current_user)


@router.delete("/labels/{label_id}", status_code=status.HTTP_200_OK)
async def delete_task_label(
    label_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a task label"""
    service = TaskCollaborationService(db)
    return await service.delete_label(label_id, current_user)
