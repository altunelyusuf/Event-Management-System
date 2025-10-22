"""Security Hardening Models - Sprint 23"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base

class SecurityEvent(Base):
    """Security event log"""
    __tablename__ = "security_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(String(500), nullable=True)
    description = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

class RateLimitEntry(Base):
    """Rate limiting"""
    __tablename__ = "rate_limit_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identifier = Column(String(255), nullable=False, index=True)
    resource = Column(String(100), nullable=False)
    request_count = Column(Integer, default=1)
    window_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    window_end = Column(DateTime, nullable=False, index=True)

class IPBlacklist(Base):
    """IP blacklist"""
    __tablename__ = "ip_blacklist"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address = Column(String(45), unique=True, nullable=False, index=True)
    reason = Column(Text, nullable=False)
    blocked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
