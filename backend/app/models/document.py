"""
Document Management Models

This module defines the database models for document management including
documents, folders, versions, templates, and signatures.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Numeric, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


# Enums
class DocumentType(str, enum.Enum):
    """Document type enumeration"""
    CONTRACT = "contract"
    INVOICE = "invoice"
    RECEIPT = "receipt"
    PROPOSAL = "proposal"
    AGREEMENT = "agreement"
    PERMIT = "permit"
    LICENSE = "license"
    INSURANCE = "insurance"
    QUOTE = "quote"
    REPORT = "report"
    PRESENTATION = "presentation"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    """Document status enumeration"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SIGNED = "signed"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class AccessLevel(str, enum.Enum):
    """Access level for document sharing"""
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    COMMENTER = "commenter"


class SignatureStatus(str, enum.Enum):
    """E-signature status"""
    PENDING = "pending"
    SIGNED = "signed"
    DECLINED = "declined"
    EXPIRED = "expired"


class Document(Base):
    """
    Document model representing uploaded files and documents

    Supports versioning, sharing, and comprehensive metadata
    """
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Document details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), default=DocumentType.OTHER.value, index=True)

    # File information
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # Storage path
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_extension = Column(String(10), nullable=True)
    mime_type = Column(String(100), nullable=True)

    # Document metadata
    version_number = Column(Integer, default=1)
    is_latest_version = Column(Boolean, default=True)
    parent_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)

    # Status
    status = Column(String(20), default=DocumentStatus.DRAFT.value, index=True)

    # Associations
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True, index=True)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True, index=True)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True, index=True)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payment_transactions.id"), nullable=True)

    # Folder organization
    folder_id = Column(UUID(as_uuid=True), ForeignKey("document_folders.id"), nullable=True, index=True)

    # Document properties
    is_template = Column(Boolean, default=False)
    requires_signature = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)

    # Expiration
    expires_at = Column(DateTime, nullable=True)

    # Security
    password_protected = Column(Boolean, default=False)
    password_hash = Column(String(255), nullable=True)
    encryption_enabled = Column(Boolean, default=False)

    # Content extraction (for search)
    extracted_text = Column(Text, nullable=True)  # Full-text search
    tags = Column(ARRAY(String(50)), default=list)

    # Document metadata
    metadata = Column(JSON, default={})
    # {
    #     "author": "John Doe",
    #     "company": "ABC Corp",
    #     "contract_value": 5000.00,
    #     "contract_date": "2024-01-01",
    #     "custom_fields": {}
    # }

    # Statistics
    download_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    event = relationship("Event", foreign_keys=[event_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    booking = relationship("Booking", foreign_keys=[booking_id])
    folder = relationship("DocumentFolder", back_populates="documents")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    parent_document = relationship("Document", remote_side=[id], foreign_keys=[parent_document_id])
    versions = relationship("Document", foreign_keys=[parent_document_id], cascade="all, delete-orphan")
    shares = relationship("DocumentShare", back_populates="document", cascade="all, delete-orphan")
    comments = relationship("DocumentComment", back_populates="document", cascade="all, delete-orphan")
    signatures = relationship("DocumentSignature", back_populates="document", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_document_type", "type"),
        Index("idx_document_status", "status"),
        Index("idx_document_event", "event_id"),
        Index("idx_document_vendor", "vendor_id"),
        Index("idx_document_folder", "folder_id"),
        Index("idx_document_created", "created_at"),
        Index("idx_document_template", "is_template"),
    )

    def __repr__(self):
        return f"<Document {self.title} ({self.file_name})>"


class DocumentFolder(Base):
    """
    Document folder model for organizing documents

    Supports hierarchical folder structure
    """
    __tablename__ = "document_folders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Folder details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color

    # Hierarchy
    parent_folder_id = Column(UUID(as_uuid=True), ForeignKey("document_folders.id"), nullable=True)
    path = Column(String(1000), nullable=True)  # Full path for quick lookup

    # Associations
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True, index=True)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True, index=True)

    # Properties
    is_public = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)

    # Statistics
    document_count = Column(Integer, default=0)
    total_size = Column(Integer, default=0)  # Total size in bytes

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    event = relationship("Event", foreign_keys=[event_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    creator = relationship("User", foreign_keys=[created_by])
    parent_folder = relationship("DocumentFolder", remote_side=[id], foreign_keys=[parent_folder_id])
    subfolders = relationship("DocumentFolder", foreign_keys=[parent_folder_id], cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="folder")

    # Indexes
    __table_args__ = (
        Index("idx_folder_event", "event_id"),
        Index("idx_folder_vendor", "vendor_id"),
        Index("idx_folder_parent", "parent_folder_id"),
    )

    def __repr__(self):
        return f"<DocumentFolder {self.name}>"


class DocumentShare(Base):
    """
    Document share model for sharing documents with users

    Controls access levels and permissions
    """
    __tablename__ = "document_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Share details
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    shared_with_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Access control
    access_level = Column(String(20), default=AccessLevel.VIEWER.value)

    # Permissions
    can_download = Column(Boolean, default=True)
    can_print = Column(Boolean, default=True)
    can_share = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)

    # Expiration
    expires_at = Column(DateTime, nullable=True)

    # Notification
    notify_on_view = Column(Boolean, default=False)
    notify_on_download = Column(Boolean, default=False)

    # Message
    share_message = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    accepted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="shares")
    shared_with = relationship("User", foreign_keys=[shared_with_user_id])
    sharer = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        Index("idx_share_document", "document_id"),
        Index("idx_share_user", "shared_with_user_id"),
        UniqueConstraint("document_id", "shared_with_user_id", name="uq_document_user_share"),
    )

    def __repr__(self):
        return f"<DocumentShare {self.document_id} with {self.shared_with_user_id}>"


class DocumentComment(Base):
    """
    Document comment model for collaboration

    Allows users to comment on documents
    """
    __tablename__ = "document_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Comment details
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)

    # Threading
    parent_comment_id = Column(UUID(as_uuid=True), ForeignKey("document_comments.id"), nullable=True)

    # Location (for PDF annotations)
    page_number = Column(Integer, nullable=True)
    position_x = Column(Numeric(10, 2), nullable=True)
    position_y = Column(Numeric(10, 2), nullable=True)

    # Status
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="comments")
    author = relationship("User", foreign_keys=[created_by])
    resolver = relationship("User", foreign_keys=[resolved_by])
    parent_comment = relationship("DocumentComment", remote_side=[id], foreign_keys=[parent_comment_id])
    replies = relationship("DocumentComment", foreign_keys=[parent_comment_id])

    # Indexes
    __table_args__ = (
        Index("idx_comment_document", "document_id"),
        Index("idx_comment_parent", "parent_comment_id"),
        Index("idx_comment_created", "created_at"),
    )

    def __repr__(self):
        return f"<DocumentComment {self.id} on {self.document_id}>"


class DocumentSignature(Base):
    """
    Document signature model for e-signature tracking

    Tracks signature requests and completion
    """
    __tablename__ = "document_signatures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Signature details
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    signer_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    # Signer information (for non-users)
    signer_name = Column(String(200), nullable=True)
    signer_email = Column(String(255), nullable=True)
    signer_title = Column(String(100), nullable=True)

    # Signature status
    status = Column(String(20), default=SignatureStatus.PENDING.value, index=True)
    order = Column(Integer, default=1)  # Signing order

    # Signature data
    signature_data = Column(Text, nullable=True)  # Base64 encoded signature
    signature_type = Column(String(20), nullable=True)  # draw, type, upload
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Certificate (for verification)
    certificate_data = Column(JSON, default={})

    # Expiration
    expires_at = Column(DateTime, nullable=True)

    # Notification
    reminder_sent_count = Column(Integer, default=0)
    last_reminder_sent_at = Column(DateTime, nullable=True)

    # Timestamps
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    signed_at = Column(DateTime, nullable=True)
    declined_at = Column(DateTime, nullable=True)
    decline_reason = Column(Text, nullable=True)

    # Request details
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="signatures")
    signer = relationship("User", foreign_keys=[signer_user_id])
    requester = relationship("User", foreign_keys=[requested_by])

    # Indexes
    __table_args__ = (
        Index("idx_signature_document", "document_id"),
        Index("idx_signature_signer", "signer_user_id"),
        Index("idx_signature_status", "status"),
    )

    def __repr__(self):
        return f"<DocumentSignature {self.id} - {self.status}>"


class DocumentTemplate(Base):
    """
    Document template model for reusable document templates

    Supports variable substitution and customization
    """
    __tablename__ = "document_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Template details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)

    # Template file
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=True)

    # Template variables
    variables = Column(JSON, default=[])
    # [
    #     {"name": "client_name", "type": "text", "required": true},
    #     {"name": "event_date", "type": "date", "required": true}
    # ]

    # Template content (for text-based templates)
    content = Column(Text, nullable=True)

    # Usage
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        Index("idx_template_category", "category"),
        Index("idx_template_active", "is_active"),
    )

    def __repr__(self):
        return f"<DocumentTemplate {self.name}>"


class DocumentActivity(Base):
    """
    Document activity log for tracking document access and changes

    Audit trail for document operations
    """
    __tablename__ = "document_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Activity details
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    # Actions: uploaded, viewed, downloaded, edited, deleted, shared, signed, commented

    # Actor
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Details
    details = Column(JSON, default={})
    # {
    #     "shared_with": "user_id",
    #     "version_from": 1,
    #     "version_to": 2,
    #     "changes": {}
    # }

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    document = relationship("Document")
    user = relationship("User", foreign_keys=[user_id])

    # Indexes
    __table_args__ = (
        Index("idx_activity_document", "document_id"),
        Index("idx_activity_user", "user_id"),
        Index("idx_activity_action", "action"),
        Index("idx_activity_created", "created_at"),
    )

    def __repr__(self):
        return f"<DocumentActivity {self.action} on {self.document_id}>"
