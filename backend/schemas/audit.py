from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, ConfigDict, Field, ValidationInfo, field_validator

from database.models.enums import AuditAction, AuditResourceType, AuditResult
from schemas.common import BaseSchema, PaginationParams


class AuditLogRead(BaseSchema):
    """Полное представление события аудита."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор события аудита.",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, выполнившего действие. None означает системное действие.",
    )
    action: AuditAction = Field(
        ...,
        description="Тип действия, выполненного в системе.",
    )
    result: AuditResult = Field(
        ...,
        description="Результат выполнения действия.",
    )
    entity_type: str | None = Field(
        default=None,
        max_length=128,
        description="Тип сущности, затронутой действием.",
    )
    entity_id: UUID | None = Field(
        default=None,
        description="Идентификатор затронутой сущности.",
    )
    resource_type: AuditResourceType | None = Field(
        default=None,
        description="Нормализованный тип ресурса для фильтрации событий аудита.",
    )
    request_id: str | None = Field(
        default=None,
        max_length=128,
        description="Идентификатор HTTP-запроса, в рамках которого создано событие.",
    )
    correlation_id: str | None = Field(
        default=None,
        max_length=128,
        description="Идентификатор корреляции для связывания нескольких событий.",
    )
    ip_address: str | None = Field(
        default=None,
        description="IP-адрес, с которого было выполнено действие.",
    )
    user_agent: str | None = Field(
        default=None,
        description="User-Agent клиента, выполнившего действие.",
    )
    message: str | None = Field(
        default=None,
        description="Краткое человекочитаемое описание события.",
    )
    error_code: str | None = Field(
        default=None,
        max_length=128,
        description="Машиночитаемый код ошибки, если действие завершилось неуспешно.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata", "metadata_"),
        serialization_alias="metadata",
        description="Дополнительные структурированные данные события аудита.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания события аудита.",
    )


class AuditLogListItem(BaseSchema):
    """Краткое представление события аудита для списков."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор события аудита.",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, выполнившего действие. None означает системное действие.",
    )
    action: AuditAction = Field(
        ...,
        description="Тип действия, выполненного в системе.",
    )
    result: AuditResult = Field(
        ...,
        description="Результат выполнения действия.",
    )
    entity_type: str | None = Field(
        default=None,
        max_length=128,
        description="Тип сущности, затронутой действием.",
    )
    entity_id: UUID | None = Field(
        default=None,
        description="Идентификатор затронутой сущности.",
    )
    resource_type: AuditResourceType | None = Field(
        default=None,
        description="Нормализованный тип ресурса.",
    )
    request_id: str | None = Field(
        default=None,
        max_length=128,
        description="Идентификатор HTTP-запроса.",
    )
    correlation_id: str | None = Field(
        default=None,
        max_length=128,
        description="Идентификатор корреляции.",
    )
    ip_address: str | None = Field(
        default=None,
        description="IP-адрес, с которого было выполнено действие.",
    )
    message: str | None = Field(
        default=None,
        description="Краткое описание события.",
    )
    error_code: str | None = Field(
        default=None,
        max_length=128,
        description="Машиночитаемый код ошибки.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания события аудита.",
    )


class AuditLogCreate(BaseSchema):
    """DTO для создания события аудита сервисным слоем."""

    user_id: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, выполнившего действие. None означает системное действие.",
    )
    action: AuditAction = Field(
        ...,
        description="Тип действия, выполненного в системе.",
    )
    result: AuditResult = Field(
        default=AuditResult.SUCCESS,
        description="Результат выполнения действия.",
    )
    entity_type: str | None = Field(
        default=None,
        max_length=128,
        description="Тип сущности, затронутой действием.",
    )
    entity_id: UUID | None = Field(
        default=None,
        description="Идентификатор затронутой сущности.",
    )
    resource_type: AuditResourceType | None = Field(
        default=None,
        description="Нормализованный тип ресурса для фильтрации событий аудита.",
    )
    request_id: str | None = Field(
        default=None,
        max_length=128,
        description="Идентификатор HTTP-запроса.",
    )
    correlation_id: str | None = Field(
        default=None,
        max_length=128,
        description="Идентификатор корреляции.",
    )
    ip_address: str | None = Field(
        default=None,
        description="IP-адрес, с которого было выполнено действие.",
    )
    user_agent: str | None = Field(
        default=None,
        description="User-Agent клиента, выполнившего действие.",
    )
    message: str | None = Field(
        default=None,
        description="Краткое человекочитаемое описание события.",
    )
    error_code: str | None = Field(
        default=None,
        max_length=128,
        description="Машиночитаемый код ошибки.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata", "metadata_"),
        serialization_alias="metadata",
        description="Дополнительные структурированные данные события аудита.",
    )

    @field_validator(
        "entity_type",
        "request_id",
        "correlation_id",
        "ip_address",
        "user_agent",
        "message",
        "error_code",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class AuditQueryParams(PaginationParams):
    """Параметры фильтрации журнала аудита."""

    user_id: UUID | None = Field(
        default=None,
        description="Фильтр по пользователю, выполнившему действие.",
    )
    action: AuditAction | None = Field(
        default=None,
        description="Фильтр по типу действия.",
    )
    result: AuditResult | None = Field(
        default=None,
        description="Фильтр по результату выполнения действия.",
    )
    resource_type: AuditResourceType | None = Field(
        default=None,
        description="Фильтр по нормализованному типу ресурса.",
    )
    entity_type: str | None = Field(
        default=None,
        max_length=128,
        description="Фильтр по типу затронутой сущности.",
    )
    entity_id: UUID | None = Field(
        default=None,
        description="Фильтр по идентификатору затронутой сущности.",
    )
    request_id: str | None = Field(
        default=None,
        max_length=128,
        description="Фильтр по идентификатору HTTP-запроса.",
    )
    correlation_id: str | None = Field(
        default=None,
        max_length=128,
        description="Фильтр по идентификатору корреляции.",
    )
    ip_address: str | None = Field(
        default=None,
        description="Фильтр по IP-адресу клиента.",
    )
    created_from: datetime | None = Field(
        default=None,
        description="Фильтр по дате создания события: начало диапазона включительно.",
    )
    created_to: datetime | None = Field(
        default=None,
        description="Фильтр по дате создания события: конец диапазона включительно.",
    )
    query: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Поисковая строка по сообщению, коду ошибки, request_id или correlation_id.",
    )
    sort_by: str = Field(
        default="created_at",
        min_length=1,
        max_length=64,
        description="Поле сортировки.",
        examples=["created_at", "action", "result", "resource_type"],
    )
    sort_desc: bool = Field(
        default=True,
        description="Сортировать по убыванию.",
    )

    @field_validator(
        "entity_type",
        "request_id",
        "correlation_id",
        "ip_address",
        "query",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("created_to")
    @classmethod
    def validate_created_range(
        cls,
        value: datetime | None,
        info: ValidationInfo,
    ) -> datetime | None:
        created_from = info.data.get("created_from")

        if created_from is not None and value is not None and value < created_from:
            raise ValueError("created_to не может быть раньше created_from.")

        return value


class AuditExportRequest(BaseSchema):
    """Запрос на экспорт журнала аудита."""

    user_id: UUID | None = Field(
        default=None,
        description="Фильтр экспорта по пользователю.",
    )
    action: AuditAction | None = Field(
        default=None,
        description="Фильтр экспорта по типу действия.",
    )
    result: AuditResult | None = Field(
        default=None,
        description="Фильтр экспорта по результату действия.",
    )
    resource_type: AuditResourceType | None = Field(
        default=None,
        description="Фильтр экспорта по типу ресурса.",
    )
    entity_type: str | None = Field(
        default=None,
        max_length=128,
        description="Фильтр экспорта по типу сущности.",
    )
    entity_id: UUID | None = Field(
        default=None,
        description="Фильтр экспорта по идентификатору сущности.",
    )
    request_id: str | None = Field(
        default=None,
        max_length=128,
        description="Фильтр экспорта по идентификатору HTTP-запроса.",
    )
    correlation_id: str | None = Field(
        default=None,
        max_length=128,
        description="Фильтр экспорта по идентификатору корреляции.",
    )
    created_from: datetime | None = Field(
        default=None,
        description="Начало периода экспорта включительно.",
    )
    created_to: datetime | None = Field(
        default=None,
        description="Конец периода экспорта включительно.",
    )
    format: str = Field(
        default="json",
        min_length=1,
        max_length=16,
        description="Формат экспорта журнала аудита.",
        examples=["json", "csv"],
    )
    include_metadata: bool = Field(
        default=True,
        description="Включать ли metadata событий в экспорт.",
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        le=100_000,
        description="Максимальное количество событий для экспорта.",
    )

    @field_validator(
        "entity_type",
        "request_id",
        "correlation_id",
        "format",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("format")
    @classmethod
    def validate_format(cls, value: str) -> str:
        normalized_value = value.strip().lower()

        if normalized_value not in {"json", "csv"}:
            raise ValueError("format должен быть json или csv.")

        return normalized_value

    @field_validator("created_to")
    @classmethod
    def validate_created_range(
        cls,
        value: datetime | None,
        info: ValidationInfo,
    ) -> datetime | None:
        created_from = info.data.get("created_from")

        if created_from is not None and value is not None and value < created_from:
            raise ValueError("created_to не может быть раньше created_from.")

        return value


class AuditSummaryRead(BaseSchema):
    """Сводка по событиям аудита."""

    total_count: int = Field(
        ...,
        ge=0,
        description="Общее количество событий аудита в выборке.",
    )
    success_count: int = Field(
        default=0,
        ge=0,
        description="Количество успешных событий.",
    )
    failure_count: int = Field(
        default=0,
        ge=0,
        description="Количество событий с ошибкой.",
    )
    denied_count: int = Field(
        default=0,
        ge=0,
        description="Количество событий с отказом в доступе.",
    )
    warning_count: int = Field(
        default=0,
        ge=0,
        description="Количество предупреждений.",
    )
    by_action: dict[AuditAction, int] = Field(
        default_factory=dict,
        description="Количество событий по типам действий.",
    )
    by_resource_type: dict[AuditResourceType, int] = Field(
        default_factory=dict,
        description="Количество событий по типам ресурсов.",
    )
    by_result: dict[AuditResult, int] = Field(
        default_factory=dict,
        description="Количество событий по результатам выполнения.",
    )
    period_from: datetime | None = Field(
        default=None,
        description="Начало периода, по которому построена сводка.",
    )
    period_to: datetime | None = Field(
        default=None,
        description="Конец периода, по которому построена сводка.",
    )
