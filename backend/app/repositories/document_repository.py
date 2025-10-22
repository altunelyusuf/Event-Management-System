"""
Document Repository

Data access layer for document management.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from typing import Optional, List
from uuid import UUID

from app.models.document import (
    Document, DocumentFolder, DocumentShare, DocumentComment,
    DocumentSignature, DocumentTemplate, DocumentActivity
)
from app.schemas.document import DocumentUpload, DocumentUpdate


class DocumentRepository:
    """Repository for document operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Document CRUD
    async def create_document(self, document: Document) -> Document:
        """Create a document"""
        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def get_document(self, document_id: UUID) -> Optional[Document]:
        """Get document by ID"""
        query = select(Document).where(Document.id == document_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_documents(
        self,
        event_id: Optional[UUID] = None,
        vendor_id: Optional[UUID] = None,
        folder_id: Optional[UUID] = None,
        document_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Document]:
        """Get documents with filters"""
        query = select(Document).where(Document.is_latest_version == True)

        if event_id:
            query = query.where(Document.event_id == event_id)
        if vendor_id:
            query = query.where(Document.vendor_id == vendor_id)
        if folder_id:
            query = query.where(Document.folder_id == folder_id)
        if document_type:
            query = query.where(Document.type == document_type)

        query = query.order_by(desc(Document.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_document(self, document_id: UUID, update_data: dict) -> Optional[Document]:
        """Update document"""
        document = await self.get_document(document_id)
        if not document:
            return None

        for key, value in update_data.items():
            if hasattr(document, key):
                setattr(document, key, value)

        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def delete_document(self, document_id: UUID) -> bool:
        """Delete document"""
        document = await self.get_document(document_id)
        if not document:
            return False
        await self.db.delete(document)
        await self.db.flush()
        return True

    # Folder Operations
    async def create_folder(self, folder: DocumentFolder) -> DocumentFolder:
        """Create folder"""
        self.db.add(folder)
        await self.db.flush()
        await self.db.refresh(folder)
        return folder

    async def get_folder(self, folder_id: UUID) -> Optional[DocumentFolder]:
        """Get folder by ID"""
        query = select(DocumentFolder).where(DocumentFolder.id == folder_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_folders(self, event_id: Optional[UUID] = None) -> List[DocumentFolder]:
        """Get folders"""
        query = select(DocumentFolder)
        if event_id:
            query = query.where(DocumentFolder.event_id == event_id)
        query = query.order_by(DocumentFolder.name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # Share Operations
    async def create_share(self, share: DocumentShare) -> DocumentShare:
        """Create document share"""
        self.db.add(share)
        await self.db.flush()
        await self.db.refresh(share)
        return share

    async def get_shares(self, document_id: UUID) -> List[DocumentShare]:
        """Get shares for document"""
        query = select(DocumentShare).where(DocumentShare.document_id == document_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # Activity Logging
    async def log_activity(self, activity: DocumentActivity) -> DocumentActivity:
        """Log document activity"""
        self.db.add(activity)
        await self.db.flush()
        await self.db.refresh(activity)
        return activity

    # Statistics
    async def get_document_statistics(self, event_id: Optional[UUID] = None) -> dict:
        """Get document statistics"""
        query = select(func.count(Document.id), func.sum(Document.file_size)).where(
            Document.is_latest_version == True
        )
        if event_id:
            query = query.where(Document.event_id == event_id)

        result = await self.db.execute(query)
        total_docs, total_size = result.one()

        return {
            "total_documents": total_docs or 0,
            "total_size": int(total_size or 0),
            "by_type": {},
            "by_status": {},
            "pending_signatures": 0,
            "recent_uploads": 0
        }
