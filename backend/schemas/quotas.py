from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field, computed_field

from database.models.enums import QuotaResourceType
from schemas.common import BaseSchema


class UserQuotaBase(BaseSchema):
    """Базовые поля пользовательской квоты."""

    storage_limit_bytes: int = Field(
        ...,
        ge=0,
        description="Максимальный размер хранилища пользователя в байтах.",
    )
    storage_used_bytes: int = Field(
        default=0,
        ge=0,
        description="Текущий использованный объём хранилища в байтах.",
    )
    max_file_size_bytes: int = Field(
        ...,
        ge=0,
        description="Максимально допустимый размер одного файла в байтах.",
    )
    files_limit: int | None = Field(
        default=None,
        ge=0,
        description="Максимальное количество файлов. None означает отсутствие лимита.",
    )
    files_used: int = Field(
        default=0,
        ge=0,
        description="Текущее количество файлов пользователя.",
    )
    public_links_limit: int | None = Field(
        default=None,
        ge=0,
        description="Максимальное количество публичных ссылок. None означает отсутствие лимита.",
    )
    public_links_used: int = Field(
        default=0,
        ge=0,
        description="Текущее количество публичных ссылок пользователя.",
    )
    active_upload_sessions_limit: int | None = Field(
        default=None,
        ge=0,
        description="Максимальное количество активных upload-сессий. None означает отсутствие лимита.",
    )
    active_upload_sessions_used: int = Field(
        default=0,
        ge=0,
        description="Текущее количество активных upload-сессий пользователя.",
    )


class UserQuotaCreate(UserQuotaBase):
    """Запрос на создание квоты пользователя."""

    user_id: UUID = Field(
        ...,
        description="Идентификатор пользователя, которому создаётся квота.",
    )


class UserQuotaUpdate(BaseSchema):
    """Запрос на обновление пользовательской квоты."""

    storage_limit_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Новый максимальный размер хранилища пользователя в байтах.",
    )
    storage_used_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Новое значение использованного объёма хранилища в байтах.",
    )
    max_file_size_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Новый максимально допустимый размер одного файла в байтах.",
    )
    files_limit: int | None = Field(
        default=None,
        ge=0,
        description="Новый лимит количества файлов. None означает отсутствие лимита.",
    )
    files_used: int | None = Field(
        default=None,
        ge=0,
        description="Новое текущее количество файлов пользователя.",
    )
    public_links_limit: int | None = Field(
        default=None,
        ge=0,
        description="Новый лимит количества публичных ссылок. None означает отсутствие лимита.",
    )
    public_links_used: int | None = Field(
        default=None,
        ge=0,
        description="Новое текущее количество публичных ссылок пользователя.",
    )
    active_upload_sessions_limit: int | None = Field(
        default=None,
        ge=0,
        description="Новый лимит активных upload-сессий. None означает отсутствие лимита.",
    )
    active_upload_sessions_used: int | None = Field(
        default=None,
        ge=0,
        description="Новое текущее количество активных upload-сессий пользователя.",
    )


class UserQuotaRead(UserQuotaBase):
    """Полное представление пользовательской квоты."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор записи квоты.",
    )
    user_id: UUID = Field(
        ...,
        description="Идентификатор пользователя, которому принадлежит квота.",
    )
    available_storage_bytes: int = Field(
        ...,
        ge=0,
        description="Доступный объём хранилища в байтах.",
    )
    usage_percent: float = Field(
        ...,
        ge=0,
        le=100,
        description="Процент использования хранилища.",
    )
    is_storage_full: bool = Field(
        ...,
        description="Признак полного заполнения хранилища.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания квоты.",
    )
    updated_at: datetime = Field(
        ...,
        description="Дата и время последнего обновления квоты.",
    )


class QuotaUsageRead(BaseSchema):
    """Сводка использования квот пользователя."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: UUID = Field(
        ...,
        description="Идентификатор пользователя.",
    )
    storage_limit_bytes: int = Field(
        ...,
        ge=0,
        description="Максимальный размер хранилища пользователя в байтах.",
    )
    storage_used_bytes: int = Field(
        ...,
        ge=0,
        description="Использованный объём хранилища в байтах.",
    )
    max_file_size_bytes: int = Field(
        ...,
        ge=0,
        description="Максимально допустимый размер одного файла в байтах.",
    )
    files_limit: int | None = Field(
        default=None,
        ge=0,
        description="Максимальное количество файлов. None означает отсутствие лимита.",
    )
    files_used: int = Field(
        ...,
        ge=0,
        description="Текущее количество файлов пользователя.",
    )
    public_links_limit: int | None = Field(
        default=None,
        ge=0,
        description="Максимальное количество публичных ссылок. None означает отсутствие лимита.",
    )
    public_links_used: int = Field(
        ...,
        ge=0,
        description="Текущее количество публичных ссылок пользователя.",
    )
    active_upload_sessions_limit: int | None = Field(
        default=None,
        ge=0,
        description="Максимальное количество активных upload-сессий. None означает отсутствие лимита.",
    )
    active_upload_sessions_used: int = Field(
        ...,
        ge=0,
        description="Текущее количество активных upload-сессий пользователя.",
    )

    @computed_field(description="Доступный объём хранилища в байтах.")
    @property
    def available_storage_bytes(self) -> int:
        return max(self.storage_limit_bytes - self.storage_used_bytes, 0)

    @computed_field(description="Процент использования хранилища.")
    @property
    def usage_percent(self) -> float:
        if self.storage_limit_bytes <= 0:
            return 100.0 if self.storage_used_bytes > 0 else 0.0

        percent = self.storage_used_bytes / self.storage_limit_bytes * 100
        return round(min(percent, 100.0), 2)

    @computed_field(description="Признак полного заполнения хранилища.")
    @property
    def is_storage_full(self) -> bool:
        return self.storage_used_bytes >= self.storage_limit_bytes

    @computed_field(description="Достигнут ли лимит количества файлов.")
    @property
    def is_files_limit_reached(self) -> bool:
        return self.files_limit is not None and self.files_used >= self.files_limit

    @computed_field(description="Достигнут ли лимит публичных ссылок.")
    @property
    def is_public_links_limit_reached(self) -> bool:
        return (
            self.public_links_limit is not None
            and self.public_links_used >= self.public_links_limit
        )

    @computed_field(description="Достигнут ли лимит активных upload-сессий.")
    @property
    def is_active_upload_sessions_limit_reached(self) -> bool:
        return (
            self.active_upload_sessions_limit is not None
            and self.active_upload_sessions_used >= self.active_upload_sessions_limit
        )


class QuotaCheckRequest(BaseSchema):
    """Запрос на проверку возможности расходования квоты."""

    user_id: UUID = Field(
        ...,
        description="Идентификатор пользователя, для которого проверяется квота.",
    )
    resource_type: QuotaResourceType = Field(
        ...,
        description="Тип ресурса, для которого выполняется проверка квоты.",
    )
    requested_amount: int = Field(
        ...,
        ge=0,
        description="Запрашиваемый объём ресурса.",
    )


class QuotaCheckResponse(BaseSchema):
    """Результат проверки квоты."""

    allowed: bool = Field(
        ...,
        description="Разрешена ли операция с учётом текущей квоты.",
    )
    user_id: UUID = Field(
        ...,
        description="Идентификатор пользователя, для которого выполнена проверка.",
    )
    resource_type: QuotaResourceType = Field(
        ...,
        description="Тип проверенного ресурса.",
    )
    requested_amount: int = Field(
        ...,
        ge=0,
        description="Запрошенный объём ресурса.",
    )
    limit: int | None = Field(
        default=None,
        ge=0,
        description="Установленный лимит ресурса. None означает отсутствие лимита.",
    )
    used: int = Field(
        ...,
        ge=0,
        description="Текущий использованный объём ресурса.",
    )
    available: int | None = Field(
        default=None,
        ge=0,
        description="Доступный объём ресурса. None означает отсутствие лимита.",
    )
    reason: str | None = Field(
        default=None,
        max_length=512,
        description="Причина отказа или дополнительное пояснение.",
    )


class QuotaRecalculateRequest(BaseSchema):
    """Запрос на пересчёт квоты пользователя."""

    user_id: UUID = Field(
        ...,
        description="Идентификатор пользователя, для которого нужно пересчитать квоту.",
    )
    resource_types: list[QuotaResourceType] | None = Field(
        default=None,
        description=(
            "Список типов ресурсов для пересчёта. "
            "None означает пересчёт всех поддерживаемых ресурсов."
        ),
    )
    force: bool = Field(
        default=False,
        description="Выполнить пересчёт принудительно.",
    )
