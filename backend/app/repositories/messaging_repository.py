"""
CelebraTech Event Management System - Messaging Repository
Sprint 7: Messaging System
FR-007: Real-time Communication
Data access layer for messaging
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, update, delete
from sqlalchemy.orm import joinedload, selectinload
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID

from app.models.messaging import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageReadReceipt,
    MessageAttachment,
    TypingIndicator,
    MessageReaction,
    ConversationType,
    ConversationStatus,
    MessageStatus,
    ParticipantRole
)
from app.schemas.messaging import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
    ParticipantAdd,
    ConversationFilters
)


class MessagingRepository:
    """Repository for messaging data access"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Conversation Operations
    # ========================================================================

    async def create_conversation(
        self,
        conversation_data: ConversationCreate,
        creator_id: UUID
    ) -> Conversation:
        """Create a new conversation"""
        conversation = Conversation(
            type=conversation_data.type.value,
            title=conversation_data.title,
            description=conversation_data.description,
            booking_id=conversation_data.booking_id,
            event_id=conversation_data.event_id,
            created_by=creator_id,
            status=ConversationStatus.ACTIVE.value
        )

        self.db.add(conversation)
        await self.db.flush()

        # Add creator as participant (owner)
        creator_participant = ConversationParticipant(
            conversation_id=conversation.id,
            user_id=creator_id,
            role=ParticipantRole.OWNER.value
        )
        self.db.add(creator_participant)

        # Add other participants
        for participant_id in conversation_data.participant_ids:
            if participant_id != creator_id:
                participant = ConversationParticipant(
                    conversation_id=conversation.id,
                    user_id=participant_id,
                    role=ParticipantRole.MEMBER.value
                )
                self.db.add(participant)

        await self.db.flush()
        await self.db.refresh(conversation)

        return conversation

    async def get_conversation_by_id(
        self,
        conversation_id: UUID,
        load_relations: bool = False
    ) -> Optional[Conversation]:
        """Get conversation by ID"""
        query = select(Conversation).where(Conversation.id == conversation_id)

        if load_relations:
            query = query.options(
                joinedload(Conversation.creator),
                selectinload(Conversation.participants).joinedload(ConversationParticipant.user)
            )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_direct_conversation(
        self,
        user1_id: UUID,
        user2_id: UUID
    ) -> Optional[Conversation]:
        """Get existing direct conversation between two users"""
        # Find conversations where both users are participants
        query = select(Conversation).join(
            ConversationParticipant,
            Conversation.id == ConversationParticipant.conversation_id
        ).where(
            and_(
                Conversation.type == ConversationType.DIRECT.value,
                Conversation.status != ConversationStatus.BLOCKED.value,
                ConversationParticipant.user_id.in_([user1_id, user2_id])
            )
        ).group_by(Conversation.id).having(
            func.count(ConversationParticipant.user_id) == 2
        )

        result = await self.db.execute(query)
        conversations = result.scalars().all()

        # Verify both users are in the conversation
        for conv in conversations:
            participants_query = select(ConversationParticipant.user_id).where(
                ConversationParticipant.conversation_id == conv.id
            )
            participants_result = await self.db.execute(participants_query)
            participant_ids = set(participants_result.scalars().all())

            if participant_ids == {user1_id, user2_id}:
                return conv

        return None

    async def update_conversation(
        self,
        conversation_id: UUID,
        conversation_data: ConversationUpdate
    ) -> Optional[Conversation]:
        """Update conversation"""
        conversation = await self.get_conversation_by_id(conversation_id)
        if not conversation:
            return None

        update_data = conversation_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(conversation, field, value)

        conversation.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(conversation)

        return conversation

    async def archive_conversation(self, conversation_id: UUID) -> bool:
        """Archive a conversation"""
        conversation = await self.get_conversation_by_id(conversation_id)
        if not conversation:
            return False

        conversation.status = ConversationStatus.ARCHIVED.value
        conversation.archived_at = datetime.utcnow()

        await self.db.flush()
        return True

    async def list_user_conversations(
        self,
        user_id: UUID,
        filters: Optional[ConversationFilters] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Conversation], int]:
        """List conversations for a user"""
        # Base query - conversations where user is a participant
        query = select(Conversation).join(
            ConversationParticipant,
            Conversation.id == ConversationParticipant.conversation_id
        ).where(
            and_(
                ConversationParticipant.user_id == user_id,
                ConversationParticipant.is_active == True
            )
        )

        # Apply filters
        if filters:
            if filters.type:
                query = query.where(Conversation.type == filters.type.value)
            if filters.status:
                query = query.where(Conversation.status == filters.status.value)
            if filters.has_unread:
                if filters.has_unread:
                    query = query.where(ConversationParticipant.unread_count > 0)
                else:
                    query = query.where(ConversationParticipant.unread_count == 0)
            if filters.is_pinned is not None:
                query = query.where(ConversationParticipant.is_pinned == filters.is_pinned)
            if filters.is_muted is not None:
                query = query.where(ConversationParticipant.is_muted == filters.is_muted)
            if filters.booking_id:
                query = query.where(Conversation.booking_id == filters.booking_id)
            if filters.event_id:
                query = query.where(Conversation.event_id == filters.event_id)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Sort by last message time (most recent first)
        query = query.order_by(desc(Conversation.last_message_at))

        # Pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Load relations
        query = query.options(
            selectinload(Conversation.participants).joinedload(ConversationParticipant.user)
        )

        result = await self.db.execute(query)
        conversations = result.scalars().unique().all()

        return list(conversations), total

    # ========================================================================
    # Participant Operations
    # ========================================================================

    async def add_participant(
        self,
        conversation_id: UUID,
        participant_data: ParticipantAdd
    ) -> ConversationParticipant:
        """Add participant to conversation"""
        participant = ConversationParticipant(
            conversation_id=conversation_id,
            user_id=participant_data.user_id,
            role=participant_data.role.value
        )

        self.db.add(participant)
        await self.db.flush()
        await self.db.refresh(participant)

        return participant

    async def get_participant(
        self,
        conversation_id: UUID,
        user_id: UUID
    ) -> Optional[ConversationParticipant]:
        """Get participant"""
        query = select(ConversationParticipant).where(
            and_(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_participant_settings(
        self,
        conversation_id: UUID,
        user_id: UUID,
        **settings
    ) -> Optional[ConversationParticipant]:
        """Update participant settings"""
        participant = await self.get_participant(conversation_id, user_id)
        if not participant:
            return None

        for key, value in settings.items():
            if hasattr(participant, key) and value is not None:
                setattr(participant, key, value)

        await self.db.flush()
        await self.db.refresh(participant)

        return participant

    async def remove_participant(
        self,
        conversation_id: UUID,
        user_id: UUID
    ) -> bool:
        """Remove participant from conversation"""
        participant = await self.get_participant(conversation_id, user_id)
        if not participant:
            return False

        participant.is_active = False
        participant.left_at = datetime.utcnow()

        await self.db.flush()
        return True

    async def is_participant(
        self,
        conversation_id: UUID,
        user_id: UUID
    ) -> bool:
        """Check if user is participant in conversation"""
        query = select(func.count()).select_from(ConversationParticipant).where(
            and_(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
                ConversationParticipant.is_active == True
            )
        )
        result = await self.db.execute(query)
        count = result.scalar()
        return count > 0

    # ========================================================================
    # Message Operations
    # ========================================================================

    async def create_message(
        self,
        message_data: MessageCreate,
        sender_id: UUID
    ) -> Message:
        """Create a new message"""
        message = Message(
            conversation_id=message_data.conversation_id,
            sender_id=sender_id,
            reply_to_id=message_data.reply_to_id,
            type=message_data.type.value,
            content=message_data.content,
            status=MessageStatus.SENT.value,
            sent_at=datetime.utcnow()
        )

        self.db.add(message)
        await self.db.flush()

        # Create attachments
        if message_data.attachments:
            for att_data in message_data.attachments:
                attachment = MessageAttachment(
                    message_id=message.id,
                    uploaded_by=sender_id,
                    file_name=att_data.file_name,
                    file_type=att_data.file_type,
                    file_size=att_data.file_size,
                    file_url=att_data.file_url,
                    thumbnail_url=att_data.thumbnail_url,
                    width=att_data.width,
                    height=att_data.height,
                    duration=att_data.duration
                )
                self.db.add(attachment)

        # Update conversation
        await self.db.execute(
            update(Conversation)
            .where(Conversation.id == message_data.conversation_id)
            .values(
                last_message_at=datetime.utcnow(),
                last_message_preview=message.content[:100] if message.content else "[Attachment]",
                message_count=Conversation.message_count + 1
            )
        )

        # Update unread counts for other participants
        await self.db.execute(
            update(ConversationParticipant)
            .where(
                and_(
                    ConversationParticipant.conversation_id == message_data.conversation_id,
                    ConversationParticipant.user_id != sender_id,
                    ConversationParticipant.is_active == True
                )
            )
            .values(unread_count=ConversationParticipant.unread_count + 1)
        )

        await self.db.flush()
        await self.db.refresh(message)

        return message

    async def get_message_by_id(
        self,
        message_id: UUID,
        load_relations: bool = False
    ) -> Optional[Message]:
        """Get message by ID"""
        query = select(Message).where(Message.id == message_id)

        if load_relations:
            query = query.options(
                joinedload(Message.sender),
                selectinload(Message.read_receipts),
                selectinload(Message.attachments_rel)
            )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_message(
        self,
        message_id: UUID,
        content: str
    ) -> Optional[Message]:
        """Update message content"""
        message = await self.get_message_by_id(message_id)
        if not message or message.is_deleted:
            return None

        message.content = content
        message.is_edited = True
        message.edited_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(message)

        return message

    async def delete_message(
        self,
        message_id: UUID,
        delete_for_everyone: bool = False
    ) -> bool:
        """Delete message"""
        message = await self.get_message_by_id(message_id)
        if not message:
            return False

        message.is_deleted = True
        message.deleted_at = datetime.utcnow()
        message.deleted_for_everyone = delete_for_everyone

        if delete_for_everyone:
            message.content = None

        await self.db.flush()
        return True

    async def list_conversation_messages(
        self,
        conversation_id: UUID,
        page: int = 1,
        page_size: int = 50,
        before_message_id: Optional[UUID] = None
    ) -> Tuple[List[Message], int]:
        """List messages in a conversation"""
        query = select(Message).where(
            and_(
                Message.conversation_id == conversation_id,
                Message.is_deleted == False
            )
        )

        # Pagination with cursor (before_message_id)
        if before_message_id:
            before_message = await self.get_message_by_id(before_message_id)
            if before_message:
                query = query.where(Message.created_at < before_message.created_at)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Sort by created_at descending (most recent first)
        query = query.order_by(desc(Message.created_at))

        # Pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Load relations
        query = query.options(
            joinedload(Message.sender),
            selectinload(Message.read_receipts),
            selectinload(Message.attachments_rel)
        )

        result = await self.db.execute(query)
        messages = result.scalars().unique().all()

        # Reverse to chronological order
        return list(reversed(messages)), total

    async def search_messages(
        self,
        query_text: str,
        user_id: UUID,
        conversation_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Message], int]:
        """Search messages"""
        # Get user's conversations
        user_conversations_query = select(ConversationParticipant.conversation_id).where(
            and_(
                ConversationParticipant.user_id == user_id,
                ConversationParticipant.is_active == True
            )
        )
        user_conversations_result = await self.db.execute(user_conversations_query)
        user_conversation_ids = user_conversations_result.scalars().all()

        # Search query
        query = select(Message).where(
            and_(
                Message.conversation_id.in_(user_conversation_ids),
                Message.is_deleted == False,
                Message.content.ilike(f"%{query_text}%")
            )
        )

        if conversation_id:
            query = query.where(Message.conversation_id == conversation_id)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Sort by relevance (most recent first for now)
        query = query.order_by(desc(Message.created_at))

        # Pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Load relations
        query = query.options(joinedload(Message.sender))

        result = await self.db.execute(query)
        messages = result.scalars().unique().all()

        return list(messages), total

    # ========================================================================
    # Read Receipt Operations
    # ========================================================================

    async def mark_message_as_read(
        self,
        message_id: UUID,
        user_id: UUID
    ) -> MessageReadReceipt:
        """Mark message as read"""
        # Check if already read
        query = select(MessageReadReceipt).where(
            and_(
                MessageReadReceipt.message_id == message_id,
                MessageReadReceipt.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        existing_receipt = result.scalar_one_or_none()

        if existing_receipt:
            return existing_receipt

        # Create read receipt
        receipt = MessageReadReceipt(
            message_id=message_id,
            user_id=user_id,
            read_at=datetime.utcnow()
        )

        self.db.add(receipt)

        # Update message status if all participants have read
        message = await self.get_message_by_id(message_id)
        if message:
            # Get total participants (excluding sender)
            participants_query = select(func.count()).select_from(ConversationParticipant).where(
                and_(
                    ConversationParticipant.conversation_id == message.conversation_id,
                    ConversationParticipant.user_id != message.sender_id,
                    ConversationParticipant.is_active == True
                )
            )
            participants_result = await self.db.execute(participants_query)
            total_participants = participants_result.scalar()

            # Get total read receipts
            receipts_query = select(func.count()).select_from(MessageReadReceipt).where(
                MessageReadReceipt.message_id == message_id
            )
            receipts_result = await self.db.execute(receipts_query)
            total_receipts = receipts_result.scalar() + 1  # Include current receipt

            if total_receipts >= total_participants:
                message.status = MessageStatus.READ.value
                message.read_by_all_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(receipt)

        return receipt

    async def mark_conversation_as_read(
        self,
        conversation_id: UUID,
        user_id: UUID,
        up_to_message_id: Optional[UUID] = None
    ) -> int:
        """Mark conversation messages as read"""
        # Get messages to mark as read
        query = select(Message).where(
            and_(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.is_deleted == False
            )
        )

        if up_to_message_id:
            up_to_message = await self.get_message_by_id(up_to_message_id)
            if up_to_message:
                query = query.where(Message.created_at <= up_to_message.created_at)

        result = await self.db.execute(query)
        messages = result.scalars().all()

        # Mark each as read
        count = 0
        for message in messages:
            # Check if not already read
            check_query = select(func.count()).select_from(MessageReadReceipt).where(
                and_(
                    MessageReadReceipt.message_id == message.id,
                    MessageReadReceipt.user_id == user_id
                )
            )
            check_result = await self.db.execute(check_query)
            if check_result.scalar() == 0:
                await self.mark_message_as_read(message.id, user_id)
                count += 1

        # Update participant unread count
        await self.db.execute(
            update(ConversationParticipant)
            .where(
                and_(
                    ConversationParticipant.conversation_id == conversation_id,
                    ConversationParticipant.user_id == user_id
                )
            )
            .values(
                unread_count=0,
                last_read_at=datetime.utcnow(),
                last_read_message_id=up_to_message_id
            )
        )

        await self.db.flush()

        return count

    # ========================================================================
    # Typing Indicator Operations
    # ========================================================================

    async def set_typing_indicator(
        self,
        conversation_id: UUID,
        user_id: UUID,
        is_typing: bool = True
    ) -> TypingIndicator:
        """Set typing indicator"""
        # Check if indicator exists
        query = select(TypingIndicator).where(
            and_(
                TypingIndicator.conversation_id == conversation_id,
                TypingIndicator.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        indicator = result.scalar_one_or_none()

        if indicator:
            # Update existing
            indicator.is_typing = is_typing
            indicator.started_at = datetime.utcnow()
            indicator.expires_at = datetime.utcnow() + timedelta(seconds=10)
        else:
            # Create new
            indicator = TypingIndicator(
                conversation_id=conversation_id,
                user_id=user_id,
                is_typing=is_typing,
                started_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(seconds=10)
            )
            self.db.add(indicator)

        await self.db.flush()
        await self.db.refresh(indicator)

        return indicator

    async def get_typing_indicators(
        self,
        conversation_id: UUID
    ) -> List[TypingIndicator]:
        """Get active typing indicators"""
        # Clean up expired indicators first
        await self.db.execute(
            delete(TypingIndicator).where(TypingIndicator.expires_at < datetime.utcnow())
        )

        # Get active indicators
        query = select(TypingIndicator).where(
            and_(
                TypingIndicator.conversation_id == conversation_id,
                TypingIndicator.is_typing == True,
                TypingIndicator.expires_at > datetime.utcnow()
            )
        ).options(joinedload(TypingIndicator.user))

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    # ========================================================================
    # Reaction Operations
    # ========================================================================

    async def add_reaction(
        self,
        message_id: UUID,
        user_id: UUID,
        emoji: str
    ) -> MessageReaction:
        """Add reaction to message"""
        # Check if reaction already exists
        query = select(MessageReaction).where(
            and_(
                MessageReaction.message_id == message_id,
                MessageReaction.user_id == user_id,
                MessageReaction.emoji == emoji
            )
        )
        result = await self.db.execute(query)
        existing_reaction = result.scalar_one_or_none()

        if existing_reaction:
            return existing_reaction

        # Create reaction
        reaction = MessageReaction(
            message_id=message_id,
            user_id=user_id,
            emoji=emoji
        )

        self.db.add(reaction)
        await self.db.flush()
        await self.db.refresh(reaction)

        return reaction

    async def remove_reaction(
        self,
        message_id: UUID,
        user_id: UUID,
        emoji: str
    ) -> bool:
        """Remove reaction from message"""
        result = await self.db.execute(
            delete(MessageReaction).where(
                and_(
                    MessageReaction.message_id == message_id,
                    MessageReaction.user_id == user_id,
                    MessageReaction.emoji == emoji
                )
            )
        )

        await self.db.flush()
        return result.rowcount > 0

    async def get_message_reactions(
        self,
        message_id: UUID
    ) -> List[MessageReaction]:
        """Get all reactions for a message"""
        query = select(MessageReaction).where(
            MessageReaction.message_id == message_id
        ).options(joinedload(MessageReaction.user))

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    # ========================================================================
    # Statistics Operations
    # ========================================================================

    async def get_user_conversation_stats(
        self,
        user_id: UUID
    ) -> dict:
        """Get user's conversation statistics"""
        # Total conversations
        total_query = select(func.count()).select_from(ConversationParticipant).where(
            and_(
                ConversationParticipant.user_id == user_id,
                ConversationParticipant.is_active == True
            )
        )
        total_result = await self.db.execute(total_query)
        total_conversations = total_result.scalar()

        # Unread count
        unread_query = select(func.sum(ConversationParticipant.unread_count)).where(
            and_(
                ConversationParticipant.user_id == user_id,
                ConversationParticipant.is_active == True
            )
        )
        unread_result = await self.db.execute(unread_query)
        total_unread = unread_result.scalar() or 0

        # Unread conversations count
        unread_convs_query = select(func.count()).select_from(ConversationParticipant).where(
            and_(
                ConversationParticipant.user_id == user_id,
                ConversationParticipant.is_active == True,
                ConversationParticipant.unread_count > 0
            )
        )
        unread_convs_result = await self.db.execute(unread_convs_query)
        unread_conversations = unread_convs_result.scalar()

        return {
            "total_conversations": total_conversations,
            "total_unread_messages": total_unread,
            "unread_conversations": unread_conversations
        }
