from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, ConfigDict, Field, field_validator

from database.models.enums import (
    FilePreviewStatus,
    FileProcessingStatus,
    FileVersionStatus,
    StorageObjectStatus,
)
from schemas.common import BaseSchema, PaginationParams
from schemas.nodes import NodeListItem, NodeRead, validate_node_name


class FileMetadataRead(BaseSchema):
    """Метаданные содержимого файла без внутренних storage-ключей."""

    size_bytes: int = Field(
        ...,
        ge=0,
        description="Размер файла в байтах.",
    )
    mime_type: str | None = Field(
        default=None,
        max_length=255,
        description="MIME-тип файла.",
        examples=["application/pdf", "image/png", "text/plain"],
    )
    extension: str | None = Field(
        default=None,
        max_length=32,
        description="Расширение файла без ведущей точки.",
        examples=["pdf", "png", "txt"],
    )
    checksum: str | None = Field(
        default=None,
        max_length=128,
        description="Контрольная сумма файла.",
    )
    checksum_algorithm: str | None = Field(
        default=None,
        max_length=32,
        description="Алгоритм контрольной суммы.",
        examples=["sha256", "md5"],
    )
    storage_status: StorageObjectStatus = Field(
        ...,
        description="Статус физического объекта файла в хранилище.",
    )
    processing_status: FileProcessingStatus = Field(
        ...,
        description="Статус обработки файла.",
    )
    preview_status: FilePreviewStatus = Field(
        ...,
        description="Статус генерации предпросмотра файла.",
    )
    current_version_id: UUID | None = Field(
        default=None,
        description="Идентификатор текущей версии файла.",
    )


class FileRead(BaseSchema):
    """
    Полное публичное представление файла.

    В этой схеме намеренно нет storage_bucket, storage_key и preview_storage_key,
    чтобы не раскрывать внутреннюю структуру объектного хранилища.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор metadata-записи файла.",
    )
    node_id: UUID = Field(
        ...,
        description="Идентификатор узла файловой системы, связанного с файлом.",
    )
    size_bytes: int = Field(
        ...,
        ge=0,
        description="Размер файла в байтах.",
    )
    mime_type: str | None = Field(
        default=None,
        max_length=255,
        description="MIME-тип файла.",
    )
    extension: str | None = Field(
        default=None,
        max_length=32,
        description="Расширение файла без ведущей точки.",
    )
    checksum: str | None = Field(
        default=None,
        max_length=128,
        description="Контрольная сумма файла.",
    )
    checksum_algorithm: str | None = Field(
        default=None,
        max_length=32,
        description="Алгоритм контрольной суммы.",
    )
    storage_status: StorageObjectStatus = Field(
        ...,
        description="Статус физического объекта файла в хранилище.",
    )
    processing_status: FileProcessingStatus = Field(
        ...,
        description="Статус обработки файла.",
    )
    preview_status: FilePreviewStatus = Field(
        ...,
        description="Статус генерации предпросмотра файла.",
    )
    current_version_id: UUID | None = Field(
        default=None,
        description="Идентификатор текущей версии файла.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания metadata-записи файла.",
    )
    updated_at: datetime = Field(
        ...,
        description="Дата и время последнего обновления metadata-записи файла.",
    )
    node: NodeRead | None = Field(
        default=None,
        description="Общие данные узла файловой системы, если они были загружены.",
    )


class FileListItem(BaseSchema):
    """Краткое представление файла для списков."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор metadata-записи файла.",
    )
    node_id: UUID = Field(
        ...,
        description="Идентификатор узла файловой системы, связанного с файлом.",
    )
    size_bytes: int = Field(
        ...,
        ge=0,
        description="Размер файла в байтах.",
    )
    mime_type: str | None = Field(
        default=None,
        max_length=255,
        description="MIME-тип файла.",
    )
    extension: str | None = Field(
        default=None,
        max_length=32,
        description="Расширение файла без ведущей точки.",
    )
    checksum: str | None = Field(
        default=None,
        max_length=128,
        description="Контрольная сумма файла.",
    )
    checksum_algorithm: str | None = Field(
        default=None,
        max_length=32,
        description="Алгоритм контрольной суммы.",
    )
    storage_status: StorageObjectStatus = Field(
        ...,
        description="Статус физического объекта файла в хранилище.",
    )
    processing_status: FileProcessingStatus = Field(
        ...,
        description="Статус обработки файла.",
    )
    preview_status: FilePreviewStatus = Field(
        ...,
        description="Статус генерации предпросмотра файла.",
    )
    current_version_id: UUID | None = Field(
        default=None,
        description="Идентификатор текущей версии файла.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания metadata-записи файла.",
    )
    updated_at: datetime = Field(
        ...,
        description="Дата и время последнего обновления metadata-записи файла.",
    )
    node: NodeListItem | None = Field(
        default=None,
        description="Краткие данные узла файловой системы, если они были загружены.",
    )


class FileUpdateRequest(BaseSchema):
    """Запрос на обновление пользовательских metadata файла."""

    mime_type: str | None = Field(
        default=None,
        max_length=255,
        description="Новый MIME-тип файла.",
    )
    extension: str | None = Field(
        default=None,
        max_length=32,
        description="Новое расширение файла без ведущей точки.",
    )
    checksum: str | None = Field(
        default=None,
        max_length=128,
        description="Новая контрольная сумма файла.",
    )
    checksum_algorithm: str | None = Field(
        default=None,
        max_length=32,
        description="Новый алгоритм контрольной суммы.",
    )

    @field_validator("mime_type", "extension", "checksum", "checksum_algorithm")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("extension")
    @classmethod
    def normalize_extension(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip().lower().lstrip(".")
        return normalized_value or None

    @field_validator("checksum_algorithm")
    @classmethod
    def normalize_checksum_algorithm(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip().lower()
        return normalized_value or None


class FileRenameRequest(BaseSchema):
    """Запрос на переименование файла."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Новое имя файла.",
        examples=["document.pdf", "photo.png"],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_node_name(value)


class FileMoveRequest(BaseSchema):
    """Запрос на перемещение файла."""

    target_parent_id: UUID | None = Field(
        default=None,
        description="Идентификатор целевой папки. None означает перемещение в корень.",
    )


class FileDownloadRequest(BaseSchema):
    """Запрос на получение ссылки для скачивания файла."""

    file_id: UUID = Field(
        ...,
        description="Идентификатор файла, для которого нужно получить ссылку на скачивание.",
    )
    version_id: UUID | None = Field(
        default=None,
        description="Идентификатор версии файла. None означает скачивание текущей версии.",
    )
    force_download: bool = Field(
        default=True,
        description="Добавлять ли заголовки для скачивания как attachment.",
    )
    filename: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Имя файла, которое нужно предложить клиенту при скачивании.",
    )

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return validate_node_name(value)


class FileDownloadResponse(BaseSchema):
    """Ответ со ссылкой на скачивание файла."""

    presigned_url: AnyHttpUrl | str = Field(
        ...,
        description="Предварительно подписанная ссылка на скачивание файла.",
    )
    expires_at: datetime = Field(
        ...,
        description="Дата и время истечения срока действия ссылки.",
    )
    method: str = Field(
        default="GET",
        description="HTTP-метод, которым нужно воспользоваться для скачивания.",
        examples=["GET"],
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP-заголовки, которые нужно использовать при скачивании, если применимо.",
    )
    file_id: UUID | None = Field(
        default=None,
        description="Идентификатор файла, для которого сформирована ссылка.",
    )
    version_id: UUID | None = Field(
        default=None,
        description="Идентификатор версии файла, если ссылка сформирована для конкретной версии.",
    )
    filename: str | None = Field(
        default=None,
        description="Предлагаемое имя файла для скачивания.",
    )
    size_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Размер скачиваемого файла в байтах, если известен.",
    )
    mime_type: str | None = Field(
        default=None,
        max_length=255,
        description="MIME-тип скачиваемого файла, если известен.",
    )

    @field_validator("method")
    @classmethod
    def normalize_method(cls, value: str) -> str:
        normalized_value = value.strip().upper()

        if not normalized_value:
            raise ValueError("HTTP-метод не должен быть пустым.")

        return normalized_value


class FilePreviewRead(BaseSchema):
    """Представление предпросмотра файла."""

    file_id: UUID = Field(
        ...,
        description="Идентификатор файла.",
    )
    preview_status: FilePreviewStatus = Field(
        ...,
        description="Статус генерации предпросмотра.",
    )
    preview_available: bool = Field(
        default=False,
        description="Доступен ли предпросмотр файла.",
    )
    presigned_url: AnyHttpUrl | str | None = Field(
        default=None,
        description="Предварительно подписанная ссылка на предпросмотр, если он доступен.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Дата и время истечения ссылки на предпросмотр.",
    )
    mime_type: str | None = Field(
        default=None,
        max_length=255,
        description="MIME-тип предпросмотра.",
    )
    message: str | None = Field(
        default=None,
        description="Дополнительное сообщение о состоянии предпросмотра.",
    )


class FileVersionRead(BaseSchema):
    """
    Полное публичное представление версии файла.

    storage_bucket и storage_key намеренно не возвращаются.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор версии файла.",
    )
    file_id: UUID = Field(
        ...,
        description="Идентификатор файла, к которому относится версия.",
    )
    version_number: int = Field(
        ...,
        ge=1,
        description="Порядковый номер версии внутри файла.",
    )
    status: FileVersionStatus = Field(
        ...,
        description="Статус версии файла.",
    )
    size_bytes: int = Field(
        ...,
        ge=0,
        description="Размер версии файла в байтах.",
    )
    checksum: str | None = Field(
        default=None,
        max_length=128,
        description="Контрольная сумма версии файла.",
    )
    checksum_algorithm: str | None = Field(
        default=None,
        max_length=32,
        description="Алгоритм контрольной суммы версии файла.",
    )
    mime_type: str | None = Field(
        default=None,
        max_length=255,
        description="MIME-тип версии файла.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания версии файла.",
    )
    created_by: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, создавшего версию файла.",
    )
    change_comment: str | None = Field(
        default=None,
        description="Комментарий к изменению версии.",
    )
    is_current: bool = Field(
        ...,
        description="Признак текущей активной версии файла.",
    )


class FileVersionListItem(BaseSchema):
    """Краткое представление версии файла для списков."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор версии файла.",
    )
    file_id: UUID = Field(
        ...,
        description="Идентификатор файла, к которому относится версия.",
    )
    version_number: int = Field(
        ...,
        ge=1,
        description="Порядковый номер версии внутри файла.",
    )
    status: FileVersionStatus = Field(
        ...,
        description="Статус версии файла.",
    )
    size_bytes: int = Field(
        ...,
        ge=0,
        description="Размер версии файла в байтах.",
    )
    mime_type: str | None = Field(
        default=None,
        max_length=255,
        description="MIME-тип версии файла.",
    )
    checksum: str | None = Field(
        default=None,
        max_length=128,
        description="Контрольная сумма версии файла.",
    )
    checksum_algorithm: str | None = Field(
        default=None,
        max_length=32,
        description="Алгоритм контрольной суммы версии файла.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания версии файла.",
    )
    created_by: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, создавшего версию файла.",
    )
    is_current: bool = Field(
        ...,
        description="Признак текущей активной версии файла.",
    )


class FileVersionRestoreRequest(BaseSchema):
    """Запрос на восстановление версии файла как текущей."""

    version_id: UUID = Field(
        ...,
        description="Идентификатор версии файла, которую нужно восстановить.",
    )
    change_comment: str | None = Field(
        default=None,
        max_length=512,
        description="Комментарий к восстановлению версии.",
    )

    @field_validator("change_comment")
    @classmethod
    def normalize_change_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class FileSearchQuery(PaginationParams):
    """Параметры поиска файлов."""

    query: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Поисковая строка по имени файла, пути или metadata.",
        examples=["report", "pdf", "photo"],
    )
    parent_id: UUID | None = Field(
        default=None,
        description="Ограничить поиск указанной папкой.",
    )
    owner_id: UUID | None = Field(
        default=None,
        description="Ограничить поиск указанным владельцем.",
    )
    mime_type: str | None = Field(
        default=None,
        max_length=255,
        description="Фильтр по MIME-типу.",
        examples=["application/pdf", "image/png"],
    )
    extension: str | None = Field(
        default=None,
        max_length=32,
        description="Фильтр по расширению файла без ведущей точки.",
        examples=["pdf", "png", "txt"],
    )
    storage_status: StorageObjectStatus | None = Field(
        default=None,
        description="Фильтр по статусу объекта в хранилище.",
    )
    processing_status: FileProcessingStatus | None = Field(
        default=None,
        description="Фильтр по статусу обработки файла.",
    )
    preview_status: FilePreviewStatus | None = Field(
        default=None,
        description="Фильтр по статусу предпросмотра.",
    )
    min_size_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Минимальный размер файла в байтах.",
    )
    max_size_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Максимальный размер файла в байтах.",
    )
    created_from: datetime | None = Field(
        default=None,
        description="Фильтр по дате создания: начало диапазона включительно.",
    )
    created_to: datetime | None = Field(
        default=None,
        description="Фильтр по дате создания: конец диапазона включительно.",
    )
    updated_from: datetime | None = Field(
        default=None,
        description="Фильтр по дате обновления: начало диапазона включительно.",
    )
    updated_to: datetime | None = Field(
        default=None,
        description="Фильтр по дате обновления: конец диапазона включительно.",
    )
    include_deleted: bool = Field(
        default=False,
        description="Включать ли логически удалённые файлы в результаты поиска.",
    )
    sort_by: str = Field(
        default="created_at",
        min_length=1,
        max_length=64,
        description="Поле сортировки.",
        examples=["name", "created_at", "updated_at", "size_bytes", "mime_type"],
    )
    sort_desc: bool = Field(
        default=True,
        description="Сортировать по убыванию.",
    )

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("mime_type")
    @classmethod
    def normalize_mime_type(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip().lower()
        return normalized_value or None

    @field_validator("extension")
    @classmethod
    def normalize_extension(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip().lower().lstrip(".")
        return normalized_value or None

    @field_validator("max_size_bytes")
    @classmethod
    def validate_size_range(
        cls,
        value: int | None,
        info: object,
    ) -> int | None:
        data = getattr(info, "data", {})
        min_size_bytes = data.get("min_size_bytes")

        if min_size_bytes is not None and value is not None and value < min_size_bytes:
            raise ValueError("max_size_bytes не может быть меньше min_size_bytes.")

        return value

    @field_validator("created_to")
    @classmethod
    def validate_created_range(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        data = getattr(info, "data", {})
        created_from = data.get("created_from")

        if created_from is not None and value is not None and value < created_from:
            raise ValueError("created_to не может быть раньше created_from.")

        return value

    @field_validator("updated_to")
    @classmethod
    def validate_updated_range(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        data = getattr(info, "data", {})
        updated_from = data.get("updated_from")

        if updated_from is not None and value is not None and value < updated_from:
            raise ValueError("updated_to не может быть раньше updated_from.")

        return value
