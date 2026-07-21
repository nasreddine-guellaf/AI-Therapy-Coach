"""SQLAlchemy implementation of the authentication user repository."""

import logging
from uuid import UUID

from asyncpg import PostgresError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import User as DomainUser
from app.domain.interfaces.auth import UserAlreadyExistsError, UserRepositoryError
from app.domain.interfaces.auth import UserRepository as UserRepositoryPort
from app.infrastructure.database.models import User as UserModel


logger = logging.getLogger(__name__)


class PostgreSQLUserRepository(UserRepositoryPort):
    """Persist normalized users through one request-scoped async session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> DomainUser | None:
        try:
            result = await self._session.execute(
                select(UserModel).where(UserModel.email == email)
            )
            model = result.scalar_one_or_none()
            return self._to_domain(model) if model else None
        except (SQLAlchemyError, PostgresError, OSError) as error:
            self._log_database_error("get_by_email", error)
            raise UserRepositoryError from error

    async def get_by_id(self, user_id: UUID) -> DomainUser | None:
        try:
            model = await self._session.get(UserModel, user_id)
            return self._to_domain(model) if model else None
        except (SQLAlchemyError, PostgresError, OSError) as error:
            self._log_database_error("get_by_id", error)
            raise UserRepositoryError from error

    async def create(
        self,
        *,
        email: str,
        hashed_password: str,
        full_name: str | None,
    ) -> DomainUser:
        model = UserModel(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
        )
        self._session.add(model)
        try:
            await self._session.flush()
            await self._session.refresh(model)
        except IntegrityError as error:
            self._log_database_error("create_conflict", error)
            raise UserAlreadyExistsError from error
        except (SQLAlchemyError, PostgresError, OSError) as error:
            self._log_database_error("create", error)
            raise UserRepositoryError from error
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: UserModel) -> DomainUser:
        return DomainUser(
            id=model.id,
            email=model.email,
            hashed_password=model.hashed_password,
            full_name=model.full_name,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _log_database_error(
        operation: str,
        error: SQLAlchemyError | PostgresError | OSError,
    ) -> None:
        logger.warning(
            "User repository failure: operation=%s error_type=%s",
            operation,
            type(error).__name__,
        )
