"""
CelebraTech Event Management System - Messaging Service
Sprint 7: Messaging System
FR-007: Real-time Communication
Business logic for messaging operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List, Optional, Tuple
from datetime import datetime
from uuid import UUID

from app.repositories.messaging_repository import MessagingRepository
from app.models.user import User, UserRole
from app.models.messaging import ConversationType, ParticipantRole
from app.schemas.messaging import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
    MessageUpdate,
    ParticipantAdd,
    ParticipantUpdate,
    MarkAsRead,
    MarkConversationAsRead,
    TypingIndicatorCreate,
    MessageReactionCreate,
    ConversationFilters,
    MessageSearch
)


class MessagingService:
    """Service for messaging business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MessagingRepository(db)

    # ========================================================================
    # Conversation Operations
    # ========================================================================

    async def create_conversation(
        self,
        conversation_data: ConversationCreate,
        current_user: User
    ):
        """
        Create a new conversation

        Business rules:
        - Direct conversations: Check if already exists between participants
        - Group conversations: Require title
        - User must be in participant list
        """
        # For direct conversations, check if already exists
        if conversation_data.type == ConversationType.DIRECT:
            if len(conversation_data.participant_ids) != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Direct conversations must have exactly 1 other participant"
                )

            # Check if conversation already exists
            other_user_id = conversation_data.participant_ids[0]
            existing_conv = await self.repo.get_direct_conversation(
                current_user.id,
                other_user_id
            )

            if existing_conv:
                # Return existing conversation
                return existing_conv

        # Create conversation
        conversation = await self.repo.create_conversation(
            conversation_data,
            current_user.id
        )

        await self.db.commit()

        return conversation

    async def get_conversation(
        self,
        conversation_id: UUID,
        current_user: User
    ):
        """Get conversation by ID"""
        conversation = await self.repo.get_conversation_by_id(
            conversation_id,
            load_relations=True
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Check if user is participant
        is_participant = await self.repo.is_participant(conversation_id, current_user.id)
        if not is_participant and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this conversation"
            )

        return conversation

    async def update_conversation(
        self,
        conversation_id: UUID,
        conversation_data: ConversationUpdate,
        current_user: User
    ):
        """
        Update conversation

        Business rules:
        - Only owner or admin can update
        """
        conversation = await self.repo.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Check permissions
        is_owner = str(conversation.created_by) == str(current_user.id)
        is_admin = current_user.role == UserRole.ADMIN.value

        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only conversation owner can update"
            )

        # Update conversation
        updated_conversation = await self.repo.update_conversation(
            conversation_id,
            conversation_data
        )

        await self.db.commit()

        return updated_conversation

    async def archive_conversation(
        self,
        conversation_id: UUID,
        current_user: User
    ):
        """Archive conversation"""
        # Check if user is participant
        is_participant = await self.repo.is_participant(conversation_id, current_user.id)
        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to archive this conversation"
            )

        # Archive
        success = await self.repo.archive_conversation(conversation_id)
        await self.db.commit()

        return success

    async def list_conversations(
        self,
        current_user: User,
        filters: Optional[ConversationFilters] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List, int]:
        """List user's conversations"""
        return await self.repo.list_user_conversations(
            current_user.id,
            filters,
            page,
            page_size
        )

    # ========================================================================
    # Participant Operations
    # ========================================================================

    async def add_participant(
        self,
        conversation_id: UUID,
        participant_data: ParticipantAdd,
        current_user: User
    ):
        """
        Add participant to conversation

        Business rules:
        - Only owner or admin can add participants
        - Cannot add to direct conversations
        """
        conversation = await self.repo.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Check if direct conversation
        if conversation.type == ConversationType.DIRECT.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add participants to direct conversations"
            )

        # Check permissions
        is_owner = str(conversation.created_by) == str(current_user.id)
        is_admin = current_user.role == UserRole.ADMIN.value

        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only conversation owner can add participants"
            )

        # Add participant
        participant = await self.repo.add_participant(conversation_id, participant_data)
        await self.db.commit()

        return participant

    async def update_participant_settings(
        self,
        conversation_id: UUID,
        settings_data: ParticipantUpdate,
        current_user: User
    ):
        """Update participant settings (own settings)"""
        # Check if user is participant
        participant = await self.repo.get_participant(conversation_id, current_user.id)
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not a participant in this conversation"
            )

        # Update settings
        settings_dict = settings_data.dict(exclude_unset=True)
        updated_participant = await self.repo.update_participant_settings(
            conversation_id,
            current_user.id,
            **settings_dict
        )

        await self.db.commit()

        return updated_participant

    async def leave_conversation(
        self,
        conversation_id: UUID,
        current_user: User
    ):
        """Leave conversation"""
        # Check if user is participant
        is_participant = await self.repo.is_participant(conversation_id, current_user.id)
        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not a participant in this conversation"
            )

        # Leave
        success = await self.repo.remove_participant(conversation_id, current_user.id)
        await self.db.commit()

        return success

    # ========================================================================
    # Message Operations
    # ========================================================================

    async def send_message(
        self,
        message_data: MessageCreate,
        current_user: User
    ):
        """
        Send a message

        Business rules:
        - User must be participant in conversation
        - Content required for text messages
        - Attachments required for attachment messages
        """
        # Check if user is participant
        is_participant = await self.repo.is_participant(
            message_data.conversation_id,
            current_user.id
        )

        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to send messages in this conversation"
            )

        # Validate reply_to message exists in same conversation
        if message_data.reply_to_id:
            reply_to = await self.repo.get_message_by_id(message_data.reply_to_id)
            if not reply_to:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Reply-to message not found"
                )
            if str(reply_to.conversation_id) != str(message_data.conversation_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reply-to message must be in same conversation"
                )

        # Send message
        message = await self.repo.create_message(message_data, current_user.id)
        await self.db.commit()

        return message

    async def get_message(
        self,
        message_id: UUID,
        current_user: User
    ):
        """Get message by ID"""
        message = await self.repo.get_message_by_id(message_id, load_relations=True)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )

        # Check if user is participant in conversation
        is_participant = await self.repo.is_participant(
            message.conversation_id,
            current_user.id
        )

        if not is_participant and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this message"
            )

        return message

    async def update_message(
        self,
        message_id: UUID,
        message_data: MessageUpdate,
        current_user: User
    ):
        """
        Update message

        Business rules:
        - Only sender can update
        - Can update within 15 minutes
        - Cannot update deleted messages
        """
        message = await self.repo.get_message_by_id(message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )

        # Check if sender
        if str(message.sender_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only sender can update message"
            )

        # Check if deleted
        if message.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update deleted message"
            )

        # Check time limit (15 minutes)
        minutes_since_sent = (datetime.utcnow() - message.sent_at).total_seconds() / 60
        if minutes_since_sent > 15:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update message after 15 minutes"
            )

        # Update message
        updated_message = await self.repo.update_message(
            message_id,
            message_data.content
        )

        await self.db.commit()

        return updated_message

    async def delete_message(
        self,
        message_id: UUID,
        delete_for_everyone: bool,
        current_user: User
    ):
        """
        Delete message

        Business rules:
        - Only sender can delete
        - Delete for everyone: within 1 hour
        - Delete for self: anytime
        """
        message = await self.repo.get_message_by_id(message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )

        # Check if sender
        if str(message.sender_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only sender can delete message"
            )

        # Check time limit for delete_for_everyone (1 hour)
        if delete_for_everyone:
            hours_since_sent = (datetime.utcnow() - message.sent_at).total_seconds() / 3600
            if hours_since_sent > 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Can only delete for everyone within 1 hour"
                )

        # Delete message
        success = await self.repo.delete_message(message_id, delete_for_everyone)
        await self.db.commit()

        return success

    async def list_messages(
        self,
        conversation_id: UUID,
        current_user: User,
        page: int = 1,
        page_size: int = 50,
        before_message_id: Optional[UUID] = None
    ) -> Tuple[List, int]:
        """List messages in conversation"""
        # Check if user is participant
        is_participant = await self.repo.is_participant(conversation_id, current_user.id)
        if not is_participant and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view messages in this conversation"
            )

        return await self.repo.list_conversation_messages(
            conversation_id,
            page,
            page_size,
            before_message_id
        )

    async def search_messages(
        self,
        search_data: MessageSearch,
        current_user: User,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List, int]:
        """Search messages"""
        return await self.repo.search_messages(
            search_data.query,
            current_user.id,
            search_data.conversation_id,
            page,
            page_size
        )

    # ========================================================================
    # Read Receipt Operations
    # ========================================================================

    async def mark_messages_as_read(
        self,
        mark_data: MarkAsRead,
        current_user: User
    ):
        """Mark messages as read"""
        receipts = []
        for message_id in mark_data.message_ids:
            # Get message
            message = await self.repo.get_message_by_id(message_id)
            if not message:
                continue

            # Check if user is participant
            is_participant = await self.repo.is_participant(
                message.conversation_id,
                current_user.id
            )

            if not is_participant:
                continue

            # Don't mark own messages as read
            if str(message.sender_id) == str(current_user.id):
                continue

            # Mark as read
            receipt = await self.repo.mark_message_as_read(message_id, current_user.id)
            receipts.append(receipt)

        await self.db.commit()

        return receipts

    async def mark_conversation_as_read(
        self,
        conversation_id: UUID,
        mark_data: MarkConversationAsRead,
        current_user: User
    ):
        """Mark conversation as read"""
        # Check if user is participant
        is_participant = await self.repo.is_participant(conversation_id, current_user.id)
        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to mark this conversation as read"
            )

        # Mark as read
        count = await self.repo.mark_conversation_as_read(
            conversation_id,
            current_user.id,
            mark_data.up_to_message_id
        )

        await self.db.commit()

        return {"marked_count": count}

    # ========================================================================
    # Typing Indicator Operations
    # ========================================================================

    async def set_typing_indicator(
        self,
        typing_data: TypingIndicatorCreate,
        current_user: User
    ):
        """Set typing indicator"""
        # Check if user is participant
        is_participant = await self.repo.is_participant(
            typing_data.conversation_id,
            current_user.id
        )

        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to set typing indicator in this conversation"
            )

        # Set indicator
        indicator = await self.repo.set_typing_indicator(
            typing_data.conversation_id,
            current_user.id,
            typing_data.is_typing
        )

        await self.db.commit()

        return indicator

    async def get_typing_indicators(
        self,
        conversation_id: UUID,
        current_user: User
    ):
        """Get typing indicators"""
        # Check if user is participant
        is_participant = await self.repo.is_participant(conversation_id, current_user.id)
        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view typing indicators"
            )

        return await self.repo.get_typing_indicators(conversation_id)

    # ========================================================================
    # Reaction Operations
    # ========================================================================

    async def add_reaction(
        self,
        message_id: UUID,
        reaction_data: MessageReactionCreate,
        current_user: User
    ):
        """Add reaction to message"""
        # Get message
        message = await self.repo.get_message_by_id(message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )

        # Check if user is participant
        is_participant = await self.repo.is_participant(
            message.conversation_id,
            current_user.id
        )

        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to react to this message"
            )

        # Add reaction
        reaction = await self.repo.add_reaction(
            message_id,
            current_user.id,
            reaction_data.emoji
        )

        await self.db.commit()

        return reaction

    async def remove_reaction(
        self,
        message_id: UUID,
        emoji: str,
        current_user: User
    ):
        """Remove reaction from message"""
        # Get message
        message = await self.repo.get_message_by_id(message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )

        # Remove reaction
        success = await self.repo.remove_reaction(message_id, current_user.id, emoji)
        await self.db.commit()

        return success

    async def get_message_reactions(
        self,
        message_id: UUID,
        current_user: User
    ):
        """Get message reactions"""
        # Get message
        message = await self.repo.get_message_by_id(message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )

        # Check if user is participant
        is_participant = await self.repo.is_participant(
            message.conversation_id,
            current_user.id
        )

        if not is_participant and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view reactions"
            )

        return await self.repo.get_message_reactions(message_id)

    # ========================================================================
    # Statistics Operations
    # ========================================================================

    async def get_conversation_stats(self, current_user: User):
        """Get user's conversation statistics"""
        return await self.repo.get_user_conversation_stats(current_user.id)
