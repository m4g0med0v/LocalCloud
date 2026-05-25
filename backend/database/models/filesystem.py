from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    and_,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base
from database.models.enums import (
    FilePreviewStatus,
    FileProcessingStatus,
    FileVersionStatus,
    NodeType,
    NodeVisibility,
    StorageObjectStatus,
    TrashItemStatus,
)
from database.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from database.models.links import PublicLink
    from database.models.permissions import NodePermission
    from database.models.users import User


class FileSystemNode(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Узел файловой системы.

    Представляет общий элемент виртуальной файловой системы.

    Конкретный тип узла определяется полем ``node_type``:
        - file;
        - folder.

    Иерархия хранится через ``parent_id``. Для ускорения поиска и перемещения
    также используется материализованный путь.

    Таблица:
        file_system_nodes
    """

    __tablename__ = "file_system_nodes"  # pyright: ignore[reportAssignmentType]

    __table_args__ = (
        CheckConstraint(
            "depth >= 0",
            name="ck_file_system_nodes_depth_non_negative",
        ),
        Index("ix_file_system_nodes_owner_id", "owner_id"),
        Index("ix_file_system_nodes_parent_id", "parent_id"),
        Index("ix_file_system_nodes_name", "name"),
        Index("ix_file_system_nodes_node_type", "node_type"),
        Index("ix_file_system_nodes_visibility", "visibility"),
        Index("ix_file_system_nodes_is_deleted", "is_deleted"),
        Index("ix_file_system_nodes_deleted_at", "deleted_at"),
        Index("ix_file_system_nodes_created_at", "created_at"),
        Index("ix_file_system_nodes_updated_at", "updated_at"),
        Index("ix_file_system_nodes_owner_parent", "owner_id", "parent_id"),
        Index(
            "ix_file_system_nodes_owner_parent_name",
            "owner_id",
            "parent_id",
            "name",
        ),
        Index(
            "ix_file_system_nodes_owner_deleted",
            "owner_id",
            "is_deleted",
        ),
        Index(
            "ix_file_system_nodes_parent_deleted",
            "parent_id",
            "is_deleted",
        ),
        Index(
            "ix_file_system_nodes_owner_type_deleted",
            "owner_id",
            "node_type",
            "is_deleted",
        ),
        Index(
            "ix_file_system_nodes_owner_path",
            "owner_id",
            "path",
        ),
        Index(
            "uq_file_system_nodes_active_name_in_parent",
            "owner_id",
            "parent_id",
            "name",
            unique=True,
            postgresql_where=and_(
                text("is_deleted = false"),
                text("parent_id IS NOT NULL"),
            ),
        ),
        Index(
            "uq_file_system_nodes_active_root_name",
            "owner_id",
            "name",
            unique=True,
            postgresql_where=and_(
                text("is_deleted = false"),
                text("parent_id IS NULL"),
            ),
        ),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Пользователь, которому принадлежит узел файловой системы.",
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_system_nodes.id", ondelete="CASCADE"),
        nullable=True,
        comment=(
            "Родительская папка. Null означает, что узел находится на корневом уровне."
        ),
    )

    name: Mapped[str] = mapped_column(
        String(length=255),
        nullable=False,
        comment="Имя файла или папки, отображаемое пользователю.",
    )

    node_type: Mapped[NodeType] = mapped_column(
        Enum(
            NodeType,
            name="node_type",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        comment="Тип узла файловой системы.",
    )

    visibility: Mapped[NodeVisibility] = mapped_column(
        Enum(
            NodeVisibility,
            name="node_visibility",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=NodeVisibility.PRIVATE,
        server_default=NodeVisibility.PRIVATE.value,
        comment="Видимость узла: private, shared или public.",
    )

    path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Материализованный логический путь узла.",
    )

    depth: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Глубина вложенности узла.",
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Пользователь, создавший узел.",
    )

    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Пользователь, последним изменивший узел.",
    )

    deleted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Пользователь, удаливший узел.",
    )

    # -------------------------------------------------------------------------
    # Связи
    # -------------------------------------------------------------------------

    owner: Mapped[User] = relationship(
        "User",
        foreign_keys=[owner_id],
        back_populates="file_system_nodes",
        lazy="selectin",
    )

    creator: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="selectin",
    )

    updater: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[updated_by],
        lazy="selectin",
    )

    deleter: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[deleted_by],
        lazy="selectin",
    )

    parent: Mapped[FileSystemNode | None] = relationship(
        "FileSystemNode",
        remote_side="FileSystemNode.id",
        foreign_keys=[parent_id],
        back_populates="children",
        lazy="selectin",
    )

    children: Mapped[list[FileSystemNode]] = relationship(
        "FileSystemNode",
        foreign_keys=[parent_id],
        back_populates="parent",
        cascade="all, delete-orphan",
        single_parent=True,
        lazy="selectin",
    )

    file: Mapped[File | None] = relationship(
        "File",
        foreign_keys="File.node_id",
        back_populates="node",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    folder: Mapped[Folder | None] = relationship(
        "Folder",
        foreign_keys="Folder.node_id",
        back_populates="node",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    trash_item: Mapped[TrashItem | None] = relationship(
        "TrashItem",
        foreign_keys="TrashItem.node_id",
        back_populates="node",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    permissions: Mapped[list[NodePermission]] = relationship(
        "NodePermission",
        foreign_keys="NodePermission.node_id",
        back_populates="node",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    public_links: Mapped[list[PublicLink]] = relationship(
        "PublicLink",
        foreign_keys="PublicLink.node_id",
        back_populates="node",
        lazy="selectin",
    )

    # -------------------------------------------------------------------------
    # Вспомогательные свойства
    # -------------------------------------------------------------------------

    @property
    def is_file(self) -> bool:
        """Возвращает True, если узел является файлом."""

        return self.node_type == NodeType.FILE

    @property
    def is_folder(self) -> bool:
        """Возвращает True, если узел является папкой."""

        return self.node_type == NodeType.FOLDER

    @property
    def is_root_level(self) -> bool:
        """Возвращает True, если узел расположен в корне хранилища."""

        return self.parent_id is None

    @property
    def is_private(self) -> bool:
        """Возвращает True, если узел приватный."""

        return self.visibility == NodeVisibility.PRIVATE

    @property
    def is_shared(self) -> bool:
        """Возвращает True, если узел имеет выданные права доступа."""

        return self.visibility == NodeVisibility.SHARED

    @property
    def is_public(self) -> bool:
        """Возвращает True, если узел доступен через публичную ссылку."""

        return self.visibility == NodeVisibility.PUBLIC

    # -------------------------------------------------------------------------
    # Методы изменения состояния
    # -------------------------------------------------------------------------

    def rename(self, new_name: str, updated_by: uuid.UUID | None = None) -> None:
        """Переименовывает узел.

        Изменение ``path`` для самого узла и его потомков должно выполняться
        в сервисном слое, потому что требует знания всей иерархии.

        Args:
            new_name: Новое имя узла.
            updated_by: Идентификатор пользователя, изменившего узел.
        """

        self.name = new_name
        self.updated_by = updated_by

    def move(
        self,
        new_parent_id: uuid.UUID | None,
        new_path: str,
        new_depth: int,
        updated_by: uuid.UUID | None = None,
    ) -> None:
        """Перемещает узел в другую папку.

        Обновление путей дочерних узлов выполняется сервисным слоем.

        Args:
            new_parent_id: Идентификатор новой родительской папки.
            new_path: Новый материализованный путь.
            new_depth: Новая глубина вложенности.
            updated_by: Идентификатор пользователя, переместившего узел.
        """

        self.parent_id = new_parent_id
        self.path = new_path
        self.depth = new_depth
        self.updated_by = updated_by

    def mark_deleted(
        self,
        deleted_at: datetime | None = None,
        *,
        deleted_by: uuid.UUID | None = None,
    ) -> None:
        """Помечает узел как удалённый.

        Args:
            deleted_by: Идентификатор пользователя, удалившего узел.
            deleted_at: Дата и время удаления. Если не передано, используется
                текущее UTC-время.
        """

        self.is_deleted = True
        self.deleted_at = deleted_at or datetime.now(UTC)
        self.deleted_by = deleted_by

    def restore(
        self,
        *,
        parent_id: uuid.UUID | None = None,
        path: str | None = None,
        depth: int | None = None,
        updated_by: uuid.UUID | None = None,
    ) -> None:
        """Восстанавливает узел из корзины.

        Args:
            parent_id: Идентификатор родительской папки после восстановления.
            path: Восстановленный материализованный путь.
            depth: Глубина вложенности после восстановления.
            updated_by: Идентификатор пользователя, восстановившего узел.
        """

        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        if parent_id is not None or self.parent_id is not None:
            self.parent_id = parent_id
        if path is not None:
            self.path = path
        if depth is not None:
            self.depth = depth
        self.updated_by = updated_by

    def make_private(self) -> None:
        """Делает узел приватным."""

        self.visibility = NodeVisibility.PRIVATE

    def make_shared(self) -> None:
        """Помечает узел как общий."""

        self.visibility = NodeVisibility.SHARED

    def make_public(self) -> None:
        """Помечает узел как публичный."""

        self.visibility = NodeVisibility.PUBLIC

    def __repr__(self) -> str:
        return (
            f"<FileSystemNode("
            f"id={self.id}, "
            f"name={self.name!r}, "
            f"node_type={self.node_type.value!r}, "
            f"owner_id={self.owner_id}, "
            f"parent_id={self.parent_id}, "
            f"is_deleted={self.is_deleted}"
            f")>"
        )


class File(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Метаданные файла.

    Хранит сведения о файле, объекте MinIO/S3, размере, MIME-типе,
    контрольной сумме, статусе обработки и статусе предпросмотра.

    Таблица:
        files
    """

    __tablename__ = "files"  # pyright: ignore[reportAssignmentType]

    __table_args__ = (
        CheckConstraint(
            "size_bytes >= 0",
            name="ck_files_size_bytes_non_negative",
        ),
        UniqueConstraint("node_id", name="uq_files_node_id"),
        UniqueConstraint("storage_key", name="uq_files_storage_key"),
        Index("ix_files_node_id", "node_id"),
        Index("ix_files_storage_bucket_key", "storage_bucket", "storage_key"),
        Index(
            "ix_files_checksum_algorithm_checksum",
            "checksum_algorithm",
            "checksum",
        ),
        Index("ix_files_extension_mime_type", "extension", "mime_type"),
        Index("ix_files_processing_status", "processing_status"),
        Index("ix_files_preview_status", "preview_status"),
        Index("ix_files_storage_status", "storage_status"),
        Index("ix_files_current_version_id", "current_version_id"),
        Index("ix_files_created_at", "created_at"),
        Index("ix_files_updated_at", "updated_at"),
    )

    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_system_nodes.id", ondelete="CASCADE"),
        nullable=False,
        comment="Узел файловой системы, связанный с этим файлом.",
    )

    storage_bucket: Mapped[str] = mapped_column(
        String(length=128),
        nullable=False,
        comment="Bucket MinIO/S3, в котором хранится объект файла.",
    )

    storage_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Ключ объекта MinIO/S3 для текущего содержимого файла.",
    )

    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Размер файла в байтах.",
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(length=255),
        nullable=True,
        comment="MIME-тип файла.",
    )

    extension: Mapped[str | None] = mapped_column(
        String(length=32),
        nullable=True,
        comment="Расширение файла без ведущей точки.",
    )

    checksum: Mapped[str | None] = mapped_column(
        String(length=128),
        nullable=True,
        comment="Контрольная сумма файла.",
    )

    checksum_algorithm: Mapped[str | None] = mapped_column(
        String(length=32),
        nullable=True,
        comment="Алгоритм контрольной суммы, например sha256.",
    )

    storage_status: Mapped[StorageObjectStatus] = mapped_column(
        Enum(
            StorageObjectStatus,
            name="storage_object_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=StorageObjectStatus.AVAILABLE,
        server_default=StorageObjectStatus.AVAILABLE.value,
        comment="Статус физического объекта в MinIO/S3.",
    )

    processing_status: Mapped[FileProcessingStatus] = mapped_column(
        Enum(
            FileProcessingStatus,
            name="file_processing_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=FileProcessingStatus.READY,
        server_default=FileProcessingStatus.READY.value,
        comment="Статус постобработки файла.",
    )

    preview_status: Mapped[FilePreviewStatus] = mapped_column(
        Enum(
            FilePreviewStatus,
            name="file_preview_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=FilePreviewStatus.NOT_REQUIRED,
        server_default=FilePreviewStatus.NOT_REQUIRED.value,
        comment="Статус генерации предпросмотра.",
    )

    preview_storage_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Ключ объекта предпросмотра в MinIO/S3.",
    )

    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "file_versions.id",
            name="fk_files_current_version_id",
            ondelete="SET NULL",
            use_alter=True,
        ),
        nullable=True,
        comment="Текущая активная версия файла.",
    )

    # -------------------------------------------------------------------------
    # Связи
    # -------------------------------------------------------------------------

    node: Mapped[FileSystemNode] = relationship(
        "FileSystemNode",
        foreign_keys=[node_id],
        back_populates="file",
        lazy="selectin",
    )

    versions: Mapped[list[FileVersion]] = relationship(
        "FileVersion",
        foreign_keys="FileVersion.file_id",
        back_populates="file",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    current_version: Mapped[FileVersion | None] = relationship(
        "FileVersion",
        foreign_keys=[current_version_id],
        post_update=True,
        lazy="selectin",
    )

    # -------------------------------------------------------------------------
    # Вспомогательные свойства и методы
    # -------------------------------------------------------------------------

    @property
    def preview_available(self) -> bool:
        """Возвращает True, если предпросмотр файла готов."""

        return (
            self.preview_status == FilePreviewStatus.READY
            and self.preview_storage_key is not None
        )

    @property
    def is_ready(self) -> bool:
        """Возвращает True, если файл готов к использованию."""

        return (
            self.processing_status == FileProcessingStatus.READY
            and self.storage_status == StorageObjectStatus.AVAILABLE
        )

    def mark_processing(self) -> None:
        """Помечает файл как находящийся в обработке."""

        self.processing_status = FileProcessingStatus.PROCESSING

    def mark_ready(self) -> None:
        """Помечает файл как готовый."""

        self.processing_status = FileProcessingStatus.READY
        self.storage_status = StorageObjectStatus.AVAILABLE

    def mark_processing_failed(self) -> None:
        """Помечает обработку файла как завершившуюся ошибкой."""

        self.processing_status = FileProcessingStatus.FAILED

    def mark_storage_missing(self) -> None:
        """Помечает физический объект как отсутствующий."""

        self.storage_status = StorageObjectStatus.MISSING

    def mark_storage_corrupted(self) -> None:
        """Помечает физический объект как повреждённый."""

        self.storage_status = StorageObjectStatus.CORRUPTED

    def set_preview_ready(self, preview_storage_key: str) -> None:
        """Сохраняет ключ предпросмотра и помечает предпросмотр как готовый.

        Args:
            preview_storage_key: Ключ объекта предпросмотра в MinIO/S3.
        """

        self.preview_storage_key = preview_storage_key
        self.preview_status = FilePreviewStatus.READY

    def set_current_version(self, version: FileVersion) -> None:
        """Устанавливает текущую версию файла.

        Args:
            version: Версия, которая должна стать текущей.
        """

        self.current_version = version
        self.current_version_id = version.id

    def __repr__(self) -> str:
        return (
            f"<File("
            f"id={self.id}, "
            f"node_id={self.node_id}, "
            f"size_bytes={self.size_bytes}, "
            f"mime_type={self.mime_type!r}, "
            f"storage_status={self.storage_status.value!r}"
            f")>"
        )


class Folder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Метаданные папки.

    Иерархия папок хранится в ``file_system_nodes`` через ``parent_id``.
    Эта таблица содержит только дополнительные свойства, относящиеся к папке.

    Таблица:
        folders
    """

    __tablename__ = "folders"  # pyright: ignore[reportAssignmentType]

    __table_args__ = (
        UniqueConstraint("node_id", name="uq_folders_node_id"),
        Index("ix_folders_node_id", "node_id"),
        Index("ix_folders_created_at", "created_at"),
        Index("ix_folders_updated_at", "updated_at"),
    )

    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_system_nodes.id", ondelete="CASCADE"),
        nullable=False,
        comment="Узел файловой системы, связанный с этой папкой.",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Необязательное описание папки.",
    )

    color: Mapped[str | None] = mapped_column(
        String(length=32),
        nullable=True,
        comment="Цветовая метка папки в интерфейсе.",
    )

    # -------------------------------------------------------------------------
    # Связи
    # -------------------------------------------------------------------------

    node: Mapped[FileSystemNode] = relationship(
        "FileSystemNode",
        foreign_keys=[node_id],
        back_populates="folder",
        lazy="selectin",
    )

    # -------------------------------------------------------------------------
    # Методы изменения состояния
    # -------------------------------------------------------------------------

    def update_metadata(
        self,
        description: str | None = None,
        color: str | None = None,
    ) -> None:
        """Обновляет пользовательские метаданные папки.

        Args:
            description: Новое описание папки.
            color: Новая цветовая метка папки.
        """

        self.description = description
        self.color = color

    def __repr__(self) -> str:
        return f"<Folder(id={self.id}, node_id={self.node_id}, color={self.color!r})>"


class FileVersion(Base, UUIDPrimaryKeyMixin):
    """Версия файла.

    Каждая версия указывает на отдельный объект в MinIO/S3. Это позволяет
    хранить историю изменений файла и при необходимости восстанавливать
    предыдущие версии.

    Таблица:
        file_versions
    """

    __tablename__ = "file_versions"  # pyright: ignore[reportAssignmentType]

    __table_args__ = (
        UniqueConstraint(
            "file_id",
            "version_number",
            name="uq_file_versions_file_id_version_number",
        ),
        UniqueConstraint(
            "storage_key",
            name="uq_file_versions_storage_key",
        ),
        CheckConstraint(
            "version_number > 0",
            name="ck_file_versions_version_number_positive",
        ),
        CheckConstraint(
            "size_bytes >= 0",
            name="ck_file_versions_size_bytes_non_negative",
        ),
        Index("ix_file_versions_file_id", "file_id"),
        Index("ix_file_versions_status", "status"),
        Index("ix_file_versions_file_current", "file_id", "is_current"),
        Index("ix_file_versions_file_created_at", "file_id", "created_at"),
        Index(
            "ix_file_versions_storage_bucket_key",
            "storage_bucket",
            "storage_key",
        ),
        Index(
            "uq_file_versions_current_per_file",
            "file_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
    )

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        comment="Файл, к которому относится версия.",
    )

    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Порядковый номер версии внутри файла.",
    )

    status: Mapped[FileVersionStatus] = mapped_column(
        Enum(
            FileVersionStatus,
            name="file_version_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=FileVersionStatus.ACTIVE,
        server_default=FileVersionStatus.ACTIVE.value,
        comment="Статус версии файла.",
    )

    storage_bucket: Mapped[str] = mapped_column(
        String(length=128),
        nullable=False,
        comment="Bucket MinIO/S3, в котором хранится объект версии.",
    )

    storage_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Ключ объекта MinIO/S3 для версии файла.",
    )

    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Размер версии файла в байтах.",
    )

    checksum: Mapped[str | None] = mapped_column(
        String(length=128),
        nullable=True,
        comment="Контрольная сумма версии файла.",
    )

    checksum_algorithm: Mapped[str | None] = mapped_column(
        String(length=32),
        nullable=True,
        comment="Алгоритм контрольной суммы версии.",
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(length=255),
        nullable=True,
        comment="MIME-тип версии файла.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Дата и время создания версии.",
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Пользователь, создавший версию файла.",
    )

    change_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Комментарий к изменению версии.",
    )

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="Признак текущей активной версии файла.",
    )

    # -------------------------------------------------------------------------
    # Связи
    # -------------------------------------------------------------------------

    file: Mapped[File] = relationship(
        "File",
        foreign_keys=[file_id],
        back_populates="versions",
        lazy="selectin",
    )

    creator: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="selectin",
    )

    # -------------------------------------------------------------------------
    # Вспомогательные свойства и методы
    # -------------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """Возвращает True, если версия активна."""

        return self.status == FileVersionStatus.ACTIVE

    # -------------------------------------------------------------------------
    # Методы изменения состояния
    # -------------------------------------------------------------------------

    def make_current(self) -> None:
        """Помечает версию как текущую.

        Снятие флага ``is_current`` с других версий этого файла должно
        выполняться в сервисном слое.
        """

        self.is_current = True
        self.status = FileVersionStatus.ACTIVE

    def archive(self) -> None:
        """Архивирует версию файла."""

        self.is_current = False
        self.status = FileVersionStatus.ARCHIVED

    def mark_deleted(self) -> None:
        """Помечает версию как удалённую."""

        self.is_current = False
        self.status = FileVersionStatus.DELETED

    def __repr__(self) -> str:
        return (
            f"<FileVersion("
            f"id={self.id}, "
            f"file_id={self.file_id}, "
            f"version_number={self.version_number}, "
            f"status={self.status.value!r}, "
            f"is_current={self.is_current}"
            f")>"
        )


class TrashItem(Base, UUIDPrimaryKeyMixin):
    """Элемент корзины.

    Хранит информацию об удалённых файлах и папках, которые могут быть
    восстановлены до окончательного удаления.

    Таблица:
        trash_items
    """

    __tablename__ = "trash_items"  # pyright: ignore[reportAssignmentType]

    __table_args__ = (
        UniqueConstraint("node_id", name="uq_trash_items_node_id"),
        Index("ix_trash_items_node_id", "node_id"),
        Index("ix_trash_items_owner_id", "owner_id"),
        Index("ix_trash_items_status", "status"),
        Index("ix_trash_items_deleted_by", "deleted_by"),
        Index("ix_trash_items_original_parent_id", "original_parent_id"),
        Index("ix_trash_items_deleted_at", "deleted_at"),
        Index("ix_trash_items_expires_at", "expires_at"),
        Index("ix_trash_items_purged_at", "purged_at"),
        Index("ix_trash_items_restore_available", "restore_available"),
        Index("ix_trash_items_owner_deleted_at", "owner_id", "deleted_at"),
        Index("ix_trash_items_owner_expires_at", "owner_id", "expires_at"),
    )

    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_system_nodes.id", ondelete="CASCADE"),
        nullable=False,
        comment="Удалённый узел файловой системы.",
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Владелец удалённого узла.",
    )

    deleted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Пользователь, который переместил узел в корзину.",
    )

    original_parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_system_nodes.id", ondelete="SET NULL"),
        nullable=True,
        comment="Исходная родительская папка до удаления.",
    )

    original_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Исходный логический путь до удаления.",
    )

    status: Mapped[TrashItemStatus] = mapped_column(
        Enum(
            TrashItemStatus,
            name="trash_item_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=TrashItemStatus.IN_TRASH,
        server_default=TrashItemStatus.IN_TRASH.value,
        comment="Статус элемента корзины.",
    )

    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Дата и время перемещения узла в корзину.",
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата, после которой элемент может быть окончательно удалён.",
    )

    restore_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="Признак возможности восстановления.",
    )

    purged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата и время окончательного удаления.",
    )

    # -------------------------------------------------------------------------
    # Связи
    # -------------------------------------------------------------------------

    node: Mapped[FileSystemNode] = relationship(
        "FileSystemNode",
        foreign_keys=[node_id],
        back_populates="trash_item",
        lazy="selectin",
    )

    owner: Mapped[User] = relationship(
        "User",
        foreign_keys=[owner_id],
        lazy="selectin",
    )

    deleter: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[deleted_by],
        lazy="selectin",
    )

    original_parent: Mapped[FileSystemNode | None] = relationship(
        "FileSystemNode",
        foreign_keys=[original_parent_id],
        lazy="selectin",
    )

    # -------------------------------------------------------------------------
    # Вспомогательные свойства и методы
    # -------------------------------------------------------------------------

    @property
    def is_in_trash(self) -> bool:
        """Возвращает True, если элемент находится в корзине."""

        return self.status == TrashItemStatus.IN_TRASH

    @property
    def is_restored(self) -> bool:
        """Возвращает True, если элемент был восстановлен."""

        return self.status == TrashItemStatus.RESTORED

    @property
    def is_purged(self) -> bool:
        """Возвращает True, если элемент окончательно удалён."""

        return self.status == TrashItemStatus.PURGED or self.purged_at is not None

    @property
    def can_restore(self) -> bool:
        """Возвращает True, если элемент можно восстановить."""

        return (
            self.status == TrashItemStatus.IN_TRASH
            and self.restore_available
            and self.purged_at is None
        )

    # -------------------------------------------------------------------------
    # Методы изменения состояния
    # -------------------------------------------------------------------------

    def restore(self) -> None:
        """Помечает элемент корзины как восстановленный."""

        self.status = TrashItemStatus.RESTORED
        self.restore_available = False

    def purge(self, purged_at: datetime | None = None) -> None:
        """Помечает элемент корзины как окончательно удалённый.

        Args:
            purged_at: Дата и время окончательного удаления. Если не передано,
                используется текущее UTC-время.
        """

        self.status = TrashItemStatus.PURGED
        self.restore_available = False
        self.purged_at = purged_at or datetime.now(UTC)

    def disable_restore(self) -> None:
        """Запрещает восстановление элемента."""

        self.restore_available = False

    def is_expired_at(self, moment: datetime) -> bool:
        """Проверяет, истёк ли срок хранения элемента в корзине.

        Args:
            moment: Дата и время для проверки срока хранения.

        Returns:
            True, если срок хранения истёк к указанному моменту.
        """

        return self.expires_at is not None and self.expires_at <= moment

    def __repr__(self) -> str:
        return (
            f"<TrashItem("
            f"id={self.id}, "
            f"node_id={self.node_id}, "
            f"owner_id={self.owner_id}, "
            f"status={self.status.value!r}, "
            f"restore_available={self.restore_available}, "
            f"purged_at={self.purged_at}"
            f")>"
        )
