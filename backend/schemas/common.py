from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

T = TypeVar("T")


class BaseSchema(BaseModel):
    """
    Базовая схема API.

    Используется как общий родитель для DTO, которые могут создаваться
    из ORM-объектов SQLAlchemy через Pydantic v2.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class UUIDSchema(BaseSchema):
    """Базовая схема сущности с UUID-идентификатором."""

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор сущности.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class CreatedAtSchema(BaseSchema):
    """Базовая схема сущности с датой создания."""

    created_at: datetime = Field(
        ...,
        description="Дата и время создания сущности.",
    )


class TimestampedSchema(CreatedAtSchema):
    """Базовая схема сущности с датой создания и обновления."""

    updated_at: datetime = Field(
        ...,
        description="Дата и время последнего обновления сущности.",
    )


class SoftDeleteSchema(BaseSchema):
    """Базовая схема сущности с поддержкой логического удаления."""

    is_deleted: bool = Field(
        default=False,
        description="Признак логического удаления сущности.",
    )
    deleted_at: datetime | None = Field(
        default=None,
        description="Дата и время логического удаления сущности.",
    )


class MessageResponse(BaseSchema):
    """Универсальный ответ с текстовым сообщением."""

    message: str = Field(
        ...,
        min_length=1,
        description="Человекочитаемое сообщение о результате операции.",
        examples=["Операция выполнена успешно."],
    )


class StatusResponse(MessageResponse):
    """Универсальный ответ со статусом выполнения операции."""

    success: bool = Field(
        ...,
        description="Признак успешного выполнения операции.",
    )
    status: str | None = Field(
        default=None,
        description="Машиночитаемый статус операции.",
        examples=["ok", "created", "updated", "deleted"],
    )


class ErrorDetail(BaseSchema):
    """Описание одной ошибки или причины отказа."""

    code: str | None = Field(
        default=None,
        description="Машиночитаемый код ошибки.",
        examples=["entity_not_found", "validation_error"],
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Человекочитаемое описание ошибки.",
    )
    field: str | None = Field(
        default=None,
        description="Поле, с которым связана ошибка, если применимо.",
        examples=["email", "password", "node_id"],
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Дополнительные структурированные сведения об ошибке.",
    )


class ErrorResponse(BaseSchema):
    """Универсальный ответ API при ошибке."""

    success: bool = Field(
        default=False,
        description="Признак успешности операции. Для ошибки всегда false.",
    )
    error: str = Field(
        ...,
        min_length=1,
        description="Краткое машинное имя ошибки или тип исключения.",
        examples=["EntityNotFoundError", "ValidationError"],
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Человекочитаемое сообщение об ошибке.",
    )
    details: dict[str, Any] | list[ErrorDetail] | None = Field(
        default=None,
        description="Дополнительные сведения об ошибке.",
    )
    request_id: str | None = Field(
        default=None,
        description="Идентификатор HTTP-запроса для трассировки ошибки.",
    )


class ValidationErrorItem(BaseSchema):
    """Описание ошибки валидации отдельного поля."""

    field: str = Field(
        ...,
        min_length=1,
        description="Имя поля или путь к полю, в котором обнаружена ошибка.",
        examples=["body.email", "query.limit"],
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Описание ошибки валидации.",
    )
    code: str | None = Field(
        default=None,
        description="Машиночитаемый код ошибки валидации.",
        examples=["string_too_short", "greater_than_equal"],
    )
    value: Any | None = Field(
        default=None,
        description="Переданное значение, вызвавшее ошибку, если его безопасно возвращать клиенту.",
    )


class ValidationErrorResponse(BaseSchema):
    """Универсальный ответ API при ошибке валидации данных."""

    success: bool = Field(
        default=False,
        description="Признак успешности операции. Для ошибки валидации всегда false.",
    )
    error: str = Field(
        default="ValidationError",
        description="Тип ошибки.",
    )
    message: str = Field(
        default="Переданы некорректные данные.",
        description="Общее описание ошибки валидации.",
    )
    errors: list[ValidationErrorItem] = Field(
        default_factory=list,
        description="Список ошибок валидации по отдельным полям.",
    )
    request_id: str | None = Field(
        default=None,
        description="Идентификатор HTTP-запроса для трассировки ошибки.",
    )


class PaginationParams(BaseSchema):
    """Параметры постраничной выборки."""

    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Максимальное количество элементов в ответе.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Смещение от начала выборки.",
    )


class PageMeta(BaseSchema):
    """Метаданные постраничного ответа."""

    limit: int = Field(
        ...,
        ge=1,
        description="Максимальное количество элементов в текущей выборке.",
    )
    offset: int = Field(
        ...,
        ge=0,
        description="Смещение текущей выборки от начала списка.",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Общее количество элементов, соответствующих запросу.",
    )
    count: int = Field(
        ...,
        ge=0,
        description="Фактическое количество элементов в текущем ответе.",
    )

    @computed_field(description="Есть ли следующая страница.")
    @property
    def has_next(self) -> bool:
        return self.offset + self.count < self.total

    @computed_field(description="Есть ли предыдущая страница.")
    @property
    def has_previous(self) -> bool:
        return self.offset > 0

    @computed_field(description="Номер текущей страницы, начиная с 1.")
    @property
    def page(self) -> int:
        if self.limit <= 0:
            return 1
        return self.offset // self.limit + 1

    @computed_field(description="Общее количество страниц.")
    @property
    def pages(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.limit - 1) // self.limit


class PageResponse(BaseSchema, Generic[T]):
    """Универсальный постраничный ответ."""

    items: list[T] = Field(
        default_factory=list,
        description="Элементы текущей страницы.",
    )
    meta: PageMeta = Field(
        ...,
        description="Метаданные пагинации.",
    )


class SortOrder(BaseSchema):
    """Параметры сортировки списка."""

    sort_by: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Поле, по которому нужно отсортировать результат.",
        examples=["created_at", "name", "updated_at"],
    )
    sort_desc: bool = Field(
        default=False,
        description="Сортировать по убыванию.",
    )


class DateTimeRangeQuery(BaseSchema):
    """Фильтр по диапазону дат и времени."""

    date_from: datetime | None = Field(
        default=None,
        description="Начало временного диапазона включительно.",
    )
    date_to: datetime | None = Field(
        default=None,
        description="Конец временного диапазона включительно.",
    )

    @field_validator("date_to")
    @classmethod
    def validate_date_range(
        cls,
        value: datetime | None,
        info: Any,
    ) -> datetime | None:
        date_from = info.data.get("date_from")
        if date_from is not None and value is not None and value < date_from:
            raise ValueError("date_to не может быть раньше date_from.")
        return value


class IdListRequest(BaseSchema):
    """Запрос для массовой операции над списком UUID."""

    ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Список идентификаторов сущностей.",
    )

    @field_validator("ids")
    @classmethod
    def validate_unique_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Список ids не должен содержать дубликаты.")
        return value


class BulkActionResult(BaseSchema):
    """Результат массовой операции."""

    requested_count: int = Field(
        ...,
        ge=0,
        description="Количество сущностей, запрошенных для обработки.",
    )
    processed_count: int = Field(
        ...,
        ge=0,
        description="Количество успешно обработанных сущностей.",
    )
    failed_count: int = Field(
        default=0,
        ge=0,
        description="Количество сущностей, обработка которых завершилась ошибкой.",
    )
    skipped_count: int = Field(
        default=0,
        ge=0,
        description="Количество сущностей, которые были пропущены.",
    )
    processed_ids: list[UUID] = Field(
        default_factory=list,
        description="Идентификаторы успешно обработанных сущностей.",
    )
    failed_ids: list[UUID] = Field(
        default_factory=list,
        description="Идентификаторы сущностей, обработка которых завершилась ошибкой.",
    )
    errors: list[ErrorDetail] = Field(
        default_factory=list,
        description="Ошибки, возникшие при выполнении массовой операции.",
    )

    @computed_field(description="Все ли запрошенные сущности были успешно обработаны.")
    @property
    def success(self) -> bool:
        return self.failed_count == 0 and self.processed_count == self.requested_count
