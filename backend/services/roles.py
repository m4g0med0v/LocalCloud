from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any
from uuid import UUID

from core.logging import get_logger
from database import DatabaseError, UnitOfWorkFactory, create_unit_of_work_factory
from database.models.enums import AuditAction, AuditResourceType, SystemRole
from database.models.roles import Role, UserRole
from schemas.common import PageMeta, PageResponse
from schemas.roles import (
    RoleAssignRequest,
    RoleCreate,
    RoleListItem,
    RoleRead,
    RoleRemoveRequest,
    RoleUpdate,
    UserRoleRead,
)
from services.audit import AuditService, get_audit_service
from services.exceptions import (
    ConflictServiceError,
    ServiceError,
    ValidationServiceError,
    service_error_from_database,
    service_error_from_exception,
)

logger = get_logger("services.roles")

SERVICE_NAME = "roles"
MAX_PAGE_LIMIT = 1000
REPOSITORY_PAGE_LIMIT = 1000


class RolesService:
    """Business service for LocalCloud roles and user role assignments."""

    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.uow_factory = uow_factory or create_unit_of_work_factory()
        self.audit_service = audit_service or get_audit_service(
            uow_factory=self.uow_factory,
        )

    async def ensure_system_roles(self) -> list[RoleRead]:
        """Create required system roles when they are missing."""

        operation = "ensure_system_roles"
        snapshots: list[dict[str, Any]] = []
        try:
            async with self.uow_factory() as uow:
                roles = await uow.roles.ensure_system_roles(flush=True)
                snapshots = [_role_snapshot(role) for role in roles]
                await uow.commit()

            await self._safe_log_system_event(
                action=AuditAction.USER_UPDATED,
                message="System roles were checked and created if necessary.",
                metadata={
                    "operation": operation,
                    "role_codes": [role["code"] for role in snapshots],
                },
            )

            return [_role_read(snapshot) for snapshot in snapshots]

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось инициализировать системные роли.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при инициализации системных ролей.",
            ) from exc

    async def create_role(
        self,
        data: RoleCreate,
        actor_id: UUID | None = None,
    ) -> RoleRead:
        """Create a new role."""

        operation = "create_role"
        snapshot: dict[str, Any] = {}
        try:
            async with self.uow_factory() as uow:
                role = await uow.roles.create_role(
                    name=data.name,
                    code=data.code,
                    display_name=data.display_name,
                    description=data.description,
                    is_system=data.is_system,
                    is_active=data.is_active,
                    flush=True,
                    refresh=True,
                    check_duplicate=True,
                )
                snapshot = _role_snapshot(role)
                await uow.commit()

            await self._safe_log_user_or_system_event(
                actor_id=actor_id,
                action=AuditAction.USER_UPDATED,
                entity_id=snapshot["id"],
                message="Role was created.",
                metadata={
                    "operation": operation,
                    "role": _audit_role(snapshot),
                },
            )

            return _role_read(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось создать роль.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при создании роли.",
            ) from exc

    async def update_role(
        self,
        role_id: UUID,
        data: RoleUpdate,
        actor_id: UUID | None = None,
    ) -> RoleRead:
        """Update an existing role."""

        operation = "update_role"
        values = data.model_dump(exclude_unset=True)
        if not values:
            return await self.get_role(role_id)

        try:
            snapshot: dict[str, Any] = {}
            async with self.uow_factory() as uow:
                role = await uow.roles.get_required_role_by_id(role_id)

                if "name" in values:
                    await self._ensure_role_name_is_unique(
                        uow=uow,
                        name=values["name"],
                        exclude_role_id=role_id,
                    )
                if "code" in values:
                    await self._ensure_role_code_is_unique(
                        uow=uow,
                        code=values["code"],
                        exclude_role_id=role_id,
                    )

                updated_role = await uow.roles.update_role(
                    role,
                    values,
                    flush=True,
                    refresh=True,
                    exclude_none=False,
                )
                snapshot = _role_snapshot(updated_role)
                await uow.commit()

            await self._safe_log_user_or_system_event(
                actor_id=actor_id,
                action=AuditAction.USER_UPDATED,
                entity_id=role_id,
                message="Role was updated.",
                metadata={
                    "operation": operation,
                    "role": _audit_role(snapshot),
                    "updated_fields": sorted(values),
                },
            )

            return _role_read(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось обновить роль.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при обновлении роли.",
            ) from exc

    async def get_role(self, role_id: UUID) -> RoleRead:
        """Return a role by id."""

        operation = "get_role"
        role_read: RoleRead | None = None
        try:
            async with self.uow_factory() as uow:
                role = await uow.roles.get_required_role_by_id(role_id)
                snapshot = _role_snapshot(role)
                role_read = _role_read(snapshot)

            if role_read is None:
                raise ServiceError(
                    "Не удалось получить роль.",
                    service=SERVICE_NAME,
                    operation=operation,
                )
            return role_read

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Роль не найдена.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении роли.",
            ) from exc

    async def get_role_by_name(self, name: str) -> RoleRead:
        """Return a role by technical name."""

        operation = "get_role_by_name"
        role_read: RoleRead | None = None
        try:
            async with self.uow_factory() as uow:
                role = await uow.roles.get_required_role_by_name(name)
                snapshot = _role_snapshot(role)
                role_read = _role_read(snapshot)

            if role_read is None:
                raise ServiceError(
                    "Не удалось получить роль по имени.",
                    service=SERVICE_NAME,
                    operation=operation,
                )
            return role_read

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Роль с указанным именем не найдена.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении роли по имени.",
            ) from exc

    async def get_role_by_code(self, code: str | SystemRole) -> RoleRead:
        """Return a role by stable code."""

        operation = "get_role_by_code"
        role_read: RoleRead | None = None
        try:
            async with self.uow_factory() as uow:
                role = await uow.roles.get_required_role_by_code(code)
                snapshot = _role_snapshot(role)
                role_read = _role_read(snapshot)

            if role_read is None:
                raise ServiceError(
                    "Не удалось получить роль по коду.",
                    service=SERVICE_NAME,
                    operation=operation,
                )
            return role_read

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Роль с указанным кодом не найдена.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении роли по коду.",
            ) from exc

    async def get_admin_role(self) -> RoleRead:
        """Return the system administrator role."""

        return await self.get_role_by_code(SystemRole.ADMIN)

    async def get_default_user_role(self) -> RoleRead:
        """Return the default system user role."""

        return await self.get_role_by_code(SystemRole.USER)

    async def list_roles(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        only_active: bool | None = None,
        only_system: bool | None = None,
        search: str | None = None,
        order_by_name: bool = True,
    ) -> PageResponse[RoleListItem]:
        """Return roles with filtering and API pagination metadata."""

        operation = "list_roles"
        self._validate_pagination(offset=offset, limit=limit)
        snapshots: list[dict[str, Any]] = []

        try:
            async with self.uow_factory() as uow:
                snapshots = await self._collect_role_snapshots(
                    uow=uow,
                    only_active=only_active,
                    only_system=only_system,
                    search=search,
                    order_by_name=order_by_name,
                )

            total = len(snapshots)
            page_items = snapshots[offset : offset + limit]

            return PageResponse[RoleListItem](
                items=[_role_list_item(snapshot) for snapshot in page_items],
                meta=PageMeta(
                    limit=limit,
                    offset=offset,
                    total=total,
                    count=len(page_items),
                ),
            )

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить список ролей.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении списка ролей.",
            ) from exc

    async def activate_role(
        self,
        role_id: UUID,
        actor_id: UUID | None = None,
    ) -> RoleRead:
        """Activate a role."""

        operation = "activate_role"
        snapshot: dict[str, Any] = {}
        try:
            async with self.uow_factory() as uow:
                role = await uow.roles.activate_role(role_id, flush=True)
                snapshot = _role_snapshot(role)
                await uow.commit()

            await self._safe_log_user_or_system_event(
                actor_id=actor_id,
                action=AuditAction.USER_UPDATED,
                entity_id=role_id,
                message="Role was activated.",
                metadata={"operation": operation, "role": _audit_role(snapshot)},
            )

            return _role_read(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось активировать роль.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при активации роли.",
            ) from exc

    async def deactivate_role(
        self,
        role_id: UUID,
        actor_id: UUID | None = None,
    ) -> RoleRead:
        """Deactivate a non-system role."""

        operation = "deactivate_role"
        snapshot: dict[str, Any] = {}
        try:
            async with self.uow_factory() as uow:
                role = await uow.roles.deactivate_role(
                    role_id,
                    flush=True,
                    forbid_system_role=True,
                )
                snapshot = _role_snapshot(role)
                await uow.commit()

            await self._safe_log_user_or_system_event(
                actor_id=actor_id,
                action=AuditAction.USER_UPDATED,
                entity_id=role_id,
                message="Role was deactivated.",
                metadata={"operation": operation, "role": _audit_role(snapshot)},
            )

            return _role_read(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось деактивировать роль.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при деактивации роли.",
            ) from exc

    async def role_exists(
        self,
        *,
        name: str | None = None,
        code: str | SystemRole | None = None,
        exclude_role_id: UUID | None = None,
    ) -> bool:
        """Check whether a role exists by name or code."""

        operation = "role_exists"
        result = False
        try:
            async with self.uow_factory() as uow:
                result = await uow.roles.role_exists(
                    name=name,
                    code=code,
                    exclude_role_id=exclude_role_id,
                )
            return result

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось проверить существование роли.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при проверке существования роли.",
            ) from exc

    async def assign_role(
        self,
        data: RoleAssignRequest,
        actor_id: UUID | None = None,
    ) -> UserRoleRead:
        """Assign a role to a user."""

        operation = "assign_role"
        assigned_by = actor_id or data.assigned_by
        role_snapshot: dict[str, Any] = {}
        assignment_snapshot: dict[str, Any] = {}

        try:
            async with self.uow_factory() as uow:
                role = await self._resolve_role(
                    uow=uow,
                    role_id=data.role_id,
                    role_code=data.role_code,
                    operation=operation,
                )

                if not role.is_active:
                    raise ConflictServiceError(
                        "Нельзя назначить неактивную роль.",
                        entity_name="Role",
                        entity_id=role.id,
                        reason="role_is_inactive",
                        details={
                            "service": SERVICE_NAME,
                            "operation": operation,
                            "role_code": role.code,
                            "user_id": str(data.user_id),
                        },
                    )

                assignment = await uow.roles.assign_role(
                    user_id=data.user_id,
                    role_id=role.id,
                    assigned_by=assigned_by,
                    flush=True,
                    refresh=True,
                    check_user_exists=True,
                    check_role_exists=False,
                    ignore_existing=True,
                )
                role_snapshot = _role_snapshot(role)
                assignment_snapshot = _assignment_snapshot(
                    assignment,
                    role_snapshot=role_snapshot,
                )
                await uow.commit()

            await self._safe_log_user_or_system_event(
                actor_id=assigned_by,
                action=AuditAction.USER_ROLE_ASSIGNED,
                entity_id=data.user_id,
                resource_type=AuditResourceType.USER,
                message="Role was assigned to user.",
                metadata={
                    "operation": operation,
                    "user_id": str(data.user_id),
                    "role": _audit_role(role_snapshot),
                    "assigned_by": str(assigned_by) if assigned_by else None,
                },
            )

            return _user_role_read(assignment_snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось назначить роль пользователю.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при назначении роли пользователю.",
            ) from exc

    async def remove_role(
        self,
        data: RoleRemoveRequest,
        actor_id: UUID | None = None,
    ) -> bool:
        """Remove a role assignment from a user."""

        operation = "remove_role"
        role_snapshot: dict[str, Any] = {}
        removed = False
        try:
            async with self.uow_factory() as uow:
                role = await self._resolve_role(
                    uow=uow,
                    role_id=data.role_id,
                    role_code=data.role_code,
                    operation=operation,
                )
                role_snapshot = _role_snapshot(role)
                removed = await uow.roles.remove_role(
                    user_id=data.user_id,
                    role_id=role.id,
                    flush=True,
                    required=False,
                )
                await uow.commit()

            if removed:
                await self._safe_log_user_or_system_event(
                    actor_id=actor_id,
                    action=AuditAction.USER_ROLE_REMOVED,
                    entity_id=data.user_id,
                    resource_type=AuditResourceType.USER,
                    message="Role was removed from user.",
                    metadata={
                        "operation": operation,
                        "user_id": str(data.user_id),
                        "role": _audit_role(role_snapshot),
                    },
                )

            return removed

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось снять роль с пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при снятии роли с пользователя.",
            ) from exc

    async def replace_user_roles(
        self,
        *,
        user_id: UUID,
        role_codes: Sequence[str | SystemRole],
        actor_id: UUID | None = None,
    ) -> list[UserRoleRead]:
        """Replace all user roles by role codes."""

        operation = "replace_user_roles"
        if not role_codes:
            raise ValidationServiceError(
                "Список ролей не должен быть пустым.",
                field="role_codes",
                reason="empty_role_codes",
                details={"service": SERVICE_NAME, "operation": operation},
            )

        snapshots: list[dict[str, Any]] = []
        try:
            async with self.uow_factory() as uow:
                assignments = await uow.roles.replace_user_roles_by_codes(
                    user_id=user_id,
                    role_codes=role_codes,
                    assigned_by=actor_id,
                    flush=True,
                    check_user_exists=True,
                )
                roles = await uow.roles.get_user_roles(
                    user_id,
                    only_active_roles=False,
                    order_by_name=True,
                )
                role_by_id = {role.id: _role_snapshot(role) for role in roles}
                snapshots = [
                    _assignment_snapshot(
                        assignment,
                        role_snapshot=role_by_id.get(assignment.role_id),
                    )
                    for assignment in assignments
                ]
                await uow.commit()

            await self._safe_log_user_or_system_event(
                actor_id=actor_id,
                action=AuditAction.USER_ROLE_ASSIGNED,
                entity_id=user_id,
                resource_type=AuditResourceType.USER,
                message="User roles were replaced.",
                metadata={
                    "operation": operation,
                    "user_id": str(user_id),
                    "role_codes": [_normalize_role_code(code) for code in role_codes],
                    "assigned_count": len(snapshots),
                },
            )

            return [_user_role_read(snapshot) for snapshot in snapshots]

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось заменить роли пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при замене ролей пользователя.",
            ) from exc

    async def clear_user_roles(
        self,
        user_id: UUID,
        *,
        actor_id: UUID | None = None,
    ) -> int:
        """Remove all role assignments from a user."""

        operation = "clear_user_roles"
        removed_count = 0
        try:
            async with self.uow_factory() as uow:
                removed_count = await uow.roles.clear_user_roles(
                    user_id=user_id,
                    flush=True,
                )
                await uow.commit()

            if removed_count:
                await self._safe_log_user_or_system_event(
                    actor_id=actor_id,
                    action=AuditAction.USER_ROLE_REMOVED,
                    entity_id=user_id,
                    resource_type=AuditResourceType.USER,
                    message="All roles were removed from user.",
                    metadata={
                        "operation": operation,
                        "user_id": str(user_id),
                        "removed_count": removed_count,
                    },
                )

            return removed_count

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось очистить роли пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при очистке ролей пользователя.",
            ) from exc

    async def user_has_role(
        self,
        user_id: UUID,
        role_code: str | SystemRole,
    ) -> bool:
        """Check whether a user has an active role with the given code."""

        operation = "user_has_role"
        result = False
        try:
            async with self.uow_factory() as uow:
                result = await uow.roles.user_has_role(
                    user_id=user_id,
                    role_code=role_code,
                    only_active_roles=True,
                )
            return result

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось проверить роль пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при проверке роли пользователя.",
            ) from exc

    async def get_user_roles(
        self,
        user_id: UUID,
        *,
        only_active_roles: bool = True,
    ) -> list[RoleListItem]:
        """Return user roles."""

        operation = "get_user_roles"
        role_items: list[RoleListItem] | None = None
        try:
            async with self.uow_factory() as uow:
                roles = await uow.roles.get_user_roles(
                    user_id,
                    only_active_roles=only_active_roles,
                    order_by_name=True,
                )
                snapshots = [_role_snapshot(role) for role in roles]
                role_items = [_role_list_item(snapshot) for snapshot in snapshots]

            if role_items is None:
                raise ServiceError(
                    "Не удалось получить роли пользователя.",
                    service=SERVICE_NAME,
                    operation=operation,
                )
            return role_items

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить роли пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении ролей пользователя.",
            ) from exc

    async def get_user_role_codes(
        self,
        user_id: UUID,
        *,
        only_active_roles: bool = True,
    ) -> list[str]:
        """Return user role codes."""

        operation = "get_user_role_codes"
        role_codes: list[str] = []
        try:
            async with self.uow_factory() as uow:
                role_codes = await uow.roles.get_user_role_codes(
                    user_id,
                    only_active_roles=only_active_roles,
                    order_by_code=True,
                )
            return role_codes

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить коды ролей пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении кодов ролей пользователя.",
            ) from exc

    async def get_user_role_assignments(self, user_id: UUID) -> list[UserRoleRead]:
        """Return user role assignment records."""

        operation = "get_user_role_assignments"
        assignment_items: list[UserRoleRead] | None = None
        try:
            async with self.uow_factory() as uow:
                assignments = await uow.roles.get_user_role_assignments(
                    user_id,
                    order_by_assigned_at=True,
                )
                roles = await uow.roles.get_user_roles(
                    user_id,
                    only_active_roles=False,
                    order_by_name=True,
                )
                role_by_id = {role.id: _role_snapshot(role) for role in roles}
                snapshots = [
                    _assignment_snapshot(
                        assignment,
                        role_snapshot=role_by_id.get(assignment.role_id),
                    )
                    for assignment in assignments
                ]
                assignment_items = [_user_role_read(snapshot) for snapshot in snapshots]

            if assignment_items is None:
                raise ServiceError(
                    "Не удалось получить назначения ролей пользователя.",
                    service=SERVICE_NAME,
                    operation=operation,
                )
            return assignment_items

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить назначения ролей пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении назначений ролей пользователя.",
            ) from exc

    async def _collect_role_snapshots(
        self,
        *,
        uow: Any,
        only_active: bool | None,
        only_system: bool | None,
        search: str | None,
        order_by_name: bool,
    ) -> list[dict[str, Any]]:
        snapshots: list[dict[str, Any]] = []
        offset = 0

        while True:
            roles = await uow.roles.list_roles(
                offset=offset,
                limit=REPOSITORY_PAGE_LIMIT,
                only_active=only_active,
                only_system=only_system,
                search=search,
                order_by_name=order_by_name,
            )
            snapshots.extend(_role_snapshot(role) for role in roles)

            if len(roles) < REPOSITORY_PAGE_LIMIT:
                break
            offset += REPOSITORY_PAGE_LIMIT

        return snapshots

    async def _resolve_role(
        self,
        *,
        uow: Any,
        role_id: UUID | None,
        role_code: str | SystemRole | None,
        operation: str,
    ) -> Role:
        if role_id is not None:
            return await uow.roles.get_required_role_by_id(role_id)
        if role_code is not None:
            return await uow.roles.get_required_role_by_code(role_code)

        raise ValidationServiceError(
            "Нужно передать role_id или role_code.",
            field="role_id|role_code",
            reason="missing_role_identifier",
            details={"service": SERVICE_NAME, "operation": operation},
        )

    async def _ensure_role_name_is_unique(
        self,
        *,
        uow: Any,
        name: str,
        exclude_role_id: UUID,
    ) -> None:
        if await uow.roles.role_exists(name=name, exclude_role_id=exclude_role_id):
            raise ConflictServiceError(
                "Роль с таким name уже существует.",
                entity_name="Role",
                field="name",
                value=name,
                reason="duplicate_role_name",
                details={"service": SERVICE_NAME, "operation": "update_role"},
            )

    async def _ensure_role_code_is_unique(
        self,
        *,
        uow: Any,
        code: str | SystemRole,
        exclude_role_id: UUID,
    ) -> None:
        if await uow.roles.role_exists(code=code, exclude_role_id=exclude_role_id):
            raise ConflictServiceError(
                "Роль с таким code уже существует.",
                entity_name="Role",
                field="code",
                value=_normalize_role_code(code),
                reason="duplicate_role_code",
                details={"service": SERVICE_NAME, "operation": "update_role"},
            )

    async def _safe_log_user_or_system_event(
        self,
        *,
        actor_id: UUID | None,
        action: AuditAction,
        entity_id: UUID | None,
        message: str,
        metadata: Mapping[str, Any] | None = None,
        resource_type: AuditResourceType = AuditResourceType.ROLE,
    ) -> None:
        try:
            if actor_id is None:
                await self.audit_service.log_system_event(
                    action=action,
                    entity_type=resource_type.value,
                    entity_id=entity_id,
                    resource_type=resource_type,
                    message=message,
                    metadata=metadata,
                )
                return

            await self.audit_service.log_user_event(
                user_id=actor_id,
                action=action,
                entity_type=resource_type.value,
                entity_id=entity_id,
                resource_type=resource_type,
                message=message,
                metadata=metadata,
            )
        except Exception as exc:
            logger.warning(
                "Failed to write audit event for roles service.",
                extra={
                    "action": action.value,
                    "entity_id": str(entity_id) if entity_id else None,
                    "actor_id": str(actor_id) if actor_id else None,
                    "error_type": exc.__class__.__name__,
                    "reason": str(exc),
                },
            )

    async def _safe_log_system_event(
        self,
        *,
        action: AuditAction,
        message: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        try:
            await self.audit_service.log_system_event(
                action=action,
                entity_type=AuditResourceType.ROLE.value,
                resource_type=AuditResourceType.ROLE,
                message=message,
                metadata=metadata,
            )
        except Exception as exc:
            logger.warning(
                "Failed to write system audit event for roles service.",
                extra={
                    "action": action.value,
                    "error_type": exc.__class__.__name__,
                    "reason": str(exc),
                },
            )

    @staticmethod
    def _validate_pagination(*, offset: int, limit: int) -> None:
        if offset < 0:
            raise ValidationServiceError(
                "offset не может быть отрицательным.",
                field="offset",
                value=offset,
                reason="negative_offset",
                details={"service": SERVICE_NAME, "operation": "validate_pagination"},
            )
        if limit < 1:
            raise ValidationServiceError(
                "limit должен быть больше нуля.",
                field="limit",
                value=limit,
                reason="invalid_limit",
                details={"service": SERVICE_NAME, "operation": "validate_pagination"},
            )
        if limit > MAX_PAGE_LIMIT:
            raise ValidationServiceError(
                f"limit не должен превышать {MAX_PAGE_LIMIT}.",
                field="limit",
                value=limit,
                reason="limit_too_large",
                details={
                    "service": SERVICE_NAME,
                    "operation": "validate_pagination",
                    "max_limit": MAX_PAGE_LIMIT,
                },
            )

    @staticmethod
    def _database_error(
        exc: DatabaseError,
        *,
        operation: str,
        message: str,
    ) -> ServiceError:
        return service_error_from_database(
            exc,
            operation=operation,
            message=message,
            service=SERVICE_NAME,
        )

    @staticmethod
    def _unexpected_error(
        exc: Exception,
        *,
        operation: str,
        message: str,
    ) -> ServiceError:
        logger.exception(
            message,
            extra={
                "operation": operation,
                "error_type": exc.__class__.__name__,
            },
        )
        return service_error_from_exception(
            exc,
            operation=operation,
            message=message,
            service=SERVICE_NAME,
        )


def _role_snapshot(role: Role) -> dict[str, Any]:
    return {
        "id": role.id,
        "name": role.name,
        "code": role.code,
        "display_name": role.display_name,
        "description": role.description,
        "is_system": role.is_system,
        "is_active": role.is_active,
        "created_at": role.created_at,
    }


def _assignment_snapshot(
    assignment: UserRole,
    *,
    role_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    role_payload: Mapping[str, Any] | None = role_snapshot
    if role_payload is None:
        loaded_role = getattr(assignment, "role", None)
        if loaded_role is not None:
            role_payload = _role_snapshot(loaded_role)

    return {
        "user_id": assignment.user_id,
        "role_id": assignment.role_id,
        "assigned_at": assignment.assigned_at,
        "assigned_by": assignment.assigned_by,
        "role": _role_list_payload(role_payload) if role_payload else None,
    }


def _role_read(snapshot: Mapping[str, Any]) -> RoleRead:
    return RoleRead.model_validate(dict(snapshot))


def _role_list_item(snapshot: Mapping[str, Any]) -> RoleListItem:
    return RoleListItem.model_validate(_role_list_payload(snapshot))


def _user_role_read(snapshot: Mapping[str, Any]) -> UserRoleRead:
    return UserRoleRead.model_validate(dict(snapshot))


def _role_list_payload(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": snapshot["id"],
        "name": snapshot["name"],
        "code": snapshot["code"],
        "display_name": snapshot["display_name"],
        "is_system": snapshot["is_system"],
        "is_active": snapshot["is_active"],
    }


def _audit_role(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(snapshot["id"]),
        "name": snapshot["name"],
        "code": snapshot["code"],
        "is_system": snapshot["is_system"],
        "is_active": snapshot["is_active"],
    }


def _normalize_role_code(code: str | SystemRole) -> str:
    value = code.value if isinstance(code, Enum) else code
    return str(value).strip().lower()


def get_roles_service(
    *,
    uow_factory: UnitOfWorkFactory | None = None,
    audit_service: AuditService | None = None,
) -> RolesService:
    return RolesService(
        uow_factory=uow_factory,
        audit_service=audit_service,
    )


__all__ = [
    "RolesService",
    "get_roles_service",
]
