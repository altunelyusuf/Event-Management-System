"""
Document Management Schemas

Pydantic schemas for document management validation and serialization.
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from app.models.document import DocumentType, DocumentStatus, AccessLevel, SignatureStatus


# Document Schemas
class DocumentBase(BaseModel):
    """Base document schema"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    type: DocumentType = Field(DocumentType.OTHER)


class DocumentUpload(DocumentBase):
    """Schema for document upload"""
    event_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    booking_id: Optional[UUID] = None
    folder_id: Optional[UUID] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    requires_signature: bool = Field(False)


class DocumentUpdate(BaseModel):
    """Schema for document update"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    type: Optional[DocumentType] = None
    status: Optional[DocumentStatus] = None
    folder_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentResponse(DocumentBase):
    """Schema for document response"""
    id: UUID
    file_name: str
    file_size: int
    file_extension: Optional[str]
    mime_type: Optional[str]
    version_number: int
    is_latest_version: bool
    status: str
    event_id: Optional[UUID]
    vendor_id: Optional[UUID]
    booking_id: Optional[UUID]
    folder_id: Optional[UUID]
    is_template: bool
    requires_signature: bool
    is_public: bool
    tags: List[str]
    download_count: int
    view_count: int
    created_at: datetime
    updated_at: datetime
    uploaded_by: UUID

    class Config:
        from_attributes = True


# Folder Schemas
class DocumentFolderCreate(BaseModel):
    """Schema for creating folder"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    parent_folder_id: Optional[UUID] = None
    event_id: Optional[UUID] = None
    vendor_id: Optional[UUID] = None
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class DocumentFolderUpdate(BaseModel):
    """Schema for updating folder"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class DocumentFolderResponse(BaseModel):
    """Schema for folder response"""
    id: UUID
    name: str
    description: Optional[str]
    parent_folder_id: Optional[UUID]
    path: Optional[str]
    event_id: Optional[UUID]
    vendor_id: Optional[UUID]
    document_count: int
    total_size: int
    created_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True


# Share Schemas
class DocumentShareCreate(BaseModel):
    """Schema for sharing document"""
    document_id: UUID
    shared_with_user_id: UUID
    access_level: AccessLevel = Field(AccessLevel.VIEWER)
    can_download: bool = Field(True)
    can_print: bool = Field(True)
    can_share: bool = Field(False)
    share_message: Optional[str] = None
    expires_at: Optional[datetime] = None


class DocumentShareResponse(BaseModel):
    """Schema for share response"""
    id: UUID
    document_id: UUID
    shared_with_user_id: UUID
    access_level: str
    can_download: bool
    can_print: bool
    can_share: bool
    expires_at: Optional[datetime]
    created_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True


# Comment Schemas
class DocumentCommentCreate(BaseModel):
    """Schema for creating comment"""
    document_id: UUID
    content: str = Field(..., min_length=1, max_length=2000)
    parent_comment_id: Optional[UUID] = None
    page_number: Optional[int] = None


class DocumentCommentResponse(BaseModel):
    """Schema for comment response"""
    id: UUID
    document_id: UUID
    content: str
    parent_comment_id: Optional[UUID]
    is_resolved: bool
    created_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True


# Signature Schemas
class DocumentSignatureRequest(BaseModel):
    """Schema for signature request"""
    document_id: UUID
    signers: List[Dict[str, Any]] = Field(..., min_items=1, max_items=10)
    # [{"user_id": "uuid"}, {"email": "test@test.com", "name": "John"}]
    expires_in_days: int = Field(30, ge=1, le=365)


class DocumentSignatureResponse(BaseModel):
    """Schema for signature response"""
    id: UUID
    document_id: UUID
    signer_user_id: Optional[UUID]
    signer_email: Optional[str]
    status: str
    requested_at: datetime
    signed_at: Optional[datetime]

    class Config:
        from_attributes = True


# Template Schemas
class DocumentTemplateCreate(BaseModel):
    """Schema for creating template"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    variables: List[Dict[str, Any]] = Field(default_factory=list)


class DocumentTemplateResponse(BaseModel):
    """Schema for template response"""
    id: UUID
    name: str
    description: Optional[str]
    category: Optional[str]
    file_name: str
    variables: List[Dict[str, Any]]
    usage_count: int
    is_active: bool
    created_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True


# Statistics
class DocumentStatistics(BaseModel):
    """Document statistics"""
    total_documents: int
    total_size: int
    by_type: Dict[str, int]
    by_status: Dict[str, int]
    pending_signatures: int
    recent_uploads: int
