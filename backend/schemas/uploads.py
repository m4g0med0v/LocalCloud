from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    ConfigDict,
    Field,
    ValidationInfo,
    computed_field,
    field_validator,
)

from database.models.enums import UploadPartStatus, UploadSessionStatus
from schemas.common import BaseSchema, PaginationParams
from schemas.nodes import validate_node_name


class UploadSessionCreateRequest(BaseSchema):
    """Запрос на создание multipart upload-сессии."""

    parent_node_id: UUID = Field(
        ...,
        description="Идентификатор папки назначения, в которой будет создан загруженный файл.",
    )
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Оригинальное имя загружаемого файла.",
        examples=["document.pdf", "archive.zip", "photo.png"],
    )
    file_size_bytes: int = Field(
        ...,
        gt=0,
        description="Общий размер загружаемого файла в байтах.",
    )
    part_size_bytes: int | None = Field(
        default=None,
        gt=0,
        description="Желаемый размер одной части multipart upload в байтах. Если None, размер выбирает сервисный слой.",
    )
    parts_count: int = Field(
        ...,
        gt=0,
        description="Общее количество частей загрузки.",
    )
    mime_type: str | None = Field(
        default=None,
        max_length=255,
        description="MIME-тип загружаемого файла.",
        examples=["application/pdf", "image/png"],
    )
    checksum: str | None = Field(
        default=None,
        max_length=128,
        description="Контрольная сумма всего файла.",
    )
    checksum_algorithm: str | None = Field(
        default=None,
        max_length=32,
        description="Алгоритм контрольной суммы.",
        examples=["sha256", "md5"],
    )

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        return validate_node_name(value)

    @field_validator("mime_type", "checksum", "checksum_algorithm")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("checksum_algorithm")
    @classmethod
    def normalize_checksum_algorithm(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip().lower()
        return normalized_value or None


class UploadSessionRead(BaseSchema):
    """Полное публичное представление upload-сессии."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор upload-сессии.",
    )
    user_id: UUID = Field(
        ...,
        description="Идентификатор пользователя, инициировавшего загрузку.",
    )
    parent_node_id: UUID = Field(
        ...,
        description="Идентификатор папки назначения.",
    )
    file_name: str = Field(
        ...,
        description="Оригинальное имя загружаемого файла.",
    )
    file_size_bytes: int = Field(
        ...,
        gt=0,
        description="Общий размер файла в байтах.",
    )
    part_size_bytes: int = Field(
        ...,
        gt=0,
        description="Размер одной части multipart upload в байтах.",
    )
    mime_type: str | None = Field(
        default=None,
        max_length=255,
        description="MIME-тип загружаемого файла.",
    )
    checksum: str | None = Field(
        default=None,
        max_length=128,
        description="Контрольная сумма всего файла.",
    )
    checksum_algorithm: str | None = Field(
        default=None,
        max_length=32,
        description="Алгоритм контрольной суммы.",
    )
    status: UploadSessionStatus = Field(
        ...,
        description="Текущий статус upload-сессии.",
    )
    parts_count: int = Field(
        ...,
        gt=0,
        description="Общее количество частей загрузки.",
    )
    uploaded_parts_count: int = Field(
        ...,
        ge=0,
        description="Количество успешно загруженных частей.",
    )
    uploaded_bytes: int = Field(
        ...,
        ge=0,
        description="Количество байтов, подтверждённых как загруженные.",
    )
    expires_at: datetime = Field(
        ...,
        description="Дата и время истечения upload-сессии.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Дата и время завершения загрузки.",
    )
    aborted_at: datetime | None = Field(
        default=None,
        description="Дата и время отмены загрузки.",
    )
    failed_at: datetime | None = Field(
        default=None,
        description="Дата и время ошибки загрузки.",
    )
    failure_reason: str | None = Field(
        default=None,
        description="Описание причины ошибки загрузки.",
    )
    client_ip: str | None = Field(
        default=None,
        max_length=64,
        description="IP-адрес клиента, инициировавшего загрузку.",
    )
    user_agent: str | None = Field(
        default=None,
        description="User-Agent клиента, инициировавшего загрузку.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания upload-сессии.",
    )

    @computed_field(description="Процент загрузки файла.")
    @property
    def progress_percent(self) -> float:
        if self.file_size_bytes <= 0:
            return 0.0

        percent = self.uploaded_bytes / self.file_size_bytes * 100
        return round(min(percent, 100.0), 2)

    @computed_field(description="Завершена ли upload-сессия.")
    @property
    def is_completed(self) -> bool:
        return self.status == UploadSessionStatus.COMPLETED

    @computed_field(description="Является ли upload-сессия терминальной.")
    @property
    def is_terminal(self) -> bool:
        return self.status in {
            UploadSessionStatus.COMPLETED,
            UploadSessionStatus.FAILED,
            UploadSessionStatus.ABORTED,
            UploadSessionStatus.EXPIRED,
        }


class UploadSessionListItem(BaseSchema):
    """Краткое представление upload-сессии для списков."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор upload-сессии.",
    )
    user_id: UUID = Field(
        ...,
        description="Идентификатор пользователя, инициировавшего загрузку.",
    )
    parent_node_id: UUID = Field(
        ...,
        description="Идентификатор папки назначения.",
    )
    file_name: str = Field(
        ...,
        description="Оригинальное имя загружаемого файла.",
    )
    file_size_bytes: int = Field(
        ...,
        gt=0,
        description="Общий размер файла в байтах.",
    )
    status: UploadSessionStatus = Field(
        ...,
        description="Текущий статус upload-сессии.",
    )
    parts_count: int = Field(
        ...,
        gt=0,
        description="Общее количество частей загрузки.",
    )
    uploaded_parts_count: int = Field(
        ...,
        ge=0,
        description="Количество успешно загруженных частей.",
    )
    uploaded_bytes: int = Field(
        ...,
        ge=0,
        description="Количество байтов, подтверждённых как загруженные.",
    )
    expires_at: datetime = Field(
        ...,
        description="Дата и время истечения upload-сессии.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Дата и время завершения загрузки.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания upload-сессии.",
    )

    @computed_field(description="Процент загрузки файла.")
    @property
    def progress_percent(self) -> float:
        if self.file_size_bytes <= 0:
            return 0.0

        percent = self.uploaded_bytes / self.file_size_bytes * 100
        return round(min(percent, 100.0), 2)


class UploadPartRead(BaseSchema):
    """Представление части multipart upload."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор части загрузки.",
    )
    upload_session_id: UUID = Field(
        ...,
        description="Идентификатор upload-сессии, к которой относится часть.",
    )
    part_number: int = Field(
        ...,
        ge=1,
        description="Номер части multipart upload.",
    )
    size_bytes: int = Field(
        ...,
        gt=0,
        description="Размер части в байтах.",
    )
    etag: str | None = Field(
        default=None,
        max_length=512,
        description="ETag, возвращённый MinIO/S3 после успешной загрузки части.",
    )
    checksum: str | None = Field(
        default=None,
        max_length=128,
        description="Необязательная контрольная сумма части.",
    )
    status: UploadPartStatus = Field(
        ...,
        description="Текущий статус части загрузки.",
    )
    uploaded_at: datetime | None = Field(
        default=None,
        description="Дата и время успешной загрузки части.",
    )
    failed_at: datetime | None = Field(
        default=None,
        description="Дата и время ошибки загрузки части.",
    )
    failure_reason: str | None = Field(
        default=None,
        description="Описание причины ошибки загрузки части.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания записи части загрузки.",
    )


class UploadPartPresignedUrlRead(BaseSchema):
    """Pre-signed URL для загрузки одной части файла."""

    part_number: int = Field(
        ...,
        ge=1,
        description="Номер части multipart upload.",
    )
    url: AnyHttpUrl | str = Field(
        ...,
        description="Предварительно подписанная ссылка для загрузки части.",
    )
    method: str = Field(
        default="PUT",
        description="HTTP-метод для загрузки части.",
        examples=["PUT"],
    )
    expires_at: datetime = Field(
        ...,
        description="Дата и время истечения срока действия ссылки.",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP-заголовки, которые нужно передать при загрузке части.",
    )
    size_bytes: int | None = Field(
        default=None,
        gt=0,
        description="Ожидаемый размер части в байтах, если известен.",
    )

    @field_validator("method")
    @classmethod
    def normalize_method(cls, value: str) -> str:
        normalized_value = value.strip().upper()

        if not normalized_value:
            raise ValueError("HTTP-метод не должен быть пустым.")

        return normalized_value


class UploadPresignedUrlsResponse(BaseSchema):
    """Ответ со списком pre-signed URL для загрузки частей файла."""

    upload_session_id: UUID = Field(
        ...,
        description="Идентификатор upload-сессии.",
    )
    status: UploadSessionStatus = Field(
        ...,
        description="Текущий статус upload-сессии.",
    )
    parts: list[UploadPartPresignedUrlRead] = Field(
        default_factory=list,
        description="Список ссылок для загрузки частей.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Общая дата истечения ссылок, если она одинакова для всех частей.",
    )


class UploadPartCompleteRequest(BaseSchema):
    """Запрос на подтверждение успешной загрузки одной части."""

    part_number: int = Field(
        ...,
        ge=1,
        description="Номер загруженной части multipart upload.",
    )
    etag: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="ETag, возвращённый MinIO/S3 после успешной загрузки части.",
    )
    size_bytes: int = Field(
        ...,
        gt=0,
        description="Фактический размер загруженной части в байтах.",
    )
    checksum: str | None = Field(
        default=None,
        max_length=128,
        description="Контрольная сумма части, если она вычислялась клиентом.",
    )

    @field_validator("etag")
    @classmethod
    def validate_etag(cls, value: str) -> str:
        normalized_value = value.strip().strip('"')

        if not normalized_value:
            raise ValueError("etag не должен быть пустым.")

        return normalized_value

    @field_validator("checksum")
    @classmethod
    def normalize_checksum(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class UploadCompleteRequest(BaseSchema):
    """Запрос на завершение multipart upload-сессии."""

    upload_session_id: UUID = Field(
        ...,
        description="Идентификатор upload-сессии, которую нужно завершить.",
    )
    parts: list[UploadPartCompleteRequest] = Field(
        ...,
        min_length=1,
        description="Список успешно загруженных частей с ETag.",
    )
    checksum: str | None = Field(
        default=None,
        max_length=128,
        description="Итоговая контрольная сумма файла, если она вычислялась клиентом.",
    )

    @field_validator("parts")
    @classmethod
    def validate_unique_part_numbers(
        cls,
        value: list[UploadPartCompleteRequest],
    ) -> list[UploadPartCompleteRequest]:
        part_numbers = [part.part_number for part in value]

        if len(part_numbers) != len(set(part_numbers)):
            raise ValueError(
                "Список частей не должен содержать дублирующиеся part_number."
            )

        return value

    @field_validator("checksum")
    @classmethod
    def normalize_checksum(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class UploadCompleteResponse(BaseSchema):
    """Ответ после завершения multipart upload."""

    upload_session: UploadSessionRead = Field(
        ...,
        description="Upload-сессия после завершения.",
    )
    file_id: UUID | None = Field(
        default=None,
        description="Идентификатор созданного файла.",
    )
    node_id: UUID | None = Field(
        default=None,
        description="Идентификатор созданного узла файловой системы.",
    )
    message: str = Field(
        default="Файл успешно загружен.",
        description="Сообщение о результате завершения загрузки.",
    )


class UploadAbortRequest(BaseSchema):
    """Запрос на отмену upload-сессии."""

    upload_session_id: UUID = Field(
        ...,
        description="Идентификатор upload-сессии, которую нужно отменить.",
    )
    reason: str | None = Field(
        default=None,
        max_length=512,
        description="Причина отмены upload-сессии.",
    )

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class UploadProgressRead(BaseSchema):
    """Состояние прогресса upload-сессии."""

    upload_session_id: UUID = Field(
        ...,
        description="Идентификатор upload-сессии.",
    )
    status: UploadSessionStatus = Field(
        ...,
        description="Текущий статус upload-сессии.",
    )
    file_size_bytes: int = Field(
        ...,
        gt=0,
        description="Общий размер файла в байтах.",
    )
    parts_count: int = Field(
        ...,
        gt=0,
        description="Общее количество частей загрузки.",
    )
    uploaded_parts_count: int = Field(
        ...,
        ge=0,
        description="Количество успешно загруженных частей.",
    )
    uploaded_bytes: int = Field(
        ...,
        ge=0,
        description="Количество байтов, подтверждённых как загруженные.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Дата и время истечения upload-сессии.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Дата и время завершения загрузки.",
    )
    failure_reason: str | None = Field(
        default=None,
        description="Описание причины ошибки загрузки.",
    )

    @computed_field(description="Процент загрузки файла.")
    @property
    def progress_percent(self) -> float:
        if self.file_size_bytes <= 0:
            return 0.0

        percent = self.uploaded_bytes / self.file_size_bytes * 100
        return round(min(percent, 100.0), 2)

    @field_validator("uploaded_parts_count")
    @classmethod
    def validate_uploaded_parts_count(
        cls,
        value: int,
        info: ValidationInfo,
    ) -> int:
        parts_count = info.data.get("parts_count")

        if isinstance(parts_count, int) and value > parts_count:
            raise ValueError("uploaded_parts_count не может превышать parts_count.")

        return value

    @field_validator("uploaded_bytes")
    @classmethod
    def validate_uploaded_bytes(
        cls,
        value: int,
        info: ValidationInfo,
    ) -> int:
        file_size_bytes = info.data.get("file_size_bytes")

        if isinstance(file_size_bytes, int) and value > file_size_bytes:
            raise ValueError("uploaded_bytes не может превышать file_size_bytes.")

        return value


class UploadQueryParams(PaginationParams):
    """Параметры фильтрации upload-сессий."""

    user_id: UUID | None = Field(
        default=None,
        description="Фильтр по пользователю, инициировавшему загрузку.",
    )
    parent_node_id: UUID | None = Field(
        default=None,
        description="Фильтр по папке назначения.",
    )
    status: UploadSessionStatus | None = Field(
        default=None,
        description="Фильтр по статусу upload-сессии.",
    )
    filename: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Фильтр или поиск по имени загружаемого файла.",
    )
    created_from: datetime | None = Field(
        default=None,
        description="Фильтр по дате создания: начало диапазона включительно.",
    )
    created_to: datetime | None = Field(
        default=None,
        description="Фильтр по дате создания: конец диапазона включительно.",
    )
    expires_before: datetime | None = Field(
        default=None,
        description="Вернуть upload-сессии, истекающие не позднее указанного времени.",
    )
    include_terminal: bool = Field(
        default=True,
        description="Включать ли завершённые, отменённые, просроченные и ошибочные сессии.",
    )
    sort_by: str = Field(
        default="created_at",
        min_length=1,
        max_length=64,
        description="Поле сортировки.",
        examples=["created_at", "expires_at", "file_name", "status"],
    )
    sort_desc: bool = Field(
        default=True,
        description="Сортировать по убыванию.",
    )

    @field_validator("filename")
    @classmethod
    def normalize_filename(cls, value: str | None) -> str | None:
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
