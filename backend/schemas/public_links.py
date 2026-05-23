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
    model_validator,
)

from database.models.enums import PublicLinkPermissionType, PublicLinkStatus
from schemas.common import BaseSchema, PaginationParams
from schemas.nodes import NodeListItem


class PublicLinkCreateRequest(BaseSchema):
    """Запрос на создание публичной ссылки."""

    node_id: UUID = Field(
        ...,
        description="Идентификатор файла или папки, для которого создаётся публичная ссылка.",
    )
    permission_type: PublicLinkPermissionType = Field(
        default=PublicLinkPermissionType.DOWNLOAD,
        description="Тип доступа, предоставляемый публичной ссылкой.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Дата и время истечения срока действия публичной ссылки.",
    )
    max_downloads: int | None = Field(
        default=None,
        ge=0,
        description="Максимальное количество скачиваний. None означает отсутствие лимита.",
    )
    password: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Пароль для защиты публичной ссылки. Хэширование выполняется в service/security-слое.",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Необязательное описание публичной ссылки.",
    )

    @field_validator("password", "description")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

class PublicLinkUpdateRequest(BaseSchema):
    """Запрос на обновление публичной ссылки."""

    permission_type: PublicLinkPermissionType | None = Field(
        default=None,
        description="Новый тип доступа публичной ссылки.",
    )
    status: PublicLinkStatus | None = Field(
        default=None,
        description="Новый статус публичной ссылки.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Новая дата истечения срока действия ссылки. None может означать отсутствие срока.",
    )
    max_downloads: int | None = Field(
        default=None,
        ge=0,
        description="Новый лимит скачиваний. None означает отсутствие лимита.",
    )
    password: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Новый пароль публичной ссылки. Хэширование выполняется в service/security-слое.",
    )
    clear_password: bool = Field(
        default=False,
        description="Удалить пароль публичной ссылки.",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Новое описание публичной ссылки.",
    )
    is_active: bool | None = Field(
        default=None,
        description="Новый признак активности публичной ссылки.",
    )

    @field_validator("password", "description")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @model_validator(mode="after")
    def validate_update_fields(self) -> PublicLinkUpdateRequest:
        update_fields = {
            "permission_type",
            "status",
            "expires_at",
            "max_downloads",
            "password",
            "clear_password",
            "description",
            "is_active",
        }
        if not (self.model_fields_set & update_fields):
            raise ValueError("Нужно передать хотя бы одно поле для изменения публичной ссылки.")
        if self.password is not None and self.clear_password:
            raise ValueError("Нельзя одновременно передавать новый пароль и флаг clear_password.")

        return self


class PublicLinkRead(BaseSchema):
    """Полное безопасное представление публичной ссылки для владельца."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор публичной ссылки.",
    )
    node_id: UUID = Field(
        ...,
        description="Идентификатор узла файловой системы, доступного по ссылке.",
    )
    created_by: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, создавшего публичную ссылку.",
    )
    token: str = Field(
        ...,
        description="Публичный токен ссылки.",
    )
    permission_type: PublicLinkPermissionType = Field(
        ...,
        description="Тип доступа, предоставляемый публичной ссылкой.",
    )
    status: PublicLinkStatus = Field(
        ...,
        description="Текущий статус публичной ссылки.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Дата и время истечения срока действия публичной ссылки.",
    )
    max_downloads: int | None = Field(
        default=None,
        ge=0,
        description="Максимальное количество скачиваний. None означает отсутствие лимита.",
    )
    download_count: int = Field(
        ...,
        ge=0,
        description="Текущее количество скачиваний по публичной ссылке.",
    )
    view_count: int = Field(
        ...,
        ge=0,
        description="Количество просмотров публичной ссылки.",
    )
    upload_count: int = Field(
        ...,
        ge=0,
        description="Количество загрузок через публичную ссылку.",
    )
    is_active: bool = Field(
        ...,
        description="Признак активности публичной ссылки.",
    )
    revoked_at: datetime | None = Field(
        default=None,
        description="Дата и время отзыва публичной ссылки.",
    )
    revoked_by: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, отозвавшего публичную ссылку.",
    )
    revoke_reason: str | None = Field(
        default=None,
        description="Причина отзыва публичной ссылки.",
    )
    last_accessed_at: datetime | None = Field(
        default=None,
        description="Дата и время последнего обращения к публичной ссылке.",
    )
    last_downloaded_at: datetime | None = Field(
        default=None,
        description="Дата и время последнего скачивания по публичной ссылке.",
    )
    last_uploaded_at: datetime | None = Field(
        default=None,
        description="Дата и время последней загрузки через публичную ссылку.",
    )
    description: str | None = Field(
        default=None,
        description="Описание публичной ссылки.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания публичной ссылки.",
    )
    has_password: bool = Field(
        default=False,
        description="Защищена ли публичная ссылка паролем.",
    )
    node: NodeListItem | None = Field(
        default=None,
        description="Краткие данные узла файловой системы, если они были загружены.",
    )

    @computed_field(description="Достигнут ли лимит скачиваний.")
    @property
    def is_download_limit_reached(self) -> bool:
        return (
            self.max_downloads is not None and self.download_count >= self.max_downloads
        )

    @computed_field(description="Отозвана ли публичная ссылка.")
    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None or self.status == PublicLinkStatus.REVOKED


class PublicLinkListItem(BaseSchema):
    """Краткое представление публичной ссылки для списков."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор публичной ссылки.",
    )
    node_id: UUID = Field(
        ...,
        description="Идентификатор узла файловой системы, доступного по ссылке.",
    )
    created_by: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, создавшего публичную ссылку.",
    )
    token: str = Field(
        ...,
        description="Публичный токен ссылки.",
    )
    permission_type: PublicLinkPermissionType = Field(
        ...,
        description="Тип доступа, предоставляемый публичной ссылкой.",
    )
    status: PublicLinkStatus = Field(
        ...,
        description="Текущий статус публичной ссылки.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Дата и время истечения срока действия публичной ссылки.",
    )
    max_downloads: int | None = Field(
        default=None,
        ge=0,
        description="Максимальное количество скачиваний. None означает отсутствие лимита.",
    )
    download_count: int = Field(
        ...,
        ge=0,
        description="Текущее количество скачиваний по публичной ссылке.",
    )
    view_count: int = Field(
        ...,
        ge=0,
        description="Количество просмотров публичной ссылки.",
    )
    upload_count: int = Field(
        ...,
        ge=0,
        description="Количество загрузок через публичную ссылку.",
    )
    is_active: bool = Field(
        ...,
        description="Признак активности публичной ссылки.",
    )
    has_password: bool = Field(
        default=False,
        description="Защищена ли публичная ссылка паролем.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания публичной ссылки.",
    )
    node: NodeListItem | None = Field(
        default=None,
        description="Краткие данные узла файловой системы, если они были загружены.",
    )


class PublicLinkPublicRead(BaseSchema):
    """Публичное представление ссылки без внутренних и владельческих данных."""

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор публичной ссылки.",
    )
    node_id: UUID = Field(
        ...,
        description="Идентификатор доступного узла файловой системы.",
    )
    permission_type: PublicLinkPermissionType = Field(
        ...,
        description="Тип доступа, предоставляемый публичной ссылкой.",
    )
    status: PublicLinkStatus = Field(
        ...,
        description="Текущий статус публичной ссылки.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Дата и время истечения срока действия публичной ссылки.",
    )
    has_password: bool = Field(
        default=False,
        description="Требуется ли пароль для доступа к публичной ссылке.",
    )
    description: str | None = Field(
        default=None,
        description="Описание публичной ссылки.",
    )
    node: NodeListItem | None = Field(
        default=None,
        description="Краткие данные доступного узла, если их можно показывать публично.",
    )


class PublicLinkAccessRequest(BaseSchema):
    """Запрос на доступ к публичной ссылке."""

    token: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Публичный токен ссылки.",
    )
    password: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Пароль публичной ссылки, если она защищена.",
    )

    @field_validator("token", "password")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("Значение не должно быть пустым.")

        return normalized_value


class PublicLinkAccessResponse(BaseSchema):
    """Ответ после проверки доступа к публичной ссылке."""

    allowed: bool = Field(
        ...,
        description="Разрешён ли доступ к публичной ссылке.",
    )
    link: PublicLinkPublicRead | None = Field(
        default=None,
        description="Публичные данные ссылки, если доступ разрешён.",
    )
    requires_password: bool = Field(
        default=False,
        description="Требуется ли пароль для доступа.",
    )
    message: str | None = Field(
        default=None,
        description="Дополнительное сообщение о результате проверки доступа.",
    )


class PublicLinkDownloadResponse(BaseSchema):
    """Ответ со ссылкой на скачивание через публичную ссылку."""

    presigned_url: AnyHttpUrl | str = Field(
        ...,
        description="Предварительно подписанная ссылка на скачивание.",
    )
    expires_at: datetime = Field(
        ...,
        description="Дата и время истечения срока действия ссылки на скачивание.",
    )
    method: str = Field(
        default="GET",
        description="HTTP-метод для скачивания.",
        examples=["GET"],
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP-заголовки, которые нужно использовать при скачивании.",
    )
    filename: str | None = Field(
        default=None,
        description="Предлагаемое имя скачиваемого файла.",
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


class PublicLinkRevokeRequest(BaseSchema):
    """Запрос на отзыв публичной ссылки."""

    revoke_reason: str | None = Field(
        default=None,
        max_length=512,
        description="Причина отзыва публичной ссылки.",
    )

    @field_validator("revoke_reason")
    @classmethod
    def normalize_revoke_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class PublicLinkQueryParams(PaginationParams):
    """Параметры фильтрации публичных ссылок."""

    node_id: UUID | None = Field(
        default=None,
        description="Фильтр по узлу файловой системы.",
    )
    created_by: UUID | None = Field(
        default=None,
        description="Фильтр по пользователю, создавшему публичную ссылку.",
    )
    permission_type: PublicLinkPermissionType | None = Field(
        default=None,
        description="Фильтр по типу доступа публичной ссылки.",
    )
    status: PublicLinkStatus | None = Field(
        default=None,
        description="Фильтр по статусу публичной ссылки.",
    )
    is_active: bool | None = Field(
        default=None,
        description="Фильтр по признаку активности публичной ссылки.",
    )
    has_password: bool | None = Field(
        default=None,
        description="Фильтр по признаку защиты паролем.",
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
        description="Вернуть ссылки, срок действия которых истекает не позднее указанного времени.",
    )
    query: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Поисковая строка по описанию или токену ссылки.",
    )
    sort_by: str = Field(
        default="created_at",
        min_length=1,
        max_length=64,
        description="Поле сортировки.",
        examples=["created_at", "expires_at", "download_count", "view_count", "status"],
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
