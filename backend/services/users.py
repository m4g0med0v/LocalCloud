from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from core.logging import get_logger
from database import DatabaseError, UnitOfWorkFactory, create_unit_of_work_factory
from database.models.enums import AuditAction, AuditResourceType, UserStatus
from database.models.roles import Role
from database.models.users import User
from schemas.common import PageMeta, PageResponse
from schemas.roles import RoleListItem
from schemas.users import (
    CurrentUserRead,
    UserAdminUpdate,
    UserBlockRequest,
    UserCreate,
    UserListItem,
    UserQueryParams,
    UserRead,
    UserRejectRequest,
    UserStatusUpdateRequest,
    UserUpdate,
    UserWithRolesRead,
)
from security.password import hash_password, require_strong_password
from services.audit import AuditService, get_audit_service
from services.exceptions import (
    ServiceError,
    ValidationServiceError,
    service_error_from_database,
    service_error_from_exception,
)

logger = get_logger("services.users")

SERVICE_NAME = "users"
MAX_PAGE_LIMIT = 1000
REPOSITORY_PAGE_LIMIT = 1000
USER_SORT_FIELDS = {
    "created_at",
    "updated_at",
    "email",
    "username",
    "status",
    "last_login_at",
}


class UsersService:
    """Business service for LocalCloud user accounts."""

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

    async def create_user(
        self,
        data: UserCreate,
        *,
        actor_id: UUID | None = None,
        assign_default_role: bool = True,
    ) -> UserRead:
        """Create a user and optionally assign the default user role."""

        operation = "create_user"
        password_hash = self._hash_password(data.password)
        snapshot: dict[str, Any] = {}

        try:
            async with self.uow_factory() as uow:
                user = await uow.users.create_user(
                    email=str(data.email),
                    username=data.username,
                    password_hash=password_hash,
                    status=data.status,
                    is_email_verified=data.is_email_verified,
                    flush=True,
                    refresh=True,
                    check_duplicates=True,
                )

                if assign_default_role:
                    role = await uow.roles.get_required_user_role_model()
                    await uow.roles.assign_role(
                        user_id=user.id,
                        role_id=role.id,
                        assigned_by=actor_id,
                        flush=True,
                        refresh=False,
                        check_user_exists=False,
                        check_role_exists=False,
                        ignore_existing=True,
                    )

                snapshot = _user_snapshot(user)
                await uow.commit()

            await self._safe_log_user_or_system_event(
                actor_id=actor_id,
                action=AuditAction.USER_CREATED,
                entity_id=snapshot["id"],
                message="User was created.",
                metadata={"operation": operation, "user": _audit_user(snapshot)},
            )
            return _user_read(snapshot)

        except ValueError as exc:
            raise ValidationServiceError(
                "Пароль пользователя не прошёл проверку.",
                field="password",
                reason="invalid_password",
                details={"service": SERVICE_NAME, "operation": operation},
                cause=exc,
            ) from exc
        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Не удалось создать пользователя."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при создании пользователя.",
            ) from exc

    async def get_user(self, user_id: UUID) -> UserRead:
        operation = "get_user"
        result: UserRead | None = None
        try:
            async with self.uow_factory() as uow:
                user = await uow.users.get_required_user_by_id(user_id)
                result = _user_read(_user_snapshot(user))
            return self._require_result(result, operation=operation)
        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Пользователь не найден."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении пользователя.",
            ) from exc

    async def get_user_with_roles(self, user_id: UUID) -> UserWithRolesRead:
        operation = "get_user_with_roles"
        result: UserWithRolesRead | None = None
        try:
            async with self.uow_factory() as uow:
                user = await uow.users.get_required_user_by_id(user_id)
                roles = await uow.roles.get_user_roles(
                    user.id, only_active_roles=False, order_by_name=True
                )
                result = _user_with_roles_read(_user_snapshot(user), roles)
            return self._require_result(result, operation=operation)
        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Пользователь не найден."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении пользователя с ролями.",
            ) from exc

    async def get_current_user_read(self, user_id: UUID) -> CurrentUserRead:
        operation = "get_current_user_read"
        result: CurrentUserRead | None = None
        try:
            async with self.uow_factory() as uow:
                user = await uow.users.get_required_user_by_id(user_id)
                roles = await uow.roles.get_user_roles(
                    user.id, only_active_roles=True, order_by_name=True
                )
                result = _current_user_read(_user_snapshot(user), roles)
            return self._require_result(result, operation=operation)
        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить текущего пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении текущего пользователя.",
            ) from exc

    async def get_user_by_email(self, email: str) -> UserRead:
        operation = "get_user_by_email"
        result: UserRead | None = None
        try:
            async with self.uow_factory() as uow:
                user = await uow.users.get_required_by_email(email)
                result = _user_read(_user_snapshot(user))
            return self._require_result(result, operation=operation)
        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Пользователь с указанным email не найден.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении пользователя по email.",
            ) from exc

    async def get_user_by_username(self, username: str) -> UserRead:
        operation = "get_user_by_username"
        result: UserRead | None = None
        try:
            async with self.uow_factory() as uow:
                user = await uow.users.get_required_by_username(username)
                result = _user_read(_user_snapshot(user))
            return self._require_result(result, operation=operation)
        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Пользователь с указанным username не найден.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении пользователя по username.",
            ) from exc

    async def email_exists(
        self, email: str, *, exclude_user_id: UUID | None = None
    ) -> bool:
        return await self._exists(
            operation="email_exists",
            call_name="email_exists",
            value=email,
            exclude_user_id=exclude_user_id,
        )

    async def username_exists(
        self, username: str, *, exclude_user_id: UUID | None = None
    ) -> bool:
        return await self._exists(
            operation="username_exists",
            call_name="username_exists",
            value=username,
            exclude_user_id=exclude_user_id,
        )

    async def list_users(self, params: UserQueryParams) -> PageResponse[UserListItem]:
        operation = "list_users"
        self._validate_pagination(offset=params.offset, limit=params.limit)
        snapshots: list[dict[str, Any]] = []

        try:
            async with self.uow_factory() as uow:
                snapshots = await self._collect_user_snapshots(uow=uow, params=params)

            snapshots = self._sort_snapshots(
                snapshots, sort_by=params.sort_by, sort_desc=params.sort_desc
            )
            total = len(snapshots)
            page = snapshots[params.offset : params.offset + params.limit]

            return PageResponse[UserListItem](
                items=[_user_list_item(snapshot) for snapshot in page],
                meta=PageMeta(
                    limit=params.limit,
                    offset=params.offset,
                    total=total,
                    count=len(page),
                ),
            )

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить список пользователей.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении списка пользователей.",
            ) from exc

    async def update_user(
        self,
        user_id: UUID,
        data: UserUpdate,
        *,
        actor_id: UUID | None = None,
    ) -> UserRead:
        operation = "update_user"
        values = data.model_dump(exclude_unset=True)
        if not values:
            return await self.get_user(user_id)

        snapshot: dict[str, Any] = {}
        try:
            async with self.uow_factory() as uow:
                user = await uow.users.update_identity_by_id(
                    user_id,
                    email=str(values["email"])
                    if values.get("email") is not None
                    else None,
                    username=values.get("username"),
                    flush=True,
                    refresh=True,
                    check_duplicates=True,
                )
                snapshot = _user_snapshot(user)
                await uow.commit()

            await self._safe_log_user_or_system_event(
                actor_id=actor_id or user_id,
                action=AuditAction.USER_UPDATED,
                entity_id=user_id,
                message="User identity was updated.",
                metadata={
                    "operation": operation,
                    "user": _audit_user(snapshot),
                    "updated_fields": sorted(values),
                },
            )
            return _user_read(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось обновить пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при обновлении пользователя.",
            ) from exc

    async def admin_update_user(
        self,
        user_id: UUID,
        data: UserAdminUpdate,
        *,
        actor_id: UUID | None = None,
    ) -> UserRead:
        operation = "admin_update_user"
        values = data.model_dump(exclude_unset=True)
        if not values:
            return await self.get_user(user_id)

        snapshot: dict[str, Any] = {}
        try:
            async with self.uow_factory() as uow:
                user = await uow.users.get_required_user_by_id(user_id)
                identity_values = {
                    key: values[key]
                    for key in ("email", "username")
                    if key in values and values[key] is not None
                }
                if identity_values:
                    user = await uow.users.update_identity(
                        user,
                        email=str(identity_values.get("email"))
                        if identity_values.get("email") is not None
                        else None,
                        username=identity_values.get("username"),
                        flush=True,
                        refresh=True,
                        check_duplicates=True,
                    )

                if "status" in values and values["status"] is not None:
                    user = await uow.users.update_status(
                        user,
                        values["status"],
                        block_reason=values.get("block_reason"),
                        rejection_reason=values.get("rejection_reason"),
                        flush=True,
                        refresh=True,
                    )

                if "is_email_verified" in values:
                    user = await uow.users.set_email_verified(
                        user,
                        is_verified=bool(values["is_email_verified"]),
                        flush=True,
                        refresh=True,
                    )

                snapshot = _user_snapshot(user)
                await uow.commit()

            await self._safe_log_user_or_system_event(
                actor_id=actor_id,
                action=AuditAction.USER_UPDATED,
                entity_id=user_id,
                message="User was updated by administrator.",
                metadata={
                    "operation": operation,
                    "user": _audit_user(snapshot),
                    "updated_fields": sorted(values),
                },
            )
            return _user_read(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось административно обновить пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при административном обновлении пользователя.",
            ) from exc

    async def update_status(
        self,
        user_id: UUID,
        data: UserStatusUpdateRequest,
        *,
        actor_id: UUID | None = None,
    ) -> UserRead:
        if data.status == UserStatus.ACTIVE:
            return await self.approve_user(
                user_id, actor_id=actor_id, is_email_verified=True
            )
        if data.status == UserStatus.BLOCKED:
            if not data.reason:
                raise ValidationServiceError(
                    "Для блокировки пользователя нужно указать причину.",
                    field="reason",
                    reason="missing_block_reason",
                    details={"service": SERVICE_NAME, "operation": "update_status"},
                )
            return await self.block_user(
                user_id, UserBlockRequest(reason=data.reason), actor_id=actor_id
            )
        if data.status == UserStatus.REJECTED:
            if not data.reason:
                raise ValidationServiceError(
                    "Для отклонения пользователя нужно указать причину.",
                    field="reason",
                    reason="missing_rejection_reason",
                    details={"service": SERVICE_NAME, "operation": "update_status"},
                )
            return await self.reject_user(
                user_id, UserRejectRequest(reason=data.reason), actor_id=actor_id
            )
        if data.status == UserStatus.DELETED:
            return await self.delete_user(user_id, actor_id=actor_id)
        return await self.admin_update_user(
            user_id,
            UserAdminUpdate(status=data.status),
            actor_id=actor_id,
        )

    async def approve_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID | None = None,
        is_email_verified: bool = True,
    ) -> UserRead:
        snapshot = await self._mutate_status(
            user_id=user_id,
            actor_id=actor_id,
            action=AuditAction.USER_UPDATED,
            operation="approve_user",
            message="User was approved.",
            mutator=lambda uow, user: uow.users.mark_active(
                user, flush=True, refresh=False
            ),
            after=lambda user: setattr(user, "is_email_verified", is_email_verified),
        )
        return _user_read(snapshot)

    async def block_user(
        self,
        user_id: UUID,
        data: UserBlockRequest,
        *,
        actor_id: UUID | None = None,
    ) -> UserRead:
        snapshot = await self._mutate_status(
            user_id=user_id,
            actor_id=actor_id,
            action=AuditAction.USER_BLOCKED,
            operation="block_user",
            message="User was blocked.",
            mutator=lambda uow, user: uow.users.mark_blocked(
                user, reason=data.reason, flush=True, refresh=False
            ),
        )
        return _user_read(snapshot)

    async def unblock_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID | None = None,
    ) -> UserRead:
        snapshot = await self._mutate_status(
            user_id=user_id,
            actor_id=actor_id,
            action=AuditAction.USER_UNBLOCKED,
            operation="unblock_user",
            message="User was unblocked.",
            mutator=lambda uow, user: uow.users.unblock(
                user, flush=True, refresh=False
            ),
        )
        return _user_read(snapshot)

    async def reject_user(
        self,
        user_id: UUID,
        data: UserRejectRequest,
        *,
        actor_id: UUID | None = None,
    ) -> UserRead:
        snapshot = await self._mutate_status(
            user_id=user_id,
            actor_id=actor_id,
            action=AuditAction.USER_UPDATED,
            operation="reject_user",
            message="User was rejected.",
            mutator=lambda uow, user: uow.users.mark_rejected(
                user, reason=data.reason, flush=True, refresh=False
            ),
        )
        return _user_read(snapshot)

    async def delete_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID | None = None,
    ) -> UserRead:
        snapshot = await self._mutate_status(
            user_id=user_id,
            actor_id=actor_id,
            action=AuditAction.USER_DELETED,
            operation="delete_user",
            message="User was soft deleted.",
            mutator=lambda uow, user: uow.users.mark_deleted(
                user, flush=True, refresh=False
            ),
        )
        return _user_read(snapshot)

    async def set_email_verified(
        self,
        user_id: UUID,
        *,
        is_verified: bool = True,
        actor_id: UUID | None = None,
    ) -> UserRead:
        operation = "set_email_verified"
        snapshot: dict[str, Any] = {}
        try:
            async with self.uow_factory() as uow:
                user = await uow.users.set_email_verified_by_id(
                    user_id,
                    is_verified=is_verified,
                    flush=True,
                    refresh=True,
                )
                snapshot = _user_snapshot(user)
                await uow.commit()

            await self._safe_log_user_or_system_event(
                actor_id=actor_id or user_id,
                action=AuditAction.USER_UPDATED,
                entity_id=user_id,
                message="User email verification flag was updated.",
                metadata={
                    "operation": operation,
                    "user": _audit_user(snapshot),
                    "is_email_verified": is_verified,
                },
            )
            return _user_read(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось обновить признак подтверждения email.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при обновлении признака email.",
            ) from exc

    async def change_password(
        self,
        user_id: UUID,
        new_password: str,
        *,
        actor_id: UUID | None = None,
    ) -> UserRead:
        operation = "change_password"
        password_hash = self._hash_password(new_password)
        snapshot: dict[str, Any] = {}

        try:
            async with self.uow_factory() as uow:
                user = await uow.users.update_password_hash_by_id(
                    user_id,
                    password_hash=password_hash,
                    flush=True,
                    refresh=True,
                )
                snapshot = _user_snapshot(user)
                await uow.commit()

            await self._safe_log_user_or_system_event(
                actor_id=actor_id or user_id,
                action=AuditAction.USER_UPDATED,
                entity_id=user_id,
                message="User password was changed.",
                metadata={"operation": operation, "user": _audit_user(snapshot)},
            )
            return _user_read(snapshot)

        except ValueError as exc:
            raise ValidationServiceError(
                "Пароль пользователя не прошёл проверку.",
                field="new_password",
                reason="invalid_password",
                details={"service": SERVICE_NAME, "operation": operation},
                cause=exc,
            ) from exc
        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось изменить пароль пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при изменении пароля пользователя.",
            ) from exc

    async def mark_login(self, user_id: UUID) -> UserRead:
        operation = "mark_login"
        snapshot: dict[str, Any] = {}
        try:
            async with self.uow_factory() as uow:
                user = await uow.users.update_last_login_by_id(
                    user_id,
                    last_login_at=datetime.now(UTC),
                    flush=True,
                    refresh=True,
                )
                snapshot = _user_snapshot(user)
                await uow.commit()
            return _user_read(snapshot)
        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось обновить время последнего входа.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при обновлении времени входа.",
            ) from exc

    async def get_status_counts(self) -> dict[UserStatus, int]:
        operation = "get_status_counts"
        result: dict[UserStatus, int] | None = None
        try:
            async with self.uow_factory() as uow:
                counts = await uow.users.get_status_counts()
                result = {status: counts.get(status, 0) for status in UserStatus}

            if result is None:
                raise ServiceError(
                    "Не удалось получить статистику пользователей.",
                    service=SERVICE_NAME,
                    operation=operation,
                )
            return result
        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить статистику пользователей.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении статистики пользователей.",
            ) from exc

    async def _exists(
        self,
        *,
        operation: str,
        call_name: str,
        value: str,
        exclude_user_id: UUID | None,
    ) -> bool:
        result = False
        try:
            async with self.uow_factory() as uow:
                if call_name == "email_exists":
                    result = await uow.users.email_exists(
                        value,
                        exclude_user_id=exclude_user_id,
                        include_deleted=True,
                    )
                else:
                    result = await uow.users.username_exists(
                        value,
                        exclude_user_id=exclude_user_id,
                        include_deleted=True,
                    )
            return result
        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось проверить уникальность пользователя.",
            ) from exc

    async def _collect_user_snapshots(
        self, *, uow: Any, params: UserQueryParams
    ) -> list[dict[str, Any]]:
        statuses = [params.status] if params.status is not None else None
        offset = 0
        snapshots: list[dict[str, Any]] = []

        while True:
            if params.query:
                users = await uow.users.search_users(
                    params.query,
                    offset=offset,
                    limit=REPOSITORY_PAGE_LIMIT,
                    statuses=statuses,
                    include_deleted=False,
                    only_email_verified=params.is_email_verified,
                )
            else:
                users = await uow.users.list_users(
                    offset=offset,
                    limit=REPOSITORY_PAGE_LIMIT,
                    statuses=statuses,
                    include_deleted=False,
                    only_email_verified=params.is_email_verified,
                    order_by_created_desc=True,
                )

            snapshots.extend(
                snapshot
                for snapshot in (_user_snapshot(user) for user in users)
                if _matches_created_range(snapshot, params)
            )

            if len(users) < REPOSITORY_PAGE_LIMIT:
                break
            offset += REPOSITORY_PAGE_LIMIT

        return snapshots

    async def _mutate_status(
        self,
        *,
        user_id: UUID,
        actor_id: UUID | None,
        action: AuditAction,
        operation: str,
        message: str,
        mutator: Any,
        after: Any | None = None,
    ) -> dict[str, Any]:
        snapshot: dict[str, Any] = {}
        try:
            async with self.uow_factory() as uow:
                user = await uow.users.get_required_user_by_id(user_id)
                user = await mutator(uow, user)
                if after is not None:
                    after(user)
                user = await uow.flush_and_refresh(user)
                snapshot = _user_snapshot(user)
                await uow.commit()

            await self._safe_log_user_or_system_event(
                actor_id=actor_id,
                action=action,
                entity_id=user_id,
                message=message,
                metadata={"operation": operation, "user": _audit_user(snapshot)},
            )
            return snapshot

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Не удалось изменить пользователя."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при изменении пользователя.",
            ) from exc

    @staticmethod
    def _hash_password(password: str) -> str:
        require_strong_password(password)
        return hash_password(password)

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
        if limit < 1 or limit > MAX_PAGE_LIMIT:
            raise ValidationServiceError(
                f"limit должен быть от 1 до {MAX_PAGE_LIMIT}.",
                field="limit",
                value=limit,
                reason="invalid_limit",
                details={"service": SERVICE_NAME, "operation": "validate_pagination"},
            )

    @staticmethod
    def _sort_snapshots(
        snapshots: list[dict[str, Any]], *, sort_by: str, sort_desc: bool
    ) -> list[dict[str, Any]]:
        normalized_sort_by = sort_by if sort_by in USER_SORT_FIELDS else "created_at"
        return sorted(
            snapshots,
            key=lambda item: (
                item.get(normalized_sort_by) is None,
                item.get(normalized_sort_by),
            ),
            reverse=sort_desc,
        )

    @staticmethod
    def _require_result(result: Any | None, *, operation: str) -> Any:
        if result is None:
            raise ServiceError(
                "Сервис пользователей не вернул результат операции.",
                service=SERVICE_NAME,
                operation=operation,
            )
        return result

    @staticmethod
    def _database_error(
        exc: DatabaseError, *, operation: str, message: str
    ) -> ServiceError:
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

    async def _safe_log_user_or_system_event(
        self,
        *,
        actor_id: UUID | None,
        action: AuditAction,
        entity_id: UUID | None,
        message: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        try:
            if actor_id is None:
                await self.audit_service.log_system_event(
                    action=action,
                    entity_type=AuditResourceType.USER.value,
                    entity_id=entity_id,
                    resource_type=AuditResourceType.USER,
                    message=message,
                    metadata=metadata,
                )
                return
            await self.audit_service.log_user_event(
                user_id=actor_id,
                action=action,
                entity_type=AuditResourceType.USER.value,
                entity_id=entity_id,
                resource_type=AuditResourceType.USER,
                message=message,
                metadata=metadata,
            )
        except Exception as exc:
            logger.warning(
                "Failed to write audit event for users service.",
                extra={
                    "action": action.value,
                    "entity_id": str(entity_id) if entity_id else None,
                    "actor_id": str(actor_id) if actor_id else None,
                    "error_type": exc.__class__.__name__,
                    "reason": str(exc),
                },
            )


def _user_snapshot(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "status": user.status,
        "is_email_verified": user.is_email_verified,
        "last_login_at": user.last_login_at,
        "approved_at": user.approved_at,
        "blocked_at": user.blocked_at,
        "rejected_at": user.rejected_at,
        "deleted_at": user.deleted_at,
        "block_reason": user.block_reason,
        "rejection_reason": user.rejection_reason,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def _role_snapshot(role: Role) -> dict[str, Any]:
    return {
        "id": role.id,
        "name": role.name,
        "code": role.code,
        "display_name": role.display_name,
        "is_system": role.is_system,
        "is_active": role.is_active,
    }


def _user_read(snapshot: Mapping[str, Any]) -> UserRead:
    return UserRead.model_validate(dict(snapshot))


def _user_list_item(snapshot: Mapping[str, Any]) -> UserListItem:
    return UserListItem.model_validate(dict(snapshot))


def _user_with_roles_read(
    snapshot: Mapping[str, Any], roles: list[Role]
) -> UserWithRolesRead:
    payload = dict(snapshot)
    payload["roles"] = [_role_list_item(role) for role in roles]
    return UserWithRolesRead.model_validate(payload)


def _current_user_read(
    snapshot: Mapping[str, Any], roles: list[Role]
) -> CurrentUserRead:
    payload = dict(snapshot)
    payload["roles"] = [_role_list_item(role) for role in roles]
    return CurrentUserRead.model_validate(payload)


def _role_list_item(role: Role) -> RoleListItem:
    return RoleListItem.model_validate(_role_snapshot(role))


def _audit_user(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(snapshot["id"]),
        "email": str(snapshot["email"]),
        "username": snapshot["username"],
        "status": snapshot["status"].value
        if isinstance(snapshot["status"], UserStatus)
        else str(snapshot["status"]),
    }


def _matches_created_range(
    snapshot: Mapping[str, Any], params: UserQueryParams
) -> bool:
    created_at = snapshot.get("created_at")
    if not isinstance(created_at, datetime):
        return True
    if params.created_from is not None and created_at < params.created_from:
        return False
    if params.created_to is not None and created_at > params.created_to:
        return False
    return True


def get_users_service(
    *,
    uow_factory: UnitOfWorkFactory | None = None,
    audit_service: AuditService | None = None,
) -> UsersService:
    return UsersService(uow_factory=uow_factory, audit_service=audit_service)


__all__ = ["UsersService", "get_users_service"]
