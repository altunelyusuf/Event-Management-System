"""Admin & Moderation Models - Sprint 21"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base

class AdminAction(Base):
    """Admin action audit log"""
    __tablename__ = "admin_actions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    action_type = Column(String(100), nullable=False, index=True)
    target_type = Column(String(50), nullable=True)
    target_id = Column(UUID(as_uuid=True), nullable=True)
    changes = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    performed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

class ModerationQueue(Base):
    """Content moderation queue"""
    __tablename__ = "moderation_queue"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_type = Column(String(50), nullable=False, index=True)
    content_id = Column(UUID(as_uuid=True), nullable=False)
    reason = Column(String(200), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    decision = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    reviewed_at = Column(DateTime, nullable=True)

class SystemConfig(Base):
    """System configuration"""
    __tablename__ = "system_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_key = Column(String(200), unique=True, nullable=False, index=True)
    config_value = Column(JSON, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    is_sensitive = Column(Boolean, default=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
