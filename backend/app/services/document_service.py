"""
Document Service

Business logic for document management.
"""

from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.models.user import User
from app.models.document import Document, DocumentFolder, DocumentShare
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import (
    DocumentUpload, DocumentUpdate, DocumentResponse,
    DocumentFolderCreate, DocumentFolderResponse,
    DocumentShareCreate, DocumentShareResponse,
    DocumentStatistics
)


class DocumentService:
    """Service for document management"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DocumentRepository(db)

    async def upload_document(
        self,
        file: UploadFile,
        document_data: DocumentUpload,
        current_user: User
    ) -> DocumentResponse:
        """Upload a document"""
        # In production, upload to S3/storage service
        file_path = f"/uploads/{file.filename}"  # Placeholder
        file_size = 0  # Get from file

        document = Document(
            **document_data.model_dump(),
            file_name=file.filename,
            file_path=file_path,
            file_size=file_size,
            file_extension=os.path.splitext(file.filename)[1],
            mime_type=file.content_type,
            uploaded_by=current_user.id
        )

        created_document = await self.repo.create_document(document)
        await self.db.commit()
        return DocumentResponse.model_validate(created_document)

    async def get_document(self, document_id: UUID, current_user: User) -> DocumentResponse:
        """Get document by ID"""
        document = await self.repo.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        # TODO: Check access permissions
        return DocumentResponse.model_validate(document)

    async def get_documents(
        self,
        event_id: Optional[UUID],
        folder_id: Optional[UUID],
        current_user: User,
        skip: int = 0,
        limit: int = 50
    ) -> List[DocumentResponse]:
        """Get documents"""
        documents = await self.repo.get_documents(
            event_id=event_id,
            folder_id=folder_id,
            skip=skip,
            limit=limit
        )
        return [DocumentResponse.model_validate(d) for d in documents]

    async def update_document(
        self,
        document_id: UUID,
        document_data: DocumentUpdate,
        current_user: User
    ) -> DocumentResponse:
        """Update document"""
        update_dict = document_data.model_dump(exclude_unset=True)
        updated_document = await self.repo.update_document(document_id, update_dict)
        if not updated_document:
            raise HTTPException(status_code=404, detail="Document not found")
        await self.db.commit()
        return DocumentResponse.model_validate(updated_document)

    async def delete_document(self, document_id: UUID, current_user: User) -> dict:
        """Delete document"""
        success = await self.repo.delete_document(document_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        await self.db.commit()
        return {"message": "Document deleted successfully"}

    # Folder Operations
    async def create_folder(
        self,
        folder_data: DocumentFolderCreate,
        current_user: User
    ) -> DocumentFolderResponse:
        """Create folder"""
        folder = DocumentFolder(**folder_data.model_dump(), created_by=current_user.id)
        created_folder = await self.repo.create_folder(folder)
        await self.db.commit()
        return DocumentFolderResponse.model_validate(created_folder)

    async def get_folders(
        self,
        event_id: Optional[UUID],
        current_user: User
    ) -> List[DocumentFolderResponse]:
        """Get folders"""
        folders = await self.repo.get_folders(event_id)
        return [DocumentFolderResponse.model_validate(f) for f in folders]

    # Share Operations
    async def share_document(
        self,
        share_data: DocumentShareCreate,
        current_user: User
    ) -> DocumentShareResponse:
        """Share document"""
        share = DocumentShare(**share_data.model_dump(), created_by=current_user.id)
        created_share = await self.repo.create_share(share)
        await self.db.commit()
        return DocumentShareResponse.model_validate(created_share)

    # Statistics
    async def get_statistics(
        self,
        event_id: Optional[UUID],
        current_user: User
    ) -> DocumentStatistics:
        """Get document statistics"""
        stats = await self.repo.get_document_statistics(event_id)
        return DocumentStatistics(**stats)
