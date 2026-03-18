"""Conversation persistence for workout chat — memory + debug logs."""

import uuid
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..db_models.workout import ChatConversation, ChatMessage

logger = logging.getLogger(__name__)


class ConversationService:

    @staticmethod
    def get_or_create(
        db: Session,
        user_id: int,
        conversation_id: Optional[str],
        context: str,
        session_id: Optional[int] = None,
    ) -> str:
        """Return existing conversation_id or create a new one."""
        if conversation_id:
            existing = db.query(ChatConversation).filter(
                ChatConversation.conversation_id == conversation_id,
            ).first()
            if existing:
                return existing.conversation_id

        # Create new
        cid = conversation_id or uuid.uuid4().hex
        conv = ChatConversation(
            conversation_id=cid,
            user_id=user_id,
            session_id=session_id,
            context=context,
        )
        db.add(conv)
        db.commit()
        return cid

    @staticmethod
    def add_message(
        db: Session,
        conversation_id: str,
        role: str,
        content: str,
        context: Optional[str] = None,
        source: Optional[str] = None,
        actions: Optional[list] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Log a single chat turn."""
        msg = ChatMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            context=context,
            source=source,
            actions=actions,
            metadata_json=metadata,
        )
        db.add(msg)
        db.commit()

    @staticmethod
    def get_history(
        db: Session,
        conversation_id: str,
        limit: int = 20,
    ) -> list[dict]:
        """Return prior turns as [{role, content}, ...] for LLM replay."""
        rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.id.asc())
            .limit(limit)
            .all()
        )
        return [{"role": r.role, "content": r.content} for r in rows]

    @staticmethod
    def close(db: Session, conversation_id: str) -> None:
        """Mark a conversation as closed."""
        conv = db.query(ChatConversation).filter(
            ChatConversation.conversation_id == conversation_id,
        ).first()
        if conv:
            conv.status = "closed"
            conv.closed_at = datetime.utcnow()
            db.commit()
