from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Базовая схема API.

    Используется как общий родитель для DTO, которые могут создаваться из
    ORM-объектов SQLAlchemy через Pydantic v2. Задаёт единые настройки
    валидации, заполнения полей и сериализации для всех наследников.

    Attributes:
        model_config: Конфигурация Pydantic-модели.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class UUIDSchema(BaseSchema):
    """Базовая схема сущности с UUID-идентификатором.

    Используется как миксин или родительская схема для моделей, которым нужно
    вернуть наружу уникальный идентификатор сущности.

    Attributes:
        id: Уникальный идентификатор сущности.
    """

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор сущности.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class CreatedAtSchema(BaseSchema):
    """Базовая схема сущности с датой создания.

    Используется для DTO, которым требуется отдавать дату и время создания
    сущности.

    Attributes:
        created_at: Дата и время создания сущности.
    """

    created_at: datetime = Field(
        ...,
        description="Дата и время создания сущности.",
    )


class TimestampedSchema(CreatedAtSchema):
    """Базовая схема сущности с датой создания и обновления.

    Расширяет схему с датой создания полем последнего обновления.

    Attributes:
        created_at: Дата и время создания сущности.
        updated_at: Дата и время последнего обновления сущности.
    """

    updated_at: datetime = Field(
        ...,
        description="Дата и время последнего обновления сущности.",
    )


class SoftDeleteSchema(BaseSchema):
    """Базовая схема сущности с поддержкой логического удаления.

    Используется для DTO сущностей, которые не удаляются физически из базы, а
    помечаются как удалённые.

    Attributes:
        is_deleted: Признак логического удаления сущности.
        deleted_at: Дата и время логического удаления сущности.
    """

    is_deleted: bool = Field(
        default=False,
        description="Признак логического удаления сущности.",
    )
    deleted_at: datetime | None = Field(
        default=None,
        description="Дата и время логического удаления сущности.",
    )


class MessageResponse(BaseSchema):
    """Универсальный ответ с текстовым сообщением.

    Используется для простых API-ответов, когда достаточно вернуть только
    человекочитаемое сообщение о результате операции.

    Attributes:
        message: Человекочитаемое сообщение о результате операции.
    """

    message: str = Field(
        ...,
        min_length=1,
        description="Человекочитаемое сообщение о результате операции.",
        examples=["Операция выполнена успешно."],
    )


class StatusResponse(MessageResponse):
    """Универсальный ответ со статусом выполнения операции.

    Расширяет текстовый ответ признаком успешности и необязательным
    машиночитаемым статусом.

    Attributes:
        message: Человекочитаемое сообщение о результате операции.
        success: Признак успешного выполнения операции.
        status: Машиночитаемый статус операции.
    """

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
    """Описание одной ошибки или причины отказа.

    Используется как элемент детализации ошибок API, включая ошибки валидации,
    доменные ошибки и частичные ошибки массовых операций.

    Attributes:
        code: Машиночитаемый код ошибки.
        message: Человекочитаемое описание ошибки.
        field: Поле, с которым связана ошибка, если применимо.
        details: Дополнительные структурированные сведения об ошибке.
    """

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
    """Универсальный ответ API при ошибке.

    Используется для стандартизированного ответа при исключениях и ошибках
    бизнес-логики.

    Attributes:
        success: Признак успешности операции. Для ошибки всегда ``False``.
        error: Краткое машинное имя ошибки или тип исключения.
        message: Человекочитаемое сообщение об ошибке.
        details: Дополнительные сведения об ошибке.
        request_id: Идентификатор HTTP-запроса для трассировки ошибки.
    """

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
    """Описание ошибки валидации отдельного поля.

    Используется для передачи клиенту информации о конкретном поле или пути,
    в котором была обнаружена ошибка валидации.

    Attributes:
        field: Имя поля или путь к полю, в котором обнаружена ошибка.
        message: Описание ошибки валидации.
        code: Машиночитаемый код ошибки валидации.
        value: Переданное значение, вызвавшее ошибку, если его безопасно
            возвращать клиенту.
    """

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
    """Универсальный ответ API при ошибке валидации данных.

    Возвращается, когда входные данные не прошли проверку схемы или
    пользовательских валидаторов.

    Attributes:
        success: Признак успешности операции. Для ошибки валидации всегда
            ``False``.
        error: Тип ошибки.
        message: Общее описание ошибки валидации.
        errors: Список ошибок валидации по отдельным полям.
        request_id: Идентификатор HTTP-запроса для трассировки ошибки.
    """

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
    """Параметры постраничной выборки.

    Используется в query-параметрах API для ограничения размера страницы и
    задания смещения от начала выборки.

    Attributes:
        limit: Максимальное количество элементов в ответе.
        offset: Смещение от начала выборки.
    """

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
    """Метаданные постраничного ответа.

    Содержит информацию о текущей странице, общем количестве элементов и
    вычисляемые признаки наличия соседних страниц.

    Attributes:
        limit: Максимальное количество элементов в текущей выборке.
        offset: Смещение текущей выборки от начала списка.
        total: Общее количество элементов, соответствующих запросу.
        count: Фактическое количество элементов в текущем ответе.
        has_next: Есть ли следующая страница.
        has_previous: Есть ли предыдущая страница.
        page: Номер текущей страницы, начиная с 1.
        pages: Общее количество страниц.
    """

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
        """Проверяет наличие следующей страницы.

        Returns:
            ``True``, если после текущей страницы есть элементы, иначе
            ``False``.
        """

        return self.offset + self.count < self.total

    @computed_field(description="Есть ли предыдущая страница.")
    @property
    def has_previous(self) -> bool:
        """Проверяет наличие предыдущей страницы.

        Returns:
            ``True``, если текущая выборка начинается не с первого элемента,
            иначе ``False``.
        """

        return self.offset > 0

    @computed_field(description="Номер текущей страницы, начиная с 1.")
    @property
    def page(self) -> int:
        """Вычисляет номер текущей страницы.

        Returns:
            Номер текущей страницы, начиная с 1. Если ``limit`` некорректен,
            возвращает ``1``.
        """

        if self.limit <= 0:
            return 1
        return self.offset // self.limit + 1

    @computed_field(description="Общее количество страниц.")
    @property
    def pages(self) -> int:
        """Вычисляет общее количество страниц.

        Returns:
            Общее количество страниц. Если элементов нет, возвращает ``0``.
        """

        if self.total == 0:
            return 0
        return (self.total + self.limit - 1) // self.limit


class PageResponse(BaseSchema, Generic[T]):
    """Универсальный постраничный ответ.

    Используется для API-методов, возвращающих список элементов с метаданными
    пагинации.

    Attributes:
        items: Элементы текущей страницы.
        meta: Метаданные пагинации.
    """

    items: list[T] = Field(
        default_factory=list,
        description="Элементы текущей страницы.",
    )
    meta: PageMeta = Field(
        ...,
        description="Метаданные пагинации.",
    )


class SortOrder(BaseSchema):
    """Параметры сортировки списка.

    Используется в query-параметрах API для задания поля сортировки и
    направления сортировки.

    Attributes:
        sort_by: Поле, по которому нужно отсортировать результат.
        sort_desc: Признак сортировки по убыванию.
    """

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
    """Фильтр по диапазону дат и времени.

    Используется в query-параметрах API для фильтрации сущностей по временному
    интервалу. Верхняя граница не может быть раньше нижней.

    Attributes:
        date_from: Начало временного диапазона включительно.
        date_to: Конец временного диапазона включительно.
    """

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
        """Проверяет корректность временного диапазона.

        Args:
            value: Значение верхней границы диапазона ``date_to``.
            info: Контекст валидации Pydantic с уже обработанными значениями
                полей.

        Returns:
            Значение ``date_to``, если диапазон корректен.

        Raises:
            ValueError: Если ``date_to`` меньше ``date_from``.
        """

        date_from = info.data.get("date_from")
        if date_from is not None and value is not None and value < date_from:
            raise ValueError("date_to не может быть раньше date_from.")
        return value


class IdListRequest(BaseSchema):
    """Запрос для массовой операции над списком UUID.

    Используется в API-методах, которые выполняют действие сразу над
    несколькими сущностями. Список идентификаторов должен быть непустым и не
    должен содержать дубликаты.

    Attributes:
        ids: Список идентификаторов сущностей.
    """

    ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Список идентификаторов сущностей.",
    )

    @field_validator("ids")
    @classmethod
    def validate_unique_ids(cls, value: list[UUID]) -> list[UUID]:
        """Проверяет уникальность идентификаторов.

        Args:
            value: Список UUID, переданный в запросе.

        Returns:
            Исходный список UUID, если дубликаты отсутствуют.

        Raises:
            ValueError: Если список содержит повторяющиеся идентификаторы.
        """

        if len(value) != len(set(value)):
            raise ValueError("Список ids не должен содержать дубликаты.")
        return value


class BulkActionResult(BaseSchema):
    """Результат массовой операции.

    Содержит счётчики обработки, списки успешно обработанных и ошибочных
    идентификаторов, а также детализацию возникших ошибок.

    Attributes:
        requested_count: Количество сущностей, запрошенных для обработки.
        processed_count: Количество успешно обработанных сущностей.
        failed_count: Количество сущностей, обработка которых завершилась
            ошибкой.
        skipped_count: Количество сущностей, которые были пропущены.
        processed_ids: Идентификаторы успешно обработанных сущностей.
        failed_ids: Идентификаторы сущностей, обработка которых завершилась
            ошибкой.
        errors: Ошибки, возникшие при выполнении массовой операции.
        success: Все ли запрошенные сущности были успешно обработаны.
    """

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
        """Проверяет успешность массовой операции.

        Returns:
            ``True``, если нет ошибок и количество обработанных сущностей равно
            количеству запрошенных сущностей, иначе ``False``.
        """

        return self.failed_count == 0 and self.processed_count == self.requested_count
