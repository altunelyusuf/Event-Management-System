"""
Task Collaboration Service
Sprint 12: Advanced Task Management & Team Collaboration

Business logic and authorization for task collaboration features.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from app.repositories.task_collaboration_repository import TaskCollaborationRepository
from app.models.user import User
from app.models.task_collaboration import TeamMemberRole
from app.schemas.task_collaboration import (
    TaskTemplateCreate, TaskTemplateUpdate,
    TaskAssignmentCreate, TaskAssignmentUpdate,
    TimeLogCreate, TimeLogUpdate,
    ChecklistItemCreate, ChecklistItemUpdate,
    TeamMemberCreate, TeamMemberUpdate,
    TaskBoardCreate, TaskBoardUpdate,
    TaskLabelCreate, TaskLabelUpdate,
    BulkAssignmentCreate, TaskFromTemplateCreate, BulkTaskUpdate
)


class TaskCollaborationService:
    """Service for task collaboration operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TaskCollaborationRepository(db)

    # ========================================================================
    # Task Template Methods
    # ========================================================================

    async def create_template(
        self,
        template_data: TaskTemplateCreate,
        current_user: User
    ):
        """Create a new task template"""
        data = template_data.model_dump()
        data['created_by'] = current_user.id
        return await self.repo.create_template(data)

    async def get_template(self, template_id: UUID, current_user: User):
        """Get a task template"""
        template = await self.repo.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )

        # Check access
        if not template.is_public and template.created_by != current_user.id:
            if current_user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to private template"
                )

        return template

    async def get_templates(
        self,
        category: Optional[str] = None,
        is_public: Optional[bool] = None,
        current_user: Optional[User] = None,
        skip: int = 0,
        limit: int = 50
    ):
        """Get task templates with filters"""
        # If filtering for user's templates, use created_by
        created_by = current_user.id if current_user and not is_public else None

        return await self.repo.get_templates(
            created_by=created_by,
            category=category,
            is_public=is_public,
            skip=skip,
            limit=limit
        )

    async def update_template(
        self,
        template_id: UUID,
        template_data: TaskTemplateUpdate,
        current_user: User
    ):
        """Update a task template"""
        template = await self.repo.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )

        # Check permissions
        if template.created_by != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the template creator or admin can update"
            )

        # Cannot modify system templates
        if template.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify system templates"
            )

        data = template_data.model_dump(exclude_unset=True)
        return await self.repo.update_template(template_id, data)

    async def delete_template(self, template_id: UUID, current_user: User):
        """Delete a task template"""
        template = await self.repo.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )

        # Check permissions
        if template.created_by != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the template creator or admin can delete"
            )

        # Cannot delete system templates
        if template.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete system templates"
            )

        success = await self.repo.delete_template(template_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete template"
            )

        return {"message": "Template deleted successfully"}

    async def create_task_from_template(
        self,
        template_data: TaskFromTemplateCreate,
        current_user: User
    ):
        """Create a task from a template"""
        # Get template
        template = await self.get_template(template_data.template_id, current_user)

        # Increment use count
        await self.repo.increment_template_use_count(template.id)

        # Create task data from template
        task_data = {
            "event_id": template_data.event_id,
            "title": template_data.title or template.name,
            "description": template.description,
            "priority": template.default_priority,
            "phase": template_data.phase,
            "estimated_duration_hours": template.estimated_hours,
            "created_by": current_user.id
        }

        if template_data.due_date:
            task_data["due_date"] = template_data.due_date
        if template_data.assigned_to:
            task_data["assigned_to"] = template_data.assigned_to

        # Note: This would require the task repository/service to be injected
        # For now, return the task data structure
        return {
            "task_data": task_data,
            "checklist_items": template.checklist_items,
            "default_assignments": template.default_assignments
        }

    # ========================================================================
    # Task Assignment Methods
    # ========================================================================

    async def create_assignment(
        self,
        assignment_data: TaskAssignmentCreate,
        current_user: User
    ):
        """Create a new task assignment"""
        # Check if assignment already exists
        existing = await self.repo.get_task_assignments(assignment_data.task_id)
        if any(a.user_id == assignment_data.user_id for a in existing):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already assigned to this task"
            )

        data = assignment_data.model_dump()
        data['assigned_by'] = current_user.id
        return await self.repo.create_assignment(data)

    async def get_assignment(self, assignment_id: UUID, current_user: User):
        """Get a task assignment"""
        assignment = await self.repo.get_assignment(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        return assignment

    async def get_user_assignments(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        current_user: Optional[User] = None,
        skip: int = 0,
        limit: int = 50
    ):
        """Get assignments for a user"""
        # Users can only see their own assignments unless admin
        if current_user and user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        return await self.repo.get_user_assignments(user_id, status, skip, limit)

    async def update_assignment(
        self,
        assignment_id: UUID,
        assignment_data: TaskAssignmentUpdate,
        current_user: User
    ):
        """Update a task assignment"""
        assignment = await self.repo.get_assignment(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )

        # Only assignee can update their own assignment status
        # Assignment creator or admin can update other fields
        data = assignment_data.model_dump(exclude_unset=True)

        if 'status' in data:
            if assignment.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the assignee can update assignment status"
                )
            # Add completed_by when marking as completed
            if data['status'] == 'completed':
                data['completed_by'] = current_user.id

        return await self.repo.update_assignment(assignment_id, data)

    async def delete_assignment(self, assignment_id: UUID, current_user: User):
        """Delete a task assignment"""
        assignment = await self.repo.get_assignment(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )

        # Only assigner or admin can delete
        if assignment.assigned_by != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        success = await self.repo.delete_assignment(assignment_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete assignment"
            )

        return {"message": "Assignment deleted successfully"}

    async def bulk_assign_tasks(
        self,
        bulk_data: BulkAssignmentCreate,
        current_user: User
    ):
        """Bulk assign multiple tasks to multiple users"""
        assignments = []
        for task_id in bulk_data.task_ids:
            for user_id in bulk_data.user_ids:
                assignment_data = {
                    "task_id": task_id,
                    "user_id": user_id,
                    "assigned_by": current_user.id,
                    "estimated_hours": bulk_data.estimated_hours_per_task,
                    "notify_on_assign": bulk_data.notify
                }
                try:
                    assignment = await self.repo.create_assignment(assignment_data)
                    assignments.append(assignment)
                except Exception:
                    # Skip if assignment already exists
                    continue

        return assignments

    # ========================================================================
    # Time Log Methods
    # ========================================================================

    async def create_time_log(
        self,
        log_data: TimeLogCreate,
        current_user: User
    ):
        """Create a time log entry"""
        data = log_data.model_dump()
        data['user_id'] = current_user.id
        return await self.repo.create_time_log(data)

    async def get_time_log(self, log_id: UUID, current_user: User):
        """Get a time log entry"""
        log = await self.repo.get_time_log(log_id)
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Time log not found"
            )

        # Users can only see their own time logs unless admin
        if log.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        return log

    async def get_user_time_logs(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        current_user: Optional[User] = None,
        skip: int = 0,
        limit: int = 100
    ):
        """Get time logs for a user"""
        # Users can only see their own time logs unless admin
        if current_user and user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        return await self.repo.get_user_time_logs(user_id, start_date, end_date, skip, limit)

    async def update_time_log(
        self,
        log_id: UUID,
        log_data: TimeLogUpdate,
        current_user: User
    ):
        """Update a time log entry"""
        log = await self.repo.get_time_log(log_id)
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Time log not found"
            )

        # Only the creator can update
        if log.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the log creator can update"
            )

        data = log_data.model_dump(exclude_unset=True)
        return await self.repo.update_time_log(log_id, data)

    async def delete_time_log(self, log_id: UUID, current_user: User):
        """Delete a time log entry"""
        log = await self.repo.get_time_log(log_id)
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Time log not found"
            )

        # Only the creator or admin can delete
        if log.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        success = await self.repo.delete_time_log(log_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete time log"
            )

        return {"message": "Time log deleted successfully"}

    # ========================================================================
    # Checklist Methods
    # ========================================================================

    async def create_checklist_item(
        self,
        item_data: ChecklistItemCreate,
        current_user: User
    ):
        """Create a checklist item"""
        data = item_data.model_dump()
        return await self.repo.create_checklist_item(data)

    async def update_checklist_item(
        self,
        item_id: UUID,
        item_data: ChecklistItemUpdate,
        current_user: User
    ):
        """Update a checklist item"""
        item = await self.repo.get_checklist_item(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Checklist item not found"
            )

        data = item_data.model_dump(exclude_unset=True)

        # Mark who completed the item
        if data.get('is_completed') and not item.is_completed:
            data['completed_by'] = current_user.id

        return await self.repo.update_checklist_item(item_id, data)

    async def delete_checklist_item(self, item_id: UUID, current_user: User):
        """Delete a checklist item"""
        item = await self.repo.get_checklist_item(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Checklist item not found"
            )

        success = await self.repo.delete_checklist_item(item_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete checklist item"
            )

        return {"message": "Checklist item deleted successfully"}

    # ========================================================================
    # Team Member Methods
    # ========================================================================

    async def add_team_member(
        self,
        member_data: TeamMemberCreate,
        current_user: User
    ):
        """Add a team member"""
        # Check if already a member
        existing = await self.repo.get_event_team_members(member_data.event_id)
        if any(m.user_id == member_data.user_id for m in existing):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a team member"
            )

        data = member_data.model_dump()
        data['added_by'] = current_user.id
        return await self.repo.create_team_member(data)

    async def get_team_member(self, member_id: UUID, current_user: User):
        """Get a team member"""
        member = await self.repo.get_team_member(member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found"
            )
        return member

    async def get_event_team(self, event_id: UUID, current_user: User):
        """Get all team members for an event"""
        return await self.repo.get_event_team_members(event_id, is_active=True)

    async def update_team_member(
        self,
        member_id: UUID,
        member_data: TeamMemberUpdate,
        current_user: User
    ):
        """Update a team member"""
        member = await self.repo.get_team_member(member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found"
            )

        data = member_data.model_dump(exclude_unset=True)
        return await self.repo.update_team_member(member_id, data)

    async def remove_team_member(self, member_id: UUID, current_user: User):
        """Remove a team member"""
        member = await self.repo.get_team_member(member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found"
            )

        # Deactivate instead of delete to preserve history
        await self.repo.update_team_member(member_id, {"is_active": False})

        return {"message": "Team member removed successfully"}

    async def get_team_member_workload(
        self,
        team_member_id: UUID,
        current_user: User
    ):
        """Get current workload for a team member"""
        member = await self.repo.get_team_member(team_member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found"
            )

        workload = await self.repo.calculate_team_member_workload(team_member_id, member)

        # Add helper flags
        workload['is_overloaded'] = workload['utilization_percentage'] > 100
        workload['is_underutilized'] = workload['utilization_percentage'] < 50

        return workload

    # ========================================================================
    # Task Board Methods
    # ========================================================================

    async def create_board(
        self,
        board_data: TaskBoardCreate,
        current_user: User
    ):
        """Create a task board"""
        data = board_data.model_dump()
        data['created_by'] = current_user.id
        return await self.repo.create_board(data)

    async def get_board(self, board_id: UUID, current_user: User):
        """Get a task board"""
        board = await self.repo.get_board(board_id)
        if not board:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Board not found"
            )
        return board

    async def get_event_boards(self, event_id: UUID, current_user: User):
        """Get all boards for an event"""
        return await self.repo.get_event_boards(event_id, is_archived=False)

    async def update_board(
        self,
        board_id: UUID,
        board_data: TaskBoardUpdate,
        current_user: User
    ):
        """Update a task board"""
        board = await self.repo.get_board(board_id)
        if not board:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Board not found"
            )

        data = board_data.model_dump(exclude_unset=True)
        return await self.repo.update_board(board_id, data)

    async def delete_board(self, board_id: UUID, current_user: User):
        """Delete a task board"""
        board = await self.repo.get_board(board_id)
        if not board:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Board not found"
            )

        # Archive instead of delete if it's the default board
        if board.is_default:
            await self.repo.update_board(board_id, {"is_archived": True})
            return {"message": "Default board archived successfully"}

        success = await self.repo.delete_board(board_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete board"
            )

        return {"message": "Board deleted successfully"}

    # ========================================================================
    # Task Label Methods
    # ========================================================================

    async def create_label(
        self,
        label_data: TaskLabelCreate,
        current_user: User
    ):
        """Create a task label"""
        data = label_data.model_dump()
        return await self.repo.create_label(data)

    async def get_label(self, label_id: UUID, current_user: User):
        """Get a task label"""
        label = await self.repo.get_label(label_id)
        if not label:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Label not found"
            )
        return label

    async def update_label(
        self,
        label_id: UUID,
        label_data: TaskLabelUpdate,
        current_user: User
    ):
        """Update a task label"""
        label = await self.repo.get_label(label_id)
        if not label:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Label not found"
            )

        data = label_data.model_dump(exclude_unset=True)
        return await self.repo.update_label(label_id, data)

    async def delete_label(self, label_id: UUID, current_user: User):
        """Delete a task label"""
        label = await self.repo.get_label(label_id)
        if not label:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Label not found"
            )

        success = await self.repo.delete_label(label_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete label"
            )

        return {"message": "Label deleted successfully"}
