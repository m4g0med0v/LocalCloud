from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from core.logging import get_logger
from database import (
    DatabaseError,
    EntityNotFoundError,
    UnitOfWorkFactory,
    create_unit_of_work_factory,
)
from database.models.enums import (
    NodeType,
    NodeVisibility,
    PermissionLevel,
    UserStatus,
)
from database.models.filesystem import FileSystemNode
from schemas.permissions import (
    EffectivePermissionRead,
    PermissionCheckRequest,
    PermissionCheckResponse,
)
from security.permissions import (
    PermissionAction,
    PermissionCheckResult,
    PermissionDeniedReason,
    SupportsNode,
    SupportsNodePermission,
    SupportsUser,
    check_node_permission,
    permission_level_allows_action,
)
from security.permissions.exceptions import PermissionCheckError, PermissionDeniedError
from services.exceptions import (
    NotFoundServiceError,
    PermissionServiceError,
    ServiceError,
    service_error_from_database,
    service_error_from_exception,
)

logger = get_logger("services.access")

SERVICE_NAME = "access"
REPOSITORY_PAGE_LIMIT = 1000


@dataclass(frozen=True, slots=True)
class AccessRole:
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class AccessUser:
    id: UUID
    status: UserStatus | str
    roles: tuple[AccessRole, ...]


@dataclass(frozen=True, slots=True)
class AccessNode:
    id: UUID
    owner_id: UUID
    node_type: NodeType | str
    visibility: NodeVisibility | str
    is_deleted: bool


@dataclass(frozen=True, slots=True)
class AccessPermission:
    id: UUID
    user_id: UUID
    permission_level: PermissionLevel | str
    can_read: bool
    can_download: bool
    can_write: bool
    can_delete: bool
    can_share: bool
    revoked_at: datetime | None
    expires_at: datetime | None

    def is_active_at(self, moment: datetime) -> bool:
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at <= moment:
            return False
        return True


class AccessService:
    """Single service entry point for checking access to filesystem nodes."""

    def __init__(self, *, uow_factory: UnitOfWorkFactory | None = None) -> None:
        self.uow_factory = uow_factory or create_unit_of_work_factory()

    async def check_node_access(
        self,
        request: PermissionCheckRequest,
        *,
        uow: Any | None = None,
    ) -> PermissionCheckResponse:
        """Check access using the public permissions DTO."""

        return await self.check_access(
            node_id=request.node_id,
            user_id=request.user_id,
            action=request.action,
            allow_deleted=request.allow_deleted,
            allow_public=request.allow_public,
            uow=uow,
        )

    async def check_access(
        self,
        *,
        node_id: UUID,
        user_id: UUID | None,
        action: PermissionAction | str,
        allow_deleted: bool = False,
        allow_public: bool = True,
        uow: Any | None = None,
    ) -> PermissionCheckResponse:
        """Return an allow/deny DTO without raising on denied access."""

        operation = "check_access"
        try:
            result = await self._check_access(
                node_id=node_id,
                user_id=user_id,
                action=action,
                allow_deleted=allow_deleted,
                allow_public=allow_public,
                uow=uow,
            )
            return _check_response(result)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Не удалось проверить доступ к узлу."
            ) from exc
        except PermissionCheckError as exc:
            raise self._permission_error(exc, operation=operation) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при проверке доступа к узлу.",
            ) from exc

    async def require_access(
        self,
        *,
        node_id: UUID,
        user_id: UUID | None,
        action: PermissionAction | str,
        allow_deleted: bool = False,
        allow_public: bool = True,
        uow: Any | None = None,
    ) -> PermissionCheckResponse:
        """Require access and raise PermissionServiceError when denied."""

        operation = "require_access"
        response = await self.check_access(
            node_id=node_id,
            user_id=user_id,
            action=action,
            allow_deleted=allow_deleted,
            allow_public=allow_public,
            uow=uow,
        )
        if response.allowed:
            return response
        raise self._denied_response_error(response, operation=operation)

    async def get_accessible_node(
        self,
        *,
        node_id: UUID,
        user_id: UUID | None,
        action: PermissionAction | str,
        allow_deleted: bool = False,
        allow_public: bool = True,
        uow: Any | None = None,
    ) -> FileSystemNode:
        """Return a node after access is granted.

        When `uow` is passed, the returned ORM object belongs to that same
        transaction and can be safely reused by the caller.
        """

        operation = "get_accessible_node"
        accessible_node: FileSystemNode | None = None
        try:
            if uow is not None:
                node = await self._load_node(uow, node_id, allow_deleted=allow_deleted)
                result = await self._check_loaded_access(
                    uow=uow,
                    node=node,
                    user_id=user_id,
                    action=action,
                    allow_deleted=allow_deleted,
                    allow_public=allow_public,
                )
                if result.denied:
                    raise self._denied_result_error(result, operation=operation)
                accessible_node = node

            else:
                async with self.uow_factory() as own_uow:
                    node = await self._load_node(
                        own_uow, node_id, allow_deleted=allow_deleted
                    )
                    result = await self._check_loaded_access(
                        uow=own_uow,
                        node=node,
                        user_id=user_id,
                        action=action,
                        allow_deleted=allow_deleted,
                        allow_public=allow_public,
                    )
                    if result.denied:
                        raise self._denied_result_error(result, operation=operation)
                    accessible_node = node

            if accessible_node is None:
                raise ServiceError(
                    "Сервис доступа не вернул узел файловой системы.",
                    service=SERVICE_NAME,
                    operation=operation,
                )
            return accessible_node

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить доступный узел файловой системы.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении доступного узла.",
            ) from exc

    async def get_effective_permissions(
        self,
        *,
        node_id: UUID,
        user_id: UUID | None,
        allow_deleted: bool = False,
        allow_public: bool = True,
        uow: Any | None = None,
    ) -> EffectivePermissionRead:
        """Build effective flags for a user on a node."""

        operation = "get_effective_permissions"
        try:
            result = await self._check_access(
                node_id=node_id,
                user_id=user_id,
                action=PermissionAction.READ,
                allow_deleted=allow_deleted,
                allow_public=allow_public,
                uow=uow,
            )
            return _effective_permission_read(result)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить эффективные права доступа.",
            ) from exc
        except PermissionCheckError as exc:
            raise self._permission_error(exc, operation=operation) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении эффективных прав.",
            ) from exc

    async def can_read_node(
        self, *, node_id: UUID, user_id: UUID | None, uow: Any | None = None
    ) -> bool:
        return await self._can(
            node_id=node_id, user_id=user_id, action=PermissionAction.READ, uow=uow
        )

    async def can_download_node(
        self, *, node_id: UUID, user_id: UUID | None, uow: Any | None = None
    ) -> bool:
        return await self._can(
            node_id=node_id, user_id=user_id, action=PermissionAction.DOWNLOAD, uow=uow
        )

    async def can_write_node(
        self, *, node_id: UUID, user_id: UUID | None, uow: Any | None = None
    ) -> bool:
        return await self._can(
            node_id=node_id, user_id=user_id, action=PermissionAction.WRITE, uow=uow
        )

    async def can_delete_node(
        self,
        *,
        node_id: UUID,
        user_id: UUID | None,
        allow_deleted: bool = False,
        uow: Any | None = None,
    ) -> bool:
        return await self._can(
            node_id=node_id,
            user_id=user_id,
            action=PermissionAction.DELETE,
            allow_deleted=allow_deleted,
            uow=uow,
        )

    async def can_share_node(
        self, *, node_id: UUID, user_id: UUID | None, uow: Any | None = None
    ) -> bool:
        return await self._can(
            node_id=node_id, user_id=user_id, action=PermissionAction.SHARE, uow=uow
        )

    async def can_manage_node(
        self, *, node_id: UUID, user_id: UUID | None, uow: Any | None = None
    ) -> bool:
        return await self._can(
            node_id=node_id, user_id=user_id, action=PermissionAction.MANAGE, uow=uow
        )

    async def require_read_node(
        self, *, node_id: UUID, user_id: UUID | None, uow: Any | None = None
    ) -> PermissionCheckResponse:
        return await self.require_access(
            node_id=node_id, user_id=user_id, action=PermissionAction.READ, uow=uow
        )

    async def require_download_node(
        self, *, node_id: UUID, user_id: UUID | None, uow: Any | None = None
    ) -> PermissionCheckResponse:
        return await self.require_access(
            node_id=node_id, user_id=user_id, action=PermissionAction.DOWNLOAD, uow=uow
        )

    async def require_write_node(
        self, *, node_id: UUID, user_id: UUID | None, uow: Any | None = None
    ) -> PermissionCheckResponse:
        return await self.require_access(
            node_id=node_id, user_id=user_id, action=PermissionAction.WRITE, uow=uow
        )

    async def require_delete_node(
        self,
        *,
        node_id: UUID,
        user_id: UUID | None,
        allow_deleted: bool = False,
        uow: Any | None = None,
    ) -> PermissionCheckResponse:
        return await self.require_access(
            node_id=node_id,
            user_id=user_id,
            action=PermissionAction.DELETE,
            allow_deleted=allow_deleted,
            uow=uow,
        )

    async def require_share_node(
        self, *, node_id: UUID, user_id: UUID | None, uow: Any | None = None
    ) -> PermissionCheckResponse:
        return await self.require_access(
            node_id=node_id, user_id=user_id, action=PermissionAction.SHARE, uow=uow
        )

    async def require_manage_node(
        self, *, node_id: UUID, user_id: UUID | None, uow: Any | None = None
    ) -> PermissionCheckResponse:
        return await self.require_access(
            node_id=node_id, user_id=user_id, action=PermissionAction.MANAGE, uow=uow
        )

    async def _can(
        self,
        *,
        node_id: UUID,
        user_id: UUID | None,
        action: PermissionAction,
        allow_deleted: bool = False,
        allow_public: bool = True,
        uow: Any | None = None,
    ) -> bool:
        response = await self.check_access(
            node_id=node_id,
            user_id=user_id,
            action=action,
            allow_deleted=allow_deleted,
            allow_public=allow_public,
            uow=uow,
        )
        return response.allowed

    async def _check_access(
        self,
        *,
        node_id: UUID,
        user_id: UUID | None,
        action: PermissionAction | str,
        allow_deleted: bool,
        allow_public: bool,
        uow: Any | None,
    ) -> PermissionCheckResult:
        result: PermissionCheckResult | None = None

        if uow is not None:
            node = await self._load_node(uow, node_id, allow_deleted=allow_deleted)
            result = await self._check_loaded_access(
                uow=uow,
                node=node,
                user_id=user_id,
                action=action,
                allow_deleted=allow_deleted,
                allow_public=allow_public,
            )
        else:
            async with self.uow_factory() as own_uow:
                node = await self._load_node(
                    own_uow, node_id, allow_deleted=allow_deleted
                )
                result = await self._check_loaded_access(
                    uow=own_uow,
                    node=node,
                    user_id=user_id,
                    action=action,
                    allow_deleted=allow_deleted,
                    allow_public=allow_public,
                )

        if result is None:
            raise ServiceError(
                "Сервис доступа не вернул результат проверки.",
                service=SERVICE_NAME,
                operation="check_access",
            )
        return result

    async def _check_loaded_access(
        self,
        *,
        uow: Any,
        node: FileSystemNode,
        user_id: UUID | None,
        action: PermissionAction | str,
        allow_deleted: bool,
        allow_public: bool,
    ) -> PermissionCheckResult:
        access_node = _node_snapshot(node)
        access_user = await self._load_access_user(uow, user_id)
        permissions = await self._load_node_permissions(uow, node.id)

        return check_node_permission(
            user=cast(SupportsUser | None, access_user),
            node=cast(SupportsNode, access_node),
            action=action,
            permissions=cast(Iterable[SupportsNodePermission], permissions),
            allow_deleted=allow_deleted,
            allow_public=allow_public,
        )

    async def _load_node(
        self, uow: Any, node_id: UUID, *, allow_deleted: bool
    ) -> FileSystemNode:
        if allow_deleted:
            return await uow.nodes.get_required_by_id(node_id)
        return await uow.nodes.get_required_active_node_by_id(node_id)

    async def _load_access_user(
        self, uow: Any, user_id: UUID | None
    ) -> AccessUser | None:
        if user_id is None:
            return None

        user = await uow.users.get_required_user_by_id(user_id)
        roles = await uow.roles.get_user_roles(
            user_id,
            only_active_roles=True,
            order_by_name=True,
        )
        return AccessUser(
            id=user.id,
            status=user.status,
            roles=tuple(
                AccessRole(code=str(role.code), name=str(role.name)) for role in roles
            ),
        )

    async def _load_node_permissions(
        self, uow: Any, node_id: UUID
    ) -> tuple[AccessPermission, ...]:
        permissions: list[AccessPermission] = []
        offset = 0
        while True:
            chunk = await uow.permissions.get_node_permissions(
                node_id=node_id,
                active_only=False,
                offset=offset,
                limit=REPOSITORY_PAGE_LIMIT,
            )
            permissions.extend(_permission_snapshot(permission) for permission in chunk)
            if len(chunk) < REPOSITORY_PAGE_LIMIT:
                break
            offset += REPOSITORY_PAGE_LIMIT
        return tuple(permissions)

    @staticmethod
    def _denied_response_error(
        response: PermissionCheckResponse, *, operation: str
    ) -> PermissionServiceError:
        return PermissionServiceError(
            response.message or "Недостаточно прав для доступа к узлу.",
            user_id=response.user_id,
            resource_type="filesystem_node",
            resource_id=response.node_id,
            action=response.action,
            required_permission=response.action,
            reason=response.denied_reason,
            details={"service": SERVICE_NAME, "operation": operation},
        )

    @staticmethod
    def _denied_result_error(
        result: PermissionCheckResult, *, operation: str
    ) -> PermissionServiceError:
        return PermissionServiceError(
            _message_for_denied_reason(result.reason),
            user_id=result.user_id,
            resource_type="filesystem_node",
            resource_id=result.node_id,
            action=result.action,
            required_permission=result.action,
            reason=result.reason,
            details={"service": SERVICE_NAME, "operation": operation},
        )

    @staticmethod
    def _permission_error(
        exc: PermissionCheckError, *, operation: str
    ) -> PermissionServiceError:
        return PermissionServiceError(
            str(exc),
            details={"service": SERVICE_NAME, "operation": operation, **exc.to_dict()},
            cause=exc,
        )

    @staticmethod
    def _database_error(
        exc: DatabaseError, *, operation: str, message: str
    ) -> ServiceError:
        if isinstance(exc, EntityNotFoundError):
            return NotFoundServiceError(
                message,
                entity_name="FileSystemNode",
                details={"service": SERVICE_NAME, "operation": operation},
                cause=exc,
            )
        return service_error_from_database(
            exc, operation=operation, message=message, service=SERVICE_NAME
        )

    @staticmethod
    def _unexpected_error(
        exc: Exception, *, operation: str, message: str
    ) -> ServiceError:
        logger.exception(
            message,
            extra={"operation": operation, "error_type": exc.__class__.__name__},
        )
        return service_error_from_exception(
            exc, operation=operation, message=message, service=SERVICE_NAME
        )


def _node_snapshot(node: FileSystemNode) -> AccessNode:
    return AccessNode(
        id=node.id,
        owner_id=node.owner_id,
        node_type=node.node_type,
        visibility=node.visibility,
        is_deleted=bool(node.is_deleted),
    )


def _permission_snapshot(permission: Any) -> AccessPermission:
    return AccessPermission(
        id=permission.id,
        user_id=permission.user_id,
        permission_level=permission.permission_level,
        can_read=bool(permission.can_read),
        can_download=bool(permission.can_download),
        can_write=bool(permission.can_write),
        can_delete=bool(permission.can_delete),
        can_share=bool(permission.can_share),
        revoked_at=permission.revoked_at,
        expires_at=permission.expires_at,
    )


def _check_response(result: PermissionCheckResult) -> PermissionCheckResponse:
    return PermissionCheckResponse(
        allowed=result.allowed,
        node_id=_require_node_id(result),
        user_id=result.user_id,
        action=result.action,
        permission_level=result.permission_level,
        denied_reason=result.reason,
        message=None if result.allowed else _message_for_denied_reason(result.reason),
    )


def _effective_permission_read(
    result: PermissionCheckResult,
) -> EffectivePermissionRead:
    can_read = _allows(result, PermissionAction.READ)
    can_download = _allows(result, PermissionAction.DOWNLOAD)
    can_write = _allows(result, PermissionAction.WRITE)
    can_delete = _allows(result, PermissionAction.DELETE)
    can_share = _allows(result, PermissionAction.SHARE)

    return EffectivePermissionRead(
        node_id=_require_node_id(result),
        user_id=result.user_id,
        permission_level=result.permission_level,
        source_permission_id=None,
        is_owner=result.is_owner,
        is_admin=result.is_admin,
        is_public=bool(
            result.details and result.details.get("source") == "public_node"
        ),
        expires_at=None,
        can_read=can_read,
        can_download=can_download,
        can_write=can_write,
        can_delete=can_delete,
        can_share=can_share,
    )


def _allows(result: PermissionCheckResult, action: PermissionAction) -> bool:
    if result.denied:
        return False
    if result.is_admin or result.is_owner:
        return True
    if result.details and result.details.get("source") == "public_node":
        return action in {PermissionAction.READ, PermissionAction.DOWNLOAD}
    if result.permission_level is None:
        return result.allowed and action == result.action
    return permission_level_allows_action(result.permission_level, action)


def _require_node_id(result: PermissionCheckResult) -> UUID:
    if result.node_id is None:
        raise PermissionDeniedError(
            "Результат проверки доступа не содержит идентификатор узла.",
            action=result.action,
            reason=result.reason,
            user_id=result.user_id,
        )
    return result.node_id


def _message_for_denied_reason(reason: PermissionDeniedReason | None) -> str:
    default_message = "Недостаточно прав для доступа к узлу."
    messages = {
        PermissionDeniedReason.ANONYMOUS_USER: "Требуется авторизация для доступа к узлу.",
        PermissionDeniedReason.INACTIVE_USER: "Учетная запись неактивна или заблокирована.",
        PermissionDeniedReason.DELETED_NODE: "Узел файловой системы удален.",
        PermissionDeniedReason.NOT_OWNER: "Операция доступна только владельцу узла.",
        PermissionDeniedReason.NOT_ADMIN: "Операция доступна только администратору.",
        PermissionDeniedReason.PERMISSION_NOT_FOUND: "Разрешение на доступ к узлу не найдено.",
        PermissionDeniedReason.PERMISSION_REVOKED: "Разрешение на доступ к узлу отозвано.",
        PermissionDeniedReason.PERMISSION_EXPIRED: "Срок действия разрешения истек.",
        PermissionDeniedReason.INSUFFICIENT_PERMISSION: "Недостаточно прав для доступа к узлу.",
        PermissionDeniedReason.PRIVATE_NODE: "Узел закрыт для публичного доступа.",
        PermissionDeniedReason.INVALID_ACTION: "Действие доступа не поддерживается.",
    }
    if reason is None:
        return default_message
    return messages.get(reason, default_message)


def get_access_service(
    *, uow_factory: UnitOfWorkFactory | None = None
) -> AccessService:
    return AccessService(uow_factory=uow_factory)


__all__ = [
    "AccessRole",
    "AccessUser",
    "AccessNode",
    "AccessPermission",
    "AccessService",
    "get_access_service",
]
