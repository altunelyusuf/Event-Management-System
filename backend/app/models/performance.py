"""Performance & Optimization Models - Sprint 22"""
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base

class PerformanceMetric(Base):
    """Performance metrics"""
    __tablename__ = "performance_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_type = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    tags = Column(JSON, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

class CacheEntry(Base):
    """Cache management"""
    __tablename__ = "cache_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key = Column(String(500), unique=True, nullable=False, index=True)
    cache_value = Column(JSON, nullable=False)
    ttl = Column(Integer, nullable=False)
    hit_count = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
