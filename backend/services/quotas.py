from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from core.logging import get_logger
from database import DatabaseError, UnitOfWorkFactory, create_unit_of_work_factory
from database.models.enums import AuditAction, AuditResourceType, QuotaResourceType
from database.models.quotas import UserQuota
from schemas.common import PageMeta, PageResponse
from schemas.quotas import (
    QuotaCheckRequest,
    QuotaCheckResponse,
    QuotaRecalculateRequest,
    QuotaUsageRead,
    UserQuotaCreate,
    UserQuotaRead,
    UserQuotaUpdate,
)
from services.audit import AuditService, get_audit_service
from services.exceptions import (
    QuotaExceededServiceError,
    ServiceError,
    ValidationServiceError,
    service_error_from_database,
    service_error_from_exception,
)

logger = get_logger("services.quotas")

SERVICE_NAME = "quotas"
MAX_PAGE_LIMIT = 1000
REPOSITORY_PAGE_LIMIT = 1000


class QuotasService:
    """Business service for user quota limits and resource usage counters."""

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

    async def create_quota(
        self, data: UserQuotaCreate, *, actor_id: UUID | None = None
    ) -> UserQuotaRead:
        """Create an explicit quota for a user."""

        operation = "create_quota"
        snapshot: dict[str, Any] = {}
        try:
            async with self.uow_factory() as uow:
                quota = await uow.quotas.create_quota(
                    user_id=data.user_id,
                    storage_limit_bytes=data.storage_limit_bytes,
                    max_file_size_bytes=data.max_file_size_bytes,
                    storage_used_bytes=data.storage_used_bytes,
                    files_limit=data.files_limit,
                    files_used=data.files_used,
                    public_links_limit=data.public_links_limit,
                    public_links_used=data.public_links_used,
                    active_upload_sessions_limit=data.active_upload_sessions_limit,
                    active_upload_sessions_used=data.active_upload_sessions_used,
                    flush=True,
                    refresh=True,
                )
                snapshot = _quota_snapshot(quota)
                await uow.commit()

            await self._safe_log_quota_event(
                actor_id=actor_id,
                user_id=data.user_id,
                action=AuditAction.QUOTA_CREATED,
                entity_id=snapshot["id"],
                message="User quota was created.",
                metadata={"operation": operation, "quota": _audit_quota(snapshot)},
            )
            return _quota_read(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось создать квоту пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при создании квоты пользователя.",
            ) from exc

    async def create_default_quota(
        self,
        user_id: UUID,
        *,
        actor_id: UUID | None = None,
        storage_limit_bytes: int = 10 * 1024 * 1024 * 1024,
        max_file_size_bytes: int = 1024 * 1024 * 1024,
        files_limit: int | None = None,
        public_links_limit: int | None = 100,
        active_upload_sessions_limit: int | None = 10,
    ) -> UserQuotaRead:
        """Create a quota with LocalCloud default limits."""

        operation = "create_default_quota"
        snapshot: dict[str, Any] = {}
        try:
            async with self.uow_factory() as uow:
                quota = await uow.quotas.create_default_quota(
                    user_id=user_id,
                    storage_limit_bytes=storage_limit_bytes,
                    max_file_size_bytes=max_file_size_bytes,
                    files_limit=files_limit,
                    public_links_limit=public_links_limit,
                    active_upload_sessions_limit=active_upload_sessions_limit,
                    flush=True,
                    refresh=True,
                )
                snapshot = _quota_snapshot(quota)
                await uow.commit()

            await self._safe_log_quota_event(
                actor_id=actor_id,
                user_id=user_id,
                action=AuditAction.QUOTA_CREATED,
                entity_id=snapshot["id"],
                message="Default user quota was created.",
                metadata={"operation": operation, "quota": _audit_quota(snapshot)},
            )
            return _quota_read(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось создать стандартную квоту пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при создании стандартной квоты.",
            ) from exc

    async def ensure_default_quota(
        self,
        user_id: UUID,
        *,
        actor_id: UUID | None = None,
        storage_limit_bytes: int = 10 * 1024 * 1024 * 1024,
        max_file_size_bytes: int = 1024 * 1024 * 1024,
        files_limit: int | None = None,
        public_links_limit: int | None = 100,
        active_upload_sessions_limit: int | None = 10,
    ) -> UserQuotaRead:
        """Return an existing quota or create the default quota for a user."""

        existing = await self.get_quota_or_none(user_id)
        if existing is not None:
            return existing
        return await self.create_default_quota(
            user_id,
            actor_id=actor_id,
            storage_limit_bytes=storage_limit_bytes,
            max_file_size_bytes=max_file_size_bytes,
            files_limit=files_limit,
            public_links_limit=public_links_limit,
            active_upload_sessions_limit=active_upload_sessions_limit,
        )

    async def get_quota(self, user_id: UUID) -> UserQuotaRead:
        operation = "get_quota"
        result: UserQuotaRead | None = None
        try:
            async with self.uow_factory() as uow:
                quota = await uow.quotas.get_required_by_user_id(user_id)
                result = _quota_read(_quota_snapshot(quota))
            return self._require_result(result, operation=operation)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Квота пользователя не найдена."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении квоты пользователя.",
            ) from exc

    async def get_quota_or_none(self, user_id: UUID) -> UserQuotaRead | None:
        operation = "get_quota_or_none"
        try:
            async with self.uow_factory() as uow:
                quota = await uow.quotas.get_by_user_id(user_id)
                if quota is None:
                    return None
                return _quota_read(_quota_snapshot(quota))

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить квоту пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении квоты пользователя.",
            ) from exc

    async def get_usage(self, user_id: UUID) -> QuotaUsageRead:
        operation = "get_usage"
        result: QuotaUsageRead | None = None
        try:
            async with self.uow_factory() as uow:
                quota = await uow.quotas.get_required_by_user_id(user_id)
                result = _usage_read(_quota_snapshot(quota))
            return self._require_result(result, operation=operation)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить использование квоты.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении использования квоты.",
            ) from exc

    async def update_quota(
        self,
        user_id: UUID,
        data: UserQuotaUpdate,
        *,
        actor_id: UUID | None = None,
    ) -> UserQuotaRead:
        """Update quota limits and, when explicitly provided, stored counters."""

        operation = "update_quota"
        values = data.model_dump(exclude_unset=True)
        if not values:
            return await self.get_quota(user_id)

        snapshot: dict[str, Any] = {}
        try:
            async with self.uow_factory() as uow:
                quota = await uow.quotas.get_required_by_user_id(
                    user_id, for_update=True
                )

                limit_kwargs: dict[str, Any] = {}
                for field_name in (
                    "storage_limit_bytes",
                    "max_file_size_bytes",
                    "files_limit",
                    "public_links_limit",
                    "active_upload_sessions_limit",
                ):
                    if field_name in values:
                        limit_kwargs[field_name] = values[field_name]

                if limit_kwargs:
                    quota = await uow.quotas.update_limits(
                        user_id,
                        **limit_kwargs,
                        flush=True,
                        refresh=False,
                        for_update=False,
                    )

                if (
                    "storage_used_bytes" in values
                    and values["storage_used_bytes"] is not None
                ):
                    quota = await uow.quotas.update_storage_used(
                        user_id,
                        storage_used_bytes=values["storage_used_bytes"],
                        flush=True,
                        refresh=False,
                        for_update=False,
                    )
                if "files_used" in values and values["files_used"] is not None:
                    quota = await uow.quotas.set_files_used(
                        user_id,
                        count=values["files_used"],
                        flush=True,
                        refresh=False,
                        for_update=False,
                    )
                if (
                    "public_links_used" in values
                    and values["public_links_used"] is not None
                ):
                    quota = await uow.quotas.set_public_links_used(
                        user_id,
                        count=values["public_links_used"],
                        flush=True,
                        refresh=False,
                        for_update=False,
                    )
                if (
                    "active_upload_sessions_used" in values
                    and values["active_upload_sessions_used"] is not None
                ):
                    quota = await uow.quotas.set_active_upload_sessions_used(
                        user_id,
                        count=values["active_upload_sessions_used"],
                        flush=True,
                        refresh=False,
                        for_update=False,
                    )

                quota = await uow.flush_and_refresh(quota)
                snapshot = _quota_snapshot(quota)
                await uow.commit()

            await self._safe_log_quota_event(
                actor_id=actor_id,
                user_id=user_id,
                action=AuditAction.QUOTA_UPDATED,
                entity_id=snapshot["id"],
                message="User quota was updated.",
                metadata={
                    "operation": operation,
                    "updated_fields": sorted(values),
                    "quota": _audit_quota(snapshot),
                },
            )
            return _quota_read(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось обновить квоту пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при обновлении квоты пользователя.",
            ) from exc

    async def check_quota(self, data: QuotaCheckRequest) -> QuotaCheckResponse:
        """Check whether a requested resource amount fits into the current quota."""

        operation = "check_quota"
        snapshot: dict[str, Any] = {}
        try:
            async with self.uow_factory() as uow:
                quota = await uow.quotas.get_required_by_user_id(data.user_id)
                snapshot = _quota_snapshot(quota)
            return _check_response(snapshot, data.resource_type, data.requested_amount)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось проверить квоту пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при проверке квоты пользователя.",
            ) from exc

    async def require_quota(
        self,
        data: QuotaCheckRequest,
        *,
        actor_id: UUID | None = None,
    ) -> QuotaCheckResponse:
        """Check quota and raise a service error when the operation is denied."""

        response = await self.check_quota(data)
        if response.allowed:
            return response

        await self._safe_log_quota_event(
            actor_id=actor_id,
            user_id=data.user_id,
            action=AuditAction.QUOTA_EXCEEDED,
            entity_id=None,
            message="User quota was exceeded.",
            metadata={
                "operation": "require_quota",
                "check": response.model_dump(mode="json"),
            },
        )
        raise QuotaExceededServiceError(
            response.reason,
            user_id=data.user_id,
            resource_type=response.resource_type.value,
            requested=response.requested_amount,
            used=response.used,
            limit=response.limit,
            available=response.available,
            details={"service": SERVICE_NAME, "operation": "require_quota"},
        )

    async def increase_usage(
        self,
        user_id: UUID,
        resource_type: QuotaResourceType,
        amount: int = 1,
        *,
        actor_id: UUID | None = None,
        check_limit: bool = True,
    ) -> UserQuotaRead:
        """Increase a stored quota counter atomically."""

        operation = "increase_usage"
        self._validate_amount(amount, operation=operation)

        if check_limit:
            await self.require_quota(
                QuotaCheckRequest(
                    user_id=user_id,
                    resource_type=resource_type,
                    requested_amount=amount,
                ),
                actor_id=actor_id,
            )

        snapshot: dict[str, Any] = {}
        try:
            async with self.uow_factory() as uow:
                quota = await self._increase_counter(
                    uow=uow,
                    user_id=user_id,
                    resource_type=resource_type,
                    amount=amount,
                )
                quota = await uow.flush_and_refresh(quota)
                snapshot = _quota_snapshot(quota)
                await uow.commit()

            return _quota_read(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось увеличить использование квоты.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при увеличении использования квоты.",
            ) from exc

    async def decrease_usage(
        self,
        user_id: UUID,
        resource_type: QuotaResourceType,
        amount: int = 1,
    ) -> UserQuotaRead:
        """Decrease a stored quota counter atomically without going below zero."""

        operation = "decrease_usage"
        self._validate_amount(amount, operation=operation)
        snapshot: dict[str, Any] = {}

        try:
            async with self.uow_factory() as uow:
                quota = await self._decrease_counter(
                    uow=uow,
                    user_id=user_id,
                    resource_type=resource_type,
                    amount=amount,
                )
                quota = await uow.flush_and_refresh(quota)
                snapshot = _quota_snapshot(quota)
                await uow.commit()

            return _quota_read(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось уменьшить использование квоты.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при уменьшении использования квоты.",
            ) from exc

    async def can_store_file(self, user_id: UUID, file_size_bytes: int) -> bool:
        operation = "can_store_file"
        self._validate_amount(file_size_bytes, operation=operation, allow_zero=True)
        result: bool | None = None
        try:
            async with self.uow_factory() as uow:
                result = await uow.quotas.can_store_file(
                    user_id,
                    file_size_bytes=file_size_bytes,
                )
            if result is None:
                raise ServiceError(
                    "Сервис квот не вернул результат проверки загрузки файла.",
                    service=SERVICE_NAME,
                    operation=operation,
                )
            return result

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось проверить возможность загрузки файла.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при проверке загрузки файла.",
            ) from exc

    async def require_file_can_be_stored(
        self,
        user_id: UUID,
        file_size_bytes: int,
        *,
        actor_id: UUID | None = None,
    ) -> None:
        allowed = await self.can_store_file(user_id, file_size_bytes)
        if allowed:
            return

        check = await self.check_quota(
            QuotaCheckRequest(
                user_id=user_id,
                resource_type=QuotaResourceType.STORAGE_BYTES,
                requested_amount=file_size_bytes,
            )
        )
        await self._safe_log_quota_event(
            actor_id=actor_id,
            user_id=user_id,
            action=AuditAction.QUOTA_EXCEEDED,
            entity_id=None,
            message="File cannot be stored because quota limits were exceeded.",
            metadata={
                "operation": "require_file_can_be_stored",
                "check": check.model_dump(mode="json"),
            },
        )
        raise QuotaExceededServiceError(
            check.reason or "Файл превышает доступные лимиты пользователя.",
            user_id=user_id,
            resource_type=QuotaResourceType.STORAGE_BYTES.value,
            requested=file_size_bytes,
            used=check.used,
            limit=check.limit,
            available=check.available,
            details={
                "service": SERVICE_NAME,
                "operation": "require_file_can_be_stored",
            },
        )

    async def recalculate_quota(
        self,
        data: QuotaRecalculateRequest,
        *,
        actor_id: UUID | None = None,
    ) -> UserQuotaRead:
        """Recalculate quota counters from database metadata."""

        operation = "recalculate_quota"
        resource_types = set(data.resource_types or list(QuotaResourceType))
        snapshot: dict[str, Any] = {}

        try:
            async with self.uow_factory() as uow:
                if resource_types == set(QuotaResourceType):
                    quota = await uow.quotas.recalculate_all(data.user_id)
                elif resource_types == {QuotaResourceType.STORAGE_BYTES}:
                    quota = await uow.quotas.recalculate_usage(data.user_id)
                elif resource_types.isdisjoint({QuotaResourceType.STORAGE_BYTES}):
                    quota = await uow.quotas.recalculate_counters(data.user_id)
                else:
                    quota = await uow.quotas.recalculate_usage(data.user_id)
                    quota = await uow.quotas.recalculate_counters(
                        data.user_id,
                        for_update=False,
                    )

                quota = await uow.flush_and_refresh(quota)
                snapshot = _quota_snapshot(quota)
                await uow.commit()

            await self._safe_log_quota_event(
                actor_id=actor_id,
                user_id=data.user_id,
                action=AuditAction.QUOTA_RECALCULATED,
                entity_id=snapshot["id"],
                message="User quota was recalculated.",
                metadata={
                    "operation": operation,
                    "resource_types": [
                        resource_type.value for resource_type in resource_types
                    ],
                    "force": data.force,
                    "quota": _audit_quota(snapshot),
                },
            )
            return _quota_read(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось пересчитать квоту пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при пересчете квоты пользователя.",
            ) from exc

    async def list_near_limit(
        self,
        *,
        threshold_percent: float = 90.0,
        offset: int = 0,
        limit: int = 100,
    ) -> PageResponse[UserQuotaRead]:
        operation = "list_near_limit"
        self._validate_pagination(offset=offset, limit=limit)
        snapshots: list[dict[str, Any]] = []

        try:
            async with self.uow_factory() as uow:
                snapshots = await self._collect_near_limit_snapshots(
                    uow=uow,
                    threshold_percent=threshold_percent,
                )

            total = len(snapshots)
            page = snapshots[offset : offset + limit]
            return PageResponse[UserQuotaRead](
                items=[_quota_read(snapshot) for snapshot in page],
                meta=PageMeta(limit=limit, offset=offset, total=total, count=len(page)),
            )

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить квоты, близкие к лимиту.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении квот, близких к лимиту.",
            ) from exc

    async def list_over_limit(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> PageResponse[UserQuotaRead]:
        operation = "list_over_limit"
        self._validate_pagination(offset=offset, limit=limit)
        snapshots: list[dict[str, Any]] = []

        try:
            async with self.uow_factory() as uow:
                snapshots = await self._collect_over_limit_snapshots(uow=uow)

            total = len(snapshots)
            page = snapshots[offset : offset + limit]
            return PageResponse[UserQuotaRead](
                items=[_quota_read(snapshot) for snapshot in page],
                meta=PageMeta(limit=limit, offset=offset, total=total, count=len(page)),
            )

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить квоты с превышением лимита.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении квот с превышением лимита.",
            ) from exc

    async def _increase_counter(
        self,
        *,
        uow: Any,
        user_id: UUID,
        resource_type: QuotaResourceType,
        amount: int,
    ) -> UserQuota:
        if resource_type == QuotaResourceType.STORAGE_BYTES:
            return await uow.quotas.increase_used_space(
                user_id,
                size_bytes=amount,
                flush=True,
                refresh=False,
            )
        if resource_type == QuotaResourceType.FILE_COUNT:
            return await uow.quotas.increase_files_used(
                user_id,
                count=amount,
                flush=True,
                refresh=False,
            )
        if resource_type == QuotaResourceType.PUBLIC_LINK_COUNT:
            return await uow.quotas.increase_public_links_used(
                user_id,
                count=amount,
                flush=True,
                refresh=False,
            )
        if resource_type == QuotaResourceType.UPLOAD_SESSION_COUNT:
            return await uow.quotas.increase_active_upload_sessions_used(
                user_id,
                count=amount,
                flush=True,
                refresh=False,
            )
        raise self._invalid_resource_type(resource_type)

    async def _decrease_counter(
        self,
        *,
        uow: Any,
        user_id: UUID,
        resource_type: QuotaResourceType,
        amount: int,
    ) -> UserQuota:
        if resource_type == QuotaResourceType.STORAGE_BYTES:
            return await uow.quotas.decrease_used_space(
                user_id,
                size_bytes=amount,
                flush=True,
                refresh=False,
            )
        if resource_type == QuotaResourceType.FILE_COUNT:
            return await uow.quotas.decrease_files_used(
                user_id,
                count=amount,
                flush=True,
                refresh=False,
            )
        if resource_type == QuotaResourceType.PUBLIC_LINK_COUNT:
            return await uow.quotas.decrease_public_links_used(
                user_id,
                count=amount,
                flush=True,
                refresh=False,
            )
        if resource_type == QuotaResourceType.UPLOAD_SESSION_COUNT:
            return await uow.quotas.decrease_active_upload_sessions_used(
                user_id,
                count=amount,
                flush=True,
                refresh=False,
            )
        raise self._invalid_resource_type(resource_type)

    async def _collect_near_limit_snapshots(
        self, *, uow: Any, threshold_percent: float
    ) -> list[dict[str, Any]]:
        snapshots: list[dict[str, Any]] = []
        offset = 0
        while True:
            quotas = await uow.quotas.list_near_limit(
                threshold_percent=threshold_percent,
                offset=offset,
                limit=REPOSITORY_PAGE_LIMIT,
            )
            snapshots.extend(_quota_snapshot(quota) for quota in quotas)
            if len(quotas) < REPOSITORY_PAGE_LIMIT:
                break
            offset += REPOSITORY_PAGE_LIMIT
        return snapshots

    async def _collect_over_limit_snapshots(self, *, uow: Any) -> list[dict[str, Any]]:
        snapshots: list[dict[str, Any]] = []
        offset = 0
        while True:
            quotas = await uow.quotas.list_over_limit(
                offset=offset,
                limit=REPOSITORY_PAGE_LIMIT,
            )
            snapshots.extend(_quota_snapshot(quota) for quota in quotas)
            if len(quotas) < REPOSITORY_PAGE_LIMIT:
                break
            offset += REPOSITORY_PAGE_LIMIT
        return snapshots

    @staticmethod
    def _validate_amount(
        amount: int, *, operation: str, allow_zero: bool = False
    ) -> None:
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ValidationServiceError(
                "Количество ресурса должно быть целым числом.",
                field="amount",
                value=amount,
                reason="invalid_amount_type",
                details={"service": SERVICE_NAME, "operation": operation},
            )
        if amount < 0 or (amount == 0 and not allow_zero):
            raise ValidationServiceError(
                "Количество ресурса должно быть больше нуля.",
                field="amount",
                value=amount,
                reason="invalid_amount",
                details={"service": SERVICE_NAME, "operation": operation},
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
        if limit < 1 or limit > MAX_PAGE_LIMIT:
            raise ValidationServiceError(
                f"limit должен быть от 1 до {MAX_PAGE_LIMIT}.",
                field="limit",
                value=limit,
                reason="invalid_limit",
                details={"service": SERVICE_NAME, "operation": "validate_pagination"},
            )

    @staticmethod
    def _invalid_resource_type(resource_type: Any) -> ValidationServiceError:
        return ValidationServiceError(
            "Тип ресурса квоты не поддерживается.",
            field="resource_type",
            value=str(resource_type),
            reason="invalid_resource_type",
            details={"service": SERVICE_NAME},
        )

    @staticmethod
    def _require_result(result: Any | None, *, operation: str) -> Any:
        if result is None:
            raise ServiceError(
                "Сервис квот не вернул результат операции.",
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

    async def _safe_log_quota_event(
        self,
        *,
        actor_id: UUID | None,
        user_id: UUID,
        action: AuditAction,
        entity_id: UUID | None,
        message: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        try:
            if actor_id is None:
                await self.audit_service.log_system_event(
                    action=action,
                    entity_type=AuditResourceType.QUOTA.value,
                    entity_id=entity_id,
                    resource_type=AuditResourceType.QUOTA,
                    message=message,
                    metadata={"target_user_id": str(user_id), **dict(metadata or {})},
                )
                return
            await self.audit_service.log_user_event(
                user_id=actor_id,
                action=action,
                entity_type=AuditResourceType.QUOTA.value,
                entity_id=entity_id,
                resource_type=AuditResourceType.QUOTA,
                message=message,
                metadata={"target_user_id": str(user_id), **dict(metadata or {})},
            )
        except Exception as exc:
            logger.warning(
                "Failed to write audit event for quotas service.",
                extra={
                    "action": action.value,
                    "entity_id": str(entity_id) if entity_id else None,
                    "actor_id": str(actor_id) if actor_id else None,
                    "target_user_id": str(user_id),
                    "error_type": exc.__class__.__name__,
                    "reason": str(exc),
                },
            )


def _quota_snapshot(quota: UserQuota) -> dict[str, Any]:
    storage_limit = int(quota.storage_limit_bytes)
    storage_used = int(quota.storage_used_bytes)
    available_storage = max(storage_limit - storage_used, 0)
    usage_percent = 100.0 if storage_limit <= 0 and storage_used > 0 else 0.0
    if storage_limit > 0:
        usage_percent = round(min((storage_used / storage_limit) * 100, 100.0), 2)

    return {
        "id": quota.id,
        "user_id": quota.user_id,
        "storage_limit_bytes": storage_limit,
        "storage_used_bytes": storage_used,
        "max_file_size_bytes": int(quota.max_file_size_bytes),
        "files_limit": quota.files_limit,
        "files_used": int(quota.files_used),
        "public_links_limit": quota.public_links_limit,
        "public_links_used": int(quota.public_links_used),
        "active_upload_sessions_limit": quota.active_upload_sessions_limit,
        "active_upload_sessions_used": int(quota.active_upload_sessions_used),
        "available_storage_bytes": available_storage,
        "usage_percent": usage_percent,
        "is_storage_full": storage_used >= storage_limit,
        "created_at": quota.created_at,
        "updated_at": quota.updated_at,
    }


def _quota_read(snapshot: Mapping[str, Any]) -> UserQuotaRead:
    return UserQuotaRead.model_validate(dict(snapshot))


def _usage_read(snapshot: Mapping[str, Any]) -> QuotaUsageRead:
    return QuotaUsageRead.model_validate(
        {
            "user_id": snapshot["user_id"],
            "storage_limit_bytes": snapshot["storage_limit_bytes"],
            "storage_used_bytes": snapshot["storage_used_bytes"],
            "max_file_size_bytes": snapshot["max_file_size_bytes"],
            "files_limit": snapshot["files_limit"],
            "files_used": snapshot["files_used"],
            "public_links_limit": snapshot["public_links_limit"],
            "public_links_used": snapshot["public_links_used"],
            "active_upload_sessions_limit": snapshot["active_upload_sessions_limit"],
            "active_upload_sessions_used": snapshot["active_upload_sessions_used"],
        }
    )


def _check_response(
    snapshot: Mapping[str, Any], resource_type: QuotaResourceType, requested_amount: int
) -> QuotaCheckResponse:
    limit, used = _resource_limit_and_used(snapshot, resource_type)
    if limit is None:
        return QuotaCheckResponse(
            allowed=True,
            user_id=snapshot["user_id"],
            resource_type=resource_type,
            requested_amount=requested_amount,
            limit=None,
            used=used,
            available=None,
            reason=None,
        )

    available = max(limit - used, 0)
    allowed = requested_amount <= available
    return QuotaCheckResponse(
        allowed=allowed,
        user_id=snapshot["user_id"],
        resource_type=resource_type,
        requested_amount=requested_amount,
        limit=limit,
        used=used,
        available=available,
        reason=None
        if allowed
        else "Запрошенный объем ресурса превышает доступную квоту.",
    )


def _resource_limit_and_used(
    snapshot: Mapping[str, Any], resource_type: QuotaResourceType
) -> tuple[int | None, int]:
    if resource_type == QuotaResourceType.STORAGE_BYTES:
        return int(snapshot["storage_limit_bytes"]), int(snapshot["storage_used_bytes"])
    if resource_type == QuotaResourceType.FILE_COUNT:
        return _optional_int(snapshot["files_limit"]), int(snapshot["files_used"])
    if resource_type == QuotaResourceType.PUBLIC_LINK_COUNT:
        return _optional_int(snapshot["public_links_limit"]), int(
            snapshot["public_links_used"]
        )
    if resource_type == QuotaResourceType.UPLOAD_SESSION_COUNT:
        return _optional_int(snapshot["active_upload_sessions_limit"]), int(
            snapshot["active_upload_sessions_used"]
        )
    raise ValidationServiceError(
        "Тип ресурса квоты не поддерживается.",
        field="resource_type",
        value=str(resource_type),
        reason="invalid_resource_type",
        details={"service": SERVICE_NAME},
    )


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _audit_quota(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(snapshot["id"]),
        "user_id": str(snapshot["user_id"]),
        "storage_limit_bytes": snapshot["storage_limit_bytes"],
        "storage_used_bytes": snapshot["storage_used_bytes"],
        "usage_percent": snapshot["usage_percent"],
        "max_file_size_bytes": snapshot["max_file_size_bytes"],
        "files_limit": snapshot["files_limit"],
        "files_used": snapshot["files_used"],
        "public_links_limit": snapshot["public_links_limit"],
        "public_links_used": snapshot["public_links_used"],
        "active_upload_sessions_limit": snapshot["active_upload_sessions_limit"],
        "active_upload_sessions_used": snapshot["active_upload_sessions_used"],
    }


def get_quotas_service(
    *,
    uow_factory: UnitOfWorkFactory | None = None,
    audit_service: AuditService | None = None,
) -> QuotasService:
    return QuotasService(uow_factory=uow_factory, audit_service=audit_service)


__all__ = [
    "QuotasService",
    "get_quotas_service",
]
