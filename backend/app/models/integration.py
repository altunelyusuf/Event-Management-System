"""
Integration Hub Models
Sprint 20: Integration Hub

Database models for third-party integrations including payment gateways,
calendar systems, social media, cloud storage, email services, and webhooks.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, JSON, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum
from app.core.database import Base

class IntegrationType(str, enum.Enum):
    PAYMENT = "payment"
    CALENDAR = "calendar"
    SOCIAL_MEDIA = "social_media"
    CLOUD_STORAGE = "cloud_storage"
    EMAIL = "email"
    SMS = "sms"
    ANALYTICS = "analytics"
    WEBHOOK = "webhook"

class IntegrationStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    EXPIRED = "expired"

class Integration(Base):
    """Third-party service integrations"""
    __tablename__ = "integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    integration_type = Column(String(50), nullable=False, index=True)
    provider = Column(String(100), nullable=False, index=True)
    credentials = Column(JSON, nullable=False)  # Encrypted credentials
    config = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    last_sync_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (Index('ix_integrations_user_type', 'user_id', 'integration_type'),)

class Webhook(Base):
    """Webhook endpoints"""
    __tablename__ = "webhooks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class WebhookDelivery(Base):
    """Webhook delivery log"""
    __tablename__ = "webhook_deliveries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(UUID(as_uuid=True), ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    delivered_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
