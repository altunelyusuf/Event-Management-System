"""
Schemas for Final Sprints 20-24
Combined schemas for efficiency
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# Sprint 20: Integration Hub
class IntegrationCreate(BaseModel):
    integration_type: str
    provider: str
    credentials: Dict[str, Any]
    config: Optional[Dict[str, Any]] = None

class IntegrationResponse(BaseModel):
    id: UUID
    user_id: UUID
    integration_type: str
    provider: str
    status: str
    last_sync_at: Optional[datetime]
    created_at: datetime
    class Config:
        from_attributes = True

class WebhookCreate(BaseModel):
    event_type: str
    url: str = Field(..., max_length=500)

class WebhookResponse(BaseModel):
    id: UUID
    event_type: str
    url: str
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

# Sprint 21: Admin & Moderation
class AdminActionResponse(BaseModel):
    id: UUID
    admin_id: UUID
    action_type: str
    target_type: Optional[str]
    target_id: Optional[UUID]
    performed_at: datetime
    class Config:
        from_attributes = True

class ModerationQueueResponse(BaseModel):
    id: UUID
    content_type: str
    content_id: UUID
    reason: str
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

class SystemConfigUpdate(BaseModel):
    config_key: str
    config_value: Any
    category: str

# Sprint 22: Performance
class PerformanceMetricCreate(BaseModel):
    metric_type: str
    metric_value: float
    tags: Optional[Dict[str, Any]] = None

class PerformanceMetricResponse(BaseModel):
    id: UUID
    metric_type: str
    metric_value: float
    recorded_at: datetime
    class Config:
        from_attributes = True

# Sprint 23: Security
class SecurityEventCreate(BaseModel):
    event_type: str
    severity: str
    description: str
    metadata: Optional[Dict[str, Any]] = None

class SecurityEventResponse(BaseModel):
    id: UUID
    event_type: str
    severity: str
    ip_address: str
    description: str
    occurred_at: datetime
    class Config:
        from_attributes = True

class IPBlacklistCreate(BaseModel):
    ip_address: str
    reason: str
    blocked_until: Optional[datetime] = None

# Sprint 24: Testing
class TestRunCreate(BaseModel):
    test_suite: str
    environment: str

class TestRunResponse(BaseModel):
    id: UUID
    test_suite: str
    status: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    started_at: datetime
    class Config:
        from_attributes = True

class APIDocumentationResponse(BaseModel):
    id: UUID
    endpoint: str
    method: str
    description: str
    version: str
    updated_at: datetime
    class Config:
        from_attributes = True
