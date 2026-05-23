from __future__ import annotations

import uuid
from typing import Annotated, Any, cast

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.logging import get_logger
from database.models.users import User
from security.dependencies.auth import (
    CurrentAccessPayloadDependency,
    CurrentRefreshPayloadDependency,
    DatabaseSessionDependency,
    OptionalAccessPayloadDependency,
    forbidden_exception,
    unauthorized_exception,
)
from security.permissions import (
    PermissionDeniedError,
    is_active_user,
    require_active_user,
    require_admin,
)


logger = get_logger(__name__)


async def get_user_by_id(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    load_roles: bool = True,
) -> User | None:
    statement = select(User).where(User.id == user_id)
    if load_roles:
        statement = statement.options(selectinload(User.roles))
    try:
        result = await session.execute(statement)
        return result.scalar_one_or_none()
    except SQLAlchemyError as exc:
        logger.warning(
            "Failed to load user by id",
            extra={
                "user_id": str(user_id),
                "reason": str(exc),
                "error_type": exc.__class__.__name__,
            },
        )
        raise unauthorized_exception("Не удалось загрузить пользователя.") from exc


async def get_current_user(
    payload: CurrentAccessPayloadDependency,
    session: DatabaseSessionDependency,
) -> User:
    user = await get_user_by_id(cast(AsyncSession, session), payload.user_id)
    if user is None:
        raise unauthorized_exception("Пользователь из токена не найден.")
    return user


async def get_optional_current_user(
    payload: OptionalAccessPayloadDependency,
    session: DatabaseSessionDependency,
) -> User | None:
    if payload is None:
        return None
    user = await get_user_by_id(cast(AsyncSession, session), payload.user_id)
    if user is None:
        raise unauthorized_exception("Пользователь из токена не найден.")
    return user


async def get_current_user_from_refresh_token(
    payload: CurrentRefreshPayloadDependency,
    session: DatabaseSessionDependency,
) -> User:
    user = await get_user_by_id(cast(AsyncSession, session), payload.user_id)
    if user is None:
        raise unauthorized_exception("Пользователь из refresh token не найден.")
    return user


CurrentUserDependency = Annotated[User, Depends(get_current_user)]
OptionalCurrentUserDependency = Annotated[User | None, Depends(get_optional_current_user)]
CurrentRefreshUserDependency = Annotated[
    User,
    Depends(get_current_user_from_refresh_token),
]


async def get_current_active_user(user: CurrentUserDependency) -> User:
    try:
        require_active_user(cast(Any, user))
    except PermissionDeniedError as exc:
        raise forbidden_exception("Учётная запись неактивна или заблокирована.") from exc
    return user


async def get_optional_active_user(
    user: OptionalCurrentUserDependency,
) -> User | None:
    if user is None:
        return None
    if not is_active_user(cast(Any, user)):
        raise forbidden_exception("Учётная запись неактивна или заблокирована.")
    return user


async def get_current_admin_user(user: CurrentUserDependency) -> User:
    try:
        require_admin(cast(Any, user))
    except PermissionDeniedError as exc:
        raise forbidden_exception("Требуются права администратора.") from exc
    return user


CurrentActiveUserDependency = Annotated[User, Depends(get_current_active_user)]
OptionalActiveUserDependency = Annotated[
    User | None,
    Depends(get_optional_active_user),
]
CurrentAdminUserDependency = Annotated[User, Depends(get_current_admin_user)]


def require_authenticated_user(user: CurrentUserDependency) -> User:
    return user


def require_active_authenticated_user(user: CurrentActiveUserDependency) -> User:
    return user


def require_admin_user(user: CurrentAdminUserDependency) -> User:
    return user


__all__ = [
    "get_user_by_id",
    "get_current_user",
    "get_optional_current_user",
    "get_current_user_from_refresh_token",
    "CurrentUserDependency",
    "OptionalCurrentUserDependency",
    "CurrentRefreshUserDependency",
    "get_current_active_user",
    "get_optional_active_user",
    "get_current_admin_user",
    "CurrentActiveUserDependency",
    "OptionalActiveUserDependency",
    "CurrentAdminUserDependency",
    "require_authenticated_user",
    "require_active_authenticated_user",
    "require_admin_user",
]
