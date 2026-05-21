from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base
from database.models.enums import UploadPartStatus, UploadSessionStatus
from database.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from database.models.filesystem import FileSystemNode
    from database.models.users import User


class UploadSession(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Сеанс multipart upload.

    Сеанс создаётся перед загрузкой файла. Backend:
        - создаёт запись ``upload_sessions``;
        - инициирует multipart upload в MinIO/S3;
        - сохраняет ``upload_id``;
        - создаёт записи ``upload_parts``;
        - выдаёт клиенту pre-signed URL для каждой части;
        - отслеживает прогресс;
        - завершает или отменяет загрузку.

    Таблица:
        upload_sessions
    """

    __tablename__ = "upload_sessions"  # pyright: ignore[reportAssignmentType]

    __table_args__ = (
        CheckConstraint(
            "file_size_bytes >= 0",
            name="ck_upload_sessions_file_size_bytes_non_negative",
        ),
        CheckConstraint(
            "parts_count > 0",
            name="ck_upload_sessions_parts_count_positive",
        ),
        CheckConstraint(
            "uploaded_parts_count >= 0",
            name="ck_upload_sessions_uploaded_parts_count_non_negative",
        ),
        CheckConstraint(
            "uploaded_parts_count <= parts_count",
            name="ck_upload_sessions_uploaded_parts_count_lte_parts_count",
        ),
        CheckConstraint(
            "part_size_bytes > 0",
            name="ck_upload_sessions_part_size_bytes_positive",
        ),
        Index("ix_upload_sessions_user_id", "user_id"),
        Index("ix_upload_sessions_parent_node_id", "parent_node_id"),
        Index("ix_upload_sessions_upload_id", "upload_id"),
        Index("ix_upload_sessions_status", "status"),
        Index("ix_upload_sessions_expires_at", "expires_at"),
        Index("ix_upload_sessions_created_at", "created_at"),
        Index("ix_upload_sessions_completed_at", "completed_at"),
        Index("ix_upload_sessions_aborted_at", "aborted_at"),
        Index("ix_upload_sessions_failed_at", "failed_at"),
        Index("ix_upload_sessions_user_status", "user_id", "status"),
        Index("ix_upload_sessions_user_created_at", "user_id", "created_at"),
        Index("ix_upload_sessions_parent_status", "parent_node_id", "status"),
        Index("ix_upload_sessions_status_expires_at", "status", "expires_at"),
        Index(
            "ix_upload_sessions_storage_bucket_key",
            "storage_bucket",
            "storage_key",
        ),
        UniqueConstraint("upload_id", name="uq_upload_sessions_upload_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Пользователь, инициировавший загрузку.",
    )

    parent_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_system_nodes.id", ondelete="CASCADE"),
        nullable=False,
        comment="Папка назначения, в которой будет создан загруженный файл.",
    )

    file_name: Mapped[str] = mapped_column(
        String(length=255),
        nullable=False,
        comment="Оригинальное имя загружаемого файла.",
    )

    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Общий размер файла в байтах.",
    )

    part_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Размер одной части multipart upload в байтах.",
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(length=255),
        nullable=True,
        comment="MIME-тип загружаемого файла.",
    )

    checksum: Mapped[str | None] = mapped_column(
        String(length=128),
        nullable=True,
        comment="Контрольная сумма всего файла.",
    )

    checksum_algorithm: Mapped[str | None] = mapped_column(
        String(length=32),
        nullable=True,
        comment="Алгоритм контрольной суммы, например sha256.",
    )

    storage_bucket: Mapped[str] = mapped_column(
        String(length=128),
        nullable=False,
        comment="Bucket MinIO/S3, используемый для загрузки.",
    )

    storage_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Ключ объекта MinIO/S3 для итогового файла.",
    )

    upload_id: Mapped[str] = mapped_column(
        String(length=512),
        nullable=False,
        comment="Идентификатор multipart upload, возвращённый MinIO/S3.",
    )

    status: Mapped[UploadSessionStatus] = mapped_column(
        Enum(
            UploadSessionStatus,
            name="upload_session_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=UploadSessionStatus.CREATED,
        server_default=UploadSessionStatus.CREATED.value,
        comment="Текущий статус сеанса загрузки.",
    )

    parts_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Общее количество частей загрузки.",
    )

    uploaded_parts_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Количество успешно загруженных частей.",
    )

    uploaded_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Количество байтов, подтверждённых как загруженные.",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Дата и время истечения срока действия сеанса загрузки.",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата и время завершения загрузки.",
    )

    aborted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата и время отмены загрузки.",
    )

    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата и время ошибки загрузки.",
    )

    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Описание причины ошибки загрузки.",
    )

    client_ip: Mapped[str | None] = mapped_column(
        String(length=64),
        nullable=True,
        comment="IP-адрес клиента, инициировавшего загрузку.",
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="User-Agent клиента, инициировавшего загрузку.",
    )

    # -------------------------------------------------------------------------
    # Связи
    # -------------------------------------------------------------------------

    user: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    parent_node: Mapped[FileSystemNode] = relationship(
        "FileSystemNode",
        foreign_keys=[parent_node_id],
        lazy="selectin",
    )

    parts: Mapped[list[UploadPart]] = relationship(
        "UploadPart",
        foreign_keys="UploadPart.upload_session_id",
        back_populates="upload_session",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="UploadPart.part_number",
    )

    # -------------------------------------------------------------------------
    # Вспомогательные свойства
    # -------------------------------------------------------------------------

    @property
    def is_created(self) -> bool:
        """Возвращает True, если сеанс создан, но загрузка ещё не началась."""

        return self.status == UploadSessionStatus.CREATED

    @property
    def is_uploading(self) -> bool:
        """Возвращает True, если загрузка выполняется."""

        return self.status == UploadSessionStatus.UPLOADING

    @property
    def is_completed(self) -> bool:
        """Возвращает True, если загрузка завершена."""

        return self.status == UploadSessionStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Возвращает True, если загрузка завершилась ошибкой."""

        return self.status == UploadSessionStatus.FAILED

    @property
    def is_aborted(self) -> bool:
        """Возвращает True, если загрузка была отменена."""

        return self.status == UploadSessionStatus.ABORTED

    @property
    def is_expired(self) -> bool:
        """Возвращает True, если сеанс помечен как истёкший."""

        return self.status == UploadSessionStatus.EXPIRED

    @property
    def is_finished(self) -> bool:
        """Возвращает True, если сеанс находится в конечном состоянии."""

        return self.status in {
            UploadSessionStatus.COMPLETED,
            UploadSessionStatus.FAILED,
            UploadSessionStatus.ABORTED,
            UploadSessionStatus.EXPIRED,
        }

    @property
    def progress_percent(self) -> float:
        """Возвращает прогресс загрузки в процентах.

        Основной расчёт выполняется по количеству загруженных частей.

        Returns:
            Процент загруженных частей, округлённый до двух знаков.
        """

        if self.parts_count <= 0:
            return 0.0

        progress = (self.uploaded_parts_count / self.parts_count) * 100
        return round(min(progress, 100.0), 2)

    @property
    def byte_progress_percent(self) -> float:
        """Возвращает прогресс загрузки в процентах по байтам.

        Returns:
            Процент загруженных байтов, округлённый до двух знаков.
        """

        if self.file_size_bytes <= 0:
            return 100.0

        progress = (self.uploaded_bytes / self.file_size_bytes) * 100
        return round(min(progress, 100.0), 2)

    @property
    def all_parts_uploaded(self) -> bool:
        """Возвращает True, если все ожидаемые части загружены."""

        return self.parts_count > 0 and self.uploaded_parts_count == self.parts_count

    @property
    def remaining_parts_count(self) -> int:
        """Возвращает количество оставшихся частей."""

        return max(self.parts_count - self.uploaded_parts_count, 0)

    @property
    def remaining_bytes(self) -> int:
        """Возвращает примерное количество оставшихся байтов."""

        return max(self.file_size_bytes - self.uploaded_bytes, 0)

    # -------------------------------------------------------------------------
    # Проверки состояния
    # -------------------------------------------------------------------------

    def is_expired_at(self, moment: datetime) -> bool:
        """Проверяет, истёк ли срок действия сеанса.

        Args:
            moment: Дата и время для проверки срока действия.

        Returns:
            True, если срок действия сеанса истёк к указанному моменту.
        """

        return self.expires_at <= moment

    def can_receive_parts_at(self, moment: datetime) -> bool:
        """Проверяет, может ли сеанс принимать части.

        Args:
            moment: Дата и время для проверки.

        Returns:
            True, если сеанс может принимать части в указанный момент.
        """

        return (
            not self.is_finished
            and not self.is_expired_at(moment)
            and self.status
            in {
                UploadSessionStatus.CREATED,
                UploadSessionStatus.UPLOADING,
            }
        )

    def can_be_completed_at(self, moment: datetime) -> bool:
        """Проверяет, можно ли завершить сеанс.

        Args:
            moment: Дата и время для проверки.

        Returns:
            True, если сеанс можно завершить в указанный момент.
        """

        return (
            not self.is_finished
            and not self.is_expired_at(moment)
            and self.all_parts_uploaded
        )

    def can_be_aborted_at(self, moment: datetime) -> bool:
        """Проверяет, можно ли отменить сеанс.

        Args:
            moment: Дата и время для проверки.

        Returns:
            True, если сеанс можно отменить в указанный момент.
        """

        return not self.is_finished and not self.is_expired_at(moment)

    # -------------------------------------------------------------------------
    # Методы изменения состояния
    # -------------------------------------------------------------------------

    def mark_uploading(self) -> None:
        """Переводит сеанс в состояние загрузки."""

        if self.status == UploadSessionStatus.CREATED:
            self.status = UploadSessionStatus.UPLOADING

    def register_uploaded_part(self, part_size_bytes: int) -> None:
        """Увеличивает счётчики загруженных частей и байтов.

        Обычно вызывается после успешного подтверждения ETag части.

        Args:
            part_size_bytes: Размер загруженной части в байтах.

        Raises:
            ValueError: Если размер части отрицательный или все части уже
                зарегистрированы как загруженные.
        """

        if part_size_bytes < 0:
            raise ValueError("Размер загруженной части не может быть отрицательным.")

        if self.uploaded_parts_count >= self.parts_count:
            raise ValueError(
                "Количество загруженных частей не может превышать общее "
                "количество частей."
            )

        self.uploaded_parts_count += 1
        self.uploaded_bytes = min(
            self.uploaded_bytes + part_size_bytes,
            self.file_size_bytes,
        )

        if self.status == UploadSessionStatus.CREATED:
            self.status = UploadSessionStatus.UPLOADING

    def unregister_uploaded_part(self, part_size_bytes: int) -> None:
        """Уменьшает счётчики загруженных частей и байтов.

        Используется при откате статуса части.

        Args:
            part_size_bytes: Размер части в байтах.

        Raises:
            ValueError: Если размер части отрицательный.
        """

        if part_size_bytes < 0:
            raise ValueError("Размер загруженной части не может быть отрицательным.")

        self.uploaded_parts_count = max(self.uploaded_parts_count - 1, 0)
        self.uploaded_bytes = max(self.uploaded_bytes - part_size_bytes, 0)

    def complete(self, completed_at: datetime | None = None) -> None:
        """Помечает сеанс как успешно завершённый.

        Args:
            completed_at: Дата и время завершения. Если не передано,
                используется текущее UTC-время.
        """

        self.status = UploadSessionStatus.COMPLETED
        self.completed_at = completed_at or datetime.now(UTC)
        self.failure_reason = None

    def fail(
        self,
        reason: str | None = None,
        failed_at: datetime | None = None,
    ) -> None:
        """Помечает сеанс как завершившийся ошибкой.

        Args:
            reason: Причина ошибки загрузки.
            failed_at: Дата и время ошибки. Если не передано, используется
                текущее UTC-время.
        """

        self.status = UploadSessionStatus.FAILED
        self.failed_at = failed_at or datetime.now(UTC)
        self.failure_reason = reason

    def abort(self, aborted_at: datetime | None = None) -> None:
        """Помечает сеанс как отменённый.

        Args:
            aborted_at: Дата и время отмены. Если не передано, используется
                текущее UTC-время.
        """

        self.status = UploadSessionStatus.ABORTED
        self.aborted_at = aborted_at or datetime.now(UTC)

    def expire(self, expired_at: datetime | None = None) -> None:
        """Помечает сеанс как истёкший.

        Значение ``expired_at`` сохраняется в ``aborted_at``, потому что
        отдельного поля ``expired_at`` нет: срок действия уже хранится
        в ``expires_at``.

        Args:
            expired_at: Дата и время истечения. Если не передано, используется
                текущее UTC-время.
        """

        self.status = UploadSessionStatus.EXPIRED
        self.aborted_at = expired_at or datetime.now(UTC)

    def recalculate_progress_from_parts(self) -> None:
        """Пересчитывает прогресс на основе связанных частей.

        Метод предполагает, что связь ``parts`` уже загружена.
        """

        uploaded_parts = [part for part in self.parts if part.is_uploaded]
        self.uploaded_parts_count = len(uploaded_parts)
        self.uploaded_bytes = sum(part.size_bytes for part in uploaded_parts)

    def __repr__(self) -> str:
        return (
            f"<UploadSession("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"file_name={self.file_name!r}, "
            f"status={self.status.value!r}, "
            f"uploaded_parts_count={self.uploaded_parts_count}, "
            f"parts_count={self.parts_count}, "
            f"progress_percent={self.progress_percent}"
            f")>"
        )


class UploadPart(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Часть multipart upload.

    Каждая часть имеет номер, размер, статус и ETag, возвращаемый MinIO/S3
    после успешной загрузки.

    Таблица:
        upload_parts
    """

    __tablename__ = "upload_parts"  # pyright: ignore[reportAssignmentType]

    __table_args__ = (
        UniqueConstraint(
            "upload_session_id",
            "part_number",
            name="uq_upload_parts_session_part_number",
        ),
        CheckConstraint(
            "part_number > 0",
            name="ck_upload_parts_part_number_positive",
        ),
        CheckConstraint(
            "size_bytes > 0",
            name="ck_upload_parts_size_bytes_positive",
        ),
        Index("ix_upload_parts_upload_session_id", "upload_session_id"),
        Index("ix_upload_parts_part_number", "part_number"),
        Index("ix_upload_parts_status", "status"),
        Index("ix_upload_parts_uploaded_at", "uploaded_at"),
        Index("ix_upload_parts_created_at", "created_at"),
        Index("ix_upload_parts_session_status", "upload_session_id", "status"),
        Index(
            "ix_upload_parts_session_part_number",
            "upload_session_id",
            "part_number",
        ),
        Index("ix_upload_parts_status_uploaded_at", "status", "uploaded_at"),
    )

    upload_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("upload_sessions.id", ondelete="CASCADE"),
        nullable=False,
        comment="Сеанс загрузки, к которому относится часть.",
    )

    part_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Номер части multipart upload.",
    )

    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Размер части в байтах.",
    )

    etag: Mapped[str | None] = mapped_column(
        String(length=512),
        nullable=True,
        comment="ETag, возвращённый MinIO/S3 после успешной загрузки части.",
    )

    checksum: Mapped[str | None] = mapped_column(
        String(length=128),
        nullable=True,
        comment="Необязательная контрольная сумма части.",
    )

    status: Mapped[UploadPartStatus] = mapped_column(
        Enum(
            UploadPartStatus,
            name="upload_part_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=UploadPartStatus.PENDING,
        server_default=UploadPartStatus.PENDING.value,
        comment="Текущий статус части загрузки.",
    )

    uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата и время успешной загрузки части.",
    )

    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата и время ошибки загрузки части.",
    )

    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Описание причины ошибки загрузки части.",
    )

    # -------------------------------------------------------------------------
    # Связи
    # -------------------------------------------------------------------------

    upload_session: Mapped[UploadSession] = relationship(
        "UploadSession",
        foreign_keys=[upload_session_id],
        back_populates="parts",
        lazy="selectin",
    )

    # -------------------------------------------------------------------------
    # Фабричные методы
    # -------------------------------------------------------------------------

    @classmethod
    def create_pending(
        cls,
        upload_session_id: uuid.UUID,
        part_number: int,
        size_bytes: int,
    ) -> UploadPart:
        """Создаёт ожидающую загрузки часть.

        Args:
            upload_session_id: Идентификатор сеанса загрузки.
            part_number: Номер части.
            size_bytes: Размер части в байтах.

        Returns:
            Часть загрузки со статусом ``PENDING``.
        """

        return cls(
            upload_session_id=upload_session_id,
            part_number=part_number,
            size_bytes=size_bytes,
            status=UploadPartStatus.PENDING,
        )

    # -------------------------------------------------------------------------
    # Вспомогательные свойства
    # -------------------------------------------------------------------------

    @property
    def is_pending(self) -> bool:
        """Возвращает True, если часть ожидает загрузки."""

        return self.status == UploadPartStatus.PENDING

    @property
    def is_uploaded(self) -> bool:
        """Возвращает True, если часть успешно загружена."""

        return self.status == UploadPartStatus.UPLOADED

    @property
    def is_failed(self) -> bool:
        """Возвращает True, если загрузка части завершилась ошибкой."""

        return self.status == UploadPartStatus.FAILED

    @property
    def has_etag(self) -> bool:
        """Возвращает True, если у части сохранён ETag."""

        return self.etag is not None

    @property
    def can_complete(self) -> bool:
        """Возвращает True, если часть готова для complete multipart upload."""

        return self.status == UploadPartStatus.UPLOADED and self.etag is not None

    # -------------------------------------------------------------------------
    # Методы изменения состояния
    # -------------------------------------------------------------------------

    def mark_uploaded(
        self,
        etag: str,
        uploaded_at: datetime | None = None,
        checksum: str | None = None,
    ) -> None:
        """Помечает часть как успешно загруженную.

        Args:
            etag: ETag, возвращённый MinIO/S3.
            uploaded_at: Дата и время загрузки. Если не передано, используется
                текущее UTC-время.
            checksum: Необязательная контрольная сумма части.

        Raises:
            ValueError: Если ETag не передан.
        """

        if not etag:
            raise ValueError("ETag обязателен для загруженной части.")

        self.status = UploadPartStatus.UPLOADED
        self.etag = etag
        self.checksum = checksum
        self.uploaded_at = uploaded_at or datetime.now(UTC)
        self.failed_at = None
        self.failure_reason = None

    def mark_failed(
        self,
        reason: str | None = None,
        failed_at: datetime | None = None,
    ) -> None:
        """Помечает часть как завершившуюся ошибкой.

        Args:
            reason: Причина ошибки загрузки.
            failed_at: Дата и время ошибки. Если не передано, используется
                текущее UTC-время.
        """

        self.status = UploadPartStatus.FAILED
        self.failed_at = failed_at or datetime.now(UTC)
        self.failure_reason = reason

    def reset(self) -> None:
        """Возвращает часть в состояние ожидания загрузки."""

        self.status = UploadPartStatus.PENDING
        self.etag = None
        self.checksum = None
        self.uploaded_at = None
        self.failed_at = None
        self.failure_reason = None

    def __repr__(self) -> str:
        return (
            f"<UploadPart("
            f"id={self.id}, "
            f"upload_session_id={self.upload_session_id}, "
            f"part_number={self.part_number}, "
            f"size_bytes={self.size_bytes}, "
            f"status={self.status.value!r}, "
            f"uploaded_at={self.uploaded_at}"
            f")>"
        )
