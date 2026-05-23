from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated, Any, cast

from fastapi import Depends, Path
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.logging import get_logger
from database.models.filesystem import FileSystemNode
from database.models.permissions import NodePermission
from security.dependencies.auth import DatabaseSessionDependency, forbidden_exception
from security.dependencies.users import OptionalActiveUserDependency
from security.permissions import PermissionAction, check_node_permission


logger = get_logger(__name__)


async def get_node_by_id(
    session: AsyncSession,
    node_id: uuid.UUID,
    *,
    load_permissions: bool = True,
) -> FileSystemNode | None:
    statement = select(FileSystemNode).where(FileSystemNode.id == node_id)
    if load_permissions:
        statement = statement.options(selectinload(FileSystemNode.permissions))
    try:
        result = await session.execute(statement)
        return result.scalar_one_or_none()
    except SQLAlchemyError as exc:
        logger.warning(
            "Failed to load filesystem node by id",
            extra={
                "node_id": str(node_id),
                "reason": str(exc),
                "error_type": exc.__class__.__name__,
            },
        )
        raise forbidden_exception("Не удалось проверить доступ к объекту.") from exc


async def get_node_permissions(
    session: AsyncSession,
    node_id: uuid.UUID,
) -> list[NodePermission]:
    statement = select(NodePermission).where(NodePermission.node_id == node_id)
    try:
        result = await session.execute(statement)
        return list(result.scalars().all())
    except SQLAlchemyError as exc:
        logger.warning(
            "Failed to load node permissions",
            extra={
                "node_id": str(node_id),
                "reason": str(exc),
                "error_type": exc.__class__.__name__,
            },
        )
        raise forbidden_exception("Не удалось проверить права доступа.") from exc


def require_node_permission_dependency(
    action: PermissionAction | str,
    *,
    allow_deleted: bool = False,
    allow_public: bool = True,
) -> Callable[..., Any]:
    async def dependency(
        node_id: Annotated[uuid.UUID, Path()],
        user: OptionalActiveUserDependency,
        session: DatabaseSessionDependency,
    ) -> None:
        node = await get_node_by_id(cast(AsyncSession, session), node_id)
        if node is None:
            raise forbidden_exception("Объект файловой системы не найден.")
        result = check_node_permission(
            user=cast(Any, user),
            node=cast(Any, node),
            action=action,
            permissions=cast(Any, node.permissions),
            allow_deleted=allow_deleted,
            allow_public=allow_public,
        )
        if result.denied:
            raise forbidden_exception("Недостаточно прав для доступа к объекту.")

    return dependency


def get_accessible_node_dependency(
    action: PermissionAction | str,
    *,
    allow_deleted: bool = False,
    allow_public: bool = True,
) -> Callable[..., Any]:
    async def dependency(
        node_id: Annotated[uuid.UUID, Path()],
        user: OptionalActiveUserDependency,
        session: DatabaseSessionDependency,
    ) -> FileSystemNode:
        node = await get_node_by_id(cast(AsyncSession, session), node_id)
        if node is None:
            raise forbidden_exception("Объект файловой системы не найден.")
        result = check_node_permission(
            user=cast(Any, user),
            node=cast(Any, node),
            action=action,
            permissions=cast(Any, node.permissions),
            allow_deleted=allow_deleted,
            allow_public=allow_public,
        )
        if result.denied:
            raise forbidden_exception("Недостаточно прав для доступа к объекту.")
        return node

    return dependency


RequireReadNodeDependency = Depends(
    require_node_permission_dependency(PermissionAction.READ)
)
RequireDownloadNodeDependency = Depends(
    require_node_permission_dependency(PermissionAction.DOWNLOAD)
)
RequireWriteNodeDependency = Depends(
    require_node_permission_dependency(PermissionAction.WRITE)
)
RequireDeleteNodeDependency = Depends(
    require_node_permission_dependency(PermissionAction.DELETE)
)
RequireShareNodeDependency = Depends(
    require_node_permission_dependency(PermissionAction.SHARE)
)


__all__ = [
    "get_node_by_id",
    "get_node_permissions",
    "require_node_permission_dependency",
    "get_accessible_node_dependency",
    "RequireReadNodeDependency",
    "RequireDownloadNodeDependency",
    "RequireWriteNodeDependency",
    "RequireDeleteNodeDependency",
    "RequireShareNodeDependency",
]
