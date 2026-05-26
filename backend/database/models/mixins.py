"""Mixin-классы для ORM-моделей.

Модуль содержит переиспользуемые SQLAlchemy mixin-классы, добавляющие
типовые поля ORM-моделям: UUID-первичный ключ, временные метки создания
и обновления, отдельную временную метку создания, а также поля мягкого
удаления.

Attributes:
    UUIDPrimaryKeyMixin: Mixin для добавления UUID-первичного ключа.
    TimestampMixin: Mixin для добавления временных меток создания и обновления.
    CreatedAtMixin: Mixin для добавления временной метки создания.
    SoftDeleteMixin: Mixin для добавления полей мягкого удаления.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Добавляет UUID-первичный ключ.

    Mixin добавляет колонку `id`, которая используется как первичный ключ
    ORM-модели. Значение UUID генерируется автоматически при создании объекта.

    Attributes:
        id: Уникальный идентификатор записи.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


class TimestampMixin:
    """Добавляет временные метки создания и обновления.

    Mixin добавляет поля `created_at` и `updated_at`. Время создания
    устанавливается на уровне базы данных, а время обновления автоматически
    изменяется при обновлении записи.

    Attributes:
        created_at: Дата и время создания записи.
        updated_at: Дата и время последнего обновления записи.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CreatedAtMixin:
    """Добавляет временную метку создания.

    Mixin добавляет только поле `created_at`, которое устанавливается
    на уровне базы данных при создании записи.

    Attributes:
        created_at: Дата и время создания записи.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Добавляет поля для мягкого удаления.

    Mixin добавляет признак удаления и дату удаления. Мягкое удаление
    позволяет скрывать объект из активных выборок без физического удаления
    записи из базы данных.

    Attributes:
        is_deleted: Признак мягкого удаления записи.
        deleted_at: Дата и время мягкого удаления записи.
    """

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def mark_deleted(
        self,
        deleted_at: datetime | None = None,
        *,
        deleted_by: uuid.UUID | None = None,
    ) -> None:
        """Помечает объект как удалённый.

        Устанавливает признак мягкого удаления и сохраняет дату удаления.
        Если дата удаления не передана, используется текущее UTC-время.
        Параметр `deleted_by` оставлен для совместимости с моделями,
        которые переопределяют этот метод и хранят пользователя, выполнившего
        удаление.

        Args:
            deleted_at: Дата и время удаления. Если не передано, используется
                текущее UTC-время.
            deleted_by: Идентификатор пользователя, выполнившего удаление.

        Returns:
            None.
        """

        self.is_deleted = True
        self.deleted_at = deleted_at or datetime.now(UTC)

    def restore(
        self,
        *,
        parent_id: uuid.UUID | None = None,
        path: str | None = None,
        depth: int | None = None,
        updated_by: uuid.UUID | None = None,
    ) -> None:
        """Восстанавливает объект после мягкого удаления.

        Снимает признак мягкого удаления и очищает дату удаления. Дополнительные
        параметры оставлены для совместимости с моделями файловой системы,
        которые переопределяют восстановление и обновляют родителя, путь,
        глубину вложенности и пользователя, выполнившего изменение.

        Args:
            parent_id: Идентификатор родительского объекта после восстановления.
            path: Восстановленный материализованный путь.
            depth: Глубина вложенности после восстановления.
            updated_by: Идентификатор пользователя, восстановившего объект.

        Returns:
            None.
        """

        self.is_deleted = False
        self.deleted_at = None
