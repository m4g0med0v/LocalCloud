from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from core.logging import get_logger
from database import DatabaseError, UnitOfWorkFactory, create_unit_of_work_factory
from database.models.enums import (
    AuditAction,
    AuditResourceType,
    RegistrationRequestStatus,
    UserStatus,
)
from database.models.registration import RegistrationRequest
from schemas.common import PageMeta, PageResponse
from schemas.registration import (
    RegistrationApproveRequest,
    RegistrationCancelRequest,
    RegistrationDecisionResponse,
    RegistrationQueryParams,
    RegistrationRejectRequest,
    RegistrationRequestCreate,
    RegistrationRequestListItem,
    RegistrationRequestRead,
)
from security.password import hash_password, require_strong_password
from services.audit import AuditService, get_audit_service
from services.exceptions import (
    ConflictServiceError,
    ServiceError,
    ValidationServiceError,
    service_error_from_database,
    service_error_from_exception,
)

logger = get_logger("services.registration")

SERVICE_NAME = "registration"
MAX_PAGE_LIMIT = 1000
REPOSITORY_PAGE_LIMIT = 1000
REGISTRATION_SORT_FIELDS = {
    "created_at",
    "reviewed_at",
    "email",
    "username",
    "status",
}


class RegistrationService:
    """Business service for the moderated LocalCloud registration flow."""

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

    async def submit_request(
        self,
        data: RegistrationRequestCreate,
    ) -> RegistrationRequestRead:
        """Create a pending registration request after validating credentials."""

        operation = "submit_request"
        password_hash = self._hash_password(data.password)
        snapshot: dict[str, Any] = {}

        try:
            async with self.uow_factory() as uow:
                await self._ensure_identity_available(
                    email=str(data.email),
                    username=data.username,
                    operation=operation,
                    uow=uow,
                )

                request = await uow.registration_requests.create_request(
                    email=str(data.email),
                    username=data.username,
                    password_hash=password_hash,
                    status=RegistrationRequestStatus.PENDING,
                    flush=True,
                    refresh=True,
                    check_pending_duplicates=True,
                )

                snapshot = _registration_snapshot(request)
                await uow.commit()

            await self._safe_log_registration_event(
                actor_id=None,
                action=AuditAction.REGISTRATION_REQUEST_CREATED,
                entity_id=snapshot["id"],
                message="Registration request was created.",
                metadata={
                    "operation": operation,
                    "request": _audit_registration_request(snapshot),
                },
            )
            return _registration_read(snapshot)

        except ValueError as exc:
            raise ValidationServiceError(
                "Пароль заявки на регистрацию не прошёл проверку.",
                field="password",
                reason="invalid_password",
                details={"service": SERVICE_NAME, "operation": operation},
                cause=exc,
            ) from exc
        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось создать заявку на регистрацию.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при создании заявки на регистрацию.",
            ) from exc

    async def get_request(self, request_id: UUID) -> RegistrationRequestRead:
        operation = "get_request"
        result: RegistrationRequestRead | None = None

        try:
            async with self.uow_factory() as uow:
                request = await uow.registration_requests.get_required_request_by_id(
                    request_id,
                )
                result = _registration_read(_registration_snapshot(request))
            return self._require_result(result, operation=operation)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Заявка на регистрацию не найдена.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении заявки на регистрацию.",
            ) from exc

    async def list_requests(
        self,
        params: RegistrationQueryParams,
    ) -> PageResponse[RegistrationRequestListItem]:
        operation = "list_requests"
        self._validate_pagination(params.limit, params.offset, operation=operation)

        snapshots: list[dict[str, Any]] = []

        try:
            async with self.uow_factory() as uow:
                snapshots = await self._load_request_snapshots(
                    uow=uow,
                    params=params,
                )

            filtered_snapshots = self._filter_request_snapshots(snapshots, params)
            sorted_snapshots = self._sort_request_snapshots(
                filtered_snapshots,
                sort_by=params.sort_by,
                sort_desc=params.sort_desc,
            )
            total = len(sorted_snapshots)
            page_snapshots = sorted_snapshots[
                params.offset : params.offset + params.limit
            ]
            items = [_registration_list_item(snapshot) for snapshot in page_snapshots]

            return PageResponse[RegistrationRequestListItem](
                items=items,
                meta=PageMeta(
                    limit=params.limit,
                    offset=params.offset,
                    total=total,
                    count=len(items),
                ),
            )

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить список заявок на регистрацию.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении списка заявок.",
            ) from exc

    async def approve_request(
        self,
        request_id: UUID,
        data: RegistrationApproveRequest,
        *,
        reviewed_by: UUID,
    ) -> RegistrationDecisionResponse:
        """Approve a pending request and atomically create user, role and quota."""

        operation = "approve_request"
        snapshot: dict[str, Any] = {}
        created_user_id: UUID | None = None

        try:
            async with self.uow_factory() as uow:
                await uow.users.get_required_user_by_id(reviewed_by)
                request = await uow.registration_requests.get_required_request_by_id(
                    request_id,
                )
                await self._ensure_identity_available(
                    email=request.email,
                    username=request.username,
                    operation=operation,
                    uow=uow,
                )

                now = datetime.now(UTC)
                user = await uow.users.create_user(
                    email=request.email,
                    username=request.username,
                    password_hash=request.password_hash,
                    status=UserStatus.ACTIVE,
                    is_email_verified=data.is_email_verified,
                    approved_at=now,
                    flush=True,
                    refresh=True,
                    check_duplicates=True,
                )
                created_user_id = user.id

                role = await uow.roles.get_required_user_role_model()
                await uow.roles.assign_role(
                    user_id=user.id,
                    role_id=role.id,
                    assigned_by=reviewed_by,
                    flush=True,
                    refresh=False,
                    check_user_exists=False,
                    check_role_exists=False,
                    ignore_existing=True,
                )
                await uow.quotas.create_default_quota(
                    user_id=user.id,
                    flush=True,
                    refresh=False,
                    check_user_exists=False,
                    check_duplicate=True,
                )
                approved_request = await uow.registration_requests.approve_request(
                    request,
                    reviewed_by=reviewed_by,
                    created_user_id=user.id,
                    comment=data.comment,
                    reviewed_at=now,
                    flush=True,
                    refresh=True,
                    check_user_exists=False,
                    require_pending=True,
                )

                snapshot = _registration_snapshot(approved_request)
                await uow.commit()

            await self._safe_log_registration_event(
                actor_id=reviewed_by,
                action=AuditAction.REGISTRATION_REQUEST_APPROVED,
                entity_id=snapshot["id"],
                message="Registration request was approved.",
                metadata={
                    "operation": operation,
                    "created_user_id": str(created_user_id)
                    if created_user_id
                    else None,
                    "request": _audit_registration_request(snapshot),
                },
            )
            return _decision_response(snapshot, "Заявка на регистрацию одобрена.")

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось одобрить заявку на регистрацию.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при одобрении заявки на регистрацию.",
            ) from exc

    async def reject_request(
        self,
        request_id: UUID,
        data: RegistrationRejectRequest,
        *,
        reviewed_by: UUID,
    ) -> RegistrationDecisionResponse:
        operation = "reject_request"
        snapshot: dict[str, Any] = {}

        try:
            async with self.uow_factory() as uow:
                await uow.users.get_required_user_by_id(reviewed_by)
                request = await uow.registration_requests.get_required_request_by_id(
                    request_id,
                )
                rejected_request = await uow.registration_requests.reject_request(
                    request,
                    reviewed_by=reviewed_by,
                    reason=data.rejection_reason,
                    comment=data.comment,
                    reviewed_at=datetime.now(UTC),
                    flush=True,
                    refresh=True,
                    require_pending=True,
                )

                snapshot = _registration_snapshot(rejected_request)
                await uow.commit()

            await self._safe_log_registration_event(
                actor_id=reviewed_by,
                action=AuditAction.REGISTRATION_REQUEST_REJECTED,
                entity_id=snapshot["id"],
                message="Registration request was rejected.",
                metadata={
                    "operation": operation,
                    "request": _audit_registration_request(snapshot),
                },
            )
            return _decision_response(snapshot, "Заявка на регистрацию отклонена.")

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось отклонить заявку на регистрацию.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при отклонении заявки на регистрацию.",
            ) from exc

    async def cancel_request(
        self,
        request_id: UUID,
        data: RegistrationCancelRequest,
    ) -> RegistrationDecisionResponse:
        operation = "cancel_request"
        snapshot: dict[str, Any] = {}

        try:
            async with self.uow_factory() as uow:
                request = await uow.registration_requests.get_required_request_by_id(
                    request_id,
                )
                cancelled_request = await uow.registration_requests.cancel_request(
                    request,
                    comment=data.reason,
                    cancelled_at=datetime.now(UTC),
                    flush=True,
                    refresh=True,
                    require_pending=True,
                )

                snapshot = _registration_snapshot(cancelled_request)
                await uow.commit()

            await self._safe_log_registration_event(
                actor_id=None,
                action=AuditAction.REGISTRATION_REQUEST_CANCELLED,
                entity_id=snapshot["id"],
                message="Registration request was cancelled.",
                metadata={
                    "operation": operation,
                    "request": _audit_registration_request(snapshot),
                },
            )
            return _decision_response(snapshot, "Заявка на регистрацию отменена.")

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось отменить заявку на регистрацию.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при отмене заявки на регистрацию.",
            ) from exc

    async def count_pending(self) -> int:
        operation = "count_pending"
        result: int | None = None

        try:
            async with self.uow_factory() as uow:
                result = await uow.registration_requests.count_pending()
            return self._require_result(result, operation=operation)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось посчитать ожидающие заявки на регистрацию.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при подсчёте заявок.",
            ) from exc

    async def get_status_counts(self) -> dict[RegistrationRequestStatus, int]:
        operation = "get_status_counts"
        result: dict[RegistrationRequestStatus, int] | None = None

        try:
            async with self.uow_factory() as uow:
                result = await uow.registration_requests.get_status_counts()
            return self._require_result(result, operation=operation)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить статистику заявок на регистрацию.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении статистики заявок.",
            ) from exc

    async def has_pending_request(self, *, email: str, username: str) -> bool:
        operation = "has_pending_request"
        result: bool | None = None

        try:
            async with self.uow_factory() as uow:
                result = (
                    await uow.registration_requests.get_pending_by_email_or_username(
                        email=email,
                        username=username,
                    )
                    is not None
                )
            return self._require_result(result, operation=operation)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось проверить наличие ожидающей заявки.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при проверке ожидающей заявки.",
            ) from exc

    async def _ensure_identity_available(
        self,
        *,
        email: str,
        username: str,
        operation: str,
        uow: Any,
    ) -> None:
        if await uow.users.email_exists(email, include_deleted=False):
            raise ConflictServiceError(
                "Пользователь с таким email уже существует.",
                entity_name="User",
                field="email",
                value=email,
                reason="email_already_registered",
                details={"service": SERVICE_NAME, "operation": operation},
            )
        if await uow.users.username_exists(username, include_deleted=False):
            raise ConflictServiceError(
                "Пользователь с таким username уже существует.",
                entity_name="User",
                field="username",
                value=username,
                reason="username_already_registered",
                details={"service": SERVICE_NAME, "operation": operation},
            )

    async def _load_request_snapshots(
        self,
        *,
        uow: Any,
        params: RegistrationQueryParams,
    ) -> list[dict[str, Any]]:
        statuses = [params.status] if params.status is not None else None
        snapshots: list[dict[str, Any]] = []
        offset = 0

        while True:
            if params.query:
                requests = await uow.registration_requests.search_requests(
                    params.query,
                    offset=offset,
                    limit=REPOSITORY_PAGE_LIMIT,
                    statuses=statuses,
                )
            else:
                requests = await uow.registration_requests.list_requests(
                    offset=offset,
                    limit=REPOSITORY_PAGE_LIMIT,
                    statuses=statuses,
                    reviewed_by=params.reviewed_by,
                    order_by_created_desc=True,
                )

            snapshots.extend(_registration_snapshot(request) for request in requests)
            if len(requests) < REPOSITORY_PAGE_LIMIT:
                break
            offset += REPOSITORY_PAGE_LIMIT

        return snapshots

    @staticmethod
    def _filter_request_snapshots(
        snapshots: list[dict[str, Any]],
        params: RegistrationQueryParams,
    ) -> list[dict[str, Any]]:
        return [
            snapshot
            for snapshot in snapshots
            if _matches_registration_filters(snapshot, params)
        ]

    @staticmethod
    def _sort_request_snapshots(
        snapshots: list[dict[str, Any]],
        *,
        sort_by: str,
        sort_desc: bool,
    ) -> list[dict[str, Any]]:
        normalized_sort_by = sort_by.strip().lower()
        if normalized_sort_by not in REGISTRATION_SORT_FIELDS:
            normalized_sort_by = "created_at"

        return sorted(
            snapshots,
            key=lambda item: (
                item.get(normalized_sort_by) is None,
                item.get(normalized_sort_by),
            ),
            reverse=sort_desc,
        )

    @staticmethod
    def _hash_password(password: str) -> str:
        require_strong_password(password)
        return hash_password(password)

    @staticmethod
    def _validate_pagination(limit: int, offset: int, *, operation: str) -> None:
        if limit < 1 or limit > MAX_PAGE_LIMIT:
            raise ValidationServiceError(
                "Некорректный размер страницы списка заявок.",
                field="limit",
                value=limit,
                reason="invalid_limit",
                details={"service": SERVICE_NAME, "operation": operation},
            )
        if offset < 0:
            raise ValidationServiceError(
                "Смещение списка заявок не может быть отрицательным.",
                field="offset",
                value=offset,
                reason="invalid_offset",
                details={"service": SERVICE_NAME, "operation": operation},
            )

    @staticmethod
    def _require_result(result: Any | None, *, operation: str) -> Any:
        if result is None:
            raise ServiceError(
                "Сервис регистрации не вернул результат операции.",
                service=SERVICE_NAME,
                operation=operation,
            )
        return result

    @staticmethod
    def _database_error(
        exc: DatabaseError, *, operation: str, message: str
    ) -> ServiceError:
        return service_error_from_database(
            exc,
            operation=operation,
            message=message,
            service=SERVICE_NAME,
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
            exc,
            operation=operation,
            message=message,
            service=SERVICE_NAME,
        )

    async def _safe_log_registration_event(
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
                    entity_type=AuditResourceType.REGISTRATION_REQUEST.value,
                    entity_id=entity_id,
                    resource_type=AuditResourceType.REGISTRATION_REQUEST,
                    message=message,
                    metadata=metadata,
                )
                return

            await self.audit_service.log_user_event(
                user_id=actor_id,
                action=action,
                entity_type=AuditResourceType.REGISTRATION_REQUEST.value,
                entity_id=entity_id,
                resource_type=AuditResourceType.REGISTRATION_REQUEST,
                message=message,
                metadata=metadata,
            )
        except Exception as exc:
            logger.warning(
                "Failed to write audit event for registration service.",
                extra={
                    "action": action.value,
                    "entity_id": str(entity_id) if entity_id else None,
                    "actor_id": str(actor_id) if actor_id else None,
                    "error_type": exc.__class__.__name__,
                    "reason": str(exc),
                },
            )


def _registration_snapshot(request: RegistrationRequest) -> dict[str, Any]:
    return {
        "id": request.id,
        "email": request.email,
        "username": request.username,
        "status": request.status,
        "comment": request.comment,
        "rejection_reason": request.rejection_reason,
        "reviewed_at": request.reviewed_at,
        "reviewed_by": request.reviewed_by,
        "created_user_id": request.created_user_id,
        "created_at": request.created_at,
    }


def _registration_read(snapshot: Mapping[str, Any]) -> RegistrationRequestRead:
    return RegistrationRequestRead.model_validate(dict(snapshot))


def _registration_list_item(
    snapshot: Mapping[str, Any],
) -> RegistrationRequestListItem:
    return RegistrationRequestListItem.model_validate(dict(snapshot))


def _decision_response(
    snapshot: Mapping[str, Any],
    message: str,
) -> RegistrationDecisionResponse:
    return RegistrationDecisionResponse(
        request=_registration_read(snapshot),
        created_user_id=snapshot.get("created_user_id"),
        message=message,
    )


def _audit_registration_request(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(snapshot["id"]),
        "email": snapshot["email"],
        "username": snapshot["username"],
        "status": _enum_or_value(snapshot["status"]),
        "reviewed_by": _optional_uuid(snapshot.get("reviewed_by")),
        "created_user_id": _optional_uuid(snapshot.get("created_user_id")),
    }


def _matches_registration_filters(
    snapshot: Mapping[str, Any],
    params: RegistrationQueryParams,
) -> bool:
    if (
        params.reviewed_by is not None
        and snapshot.get("reviewed_by") != params.reviewed_by
    ):
        return False

    created_at = snapshot.get("created_at")
    if not _matches_datetime_range(
        created_at,
        from_value=params.created_from,
        to_value=params.created_to,
    ):
        return False

    reviewed_at = snapshot.get("reviewed_at")
    if not _matches_datetime_range(
        reviewed_at,
        from_value=params.reviewed_from,
        to_value=params.reviewed_to,
    ):
        return False

    return True


def _matches_datetime_range(
    value: Any,
    *,
    from_value: datetime | None,
    to_value: datetime | None,
) -> bool:
    if from_value is None and to_value is None:
        return True
    if not isinstance(value, datetime):
        return False

    comparable_value = _normalize_datetime(value)
    if from_value is not None and comparable_value < _normalize_datetime(from_value):
        return False
    if to_value is not None and comparable_value > _normalize_datetime(to_value):
        return False
    return True


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _optional_uuid(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _enum_or_value(value: Any) -> Any:
    return getattr(value, "value", value)


def get_registration_service(
    *,
    uow_factory: UnitOfWorkFactory | None = None,
    audit_service: AuditService | None = None,
) -> RegistrationService:
    return RegistrationService(
        uow_factory=uow_factory,
        audit_service=audit_service,
    )


__all__ = [
    "RegistrationService",
    "get_registration_service",
]
