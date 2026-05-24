"""Сервис управления ролями LocalCloud.

Модуль содержит бизнес-логику для работы с ролями, системными ролями и
назначениями ролей пользователям. Сервис не зависит от FastAPI напрямую:
все операции с хранилищем выполняются через UnitOfWork и репозиторий ролей,
а наружу возвращаются DTO из `schemas.roles`.

Сервис также записывает события аудита для операций создания, обновления,
активации, деактивации, назначения и снятия ролей.
"""

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
    """Бизнес-сервис для ролей LocalCloud и назначений ролей пользователям.

    Сервис инкапсулирует операции создания, обновления, получения,
    активации, деактивации и назначения ролей. Все обращения к базе данных
    выполняются через UnitOfWork, а события значимых изменений по возможности
    записываются в аудит.

    Attributes:
        uow_factory: Фабрика UnitOfWork для создания транзакционных контекстов.
        audit_service: Сервис аудита для записи событий ролей.
    """

    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        """Инициализирует сервис ролей.

        Args:
            uow_factory: Фабрика UnitOfWork. Если не передана, создаётся
                стандартная фабрика через `create_unit_of_work_factory()`.
            audit_service: Сервис аудита. Если не передан, создаётся сервис
                аудита с той же фабрикой UnitOfWork.
        """

        self.uow_factory = uow_factory or create_unit_of_work_factory()
        self.audit_service = audit_service or get_audit_service(
            uow_factory=self.uow_factory,
        )

    async def ensure_system_roles(self) -> list[RoleRead]:
        """Создаёт обязательные системные роли, если они отсутствуют.

        Returns:
            Список системных ролей после проверки и возможного создания.

        Raises:
            ServiceError: Если системные роли не удалось инициализировать.
        """

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
        """Создаёт новую роль.

        Args:
            data: Данные создаваемой роли.
            actor_id: Идентификатор пользователя, выполняющего операцию. Если
                не передан, событие аудита записывается как системное.

        Returns:
            DTO созданной роли.

        Raises:
            ServiceError: Если роль не удалось создать.
        """

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
        """Обновляет существующую роль.

        Args:
            role_id: Идентификатор обновляемой роли.
            data: Данные для частичного обновления роли.
            actor_id: Идентификатор пользователя, выполняющего операцию. Если
                не передан, событие аудита записывается как системное.

        Returns:
            DTO обновлённой роли. Если в `data` нет полей для обновления,
            возвращается текущая роль.

        Raises:
            ConflictServiceError: Если новое имя или код роли уже заняты.
            ServiceError: Если роль не удалось обновить.
        """

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
        """Возвращает роль по идентификатору.

        Args:
            role_id: Идентификатор роли.

        Returns:
            DTO найденной роли.

        Raises:
            ServiceError: Если роль не найдена или её не удалось получить.
        """

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
        """Возвращает роль по техническому имени.

        Args:
            name: Техническое имя роли.

        Returns:
            DTO найденной роли.

        Raises:
            ServiceError: Если роль не найдена или её не удалось получить.
        """

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
        """Возвращает роль по стабильному коду.

        Args:
            code: Код роли или значение `SystemRole`.

        Returns:
            DTO найденной роли.

        Raises:
            ServiceError: Если роль не найдена или её не удалось получить.
        """

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
        """Возвращает системную роль администратора.

        Returns:
            DTO роли администратора.

        Raises:
            ServiceError: Если роль администратора не найдена или её не удалось
                получить.
        """

        return await self.get_role_by_code(SystemRole.ADMIN)

    async def get_default_user_role(self) -> RoleRead:
        """Возвращает системную роль пользователя по умолчанию.

        Returns:
            DTO роли пользователя по умолчанию.

        Raises:
            ServiceError: Если роль пользователя не найдена или её не удалось
                получить.
        """

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
        """Возвращает список ролей с фильтрацией и метаданными пагинации.

        Args:
            offset: Смещение первой записи.
            limit: Максимальное количество ролей на странице.
            only_active: Если задано, фильтрует роли по признаку активности.
            only_system: Если задано, фильтрует роли по признаку системности.
            search: Поисковая строка для фильтрации ролей.
            order_by_name: Нужно ли сортировать роли по имени.

        Returns:
            Страница ролей с метаданными пагинации.

        Raises:
            ValidationServiceError: Если параметры пагинации некорректны.
            ServiceError: Если список ролей не удалось получить.
        """

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
        """Активирует роль.

        Args:
            role_id: Идентификатор активируемой роли.
            actor_id: Идентификатор пользователя, выполняющего операцию. Если
                не передан, событие аудита записывается как системное.

        Returns:
            DTO активированной роли.

        Raises:
            ServiceError: Если роль не удалось активировать.
        """

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
        """Деактивирует несистемную роль.

        Args:
            role_id: Идентификатор деактивируемой роли.
            actor_id: Идентификатор пользователя, выполняющего операцию. Если
                не передан, событие аудита записывается как системное.

        Returns:
            DTO деактивированной роли.

        Raises:
            ServiceError: Если роль не удалось деактивировать.
        """

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
        """Проверяет существование роли по имени или коду.

        Args:
            name: Техническое имя роли для проверки.
            code: Код роли или значение `SystemRole` для проверки.
            exclude_role_id: Идентификатор роли, которую нужно исключить из
                проверки уникальности.

        Returns:
            `True`, если роль с указанным именем или кодом существует.

        Raises:
            ServiceError: Если проверку существования роли не удалось выполнить.
        """

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
        """Назначает роль пользователю.

        Args:
            data: Данные назначения роли пользователю.
            actor_id: Идентификатор пользователя, выполняющего назначение.
                Если не передан, используется `data.assigned_by`.

        Returns:
            DTO созданного или существующего назначения роли.

        Raises:
            ConflictServiceError: Если роль неактивна.
            ValidationServiceError: Если не передан идентификатор роли или код
                роли.
            ServiceError: Если роль не удалось назначить.
        """

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
        """Снимает назначение роли с пользователя.

        Args:
            data: Данные снятия роли с пользователя.
            actor_id: Идентификатор пользователя, выполняющего операцию. Если
                не передан, событие аудита записывается как системное.

        Returns:
            `True`, если назначение было удалено. `False`, если такого
            назначения не было.

        Raises:
            ValidationServiceError: Если не передан идентификатор роли или код
                роли.
            ServiceError: Если роль не удалось снять.
        """

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
        """Заменяет все роли пользователя набором ролей по кодам.

        Args:
            user_id: Идентификатор пользователя.
            role_codes: Последовательность кодов ролей или значений
                `SystemRole`, которые должны остаться назначенными пользователю.
            actor_id: Идентификатор пользователя, выполняющего операцию.

        Returns:
            Список актуальных назначений ролей пользователя после замены.

        Raises:
            ValidationServiceError: Если список `role_codes` пуст.
            ServiceError: Если роли пользователя не удалось заменить.
        """

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
        """Удаляет все назначения ролей пользователя.

        Args:
            user_id: Идентификатор пользователя.
            actor_id: Идентификатор пользователя, выполняющего операцию. Если
                не передан, событие аудита записывается как системное.

        Returns:
            Количество удалённых назначений ролей.

        Raises:
            ServiceError: Если роли пользователя не удалось очистить.
        """

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
        """Проверяет наличие активной роли у пользователя.

        Args:
            user_id: Идентификатор пользователя.
            role_code: Код роли или значение `SystemRole`.

        Returns:
            `True`, если у пользователя есть активная роль с указанным кодом.

        Raises:
            ServiceError: Если проверку роли пользователя не удалось выполнить.
        """

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
        """Возвращает роли пользователя.

        Args:
            user_id: Идентификатор пользователя.
            only_active_roles: Если `True`, возвращает только активные роли.

        Returns:
            Список ролей пользователя.

        Raises:
            ServiceError: Если роли пользователя не удалось получить.
        """

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
        """Возвращает коды ролей пользователя.

        Args:
            user_id: Идентификатор пользователя.
            only_active_roles: Если `True`, учитывает только активные роли.

        Returns:
            Отсортированный список кодов ролей пользователя.

        Raises:
            ServiceError: Если коды ролей пользователя не удалось получить.
        """

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
        """Возвращает записи назначений ролей пользователя.

        Args:
            user_id: Идентификатор пользователя.

        Returns:
            Список назначений ролей пользователя с вложенной информацией о
            ролях, если она доступна.

        Raises:
            ServiceError: Если назначения ролей пользователя не удалось получить.
        """

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
        """Собирает снимки ролей из репозитория постранично.

        Args:
            uow: Активный UnitOfWork с репозиторием ролей.
            only_active: Фильтр по активности роли.
            only_system: Фильтр по системности роли.
            search: Поисковая строка для фильтрации ролей.
            order_by_name: Нужно ли сортировать роли по имени.

        Returns:
            Список словарных снимков ролей.
        """

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
        """Находит роль по идентификатору или коду.

        Args:
            uow: Активный UnitOfWork с репозиторием ролей.
            role_id: Идентификатор роли.
            role_code: Код роли или значение `SystemRole`.
            operation: Название операции сервиса для деталей ошибки.

        Returns:
            Найденная ORM-модель роли.

        Raises:
            ValidationServiceError: Если не переданы ни `role_id`, ни
                `role_code`.
            ServiceError: Если роль не удалось получить через репозиторий.
        """

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
        """Проверяет уникальность имени роли при обновлении.

        Args:
            uow: Активный UnitOfWork с репозиторием ролей.
            name: Новое техническое имя роли.
            exclude_role_id: Идентификатор обновляемой роли, которую нужно
                исключить из проверки.

        Raises:
            ConflictServiceError: Если другая роль с таким именем уже
                существует.
        """

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
        """Проверяет уникальность кода роли при обновлении.

        Args:
            uow: Активный UnitOfWork с репозиторием ролей.
            code: Новый код роли или значение `SystemRole`.
            exclude_role_id: Идентификатор обновляемой роли, которую нужно
                исключить из проверки.

        Raises:
            ConflictServiceError: Если другая роль с таким кодом уже существует.
        """

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
        """Безопасно записывает пользовательское или системное событие аудита.

        Ошибки аудита не прерывают основную бизнес-операцию: они логируются как
        предупреждения.

        Args:
            actor_id: Идентификатор пользователя-инициатора. Если `None`,
                записывается системное событие.
            action: Аудит-действие.
            entity_id: Идентификатор сущности, связанной с событием.
            message: Сообщение события аудита.
            metadata: Дополнительные данные события аудита.
            resource_type: Тип ресурса, связанного с событием.
        """

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
                "Не удалось записать событие аудита для сервиса ролей.",
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
        """Безопасно записывает системное событие аудита для ролей.

        Ошибки аудита не прерывают основную бизнес-операцию: они логируются как
        предупреждения.

        Args:
            action: Аудит-действие.
            message: Сообщение события аудита.
            metadata: Дополнительные данные события аудита.
        """

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
                "Не удалось записать системное событие аудита для сервиса ролей.",
                extra={
                    "action": action.value,
                    "error_type": exc.__class__.__name__,
                    "reason": str(exc),
                },
            )

    @staticmethod
    def _validate_pagination(*, offset: int, limit: int) -> None:
        """Проверяет параметры пагинации.

        Args:
            offset: Смещение первой записи.
            limit: Максимальное количество записей на странице.

        Raises:
            ValidationServiceError: Если `offset` отрицательный, `limit`
                меньше 1 или `limit` превышает `MAX_PAGE_LIMIT`.
        """

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
        """Преобразует ошибку базы данных в сервисную ошибку ролей.

        Args:
            exc: Исходная ошибка базы данных.
            operation: Название операции сервиса.
            message: Сообщение для итоговой сервисной ошибки.

        Returns:
            Сервисная ошибка, соответствующая ошибке базы данных.
        """

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
        """Логирует непредвиденную ошибку и преобразует её в `ServiceError`.

        Args:
            exc: Исходное исключение.
            operation: Название операции сервиса.
            message: Сообщение для логирования и итоговой сервисной ошибки.

        Returns:
            Сервисная ошибка, созданная из исходного исключения.
        """

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
    """Создаёт словарный снимок ORM-модели роли.

    Args:
        role: ORM-модель роли.

    Returns:
        Словарь с полями роли, подходящий для построения DTO.
    """

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
    """Создаёт словарный снимок назначения роли пользователю.

    Args:
        assignment: ORM-модель назначения роли.
        role_snapshot: Опциональный заранее подготовленный снимок роли. Если не
            передан, функция пытается использовать загруженную связь
            `assignment.role`.

    Returns:
        Словарь с данными назначения роли и вложенным payload роли, если роль
        доступна.
    """

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
    """Создаёт DTO чтения роли из словарного снимка.

    Args:
        snapshot: Словарный снимок роли.

    Returns:
        DTO `RoleRead`.
    """

    return RoleRead.model_validate(dict(snapshot))


def _role_list_item(snapshot: Mapping[str, Any]) -> RoleListItem:
    """Создаёт DTO элемента списка ролей из словарного снимка.

    Args:
        snapshot: Словарный снимок роли.

    Returns:
        DTO `RoleListItem`.
    """

    return RoleListItem.model_validate(_role_list_payload(snapshot))


def _user_role_read(snapshot: Mapping[str, Any]) -> UserRoleRead:
    """Создаёт DTO назначения роли из словарного снимка.

    Args:
        snapshot: Словарный снимок назначения роли.

    Returns:
        DTO `UserRoleRead`.
    """

    return UserRoleRead.model_validate(dict(snapshot))


def _role_list_payload(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Создаёт компактный payload роли для списков и вложенных DTO.

    Args:
        snapshot: Словарный снимок роли.

    Returns:
        Словарь с основными полями роли.
    """

    return {
        "id": snapshot["id"],
        "name": snapshot["name"],
        "code": snapshot["code"],
        "display_name": snapshot["display_name"],
        "is_system": snapshot["is_system"],
        "is_active": snapshot["is_active"],
    }


def _audit_role(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Создаёт payload роли для записи в аудит.

    Args:
        snapshot: Словарный снимок роли.

    Returns:
        JSON-сериализуемый словарь с ключевыми полями роли.
    """

    return {
        "id": str(snapshot["id"]),
        "name": snapshot["name"],
        "code": snapshot["code"],
        "is_system": snapshot["is_system"],
        "is_active": snapshot["is_active"],
    }


def _normalize_role_code(code: str | SystemRole) -> str:
    """Нормализует код роли.

    Args:
        code: Строковый код роли или значение `SystemRole`.

    Returns:
        Код роли в нижнем регистре без пробелов по краям.
    """

    value = code.value if isinstance(code, Enum) else code
    return str(value).strip().lower()


def get_roles_service(
    *,
    uow_factory: UnitOfWorkFactory | None = None,
    audit_service: AuditService | None = None,
) -> RolesService:
    """Создаёт экземпляр сервиса ролей.

    Args:
        uow_factory: Фабрика UnitOfWork. Если не передана, сервис создаст
            стандартную фабрику самостоятельно.
        audit_service: Сервис аудита. Если не передан, будет создан сервис
            аудита с той же фабрикой UnitOfWork.

    Returns:
        Экземпляр `RolesService`.
    """

    return RolesService(
        uow_factory=uow_factory,
        audit_service=audit_service,
    )


__all__ = [
    "RolesService",
    "get_roles_service",
]
