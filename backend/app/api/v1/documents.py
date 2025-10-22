"""
Document Management API Endpoints

REST API for document upload, management, sharing, and collaboration.
"""

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
import json

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.document_service import DocumentService
from app.schemas.document import (
    DocumentUpload, DocumentUpdate, DocumentResponse,
    DocumentFolderCreate, DocumentFolderUpdate, DocumentFolderResponse,
    DocumentShareCreate, DocumentShareResponse,
    DocumentCommentCreate, DocumentCommentResponse,
    DocumentStatistics
)


router = APIRouter(prefix="/documents", tags=["Documents"])


# ============================================================================
# Document Endpoints
# ============================================================================

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    type: str = Form("other"),
    event_id: Optional[str] = Form(None),
    folder_id: Optional[str] = Form(None),
    tags: str = Form("[]"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a new document.

    Supports various file types including PDFs, images, documents.
    Automatically extracts metadata and indexes content for search.
    """
    tags_list = json.loads(tags) if tags else []
    event_uuid = UUID(event_id) if event_id else None
    folder_uuid = UUID(folder_id) if folder_id else None

    document_data = DocumentUpload(
        title=title,
        description=description,
        type=type,
        event_id=event_uuid,
        folder_id=folder_uuid,
        tags=tags_list
    )

    service = DocumentService(db)
    return await service.upload_document(file, document_data, current_user)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get document by ID with access control check."""
    service = DocumentService(db)
    return await service.get_document(document_id, current_user)


@router.get("", response_model=List[DocumentResponse])
async def get_documents(
    event_id: Optional[UUID] = Query(None),
    folder_id: Optional[UUID] = Query(None),
    document_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get documents with filters."""
    service = DocumentService(db)
    return await service.get_documents(event_id, folder_id, current_user, skip, limit)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    document_data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update document metadata."""
    service = DocumentService(db)
    return await service.update_document(document_id, document_data, current_user)


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete document."""
    service = DocumentService(db)
    return await service.delete_document(document_id, current_user)


# ============================================================================
# Folder Endpoints
# ============================================================================

@router.post("/folders", response_model=DocumentFolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: DocumentFolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a document folder for organization."""
    service = DocumentService(db)
    return await service.create_folder(folder_data, current_user)


@router.get("/folders", response_model=List[DocumentFolderResponse])
async def get_folders(
    event_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all folders with optional event filter."""
    service = DocumentService(db)
    return await service.get_folders(event_id, current_user)


# ============================================================================
# Share Endpoints
# ============================================================================

@router.post("/share", response_model=DocumentShareResponse, status_code=status.HTTP_201_CREATED)
async def share_document(
    share_data: DocumentShareCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Share document with another user.

    Set access level (owner, editor, viewer, commenter) and permissions.
    """
    service = DocumentService(db)
    return await service.share_document(share_data, current_user)


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/statistics", response_model=DocumentStatistics)
async def get_document_statistics(
    event_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get document statistics.

    Includes total documents, storage usage, document types breakdown.
    """
    service = DocumentService(db)
    return await service.get_statistics(event_id, current_user)


# ============================================================================
# Download Endpoint
# ============================================================================

@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download document file.

    Checks permissions and logs download activity.
    """
    # TODO: Implement file download
    return {
        "message": "Download functionality coming soon",
        "document_id": document_id
    }
