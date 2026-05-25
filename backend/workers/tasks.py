from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from workers.exceptions import WorkerTaskHandlerError
from workers.types import WorkerTaskExecutionContext, WorkerTaskExecutionResult


def success_result(
    result_data: dict[str, Any] | None = None,
    progress_percent: int = 100,
) -> WorkerTaskExecutionResult:
    """Создаёт успешный результат выполнения задачи."""

    return WorkerTaskExecutionResult(
        success=True,
        progress_percent=progress_percent,
        result_data=None if result_data is None else cast_dict_jsonable(result_data),
        retry=False,
    )


def failure_result(
    error_message: str,
    error_code: str | None = None,
    result_data: dict[str, Any] | None = None,
    retry: bool = False,
    progress_percent: int = 0,
) -> WorkerTaskExecutionResult:
    """Создаёт результат неуспешного выполнения задачи."""

    return WorkerTaskExecutionResult(
        success=False,
        progress_percent=progress_percent,
        result_data=None if result_data is None else cast_dict_jsonable(result_data),
        error_message=error_message,
        error_code=error_code,
        retry=retry,
    )


def retry_result(
    error_message: str,
    error_code: str | None = None,
    result_data: dict[str, Any] | None = None,
) -> WorkerTaskExecutionResult:
    """Создаёт результат с признаком повторной попытки."""

    return failure_result(
        error_message=error_message,
        error_code=error_code,
        result_data=result_data,
        retry=True,
        progress_percent=0,
    )


async def unsupported_task_handler(
    context: WorkerTaskExecutionContext,
) -> WorkerTaskExecutionResult:
    """Обработчик неподдерживаемого типа фоновой задачи."""

    return failure_result(
        error_message=f"Тип задачи '{context.task_type.value}' пока не поддерживается.",
        error_code="not_implemented",
        result_data={
            "task_id": str(context.task_id),
            "task_type": context.task_type.value,
            "worker_id": context.worker_id,
        },
        retry=False,
        progress_percent=0,
    )


def require_payload_value(
    payload: Mapping[str, Any],
    key: str,
    expected_type: type[Any] | tuple[type[Any], ...] | None = None,
) -> Any:
    """Возвращает обязательное значение из payload и проверяет тип."""

    if key not in payload:
        raise WorkerTaskHandlerError(
            "В payload отсутствует обязательное поле.",
            operation="require_payload_value",
            details={"key": key},
        )
    value = payload[key]
    if expected_type is not None and not isinstance(value, expected_type):
        raise WorkerTaskHandlerError(
            "Поле payload имеет некорректный тип.",
            operation="require_payload_value",
            details={
                "key": key,
                "expected_type": _type_name(expected_type),
                "actual_type": type(value).__name__,
            },
        )
    return value


def optional_payload_value(
    payload: Mapping[str, Any],
    key: str,
    expected_type: type[Any] | tuple[type[Any], ...] | None = None,
    default: Any = None,
) -> Any:
    """Возвращает необязательное значение из payload и проверяет тип."""

    if key not in payload or payload[key] is None:
        return default
    value = payload[key]
    if expected_type is not None and not isinstance(value, expected_type):
        raise WorkerTaskHandlerError(
            "Поле payload имеет некорректный тип.",
            operation="optional_payload_value",
            details={
                "key": key,
                "expected_type": _type_name(expected_type),
                "actual_type": type(value).__name__,
            },
        )
    return value


def payload_uuid(payload: Mapping[str, Any], key: str) -> UUID:
    """Читает UUID из payload."""

    value = require_payload_value(payload, key)
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError as exc:
            raise WorkerTaskHandlerError(
                "Поле payload содержит некорректный UUID.",
                operation="payload_uuid",
                details={"key": key, "value": value},
                cause=exc,
            ) from exc
    raise WorkerTaskHandlerError(
        "Поле payload должно быть UUID или строкой UUID.",
        operation="payload_uuid",
        details={"key": key, "actual_type": type(value).__name__},
    )


def payload_datetime(payload: Mapping[str, Any], key: str) -> datetime:
    """Читает datetime из payload."""

    value = require_payload_value(payload, key)
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise WorkerTaskHandlerError(
                "Поле payload содержит некорректный datetime в ISO-формате.",
                operation="payload_datetime",
                details={"key": key, "value": value},
                cause=exc,
            ) from exc
    raise WorkerTaskHandlerError(
        "Поле payload должно быть datetime или ISO-строкой.",
        operation="payload_datetime",
        details={"key": key, "actual_type": type(value).__name__},
    )


def payload_int(
    payload: Mapping[str, Any],
    key: str,
    default: int | None = None,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int | None:
    """Читает целое число из payload с проверкой диапазона."""

    value = optional_payload_value(payload, key, default=default)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise WorkerTaskHandlerError(
            "Поле payload должно быть целым числом.",
            operation="payload_int",
            details={"key": key, "actual_type": type(value).__name__},
        )
    if min_value is not None and value < min_value:
        raise WorkerTaskHandlerError(
            "Значение поля payload меньше минимально допустимого.",
            operation="payload_int",
            details={"key": key, "value": value, "min_value": min_value},
        )
    if max_value is not None and value > max_value:
        raise WorkerTaskHandlerError(
            "Значение поля payload больше максимально допустимого.",
            operation="payload_int",
            details={"key": key, "value": value, "max_value": max_value},
        )
    return value


def jsonable(value: Any) -> Any:
    """Преобразует значение в JSON-совместимый формат."""

    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, Iterable):
        return [jsonable(item) for item in value]
    return str(value)


def cast_dict_jsonable(data: Mapping[str, Any]) -> dict[str, Any]:
    """Нормализует словарь к JSON-совместимому виду."""

    return {str(key): jsonable(value) for key, value in data.items()}


def _type_name(expected_type: type[Any] | tuple[type[Any], ...]) -> str:
    if isinstance(expected_type, tuple):
        return " | ".join(item.__name__ for item in expected_type)
    return expected_type.__name__


__all__ = [
    "success_result",
    "failure_result",
    "retry_result",
    "unsupported_task_handler",
    "require_payload_value",
    "optional_payload_value",
    "payload_uuid",
    "payload_datetime",
    "payload_int",
    "jsonable",
]
