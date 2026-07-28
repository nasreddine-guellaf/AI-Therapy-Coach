"""PostgreSQL adapters for conversation persistence ports."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.message import Message as DomainMessage
from app.domain.entities.message import MessageRole
from app.domain.entities.session import CoachingSession as DomainSession
from app.domain.entities.session import ConversationSummary
from app.domain.interfaces.conversation_repository import (
    ConversationRepositoryError,
    ConversationSessionRepository,
    MessageRepository,
)
from app.infrastructure.database.models import CoachingSession, Message
from app.infrastructure.database.postgres import async_session_factory


logger = logging.getLogger(__name__)
SessionFactory = async_sessionmaker[AsyncSession]


class PostgreSQLConversationSessionRepository(ConversationSessionRepository):
    """Persist sessions with short, operation-scoped transactions."""

    def __init__(self, session_factory: SessionFactory = async_session_factory) -> None:
        self._session_factory = session_factory

    async def create(self, user_id: UUID, title: str | None) -> DomainSession:
        try:
            async with self._session_factory() as database:
                async with database.begin():
                    model = CoachingSession(user_id=user_id, title=title)
                    database.add(model)
                    await database.flush()
                    await database.refresh(model)
                return _to_domain_session(model)
        except (SQLAlchemyError, OSError) as error:
            _raise_repository_error("create_session", error)

    async def get_owned(
        self, session_id: UUID, user_id: UUID
    ) -> DomainSession | None:
        try:
            async with self._session_factory() as database:
                result = await database.execute(
                    select(CoachingSession).where(
                        CoachingSession.id == session_id,
                        CoachingSession.user_id == user_id,
                    )
                )
                model = result.scalar_one_or_none()
                return _to_domain_session(model) if model else None
        except (SQLAlchemyError, OSError) as error:
            _raise_repository_error("get_owned_session", error)

    async def list_for_user(
        self, user_id: UUID, limit: int = 50
    ) -> list[ConversationSummary]:
        if limit <= 0:
            return []

        last_message_preview = (
            select(func.left(Message.content, 160))
            .where(Message.session_id == CoachingSession.id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(1)
            .correlate(CoachingSession)
            .scalar_subquery()
        )
        try:
            async with self._session_factory() as database:
                result = await database.execute(
                    select(CoachingSession, last_message_preview)
                    .where(CoachingSession.user_id == user_id)
                    .order_by(
                        CoachingSession.updated_at.desc(),
                        CoachingSession.id.desc(),
                    )
                    .limit(limit)
                )
                return [
                    ConversationSummary(
                        session_id=model.id,
                        title=model.title,
                        created_at=model.created_at,
                        updated_at=model.updated_at,
                        last_message_preview=preview,
                    )
                    for model, preview in result.all()
                ]
        except (SQLAlchemyError, OSError) as error:
            _raise_repository_error("list_user_sessions", error)

    async def delete_owned(self, session_id: UUID, user_id: UUID) -> bool:
        try:
            async with self._session_factory() as database:
                async with database.begin():
                    result = await database.execute(
                        delete(CoachingSession)
                        .where(
                            CoachingSession.id == session_id,
                            CoachingSession.user_id == user_id,
                        )
                        .returning(CoachingSession.id)
                    )
                    return result.scalar_one_or_none() is not None
        except (SQLAlchemyError, OSError) as error:
            _raise_repository_error("delete_owned_session", error)


class PostgreSQLMessageRepository(MessageRepository):
    """Persist messages and retrieve bounded chronological history."""

    def __init__(self, session_factory: SessionFactory = async_session_factory) -> None:
        self._session_factory = session_factory

    async def add(
        self,
        session_id: UUID,
        role: MessageRole,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> DomainMessage:
        try:
            async with self._session_factory() as database:
                async with database.begin():
                    model = Message(
                        session_id=session_id,
                        role=role.value,
                        content=content,
                        metadata_json=metadata,
                    )
                    database.add(model)
                    await database.flush()
                    await database.execute(
                        update(CoachingSession)
                        .where(CoachingSession.id == session_id)
                        .values(updated_at=model.created_at)
                    )
                    await database.refresh(model)
                return _to_domain_message(model)
        except (SQLAlchemyError, OSError) as error:
            _raise_repository_error("add_message", error)

    async def list_recent(
        self,
        session_id: UUID,
        limit: int,
        *,
        exclude_message_id: UUID | None = None,
    ) -> list[DomainMessage]:
        if limit <= 0:
            return []

        try:
            async with self._session_factory() as database:
                statement = select(Message).where(Message.session_id == session_id)
                if exclude_message_id is not None:
                    statement = statement.where(Message.id != exclude_message_id)
                result = await database.execute(
                    statement.order_by(Message.created_at.desc(), Message.id.desc()).limit(
                        limit
                    )
                )
                models = list(result.scalars())
                return [_to_domain_message(model) for model in reversed(models)]
        except (SQLAlchemyError, OSError) as error:
            _raise_repository_error("list_recent_messages", error)

    async def list_for_session(self, session_id: UUID) -> list[DomainMessage]:
        try:
            async with self._session_factory() as database:
                result = await database.execute(
                    select(Message)
                    .where(Message.session_id == session_id)
                    .order_by(Message.created_at.asc(), Message.id.asc())
                )
                return [_to_domain_message(model) for model in result.scalars()]
        except (SQLAlchemyError, OSError) as error:
            _raise_repository_error("list_session_messages", error)


def _to_domain_session(model: CoachingSession) -> DomainSession:
    return DomainSession(
        id=model.id,
        user_id=model.user_id,
        title=model.title,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_domain_message(model: Message) -> DomainMessage:
    return DomainMessage(
        id=model.id,
        session_id=model.session_id,
        role=MessageRole(model.role),
        content=model.content,
        metadata=model.metadata_json,
        created_at=model.created_at,
    )


def _raise_repository_error(operation: str, error: Exception) -> None:
    logger.warning(
        "Conversation persistence failed: operation=%s error_type=%s",
        operation,
        type(error).__name__,
    )
    raise ConversationRepositoryError("Conversation persistence is unavailable") from error
