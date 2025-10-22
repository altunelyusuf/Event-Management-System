"""
CelebraTech Event Management System - Task Models
Sprint 2: Event Management Core
Task and timeline management
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Numeric, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class TaskPriority(str, enum.Enum):
    """Task priority enumeration"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TaskStatus(str, enum.Enum):
    """Task status enumeration"""
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ON_HOLD = "ON_HOLD"


class DependencyType(str, enum.Enum):
    """Task dependency type enumeration"""
    FINISH_TO_START = "FINISH_TO_START"
    START_TO_START = "START_TO_START"
    FINISH_TO_FINISH = "FINISH_TO_FINISH"
    START_TO_FINISH = "START_TO_FINISH"


class Task(Base):
    """
    Task model - Event planning tasks with dependencies
    """
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    phase = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Priority and status
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM, index=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.TODO, nullable=False, index=True)

    # Assignment
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    # Timing
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    estimated_duration_hours = Column(Numeric(6, 2), nullable=True)
    actual_duration_hours = Column(Numeric(6, 2), nullable=True)

    # Flags
    is_milestone = Column(Boolean, default=False)
    is_critical = Column(Boolean, default=False)

    # Hierarchy
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    order_index = Column(Integer, default=0)

    # Metadata
    metadata = Column(JSON, default={})

    # Ownership
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    event = relationship("Event", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assigned_to])
    creator = relationship("User", foreign_keys=[created_by])
    parent_task = relationship("Task", remote_side=[id], backref="subtasks")
    dependencies = relationship("TaskDependency", foreign_keys="TaskDependency.task_id", back_populates="task")
    dependents = relationship("TaskDependency", foreign_keys="TaskDependency.depends_on_task_id", back_populates="depends_on")
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("TaskAttachment", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Task {self.title} for event {self.event_id}>"


class TaskDependency(Base):
    """
    Task dependency model - Defines relationships between tasks
    """
    __tablename__ = "task_dependencies"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    depends_on_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    dependency_type = Column(SQLEnum(DependencyType), default=DependencyType.FINISH_TO_START)
    lag_days = Column(Integer, default=0)

    # Relationships
    task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")
    depends_on = relationship("Task", foreign_keys=[depends_on_task_id], back_populates="dependents")

    def __repr__(self):
        return f"<TaskDependency {self.task_id} depends on {self.depends_on_task_id}>"


class TaskComment(Base):
    """
    Task comment model - Comments on tasks
    """
    __tablename__ = "task_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    comment_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    task = relationship("Task", back_populates="comments")
    user = relationship("User")

    def __repr__(self):
        return f"<TaskComment on task {self.task_id} by user {self.user_id}>"


class TaskAttachment(Base):
    """
    Task attachment model - Files attached to tasks
    """
    __tablename__ = "task_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String(100), nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    task = relationship("Task", back_populates="attachments")
    uploader = relationship("User")

    def __repr__(self):
        return f"<TaskAttachment {self.file_name} for task {self.task_id}>"
