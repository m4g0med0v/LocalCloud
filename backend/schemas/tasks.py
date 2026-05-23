from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import ConfigDict, Field, ValidationInfo, field_validator

from database.models.enums import BackgroundTaskStatus, BackgroundTaskType, TaskPriority
from schemas.common import BaseSchema, PaginationParams


class BackgroundTaskCreate(BaseSchema):
    """Запрос на создание фоновой задачи."""

    task_type: BackgroundTaskType = Field(
        ...,
        description="Тип фоновой задачи.",
    )
    priority: TaskPriority = Field(
        default=TaskPriority.NORMAL,
        description="Приоритет выполнения фоновой задачи.",
    )
    created_by: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, инициировавшего задачу. None означает системную задачу.",
    )
    related_entity_type: str | None = Field(
        default=None,
        max_length=128,
        description="Тип сущности, связанной с задачей.",
    )
    related_entity_id: UUID | None = Field(
        default=None,
        description="Идентификатор сущности, связанной с задачей.",
    )
    payload: dict[str, Any] | None = Field(
        default=None,
        description="Входные параметры фоновой задачи.",
    )
    max_attempts: int = Field(
        default=1,
        gt=0,
        description="Максимальное количество попыток выполнения задачи.",
    )
    idempotency_key: str | None = Field(
        default=None,
        max_length=255,
        description="Ключ идемпотентности для предотвращения дублирования задач.",
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Дата и время, не раньше которого задача может быть запущена.",
    )

    @field_validator("related_entity_type", "idempotency_key")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class BackgroundTaskRead(BaseSchema):
    """Полное представление фоновой задачи."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор фоновой задачи.",
    )
    task_type: BackgroundTaskType = Field(
        ...,
        description="Тип фоновой задачи.",
    )
    status: BackgroundTaskStatus = Field(
        ...,
        description="Текущий статус выполнения задачи.",
    )
    priority: TaskPriority = Field(
        ...,
        description="Приоритет выполнения задачи.",
    )
    created_by: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, инициировавшего задачу. None означает системную задачу.",
    )
    related_entity_type: str | None = Field(
        default=None,
        description="Тип сущности, связанной с задачей.",
    )
    related_entity_id: UUID | None = Field(
        default=None,
        description="Идентификатор сущности, связанной с задачей.",
    )
    progress_percent: int = Field(
        ...,
        ge=0,
        le=100,
        description="Прогресс выполнения задачи от 0 до 100 процентов.",
    )
    payload: dict[str, Any] | None = Field(
        default=None,
        description="Входные параметры задачи.",
    )
    result_data: dict[str, Any] | None = Field(
        default=None,
        description="Структурированные данные результата задачи.",
    )
    error_message: str | None = Field(
        default=None,
        description="Сообщение об ошибке, если задача завершилась неудачно.",
    )
    error_code: str | None = Field(
        default=None,
        max_length=128,
        description="Машиночитаемый код ошибки.",
    )
    attempts_count: int = Field(
        ...,
        ge=0,
        description="Количество выполненных попыток запуска задачи.",
    )
    max_attempts: int = Field(
        ...,
        gt=0,
        description="Максимальное количество попыток выполнения задачи.",
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Ключ идемпотентности для предотвращения дублирования задач.",
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Дата и время, не раньше которого задача может быть запущена.",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Дата и время начала выполнения задачи.",
    )
    finished_at: datetime | None = Field(
        default=None,
        description="Дата и время завершения выполнения задачи.",
    )
    locked_by: str | None = Field(
        default=None,
        description="Идентификатор worker-процесса, заблокировавшего задачу.",
    )
    locked_until: datetime | None = Field(
        default=None,
        description="Дата и время окончания блокировки задачи worker-процессом.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания задачи.",
    )
    updated_at: datetime = Field(
        ...,
        description="Дата и время последнего обновления задачи.",
    )


class BackgroundTaskListItem(BaseSchema):
    """Краткое представление фоновой задачи для списков."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор фоновой задачи.",
    )
    task_type: BackgroundTaskType = Field(
        ...,
        description="Тип фоновой задачи.",
    )
    status: BackgroundTaskStatus = Field(
        ...,
        description="Текущий статус выполнения задачи.",
    )
    priority: TaskPriority = Field(
        ...,
        description="Приоритет выполнения задачи.",
    )
    created_by: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, инициировавшего задачу.",
    )
    related_entity_type: str | None = Field(
        default=None,
        description="Тип сущности, связанной с задачей.",
    )
    related_entity_id: UUID | None = Field(
        default=None,
        description="Идентификатор сущности, связанной с задачей.",
    )
    progress_percent: int = Field(
        ...,
        ge=0,
        le=100,
        description="Прогресс выполнения задачи от 0 до 100 процентов.",
    )
    error_code: str | None = Field(
        default=None,
        description="Машиночитаемый код ошибки.",
    )
    attempts_count: int = Field(
        ...,
        ge=0,
        description="Количество выполненных попыток запуска задачи.",
    )
    max_attempts: int = Field(
        ...,
        gt=0,
        description="Максимальное количество попыток выполнения задачи.",
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Дата и время, не раньше которого задача может быть запущена.",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Дата и время начала выполнения задачи.",
    )
    finished_at: datetime | None = Field(
        default=None,
        description="Дата и время завершения выполнения задачи.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания задачи.",
    )
    updated_at: datetime = Field(
        ...,
        description="Дата и время последнего обновления задачи.",
    )


class BackgroundTaskUpdate(BaseSchema):
    """Запрос на обновление фоновой задачи."""

    status: BackgroundTaskStatus | None = Field(
        default=None,
        description="Новый статус фоновой задачи.",
    )
    priority: TaskPriority | None = Field(
        default=None,
        description="Новый приоритет выполнения задачи.",
    )
    progress_percent: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Новый прогресс выполнения задачи от 0 до 100 процентов.",
    )
    payload: dict[str, Any] | None = Field(
        default=None,
        description="Новые входные параметры задачи.",
    )
    result_data: dict[str, Any] | None = Field(
        default=None,
        description="Новые структурированные данные результата задачи.",
    )
    error_message: str | None = Field(
        default=None,
        description="Новое сообщение об ошибке.",
    )
    error_code: str | None = Field(
        default=None,
        max_length=128,
        description="Новый машиночитаемый код ошибки.",
    )
    attempts_count: int | None = Field(
        default=None,
        ge=0,
        description="Новое количество выполненных попыток.",
    )
    max_attempts: int | None = Field(
        default=None,
        gt=0,
        description="Новое максимальное количество попыток выполнения задачи.",
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Новая дата планового запуска задачи.",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Дата и время начала выполнения задачи.",
    )
    finished_at: datetime | None = Field(
        default=None,
        description="Дата и время завершения выполнения задачи.",
    )
    locked_by: str | None = Field(
        default=None,
        max_length=255,
        description="Идентификатор worker-процесса, заблокировавшего задачу.",
    )
    locked_until: datetime | None = Field(
        default=None,
        description="Дата и время окончания блокировки задачи.",
    )

    @field_validator("error_message", "error_code", "locked_by")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("finished_at")
    @classmethod
    def validate_finished_at(
        cls,
        value: datetime | None,
        info: ValidationInfo,
    ) -> datetime | None:
        started_at = info.data.get("started_at")

        if started_at is not None and value is not None and value < started_at:
            raise ValueError("finished_at не может быть раньше started_at.")

        return value

    @field_validator("attempts_count")
    @classmethod
    def validate_attempts_count(
        cls,
        value: int | None,
        info: ValidationInfo,
    ) -> int | None:
        max_attempts = info.data.get("max_attempts")

        if value is not None and max_attempts is not None and value > max_attempts:
            raise ValueError("attempts_count не может быть больше max_attempts.")

        return value


class BackgroundTaskProgressUpdate(BaseSchema):
    """Запрос на обновление прогресса фоновой задачи."""

    progress_percent: int = Field(
        ...,
        ge=0,
        le=100,
        description="Текущий прогресс выполнения задачи от 0 до 100 процентов.",
    )
    message: str | None = Field(
        default=None,
        max_length=1000,
        description="Текущее сообщение о ходе выполнения задачи.",
    )
    result_data: dict[str, Any] | None = Field(
        default=None,
        description="Промежуточные или итоговые структурированные данные результата.",
    )

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class BackgroundTaskCancelRequest(BaseSchema):
    """Запрос на отмену фоновой задачи."""

    reason: str | None = Field(
        default=None,
        max_length=1000,
        description="Причина отмены фоновой задачи.",
    )

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class BackgroundTaskRetryRequest(BaseSchema):
    """Запрос на повторный запуск фоновой задачи."""

    reset_attempts: bool = Field(
        default=False,
        description="Сбросить ли счётчик попыток перед повторным запуском.",
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Дата и время, не раньше которого нужно повторно запустить задачу.",
    )
    priority: TaskPriority | None = Field(
        default=None,
        description="Новый приоритет задачи при повторном запуске.",
    )


class BackgroundTaskQueryParams(PaginationParams):
    """Параметры фильтрации фоновых задач."""

    task_type: BackgroundTaskType | None = Field(
        default=None,
        description="Фильтр по типу фоновой задачи.",
    )
    status: BackgroundTaskStatus | None = Field(
        default=None,
        description="Фильтр по статусу фоновой задачи.",
    )
    priority: TaskPriority | None = Field(
        default=None,
        description="Фильтр по приоритету задачи.",
    )
    created_by: UUID | None = Field(
        default=None,
        description="Фильтр по пользователю, инициировавшему задачу.",
    )
    related_entity_type: str | None = Field(
        default=None,
        max_length=128,
        description="Фильтр по типу связанной сущности.",
    )
    related_entity_id: UUID | None = Field(
        default=None,
        description="Фильтр по идентификатору связанной сущности.",
    )
    idempotency_key: str | None = Field(
        default=None,
        max_length=255,
        description="Фильтр по ключу идемпотентности.",
    )
    locked_by: str | None = Field(
        default=None,
        max_length=255,
        description="Фильтр по worker-процессу, заблокировавшему задачу.",
    )
    created_from: datetime | None = Field(
        default=None,
        description="Фильтр по дате создания: начало диапазона включительно.",
    )
    created_to: datetime | None = Field(
        default=None,
        description="Фильтр по дате создания: конец диапазона включительно.",
    )
    scheduled_before: datetime | None = Field(
        default=None,
        description="Вернуть задачи, запланированные не позднее указанного времени.",
    )
    only_locked: bool | None = Field(
        default=None,
        description="Фильтр по наличию активной или сохранённой блокировки worker-процессом.",
    )
    sort_by: str = Field(
        default="created_at",
        min_length=1,
        max_length=64,
        description="Поле сортировки.",
        examples=["created_at", "updated_at", "scheduled_at", "priority", "status"],
    )
    sort_desc: bool = Field(
        default=True,
        description="Сортировать по убыванию.",
    )

    @field_validator("related_entity_type", "idempotency_key", "locked_by")
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


class TaskResultRead(BaseSchema):
    """Результат выполнения фоновой задачи."""

    task_id: UUID = Field(
        ...,
        description="Идентификатор фоновой задачи.",
    )
    task_type: BackgroundTaskType = Field(
        ...,
        description="Тип фоновой задачи.",
    )
    status: BackgroundTaskStatus = Field(
        ...,
        description="Итоговый или текущий статус задачи.",
    )
    progress_percent: int = Field(
        ...,
        ge=0,
        le=100,
        description="Прогресс выполнения задачи от 0 до 100 процентов.",
    )
    result_data: dict[str, Any] | None = Field(
        default=None,
        description="Структурированные данные результата задачи.",
    )
    error_message: str | None = Field(
        default=None,
        description="Сообщение об ошибке, если задача завершилась неудачно.",
    )
    error_code: str | None = Field(
        default=None,
        description="Машиночитаемый код ошибки.",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Дата и время начала выполнения задачи.",
    )
    finished_at: datetime | None = Field(
        default=None,
        description="Дата и время завершения выполнения задачи.",
    )
