"""
Task Collaboration Repository
Sprint 12: Advanced Task Management & Team Collaboration

Data access layer for task collaboration features.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from app.models.task_collaboration import (
    TaskTemplate, TaskAssignment, TaskTimeLog, TaskChecklist,
    TeamMember, WorkloadSnapshot, TaskBoard, TaskLabel,
    TaskAssignmentStatus, TeamMemberRole
)
from app.models.task import Task
from app.models.user import User


class TaskCollaborationRepository:
    """Repository for task collaboration operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Task Template Operations
    # ========================================================================

    async def create_template(self, template_data: Dict[str, Any]) -> TaskTemplate:
        """Create a new task template"""
        template = TaskTemplate(**template_data)
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def get_template(self, template_id: UUID) -> Optional[TaskTemplate]:
        """Get a task template by ID"""
        result = await self.db.execute(
            select(TaskTemplate).where(TaskTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_templates(
        self,
        created_by: Optional[UUID] = None,
        event_id: Optional[UUID] = None,
        category: Optional[str] = None,
        is_public: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[TaskTemplate]:
        """Get task templates with filters"""
        query = select(TaskTemplate)

        filters = []
        if created_by:
            filters.append(TaskTemplate.created_by == created_by)
        if event_id:
            filters.append(TaskTemplate.event_id == event_id)
        if category:
            filters.append(TaskTemplate.category == category)
        if is_public is not None:
            filters.append(TaskTemplate.is_public == is_public)

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(TaskTemplate.use_count.desc(), TaskTemplate.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_template(self, template_id: UUID, template_data: Dict[str, Any]) -> Optional[TaskTemplate]:
        """Update a task template"""
        await self.db.execute(
            update(TaskTemplate)
            .where(TaskTemplate.id == template_id)
            .values(**template_data)
        )
        await self.db.commit()
        return await self.get_template(template_id)

    async def delete_template(self, template_id: UUID) -> bool:
        """Delete a task template (if not system template)"""
        result = await self.db.execute(
            delete(TaskTemplate)
            .where(and_(
                TaskTemplate.id == template_id,
                TaskTemplate.is_system == False
            ))
        )
        await self.db.commit()
        return result.rowcount > 0

    async def increment_template_use_count(self, template_id: UUID):
        """Increment template use count"""
        await self.db.execute(
            update(TaskTemplate)
            .where(TaskTemplate.id == template_id)
            .values(use_count=TaskTemplate.use_count + 1)
        )
        await self.db.commit()

    # ========================================================================
    # Task Assignment Operations
    # ========================================================================

    async def create_assignment(self, assignment_data: Dict[str, Any]) -> TaskAssignment:
        """Create a new task assignment"""
        assignment = TaskAssignment(**assignment_data)
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def get_assignment(self, assignment_id: UUID) -> Optional[TaskAssignment]:
        """Get a task assignment by ID"""
        result = await self.db.execute(
            select(TaskAssignment)
            .options(selectinload(TaskAssignment.task))
            .options(selectinload(TaskAssignment.assignee))
            .where(TaskAssignment.id == assignment_id)
        )
        return result.scalar_one_or_none()

    async def get_task_assignments(self, task_id: UUID) -> List[TaskAssignment]:
        """Get all assignments for a task"""
        result = await self.db.execute(
            select(TaskAssignment)
            .options(selectinload(TaskAssignment.assignee))
            .where(TaskAssignment.task_id == task_id)
            .order_by(TaskAssignment.assigned_at)
        )
        return result.scalars().all()

    async def get_user_assignments(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[TaskAssignment]:
        """Get all assignments for a user"""
        query = select(TaskAssignment).options(selectinload(TaskAssignment.task))

        filters = [TaskAssignment.user_id == user_id]
        if status:
            filters.append(TaskAssignment.status == status)

        query = query.where(and_(*filters))
        query = query.order_by(TaskAssignment.assigned_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_assignment(self, assignment_id: UUID, assignment_data: Dict[str, Any]) -> Optional[TaskAssignment]:
        """Update a task assignment"""
        # Handle status transitions with timestamps
        if 'status' in assignment_data:
            status = assignment_data['status']
            if status == TaskAssignmentStatus.ACCEPTED.value and 'accepted_at' not in assignment_data:
                assignment_data['accepted_at'] = datetime.utcnow()
            elif status == TaskAssignmentStatus.IN_PROGRESS.value and 'started_at' not in assignment_data:
                assignment_data['started_at'] = datetime.utcnow()
            elif status == TaskAssignmentStatus.COMPLETED.value and 'completed_at' not in assignment_data:
                assignment_data['completed_at'] = datetime.utcnow()
            elif status == TaskAssignmentStatus.DECLINED.value and 'declined_at' not in assignment_data:
                assignment_data['declined_at'] = datetime.utcnow()

        await self.db.execute(
            update(TaskAssignment)
            .where(TaskAssignment.id == assignment_id)
            .values(**assignment_data)
        )
        await self.db.commit()
        return await self.get_assignment(assignment_id)

    async def delete_assignment(self, assignment_id: UUID) -> bool:
        """Delete a task assignment"""
        result = await self.db.execute(
            delete(TaskAssignment).where(TaskAssignment.id == assignment_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def update_assignment_hours(self, assignment_id: UUID, hours: float):
        """Update actual hours for an assignment"""
        await self.db.execute(
            update(TaskAssignment)
            .where(TaskAssignment.id == assignment_id)
            .values(actual_hours=TaskAssignment.actual_hours + hours)
        )
        await self.db.commit()

    # ========================================================================
    # Time Log Operations
    # ========================================================================

    async def create_time_log(self, log_data: Dict[str, Any]) -> TaskTimeLog:
        """Create a time log entry"""
        # Calculate duration if not provided
        if 'duration_minutes' not in log_data and 'ended_at' in log_data and log_data['ended_at']:
            start = log_data['started_at']
            end = log_data['ended_at']
            log_data['duration_minutes'] = int((end - start).total_seconds() / 60)

        time_log = TaskTimeLog(**log_data)
        self.db.add(time_log)
        await self.db.commit()
        await self.db.refresh(time_log)

        # Update assignment actual hours
        if time_log.assignment_id and time_log.duration_minutes:
            hours = time_log.duration_minutes / 60.0
            await self.update_assignment_hours(time_log.assignment_id, hours)

        return time_log

    async def get_time_log(self, log_id: UUID) -> Optional[TaskTimeLog]:
        """Get a time log entry by ID"""
        result = await self.db.execute(
            select(TaskTimeLog).where(TaskTimeLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def get_task_time_logs(self, task_id: UUID) -> List[TaskTimeLog]:
        """Get all time logs for a task"""
        result = await self.db.execute(
            select(TaskTimeLog)
            .where(TaskTimeLog.task_id == task_id)
            .order_by(TaskTimeLog.started_at.desc())
        )
        return result.scalars().all()

    async def get_user_time_logs(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[TaskTimeLog]:
        """Get time logs for a user"""
        query = select(TaskTimeLog).options(selectinload(TaskTimeLog.task))

        filters = [TaskTimeLog.user_id == user_id]
        if start_date:
            filters.append(TaskTimeLog.started_at >= start_date)
        if end_date:
            filters.append(TaskTimeLog.started_at <= end_date)

        query = query.where(and_(*filters))
        query = query.order_by(TaskTimeLog.started_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_time_log(self, log_id: UUID, log_data: Dict[str, Any]) -> Optional[TaskTimeLog]:
        """Update a time log entry"""
        # Recalculate duration if ended_at is updated
        time_log = await self.get_time_log(log_id)
        if time_log and 'ended_at' in log_data and log_data['ended_at']:
            duration = int((log_data['ended_at'] - time_log.started_at).total_seconds() / 60)
            log_data['duration_minutes'] = duration

        await self.db.execute(
            update(TaskTimeLog)
            .where(TaskTimeLog.id == log_id)
            .values(**log_data)
        )
        await self.db.commit()
        return await self.get_time_log(log_id)

    async def delete_time_log(self, log_id: UUID) -> bool:
        """Delete a time log entry"""
        result = await self.db.execute(
            delete(TaskTimeLog).where(TaskTimeLog.id == log_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    # ========================================================================
    # Checklist Operations
    # ========================================================================

    async def create_checklist_item(self, item_data: Dict[str, Any]) -> TaskChecklist:
        """Create a checklist item"""
        item = TaskChecklist(**item_data)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def get_checklist_item(self, item_id: UUID) -> Optional[TaskChecklist]:
        """Get a checklist item by ID"""
        result = await self.db.execute(
            select(TaskChecklist).where(TaskChecklist.id == item_id)
        )
        return result.scalar_one_or_none()

    async def get_task_checklist(self, task_id: UUID) -> List[TaskChecklist]:
        """Get all checklist items for a task"""
        result = await self.db.execute(
            select(TaskChecklist)
            .where(TaskChecklist.task_id == task_id)
            .order_by(TaskChecklist.order)
        )
        return result.scalars().all()

    async def update_checklist_item(self, item_id: UUID, item_data: Dict[str, Any]) -> Optional[TaskChecklist]:
        """Update a checklist item"""
        # Mark as completed if is_completed is set to True
        if item_data.get('is_completed') and 'completed_at' not in item_data:
            item_data['completed_at'] = datetime.utcnow()

        await self.db.execute(
            update(TaskChecklist)
            .where(TaskChecklist.id == item_id)
            .values(**item_data)
        )
        await self.db.commit()
        return await self.get_checklist_item(item_id)

    async def delete_checklist_item(self, item_id: UUID) -> bool:
        """Delete a checklist item"""
        result = await self.db.execute(
            delete(TaskChecklist).where(TaskChecklist.id == item_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    # ========================================================================
    # Team Member Operations
    # ========================================================================

    async def create_team_member(self, member_data: Dict[str, Any]) -> TeamMember:
        """Add a team member"""
        member = TeamMember(**member_data)
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def get_team_member(self, member_id: UUID) -> Optional[TeamMember]:
        """Get a team member by ID"""
        result = await self.db.execute(
            select(TeamMember)
            .options(selectinload(TeamMember.user))
            .where(TeamMember.id == member_id)
        )
        return result.scalar_one_or_none()

    async def get_event_team_members(
        self,
        event_id: UUID,
        is_active: Optional[bool] = None
    ) -> List[TeamMember]:
        """Get all team members for an event"""
        query = select(TeamMember).options(selectinload(TeamMember.user))

        filters = [TeamMember.event_id == event_id]
        if is_active is not None:
            filters.append(TeamMember.is_active == is_active)

        query = query.where(and_(*filters))
        query = query.order_by(TeamMember.joined_at)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_user_team_memberships(self, user_id: UUID) -> List[TeamMember]:
        """Get all team memberships for a user"""
        result = await self.db.execute(
            select(TeamMember)
            .options(selectinload(TeamMember.event))
            .where(and_(
                TeamMember.user_id == user_id,
                TeamMember.is_active == True
            ))
            .order_by(TeamMember.joined_at.desc())
        )
        return result.scalars().all()

    async def update_team_member(self, member_id: UUID, member_data: Dict[str, Any]) -> Optional[TeamMember]:
        """Update a team member"""
        # Set removed_at if is_active is set to False
        if 'is_active' in member_data and not member_data['is_active']:
            if 'removed_at' not in member_data:
                member_data['removed_at'] = datetime.utcnow()

        await self.db.execute(
            update(TeamMember)
            .where(TeamMember.id == member_id)
            .values(**member_data)
        )
        await self.db.commit()
        return await self.get_team_member(member_id)

    async def delete_team_member(self, member_id: UUID) -> bool:
        """Remove a team member"""
        result = await self.db.execute(
            delete(TeamMember).where(TeamMember.id == member_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    # ========================================================================
    # Workload Operations
    # ========================================================================

    async def create_workload_snapshot(self, snapshot_data: Dict[str, Any]) -> WorkloadSnapshot:
        """Create a workload snapshot"""
        snapshot = WorkloadSnapshot(**snapshot_data)
        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)
        return snapshot

    async def get_team_member_workload(
        self,
        team_member_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[WorkloadSnapshot]:
        """Get workload snapshots for a team member"""
        query = select(WorkloadSnapshot)

        filters = [WorkloadSnapshot.team_member_id == team_member_id]
        if start_date:
            filters.append(WorkloadSnapshot.snapshot_date >= start_date)
        if end_date:
            filters.append(WorkloadSnapshot.snapshot_date <= end_date)

        query = query.where(and_(*filters))
        query = query.order_by(WorkloadSnapshot.snapshot_date.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def calculate_team_member_workload(self, team_member_id: UUID, team_member: TeamMember) -> Dict[str, Any]:
        """Calculate current workload for a team member"""
        # Get active assignments
        result = await self.db.execute(
            select(TaskAssignment)
            .join(Task)
            .where(and_(
                TaskAssignment.user_id == team_member.user_id,
                Task.event_id == team_member.event_id,
                TaskAssignment.status.in_([
                    TaskAssignmentStatus.ASSIGNED.value,
                    TaskAssignmentStatus.ACCEPTED.value,
                    TaskAssignmentStatus.IN_PROGRESS.value
                ])
            ))
        )
        assignments = result.scalars().all()

        total_tasks = len(assignments)
        in_progress = sum(1 for a in assignments if a.status == TaskAssignmentStatus.IN_PROGRESS.value)
        estimated_hours = sum(a.estimated_hours or 0 for a in assignments)
        actual_hours = sum(a.actual_hours for a in assignments)
        remaining_hours = estimated_hours - actual_hours

        # Get completed tasks for the current week
        week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        result = await self.db.execute(
            select(func.count(TaskAssignment.id))
            .join(Task)
            .where(and_(
                TaskAssignment.user_id == team_member.user_id,
                Task.event_id == team_member.event_id,
                TaskAssignment.status == TaskAssignmentStatus.COMPLETED.value,
                TaskAssignment.completed_at >= week_start
            ))
        )
        completed_tasks = result.scalar_one()

        utilization = (actual_hours / team_member.max_hours_per_week * 100) if team_member.max_hours_per_week > 0 else 0

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress,
            "estimated_hours": estimated_hours,
            "actual_hours": actual_hours,
            "remaining_hours": remaining_hours,
            "available_hours": team_member.max_hours_per_week,
            "utilization_percentage": round(utilization, 2)
        }

    # ========================================================================
    # Task Board Operations
    # ========================================================================

    async def create_board(self, board_data: Dict[str, Any]) -> TaskBoard:
        """Create a task board"""
        board = TaskBoard(**board_data)
        self.db.add(board)
        await self.db.commit()
        await self.db.refresh(board)
        return board

    async def get_board(self, board_id: UUID) -> Optional[TaskBoard]:
        """Get a task board by ID"""
        result = await self.db.execute(
            select(TaskBoard)
            .options(selectinload(TaskBoard.labels))
            .where(TaskBoard.id == board_id)
        )
        return result.scalar_one_or_none()

    async def get_event_boards(self, event_id: UUID, is_archived: bool = False) -> List[TaskBoard]:
        """Get all task boards for an event"""
        result = await self.db.execute(
            select(TaskBoard)
            .where(and_(
                TaskBoard.event_id == event_id,
                TaskBoard.is_archived == is_archived
            ))
            .order_by(TaskBoard.is_default.desc(), TaskBoard.created_at)
        )
        return result.scalars().all()

    async def update_board(self, board_id: UUID, board_data: Dict[str, Any]) -> Optional[TaskBoard]:
        """Update a task board"""
        if 'is_archived' in board_data and board_data['is_archived']:
            if 'archived_at' not in board_data:
                board_data['archived_at'] = datetime.utcnow()

        await self.db.execute(
            update(TaskBoard)
            .where(TaskBoard.id == board_id)
            .values(**board_data)
        )
        await self.db.commit()
        return await self.get_board(board_id)

    async def delete_board(self, board_id: UUID) -> bool:
        """Delete a task board"""
        result = await self.db.execute(
            delete(TaskBoard).where(TaskBoard.id == board_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    # ========================================================================
    # Task Label Operations
    # ========================================================================

    async def create_label(self, label_data: Dict[str, Any]) -> TaskLabel:
        """Create a task label"""
        label = TaskLabel(**label_data)
        self.db.add(label)
        await self.db.commit()
        await self.db.refresh(label)
        return label

    async def get_label(self, label_id: UUID) -> Optional[TaskLabel]:
        """Get a task label by ID"""
        result = await self.db.execute(
            select(TaskLabel).where(TaskLabel.id == label_id)
        )
        return result.scalar_one_or_none()

    async def get_board_labels(self, board_id: UUID) -> List[TaskLabel]:
        """Get all labels for a board"""
        result = await self.db.execute(
            select(TaskLabel)
            .where(and_(
                TaskLabel.board_id == board_id,
                TaskLabel.is_active == True
            ))
            .order_by(TaskLabel.order)
        )
        return result.scalars().all()

    async def get_event_labels(self, event_id: UUID) -> List[TaskLabel]:
        """Get all labels for an event"""
        result = await self.db.execute(
            select(TaskLabel)
            .where(and_(
                TaskLabel.event_id == event_id,
                TaskLabel.is_active == True
            ))
            .order_by(TaskLabel.order)
        )
        return result.scalars().all()

    async def update_label(self, label_id: UUID, label_data: Dict[str, Any]) -> Optional[TaskLabel]:
        """Update a task label"""
        await self.db.execute(
            update(TaskLabel)
            .where(TaskLabel.id == label_id)
            .values(**label_data)
        )
        await self.db.commit()
        return await self.get_label(label_id)

    async def delete_label(self, label_id: UUID) -> bool:
        """Delete a task label"""
        result = await self.db.execute(
            delete(TaskLabel).where(TaskLabel.id == label_id)
        )
        await self.db.commit()
        return result.rowcount > 0
