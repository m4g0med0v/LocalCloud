from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from database.models.enums import HealthStatus
from schemas.common import BaseSchema


def normalize_health_status(value: HealthStatus | str) -> HealthStatus:
    """Нормализует внутренние health-статусы к публичному HealthStatus."""

    if isinstance(value, HealthStatus):
        return value

    normalized_value = str(value).strip().lower()

    if normalized_value in {"ok", "healthy", "success", "available"}:
        return HealthStatus.OK

    if normalized_value in {"degraded", "warning", "slow"}:
        return HealthStatus.DEGRADED

    if normalized_value in {"unavailable", "unhealthy", "failed", "failure", "error"}:
        return HealthStatus.UNAVAILABLE

    raise ValueError(
        "Недопустимый health status. Ожидается ok, degraded, unavailable "
        "или совместимый внутренний статус."
    )


class ComponentHealthRead(BaseSchema):
    """Универсальное состояние отдельного компонента системы."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    component: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Название проверяемого компонента.",
        examples=["application", "database", "storage"],
    )
    status: HealthStatus = Field(
        ...,
        description="Публичный статус работоспособности компонента.",
    )
    connection: bool | None = Field(
        default=None,
        description="Доступно ли подключение к компоненту, если это применимо.",
    )
    latency_ms: float | None = Field(
        default=None,
        ge=0,
        description="Задержка проверки компонента в миллисекундах.",
    )
    latency_threshold_ms: float | None = Field(
        default=None,
        gt=0,
        description="Порог допустимой задержки в миллисекундах.",
    )
    error: str | None = Field(
        default=None,
        max_length=255,
        description="Машиночитаемый тип ошибки, если проверка завершилась неуспешно.",
    )
    message: str | None = Field(
        default=None,
        description="Человекочитаемое сообщение о состоянии компонента.",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Дополнительные структурированные детали проверки.",
    )
    checked_at: datetime | None = Field(
        default=None,
        description="Дата и время проверки компонента.",
    )

    @field_validator("component", "error", "message")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: HealthStatus | str) -> HealthStatus:
        return normalize_health_status(value)


class DatabaseHealthRead(ComponentHealthRead):
    """Состояние подключения к PostgreSQL."""

    component: str = Field(
        default="database",
        description="Название проверяемого компонента.",
    )
    connection: bool | None = Field(
        default=None,
        description="Доступно ли подключение к базе данных.",
    )


class StorageHealthRead(BaseSchema):
    """Состояние подключения к объектному хранилищу."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    component: str = Field(
        default="storage",
        min_length=1,
        max_length=128,
        description="Название проверяемого компонента.",
    )
    status: HealthStatus = Field(
        ...,
        description="Публичный статус работоспособности объектного хранилища.",
    )
    checked_at: datetime | None = Field(
        default=None,
        description="Дата и время проверки объектного хранилища.",
    )
    connection_ok: bool = Field(
        ...,
        description="Доступно ли подключение к объектному хранилищу.",
    )
    bucket_access_ok: bool | None = Field(
        default=None,
        description="Доступен ли проверяемый bucket.",
    )
    read_write_ok: bool | None = Field(
        default=None,
        description="Успешна ли проверка чтения/записи.",
    )
    latency_ms: float | None = Field(
        default=None,
        ge=0,
        description="Задержка проверки объектного хранилища в миллисекундах.",
    )
    latency_threshold_ms: float | None = Field(
        default=None,
        gt=0,
        description="Порог допустимой задержки объектного хранилища в миллисекундах.",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Дополнительные структурированные детали проверки.",
    )

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: HealthStatus | str) -> HealthStatus:
        return normalize_health_status(value)

    @model_validator(mode="before")
    @classmethod
    def support_storage_health_status_shape(cls, data: Any) -> Any:
        """
        Поддерживает объект storage.types.StorageHealthStatus.

        В storage DTO статус называется state, а в публичной API-схеме — status.
        """
        if not isinstance(data, dict):
            state = getattr(data, "state", None)
            if state is not None:
                return {
                    "component": "storage",
                    "status": state,
                    "checked_at": getattr(data, "checked_at", None),
                    "connection_ok": getattr(data, "connection_ok", False),
                    "bucket_access_ok": getattr(data, "bucket_access_ok", None),
                    "read_write_ok": getattr(data, "read_write_ok", None),
                    "latency_ms": getattr(data, "latency_ms", None),
                    "latency_threshold_ms": getattr(data, "latency_threshold_ms", None),
                    "details": getattr(data, "details", None),
                }

            return data

        if "status" not in data and "state" in data:
            normalized_data = dict(data)
            normalized_data["status"] = normalized_data.pop("state")
            normalized_data.setdefault("component", "storage")
            return normalized_data

        return data


class ApplicationHealthRead(BaseSchema):
    """Состояние самого backend-приложения."""

    component: str = Field(
        default="application",
        description="Название проверяемого компонента.",
    )
    status: HealthStatus = Field(
        default=HealthStatus.OK,
        description="Публичный статус работоспособности приложения.",
    )
    app_name: str = Field(
        ...,
        min_length=1,
        description="Название приложения.",
        examples=["LocalCloud"],
    )
    app_version: str = Field(
        ...,
        min_length=1,
        description="Версия приложения.",
        examples=["0.1.0"],
    )
    debug: bool | None = Field(
        default=None,
        description="Запущено ли приложение в debug-режиме.",
    )
    uptime_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Время работы приложения в секундах, если известно.",
    )
    checked_at: datetime = Field(
        ...,
        description="Дата и время проверки приложения.",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Дополнительные сведения о состоянии приложения.",
    )

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: HealthStatus | str) -> HealthStatus:
        return normalize_health_status(value)


class HealthCheckResponse(BaseSchema):
    """Полный ответ health-check endpoint."""

    app_name: str = Field(
        ...,
        min_length=1,
        description="Название приложения.",
        examples=["LocalCloud"],
    )
    app_version: str = Field(
        ...,
        min_length=1,
        description="Версия приложения.",
        examples=["0.1.0"],
    )
    status: HealthStatus = Field(
        ...,
        description="Итоговый статус работоспособности системы.",
    )
    checked_at: datetime = Field(
        ...,
        description="Дата и время выполнения общей проверки.",
    )
    application: ApplicationHealthRead | None = Field(
        default=None,
        description="Состояние backend-приложения.",
    )
    database: DatabaseHealthRead | None = Field(
        default=None,
        description="Состояние подключения к базе данных.",
    )
    storage: StorageHealthRead | None = Field(
        default=None,
        description="Состояние объектного хранилища.",
    )
    components: list[ComponentHealthRead] = Field(
        default_factory=list,
        description="Дополнительные компоненты, участвующие в health-check.",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Дополнительные сведения о результате проверки.",
    )

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: HealthStatus | str) -> HealthStatus:
        return normalize_health_status(value)


class ReadinessResponse(BaseSchema):
    """Ответ проверки готовности приложения принимать пользовательские запросы."""

    app_name: str = Field(
        ...,
        min_length=1,
        description="Название приложения.",
        examples=["LocalCloud"],
    )
    app_version: str = Field(
        ...,
        min_length=1,
        description="Версия приложения.",
        examples=["0.1.0"],
    )
    status: HealthStatus = Field(
        ...,
        description="Статус готовности приложения.",
    )
    ready: bool = Field(
        ...,
        description="Готово ли приложение принимать пользовательские запросы.",
    )
    checked_at: datetime = Field(
        ...,
        description="Дата и время проверки готовности.",
    )
    database: DatabaseHealthRead | None = Field(
        default=None,
        description="Состояние базы данных, если проверка выполнялась.",
    )
    storage: StorageHealthRead | None = Field(
        default=None,
        description="Состояние объектного хранилища, если проверка выполнялась.",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Дополнительные сведения о готовности приложения.",
    )

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: HealthStatus | str) -> HealthStatus:
        return normalize_health_status(value)


class LivenessResponse(BaseSchema):
    """Ответ проверки жизнеспособности backend-процесса."""

    app_name: str = Field(
        ...,
        min_length=1,
        description="Название приложения.",
        examples=["LocalCloud"],
    )
    app_version: str = Field(
        ...,
        min_length=1,
        description="Версия приложения.",
        examples=["0.1.0"],
    )
    status: HealthStatus = Field(
        ...,
        description="Статус жизнеспособности приложения.",
    )
    alive: bool = Field(
        ...,
        description="Работает ли backend-процесс.",
    )
    checked_at: datetime = Field(
        ...,
        description="Дата и время проверки жизнеспособности.",
    )
    uptime_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Время работы приложения в секундах, если известно.",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Дополнительные сведения о жизнеспособности приложения.",
    )

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: HealthStatus | str) -> HealthStatus:
        return normalize_health_status(value)
