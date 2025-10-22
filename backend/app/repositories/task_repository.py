"""
CelebraTech Event Management System - Task Repository
Sprint 2: Event Management Core
Data access layer for task operations
"""
from typing import Optional, List, Tuple
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.task import Task, TaskComment, TaskAttachment, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate


class TaskRepository:
    """Repository for task database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        event_id: str,
        task_data: TaskCreate,
        created_by: str
    ) -> Task:
        """Create a new task"""
        task = Task(
            event_id=event_id,
            phase=task_data.phase,
            title=task_data.title,
            description=task_data.description,
            priority=task_data.priority,
            status=TaskStatus.TODO,
            due_date=task_data.due_date,
            estimated_duration_hours=task_data.estimated_duration_hours,
            assigned_to=task_data.assigned_to,
            parent_task_id=task_data.parent_task_id,
            is_milestone=task_data.is_milestone,
            is_critical=task_data.is_critical,
            order_index=task_data.order_index,
            metadata=task_data.metadata,
            created_by=created_by
        )

        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_by_event(
        self,
        event_id: str,
        page: int = 1,
        page_size: int = 50,
        status: Optional[TaskStatus] = None,
        phase: Optional[str] = None
    ) -> Tuple[List[Task], int]:
        """Get tasks for an event"""
        base_query = select(Task).where(Task.event_id == event_id)

        if status:
            base_query = base_query.where(Task.status == status)
        if phase:
            base_query = base_query.where(Task.phase == phase)

        # Count
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Data
        data_query = base_query.order_by(
            Task.is_critical.desc(),
            Task.due_date,
            Task.order_index
        ).offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(data_query)
        tasks = result.scalars().all()

        return tasks, total

    async def update(
        self,
        task_id: str,
        task_data: TaskUpdate
    ) -> Optional[Task]:
        """Update task"""
        task = await self.get_by_id(task_id)
        if not task:
            return None

        update_data = task_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        if task_data.status == TaskStatus.COMPLETED and not task.completed_at:
            task.completed_at = datetime.utcnow()

        task.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete(self, task_id: str) -> bool:
        """Delete task"""
        task = await self.get_by_id(task_id)
        if not task:
            return False

        await self.db.delete(task)
        await self.db.commit()
        return True

    async def add_comment(
        self,
        task_id: str,
        user_id: str,
        comment_text: str
    ) -> TaskComment:
        """Add comment to task"""
        comment = TaskComment(
            task_id=task_id,
            user_id=user_id,
            comment_text=comment_text
        )
        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)
        return comment

    async def get_comments(self, task_id: str) -> List[TaskComment]:
        """Get all comments for a task"""
        result = await self.db.execute(
            select(TaskComment).where(
                TaskComment.task_id == task_id
            ).order_by(desc(TaskComment.created_at))
        )
        return result.scalars().all()
