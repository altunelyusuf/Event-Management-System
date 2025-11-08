"""Testing & Documentation Models - Sprint 24"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base

class TestRun(Base):
    """Test execution tracking"""
    __tablename__ = "test_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_suite = Column(String(200), nullable=False, index=True)
    environment = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    total_tests = Column(Integer, default=0)
    passed_tests = Column(Integer, default=0)
    failed_tests = Column(Integer, default=0)
    duration_seconds = Column(Integer, nullable=True)
    results = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

class APIDocumentation(Base):
    """API documentation"""
    __tablename__ = "api_documentation"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    endpoint = Column(String(500), unique=True, nullable=False, index=True)
    method = Column(String(10), nullable=False)
    description = Column(Text, nullable=False)
    parameters = Column(JSON, nullable=True)
    responses = Column(JSON, nullable=True)
    examples = Column(JSON, nullable=True)
    version = Column(String(20), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
