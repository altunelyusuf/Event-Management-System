"""
CelebraTech Event Management System - Task API
Sprint 2: Event Management Core
Task management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.task import TaskStatus
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    TaskCommentCreate,
    TaskCommentResponse
)
from app.repositories.task_repository import TaskRepository
from app.repositories.event_repository import EventRepository

router = APIRouter(prefix="/events/{event_id}/tasks", tags=["Tasks"])


async def verify_event_access(
    event_id: str,
    current_user: User,
    db: AsyncSession
) -> bool:
    """Verify user has access to event"""
    event_repo = EventRepository(db)
    has_permission = await event_repo.has_permission(
        event_id, str(current_user.id), "view"
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to access this event"
        )
    return True


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create task",
    description="Create a new task for an event"
)
async def create_task(
    event_id: str,
    task_data: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new task

    - **title**: Task title (required)
    - **description**: Task description
    - **priority**: LOW, MEDIUM, HIGH, CRITICAL
    - **phase**: Event phase this task belongs to
    - **due_date**: Task due date
    - **assigned_to**: User ID to assign task to
    - **is_critical**: Mark as critical task
    - **is_milestone**: Mark as milestone task

    Returns created task
    """
    await verify_event_access(event_id, current_user, db)

    task_repo = TaskRepository(db)
    task = await task_repo.create(event_id, task_data, str(current_user.id))
    return TaskResponse.from_orm(task)


@router.get(
    "",
    response_model=TaskListResponse,
    summary="Get event tasks",
    description="Get all tasks for an event"
)
async def get_event_tasks(
    event_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[TaskStatus] = None,
    phase: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all tasks for an event

    Query parameters:
    - **page**: Page number
    - **page_size**: Items per page
    - **status**: Filter by status (TODO, IN_PROGRESS, COMPLETED, etc.)
    - **phase**: Filter by event phase

    Returns paginated list of tasks
    """
    await verify_event_access(event_id, current_user, db)

    task_repo = TaskRepository(db)
    tasks, total = await task_repo.get_by_event(
        event_id,
        page,
        page_size,
        status,
        phase
    )

    return TaskListResponse(
        tasks=[TaskResponse.from_orm(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get task by ID",
    description="Get task details"
)
async def get_task(
    event_id: str,
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get task by ID"""
    await verify_event_access(event_id, current_user, db)

    task_repo = TaskRepository(db)
    task = await task_repo.get_by_id(task_id)
    if not task or str(task.event_id) != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return TaskResponse.from_orm(task)


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update task",
    description="Update task details"
)
async def update_task(
    event_id: str,
    task_id: str,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update task

    All fields are optional - only provided fields will be updated.
    """
    await verify_event_access(event_id, current_user, db)

    task_repo = TaskRepository(db)
    task = await task_repo.update(task_id, task_data)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return TaskResponse.from_orm(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    description="Delete a task"
)
async def delete_task(
    event_id: str,
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete task"""
    await verify_event_access(event_id, current_user, db)

    task_repo = TaskRepository(db)
    success = await task_repo.delete(task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return None


@router.post(
    "/{task_id}/comments",
    response_model=TaskCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add task comment",
    description="Add a comment to a task"
)
async def add_task_comment(
    event_id: str,
    task_id: str,
    comment_data: TaskCommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add comment to task

    - **comment_text**: Comment text (required)

    Returns created comment
    """
    await verify_event_access(event_id, current_user, db)

    task_repo = TaskRepository(db)
    comment = await task_repo.add_comment(
        task_id,
        str(current_user.id),
        comment_data.comment_text
    )
    return TaskCommentResponse.from_orm(comment)


@router.get(
    "/{task_id}/comments",
    response_model=list[TaskCommentResponse],
    summary="Get task comments",
    description="Get all comments for a task"
)
async def get_task_comments(
    event_id: str,
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all comments for a task"""
    await verify_event_access(event_id, current_user, db)

    task_repo = TaskRepository(db)
    comments = await task_repo.get_comments(task_id)
    return [TaskCommentResponse.from_orm(c) for c in comments]
