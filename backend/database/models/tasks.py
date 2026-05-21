from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base
from database.models.enums import BackgroundTaskStatus, BackgroundTaskType, TaskPriority
from database.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from database.models.users import User


class BackgroundTask(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Фоновая задача.

    Представляет длительную или асинхронную операцию, которая может выполняться
    отдельно от основного HTTP-запроса.

    Основные сценарии использования:
        - постановка задач в очередь;
        - выполнение задач worker-процессами;
        - повторный запуск задач после ошибки;
        - отслеживание прогресса выполнения;
        - хранение результата или ошибки выполнения;
        - блокировка задачи на время обработки;
        - привязка задачи к доменной сущности.

    Таблица:
        background_tasks
    """

    __tablename__ = "background_tasks"  # pyright: ignore[reportAssignmentType]

    __table_args__ = (
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="ck_background_tasks_progress_percent_range",
        ),
        CheckConstraint(
            "attempts_count >= 0",
            name="ck_background_tasks_attempts_count_non_negative",
        ),
        CheckConstraint(
            "max_attempts > 0",
            name="ck_background_tasks_max_attempts_positive",
        ),
        CheckConstraint(
            "attempts_count <= max_attempts",
            name="ck_background_tasks_attempts_count_lte_max_attempts",
        ),
        CheckConstraint(
            """
            finished_at IS NULL
            OR started_at IS NULL
            OR finished_at >= started_at
            """,
            name="ck_background_tasks_finished_at_gte_started_at",
        ),
        UniqueConstraint(
            "idempotency_key",
            name="uq_background_tasks_idempotency_key",
        ),
        Index("ix_background_tasks_task_type", "task_type"),
        Index("ix_background_tasks_status", "status"),
        Index("ix_background_tasks_priority", "priority"),
        Index("ix_background_tasks_created_by", "created_by"),
        Index("ix_background_tasks_scheduled_at", "scheduled_at"),
        Index("ix_background_tasks_locked_until", "locked_until"),
        Index("ix_background_tasks_started_at", "started_at"),
        Index("ix_background_tasks_finished_at", "finished_at"),
        Index("ix_background_tasks_created_at", "created_at"),
        Index("ix_background_tasks_idempotency_key", "idempotency_key"),
        Index("ix_background_tasks_type_status", "task_type", "status"),
        Index("ix_background_tasks_status_created_at", "status", "created_at"),
        Index("ix_background_tasks_created_by_status", "created_by", "status"),
        Index(
            "ix_background_tasks_related_entity",
            "related_entity_type",
            "related_entity_id",
        ),
        Index(
            "ix_background_tasks_status_priority_scheduled",
            "status",
            "priority",
            "scheduled_at",
        ),
        Index(
            "ix_background_tasks_result_data_gin", "result_data", postgresql_using="gin"
        ),
        Index("ix_background_tasks_payload_gin", "payload", postgresql_using="gin"),
    )

    task_type: Mapped[BackgroundTaskType] = mapped_column(
        Enum(
            BackgroundTaskType,
            name="background_task_type",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        comment="Тип фоновой задачи.",
    )

    status: Mapped[BackgroundTaskStatus] = mapped_column(
        Enum(
            BackgroundTaskStatus,
            name="background_task_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=BackgroundTaskStatus.PENDING,
        server_default=BackgroundTaskStatus.PENDING.value,
        comment="Текущий статус выполнения задачи.",
    )

    priority: Mapped[TaskPriority] = mapped_column(
        Enum(
            TaskPriority,
            name="task_priority",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=TaskPriority.NORMAL,
        server_default=TaskPriority.NORMAL.value,
        comment="Приоритет выполнения задачи.",
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "Пользователь, инициировавший задачу. Null означает системную задачу."
        ),
    )

    related_entity_type: Mapped[str | None] = mapped_column(
        String(length=128),
        nullable=True,
        comment="Тип сущности, связанной с задачей.",
    )

    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Идентификатор сущности, связанной с задачей.",
    )

    progress_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Прогресс выполнения задачи от 0 до 100 процентов.",
    )

    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Входные параметры задачи.",
    )

    result_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Структурированные данные результата задачи.",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Сообщение об ошибке, если задача завершилась неудачно.",
    )

    error_code: Mapped[str | None] = mapped_column(
        String(length=128),
        nullable=True,
        comment="Машиночитаемый код ошибки.",
    )

    attempts_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Количество выполненных попыток запуска задачи.",
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Максимальное количество попыток выполнения задачи.",
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(length=255),
        nullable=True,
        comment="Ключ идемпотентности для предотвращения дублирования задач.",
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата и время, не раньше которого задача может быть запущена.",
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата и время начала выполнения задачи.",
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата и время завершения выполнения задачи.",
    )

    locked_by: Mapped[str | None] = mapped_column(
        String(length=255),
        nullable=True,
        comment="Идентификатор worker-процесса, заблокировавшего задачу.",
    )

    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата и время окончания блокировки задачи worker-процессом.",
    )

    # -------------------------------------------------------------------------
    # Связи
    # -------------------------------------------------------------------------

    creator: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="background_tasks",
        lazy="selectin",
    )

    # -------------------------------------------------------------------------
    # Фабричные методы
    # -------------------------------------------------------------------------

    @classmethod
    def create_system_task(
        cls,
        task_type: BackgroundTaskType,
        payload: dict[str, Any] | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        related_entity_type: str | None = None,
        related_entity_id: uuid.UUID | None = None,
        scheduled_at: datetime | None = None,
        max_attempts: int = 1,
        idempotency_key: str | None = None,
    ) -> BackgroundTask:
        """Создаёт системную фоновую задачу.

        Args:
            task_type: Тип фоновой задачи.
            payload: Входные параметры задачи.
            priority: Приоритет выполнения задачи.
            related_entity_type: Тип связанной доменной сущности.
            related_entity_id: Идентификатор связанной доменной сущности.
            scheduled_at: Дата и время, не раньше которого задача может быть
                запущена.
            max_attempts: Максимальное количество попыток выполнения задачи.
            idempotency_key: Ключ идемпотентности для предотвращения
                дублирования задач.

        Returns:
            Экземпляр ``BackgroundTask`` для системной задачи.
        """

        return cls(
            task_type=task_type,
            status=BackgroundTaskStatus.PENDING,
            priority=priority,
            created_by=None,
            payload=payload,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            scheduled_at=scheduled_at,
            max_attempts=max_attempts,
            idempotency_key=idempotency_key,
        )

    @classmethod
    def create_user_task(
        cls,
        task_type: BackgroundTaskType,
        created_by: uuid.UUID,
        payload: dict[str, Any] | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        related_entity_type: str | None = None,
        related_entity_id: uuid.UUID | None = None,
        scheduled_at: datetime | None = None,
        max_attempts: int = 1,
        idempotency_key: str | None = None,
    ) -> BackgroundTask:
        """Создаёт пользовательскую фоновую задачу.

        Args:
            task_type: Тип фоновой задачи.
            created_by: Идентификатор пользователя, инициировавшего задачу.
            payload: Входные параметры задачи.
            priority: Приоритет выполнения задачи.
            related_entity_type: Тип связанной доменной сущности.
            related_entity_id: Идентификатор связанной доменной сущности.
            scheduled_at: Дата и время, не раньше которого задача может быть
                запущена.
            max_attempts: Максимальное количество попыток выполнения задачи.
            idempotency_key: Ключ идемпотентности для предотвращения
                дублирования задач.

        Returns:
            Экземпляр ``BackgroundTask`` для пользовательской задачи.
        """

        return cls(
            task_type=task_type,
            status=BackgroundTaskStatus.PENDING,
            priority=priority,
            created_by=created_by,
            payload=payload,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            scheduled_at=scheduled_at,
            max_attempts=max_attempts,
            idempotency_key=idempotency_key,
        )

    # -------------------------------------------------------------------------
    # Вспомогательные свойства
    # -------------------------------------------------------------------------

    @property
    def is_system_task(self) -> bool:
        """Возвращает True, если задача была создана системой."""

        return self.created_by is None

    @property
    def is_pending(self) -> bool:
        """Возвращает True, если задача ожидает выполнения."""

        return self.status == BackgroundTaskStatus.PENDING

    @property
    def is_running(self) -> bool:
        """Возвращает True, если задача выполняется."""

        return self.status == BackgroundTaskStatus.RUNNING

    @property
    def is_completed(self) -> bool:
        """Возвращает True, если задача успешно завершена."""

        return self.status == BackgroundTaskStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Возвращает True, если задача завершилась ошибкой."""

        return self.status == BackgroundTaskStatus.FAILED

    @property
    def is_cancelled(self) -> bool:
        """Возвращает True, если задача была отменена."""

        return self.status == BackgroundTaskStatus.CANCELLED

    @property
    def is_finished(self) -> bool:
        """Возвращает True, если задача находится в конечном состоянии."""

        return self.status in {
            BackgroundTaskStatus.COMPLETED,
            BackgroundTaskStatus.FAILED,
            BackgroundTaskStatus.CANCELLED,
        }

    @property
    def has_related_entity(self) -> bool:
        """Возвращает True, если задача связана с конкретной сущностью."""

        return (
            self.related_entity_type is not None and self.related_entity_id is not None
        )

    @property
    def has_error(self) -> bool:
        """Возвращает True, если задача имеет ошибку."""

        return self.error_message is not None or self.error_code is not None

    @property
    def can_retry(self) -> bool:
        """Возвращает True, если задачу можно повторить."""

        return self.attempts_count < self.max_attempts

    @property
    def duration_seconds(self) -> float | None:
        """Возвращает длительность выполнения задачи в секундах.

        Если задача ещё не была запущена или не завершена, возвращает None.
        """

        if self.started_at is None or self.finished_at is None:
            return None

        return (self.finished_at - self.started_at).total_seconds()

    # -------------------------------------------------------------------------
    # Проверки планирования и блокировки
    # -------------------------------------------------------------------------

    def is_scheduled_for_at(self, moment: datetime) -> bool:
        """Проверяет, может ли задача быть запущена в указанный момент.

        Args:
            moment: Момент времени для проверки.

        Returns:
            True, если задача может быть запущена с учётом ``scheduled_at``.
        """

        return self.scheduled_at is None or self.scheduled_at <= moment

    def is_locked_at(self, moment: datetime) -> bool:
        """Проверяет, заблокирована ли задача в указанный момент.

        Args:
            moment: Момент времени для проверки.

        Returns:
            True, если задача заблокирована worker-процессом.
        """

        return self.locked_until is not None and self.locked_until > moment

    def can_start_at(self, moment: datetime) -> bool:
        """Проверяет, можно ли запустить задачу в указанный момент.

        Args:
            moment: Момент времени для проверки.

        Returns:
            True, если задачу можно запустить.
        """

        return (
            self.status == BackgroundTaskStatus.PENDING
            and self.is_scheduled_for_at(moment)
            and not self.is_locked_at(moment)
            and self.can_retry
        )

    # -------------------------------------------------------------------------
    # Методы жизненного цикла
    # -------------------------------------------------------------------------

    def lock(
        self,
        worker_id: str,
        locked_until: datetime,
    ) -> None:
        """Блокирует задачу за worker-процессом.

        Args:
            worker_id: Идентификатор worker-процесса.
            locked_until: Дата и время окончания блокировки.

        Raises:
            ValueError: Если идентификатор worker-процесса не передан.
        """

        if not worker_id:
            raise ValueError("Идентификатор worker-процесса обязателен.")

        self.locked_by = worker_id
        self.locked_until = locked_until

    def unlock(self) -> None:
        """Снимает блокировку задачи."""

        self.locked_by = None
        self.locked_until = None

    def start(
        self,
        started_at: datetime | None = None,
        worker_id: str | None = None,
        locked_until: datetime | None = None,
    ) -> None:
        """Переводит задачу в состояние выполнения.

        Args:
            started_at: Дата и время начала выполнения. Если значение не
                передано, используется текущее время UTC.
            worker_id: Идентификатор worker-процесса.
            locked_until: Дата и время окончания блокировки.
        """

        self.status = BackgroundTaskStatus.RUNNING
        self.started_at = started_at or datetime.now(UTC)
        self.finished_at = None
        self.error_message = None
        self.error_code = None
        self.attempts_count += 1

        if worker_id is not None and locked_until is not None:
            self.lock(worker_id=worker_id, locked_until=locked_until)

    def update_progress(self, progress_percent: int) -> None:
        """Обновляет прогресс задачи.

        Args:
            progress_percent: Целое число от 0 до 100.

        Raises:
            ValueError: Если прогресс выходит за допустимые границы.
        """

        if progress_percent < 0 or progress_percent > 100:
            raise ValueError("Прогресс задачи должен быть в диапазоне от 0 до 100.")

        self.progress_percent = progress_percent

    def complete(
        self,
        result_data: dict[str, Any] | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        """Помечает задачу как успешно завершённую.

        Args:
            result_data: Структурированные данные результата задачи.
            finished_at: Дата и время завершения. Если значение не передано,
                используется текущее время UTC.
        """

        self.status = BackgroundTaskStatus.COMPLETED
        self.progress_percent = 100
        self.result_data = result_data
        self.error_message = None
        self.error_code = None
        self.finished_at = finished_at or datetime.now(UTC)
        self.unlock()

    def fail(
        self,
        error_message: str | None = None,
        error_code: str | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        """Помечает задачу как завершившуюся ошибкой.

        Args:
            error_message: Сообщение об ошибке.
            error_code: Машиночитаемый код ошибки.
            finished_at: Дата и время завершения. Если значение не передано,
                используется текущее время UTC.
        """

        self.status = BackgroundTaskStatus.FAILED
        self.error_message = error_message
        self.error_code = error_code
        self.finished_at = finished_at or datetime.now(UTC)
        self.unlock()

    def retry(
        self,
        scheduled_at: datetime | None = None,
    ) -> None:
        """Возвращает задачу в очередь на повторное выполнение.

        Args:
            scheduled_at: Дата и время, не раньше которого задача может быть
                повторно запущена.

        Raises:
            ValueError: Если лимит попыток уже исчерпан.
        """

        if not self.can_retry:
            raise ValueError("Лимит попыток повторного запуска задачи исчерпан.")

        self.status = BackgroundTaskStatus.PENDING
        self.scheduled_at = scheduled_at
        self.finished_at = None
        self.error_message = None
        self.error_code = None
        self.unlock()

    def cancel(
        self,
        reason: str | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        """Отменяет задачу.

        Args:
            reason: Причина отмены задачи.
            finished_at: Дата и время отмены. Если значение не передано,
                используется текущее время UTC.
        """

        self.status = BackgroundTaskStatus.CANCELLED
        self.error_message = reason
        self.finished_at = finished_at or datetime.now(UTC)
        self.unlock()

    def attach_related_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> None:
        """Связывает задачу с доменной сущностью.

        Args:
            entity_type: Тип доменной сущности.
            entity_id: Идентификатор доменной сущности.
        """

        self.related_entity_type = entity_type
        self.related_entity_id = entity_id

    def clear_related_entity(self) -> None:
        """Удаляет связь задачи с доменной сущностью."""

        self.related_entity_type = None
        self.related_entity_id = None

    def __repr__(self) -> str:
        return (
            f"<BackgroundTask("
            f"id={self.id}, "
            f"task_type={self.task_type.value!r}, "
            f"status={self.status.value!r}, "
            f"priority={self.priority.value!r}, "
            f"created_by={self.created_by}, "
            f"progress_percent={self.progress_percent}, "
            f"attempts_count={self.attempts_count}, "
            f"max_attempts={self.max_attempts}, "
            f"related_entity_type={self.related_entity_type!r}, "
            f"related_entity_id={self.related_entity_id}"
            f")>"
        )
